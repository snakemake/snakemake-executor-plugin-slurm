from unittest.mock import patch

from snakemake_executor_plugin_slurm.utils import add_failing_nodes


def test_add_failing_nodes_returns_node_from_sacct():
    with patch(
        "snakemake_executor_plugin_slurm.utils.subprocess.check_output",
        return_value="node01\n",
    ):
        assert add_failing_nodes("12345") == {"node01"}


def test_add_failing_nodes_ignores_none_assigned():
    with patch(
        "snakemake_executor_plugin_slurm.utils.subprocess.check_output",
        return_value="None assigned\nnode01\n",
    ):
        assert add_failing_nodes("12345") == {"node01"}