from snakemake_interface_common.exceptions import WorkflowError
from snakemake_executor_plugin_slurm_jobstep import get_cpu_setting
from types import SimpleNamespace
import shlex


def safe_quote(value):
    """
    Safely quote a parameter value using shlex.quote.
    Handles None values and converts to string if needed.
    Returns empty quotes for empty strings.
    """
    str_value = str(value)
    if str_value == "":
        return "''"
    return shlex.quote(str_value)


def get_submit_command(job, params):
    """
    Return the submit command for the job.
    """
    # Convert params dict to a SimpleNamespace for attribute-style access
    params = SimpleNamespace(**params)

    call = (
        "sbatch "
        "--parsable "
        f"--job-name {safe_quote(params.run_uuid)} "
        f"--output {safe_quote(params.slurm_logfile)} "
        "--export=ALL "
        f"--comment {safe_quote(params.comment_str)}"
    )

    # No accout or partition checking is required, here.
    # Checking is done in the submit function.

    # here, only the string is used, as it already contains
    # "-A '{account_name}'"
    call += f" {params.account}"
    # here, only the string is used, as it already contains
    # "- p '{partition_name}'"
    call += f" {params.partition}"

    if job.resources.get("clusters"):
        call += f" --clusters {safe_quote(job.resources.clusters)}"

    if job.resources.get("runtime"):
        call += f" -t {safe_quote(job.resources.runtime)}"

    # Both, constraint and qos are optional.
    # If not set, they will not be added to the sbatch call.
    # If explicitly set to an empty string,
    # `--constraint ''` or `--qos ''` will be added.
    constraint = job.resources.get("constraint")
    if constraint is not None:
        call += f" -C {safe_quote(constraint)}"

    qos = job.resources.get("qos")
    if qos is not None:
        call += f" --qos={safe_quote(qos)}"

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
        # if the job is a MPI job, ntasks will be set later
        if not job.resources.get("mpi", False):
            call += f" --ntasks={job.resources.get('tasks') or 1}"

    # if the job is an MPI job, we need to have some task setting:
    if job.resources.get("mpi", False):
        if not job.resources.get("tasks_per_node") and not job.resources.get("tasks"):
            raise WorkflowError(
                "For MPI jobs, please specify either "
                "'tasks_per_node' or 'tasks' (at least one is required)."
            )
        # raise an error if both task settings are used
        if job.resources.get("tasks_per_node") and job.resources.get("tasks"):
            raise WorkflowError(
                "For MPI jobs, please specify either 'tasks_per_node' or 'tasks', "
                "but not both."
            )
        if job.resources.get("tasks_per_node"):
            if job.resources.get("tasks_per_node") <= 1:
                raise WorkflowError(
                    "For MPI jobs, 'tasks_per_node' must be greater than 1."
                )
            call += f" --ntasks-per-node={job.resources.tasks_per_node}"
        elif job.resources.get("tasks"):
            if job.resources.get("tasks") == 1:
                raise WorkflowError("For MPI jobs, 'tasks' must be greater than 1.")
            call += f" --ntasks={job.resources.tasks}"
        # nodes CAN be set independently of tasks or tasks_per_node
        # this is at a user's discretion. The nodes flag might already
        # be set above, if the user specified it.

    # we need to set cpus-per-task OR cpus-per-gpu, the function
    # will return a string with the corresponding value
    call += f" {get_cpu_setting(job, gpu_job)}"
    if job.resources.get("slurm_extra"):
        call += f" {job.resources.slurm_extra}"

    # ensure that workdir is set correctly
    # use short argument as this is the same in all slurm versions
    # (see https://github.com/snakemake/snakemake/issues/2014)
    if params.workdir:
        call += f" -D {safe_quote(params.workdir)}"

    return call
