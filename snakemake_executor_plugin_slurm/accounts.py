import getpass
import shlex
import subprocess

from snakemake_interface_common.exceptions import WorkflowError


def test_account(account, logger):
    """
    tests whether the given account is registered, raises an error, if not
    """
    # first we need to test with sacctmgr because sshare might not
    # work in a multicluster environment
    cmd = f'sacctmgr -n -s list user "{getpass.getuser()}" format=account%256'
    cmd = shlex.split(cmd)
    sacctmgr_report = sshare_report = ""
    try:
        accounts = subprocess.check_output(
            cmd, text=True, stderr=subprocess.PIPE
        )
    except subprocess.CalledProcessError as e:
        sacctmgr_report = (
            "Unable to test the validity of the given or guessed"
            f" SLURM account '{account}' with sacctmgr: {e.stderr}."
        )
        accounts = ""

    if not accounts.strip():
        cmd = "sshare -U --format Account%256 --noheader"
        cmd = shlex.split(cmd)
        try:
            accounts = subprocess.check_output(
                cmd, text=True, stderr=subprocess.PIPE
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


def get_account(logger):
    """
    tries to deduce the acccount from recent jobs,
    returns None, if none is found
    """
    cmd = f'sacct -nu "{getpass.getuser()}" -o Account%256 | tail -1'
    cmd = shlex.split(cmd)
    try:
        sacct_out = subprocess.check_output(
            cmd, text=True, stderr=subprocess.PIPE
        )
        possible_account = sacct_out.replace("(null)", "").strip()
        if possible_account == "none":  # some clusters may not use an account
            return None
    except subprocess.CalledProcessError as e:
        logger.warning(
            f"No account was given, not able to get a SLURM account via sacct: "
            f"{e.stderr}"
        )
        return None
