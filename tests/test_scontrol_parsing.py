"""
Tests for scontrol partition query and parsing functionality.
"""

from snakemake_executor_plugin_slurm.partitions import (
    parse_scontrol_partition_output,
    extract_partition_limits,
    generate_partitions_from_scontrol,
)


SCONTROL_OUTPUT = """PartitionName=standard
   AllowGroups=ALL DenyAccounts=none AllowQos=ALL
   AllocNodes=ALL Default=YES QoS=standard
   DefaultTime=01:00:00 DisableRootJobs=NO ExclusiveUser=NO ExclusiveTopo=NO GraceTime=0 Hidden=NO
   MaxNodes=1 MaxTime=6-00:00:00 MinNodes=0 LLN=NO MaxCPUsPerNode=UNLIMITED MaxCPUsPerSocket=UNLIMITED
   NodeSets=compute_small
   Nodes=compute[0001-0100]
   PriorityJobFactor=1 PriorityTier=2 RootOnly=NO ReqResv=NO OverSubscribe=NO
   OverTimeLimit=NONE PreemptMode=OFF
   State=UP TotalCPUs=71808 TotalNodes=561 SelectTypeParameters=NONE
   JobDefaults=(null)
   DefMemPerCPU=1930 MaxMemPerNode=UNLIMITED
   TRES=cpu=71808,mem=180600000M,node=561,billing=248175
   TRESBillingWeights=cpu=1.0,mem=1G

PartitionName=parallel
   AllowGroups=ALL DenyAccounts=none AllowQos=ALL
   AllocNodes=ALL Default=NO QoS=N/A
   DefaultTime=01:00:00 DisableRootJobs=NO ExclusiveUser=NO ExclusiveTopo=NO GraceTime=0 Hidden=NO
   MaxNodes=UNLIMITED MaxTime=6-00:00:00 MinNodes=0 LLN=NO MaxCPUsPerNode=UNLIMITED MaxCPUsPerSocket=UNLIMITED
   NodeSets=compute_large
   Nodes=compute[0101-0200]
   PriorityJobFactor=1 PriorityTier=1 RootOnly=NO ReqResv=NO OverSubscribe=EXCLUSIVE
   OverTimeLimit=NONE PreemptMode=OFF
   State=UP TotalCPUs=71808 TotalNodes=561 SelectTypeParameters=NONE
   JobDefaults=(null)
   DefMemPerNode=248000 MaxMemPerNode=UNLIMITED
   TRES=cpu=71808,mem=180600000M,node=561,billing=248175
   TRESBillingWeights=cpu=1,mem=1.0G

PartitionName=gpu
   AllowGroups=ALL DenyAccounts=none AllowQos=ALL
   AllocNodes=ALL Default=NO QoS=N/A
   DefaultTime=01:00:00 DisableRootJobs=NO ExclusiveUser=NO ExclusiveTopo=NO GraceTime=0 Hidden=NO
   MaxNodes=UNLIMITED MaxTime=6-00:00:00 MinNodes=0 LLN=NO MaxCPUsPerNode=UNLIMITED MaxCPUsPerSocket=UNLIMITED
   NodeSets=gpu_nodes
   Nodes=gpu[0001-0010]
   PriorityJobFactor=1 PriorityTier=1 RootOnly=NO ReqResv=NO OverSubscribe=NO
   OverTimeLimit=NONE PreemptMode=OFF
   State=UP TotalCPUs=1280 TotalNodes=10 SelectTypeParameters=NONE
   JobDefaults=(null)
   DefMemPerCPU=7930 MaxMemPerNode=UNLIMITED
   TRES=cpu=1280,mem=10160000M,node=10,billing=16522,gres/gpu=40
   TRESBillingWeights=cpu=1.0,mem=1.5G,GRES/gpu=9
"""


def test_parse_scontrol_output():
    """Test parsing of scontrol show partition output."""
    partitions = parse_scontrol_partition_output(SCONTROL_OUTPUT)

    assert "standard" in partitions
    assert "parallel" in partitions
    assert "gpu" in partitions

    # Check standard partition
    standard = partitions["standard"]
    assert "MaxNodes" in standard
    assert standard["MaxNodes"] == "1"
    assert "MaxTime" in standard
    assert standard["MaxTime"] == "6-00:00:00"
    assert "TotalCPUs" in standard
    assert standard["TotalCPUs"] == "71808"


def test_extract_partition_limits():
    """Test extraction of partition limits from scontrol data."""
    partitions = parse_scontrol_partition_output(SCONTROL_OUTPUT)

    standard_limits = extract_partition_limits(partitions["standard"])
    assert "max_runtime" in standard_limits
    assert standard_limits["max_runtime"] == "6-00:00:00"
    assert "max_nodes" in standard_limits
    assert standard_limits["max_nodes"] == 1
    assert "max_mem_mb_per_cpu" in standard_limits
    assert standard_limits["max_mem_mb_per_cpu"] == 1930
    assert "max_threads" in standard_limits
    # 71808 / 561 = 128
    assert standard_limits["max_threads"] == 128

    # Check GPU partition
    gpu_limits = extract_partition_limits(partitions["gpu"])
    assert "max_gpu" in gpu_limits
    assert gpu_limits["max_gpu"] == 40


def test_extract_partition_limits_with_cluster():
    """Test that cluster is properly added to limits."""
    partitions = parse_scontrol_partition_output(SCONTROL_OUTPUT)
    limits = extract_partition_limits(partitions["standard"])

    # Add cluster manually for this test
    limits["cluster"] = "test-cluster"
    assert limits["cluster"] == "test-cluster"


def test_generate_partitions_from_scontrol_mock(monkeypatch):
    """Test partition configuration generation (mocked scontrol)."""

    # Mock the query function to return our test data
    def mock_query(cluster=None):
        return SCONTROL_OUTPUT

    import snakemake_executor_plugin_slurm.partitions as partitions_module

    monkeypatch.setattr(partitions_module, "query_scontrol_partitions", mock_query)

    config = generate_partitions_from_scontrol(cluster="test-cluster")

    assert "partitions" in config
    assert "standard" in config["partitions"]
    assert config["partitions"]["standard"]["cluster"] == "test-cluster"
    assert config["partitions"]["standard"]["max_nodes"] == 1
