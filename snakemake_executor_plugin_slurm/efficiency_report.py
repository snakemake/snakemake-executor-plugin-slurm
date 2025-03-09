import pandas as pd
import subprocess
import re


def time_to_seconds(time_str):
    """Convert SLURM time format to seconds."""
    if pd.isna(time_str) or time_str.strip() == "":
        return 0
    parts = time_str.split(":")
    parts = [int(p) for p in parts]
    if len(parts) == 3:  # H:M:S
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:  # M:S
        return parts[0] * 60 + parts[1]
    elif len(parts) == 1:  # S
        return parts[0]
    return 0


def parse_maxrss(maxrss):
    """Convert MaxRSS to MB."""
    if pd.isna(maxrss) or maxrss.strip() == "" or maxrss == "0":
        return 0
    match = re.match(r"(\d+)([KMG]?)", maxrss)
    if match:
        value, unit = match.groups()
        value = int(value)
        unit_multipliers = {"K": 1 / 1024, "M": 1, "G": 1024}
        return value * unit_multipliers.get(unit, 1)
    return 0


def parse_reqmem(reqmem):
    """Convert requested memory to MB."""
    if pd.isna(reqmem) or reqmem.strip() == "":
        return 0
    match = re.match(
        r"(\d+)([KMG])?(\S+)?", reqmem
    )  # Handles "4000M" or "4G" or "2G/node"
    if match:
        value, unit, per_unit = match.groups()
        value = int(value)
        unit_multipliers = {"K": 1 / 1024, "M": 1, "G": 1024}
        mem_mb = value * unit_multipliers.get(unit, 1)
        if per_unit == "/node":
            return mem_mb  # Memory is per node
        return mem_mb  # Default case (per CPU or total)
    return 0


def fetch_sacct_data(run_uuid, logger, efficiency_threshold=0.8):
    """Fetch sacct job data for a Snakemake workflow and compute efficiency metrics."""

    cmd = [
        "sacct",
        f"--name={run_uuid}",
        "--format=JobID,JobName,Comment,Elapsed,TotalCPU,NNodes,NCPUS,MaxRSS,ReqMem",
        "--parsable2",
        "--noheader",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split("\n")
    except subprocess.CalledProcessError:
        logger.warning(f"Error: Failed to retrieve job data for workflow ({run_uuid}).")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(
        (l.split("|") for l in lines),
        columns=[
            "JobID",
            "JobName",
            "Comment",
            "Elapsed",
            "TotalCPU",
            "NNodes",
            "NCPUS",
            "MaxRSS",
            "ReqMem",
        ],
    )

    # Convert types
    df["NNodes"] = pd.to_numeric(df["NNodes"], errors="coerce")
    df["NCPUS"] = pd.to_numeric(df["NCPUS"], errors="coerce")

    # Convert time fields
    df["Elapsed_sec"] = df["Elapsed"].apply(time_to_seconds)
    df["TotalCPU_sec"] = df["TotalCPU"].apply(time_to_seconds)

    # Compute CPU efficiency
    df["CPU Efficiency (%)"] = (
        df["TotalCPU_sec"] / (df["Elapsed_sec"] * df["NCPUS"])
    ) * 100
    df["CPU Efficiency (%)"] = df["CPU Efficiency (%)"].fillna(0).round(2)

    # Convert MaxRSS
    df["MaxRSS_MB"] = df["MaxRSS"].apply(parse_maxrss)

    # Convert ReqMem and calculate memory efficiency
    df["RequestedMem_MB"] = df["ReqMem"].apply(parse_reqmem)
    df["Memory Usage (%)"] = (df["MaxRSS_MB"] / df["RequestedMem_MB"]) * 100
    df["Memory Usage (%)"] = df["Memory Usage (%)"].fillna(0).round(2)

    # Log warnings for low efficiency
    for _, row in df.iterrows():
        if row["CPU Efficiency (%)"] < efficiency_threshold:
            logger.warning(
                f"Job {row['JobID']} for rule '{row['Comment']}' ({row['JobName']})",
                f" has low CPU efficiency: {row['CPU Efficiency (%)']}%."
            )
    logfile = f"efficiency_report_{run_uuid}.log"

    logger.info(f"Saved efficiency evaluation to '{logfile}'")
    return df


# Example usage:
#df = fetch_sacct_data("snakemake_workflow_uuid")  # Replace with actual UUID
