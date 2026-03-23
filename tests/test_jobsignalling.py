"""Test suite for SLURM signal handling in job submission.

This module provides fixtures and tests for SLURM pre-timeout signal support.
Signals can be directed at either the job payload or the batch script controller,
and are triggered N seconds before the wall time limit.
"""

import pytest
from unittest.mock import MagicMock, patch
from snakemake_interface_common.exceptions import WorkflowError
from snakemake_executor_plugin_slurm import Executor, ExecutorSettings
from snakemake_executor_plugin_slurm.utils import get_slurm_signal_arg
from snakemake_executor_plugin_slurm.validation import validate_slurm_extra


@pytest.fixture
def mock_job():
    """Create a mock job with configurable resources and metadata.

    Returns a factory function that constructs mock jobs for testing.
    """

    def _create_job(name="signal_shell", **resources):
        mock_resources = MagicMock()
        mock_resources.get.side_effect = lambda key, default=None: resources.get(
            key, default
        )
        for key, value in resources.items():
            setattr(mock_resources, key, value)

        mock_job = MagicMock()
        mock_job.resources = mock_resources
        mock_job.name = name
        mock_job.wildcards = {}
        mock_job.is_group.return_value = False
        mock_job.jobid = 1
        mock_job.rule = MagicMock()
        mock_job.rule.name = name
        return mock_job

    return _create_job


class TestSlurmSignalParsing:
    """Test signal specification parsing and transformation to sbatch arguments."""

    def test_signal_targets_batch_script_by_default(self):
        """Default behavior: signal targets the batch script (B: prefix)."""
        assert (
            get_slurm_signal_arg("signal_shell:SIGTERM@45", "signal_shell")
            == " --signal=B:15@45"
        )

    def test_signal_with_reservation_target(self):
        """When R is specified, signal targets the reservation."""
        assert (
            get_slurm_signal_arg("signal_python:R:SIGUSR2@30", "signal_python")
            == " --signal=R:12@30"
        )

    def test_signal_number_format(self):
        """Signals can be specified by number (1-31)."""
        assert (
            get_slurm_signal_arg("signal_shell:15@60", "signal_shell")
            == " --signal=B:15@60"
        )

    def test_signal_is_ignored_for_other_rules(self):
        """Signals configured for a rule do not apply to other rules."""
        assert get_slurm_signal_arg("signal_shell:SIGTERM@60", "other_rule") == ""

    def test_multiple_signals_in_one_setting(self):
        """Multiple rules can have signals in a comma-separated list."""
        setting = "signal_shell:SIGUSR1@30,signal_python:R:SIGTERM@45"
        assert get_slurm_signal_arg(setting, "signal_shell") == " --signal=B:10@30"
        assert get_slurm_signal_arg(setting, "signal_python") == " --signal=R:15@45"

    def test_all_keyword_applies_to_any_rule(self):
        """The 'all' keyword applies signal to any rule not explicitly configured."""
        assert get_slurm_signal_arg("all:SIGUSR1@60", "any_rule") == " --signal=B:10@60"
        assert (
            get_slurm_signal_arg("all:R:SIGTERM@45", "other_rule")
            == " --signal=R:15@45"
        )

    def test_explicit_rule_takes_precedence_over_all(self):
        """An explicit rule setting overrides the 'all' setting."""
        setting = "all:SIGUSR1@60,signal_python:SIGTERM@30"
        # signal_python has explicit config
        assert get_slurm_signal_arg(setting, "signal_python") == " --signal=B:15@30"
        # other_rule falls back to 'all'
        assert get_slurm_signal_arg(setting, "other_rule") == " --signal=B:10@60"


class TestSlurmSignalValidation:
    """Test signal specification validation."""

    def test_invalid_signal_setting_is_rejected(self):
        """Malformed signal specs are rejected at settings initialization."""
        with pytest.raises(WorkflowError, match="Invalid signal specification"):
            ExecutorSettings(signal="signal_shell:SIGTERM")

    def test_reservation_scope_requires_reservation_setting(self):
        """Using R: scope without --slurm-reservation should raise an error."""
        with pytest.raises(
            WorkflowError, match="targets reservation.*no --slurm-reservation"
        ):
            ExecutorSettings(signal="signal_shell:R:SIGTERM@30")

    def test_reservation_scope_allowed_with_reservation_setting(self):
        """Using R: scope with --slurm-reservation should not raise an error."""
        # Should not raise
        ExecutorSettings(
            signal="signal_shell:R:SIGTERM@30", reservation="my_reservation"
        )

    def test_signal_cannot_be_overridden_via_slurm_extra(self, mock_job):
        """Prevent silent override: slurm_extra cannot set --signal."""
        job = mock_job(slurm_extra="--signal=B:SIGTERM@30")

        with pytest.raises(WorkflowError, match=r"signal.*not allowed"):
            validate_slurm_extra(job)

    def test_slurm_extra_with_other_flags_is_allowed(self, mock_job):
        """Other sbatch flags in slurm_extra are allowed."""
        job = mock_job(slurm_extra="--mail-type=END --mail-user=test@example.com")
        # Should not raise
        validate_slurm_extra(job)


class TestSlurmSignalInExecutor:
    """Test signal argument injection into the sbatch command during job submission."""

    def test_executor_run_job_adds_signal_argument(self, tmp_path, mock_job):
        """Verify that Executor.run_job includes --signal in the sbatch call."""
        executor = Executor.__new__(Executor)
        executor.workflow = MagicMock(
            executor_settings=ExecutorSettings(
                signal="signal_python:R:SIGTERM@15",
                init_seconds_before_status_checks=1,
            ),
            workdir_init=".",
        )
        executor.logger = MagicMock()
        executor._failed_nodes = set()

        job = mock_job("signal_python")
        job.threads = 1
        job.resources.get.side_effect = lambda key, default=None: {
            "runtime": 60,
            "mem_mb_per_cpu": 1000,
        }.get(key, default)

        with patch("subprocess.Popen") as mock_popen:
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("12345", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

            with patch.object(executor, "format_job_exec", return_value="echo test"):
                with patch.object(executor, "report_job_submission"):
                    executor.run_job(job)

            # Verify that --signal was included in the sbatch call
            assert mock_popen.called
            call_args = mock_popen.call_args[0][0]
            assert "--signal=R:15@15" in call_args

    def test_executor_ignores_signal_for_unrelated_rules(self, tmp_path, mock_job):
        """Executor should not add --signal for rules not in the signal spec."""
        executor = Executor.__new__(Executor)
        executor.workflow = MagicMock(
            executor_settings=ExecutorSettings(
                signal="signal_python:R:SIGTERM@15",
                init_seconds_before_status_checks=1,
            ),
            workdir_init=".",
        )
        executor.logger = MagicMock()
        executor._failed_nodes = set()

        job = mock_job("other_rule")
        job.threads = 1
        job.resources.get.side_effect = lambda key, default=None: {
            "runtime": 60,
            "mem_mb_per_cpu": 1000,
        }.get(key, default)

        with patch("subprocess.Popen") as mock_popen:
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("12345", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

            with patch.object(executor, "format_job_exec", return_value="echo test"):
                with patch.object(executor, "report_job_submission"):
                    executor.run_job(job)

            # Verify that --signal was NOT included
            assert mock_popen.called
            call_args = mock_popen.call_args[0][0]
            assert "--signal" not in call_args
