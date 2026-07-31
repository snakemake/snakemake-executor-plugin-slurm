"""
Tests for CLI-related executor settings.

This suite will only test settings, which
are to be tested separately from the full
executor functionality.
"""

from argparse import ArgumentParser
from unittest.mock import MagicMock, patch
import uuid

import pytest

from snakemake_executor_plugin_slurm import Executor, ExecutorSettings
from snakemake_interface_common.exceptions import WorkflowError
from snakemake_interface_common.plugin_registry.plugin import PluginBase


class _SlurmSettingsPlugin(PluginBase[ExecutorSettings]):
    """Minimal plugin wrapper for exercising the settings resolution path."""

    @property
    def name(self) -> str:
        return "slurm"

    @property
    def cli_prefix(self) -> str:
        return "slurm"

    @property
    def settings_cls(self):
        return ExecutorSettings


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

    with patch(
        "snakemake_executor_plugin_slurm.uuid.uuid4",
        return_value=uuid.UUID("00000000-0000-0000-0000-000000000000"),
    ):
        executor.__post_init__(test_mode=True)

    assert executor.run_uuid == "testprefix_00000000-0000-0000-0000-000000000000"


def test_jobname_prefix_validation():
    executor = _make_executor("bad!prefix")

    with pytest.raises(WorkflowError, match="jobname_prefix"):
        executor.__post_init__(test_mode=True)


def test_array_memory_fudge_false_resolves_from_cli():
    """The executor setting must not retain the truthy string ``"false"``."""
    plugin = _SlurmSettingsPlugin()
    parser = ArgumentParser()
    plugin.register_cli_args(parser, "executor")

    args = parser.parse_args(["--slurm-array-memory-fudge", "false"])
    settings = plugin.get_settings(args)

    assert settings.array_memory_fudge is False
