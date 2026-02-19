# Current State

The current state is as follows:

Manually performed:
```
rm -rf dist/ build
# manual deletion of the library directory in the environment
TMPDIR=. poetry build --no-cache # as /tmp is no option on my login node
python cleanup_wheel.py # getting rid of the '.c' and '.py' files in the wheel
                        # leaving the __init__.py
TMPDIR=. poetry run pip install --force-reinstall "dist/snakemake_executor_plugin_slurm-2.1.0-cp313-cp313-manylinux_2_28_x86_64.whl"
```

This leaves us with: `__init__.py` and `snakemake_executor_plugin_slurm/_core.cpython-313-x86_64-linux-gnu.so`.

# TODO

- Refactor __init__.py so that imports from _core and serves as the entry point.
