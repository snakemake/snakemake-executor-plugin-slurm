import shlex
import subprocess
import re
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


def query_job_status_sacct(runid) -> list:
    """
    Query job status using sacct command

    Args:
        runid: workflow run ID

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

    # for better redability in verbose output
    query_command = " ".join(shlex.split(query_command))

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
    query_command = f"""squeue
                       --format=%i|%T
                       --states=all
                       --noheader
                       --name {runid}"""
    # for better redability in verbose output
    query_command = " ".join(shlex.split(query_command))

    return query_command
