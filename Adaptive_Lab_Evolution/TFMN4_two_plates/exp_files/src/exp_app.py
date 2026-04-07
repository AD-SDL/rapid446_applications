import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import random

from dotenv import load_dotenv
from madsci.client import (
    ExperimentClient,
    LocationClient,
    ResourceClient,
    WorkcellClient,
)
from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.resource_types import Collection, Resource, Slot
from madsci.experiment_application import (
    ExperimentApplication,
    ExperimentApplicationConfig,
)
from pottery import Redlock
from pydantic import AnyUrl
from redis import Redis

# Add the root project folder (TFMN4 directory) to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from utils import helper_functions
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
    password=redis_password,
)

# TEST PING TO REDIS
try:
    redis.ping()
except Exception as e:
    print("Redis connection error.")
    raise e

class ALEApp(ExperimentApplication):
    """ALE Experiment Application

    # TODO:
    - collect bmg data output here and upload to globus?
    - get rid of payload to collect variables.
        - although some variables shouldn't be changeable mid-experiment...

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

    # Experiment settings file
    experiment_settings_file = None
    exeriment_settings = {}
    try_reload_config.last_mtime = None

    def __init__(self, experiment_settings_file: str) -> None:
        """Initializes the ALE Experiment App"""
        super().__init__()
        self.experiment_settings_file = experiment_settings_file
        self.exchange_lock = Redlock(
            key='exchange_nest',
            masters={redis},
            auto_release_time=exchange_auto_unlock_seconds,
            context_manager_blocking=True,
            context_manager_timeout=exchange_lock_timeout,
        )
        self.acquired = False
        self._validate_settings_path()

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
                resource_name = f"assay_plate_{experiment_label}_{experiment_number}_{experiment_id}_plate{plate_num}",
                capacity=2,
                children={
                    "lid_slot": Slot(
                        resource_name = "lid slot resource on test plate",
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
        print(f"Processes waiting for exchange lock = {waiters}")
        if waiters > 0:
            print("Using polite jitter.")
            time.sleep(random.uniform(1.0, 3.0))   # be polite

        else:
            print("Using fast jitter.")
            time.sleep(random.uniform(0.1, 0.5))   # go fast



    def run_experiment(self) -> None:
        """main experiment function"""

        # --- DEFINE PATHS AND STARTING VARIABLES ---
        run_robots = True  # if False, no robots will run
        run_resources = True
        test_prints = True  # if True, will print out extra info for testing purposes

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

        # Load experiment settings.
        self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)

        # Initial payload setup
        payload = {
            "experiment_label": self.experiment_settings["experiment_label"],
            "experiment_number": self.experiment_settings["experiment_number"],

            "lid_location": self.experiment_settings["old_lid_location"],
            "lid_safe_path": self.experiment_settings["old_safe_lid_location"],

            "ot2_node": self.experiment_settings["ot2_node"],
            "ot2_location": self.experiment_settings["old_ot2_plate_location"],
            "ot2_safe_path": self.experiment_settings["ot2_safe_path"],
            "inoculation_volume": self.experiment_settings["inoculation_volume"],
            "tip_box_location": tip_box_location,
            "current_ot2_protocol": None,
            "use_existing_resources": False,

            "incubator_node": self.experiment_settings["incubator_node"],
            "incubator_location": self.experiment_settings["incubator_location"],
            "incubator_safe_path": self.experiment_settings["incubator_safe_path"],
            "incubation_seconds": self.experiment_settings["incubation_seconds_initial"],

            "sciclops_stack_new_plates": self.experiment_settings["sciclops_stack_new_plates"],
            "sciclops_stack_old_plates": self.experiment_settings["sciclops_stack_old_plates"],

            "bmg_assay_name": "NIDHI",
        }
        if test_prints:
            print(f"{payload=}")

        # --- EXPERIMENT ACTIONS -------------------------------------------------------
        """
        Experiment setup at start:

        Location:
            exchange: inoculated microplate plate with lid
            Stack (1 or 2 depending on settings JSON): extra substrate microplates with lids
            OT-2 (ot2_spongebob or ot2_patrick depending on settings JSON) decks 4-11: 20uL tip racks
            ALL OTHER LOCATIONS: EMPTY
        """
        # self.exchange_lock = Redlock(key='exchange_nest', masters={redis}, auto_release_time=exchange_auto_unlock_seconds)

        # increase waiting processes count in redis before trying to acquired the lock
        self.acquired = False
        redis.incr(exchange_waiters_key)

        # TESTING:
        print(f"{payload['experiment_number']} is waiting for the exchange lock.")
        waiters = int(redis.get(exchange_waiters_key) or 0)
        print(f"{waiters=}")

        try:
            with self.exchange_lock:
                # Exchange lock is LOCKED for step 1 workflow.
                print(f"\nExchange is LOCKED by {self.experiment_settings['experiment_number']}")

                # Decrease waiting process count after lock is acquired.
                self.acquired = True
                redis.decr(exchange_waiters_key)

                # --- 1. TRANSFER IMMEDIATELY FROM EXCHANGE TO INCUBATOR ---
                # ResourceHandler: Push starting plate into exchange.
                if run_resources:
                    new_plate, old_plate = self._push_new_assay_plate_resource(
                        plate_num=plate_num,
                        location_name="exchange_nest_low_wide",
                        experiment_id=experiment_id,
                        experiment_label=payload["experiment_label"],
                        experiment_number=payload["experiment_number"]
                    )
                    assay_plate_list[plate_num] = new_plate.resource_id, new_plate.resource_name


                # Run the workflow: exchange_to_run_incubator_wf.yaml
                if run_robots:
                    workflow = self.workcell_client.submit_workflow(
                        exchange_to_run_incubator_wf.resolve(),
                        json_inputs={
                            "incubator_node": payload["incubator_node"],
                            "incubator_location": payload["incubator_location"],
                            "incubator_safe_path": payload["incubator_safe_path"],
                            "incubation_seconds": payload["incubation_seconds"],
                        },
                    )
                # Exchange lock is UNLOCKED.
                print(f"\nExchange is UNLOCKED by {self.experiment_settings['experiment_number']}")

        finally:
            # always clean up the waiting process count.
            if not self.acquired:
                redis.decr(exchange_waiters_key)

        # # Polite jitter to aid scheduling fairness
        self.jitter()

        # Reload experiment settings and capture incubation start time.
        self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)
        payload["incubation_seconds"] = self.experiment_settings["incubation_seconds_initial"]
        incubation_start_time = time.time()

        # Wait for incubation to finish.
        if test_prints:
            print("Running initial incubation")
        if run_robots:
            while time.time() - incubation_start_time < payload["incubation_seconds"]:
                print(
                    f"will continue in... {int(payload['incubation_seconds'] - (time.time() - incubation_start_time))} seconds"
                )
                time.sleep(5)  # 5 seconds

                if time.time() - incubation_start_time >= payload["incubation_seconds"]:
                    print("Incubation complete.")
                    break



        # LOCK exchange lock for steps 2 and 3.
        # Increase waiting processes count in redis before trying to acquire the lock
        self.acquired = False
        redis.incr(exchange_waiters_key)

        # TESTING:
        print(f"{payload['experiment_number']} is waiting for the exchange lock.")
        waiters = int(redis.get(exchange_waiters_key) or 0)
        print(f"{waiters=}")

        try:
            #self.exchange_lock = Redlock(key='exchange_nest', masters={redis}, auto_release_time=exchange_auto_unlock_seconds)
            with self.exchange_lock:
                print(f"\nExchange is LOCKED by {self.experiment_settings['experiment_number']}")

                # Decrease waiting process count after lock is acquired.
                self.acquired = True
                redis.decr(exchange_waiters_key)

                # --- 2. TRANSFER PLATE0 INTO BMG AND TAKE READING ---
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
                            "incubator_safe_path": payload["incubator_safe_path"],
                            "incubation_seconds": payload["incubation_seconds"],
                            "incubator_node": payload["incubator_node"],
                            "lid_location": payload["lid_location"],
                            "lid_safe_path": payload["lid_safe_path"],
                            "bmg_data_output_name": payload["bmg_data_output_name"],
                            "data_output_directory_path": bmg_data_output_directory,
                        },
                    )

                    # Collect associated resource id.
                    datapoint_id = workflow.get_datapoint_id(step_key="bmg_data", label="json_result")
                    resource_id = self.data_client.get_datapoint_value(datapoint_id=datapoint_id)

                    # Write UTC BMG timestamp to CSV data file.
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

                # --- 3. TRANSFER OLD PLATE INTO THE OT-2 ---
                # Run the workflow: bmg_to_ot2_wf.yaml
                if run_robots:
                        workflow = self.workcell_client.submit_workflow(
                            bmg_to_ot2_wf.resolve(),
                            json_inputs={
                                "ot2_location": payload["ot2_location"],
                                "ot2_safe_path": payload["ot2_safe_path"],
                            },
                        )

                print(f"\nExchange is UNLOCKED by {self.experiment_settings['experiment_number']}")


        finally:
            # always clean up the waiting process count.
            if not self.acquired:
                redis.decr(exchange_waiters_key)

        # Polite jitter to aid scheduling fairness
        self.jitter()


        # ---<<< OUTER LOOP START >>>---
        # Reload the experiment settings (before loop).
        self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)

        # Start the outer loop.
        while current_outer_loop < self.experiment_settings["total_outer_loops"]:

            # Reload experiment settings (inside loop) and reset variables.
            self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)
            if test_prints:
                print(f"\nOUTER LOOP INDEX: {current_outer_loop} -------------------")
                print(f"{self.experiment_settings}")
            plate_num += 1
            reading_in_plate_num = 0
            payload["lid_location"] = self.experiment_settings["new_lid_location"]
            payload["lid_safe_path"] = self.experiment_settings["new_safe_lid_location"]
            payload["ot2_location"] = self.experiment_settings["new_ot2_plate_location"]
            payload["ot2_safe_path"] = self.experiment_settings["ot2_safe_path"]
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
            print(f"{payload['experiment_number']} is waiting for the exchange lock.")
            waiters = int(redis.get(exchange_waiters_key) or 0)
            print(f"{waiters=}")

            try:
                #self.exchange_lock = Redlock(key='exchange_nest', masters={redis}, auto_release_time=exchange_auto_unlock_seconds)
                with self.exchange_lock:
                    print(f"\nExchange is LOCKED by {self.experiment_settings['experiment_number']}")

                    # Decrease waiting process count after lock is acquired.
                    self.acquired = True
                    redis.decr(exchange_waiters_key)

                    # --- 4. GET NEW ASSAY PLATE, TAKE CONTAM READING, MOVE TO NEW OT-2 LOCATION. ---
                    # Set variables.
                    timestamp_now = int(datetime.now().timestamp())
                    payload["bmg_data_output_name"] = (
                        f"{payload['experiment_label']}_{timestamp_now}_{experiment_id}_{payload['experiment_number']}_{plate_num}_contam.txt"
                    )
                    if test_prints:
                        print(f"getting new plate from {payload['sciclops_stack_new_plates']}")

                    # Run the workflow: get_new_plate_and_run_bmg_wf.yaml
                    if run_robots:
                        workflow = self.workcell_client.submit_workflow(
                            get_new_plate_and_run_bmg_wf.resolve(),
                            json_inputs={
                                "bmg_data_file_name": payload["bmg_data_output_name"],
                                "data_output_directory_path": bmg_data_output_directory,
                                "lid_location": payload["lid_location"],
                                "lid_safe_path": payload["lid_safe_path"],
                                "sciclops_stack_new_plates": payload["sciclops_stack_new_plates"]

                            },
                        )

                        # Collect associated resource id.
                        datapoint_id = workflow.get_datapoint_id(step_key="bmg_data", label="json_result")
                        resource_id = self.data_client.get_datapoint_value(datapoint_id=datapoint_id)

                        # Write UTC BMG timestamp to CSV data file
                        helper_functions.write_timestamps_to_csv(
                            csv_directory_path=csv_data_directory,
                            experiment_id=experiment_id,
                            bmg_filename=payload["bmg_data_output_name"],
                            accurate_timestamp=workflow.steps[6].end_time, # index 6 = bmg reading
                            resource_id=resource_id,
                        )
                        if test_prints:
                            print(f"\twriting data to csv: {payload['bmg_data_output_name']}, with timestamp {workflow.steps[5].end_time}")
                    else:
                        if test_prints:
                            print(f"\twriting data to csv: {payload['bmg_data_output_name']}")

                    # --- 5. TRANSFER NEW PLATE FROM THE BMG TO NEW OT-2 LOCATION
                    # Run the workflow: bmg_to_ot2_wf.yaml
                    if run_robots:
                        workflow = self.workcell_client.submit_workflow(
                            bmg_to_ot2_wf.resolve(),
                            json_inputs={
                                "ot2_location": payload["ot2_location"],
                                "ot2_safe_path": payload["ot2_safe_path"],
                            },
                        )

                    print(f"\nExchange is UNLOCKED by {self.experiment_settings['experiment_number']}")

            finally:
                # always clean up the waiting process count.
                if not self.acquired:
                    redis.decr(exchange_waiters_key)

            # Polite jitter to aid scheduling fairness
            self.jitter()


            # --- 6. RUN INOCULATION OT-2 PROTOCOL --- (no exchage lock needed)
            # Reload experiment settings and set variables.
            self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)
            payload["ot2_node"] = self.experiment_settings["ot2_node"]
            payload["ot2_location"] = self.experiment_settings["new_ot2_plate_location"]
            payload["ot2_safe_path"] = self.experiment_settings["ot2_safe_path"]
            payload["inoculation_volume"] = self.experiment_settings["inoculation_volume"]

            # Generate OT-2 protocol.
            ot2_replacement_variables = helper_functions.collect_ot2_replacement_variables(payload)
            temp_ot2_file_str = helper_functions.generate_ot2_protocol(inoculate_protocol, ot2_replacement_variables)
            payload["current_ot2_protocol"] = temp_ot2_file_str
            if test_prints:
                print(f"running ot2 inoculation with tip box @ deck {payload['tip_box_location']}")

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
            #self.exchange_lock = Redlock(key='exchange_nest', masters={redis}, auto_release_time=exchange_auto_unlock_seconds)

            # Increase waiting processes count in redis before trying to acquire the lock
            self.acquired = False
            redis.incr(exchange_waiters_key)

            # TESTING:
            print(f"{payload['experiment_number']} is waiting for the exchange lock.")
            waiters = int(redis.get(exchange_waiters_key) or 0)
            print(f"{waiters=}")

            try:
                with self.exchange_lock:
                    print(f"\nExchange is LOCKED by {self.experiment_settings['experiment_number']}")

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
                                "ot2_safe_path": payload["ot2_safe_path"]
                            },
                        )

                        # Collect associated resource ID.
                        datapoint_id = workflow.get_datapoint_id(step_key="bmg_data", label="json_result")
                        resource_id = self.data_client.get_datapoint_value(datapoint_id=datapoint_id)

                        # Write UTC BMG timestamp to CSV data file.
                        helper_functions.write_timestamps_to_csv(
                            csv_directory_path=csv_data_directory,
                            experiment_id=experiment_id,
                            bmg_filename=payload["bmg_data_output_name"],
                            accurate_timestamp=workflow.steps[4].end_time,  # index 4 = bmg reading
                            resource_id=resource_id,
                        )
                        if test_prints:
                            print(f"\twriting data to csv: {payload['bmg_data_output_name']}, with timestamp {workflow.steps[4].end_time}, and resource id {resource_id}")
                    else:
                        if test_prints:
                            print(f"\twriting data to csv: {payload['bmg_data_output_name']}")



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
                                "lid_safe_path": payload["lid_safe_path"],
                                "incubator_location": payload["incubator_location"],
                                "incubator_safe_path": payload["incubator_safe_path"],
                                "incubation_seconds": payload["incubation_seconds"],
                                "incubator_node": payload["incubator_node"]
                            },
                        )

                    # Capture incubation start time.
                    incubation_start_time = time.time()

                    print(f"\nExchange is UNLOCKED by {self.experiment_settings['experiment_number']}")

            finally:
                # always clean up the waiting process count.
                if not self.acquired:
                    redis.decr(exchange_waiters_key)

            # Polite jitter to aid scheduling fairness
            self.jitter()

            # --- 9. GET RID OF THE OLD SUBSTRATE PLATE ---
            # Reload experiment settings and modify variables.
            self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)
            payload["lid_location"] = self.experiment_settings["old_lid_location"]
            payload["lid_safe_path"] = self.experiment_settings["old_safe_lid_location"]
            payload["ot2_location"] = self.experiment_settings["old_ot2_plate_location"]

            # Run the workflow: remove_old_substrate_plate_wf.yaml
            if run_robots:
                #self.exchange_lock = Redlock(key='exchange_nest', masters={redis}, auto_release_time=exchange_auto_unlock_seconds)

                # Increase waiting processes count in redis before trying to acquire the lock
                self.acquired = False
                redis.incr(exchange_waiters_key)

                # TESTING:
                print(f"{payload['experiment_number']} is waiting for the exchange lock.")
                waiters = int(redis.get(exchange_waiters_key) or 0)
                print(f"{waiters=}")

                try:
                    with self.exchange_lock:
                        # Exchange lock is LOCKED.
                        print(f"\nExchange is LOCKED by {self.experiment_settings['experiment_number']}")

                        # Decrease waiting process count after lock is acquired.
                        self.acquired = True
                        redis.decr(exchange_waiters_key)

                        workflow = self.workcell_client.submit_workflow(
                            remove_old_substrate_plate_wf.resolve(),
                            json_inputs={
                                "lid_location": payload["lid_location"],
                                "lid_safe_path": payload["lid_safe_path"],
                                "ot2_location": payload["ot2_location"],
                                "ot2_safe_path": payload["ot2_safe_path"],
                                "sciclops_stack_old_plates": payload["sciclops_stack_old_plates"]
                            },
                        )
                        # Exchange lock is UNLOCKED.
                        print(f"\nExchange is UNLOCKED by {self.experiment_settings['experiment_number']}")

                finally:
                    # always clean up the waiting process count.
                    if not self.acquired:
                        redis.decr(exchange_waiters_key)

                # Polite jitter to aid scheduling fairness
                self.jitter()

            # --- FINISH INCUBATION ---
            # Wait for incubation to finish.
            if test_prints:
                print("running incubation")
            if run_robots:
                while (time.time() - incubation_start_time) < payload["incubation_seconds"]:
                    print(f"will continue in... {int(payload['incubation_seconds']-(time.time() - incubation_start_time))} seconds")
                    time.sleep(5) # 5 seconds


            # ---<<< INNER LOOP START >>>---
            # Reload experiment settings (outside loop).
            self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)

            # Start inner loop.
            while current_inner_loop < self.experiment_settings["total_inner_loops"]:

                # Reload experiment settings (inside loop)
                self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)
                payload["incubation_seconds"] = self.experiment_settings["incubation_seconds_between_readings"]
                if test_prints:
                    print(f"\ninner loop index = {current_inner_loop}")
                    print(f"running incubator to bmg, taking T{current_inner_loop+1} reading")

                # Lock exchange lock for steps 10 and 11 (or 12.)
                #self.exchange_lock = Redlock(key='exchange_nest', masters={redis}, auto_release_time=exchange_auto_unlock_seconds)

                # Increase waiting processes count in redis before trying to acquire the lock
                self.acquired = False
                redis.incr(exchange_waiters_key)

                # TESTING:
                print(f"{payload['experiment_number']} is waiting for the exchange lock.")
                waiters = int(redis.get(exchange_waiters_key) or 0)
                print(f"{waiters=}")

                try:
                    # acquire the lock:
                    # --> Cannot use with self.exchange_lock here since we need to release optionally for incubation.
                    self.exchange_lock.acquire()
                    self.acquired = True
                    redis.decr(exchange_waiters_key)
                    print(f"\nExchange is LOCKED by {self.experiment_settings['experiment_number']}")

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
                                "incubator_safe_path": payload["incubator_safe_path"],
                                "incubation_seconds": payload["incubation_seconds"],
                                "incubator_node": payload["incubator_node"],
                                "lid_location": payload["lid_location"],
                                "lid_safe_path": payload["lid_safe_path"],
                                "bmg_data_output_name": payload["bmg_data_output_name"],
                                "data_output_directory_path": bmg_data_output_directory,
                            },
                        )

                        # Collect associated resource ID.
                        datapoint_id = workflow.get_datapoint_id(step_key="bmg_data", label="json_result")
                        resource_id = self.data_client.get_datapoint_value(datapoint_id=datapoint_id)

                        # Write UTC BMG timestamp to CSV data file.
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

                    # Modify variables.
                    reading_in_plate_num += 1

                    # If NOT the last loop...
                    if current_inner_loop < (self.experiment_settings["total_inner_loops"]-1):

                        # --- 11. TRANSFER FROM BMG TO INCUBATOR, INCUBATE ---
                        # Reload experiment settings and update incubation seconds.
                        self.experiment_settings = try_reload_config(config_file=self.experiment_settings_file)
                        payload["incubation_seconds"] = self.experiment_settings["incubation_seconds_between_readings"]
                        if test_prints:
                            print("running bmg to incubator")

                        # Run the workflow: bmg_to_run_incubator_wf.yaml
                        if run_robots:
                            workflow = self.workcell_client.submit_workflow(
                                bmg_to_run_incubator_wf.resolve(),
                                json_inputs={
                                    "lid_location": payload["lid_location"],
                                    "lid_safe_path": payload["lid_safe_path"],
                                    "incubator_location": payload["incubator_location"],
                                    "incubator_safe_path": payload["incubator_safe_path"],
                                    "incubation_seconds": payload["incubation_seconds"],
                                    "incubator_node": payload["incubator_node"]
                                },
                            )

                        # Capture incubation start time.
                        incubation_start_time = time.time()

                        # Release the lock for incubation
                        self.exchange_lock.release()
                        self.acquired = False
                        print(f"\nExchange UNLOCKED by {self.experiment_settings['experiment_number']} for incubation")


                        # decrease process count waiting for exchange lock
                        # allows other processes to quickly acquire exchange lock
                        redis.decr(exchange_waiters_key)
                        # TESTING
                        waiters = int(redis.get(exchange_waiters_key) or 0)
                        print(f"waiters count {waiters} --> should be 0.")

                        # Sleep for incubation.
                        if test_prints:
                            print("running 1 hour incubaton")
                        if run_robots:
                            while time.time() - incubation_start_time < payload["incubation_seconds"]:
                                print(f"will continue in... {int(payload['incubation_seconds']-(time.time() - incubation_start_time))} seconds")
                                time.sleep(5) # 5 seconds

                    # If last loop...
                    else:

                        # --- 12. TRANSFER FROM BMG TO OT2 OLD LOCATION ---
                        # Note: The plate will start in the open BMG nest.
                        if test_prints:
                            print("running bmg to ot2")

                        # Run the workflow: bmg_to_ot2_wf.yaml
                        if run_robots:
                            workflow = self.workcell_client.submit_workflow(
                                bmg_to_ot2_wf.resolve(),
                                json_inputs={
                                    "ot2_location": payload["ot2_location"],
                                    "ot2_safe_path": payload["ot2_safe_path"],
                                },
                            )

                        self.exchange_lock.release()
                        self.acquired = False
                        print(f"\nExchange is UNLOCKED by {self.experiment_settings['experiment_number']}")
                        redis.decr(exchange_waiters_key)  # decrease count of processes waiting for exchange lock.

                        # TESTING
                        waiters = int(redis.get(exchange_waiters_key) or 0)
                        print(f"waiters count {waiters} --> should be 0.")

                finally:
                    # if the lock was not unlocked properly by the if or else statement...
                    if self.acquired:
                        self.exchange_lock.release()
                        redis.decr(exchange_waiters_key)
                        self.acquired = False



                # Polite jitter to aid scheduling fairness
                self.jitter()

                current_inner_loop += 1
            # ---<<< INNER LOOP END >>>---

            current_outer_loop += 1
        # ---<<< OUTER LOOP END >>>---

        # # # NOTE: If there are no more outer loops, the final assay plate ends in old OT-2 location.

        # Lock exchange lock for steps 13 and 14.
        # self.exchange_lock = Redlock(key='exchange_nest', masters={redis}, auto_release_time=exchange_auto_unlock_seconds)

                        # Increase waiting processes count in redis before trying to acquire the lock
        self.acquired = False
        redis.incr(exchange_waiters_key)

        # TESTING:
        print(f"{payload['experiment_number']} is waiting for the exchange lock.")
        waiters = int(redis.get(exchange_waiters_key) or 0)
        print(f"{waiters=}")

        try:
            with self.exchange_lock:

                # Exchange lock is LOCKED.
                print(f"\nExchange is LOCKED by {self.experiment_settings['experiment_number']}")

                # Decrease waiting process count after lock is acquired.
                self.acquired = True
                redis.decr(exchange_waiters_key)

                if test_prints:
                    print("END OF EXPEREMENT APP: Returning old plate from ot2 to exchange then trash stack.")

                # --- 13. MOVE PLATE FROM OLD OT-2 LOCATION TO EXCHANGE, REPLACE LID ---
                # Run the workflow: at_end_ot2_to_exchange_wf.yaml
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
                print(f"\nExchange is UNLOCKED by {self.experiment_settings['experiment_number']}")

        finally:
            # always clean up the waiting process count.
            if not self.acquired:
                redis.decr(exchange_waiters_key)

        # Polite jitter to aid scheduling fairness
        self.jitter()

        # END OF EXPERIMENT!
        print("YAY WE MADE IT!")



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
    exp_app = ALEApp(experiment_settings_file=args.settings)
    current_time = datetime.now()
    with exp_app.manage_experiment(
        run_name = f"ALE_{current_time.strftime('%Y%m%d_%H%M%S')}",
        run_description = "Adaptive Lab Evolution Experiment Run",
    ):
        exp_app.start_app()



