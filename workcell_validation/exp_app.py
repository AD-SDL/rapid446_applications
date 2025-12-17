"""An Example Application"""

import time
from pathlib import Path

from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.node_types import NodeDefinition
from madsci.experiment_application import (
    ExperimentApplication,
    ExperimentApplicationConfig,
)
from pydantic import AnyUrl
from datetime import datetime


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
        get_flat_bottom_plate_remove_lid_wf = wf_directory / "get_flat_bottom_plate_remove_lid_wf.yaml"
        ot2_validate_wf = wf_directory / "ot2_validate_wf.yaml"
        bmg_validate_wf = wf_directory / "bmg_validate_wf.yaml"
        hidex_validate_wf = wf_directory / "hidex_validate_wf.yaml"
        inheco_validate_wf = wf_directory / "inheco_validate_wf.yaml"
        replace_lid_return_to_rack_wf = wf_directory / "replace_lid_return_to_rack_wf.yaml"
        get_new_pcr_plate_wf = wf_directory / "get_new_pcr_plate_wf.yaml"
        sealer_validate_wf = wf_directory / "sealer_validate_wf.yaml"
        peeler_validate_wf = wf_directory / "peeler_validate_wf.yaml"
        return_pcr_plate_to_rack_wf = wf_directory / "return_pcr_plate_to_rack_wf.yaml"

        # protocols
        test_ot2_protocol = protocol_directory / "test_ot2_protocol.py"

        # RUN VALIDATION WORKFLOWS ---------------------------------------------

        # TODO: Validate SciClops

        # 1. Get new flat bottom plate with lid from Rack Row 1 Nest 1 and place on exchange
        workflow = self.workcell_client.submit_workflow(
            get_flat_bottom_plate_remove_lid_wf.resolve()
        )

        # 2. Validate both Opentrons OT-2s
        workflow = self.workcell_client.submit_workflow(
            ot2_validate_wf.resolve(),
            file_inputs={"ot2_protocol": test_ot2_protocol.resolve()},
        )

        # 3. Validate BMG VANTAstar Microplate Reader
        workflow = self.workcell_client.submit_workflow(
            bmg_validate_wf.resolve(),
            json_inputs={
                "bmg_assay_name": "Absorbance_Test",
                "bmg_data_file_name": f"workcell_validation_{int(time.time())}.txt",
                "data_output_directory_path": "C:\\Users\\RPL\\DEMO",
            },
        )

        # 4. Validate Hidex Sense Microplate Reader
        workflow = self.workcell_client.submit_workflow(
            hidex_validate_wf.resolve(),
            json_inputs={
                "hidex_assay_name": "Absorbance_Workcell_Validation"
            },
        )

        # 5. Validate both Inheco Single Plate Incubators
        workflow = self.workcell_client.submit_workflow(
            inheco_validate_wf.resolve()
        )

        # 6. Replace lid on flat bottom plate and return to Rack Row 1 Nest 1
        workflow = self.workcell_client.submit_workflow(
            replace_lid_return_to_rack_wf.resolve()
        )

        # 7. Get a new PCR plate from Rack Row 1 Nest 2 and transfer to exchange
        workflow = self.workcell_client.submit_workflow(
            get_new_pcr_plate_wf.resolve()
        )

        # 8. Validate Sealer
        workflow = self.workcell_client.submit_workflow(
            sealer_validate_wf.resolve()
        )

        # 9. Validate Peeler
        workflow = self.workcell_client.submit_workflow(
            peeler_validate_wf.resolve()
        )

        # TODO: Validate OT-Flex

        # TODO: Validate Biometra TRobot II Themocyclers

        # 10. Return PCR plate to Rack Row 1 Nest 2
        workflow = self.workcell_client.submit_workflow(
            return_pcr_plate_to_rack_wf.resolve()
        )

if __name__ == "__main__":
    exp_app = ExampleApp()

    current_time = datetime.now()

    # Start experiment run
    with exp_app.manage_experiment(
        run_name = f"Workcell_Validation_App_{current_time.strftime('%Y%m%d_%H%M%S')}",
        run_description = "Workcell Validation App",
    ):
        exp_app.start_app()