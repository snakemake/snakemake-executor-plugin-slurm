import asyncio
import shlex
import sys
from unittest.mock import MagicMock

from snakemake_executor_plugin_slurm.job_status_query import query_job_status


def _run_query_with_output(output: str):
    command = shlex.join(
        [sys.executable, "-c", f"import sys; sys.stdout.write({output!r})"]
    )
    return asyncio.run(query_job_status(command, MagicMock()))


def test_query_job_status_strips_state_details():
    status_of_jobs, _ = _run_query_with_output(
        "3080285|CANCELLED by 12345\n"
        "3080286|COMPLETED\n"
        "3080287|RUNNING\n"
        "3080288|\n"
    )
    assert status_of_jobs == {
        "3080285": "CANCELLED",
        "3080286": "COMPLETED",
        "3080287": "RUNNING",
        "3080288": "",
    }
