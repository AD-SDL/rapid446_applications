import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import random
from typing import Any, ClassVar, Optional, Union
from dotenv import load_dotenv

from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.resource_types import Collection, Resource, Slot

from madsci.experiment_application.experiment_script import ExperimentScript
from pottery import Redlock

from redis import Redis

# Add the root project folder (TFMN4 directory) to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from utils import helper_functions
from utils import lab_mail
from utils.load_settings import try_reload_config

# loads .env into environment
load_dotenv()

# Set up redis for exchange location lock
redis_host = os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_password = os.getenv("REDIS_PASSWORD")
exchange_auto_unlock_seconds = 86400 # 86400 seconds = 24 hours
exchange_lock_timeout = 7200 # 7200 seconds = 2 hours
exchange_waiters_key = "exchange_waiters"

redis = Redis(
    host=redis_host,
    port=redis_port,
    # password=redis_password,  
)

# TEST PING TO REDIS
try:
    redis.ping()
    print("Sent ping")
except Exception as e:
    print("Redis connection error.", flush=True)
    raise e

class ALEApp(ExperimentScript,):
    """ALE Experiment Application

    # TODO:
    - collect bmg data output here and upload to globus?
    - get rid of payload to collect variables.
        - although some variables shouldn't be changeable mid-experiment...

    """
    experiment_design = ExperimentDesign(
        experiment_name="ALE_App",
        
    )

    experiment_id = None
    experiment_label = None

    # Experiment settings file
    experiment_settings_file = None
    exeriment_settings = {}
    try_reload_config.last_mtime = None

    exchange_lock = None

    def _validate_settings_path(self):
        if not os.path.isfile(self.experiment_settings_file):
            raise FileNotFoundError(
                f"Settings file not found: {self.experiment_settings_file}"
            )

    def _push_new_assay_plate_resource(
            self,
            plate_num: int,
            location_name: str,
            experiment_id: int,
            experiment_label: str,
            experiment_number: str,
        ) -> None | Resource:
            """
            Pushes a new assay plate resource into the specified location, popping an existing plate in that location if necessary.
            """
            # Get the resource id of the resource associated with the given location.
            associated_resource_id = self.location_client.get_location_by_name(location_name).resource_id

            # Get the resource object from the resource id.
            resource_object = self.resource_client.get_resource(associated_resource_id)

            # Check if the resource object currently has child resources (a plate already at that location).
            old_plate = None
            if len(resource_object.children) > 0:
                    # There is already a plate at this location.
                    self.logger.log_info(f"Child resources already exist at this location. Child resources = {resource_object.children}")

                    # Pop the old plate.
                    popped_plate, updated_parent = self.resource_client.pop(resource=associated_resource_id)
                    self.logger.log_info(f"Popped plate with ID {popped_plate.resource_id} from location: {location_name}")
                    old_plate = popped_plate


            # Create a new assay plate resource and push it into the resource object associated with the given location.
            lid_resource = Resource(
                resource_name = f"lid_for_plate_{plate_num}_expID_{experiment_id}",
                attributes={
                    "lid": True
                }
            )

            new_plate = Collection(
                resource_name=f"assay_plate_{experiment_label}_{experiment_number}_{experiment_id}_plate{plate_num}",
                resource_class="Microplate",
                capacity=2, # lid slot and seal slot
                attributes={
                    # Common attributes
                    "plate_height": 14, 
                    "lid_height": 10,
                    "plate_height_with_lid": 16,
                    "description": "96-well microplate with or without lid",

                    # PF400 specific attributes
                    "pf400_grip_height": 3,
                    "pf400_lid_only_grip_height":4,
                    "pf400_lid_removal_grip_height": 10,

                    # SciClops specific attributes
                    "sciclops_grip_height": 1, 
                    "sciclops_lid_grip_height": 4, 
                    "sciclops_lid_removal_grip_height": 12,
                },
                children={
                    "lid_slot": Slot(
                        resource_name = "lid slot resource",
                        children=[lid_resource]
                    )
                }
            )
            self.resource_client.add_resource(new_plate)
            self.logger.log_info(f"Created new plate resource {new_plate.resource_name}, {new_plate.resource_id}")

            self.resource_client.push(
                resource = associated_resource_id,
                child = new_plate.resource_id,
            )
            self.logger.log_info(f"Pushed new plate resource into location {location_name}")
            return new_plate, old_plate


    def jitter(self) -> None:
        "Implements polite random jitter to assist in schedueling fairness between the running experiments."
        waiters = int(redis.get(exchange_waiters_key) or 0)
        print(f"Processes waiting for exchange lock = {waiters}", flush=True)
        if waiters > 0:
            print("Using polite jitter.", flush=True)
            time.sleep(random.uniform(1.0, 3.0))   # be polite
        else:
            print("Using fast jitter.",flush=True)
            time.sleep(random.uniform(0.1, 0.5))   # go fast


    def run_experiment(self, *args, **kwargs) -> None:
        """main experiment function"""

        # Collect, validate, and load experiment settings file 
        self.experiment_settings_file = kwargs.get("settings_file")
        self._validate_settings_path()
        self.experiment_settings = try_reload_config(
            config_file=self.experiment_settings_file
        )

        # Set up exchange lock
        self.exchange_lock = Redlock(
            key='exchange_nest',
            masters={redis},
            auto_release_time=exchange_auto_unlock_seconds,
            context_manager_blocking=True,
            context_manager_timeout=exchange_lock_timeout,
        )
        self.acquired = False

        # --- DEFINE PATHS AND STARTING VARIABLES ---
        run_robots = True
        run_resources = True
        test_prints = True

        # Directory paths.
        app_directory = Path(__file__).parent.parent   # experiment app
        wf_directory = app_directory / "workflows"  # workflows
        protocol_directory = app_directory / "protocols"    # protocols
        csv_data_directory = "/home/rpl/workspace/Nidhi_data"
        bmg_data_output_directory = "C:\\Users\\RPL\\NIDHI_DATA"  # BMG data output directory on BMG PC

        # Workflow paths.
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
        trash_final_plate_wf = (
            wf_directory / "trash_final_plate_wf.yaml"
        )

        # Protocol paths (for OT-2).
        inoculate_protocol = protocol_directory / "inoculate.py"

        # Important variables.
        experiment_id = self.experiment.experiment_id
        plate_num = 0
        reading_in_plate_num = 12
        current_outer_loop = 0
        current_inner_loop = 0
        assay_plate_list = {}
        tip_box_location = 4

        # Initial payload setup
        payload = {
            "experiment_label": self.experiment_settings["experiment_label"],
            "experiment_number": self.experiment_settings["experiment_number"],

            "lid_location": self.experiment_settings["old_lid_location"],

            "ot2_node": self.experiment_settings["ot2_node"],
            "ot2_location": self.experiment_settings["old_ot2_plate_location"],
            "inoculation_volume": self.experiment_settings["inoculation_volume"],
            "tip_box_location": tip_box_location,
            "current_ot2_protocol": None,
            "use_existing_resources": False,

            "incubator_node": self.experiment_settings["incubator_node"],
            "incubator_location": self.experiment_settings["incubator_location"],
            "incubation_seconds": self.experiment_settings["incubation_seconds_initial"],

            "sciclops_stack_new_plates": self.experiment_settings["sciclops_stack_new_plates"],
            "sciclops_stack_old_plates": self.experiment_settings["sciclops_stack_old_plates"],

            "bmg_assay_name": "NIDHI",
        }
        if test_prints:
            self.logger.log_info(f"{payload=}", flush=True)

        # --- EXPERIMENT ACTIONS -------------------------------------------------------
        """
        Experiment setup at start:

        Location:
            exchange: inoculated microplate plate with lid
            Stack (1 or 2 depending on settings JSON): extra substrate microplates with lids
            OT-2 (ot2_spongebob or ot2_patrick depending on settings JSON) decks 4-11: 20uL tip racks
            ALL OTHER LOCATIONS: EMPTY
        """
        # Increase waiting processes count in redis before trying to acquired the lock
        self.acquired = False
        redis.incr(exchange_waiters_key)

        # TESTING:
        self.logger.log_info(f"{payload['experiment_number']} is waiting for the exchange lock.", flush=True)
        waiters = int(redis.get(exchange_waiters_key) or 0)
        self.logger.log_info(f"{waiters=}", flush=True)

        try:
            with self.exchange_lock:
                # Exchange lock is LOCKED for step 1 workflow.
                self.logger.log_info(f"\nExchange is LOCKED by {self.experiment_settings['experiment_number']}", flush=True)

                # Decrease waiting process count after lock is acquired.
                self.acquired = True
                redis.decr(exchange_waiters_key)

                # --- 1. TRANSFER IMMEDIATELY FROM EXCHANGE TO INCUBATOR ---  # WORKING!
                # ResourceHandler: Push starting plate into exchange.
                if run_resources:
                    new_plate, old_plate = self._push_new_assay_plate_resource(
                        plate_num=plate_num,
                        location_name="exchange_wide",
                        experiment_id=experiment_id,
                        experiment_label=payload["experiment_label"],
                        experiment_number=payload["experiment_number"]
                    )
                    assay_plate_list[plate_num] = new_plate.resource_id, new_plate.resource_name
                    pass

                # Run the workflow: exchange_to_run_incubator_wf.yaml
                if run_robots:
                    workflow = self.workcell_client.submit_workflow(
                        exchange_to_run_incubator_wf.resolve(),
                        json_inputs={
                            "incubator_node": payload["incubator_node"],
                            "incubator_location": payload["incubator_location"],
                            "incubation_seconds": payload["incubation_seconds"],
                        },
                    )
                # Exchange lock is UNLOCKED.
                self.logger.log_info(f"\nExchange is UNLOCKED by {self.experiment_settings['experiment_number']}", flush=True)
            
        finally:
            # Always clean up the waiting process count.
            if not self.acquired:
                redis.decr(exchange_waiters_key)

        # Polite jitter to aid scheduling fairness
        self.jitter()

        # Reload experiment settings and capture incubation start time.
        self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)
        payload["incubation_seconds"] = self.experiment_settings["incubation_seconds_initial"]
        incubation_start_time = time.time()

        # Wait for incubation to finish
        helper_functions.wait_for_incubation(payload["incubation_seconds"])

        # LOCK exchange lock for steps 2 and 3.
        # Increase waiting processes count in redis before trying to acquire the lock
        self.acquired = False
        redis.incr(exchange_waiters_key)

        # TESTING:
        self.logger.log_info(f"{payload['experiment_number']} is waiting for the exchange lock.", flush=True)
        waiters = int(redis.get(exchange_waiters_key) or 0)
        self.logger.log_info(f"{waiters=}", flush=True)

        try:
            with self.exchange_lock:
                self.logger.log_info(f"\nExchange is LOCKED by {self.experiment_settings['experiment_number']}", flush=True)

                # Decrease waiting process count after lock is acquired.
                self.acquired = True
                redis.decr(exchange_waiters_key)

                # --- 2. TRANSFER PLATE0 INTO BMG AND TAKE READING ---  WORKING!
                # Note: This will be an endpoint reading for plate0

                # Set variables.
                timestamp_now = int(datetime.now().timestamp())
                payload["bmg_data_output_name"] = (
                    f"{payload['experiment_label']}_{timestamp_now}_{experiment_id}_{payload['experiment_number']}_{plate_num}_{reading_in_plate_num}.txt"
                )

                # Run the workflow: incubator_to_run_bmg_wf.yaml
                if run_robots:
                    workflow = self.workcell_client.submit_workflow(
                        incubator_to_run_bmg_wf.resolve(),
                        json_inputs={
                            "incubator_location": payload["incubator_location"],
                            "incubation_seconds": payload["incubation_seconds"],
                            "incubator_node": payload["incubator_node"],
                            "lid_location": payload["lid_location"],
                            "bmg_data_output_name": payload["bmg_data_output_name"],
                            "data_output_directory_path": bmg_data_output_directory,
                        },
                    )

                    # Collect associated resource ID.
                    resource_datapoint_id = workflow.get_datapoint(step_key="bmg_data", label="json_result").datapoint_id
                    resource_id = self.data_client.get_datapoint_value(datapoint_id=resource_datapoint_id)

                    # Write UTC BMG timestamp to CSV data file.
                    helper_functions.write_timestamps_to_csv(
                        csv_directory_path=csv_data_directory,
                        experiment_id=experiment_id,
                        bmg_filename=payload["bmg_data_output_name"],
                        accurate_timestamp=workflow.steps[8].end_time,  # index 8 = bmg reading 
                        resource_id=resource_id,
                    )
                    if test_prints:
                        self.logger.log_info(f"\twriting data to csv: {payload['bmg_data_output_name']}, with timestamp {workflow.steps[8].end_time}, and respource id {resource_id}", flush=True)
                else:
                    if test_prints:
                        self.logger.log_info(f"\twriting data to csv: {payload['bmg_data_output_name']}", flush=True)

                # --- 3. TRANSFER OLD PLATE INTO THE OT-2 ---  # WORKS!
                # Run the workflow: bmg_to_ot2_wf.yaml
                if run_robots:
                        workflow = self.workcell_client.submit_workflow(
                            bmg_to_ot2_wf.resolve(),
                            json_inputs={
                                "ot2_location": payload["ot2_location"],
                            },
                        )

                self.logger.log_info(f"\nExchange is UNLOCKED by {self.experiment_settings['experiment_number']}", flush=True)


        finally:
            # Always clean up the waiting process count.
            if not self.acquired:
                redis.decr(exchange_waiters_key)

        # Polite jitter to aid scheduling fairness
        self.jitter()


        # # ---<<< OUTER LOOP START >>>---
        # Reload the experiment settings (before loop).
        self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)

        # Start the outer loop.
        while current_outer_loop < self.experiment_settings["total_outer_loops"]:

            # Reset the inner loop counter.
            current_inner_loop = 0

            # Reload experiment settings (inside loop) and reset variables.
            self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)
            if test_prints:
                self.logger.log_info(f"\nOUTER LOOP INDEX: {current_outer_loop} -------------------", flush=True)
                self.logger.log_info(f"{self.experiment_settings}", flush=True)
            plate_num += 1
            reading_in_plate_num = 0
            payload["lid_location"] = self.experiment_settings["new_lid_location"]
            payload["ot2_location"] = self.experiment_settings["new_ot2_plate_location"]
            payload["incubation_seconds"] = self.experiment_settings["incubation_seconds_between_readings"]

            # ResourceHandler: Populate current stack with a new assay plate.
            if run_resources:
                new_plate, old_plate = self._push_new_assay_plate_resource(
                    plate_num=plate_num,
                    location_name=payload["sciclops_stack_new_plates"],
                    experiment_id=experiment_id,
                    experiment_label=payload['experiment_label'],
                    experiment_number=payload["experiment_number"]
                )
                assay_plate_list[plate_num] = new_plate.resource_id, new_plate.resource_name
                # Log error if old plate is found, there should be no old plate returned here.
                if old_plate:
                    self.logger.log_warning(f"An old plate was returned from push_new_assay_plate_resource(): {old_plate.resource_id}.")


            # Lock exchange lock for steps 4 and 5.
            # Increase waiting processes count in redis before trying to acquire the lock
            self.acquired = False
            redis.incr(exchange_waiters_key)

            # TESTING:
            self.logger.log_info(f"{payload['experiment_number']} is waiting for the exchange lock.", flush=True)
            waiters = int(redis.get(exchange_waiters_key) or 0)
            self.logger.log_info(f"{waiters=}", flush=True)

            try:
                with self.exchange_lock:
                    self.logger.log_info(f"\nExchange is LOCKED by {self.experiment_settings['experiment_number']}", flush=True)

                    # Decrease waiting process count after lock is acquired.
                    self.acquired = True
                    redis.decr(exchange_waiters_key)

                    # --- 4. GET NEW ASSAY PLATE, TAKE CONTAM READING, MOVE TO NEW OT-2 LOCATION. ---  # WORKS!
                    # Set variables.
                    timestamp_now = int(datetime.now().timestamp())
                    payload["bmg_data_output_name"] = (
                        f"{payload['experiment_label']}_{timestamp_now}_{experiment_id}_{payload['experiment_number']}_{plate_num}_contam.txt"
                    )
                    if test_prints:
                        self.logger.log_info(f"getting new plate from {payload['sciclops_stack_new_plates']}", flush=True)

                    # Run the workflow: get_new_plate_and_run_bmg_wf.yaml
                    if run_robots:
                        workflow = self.workcell_client.submit_workflow(
                            get_new_plate_and_run_bmg_wf.resolve(),
                            json_inputs={
                                "bmg_data_file_name": payload["bmg_data_output_name"],
                                "data_output_directory_path": bmg_data_output_directory,
                                "lid_location": payload["lid_location"],
                                "sciclops_stack_new_plates": payload["sciclops_stack_new_plates"]

                            },
                        )
                        # Collect associated resource ID.
                        resource_datapoint_id = workflow.get_datapoint(step_key="bmg_data", label="json_result").datapoint_id
                        resource_id = self.data_client.get_datapoint_value(datapoint_id=resource_datapoint_id)
                        
                        # Write UTC BMG timestamp to CSV data file
                        helper_functions.write_timestamps_to_csv(
                            csv_directory_path=csv_data_directory,
                            experiment_id=experiment_id,
                            bmg_filename=payload["bmg_data_output_name"],
                            accurate_timestamp=workflow.steps[7].end_time, # index 7 = bmg reading
                            resource_id=resource_id,
                        )
                        if test_prints:
                            self.logger.log_info(f"\twriting data to csv: {payload['bmg_data_output_name']}, with timestamp {workflow.steps[7].end_time}", flush=True)
                    else:
                        if test_prints:
                            self.logger.log_info(f"\twriting data to csv: {payload['bmg_data_output_name']}", flush=True)

                    # --- 5. TRANSFER NEW PLATE FROM THE BMG TO NEW OT-2 LOCATION  # WORKS!
                    # Run the workflow: bmg_to_ot2_wf.yaml
                    if run_robots:
                        workflow = self.workcell_client.submit_workflow(
                            bmg_to_ot2_wf.resolve(),
                            json_inputs={
                                "ot2_location": payload["ot2_location"],
                            },
                        )

                    self.logger.log_info(f"\nExchange is UNLOCKED by {self.experiment_settings['experiment_number']}", flush=True)

            finally:
                # Always clean up the waiting process count.
                if not self.acquired:
                    redis.decr(exchange_waiters_key)

            # Polite jitter to aid scheduling fairness
            self.jitter()

            # --- 6. RUN INOCULATION OT-2 PROTOCOL --- (no exchage lock needed)
            # Reload experiment settings and set variables.
            self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)
            payload["ot2_node"] = self.experiment_settings["ot2_node"]
            payload["ot2_location"] = self.experiment_settings["new_ot2_plate_location"]
            payload["inoculation_volume"] = self.experiment_settings["inoculation_volume"]

            # Generate OT-2 protocol.
            # TODO: Do I want to keep the experiment locked for the whole OT-2 execution?
            ot2_replacement_variables = helper_functions.collect_ot2_replacement_variables(payload)
            temp_ot2_file_str = helper_functions.generate_ot2_protocol(inoculate_protocol, ot2_replacement_variables)
            payload["current_ot2_protocol"] = temp_ot2_file_str
            if test_prints:
                self.logger.log_info(f"running ot2 inoculation with tip box @ deck {payload['tip_box_location']}", flush=True)

            # Run the workflow: run_ot2_wf.yaml
            if run_robots:
                workflow = self.workcell_client.submit_workflow(
                    run_ot2_wf.resolve(),
                    file_inputs={
                        "ot2_protocol": payload["current_ot2_protocol"],
                    },
                    json_inputs={
                        "ot2_node": payload["ot2_node"]
                    }
                )

            # Modify variables.
            tip_box_location += 1
            if tip_box_location == 12:  # reset if necessary
                tip_box_location = 4
            payload["tip_box_location"] = tip_box_location

            # Lock exchange lock for steps 7 and 8.
            # Increase waiting processes count in redis before trying to acquire the lock
            self.acquired = False
            redis.incr(exchange_waiters_key)

            # TESTING:
            self.logger.log_info(f"{payload['experiment_number']} is waiting for the exchange lock.", flush=True)
            waiters = int(redis.get(exchange_waiters_key) or 0)
            self.logger.log_info(f"{waiters=}", flush=True)

            try:
                with self.exchange_lock:
                    self.logger.log_info(f"\nExchange is LOCKED by {self.experiment_settings['experiment_number']}", flush=True)

                    # Decrease waiting process count after lock is acquired.
                    self.acquired = True
                    redis.decr(exchange_waiters_key)

                    # --- 7. TRANSFER NEW PLATE INTO BMG AND TAKE T0 READING ---
                    # Set variables.
                    timestamp_now = int(datetime.now().timestamp())
                    payload["bmg_data_output_name"] = (
                        f"{payload['experiment_label']}_{timestamp_now}_{experiment_id}_{payload['experiment_number']}_{plate_num}_{reading_in_plate_num}.txt"
                    )

                    # Run the workflow: ot2_to_run_bmg_wf.yaml
                    if run_robots:
                        workflow = self.workcell_client.submit_workflow(
                            ot2_to_run_bmg_wf.resolve(),
                            json_inputs={
                                "bmg_data_file_name": payload["bmg_data_output_name"],
                                "data_output_directory_path": bmg_data_output_directory,
                                "ot2_location": payload["ot2_location"],
                            },
                        )
                        # Collect associated resource ID.
                        resource_datapoint_id = workflow.get_datapoint(step_key="bmg_data", label="json_result").datapoint_id
                        resource_id = self.data_client.get_datapoint_value(datapoint_id=resource_datapoint_id)

                        # Write UTC BMG timestamp to CSV data file.
                        helper_functions.write_timestamps_to_csv(
                            csv_directory_path=csv_data_directory,
                            experiment_id=experiment_id,
                            bmg_filename=payload["bmg_data_output_name"],
                            accurate_timestamp=workflow.steps[4].end_time,  # index 4 = bmg reading
                            resource_id=resource_id,
                        )
                        if test_prints:
                            self.logger.log_info(f"\twriting data to csv: {payload['bmg_data_output_name']}, with timestamp {workflow.steps[4].end_time}, and resource id {resource_id}", flush=True)
                    else:
                        if test_prints:
                            self.logger.log_info(f"\twriting data to csv: {payload['bmg_data_output_name']}", flush=True)


                    # --- 8. TRANSFER FROM BMG TO INCUBATOR AND INCUBATE ---
                    # Reload experiment settings and modify variables.
                    self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)
                    payload["incubation_seconds"] = self.experiment_settings["incubation_seconds_between_readings"]
                    reading_in_plate_num += 1

                    # Run the workflow: bmg_to_run_incubator_wf.yaml
                    if run_robots:
                        workflow = self.workcell_client.submit_workflow(
                            bmg_to_run_incubator_wf.resolve(),
                            json_inputs={
                                "lid_location": payload["lid_location"],
                                "incubator_location": payload["incubator_location"],
                                "incubation_seconds": payload["incubation_seconds"],
                                "incubator_node": payload["incubator_node"]
                            },
                        )

                    # Capture incubation start time.
                    incubation_start_time = time.time()

                    self.logger.log_info(f"\nExchange is UNLOCKED by {self.experiment_settings['experiment_number']}", flush=True)

            finally:
                # Always clean up the waiting process count.
                if not self.acquired:
                    redis.decr(exchange_waiters_key)

            # Polite jitter to aid scheduling fairness
            self.jitter()

            # --- 9. GET RID OF THE OLD SUBSTRATE PLATE ---
            # Reload experiment settings and modify variables.
            self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)
            payload["lid_location"] = self.experiment_settings["old_lid_location"]
            payload["ot2_location"] = self.experiment_settings["old_ot2_plate_location"]

            # Run the workflow: remove_old_substrate_plate_wf.yaml
            if run_robots:

                # Increase waiting processes count in redis before trying to acquire the lock
                self.acquired = False
                redis.incr(exchange_waiters_key)

                # TESTING:
                self.logger.log_info(f"{payload['experiment_number']} is waiting for the exchange lock.", flush=True)
                waiters = int(redis.get(exchange_waiters_key) or 0)
                self.logger.log_info(f"{waiters=}", flush=True)

                try:
                    with self.exchange_lock:
                        # Exchange lock is LOCKED.
                        self.logger.log_info(f"\nExchange is LOCKED by {self.experiment_settings['experiment_number']}", flush=True)

                        # Decrease waiting process count after lock is acquired.
                        self.acquired = True
                        redis.decr(exchange_waiters_key)

                        workflow = self.workcell_client.submit_workflow(
                            remove_old_substrate_plate_wf.resolve(),
                            json_inputs={
                                "lid_location": payload["lid_location"],
                                "ot2_location": payload["ot2_location"],
                                "sciclops_stack_old_plates": payload["sciclops_stack_old_plates"]
                            },
                        )
                        # Exchange lock is UNLOCKED.
                        self.logger.log_info(f"\nExchange is UNLOCKED by {self.experiment_settings['experiment_number']}", flush=True)

                finally:
                    # Always clean up the waiting process count.
                    if not self.acquired:
                        redis.decr(exchange_waiters_key)

                # Polite jitter to aid scheduling fairness
                self.jitter()

            # --- FINISH INCUBATION ---
            time_now = time.time()
            incubation_seconds_reminaing = int(payload["incubation_seconds"] - (time_now - incubation_start_time))
            helper_functions.wait_for_incubation(incubation_seconds_reminaing)

            # ---<<< INNER LOOP START >>>---
            # Reload experiment settings (outside loop).
            self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)

            # Start inner loop.
            while current_inner_loop < self.experiment_settings["total_inner_loops"]:

                # Reset variables
                self.waiter_counted = False

                # Reload experiment settings (inside loop)
                self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)
                payload["incubation_seconds"] = self.experiment_settings["incubation_seconds_between_readings"]
                if test_prints:
                    self.logger.log_info(f"\ninner loop index = {current_inner_loop}", flush=True)
                    self.logger.log_info(f"running incubator to bmg, taking T{current_inner_loop+1} reading", flush=True)

                # Lock exchange lock for steps 10 and 11 (or 12.)
                # Increase waiting processes count in redis before trying to acquire the lock
                self.acquired = False
                redis.incr(exchange_waiters_key)
                self.waiter_counted = True

                # TESTING:
                self.logger.log_info(f"{payload['experiment_number']} is waiting for the exchange lock.", flush=True)
                waiters = int(redis.get(exchange_waiters_key) or 0)
                self.logger.log_info(f"{waiters=}", flush=True)

                try:
                    # Acquire the exchange lock.
                    got_lock = self.exchange_lock.acquire()

                    # Catch aquire lock timeout case and cleanup variables.
                    if not got_lock:
                        redis.decr(exchange_waiters_key)
                        self.waiter_counted = False
                        raise RuntimeError("Failed to aquire the exchange lock most likely due to a timeout.")
                        # Note: The finally block will still execute.

                    self.acquired = True
                    self.logger.log_info(f"\nExchange is LOCKED by {self.experiment_settings['experiment_number']}", flush=True)

                    # --- 10. INCUBATOR TO RUN BMG ---
                    # Set variables.
                    timestamp_now = int(datetime.now().timestamp())
                    payload["bmg_data_output_name"] = (
                        f"{payload['experiment_label']}_{timestamp_now}_{experiment_id}_{payload['experiment_number']}_{plate_num}_{reading_in_plate_num}.txt"
                    )

                    # Run the workflow: incubator_to_run_bmg_wf.yaml
                    if run_robots:
                        workflow = self.workcell_client.submit_workflow(
                            incubator_to_run_bmg_wf.resolve(),
                            json_inputs={
                                "incubator_location": payload["incubator_location"],
                                "incubation_seconds": payload["incubation_seconds"],
                                "incubator_node": payload["incubator_node"],
                                "lid_location": payload["lid_location"],
                                "bmg_data_output_name": payload["bmg_data_output_name"],
                                "data_output_directory_path": bmg_data_output_directory,
                            },
                        )
                        # Collect associated resource ID.
                        resource_datapoint_id = workflow.get_datapoint(step_key="bmg_data", label="json_result").datapoint_id
                        resource_id = self.data_client.get_datapoint_value(datapoint_id=resource_datapoint_id)

                        # Write UTC BMG timestamp to CSV data file.
                        helper_functions.write_timestamps_to_csv(
                            csv_directory_path=csv_data_directory,
                            experiment_id=experiment_id,
                            bmg_filename=payload["bmg_data_output_name"],
                            accurate_timestamp=workflow.steps[8].end_time,  # index 8 = bmg reading
                            resource_id=resource_id,
                        )
                        if test_prints:
                            self.logger.log_info(f"\twriting data to csv: {payload['bmg_data_output_name']}, with timestamp {workflow.steps[8].end_time}, and resource id {resource_id}", flush=True)
                    else:
                        if test_prints:
                            self.logger.log_info(f"\twriting data to csv: {payload['bmg_data_output_name']}", flush=True)

                    # Modify variables.
                    reading_in_plate_num += 1

                    # If it is NOT the last inner loop...
                    if current_inner_loop < (self.experiment_settings["total_inner_loops"]-1):

                        # --- 11. TRANSFER FROM BMG TO INCUBATOR, INCUBATE ---
                        # Reload experiment settings and update incubation seconds.
                        self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)
                        payload["incubation_seconds"] = self.experiment_settings["incubation_seconds_between_readings"]
                        if test_prints:
                            self.logger.log_info("running bmg to incubator", flush=True)

                        # Run the workflow: bmg_to_run_incubator_wf.yaml
                        if run_robots:
                            workflow = self.workcell_client.submit_workflow(
                                bmg_to_run_incubator_wf.resolve(),
                                json_inputs={
                                    "lid_location": payload["lid_location"],
                                    "incubator_location": payload["incubator_location"],
                                    "incubation_seconds": payload["incubation_seconds"],
                                    "incubator_node": payload["incubator_node"]
                                },
                            )

                        # Capture incubation start time.
                        incubation_start_time = time.time()

                        # Release the lock for incubation.
                        self.exchange_lock.release()
                        self.acquired = False
                        self.logger.log_info(f"\nExchange UNLOCKED by {self.experiment_settings['experiment_number']} for incubation", flush=True)

                        # Decrement waiters because no process is holding the lock anymore.
                        if self.waiter_counted:
                            redis.decr(exchange_waiters_key)
                            self.waiter_counted = False

                        # TESTING
                        waiters = int(redis.get(exchange_waiters_key) or 0)
                        self.logger.log_info(f"waiters count {waiters} --> should be 0.", flush=True)

                        # Sleep for incubation.
                        helper_functions.wait_for_incubation(payload["incubation_seconds"])

                    # If it IS the last inner loop:
                    else:

                        # --- 12. TRANSFER FROM BMG TO OT2 OLD LOCATION ---
                        # Note: The plate will start in the open BMG nest.
                        if test_prints:
                            self.logger.log_info("running bmg to ot2", flush=True)

                        # Run the workflow: bmg_to_ot2_wf.yaml
                        if run_robots:
                            workflow = self.workcell_client.submit_workflow(
                                bmg_to_ot2_wf.resolve(),
                                json_inputs={
                                    "ot2_location": payload["ot2_location"],
                                },
                            )

                        # Release the exchange lock once workflow is completed.
                        self.exchange_lock.release()
                        self.acquired = False
                        self.logger.log_info(f"\nExchange is UNLOCKED by {self.experiment_settings['experiment_number']}", flush=True)

                        # Decrement waiters because no process is holding the lock anymore
                        if self.waiter_counted:
                            redis.decr(exchange_waiters_key)
                            self.waiter_counted = False

                        # TESTING
                        waiters = int(redis.get(exchange_waiters_key) or 0)
                        self.logger.log_info(f"waiters count {waiters} --> should be 0.", flush=True)

                finally:
                    # If lock was aquired but never released...
                    if self.acquired:
                        self.exchange_lock.release()
                        self.acquired = False

                    # If the waiter was counted but never decreased....
                    if self.waiter_counted:
                        redis.decr(exchange_waiters_key)
                        self.waiter_counted = False

                # Polite jitter to aid scheduling fairness
                self.jitter()

                current_inner_loop += 1
            # ---<<< INNER LOOP END >>>---

            current_outer_loop += 1
        # ---<<< OUTER LOOP END >>>---

        # # # # NOTE: If there are no more outer loops, the final assay plate ends in old OT-2 location.

        # Lock exchange lock for steps 13 and 14.
        # Increase waiting processes count in redis before trying to acquire the lock
        self.acquired = False
        redis.incr(exchange_waiters_key)

        # TESTING:
        self.logger.log_info(f"{payload['experiment_number']} is waiting for the exchange lock.", flush=True)
        waiters = int(redis.get(exchange_waiters_key) or 0)
        self.logger.log_info(f"{waiters=}", flush=True)

        try:
            with self.exchange_lock:

                # Exchange lock is LOCKED.
                self.logger.log_info(f"\nExchange is LOCKED by {self.experiment_settings['experiment_number']}", flush=True)

                # Decrease waiting process count after lock is acquired.
                self.acquired = True
                redis.decr(exchange_waiters_key)

                if test_prints:
                    self.logger.log_info("END OF EXPEREMENT APP: Returning old plate from ot2 to exchange then trash stack.", flush=True)

                # --- 13. MOVE PLATE FROM OLD OT-2 LOCATION TO EXCHANGE, REPLACE LID ---
                # Run the workflow: at_end_ot2_to_exchange_wf.yaml
                if run_robots:
                    workflow = self.workcell_client.submit_workflow(
                        at_end_ot2_to_exchange_wf.resolve(),
                        json_inputs={
                            "ot2_location": payload["ot2_location"],
                            "lid_location": payload["lid_location"],
                        },
                    )

                # --- 14. TRANSFER FINAL ASSAY PLATE TO TRASH STACK ---
                # Run the workflow: trash_final_plate_wf.yaml
                if run_robots:
                    workflow = self.workcell_client.submit_workflow(
                        trash_final_plate_wf.resolve(),
                        json_inputs={
                            "sciclops_stack_old_plates": payload["sciclops_stack_old_plates"]
                        },
                    )
                # Exchange lock is UNLOCKED.
                self.logger.log_info(f"\nExchange is UNLOCKED by {self.experiment_settings['experiment_number']}", flush=True)

        finally:
            # Always clean up the waiting process count.
            if not self.acquired:
                redis.decr(exchange_waiters_key)

        # Polite jitter to aid scheduling fairness
        self.jitter()

        # END OF EXPERIMENT!
        self.logger.log_info("YAY WE MADE IT!", flush=True)




if __name__ == "__main__":
    # Parse experiment settings argument.
    parser = argparse.ArgumentParser(description="Run ALE experiment")
    parser.add_argument(
        "-s", "--settings",
        type=str,
        required=True,
        help="Path to experiment settings file."
    )
    args = parser.parse_args()

    # Start the experiment run.
    ALEApp.main(
        lab_server_url="http://146.137.240.20:8000/",
        settings_file=args.settings
    )



