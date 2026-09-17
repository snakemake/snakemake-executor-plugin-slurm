from snakemake_executor_plugin_slurm.utils import encode_deferred_envvars


def test_encode_deferred_envvars_rewrites_simple_env_vars():
    assert (
        encode_deferred_envvars("/localscratch/$SLURM_JOB_ID")
        == "/localscratch/__ENV_SLURM_JOB_ID__"
    )
    assert (
        encode_deferred_envvars("/localscratch/${SLURM_JOB_ID}/run")
        == "/localscratch/__ENV_SLURM_JOB_ID__/run"
    )


def test_encode_deferred_envvars_leaves_literal_text_alone():
    assert encode_deferred_envvars("/localscratch/job-1") == "/localscratch/job-1"
    assert (
        encode_deferred_envvars(r"/localscratch/\$SLURM_JOB_ID")
        == r"/localscratch/\$SLURM_JOB_ID"
    )
