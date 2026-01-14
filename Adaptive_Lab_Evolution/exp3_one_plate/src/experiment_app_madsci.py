#!/usr/bin/env python3
"""Experiment application for the Adaptive Lab Evolution experiment"""

import time
from datetime import datetime
from pathlib import Path

import helper_functions
from madsci.common.types.experiment_types import ExperimentDesign
from madsci.client import ExperimentClient, WorkcellClient, LocationClient, ResourceClient
from madsci.common.types.node_types import NodeDefinition
from madsci.common.types.resource_types import Resource
from madsci.experiment_application import (
    ExperimentApplication,
    ExperimentApplicationConfig,
)
from pydantic import AnyUrl


class ALEApp(ExperimentApplication):
    """ALE Experiment Application

    # TODO:
    - collect bmg data output here and upload to globus?
    - change the experiment live based on a configuration file

    """

    experiment_design = ExperimentDesign(
        experiment_name="ALE_App",
    )
    config = ExperimentApplicationConfig(node_url=AnyUrl("http://localhost:6000"))
    experiment_client = ExperimentClient()
    workcell_client = WorkcellClient()
    location_client = LocationClient()
    resource_client = ResourceClient()
    experiment_id = None
    experiment_label = None


    def __init__(self) -> None:
        """Initializes the ALE Experiment App"""

        super().__init__()
        self.init_assay_plate_resource_template()


    def init_assay_plate_resource_template(self):
        """Initializes assay plate resource template"""

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
            return new_plate, old_plate


    def run_experiment(self) -> None:
        """main experiment function"""

        # DEFINE PATHS AND VARIABLES ========
        run_robots = True  # if False, no robots will run
        run_resources = True
        test_prints = True  # if True, will print out extra info for testing purposes

        # Experiment ID and name
        experiment_id = self.experiment.experiment_id
        experiment_label = "TFMN1_TEST6"

        # Directory paths
        app_directory = Path(__file__).parent.parent   # experiment app
        wf_directory = app_directory / "workflows"  # workflows
        protocol_directory = app_directory / "protocols"    # protocols
        csv_data_directory = "/home/rpl/workspace/Nidhi_data"
        bmg_data_output_directory = "C:\\Users\\RPL\\NIDHI_DATA"  # BMG data output directory on BMG PC

        # Workflow paths
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

        # Protocol paths (for OT-2)
        inoculate_protocol = protocol_directory / "inoculate.py"

        # Important variables
        # total_outer_loops = 40 # 40 # inoculations into new plate every 12ish hours
        total_outer_loops = 2 # 40 # inoculations into new plate every 12ish hours  # TESTING
        # total_inner_loops = 12 # 12 readings = ~ 12 hours between incubations
        total_inner_loops = 2 # TESTING
        incubation_seconds_initial = 10 # 36000 seconds = 10 hours
        # incubation_seconds_between_readings = 3600 # 3600 seconds = 1 hour
        incubation_seconds_between_readings = 36 # 3600 seconds = 1 hour  # TESTING

        plate_num = 0
        reading_in_plate_num = 10
        assay_plate_list = {}

        current_rack_nest_index = 0
        rack_nest_location_names = [
            "rack_row1_nest1",
            "rack_row1_nest2",
            "rack_row1_nest3",
            "rack_row2_nest1",
            "rack_row2_nest2",
            "rack_row2_nest3",
            "rack_row3_nest1",
            "rack_row3_nest2",
            "rack_row3_nest3",
            "rack_row4_nest1",
            "rack_row4_nest2",
            "rack_row4_nest3",
        ]

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
            "current_rack_nest": rack_nest_location_names[current_rack_nest_index],
            "current_rack_nest_safe_path": "safe_path_" + rack_nest_location_names[current_rack_nest_index],
            "use_existing_resources": False,
            "bmg_assay_name": "NIDHI",
        }

        # EXPERIMENT ACTIONS -------------------------------------------------------
        """
        Experiment setup at start:

        Location:
            exchange: inoculated microplate plate with lid
            ALL RACK NESTS (rows 1-4, nests 1-3 in each row): extra substrate microplates with lids
            OT-2 (ot2biobeta) decks 4-11: 20uL tip racks
            ALL OTHER LOCATIONS: EMPTY
        """

        # RESOURCES: Initial resources setup
        if run_resources:
            new_plate, old_plate = self.push_new_assay_plate_resource(
                plate_num=plate_num,
                location_name="exchange_nest_low_wide",
                experiment_id=experiment_id
            )
            assay_plate_list[plate_num] = new_plate.resource_id, new_plate.resource_name

        # RUN THE EXPERIMENT
        # 1. Move immediately into incubator with lid on for 10 hours
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

        # 2. Transfer plate 0 into bmg and take reading (plate0_T10)
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
            # collect associated resource id
            datapoint_id = workflow.get_datapoint_id(step_key="bmg_data", label="json_result")
            resource_id = self.data_client.get_datapoint_value(datapoint_id=datapoint_id)
            # write utc bmg timestamp to csv data file
            helper_functions.write_timestamps_to_csv(
                csv_directory_path=csv_data_directory,
                experiment_id=experiment_id,
                bmg_filename=payload["bmg_data_output_name"],
                accurate_timestamp=workflow.steps[8].end_time,  # index 8 = bmg reading
                resource_id=resource_id,
            )
            if test_prints:
                print(f"\twriting data to csv: {payload['bmg_data_output_name']}, with timestamp {workflow.steps[8].end_time}, and respource id {resource_id}")
        else:
            if test_prints:
                print(f"\twriting data to csv: {payload['bmg_data_output_name']}")

        # 3. Transfer old plate into the OT-2
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

            # RESOURCES: Populate current rack nest with a new assay plate
            if run_resources:
                new_plate, old_plate = self.push_new_assay_plate_resource(
                    plate_num=plate_num,
                    location_name=payload["current_rack_nest"],
                    experiment_id=experiment_id,
                )
                assay_plate_list[plate_num] = new_plate.resource_id, new_plate.resource_name
                # Log error if old plate is found, there should be no old plate returned here
                if old_plate:
                    if i < len(rack_nest_location_names):
                        self.logger.log_error(f"An old plate was returned from push_new_assay_plate_resource(): {old_plate.resource_id}. There should have been no existing plate resource at location {payload['current_rack_nest']}")
                # TESTING
                print(f"{assay_plate_list=}")
                time.sleep(5)



            # 4. Get new substrate plate, take contam reading, then move to OT-2 new location
            timestamp_now = int(datetime.now().timestamp())
            payload["bmg_data_output_name"] = (
                f"{experiment_label}_{timestamp_now}_{experiment_id}_exp1_{plate_num}_contam.txt"
            )
            if test_prints:
                print("getting new plate from rack")
                print(f"\tplate num: {plate_num}")
                print(f"\track location: {payload['current_rack_nest']}")
                print(f"\track safe path: {payload['current_rack_nest_safe_path']}")
            if run_robots:
                workflow = self.workcell_client.submit_workflow(
                    get_new_plate_and_run_bmg_wf.resolve(),
                    json_inputs={
                        "bmg_data_file_name": payload["bmg_data_output_name"],
                        "data_output_directory_path": bmg_data_output_directory,
                        "lid_location": payload["lid_location"],
                        "lid_safe_path": payload["lid_safe_path"],
                        "current_rack_nest": payload["current_rack_nest"],
                        "current_rack_nest_safe_path": payload["current_rack_nest_safe_path"],
                    },
                )
                # collect associated resource id
                datapoint_id = workflow.get_datapoint_id(step_key="bmg_data", label="json_result")
                resource_id = self.data_client.get_datapoint_value(datapoint_id=datapoint_id)
                # write utc bmg timestamp to csv data file
                helper_functions.write_timestamps_to_csv(
                    csv_directory_path=csv_data_directory,
                    experiment_id=experiment_id,
                    bmg_filename=payload["bmg_data_output_name"],
                    accurate_timestamp=workflow.steps[5].end_time, # index 5 = bmg reading
                    resource_id=resource_id,
                )
                if test_prints:
                    print(f"\twriting data to csv: {payload['bmg_data_output_name']}, with timestamp {workflow.steps[5].end_time}")
            else:
                if test_prints:
                    print(f"\twriting data to csv: {payload['bmg_data_output_name']}")

            # 5. Transfer new plate from bmg to new ot2 location
            if run_robots:
                workflow = self.workcell_client.submit_workflow(
                    bmg_to_ot2_wf.resolve(),
                    json_inputs={
                        "ot2_location": payload["ot2_location"],
                        "ot2_safe_path": payload["ot2_safe_path"],
                    },
                )

            # 6. Run inoculation ot2 protocol
            ot2_replacement_variables = helper_functions.collect_ot2_replacement_variables(payload)
            temp_ot2_file_str = helper_functions.generate_ot2_protocol(inoculate_protocol, ot2_replacement_variables)
            payload["current_ot2_protocol"] = temp_ot2_file_str
            if test_prints:
                print(f"running ot2 inoculation with tip box @ deck {payload['tip_box_location']}")
            if run_robots:
                workflow = self.workcell_client.submit_workflow(
                    run_ot2_wf.resolve(),
                    file_inputs={
                        "ot2_protocol": payload["current_ot2_protocol"],
                    },
                )

            # modify variables
            exp1_variables["tip_box_location"] += 1
            if exp1_variables["tip_box_location"] == 12:  # reset if necessary
                exp1_variables["tip_box_location"] = 4
            payload["tip_box_location"] = exp1_variables["tip_box_location"]

            # 7. Transfer new plate into bmg and take T0 reading
            timestamp_now = int(datetime.now().timestamp())
            payload["bmg_data_output_name"] = (
                f"{experiment_label}_{timestamp_now}_{experiment_id}_exp1_{plate_num}_T{reading_in_plate_num}.txt"
            )
            if run_robots:
                workflow = self.workcell_client.submit_workflow(
                    ot2_to_run_bmg_wf.resolve(),
                    json_inputs={
                        "bmg_data_file_name": payload["bmg_data_output_name"],
                        "data_output_directory_path": bmg_data_output_directory,
                        "ot2_location": payload["ot2_location"],
                        "ot2_safe_path": payload["ot2_safe_path"]
                    },
                )
                # collect associated resource id
                datapoint_id = workflow.get_datapoint_id(step_key="bmg_data", label="json_result")
                resource_id = self.data_client.get_datapoint_value(datapoint_id=datapoint_id)
                # write utc bmg timestamp to csv data file
                helper_functions.write_timestamps_to_csv(
                    csv_directory_path=csv_data_directory,
                    experiment_id=experiment_id,
                    bmg_filename=payload["bmg_data_output_name"],
                    accurate_timestamp=workflow.steps[4].end_time,  # index 5 = bmg reading
                    resource_id=resource_id,
                )
                if test_prints:
                    print(f"\twriting data to csv: {payload['bmg_data_output_name']}, with timestamp {workflow.steps[4].end_time}, and resource id {resource_id}")
            else:
                if test_prints:
                    print(f"\twriting data to csv: {payload['bmg_data_output_name']}")

            # modify variables
            reading_in_plate_num += 1

            # 8. Transfer from bmg to incubator and incubate (1hr)
            if run_robots:
                workflow = self.workcell_client.submit_workflow(
                    bmg_to_run_incubator_wf.resolve(),
                    json_inputs={
                        "lid_location": payload["lid_location"],
                        "lid_safe_path": payload["lid_safe_path"],
                        "incubator_location": payload["incubator_location"],
                        "incubation_seconds": payload["incubation_seconds"]
                    },
                )
            # capture incubation start time
            incubation_start_time = time.time()

            # modify variables
            payload["lid_location"] = exp1_variables["old_lid_location"]
            payload["lid_safe_path"] = exp1_variables["old_safe_lid_location"]
            payload["ot2_location"] = exp1_variables["old_ot2_plate_location"]

            # 9. Get rid of the old substrate plate
            if run_robots:
                workflow = self.workcell_client.submit_workflow(
                    remove_old_substrate_plate_wf.resolve(),
                    json_inputs={
                        "lid_location": payload["lid_location"],
                        "lid_safe_path": payload["lid_safe_path"],
                        "ot2_location": payload["ot2_location"],
                        "ot2_safe_path": payload["ot2_safe_path"],
                        "current_rack_nest": payload["current_rack_nest"],
                        "current_rack_nest_safe_path": payload["current_rack_nest_safe_path"]
                    },
                )

            # modify variables
            current_rack_nest_index += 1
            if current_rack_nest_index == 12:  # reset if necessary
                current_rack_nest_index = 0
            payload["current_rack_nest"] = rack_nest_location_names[current_rack_nest_index]
            payload["current_rack_nest_safe_path"] = "safe_path_" + rack_nest_location_names[current_rack_nest_index]

            # wait for incubation to finish
            if test_prints:
                print("running 1 hour incubation")
            if run_robots:
                while (time.time() - incubation_start_time) < payload["incubation_seconds"]:
                    print(f"will continue in... {int(payload['incubation_seconds']-(time.time() - incubation_start_time))} seconds")
                    time.sleep(5) # 5 seconds


            # INNER LOOP START HERE
            for j in range(total_inner_loops):

                # NOTE: lid can be removed to old location this whole time

                if test_prints:
                    print()
                    print(f"inner loop index = {j}")

                # 10. Incubator to run BMG  (T1 - T10 readings)
                if test_prints:
                    print(f"running incubator to bmg, taking T{j+1} reading")
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
                    # collect associated resource id
                    datapoint_id = workflow.get_datapoint_id(step_key="bmg_data", label="json_result")
                    resource_id = self.data_client.get_datapoint_value(datapoint_id=datapoint_id)
                    # write utc bmg timestamp to csv data file
                    helper_functions.write_timestamps_to_csv(
                        csv_directory_path=csv_data_directory,
                        experiment_id=experiment_id,
                        bmg_filename=payload["bmg_data_output_name"],
                        accurate_timestamp=workflow.steps[8].end_time,  # index 8 = bmg reading
                        resource_id=resource_id,
                    )
                    if test_prints:
                        print(f"\twriting data to csv: {payload['bmg_data_output_name']}, with timestamp {workflow.steps[8].end_time}, and resource id {resource_id}")
                else:
                    if test_prints:
                        print(f"\twriting data to csv: {payload['bmg_data_output_name']}")

                # modify variables
                reading_in_plate_num += 1

                if j < (total_inner_loops-1):
                    # 11. Transfer from bmg to incubator, and incubate
                    if test_prints:
                        print("running bmg to incubator")
                    if run_robots:
                        workflow = self.workcell_client.submit_workflow(
                            bmg_to_run_incubator_wf.resolve(),
                            json_inputs={
                                "lid_location": payload["lid_location"],
                                "lid_safe_path": payload["lid_safe_path"],
                                "incubator_location": payload["incubator_location"],
                                "incubation_seconds": payload["incubation_seconds"]
                            },
                        )
                    # capture incubation start time
                    incubation_start_time = time.time()

                    # sleep for incubation
                    if test_prints:
                        print("running 1 hour incubaton")
                    if run_robots:
                        while time.time() - incubation_start_time < payload["incubation_seconds"]:
                            print(f"will continue in... {int(payload['incubation_seconds']-(time.time() - incubation_start_time))} seconds")
                            time.sleep(5) # 5 seconds


                else:  # plate will end in the bmg with bmg open
                    # 12. transfer from bmg to ot2 old location
                    if test_prints:
                        print("running bmg to ot2")
                    if run_robots:
                        workflow = self.workcell_client.submit_workflow(
                            bmg_to_ot2_wf.resolve(),
                            json_inputs={
                                "ot2_location": payload["ot2_location"],
                                "ot2_safe_path": payload["ot2_safe_path"],
                            },
                        )

            # INNER LOOP END HERE

        # OUTER LOOP ENDS HERE

        # NOTE: if no more outer loops, plate ends at old ot-2 location with lid on lidnest 2
        # can't return plate to rack since we didn't grab a new substrate plate

        # 13. Move from old ot-2 location to exchange, replace lid.
        if test_prints:
            print("END OF EXPEREMENT APP: returning old plate from ot2 to exchange")
        if run_robots:
            workflow = self.workcell_client.submit_workflow(
                at_end_ot2_to_exchange_wf.resolve(),
                json_inputs={
                    "ot2_location": payload["ot2_location"],
                    "ot2_safe_path": payload["ot2_safe_path"],
                    "lid_location": payload["lid_location"],
                    "lid_safe_path": payload["lid_safe_path"]
                },
            )

        print("YAY WE MADE IT!")




if __name__ == "__main__":
    exp_app = ALEApp()

    current_time = datetime.now()

    # Start experiment run
    with exp_app.manage_experiment(
        run_name = f"ALE_Exp3_OnePlate_{current_time.strftime('%Y%m%d_%H%M%S')}",
        run_description = "Adaptive Lab Evolution Experiment 3 - One Plate",
    ):
        exp_app.start_app()


