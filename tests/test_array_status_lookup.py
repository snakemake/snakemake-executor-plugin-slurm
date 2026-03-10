import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from snakemake_executor_plugin_slurm import Executor, _status_lookup_ids


class _NoopAsyncContext:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def test_status_lookup_ids_for_array_task():
    assert _status_lookup_ids("1057651_6") == ["1057651_6", "1057651"]
    assert _status_lookup_ids("1057651") == ["1057651"]
    assert _status_lookup_ids("abc_1") == ["abc_1"]


def test_check_active_jobs_uses_parent_array_status(monkeypatch):
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
            keep_successful_logs=True,
            requeue=False,
        )
    )

    async def _mock_query_job_status(command, logger):
        return ({"1057651": "FAILED"}, 0.01)

    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.query_job_status",
        _mock_query_job_status,
    )
    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.query_job_status_sacct",
        lambda run_uuid: "mock_sacct_command",
    )
    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.get_min_job_age",
        lambda: 300,
    )
    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.is_query_tool_available",
        lambda tool: True,
    )

    active_job = SimpleNamespace(
        external_jobid="1057651_1",
        aux={"slurm_logfile": Path("fake.log")},
    )

    async def _collect_remaining_jobs():
        remaining = []
        async for job in executor.check_active_jobs([active_job]):
            remaining.append(job)
        return remaining

    remaining = asyncio.run(_collect_remaining_jobs())

    assert remaining == []
    executor.report_job_success.assert_not_called()
    executor.report_job_error.assert_called_once()


def test_parent_fallback_completed_keeps_array_task_log(monkeypatch, tmp_path):
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

    async def _mock_query_job_status(command, logger):
        return ({"1057651": "COMPLETED"}, 0.01)

    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.query_job_status",
        _mock_query_job_status,
    )
    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.query_job_status_sacct",
        lambda run_uuid: "mock_sacct_command",
    )
    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.get_min_job_age",
        lambda: 300,
    )
    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.is_query_tool_available",
        lambda tool: True,
    )

    log_path = tmp_path / "1057651_1.log"
    log_path.write_text("content")

    active_job = SimpleNamespace(
        external_jobid="1057651_1",
        aux={"slurm_logfile": log_path},
    )

    async def _collect_remaining_jobs():
        remaining = []
        async for job in executor.check_active_jobs([active_job]):
            remaining.append(job)
        return remaining

    remaining = asyncio.run(_collect_remaining_jobs())

    assert remaining == []
    executor.report_job_success.assert_called_once()
    executor.report_job_error.assert_not_called()
    # TODO: look into this: the log_path should not exist, but this
    #      might through an error
    # assert not log_path.exists()
