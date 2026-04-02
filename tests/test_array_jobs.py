"""Unit tests for SLURM array-job functionality.

These tests do NOT require a live SLURM cluster and do NOT subclass
TestWorkflows. They cover:

  - ExecutorSettings array-job field defaults and parsing  (TestArrayJobsSettings)
  - run_jobs() dispatch routing                            (TestRunJobsRouting)
  - run_array_jobs() sbatch construction and chunking      (TestRunArrayJobs)
  - _status_lookup_ids() helper edge cases                 (TestStatusLookupIds)
  - check_active_jobs() status resolution for array tasks  (TestCheckActiveArrayJobs)
"""

import asyncio
import base64
import errno
import json
import re
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from snakemake_executor_plugin_slurm import (
    Executor,
    ExecutorSettings,
    _status_lookup_ids,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class _Resources(dict):
    """Dict-like resources with attribute access for known keys only."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e


def _make_mock_job(
    rule_name="myrule",
    name=None,
    wildcards=None,
    jobid=1,
    is_group=False,
    **resources,
):
    """Return a minimal mock job compatible with run_jobs / run_array_jobs."""
    mock_resources = _Resources(resources)

    mock_rule = MagicMock()
    mock_rule.name = rule_name

    job = MagicMock()
    job.resources = mock_resources
    job.rule = mock_rule
    job.name = name if name is not None else rule_name
    job.wildcards = wildcards if wildcards is not None else {}
    job.is_group.return_value = is_group
    job.threads = resources.get("threads", 1)
    job.jobid = jobid
    return job


def _make_executor_stub(array_jobs=None, array_limit=100):
    """Return a minimal Executor stub (bypasses __post_init__ entirely)."""
    executor = Executor.__new__(Executor)
    executor.logger = MagicMock()
    executor.run_uuid = "test-run-uuid"
    executor._fallback_account_arg = None
    executor._fallback_partition = None
    executor._partitions = None
    executor._failed_nodes = set()
    executor._main_event_loop = None
    executor._status_query_calls = 0
    executor._status_query_failures = 0
    executor._status_query_total_seconds = 0.0
    executor._status_query_min_seconds = None
    executor._status_query_max_seconds = 0.0
    executor._status_query_cycle_rows = []
    executor._preemption_warning = False
    executor._submitted_job_clusters = set()

    # Replicate the array_jobs parsing from Executor.__post_init__
    if array_jobs:
        normalized = array_jobs.replace(";", ",")
        executor.array_jobs = {r.strip() for r in normalized.split(",") if r.strip()}
    else:
        executor.array_jobs = set()
    executor.max_array_size = int(array_limit)

    executor.slurm_logdir = Path("/tmp/test_slurm_logs")
    executor.workflow = SimpleNamespace(
        executor_settings=SimpleNamespace(
            array_limit=array_limit,
            status_attempts=1,
            init_seconds_before_status_checks=40,
            keep_successful_logs=False,
            requeue=False,
            qos=None,
            reservation=None,
            pass_command_as_script=False,
        ),
        workdir_init=Path("/tmp"),
    )

    executor._job_submission_executor = MagicMock()
    executor.report_job_success = MagicMock()
    executor.report_job_error = MagicMock()
    executor._report_job_submission_threadsafe = MagicMock()
    executor._report_job_error_threadsafe = MagicMock()
    return executor


class TestArrayJobsSettings:
    """Tests for ExecutorSettings array-job fields and their defaults."""

    def test_array_jobs_default_is_none(self):
        """array_jobs field defaults to None."""
        settings = ExecutorSettings()
        assert settings.array_jobs is None

    def test_array_limit_default_is_1000(self):
        """array_limit field defaults to 1000."""
        settings = ExecutorSettings()
        assert settings.array_limit == 1000

    def test_array_jobs_none_yields_empty_set_on_executor(self):
        """Executor with array_jobs=None initialises self.array_jobs as empty set."""
        executor = _make_executor_stub(array_jobs=None)
        assert executor.array_jobs == set()

    def test_array_jobs_comma_separated_parsed(self):
        """Comma-separated rule names are split into a set."""
        executor = _make_executor_stub(array_jobs="rule1, rule2")
        assert executor.array_jobs == {"rule1", "rule2"}

    def test_array_jobs_semicolons_normalised(self):
        """Semicolons are normalised to commas before splitting."""
        executor = _make_executor_stub(array_jobs="rule1; rule2")
        assert executor.array_jobs == {"rule1", "rule2"}

    def test_array_jobs_all_keyword_preserved(self):
        """The magic keyword 'all' is preserved as a set member."""
        executor = _make_executor_stub(array_jobs="all")
        assert executor.array_jobs == {"all"}

    def test_array_jobs_extra_whitespace_stripped(self):
        """Leading/trailing whitespace is stripped from each rule name."""
        executor = _make_executor_stub(array_jobs="  rule1 ,  rule2  ")
        assert executor.array_jobs == {"rule1", "rule2"}


class TestRunJobsRouting:
    """Tests that run_jobs dispatches to run_job or run_array_jobs correctly."""

    def test_single_non_array_job_uses_run_job(self):
        """One job with no array setting → run_job is enqueued."""
        executor = _make_executor_stub()
        job = _make_mock_job(rule_name="myrule")
        executor.run_jobs([job])

        calls = executor._job_submission_executor.submit.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == executor.run_job

    def test_multiple_non_array_jobs_each_get_run_job(self):
        """Three jobs, no array setting → three individual run_job submissions."""
        executor = _make_executor_stub()
        jobs = [_make_mock_job(rule_name="myrule", jobid=i) for i in range(3)]
        executor.run_jobs(jobs)

        calls = executor._job_submission_executor.submit.call_args_list
        assert len(calls) == 3
        for c in calls:
            assert c[0][0] == executor.run_job

    def test_array_rule_single_ready_job_falls_back_to_run_job(self):
        """Array selected for rule but only 1 ready job → run_job, debug log emitted."""
        executor = _make_executor_stub(array_jobs="myrule")
        job = _make_mock_job(rule_name="myrule")
        executor.run_jobs([job])

        calls = executor._job_submission_executor.submit.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == executor.run_job
        # A debug-level message explains the single-job fallback
        executor.logger.debug.assert_called()

    def test_array_rule_multiple_jobs_use_run_array_jobs(self):
        """Array selected + 3 ready jobs for the same rule → one run_array_jobs call."""
        executor = _make_executor_stub(array_jobs="myrule")
        jobs = [_make_mock_job(rule_name="myrule", jobid=i) for i in range(3)]
        executor.run_jobs(jobs)

        calls = executor._job_submission_executor.submit.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == executor.run_array_jobs
        # All 3 jobs are forwarded together
        assert calls[0][0][1] == jobs

    def test_group_job_for_array_rule_uses_run_job_with_warning(self):
        """Group job whose rule is in array_jobs → run_job; logger.warning called."""
        executor = _make_executor_stub(array_jobs="myrule")
        job = _make_mock_job(rule_name="myrule", is_group=True)
        executor.run_jobs([job])

        calls = executor._job_submission_executor.submit.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == executor.run_job
        executor.logger.warning.assert_called()

    def test_all_keyword_routes_to_run_array_jobs(self):
        """array_jobs='all' + 2 regular jobs for any rule → run_array_jobs."""
        executor = _make_executor_stub(array_jobs="all")
        jobs = [_make_mock_job(rule_name="anyrule", jobid=i) for i in range(2)]
        executor.run_jobs(jobs)

        calls = executor._job_submission_executor.submit.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == executor.run_array_jobs

    def test_mixed_group_and_regular_jobs_routed_independently(self):
        """Group job → run_job; regular job pair for array rule → run_array_jobs."""
        executor = _make_executor_stub(array_jobs="myrule")
        group_job = _make_mock_job(rule_name="myrule", jobid=0, is_group=True)
        regular_jobs = [
            _make_mock_job(rule_name="myrule", jobid=i) for i in range(1, 3)
        ]
        executor.run_jobs([group_job] + regular_jobs)

        calls = executor._job_submission_executor.submit.call_args_list
        assert len(calls) == 2
        methods = [c[0][0] for c in calls]
        assert executor.run_job in methods
        assert executor.run_array_jobs in methods

    def test_array_rule_waits_below_chunk_if_more_eligible_in_dag(self):
        """
        With DAG showing more pending jobs, do not submit until chunk
        size is reached.
        """
        executor = _make_executor_stub(array_jobs="myrule", array_limit=10)
        ready_jobs = [_make_mock_job(rule_name="myrule", jobid=i) for i in range(1, 6)]
        pending_jobs = [
            _make_mock_job(rule_name="myrule", jobid=i) for i in range(1, 101)
        ]
        executor.workflow.dag = SimpleNamespace(needrun_jobs=lambda: pending_jobs)

        executor.run_jobs(ready_jobs)

        assert executor._job_submission_executor.submit.call_count == 0

    def test_array_rule_submits_at_chunk_size_even_if_more_eligible_in_dag(self):
        """
        With DAG showing more pending jobs, submit once at least one full
        chunk is ready.
        """
        executor = _make_executor_stub(array_jobs="myrule", array_limit=10)
        ready_jobs = [_make_mock_job(rule_name="myrule", jobid=i) for i in range(1, 11)]
        pending_jobs = [
            _make_mock_job(rule_name="myrule", jobid=i) for i in range(1, 101)
        ]
        executor.workflow.dag = SimpleNamespace(needrun_jobs=lambda: pending_jobs)

        executor.run_jobs(ready_jobs)

        calls = executor._job_submission_executor.submit.call_args_list
        assert len(calls) == 1
        assert calls[0][0][0] == executor.run_array_jobs
        assert calls[0][0][1] == ready_jobs


class TestRunArrayJobs:
    """Tests for run_array_jobs: sbatch command structure, chunking, error handling."""

    # --- fixtures & helpers ------------------------------------------------

    @pytest.fixture
    def mock_popen_success(self):
        """Popen mock that returns a successful sbatch response with job ID 987654."""
        with patch("snakemake_executor_plugin_slurm.subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.communicate.return_value = ("987654", "")
            proc.returncode = 0
            mock_popen.return_value = proc
            yield mock_popen

    def _build_executor(self, tmp_path, array_limit=1000):
        executor = _make_executor_stub(array_limit=array_limit)
        executor.slurm_logdir = tmp_path / "slurm_logs"
        executor.get_account_arg = MagicMock(
            side_effect=lambda job: iter(["-A testaccount"])
        )
        executor.get_partition_arg = MagicMock(return_value="-p main")
        executor.format_job_exec = MagicMock(
            side_effect=lambda job: f"snakemake_exec_{job.jobid}"
        )
        return executor

    def _make_jobs(self, n=3, rule_name="myrule"):
        return [_make_mock_job(rule_name=rule_name, jobid=i) for i in range(1, n + 1)]

    # --- tests -------------------------------------------------------------

    def test_logfile_per_task_uses_resolved_jobid_and_index(
        self, tmp_path, mock_popen_success
    ):
        """Reported logfile for each task is '<slurm_id>_<index>.log' (1-based)."""
        executor = self._build_executor(tmp_path)
        jobs = self._make_jobs(n=2)
        executor.run_array_jobs(jobs)

        calls = executor._report_job_submission_threadsafe.call_args_list
        assert len(calls) == 2
        for idx, c in enumerate(calls, start=1):
            job_info = c[0][0]
            assert job_info.aux["slurm_logfile"].name == f"987654_{idx}.log"

    def test_external_jobid_per_task_is_jobid_underscore_index(
        self, tmp_path, mock_popen_success
    ):
        """external_jobid for each task is '<slurm_id>_<index>' (1-based)."""
        executor = self._build_executor(tmp_path)
        jobs = self._make_jobs(n=3)
        executor.run_array_jobs(jobs)

        calls = executor._report_job_submission_threadsafe.call_args_list
        assert len(calls) == 3
        external_ids = [c[0][0].external_jobid for c in calls]
        assert external_ids == ["987654_1", "987654_2", "987654_3"]

    def test_array_execs_task_1_absent_tasks_2_plus_present(
        self, tmp_path, mock_popen_success
    ):
        """The --slurm-jobstep-array-execs map has keys 2,3,… but never 1.

        Task 1 executes via the plain base exec_job; tasks 2+ are encoded
        in the compressed map so the job-step can dispatch them.
        """
        executor = self._build_executor(tmp_path)
        jobs = self._make_jobs(n=3)
        executor.run_array_jobs(jobs)
        popen_call_str = mock_popen_success.call_args_list[0][0][0]
        match = re.search(
            r"--slurm-jobstep-array-execs=(?:'([A-Za-z0-9+/=]+)'|([A-Za-z0-9+/=]+))",
            popen_call_str,
        )
        assert match, (
            "Could not find --slurm-jobstep-array-execs in sbatch call.\n"
            f"Call was: {popen_call_str!r}"
        )
        encoded_payload = match.group(1) or match.group(2)
        array_execs = json.loads(base64.b64decode(encoded_payload).decode("utf-8"))
        assert "1" not in array_execs
        assert "2" in array_execs
        assert "3" in array_execs

    def test_array_execs_omits_first_task_of_each_chunk(self, tmp_path):
        """For each chunk, first task uses base exec command and is absent from map."""
        executor = self._build_executor(tmp_path, array_limit=3)
        jobs = self._make_jobs(n=5)

        with patch("snakemake_executor_plugin_slurm.subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.communicate.return_value = ("333333", "")
            proc.returncode = 0
            mock_popen.return_value = proc
            executor.run_array_jobs(jobs)

        first_call_str = mock_popen.call_args_list[0][0][0]
        second_call_str = mock_popen.call_args_list[1][0][0]

        assert '--wrap="snakemake_exec_1 ' in first_call_str
        assert '--wrap="snakemake_exec_4 ' in second_call_str

        first_match = re.search(
            r"--slurm-jobstep-array-execs=(?:'([A-Za-z0-9+/=]+)'|([A-Za-z0-9+/=]+))",
            first_call_str,
        )
        second_match = re.search(
            r"--slurm-jobstep-array-execs=(?:'([A-Za-z0-9+/=]+)'|([A-Za-z0-9+/=]+))",
            second_call_str,
        )
        assert first_match and second_match

        first_payload = first_match.group(1) or first_match.group(2)
        second_payload = second_match.group(1) or second_match.group(2)
        first_map = json.loads(base64.b64decode(first_payload).decode("utf-8"))
        second_map = json.loads(base64.b64decode(second_payload).decode("utf-8"))

        assert "1" not in first_map
        assert "2" in first_map
        assert "3" in first_map
        assert "4" not in second_map
        assert "5" in second_map

    def test_array_limit_produces_chunked_sbatch_calls(self, tmp_path):
        """5 jobs with array_limit=3 → 2 Popen calls: --array=1-3 and --array=4-5."""
        executor = self._build_executor(tmp_path, array_limit=3)
        jobs = self._make_jobs(n=5)

        with patch("snakemake_executor_plugin_slurm.subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.communicate.return_value = ("111111", "")
            proc.returncode = 0
            mock_popen.return_value = proc
            executor.run_array_jobs(jobs)

        assert mock_popen.call_count == 2
        first_call_str = mock_popen.call_args_list[0][0][0]
        second_call_str = mock_popen.call_args_list[1][0][0]
        assert "--array=1-3" in first_call_str
        assert "--array=4-5" in second_call_str

    def test_e2big_retries_with_stdin_script_mode(self, tmp_path):
        """If --wrap exceeds argv size, retry once via /dev/stdin script mode."""
        executor = self._build_executor(tmp_path)
        jobs = self._make_jobs(n=3)

        with patch("snakemake_executor_plugin_slurm.subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.communicate.return_value = ("222222", "")
            proc.returncode = 0
            mock_popen.side_effect = [
                OSError(errno.E2BIG, "Argument list too long"),
                proc,
            ]

            executor.run_array_jobs(jobs)

        assert mock_popen.call_count == 2
        first_call_str = mock_popen.call_args_list[0][0][0]
        second_call_str = mock_popen.call_args_list[1][0][0]
        assert "--wrap=" in first_call_str
        assert "/dev/stdin" in second_call_str
        assert proc.communicate.call_args.kwargs["input"].startswith("#!/bin/sh")

    def test_non_empty_wildcards_in_comment_triggers_warning(
        self, tmp_path, mock_popen_success
    ):
        """
        When wildcards are non-empty, a warning
        about comment limitations is logged.
        """
        executor = self._build_executor(tmp_path)
        jobs = self._make_jobs(n=2)

        with patch(
            "snakemake_executor_plugin_slurm.get_job_wildcards",
            side_effect=["sample_A", "sample_B"],
        ):
            executor.run_array_jobs(jobs)

        executor.logger.warning.assert_called()
        warning_msgs = " ".join(str(c) for c in executor.logger.warning.call_args_list)
        assert "wildcard" in warning_msgs.lower()

    def test_no_wildcards_comment_is_plain_rule_name(
        self, tmp_path, mock_popen_success
    ):
        """Empty wildcards → comment is 'rule_<name>'; no wildcard warning."""
        executor = self._build_executor(tmp_path)
        jobs = self._make_jobs(n=2)

        # Real get_job_wildcards returns "" for jobs with empty wildcards dict
        executor.run_array_jobs(jobs)

        popen_call_str = mock_popen_success.call_args_list[0][0][0]
        assert "rule_myrule" in popen_call_str

        # No wildcard-specific warning should have been issued
        for c in executor.logger.warning.call_args_list:
            assert "wildcard" not in str(c).lower()

    def test_failed_nodes_exclusion_propagated_to_sbatch_call(
        self, tmp_path, mock_popen_success
    ):
        """_failed_nodes set is propagated as --exclude=<node> in the sbatch call."""
        executor = self._build_executor(tmp_path)
        executor._failed_nodes = {"bad_node01"}
        jobs = self._make_jobs(n=2)
        executor.run_array_jobs(jobs)

        popen_call_str = mock_popen_success.call_args_list[0][0][0]
        assert "--exclude=bad_node01" in popen_call_str


class TestStatusLookupIds:
    """Edge-case unit tests for _status_lookup_ids."""

    def test_plain_numeric_id_returns_single_entry(self):
        """A plain numeric job ID returns only itself — no parent appended."""
        assert _status_lookup_ids("12345") == ["12345"]

    def test_array_task_appends_parent_id(self):
        """'<jobid>_<taskid>' with all-numeric parts appends the parent ID."""
        assert _status_lookup_ids("12345_3") == ["12345_3", "12345"]

    def test_non_numeric_parent_not_treated_as_array(self):
        """Non-numeric parent prevents parent-ID fallback."""
        assert _status_lookup_ids("abc_123") == ["abc_123"]

    def test_non_numeric_task_not_treated_as_array(self):
        """Non-numeric task index prevents parent-ID fallback."""
        assert _status_lookup_ids("abc_1") == ["abc_1"]

    def test_multiple_underscores_first_split_only(self):
        """Only the first underscore is used; extra parts make task non-numeric."""
        # parent="12345" (digits), task="3_extra" (not digits) → no fallback
        result = _status_lookup_ids("12345_3_extra")
        assert result == ["12345_3_extra"]


class _NoopAsyncContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_check_executor():
    """Return an Executor stub wired for check_active_jobs tests."""
    executor = Executor.__new__(Executor)
    executor.logger = MagicMock()
    executor.run_uuid = "run-uuid"
    executor.status_rate_limiter = _NoopAsyncContext()
    executor.get_status_command = lambda: "sacct"
    executor.next_seconds_between_status_checks = 40
    executor._status_query_calls = 0
    executor._status_query_failures = 0
    executor._status_query_total_seconds = 0.0
    executor._status_query_min_seconds = None
    executor._status_query_max_seconds = 0.0
    executor._status_query_cycle_rows = []
    executor._preemption_warning = False
    executor._failed_nodes = set()
    executor.report_job_success = MagicMock()
    executor.report_job_error = MagicMock()
    executor.workflow = SimpleNamespace(
        executor_settings=SimpleNamespace(
            status_attempts=1,
            init_seconds_before_status_checks=40,
            keep_successful_logs=False,
            requeue=False,
        )
    )
    return executor


def _run_check(executor, active_jobs):
    """Drain check_active_jobs into a list synchronously."""

    async def _collect():
        remaining = []
        async for job in executor.check_active_jobs(active_jobs):
            remaining.append(job)
        return remaining

    return asyncio.run(_collect())


class TestCheckActiveArrayJobs:
    """Tests for check_active_jobs status resolution with array tasks."""

    def _patch_all(self, monkeypatch, status_dict):
        """Patch all external dependencies used by check_active_jobs."""

        async def _mock_query(command, logger):
            return (status_dict, 0.01)

        monkeypatch.setattr(
            "snakemake_executor_plugin_slurm.query_job_status", _mock_query
        )
        monkeypatch.setattr(
            "snakemake_executor_plugin_slurm.query_job_status_sacct",
            lambda run_uuid: "mock_sacct_cmd",
        )
        monkeypatch.setattr(
            "snakemake_executor_plugin_slurm.get_min_job_age", lambda: 300
        )
        monkeypatch.setattr(
            "snakemake_executor_plugin_slurm.is_query_tool_available",
            lambda tool: True,
        )

    def test_task_level_status_takes_precedence_over_parent(
        self, monkeypatch, tmp_path
    ):
        """Task-specific 'COMPLETED' wins over parent-array 'FAILED'."""
        executor = _make_check_executor()
        self._patch_all(monkeypatch, {"123_2": "COMPLETED", "123": "FAILED"})

        log = tmp_path / "123_2.log"
        log.write_text("content")
        active_job = SimpleNamespace(external_jobid="123_2", aux={"slurm_logfile": log})

        remaining = _run_check(executor, [active_job])

        assert remaining == []
        executor.report_job_success.assert_called_once()
        executor.report_job_error.assert_not_called()

    def test_all_tasks_of_array_resolved_via_parent_status(self, monkeypatch, tmp_path):
        """Multiple array tasks all resolved via parent 'COMPLETED' in one cycle."""
        executor = _make_check_executor()
        self._patch_all(monkeypatch, {"123": "COMPLETED"})

        active_jobs = [
            SimpleNamespace(
                external_jobid=f"123_{i}",
                aux={"slurm_logfile": tmp_path / f"123_{i}.log"},
            )
            for i in range(1, 4)
        ]

        remaining = _run_check(executor, active_jobs)

        assert remaining == []
        assert executor.report_job_success.call_count == 3
        executor.report_job_error.assert_not_called()

    def test_non_terminal_status_keeps_job_active(self, monkeypatch, tmp_path):
        """A status not in the terminal set (e.g. 'RUNNING') keeps the job active."""
        executor = _make_check_executor()
        self._patch_all(monkeypatch, {"123_1": "RUNNING"})

        active_job = SimpleNamespace(
            external_jobid="123_1",
            aux={"slurm_logfile": tmp_path / "123_1.log"},
        )

        remaining = _run_check(executor, [active_job])

        assert remaining == [active_job]
        executor.report_job_success.assert_not_called()
        executor.report_job_error.assert_not_called()


class TestGetAccountArg:
    """Unit tests for get_account_arg() method."""

    def _make_executor_stub(self):
        """Return a minimal Executor stub."""
        executor = Executor.__new__(Executor)
        executor.logger = MagicMock()
        executor._fallback_account_arg = None
        return executor

    @patch("snakemake_executor_plugin_slurm.get_account")
    @patch("snakemake_executor_plugin_slurm.test_account")
    def test_string_account(self, mock_test_account, mock_get_account, tmp_path):
        """String account values work correctly."""
        executor = self._make_executor_stub()
        job = _make_mock_job(slurm_account="123456789")
        result = next(executor.get_account_arg(job))
        assert result == " -A 123456789"
        mock_test_account.assert_called_with("123456789", executor.logger)

    @patch("snakemake_executor_plugin_slurm.get_account")
    @patch("snakemake_executor_plugin_slurm.test_account")
    def test_integer_account(self, mock_test_account, mock_get_account, tmp_path):
        """Integer account values (from YAML parsing) work correctly."""
        executor = self._make_executor_stub()
        job = _make_mock_job(slurm_account=123456789)
        result = next(executor.get_account_arg(job))
        assert result == " -A 123456789"
        mock_test_account.assert_called_with("123456789", executor.logger)

    @patch("snakemake_executor_plugin_slurm.get_account")
    @patch("snakemake_executor_plugin_slurm.test_account")
    def test_multiple_accounts_string(self, mock_test_account, mock_get_account, tmp_path):
        """Multiple string accounts work correctly."""
        executor = self._make_executor_stub()
        job = _make_mock_job(slurm_account="acc1,acc2 acc3")
        results = list(executor.get_account_arg(job))
        assert results == [" -A acc1", " -A acc2", " -A acc3"]

    @patch("snakemake_executor_plugin_slurm.get_account")
    @patch("snakemake_executor_plugin_slurm.test_account")
    def test_multiple_accounts_integer(self, mock_test_account, mock_get_account, tmp_path):
        """Multiple integer accounts work correctly."""
        executor = self._make_executor_stub()
        job = _make_mock_job(slurm_account=123)
        results = list(executor.get_account_arg(job))
        assert results == [" -A 123"]
