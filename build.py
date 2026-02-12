"""
Poetry build hook for Cython compilation.
"""
import os
from Cython.Build import cythonize
from setuptools import Extension


def build(setup_kwargs):
    """
    This function is called by Poetry's build system.
    Override everything to ensure only ONE .so file is built.
    """
    # Collect all .py files in snakemake_executor_plugin_slurm directory for Cython compilation
    base_dir = "snakemake_executor_plugin_slurm"
    py_files = []

    for filename in os.listdir(base_dir):
        if filename.endswith(".py"):
            file_path = os.path.join(base_dir, filename)
            py_files.append(file_path)

    # Create a single Extension with all Python files compiled into one .so
    extensions = [
        Extension(
            "snakemake_executor_plugin_slurm._core",
            py_files
        )
    ]

    # gcc arguments for optimization
    os.environ["CFLAGS"] = "-O3"

    # REPLACE setup_kwargs completely to prevent Poetry from adding its own extensions
    setup_kwargs.clear()
    setup_kwargs.update({
        "packages": ["snakemake_executor_plugin_slurm"],
        "ext_modules": cythonize(
            extensions,
            language_level=3,
            compiler_directives={"linetrace": True},
        ),
    })

