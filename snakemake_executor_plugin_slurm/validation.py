"""
SLURM parameter validation functions for the Snakemake executor plugin.
"""

import re
from pathlib import Path
from snakemake_interface_common.exceptions import WorkflowError
from .job_status_query import get_min_job_age, is_query_tool_available


def get_forbidden_slurm_options():
    """
    Return a dictionary of forbidden SLURM options that the executor manages.

    Returns:
        dict: Mapping of regex patterns to human-readable option names
    """
    return {
        # Job identification and output
        r"--job-name[=\s]|-J\s?": "job name",
        r"--output[=\s]|-o\s": "output file",
        r"--error[=\s]|-e\s": "error file",
        r"--parsable": "parsable output",
        r"--export[=\s]": "environment export",
        r"--comment[=\s]": "job comment",
        r"--workdir[=\s]|-D\s": "working directory",
        # Account and partition
        r"--account[=\s]|-A\s": "account",
        r"--partition[=\s]|-p\s": "partition",
        # Memory options
        r"--mem[=\s]": "memory",
        r"--mem-per-cpu[=\s]": "memory per CPU",
        # CPU and task options
        r"--ntasks[=\s]|-n\s": "number of tasks",
        r"--ntasks-per-gpu[=\s]": "tasks per GPU",
        r"--cpus-per-task[=\s]|-c\s": "CPUs per task",
        r"--cpus-per-gpu[=\s]": "CPUs per GPU",
        # Time and resource constraints
        r"--time[=\s]|-t\s": "runtime/time limit",
        r"--constraint[=\s]|-C\s": "node constraints",
        r"--qos[=\s]": "quality of service",
        r"--nodes[=\s]|-N\s": "number of nodes",
        r"--clusters[=\s]": "cluster specification",
        # GPU options
        r"--gres[=\s]": "generic resources (GRES)",
        r"--gpus[=\s]": "GPU allocation",
    }


def validate_slurm_extra(job):
    """
    Validate that slurm_extra doesn't contain executor-managed options.

    Args:
        job: Snakemake job object with resources attribute

    Raises:
        WorkflowError: If forbidden SLURM options are found in slurm_extra
    """
    # skip testing if no slurm_extra is set
    slurm_extra = getattr(job.resources, "slurm_extra", None)
    if not slurm_extra:
        return

    forbidden_options = get_forbidden_slurm_options()

    for pattern, option_name in forbidden_options.items():
        if re.search(pattern, slurm_extra):
            raise WorkflowError(
                f"The --{option_name.replace(' ', '-')} option is not "
                f"allowed in the 'slurm_extra' parameter. "
                f"The {option_name} is set by the snakemake executor plugin "
                f"and must not be overwritten. "
                f"Please use the appropriate snakemake resource "
                f"specification instead. "
                f"Consult the documentation for proper resource configuration."
            )


def validate_status_command_settings(settings, logger):
    """Emit warnings about status_command sensibility."""
    if not hasattr(settings, "status_command"):
        return
    status_command = settings.status_command
    if not status_command:
        return
    min_job_age = get_min_job_age()
    sacct_available = is_query_tool_available("sacct")
    initial_interval = getattr(
        settings,
        "init_seconds_before_status_checks",
        40,
    )
    dynamic_check_threshold = 3 * initial_interval
    if not sacct_available and status_command == "sacct":
        logger.warning(
            "The 'sacct' command is not available. Falling back to 'squeue'."
        )
    elif sacct_available and min_job_age is not None:
        if min_job_age < dynamic_check_threshold and status_command == "squeue":
            logger.warning(
                f"MinJobAge {min_job_age}s (< {dynamic_check_threshold}s). "
                "This may cause 'squeue' to miss recently finished jobs. "
                "Consider using 'sacct' or increasing MinJobAge."
            )
        elif min_job_age >= dynamic_check_threshold and status_command == "sacct":
            logger.warning(
                f"MinJobAge {min_job_age}s (>= {dynamic_check_threshold}s). "
                "'squeue' should work reliably for status queries."
            )


def validate_executor_settings(settings, logger=None):
    """
    Validate ExecutorSettings fields for correctness
    (better user feedback in case of wrong inputs)
    """
    # status_command: only allow known values
    if settings.status_command is not None:
        if settings.status_command not in {"sacct", "squeue"}:
            raise WorkflowError(
                "Invalid status command. Allowed values are 'sacct' or 'squeue'."
            )
    # status_attempts
    if settings.status_attempts is not None:
        if (
            not isinstance(settings.status_attempts, int)
            or settings.status_attempts < 1
        ):
            raise WorkflowError("status_attempts must be a positive integer")
    # init_seconds_before_status_checks
    if settings.init_seconds_before_status_checks is not None:
        if (
            not isinstance(settings.init_seconds_before_status_checks, int)
            or settings.init_seconds_before_status_checks < 1
        ):
            raise WorkflowError(
                "init-seconds-before-status-checks must be a positive integer."
            )
    # efficiency_threshold
    if settings.efficiency_threshold is not None:
        try:
            thr = float(settings.efficiency_threshold)
        except (TypeError, ValueError):
            raise WorkflowError(
                "efficiency-threshold must be a number in range (0, 1]."
            )
        if not (0 < thr <= 1.0):
            raise WorkflowError(
                "efficiency-threshold must be a number in range (0, 1]."
            )
    # partition_config
    if settings.partition_config is not None:
        p = Path(settings.partition_config)
        if not p.exists():
            raise WorkflowError(
                f"Partition configuration file not found, given was {p}."
            )
    # delete_logfiles_older_than
    if settings.delete_logfiles_older_than is not None:
        if not isinstance(settings.delete_logfiles_older_than, int):
            raise WorkflowError(
                "delete-logfiles-older-than must be an integer (days)."
            )
    # status_command warnings (optional logger)
    if logger:
        validate_status_command_settings(settings, logger)
