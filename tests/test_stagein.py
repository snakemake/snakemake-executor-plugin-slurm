from pathlib import Path
from typing import Optional

import snakemake.common.tests
import snakemake.settings.types as settings
from snakemake import api
from snakemake.settings.types import ConfigSettings
from snakemake_interface_executor_plugins.settings import ExecutorSettingsBase

from snakemake_executor_plugin_slurm import ExecutorSettings


class LocalStageinTestcasesBase(snakemake.common.tests.TestWorkflowsLocalStorageBase):
    """Resolve stage-in testcases from this plugin's tests/testcases directory."""

    def get_config_settings(self) -> Optional[ConfigSettings]:
        return None

    def run_workflow(self, test_name, tmp_path, deployment_method=frozenset()):
        test_path = Path(__file__).parent / "testcases" / test_name
        if not test_path.exists():
            return super().run_workflow(test_name, tmp_path, deployment_method)

        if self.omit_tmp:
            tmp_path = test_path
        else:
            tmp_path = Path(tmp_path) / test_name
            self._copy_test_files(test_path, tmp_path)

        resource_settings = self.get_resource_settings()

        if self._common_settings().local_exec:
            resource_settings.cores = 3
            resource_settings.nodes = None
        else:
            resource_settings.cores = 1
            resource_settings.nodes = 3

        with api.SnakemakeApi(
            settings.OutputSettings(
                verbose=True,
                show_failed_logs=True,
            ),
        ) as snakemake_api:
            workflow_api = snakemake_api.workflow(
                config_settings=self.get_config_settings(),
                resource_settings=resource_settings,
                storage_settings=settings.StorageSettings(
                    default_storage_provider=self.get_default_storage_provider(),
                    default_storage_prefix=self.get_default_storage_prefix(),
                    shared_fs_usage=(
                        settings.SharedFSUsage.all()
                        if self.get_assume_shared_fs()
                        else frozenset()
                    ),
                ),
                deployment_settings=self.get_deployment_settings(deployment_method),
                storage_provider_settings=self.get_default_storage_provider_settings(),
                workdir=Path(tmp_path),
                snakefile=tmp_path / "Snakefile",
            )

            dag_api = workflow_api.dag()
            dag_api.execute_workflow(
                executor=self.get_executor(),
                executor_settings=self.get_executor_settings(),
                execution_settings=settings.ExecutionSettings(
                    latency_wait=self.latency_wait,
                ),
                remote_execution_settings=self.get_remote_execution_settings(),
            )


class TestStageInSbcast(LocalStageinTestcasesBase):
    """Integration test for sbcast stage-in with a small synthetic input."""

    __test__ = True

    def get_executor(self) -> str:
        return "slurm"

    def get_executor_settings(self) -> Optional[ExecutorSettingsBase]:
        return ExecutorSettings(
            init_seconds_before_status_checks=2,
            node_local_prefix="/tmp/snakemake-stagein",
        )

    def test_stagein_sbcast(self, tmp_path):
        self.run_workflow("stagein_sbcast", tmp_path)

        run_dir = Path(tmp_path) / "stagein_sbcast"
        count_file = run_dir / "counted" / "count.txt"
        sbcast_log = run_dir / "log" / "sbcast.log"

        assert count_file.exists()
        assert sbcast_log.exists()
        assert count_file.read_text().strip().startswith("3 ")


class TestStageInSSH(LocalStageinTestcasesBase):
    """Optional integration test for SSH stage-in with a sparse large input."""

    __test__ = True

    def get_executor(self) -> str:
        return "slurm"

    def get_executor_settings(self) -> Optional[ExecutorSettingsBase]:
        return ExecutorSettings(
            init_seconds_before_status_checks=2,
            node_local_prefix="/tmp/snakemake-stagein",
        )

    def test_stagein_ssh(self, tmp_path):
        self.run_workflow("stagein_ssh", tmp_path)

        run_dir = Path(tmp_path) / "stagein_ssh"
        size_file = run_dir / "measured" / "size.txt"
        ssh_log = run_dir / "log" / "ssh.log"

        assert size_file.exists()
        assert ssh_log.exists()
        assert "data/big" in size_file.read_text()
