# Snakemake executor plugin: cannon

This is a fork of the [SLURM executor plugin for Snakemake](https://github.com/snakemake/snakemake-executor-plugin-slurm) for the [Cannon cluster at Harvard University](https://docs.rc.fas.harvard.edu/kb/running-jobs/). This plugin performs automatic partition selection based on the resources specified in a given Snakemake rule. It also offers some error checking for partition selection.

## Setting up your profile

As a template, you can use the `tests/profiles/cannon/config.yaml` which will need to be modified with the necessary changes for the workflow that you want to run.

## Example

In order to test if this plugin works, we can run several small test slurm jobs with the following steps:

1. Log onto the Cannon cluster
2. Clone this repository
3. Run: `pip install -e .` to install the plugin
4. Navigate to the `test` folder and run: `snakemake -J 5 -e cannon --profiles profiles/cannon/`

These test scripts can also be used as a template for setting up profiles and rules that are compatible with this plugin.

## Features
For documentation, see the [Snakemake plugin catalog](https://snakemake.github.io/snakemake-plugin-catalog/plugins/executor/slurm.html).
