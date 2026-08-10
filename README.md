# Snakemake executor plugin: slurm

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/snakemake/snakemake-executor-plugin-slurm)

For documentation, see the [Snakemake plugin catalog](https://snakemake.github.io/snakemake-plugin-catalog/plugins/executor/slurm.html).

For development and testing, checkout this repo and (depending on your needs) do one of the following

* Run `pixi shell -e dev` to open a development environment
* Run `pixi run test` to run tests locally (requires a running slurm system)
* To simultaneously develop the slurm-jobstep and the slurm plugin, uncommend and edit the line `#snakemake-executor-plugin-slurm-jobstep = { path = "../snakemake-executor-plugin-slurm-jobstep", editable = true}` in the pyproject.toml before running `pixi shell -e dev`.