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
    # gpus can be of type "int" or "string:int"
    gpus_re = re.compile(r"^\d+$|^[a-zA-Z0-9_]+:\d+$")

    if job.resources.get("gres"):
        # Validate GRES format (e.g., "gpu:1", "gpu:tesla:2")
        gres = job.resources.gres
        if not gres_re.match(gres):
            raise WorkflowError(
                f"Invalid GRES format: {gres}. Expected format: "
                "'<name>:<number>' or '<name>:<type>:<number>' "
                "(e.g., 'gpu:1' or 'gpu:tesla:2')"
            )
        gres_string = f" --gres={job.resources.gres}"
    if job.resources.get("gpu"):
        # ensure that gres is not set, if gpu and gpu_model are set
        if job.resources.get("gres"):
            raise WorkflowError("GRES and GPU are set. Please only set one of them.")
        # ensure that 'gpu' is an integer
        if not isinstance(job.resources.gpu, int):
            raise WorkflowError(
                "The 'gpu' resource must be an integer. "
                f"Got: {job.resources.gpu} ({type(job.resources.gpu)})."
            )
        gres_string = f" --gpus={job.resources.gpu}"
    if job.resources.get("gpu"):
        # ensure that gres is not set, if gpu and gpu_model are set
        if job.resources.get("gres"):
            raise WorkflowError("GRES and GPU are set. Please only set one" " of them.")
        # validate GPU format
        if not gpus_re.match(str(job.resources.gpu)):
            raise WorkflowError(
                f"Invalid GPU format: {job.resources.gpu}. "
                "Expected format: '<number>' or '<name>:<number>' "
                "(e.g., '1' or 'tesla:2')"
            )
        gres_string = f" --gpus={job.resources.gpu}"
    elif job.resources.get("gpu_model") and job.resources.get("gpu"):
        # validate GPU model format
        if not gpu_model_re.match(job.resources.gpu_model):
            raise WorkflowError(
                f"Invalid GPU model format: {job.resources.gpu_model}. "
                "Expected format: '<name>' "
                "(e.g., 'tesla')"
            )
        gres_string = f" --gpus:{job.resources.gpu_model}:{job.resources.gpu}"
    elif job.resources.get("gpu_model") and not job.resources.get("gpu"):
        raise WorkflowError(
            "GPU model is set, but no GPU number is given. " "Please set 'gpu' as well."
        )
    return gres_string if job.resources.get("gres") or job.resources.get("gpu") else ""
