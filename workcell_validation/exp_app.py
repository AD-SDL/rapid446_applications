"""An Example Application"""

from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.node_types import NodeDefinition
from madsci.experiment_application import (
    ExperimentApplication,
    ExperimentApplicationConfig,
)
from pydantic import AnyUrl
from pathlib import Path
import time


class ExampleApp(ExperimentApplication):
    """An Example Application"""

    experiment_design = ExperimentDesign(
        experiment_name="Example_App",
    )
    config = ExperimentApplicationConfig(node_url=AnyUrl("http://localhost:6000"))

    def run_experiment(self) -> None:
        """main experiment function"""

        # define paths
        app_directory = Path(__file__).parent   # experiment app
        wf_directory = app_directory / "workflows"  # workflows
        protocol_directory = app_directory / "protocols"

        # workflows
        test_workflow = wf_directory / "test_wf.yaml"

        # protocols
        test_ot2_protocol = protocol_directory / "test_ot2_protocol.py"

        workflow = self.workcell_client.submit_workflow(
            test_workflow.resolve(),
            json_inputs={
                "bmg_assay_name": "Absorbance_Test",
                "bmg_data_file_name": f"workcell_validation_{int(time.time())}.txt",
                "data_output_directory_path": "C:\\Users\\RPL\\DEMO"
            },
            file_inputs={"ot2_protocol": test_ot2_protocol.resolve()},
        )


if __name__ == "__main__":
    app = ExampleApp(
        node_definition=NodeDefinition(
            node_name="workcell_validation_app", module_name="workcell_validation_app"
        )
    )
    app.start_app()



