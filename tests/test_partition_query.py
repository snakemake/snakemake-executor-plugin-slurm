#!/usr/bin/env python
"""
Quick test script for the partition query functionality.
This can be run locally to test the parsing logic.
"""

from snakemake_executor_plugin_slurm.partitions import (
    parse_scontrol_partition_output,
    extract_partition_limits,
)
import yaml

SCONTROL_OUTPUT = """PartitionName=smallcpu
   AllowGroups=ALL DenyAccounts=none,ki-topml,ki-czlab AllowQos=ALL
   AllocNodes=ALL Default=YES QoS=smallcpu
   DefaultTime=01:00:00 DisableRootJobs=NO ExclusiveUser=NO ExclusiveTopo=NO GraceTime=0 Hidden=NO
   MaxNodes=1 MaxTime=6-00:00:00 MinNodes=0 LLN=NO MaxCPUsPerNode=UNLIMITED MaxCPUsPerSocket=UNLIMITED
   NodeSets=cpu256,cpu512
   Nodes=cpu[0019-0080,0085-0160,0165-0240,0245-0320,0325-0400,0405-0480,0485-0560,0565-0607]
   PriorityJobFactor=1 PriorityTier=2 RootOnly=NO ReqResv=NO OverSubscribe=NO
   OverTimeLimit=NONE PreemptMode=OFF
   State=UP TotalCPUs=71808 TotalNodes=561 SelectTypeParameters=NONE
   JobDefaults=(null)
   DefMemPerCPU=1930 MaxMemPerNode=UNLIMITED
   TRES=cpu=71808,mem=180600000M,node=561,billing=248175
   TRESBillingWeights=cpu=1.0,mem=1G

PartitionName=parallel
   AllowGroups=ALL DenyAccounts=none,ki-topml,kiczlab AllowQos=ALL
   AllocNodes=ALL Default=NO QoS=N/A
   DefaultTime=01:00:00 DisableRootJobs=NO ExclusiveUser=NO ExclusiveTopo=NO GraceTime=0 Hidden=NO
   MaxNodes=UNLIMITED MaxTime=6-00:00:00 MinNodes=0 LLN=NO MaxCPUsPerNode=UNLIMITED MaxCPUsPerSocket=UNLIMITED
   NodeSets=cpu256,cpu512
   Nodes=cpu[0019-0080,0085-0160,0165-0240,0245-0320,0325-0400,0405-0480,0485-0560,0565-0607]
   PriorityJobFactor=1 PriorityTier=1 RootOnly=NO ReqResv=NO OverSubscribe=EXCLUSIVE
   OverTimeLimit=NONE PreemptMode=OFF
   State=UP TotalCPUs=71808 TotalNodes=561 SelectTypeParameters=NONE
   JobDefaults=(null)
   DefMemPerNode=248000 MaxMemPerNode=UNLIMITED
   TRES=cpu=71808,mem=180600000M,node=561,billing=248175
   TRESBillingWeights=cpu=1,mem=1.0G

PartitionName=a100dl
   AllowGroups=ALL DenyAccounts=none,ki-topml AllowQos=ALL
   AllocNodes=ALL Default=NO QoS=N/A
   DefaultTime=01:00:00 DisableRootJobs=NO ExclusiveUser=NO ExclusiveTopo=NO GraceTime=0 Hidden=NO
   MaxNodes=UNLIMITED MaxTime=6-00:00:00 MinNodes=0 LLN=NO MaxCPUsPerNode=UNLIMITED MaxCPUsPerSocket=UNLIMITED
   NodeSets=4A100
   Nodes=gpu[0001-0010]
   PriorityJobFactor=1 PriorityTier=1 RootOnly=NO ReqResv=NO OverSubscribe=NO
   OverTimeLimit=NONE PreemptMode=OFF
   State=UP TotalCPUs=1280 TotalNodes=10 SelectTypeParameters=NONE
   JobDefaults=(null)
   DefMemPerCPU=7930 MaxMemPerNode=UNLIMITED
   TRES=cpu=1280,mem=10160000M,node=10,billing=16522,gres/gpu=40
   TRESBillingWeights=cpu=1.0,mem=1.5G,GRES/gpu=9
"""

def test_parsing():
    """Test the partition parsing logic."""
    partitions = parse_scontrol_partition_output(SCONTROL_OUTPUT)
    
    print("Parsed partitions:", list(partitions.keys()))
    
    output_config = {"partitions": {}}
    
    for partition_name, partition_data in partitions.items():
        limits = extract_partition_limits(partition_data)
        limits["cluster"] = "mogonnhr"
        output_config["partitions"][partition_name] = limits
    
    print("\nGenerated partition configuration:")
    print(yaml.dump(output_config, default_flow_style=False, sort_keys=False))

if __name__ == "__main__":
    test_parsing()
