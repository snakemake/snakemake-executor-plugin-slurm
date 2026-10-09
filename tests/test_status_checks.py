import asyncio
import os
import shlex
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from snakemake_executor_plugin_slurm import Executor, _get_status_command_default
from snakemake_executor_plugin_slurm.job_status_query import (
    get_status_check_intervals,
    query_job_status_sacct,
    query_job_status_squeue,
)


class _NoopAsyncContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_executor(status_command, init_seconds, max_seconds, next_seconds):
    executor = Executor.__new__(Executor)
    executor.logger = MagicMock()
    executor.run_uuid = "run-uuid"
    executor.status_rate_limiter = _NoopAsyncContext()
    executor.get_status_command = lambda: status_command
    executor.next_seconds_between_status_checks = next_seconds
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
            init_seconds_before_status_checks=init_seconds,
            max_seconds_between_status_checks=max_seconds,
            keep_successful_logs=True,
            requeue=False,
        )
    )
    return executor


def _mock_status_queries(monkeypatch, squeue_output, sacct_output):
    """Mock squeue and sacct output; return the list of issued commands."""
    commands = []

    async def _mock_query_job_status(command, logger):
        commands.append(command)
        if command == "squeue":
            return (squeue_output, 0.01)
        return (sacct_output, 0.01)

    def _mock_sacct_command(run_uuid, job_ids=None):
        if job_ids:
            return f"sacct --jobs {','.join(job_ids)}"
        return "sacct"

    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.query_job_status",
        _mock_query_job_status,
    )
    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.query_job_status_squeue",
        lambda run_uuid: "squeue",
    )
    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.query_job_status_sacct",
        _mock_sacct_command,
    )
    # A MinJobAge below the squeue threshold must not matter for squeue+sacct.
    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.get_min_job_age",
        lambda: 60,
    )
    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.is_query_tool_available",
        lambda tool: True,
    )
    return commands


def _make_job(external_jobid):
    return SimpleNamespace(
        external_jobid=external_jobid,
        aux={"slurm_logfile": Path(f"{external_jobid}.log")},
    )


def _check_active_jobs(executor, active_jobs):
    async def _collect_remaining_jobs():
        remaining = []
        async for job in executor.check_active_jobs(active_jobs):
            remaining.append(job)
        return remaining

    return asyncio.run(_collect_remaining_jobs())


@pytest.mark.parametrize(
    "init_seconds, max_seconds, next_seconds, expected_next_seconds",
    [
        # without finished jobs, the interval grows by 10 s up to the maximum
        (40, 60, 55, 60),
        # init == max gives a fixed interval
        (30, 30, 30, 30),
    ],
)
def test_status_interval_is_capped_by_max_setting(
    monkeypatch, init_seconds, max_seconds, next_seconds, expected_next_seconds
):
    executor = _make_executor("sacct", init_seconds, max_seconds, next_seconds)
    _mock_status_queries(monkeypatch, {}, {"101": "RUNNING"})
    job = _make_job("101")

    remaining = _check_active_jobs(executor, [job])

    assert remaining == [job]
    assert executor.next_seconds_between_status_checks == expected_next_seconds


@pytest.mark.parametrize(
    "status_command, init_seconds, max_seconds, expected_intervals",
    [
        ("squeue+sacct", None, None, (20, 20)),
        ("sacct", None, None, (40, 180)),
        ("squeue", None, None, (40, 180)),
        # a default maximum is never smaller than a set initial time
        ("squeue+sacct", 10, None, (10, 20)),
        ("squeue+sacct", 60, None, (60, 60)),
        ("sacct", 300, None, (300, 300)),
        # a default initial time never exceeds a set maximum
        ("squeue+sacct", None, 10, (10, 10)),
        ("sacct", None, 30, (30, 30)),
        ("sacct", 10, 60, (10, 60)),
    ],
)
def test_status_check_interval_defaults_depend_on_status_command(
    status_command, init_seconds, max_seconds, expected_intervals
):
    settings = SimpleNamespace(
        init_seconds_before_status_checks=init_seconds,
        max_seconds_between_status_checks=max_seconds,
    )

    assert get_status_check_intervals(settings, status_command) == expected_intervals


def test_squeue_sacct_checks_status_every_20_seconds_by_default(monkeypatch):
    executor = _make_executor("squeue+sacct", None, None, 20)
    _mock_status_queries(monkeypatch, {"101": "RUNNING"}, {})
    job = _make_job("101")

    remaining = _check_active_jobs(executor, [job])

    assert remaining == [job]
    assert executor.next_seconds_between_status_checks == 20


@pytest.mark.parametrize(
    "available_tools, expected_default",
    [
        ({"squeue", "sacct"}, "squeue+sacct"),
        ({"sacct"}, "sacct"),
        ({"squeue"}, "squeue"),
    ],
)
def test_status_command_default(monkeypatch, available_tools, expected_default):
    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.shutil.which",
        lambda tool: f"/usr/bin/{tool}",
    )
    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.is_query_tool_available",
        lambda tool: tool in available_tools,
    )

    assert _get_status_command_default() == expected_default


def test_squeue_sacct_job_finished_in_squeue(monkeypatch):
    executor = _make_executor("squeue+sacct", 40, 180, 40)
    commands = _mock_status_queries(
        monkeypatch, {"101": "COMPLETED", "102": "RUNNING"}, {}
    )
    finished_job = _make_job("101")
    running_job = _make_job("102")

    remaining = _check_active_jobs(executor, [finished_job, running_job])

    assert remaining == [running_job]
    assert commands == ["squeue"]
    executor.report_job_success.assert_called_once_with(finished_job)
    executor.report_job_error.assert_not_called()
    assert executor.next_seconds_between_status_checks == 40


def test_squeue_sacct_job_missing_in_squeue_resolved_by_sacct(monkeypatch):
    executor = _make_executor("squeue+sacct", 40, 180, 40)
    commands = _mock_status_queries(
        monkeypatch, {"101": "RUNNING"}, {"102": "COMPLETED"}
    )
    running_job = _make_job("101")
    aged_out_job = _make_job("102")

    remaining = _check_active_jobs(executor, [running_job, aged_out_job])

    assert remaining == [running_job]
    assert commands == ["squeue", "sacct --jobs 102"]
    executor.report_job_success.assert_called_once_with(aged_out_job)
    executor.report_job_error.assert_not_called()


def test_squeue_sacct_job_missing_in_squeue_and_sacct(monkeypatch):
    executor = _make_executor("squeue+sacct", 40, 180, 40)
    commands = _mock_status_queries(monkeypatch, {}, {})
    job = _make_job("103")

    remaining = _check_active_jobs(executor, [job])

    assert remaining == [job]
    assert commands == ["squeue", "sacct --jobs 103"]
    executor.report_job_success.assert_not_called()
    executor.report_job_error.assert_not_called()
    assert executor.next_seconds_between_status_checks == 50


def test_squeue_sacct_array_task_missing_in_squeue_uses_parent_status(monkeypatch):
    executor = _make_executor("squeue+sacct", 40, 180, 40)
    commands = _mock_status_queries(monkeypatch, {}, {"200": "COMPLETED"})
    job = _make_job("200_5")

    remaining = _check_active_jobs(executor, [job])

    assert remaining == []
    assert commands == ["squeue", "sacct --jobs 200,200_5"]
    executor.report_job_success.assert_called_once_with(job)


def test_squeue_sacct_many_missing_jobs_use_run_wide_sacct(monkeypatch):
    executor = _make_executor("squeue+sacct", 40, 180, 40)
    commands = _mock_status_queries(monkeypatch, {}, {"101": "RUNNING"})
    monkeypatch.setattr("snakemake_executor_plugin_slurm._MAX_SACCT_JOB_IDS", 1)
    running_job = _make_job("101")
    unknown_job = _make_job("102")

    remaining = _check_active_jobs(executor, [running_job, unknown_job])

    assert remaining == [running_job, unknown_job]
    assert commands == ["squeue", "sacct"]


def test_squeue_sacct_failed_job_in_squeue_gets_reason_from_sacct(monkeypatch):
    executor = _make_executor("squeue+sacct", 40, 180, 40)
    _mock_status_queries(monkeypatch, {"101": "FAILED"}, {})
    reason_commands = []

    def _mock_check_output(command, **kwargs):
        reason_commands.append(command)
        if command.startswith("sacct -j 101.0 "):
            return "OutOfMemory\n"
        return ""

    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.subprocess.check_output",
        _mock_check_output,
    )
    job = _make_job("101")

    remaining = _check_active_jobs(executor, [job])

    assert remaining == []
    assert len(reason_commands) == 10
    executor.report_job_error.assert_called_once_with(
        job,
        msg="SLURM-job '101' failed, SLURM status is: 'FAILED'. "
        "Reason: Step 0: OutOfMemory.",
        aux_logs=["101.log"],
    )


def test_squeue_command_lists_array_tasks_of_current_user():
    command = query_job_status_squeue("run-uuid")

    assert shlex.split(command) == [
        "squeue",
        "--format=%i|%T",
        "--states=all",
        "--array",
        "--noheader",
        "--user",
        str(os.getuid()),
        "--name",
        "run-uuid",
    ]


def test_sacct_command_restricted_to_job_ids():
    command = query_job_status_sacct("run-uuid", ["101", "102_3"])

    assert shlex.split(command)[-4:] == ["--name", "run-uuid", "--jobs", "101,102_3"]
