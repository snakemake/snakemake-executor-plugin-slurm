"""Unit tests for get_account_arg() method."""

from unittest.mock import MagicMock, patch

from snakemake_executor_plugin_slurm import Executor


class _Resources(dict):
    """Dict-like resources with attribute access for known keys only."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e


def _make_mock_job(
    rule_name="myrule", name=None, wildcards=None, jobid=1, is_group=False, **resources
):
    """Return a minimal mock job compatible with get_account_arg."""
    mock_resources = _Resources(resources)

    mock_rule = MagicMock()
    mock_rule.name = rule_name

    job = MagicMock()
    job.resources = mock_resources
    job.rule = mock_rule
    job.name = name if name is not None else rule_name
    job.wildcards = wildcards if wildcards is not None else {}
    job.is_group.return_value = is_group
    job.threads = resources.get("threads", 1)
    job.jobid = jobid
    return job


class TestGetAccountArg:
    """Tests for get_account_arg() method handling string and integer accounts."""

    def _make_executor_stub(self):
        """Return a minimal Executor stub."""
        executor = Executor.__new__(Executor)
        executor.logger = MagicMock()
        executor._fallback_account_arg = None
        return executor

    # Patches prevent actual SLURM command execution (sacct/sacctmgr).
    # - get_account() would call 'sacct' to guess account from recent jobs.
    # - test_account() would call 'sacctmgr' or 'sshare' to validate account.
    # Mocks allow testing without a live SLURM cluster.
    @patch("snakemake_executor_plugin_slurm.get_account")
    @patch("snakemake_executor_plugin_slurm.test_account")
    def test_string_account(self, mock_test_account, mock_get_account, tmp_path):
        """String account values work correctly."""
        executor = self._make_executor_stub()
        job = _make_mock_job(slurm_account="123456789")
        result = next(executor.get_account_arg(job))
        assert result == " -A 123456789"
        mock_test_account.assert_called_with("123456789", executor.logger)

    @patch("snakemake_executor_plugin_slurm.get_account")
    @patch("snakemake_executor_plugin_slurm.test_account")
    def test_integer_account(self, mock_test_account, mock_get_account, tmp_path):
        """Integer account values (from YAML parsing) work correctly."""
        executor = self._make_executor_stub()
        job = _make_mock_job(slurm_account=123456789)
        result = next(executor.get_account_arg(job))
        assert result == " -A 123456789"
        mock_test_account.assert_called_with("123456789", executor.logger)

    @patch("snakemake_executor_plugin_slurm.get_account")
    @patch("snakemake_executor_plugin_slurm.test_account")
    def test_multiple_accounts_string(
        self, mock_test_account, mock_get_account, tmp_path
    ):
        """Multiple string accounts work correctly."""
        executor = self._make_executor_stub()
        job = _make_mock_job(slurm_account="acc1,acc2 acc3")
        results = list(executor.get_account_arg(job))
        assert results == [" -A acc1", " -A acc2", " -A acc3"]
