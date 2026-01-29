# utility functions for the SLURM executor plugin

import math
import os
import re
from pathlib import Path
from typing import Union

from snakemake_interface_executor_plugins.jobs import (
    JobExecutorInterface,
)
from snakemake_interface_common.exceptions import WorkflowError


def round_half_up(n):
    return int(math.floor(n + 0.5))


def parse_time_to_minutes(time_value: Union[str, int, float]) -> int:
    """
    Convert a time specification to minutes (integer). This function
    is intended to handle the partition definitions for the max_runtime
    value in a partition config file.

    Supports:
    - Numeric values (assumed to be in minutes): 120, 120.5
    - Snakemake-style time strings: "6d", "12h", "30m", "90s", "2d12h30m"
    - SLURM time formats:
        - "minutes" (e.g., "60")
        - "minutes:seconds" (interpreted as hours:minutes, e.g., "60:30")
        - "hours:minutes:seconds" (e.g., "1:30:45")
        - "days-hours" (e.g., "2-12")
        - "days-hours:minutes" (e.g., "2-12:30")
        - "days-hours:minutes:seconds" (e.g., "2-12:30:45")

    Args:
        time_value: Time specification as string, int, or float

    Returns:
        Time in minutes as integer (fractional minutes are rounded)

    Raises:
        WorkflowError: If the time format is invalid
    """
    # If already numeric, return as integer minutes (rounded)
    if isinstance(time_value, (int, float)):
        return round_half_up(time_value)  # implicit conversion to int

    # Convert to string and strip whitespace
    time_str = str(time_value).strip()

    # Try to parse as plain number first
    try:
        return round_half_up(float(time_str))  # implicit conversion to int
    except ValueError:
        pass

    # Try SLURM time formats first (with colons and dashes)
    # Format: days-hours:minutes:seconds or variations
    if "-" in time_str or ":" in time_str:
        try:
            days = 0
            hours = 0
            minutes = 0
            seconds = 0

            # Split by dash first (days separator)
            if "-" in time_str:
                parts = time_str.split("-")
                if len(parts) != 2:
                    raise ValueError("Invalid format with dash")
                days = int(parts[0])
                time_str = parts[1]

            # Split by colon (time separator)
            time_parts = time_str.split(":")

            if len(time_parts) == 1:
                # Just hours (after dash) or just minutes
                if days > 0:
                    hours = int(time_parts[0])
                else:
                    minutes = int(time_parts[0])
            elif len(time_parts) == 2:
                # was: days-hours:minutes
                hours = int(time_parts[0])
                minutes = int(time_parts[1])
            elif len(time_parts) == 3:
                # was: hours:minutes:seconds
                hours = int(time_parts[0])
                minutes = int(time_parts[1])
                seconds = int(time_parts[2])
            else:
                raise ValueError("Too many colons in time format")

            # Convert everything to minutes
            total_minutes = days * 24 * 60 + hours * 60 + minutes + seconds / 60.0
            return round_half_up(total_minutes)  # implicit conversion to int

        except (ValueError, IndexError):
            # If SLURM format parsing fails, try Snakemake style below
            pass

    # Parse Snakemake-style time strings (e.g., "6d", "12h", "30m", "90s", "2d12h30m")
    # Pattern matches: optional number followed by unit (d, h, m, s)
    pattern = r"(\d+(?:\.\d+)?)\s*([dhms])"
    matches = re.findall(pattern, time_str.lower())

    if not matches:
        raise WorkflowError(
            f"Invalid time format: '{time_value}'. "
            f"Expected formats:\n"
            f"  - Numeric value in minutes: 120\n"
            f"  - Snakemake style: '6d', '12h', '30m', '90s', '2d12h30m'\n"
            f"  - SLURM style: 'minutes', 'minutes:seconds', 'hours:minutes:seconds',\n"
            f"    'days-hours', 'days-hours:minutes', 'days-hours:minutes:seconds'"
        )

    total_minutes = 0.0
    for value, unit in matches:
        num = float(value)
        if unit == "d":
            total_minutes += num * 24 * 60
        elif unit == "h":
            total_minutes += num * 60
        elif unit == "m":
            total_minutes += num
        elif unit == "s":
            total_minutes += num / 60

    return round_half_up(total_minutes)


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
    gres_re = re.compile(r"^[a-zA-Z0-9_]+(:[a-zA-Z0-9_\.]+)?:\d+$")
    # gpu model arguments can be of type "string"
    # The model string may contain a dot for variants, see
    # https://github.com/snakemake/snakemake-executor-plugin-slurm/issues/387
    gpu_model_re = re.compile(r"^[a-zA-Z0-9_\.]+$")
    # any arguments should not start and end with ticks or
    # quotation marks:
    string_check = re.compile(r"^[^'\"].*[^'\"]$")
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
            if not string_check.match(gres):
                raise WorkflowError(
                    "GRES format should not be a nested string (start "
                    "and end with ticks or quotation marks). "
                    "Expected format: "
                    "'<name>:<number>' or '<name>:<type>:<number>' "
                    "(e.g., 'gpu:1' or 'gpu:tesla:2')"
                )
            else:
                raise WorkflowError(
                    f"Invalid GRES format: {gres}. Expected format: "
                    "'<name>:<number>' or '<name>:<type>:<number>' "
                    "(e.g., 'gpu:1' or 'gpu:tesla:2')"
                )
        return f" --gres={job.resources.gres}"

    if gpu_model and gpu_string:
        # validate GPU model format
        if not gpu_model_re.match(gpu_model):
            if not string_check.match(gpu_model):
                raise WorkflowError(
                    "GPU model format should not be a nested string (start "
                    "and end with ticks or quotation marks). "
                    "Expected format: '<name>' (e.g., 'tesla')"
                )
            else:
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
