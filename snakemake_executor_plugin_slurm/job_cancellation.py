import shlex
import subprocess
from typing import List, Set

from snakemake_interface_executor_plugins.executors.base import (
    SubmittedJobInfo,
)
from snakemake_interface_common.exceptions import WorkflowError


def cancel_slurm_jobs(
    active_jobs: List[SubmittedJobInfo],
    submitted_job_clusters: Set[str],
    logger,
):
    """
    Cancel all active SLURM jobs.

    Args:
        active_jobs: List of submitted job info objects to cancel
        submitted_job_clusters: Set of cluster names that jobs were submitted to
        logger: Logger instance for warnings and errors

    Raises:
        WorkflowError: If scancel command fails
    """
    if active_jobs:
        # TODO chunk jobids in order to avoid too long command lines
        jobids = " ".join([job_info.external_jobid for job_info in active_jobs])

        try:
            # timeout set to 60, because a scheduler cycle usually is
            # about 30 sec, but can be longer in extreme cases.
            # Under 'normal' circumstances, 'scancel' is executed in
            # virtually no time.
            scancel_command = f"scancel {jobids}"

            # Adding the --clusters=all flag, if we submitted to more than one
            # cluster (assuming that choosing _a_ cluster is enough to fullfil
            # this criterion). Issue #397 mentions that this flag is not available
            # in older SLURM versions, but we assume that multicluster setups will
            # usually run on a recent version of SLURM.
            if submitted_job_clusters:
                scancel_command += " --clusters=all"

            scancel_command = shlex.split(scancel_command)

            subprocess.check_output(
                scancel_command,
                text=True,
                timeout=60,
                stderr=subprocess.PIPE,
            )
        except subprocess.TimeoutExpired:
            logger.warning("Unable to cancel jobs within a minute.")
        except subprocess.CalledProcessError as e:
            msg = e.stderr.strip()
            if msg:
                msg = f": {msg}"
            # If we were using --clusters and it failed, provide additional context
            if submitted_job_clusters:
                msg += (
                    "\nWARNING: Job cancellation failed while using "
                    "--clusters flag. Your multicluster SLURM setup may not "
                    "support this feature, or the SLURM database may not be "
                    "properly configured for multicluster operations. "
                    "Please verify your SLURM configuration with your "
                    "HPC administrator."
                )
            raise WorkflowError(
                "Unable to cancel jobs with scancel " f"(exit code {e.returncode}){msg}"
            ) from e
