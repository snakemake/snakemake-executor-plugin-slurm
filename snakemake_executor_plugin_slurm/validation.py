"""
SLURM parameter validation functions for the Snakemake executor plugin.
"""

import re
from pathlib import Path
from snakemake_interface_common.exceptions import WorkflowError
from .job_status_query import get_min_job_age, is_query_tool_available


def validate_or_get_slurm_job_id(job_id, output):
    """
    Validate that the SLURM job ID is a positive integer.

    Args:
        job_id (str): The SLURM job ID to validate.
        output (str): The full sbatch output to parse if job_id is invalid.

    Raises:
        WorkflowError: If the job ID is not a positive integer or we cannot
                       determine a valid job ID from the given input string.
    """
    # this regex just matches a positive integer
    # strict validation would require to check for a JOBID with either
    # the SLURM database or control daemon. This is too much overhead.
    if re.match(r"^\d+$", job_id):
        return job_id
    else:
        # Try matching a positive integer, raise an error if more than one match or
        # no match found. Match standalone integers, excluding those followed by %,
        # letters, or digits (units/percentages/floats). Allows format: "1234" or
        # "1234; clustername" (SLURM multi-cluster format).

        # If the first attempt to validate the job fails, try parsing the sbatch output
        # a bit more sophisticatedly.
        # The regex below matches standalone positive integers with a word boundary
        # before the number. The number must NOT be:
        # - Part of a decimal number (neither before nor after the dot)
        # - Followed by a percent sign with optional space (23% or 23 %)
        # - Followed by units/counts with optional space:
        #   * Memory units: k, K, m, M, g, G, kiB, KiB, miB, MiB, giB, GiB
        #   * Resource counts: files, cores, hours, cpus/CPUs (case-insensitive)
        #   * minutes are excluded, because of the match to 'm' for Megabytes
        #   Units must be followed by whitespace, hyphen, period, or end of string
        # Use negative lookbehind to exclude digits after a dot, and negative lookahead
        # to exclude digits before a dot or followed by units/percent
        matches = re.findall(
            r"(?<![.\d])\d+(?![.\d]|\s*%|\s*(?:[kKmMgG](?:iB)?|files|cores|"
            r"hours|[cC][pP][uU][sS]?)(?:\s|[-.]|$))",
            output,
        )
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            raise WorkflowError(
                f"Multiple possible SLURM job IDs found in: {output}. "
                "Was looking for exactly one positive integer."
            )
        elif not matches:
            raise WorkflowError(
                f"No valid SLURM job ID found in: {output}. "
                "Was looking for exactly one positive integer. "
                "We tried our best to parse the sbatch output, but it appears "
                "too convoluted. Please run 'sbatch' manually and report the output "
                "to us. If the output is garbled, inform your cluster administrators."
            )


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
            raise WorkflowError("delete-logfiles-older-than must be an integer (days).")
    # status_command warnings (optional logger)
    if logger:
        validate_status_command_settings(settings, logger)
