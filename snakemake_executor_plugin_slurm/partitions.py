from dataclasses import dataclass
from typing import Optional, List
import yaml
from pathlib import Path
from math import inf, isinf
from snakemake_interface_common.exceptions import WorkflowError
from snakemake_interface_executor_plugins.jobs import (
    JobExecutorInterface,
)
from snakemake_interface_executor_plugins.logging import LoggerExecutorInterface


def read_partition_file(partition_file: Path) -> List["Partition"]:
    with open(partition_file, "r") as f:
        out = []
        partitions_dict = yaml.safe_load(f)["partitions"]
        for partition_name, partition_config in partitions_dict.items():
            if not partition_name or not partition_name.strip():
                raise KeyError("Partition name cannot be empty")

            out.append(
                Partition(
                    name=partition_name,
                    limits=PartitionLimits(**partition_config),
                )
            )
        return out


def get_best_partition(
    candidate_partitions: List["Partition"],
    job: JobExecutorInterface,
    logger: LoggerExecutorInterface,
) -> Optional[str]:
    scored_partitions = [
        (p, score)
        for p in candidate_partitions
        if (score := p.score_job_fit(job)) is not None
    ]

    if scored_partitions:
        best_partition, best_score = max(scored_partitions, key=lambda x: x[1])
        partition = best_partition.name
        logger.warning(
            f"Auto-selected partition '{partition}' for job {job.name} "
            f"with score {best_score:.3f}"
        )
        return partition
    else:
        logger.warning(
            f"No suitable partition found for job {job.name} based on "
            f"resource requirements. Falling back to default behavior."
        )
        return None


def parse_gpu_requirements(job: JobExecutorInterface) -> tuple[int, Optional[str]]:
    """Parse GPU requirements from job resources. Returns (count, model)"""
    gpu_required = job.resources.get("gpu", 0)
    gres = job.resources.get("gres", "")

    # Convert to int if it's a string representation of a number
    if isinstance(gpu_required, str):
        try:
            gpu_required = int(gpu_required)
        except ValueError:
            gpu_required = 0

    # Ensure gres is a string
    if not isinstance(gres, str):
        gres = str(gres) if gres else ""

    if "gpu" in gres and gpu_required:
        raise WorkflowError(
            "GPU resource specified in both 'gpu' and 'gres'. These are mutually exclusive."  # noqa: E501
        )

    if gpu_required:
        return int(gpu_required), job.resources.get("gpu_model")
    elif "gpu" in gres:
        # Parse gres string format: gpu:<number> or gpu:<model>:<number>
        gpu_parts = [part for part in gres.split(",") if part.strip().startswith("gpu")]
        if gpu_parts:
            gpu_spec = gpu_parts[0].strip().split(":")
            if len(gpu_spec) == 2:  # gpu:<number>
                return int(gpu_spec[1]), None
            elif len(gpu_spec) == 3:  # gpu:<model>:<number>
                return int(gpu_spec[2]), gpu_spec[1]

    return 0, None


def get_job_cpu_requirement(job: JobExecutorInterface) -> tuple[int, str]:
    """
    This uses the same logic as snakemake_executor_plugin_slurm_jobstep.get_cpu_setting, but returns a tuple instead of a arg string. # noqa: E501
    """

    gpu_required = job.resources.get("gpu", 0)
    gres = job.resources.get("gres", "")

    # Convert gpu_required to int if it's a string
    if isinstance(gpu_required, str):
        try:
            gpu_required = int(gpu_required)
        except ValueError:
            gpu_required = 0

    # Ensure gres is a string for the "in" check
    if not isinstance(gres, str):
        gres = str(gres) if gres else ""

    has_gpu = bool(gpu_required) or "gpu" in gres

    cpus_per_task = job.resources.get("cpus_per_task")
    if cpus_per_task is not None:
        # Convert to int if it's a string
        if isinstance(cpus_per_task, str):
            try:
                cpus_per_task = int(cpus_per_task)
            except ValueError:
                cpus_per_task = 0
        else:
            cpus_per_task = int(cpus_per_task)

        if cpus_per_task < 0:
            return (0, "none")
        # ensure that at least 1 cpu is requested because 0 is not allowed by slurm
        return (max(1, cpus_per_task), "task")

    elif has_gpu:
        cpus_per_gpu = job.resources.get("cpus_per_gpu")
        if cpus_per_gpu is not None:
            # Convert to int if it's a string
            if isinstance(cpus_per_gpu, str):
                try:
                    cpus_per_gpu = int(cpus_per_gpu)
                except ValueError:
                    cpus_per_gpu = 0
            else:
                cpus_per_gpu = int(cpus_per_gpu)

            if cpus_per_gpu <= 0:
                return (0, "none")
            return (cpus_per_gpu, "gpu")

    return (job.threads, "task")


@dataclass
class PartitionLimits:
    """Represents resource limits for a SLURM partition"""

    # Standard resources
    max_runtime: float = inf  # minutes
    max_mem_mb: float = inf
    max_mem_mb_per_cpu: float = inf
    max_cpus_per_task: float = inf

    # SLURM-specific resources
    max_nodes: float = inf
    max_tasks: float = inf
    max_tasks_per_node: float = inf

    # GPU resources
    max_gpu: int = 0
    available_gpu_models: Optional[List[str]] = None
    max_cpus_per_gpu: float = inf

    # MPI resources
    supports_mpi: bool = True
    max_mpi_tasks: float = inf

    # Node features/constraints
    available_constraints: Optional[List[str]] = None


@dataclass
class Partition:
    """Represents a SLURM partition with its properties and limits"""

    name: str
    limits: PartitionLimits

    def score_job_fit(self, job: JobExecutorInterface) -> Optional[float]:
        """
        Check if a job can run on this partition. If not return none.
        Calculate a score for how well a partition fits the job requirements
        """

        # try to score how closely a job matches a partition's limits, in order to handle case where multiple partitions can run a given job # noqa: E501
        # naive approach here is to just sum the ratio of requested resource to limit, of course this limits us to only consider numerical resources # noqa: E501
        # here a higher score indicates a better fit
        # TODO decide how to handle unspecified limits, for now we assume inf for numerical limits, none for others. # noqa: E501

        score = 0.0

        numerical_resources = {
            "mem_mb": self.limits.max_mem_mb,
            "mem_mb_per_cpu": self.limits.max_mem_mb_per_cpu,
            "runtime": self.limits.max_runtime,
            "nodes": self.limits.max_nodes,
            "tasks": self.limits.max_tasks,
            "tasks_per_node": self.limits.max_tasks_per_node,
            "mpi_tasks": self.limits.max_mpi_tasks,
        }

        for resource_key, limit in numerical_resources.items():
            job_requirement = job.resources.get(resource_key, 0)
            # Convert to numeric value if it's a string
            if isinstance(job_requirement, str):
                try:
                    job_requirement = float(job_requirement)
                except ValueError:
                    job_requirement = 0
            elif not isinstance(job_requirement, (int, float)):
                job_requirement = 0

            if job_requirement > 0:
                if not isinf(limit) and job_requirement > limit:
                    return None
                if not isinf(limit):
                    score += job_requirement / limit

        cpu_count, cpu_type = get_job_cpu_requirement(job)
        if cpu_type == "task" and cpu_count > 0:
            if (
                not isinf(self.limits.max_cpus_per_task)
                and cpu_count > self.limits.max_cpus_per_task
            ):
                return None
            if not isinf(self.limits.max_cpus_per_task):
                score += cpu_count / self.limits.max_cpus_per_task
        elif cpu_type == "gpu" and cpu_count > 0:
            if (
                not isinf(self.limits.max_cpus_per_gpu)
                and cpu_count > self.limits.max_cpus_per_gpu
            ):
                return None
            if not isinf(self.limits.max_cpus_per_gpu):
                score += cpu_count / self.limits.max_cpus_per_gpu

        gpu_count, gpu_model = parse_gpu_requirements(job)
        if gpu_count > 0:
            if self.limits.max_gpu == 0 or gpu_count > self.limits.max_gpu:
                return None
            score += gpu_count / self.limits.max_gpu

            if gpu_model and self.limits.available_gpu_models:
                if gpu_model not in self.limits.available_gpu_models:
                    return None

        if job.resources.get("mpi") and not self.limits.supports_mpi:
            return None

        constraint = job.resources.get("constraint")
        if constraint and self.limits.available_constraints:
            # Ensure constraint is a string
            if not isinstance(constraint, str):
                constraint = str(constraint)
            required_constraints = [
                c.strip() for c in constraint.split(",") if c.strip()
            ]
            if not all(
                req in self.limits.available_constraints for req in required_constraints
            ):
                return None

        return score
