# utility functions for the SLURM executor plugin

import os


def delete_slurm_environment():
    """
    Function to delete all environment variables
    starting with 'SLURM_'. The parent shell, will
    still have the this environment. Needed to
    submit within a SLURM job context to avoid
    conflicting environments.
    """
    for var in os.environ:
        if "SLURM" in var:
            os.unsetenv(var)
