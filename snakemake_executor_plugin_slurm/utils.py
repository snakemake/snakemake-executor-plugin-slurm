# utility functions for the SLURM executor plugin

import os


def delete_slurm_environment():
    """
    Function to delete all environment variables
    starting with 'SLURM_'. The parent shell will
    still have this environment. This is needed to
    submit within a SLURM job context to avoid
    conflicting environments.
    """
    for var in os.environ:
        if var.startswith("SLURM_"):
            del os.environ[var]


def clean_old_logs(logdir, age_cutoff):
    """
    Function to delete files older than 'age_cutoff'
    in the SLURM 'logdir'
    """
    cutoff_secs = age_cutoff * 86400
    for root, _, files in os.walk(logdir, topdown=False):
        for fname in files:
            file_path = os.path.join(root, fname)
            if age_cutoff > 0:
                filestamp = os.stat(file_path).st_mtime
                if filestamp > cutoff_secs:
                    os.remove(file_path)
        # remove empty rule top dir, if empty
        if len(os.listdir(root)) == 0:
            os.rmdir(root)
