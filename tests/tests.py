from typing import Optional
import snakemake.common.tests
from snakemake_interface_executor_plugins.settings import ExecutorSettingsBase
from unittest.mock import MagicMock
import pytest

from snakemake_executor_plugin_slurm import ExecutorSettings
from snakemake_executor_plugin_slurm.utils import set_gres_string
from snakemake_interface_common.exceptions import WorkflowError


class TestWorkflows(snakemake.common.tests.TestWorkflowsLocalStorageBase):
    __test__ = True

    def get_executor(self) -> str:
        return "slurm"

    def get_executor_settings(self) -> Optional[ExecutorSettingsBase]:
        return ExecutorSettings()


class TestWorkflowsRequeue(TestWorkflows):
    def get_executor_settings(self) -> Optional[ExecutorSettingsBase]:
        return ExecutorSettings(requeue=True)


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
            return mock_job

        return _create_job

    def test_no_gres_or_gpu(self, mock_job):
        """Test with no GPU or GRES resources specified."""
        job = mock_job()
        assert set_gres_string(job) == ""

    def test_valid_gres_simple(self, mock_job):
        """Test with valid GRES format (simple)."""
        job = mock_job(gres="gpu:1")
        assert set_gres_string(job) == " --gres=gpu:1"

    def test_valid_gres_with_model(self, mock_job):
        """Test with valid GRES format including GPU model."""
        job = mock_job(gres="gpu:tesla:2")
        assert set_gres_string(job) == " --gres=gpu:tesla:2"

    def test_invalid_gres_format(self, mock_job):
        """Test with invalid GRES format."""
        job = mock_job(gres="gpu")
        with pytest.raises(WorkflowError, match="Invalid GRES format"):
            set_gres_string(job)

    def test_invalid_gres_format_missing_count(self, mock_job):
        """Test with invalid GRES format (missing count)."""
        job = mock_job(gres="gpu:tesla:")
        with pytest.raises(WorkflowError, match="Invalid GRES format"):
            set_gres_string(job)

    def test_valid_gpu_number(self, mock_job):
        """Test with valid GPU number."""
        job = mock_job(gpu="2")
        assert set_gres_string(job) == " --gpus=2"

    def test_valid_gpu_with_name(self, mock_job):
        """Test with valid GPU name and number."""
        job = mock_job(gpu="tesla:2")
        assert set_gres_string(job) == " --gpus=tesla:2"

    def test_gpu_with_model(self, mock_job):
        """Test GPU with model specification."""
        job = mock_job(gpu="2", gpu_model="tesla")
        assert set_gres_string(job) == " --gpus=tesla:2"

    def test_invalid_gpu_model_format(self, mock_job):
        """Test with invalid GPU model format."""
        job = mock_job(gpu="2", gpu_model="invalid:model")
        with pytest.raises(WorkflowError, match="Invalid GPU model format"):
            set_gres_string(job)

    def test_gpu_model_without_gpu(self, mock_job):
        """Test GPU model without GPU number."""
        job = mock_job(gpu_model="tesla")
        with pytest.raises(
            WorkflowError, match="GPU model is set, but no GPU number is given"
        ):
            set_gres_string(job)

    def test_both_gres_and_gpu_set(self, mock_job):
        """Test error case when both GRES and GPU are specified."""
        job = mock_job(gres="gpu:1", gpu="2")
        with pytest.raises(
            WorkflowError, match="GRES and GPU are set. Please only set one of them."
        ):
            set_gres_string(job)
