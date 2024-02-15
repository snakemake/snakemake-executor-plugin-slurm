# The Executor Plugin for HPC Clusters using the SLURM Batch System

## The general Idea

To use this plugin, log in to your cluster's head node (sometimes called "login" node), activate your environment as usual and start Snakemake. Snakemake will then submit your jobs as cluster jobs.

## Specifying Account and Partition

Most SLURM clusters have two mandatory resource indicators for
accounting and scheduling, the account and a
partition, respectively. These resources are usually
omitted from Snakemake workflows in order to keep the workflow
definition independent of the platform. However, it is also possible
to specify them inside of the workflow as resources in the rule
definition (see `snakefiles-resources`{.interpreted-text role="ref"}).

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

## Ordinary SMP jobs

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

## MPI jobs

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

## Advanced Resource Specifications

A workflow rule may support several
[resource specifications](https://snakemake.readthedocs.io/en/latest/snakefiles/rules.html#resources).
For a SLURM cluster, a mapping between Snakemake and SLURM needs to be performed.

You can use the following specifications:

| SLURM        | Snakemake  | Description              |
|----------------|------------|---------------------------------------|
| `--partition`  | `slurm_partition`    | the partition a rule/job is to use |
| `--time`  | `runtime`  | the walltime per job in minutes       |
| `--constraint`   | `constraint`        | may hold features on some clusters    |
| `--mem`        | `mem`, `mem_mb`   | memory a cluster node must      |
|                |            | provide (`mem`: string with unit), `mem_mb`: i                               |
| `--mem-per-cpu`              | `mem_mb_per_cpu`     | memory per reserved CPU               |
| `--ntasks`     | `tasks`    | number of concurrent tasks / ranks    |
| `--cpus-per-task`       | `cpus_per_task`      | number of cpus per task (in case of SMP, rather use `threads`)   |
| `--nodes` | `nodes`    | number of nodes                       |

Each of these can be part of a rule, e.g.:

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

## Additional Custom Job Configuration

SLURM installations can support custom plugins, which may add support
for additional flags to `sbatch`. In addition, there are various
`sbatch` options not directly supported via the resource definitions
shown above. You may use the `slurm_extra` resource to specify
additional flags to `sbatch`:

``` python
rule myrule:
    input: ...
    output: ...
    resources:
        slurm_extra="--qos=long --mail-type=ALL --mail-user=<your email>"
```

Again, rather use a [profile](https://snakemake.readthedocs.io/en/latest/executing/cli.html#profiles) to specify such resources.

## Inquiring about Job Information and Adjusting the Rate Limiter

The executor plugin for SLURM uses unique job names to inquire about job status. It ensures inquiring about job status for the series of jobs of a workflow does not put too much strain on the batch system's database. Human readable information is stored in the comment of a particular job. It is a combination of the rule name and wildcards. You can ask for it with the `sacct` or `squeue` commands, e.g.:

``` console
sacct -o JobID,State,Comment%40
```

Note, the "%40" after `Comment` ensures a width of 40 characters. This setting may be changed at will. If the width is too small, SLURM will abbreviate the column with a `+` sign.

For running jobs, the `squeue` command:

``` console
squeue -u $USER -o %i,%P,%.10j,%.40k
```

Here, the `.<number>` settings for the ID and the comment ensure a sufficient width, too.

Snakemake will check the status of your jobs 40 seconds after submission. Another attempt will be made in 10 seconds, then 20, etcetera with an upper limit of 180 seconds. 