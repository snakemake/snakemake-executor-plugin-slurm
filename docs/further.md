### How this Plugin works

In this plugin, Snakemake submits itself as a job script when operating on an HPC cluster using the SLURM batch system.
Consequently, the SLURM log file will duplicate the output of the corresponding rule.
To avoid redundancy, the plugin deletes the SLURM log file for successful jobs, relying instead on the rule-specific logs.

Remote executors submit Snakemake jobs to ensure unique functionalities — such as piped group jobs and rule wrappers — are available on cluster nodes.
The memory footprint varies based on these functionalities; for instance, rules with a run directive that import modules and read data may require more memory.

### Installation

Installing this plugin into your Snakemake base environment using conda will also install the 'jobstep' plugin, utilized on cluster nodes.
Additionally, we recommend installing the `snakemake-storage-plugin-fs`, which will automate transferring data from the main file system to slurm execution nodes and back (stage-in and stage-out).

### Contributions

We welcome bug reports, feature requests, and pull requests!
Please report issues specific to this plugin [in the plugin's GitHub repository](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues).
Additionally, bugs related to the plugin can originate in the following repositories:

* [`snakemake-executor-plugin-slurm-jobstep`](https://github.com/snakemake/snakemake-executor-plugin-slurm-jobstep), which runs snakemake within slurm jobs
* [`snakemake-interface-executor-plugins`](https://github.com/snakemake/snakemake-interface-executor-plugins), which connects it to the main snakemake application
* [`snakemake`](https://github.com/snakemake/snakemake) itself

If you can pinpoint the exact repository your issue pertains to, please file it there.
If you are unsure, [create a new issue here](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues), and we will direct you to the correct repo.

For issues that are specific to your local cluster-setup, please contact your cluster administrator.

### Example

A command line invocation of the plugin could look like:

```console
$ snakemake --executor slurm \
> -j unlimited \
> --workflow-profile <profile directory with a `config.yaml`> \
> --configfile config/config.yaml \
> --directory <path>
```

This example assumes no limit for submitted jobs (`-j unlimited`). Any number, e.g. `-j 150`, will throttle a workflow to this number of concurrent jobs.
Furthermore, on many clusters we must assume separation of workflows and data. Use the `--directory <path>` flag to point to a file system that contains your data.

### Configuration

Snakemake offers great [capabilities to specify and thereby limit resources](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html#resources) used by a workflow as a whole and by individual jobs.
The SLURM executor plugin takes care of mapping all the [standard resources to SLURM specific configurations](#standard-resources) and also [provides control over SLURM-specific resources and configurations](#slurm-specific-resources).

#### Where to set Resources and Configurations

Required resources and configuration options can be specified in three different places:

1. In the `threads:` and `resources:` sections of a rule definition (in a `Snakefile` or an `include:`d `.smk` file).
2. Via [`.yaml` profile files that can be defined on the workflow, user-wide or system-wide level](https://snakemake.readthedocs.io/en/stable/executing/cli.html#profiles)
3. On the command-line, via the [arguments `--default-resources <resource>=<value>`, `--set-resources <rule_name>:<resource>=<value>` and `--set-threads <rule_name>:<resource>=<value>`](https://snakemake.readthedocs.io/en/stable/executing/cli.html#snakemake.cli-get_argument_parser-execution).

On each of these levels, you can set rule-specific limits via `set-resources` and [`set-threads` (for cpus)](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html#threads).
In profiles and on the command line, you can additionally set default resources and threads.
See the [snakemake documentation on profiles](https://snakemake.readthedocs.io/en/stable/executing/cli.html#profiles) for further details.

#### Dynamic Resource Specification

How and where you set configurations on factors like file size or increasing the runtime with every `attempt` of running a job (if [`--retries` is greater than `0`](https://snakemake.readthedocs.io/en/stable/executing/cli.html#snakemake.cli-get_argument_parser-behavior)).
[There are detailed examples for these in the snakemake documentation.](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html#dynamic-resources)

#### Automatic Partition Selection

The SLURM executor plugin supports automatic partition selection based on job resource requirements, via the command line option `--slurm-partition-config`. This feature allows the plugin to choose the most appropriate partition for each job, without the need to manually specify partitions for different job types. This also enables variable partition selection as a job's resource requirements change based on [dynamic resources](#dynamic-resource-specification), ensuring that jobs are always scheduled to an appropriate partition.

*Jobs that explicitly specify a `slurm_partition` resource will bypass automatic selection and use the specified partition directly.*

> **Note:** Partition selection supports specifying the target cluster using any of the resource keys `cluster`, `clusters`, or `slurm_cluster` in your workflow profile or the partition configuration file. All three are treated equivalently by the plugin.

##### Partition Limits Specification

To enable automatic partition selection, create a YAML configuration file that defines the available partitions and their resource limits. This file should be structured as follows:

```yaml
partitions:
  some_partition:
    max_runtime: 100
  another_partition:
    ...
```
Where `some_partition` and `another_partition` are the names of the partition on your cluster, according to `sinfo`.

The following limits can be defined for each partition:

| Parameter               | Type      | Description                        | Default   |
| ----------------------- | --------- | ---------------------------------- | --------- |
| `max_runtime`           | int/str   | Maximum walltime                   | unlimited |
| `max_mem_mb`            | int       | Maximum total memory in MB         | unlimited |
| `max_mem_mb_per_cpu`    | int       | Maximum memory per CPU in MB       | unlimited |
| `max_cpus_per_task`     | int       | Maximum CPUs per task              | unlimited |
| `max_nodes`             | int       | Maximum number of nodes            | unlimited |
| `max_tasks`             | int       | Maximum number of tasks            | unlimited |
| `max_tasks_per_node`    | int       | Maximum tasks per node             | unlimited |
| `max_threads`           | int       | Maximum threads per node           | unlimited |
| `max_gpu`               | int       | Maximum number of GPUs             | 0         |
| `available_gpu_models`  | list[str] | List of available GPU models       | none      |
| `max_cpus_per_gpu`      | int       | Maximum CPUs per GPU               | unlimited |
| `supports_mpi`          | bool      | Whether MPI jobs are supported     | true      |
| `max_mpi_tasks`         | int       | Maximum MPI tasks                  | unlimited |
| `available_constraints` | list[str] | List of available node constraints | none      |
| `cluster` | str       | Cluster name in multi-cluster setup | none |

Note: the `max_runtime` definition may contain 
  - Numeric values (assumed to be in minutes): 120, 120.5
  - Snakemake-style time strings: "6d", "12h", "30m", "90s", "2d12h30m"
  - SLURM time formats:
    - "minutes" (e.g., "60")
    - "minutes:seconds" (interpreted as hours:minutes, e.g., "60:30")
    - "hours:minutes:seconds" (e.g., "1:30:45")
    - "days-hours" (e.g., "2-12")
    - "days-hours:minutes" (e.g., "2-12:30")
    - "days-hours:minutes:seconds" (e.g., "2-12:30:45")

They are all auto-converted to minutes. Seconds are rounded to the nearest value in minutes.

##### Example Partition Configuration

```yaml
partitions:
  standard:
    max_runtime: 720  # 12 hours
    max_mem_mb: 64000  # 64 GB
    max_cpus_per_task: 24
    max_nodes: 1
    
  highmem:
    max_runtime: 1440  # 24 hours
    max_mem_mb: 512000  # 512 GB
    max_mem_mb_per_cpu: 16000
    max_cpus_per_task: 48
    max_nodes: 1
    
  gpu:
    max_runtime: 2880  # 48 hours
    max_mem_mb: 128000  # 128 GB
    max_cpus_per_task: 32
    max_gpu: 8
    available_gpu_models: ["a100", "v100", "rtx3090"]
    max_cpus_per_gpu: 8
```

The plugin supports automatic partition selection on clusters with SLURM multi-cluster setup. You can specify which cluster each partition belongs to in your partition configuration file:

```yaml
partitions:
  d-standard:
    cluster: "deviating"
    max_runtime: "6d"
    max_nodes: 1
    max_threads: 127
  d-parallel:
    cluster: "deviating"
    supports_mpi: true
    max_threads: 128
    max_runtime: "6d"
  standard:
    cluster: "other"
    max_runtime: "6d"
    max_nodes: 1
    max_threads: 127
  parallel:
    cluster: "other"
    supports_mpi: true
    max_threads: 128
    max_runtime: "6d"
```


##### How Partition Selection Works

When automatic partition selection is enabled, the plugin evaluates each job's resource requirements against the defined partition limits to ensure the job is placed on a partition that can accommodate all of its requirements. When multiple partitions are compatible, the plugin uses a scoring algorithm that favors partitions with limits closer to the job's needs, preventing jobs from being assigned to partitions with excessively high resource limits.

The scoring algorithm calculates a score by summing the ratios of requested resources to partition limits (e.g., if a job requests 8 CPUs and a partition allows 16, this contributes 0.5 to the score). Higher scores indicate better resource utilization, so a job requesting 8 CPUs would prefer a 16-CPU partition (score 0.5) over a 64-CPU partition (score 0.125).

##### Fallback Behavior

If no suitable partition is found based on the job's resource requirements, the plugin falls back to the default SLURM behavior, which typically uses the cluster's default partition or any partition specified explicitly in the job's resources.


#### Standard Resources

The SLURM executor plugin should respect all of [snakemake's standard resources](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html#standard-resources) by default.
These are usually set directly in the workflow rule, optimally as [dynamic resources](#dynamic-resource-specification) that will, for example, adapt to input file sizes.
The plugin understands all of snakemake's standard resources.
Where appropriate, they are mapped to respective configurations in SLURM:

| Snakemake            | Description                             | SLURM              |
|----------------------|-----------------------------------------|--------------------|
| `gpu`                | number of gpus needed                   | `--gpus`           |
| `mem`, `mem_mb`      | memory a cluster node must provide      | `--mem`            |
|                      | (`mem`: string with unit, `mem_mb`: int)|                    |
| `runtime`            | the walltime per job in minutes         | `--time`           |

One classical example is the `runtime` resource that defines the walltime limit for a rule, which gets translated to the `--time` argument of SLURM.
Similarly, memory requirements for rules can be specified as `mem_mb` (total memory in MB, mapped to SLURM's `--mem`) or `mem_mb_per_cpu` (memory per CPU in MB, mapped to SLURM's `--mem-per-cpu`).

#### SLURM-specific Resources

The resources described here are usually omitted from reusable Snakemake workflows, as they are platform-specific.
Instead, it makes sense to set them for the system that a workflow is run on, which can be done in profiles at the system, user or workflow level.
These are the available options, and the SLURM `sbatch` command line arguments that the plugin maps them to:

| Snakemake plugin     | Description                         | SLURM               |
|----------------------|-------------------------------------|---------------------|
| `clusters` (or `cluster` or `slurm_cluster`)           | list of clusters that (a) job(s)    | `--clusters`        |
|                      | can run on                          |                     |
| `constraint`         | requiring particular node features  | `--constraint`/`-C` |
|                      | for job execution                   |                     |
| `cpus_per_task`      | number of CPUs per task (in case of | `--cpus-per-task`   |
|                      | SMP, rather use `threads`)          |                     |
| `mem_mb_per_cpu`     | memory per reserved CPU             | `--mem-per-cpu`     |
| `nodes`              | number of nodes                     | `--nodes`           |
| `slurm_account`      | account for resource usage tracking | `--account`         |
| `slurm_partition`    | partition/queue to submit job(s) to | `--partition`       |
| `slurm_requeue`      | handle `--retries` with SLURM       | `--requeue`                    |
|                      | functionality                       |                     |
| `tasks`              | number of concurrent tasks / ranks  | `--ntasks`          |

The use of these options is explained in the documentation below.
But whenever necessary, you can [find more details regarding the SLURM `sbatch` command line arguments in the slurm documentation](https://slurm.schedmd.com/sbatch.html#SECTION_OPTIONS).

##### `constraint`
 
Administrators can annotate SLURM nodes with features, which are basically string tags that inform about some kind of capability.
Via the plugin resource `constraint`, users can specify any available feature names as required by their job.
For details on the constraint syntax, see the [documentation of the SLURM `sbatch` command-line argument `--constraint`](https://slurm.schedmd.com/sbatch.html#SECTION_OPTIONS), to which the plugin passes on the `constraint` resource.

##### `clusters`

With SLURM, it is possible to [federate multiple clusters](https://slurm.schedmd.com/multi_cluster.html).
This can allow users to submit jobs to a cluster different from the one they run their job submission commands.
If this is available on your cluster, this resource accepts a string with a comma separated list of cluster names, which is passed on to the [SLURM `sbatch` command-line argument `--clusters`](https://slurm.schedmd.com/sbatch.html#SECTION_OPTIONS).

We allow `clusters` or `cluster` or `slurm_cluster` as there are multiple conventions.

.. note:: While it is possible to submit to more than one cluster in prinicple, not all SLURM multicluster setups will support this.


##### `slurm_partition`

In SLURM, [a `partition` designates a subset of compute nodes](https://slurm.schedmd.com/quickstart_admin.html#Config), grouped for specific purposes (such as high-memory or GPU tasks).
Thus, a `partition` in SLURM is similar to a `queue` in other cluster systems.
In snakemake, you can specify the partition that jobs are supposed to run in as a resource with the name `slurm_partition` (which is mapped to the SLURM flag: `--partition`/`-p`).

##### `slurm_account`

In SLURM, an `account` can be used for [collection users' resource usage](https://slurm.schedmd.com/accounting.html), which can in turn be used to implement fair share policies.
If and how this is used depends on the local cluster setup.

It might be required or desirable for you to specify a `slurm_account`.
For example, this you might want to set the account per user, or even per workflow, when dealing with multiple SLURM accounts per user.
If you do not deliberately set the snakemake resource `slurm_account`, the plugin does its best to _guess_ your account (however, this can fail).

By contrast, some clusters _do not_ allow users to set their account or partition; for example, because they have a pre-defined default per user.
In such cases, where the plugin's default behavior would interfere with your setup or requirements, you can use the `--slurm-no-account` flag to turn it off.

##### Passing Commands as Scripts: `--slurm-pass-command-as-script`

When this flag is enabled, the command that Snakemake would normally pass directly to `sbatch` via the `--wrap` option is instead written into a small temporary shell script which is submitted with `sbatch <script>`.

Why this exists: Some SLURM installations or cluster configurations impose limits on the length or characters allowed in the `--wrap` argument or inlined command strings. This happens when administrators deliberately set the `slurm_max_submit_line_size` in their SLURM configuration to a low value. Passing the job command as a script avoids those limitations.

##### Wait Times and Frequencies

There are a number of wait times and frequencies that users can tune to their local cluster setup.
Snakemake and the plugin try to provide sensible defaults.
But especially if you become aware of your local cluster being overwhelmed with job status checks, you might want to decrease the respective frequencies further.
Or if you are a system administrator, you can adjust the respective defaults in a system-wide configuration profile, to reduce strain on your scheduling database.

Some of these are [central snakemake command-line arguments determining its behavior](https://snakemake.readthedocs.io/en/stable/executing/cli.html#snakemake.cli-get_argument_parser-behavior):

* With `--seconds-between-status-checks`, you set the wait time between rounds of status checks of all submitted jobs.
  In the SLURM plugin, this is currently fixed to a minimum of 40 seconds.
  To reduce the burden of regular status checks,  this time automatically increases in 10 second steps with every status check whenever no finished jobs are found.
  But this will never go beyond a wait time of 180 seconds (3 minutes), to avoid long wait times once jobs do finish.
  Also, as soon as finished jobs are found, this gets reset to 40 seconds.
* With `--max-status-checks-per-second`, you can limit the frequency of individual attempts of querying the job status database within a round of status checks.
  Within a round, repeated attempts will happen whenever the `sacct` command used for the status query comes back with an error.

Or you might sometimes want to decrease certain wait times for small workflow runs during development.
For example, the plugin waits 40 seconds before performing the first job status check.
You can reduce this value with the `--slurm-init-seconds-before-status-checks=<time in seconds>` option, to minimize turn-around times for test runs.

##### Retry failed Jobs

When running workflows, jobs will occasionally fail.
Snakemake provides mechanisms to handle such failures gracefully, for example by resuming a workflow from the last succesfully created outputs.
But it can even retry failed jobs within a single workflow run, for example if you expect unpredictable failures; or if you want to increase some limiting resource requirements with each attempt, because jobs will rarely exceed an otherwise sensible limit.
For this, have a look at the [documentation of the snakemake argument `--retries`](https://snakemake.readthedocs.io/en/stable/executing/cli.html#snakemake.cli-get_argument_parser-behavior) and set it to a value above `0`.

In addition, SLURM offers a built-in job requeue feature.
You can check whether your cluster has this enabled with:

```console
scontrol show config | grep Requeue
```

This should show a numerical value for the `JobRequeue` parameter, indicating the number of requeues for individual jobs.  
Any number greater than 1 will cause SLURM to requeue jobs on your cluster upon failure or preemption this many times. (Your cluster may specify additional parameters.)

If enabled, this feature allows jobs to be automatically resubmitted if they fail or are preempted - you do not need to rely on this plugin in this case.

If your cluster does not support automated requeuing, you can ask the plugin to requeue preempted jobs with the `--slurm-requeue` flag: 

```console
snakemake --slurm-requeue ...
```

This flag effectively does not consider failed SLURM jobs or preserves job IDs and priorities or allows job priority to be accumulated while pending.


#### MPI-specific Resources

Snakemake's SLURM executor plugin supports the execution of MPI ([Message Passing Interface](https://en.wikipedia.org/wiki/Message_Passing_Interface)) jobs.

By default, jobs can only run on a single cluster node (or machine) and parallelization is thus limited by the maximum number of cores that is available on any machine in the cluster.
MPI jobs enable parallel computations spanning across multiple nodes, thus potentially parallelizing to more cores than any machine in you cluster can offer.
[See the main documentation section of Snakemake, too.](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html#mpi-support)

| Snakemake     | Description                                 |
|---------------|---------------------------------------------|
| `mpi`         | MPI launcher command, for example `srun`    |
| `tasks`       | The number of SLURM tasks - equivalent to MPI-ranks |


To effectively utilize MPI within a Snakemake workflow, it's recommended to use `srun` as the MPI launcher when operating in a SLURM environment.
However, some programs do not work well with this MPI launcher or require a detailed topology layout - this can be added to the `srun` statement, if required.

Here's an example of defining an MPI rule in a Snakefile:

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

In this configuration:

- `tasks=10` specifies the number of MPI tasks (ranks) to be allocated for the job.
- `mpi="srun"` sets srun as the MPI launcher, which is optimal for SLURM-managed clusters.
- The `shell` directive constructs the command to execute the MPI program, utilizing the specified resources.

##### Portability Considerations

While SLURM's `srun` effectively manages task allocation, including the `-n {resources.tasks}` option ensures compatibility with some applications that may rely on `mpiexec` or similar MPI launchers.
This approach maintains the portability of your workflow across different computing environments.

To adapt the workflow for an application using `mpiexec`, you can override the `mpi` resource at runtime:

``` console
$ snakemake --set-resources calc_pi:mpi="mpiexec" ...
```

##### Resource Specifications for MPI Jobs

When configuring MPI jobs, it's essential to accurately define the resources to match the requirements of your application.
The tasks resource denotes the number of MPI ranks.
For hybrid applications that combine MPI with multi-threading, you can specify both `tasks` and `cpus_per_task`:

```YAML
set-resources:
    mpi_rule:
        tasks: 2048

    hybrid_mpi_rule:
        tasks: 1024
        cpus_per_task: 2
```

In this setup:

- `mpi_rule` is allocated 2048 MPI tasks.
- `hybrid_mpi_rule` is assigned 1024 MPI tasks, with each task utilizing 2 CPU cores, accommodating applications that employ both MPI and threading.

For advanced configurations, such as defining specific node distributions or memory allocations, you can utilize the `slurm_extra` parameter to pass additional SLURM directives, tailoring the job submission to the specific needs of your computational tasks.

#### GPU Jobs

Integrating GPU resources into Snakemake workflows on SLURM-managed clusters requires precise configuration to ensure optimal performance.
SLURM facilitates GPU allocation using the `--gres` (generic resources) or `--gpus` flags, and Snakemake provides corresponding mechanisms to request these resources within your workflow rules.
The preferred method for requesting GPU resources -- whether using `gpu` or `gres` -- depends on your specific cluster configuration and scheduling policies.
Consult your cluster administrator or the cluster's documentation to determine the best approach for your environment.
Additionally, while Snakemake internally recognizes the `gpu_manufacturer` resource, SLURM does not distinguish between GPU model and manufacturer in its resource allocation.
Therefore, it's essential to align your Snakemake resource definitions with your cluster's SLURM configuration to ensure accurate resource requests.

By carefully configuring GPU resources in your Snakemake workflows, you can optimize the performance of GPU-accelerated tasks and ensure efficient utilization of computational resources within SLURM-managed clusters.


##### Specifying GPU Resources in Snakemake

To request GPU resources in Snakemake, you can utilize the `gpu` resource within the resources section of a rule.
This approach allows you to specify the number of GPUs and, optionally, the GPU model.
For example:

```Python
rule gpu_task:
    input:
        "input_file"
    output:
        "output_file"
    resources:
        gpu=2,
        gpu_model="a100"
    shell:
        "your_gpu_application --input {input} --output {output}"
```

In this configuration:

- `gpu=2` requests two GPUs for the job.
- `gpu_model="a100"` specifies the desired GPU model.

Snakemake translates these resource requests into SLURM's `--gpus` flag, resulting in a submission command like sbatch `--gpus=a100:2`.
It is important to note that the `gpu` resource must be specified as a numerical value.

.. note:: Internally, Snakemake knows the resource `gpu_manufacturer`, too.
However, SLURM does not know the distinction between model and manufacturer.
Essentially, the preferred way to request an accelerator will depend on your specific cluster setup.

##### Alternative Method: Using the gres Resource

Alternatively, you can define GPU requirements using the gres resource, which corresponds directly to SLURM's `--gres` flag.
The syntax for this method is either `<resource_type>:<number>` or `<resource_type>:<model>:<number>`.
For instance:

```Python
rule gpu_task:
    input:
        "input_file"
    output:
        "output_file"
    resources:
        gres="gpu:a100:2"
    shell:
        "your_gpu_application --input {input} --output {output}"
```

Here, `gres="gpu:a100:2"` requests two GPUs of the a100 model.
This approach offers flexibility, especially on clusters where specific GPU models are available.

##### Additional Considerations: CPU Allocation per GPU

When configuring GPU jobs, it's crucial to allocate CPU resources appropriately to ensure that GPU tasks are not bottlenecked by insufficient CPU availability.
You can specify the number of CPUs per GPU using the `cpus_per_gpu` resource:

```Python
rule gpu_task:
    input:
        "input_file"
    output:
        "output_file"
    resources:
        gpu=1,
        cpus_per_gpu=4
    shell:
        "your_gpu_application --input {input} --output {output}"
```

In this example, `cpus_per_gpu=4` allocates four CPU cores for each GPU requested.

.. note:: If `cpus_per_gpu` is set to a value less than or equal to zero, Snakemake will not include a CPU request in the SLURM submission, and the cluster's default CPU allocation policy will apply. The same applies to `tasks_per_gpu`. If set to zero or lower, the SLURM parameter `--ntasks-per-gpu` will not be set.

##### Sample Workflow Profile for GPU Jobs

To streamline the management of resource specifications across multiple rules, you can define a workflow profile in a `config.yaml` file:

```YAML
set-resources:
    single_gpu_rule:
        gpu: 1
        cpus_per_gpu: 4

    multi_gpu_rule:
        gpu: 2
        gpu_model: "a100"
        cpus_per_gpu: 8

    gres_request_rule:
        gres: "gpu:rtx3090:2"
        cpus_per_gpu: 6
```

In this configuration:

- `single_gpu_rule` requests one GPU with four CPUs allocated to it.
- `multi_gpu_rule` requests two GPUs of the a100 model, with eight CPUs allocated per GPU.
- `gres_request_rule` utilizes the `gres` resource to request two rtx3090 GPUs, with six CPUs allocated per GPU.

By defining these resource specifications in a profile, you maintain a clean and organized workflow, ensuring that resource allocations are consistent and easily adjustable.

### Running Jobs locally

In Snakemake workflows executed within cluster environments, certain tasks -- such as brief data downloads or plotting -- are better suited for local execution on the head node rather than being submitted as cluster jobs.
To designate specific rules for local execution, Snakemake offers the `localrules` directive.
For more details, refer to the [Snakemake documentation on local rules](https://snakemake.readthedocs.io/en/stable/snakefiles/rules.html#local-rules).
This directive allows you to specify a comma-separated list of rules that should run locally:

```Python
localrules: <rule_a>, <rule_b>
```

#### Example of Rule Definition with Resource Specifications

Here is how you can define a rule in Snakemake with specific SLURM resource requirements:

```Python
rule example_rule:
    input: "input_file.txt"
    output: "output_file.txt"
    resources:
        slurm_partition="compute",
        runtime=120,  # in minutes
        mem_mb=8000,  # total memory in MB
        cpus_per_task=4
    shell:
        "cmd {input} {output}"
```
In this example, the job will be submitted to the 'compute' partition, with a runtime limit of 120 minutes, 8 GB of total memory, and 4 CPUs allocated.

#### Important Considerations

Mutual Exclusivity of Memory Flags: SLURM's `--mem` and `--mem-per-cpu` flags are mutually exclusive.
Therefore, in Snakemake, you should use either `mem_mb` or `mem_mb_per_cpu`, but not both simultaneously.

Avoid Hardcoding Cluster-Specific Resources: To maintain workflow portability across different computing environments, it's advisable to avoid embedding cluster-specific resource requests (like constraint) directly within your workflow rules.
Instead, utilize Snakemake's `--default-resources` and `--set-resources` command-line options or define them within a configuration profile.

#### Using Configuration Profiles for Resource Specifications

A more flexible approach to manage resource specifications is by using Snakemake profiles.
These profiles allow you to define default resources and rule-specific overrides in a centralized configuration file, enhancing the portability and maintainability of your workflows.

Example of a Snakemake Profile Configuration (`config.yaml`):

```YAML
default-resources:
    slurm_partition: "default_partition"
    slurm_account: "your_account"
    mem_mb_per_cpu: 2000
    runtime: 60  # in minutes

set-resources:
    special_rule:
        slurm_partition: "high_mem_partition"
        runtime: 180  # in minutes
        mem_mb_per_cpu: 4000
        cpus_per_task: 8
```

In this configuration:
- Default resources are set for all rules, specifying the partition, account, memory per CPU, and runtime.
- The special_rule has customized resources, overriding the defaults where specified.

To apply this profile during workflow execution, use the --profile option:

```console
snakemake --profile path/to/profile
```

By leveraging configuration profiles, you can tailor resource specifications to different computing environments without modifying the core workflow definitions, thereby enhancing reproducibility and flexibility.

### Advanced Resource Specifications

#### Multicluster Support

In Snakemake, specifying the target cluster for a particular rule is achieved using the `cluster` resource flag within the rule definition.
This allows for precise control over job distribution across different clusters.
For example:

```YAML
default-resources:
    cluster: "default_cluster"

set-resources:
    specific_rule:
        cluster: "high_memory_cluster"
    another_rule:
        cluster: "gpu_cluster"
```

In this configuration, `default-resources` sets a default cluster for all rules, while `set-resources` specifies clusters for individual rules as needed.
This method ensures that your workflow is adaptable to various computing environments without hardcoding cluster-specific details into your `Snakefile`.
Multicluster support is achieved in a comma separated list:

```YAML
set-resources:
   multicluster_rule:
       cluster: "cluster1,cluster2"
```

#### Additional Custom Job Configuration

SLURM installations can support custom plugins, which may add support
for additional flags to `sbatch`.
In addition, there are various batch options not directly supported via the resource definitions
shown above.
You may use the `slurm_extra` resource to specify
additional flags to `sbatch`:

``` python
rule myrule:
    input: ...
    output: ...
    resources:
        slurm_extra="--mail-type=ALL --mail-user=<your email>"
```

.. note:: We prevent you from overwriting all flags, which are used or configurable internally. This prevents conflicts and breaking job submission.

Again, rather use a [profile](https://snakemake.readthedocs.io/en/latest/executing/cli.html#profiles) to specify such resources.

### Software Recommendations

#### Conda

Snakemake is commonly used with software deployment via conda ([`snakemake --software-deployment-method conda ...`](https://snakemake.readthedocs.io/en/stable/snakefiles/deployment.html#integrated-package-management).
On a cluster sometimes a file system other than `HOME` needs to be indicated (for example because of quotas).
In this case pointing the installation to different file system with `--conda-prefix /other/filesystem` might be a solution.
You can use `--conda-cleanup-pkgs` to further save space by removing downloaded tarballs.

#### Using Cluster Environment:  Modules

HPC clusters provide so-called environment modules.
To require installation with environment modules you can use `--sdm env-modules`, for example for a specific rule:

```
rule ...:
   ...
   envmodules:
       "bio/VinaLC"
```

This will trigger a `module load bio VinaLC` immediately before to execution.


Note, that 
- environment modules are best specified in a configuration file.
- Using environment modules can be combined with conda and apptainer (`--sdm env-modules conda apptainer`), which will then be only used as a fallback for rules not defining environment modules.

### Inquiring about Job Information and Adjusting the Rate Limiter

The executor plugin for SLURM uses unique job names to inquire about job status.
It ensures inquiring about job status for the series of jobs of a workflow does not put too much strain on the batch system's database.
Human readable information is stored in the comment of a particular job.
It is a combination of the rule name and wildcards.
You can ask for it with the `sacct` or `squeue` commands, for example:

``` console 
sacct -o JobID,State,Comment%40
```

Note, the "%40" after `Comment` ensures a width of 40 characters.
This setting may be changed at will.
If the width is too small, SLURM will abbreviate the column with a `+` sign.

For running jobs, you can use the squeue command:

``` console
squeue -u $USER -o %i,%P,%.10j,%.40k
```

Here, the `.<number>` settings for the ID and the comment ensure a sufficient width, too.

Snakemake will check the status of your jobs 40 seconds after submission.
Another attempt will be made in 10 seconds, then 20, etcetera with an upper limit of 180 seconds.

### Using Profiles

Utilizing Snakemake [profiles](https://snakemake.readthedocs.io/en/stable/executing/cli.html#profiles) streamlines workflow execution by consolidating configuration settings into dedicated directories, simplifying command-line operations.

#### Setting Up a Global Profile:

- Create a Profile Directory: If cluster administrators did not set up a global profile at `/etc/xdg/snakemake` users can opt for individual profiles.
  Establish a directory at `$HOME/.config/snakemake`.
- The default profile will be used when specifying the `--profile`.
  It can also be set via the environment variable `SNAKEMAKE_PROFILE`, for example by specifying export `SNAKEMAKE_PROFILE=myprofile` in your `~/.bashrc`.
  Then the --profile flag can be omitted.

A sample configuration looks like this:

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
local-storage-prefix: "<your local storage prefix, for example on login nodes>"
```


In this configuration:
- `executor: slurm`: Specifies the SLURM executor for job scheduling.
The corresponding command line flag is not needed anymore.
- `latency-wait: 5`: Sets a 5-second latency wait to accommodate file system delays.
- `default-storage-provider: fs`: Utilizes the file system storage plugin for file handling.
- `shared-fs-usage:` Lists storage categories to be managed via the shared file system.
  - `remote-job-local-storage-prefix:` Defines the storage prefix for remote jobs; adjust based on your cluster's scratch directory structure.
  - `local-storage-prefix:` Specifies the storage prefix for local jobs, such as on login nodes.

Using the [file system storage plugin](https://github.com/snakemake/snakemake-storage-plugin-fs) will automatically stage-in and -out in- and output files.

> This is ongoing development. Eventually, you will be able to annotate different file access patterns.

### Log Files - Getting Information on Failures

Snakemake's SLURM executor submits itself as a job, ensuring that all features function correctly within the job context.
SLURM requires a log file for every job, which can lead to redundancy since Snakemake's output is already displayed in the terminal.
However, if a rule includes a `log` directive, SLURM logs will contain only Snakemake's output.

By default, the SLURM executor deletes log files of successful jobs immediately after completion (remember: this is redundant information).
To modify this behavior and retain logs of successful jobs, use the `--slurm-keep-successful-logs` flag.
Additionally, log files for failed jobs are preserved for 10 days by default.
To change this retention period, use the `--slurm-delete-logfiles-older-than` flag.

Snakemake's log files are typically stored in the directory where the workflow is initiated or in the directory specified with the `--directory` flag.
To redirect SLURM logs produced by Snakemake to a specific directory, use the `--slurm-logdir` flag.
To prevent log files from accumulating in various directories, consider storing them in your home directory.
For example, add the following to your Snakemake profile:

```YAML
slurm-logdir: "/home/<username>/.snakemake/slurm_logs"
```

Replace <username> with your actual username.
This configuration directs SLURM logs to a centralized location, making them easier to manage.


### Nesting Jobs (or Running this Plugin within a Job)

Running Snakemake within an active SLURM job can lead to unpredictable behavior, as the execution environment may not be properly configured for job submission.
To mitigate potential issues, the SLURM executor plugin detects when it's operating inside a SLURM job and issues a warning, pausing for 5 seconds before proceeding.

### Getting Job Efficiency Information

With `--slurm-efficiency-report` you can generate a table of all efficiency data. A logfile `efficiency_report_<workflow_id>.log` will be generated in your current directory. This is equivalent to the information with `seff <jobid>` for individual jobs. It works best if "comments" are stored as a job property on your cluster as this plugin uses the "comment" parameter to store the rule name.

### Submittings Jobs into SLURM reservations

The plugin allows specifying a flag `--slurm-reservation=<name>` to use a particular reservation.
It does not validate the spelling nor eligibility to this reservation.

### Using SLURM QoS

To use SLURM's quality of service flags (`--qos` to `sbatch`) the plugin allows specifying `--slurm-qos=<qos-string>`, too. Both, the reservation and the qos may be particularly useful in a course setting.

### Frequently Asked Questions

#### Should I run Snakemake on the Login Node of my Cluster?

Running Snakemake on a cluster's login node is generally acceptable, as the primary Snakemake process is not resource-intensive.
However, some High-Performance Computing (HPC) administrators may discourage running job management processes like Snakemake on the login node, as it is typically intended for interactive use and not for executing computational tasks.
It's advisable to consult with your cluster's support team to understand any policies or guidelines regarding this practice.

To assess the impact of running Snakemake on the login node, you can measure the CPU time consumed by Snakemake during workflow execution.
For example, using the `/usr/bin/time -v` command to profile Snakemake's resource usage:

```console
/usr/bin/time -v snakemake ...
```

This command provides detailed statistics, including the CPU time used.
Sharing such metrics with your HPC administrators can help evaluate whether running Snakemake on the login node aligns with cluster usage policies.

We provide this table of measurements:

| Workflow | Version | Number of local rules  | Total Runtime (hh:mm:ss) | CPU-Time on the login node [user + system] (s) | Fraction |
|:-------------|:---------------|:---------------|:-------------|:-------------|:-------------:|
| [Transcriptome DiffExp + Fusion detection](https://github.com/snakemake-workflows/transcriptome-differential-expression) | 0.2.0 | 12 | 9:15:43 | 225.15 | 0.68 % |

If you want to contribute similar statistics, please run `/usr/bin/time -v snakemake ...` on your cluster and submit your stats as an [issue to the plugin repo on GitHub](https://github.com/snakemake/snakemake-executor-plugin-slurm/issue).

#### My Administrators do not let me run Snakemake on a Login Node

Running Snakemake within a SLURM job can lead to unpredictable behavior, as the execution environment may not be properly configured for job submission.
The SLURM executor plugin detects when it's operating inside a SLURM job and issues a warning, pausing for 5 seconds before proceeding.

If your administrators require that you run Snakemake within a job and you encounter issues, please report the specific problems as [issues on the plugin's GitHub repository](https://github.com/snakemake/snakemake-executor-plugin-slurm/issues).
While it may be possible to adapt the plugin for different cluster configurations, it's important to note that the plugin is primarily designed for use in production environments, and not all specialized cluster setups can be accounted for.

#### How to run Snakemake in an interactive SLURM Job

If you really need to run Snakemake inside an HPC job, we recommend relying on interactive jobs. Doing so, will preserve Snakemake's output and ease debugging. You can start your interactive job like this:

```console
$ salloc -A <your SLURM account> -p <your partition> \
> --time <enough time> \
> <further arguments, e.g. memory>
```

You need to consider the extra waiting time for jobs to start on your cluster, when choosing a value for the `--time` flag.

Note that `salloc` opens a subshell. Exit it before starting another interactive job in the same terminal -- even if the previous job has completed.
