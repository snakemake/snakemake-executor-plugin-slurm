import pytest
import tempfile
import yaml
from pathlib import Path
from math import inf

from snakemake_interface_common.exceptions import WorkflowError
from snakemake_executor_plugin_slurm.utils import (
    time_to_seconds,
    parse_time_to_minutes
)
from snakemake_executor_plugin_slurm.partitions import (
    PartitionLimits,
    read_partition_file,
)
from snakemake_executor_plugin_slurm.efficiency_report import (
    parse_sacct_data,
)


def test_parse_sacct_data():
    from io import StringIO

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


class TestTimeConversion:
    """Test time string conversion to minutes"""

    def test_parse_time_numeric_int(self):
        """Test parsing of plain integer (minutes)"""
        assert parse_time_to_minutes(120) == 120
        assert parse_time_to_minutes(0) == 0
        assert parse_time_to_minutes(1440) == 1440

    def test_parse_time_numeric_float(self):
        """Test parsing of plain float (minutes) - rounds to integer"""
        assert parse_time_to_minutes(120.5) == 121  # Rounded to nearest minute
        assert parse_time_to_minutes(0.5) == 1  # Rounded to 1 minute
        assert parse_time_to_minutes(120.4) == 120  # Rounded down

    def test_parse_time_numeric_string(self):
        """Test parsing of numeric strings (minutes)"""
        assert parse_time_to_minutes("120") == 120
        assert parse_time_to_minutes("120.5") == 121  # Rounded to nearest minute
        assert parse_time_to_minutes("0") == 0

    def test_parse_time_days(self):
        """Test parsing of day notation"""
        assert parse_time_to_minutes("1d") == 1440  # 1 day = 1440 minutes
        assert parse_time_to_minutes("6d") == 8640  # 6 days = 8640 minutes
        assert parse_time_to_minutes("0.5d") == 720  # 0.5 days = 720 minutes

    def test_parse_time_hours(self):
        """Test parsing of hour notation"""
        assert parse_time_to_minutes("1h") == 60
        assert parse_time_to_minutes("12h") == 720
        assert parse_time_to_minutes("0.5h") == 30

    def test_parse_time_minutes(self):
        """Test parsing of minute notation"""
        assert parse_time_to_minutes("30m") == 30
        assert parse_time_to_minutes("90m") == 90
        assert parse_time_to_minutes("1m") == 1

    def test_parse_time_seconds(self):
        """Test parsing of second notation"""
        assert parse_time_to_minutes("60s") == 1  # 60 seconds = 1 minute
        assert (
            parse_time_to_minutes("90s") == 2
        )  # 90 seconds = 1.5 minutes, rounded to 2
        assert (
            parse_time_to_minutes("30s") == 1
        )  # 30 seconds = 0.5 minutes, rounded to 1

    def test_parse_time_combined(self):
        """Test parsing of combined time notations"""
        # 2 days + 12 hours + 30 minutes = 2880 + 720 + 30 = 3630 minutes
        assert parse_time_to_minutes("2d12h30m") == 3630
        # 1 day + 30 minutes = 1440 + 30 = 1470 minutes
        assert parse_time_to_minutes("1d30m") == 1470
        # 6 hours + 30 seconds = 360 + 0.5 = 360.5 minutes, rounded to 361
        assert parse_time_to_minutes("6h30s") == 361

    def test_parse_time_whitespace(self):
        """Test parsing with whitespace"""
        assert parse_time_to_minutes("  6d  ") == 8640
        assert parse_time_to_minutes("2d 12h 30m") == 3630

    def test_parse_time_case_insensitive(self):
        """Test that parsing is case insensitive"""
        assert parse_time_to_minutes("6D") == 8640
        assert parse_time_to_minutes("12H") == 720
        assert parse_time_to_minutes("30M") == 30
        assert parse_time_to_minutes("90S") == 2  # Rounded

    def test_parse_time_invalid_format(self):
        """Test that invalid formats raise WorkflowError"""
        with pytest.raises(WorkflowError, match="Invalid time format"):
            parse_time_to_minutes("invalid")

        with pytest.raises(WorkflowError, match="Invalid time format"):
            parse_time_to_minutes("6x")

        with pytest.raises(WorkflowError, match="Invalid time format"):
            parse_time_to_minutes("abc123")

    def test_parse_time_slurm_minutes_only(self):
        """Test SLURM format: minutes only"""
        assert parse_time_to_minutes("60") == 60
        assert parse_time_to_minutes("120") == 120
        assert parse_time_to_minutes("1440") == 1440

    def test_parse_time_slurm_minutes_seconds(self):
        """Test SLURM format: minutes:seconds
        Note: In SLURM, MM:SS format is ambiguous. For partition time limits,
        it's more commonly interpreted as hours:minutes (HH:MM) since limits
        are typically longer durations. MM:SS is mainly used for elapsed time output.
        """
        # Interpreted as hours:minutes for partition limits
        assert parse_time_to_minutes("60:30") == 3630  # 60 hours + 30 minutes
        assert parse_time_to_minutes("1:30") == 90  # 1 hour + 30 minutes
        assert parse_time_to_minutes("0:45") == 45  # 0 hours + 45 minutes

    def test_parse_time_slurm_hours_minutes_seconds(self):
        """Test SLURM format: hours:minutes:seconds"""
        assert parse_time_to_minutes("1:30:00") == 90  # 1 hour 30 minutes
        assert (
            parse_time_to_minutes("2:15:30") == 136
        )  # 2h 15m 30s = 135.5 min, rounded to 136
        assert parse_time_to_minutes("12:00:00") == 720  # 12 hours
        assert (
            parse_time_to_minutes("0:45:30") == 46
        )  # 45 minutes 30 seconds = 45.5, rounded to 46

    def test_parse_time_slurm_days_hours(self):
        """Test SLURM format: days-hours"""
        assert parse_time_to_minutes("1-0") == 1440  # 1 day
        assert parse_time_to_minutes("2-12") == 3600  # 2 days + 12 hours
        assert parse_time_to_minutes("6-0") == 8640  # 6 days

    def test_parse_time_slurm_days_hours_minutes(self):
        """Test SLURM format: days-hours:minutes"""
        assert parse_time_to_minutes("1-0:30") == 1470  # 1 day + 30 minutes
        assert (
            parse_time_to_minutes("2-12:30") == 3630
        )  # 2 days + 12 hours + 30 minutes
        assert parse_time_to_minutes("0-6:15") == 375  # 6 hours + 15 minutes

    def test_parse_time_slurm_days_hours_minutes_seconds(self):
        """Test SLURM format: days-hours:minutes:seconds"""
        assert parse_time_to_minutes("1-0:0:0") == 1440  # 1 day exactly
        assert (
            parse_time_to_minutes("2-12:30:45") == 3631
        )  # 2d 12h 30m 45s = 3630.75, rounded to 3631
        assert (
            parse_time_to_minutes("0-1:30:30") == 91
        )  # 1h 30m 30s = 90.5, rounded to 91
        # 7 days + 23 hours + 59 minutes + 59 seconds
        # = 7*24*60 + 23*60 + 59 + 59/60 = 10080 + 1380 + 59 + 0.98333 = 11519.98333,
        # rounded to 11520
        assert parse_time_to_minutes("7-23:59:59") == 11520

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
            time_to_seconds("10-01:02:03.123") == 10 * 86400 + 1 * 3600 + 2 * 60 + 3.123
        )

class TestPartitionLimitsTimeConversion:
    """Test that PartitionLimits correctly converts max_runtime"""

    def test_partition_limits_numeric_runtime(self):
        """Test PartitionLimits with numeric runtime"""
        limits = PartitionLimits(max_runtime=1440)
        assert limits.max_runtime == 1440

    def test_partition_limits_string_runtime(self):
        """Test PartitionLimits with string time format"""
        limits = PartitionLimits(max_runtime="6d")
        assert limits.max_runtime == 8640

    def test_partition_limits_combined_runtime(self):
        """Test PartitionLimits with combined time format"""
        limits = PartitionLimits(max_runtime="2d12h")
        assert limits.max_runtime == 3600  # 2880 + 720 = 3600

    def test_partition_limits_infinity_runtime(self):
        """Test PartitionLimits with infinite runtime (default)"""
        limits = PartitionLimits()
        assert limits.max_runtime == inf

    def test_partition_limits_infinity_unchanged(self):
        """Test that infinity runtime is not converted"""
        limits = PartitionLimits(max_runtime=inf)
        assert limits.max_runtime == inf


class TestPartitionFileTimeConversion:
    """Test that partition files correctly parse time formats"""

    def test_partition_file_with_time_strings(self):
        """Test reading partition file with time string formats"""
        config = {
            "partitions": {
                "short": {
                    "max_runtime": "12h",
                    "max_mem_mb": 64000,
                },
                "medium": {
                    "max_runtime": "2d",
                    "max_mem_mb": 128000,
                },
                "long": {
                    "max_runtime": "6d",
                    "max_mem_mb": 256000,
                },
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = Path(f.name)

        try:
            partitions = read_partition_file(temp_path)

            # Check that partitions were created
            assert len(partitions) == 3

            # Check that time strings were converted correctly
            short_partition = next(p for p in partitions if p.name == "short")
            assert short_partition.limits.max_runtime == 720  # 12h = 720 minutes

            medium_partition = next(p for p in partitions if p.name == "medium")
            assert medium_partition.limits.max_runtime == 2880  # 2d = 2880 minutes

            long_partition = next(p for p in partitions if p.name == "long")
            assert long_partition.limits.max_runtime == 8640  # 6d = 8640 minutes
        finally:
            temp_path.unlink()

    def test_partition_file_with_numeric_runtime(self):
        """Test that numeric runtime still works"""
        config = {
            "partitions": {
                "numeric": {
                    "max_runtime": 1440,
                    "max_mem_mb": 64000,
                },
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = Path(f.name)

        try:
            partitions = read_partition_file(temp_path)
            assert len(partitions) == 1
            assert partitions[0].limits.max_runtime == 1440
        finally:
            temp_path.unlink()

    def test_partition_file_with_combined_time(self):
        """Test partition file with combined time format"""
        config = {
            "partitions": {
                "combined": {
                    "max_runtime": "2d12h30m",
                    "max_mem_mb": 128000,
                },
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = Path(f.name)

        try:
            partitions = read_partition_file(temp_path)
            assert len(partitions) == 1
            # 2d = 2880, 12h = 720, 30m = 30 → total = 3630 minutes
            assert partitions[0].limits.max_runtime == 3630
        finally:
            temp_path.unlink()

    def test_partition_file_with_invalid_time(self):
        """Test that invalid time format in partition file raises error"""
        config = {
            "partitions": {
                "invalid": {
                    "max_runtime": "invalid_time",
                    "max_mem_mb": 64000,
                },
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(WorkflowError, match="Invalid time format"):
                read_partition_file(temp_path)
        finally:
            temp_path.unlink()

    def test_partition_file_with_slurm_time_formats(self):
        """Test reading partition file with SLURM time formats"""
        config = {
            "partitions": {
                "short_minutes": {
                    "max_runtime": "60",  # 60 minutes
                    "max_mem_mb": 32000,
                },
                "medium_hms": {
                    "max_runtime": "12:00:00",  # 12 hours in h:m:s
                    "max_mem_mb": 64000,
                },
                "long_dh": {
                    "max_runtime": "6-0",  # 6 days in d-h format
                    "max_mem_mb": 128000,
                },
                "very_long_dhms": {
                    "max_runtime": "7-12:30:00",  # 7 days 12h 30m in d-h:m:s
                    "max_mem_mb": 256000,
                },
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = Path(f.name)

        try:
            partitions = read_partition_file(temp_path)

            # Check that partitions were created
            assert len(partitions) == 4

            # Check that SLURM time formats were converted correctly
            short_partition = next(p for p in partitions if p.name == "short_minutes")
            assert short_partition.limits.max_runtime == 60

            medium_partition = next(p for p in partitions if p.name == "medium_hms")
            assert medium_partition.limits.max_runtime == 720  # 12 hours

            long_partition = next(p for p in partitions if p.name == "long_dh")
            assert long_partition.limits.max_runtime == 8640  # 6 days

            very_long_partition = next(
                p for p in partitions if p.name == "very_long_dhms"
            )
            # 7 days + 12 hours + 30 minutes = 7*24*60 + 12*60 + 30 = 10830 minutes
            assert very_long_partition.limits.max_runtime == 10830
        finally:
            temp_path.unlink()

    def test_partition_file_mixed_time_formats(self):
        """Test partition file with mixed Snakemake and SLURM formats"""
        config = {
            "partitions": {
                "snakemake_style": {
                    "max_runtime": "6d",
                    "max_mem_mb": 64000,
                },
                "slurm_style": {
                    "max_runtime": "6-0",
                    "max_mem_mb": 64000,
                },
                "numeric": {
                    "max_runtime": 8640,
                    "max_mem_mb": 64000,
                },
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config, f)
            temp_path = Path(f.name)

        try:
            partitions = read_partition_file(temp_path)
            assert len(partitions) == 3

            # All three should result in the same runtime (6 days = 8640 minutes)
            for partition in partitions:
                assert partition.limits.max_runtime == 8640
        finally:
            temp_path.unlink()
