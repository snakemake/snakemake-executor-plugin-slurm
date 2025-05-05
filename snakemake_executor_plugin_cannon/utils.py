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
            "sapphire":            {"cpus_per_task": 112, "mem_mb": 1013760, "runtime": 4320, "gpus": 0},
            "shared":              {"cpus_per_task": 48, "mem_mb": 188416, "runtime": 4320, "gpus": 0},
            "bigmem":              {"cpus_per_task": 112, "mem_mb": 2035712, "runtime": 4320, "gpus": 0},
            "bigmem_intermediate": {"cpus_per_task": 64, "mem_mb": 2048000, "runtime": 20160, "gpus": 0},
            "gpu":                 {"cpus_per_task": 64, "mem_mb": 1013760, "runtime": 4320, "gpus": 4},
            "intermediate":        {"cpus_per_task": 112, "mem_mb": 1013760, "runtime": 20160, "gpus": 0},
            "unrestricted":        {"cpus_per_task": 48, "mem_mb": 188416, "runtime": "none", "gpus": 0},
            "test":                {"cpus_per_task": 112, "mem_mb": 1013760, "runtime": 720, "gpus": 0},
            "gpu_test":            {"cpus_per_task": 64, "mem_mb": 498688, "runtime": 720, "gpus": 4}
            #"serial_requeue":     {"cpus_per_task": "varies", "mem_mb": "varies", "runtime": 4320, "gpus": 0},
            #"gpu_requeue":        {"cpus_per_task": "varies", "mem_mb": "varies", "runtime": 4320, "gpus": 4}
        }
    return partitions


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

def parse_slurm_extra(slurm_extra):
    """
    Extract number of GPUs from --gres=gpu:<count> entry in slurm_extra.

    Supports arbitrary ordering and ignores other --gres values.
    """
    gres_gpu_match = re.search(r"--gres=gpu(?::[^\s,:=]+)?:(\d+)", slurm_extra.lower())
    if gres_gpu_match:
        return int(gres_gpu_match.group(1))
    return 0
