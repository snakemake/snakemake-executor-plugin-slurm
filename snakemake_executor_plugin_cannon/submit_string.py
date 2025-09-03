from snakemake_executor_plugin_slurm_jobstep import get_cpu_setting
from types import SimpleNamespace


def get_submit_command(job, params):
    """
    Return the submit command for the job.
    """
    # Convert params dict to a SimpleNamespace for attribute-style access
    params = SimpleNamespace(**params)

    call = (
        f"sbatch "
        f"--parsable "
        f"--job-name {params.run_uuid} "
        f'--output "{params.slurm_logfile}" '
        f"--export=ALL "
        f'--comment "{params.comment_str}"'
    )

    # No accout or partition checking is required, here.
    # Checking is done in the submit function.

    # here, only the string is used, as it already contains
    # '-A {account_name}'
    call += f" {params.account}"
    # here, only the string is used, as it already contains
    # '- p {partition_name}'
    call += f" {params.partition}"

    if job.resources.get("clusters"):
        call += f" --clusters {job.resources.clusters}"

    if job.resources.get("runtime"):
        call += f" -t {job.resources.runtime}"

    if job.resources.get("constraint") or isinstance(
        job.resources.get("constraint"), str
    ):
        call += f" -C '{job.resources.get('constraint')}'"

    if job.resources.get("qos") or isinstance(job.resources.get("qos"), str):
        call += f" --qos='{job.resources.qos}'"

    if job.resources.get("mem_mb_per_cpu"):
        call += f" --mem-per-cpu {job.resources.mem_mb_per_cpu}"
    elif job.resources.get("mem_mb"):
        call += f" --mem {job.resources.mem_mb}"

    if job.resources.get("nodes", False):
        call += f" --nodes={job.resources.get('nodes', 1)}"

    gpu_job = job.resources.get("gpu") or "gpu" in job.resources.get("gres", "")
    if gpu_job:
        # fixes #316 - allow unsetting of tasks per gpu
        # apparently, python's internal process manangement interfers with SLURM
        # e.g. for pytorch
        ntasks_per_gpu = job.resources.get("tasks_per_gpu")
        if ntasks_per_gpu is None:
            ntasks_per_gpu = job.resources.get("tasks")
        if ntasks_per_gpu is None:
            ntasks_per_gpu = 1

        if ntasks_per_gpu >= 1:
            call += f" --ntasks-per-gpu={ntasks_per_gpu}"
    else:
        # fixes #40 - set ntasks regardless of mpi, because
        # SLURM v22.05 will require it for all jobs
        call += f" --ntasks={job.resources.get('tasks') or 1}"

    # we need to set cpus-per-task OR cpus-per-gpu, the function
    # will return a string with the corresponding value
    call += f" {get_cpu_setting(job, gpu_job)}"
    if job.resources.get("slurm_extra"):
        call += f" {job.resources.slurm_extra}"

    # ensure that workdir is set correctly
    # use short argument as this is the same in all slurm versions
    # (see https://github.com/snakemake/snakemake/issues/2014)
    call += f" -D '{params.workdir}'"

    return call
