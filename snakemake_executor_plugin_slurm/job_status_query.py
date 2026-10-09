import asyncio
import os
import shlex
import subprocess
import re
import csv
import time
from io import StringIO
from datetime import datetime, timedelta


def get_min_job_age():
    """
    Runs 'scontrol show config', parses the output, and extracts the MinJobAge value.
    Returns the value as an integer (seconds), or None if not found or parse error.
    Handles various time units: s/sec/secs/seconds, h/hours, or no unit
    (assumes seconds).
    """
    try:
        cmd = "scontrol show config"
        cmd = shlex.split(cmd)
        output = subprocess.check_output(
            cmd, text=True, stderr=subprocess.PIPE, timeout=10
        )
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ):
        return None

    for line in output.splitlines():
        if line.strip().startswith("MinJobAge"):
            # Example: MinJobAge               = 300 sec
            #          MinJobAge               = 1h
            #          MinJobAge               = 3600
            parts = line.split("=")
            if len(parts) < 2:
                continue
            value_part = parts[1].strip()

            # Use regex to parse value and optional unit
            # Pattern matches: number + optional whitespace + optional unit
            match = re.match(r"^(\d+)\s*([a-zA-Z]*)", value_part)
            if not match:
                continue

            value_str = match.group(1)
            unit = match.group(2).lower() if match.group(2) else ""

            try:
                value = int(value_str)

                # Convert to seconds based on unit
                if unit in ("h", "hour", "hours"):
                    return value * 3600
                elif unit in ("s", "sec", "secs", "second", "seconds", ""):
                    return value
                else:
                    # Unknown unit, assume seconds
                    return value

            except ValueError:
                return None
    return None


def is_query_tool_available(tool_name):
    """
    Check if the sacct command is available on the system.
    Returns True if sacct is available, False otherwise.
    """
    cmd = f"which {tool_name}"
    cmd = shlex.split(cmd)
    try:
        subprocess.check_output(cmd, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False


def should_recommend_squeue_status_command(min_threshold_seconds=120):
    """
    Determine if the status query with squeue should be recommended based on
    the MinJobAge configuration (if very low, squeue might not work well)

    Args:
        min_threshold_seconds: The minimum threshold in seconds for MinJobAge
                               to be considered sufficient. Default is 120
                               seconds (3 * 40s, where 40s is the default
                               initial status check interval).

    Returns True if the option should be available, False otherwise.
    """
    min_job_age = get_min_job_age()

    # If MinJobAge is sufficient (>= threshold), squeue might work for job status
    # queries. However, `sacct` is the preferred command for job status queries:
    # The SLURM accounting database will answer queries for a huge number of jobs
    # more reliably than `squeue`, which might not be configured to show past jobs
    # on every cluster.
    if min_job_age is not None and min_job_age >= min_threshold_seconds:
        return True

    # In other cases, sacct should work fine and the option might not be needed
    return False


def get_status_check_intervals(settings, status_command):
    """
    Return the initial and the maximum time in seconds between status checks.

    A default initial time never exceeds a set maximum, and a default maximum
    is never smaller than the initial time.
    """
    if status_command == "squeue+sacct":
        # Each round runs one squeue query, and sacct only for the jobs that
        # squeue does not report. So a fixed interval of 20 seconds puts
        # little load on slurmdbd.
        default_initial, default_maximum = 20, 20
    else:
        # If `AccountingStorageType`` for `sacct` is set to
        # `accounting_storage/none`, `sacct` will query `slurmctld` (instead
        # of `slurmdbd`) and this in turn can rely on default config,
        # see: https://stackoverflow.com/a/46667605
        # This config defaults to `MinJobAge=300`, which implies that jobs will
        # be removed from `slurmctld` within 6 minutes of finishing. So the
        # default maximum is conservative, with half that time.
        default_initial, default_maximum = 40, 180
    initial = getattr(settings, "init_seconds_before_status_checks", None)
    maximum = getattr(settings, "max_seconds_between_status_checks", None)
    if initial is None:
        initial = default_initial if maximum is None else min(default_initial, maximum)
    if maximum is None:
        maximum = max(default_maximum, initial)
    return initial, maximum


def query_job_status_sacct(runid, job_ids=None) -> list:
    """
    Query job status using sacct command

    Args:
        runid: workflow run ID
        job_ids: optional list of job IDs to restrict the query to

    Returns:
        Dictionary mapping job ID to JobStatus object
    """
    # We use this sacct syntax for argument 'starttime' to keep it compatible
    # with slurm < 20.11
    sacct_starttime = f"{datetime.now() - timedelta(days=2):%Y-%m-%dT%H:00}"
    # previously we had
    # f"--starttime now-2days --endtime now --name {self.run_uuid}"
    # in line 218 - once v20.11 is definitively not in use any more,
    # the more readable version ought to be re-adapted

    # -X: only show main job, no substeps
    query_command = f"""sacct -X --parsable2 \
                        --clusters all \
                        --noheader --format=JobIdRaw,State \
                        --starttime {sacct_starttime} \
                        --endtime now --name {runid}"""
    if job_ids:
        query_command = f"{query_command} --jobs {','.join(job_ids)}"

    # for better redability in verbose output
    query_command = shlex.join(shlex.split(query_command))

    return query_command


def query_job_status_squeue(runid) -> list:
    """
    Query job status using squeue command (newer SLURM functionality)

    Args:
        runid: workflow run ID

    Returns:
        Dictionary mapping job ID to JobStatus object
    """
    # Build squeue command
    # Note: The format string contains a pipe '|' which must be quoted to
    # prevent shell interpretation when passing to subprocess with shell=True
    format_arg = shlex.quote("%i|%T")
    # --array: report each pending array task on its own line
    # --user: slurmctld then sends only the jobs of this user, instead of all
    # jobs of the cluster for the client to filter by --name
    query_command = f"""squeue
                       --format={format_arg}
                       --states=all
                       --array
                       --noheader
                       --user {os.getuid()}
                       --name {runid}"""
    # for better redability in verbose output
    query_command = shlex.join(shlex.split(query_command))

    return query_command


async def query_job_status(command: str, logger):
    """Obtain SLURM job status of all submitted jobs with sacct or squeue

    Args:
        command: SLURM command that returns one line for each job with:
                 "<raw/main_job_id>|<long_status_string>"
        logger: Logger instance for debug/error output

    Returns:
        Tuple of (status_dict, query_duration) where status_dict is a dict
        mapping job IDs to status strings, and query_duration is time in seconds.
        Returns (None, None) on query failure.
    """
    status_of_jobs = {}

    start_time = time.time()
    try:
        process = await asyncio.create_subprocess_exec(
            *shlex.split(command),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        # Note: The replacement of `communicate()` with `wait_for()` has been
        #       benchmarked. The average call time has been reduced by ~16 %.
        #       Without asnyncio.wait_for, the average call time was 0.014 seconds,
        #       while with asyncio.wait_for, it is reduced to 0.011 seconds.
        #       A t-test based on about 70 calls each, gives a p-value of 2e-27.

        out, err = await asyncio.wait_for(process.communicate(), timeout=60)
        query_duration = time.time() - start_time

        out_text = out.decode() if out else ""
        err_text = err.decode() if err else ""

        if process.returncode != 0:
            if err_text:
                logger.debug(f"SLURM query command failed: {err_text}")
            return None, None

        # Parse the CSV output with | delimiter
        reader = csv.reader(StringIO(out_text), delimiter="|")
        for row in reader:
            if len(row) >= 2:
                job_id = row[0].strip()
                status = row[1].strip()
                if job_id:  # skip empty lines
                    status_of_jobs[job_id] = status

        return status_of_jobs, query_duration

    except asyncio.TimeoutError:
        logger.debug("SLURM query command timed out")
        return None, None
    except Exception as e:
        logger.debug(f"Error querying SLURM job status: {e}")
        return None, None
