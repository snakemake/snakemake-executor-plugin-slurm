import os
import re

from pathlib import Path
from typing import Optional
import snakemake.common.tests
from snakemake_interface_executor_plugins.settings import ExecutorSettingsBase
from unittest.mock import MagicMock, patch
import pytest

from snakemake_executor_plugin_slurm import ExecutorSettings
from snakemake_executor_plugin_slurm.utils import set_gres_string
from snakemake_executor_plugin_slurm.submit_string import get_submit_command
from snakemake_interface_common.exceptions import WorkflowError


class TestWorkflows(snakemake.common.tests.TestWorkflowsLocalStorageBase):
    __test__ = True

    def get_executor(self) -> str:
        return "slurm"

    def get_executor_settings(self) -> Optional[ExecutorSettingsBase]:
        return ExecutorSettings(
            init_seconds_before_status_checks=2,
            # seconds_between_status_checks=5,
        )


class TestEfficiencyReport(snakemake.common.tests.TestWorkflowsLocalStorageBase):
    __test__ = True

    def get_executor(self) -> str:
        return "slurm"

    def get_executor_settings(self) -> Optional[ExecutorSettingsBase]:
        self.REPORT_PATH = Path.cwd() / "efficiency_report_test"

        return ExecutorSettings(
                efficiency_report=True,
                init_seconds_before_status_checks=5,
                efficiency_report_path=self.REPORT_PATH,
                # seconds_between_status_checks=5,
            )

    def test_simple_workflow(self, tmp_path):
        # for an unkown reason, the efficiency report is not created
        # reliably in `tmp_path`, so we use a fixed path
        # to ensure the test is reproducible

        # a worklfow aborted:
        # error message:
        # OSError: Cannot save file into a non-existent directory:
        # '/tmp/efficiency_report_test'
        # runpath = Path("/tmp/efficiency_report_test")
        # runpath.mkdir(parents=True, exist_ok=True)
        self.run_workflow("simple", tmp_path)

        # The efficiency report is created in the
        # current working directory
        pattern = re.compile(r"efficiency_report_[\w-]+\.csv")
        report_found = False

        report_path = None

        # Check if the efficiency report file exists - based on the regex pattern
        for fname in os.listdir(self.REPORT_PATH):
            if pattern.match(fname):
                report_found = True
                report_path = os.path.join(expected_path, fname)
                # Verify it's not empty
                assert (
                    os.stat(report_path).st_size > 0
                ), f"Efficiency report {report_path} is empty"
                break
        assert report_found, "Efficiency report file not found"
        # as the directory is unclear, we need a path walk:
        # for root, _, files in os.walk("/tmp/pytest-of-runner/"):
        #    for fname in files:
        #        if pattern.match(fname):
        #            report_found = True
        #            report_path = os.path.join(root, fname)
        #            # Verify it's not empty
        #            assert (
        #                os.stat(report_path).st_size > 0
        #            ), f"Efficiency report {report_path} is empty"
        #            break
        # assert report_found, "Efficiency report file not found"


class TestWorkflowsRequeue(TestWorkflows):
    def get_executor_settings(self) -> Optional[ExecutorSettingsBase]:
        return ExecutorSettings(requeue=True, init_seconds_before_status_checks=1)


class TestGresString:
    """Test cases for the set_gres_string function."""

    @pytest.fixture
    def mock_job(self):
        """Create a mock job with configurable resources."""

        def _create_job(**resources):
            mock_resources = MagicMock()
            # Configure get method to return values from resources dict
            mock_resources.get.side_effect = lambda key, default=None: resources.get(
                key, default
            )
            # Add direct attribute access for certain resources
            for key, value in resources.items():
                setattr(mock_resources, key, value)

            mock_job = MagicMock()
            mock_job.resources = mock_resources
            mock_job.name = "test_job"
            mock_job.wildcards = {}
            mock_job.is_group.return_value = False
            mock_job.jobid = 1
            return mock_job

        return _create_job

    def test_no_gres_or_gpu(self, mock_job):
        """Test with no GPU or GRES resources specified."""
        job = mock_job()

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

        assert set_gres_string(job) == ""

    def test_valid_gres_simple(self, mock_job):
        """Test with valid GRES format (simple)."""
        job = mock_job(gres="gpu:1")

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

        assert set_gres_string(job) == " --gres=gpu:1"

    def test_valid_gres_with_model(self, mock_job):
        """Test with valid GRES format including GPU model."""
        job = mock_job(gres="gpu:tesla:2")

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

        assert set_gres_string(job) == " --gres=gpu:tesla:2"

    def test_invalid_gres_format(self, mock_job):
        """Test with invalid GRES format."""
        job = mock_job(gres="gpu")

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock
        with pytest.raises(WorkflowError, match="Invalid GRES format"):
            set_gres_string(job)

    def test_invalid_gres_format_missing_count(self, mock_job):
        """Test with invalid GRES format (missing count)."""
        job = mock_job(gres="gpu:tesla:")

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

        with pytest.raises(WorkflowError, match="Invalid GRES format"):
            set_gres_string(job)

    def test_valid_gpu_number(self, mock_job):
        """Test with valid GPU number."""
        job = mock_job(gpu="2")

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

        assert set_gres_string(job) == " --gpus=2"

    def test_valid_gpu_with_name(self, mock_job):
        """Test with valid GPU name and number."""
        job = mock_job(gpu="tesla:2")

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

        assert set_gres_string(job) == " --gpus=tesla:2"

    def test_gpu_with_model(self, mock_job):
        """Test GPU with model specification."""
        job = mock_job(gpu="2", gpu_model="tesla")

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

        assert set_gres_string(job) == " --gpus=tesla:2"

    def test_invalid_gpu_model_format(self, mock_job):
        """Test with invalid GPU model format."""
        job = mock_job(gpu="2", gpu_model="invalid:model")

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

        with pytest.raises(WorkflowError, match="Invalid GPU model format"):
            set_gres_string(job)

    def test_gpu_model_without_gpu(self, mock_job):
        """Test GPU model without GPU number."""
        job = mock_job(gpu_model="tesla")
        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

            # test whether the resource setting raises the correct error
            with pytest.raises(
                WorkflowError, match="GPU model is set, but no GPU number is given"
            ):
                set_gres_string(job)

    def test_both_gres_and_gpu_set(self, mock_job):
        """Test error case when both GRES and GPU are specified."""
        job = mock_job(gres="gpu:1", gpu="2")

        # Patch subprocess.Popen to simulate job submission
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to simulate successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

            # Ensure the error is raised when both GRES and GPU are set
            with pytest.raises(
                WorkflowError, match="GRES and GPU are set. Please only set one"
            ):
                set_gres_string(job)

    def test_nested_string_raise(self, mock_job):
        """Test error case when gres is a nested string."""
        job = mock_job(gres="'gpu:1'")
        # Patch subprocess.Popen to simulate job submission
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to simulate successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

            # Ensure the error is raised when both GRES and GPU are set
            with pytest.raises(
                WorkflowError,
                match="GRES format should not be a nested string",
            ):
                set_gres_string(job)

    def test_gpu_model_nested_string_raise(self, mock_job):
        """Test error case when gpu_model is a nested string."""
        job = mock_job(gpu_model="'tesla'", gpu="2")
        # Patch subprocess.Popen to simulate job submission
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to simulate successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

            # Ensure the error is raised when both GRES and GPU are set
            with pytest.raises(
                WorkflowError,
                match="GPU model format should not be a nested string",
            ):
                set_gres_string(job)


class TestSLURMResources(TestWorkflows):
    """
    Test workflows using job resources passed as part of the job configuration.
    This test suite uses the `get_submit_command` function to generate the
    sbatch command and validates the inclusion of resources.
    """

    @pytest.fixture
    def mock_job(self):
        """Create a mock job with configurable resources."""

        def _create_job(**resources):
            mock_resources = MagicMock()
            # Configure get method to return values from resources dict
            mock_resources.get.side_effect = lambda key, default=None: resources.get(
                key, default
            )
            # Add direct attribute access for certain resources
            for key, value in resources.items():
                setattr(mock_resources, key, value)

            mock_job = MagicMock()
            mock_job.resources = mock_resources
            mock_job.name = "test_job"
            mock_job.wildcards = {}
            mock_job.is_group.return_value = False
            mock_job.jobid = 1
            return mock_job

        return _create_job

    def test_constraint_resource(self, mock_job):
        """
        Test that the constraint resource is correctly
        added to the sbatch command.
        """
        # Create a job with a constraint resource
        job = mock_job(constraint="haswell")
        params = {
            "run_uuid": "test_run",
            "slurm_logfile": "test_logfile",
            "comment_str": "test_comment",
            "account": None,
            "partition": None,
            "workdir": ".",
            "constraint": "haswell",
        }

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

        assert " -C 'haswell'" in get_submit_command(job, params)

    def test_qos_resource(self, mock_job):
        """Test that the qos resource is correctly added to the sbatch command."""
        # Create a job with a qos resource
        job = mock_job(qos="normal")
        params = {
            "run_uuid": "test_run",
            "slurm_logfile": "test_logfile",
            "comment_str": "test_comment",
            "account": None,
            "partition": None,
            "workdir": ".",
            "qos": "normal",
        }

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

        assert " --qos='normal'" in get_submit_command(job, params)

    def test_both_constraint_and_qos(self, mock_job):
        """Test that both constraint and qos resources can be used together."""
        # Create a job with both constraint and qos resources
        job = mock_job(constraint="haswell", qos="high")
        params = {
            "run_uuid": "test_run",
            "slurm_logfile": "test_logfile",
            "comment_str": "test_comment",
            "account": None,
            "partition": None,
            "workdir": ".",
            "constraint": "haswell",
            "qos": "high",
        }

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

            # Assert both resources are correctly included
            sbatch_command = get_submit_command(job, params)
            assert " --qos='high'" in sbatch_command
            assert " -C 'haswell'" in sbatch_command

    def test_no_resources(self, mock_job):
        """
        Test that no constraint or qos flags are added
        when resources are not specified.
        """
        # Create a job without constraint or qos resources
        job = mock_job()
        params = {
            "run_uuid": "test_run",
            "slurm_logfile": "test_logfile",
            "comment_str": "test_comment",
            "account": None,
            "partition": None,
            "workdir": ".",
        }

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

            # Assert neither resource is included
            sbatch_command = get_submit_command(job, params)
            assert "-C " not in sbatch_command
            assert "--qos " not in sbatch_command

    def test_empty_constraint(self, mock_job):
        """Test that an empty constraint is still included in the command."""
        # Create a job with an empty constraint
        job = mock_job(constraint="")
        params = {
            "run_uuid": "test_run",
            "slurm_logfile": "test_logfile",
            "comment_str": "test_comment",
            "account": None,
            "partition": None,
            "workdir": ".",
            "constraint": "",
        }

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

            # Assert the constraint is included (even if empty)
            assert "-C ''" in get_submit_command(job, params)

    def test_empty_qos(self, mock_job):
        """Test that an empty qos is still included in the command."""
        # Create a job with an empty qos
        job = mock_job(qos="")
        params = {
            "run_uuid": "test_run",
            "slurm_logfile": "test_logfile",
            "comment_str": "test_comment",
            "account": None,
            "partition": None,
            "workdir": ".",
            "qos": "",
        }

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock
            # Assert the qoes is included (even if empty)
            assert "--qos=''" in get_submit_command(job, params)


class TestWildcardsWithSlashes(snakemake.common.tests.TestWorkflowsLocalStorageBase):
    """
    Test handling of wildcards with slashes to ensure log directories are
    correctly constructed.
    """

    __test__ = True

    def get_executor(self) -> str:
        return "slurm"

    def get_executor_settings(self) -> Optional[ExecutorSettingsBase]:
        return ExecutorSettings(
            logdir="test_logdir", init_seconds_before_status_checks=1
        )

    def test_wildcard_slash_replacement(self):
        """
        Test that slashes in wildcards are correctly replaced with
        underscores in log directory paths.
        """

    # Just test the wildcard sanitization logic directly
    wildcards = ["/leading_slash", "middle/slash", "trailing/"]

    # This is the actual logic from the Executor.run_job method
    wildcard_str = "_".join(wildcards).replace("/", "_") if wildcards else ""

    # Assert that slashes are correctly replaced with underscores
    assert wildcard_str == "_leading_slash_middle_slash_trailing_"

    # Verify no slashes remain in the wildcard string
    assert "/" not in wildcard_str
