#!/usr/bin/env python3
"""Experiment application for the Protein Design experiment"""

import time
from datetime import datetime
from pathlib import Path

from madsci.common.types.experiment_types import ExperimentDesign
from madsci.client import ExperimentClient, WorkcellClient, LocationClient, ResourceClient
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
    experiment_client = ExperimentClient()
    workcell_client = WorkcellClient()
    location_client = LocationClient()
    resource_client = ResourceClient()
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

        self.resource_client.create_template(
            resource=Resource(
                resource_description="ot2 20ul tiprack",
            ),
            template_name="opentrons_96_filtertiprack_20ul",
            description="Template for ot2 20ul tiprack",
            tags=["Tiprack", "ANSI/SLAS", "96 Well", "Labware"],
        )

        self.resource_client.create_template(
            resource=Resource(
                resource_description="otflex 50ul tiprack",
            ),
            template_name="opentrons_flex_96_filtertiprack_50ul",
            description="Template for OT-Flex 50ul tiprack",
            tags=["Tiprack", "ANSI/SLAS", "96 Well", "Labware"],
        )

        self.resource_client.create_template(
            resource=Resource(
                resource_description="otflex 200ul tiprack",
            ),
            template_name="opentrons_flex_96_filtertiprack_200ul",
            description="Template for 200ul OT-Flex tiprack",
            tags=["Tiprack", "ANSI/SLAS", "96 Well", "Labware"],
        )


    def push_new_assay_plate_resource(
            self,
            plate_num: int,
            location_name: str,
            experiment_id: int,
            name: str,
        ) -> None | Resource:
            """
            Pushes a new assay plate resource into the specified location, popping an existing plate in that location if necessary.
            """
            # get the resource id of the resource associated with the given location
            associated_resource_id = self.location_client.get_location_by_name(location_name).resource_id
            print("Location name: ", location_name)
            print("ASSC Resource id: ", associated_resource_id)
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
            # if name == "opentrons_96_wellplate_200ul_pcr_full_skirt":

            new_plate = self.resource_client.create_resource_from_template(
                template_name = name,
                resource_name = f"res_{experiment_id}_plate{plate_num}",
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
        # new_plate, old_plate = self.push_new_assay_plate_resource(
        #         location_name="ot2_patrick_nest6_temp_block_wide",
        #     )

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
        run_directory = wf_directory / "run_instrument"
        transfers_directory = wf_directory / "transfers"
        protocol_directory = app_directory / "protocols"    # protocols

        # Workflow paths
        run_ot2_wf = run_directory / "run_ot2_wf.yaml"
        run_flex_wf = run_directory / "run_flex.yaml"
        run_hidex = run_directory / "run_hidex.yaml"
        ot2_to_thermocycler = (
            transfers_directory / "ot2_to_thermocycler.yaml"
        ) 

        # Protocol paths (for OT-2)
        golden_gate_protocol = protocol_directory / "pd_golden_gate_ot2.py"

        A4_to_B1 = protocol_directory / "pcr_A4_to_B1.py"

        controls_plate_to_flex = (
             transfers_directory / "rmf_mixes_to_flex.yaml"
        )

        cfps_plate_to_peeler_to_flex = (
             transfers_directory / "cfps_plate_to_peeler_to_flex.yaml"
        )

        cfps_plate_to_peeler_to_flex_2 = (
             transfers_directory / "cfps_plate_to_peeler_to_flex2.yaml"
        )
        fdglu_to_hidex = (
             transfers_directory / "fdglu_to_hidex.yaml"
        )

        payload = {}



        # EXPERIMENT ACTIONS -------------------------------------------------------

        #move controls plate from? to cool block on flex
        workflow = self.workcell_client.submit_workflow(
            controls_plate_to_flex.resolve(),
        )

        payload["current_flex_protocol"] = A4_to_B1
        workflow = self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={
                "flex_protocol": payload["current_flex_protocol"],
            },
        )

        # move empty fdglu assay plate to flex

        workflow = self.workcell_client.submit_workflow(
            fdglu_plate_to_flex.resolve(),
        )

        payload["current_flex_protocol"] = A4_to_B3 #TODO
        workflow = self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={
                "flex_protocol": payload["current_flex_protocol"],
            },
        )

        # cfps plate on heater shaker, peel and put back in flex (spin down?)
        payload["current_flex_protocol"] = D1_to_A4 #TODO
        workflow = self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={
                "flex_protocol": payload["current_flex_protocol"],
            },
        )

        workflow = self.workcell_client.submit_workflow(
            cfps_plate_to_peeler_to_flex.resolve(),
        )

        new_plate, old_plate = self.push_new_assay_plate_resource(
            plate_num=plate_num,
            location_name="exchange_nest_low_narrow",
            experiment_id=experiment_id,
            name="opentrons_96_wellplate_200ul_pcr_full_skirt"
        )

        plate_num+=1

        # #WORKING
        workflow = self.workcell_client.submit_workflow(
            cfps_plate_to_peeler_to_flex_2.resolve(),
        )

        payload["current_flex_protocol"] = A4_to_B2 #TODO
        workflow = self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={
                "flex_protocol": payload["current_flex_protocol"],
            },
        )

        # flex fdglu protocol

         # payload["current_flex_protocol"] = cfps_flex_protocol
        # workflow = self.workcell_client.submit_workflow(
        #     run_flex_wf.resolve(),
        #     file_inputs={
        #         "flex_protocol": payload["current_flex_protocol"],
        #     },
        # )

        #move fdglu assay plate to hidex
        payload["current_flex_protocol"] = B3_to_A4 #TODO
        workflow = self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={
                "flex_protocol": payload["current_flex_protocol"],
            },
        )

        #run hidex
        workflow = self.workcell_client.submit_workflow(
            cfps_plate_to_peeler_to_flex.resolve(),
        )

        workflow = self.workcell_client.submit_workflow(
            fdglu_to_hidex.resolve(),
        )

        workflow = self.workcell_client.submit_workflow(
            run_hidex.resolve(),
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