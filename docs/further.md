### How this Plugin works

Like with all remote executors, Snakemake will essentially submit itself. Specifically, on an HPC cluster with the SLURM batch system will be the "job script". Hence, the SLURM logfile will contain the same output you will otherwise see for that rule. The plugin will consider this as redundant and delete this log file for successful jobs - after all, we have the rule specific logs, too.

Remote executors submit Snakemake jobs, as Snakemake needs to provide its unique functionality (piped group jobs, running rules with wrappers, etc.) on the cluster nodes. Its memory footprint will depend on that added functionality (i.e. for rules with a `run` directive, which imports modules and reads data, it will be bigger).

#### Usage Hints

To use this plugin, you can install it into your Snakemake base environment with conda. It will install its dependency, the "jobstep" plugin (which will be used on the cluster nodes). We recommend installing the `snakemake-storage-plugin-fs` (see below) for automatic stage-in and -out procedures.

#### Reporting Bugs and Feature Requests

We welcome bug reports and feature requests! Please report only those bugs related to _this_ plugin as an [issue to the plugin repo on GitHub](https://github.com/snakemake/snakemake-executor-plugin-slurm/issue). All other issues should be directed either to the [Snakemake main repository](https://github.com/snakemake/snakemake/issues) or to the appropriate Snakemake plugin repository (or, if the issue is cluster‑related, to your cluster administrator).

### Specifying Account and Partition

Most SLURM clusters have two mandatory resource indicators for
accounting and scheduling, the account and a
partition, respectively. These resources are usually
omitted from Snakemake workflows in order to keep the workflow
definition independent of the platform. However, it is also possible
to specify them inside of the workflow as resources in the rule
definition.

To specify them at the command line, define them as default resources:

``` console
$ snakemake --executor slurm --default-resources slurm_account=<your SLURM account> slurm_partition=<your SLURM partition>
```

If individual rules require e.g. a different partition, you can override
the default per rule:

``` console
$ snakemake --executor slurm --default-resources slurm_account=<your SLURM account> slurm_partition=<your SLURM partition> --set-resources <somerule>:slurm_partition=<some other partition>
```

Usually, it is advisable to persist such settings via a
[configuration profile](https://snakemake.readthedocs.io/en/latest/executing/cli.html#profiles), which
can be provided system-wide, per user, and in addition per workflow.

The executor waits per default 40 seconds for its first check of the job status. Using `--slurm-init-seconds-before-status-checks=<time in seconds>` this behaviour can be altered.

### Ordinary SMP jobs

Most jobs will be carried out by programs that are either single-core
scripts or threaded programs, hence SMP ([shared memory
programs](https://en.wikipedia.org/wiki/Shared_memory)) in nature. Any
given threads and `mem_mb` requirements will be passed to SLURM:

``` python
rule a:
    input: ...
    output: ...
    threads: 8
    resources:
        mem_mb=14000
```

This will give jobs from this rule 14GB of memory and 8 CPU cores. Using the SLURM executor plugin, we can alternatively define:

```python
rule a:
    input: ...
    output: ...
    resources:
        cpus_per_task=8,
        mem_mb=14000
```
instead of the `threads` parameter. Parameters in the `resources` section will take precedence.

Instead of writing hard-coded parameterization into Snakefiles, we recommend creating a cluster specific profile. This should be named `config.yaml` and placed in a directory `profiles` relative to your workflow directory. Indicate it to Snakemake with `--workflow-profile profiles`

```YAML
default-resources:
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

# parallelization with threads needs to be defined seperately:
set-threads:
    rule_b: 64
```

### MPI jobs

Snakemake\'s SLURM backend also supports MPI jobs, see
`snakefiles-mpi`{.interpreted-text role="ref"} for details. When using
MPI with SLURM, it is advisable to use `srun` as an MPI starter.

``` python
rule calc_pi:
  output:
      "pi.calc",
  log:
      "logs/calc_pi.log",
  resources:
      tasks=10,
      mpi="srun",
  shell:
      "{resources.mpi} -n {resources.tasks} calc-pi-mpi > {output} 2> {log}"
```

Note that the `-n {resources.tasks}` is not necessary in the case of SLURM,
but it should be kept in order to allow execution of the workflow on
other systems, e.g. by replacing `srun` with `mpiexec`:

``` console
$ snakemake --set-resources calc_pi:mpi="mpiexec" ...
```

To submit "ordinary" MPI jobs, submitting with `tasks` (the MPI ranks) is sufficient. Alternatively, on some clusters, it might be convenient to just configure `nodes`. Consider using a combination of `tasks` and `cpus_per_task` for hybrid applications (those that use ranks (multiprocessing) and threads). A detailed topology layout can be achieved using the `slurm_extra` parameter (see below) using further flags like `--distribution`.

A sample profile might look like this:

```YAML
set-resources:
    mpi_rule:
        tasks: 2048

    hybrid_mpi_rule:
        tasks: 1024
        cpus_per_tasks: 2
```

### Running Jobs locally

Not all Snakemake workflows are adapted for heterogeneous environments, particularly clusters. Users might want to avoid the submission of _all_ rules as cluster jobs. Non-cluster jobs should usually include _short_ jobs, e.g. internet downloads or plotting rules.

To label a rule as a non-cluster rule, use the `localrules` directive. Place it on top of a `Snakefile` as a comma-separated list like:

```Python
localrules: <rule_a>, <rule_b>
```

### Advanced Resource Specifications

A workflow rule may support several
[resource specifications](https://snakemake.readthedocs.io/en/latest/snakefiles/rules.html#resources).
For a SLURM cluster, a mapping between Snakemake and SLURM needs to be performed.

Each of the listed command line flags can be part of a rule, e.g.:

``` python
rule:
    input: ...
    output: ...
    resources:
        partition=<partition name>
        runtime=<some number>
```

Please note: as `--mem` and `--mem-per-cpu` are mutually exclusive on
SLURM clusters, their corresponding resource flags `mem`/`mem_mb` and
`mem_mb_per_cpu` are mutually exclusive, too. You can either reserve the
memory a compute node has to provide(`--mem` flag) or the memory required per CPU (`--mem-per-cpu` flag). Depending on your cluster's settings hyperthreads are enabled. SLURM does not make any distinction between real CPU cores and those provided by hyperthreads. SLURM will try to satisfy a combination of
`mem_mb_per_cpu` and `cpus_per_task` and `nodes` if the `nodes` parameter is not given.

Note that it is usually advisable to avoid specifying SLURM (and compute
infrastructure) specific resources (like `constraint`) inside your
workflow because that can limit the reproducibility when executed on other systems.
Consider using the `--default-resources` and `--set-resources` flags to specify such resources
at the command line or (ideally) within a [profile](https://snakemake.readthedocs.io/en/latest/executing/cli.html#profiles).

A sample configuration file as specified by the `--workflow-profile` flag might look like this:

```YAML
default-resources:
    slurm_partition: "<your default partition>"
    slurm_account:   "<your account>

set-resources:
    <rulename>:
        slurm_partition: "<other partition>" # deviating partition for this rule
        runtime: 60 # 1 hour
        slurm_extra: "'--nice=150'"
        mem_mb_per_cpu: 1800
        cpus_per_task: 40
```

#### Multicluster Support

For reasons of scheduling multicluster support is provided by the `clusters` flag in resources sections. Note, that you have to write `clusters`, not `cluster`! 

#### Additional Custom Job Configuration

SLURM installations can support custom plugins, which may add support
for additional flags to `sbatch`. In addition, there are various batch options not directly supported via the resource definitions
shown above. You may use the `slurm_extra` resource to specify
additional flags to `sbatch`:

``` python
rule myrule:
    input: ...
    output: ...
    resources:
        slurm_extra="'--qos=long --mail-type=ALL --mail-user=<your email>'"
```

Again, rather use a [profile](https://snakemake.readthedocs.io/en/latest/executing/cli.html#profiles) to specify such resources.

### Software Recommendations

#### Conda

Snakemake's default software deployment uses conda, hence `snakemake --sdm conda ...` [works as intended](https://snakemake.readthedocs.io/en/stable/snakefiles/deployment.html). On a cluster sometimes a file system other than `HOME` needs to be in dicated (e.g. because of quotas). In this case, `--conda-prefix /other/filesystem` might be a solution. You can use `--conda-cleanup-pkgs` to further save space by removing downloaded tarballs.

#### Using Cluster Environment:  Modules

HPC clusters provide so-called environment modules. Some clusters do not allow using Conda (and its derivatives). In this case, or when a particular software is not provided by a Conda channel, Snakemake can be instructed to use environment modules. The `--sdm env-modules` flag will trigger loading modules defined for a specific rule, e.g.:

```
rule ...:
   ...
   envmodules:
       "bio/VinaLC"
```

This will, internally, trigger a `module load bio VinaLC` immediately prior to execution. 

Note, that 
- environment modules are best specified in a configuration file.
- Using environment modules can be combined with conda and apptainer (`--sdm env-modules conda apptainer`), which will then be only used as a fallback for rules not defining environment modules.

### Inquiring about Job Information and Adjusting the Rate Limiter

The executor plugin for SLURM uses unique job names to inquire about job status. It ensures inquiring about job status for the series of jobs of a workflow does not put too much strain on the batch system's database. Human readable information is stored in the comment of a particular job. It is a combination of the rule name and wildcards. You can ask for it with the `sacct` or `squeue` commands, e.g.:

``` console 
sacct -o JobID,State,Comment%40
```

Note, the "%40" after `Comment` ensures a width of 40 characters. This setting may be changed at will. If the width is too small, SLURM will abbreviate the column with a `+` sign.

For running jobs, you can use the squeue command:

``` console
squeue -u $USER -o %i,%P,%.10j,%.40k
```

Here, the `.<number>` settings for the ID and the comment ensure a sufficient width, too.

Snakemake will check the status of your jobs 40 seconds after submission. Another attempt will be made in 10 seconds, then 20, etcetera with an upper limit of 180 seconds.

### Using Profiles

When using [profiles](https://snakemake.readthedocs.io/en/stable/executing/cli.html#profiles), a command line may become shorter. A sample profile could look like this:

```YAML
executor: slurm
latency-wait: 5
default-storage-provider: fs
shared-fs-usage:
  - persistence
  - software-deployment
  - sources
  - source-cache
remote-job-local-storage-prefix: "<your node local storage prefix>"
local-storage-prefix: "<your local storage prefix, e.g. on login nodes>"
```

The entire configuration will set the executor to SLURM executor, ensures sufficient file system latency and allow automatic stage-in of files using the [file system storage plugin](https://github.com/snakemake/snakemake-storage-plugin-fs).

On a cluster with a scratch directory per job id, the prefix within jobs might be:

```YAML
remote-job-local-storage-prefix: "<scratch>/$SLURM_JOB_ID"
```

On a cluster with a scratch directory per user, the prefix within jobs might be:

```YAML
remote-job-local-storage-prefix: "<scratch>/$USER"
```

Note, that the path `<scratch>` needs to be taken from a specific cluster documentation.

Further note, that you need to set the `SNAKEMAKE_PROFILE` environment variable in your `~/.bashrc` file, e.g.:

```console
export SNAKEMAKE_PROFILE="$HOME/.config/snakemake"
```

==This is ongoing development. Eventually you will be able to annotate different file access patterns.==

### Log Files - Getting Information on Failures

Snakemake, via this SLURM executor, submits itself as a job. This ensures that all features are preserved in the job context. SLURM requires a logfile to be written for _every_ job. This is redundant information and only contains the Snakemake output already printed on the terminal. If a rule is equipped with a `log` directive, SLURM logs only contain Snakemake's output.

This executor will remove SLURM logs of sucessful jobs immediately when they are finished. You can change this behaviour with the flag `--slurm-keep-successful-logs`. A log file for a failed job will be preserved per default for 10 days. You may change this value using the `--slurm-delete-logfiles-older-than` flag.

The default location of Snakemake log files are relative to the directory where the workflow is started or relative to the directory indicated with `--directory`. SLURM logs, produced by Snakemake, can be redirected using `--slurm-logdir`. If you want avoid that log files accumulate in different directories, you can store them in your home directory. Best put the parameter in your profile then, e.g.:

```YAML
slurm-logdir: "/home/<username>/.snakemake/slurm_logs"
```

### Retries - Or Trying again when a Job failed

Some cluster jobs may fail. In this case Snakemake can be instructed to try another submit before the entire workflow fails, in this example up to 3 times:

```console
snakemake --retries=3
```

If a workflow fails entirely (e.g. when there are cluster failures), it can be resumed as any other Snakemake workflow:

```console
snakemake ... --rerun-incomplete
# or the short-hand version
snakemake ... --ri
```

The "requeue" option allows jobs to be resubmitted automatically if they fail or are preempted. This is similar to Snakemake's `--retries`, except a SLURM job will not be considered failed and priority may be accumulated during pending. This might be the default on your cluster, already. You can check your cluster's requeue settings with 

```console
scontrol show config | grep Requeue
```

This requeue feature is integrated into the SLURM submission command, adding the --requeue parameter to allow requeuing after node failure or preemption using:

```console
snakemake --slurm-requeue ...
```

To prevent failures due to faulty parameterization, we can dynamically adjust the runtime behaviour:

### Dynamic Parameterization

Using dynamic parameterization we can react on different different inputs and prevent our HPC jobs from failing.

#### Adjusting Memory Requirements

Input size of files may vary. [If we have an estimate for the RAM requirement due to varying input file sizes, we can use this to dynamically adjust our jobs.](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html#dynamic-resources)

#### Adjusting Runtime

Runtime adjustments can be made in a Snakefile:

```Python
def get_time(wildcards, attempt):
    return f"{1 * attempt}h"

rule foo:
    input: ...
    output: ...
    resources:
        runtime=get_time
    ...
```

or in a workflow profile

```YAML
set-resources:
    foo:
        runtime: f"{1 * attempt}h"
```

Be sure to use sensible settings for your cluster and make use of parallel execution (e.g. threads) and [global profiles](#using-profiles) to avoid I/O contention. 


### Nesting Jobs (or Running this Plugin within a Job)

Some environments provide a shell within a SLURM job, for instance, IDEs started in on-demand context. If Snakemake attempts to use this plugin to spawn jobs on the cluster, this may work just as intended. Or it might not: depending on cluster settings or individual settings, submitted jobs may be ill-parameterized or will not find the right environment.

If the plugin detects to be running within a job, it will therefore issue a warning and stop for 5 seconds.


### Summary:

When put together, a frequent command line looks like:

```console
$ snakemake --workflow-profile <path> \
> -j unlimited \ # assuming an unlimited number of jobs
> --workflow-profile <profile directory with a `config.yaml`>
> --configfile config/config.yaml \
> --directory <path> # assuming a data path on a different file system than the workflow
```

### Frequently Asked Questions

#### Should I run Snakemake on the Login Node of my Cluster?

We recommend running Snakemake on the login node. Occasionally, HPC administrators are opposed to having a job shepherd running on the login node, since computational tasks should not be executed there.

We therefore provide this table of measurements:

| Workflow | Version | Number of local rules  | Total Runtime (hh:mm:ss) | CPU-Time on the login node [user + system] (s) | Fraction |
|:-------------|:---------------|:---------------|:-------------|:-------------|:-------------:|
| [Transcriptome DiffExp + Fusion detection](https://github.com/snakemake-workflows/transcriptome-differential-expression) | 0.2.0 | 12 | 9:15:43 | 225.15 | 0.68 % |

If you want to contribute similar statistics, please run `/usr/bin/time -v snakemake ...` on your cluster and submit your stats as an [issue to the plugin repo on GitHub](https://github.com/snakemake/snakemake-executor-plugin-slurm/issue).

