# utility functions for the SLURM executor plugin

import os
import re
from pathlib import Path

from snakemake_interface_executor_plugins.jobs import (
    JobExecutorInterface,
)
from snakemake_interface_common.exceptions import WorkflowError


def delete_slurm_environment():
    """
    Function to delete all environment variables
    starting with 'SLURM_'. The parent shell will
    still have this environment. This is needed to
    submit within a SLURM job context to avoid
    conflicting environments.
    """
    for var in os.environ:
        if var.startswith("SLURM_"):
            del os.environ[var]


def delete_empty_dirs(path: Path) -> None:
    """
    Function to delete all empty directories in a given path.
    This is needed to clean up the working directory after
    a job has sucessfully finished. This function is needed because
    the shutil.rmtree() function does not delete empty
    directories.
    """
    if not path.is_dir():
        return

    # Process subdirectories first (bottom-up)
    for child in path.iterdir():
        if child.is_dir():
            delete_empty_dirs(child)

    try:
        # Check if directory is now empty after processing children
        if not any(path.iterdir()):
            path.rmdir()
    except (OSError, FileNotFoundError) as e:
        # Provide more context in the error message
        raise OSError(f"Failed to remove empty directory {path}: {e}") from e


def set_gres_string(job: JobExecutorInterface) -> str:
    """
    Function to set the gres string for the SLURM job
    based on the resources requested in the job.
    """
    # generic resources (GRES) arguments can be of type
    # "string:int" or "string:string:int"
    gres_re = re.compile(r"^[a-zA-Z0-9_]+(:[a-zA-Z0-9_]+)?:\d+$")
    # gpu model arguments can be of type "string"
    gpu_model_re = re.compile(r"^[a-zA-Z0-9_]+$")
    # The Snakemake resources can be only be of type "int",
    # hence no further regex is needed.

    gpu_string = None
    if job.resources.get("gpu"):
        gpu_string = str(job.resources.get("gpu"))

    gpu_model = None
    if job.resources.get("gpu_model"):
        gpu_model = job.resources.get("gpu_model")

    # ensure that gres is not set, if gpu and gpu_model are set
    if job.resources.get("gres") and gpu_string:
        raise WorkflowError(
            "GRES and GPU are set. Please only set one of them.", rule=job.rule
        )
    elif not job.resources.get("gres") and not gpu_model and not gpu_string:
        return ""

    if job.resources.get("gres"):
        # Validate GRES format (e.g., "gpu:1", "gpu:tesla:2")
        gres = job.resources.gres
        if not gres_re.match(gres):
            raise WorkflowError(
                f"Invalid GRES format: {gres}. Expected format: "
                "'<name>:<number>' or '<name>:<type>:<number>' "
                "(e.g., 'gpu:1' or 'gpu:tesla:2')"
            )
        return f" --gres={job.resources.gres}"

    if gpu_model and gpu_string:
        # validate GPU model format
        if not gpu_model_re.match(gpu_model):
            raise WorkflowError(
                f"Invalid GPU model format: {gpu_model}."
                " Expected format: '<name>' (e.g., 'tesla')"
            )
        return f" --gpus={gpu_model}:{gpu_string}"
    elif gpu_model and not gpu_string:
        raise WorkflowError("GPU model is set, but no GPU number is given")
    elif gpu_string:
        # we assume here, that the validator ensures that the 'gpu_string'
        # is an integer
        return f" --gpus={gpu_string}"

def cannon_resources():
    """
    Function to return the resources for the Cannon cluster.
    """

    partitions = {
            "sapphire":            {"cpus_per_task": 112, "mem_mb": 990000, "runtime": 4320, "gpus": 0},
            "shared":              {"cpus_per_task": 48, "mem_mb": 184000, "runtime": 4320, "gpus": 0},
            "bigmem":              {"cpus_per_task": 112, "mem_mb": 1988000, "runtime": 4320, "gpus": 0},
            "bigmem_intermediate": {"cpus_per_task": 64, "mem_mb": 2000000, "runtime": 20160, "gpus": 0},
            "gpu":                 {"cpus_per_task": 64, "mem_mb": 990000, "runtime": 4320, "gpus": 4},
            "intermediate":        {"cpus_per_task": 112, "mem_mb": 990000, "runtime": 20160, "gpus": 0},
            "unrestricted":        {"cpus_per_task": 48, "mem_mb": 184000, "runtime": "none", "gpus": 0},
            "test":                {"cpus_per_task": 112, "mem_mb": 990000, "runtime": 720, "gpus": 0},
            "gpu_test":            {"cpus_per_task": 64, "mem_mb": 487000, "runtime": 720, "gpus": 4}
            #"serial_requeue":     {"cpus_per_task": "varies", "mem_mb": "varies", "runtime": 4320, "gpus": 0},
            #"gpu_requeue":        {"cpus_per_task": "varies", "mem_mb": "varies", "runtime": 4320, "gpus": 4}
        }
    return partitions


def format_cannon_resources():
    """Return a string that prints resources in a clean aligned table."""
    
    partitions = cannon_resources();
    
    # Header
    lines = [
        "Resources available on the Cannon cluster:",
        "",
        f"{'Partition':<22} {'CPUs':>5}  {'Mem (GB)':>9}  {'Runtime (min)':>14}  {'GPUs':>5}",
        f"{'-'*22} {'-'*5}  {'-'*9}  {'-'*14}  {'-'*5}",
    ]

    for name, res in partitions.items():
        cpus = res["cpus_per_task"]
        mem = res["mem_mb"]
        runtime = res["runtime"]
        gpus = res["gpus"]

        # Convert mem_mb → GB; handle "varies" or "none"
        mem_gb = int(mem) // 1000 if isinstance(mem, int) else str(mem)
        
        lines.append(
            f"{name:<22} {cpus:>5}  {str(mem_gb):>9}  {str(runtime):>14}  {str(gpus):>5}"
        )

    return "\n".join(lines)

def parse_mem_to_mb(raw_mem):
        """
        Converts memory values like '16G', '512MB', '800kb', etc. to integer MB.
        """

        raw_mem = str(raw_mem).strip().upper()
        match = re.match(r"^(\d+(?:\.\d+)?)([GMK]B?|B)?$", raw_mem)

        if not match:
            raise WorkflowError(f"Invalid memory format: '{raw_mem}'.")

        value, unit = match.groups()
        value = float(value)

        unit = unit or "MB"  # Default to MB if unit omitted
        unit_map = {
            "K": 1 / 1000,
            "KB": 1 / 1000,
            "M": 1,
            "MB": 1,
            "G": 1000,
            "GB": 1000,
            # optionally, support binary units:
            # "KI": 1 / 1024,
            # "MI": 1,
            # "GI": 1024
        }

        if unit not in unit_map:
            raise WorkflowError(f"Unsupported memory unit '{unit}' in 'mem' resource.")

        mem_mb = value * unit_map[unit]
        return int(mem_mb)

def normalize_mem(job, default_mem_mb=8005):
    if job.resources.get("mem"):
        mem_mb = parse_mem_to_mb(job.resources.get("mem"))
    elif job.resources.get("mem_gb"):
        mem_mb = job.resources.get("mem_gb", 4) * 1000;
    elif job.resources.get("mem_mb"):
        mem_mb = job.resources.get("mem_mb", 4000)
    else:
        mem_mb = default_mem_mb  # Default memory in MB
    # Convert to MB if necessary

    orig_mem = False;
    if mem_mb < default_mem_mb:
        orig_mem = mem_mb;
        mem_mb = default_mem_mb  # Minimum memory in MB

    return mem_mb, orig_mem


# def parse_slurm_extra(slurm_extra):
#     """
#     Extract number of GPUs from --gres=gpu:<count> entry in slurm_extra.

#     Supports arbitrary ordering and ignores other --gres values.
#     """
#     gres_gpu_match = re.search(r"--gres=gpu(?::[^\s,:=]+)?:(\d+)", slurm_extra.lower())
#     if gres_gpu_match:
#         return int(gres_gpu_match.group(1))
#     return 0

def parse_num_gpus(job):
    """
    Extract number of GPUs from job.resources in priority order:

    1. If gpu and optional gpu_model are provided → use those
    2. Else if gres is specified (e.g. "gpu:2" or "gpu:a100:4") → parse it
    3. Else if slurm_extra contains --gres=gpu:... → extract from there
    4. Else → assume 0 GPUs
    """
    gpu = job.resources.get("gpu", 0)
    gpu_model = job.resources.get("gpu_model")
    gres = job.resources.get("gres", None)
    slurm_extra = str(job.resources.get("slurm_extra", ""))

    # 1. GPU + optional model: gpu must be > 0
    if gpu_model:
        if not gpu or not isinstance(gpu, int):
            raise WorkflowError("GPU model is set, but 'gpu' number is missing or invalid.")
        if ":" in gpu_model:
            raise WorkflowError("Invalid GPU model format — should not contain ':'.")
        return int(gpu)  # interpreted with model separately

    if isinstance(gpu, int) and gpu > 0:
        return gpu

    # 2. Parse "gres" string if present
    if gres:
        gres = str(gres)
        match = re.match(r"^gpu(?::[a-zA-Z0-9_]+)?:(\d+)$", gres)
        if match:
            return int(match.group(1))
        else:
            raise WorkflowError(f"Invalid GRES format in resources.gres: '{gres}'")

    # 3. Parse slurm_extra
    match = re.search(r"--gres=gpu(?::[^\s,:=]+)?:(\d+)", slurm_extra.lower())
    if match:
        return int(match.group(1))

    # 4. Fallback: no GPUs requested
    return 0
