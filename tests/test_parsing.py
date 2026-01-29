"""Tests for parsing functions that don't require SLURM to be installed."""
from io import StringIO
import pandas as pd
from snakemake_executor_plugin_slurm.efficiency_report import (
    parse_sacct_data,
    time_to_seconds,
)


def test_parse_sacct_data():
    test_data = [
        "10294159|b10191d0-6985-4c3a-8ccb-"
        "aa7d23ebffc7|rule_bam_bwa_mem_mosdepth_"
        "simulate_reads|00:01:31|00:24.041|1|1||32000M",
        "10294159.batch|batch||00:01:31|00:03.292|1|1|71180K|",
        "10294159.0|python3.12||00:01:10|00:20.749|1|1|183612K|",
        "10294160|b10191d0-6985-4c3a-8ccb-"
        "aa7d23ebffc7|rule_bam_bwa_mem_mosdepth_"
        "simulate_reads|00:01:30|00:24.055|1|1||32000M",
        "10294160.batch|batch||00:01:30|00:03.186|1|1|71192K|",
        "10294160.0|python3.12||00:01:10|00:20.868|1|1|184352K|",
    ]
    df = parse_sacct_data(
        lines=test_data, e_threshold=0.0, run_uuid="test", logger=None
    )
    output = StringIO()
    df.to_csv(output, index=False)
    print(output.getvalue())
    # this should only be two rows once collapsed
    assert len(df) == 2
    # check that RuleName is properly inherited from main jobs
    assert all(df["RuleName"] == "rule_bam_bwa_mem_mosdepth_simulate_reads")
    # check that RequestedMem_MB is properly inherited
    assert all(df["RequestedMem_MB"] == 32000.0)
    # check that MaxRSS_MB is properly calculated from job steps
    assert df.iloc[0]["MaxRSS_MB"] > 0  # Should have actual memory usage from job step


class TestTimeToSeconds:
    """Test the time_to_seconds function with SLURM sacct time formats."""

    def test_elapsed_format_with_days(self):
        """
        Test Elapsed format: [D-]HH:MM:SS or
        [DD-]HH:MM:SS (no fractional seconds).
        """
        # Single digit days
        assert time_to_seconds("1-00:00:00") == 86400  # 1 day
        assert (
            time_to_seconds("1-12:30:45") == 86400 + 12 * 3600 + 30 * 60 + 45
        )  # 131445
        assert time_to_seconds("9-23:59:59") == 9 * 86400 + 23 * 3600 + 59 * 60 + 59

        # Double digit days
        assert (
            time_to_seconds("10-01:02:03") == 10 * 86400 + 1 * 3600 + 2 * 60 + 3
        )  # 867723

    def test_elapsed_format_hours_minutes_seconds(self):
        """Test Elapsed format: HH:MM:SS (no fractional seconds)."""
        assert time_to_seconds("00:00:00") == 0
        assert time_to_seconds("01:00:00") == 3600  # 1 hour
        assert time_to_seconds("23:59:59") == 23 * 3600 + 59 * 60 + 59  # 86399
        assert time_to_seconds("12:30:45") == 12 * 3600 + 30 * 60 + 45  # 45045

    def test_totalcpu_format_with_days(self):
        """
        Test TotalCPU format: [D-][HH:]MM:SS or [DD-][HH:]MM:SS
        (with fractional seconds).
        """
        # With days and hours
        assert time_to_seconds("1-12:30:45.5") == 86400 + 12 * 3600 + 30 * 60 + 45.5
        assert (
            time_to_seconds("10-01:02:03.123")
            == 10 * 86400 + 1 * 3600 + 2 * 60 + 3.123
        )

        # With days, no hours (MM:SS format)
        assert time_to_seconds("1-30:45") == 86400 + 30 * 60 + 45
        assert time_to_seconds("1-30:45.5") == 86400 + 30 * 60 + 45.5

    def test_totalcpu_format_minutes_seconds(self):
        """Test TotalCPU format: MM:SS with fractional seconds."""
        assert time_to_seconds("00:00") == 0
        assert time_to_seconds("01:00") == 60  # 1 minute
        assert time_to_seconds("59:59") == 59 * 60 + 59  # 3599
        assert time_to_seconds("30:45") == 30 * 60 + 45  # 1845
        assert time_to_seconds("30:45.5") == 30 * 60 + 45.5  # 1845.5

    def test_totalcpu_format_seconds_only(self):
        """Test TotalCPU format: SS or SS.sss (seconds only with fractional)."""
        assert time_to_seconds("0") == 0
        assert time_to_seconds("1") == 1
        assert time_to_seconds("30") == 30
        assert time_to_seconds("59") == 59

        # Fractional seconds
        assert time_to_seconds("30.5") == 30.5
        assert time_to_seconds("0.5") == 0.5

    def test_real_world_sacct_examples(self):
        """Test with realistic sacct time values from actual output."""
        # From your test data
        assert time_to_seconds("00:01:31") == 91  # 1 minute 31 seconds
        assert time_to_seconds("00:24.041") == 24.041  # 24.041 seconds
        assert time_to_seconds("00:03.292") == 3.292  # 3.292 seconds
        assert time_to_seconds("00:20.749") == 20.749  # 20.749 seconds

        # Longer running jobs
        assert time_to_seconds("02:15:30") == 2 * 3600 + 15 * 60 + 30  # 2h 15m 30s
        assert time_to_seconds("1-12:00:00") == 86400 + 12 * 3600  # 1 day 12 hours
        assert time_to_seconds("7-00:00:00") == 7 * 86400  # 1 week

    def test_empty_and_invalid_inputs(self):
        """Test empty, None, and invalid inputs."""
        assert time_to_seconds("") == 0
        assert time_to_seconds("   ") == 0
        assert time_to_seconds(None) == 0
        assert time_to_seconds(pd.NA) == 0
        assert time_to_seconds("invalid") == 0
        assert time_to_seconds("1:2:3:4") == 0  # Too many colons
        assert time_to_seconds("abc:def") == 0
        assert time_to_seconds("-1:00:00") == 0  # Negative values

    def test_whitespace_handling(self):
        """Test that whitespace is properly handled."""
        assert time_to_seconds(" 30 ") == 30
        assert time_to_seconds("  1-02:30:45  ") == 86400 + 2 * 3600 + 30 * 60 + 45
        assert time_to_seconds("\t12:30:45\n") == 12 * 3600 + 30 * 60 + 45

    def test_pandas_na_values(self):
        """Test pandas NA and NaN values."""
        assert time_to_seconds(pd.NA) == 0
        assert (
            time_to_seconds(pd.NaType()) == 0 if hasattr(pd, "NaType") else True
        )  # Skip if not available

    def test_edge_case_values(self):
        """Test edge case values that might appear in SLURM output."""
        # Zero padding variations (should work with datetime parsing)
        assert time_to_seconds("01:02:03") == 1 * 3600 + 2 * 60 + 3
        assert time_to_seconds("1:2:3") == 1 * 3600 + 2 * 60 + 3

        # Single digit values
        assert time_to_seconds("5") == 5
        assert time_to_seconds("1:5") == 1 * 60 + 5
