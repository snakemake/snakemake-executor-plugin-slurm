# Snakemake profile setup

A profile is a set of configuration files for a specific job submission system, and is specifed in the Snakemake call as:

```{bash}
snakemake --profile profile_directory/
```

Because profiles may contain multiple files, the profile argument is passed a directory path. However, for resource specification, the file you need to create is `config.yaml`, in which you can specify the resources for the rules of your pipeline, *e.g.* for a workflow with rules named *a* and *b*:

```YAML
executor: cannon

set-resources:
  a:
    slurm_partition: sapphire
    mem: 5G
    cpus_per_task: 1
    runtime: 30m

  b:
    mem: 10G
    cpus_per_task: 4
    runtime: 2h
    slurm_extra: "'--gres=gpu:2'"
```

Note that the `slurm_partition:` specification can be blank or omitted, as in rule *b*, since this plugin will select the partition for you based on the other resources provided. However, if `slurm_partition:` is provided with a value, as in rule *a*, that partition will be used.

Any resource fields implemented in Snakemake are available to be used in the profile and with this plugin, but only memory (`mem:` or `mem_mb:` or `mem_gb`), `cpus_per_task:`, `runtime:`, and GPUs via `slurm_extra:` (see below) will affect partition selection. If fields are left blank, the plugin has default values to fall back on.

In summary, the following resource flags (and default values) are available to be set in rules, with there being multiple ways to specify the amount of memory for a job.

| Resources       | Default Value | Units                                    | 
|-----------------|:-------------:|:----------------------------------------:|
| `mem`           | 4G            | G (gigabyte), M (megabyte), T (terabyte) |
| `mem_mb`        | 4000          | megabyte                                 |
| `mem_gb`        | 4             | gigabyte                                 |
| `runtime`       | 30m           | m (minutes), h (hours), d (days)         |
| `cpus_per_task` | 1             |                                          |

Note that only one of `mem`, `mem_gb`, and `mem_mb` should be set. If multiple are set, only one will be used with the order of precedence being `mem` > `mem_gb` > `mem_mb`.

## Setting GPUs

Currently, on the Cannon cluster, this plugin only supports GPU specification via the `slurm_extra:` field. See your *b* above for an example requesting 2 GPUs.

## Example profile

As a template, you can use the [`tests/cannon-test-profile/config.yaml`](), which will need to be modified with the necessary changes for the workflow that you want to run.


## Specifying the executor in the profile

Note the first line of the profile:

```YAML
executor: cannon
```

This tells Snakemake which plugin to use to execute job submission. Alternatively, if this line is excluded from the profile, one could specify the plugin directly from the command line:

```bash
snakemake -e cannon ...
```

Either method is acceptable.