from typing import Optional
import snakemake.common.tests
from snakemake_interface_executor_plugins.settings import ExecutorSettingsBase

from snakemake_executor_plugin_slurm import ExecutorSettings


class TestWorkflows(snakemake.common.tests.TestWorkflowsLocalStorageBase):
    __test__ = True

    def get_executor(self) -> str:
        return "slurm"

    def get_executor_settings(self) -> Optional[ExecutorSettingsBase]:
        return ExecutorSettings()


class TestWorkflowsRequeue(TestWorkflows):
    def get_executor_settings(self) -> Optional[ExecutorSettingsBase]:
        return ExecutorSettings(requeue=True)
