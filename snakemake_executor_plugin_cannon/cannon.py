#############################################################################
# Functions for the Cannon cluster
#
# Created May 2025
# Gregg Thomas
# Noor Sohail
#############################################################################

import re
from snakemake_interface_common.exceptions import WorkflowError


def get_cannon_partitions():
    """
    Function to return the resources for the Cannon cluster.
    """

    partitions = {
            "sapphire":            {"cpus_per_task": 112, "mem_mb": 990000, "runtime": 4320, "gpus": 0},
            "shared":              {"cpus_per_task": 48, "mem_mb": 184000, "runtime": 4320, "gpus": 0},
            "bigmem":              {"cpus_per_task": 112, "mem_mb": 1988000, "runtime": 4320, "gpus": 0},
            "bigmem_intermediate": {"cpus_per_task": 64, "mem_mb": 2000000, "runtime": 20160, "gpus": 0},
            "gpu":                 {"cpus_per_task": 64, "mem_mb": 990000, "runtime": 4320, "gpus": 4},
            "intermediate":        {"cpus_per_task": 112, "mem_mb": 990000, "runtime": 20160, "gpus": 0},
            "unrestricted":        {"cpus_per_task": 48, "mem_mb": 184000, "runtime": "none", "gpus": 0},
            "test":                {"cpus_per_task": 112, "mem_mb": 990000, "runtime": 720, "gpus": 0},
            "gpu_test":            {"cpus_per_task": 64, "mem_mb": 487000, "runtime": 720, "gpus": 4}
            #"serial_requeue":     {"cpus_per_task": "varies", "mem_mb": "varies", "runtime": 4320, "gpus": 0},
            #"gpu_requeue":        {"cpus_per_task": "varies", "mem_mb": "varies", "runtime": 4320, "gpus": 4}
        }
    return partitions

#############################################################################

def format_cannon_resources(logger):
    """Format and display resources in a clean aligned table, then exit."""
    
    partitions = get_cannon_partitions();
    
    title = "Resources available on the Cannon cluster per node"
    headers = ["Partition", "CPUs", "Mem (GB)", "Runtime (min)", "GPUs"]
    rows = [];

    for name, res in partitions.items():
        cpus = res["cpus_per_task"]
        mem = res["mem_mb"]
        runtime = res["runtime"]
        gpus = res["gpus"]

        # Convert mem_mb → GB; handle "varies" or "none"
        mem_gb = int(mem) // 1000 if isinstance(mem, int) else str(mem)
        
        rows.append((name, cpus, mem_gb, runtime, gpus))

    format_table(headers, rows, logger, title=title)

#############################################################################

def parse_mem_to_mb(raw_mem):
        """
        Converts memory values like '16G', '512MB', '800kb', etc. to integer MB.
        """

        raw_mem = str(raw_mem).strip().upper()
        match = re.match(r"^(\d+(?:\.\d+)?)([GMK]B?|B)?$", raw_mem)

        if not match:
            raise WorkflowError(f"Invalid memory format: '{raw_mem}'.")

        value, unit = match.groups()
        value = float(value)

        unit = unit or "MB"  # Default to MB if unit omitted
        unit_map = {
            "K": 1 / 1000,
            "KB": 1 / 1000,
            "M": 1,
            "MB": 1,
            "G": 1000,
            "GB": 1000,
            # optionally, support binary units:
            # "KI": 1 / 1024,
            # "MI": 1,
            # "GI": 1024
        }

        if unit not in unit_map:
            raise WorkflowError(f"Unsupported memory unit '{unit}' in 'mem' resource.")

        mem_mb = value * unit_map[unit]
        return int(mem_mb)

#############################################################################

def normalize_mem(job, logger, default_mem_mb=4005):
    if job.resources.get("mem"):
        mem_mb = parse_mem_to_mb(job.resources.get("mem"))
    elif job.resources.get("mem_gb"):
        mem_mb = job.resources.get("mem_gb", 4) * 1000;
    elif job.resources.get("mem_mb"):
        mem_mb = job.resources.get("mem_mb", 4000)
    else:
        mem_mb = default_mem_mb  # Default memory in MB
    # Convert to MB if necessary

    if mem_mb < default_mem_mb:
        logger.warning(f"\nWARNING: requested mem {mem_mb}MB is too low; clamping to {default_mem_mb}MB\n")
        mem_mb = default_mem_mb  # Minimum memory in MB

    return mem_mb

#############################################################################

def parse_num_gpus(job, logger):
    """
    Extract number of GPUs from job.resources in priority order:

    1. (DISABLED) If gpu and optional gpu_model are provided → use those
    2. (DISABLED) Else if gres is specified (e.g. "gpu:2" or "gpu:a100:4") → parse it
    3. Else if slurm_extra contains --gres=gpu:... → extract from there
    4. Else → assume 0 GPUs
    """
    gpu = job.resources.get("gpu", 0)
    gpu_model = job.resources.get("gpu_model")
    gres = job.resources.get("gres", None)
    slurm_extra = str(job.resources.get("slurm_extra", ""))

    # 1. GPU + optional model: gpu must be > 0
    
    if gpu_model:
        if not gpu or not isinstance(gpu, int):
            raise WorkflowError("GPU model is set, but 'gpu' number is missing or invalid.")
        if ":" in gpu_model:
            raise WorkflowError("Invalid GPU model format — should not contain ':'.")
        return int(gpu)  # interpreted with model separately

    if isinstance(gpu, int) and gpu > 0:
        logger.error(f"\nSpecifying GPUs as gpu: is not currently supported on the Cannon plugin.")
        logger.error(f"Please use the slurm_extra: resource instead.")
        logger.error(f"Example: slurm_extra: \"'--gres=gpu:{gpu}'\" (notice the nested quotes which are required)")
        raise WorkflowError(f"Unsupported GPU specification format: gpu:\n")
        #return gpu

    # 2. Parse "gres" string if present
    if gres:
        logger.error(f"\nSpecifying GPUs as gres: is not currently supported on the Cannon plugin.")
        logger.error(f"Please use the slurm_extra: resource instead.")
        logger.error(f"Example: slurm_extra: \"'--gres=gpu:{gpu}'\" (notice the nested quotes which are required)")
        raise WorkflowError(f"Unsupported GPU specification format: gres:\n")        
        # gres = str(gres)
        # match = re.match(r"^gpu(?::[a-zA-Z0-9_]+)?:(\d+)$", gres)
        # if match:
        #     return int(match.group(1))
        # else:
        #     raise WorkflowError(f"Invalid GRES format in resources.gres: '{gres}'")

    # 3. Parse slurm_extra
    match = re.search(r"--gres=gpu(?::[^\s,:=]+)?:(\d+)", slurm_extra.lower())
    if match:
        return int(match.group(1))

    # 4. Fallback: no GPUs requested
    return 0

#############################################################################

def check_resources(specified_resources, partitions, partition, job_name, logger):
    """
    Check if the specified resources are valid for the Cannon cluster.
    """

    rows, violations = [], []
    for resource in specified_resources:
        requested = specified_resources.get(resource, 0)
        allowed = partitions[partition].get(resource)
        if isinstance(allowed, int) and requested > allowed:
            violations.append((resource, f"{requested}/{allowed}"))
        rows.append((resource, requested))

    if violations:
        headers=["Resource", "Requested/Allowed"]
        title = f"Rule {job_name}: The requested resources exceed allowed limits for partition '{partition}'."
        format_table(headers, violations, logger.error, title=title)
        raise WorkflowError(title)

    else:
        headers=["Resource", "Requested"]
        title = f"Rule {job_name}: Requested resources for partition '{partition}'"
        format_table(headers, rows, logger.info, title=title)

#############################################################################

def format_table(headers, rows, logger, widths=None, align=None, title=None):
    """
    Render a table with N columns as an ASCII string.

    :param headers:   column titles (length = N)
    :param rows:      list of rows, each a sequence of length N
    :param widths:    optional list of column widths; if omitted, computed as max(len(header), max(len(cell_str)))
    :param align:     optional list of '<' or '>' per column (default: first left, rest right)
    :param title:     optional title for the table
    """
    # Convert everything to str and determine column count
    table = [[str(h) for h in headers]] + [[str(c) for c in row] for row in rows]
    num_cols = len(headers)

    # Compute widths if not supplied
    if widths is None:
        widths = [0] * num_cols
        for row in table:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))

    # Default alignment: first col left, others right
    if align is None:
        align = ['<'] + ['>'] * (num_cols - 1)

    # Build format strings for each column
    fmts = [f" {{:{align[i]}{widths[i]}}} " for i in range(num_cols)]

    # Render header
    lines = []
    header_line = "".join(fmts[i].format(headers[i]) for i in range(num_cols)).rstrip()
    lines.append(header_line)

    # Render separator
    sep = "".join(fmts[i].format("-" * widths[i]) for i in range(num_cols)).rstrip()
    lines.append(sep)

    # Render data rows
    for row in rows:
        line = "".join(fmts[i].format(row[i]) for i in range(num_cols)).rstrip()
        lines.append(line)

    if title:
        title_line = f"\n{title}\n" + "-" * len(title)
        lines.insert(0, title_line)
    
    logger("\n".join(lines) + "\n")


#############################################################################
