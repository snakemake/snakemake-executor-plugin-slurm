import os
import subprocess

from snakemake_interface_common.exceptions import WorkflowError


def test_account(account, logger):
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
        logger.warning(
            f"Both 'sacctmgr' and 'sshare' returned empty results for account "
            f"'{account}'. Proceeding without account validation."
        )
        return ""

    if account.lower() not in accounts:
        raise WorkflowError(
            f"The given account {account} appears to be invalid. Available "
            f"accounts:\n{', '.join(accounts)}"
        )
