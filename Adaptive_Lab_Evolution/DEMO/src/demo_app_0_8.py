"""Demo Experiment on the RAPID-446 robotic lab at Argonne National Laboratory.

Runs on MADSci 0.8
"""

from pathlib import Path
import helper_functions

from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.parameter_types import ParameterInputFile
from madsci.common.types.resource_types import Asset
from madsci.common.types.step_types import StepDefinition
from madsci.common.types.workflow_types import WorkflowDefinition
from madsci.experiment_application.experiment_script import ExperimentScript


class ExampleExperiment(ExperimentScript):
    """An example experiment that iterates until a measurement target is reached."""

    experiment_design = ExperimentDesign(
        experiment_name="Example Experiment",
        experiment_description="Iteratively run a workflow until a measurement threshold is met.",
    )

    def run_experiment(self) -> None:
        """Run the experiment loop.

        Sets up resources, then repeatedly runs the workflow until the
        platereader measurement drops below the desired limit.

        Args:
            desired_limit: Stop when the measurement is below this value.

        Returns:
            Dictionary with the final measurement result.
        """
 
        # directory paths
        app_directory = Path(__file__).parent.parent   
        wf_directory = app_directory / "workflows"
        protocol_directory = app_directory / "protocols"

        # workflow paths
        demo_workflow = wf_directory / "demo_wf.yaml"

        # protocol paths
        demo_inoculate_ot2_protocol = protocol_directory / "inoculate.py"


        payload = {
            "current_ot2_protocol": None,
        }

        # edit the ot-2 protocol
        ot2_replacement_variables = helper_functions.collect_ot2_replacement_variables(payload)
        temp_ot2_file_str = helper_functions.generate_ot2_protocol(demo_inoculate_ot2_protocol, ot2_replacement_variables)
        payload["current_ot2_protocol"] = temp_ot2_file_str
        temp_path = Path(payload["current_ot2_protocol"])

        workflow = self.workcell_client.start_workflow(
            demo_workflow.resolve(),
            file_inputs={"ot2_protocol": temp_path.resolve()},
            prompt_on_error=True,
        )

        return None


if __name__ == "__main__":
    ExampleExperiment.main(lab_server_url="http://146.137.240.20:8000/")





