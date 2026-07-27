from dataclasses import dataclass
from typing import Optional, List, Dict
import yaml
from pathlib import Path
from math import inf, isinf
import subprocess
import shlex
import re
from snakemake_interface_common.exceptions import WorkflowError
from snakemake_interface_executor_plugins.jobs import (
    JobExecutorInterface,
)
from snakemake_interface_executor_plugins.logging import LoggerExecutorInterface
from .utils import parse_time_to_minutes


def get_default_partition(
    job: JobExecutorInterface, logger: LoggerExecutorInterface
) -> str:
    """
    if no partition is given, checks whether a fallback onto a default
    partition is possible
    """
    cmd = shlex.split("sinfo -o %P")
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        raise WorkflowError(
            f"Failed to run sinfo for retrieval of cluster partitions: {e.stderr}"
        )
    for partition in out.split():
        # A default partition is marked with an asterisk, but this is not part of
        # the name.
        if "*" in partition:
            return partition.replace("*", "")
    logger.warning(
        f"No partition was given for rule '{job}', and unable to find "
        "a default partition."
        " Trying to submit without partition information."
        " You may want to invoke snakemake with --default-resources "
        "'slurm_partition=<your default partition>'."
    )
    return ""


def read_partition_file(partition_file: Path) -> List["Partition"]:
    """Read partition definitions from a YAML file"""
    try:
        with open(partition_file, "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise WorkflowError(f"Partition file not found: {partition_file}")
    except yaml.YAMLError as e:
        raise WorkflowError(f"Error parsing partition file {partition_file}: {e}")
    except Exception as e:
        raise WorkflowError(
            f"Unexpected error reading partition file {partition_file}: {e}"
        )
    if not isinstance(config, dict) or "partitions" not in config:
        raise WorkflowError(
            f"Partition file {partition_file} is missing 'partitions' section"
        )
    partitions_dict = config["partitions"]
    if not isinstance(partitions_dict, dict):
        raise WorkflowError(
            f"'partitions' section in {partition_file} must be a mapping"
        )
    out = []
    for partition_name, partition_config in partitions_dict.items():
        if not partition_name or not partition_name.strip():
            raise KeyError("Partition name cannot be empty")

        # Extract optional cluster name from partition config
        cluster = None
        for key in ("slurm_cluster", "cluster", "clusters"):
            if key in partition_config:
                cluster = partition_config.pop(key)
                break

        # Extract optional default marker.
        is_default = False
        for key in ("default", "is_default"):
            if key in partition_config:
                raw_default = partition_config.pop(key)
                if isinstance(raw_default, str):
                    is_default = raw_default.strip().lower() in {
                        "1",
                        "true",
                        "yes",
                        "on",
                    }
                else:
                    is_default = bool(raw_default)
                break

        out.append(
            Partition(
                name=partition_name,
                partition_cluster=cluster,
                limits=PartitionLimits(**partition_config),
                is_default=is_default,
            )
        )
    return out


def query_scontrol_partitions(cluster=None) -> str:
    """
    Query SLURM partition information using scontrol.

    Args:
        cluster: Optional cluster name for multi-cluster setups

    Returns:
        Raw output from scontrol show partition
    """
    cmd = "scontrol show partition"
    if cluster:
        cmd += f" -M {cluster}"

    cmd = shlex.split(cmd)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise WorkflowError(
            f"Failed to query partition information with scontrol: {e.stderr}"
        )
    except Exception as e:
        raise WorkflowError(f"Error querying scontrol: {e}")


def query_default_partitions(cluster=None) -> Optional[str]:
    """
    Query the default partition name using sinfo.

    A partition marked with an asterisk is considered default.
    """
    cmd = "sinfo -sa -o %P"
    if cluster:
        cmd += f" -M {cluster}"

    cmd = shlex.split(cmd)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        for token in result.stdout.split():
            if token == "PARTITION":
                continue
            if "*" in token:
                return token.replace("*", "")
        return None
    except subprocess.CalledProcessError as e:
        raise WorkflowError(
            f"Failed to query default partitions with sinfo: {e.stderr}"
        )
    except Exception as e:
        raise WorkflowError(f"Error querying default partitions: {e}")


def parse_scontrol_partition_output(scontrol_output: str) -> Dict[str, Dict]:
    """
    Parse scontrol show partition output into partition configurations.

    Args:
        scontrol_output: Raw output from scontrol show partition

    Returns:
        Dictionary with partition names as keys and config dicts as values
    """
    partitions = {}
    current_partition = None
    current_config = {}

    for line in scontrol_output.split("\n"):
        line = line.strip()

        if line.startswith("PartitionName="):
            # Save previous partition if exists
            if current_partition:
                partitions[current_partition] = current_config

            # Start new partition
            current_partition = line.split("=", 1)[1]
            current_config = {}

        elif current_partition and "=" in line:
            # Parse key-value pairs
            for item in line.split():
                if "=" in item:
                    key, value = item.split("=", 1)
                    current_config[key] = value

    # Don't forget the last partition
    if current_partition:
        partitions[current_partition] = current_config

    return partitions


def parse_tres_memory_to_mb(mem_value: str) -> Optional[int]:
    """
    Parse a SLURM memory token (e.g. ``180600000M`` or ``176G``) into MB.

    Returns None if the value cannot be parsed.
    """
    if not mem_value:
        return None

    token = str(mem_value).strip()
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([KMGTP])?", token, flags=re.I)
    if not match:
        return None

    value = float(match.group(1))
    unit = (match.group(2) or "M").upper()
    unit_factor_to_mb = {
        "K": 1.0 / 1024.0,
        "M": 1.0,
        "G": 1024.0,
        "T": 1024.0 * 1024.0,
        "P": 1024.0 * 1024.0 * 1024.0,
    }
    return int(value * unit_factor_to_mb[unit])


def parse_tres_billing_weights(weights_value: str) -> Dict[str, float]:
    """
    Parse TRESBillingWeights into normalized numeric values.

        Returns optional keys:
            - billing_weight_cpu
            - billing_weight_mem
            - billing_weight_mem_unit
            - billing_weight_mem_gb (compatibility alias when unit is G)
    """
    out = {}
    if not weights_value:
        return out

    cpu_match = re.search(r"(?:^|,)cpu=([0-9]+(?:\.[0-9]+)?)", weights_value)
    if cpu_match:
        out["billing_weight_cpu"] = float(cpu_match.group(1))

    mem_match = re.search(r"(?:^|,)mem=([^,]+)", weights_value)
    if mem_match:
        mem_token = mem_match.group(1).strip()
        mem_parts = re.fullmatch(
            r"([0-9]+(?:\.[0-9]+)?)([KMGTP])?", mem_token, flags=re.I
        )
        if mem_parts:
            mem_value = float(mem_parts.group(1))
            mem_unit = (mem_parts.group(2) or "M").upper()
            out["billing_weight_mem"] = mem_value
            out["billing_weight_mem_unit"] = mem_unit
            if mem_unit == "G":
                # Keep backward-compatible key without unit conversion.
                out["billing_weight_mem_gb"] = mem_value

    return out


def extract_partition_limits(partition_data: Dict[str, str]) -> Dict:
    """
    Extract partition limits from scontrol output data.

    Args:
        partition_data: Dictionary of partition key-value pairs from scontrol

    Returns:
        Dictionary with partition limit configuration
    """
    config = {}

    # MaxTime -> max_runtime
    if "MaxTime" in partition_data and partition_data["MaxTime"] != "UNLIMITED":
        config["max_runtime"] = partition_data["MaxTime"]

    # MaxNodes -> max_nodes
    if "MaxNodes" in partition_data and partition_data["MaxNodes"] != "UNLIMITED":
        try:
            config["max_nodes"] = int(partition_data["MaxNodes"])
        except ValueError:
            pass

    # MaxCPUsPerNode -> max_threads (using total CPUs / total nodes as approx)
    # Or extract from TotalCPUs if available
    if "TotalCPUs" in partition_data and "TotalNodes" in partition_data:
        try:
            total_cpus = int(partition_data["TotalCPUs"])
            total_nodes = int(partition_data["TotalNodes"])
            if total_nodes > 0:
                max_cpus_per_node = total_cpus // total_nodes
                config["max_threads"] = max_cpus_per_node
        except ValueError:
            pass

    # DefMemPerCPU -> max_mem_mb_per_cpu
    if "DefMemPerCPU" in partition_data:
        try:
            # DefMemPerCPU is in MB
            mem_mb = int(partition_data["DefMemPerCPU"])
            config["max_mem_mb_per_cpu"] = mem_mb
        except ValueError:
            pass

    # MaxMemPerNode -> max_mem_mb
    # If UNLIMITED, do not set this limit.
    if "MaxMemPerNode" in partition_data:
        max_mem_per_node = partition_data["MaxMemPerNode"]
        if max_mem_per_node != "UNLIMITED":
            mem_mb = parse_tres_memory_to_mb(max_mem_per_node)
            if mem_mb is not None:
                config["max_mem_mb"] = mem_mb

    # Check for GPU support in TRES
    if "TRES" in partition_data:
        tres = partition_data["TRES"]
        # TRES format: cpu=...,mem=...,gres/gpu=N
        mem_match = re.search(r"(?:^|,)mem=([^,]+)", tres)
        if mem_match and "max_mem_mb" not in config:
            mem_mb = parse_tres_memory_to_mb(mem_match.group(1))
            if mem_mb is not None:
                config["max_mem_mb"] = mem_mb

        if "gres/gpu" in tres:
            gpu_match = re.search(r"gres/gpu=(\d+)", tres)
            if gpu_match:
                config["max_gpu"] = int(gpu_match.group(1))

    # TRESBillingWeights -> billing weights used for cost-aware ranking
    if "TRESBillingWeights" in partition_data:
        config.update(parse_tres_billing_weights(partition_data["TRESBillingWeights"]))

    return config


def generate_partitions_from_slurm_query(
    args,
) -> Dict[str, Dict]:
    """
    Generate partition configuration by querying scontrol.

    Args:
        <cluster>,<cluster>: Optional cluster names for multi-cluster setups

    Returns:
        Dictionary formatted for partition YAML (nested under 'partitions' key)
    """
    partitions_config = {}

    if args:
        for arg in args.split(","):
            cluster = arg.strip()
            scontrol_output = query_scontrol_partitions(cluster)
            default_partition = query_default_partitions(cluster)
            partitions_data = parse_scontrol_partition_output(scontrol_output)

            for partition_name, partition_data in partitions_data.items():
                limits = extract_partition_limits(partition_data)
                limits["cluster"] = cluster
                if partition_name == default_partition:
                    limits["default"] = True
                # Scope key by cluster so identically-named partitions across
                # clusters do not overwrite each other in the generated template.
                key = f"{cluster}_{partition_name}"
                partitions_config[key] = limits
    else:
        scontrol_output = query_scontrol_partitions()
        default_partition = query_default_partitions()
        partitions_data = parse_scontrol_partition_output(scontrol_output)

        for partition_name, partition_data in partitions_data.items():
            limits = extract_partition_limits(partition_data)
            if partition_name == default_partition:
                limits["default"] = True
            partitions_config[partition_name] = limits

    return {"partitions": partitions_config}


# Note: this function is just a wrapper for the CI to work
def generate_partitions_from_scontrol(
    cluster: Optional[str] = None,
) -> Dict[str, Dict]:
    """Backward-compatible wrapper around generate_partitions_from_slurm_query."""
    return generate_partitions_from_slurm_query(cluster)


def get_best_partition(
    candidate_partitions: List["Partition"],
    job: JobExecutorInterface,
    logger: LoggerExecutorInterface,
) -> Optional[str]:
    scored_partitions = []
    for p in candidate_partitions:
        score = p.score_job_fit(job)
        logger.debug(f"Partition '{p.name}' score for job {job.name}: {score}")
        if score is not None:
            scored_partitions.append((p, score))

    if scored_partitions:
        requested_dimensions = get_requested_dimensions(job)
        best_partition, best_score = min(
            scored_partitions,
            key=lambda x: rank_partition_for_job(
                x[0],
                x[1],
                job,
                requested_dimensions,
            ),
        )
        partition = best_partition.name
        logger.info(
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


def as_positive_float(value) -> float:
    """Convert resource values to positive float, otherwise return 0."""
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            return 0.0
    elif not isinstance(value, (int, float)):
        return 0.0
    return float(value) if value > 0 else 0.0


def get_requested_dimensions(job: JobExecutorInterface) -> List[str]:
    """Return resource dimensions that are relevant for tie-breaking."""
    dimensions = []

    for key in [
        "mem_mb_per_cpu",
        "runtime",
        "nodes",
        "tasks",
        "tasks_per_node",
        "mpi_tasks",
    ]:
        if as_positive_float(job.resources.get(key, 0)) > 0:
            dimensions.append(key)

    effective_threads = get_effective_threads(job)
    if effective_threads > 0:
        dimensions.append("threads")

    cpu_count, cpu_type = get_job_cpu_requirement(job)
    if cpu_type == "task" and cpu_count > 0:
        dimensions.extend(["threads", "cpus_per_task"])
    elif cpu_type == "gpu" and cpu_count > 0:
        dimensions.append("cpus_per_gpu")

    gpu_count, _ = parse_gpu_requirements(job)
    if gpu_count > 0:
        dimensions.append("gpu")

    # De-duplicate while preserving order.
    out = []
    seen = set()
    for dim in dimensions:
        if dim not in seen:
            out.append(dim)
            seen.add(dim)
    return out


def get_partition_limit_for_dimension(partition: "Partition", dimension: str) -> float:
    """Map a dimension key to a partition limit value."""
    limits = partition.limits
    dim_to_limit = {
        "mem_mb": limits.max_mem_mb,
        "mem_mb_per_cpu": limits.max_mem_mb_per_cpu,
        "runtime": limits.max_runtime,
        "nodes": limits.max_nodes,
        "tasks": limits.max_tasks,
        "tasks_per_node": limits.max_tasks_per_node,
        "mpi_tasks": limits.max_mpi_tasks,
        "threads": limits.max_threads,
        "cpus_per_task": limits.max_cpus_per_task,
        "cpus_per_gpu": limits.max_cpus_per_gpu,
        "gpu": float(limits.max_gpu),
    }
    value = dim_to_limit.get(dimension, inf)
    if isinstance(value, (int, float)):
        return float(value)
    return inf


def rank_partition_for_job(
    partition: "Partition",
    score: float,
    job: JobExecutorInterface,
    requested_dimensions: List[str],
) -> tuple:
    """
    Ranking key used for best partition selection.

    Order:
      1) default partitions first,
      2) lower estimated billing cost first,
      3) higher score,
      4) lower limits on requested dimensions,
      5) partition name for deterministic behavior.
    """
    default_rank = 0 if partition.is_default else 1
    billing_cost = estimate_partition_billing_cost(partition, job)
    tie_break_limits = []
    for dim in requested_dimensions:
        limit = get_partition_limit_for_dimension(partition, dim)
        tie_break_limits.append(limit if not isinf(limit) else inf)
    return (default_rank, billing_cost, -score, tuple(tie_break_limits), partition.name)


def estimate_partition_billing_cost(
    partition: "Partition", job: JobExecutorInterface
) -> float:
    """
    Estimate a relative billing cost for a job on a given partition.

    If required billing weights are unavailable, returns ``inf`` so partitions
    with known lower cost are preferred.
    """
    cpu_count, _ = get_job_cpu_requirement(job)
    mem_mb = as_positive_float(job.resources.get("mem_mb", 0))
    if mem_mb <= 0:
        mem_per_cpu = as_positive_float(job.resources.get("mem_mb_per_cpu", 0))
        if mem_per_cpu > 0 and cpu_count > 0:
            mem_mb = mem_per_cpu * cpu_count

    cpu_weight = partition.limits.billing_weight_cpu
    mem_weight = partition.limits.billing_weight_mem
    mem_weight_unit = partition.limits.billing_weight_mem_unit
    if mem_weight is None and partition.limits.billing_weight_mem_gb is not None:
        # Backward compatibility for older configs.
        mem_weight = partition.limits.billing_weight_mem_gb
        mem_weight_unit = "G"

    if cpu_count > 0 and cpu_weight is None:
        return inf
    if mem_mb > 0 and mem_weight is None:
        return inf

    cost = 0.0
    if cpu_count > 0 and cpu_weight is not None:
        cost += cpu_count * cpu_weight
    if mem_mb > 0 and mem_weight is not None and mem_weight_unit is not None:
        if mem_weight_unit == "K":
            mem_units = mem_mb * 1024.0
        elif mem_weight_unit == "M":
            mem_units = mem_mb
        elif mem_weight_unit == "G":
            mem_units = mem_mb / 1024.0
        elif mem_weight_unit == "T":
            mem_units = mem_mb / (1024.0 * 1024.0)
        elif mem_weight_unit == "P":
            mem_units = mem_mb / (1024.0 * 1024.0 * 1024.0)
        else:
            return inf
        cost += mem_units * mem_weight
    return cost


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


def get_effective_threads(job: JobExecutorInterface) -> int:
    """
    Get the effective thread count for a job.
    First checks job.threads, then falls back to job.resources["threads"].
    This handles cases where threads is specified in the resources block.
    """
    threads = job.threads
    # If threads is default (1) or not set, check resources
    if threads == 1 or threads is None:
        resource_threads = job.resources.get("threads")
        if resource_threads is not None:
            try:
                resource_threads = int(resource_threads)
            except ValueError:
                resource_threads = threads
            threads = resource_threads if resource_threads > 1 else threads

    # ensuring a valid thread count
    if threads is None or threads < 1:
        threads = 1
    return threads


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
            raise WorkflowError("cpus_per_task cannot be negative")
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

    # Fall back to effective threads (checks both job.threads and resources.threads)
    return (get_effective_threads(job), "task")


@dataclass
class PartitionLimits:
    """Represents resource limits for a SLURM partition"""

    # Standard resources
    max_runtime: float = inf  # minutes
    max_mem_mb: float = inf
    max_mem_mb_per_cpu: float = inf
    max_cpus_per_task: float = inf
    max_threads: float = inf

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

    # Billing weights (from TRESBillingWeights)
    billing_weight_cpu: Optional[float] = None
    billing_weight_mem: Optional[float] = None
    billing_weight_mem_unit: Optional[str] = None
    billing_weight_mem_gb: Optional[float] = None

    def __post_init__(self):
        """Convert max_runtime to minutes if specified as a time string"""
        # Check if max_runtime is a string or needs conversion
        # isinf() only works on numeric types, so check type first
        if isinstance(self.max_runtime, str) or (
            isinstance(self.max_runtime, (int, float)) and not isinf(self.max_runtime)
        ):
            self.max_runtime = parse_time_to_minutes(self.max_runtime)


@dataclass
class Partition:
    """Represents a SLURM partition with its properties and limits"""

    name: str
    limits: PartitionLimits
    partition_cluster: Optional[str] = None
    is_default: bool = False

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

        # Check cluster compatibility, first:
        # Accept multiple possible resource names for cluster specification
        job_cluster = (
            job.resources.get("slurm_cluster")
            or job.resources.get("cluster")
            or job.resources.get("clusters")
        )

        # Enforce strict cluster eligibility:
        # - If the job specifies a cluster, only partitions with a matching cluster
        #   are eligible
        # - If the job does not specify a cluster, only partitions without a cluster
        #   are eligible
        if job_cluster is not None:
            if self.partition_cluster != job_cluster:
                return None  # Not eligible
        else:
            if self.partition_cluster is not None:
                return None  # Not eligible

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
                # max_mem_mb is treated as an upper threshold only.
                if resource_key != "mem_mb" and not isinf(limit):
                    score += job_requirement / limit

        # Check thread requirements (check both job.threads and resources.threads)
        effective_threads = get_effective_threads(job)
        if effective_threads is not None and effective_threads > 0:
            if (
                not isinf(self.limits.max_threads)
                and effective_threads > self.limits.max_threads
            ):
                # Debug: partition cannot accommodate threads
                return None
            if not isinf(self.limits.max_threads):
                score += effective_threads / self.limits.max_threads

        cpu_count, cpu_type = get_job_cpu_requirement(job)
        if cpu_type == "task" and cpu_count > 0:
            # Check cpu_count against max_threads
            if (
                not isinf(self.limits.max_threads)
                and cpu_count > self.limits.max_threads
            ):
                return None
            if not isinf(self.limits.max_threads):
                score += cpu_count / self.limits.max_threads

            # Also check against max_cpus_per_task
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
        if gpu_count == 0 and self.limits.max_gpu > 0:
            # Disadvantage gpu partitions for cpu only jobs
            score -= 1
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
