## Specifying Account and Partition

Most SLURM clusters have two mandatory resource indicators for
accounting and scheduling, [Account]{.title-ref} and
[Partition]{.title-ref}, respectively. These resources are usually
omitted from Snakemake workflows in order to keep the workflow
definition independent from the platform. However, it is also possible
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

Most jobs will be carried out by programs which are either single core
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

This will give jobs from this rule 14GB of memory and 8 CPU cores. It is
advisable to use reasonable default resources, such that you don\'t need
to specify them for every rule. Snakemake already has reasonable
defaults built in, which are automatically activated when using any non-local executor
(hence also with slurm).

## MPI jobs {#cluster-slurm-mpi}

Snakemake\'s Slurm backend also supports MPI jobs, see
`snakefiles-mpi`{.interpreted-text role="ref"} for details. When using
MPI with slurm, it is advisable to use `srun` as MPI starter.

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

Note that the `-n {resources.tasks}` is not necessary in case of SLURM,
but it should be kept in order to allow execution of the workflow on
other systems, e.g. by replacing `srun` with `mpiexec`:

``` console
$ snakemake --set-resources calc_pi:mpi="mpiexec" ...
```

## Advanced Resource Specifications

A workflow rule may support a number of
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
`mem_mb_per_cpu` are mutually exclusive, too. You can only reserve
memory a compute node has to provide or the memory required per CPU
(SLURM does not make any distinction between real CPU cores and those
provided by hyperthreads). SLURM will try to satisfy a combination of
`mem_mb_per_cpu` and `cpus_per_task` and `nodes`, if `nodes` is not
given.

Note that it is usually advisable to avoid specifying SLURM (and compute
infrastructure) specific resources (like `constraint`) inside of your
workflow because that can limit the reproducibility on other systems.
Consider using the `--default-resources` and `--set-resources` flags to specify such resources
at the command line or (ideally) within a [profile](https://snakemake.readthedocs.io/en/latest/executing/cli.html#profiles).

## Additional custom job configuration

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

## Software Recommendations

### Conda, Mamba, Micromamba

While Snakemake mainly relies on Conda for reproducible execution, many clusters impose file number limits in their "HOME" directory. You can resort to[micromamba](https://mamba.readthedocs.io/en/latest/user_guide/micromamba.html) in place of [mamba](https://mamba.readthedocs.io/en/latest/), which is recommended by Snakemake: Micromamba does not save all the package files, hence users do not have to clean up manually. In this case, you need to install your environment for a workflow manually. Alternatively, run `mamba clean -a` occasionally for your environments.

Note, `snakemake --use-conda ...` works as intended.

To ensure the working of this plugin, install it in your base environment for the desired workflow.


### Using Cluster Environment Modules

HPC clusters provide so-called environment modules. Some clusters do not allow using Conda (and its derivatives). In this case, Snakemake can be instructed to use environment modules. The `--sdm envmodules` flag will trigger loading modules defined for a specific rule, e.g.:

```
rule ...:
   ...
   envmodules:
       "bio/VinaLC"
```

This will, internally, trigger a `module load bio`/VinaLC` immediately prior to execution. 

Note, that 
- environment modules are best specified in a configuration file.
- `--use-envmodules` can be combined with `--use-conda` and `--use-singularity`, which will then be only used as a fallback for rules not defining environment modules.
