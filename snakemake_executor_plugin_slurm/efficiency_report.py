import re
import pandas as pd


def time_to_seconds(time_str):
    """Convert SLURM time format to seconds."""
    if pd.isna(time_str) or time_str.strip() == "":
        return 0
    parts = time_str.split(":")

    if len(parts) == 3:  # H:M:S
        parts = [int(p) for p in parts]
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:  # M:S
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 1:  # S
        return float(parts[0])
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
