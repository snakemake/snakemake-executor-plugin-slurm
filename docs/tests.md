# Tests (for developers)

In order to test if this plugin works, we can run a small test workflow with the following steps:

1. Log onto the Cannon cluster and ensure you're in an environment with Snakemake and Python installed.
2. Clone this repository
3. Navigate to the repository root and run: 

```bash
pip install -e .` to install the plugin
```

4. Navigate to the `tests` folder and run: 

```bash
snakemake -j 5 --profile cannon-test-profile/
```

These test scripts can also be used as a template for setting up profiles and rules that are compatible with this plugin.

## Extensive tests

For more extensive testing, ensure `pytest` is installed in your environment. Then navigate to the tests folder and run:

```bash
pytest tests.py
```

This will run the full suite of tests from the original SLURM plugin and will take some time to run.

For more extensive logging of the tests, you can run:

```bash
pytest -v -s tests.py --basetemp=./pytest-tmp &> tests.log
```