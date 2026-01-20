__author__ = "David Lähnemann, Johannes Köster, Christian Meesters"
__copyright__ = "Copyright 2023, David Lähnemann, Johannes Köster, Christian Meesters"
__email__ = "johannes.koester@uni-due.de"
__license__ = "MIT"

import atexit
import csv
from io import StringIO
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Generator, Optional
import uuid

from snakemake_interface_executor_plugins.executors.base import (
    SubmittedJobInfo,
)
from snakemake_interface_executor_plugins.executors.remote import (
    RemoteExecutor,
)
from snakemake_interface_executor_plugins.settings import (
    ExecutorSettingsBase,
    CommonSettings,
)
from snakemake_interface_executor_plugins.jobs import (
    JobExecutorInterface,
)
from snakemake_interface_common.exceptions import WorkflowError

from .utils import (
    delete_slurm_environment,
    delete_empty_dirs,
    set_gres_string,
)
from .job_status_query import (
    get_min_job_age,
    is_query_tool_available,
    should_recommend_squeue_status_command,
    query_job_status_squeue,
    query_job_status_sacct,
)
from .efficiency_report import create_efficiency_report
from .submit_string import get_submit_command
from .partitions import read_partition_file, get_best_partition
from .validation import (
    validate_slurm_extra,
    validate_executor_settings,
    validate_status_command_settings,
)


def _get_status_command_default():
    """Get smart default for status_command based on cluster configuration."""
    sacct_available = is_query_tool_available("sacct")
    squeue_available = is_query_tool_available("squeue")
    # squeue is assumed to always be available on SLURM clusters

    is_slurm_available = shutil.which("sinfo") is not None
    if not is_slurm_available:
        return None

    if not squeue_available and not sacct_available:
        raise WorkflowError(
            "Neither 'sacct' nor 'squeue' commands are available on this "
            "system. At least one of these commands is required for job "
            "status queries."
        )
    if sacct_available:
        return "sacct"
    else:
        return "squeue"


def _get_status_command_help():
    """Get help text with computed default."""
    default_cmd = _get_status_command_default()

    # if SLURM is not available (should not occur, only
    # in 3rd party CI tests)
    if default_cmd is None:
        return (
            "Command to query job status. Options: 'sacct', 'squeue'. "
            "SLURM not detected on this system, so no status command can be used."
        )

    sacct_available = is_query_tool_available("sacct")
    squeue_recommended = should_recommend_squeue_status_command()

    base_help = "Command to query job status. Options: 'sacct', 'squeue'. "

    if default_cmd == "sacct":
        if sacct_available and not squeue_recommended:
            info = (
                "'sacct' detected and will be used "
                "(MinJobAge may be too low for reliable 'squeue' usage)"
            )
        else:
            info = "'sacct' detected and will be used"
    else:  # default_cmd == "squeue"
        if squeue_recommended:
            # cumbersome, due to black and the need to stay below 80 chars
            msg_part1 = "'squeue' recommended (MinJobAge is sufficient )"
            msg_part2 = " for reliable usage"
            info = msg_part1 + msg_part2
        elif not sacct_available:
            info = (
                "'sacct' not available, falling back to 'squeue'. "
                "WARNING: 'squeue' may not work reliably if MinJobAge is "
                "too low"
            )
        else:
            info = (
                "'squeue' will be used. "
                "WARNING: MinJobAge may be too low for reliable 'squeue' usage"
            )

    return (
        f"{base_help}Default: '{default_cmd}' ({info}). "
        f"Set explicitly to override auto-detection."
    )


@dataclass
class ExecutorSettings(ExecutorSettingsBase):
    """Settings for the SLURM executor plugin."""

    logdir: Optional[Path] = field(
        default=None,
        metadata={
            "help": "Per default the SLURM log directory is relative to "
            "the working directory. "
            "This flag allows to set an alternative directory.",
            "env_var": False,
            "required": False,
        },
    )

    keep_successful_logs: bool = field(
        default=False,
        metadata={
            "help": "Per default SLURM log files will be deleted upon "
            "successful completion of a job. Whenever a SLURM job fails, "
            "its log file will be preserved. "
            "This flag allows to keep all SLURM log files, even those "
            "of successful jobs.",
            "env_var": False,
            "required": False,
        },
    )

    delete_logfiles_older_than: Optional[int] = field(
        default=10,
        metadata={
            "help": "Per default SLURM log files in the SLURM log directory "
            "of a workflow will be deleted after 10 days. For this, "
            "best leave the default log directory unaltered. "
            "Setting this flag allows to change this behaviour. "
            "If set to <=0, no old files will be deleted.",
        },
    )

    init_seconds_before_status_checks: Optional[int] = field(
        default=40,
        metadata={
            "help": "Defines the time in seconds before the first status "
            "check is performed on submitted jobs. Must be a positive "
            "integer",
        },
    )

    requeue: bool = field(
        default=False,
        metadata={
            "help": "Requeue jobs if they fail with exit code != 0, "
            "if no cluster default. Results in "
            "`sbatch ... --requeue ...` "
            "This flag has no effect, if not set.",
            "env_var": False,
            "required": False,
        },
    )

    no_account: bool = field(
        default=False,
        metadata={
            "help": "Do not use any account for submission. "
            "This flag has no effect, if not set.",
            "env_var": False,
            "required": False,
        },
    )
    partition_config: Optional[Path] = field(
        default=None,
        metadata={
            "help": "Path to YAML file defining partition limits for dynamic "
            "partition selection. When provided, jobs will be dynamically "
            "assigned to the best-fitting partition based on their resource "
            "requirements. See documentation for complete list of available limits. "
            "Alternatively, the environment variable SNAKEMAKE_SLURM_PARTITIONS "
            "can be set to point to such a file. "
            "If both are set, this flag takes precedence.",
            "env_var": False,
            "required": False,
        },
    )
    efficiency_report: bool = field(
        default=False,
        metadata={
            "help": (
                "Generate an efficiency report at the end of the workflow. "
                "This flag has no effect, if not set."
            ),
            "env_var": False,
            "required": False,
        },
    )

    efficiency_report_path: Optional[Path] = field(
        default=None,
        metadata={
            "help": "Path to the efficiency report file. "
            "If not set, the report will be written to "
            "the current working directory with the name "
            "'efficiency_report_<run_uuid>.csv'. "
            "This flag has no effect, if not set.",
            "env_var": False,
            "required": False,
        },
    )

    efficiency_threshold: Optional[float] = field(
        default=0.8,
        metadata={
            "help": "Threshold for efficiency report. "
            "Jobs with efficiency below this threshold will be reported.",
            "env_var": False,
            "required": False,
        },
    )

    status_command: Optional[str] = field(
        default_factory=_get_status_command_default,
        metadata={
            "help": _get_status_command_help(),
            "env_var": False,
            "required": False,
        },
    )

    status_attempts: Optional[int] = field(
        default=5,
        metadata={
            "help": "Defines the number of attempts to query the status of "
            "all active jobs. If the status query fails, the next attempt "
            "will be performed after the next status check interval. "
            "The default is 5 status attempts before giving up. The maximum "
            "time between status checks is 180 seconds.",
            "env_var": False,
            "required": False,
        },
    )

    qos: Optional[str] = field(
        default=None,
        metadata={
            "help": "If set, the given QoS will be used for job submission.",
            "env_var": False,
            "required": False,
        },
    )

    reservation: Optional[str] = field(
        default=None,
        metadata={
            "help": ("If set, the given reservation will be used for job submission."),
            "env_var": False,
            "required": False,
        },
    )

    pass_command_as_script: bool = field(
        default=False,
        metadata={
            "help": (
                "Pass to sbatch and srun the command to be executed as a shell script"
                " (fed through stdin) instead of wrapping it in the command line "
                "call. Useful when a limit exists on SLURM command line length (ie. "
                "max_submit_line_size)."
            ),
            "env_var": False,
            "required": False,
        },
    )

    def __post_init__(self):
        """Validate settings after initialization."""
        validate_executor_settings(self)


# Required:
# Specify common settings shared by various executors.
common_settings = CommonSettings(
    # define whether your executor plugin executes locally
    # or remotely. In virtually all cases, it will be remote execution
    # (cluster, cloud, etc.). Only Snakemake's standard execution
    # plugins (snakemake-executor-plugin-dryrun,
    #          snakemake-executor-plugin-local)
    # are expected to specify False here.
    non_local_exec=True,
    # Define whether your executor plugin implies that there is no shared
    # filesystem (True) or not (False).
    # This is e.g. the case for cloud execution.
    implies_no_shared_fs=False,
    job_deploy_sources=False,
    pass_default_storage_provider_args=True,
    pass_default_resources_args=True,
    pass_envvar_declarations_to_cmd=False,
    auto_deploy_default_storage_provider=False,
)


# Required:
# Implementation of your executor
class Executor(RemoteExecutor):
    def __post_init__(self, test_mode: bool = False):
        # run check whether we are running in a SLURM job context
        self.warn_on_jobcontext()
        self.test_mode = test_mode
        self.run_uuid = str(uuid.uuid4())
        self.logger.info(f"SLURM run ID: {self.run_uuid}")
        self._fallback_account_arg = None
        self._fallback_partition = None
        self._preemption_warning = False  # no preemption warning has been issued
        self.slurm_logdir = (
            Path(self.workflow.executor_settings.logdir)
            if self.workflow.executor_settings.logdir
            else Path(".snakemake/slurm_logs").resolve()
        )
        # Check the environment variable "SNAKEMAKE_SLURM_PARTITIONS",
        # if set, read the partitions from the given file. Let the CLI
        # option override this behavior.
        if (
            os.getenv("SNAKEMAKE_SLURM_PARTITIONS")
            and not self.workflow.executor_settings.partition_config
        ):
            partition_file = Path(os.getenv("SNAKEMAKE_SLURM_PARTITIONS"))
            self.logger.info(
                f"Reading SLURM partition configuration from "
                f"environment variable file: {partition_file}"
            )
            self._partitions = read_partition_file(partition_file)
        else:
            self._partitions = (
                read_partition_file(self.workflow.executor_settings.partition_config)
                if self.workflow.executor_settings.partition_config
                else None
            )
        atexit.register(self.clean_old_logs)
        # moved validation to validation.py
        validate_status_command_settings(self.workflow.executor_settings, self.logger)

    def get_status_command(self):
        """Get the status command to use, with fallback logic."""
        if hasattr(self.workflow.executor_settings, "status_command"):
            return self.workflow.executor_settings.status_command
        else:
            # Fallback: determine the best command based on
            # cluster configuration
            return _get_status_command_default()

    def shutdown(self) -> None:
        """
        Shutdown the executor.
        This method is overloaded, to include the cleaning of old log files
        and to optionally create an efficiency report.
        """
        # First, we invoke the original shutdown method
        super().shutdown()

        # Next, clean up old log files, unconditionally.
        self.clean_old_logs()
        # If the efficiency report is enabled, create it.
        if self.workflow.executor_settings.efficiency_report:
            threshold = self.workflow.executor_settings.efficiency_threshold
            report_path = self.workflow.executor_settings.efficiency_report_path
            create_efficiency_report(
                e_threshold=threshold,
                run_uuid=self.run_uuid,
                e_report_path=report_path,
                logger=self.logger,
            )

    def clean_old_logs(self) -> None:
        """
        Delete files older than specified age from the SLURM log directory.
        """
        # shorthands:
        age_cutoff = self.workflow.executor_settings.delete_logfiles_older_than
        keep_all = self.workflow.executor_settings.keep_successful_logs
        if age_cutoff <= 0 or keep_all:
            return
        cutoff_secs = age_cutoff * 86400
        current_time = time.time()
        self.logger.info(
            f"Cleaning up SLURM log files older than {age_cutoff} day(s)."
        )

        for path in self.slurm_logdir.rglob("*.log"):
            if path.is_file():
                try:
                    file_age = current_time - path.stat().st_mtime
                    if file_age > cutoff_secs:
                        path.unlink()
                except (OSError, FileNotFoundError) as e:
                    self.logger.error(f"Could not delete logfile {path}: {e}")
        # we need a 2nd iteration to remove putatively empty directories
        try:
            delete_empty_dirs(self.slurm_logdir)
        except (OSError, FileNotFoundError) as e:
            self.logger.error(
                f"Could not delete empty directories in {self.slurm_logdir}: {e}"
            )

    def warn_on_jobcontext(self, done=None):
        if not done:
            if "SLURM_JOB_ID" in os.environ:
                self.logger.warning(
                    "You are running snakemake in a SLURM job context. "
                    "This is not recommended, as it may lead to unexpected "
                    "behavior. "
                    "If possible, please run Snakemake directly on the "
                    "login node."
                )
                time.sleep(5)
                delete_slurm_environment()
        done = True

    def additional_general_args(self):
        general_args = "--executor slurm-jobstep --jobs 1"
        if self.workflow.executor_settings.pass_command_as_script:
            general_args += " --slurm-jobstep-pass-command-as-script"
        return general_args

    def run_job(self, job: JobExecutorInterface):
        # Implement here how to run a job.
        # You can access the job's resources, etc.
        # via the job object.
        # After submitting the job, you have to call
        # self.report_job_submission(job_info).
        # with job_info being of type
        # snakemake_interface_executor_plugins.executors.base.SubmittedJobInfo.

        group_or_rule = f"group_{job.name}" if job.is_group() else f"rule_{job.name}"

        try:
            wildcard_str = (
                "_".join(job.wildcards).replace("/", "_") if job.wildcards else ""
            )
        except AttributeError:
            wildcard_str = ""

        self.slurm_logdir.mkdir(parents=True, exist_ok=True)
        slurm_logfile = self.slurm_logdir / group_or_rule / wildcard_str / "%j.log"
        slurm_logfile.parent.mkdir(parents=True, exist_ok=True)
        # this behavior has been fixed in slurm 23.02, but there might be
        # plenty of older versions around, hence we should rather be
        # conservative here.
        assert "%j" not in str(self.slurm_logdir), (
            "bug: jobid placeholder in parent dir of logfile. This does not "
            "work as we have to create that dir before submission in order to "
            "make sbatch happy. Otherwise we get silent fails without "
            "logfiles being created."
        )

        # generic part of a submission string:
        # we use a run_uuid as the job-name, to allow `--name`-based
        # filtering in the job status checks (`sacct --name` and
        # `squeue --name`)
        if wildcard_str == "":
            comment_str = f"rule_{job.name}"
        else:
            comment_str = f"rule_{job.name}_wildcards_{wildcard_str}"
        # check whether the 'slurm_extra' parameter is used correctly
        # prior to putatively setting in the sbatch call
        if job.resources.get("slurm_extra"):
            self.check_slurm_extra(job)

        # NOTE removed partition from below, such that partition
        # selection can benefit from resource checking as the call is built up.
        job_params = {
            "run_uuid": self.run_uuid,
            "slurm_logfile": slurm_logfile,
            "comment_str": comment_str,
            "account": next(self.get_account_arg(job)),
            "partition": self.get_partition_arg(job),
            "workdir": self.workflow.workdir_init,
        }

        call = get_submit_command(job, job_params)

        if self.workflow.executor_settings.requeue:
            call += " --requeue"

        if self.workflow.executor_settings.qos:
            call += f" --qos={self.workflow.executor_settings.qos}"

        if self.workflow.executor_settings.reservation:
            call += f" --reservation={self.workflow.executor_settings.reservation}"

        call += set_gres_string(job)

        if not job.resources.get("runtime"):
            self.logger.warning(
                "No wall time information given. This might or might not "
                "work on your cluster. "
                "If not, specify the resource runtime in your rule or as "
                "a reasonable default via --default-resources."
            )

        if not job.resources.get("mem_mb_per_cpu") and not job.resources.get("mem_mb"):
            self.logger.warning(
                "No job memory information ('mem_mb' or 'mem_mb_per_cpu') is "
                "given - submitting without. This might or might not work on "
                "your cluster."
            )

        exec_job = self.format_job_exec(job)

        if not self.workflow.executor_settings.pass_command_as_script:
            # and finally wrap the job to execute with all the snakemake parameters
            call += f' --wrap="{exec_job}"'
            subprocess_stdin = None
        else:
            # format the job to execute with all the snakemake parameters into a script
            sbatch_script = "\n".join(["#!/bin/sh", exec_job])
            self.logger.debug(f"sbatch script:\n{sbatch_script}")
            # feed the shell script to sbatch via stdin
            call += " /dev/stdin"
            subprocess_stdin = sbatch_script

        self.logger.debug(f"sbatch call: {call}")
        try:
            process = subprocess.Popen(
                call,
                shell=True,
                text=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            out, err = process.communicate(
                input=subprocess_stdin  # feed the sbatch shell script through stdin
            )
            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode, call, output=err
                )
        except subprocess.CalledProcessError as e:
            self.report_job_error(
                SubmittedJobInfo(job),
                msg=(
                    "SLURM sbatch failed. "
                    f"The error message was '{e.output.strip()}'.\n"
                    f"    sbatch call:\n        {call}\n"
                    + (
                        f"    sbatch script:\n{sbatch_script}\n"
                        if subprocess_stdin is not None
                        else ""
                    )
                ),
            )
            return
        # any other error message indicating failure?
        if "submission failed" in err:
            raise WorkflowError(
                f"SLURM job submission failed. The error message was {err}"
            )

        # multicluster submissions yield submission infos like
        # "Submitted batch job <id> on cluster <name>" by default, but with the
        # --parsable option it simply yields "<id>;<name>".
        # To extract the job id we split by semicolon and take the first
        # element (this also works if no cluster name was provided)
        slurm_jobid = out.strip().split(";")[0]
        if not slurm_jobid:
            raise WorkflowError("Failed to retrieve SLURM job ID from sbatch output.")
        slurm_logfile = slurm_logfile.with_name(
            slurm_logfile.name.replace("%j", slurm_jobid)
        )
        self.logger.info(
            f"Job {job.jobid} has been submitted with SLURM jobid "
            f"{slurm_jobid} (log: {slurm_logfile})."
        )
        self.report_job_submission(
            SubmittedJobInfo(
                job,
                external_jobid=slurm_jobid,
                aux={"slurm_logfile": slurm_logfile},
            )
        )

    async def check_active_jobs(
        self, active_jobs: List[SubmittedJobInfo]
    ) -> Generator[SubmittedJobInfo, None, None]:
        # Check the status of active jobs.
        # You have to iterate over the given list active_jobs.
        # For jobs that have finished successfully, you have to call
        # self.report_job_success(job).
        # For jobs that have errored, you have to call
        # self.report_job_error(job).
        # Jobs that are still running have to be yielded.
        #
        # For queries to the remote middleware, please use
        # self.status_rate_limiter like this:
        #
        # async with self.status_rate_limiter:
        #    # query remote middleware here
        fail_stati = (
            "BOOT_FAIL",
            "CANCELLED",
            "DEADLINE",
            "FAILED",
            "NODE_FAIL",
            "OUT_OF_MEMORY",
            "TIMEOUT",
            "ERROR",
        )
        # Cap sleeping time between querying the status of all active jobs:
        # If `AccountingStorageType`` for `sacct` is set to
        # `accounting_storage/none`, `sacct` will query `slurmctld` (instead
        # of `slurmdbd`) and this in turn can rely on default config,
        # see: https://stackoverflow.com/a/46667605
        # This config defaults to `MinJobAge=300`, which implies that jobs will
        # be removed from `slurmctld` within 6 minutes of finishing. So we're
        # conservative here, with half that time.
        max_sleep_time = 180

        sacct_query_durations = []

        initial_interval = getattr(
            self.workflow.executor_settings,
            "init_seconds_before_status_checks",
            40,
        )
        # Fast path: if there are no active jobs, skip querying
        if not active_jobs:
            self.next_seconds_between_status_checks = initial_interval
            self.logger.debug("No active jobs; skipping status query.")
            return

        status_attempts = self.workflow.executor_settings.status_attempts
        self.logger.debug(
            f"Checking the status of {len(active_jobs)} active jobs "
            f"with {status_attempts} attempts."
        )

        active_jobs_ids = {job_info.external_jobid for job_info in active_jobs}
        active_jobs_seen_by_sacct = set()
        missing_sacct_status = set()

        # decide which status command to use
        status_command_name = self.get_status_command()
        min_job_age = get_min_job_age()
        dynamic_check_threshold = 3 * initial_interval
        if status_command_name == "squeue":
            if (
                min_job_age is None or min_job_age < dynamic_check_threshold
            ) and is_query_tool_available("sacct"):
                self.logger.info(
                    "Falling back to 'sacct' for status queries "
                    f"(MinJobAge={min_job_age}; threshold={dynamic_check_threshold}s)."
                )
                status_command_name = "sacct"
        if status_command_name == "sacct" and not is_query_tool_available("sacct"):
            self.logger.info("'sacct' unavailable, using 'squeue' for status queries.")
            status_command_name = "squeue"
        if status_command_name == "sacct":
            status_command = query_job_status_sacct(self.run_uuid)
        else:
            status_command = query_job_status_squeue(self.run_uuid)

        # this code is inspired by the snakemake profile:
        # https://github.com/Snakemake-Profiles/slurm
        for i in range(status_attempts):
            async with self.status_rate_limiter:
                (status_of_jobs, sacct_query_duration) = await self.job_stati(
                    status_command
                )
                if status_of_jobs is None and sacct_query_duration is None:
                    self.logger.debug(f"could not check status of job {self.run_uuid}")
                    continue
                sacct_query_durations.append(sacct_query_duration)
                self.logger.debug(f"status_of_jobs after sacct is: {status_of_jobs}")
                # only take jobs that are still active
                active_jobs_ids_with_current_sacct_status = (
                    set(status_of_jobs.keys()) & active_jobs_ids
                )
                self.logger.debug(
                    f"active_jobs_ids_with_current_sacct_status are: "
                    f"{active_jobs_ids_with_current_sacct_status}"
                )
                active_jobs_seen_by_sacct = (
                    active_jobs_seen_by_sacct
                    | active_jobs_ids_with_current_sacct_status
                )
                self.logger.debug(
                    "active_jobs_seen_by_sacct are: " f"{active_jobs_seen_by_sacct}"
                )
                missing_sacct_status = (
                    active_jobs_seen_by_sacct
                    - active_jobs_ids_with_current_sacct_status
                )
                self.logger.debug(f"missing_sacct_status are: {missing_sacct_status}")
                if not missing_sacct_status:
                    break

        if missing_sacct_status:
            self.logger.warning(
                "Unable to get the status of all active jobs that should be "
                f"in slurmdbd, even after {status_attempts} attempts.\n"
                "The jobs with the following slurm job ids were previously "
                " seen by sacct, but sacct doesn't report them any more:\n"
                f"{missing_sacct_status}\n"
                "Please double-check with your slurm cluster administrator, "
                "that slurmdbd job accounting is properly set up.\n"
            )

        if status_of_jobs is not None:
            any_finished = False
            for j in active_jobs:
                # the job probably didn't make it into slurmdbd yet, so
                # `sacct` doesn't return it
                if j.external_jobid not in status_of_jobs:
                    # but the job should still be queueing or running and
                    # appear in slurmdbd (and thus `sacct` output) later
                    yield j
                    continue
                status = status_of_jobs[j.external_jobid]
                if status == "COMPLETED":
                    self.report_job_success(j)
                    any_finished = True
                    active_jobs_seen_by_sacct.remove(j.external_jobid)
                    if not self.workflow.executor_settings.keep_successful_logs:
                        self.logger.debug(
                            "removing SLURM log for successful job "
                            f"with SLURM ID '{j.external_jobid}'"
                        )
                        try:
                            if j.aux["slurm_logfile"].exists():
                                j.aux["slurm_logfile"].unlink()
                        except (OSError, FileNotFoundError) as e:
                            self.logger.warning(
                                "Could not remove SLURM log file"
                                f" {j.aux['slurm_logfile']}: {e}"
                            )
                elif status == "PREEMPTED" and not self._preemption_warning:
                    self._preemption_warning = True
                    self.logger.warning(
                        """
===== A Job preemption  occured! =====
Leave Snakemake running, if possible. Otherwise Snakemake
needs to restart this job upon a Snakemake restart.

We leave it to SLURM to resume your job(s)"""
                    )
                    yield j
                elif status == "UNKNOWN":
                    # the job probably does not exist anymore, but 'sacct' did not work
                    # so we assume it is finished
                    self.report_job_success(j)
                    any_finished = True
                    active_jobs_seen_by_sacct.remove(j.external_jobid)
                elif status in fail_stati:
                    msg = (
                        f"SLURM-job '{j.external_jobid}' failed, SLURM status is: "
                        # message ends with '. ', because it is proceeded
                        # with a new sentence
                        f"'{status}'. "
                    )
                    self.report_job_error(
                        j, msg=msg, aux_logs=[j.aux["slurm_logfile"]._str]
                    )
                    active_jobs_seen_by_sacct.remove(j.external_jobid)
                else:  # still running?
                    yield j

            if not any_finished:
                self.next_seconds_between_status_checks = min(
                    self.next_seconds_between_status_checks + 10,
                    max_sleep_time,
                )
            else:
                self.next_seconds_between_status_checks = initial_interval

    def cancel_jobs(self, active_jobs: List[SubmittedJobInfo]):
        # Cancel all active jobs.
        # This method is called when Snakemake is interrupted.
        if active_jobs:
            # TODO chunk jobids in order to avoid too long command lines
            jobids = " ".join([job_info.external_jobid for job_info in active_jobs])
            try:
                # timeout set to 60, because a scheduler cycle usually is
                # about 30 sec, but can be longer in extreme cases.
                # Under 'normal' circumstances, 'scancel' is executed in
                # virtually no time.
                scancel_command = f"scancel {jobids} --clusters=all"

                subprocess.check_output(
                    scancel_command,
                    text=True,
                    shell=True,
                    timeout=60,
                    stderr=subprocess.PIPE,
                )
            except subprocess.TimeoutExpired:
                self.logger.warning("Unable to cancel jobs within a minute.")
            except subprocess.CalledProcessError as e:
                msg = e.stderr.strip()
                if msg:
                    msg = f": {msg}"
                raise WorkflowError(
                    "Unable to cancel jobs with scancel "
                    f"(exit code {e.returncode}){msg}"
                ) from e

    async def job_stati(self, command):
        """Obtain SLURM job status of all submitted jobs with sacct

        Keyword arguments:
        command -- a slurm command that returns one line for each job with:
                   "<raw/main_job_id>|<long_status_string>"
        """
        res = query_duration = None
        try:
            time_before_query = time.time()
            command_res = subprocess.check_output(
                command, text=True, shell=True, stderr=subprocess.PIPE
            )
            query_duration = time.time() - time_before_query
            self.logger.debug(
                f"The job status was queried with command: {command}\n"
                f"It took: {query_duration} seconds\n"
                f"The output is:\n'{command_res}'\n"
            )
            res = {
                # We split the second field in the output, as the State field
                # could contain info beyond the JOB STATE CODE according to:
                # https://slurm.schedmd.com/sacct.html#OPT_State
                entry[0]: entry[1].split(sep=None, maxsplit=1)[0]
                for entry in csv.reader(StringIO(command_res), delimiter="|")
            }
        except subprocess.CalledProcessError as e:
            error_message = e.stderr.strip()
            if "slurm_persist_conn_open_without_init" in error_message:
                self.logger.warning(
                    "The SLURM database might not be available ... "
                    f"Error message: '{error_message}'"
                    "This error message indicates that the SLURM database is "
                    "currently not available. This is not an error of the "
                    "Snakemake plugin, but some kind of server issue. "
                    "Please consult with your HPC provider."
                )
            else:
                self.logger.error(
                    f"The job status query failed with command '{command}'"
                    f"Error message: '{error_message}'"
                    "This error message is not expected, please report it back to us."
                )
            pass

        return (res, query_duration)

    def get_account_arg(self, job: JobExecutorInterface):
        """
        checks whether the desired account is valid,
        returns a default account, if applicable
        else raises an error - implicetly.
        """
        if job.resources.get("slurm_account"):
            # split the account upon ',' and whitespace, to allow
            # multiple accounts being given
            accounts = [
                a for a in re.split(r"[,\s]+", job.resources.slurm_account) if a
            ]
            for account in accounts:
                # here, we check whether the given or guessed account is valid
                # if not, a WorkflowError is raised
                self.test_account(account)
            # sbatch only allows one account per submission
            # yield one after the other, if multiple were given
            # we have to quote the account, because it might
            # contain build-in shell commands - see issue #354
            for account in accounts:
                self.test_account(account)
                yield f" -A {shlex.quote(account)}"
        else:
            if self._fallback_account_arg is None:
                self.logger.warning("No SLURM account given, trying to guess.")
                account = self.get_account()
                if account:
                    self.logger.warning(f"Guessed SLURM account: {account}")
                    self.test_account(f"{account}")
                    self._fallback_account_arg = f" -A {shlex.quote(account)}"
                else:
                    self.logger.warning(
                        "Unable to guess SLURM account. Trying to proceed without."
                    )
                    self._fallback_account_arg = (
                        ""  # no account specific args for sbatch
                    )
            yield self._fallback_account_arg

    def get_partition_arg(self, job: JobExecutorInterface):
        """
        checks whether the desired partition is valid,
        returns a default partition, if applicable
        else raises an error - implicetly.
        """
        partition = None

        # Check if a specific partition is requested
        if job.resources.get("slurm_partition"):
            # But also check if there's a cluster requirement that might override it
            job_cluster = (
                job.resources.get("slurm_cluster")
                or job.resources.get("cluster")
                or job.resources.get("clusters")
            )

            if job_cluster and self._partitions:
                # If a cluster is specified, verify the partition exists and matches
                # Otherwise, use auto-selection to find a partition for that cluster
                partition_obj = next(
                    (
                        p
                        for p in self._partitions
                        if p.name == job.resources.slurm_partition
                    ),
                    None,
                )
                if (
                    partition_obj
                    and partition_obj.partition_cluster
                    and partition_obj.partition_cluster != job_cluster
                ):
                    # Partition exists but is for a different cluster:
                    # use auto-selection
                    partition = get_best_partition(self._partitions, job, self.logger)
                else:
                    partition = job.resources.slurm_partition
            else:
                partition = job.resources.slurm_partition

        # If no partition was selected yet, try auto-selection
        if not partition and self._partitions:
            partition = get_best_partition(self._partitions, job, self.logger)

        # we didnt get a partition yet so try fallback.
        if not partition:
            if self._fallback_partition is None:
                self._fallback_partition = self.get_default_partition(job)
            partition = self._fallback_partition
        if partition:
            # we have to quote the partition, because it might
            # contain build-in shell commands
            # string conversion needed for partition if partition is an integer
            return f" -p {shlex.quote(str(partition))}"
        else:
            return ""

    def get_account(self):
        """
        tries to deduce the acccount from recent jobs,
        returns None, if none is found
        """
        cmd = f'sacct -nu "{os.environ["USER"]}" -o Account%256 | tail -1'
        try:
            sacct_out = subprocess.check_output(
                cmd, shell=True, text=True, stderr=subprocess.PIPE
            )
            possible_account = sacct_out.replace("(null)", "").strip()
            if possible_account == "none":  # some clusters may not use an account
                return None
        except subprocess.CalledProcessError as e:
            self.logger.warning(
                f"No account was given, not able to get a SLURM account via sacct: "
                f"{e.stderr}"
            )
            return None

    def test_account(self, account):
        """
        tests whether the given account is registered, raises an error, if not
        """
        # first we need to test with sacctmgr because sshare might not
        # work in a multicluster environment
        cmd = f'sacctmgr -n -s list user "{os.environ["USER"]}" format=account%256'
        sacctmgr_report = sshare_report = ""
        try:
            accounts = subprocess.check_output(
                cmd, shell=True, text=True, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            sacctmgr_report = (
                "Unable to test the validity of the given or guessed"
                f" SLURM account '{account}' with sacctmgr: {e.stderr}."
            )
            accounts = ""

        if not accounts.strip():
            cmd = "sshare -U --format Account%256 --noheader"
            try:
                accounts = subprocess.check_output(
                    cmd, shell=True, text=True, stderr=subprocess.PIPE
                )
            except subprocess.CalledProcessError as e:
                sshare_report = (
                    "Unable to test the validity of the given or guessed "
                    f"SLURM account '{account}' with sshare: {e.stderr}."
                )
                raise WorkflowError(
                    f"The 'sacctmgr' reported: '{sacctmgr_report}' "
                    f"and likewise 'sshare' reported: '{sshare_report}'."
                )

        # The set() has been introduced during review to eliminate
        # duplicates. They are not harmful, but disturbing to read.
        accounts = set(_.strip() for _ in accounts.split("\n") if _)

        if not accounts:
            self.logger.warning(
                f"Both 'sacctmgr' and 'sshare' returned empty results for account "
                f"'{account}'. Proceeding without account validation."
            )
            return ""

        if account.lower() not in accounts:
            raise WorkflowError(
                f"The given account {account} appears to be invalid. Available "
                f"accounts:\n{', '.join(accounts)}"
            )

    def get_default_partition(self, job):
        """
        if no partition is given, checks whether a fallback onto a default
        partition is possible
        """
        try:
            out = subprocess.check_output(
                r"sinfo -o %P", shell=True, text=True, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            raise WorkflowError(
                f"Failed to run sinfo for retrieval of cluster partitions: {e.stderr}"
            )
        for partition in out.split():
            # A default partition is marked with an asterisk, but this is not part of
            # the name.
            if "*" in partition:
                # the decode-call is necessary, because the output of sinfo is bytes
                return partition.replace("*", "")
        self.logger.warning(
            f"No partition was given for rule '{job}', and unable to find "
            "a default partition."
            " Trying to submit without partition information."
            " You may want to invoke snakemake with --default-resources "
            "'slurm_partition=<your default partition>'."
        )
        return ""

    def check_slurm_extra(self, job):
        """Validate that slurm_extra doesn't contain executor-managed options."""
        validate_slurm_extra(job)
