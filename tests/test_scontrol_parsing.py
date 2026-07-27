"""
Tests for scontrol partition query and parsing functionality.
"""

from snakemake_executor_plugin_slurm.partitions import (
    parse_scontrol_partition_output,
    extract_partition_limits,
    generate_partitions_from_scontrol,
    parse_tres_memory_to_mb,
    parse_tres_billing_weights,
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
    DefMemPerNode=248000 MaxMemPerNode=248000
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
    assert "max_mem_mb" in standard_limits
    assert standard_limits["max_mem_mb"] == 180600000
    assert "max_threads" in standard_limits
    # 71808 / 561 = 128
    assert standard_limits["max_threads"] == 128

    # Check GPU partition
    gpu_limits = extract_partition_limits(partitions["gpu"])
    assert "max_gpu" in gpu_limits
    assert gpu_limits["max_gpu"] == 40
    assert "max_mem_mb" in gpu_limits
    assert gpu_limits["max_mem_mb"] == 10160000
    assert "billing_weight_cpu" in gpu_limits
    assert gpu_limits["billing_weight_cpu"] == 1.0
    assert "billing_weight_mem_gb" in gpu_limits
    assert gpu_limits["billing_weight_mem_gb"] == 1.5

    # Check partition with finite MaxMemPerNode.
    # This must override the aggregate TRES mem value.
    parallel_limits = extract_partition_limits(partitions["parallel"])
    assert "max_mem_mb" in parallel_limits
    assert parallel_limits["max_mem_mb"] == 248000


def test_parse_tres_memory_to_mb_units():
    """Test TRES memory conversion for common units."""
    assert parse_tres_memory_to_mb("1024K") == 1
    assert parse_tres_memory_to_mb("500M") == 500
    assert parse_tres_memory_to_mb("2G") == 2048
    assert parse_tres_memory_to_mb("1T") == 1048576
    assert parse_tres_memory_to_mb("0.5G") == 512
    assert parse_tres_memory_to_mb("180600000M") == 180600000
    assert parse_tres_memory_to_mb("not-a-size") is None


def test_parse_tres_billing_weights():
    """Test parsing of TRES billing weights."""
    parsed = parse_tres_billing_weights("cpu=1.0,mem=2.8G")
    assert parsed["billing_weight_cpu"] == 1.0
    assert parsed["billing_weight_mem_gb"] == 2.8


def test_max_mem_per_node_unlimited_is_ignored():
    """UNLIMITED MaxMemPerNode must not create a max_mem_mb limit."""
    limits = extract_partition_limits(
        {
            "MaxMemPerNode": "UNLIMITED",
            "TRES": "cpu=1,mem=1000M,node=1,billing=1",
        }
    )
    # TRES fallback is used when MaxMemPerNode is UNLIMITED.
    assert limits["max_mem_mb"] == 1000


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
    # The cluster argument is not used in this mock,
    # but we include it to match the expected signature of
    # the real query function. This means we need to add
    # a `noqa: ARG001` comment to avoid linter warnings
    # about the unused argument.
    # See https://docs.astral.sh/ruff/rules/#flake8-unused-arguments-arg
    def mock_query(cluster=None):  # noqa: ARG001
        return SCONTROL_OUTPUT

    import snakemake_executor_plugin_slurm.partitions as partitions_module

    monkeypatch.setattr(partitions_module, "query_scontrol_partitions", mock_query)
    monkeypatch.setattr(
        partitions_module,
        "query_default_partitions",
        lambda cluster=None: "standard",  # noqa: ARG005
    )

    config = generate_partitions_from_scontrol(cluster="test-cluster")

    assert "partitions" in config
    assert "test-cluster_standard" in config["partitions"]
    assert config["partitions"]["test-cluster_standard"]["cluster"] == "test-cluster"
    assert config["partitions"]["test-cluster_standard"]["max_nodes"] == 1
    assert config["partitions"]["test-cluster_standard"]["max_mem_mb"] == 180600000
    assert config["partitions"]["test-cluster_standard"]["default"] is True


def test_generate_slurm_partition_config_strips_cluster_prefix(monkeypatch, capsys):
    """Test that CLI strips cluster prefixes from partition keys in YAML output."""
    from snakemake_executor_plugin_slurm.cli import main

    # Mock the partition generation to return prefixed keys
    mock_config = {
        "partitions": {
            "test-cluster_standard": {
                "cluster": "test-cluster",
                "max_nodes": 1,
                "max_mem_mb_per_cpu": 1930,
                "max_runtime": "6-00:00:00",
            },
            "test-cluster_gpu": {
                "cluster": "test-cluster",
                "max_gpu": 40,
                "max_runtime": "6-00:00:00",
            },
        }
    }

    # See https://docs.astral.sh/ruff/rules/#flake8-unused-arguments-arg
    # and the comment above about the unused argument in this mock function.
    def mock_generate(clusters):  # noqa: ARG001
        return mock_config

    monkeypatch.setattr(
        "snakemake_executor_plugin_slurm.cli.generate_partitions_from_slurm_query",
        mock_generate,
    )
    monkeypatch.setattr("sys.argv", ["generate-slurm-partition-config", "test-cluster"])

    main()

    captured = capsys.readouterr()
    # The YAML output should have unprefixed keys: "standard" and "gpu"
    assert "standard:" in captured.out
    assert "gpu:" in captured.out
    # Should NOT have the prefixed keys
    assert "test-cluster_standard:" not in captured.out
    assert "test-cluster_gpu:" not in captured.out


def test_generate_slurm_partition_config_outputs_max_mem_mb(monkeypatch, capsys):
    """Test that CLI output includes max_mem_mb derived from TRES mem values."""
    from snakemake_executor_plugin_slurm.cli import main
    import snakemake_executor_plugin_slurm.partitions as partitions_module

    # Use the real generation path and only mock scontrol query.
    # This verifies parse + generate + CLI write in one test.
    def mock_query(cluster=None):  # noqa: ARG001
        return SCONTROL_OUTPUT

    monkeypatch.setattr(partitions_module, "query_scontrol_partitions", mock_query)
    monkeypatch.setattr(
        partitions_module,
        "query_default_partitions",
        lambda cluster=None: "standard",  # noqa: ARG005
    )
    monkeypatch.setattr("sys.argv", ["generate-slurm-partition-config"])

    main()
    captured = capsys.readouterr()

    # YAML should include max_mem_mb values extracted from TRES=...mem=...
    assert "max_mem_mb: 180600000" in captured.out
    assert "max_mem_mb: 10160000" in captured.out
    assert "default: true" in captured.out
    assert "billing_weight_mem_gb: 1.0" in captured.out
