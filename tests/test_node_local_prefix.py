import base64

from snakemake_executor_plugin_slurm.utils import encode_deferred_envvars


def test_encode_deferred_envvars_roundtrips_via_base64():
    value = "/localscratch/$SLURM_JOB_ID"
    encoded = encode_deferred_envvars(value)
    assert encoded == base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii")
    assert base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8") == value


def test_encode_deferred_envvars_leaves_no_literal_dollar_sign():
    encoded = encode_deferred_envvars("/localscratch/${SLURM_JOB_ID}/run")
    assert "$" not in encoded


def test_encode_deferred_envvars_handles_plain_text():
    value = "/localscratch/job-1"
    encoded = encode_deferred_envvars(value)
    assert base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8") == value
