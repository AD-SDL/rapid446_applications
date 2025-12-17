#!/usr/bin/env python3
"""Experiment application for the Protein Design experiment"""

import time
from datetime import datetime
from pathlib import Path

import helper_functions
from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.node_types import NodeDefinition
from madsci.common.types.resource_types import Resource
from madsci.experiment_application import (
    ExperimentApplication,
    ExperimentApplicationConfig,
)
from pydantic import AnyUrl


class PDApp(ExperimentApplication):
    """PD Experiment Application

    # TODO:

    """

    experiment_design = ExperimentDesign(
        experiment_name="PD_App",
    )
    config = ExperimentApplicationConfig(node_url=AnyUrl("http://localhost:6000"))
    experiment_id = None
    experiment_label = None


    def __init__(self) -> None:
        """Initializes the PD Experiment App"""

        super().__init__()
        self.init_assay_plate_resource_template()

    def init_assay_plate_resource_template(self):
        """Initializes assay plate resource template"""

        self.resource_client.create_template(
            resource=Resource(
                resource_description="NEST PCR plate 200ul",
            ),
            template_name="opentrons_96_wellplate_200ul_pcr_full_skirt",
            description="Template for 200ul PCR plate",
            tags=["Plate", "ANSI/SLAS", "96 Well", "PCR", "Labware"],
        )
    

    def push_new_assay_plate_resource(
            self,
            plate_num: int,
            location_name: str,
            experiment_id: int,
        ) -> None | Resource:
            """
            Pushes a new assay plate resource into the specified location, popping an existing plate in that location if necessary.
            """
            # get the resource id of the resource associated with the given location
            associated_resource_id = self.location_client.get_location_by_name(location_name).resource_id

            # get the resource object from the resource id
            resource_object = self.resource_client.get_resource(associated_resource_id)

            # check if the resource object currently has child resources (a plate already at that location)
            old_plate = None
            if resource_object.child:
                    # there is already a plate at this location
                    self.logger.log_info(f"A plate with ID {resource_object.child.resource_id} already exists at location: {location_name}")

                    # pop the old plate
                    popped_plate, updated_parent = self.resource_client.pop(resource=associated_resource_id)
                    self.logger.log_info(f"Popped plate with ID {resource_object.child.resource_id} from location: {location_name}")
                    old_plate = popped_plate


            # create a new assay plate resource and push it into the resource object associated with the given location
            new_plate = self.resource_client.create_resource_from_template(
                template_name = "opentrons_96_wellplate_200ul_pcr_full_skirt",
                resource_name = f"assay_plate_exp3_{experiment_id}_plate{plate_num}",
            )
            self.logger.log_info(f"Created new plate resource {new_plate.resource_name}, {new_plate.resource_id}")

            self.resource_client.push(
                resource = associated_resource_id,
                child = new_plate.resource_id,
            )
            self.logger.log_info(f"Pushed new plate resource into location {location_name}")
            return new_plate, old_plate
  

    def run_experiment(self) -> None:
        """main experiment function"""

        #TODO: plate starting on ot2 patrick deck 6 on temp block
        new_plate, old_plate = self.push_new_assay_plate_resource(
                plate_num=1,
                location_name="ot2_patrick_nest6_temp_block_wide",
                experiment_id=experiment_id,
            )

        # DEFINE PATHS AND VARIABLES ========
        run_robots = False  # if False, no robots will run
        run_resources = True
        test_prints = True  # if True, will print out extra info for testing purposes

        # Experiment ID and name
        experiment_id = self.experiment.experiment_id
        experiment_label = "1"

        # Directory paths
        app_directory = Path(__file__).parent.parent   # experiment app
        wf_directory = app_directory / "workflows"  # workflows
        protocol_directory = app_directory / "protocols"    # protocols

        # Workflow paths
        run_ot2_wf = wf_directory / "run_ot2_wf.yaml"
        ot2_to_thermocycler = (
            wf_directory / "ot2_to_thermocycler_wf.yaml"
        )

        # # workflow paths (pf400 transfers)
        # ot2_temp_block_to_thermocycler = wf_directory / "ot2_temp_block_to_thermocycler.yaml"


        # Protocol paths (for OT-2)
        golden_gate_protocol = protocol_directory / "pd_golden_gate_ot2.py"

        payload = {}


    
        # EXPERIMENT ACTIONS -------------------------------------------------------

        #TODO: TEST HARDCODED VERSION
        #run ot2 protocol
        payload["current_ot2_protocol"] = golden_gate_protocol
        workflow = self.workcell_client.submit_workflow(
            run_ot2_wf.resolve(),
            file_inputs={
                "ot2_protocol": payload["current_ot2_protocol"],
            },
        )

        #transfer destination plate to thermocycler and run
        workflow = self.workcell_client.submit_workflow(
            ot2_to_thermocycler.resolve(),
        )
        




if __name__ == "__main__":
    exp_app = PDApp()

    current_time = datetime.now()

    # Start experiment run
    with exp_app.manage_experiment(
        run_name = f"PD_Experiment{current_time.strftime('%Y%m%d_%H%M%S')}",
        run_description = "PD experiment",
    ):
        exp_app.start_app()