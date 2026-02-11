#!/usr/bin/env python3
"""
Standalone script to generate SLURM partition configuration for Snakemake.

This script queries SLURM using scontrol to gather partition information
and outputs a YAML configuration file that can be used with the
snakemake-executor-plugin-slurm's partition_config setting.

Usage:
    # Generate config for the current cluster
    generate-slurm-partition-config > partitions.yaml
    
    # Generate config for specific cluster(s)
    generate-slurm-partition-config cluster1 > partitions.yaml
    generate-slurm-partition-config cluster1,cluster2 > partitions.yaml
    
    # Save to a file
    generate-slurm-partition-config -o partitions.yaml
    generate-slurm-partition-config cluster1,cluster2 -o partitions.yaml
"""

import argparse
import sys
import yaml

from .partitions import generate_partitions_from_slurm_query


def main():
    parser = argparse.ArgumentParser(
        description="Generate SLURM partition configuration for Snakemake",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query current cluster and output to stdout
  generate-slurm-partition-config
  
  # Query specific cluster
  generate-slurm-partition-config cluster1
  
  # Query multiple clusters
  generate-slurm-partition-config cluster1,cluster2
  
  # Save to file
  generate-slurm-partition-config -o partitions.yaml
  generate-slurm-partition-config cluster1,cluster2 -o partitions.yaml
  
The generated YAML file can be used with:
  snakemake --executor slurm --slurm-partition-config partitions.yaml

OR for permant use, copy the `partitions.yaml` to a location
(e.g. ~/.config/snakemake/ or /etc/xdg/snakemake). Be sure to set
`$SNAKEMAKE_SLURM_PARTITIONS`, accordingly.
    """,
    )
    parser.add_argument(
        "clusters",
        nargs="?",
        default=None,
        help="Comma-separated list of cluster names for multi-cluster setups. "
        "If omitted, queries the current/default cluster.",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output file path. If not specified, writes to stdout.",
    )

    args = parser.parse_args()

    try:
        # Generate partition configuration
        config = generate_partitions_from_slurm_query(args.clusters)

        # Format output
        yaml_output = yaml.dump(config, default_flow_style=False, sort_keys=False)

        # Write to file or stdout
        if args.output:
            with open(args.output, "w") as f:
                f.write(yaml_output)
            print(f"Partition configuration written to {args.output}", file=sys.stderr)
            # We need to issue a warning, that the file needs to be edited:
            print(
                "\033[1mWARNING: Please review the generated partition configuration file. "
                "You may need to adjust the limits based on your cluster's actual "
                "capabilities. "
                "For instance, enter `supports_mpi: true` for MPI partitions.\033[0m",
                file=sys.stderr,
            )
        else:
            print(yaml_output)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
