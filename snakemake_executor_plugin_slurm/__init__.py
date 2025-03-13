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
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Generator, Optional
import uuid
from snakemake_interface_executor_plugins.executors.base import SubmittedJobInfo
from snakemake_interface_executor_plugins.executors.remote import RemoteExecutor
from snakemake_interface_executor_plugins.settings import (
    ExecutorSettingsBase,
    CommonSettings,
)
from snakemake_interface_executor_plugins.jobs import (
    JobExecutorInterface,
)
from snakemake_interface_common.exceptions import WorkflowError
from snakemake_executor_plugin_slurm_jobstep import get_cpu_setting

from .utils import delete_slurm_environment, delete_empty_dirs, set_gres_string


@dataclass
class ExecutorSettings(ExecutorSettingsBase):
    logdir: Optional[Path] = field(
        default=None,
        metadata={
            "help": "Per default the SLURM log directory is relative to "
            "the working directory."
            "This flag allows to set an alternative directory.",
            "env_var": False,
            "required": False,
        },
    )
    keep_successful_logs: bool = field(
        default=False,
        metadata={
            "help": "Per default SLURM log files will be deleted upon sucessful "
            "completion of a job. Whenever a SLURM job fails, its log "
            "file will be preserved. "
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
            "If set to <=0, no old files will be deleted. ",
        },
    )
    init_seconds_before_status_checks: Optional[int] = field(
        default=40,
        metadata={
            "help": "Defines the time in seconds before the first status "
            "check is performed after job submission.",
            "env_var": False,
            "required": False,
        },
    )
    requeue: bool = field(
        default=False,
        metadata={
            "help": "Allow requeuing preempted of failed jobs, "
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


# Required:
# Specify common settings shared by various executors.
common_settings = CommonSettings(
    # define whether your executor plugin executes locally
    # or remotely. In virtually all cases, it will be remote execution
    # (cluster, cloud, etc.). Only Snakemake's standard execution
    # plugins (snakemake-executor-plugin-dryrun, snakemake-executor-plugin-local)
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
    # wait a bit until slurmdbd has job info available
    init_seconds_before_status_checks=40,
    pass_group_args=True,
)


# Required:
# Implementation of your executor
class Executor(RemoteExecutor):
    def __post_init__(self):
        # run check whether we are running in a SLURM job context
        self.warn_on_jobcontext()
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
        atexit.register(self.clean_old_logs)

    def clean_old_logs(self) -> None:
        """Delete files older than specified age from the SLURM log directory."""
        # shorthands:
        age_cutoff = self.workflow.executor_settings.delete_logfiles_older_than
        keep_all = self.workflow.executor_settings.keep_successful_logs
        if age_cutoff <= 0 or keep_all:
            return
        cutoff_secs = age_cutoff * 86400
        current_time = time.time()
        self.logger.info(f"Cleaning up log files older than {age_cutoff} day(s)")
        for path in self.slurm_logdir.rglob("*.log"):
            if path.is_file():
                try:
                    file_age = current_time - path.stat().st_mtime
                    if file_age > cutoff_secs:
                        path.unlink()
                except (OSError, FileNotFoundError) as e:
                    self.logger.warning(f"Could not delete logfile {path}: {e}")
        # we need a 2nd iteration to remove putatively empty directories
        try:
            delete_empty_dirs(self.slurm_logdir)
        except (OSError, FileNotFoundError) as e:
            self.logger.warning(f"Could not delete empty directory {path}: {e}")

    def warn_on_jobcontext(self, done=None):
        if not done:
            if "SLURM_JOB_ID" in os.environ:
                self.logger.warning(
                    "You are running snakemake in a SLURM job context. "
                    "This is not recommended, as it may lead to unexpected behavior. "
                    "Please run Snakemake directly on the login node."
                )
                time.sleep(5)
                delete_slurm_environment()
        done = True

    def additional_general_args(self):
        return "--executor slurm-jobstep --jobs 1"

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
        # this behavior has been fixed in slurm 23.02, but there might be plenty of
        # older versions around, hence we should rather be conservative here.
        assert "%j" not in str(self.slurm_logdir), (
            "bug: jobid placeholder in parent dir of logfile. This does not work as "
            "we have to create that dir before submission in order to make sbatch "
            "happy. Otherwise we get silent fails without logfiles being created."
        )

        # generic part of a submission string:
        # we use a run_uuid as the job-name, to allow `--name`-based
        # filtering in the job status checks (`sacct --name` and `squeue --name`)
        if wildcard_str == "":
            comment_str = f"rule_{job.name}"
        else:
            comment_str = f"rule_{job.name}_wildcards_{wildcard_str}"
        call = (
            f"sbatch "
            f"--parsable "
            f"--job-name {self.run_uuid} "
            f"--output '{slurm_logfile}' "
            f"--export=ALL "
            f"--comment '{comment_str}'"
        )

        if not self.workflow.executor_settings.no_account:
            call += self.get_account_arg(job)

        call += self.get_partition_arg(job)

        if self.workflow.executor_settings.requeue:
            call += " --requeue"

        call += set_gres_string(job)

        if job.resources.get("clusters"):
            call += f" --clusters {job.resources.clusters}"

        if job.resources.get("runtime"):
            call += f" -t {job.resources.runtime}"
        else:
            self.logger.warning(
                "No wall time information given. This might or might not "
                "work on your cluster. "
                "If not, specify the resource runtime in your rule or as a reasonable "
                "default via --default-resources."
            )

        if job.resources.get("constraint"):
            call += f" -C '{job.resources.constraint}'"
        if job.resources.get("mem_mb_per_cpu"):
            call += f" --mem-per-cpu {job.resources.mem_mb_per_cpu}"
        elif job.resources.get("mem_mb"):
            call += f" --mem {job.resources.mem_mb}"
        else:
            self.logger.warning(
                "No job memory information ('mem_mb' or 'mem_mb_per_cpu') is given "
                "- submitting without. This might or might not work on your cluster."
            )

        if job.resources.get("nodes", False):
            call += f" --nodes={job.resources.get('nodes', 1)}"

        # fixes #40 - set ntasks regardless of mpi, because
        # SLURM v22.05 will require it for all jobs
        gpu_job = job.resources.get("gpu") or "gpu" in job.resources.get("gres", "")
        if gpu_job:
            call += f" --ntasks-per-gpu={job.resources.get('tasks', 1)}"
        else:
            call += f" --ntasks={job.resources.get('tasks', 1)}"
        # MPI job
        if job.resources.get("mpi", False):
            if not job.resources.get("tasks_per_node") and not job.resources.get(
                "nodes"
            ):
                self.logger.warning(
                    "MPI job detected, but no 'tasks_per_node' or 'nodes' "
                    "specified. Assuming 'tasks_per_node=1'."
                    "Probably not what you want."
                )

        # we need to set cpus-per-task OR cpus-per-gpu, the function
        # will return a string with the corresponding value
        call += f" {get_cpu_setting(job, gpu_job)}"
        if job.resources.get("slurm_extra"):
            self.check_slurm_extra(job)
            call += f" {job.resources.slurm_extra}"

        exec_job = self.format_job_exec(job)

        # ensure that workdir is set correctly
        # use short argument as this is the same in all slurm versions
        # (see https://github.com/snakemake/snakemake/issues/2014)
        call += f" -D {self.workflow.workdir_init}"
        # and finally the job to execute with all the snakemake parameters
        call += f' --wrap="{exec_job}"'

        self.logger.debug(f"sbatch call: {call}")
        try:
            process = subprocess.Popen(
                call,
                shell=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            out, err = process.communicate()
            if process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode, call, output=err
                )
        except subprocess.CalledProcessError as e:
            raise WorkflowError(
                f"SLURM sbatch failed. The error message was {e.output}"
            )
        # any other error message indicating failure?
        if "submission failed" in err:
            raise WorkflowError(
                f"SLURM job submission failed. The error message was {err}"
            )

        # multicluster submissions yield submission infos like
        # "Submitted batch job <id> on cluster <name>" by default, but with the
        # --parsable option it simply yields "<id>;<name>".
        # To extract the job id we split by semicolon and take the first element
        # (this also works if no cluster name was provided)
        slurm_jobid = out.strip().split(";")[0]
        if not slurm_jobid:
            raise WorkflowError("Failed to retrieve SLURM job ID from sbatch output.")
        slurm_logfile = slurm_logfile.with_name(
            slurm_logfile.name.replace("%j", slurm_jobid)
        )
        self.logger.info(
            f"Job {job.jobid} has been submitted with SLURM jobid {slurm_jobid} "
            f"(log: {slurm_logfile})."
        )
        self.report_job_submission(
            SubmittedJobInfo(
                job, external_jobid=slurm_jobid, aux={"slurm_logfile": slurm_logfile}
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
        # If `AccountingStorageType`` for `sacct` is set to `accounting_storage/none`,
        # sacct will query `slurmctld` (instead of `slurmdbd`) and this in turn can
        # rely on default config, see: https://stackoverflow.com/a/46667605
        # This config defaults to `MinJobAge=300`, which implies that jobs will be
        # removed from `slurmctld` within 6 minutes of finishing. So we're conservative
        # here, with half that time
        max_sleep_time = 180

        sacct_query_durations = []

        status_attempts = 5

        active_jobs_ids = {job_info.external_jobid for job_info in active_jobs}
        active_jobs_seen_by_sacct = set()
        missing_sacct_status = set()

        # We use this sacct syntax for argument 'starttime' to keep it compatible
        # with slurm < 20.11
        sacct_starttime = f"{datetime.now() - timedelta(days = 2):%Y-%m-%dT%H:00}"
        # previously we had
        # f"--starttime now-2days --endtime now --name {self.run_uuid}"
        # in line 218 - once v20.11 is definitively not in use any more,
        # the more readable version ought to be re-adapted

        # -X: only show main job, no substeps
        sacct_command = f"""sacct -X --parsable2 \
                        --clusters all \
                        --noheader --format=JobIdRaw,State \
                        --starttime {sacct_starttime} \
                        --endtime now --name {self.run_uuid}"""

        # for better redability in verbose output
        sacct_command = " ".join(shlex.split(sacct_command))

        # this code is inspired by the snakemake profile:
        # https://github.com/Snakemake-Profiles/slurm
        for i in range(status_attempts):
            async with self.status_rate_limiter:
                (status_of_jobs, sacct_query_duration) = await self.job_stati(
                    sacct_command
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
                    f"active_jobs_seen_by_sacct are: {active_jobs_seen_by_sacct}"
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
                f"Unable to get the status of all active jobs that should be "
                f"in slurmdbd, even after {status_attempts} attempts.\n"
                f"The jobs with the following slurm job ids were previously seen "
                "by sacct, but sacct doesn't report them any more:\n"
                f"{missing_sacct_status}\n"
                f"Please double-check with your slurm cluster administrator, that "
                "slurmdbd job accounting is properly set up.\n"
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
                            "removing log for successful job "
                            f"with SLURM ID '{j.external_jobid}'"
                        )
                        try:
                            if j.aux["slurm_logfile"].exists():
                                j.aux["slurm_logfile"].unlink()
                        except (OSError, FileNotFoundError) as e:
                            self.logger.warning(
                                "Could not remove log file"
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
                    self.next_seconds_between_status_checks + 10, max_sleep_time
                )
            else:
                self.next_seconds_between_status_checks = None

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
            self.logger.error(
                f"The job status query failed with command: {command}\n"
                f"Error message: {e.stderr.strip()}\n"
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
            # here, we check whether the given or guessed account is valid
            # if not, a WorkflowError is raised
            self.test_account(job.resources.slurm_account)
            return f" -A '{job.resources.slurm_account}'"
        else:
            if self._fallback_account_arg is None:
                self.logger.warning("No SLURM account given, trying to guess.")
                account = self.get_account()
                if account:
                    self.logger.warning(f"Guessed SLURM account: {account}")
                    self.test_account(f"{account}")
                    self._fallback_account_arg = f" -A {account}"
                else:
                    self.logger.warning(
                        "Unable to guess SLURM account. Trying to proceed without."
                    )
                    self._fallback_account_arg = (
                        ""  # no account specific args for sbatch
                    )
            return self._fallback_account_arg

    def get_partition_arg(self, job: JobExecutorInterface):
        """
        checks whether the desired partition is valid,
        returns a default partition, if applicable
        else raises an error - implicetly.
        """
        if job.resources.get("slurm_partition"):
            partition = job.resources.slurm_partition
        else:
            if self._fallback_partition is None:
                self._fallback_partition = self.get_default_partition(job)
            partition = self._fallback_partition
        if partition:
            return f" -p {partition}"
        else:
            return ""

    def get_account(self):
        """
        tries to deduce the acccount from recent jobs,
        returns None, if none is found
        """
        cmd = f'sacct -nu "{os.environ["USER"]}" -o Account%256 | head -n1'
        try:
            sacct_out = subprocess.check_output(
                cmd, shell=True, text=True, stderr=subprocess.PIPE
            )
            return sacct_out.replace("(null)", "").strip()
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
        cmd = "sshare -U --format Account --noheader"
        try:
            accounts = subprocess.check_output(
                cmd, shell=True, text=True, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            sshare_report = (
                "Unable to test the validity of the given or guessed"
                f" SLURM account '{account}' with sshare: {e.stderr}."
            )
            accounts = ""

        if not accounts.strip():
            cmd = f'sacctmgr -n -s list user "{os.environ["USER"]}" format=account%256'
            try:
                accounts = subprocess.check_output(
                    cmd, shell=True, text=True, stderr=subprocess.PIPE
                )
            except subprocess.CalledProcessError as e:
                sacctmgr_report = (
                    "Unable to test the validity of the given or guessed "
                    f"SLURM account '{account}' with sacctmgr: {e.stderr}."
                )
                raise WorkflowError(
                    f"The 'sshare' reported: '{sshare_report}' "
                    f"and likewise 'sacctmgr' reported: '{sacctmgr_report}'."
                )

        # The set() has been introduced during review to eliminate
        # duplicates. They are not harmful, but disturbing to read.
        accounts = set(_.strip() for _ in accounts.split("\n") if _)

        if not accounts:
            self.logger.warning(
                f"Both 'sshare' and 'sacctmgr' returned empty results for account "
                f"'{account}'. Proceeding without account validation."
            )
            return ""

        if account not in accounts:
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
        jobname = re.compile(r"--job-name[=?|\s+]|-J\s?")
        if re.search(jobname, job.resources.slurm_extra):
            raise WorkflowError(
                "The --job-name option is not allowed in the 'slurm_extra' "
                "parameter. The job name is set by snakemake and must not be "
                "overwritten. It is internally used to check the stati of the "
                "all submitted jobs by this workflow."
                "Please consult the documentation if you are unsure how to "
                "query the status of your jobs."
            )
