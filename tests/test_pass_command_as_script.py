from typing import Optional
import snakemake.common.tests
from snakemake_interface_executor_plugins.settings import ExecutorSettingsBase
from snakemake_executor_plugin_slurm import ExecutorSettings


class TestPassCommandAsScript(snakemake.common.tests.TestWorkflowsLocalStorageBase):
    """Integration-style test that runs the real workflow on the Slurm test cluster
    and verifies the plugin can submit the job by passing the command as a script
    via stdin (pass_command_as_script=True).
    """

    __test__ = True

    def get_executor(self) -> str:
        return "slurm"

    def get_executor_settings(self) -> Optional[ExecutorSettingsBase]:
        # Use the real ExecutorSettings and enable the flag under test.
        return ExecutorSettings(
            pass_command_as_script=True,
            init_seconds_before_status_checks=2,
        )
