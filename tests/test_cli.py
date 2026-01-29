"""
   Tests for CLI-related executor settings.
   
   This suite will only test settings, which
   are to be tested separately from the full
   executor functionality.
"""

from unittest.mock import MagicMock, patch
import uuid

import pytest

from snakemake_executor_plugin_slurm import Executor, ExecutorSettings
from snakemake_interface_common.exceptions import WorkflowError


def _make_executor(jobname_prefix: str):
    settings = ExecutorSettings(
        jobname_prefix=jobname_prefix,
        init_seconds_before_status_checks=1,
    )
    workflow = MagicMock()
    workflow.executor_settings = settings
    workflow.workdir_init = "."

    executor = Executor.__new__(Executor)
    executor.workflow = workflow
    executor.logger = MagicMock()
    executor.run_uuid = "base-uuid"
    return executor


def test_jobname_prefix_applied():
    executor = _make_executor("testprefix")

    with patch.object(Executor, "warn_on_jobcontext", return_value=None):
        with patch(
            "snakemake_executor_plugin_slurm.__init__.uuid.uuid4",
            return_value=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        ):
            executor.__post_init__(test_mode=True)

    assert executor.run_uuid == "testprefix_00000000-0000-0000-0000-000000000000"


def test_jobname_prefix_validation():
    executor = _make_executor("bad!prefix")

    with patch.object(Executor, "warn_on_jobcontext", return_value=None):
        with pytest.raises(WorkflowError, match="jobname_prefix"):
            executor.__post_init__(test_mode=True)
