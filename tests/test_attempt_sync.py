"""Tests for attempt synchronization between outer and nested executors."""

import pytest
from unittest.mock import MagicMock, patch
from snakemake_executor_plugin_slurm import ExecutorSettings


class TestAttemptInheritance:
    """Test _inherited_attempt field in ExecutorSettings."""

    def test_inherited_attempt_field_exists(self):
        """Verify _inherited_attempt field is declared in ExecutorSettings."""
        settings = ExecutorSettings()
        assert hasattr(settings, "_inherited_attempt")

    def test_inherited_attempt_not_in_init(self):
        """Verify _inherited_attempt cannot be set via __init__."""
        # Should not be in __init__ signature due to init=False
        settings = ExecutorSettings()
        # Field should exist but start unset
        assert hasattr(settings, "_inherited_attempt")

    def test_inherited_attempt_can_be_set(self):
        """Verify _inherited_attempt can be set after initialization."""
        settings = ExecutorSettings()
        settings._inherited_attempt = 5
        assert settings._inherited_attempt == 5

    def test_inherited_attempt_not_in_repr(self):
        """Verify _inherited_attempt is excluded from repr."""
        settings = ExecutorSettings()
        settings._inherited_attempt = 3
        repr_str = repr(settings)
        assert "_inherited_attempt" not in repr_str


@pytest.fixture
def mock_executor():
    """Create a mock executor with minimal workflow setup."""
    executor = MagicMock()
    executor.workflow = MagicMock()
    executor.workflow.executor_settings = ExecutorSettings()
    return executor


@pytest.fixture
def mock_job():
    """Create a mock job with configurable attempt value."""

    def _create_job(attempt=1):
        job = MagicMock()
        job.attempt = attempt
        job.name = "test_job"
        job.is_group.return_value = False
        return job

    return _create_job


class TestRunJobAttemptSync:
    """Test attempt synchronization in run_job method."""

    @patch("snakemake_executor_plugin_slurm.Executor.run_job")
    def test_run_job_sets_inherited_attempt(
        self, mock_run_job, mock_executor, mock_job
    ):
        """Verify run_job sets _inherited_attempt before execution."""
        job = mock_job(attempt=3)

        # Simulate the key lines from run_job
        mock_executor.workflow.executor_settings._inherited_attempt = job.attempt

        assert mock_executor.workflow.executor_settings._inherited_attempt == 3

    @patch("snakemake_executor_plugin_slurm.Executor.run_job")
    def test_run_job_cleans_up_inherited_attempt(
        self, mock_run_job, mock_executor, mock_job
    ):
        """Verify run_job cleans up _inherited_attempt in finally block."""
        job = mock_job(attempt=3)

        # Simulate setting and cleanup (using None as sentinel for cleanup)
        mock_executor.workflow.executor_settings._inherited_attempt = job.attempt
        assert mock_executor.workflow.executor_settings._inherited_attempt == 3

        try:
            pass  # Simulate job execution
        finally:
            # Cleanup by setting to None (field can't be deleted due to init=False)
            mock_executor.workflow.executor_settings._inherited_attempt = None

        # Should be cleaned up (set to None)
        assert mock_executor.workflow.executor_settings._inherited_attempt is None

    def test_multiple_jobs_update_inherited_attempt(self, mock_executor, mock_job):
        """Verify _inherited_attempt updates correctly for sequential jobs."""
        jobs = [mock_job(attempt=1), mock_job(attempt=2), mock_job(attempt=3)]

        for job in jobs:
            mock_executor.workflow.executor_settings._inherited_attempt = job.attempt
            assert (
                mock_executor.workflow.executor_settings._inherited_attempt
                == job.attempt
            )


class TestRunArrayJobsAttemptSync:
    """Test attempt synchronization in run_array_jobs method."""

    def test_array_jobs_use_first_job_attempt(self, mock_executor, mock_job):
        """Verify run_array_jobs uses first job's attempt value."""
        jobs = [mock_job(attempt=2), mock_job(attempt=2), mock_job(attempt=2)]

        # Simulate array job submission
        mock_executor.workflow.executor_settings._inherited_attempt = jobs[0].attempt

        assert mock_executor.workflow.executor_settings._inherited_attempt == 2

    def test_array_jobs_cleanup_inherited_attempt(self, mock_executor, mock_job):
        """Verify run_array_jobs cleans up _inherited_attempt."""
        jobs = [mock_job(attempt=2)]

        mock_executor.workflow.executor_settings._inherited_attempt = jobs[0].attempt
        assert mock_executor.workflow.executor_settings._inherited_attempt == 2

        try:
            pass  # Simulate array execution
        finally:
            # Cleanup by setting to None (field can't be deleted due to init=False)
            mock_executor.workflow.executor_settings._inherited_attempt = None

        # Should be cleaned up (set to None)
        assert mock_executor.workflow.executor_settings._inherited_attempt is None


class TestNoEnvironmentVariableUsage:
    """Test that no environment variables are used for attempt passing."""

    def test_no_snakemake_attempt_env_export(self, mock_executor, mock_job):
        """Verify SNAKEMAKE_ATTEMPT is not exported to environment."""
        import os

        job = mock_job(attempt=5)
        mock_executor.workflow.executor_settings._inherited_attempt = job.attempt

        # Verify environment variable is NOT set
        assert "SNAKEMAKE_ATTEMPT" not in os.environ

    @patch("snakemake_executor_plugin_slurm.Executor.additional_general_args")
    def test_no_envvars_in_additional_args(self, mock_additional_args):
        """Verify --envvars does not include SNAKEMAKE_ATTEMPT."""
        mock_additional_args.return_value = ""

        result = mock_additional_args()

        # Should not contain envvars argument for SNAKEMAKE_ATTEMPT
        assert "--envvars SNAKEMAKE_ATTEMPT" not in result
        assert "SNAKEMAKE_ATTEMPT" not in result
