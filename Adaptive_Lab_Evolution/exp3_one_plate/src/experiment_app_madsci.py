#!/usr/bin/env python3
"""Experiment application for the Adaptive Lab Evolution experiment"""

import time
from datetime import datetime
from pathlib import Path

import helper_functions
from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.node_types import NodeDefinition
from madsci.experiment_application import (
    ExperimentApplication,
    ExperimentApplicationConfig,
)
from madsci.common.types.resource_types import Resource
from pydantic import AnyUrl


class ALEApp(ExperimentApplication):
    """ALE Experiment Application"""

    experiment_design = ExperimentDesign(
        experiment_name="ALE_App",
    )
    config = ExperimentApplicationConfig(node_url=AnyUrl("http://localhost:6000"))

    experiment_id = None
    experiment_label = None


    def __init__(self) -> None:
        """Initializes the ALE Experiment App"""

        super().__init__()


        self.init_assay_plate_resource_template()


    def init_assay_plate_resource_template(self):

        self.resource_client.create_template(
            resource=Resource(
                resource_description="Flat Bottom 96 Well Plate",
            ),
            template_name="flat_bottom_96_well_plate",
            description="Template for flat bottom 96 well plates used in ALE experiments",
            tags=["Plate", "ANSI/SLAS", "96 Well", "Flat Bottom", "Labware"],
        )

    def push_new_assay_plate_resource(
        self,
        plate_num: int,
        location_name: str,
        experiment_id: int,
    ) -> None | Resource:
        """
        Pushes a new assay plate resource into the specified location, popping an existing plate in that location if necessary.

        # TODO: extract into another file
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
            template_name = "flat_bottom_96_well_plate",
            resource_name = f"assay_plate_exp3_{experiment_id}_plate{plate_num}",
        )
        self.logger.log_info(f"Created new plate resource {new_plate.resource_name}, {new_plate.resource_id}")

        self.resource_client.push(
            resource = associated_resource_id,
            child = new_plate.resource_id,
        )
        self.logger.log_info(f"Pushed new plate resource into location {location_name}")
        return old_plate


    def run_experiment(self) -> None:
        """main experiment function"""

        # DEFINE PATHS AND VARIABLES ========
        # capture the experiment ID
        experiment_id = self.experiment.experiment_id   # TODO: figure out how to get experiment ID
        experiment_label = "3"

        # directory paths
        app_directory = Path(__file__).parent.parent   # experiment app
        wf_directory = app_directory / "workflows"  # workflows
        protocol_directory = app_directory / "protocols"    # protocols

        # workflow paths
        run_ot2_wf = wf_directory / "run_ot2_wf.yaml"
        exchange_to_run_incubator_wf = (
            wf_directory / "exchange_to_run_incubator_wf.yaml"
        )
        incubator_to_run_bmg_wf = (
            wf_directory / "incubator_to_run_bmg_wf.yaml"
        )
        get_new_plate_and_run_bmg_wf = (
            wf_directory / "get_new_plate_and_run_bmg_wf.yaml"
        )
        bmg_to_ot2_wf = (
            wf_directory / "bmg_to_ot2_wf.yaml"
        )
        ot2_to_run_bmg_wf = (
            wf_directory / "ot2_to_run_bmg_wf.yaml"
        )
        bmg_to_run_incubator_wf = (
            wf_directory / "bmg_to_run_incubator_wf.yaml"
        )
        remove_old_substrate_plate_wf = (
            wf_directory / "remove_old_substrate_plate_wf.yaml"
        )
        at_end_ot2_to_exchange_wf = (
            wf_directory / "at_end_ot2_to_exchange_wf.yaml"
        )

        # protocol paths (for OT-2)
        inoculate_protocol = protocol_directory / "inoculate.py"

        # important variables
        run_robots = True  # if False, no robots will run
        test_prints = True  # if True, will print out extra info for testing purposes
        # total_outer_loops = 33 # 33 # inoculations into new plate every 10ish hours
        total_outer_loops = 1  # TESTING
        # total_inner_loops = 10 # 10 readings (T1 happens before the inner loop starts, only need 9 more inner loops)
        total_inner_loops = 1 # TESTING

        plate_num = 0
        reading_in_plate_num = 10
        current_tower_nest = 1
        csv_data_directory = "/home/rpl/workspace/Nidhi_data"
        bmg_data_output_directory = "C:\\Users\\RPL\\NIDHI_DATA"  # BMG data output directory on BMG PC

        incubation_seconds_initial = 10 # 36000 seconds = 10 hours
        incubation_seconds_between_readings = 3600 # 3600 seconds = 1 hour

        assay_plate_resources = {}

        exp1_variables = {
            "old_lid_location": "lidnest_2_wide", # use old lid location at start
            "new_lid_location": "lidnest_1_wide",
            "old_safe_lid_location": "safe_path_lidnest_2",
            "new_safe_lid_location": "safe_path_lidnest_1",
            "ot2_node": "ot2_spongebob",
            "new_ot2_plate_location": "ot2_spongebob_nest1_wide",
            "old_ot2_plate_location": "ot2_spongebob_nest3_wide",
            "ot2_safe_path": "safe_path_ot2_spongebob",
            "incubator_node": "inheco_devID2_floor0",
            "incubator_location": "inheco_devID2_floor0_nest",
            "tip_box_location": 4,
            "new_stack": "stack1",
            "trash_stack": "stack4",
        }

        # initial payload setup
        payload = {
            "lid_location": exp1_variables["old_lid_location"],
            "lid_safe_path": exp1_variables["old_safe_lid_location"],
            "ot2_node": exp1_variables["ot2_node"],
            "ot2_location": exp1_variables["old_ot2_plate_location"],
            "ot2_safe_path": exp1_variables["ot2_safe_path"],
            "tip_box_location": exp1_variables["tip_box_location"],
            "incubator_node": exp1_variables["incubator_node"],
            "incubator_location": exp1_variables["incubator_location"],
            "incubation_seconds": incubation_seconds_initial,
            "current_ot2_protocol": None,
            "current_tower_nest": "tower_nest" + str(current_tower_nest),
            "current_tower_nest_safe_path": "safe_path_tower_nest" + str(current_tower_nest),
            "use_existing_resources": False,
            "bmg_assay_name": "NIDHI",
        }

        # EXPERIMENT ACTIONS -------------------------------------------------------
        """
        Experiment setup at start:

        Location:
            exchange: inoculated microplate plate with lid
            Tower decks 1-5: extra substrate microplates with lids
            OT-2 (ot2biobeta) decks 4-11: 20uL tip racks
            ALL OTHER LOCATIONS: EMPTY
        """

        # RESORUCES: Initial resources setup
        self.push_new_assay_plate_resource(
            plate_num=plate_num,
            location_name="exchange_nest_low_wide",
            experiment_id=experiment_id
        )

        # # RUN THE EXPERIMENT
        # 1. Move immediately into incubator with lid on for 10 hours -- WORKING
        if run_robots:
            workflow = self.workcell_client.submit_workflow(
                exchange_to_run_incubator_wf.resolve(),
                json_inputs={
                    "incubator_location": payload["incubator_location"],
                    "incubation_seconds": payload["incubation_seconds"],
                },
            )

        # capture incubation start time
        incubation_start_time = time.time()

        # wait for incubation to finish
        if test_prints:
            print("running 10 hour incubation")
        if run_robots:
            while time.time() - incubation_start_time < payload["incubation_seconds"]:
                print(
                    f"will continue in... {int(payload['incubation_seconds'] - (time.time() - incubation_start_time))} seconds"
                )
                time.sleep(5)  # 5 seconds

                if time.time() - incubation_start_time >= payload["incubation_seconds"]:
                    print("Incubation complete.")
                    break

        # 2. Transfer plate 0 into bmg and take reading (plate0_T10) --  WORKING
        timestamp_now = int(datetime.now().timestamp())
        payload["bmg_data_output_name"] = (
            f"{experiment_label}_{timestamp_now}_{experiment_id}_exp1_{plate_num}_T{reading_in_plate_num}.txt"
        )
        if run_robots:
            workflow = self.workcell_client.submit_workflow(
                incubator_to_run_bmg_wf.resolve(),
                json_inputs={
                    "incubator_location": payload["incubator_location"],
                    "incubation_seconds": payload["incubation_seconds"],
                    "lid_location": payload["lid_location"],
                    "lid_safe_path": payload["lid_safe_path"],
                    "bmg_data_output_name": payload["bmg_data_output_name"],
                    "data_output_directory_path": bmg_data_output_directory,
                },
            )
            # write utc bmg timestamp to csv data file
            helper_functions.write_timestamps_to_csv(
                csv_directory_path=csv_data_directory,
                experiment_id=experiment_id,
                bmg_filename=payload["bmg_data_output_name"],
                accurate_timestamp=workflow.steps[8].end_time,  # index 8 = bmg reading
            )
            if test_prints:
                print(f"\twriting data to csv: {payload['bmg_data_output_name']}, with timestamp {workflow.steps[8].end_time}")
        else:
            if test_prints:
                print(f"\twriting data to csv: {payload['bmg_data_output_name']}")

        # 3. Transfer old plate into the OT-2  -- working
        if run_robots:
            workflow = self.workcell_client.submit_workflow(
                bmg_to_ot2_wf.resolve(),
                json_inputs={
                    "ot2_location": payload["ot2_location"],
                    "ot2_safe_path": payload["ot2_safe_path"],
                },
            )

        # OUTER LOOP START
        for i in range(total_outer_loops):

            if test_prints:
                print(f"\nOUTER LOOP INDEX: {i} -------------------")

            # modify variables
            plate_num += 1
            reading_in_plate_num = 0
            payload["lid_location"] = exp1_variables["new_lid_location"]
            payload["lid_safe_path"] = exp1_variables["new_safe_lid_location"]
            payload["ot2_location"] = exp1_variables["new_ot2_plate_location"]
            payload["incubation_seconds"] = incubation_seconds_between_readings

            # RESOURCES: Populate current tower nest with a new assay plate
            old_plate = self.push_new_assay_plate_resource(
                plate_num=plate_num,
                location_name=payload["current_tower_nest"],
                experiment_id=experiment_id,
            )
            # Log error if old plate is found, there should be no old plate returned here
            if old_plate:
                self.logger.log_error(f"An old plate was returned from push_new_assay_plate_resource(): {old_plate.resource_id}. There should have been no existing plate resource at location {payload['current_tower_nest']}")

            # 4. Get new substrate plate, take contam reading, then move to OT-2 new location
            timestamp_now = int(datetime.now().timestamp())
            payload["bmg_data_output_name"] = (
                f"{experiment_label}_{timestamp_now}_{experiment_id}_exp1_{plate_num}_contam.txt"
            )
            if test_prints:
                print("getting new plate from tower")
                print(f"\tplate num: {plate_num}")
                print(f"\ttower location: {payload['current_tower_nest']}")
                print(f"\ttower safe path: {payload['current_tower_nest_safe_path']}")
            if run_robots:
                workflow = self.workcell_client.submit_workflow(
                    get_new_plate_and_run_bmg_wf.resolve(),
                    json_inputs={
                        "bmg_data_file_name": payload["bmg_data_output_name"],
                        "data_output_directory_path": bmg_data_output_directory,
                        "lid_location": payload["lid_location"],
                        "lid_safe_path": payload["lid_safe_path"],
                        "current_tower_nest": payload["current_tower_nest"],
                        "current_tower_nest_safe_path": payload["current_tower_nest_safe_path"],
                    },
                )
                # write utc bmg timestamp to csv data file
                helper_functions.write_timestamps_to_csv(
                    csv_directory_path=csv_data_directory,
                    experiment_id=experiment_id,
                    bmg_filename=payload["bmg_data_output_name"],
                    accurate_timestamp=workflow.steps[5].end_time,  # index 5 = bmg reading
                )
                if test_prints:
                    print(f"\twriting data to csv: {payload['bmg_data_output_name']}, with timestamp {workflow.steps[5].end_time}")
            else:
                if test_prints:
                    print(f"\twriting data to csv: {payload['bmg_data_output_name']}")




if __name__ == "__main__":
    exp_app = ALEApp()

    current_time = datetime.now()

    # Start experiment run
    with exp_app.manage_experiment(
        run_name = f"ALE_Exp3_OnePlate_{current_time.strftime('%Y%m%d_%H%M%S')}",
        run_description = "Adaptive Lab Evolution Experiment 3 - One Plate",
    ):
        exp_app.start_app()


