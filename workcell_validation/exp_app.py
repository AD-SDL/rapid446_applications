"""An Example Application"""

from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.node_types import NodeDefinition
from madsci.experiment_application import (
    ExperimentApplication,
    ExperimentApplicationConfig,
)
from pydantic import AnyUrl
from pathlib import Path


class ExampleApp(ExperimentApplication):
    """An Example Application"""

    experiment_design = ExperimentDesign(
        experiment_name="Example_App",
    )
    config = ExperimentApplicationConfig(node_url=AnyUrl("http://localhost:6000"))
    # lab_server_url = "http://localhost:8000"

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
            json_inputs={"bmg_output_filename": "test_data.txt"},
            file_inputs={"ot2_protocol": test_ot2_protocol.resolve()},
        )


if __name__ == "__main__":
    app = ExampleApp(
        node_definition=NodeDefinition(
            node_name="test_app", module_name="test_app"
        )
    )
    app.start_app()



