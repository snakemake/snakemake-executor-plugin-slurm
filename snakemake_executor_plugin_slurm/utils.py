# utility functions for the SLURM executor plugin

import os
from pathlib import Path


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


def delete_empty_dirs(path: Path) -> list:
    """
    Function to delete all empty directories in a given path.
    This is needed to clean up the working directory after
    a job has sucessfully finished. This function is needed because
    the shutil.rmtree() function does not delete empty
    directories.
    """

    # get a list of all directorys in path and subpaths
    def get_dirs(path: Path, result=[]):
        for p in path.iterdir():
            if p.is_dir():
                result.append(p)
                if any(p.iterdir()):
                    get_dirs(p)
        return result

    # keep trying to delete empty folders until none are left
    dirs = get_dirs(path)
    done = False
    while not done:
        done = True
        for p in dirs:
            try:
                if not any(p.iterdir()):  # if directory is empty
                    p.rmdir()
            except (OSError, FileNotFoundError) as e:
                raise e  # re-raise exception
            finally:
                done = False
                dirs.remove(p)
