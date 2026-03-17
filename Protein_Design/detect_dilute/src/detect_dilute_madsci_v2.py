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
        ot2_to_thermocycler = (
            transfers_directory / "ot2_to_thermocycler.yaml"
        )

        # Protocol paths (for OT-2)
        golden_gate_protocol = protocol_directory / "pd_golden_gate_ot2.py"

        thermocycler_to_flex = (
             transfers_directory / "thermocycler_to_flex.yaml"
        )

        controls_to_flex = (
             transfers_directory / "controls_to_flex.yaml"
        )

        sybrgreen_to_flex = (
             transfers_directory / "sybrgreen_to_flex.yaml"
        )

        empty_pcr_to_ot2 = (
             transfers_directory / "sybrgreen_to_flex.yaml"
        )

        pcr_plate_to_ot2_block = (
             transfers_directory / "pcr_plate_to_ot2_block.yaml"
        )

        pcr_plate_to_ot2_block_2 = (
             transfers_directory / "pcr_plate_to_ot2_block_2.yaml"
        )

        A4_to_C1 = protocol_directory / "pcr_A4_to_C1.py"
        A4_to_B1 = protocol_directory / "pcr_A4_to_B1.py"
        A4_to_C2 = protocol_directory / "pcr_A4_to_C2.py"
        C1_to_A4 = protocol_directory / "pcr_C1_to_A4.py"

        payload = {}



        # EXPERIMENT ACTIONS -------------------------------------------------------


        #verify all temp blocks on flex and ot2 set to 4 deg

        #move pcr plate to cool block in flex C1
        workflow = self.workcell_client.submit_workflow(
            thermocycler_to_flex.resolve(),
        )

        payload["current_flex_protocol"] = A4_to_C1
        workflow = self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={
                "flex_protocol": payload["current_flex_protocol"],
            },
        )

        #move controls plate (FROM?) to cool block in flex #TODO: needs to be cooled
        workflow = self.workcell_client.submit_workflow(
            controls_to_flex.resolve(),
        )

        payload["current_flex_protocol"] = A4_to_B1
        workflow = self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={
                "flex_protocol": payload["current_flex_protocol"],
            },
        )

        #move empty sybrgreen plate to flex
        workflow = self.workcell_client.submit_workflow(
            sybrgreen_to_flex.resolve(),
        )

        payload["current_flex_protocol"] = A4_to_C2
        workflow = self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={
                "flex_protocol": payload["current_flex_protocol"],
            },
        )

        #move empty diluted pcr plate to OT-2 (6)
        workflow = self.workcell_client.submit_workflow(
            empty_pcr_to_ot2.resolve(),
        )

        #multichannel flex protocol
        payload["current_ot2_protocol"] = dd_flex_protocol
        workflow = self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={
                "flex_protocol": payload["current_flex_protocol"],
            },
        )

#move pcr products plate from flex to cool block in ot2 (4)
        payload["current_flex_protocol"] = C1_to_A4
        workflow = self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={
                "flex_protocol": payload["current_flex_protocol"],
            },
        )

        # #WORKING
        workflow = self.workcell_client.submit_workflow(
            pcr_plate_to_ot2_block.resolve(),
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
            pcr_plate_to_ot2_block_2.resolve(),
        )


        

#TODO

        #move controls from flex to ot-2
        workflow = self.workcell_client.submit_workflow(
            controls_flex_to_ot2.resolve(),
        )

        #ot2 dilution protocol

        payload["current_ot2_protocol"] = pcr_ot2_protocol
        workflow = self.workcell_client.submit_workflow(
            run_ot2_wf.resolve(),
            file_inputs={
                "ot2_protocol": payload["current_ot2_protocol"],
            },
        )

        #move sybrgreen plate to the hidex
        workflow = self.workcell_client.submit_workflow(
            ot2_to_hidex.resolve(),
        )

        #run hidex protocol
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