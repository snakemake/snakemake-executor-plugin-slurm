### How this Plugin works

This plugin is based off of the general SLURM plugin, but with added logic for automatic partition selection specifically on the Cannon cluster at Harvard University. With this plugin, Snakemake submits itself as a job script when operating on the Cannon cluster. 
Consequently, the SLURM log file will duplicate the output of the corresponding rule.
To avoid redundancy, the plugin deletes the SLURM log file for successful jobs, relying instead on the rule-specific logs.

Remote executors submit Snakemake jobs to ensure unique functionalities — such as piped group jobs and rule wrappers — are available on cluster nodes.
The memory footprint varies based on these functionalities; for instance, rules with a run directive that import modules and read data may require more memory.

**The information provided below is specific to the Cannon plugin. For full documentation of the general SLURM plugin see the** [official documentation](https://snakemake.github.io/snakemake-plugin-catalog/plugins/executor/slurm.html#further-detail) **for that plugin.**


Installing this plugin into your Snakemake base environment using conda will also install the 'jobstep' plugin, utilized on cluster nodes.
Additionally, we recommend installing the `snakemake-storage-plugin-fs`, which will automate transferring data from the main file system to slurm execution nodes and back (stage-in and stage-out).

### Contributions

We welcome bug reports and feature requests!
Please report issues specific to this plugin [in the plugin's GitHub repository](https://github.com/harvardinformatics/snakemake-executor-plugin-cannon/issues).
For other concerns, refer to the [Snakemake main repository](https://github.com/snakemake/snakemake/issues) or the relevant Snakemake plugin repository.
Cluster-related issues should be directed to [FAS Research Computing](https://www.rc.fas.harvard.edu/) or [FAS Informatics](https://informatics.fas.harvard.edu/).

### Partition selection

On a computinng cluster, a **partition** designates a subset of compute nodes grouped for specific purposes, such as high-memory or GPU tasks.

The Cannon plugin uses the provided resources (see below) to best place a job on a [partition on the cluster](https://docs.rc.fas.harvard.edu/kb/running-jobs/). Briefly, the plugin first checks if any GPUs are required and, if so, assigns the job to the *gpu* partition. Next, if the job requires a lot of memory, it will be assigned to one of the *bigmem* partitions. If the job requires many CPUs, it will be assigned to *intermediate* or *sapphire* depending on memory an runtime requirements. If the job doesn't exceed either the memory or CPU threshold, it will be put on the *shared* partition.

If a partition for a particular rule is provided in the rule, the command line, or in the profile, that partition will be used regardless.

After partition selection, the plugin does some checks to ensure the selected partition has the resources requested and will inform the user if not.

### Specifying Account

In SLURM, an **account** is used for resource accounting and allocation.

This resource is typically omitted from Snakemake workflows to maintain platform independence, allowing the same workflow to run on different systems without modification.

To specify it at the command line, define it as default resources:

```console
$ snakemake --executor slurm \
> -j unlimited \
> --workflow-profile <profile directory with a `config.yaml`> \
> --configfile config/config.yaml \
> --directory <path>
``` console
$ snakemake --executor cannon --default-resources slurm_account=<your SLURM account>
```

The plugin does its best to _guess_ your account. That might not be possible. Particularly, when dealing with several SLURM accounts, users ought to set them per workflow.
Some clusters, however, have a pre-defined default per user and _do not_ allow users to set their account or partition. The plugin will always attempt to set an account. To override this behavior, the `--slurm-no-account` flag can be used.

If individual rules require *e.g.* a different partition, you can override the default per rule:

``` console
$ snakemake --executor cannon --default-resources slurm_account=<your SLURM account> slurm_partition=<your SLURM partition> --set-resources <somerule>:slurm_partition=<some other partition>
```

To ensure consistency and ease of management, it's advisable to persist such settings via a [configuration profile](https://snakemake.readthedocs.io/en/latest/executing/cli.html#profiles), which can be provided system-wide, per user, or per workflow.

By default, the executor waits 40 seconds before performing the first job status check.
This interval can be adjusted using the `--slurm-init-seconds-before-status-checks=<time in seconds>` option, which may be useful when developing workflows on an HPC cluster to minimize turn-around times.

### Configuring SMP Jobs in Snakemake with the Cannon Executor Plugin

In Snakemake workflows, many jobs are executed by programs that are either single-core scripts or multithreaded applications, which are categorized as SMP ([**S**hared **M**memory **P**rocessing](https://en.wikipedia.org/wiki/Shared_memory)) jobs.
To allocate resources for such jobs using the SLURM executor plugin, you can specify the required number of CPU cores and memory directly within the resources section of a rule.
Here's how you can define a rule that requests 8 CPU cores and 14 GB of memory:

``` python
rule a:
    input: ...
    output: ...
    threads: 8
    resources:
        mem_mb=14000
```

Snakemake knows the `cpus_per_task`, similar to SLURM, as an alternative to `threads`.
Parameters in the `resources` section will take precedence.

#### Default resource values for the Cannon plugin

The following resource flags (and default values) are available to be set in rules and affect partition selection, with there being multiple ways to specify the amount of memory for a job.

| Resources     | Default Value | Units                                    | 
|---------------|:-------------:|:----------------------------------------:|
| mem           | 4G            | G (gigabyte), M (megabyte), T (terabyte) |
| mem_mb        | 4000          | megabyte                                 |
| mem_gb        | 4             | gigabyte                                 |
| runtime       | 30m           | m (minutes), h (hours), d (days)         |
| cpus_per_task | 1             |                                          |

Note that only one of `mem`, `mem_gb`, and `mem_mb` should be set. If multiple are set, only one will be used with the order of precedence being `mem` > `mem_gb` > `mem_mb`.

If you want to specify usage of GPUs in resources, you will have to use the `slurm_extra` tag, which there are examples of below in the [Setting GPUs](#setting-gpus) section.

See the [official SLURM plugin docs](https://snakemake.github.io/snakemake-plugin-catalog/plugins/executor/slurm.html) for information about other resource specifciations available.

### Workflow profiles

To avoid hard-coding resource parameters into your Snakefiles, it is advisable to create a cluster-specific workflow profile.
This profile should be named `config.yaml` and placed in a directory named `profiles` relative to your workflow directory.
You can then indicate this profile to Snakemake using the `--workflow-profile` profiles option.
Here's an example of how the `config.yaml` file might look:

```YAML
default-resources: # Set these if you wish to override the defaults set in the Cannon plugin
    slurm_account: "<account>"
    slurm_partition: "<default partition>"
    mem_mb_per_cpu: 1800 # take a sensible default for your cluster
    runtime: "30m"

# here only rules, which require different (more) resources:
set-resources:
    rule_a:
        runtime: "2h"

    rule_b:
        mem_mb_per_cpu: 3600
        runtime: "5h"

# parallelization with threads needs to be defined separately:
set-threads:
    rule_b: 64
```

In this configuration:

- `default-resources` sets the default SLURM account, partition, memory per CPU, and runtime for all jobs. These only need to be set if you want to change the ones set in the Cannon plugin (see [above](#default-resource-values-for-the-cannon-plugin))
- `set-resources` allows you to override these defaults for specific rules, such as `rule_a` and `rule_b`
- `set-threads` specifies the number of `threads` for particular rules, enabling fine-grained control over parallelization.

One may also set a specific partition for a specific rule by using the `slurm_partition:` parameter under a rule. This will override the Cannon plugin's automatic partition selection.

By utilizing a configuration profile, you can maintain a clean and platform-independent workflow definition while tailoring resource specifications to the requirements of your SLURM cluster environment.

#### Cannon plugin profile example

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
    gres: "'gpu:2'"
```

Note that the `slurm_partition:` specification can be blank or omitted, as in rule *b*, since this plugin will select the partition for you based on the other resources provided. However, if `slurm_partition:` is provided with a value, as in rule *a*, that partition will be used.

Any resource fields implemented in Snakemake are available to be used in the profile and with this plugin, but only memory (`mem:` or `mem_mb:` or `mem_gb`), `cpus_per_task:`, `runtime:`, and GPUs via `slurm_extra:` will affect partition selection. If fields are left blank, the plugin has default values to fall back on.

The resource flags and default values are used in profiles as described [above](#default-resource-values-for-the-cannon-plugin).

#### Setting GPUs

Use the `gres:` field to supply the number of GPUs. See *b* above for an example requesting 2 GPUs.

#### Knowing which rules are in a workflow

If you're working with a workflow developed by someone else, you will need to get a general sense of which rules exist to specify resources for them in your profile. 

The absolute quickest way to see the names of the rules in a workflow is to use the `--list` option:

```bash
snakemake -s <path/to/snakefile.smk> --list
```

This will simply print out the names of the rules in the workflow, which are hopefully descriptive enough to give you a sense for what resources they will need.

For a little more information, you can use `--dryrun`:

```bash
snakemake -s <path/to/snakefile.smk> --dryrun
```

This will run through the workflow and report exactly what jobs will be submitted without actually submitting them.

Once you know the rules in your workflow, you can setup their resources in your profile.

#### Example profile

As a template, you can use the [tests/cannon-test-profile/config.yaml](https://github.com/harvardinformatics/snakemake-executor-plugin-cannon/blob/main/tests/cannon-test-profile/config.yaml), which will need to be modified with the necessary changes for the workflow that you want to run.

#### Specifying the executor in the profile

Note the first line of the profile:

```YAML
executor: cannon
```

This tells Snakemake which plugin to use to execute job submission. Alternatively, if this line is excluded from the profile, one could specify the plugin directly from the command line:

```bash
snakemake -e cannon ...
```

Either method is acceptable.

### End

Recall that this information is specific to the Cannon plugin for the Cannon cluster at Harvard University. For full documentation of the general SLURM plugin see the [official documentation](https://snakemake.github.io/snakemake-plugin-catalog/plugins/executor/slurm.html#further-detail).
