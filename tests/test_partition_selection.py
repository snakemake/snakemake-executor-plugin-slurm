import tempfile
import yaml

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from snakemake_interface_common.exceptions import WorkflowError
from snakemake_executor_plugin_slurm.partitions import (
    read_partition_file,
    get_best_partition,
)


class TestPartitionSelection:
    @pytest.fixture
    def basic_partition_config(self):
        """Basic partition configuration with two partitions."""
        return {
            "partitions": {
                "default": {
                    "max_runtime": 1440,
                    "max_mem_mb": 128000,
                    "max_cpus_per_task": 32,
                    "supports_mpi": True,
                },
                "gpu": {
                    "max_runtime": 720,
                    "max_mem_mb": 256000,
                    "max_gpu": 4,
                    "available_gpu_models": ["a100", "v100"],
                    "supports_mpi": False,
                },
            }
        }

    @pytest.fixture
    def minimal_partition_config(self):
        """Minimal partition configuration."""
        return {"partitions": {"minimal": {}}}

    @pytest.fixture
    def comprehensive_partition_config(self):
        """Comprehensive partition configuration with all limit types."""
        return {
            "partitions": {
                "comprehensive": {
                    # Standard resources
                    "max_runtime": 2880,
                    "max_mem_mb": 500000,
                    "max_mem_mb_per_cpu": 8000,
                    "max_cpus_per_task": 64,
                    # SLURM-specific resources
                    "max_nodes": 4,
                    "max_tasks": 256,
                    "max_tasks_per_node": 64,
                    # GPU resources
                    "max_gpu": 8,
                    "available_gpu_models": ["a100", "v100", "rtx3090"],
                    "max_cpus_per_gpu": 16,
                    # MPI resources
                    "supports_mpi": True,
                    "max_mpi_tasks": 512,
                    # Node features/constraints
                    "available_constraints": ["intel", "avx2", "highmem"],
                }
            }
        }

    @pytest.fixture
    def empty_partitions_config(self):
        """Empty partitions configuration."""
        return {"partitions": {}}

    @pytest.fixture
    def missing_name_config(self):
        """Configuration with missing name field."""
        return {"partitions": {"": {}}}  # Empty partition name

    @pytest.fixture
    def invalid_key_config(self):
        """Configuration with invalid key."""
        return {"invalid_key": []}

    @pytest.fixture
    def temp_yaml_file(self):
        """Helper fixture to create temporary YAML files."""

        def _create_temp_file(config):
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as f:
                yaml.dump(config, f)
                return Path(f.name)

        return _create_temp_file

    def test_read_valid_partition_file(self, basic_partition_config, temp_yaml_file):
        """Test reading a valid partition configuration file."""
        temp_path = temp_yaml_file(basic_partition_config)

        try:
            partitions = read_partition_file(temp_path)

            assert len(partitions) == 2

            # Check first partition
            assert partitions[0].name == "default"
            assert partitions[0].limits.max_runtime == 1440
            assert partitions[0].limits.max_mem_mb == 128000
            assert partitions[0].limits.max_cpus_per_task == 32
            assert partitions[0].limits.supports_mpi is True

            # Check second partition
            assert partitions[1].name == "gpu"
            assert partitions[1].limits.max_runtime == 720
            assert partitions[1].limits.max_gpu == 4
            assert partitions[1].limits.available_gpu_models == ["a100", "v100"]
            assert partitions[1].limits.supports_mpi is False

        finally:
            temp_path.unlink()

    def test_read_minimal_partition_file(
        self, minimal_partition_config, temp_yaml_file
    ):
        """Test reading a partition file with minimal configuration."""
        from math import isinf

        temp_path = temp_yaml_file(minimal_partition_config)

        try:
            partitions = read_partition_file(temp_path)

            assert len(partitions) == 1
            assert partitions[0].name == "minimal"

            # Check that all limits are inf
            limits = partitions[0].limits
            assert isinf(limits.max_runtime)
            assert isinf(limits.max_mem_mb)
            assert limits.max_gpu == 0
            assert limits.supports_mpi is True

        finally:
            temp_path.unlink()

    def test_read_partition_file_with_all_limits(
        self, comprehensive_partition_config, temp_yaml_file
    ):
        """Test reading a partition file with all possible limit types."""
        temp_path = temp_yaml_file(comprehensive_partition_config)

        try:
            partitions = read_partition_file(temp_path)

            assert len(partitions) == 1
            limits = partitions[0].limits

            # Check standard resources
            assert limits.max_runtime == 2880
            assert limits.max_mem_mb == 500000
            assert limits.max_mem_mb_per_cpu == 8000
            assert limits.max_cpus_per_task == 64

            # Check SLURM-specific resources
            assert limits.max_nodes == 4
            assert limits.max_tasks == 256
            assert limits.max_tasks_per_node == 64

            # Check GPU resources
            assert limits.max_gpu == 8
            assert limits.available_gpu_models == ["a100", "v100", "rtx3090"]
            assert limits.max_cpus_per_gpu == 16

            # Check MPI resources
            assert limits.supports_mpi is True
            assert limits.max_mpi_tasks == 512

            # Check constraints
            assert limits.available_constraints == ["intel", "avx2", "highmem"]

        finally:
            temp_path.unlink()

    def test_read_empty_partitions_list(self, empty_partitions_config, temp_yaml_file):
        """Test reading a file with empty partitions list."""
        temp_path = temp_yaml_file(empty_partitions_config)

        try:
            partitions = read_partition_file(temp_path)
            assert len(partitions) == 0

        finally:
            temp_path.unlink()

    def test_read_nonexistent_file(self):
        """Test reading a non-existent file raises appropriate error."""

        nonexistent_path = Path("/nonexistent/path/to/file.yaml")

        with pytest.raises(WorkflowError, match="Partition file not found"):
            read_partition_file(nonexistent_path)

    def test_read_invalid_yaml_file(self):
        """Test reading an invalid YAML file raises appropriate error."""

        invalid_yaml = "partitions:\n  - name: test\n    invalid: {\n"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(invalid_yaml)
            temp_path = Path(f.name)

        try:
            with pytest.raises(WorkflowError, match="Error parsing partition file"):
                read_partition_file(temp_path)
        finally:
            temp_path.unlink()

    def test_read_file_missing_partitions_key(self, invalid_key_config, temp_yaml_file):
        """Test reading a file without 'partitions' key raises KeyError."""

        temp_path = temp_yaml_file(invalid_key_config)

        try:
            with pytest.raises(WorkflowError, match="missing 'partitions' section"):
                read_partition_file(temp_path)
        finally:
            temp_path.unlink()

    def test_read_partition_missing_required_fields(
        self, missing_name_config, temp_yaml_file
    ):
        """Test reading partition with missing required fields."""
        temp_path = temp_yaml_file(missing_name_config)

        try:
            with pytest.raises(KeyError):
                read_partition_file(temp_path)
        finally:
            temp_path.unlink()

    @pytest.fixture
    def mock_job(self):
        """Create a mock job with configurable resources and threads."""

        def _create_job(threads=1, **resources):
            mock_resources = MagicMock()
            mock_resources.get.side_effect = lambda key, default=None: resources.get(
                key, default
            )

            mock_job = MagicMock()
            mock_job.resources = mock_resources
            mock_job.threads = threads
            mock_job.name = "test_job"
            mock_job.is_group.return_value = False
            mock_job.jobid = 1
            return mock_job

        return _create_job

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    def test_basic_partition_selection_cpu_job(
        self, basic_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test selecting partition for a basic CPU job."""
        temp_path = temp_yaml_file(basic_partition_config)

        try:
            partitions = read_partition_file(temp_path)
            job = mock_job(threads=4, mem_mb=16000, runtime=60)

            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should select 'default' partition as it supports CPU jobs
            assert selected_partition == "default"
            # Check that the final call contains the auto-selection message
            assert mock_logger.info.call_count >= 1
            assert (
                "Auto-selected partition 'default'"
                in mock_logger.info.call_args_list[-1][0][0]
            )
        finally:
            temp_path.unlink()

    def test_basic_partition_selection_gpu_job(
        self, basic_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test selecting partition for a GPU job."""
        temp_path = temp_yaml_file(basic_partition_config)

        try:
            partitions = read_partition_file(temp_path)
            job = mock_job(
                threads=2, mem_mb=32000, runtime=300, gpu=2, gpu_model="a100"
            )

            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should select 'gpu' partition as it supports GPU jobs
            assert selected_partition == "gpu"
            assert mock_logger.info.call_count >= 1
            assert (
                "Auto-selected partition 'gpu'"
                in mock_logger.info.call_args_list[-1][0][0]
            )
        finally:
            temp_path.unlink()

    def test_no_suitable_partition(
        self, basic_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test when no partition can accommodate the job requirements."""
        temp_path = temp_yaml_file(basic_partition_config)

        try:
            partitions = read_partition_file(temp_path)
            # Job requires more memory than any partition allows
            job = mock_job(threads=1, mem_mb=500000, runtime=60)

            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should return None when no suitable partition found
            assert selected_partition is None
            assert mock_logger.info.call_count >= 1
            assert (
                "No suitable partition found"
                in mock_logger.info.call_args_list[-1][0][0]
            )
        finally:
            temp_path.unlink()

    def test_comprehensive_partition_selection(
        self, comprehensive_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test partition selection with comprehensive limits."""
        temp_path = temp_yaml_file(comprehensive_partition_config)

        try:
            partitions = read_partition_file(temp_path)
            job = mock_job(
                threads=8,
                mem_mb=64000,
                runtime=1200,
                gpu=2,
                gpu_model="a100",
                constraint="intel,avx2",
            )

            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should select the comprehensive partition
            assert selected_partition == "comprehensive"
            assert mock_logger.info.call_count >= 1
            assert (
                "Auto-selected partition 'comprehensive'"
                in mock_logger.info.call_args_list[-1][0][0]
            )
        finally:
            temp_path.unlink()

    def test_constraint_mismatch(
        self, comprehensive_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test job with constraints not available in partition."""
        temp_path = temp_yaml_file(comprehensive_partition_config)

        try:
            partitions = read_partition_file(temp_path)
            # Job requires constraint not available in partition
            job = mock_job(threads=2, constraint="amd,gpu_direct")

            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should return None due to constraint mismatch
            assert selected_partition is None
            assert mock_logger.warning.call_count >= 1
            assert (
                "No suitable partition found"
                in mock_logger.warning.call_args_list[-1][0][0]
            )
        finally:
            temp_path.unlink()

    def test_mpi_job_selection(
        self, basic_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test MPI job partition selection."""
        temp_path = temp_yaml_file(basic_partition_config)

        try:
            partitions = read_partition_file(temp_path)
            job = mock_job(threads=1, mpi=True, tasks=16)

            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should select 'default' partition as it supports MPI, 'gpu' doesn't
            assert selected_partition == "default"
            assert mock_logger.info.call_count >= 1
            assert (
                "Auto-selected partition 'default'"
                in mock_logger.info.call_args_list[-1][0][0]
            )
        finally:
            temp_path.unlink()

    def test_gpu_model_mismatch(
        self, basic_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test GPU job with unsupported GPU model."""
        temp_path = temp_yaml_file(basic_partition_config)

        try:
            partitions = read_partition_file(temp_path)
            # Request GPU model not available in any partition
            job = mock_job(threads=2, gpu=1, gpu_model="rtx4090")

            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should return None due to GPU model mismatch
            assert selected_partition is None
            assert mock_logger.warning.call_count >= 1
            assert (
                "No suitable partition found"
                in mock_logger.warning.call_args_list[-1][0][0]
            )
        finally:
            temp_path.unlink()

    def test_empty_partitions_list(
        self, empty_partitions_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test partition selection with empty partitions list."""
        temp_path = temp_yaml_file(empty_partitions_config)

        try:
            partitions = read_partition_file(temp_path)
            job = mock_job(threads=1, mem_mb=1000)

            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should return None when no partitions available
            assert selected_partition is None
            assert mock_logger.warning.call_count >= 1
            assert (
                "No suitable partition found"
                in mock_logger.warning.call_args_list[-1][0][0]
            )
        finally:
            temp_path.unlink()

    def test_gres_gpu_specification(
        self, basic_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test GPU job specified via gres parameter."""
        temp_path = temp_yaml_file(basic_partition_config)

        try:
            partitions = read_partition_file(temp_path)
            job = mock_job(threads=2, gres="gpu:v100:1", runtime=400)

            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should select 'gpu' partition as it supports v100 GPUs
            assert selected_partition == "gpu"
            assert mock_logger.info.call_count >= 1
            assert (
                "Auto-selected partition 'gpu'"
                in mock_logger.info.call_args_list[-1][0][0]
            )
        finally:
            temp_path.unlink()

    def test_cpus_per_task_specification(
        self, comprehensive_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test job with cpus_per_task specification."""
        temp_path = temp_yaml_file(comprehensive_partition_config)

        try:
            partitions = read_partition_file(temp_path)
            job = mock_job(threads=1, cpus_per_task=32, mem_mb=64000)

            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should select comprehensive partition as it can handle 32 cpus per task
            assert selected_partition == "comprehensive"
            assert mock_logger.info.call_count >= 1
            assert (
                "Auto-selected partition 'comprehensive'"
                in mock_logger.info.call_args_list[-1][0][0]
            )
        finally:
            temp_path.unlink()

    def test_runtime_exceeds_limit(
        self, basic_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test job with runtime exceeding partition limits."""
        temp_path = temp_yaml_file(basic_partition_config)

        try:
            partitions = read_partition_file(temp_path)
            # Job requires more runtime than gpu partition allows (720 min max)
            job = mock_job(threads=1, runtime=1000, gpu=1, gpu_model="a100")

            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should return None as no partition can accommodate the runtime
            assert selected_partition is None
            assert mock_logger.warning.call_count >= 1
            assert (
                "No suitable partition found"
                in mock_logger.warning.call_args_list[-1][0][0]
            )
        finally:
            temp_path.unlink()

    @pytest.fixture
    def multicluster_partition_config(self):
        """Partition configuration with multiple clusters."""
        return {
            "partitions": {
                "normal-small": {
                    "cluster": "normal",
                    "max_runtime": 360,
                    "max_threads": 32,
                    "max_mem_mb": 64000,
                },
                "normal-large": {
                    "cluster": "normal",
                    "max_runtime": 1440,
                    "max_threads": 128,
                    "max_mem_mb": 256000,
                },
                "deviating-small": {
                    "cluster": "deviating",
                    "max_runtime": 360,
                    "max_threads": 64,
                    "max_mem_mb": 128000,
                },
                "deviating-gpu": {
                    "cluster": "deviating",
                    "max_runtime": 720,
                    "max_threads": 32,
                    "max_gpu": 4,
                    "available_gpu_models": ["a100"],
                },
            }
        }

    @pytest.fixture
    def max_threads_partition_config(self):
        """Partition configuration specifically testing max_threads limits."""
        return {
            "partitions": {
                "tiny": {
                    "max_threads": 8,
                    "max_mem_mb": 32000,
                },
                "small": {
                    "max_threads": 32,
                    "max_mem_mb": 64000,
                },
                "medium": {
                    "max_threads": 127,
                    "max_mem_mb": 128000,
                },
                "large": {
                    "max_threads": 256,
                    "max_mem_mb": 512000,
                },
            }
        }

    def test_cluster_specification_via_slurm_cluster(
        self, multicluster_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test cluster specification using slurm_cluster resource."""
        temp_path = temp_yaml_file(multicluster_partition_config)

        try:
            partitions = read_partition_file(temp_path)

            # Verify cluster field is read correctly
            # Find partitions by name instead of assuming order
            partition_map = {p.name: p for p in partitions}
            assert partition_map["normal-small"].cluster == "normal"
            assert partition_map["deviating-small"].cluster == "deviating"

            # Job targeting 'normal' cluster
            job = mock_job(threads=16, mem_mb=32000, slurm_cluster="normal")
            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should select a partition from 'normal' cluster
            assert selected_partition in ["normal-small", "normal-large"]
            assert mock_logger.warning.call_count >= 1
        finally:
            temp_path.unlink()

    def test_cluster_specification_via_clusters(
        self, multicluster_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test cluster specification using clusters resource."""
        temp_path = temp_yaml_file(multicluster_partition_config)

        try:
            partitions = read_partition_file(temp_path)

            # Job targeting 'deviating' cluster via 'clusters' resource
            job = mock_job(threads=48, mem_mb=64000, clusters="deviating")
            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should select deviating-small partition
            assert selected_partition == "deviating-small"
            assert mock_logger.warning.call_count >= 1
        finally:
            temp_path.unlink()

    def test_cluster_specification_via_cluster(
        self, multicluster_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test cluster specification using cluster resource."""
        temp_path = temp_yaml_file(multicluster_partition_config)

        try:
            partitions = read_partition_file(temp_path)

            # Job targeting 'normal' cluster via 'cluster' resource
            job = mock_job(threads=64, mem_mb=128000, cluster="normal")
            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should select normal-large partition
            assert selected_partition == "normal-large"
            assert mock_logger.warning.call_count >= 1
        finally:
            temp_path.unlink()

    def test_cluster_mismatch_excludes_partitions(
        self, multicluster_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """
        Test that jobs requesting a cluster exclude partitions from other
        clusters.
        """
        temp_path = temp_yaml_file(multicluster_partition_config)

        try:
            partitions = read_partition_file(temp_path)

            # Job requesting GPU on 'normal' cluster (only deviating has GPU)
            job = mock_job(threads=16, gpu=2, gpu_model="a100", slurm_cluster="normal")
            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should return None as normal cluster has no GPU partitions
            assert selected_partition is None
            assert mock_logger.warning.call_count >= 1
        finally:
            temp_path.unlink()

    def test_job_without_cluster_uses_any_partition(
        self, multicluster_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test that jobs without cluster specification can use any partition."""
        temp_path = temp_yaml_file(multicluster_partition_config)

        try:
            partitions = read_partition_file(temp_path)

            # Job without cluster specification
            job = mock_job(threads=16, mem_mb=32000)
            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should select a partition (any cluster is acceptable)
            assert selected_partition is not None
            assert mock_logger.warning.call_count >= 1
        finally:
            temp_path.unlink()

    def test_max_threads_with_threads_resource(
        self, max_threads_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test max_threads limit with threads resource."""
        temp_path = temp_yaml_file(max_threads_partition_config)

        try:
            partitions = read_partition_file(temp_path)

            # Job with 4 threads - should prefer tiny partition
            job = mock_job(threads=4, mem_mb=16000)
            selected_partition = get_best_partition(partitions, job, mock_logger)
            assert selected_partition == "tiny"

            # Job with 16 threads - should prefer small partition
            mock_logger.reset_mock()
            job = mock_job(threads=16, mem_mb=32000)
            selected_partition = get_best_partition(partitions, job, mock_logger)
            assert selected_partition == "small"

            # Job with 64 threads - should use medium partition
            mock_logger.reset_mock()
            job = mock_job(threads=64, mem_mb=64000)
            selected_partition = get_best_partition(partitions, job, mock_logger)
            assert selected_partition == "medium"

        finally:
            temp_path.unlink()

    def test_max_threads_with_cpus_per_task_resource(
        self, max_threads_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test max_threads limit with cpus_per_task resource."""
        temp_path = temp_yaml_file(max_threads_partition_config)

        try:
            partitions = read_partition_file(temp_path)

            # Job with cpus_per_task=128 - exceeds medium (127), needs large
            job = mock_job(threads=None, cpus_per_task=128, mem_mb=128000)
            selected_partition = get_best_partition(partitions, job, mock_logger)
            assert selected_partition == "large"

            # Job with cpus_per_task=127 - exactly matches medium
            mock_logger.reset_mock()
            job = mock_job(threads=None, cpus_per_task=127, mem_mb=64000)
            selected_partition = get_best_partition(partitions, job, mock_logger)
            assert selected_partition == "medium"

        finally:
            temp_path.unlink()

    def test_max_threads_excludes_too_small_partitions(
        self, max_threads_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test that partitions with insufficient max_threads are excluded."""
        temp_path = temp_yaml_file(max_threads_partition_config)

        try:
            partitions = read_partition_file(temp_path)

            # Job with 128 threads - tiny, small, medium cannot accommodate
            job = mock_job(threads=128, mem_mb=256000)
            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Only large partition should be selected
            assert selected_partition == "large"
            assert mock_logger.warning.call_count >= 1

        finally:
            temp_path.unlink()

    def test_max_threads_job_exceeds_all_partitions(
        self, max_threads_partition_config, temp_yaml_file, mock_job, mock_logger
    ):
        """Test job requiring more threads than any partition supports."""
        temp_path = temp_yaml_file(max_threads_partition_config)

        try:
            partitions = read_partition_file(temp_path)

            # Job with 512 threads - exceeds all partitions
            job = mock_job(threads=512, mem_mb=128000)
            selected_partition = get_best_partition(partitions, job, mock_logger)

            # Should return None
            assert selected_partition is None
            assert mock_logger.warning.call_count >= 1
            assert (
                "No suitable partition found"
                in mock_logger.warning.call_args_list[-1][0][0]
            )

        finally:
            temp_path.unlink()

    def test_multicluster_with_max_threads(self, temp_yaml_file, mock_job, mock_logger):
        """Test combined cluster and max_threads constraints."""
        config = {
            "partitions": {
                "normal-small": {
                    "cluster": "normal",
                    "max_threads": 64,
                    "max_mem_mb": 128000,
                },
                "normal-large": {
                    "cluster": "normal",
                    "max_threads": 256,
                    "max_mem_mb": 512000,
                },
                "deviating-medium": {
                    "cluster": "deviating",
                    "max_threads": 128,
                    "max_mem_mb": 256000,
                },
            }
        }
        temp_path = temp_yaml_file(config)

        try:
            partitions = read_partition_file(temp_path)

            # Job targeting normal cluster with 128 threads
            # normal-small (64) is too small, should use normal-large (256)
            job = mock_job(threads=128, mem_mb=256000, slurm_cluster="normal")
            selected_partition = get_best_partition(partitions, job, mock_logger)

            assert selected_partition == "normal-large"
            assert mock_logger.warning.call_count >= 1

            # Job targeting deviating cluster with 128 threads
            # Should exactly match deviating-medium
            mock_logger.reset_mock()
            job = mock_job(threads=128, mem_mb=128000, slurm_cluster="deviating")
            selected_partition = get_best_partition(partitions, job, mock_logger)

            assert selected_partition == "deviating-medium"
            assert mock_logger.warning.call_count >= 1

        finally:
            temp_path.unlink()
