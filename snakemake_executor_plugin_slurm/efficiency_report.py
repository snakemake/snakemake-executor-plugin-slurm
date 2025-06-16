import re
import pandas as pd
from pathlib import Path
import subprocess
import shlex

import os # only temporarily needed for printf debugging


def time_to_seconds(time_str):
    """Convert SLURM time format to seconds."""
    if pd.isna(time_str) or time_str.strip() == "":
        return 0
    parts = time_str.split(":")

    if len(parts) == 3:  # H:M:S
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:  # M:S
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 1:  # S
        return float(parts[0])
    return 0


def parse_maxrss(maxrss):
    """Convert MaxRSS to MB."""
    if pd.isna(maxrss) or maxrss.strip() == "" or maxrss == "0":
        return 0
    match = re.match(r"(\d+(?:\.\d+)?)([KMG]?)", maxrss)
    if match:
        value, unit = match.groups()
        value = float(value)
        unit_multipliers = {"K": 1 / 1024, "M": 1, "G": 1024}
        return value * unit_multipliers.get(unit, 1)
    return 0


def parse_reqmem(reqmem, number_of_nodes=1):
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
        if per_unit and "/node" in per_unit:
            # the memory values is per node, hence we need to
            # multiply with the number of nodes
            return mem_mb * number_of_nodes
        return mem_mb  # Default case (per CPU or total)
    return 0


def create_efficiency_report(e_threshold, run_uuid, e_report_path, logger):
    """
    Fetch sacct job data for a Snakemake workflow
    and compute efficiency metrics.
    """
    cmd = f"sacct --name={run_uuid} --parsable2 --noheader"
    cmd += (
        " --format=JobID,JobName,Comment,Elapsed,TotalCPU," "NNodes,NCPUS,MaxRSS,ReqMem"
    )

    try:
        result = subprocess.run(
            shlex.split(cmd), capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().split("\n")
    except subprocess.CalledProcessError:
        logger.error(f"Failed to retrieve job data for workflow {run_uuid}.")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(
        (line.split("|") for line in lines),
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

    # If the "Comment" column is empty,
    # a) delete the column
    # b) issue a warning
    if df["Comment"].isnull().all():
        logger.warning(
            f"No comments found for workflow {run_uuid}. "
            "This field is used to store the rule name. "
            "Please ensure that the 'comment' field is set for your cluster. "
            "Administrators can set this up in the SLURM configuration."
        )
        df.drop(columns=["Comment"], inplace=True)
        # remember, that the comment column is not available
        nocomment = True
    # else: rename the column to 'RuleName'
    else:
        df.rename(columns={"Comment": "RuleName"}, inplace=True)
        nocomment = False
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
    df["RequestedMem_MB"] = df.apply(
        lambda row: parse_reqmem(row["ReqMem"], row["NNodes"]), axis=1
    )
    df["Memory Usage (%)"] = df.apply(
        lambda row: (
            (row["MaxRSS_MB"] / row["RequestedMem_MB"] * 100)
            if row["RequestedMem_MB"] > 0
            else 0
        ),
        axis=1,
    )

    df["Memory Usage (%)"] = df["Memory Usage (%)"].fillna(0).round(2)

    # Drop all rows containing "batch" or "extern" as job names
    df = df[~df["JobName"].str.contains("batch|extern", na=False)]

    # Log warnings for low efficiency
    for _, row in df.iterrows():
        if row["CPU Efficiency (%)"] < e_threshold:
            if nocomment:
                logger.warning(
                    f"Job {row['JobID']} ({row['JobName']}) "
                    f"has low CPU efficiency: {row['CPU Efficiency (%)']}%."
                )
            else:
                # if the comment column is available, we can use it to
                # identify the rule name
                logger.warning(
                    f"Job {row['JobID']} for rule '{row['RuleName']}' "
                    f"({row['JobName']}) has low CPU efficiency: "
                    f"{row['CPU Efficiency (%)']}%."
                )

    # we construct a path object to allow for a customi
    # logdir, if specified
    p = Path()

    # Save the report to a CSV file
    logfile = f"efficiency_report_{run_uuid}.csv"
    if e_report_path:
        logfile = Path(e_report_path) / logfile
    else:
        logfile = p.cwd() / logfile
    df.to_csv(logfile)

    # write out the efficiency report at normal verbosity in any case
    logger.info(f"Efficiency report for workflow {run_uuid} saved to {logfile}.")
    # state directory contents for debugging purposes
    logger.debug(f"Current directory contents in '{p.cwd()}': {os.listdir(p.cwd())}")

