# Snakemake executor plugin: cannon

This is a fork of the [SLURM executor plugin for Snakemake](https://github.com/snakemake/snakemake-executor-plugin-slurm) for the [Cannon cluster at Harvard University](https://docs.rc.fas.harvard.edu/kb/running-jobs/). It has all the same features as the SLURM plugin, but performs automatic partition selection for the Cannon cluster based on the resources specified in a given Snakemake rule. It also offers some error checking for partition selection.

## Installation

The executor can be installed with either pip:

```bash
pip install snakemake-executor-plugin-cannon
```

Or conda/mamba:

```bash
mamba install snakemake-executor-plugin-cannon
```

## Specifying the executor

To use the executor with Snakemake, either specify it in the command line as:

```bash
snakemake -e cannon ...
```

Or add it to your [profile](https://github.com/harvardinformatics/snakemake-executor-plugin-cannon/blob/main/docs/profile.md):

```YAML
executor: cannon
```

## Setting up your profile

While this plugin does automatic partition selection, the user is still responsible for specifying other resources for rules in their workflow. This is usually done through a cluster **profile**, but this may differ based on your workflow. 

See the [profile setup page](https://github.com/harvardinformatics/snakemake-executor-plugin-cannon/blob/main/docs/profile.md) for mor information. 

An example profile can be found at [`tests/cannon-test-profile/config.yaml`](https://github.com/harvardinformatics/snakemake-executor-plugin-cannon/blob/main/tests/cannon-test-profile/config.yaml)

## Features

For documentation, see the [Snakemake plugin catalog](https://snakemake.github.io/snakemake-plugin-catalog/plugins/executor/cannon.html).
