__author__ = "David Lähnemann, Johannes Köster, Christian Meesters"
__copyright__ = "Copyright 2023, David Lähnemann, Johannes Köster, Christian Meesters"
__email__ = "johannes.koester@uni-due.de"
__license__ = "MIT"

import csv
from io import StringIO
import os
import subprocess
import time
from typing import List, Generator
import uuid
from snakemake_interface_executor_plugins.executors.base import SubmittedJobInfo
from snakemake_interface_executor_plugins.executors.remote import RemoteExecutor
from snakemake_interface_executor_plugins.settings import CommonSettings
from snakemake_interface_executor_plugins.jobs import (
    JobExecutorInterface,
)
from snakemake_interface_common.exceptions import WorkflowError


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
)


# Required:
# Implementation of your executor
class Executor(RemoteExecutor):
    def __post_init__(self):
        self.run_uuid = str(uuid.uuid4())
        self._fallback_account_arg = None
        self._fallback_partition = None

    def additional_general_args(self):
        # we need to set -j to 1 here, because the behaviour
        # of snakemake is to submit all jobs at once, otherwise.
        # However, the SLURM Executor is supposed to submit jobs
        # one after another, so we need to set -j to 1 for the
        # JobStep Executor, which in turn handles the launch of
        # SLURM jobsteps.
        return "--executor slurm-jobstep --jobs 1"

    def run_job(self, job: JobExecutorInterface):
        # Implement here how to run a job.
        # You can access the job's resources, etc.
        # via the job object.
        # After submitting the job, you have to call
        # self.report_job_submission(job_info).
        # with job_info being of type
        # snakemake_interface_executor_plugins.executors.base.SubmittedJobInfo.

        jobid = job.jobid

        log_folder = f"group_{job.name}" if job.is_group() else f"rule_{job.name}"

        slurm_logfile = os.path.abspath(f".snakemake/slurm_logs/{log_folder}/%j.log")
        os.makedirs(os.path.dirname(slurm_logfile), exist_ok=True)

        # generic part of a submission string:
        # we use a run_uuid as the job-name, to allow `--name`-based
        # filtering in the job status checks (`sacct --name` and `squeue --name`)
        call = f"sbatch --job-name {self.run_uuid} -o {slurm_logfile} --export=ALL"

        call += self.get_account_arg(job)
        call += self.get_partition_arg(job)

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
            call += f" -C {job.resources.constraint}"
        if job.resources.get("mem_mb_per_cpu"):
            call += f" --mem-per-cpu {job.resources.mem_mb_per_cpu}"
        elif job.resources.get("mem_mb"):
            call += f" --mem {job.resources.mem_mb}"
        else:
            self.logger.warning(
                "No job memory information ('mem_mb' or 'mem_mb_per_cpu') is given "
                "- submitting without. This might or might not work on your cluster."
            )

        # MPI job
        if job.resources.get("mpi", False):
            if job.resources.get("nodes", False):
                call += f" --nodes={job.resources.get('nodes', 1)}"
            if job.resources.get("tasks", False):
                call += f" --ntasks={job.resources.get('tasks', 1)}"

        cpus_per_task = job.threads
        if job.resources.get("cpus_per_task"):
            if not isinstance(cpus_per_task, int):
                raise WorkflowError(
                    f"cpus_per_task must be an integer, but is {cpus_per_task}"
                )
            cpus_per_task = job.resources.cpus_per_task
        # ensure that at least 1 cpu is requested
        # because 0 is not allowed by slurm
        cpus_per_task = max(1, cpus_per_task)
        call += f" --cpus-per-task={cpus_per_task}"

        if job.resources.get("slurm_extra"):
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
            out = subprocess.check_output(
                call, shell=True, text=True, stderr=subprocess.STDOUT
            ).strip()
        except subprocess.CalledProcessError as e:
            raise WorkflowError(
                f"SLURM job submission failed. The error message was {e.output}"
            )

        slurm_jobid = out.split(" ")[-1]
        slurm_logfile = slurm_logfile.replace("%j", slurm_jobid)
        self.logger.info(
            f"Job {jobid} has been submitted with SLURM jobid {slurm_jobid} "
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
            "PREEMPTED",
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

        # this code is inspired by the snakemake profile:
        # https://github.com/Snakemake-Profiles/slurm
        for i in range(status_attempts):
            async with self.status_rate_limiter:
                (status_of_jobs, sacct_query_duration) = await self.job_stati(
                    # -X: only show main job, no substeps
                    f"sacct -X --parsable2 --noheader --format=JobIdRaw,State "
                    f"--starttime now-2days --endtime now --name {self.run_uuid}"
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
            if i >= status_attempts - 1:
                self.logger.warning(
                    f"Unable to get the status of all active_jobs that should be "
                    f"in slurmdbd, even after {status_attempts} attempts.\n"
                    f"The jobs with the following slurm job ids were previously seen "
                    "by sacct, but sacct doesn't report them any more:\n"
                    f"{missing_sacct_status}\n"
                    f"Please double-check with your slurm cluster administrator, that "
                    "slurmdbd job accounting is properly set up.\n"
                )

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
            elif status == "UNKNOWN":
                # the job probably does not exist anymore, but 'sacct' did not work
                # so we assume it is finished
                self.report_job_success(j)
                any_finished = True
                active_jobs_seen_by_sacct.remove(j.external_jobid)
            elif status in fail_stati:
                msg = (
                    f"SLURM-job '{j.external_jobid}' failed, SLURM status is: "
                    f"'{status}'"
                )
                self.report_job_error(j, msg=msg, aux_logs=[j.aux["slurm_logfile"]])
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
                subprocess.check_output(
                    f"scancel {jobids}",
                    text=True,
                    shell=True,
                    timeout=60,
                    stderr=subprocess.PIPE,
                )
            except subprocess.TimeoutExpired:
                self.logger.warning("Unable to cancel jobs within a minute.")

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
            return f" -A {job.resources.slurm_account}"
        else:
            if self._fallback_account_arg is None:
                self.logger.warning("No SLURM account given, trying to guess.")
                account = self.get_account()
                if account:
                    self.logger.warning(f"Guessed SLURM account: {account}")
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
            return sacct_out.strip()
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
        cmd = f'sacctmgr -n -s list user "{os.environ["USER"]}" format=account%256'
        try:
            accounts = subprocess.check_output(
                cmd, shell=True, text=True, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError as e:
            raise WorkflowError(
                f"Unable to test the validity of the given or guessed SLURM account "
                f"'{account}' with sacctmgr: {e.stderr}"
            )

        accounts = accounts.split()

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
