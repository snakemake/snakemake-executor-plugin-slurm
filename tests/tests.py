import os
import re

from pathlib import Path
from typing import Optional
import snakemake.common.tests
from snakemake_interface_executor_plugins.settings import ExecutorSettingsBase
from unittest.mock import MagicMock, patch
import pytest

from snakemake_executor_plugin_cannon import ExecutorSettings
from snakemake_executor_plugin_cannon.efficiency_report import (
    parse_sacct_data,
    time_to_seconds,
)
from snakemake_executor_plugin_cannon.utils import set_gres_string
from snakemake_executor_plugin_cannon.submit_string import get_submit_command
from snakemake_executor_plugin_cannon.validation import validate_slurm_extra
from snakemake_interface_common.exceptions import WorkflowError
import pandas as pd


class TestWorkflows(snakemake.common.tests.TestWorkflowsLocalStorageBase):
    __test__ = True

    def get_executor(self) -> str:
        return "cannon"

    def get_executor_settings(self) -> Optional[ExecutorSettingsBase]:
        return ExecutorSettings(
            init_seconds_before_status_checks=2,
            # seconds_between_status_checks=5,
        )


def test_parse_sacct_data():
    from io import StringIO

    test_data = [
        "10294159|b10191d0-6985-4c3a-8ccb-"
        "aa7d23ebffc7|rule_bam_bwa_mem_mosdepth_"
        "simulate_reads|00:01:31|00:24.041|1|1||32000M",
        "10294159.batch|batch||00:01:31|00:03.292|1|1|71180K|",
        "10294159.0|python3.12||00:01:10|00:20.749|1|1|183612K|",
        "10294160|b10191d0-6985-4c3a-8ccb-"
        "aa7d23ebffc7|rule_bam_bwa_mem_mosdepth_"
        "simulate_reads|00:01:30|00:24.055|1|1||32000M",
        "10294160.batch|batch||00:01:30|00:03.186|1|1|71192K|",
        "10294160.0|python3.12||00:01:10|00:20.868|1|1|184352K|",
    ]
    df = parse_sacct_data(
        lines=test_data, e_threshold=0.0, run_uuid="test", logger=None
    )
    output = StringIO()
    df.to_csv(output, index=False)
    print(output.getvalue())
    # this should only be two rows once collapsed
    assert len(df) == 2
    # check that RuleName is properly inherited from main jobs
    assert all(df["RuleName"] == "rule_bam_bwa_mem_mosdepth_simulate_reads")
    # check that RequestedMem_MB is properly inherited
    assert all(df["RequestedMem_MB"] == 32000.0)
    # check that MaxRSS_MB is properly calculated from job steps
    assert df.iloc[0]["MaxRSS_MB"] > 0  # Should have actual memory usage from job step


class TestTimeToSeconds:
    """Test the time_to_seconds function with SLURM sacct time formats."""

    def test_elapsed_format_with_days(self):
        """
        Test Elapsed format: [D-]HH:MM:SS or
        [DD-]HH:MM:SS (no fractional seconds).
        """
        # Single digit days
        assert time_to_seconds("1-00:00:00") == 86400  # 1 day
        assert (
            time_to_seconds("1-12:30:45") == 86400 + 12 * 3600 + 30 * 60 + 45
        )  # 131445
        assert time_to_seconds("9-23:59:59") == 9 * 86400 + 23 * 3600 + 59 * 60 + 59

        # Double digit days
        assert (
            time_to_seconds("10-01:02:03") == 10 * 86400 + 1 * 3600 + 2 * 60 + 3
        )  # 867723

    def test_elapsed_format_hours_minutes_seconds(self):
        """Test Elapsed format: HH:MM:SS (no fractional seconds)."""
        assert time_to_seconds("00:00:00") == 0
        assert time_to_seconds("01:00:00") == 3600  # 1 hour
        assert time_to_seconds("23:59:59") == 23 * 3600 + 59 * 60 + 59  # 86399
        assert time_to_seconds("12:30:45") == 12 * 3600 + 30 * 60 + 45  # 45045

    def test_totalcpu_format_with_days(self):
        """
        Test TotalCPU format: [D-][HH:]MM:SS or [DD-][HH:]MM:SS
        (with fractional seconds).
        """
        # With days and hours
        assert time_to_seconds("1-12:30:45.5") == 86400 + 12 * 3600 + 30 * 60 + 45.5
        assert (
            time_to_seconds("10-01:02:03.123") == 10 * 86400 + 1 * 3600 + 2 * 60 + 3.123
        )

        # With days, no hours (MM:SS format)
        assert time_to_seconds("1-30:45") == 86400 + 30 * 60 + 45
        assert time_to_seconds("1-30:45.5") == 86400 + 30 * 60 + 45.5

    def test_totalcpu_format_minutes_seconds(self):
        """Test TotalCPU format: MM:SS with fractional seconds."""
        assert time_to_seconds("00:00") == 0
        assert time_to_seconds("01:00") == 60  # 1 minute
        assert time_to_seconds("59:59") == 59 * 60 + 59  # 3599
        assert time_to_seconds("30:45") == 30 * 60 + 45  # 1845
        assert time_to_seconds("30:45.5") == 30 * 60 + 45.5  # 1845.5

    def test_totalcpu_format_seconds_only(self):
        """Test TotalCPU format: SS or SS.sss (seconds only with fractional)."""
        assert time_to_seconds("0") == 0
        assert time_to_seconds("1") == 1
        assert time_to_seconds("30") == 30
        assert time_to_seconds("59") == 59

        # Fractional seconds
        assert time_to_seconds("30.5") == 30.5
        assert time_to_seconds("0.5") == 0.5

    def test_real_world_sacct_examples(self):
        """Test with realistic sacct time values from actual output."""
        # From your test data
        assert time_to_seconds("00:01:31") == 91  # 1 minute 31 seconds
        assert time_to_seconds("00:24.041") == 24.041  # 24.041 seconds
        assert time_to_seconds("00:03.292") == 3.292  # 3.292 seconds
        assert time_to_seconds("00:20.749") == 20.749  # 20.749 seconds

        # Longer running jobs
        assert time_to_seconds("02:15:30") == 2 * 3600 + 15 * 60 + 30  # 2h 15m 30s
        assert time_to_seconds("1-12:00:00") == 86400 + 12 * 3600  # 1 day 12 hours
        assert time_to_seconds("7-00:00:00") == 7 * 86400  # 1 week

    def test_empty_and_invalid_inputs(self):
        """Test empty, None, and invalid inputs."""
        assert time_to_seconds("") == 0
        assert time_to_seconds("   ") == 0
        assert time_to_seconds(None) == 0
        assert time_to_seconds(pd.NA) == 0
        assert time_to_seconds("invalid") == 0
        assert time_to_seconds("1:2:3:4") == 0  # Too many colons
        assert time_to_seconds("abc:def") == 0
        assert time_to_seconds("-1:00:00") == 0  # Negative values

    def test_whitespace_handling(self):
        """Test that whitespace is properly handled."""
        assert time_to_seconds(" 30 ") == 30
        assert time_to_seconds("  1-02:30:45  ") == 86400 + 2 * 3600 + 30 * 60 + 45
        assert time_to_seconds("\t12:30:45\n") == 12 * 3600 + 30 * 60 + 45

    def test_pandas_na_values(self):
        """Test pandas NA and NaN values."""
        assert time_to_seconds(pd.NA) == 0
        assert (
            time_to_seconds(pd.NaType()) == 0 if hasattr(pd, "NaType") else True
        )  # Skip if not available

    def test_edge_case_values(self):
        """Test edge case values that might appear in SLURM output."""
        # Zero padding variations (should work with datetime parsing)
        assert time_to_seconds("01:02:03") == 1 * 3600 + 2 * 60 + 3
        assert time_to_seconds("1:2:3") == 1 * 3600 + 2 * 60 + 3

        # Single digit values
        assert time_to_seconds("5") == 5
        assert time_to_seconds("1:5") == 1 * 60 + 5


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
        self.run_workflow("simple", tmp_path)

        # The efficiency report is created in the
        # current working directory
        pattern = re.compile(r"efficiency_report_[\w-]+\.csv")
        report_found = False

        report_path = None
        # using a short handle for the expected path
        expected_path = self.REPORT_PATH

        # Check if the efficiency report file exists - based on the regex pattern
        for fname in os.listdir(expected_path):
            if pattern.match(fname):
                report_found = True
                report_path = os.path.join(expected_path, fname)
                # Verify it's not empty
                assert (
                    os.stat(report_path).st_size > 0
                ), f"Efficiency report {report_path} is empty"
                break
        assert report_found, "Efficiency report file not found"


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

        assert " -C haswell" in get_submit_command(job, params)

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

        assert " --qos=normal" in get_submit_command(job, params)

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
            assert " --qos=high" in sbatch_command
            assert " -C haswell" in sbatch_command

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
            # Assert the qos is included (even if empty)
            assert "--qos=''" in get_submit_command(job, params)

    def test_taks(self, mock_job):
        """Test that tasks are correctly included in the sbatch command."""
        # Create a job with tasks
        job = mock_job(tasks=4)
        params = {
            "run_uuid": "test_run",
            "slurm_logfile": "test_logfile",
            "comment_str": "test_comment",
            "account": None,
            "partition": None,
            "workdir": ".",
            "tasks": 4,
        }

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

        assert "--ntasks=4" in get_submit_command(job, params)

    def test_gpu_tasks(self, mock_job):
        """Test that GPU tasks are correctly included in the sbatch command."""
        # Create a job with GPU tasks
        job = mock_job(gpu=1, tasks_per_gpu=2)
        params = {
            "run_uuid": "test_run",
            "slurm_logfile": "test_logfile",
            "comment_str": "test_comment",
            "account": None,
            "partition": None,
            "workdir": ".",
            "tasks_per_gpu": 2,
        }

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

        assert "--ntasks-per-gpu=2" in get_submit_command(job, params)

    def test_no_gpu_task(self, mock_job):
        """Test that no GPU tasks are included when not specified."""
        # Create a job without GPU tasks
        job = mock_job(gpu=1, tasks_per_gpu=-1)
        params = {
            "run_uuid": "test_run",
            "slurm_logfile": "test_logfile",
            "comment_str": "test_comment",
            "account": None,
            "partition": None,
            "workdir": ".",
            "tasks_per_gpu": -1,
        }

        # Patch subprocess.Popen to capture the sbatch command
        with patch("subprocess.Popen") as mock_popen:
            # Configure the mock to return successful submission
            process_mock = MagicMock()
            process_mock.communicate.return_value = ("123", "")
            process_mock.returncode = 0
            mock_popen.return_value = process_mock

        assert "--ntasks-per-gpu" not in get_submit_command(job, params)

    def test_task_set_for_unset_tasks(self, mock_job):
        """Test that tasks are set to 1 when unset."""
        # Create a job without tasks
        job = mock_job(tasks=None)
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

        assert "--ntasks=1" in get_submit_command(job, params)

    def test_gpu_tasks_set_for_unset_tasks(self, mock_job):
        """Test that GPU tasks are set to 1 when unset."""
        # Create a job without GPU tasks
        job = mock_job(gpu=1)
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

        assert "--ntasks-per-gpu=1" in get_submit_command(job, params)


class TestWildcardsWithSlashes(snakemake.common.tests.TestWorkflowsLocalStorageBase):
    """
    Test handling of wildcards with slashes to ensure log directories are
    correctly constructed.
    """

    __test__ = True

    def get_executor(self) -> str:
        return "cannon"

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


class TestSlurmExtraValidation:
    """Test cases for the validate_slurm_extra function."""

    @pytest.fixture
    def mock_job(self):
        """Create a mock job with configurable slurm_extra resource."""

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

    def test_valid_slurm_extra(self, mock_job):
        """Test that validation passes with allowed SLURM options."""
        job = mock_job(slurm_extra="--mail-type=END --mail-user=user@example.com")
        # Should not raise any exception
        validate_slurm_extra(job)

    def test_forbidden_job_name_long_form(self, mock_job):
        """Test that --job-name is rejected."""
        job = mock_job(slurm_extra="--job-name=my-job --mail-type=END")
        with pytest.raises(WorkflowError, match=r"job-name.*not allowed"):
            validate_slurm_extra(job)

    def test_forbidden_job_name_short_form(self, mock_job):
        """Test that -J is rejected."""
        job = mock_job(slurm_extra="-J my-job --mail-type=END")
        with pytest.raises(WorkflowError, match=r"job-name.*not allowed"):
            validate_slurm_extra(job)

    def test_forbidden_account_long_form(self, mock_job):
        """Test that --account is rejected."""
        job = mock_job(slurm_extra="--account=myaccount --mail-type=END")
        with pytest.raises(WorkflowError, match=r"account.*not allowed"):
            validate_slurm_extra(job)

    def test_forbidden_account_short_form(self, mock_job):
        """Test that -A is rejected."""
        job = mock_job(slurm_extra="-A myaccount --mail-type=END")
        with pytest.raises(WorkflowError, match=r"account.*not allowed"):
            validate_slurm_extra(job)

    def test_forbidden_comment(self, mock_job):
        """Test that --comment is rejected."""
        job = mock_job(slurm_extra="--comment='my comment' --mail-type=END")
        with pytest.raises(WorkflowError, match=r"job-comment.*not allowed"):
            validate_slurm_extra(job)

    def test_forbidden_gres(self, mock_job):
        """Test that --gres is rejected."""
        job = mock_job(slurm_extra="--gres=gpu:1 --mail-type=END")
        with pytest.raises(WorkflowError, match=r"generic-resources.*not allowed"):
            validate_slurm_extra(job)

    def test_multiple_forbidden_options(self, mock_job):
        """Test that the first forbidden option found is reported."""
        job = mock_job(slurm_extra="--job-name=test --account=myaccount")
        # Should raise error for job-name (first one encountered)
        with pytest.raises(WorkflowError, match=r"job-name.*not allowed"):
            validate_slurm_extra(job)
