"""
SLURM parameter validation functions for the Snakemake executor plugin.
"""

import re
from snakemake_interface_common.exceptions import WorkflowError


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
