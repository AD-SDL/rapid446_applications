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
from madsci.client.resource_client import ResourceClient
from pottery import Redlock

from redis import Redis
from pydantic import AnyUrl

from REST_connection.REST_connect import RESTHandlerPD
import helper_functions


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








class PDApp(ExperimentScript,): # TODO
    """PD Experiment Application

    # TODO:

    """

    experiment_design = ExperimentDesign(
        experiment_name="PD_App",
    )
    # config = ExperimentApplicationConfig(node_url=AnyUrl("http://localhost:6000"))
    # experiment_client = ExperimentClient()
    # workcell_client = WorkcellClient()
    # location_client = LocationClient()
    # resource_client = ResourceClient()
    experiment_id = None
    experiment_label = None
    rest_handler = RESTHandlerPD()

    # def _validate_settings_path(self):
    #     if not os.path.isfile(self.experiment_settings_file):
    #         raise FileNotFoundError(
    #             f"Settings file not found: {self.experiment_settings_file}"
    #         )

    # def __init__(self) -> None:
    #     """Initializes the PD Experiment App"""

    #     super().__init__()
    #     self.init_assay_plate_resource_template()

    # def init_assay_plate_resource_template(self):
    #     """Initializes assay plate resource template"""

    #     self.resource_client.create_template(
    #         resource=Resource(
    #             resource_description="NEST PCR plate 200ul",
    #         ),
    #         template_name="opentrons_96_wellplate_200ul_pcr_full_skirt",
    #         description="Template for 200ul PCR plate",
    #         tags=["Plate", "ANSI/SLAS", "96 Well", "PCR", "Labware"],
    #     )

    #     self.resource_client.create_template(
    #         resource=Resource(
    #             resource_description="ot2 20ul tiprack",
    #         ),
    #         template_name="opentrons_96_filtertiprack_20ul",
    #         description="Template for ot2 20ul tiprack",
    #         tags=["Tiprack", "ANSI/SLAS", "96 Well", "Labware"],
    #     )

    #     self.resource_client.create_template(
    #         resource=Resource(
    #             resource_description="otflex 50ul tiprack",
    #         ),
    #         template_name="opentrons_flex_96_filtertiprack_50ul",
    #         description="Template for OT-Flex 50ul tiprack",
    #         tags=["Tiprack", "ANSI/SLAS", "96 Well", "Labware"],
    #     )

    #     self.resource_client.create_template(
    #         resource=Resource(
    #             resource_description="otflex 200ul tiprack",
    #         ),
    #         template_name="opentrons_flex_96_filtertiprack_200ul",
    #         description="Template for 200ul OT-Flex tiprack",
    #         tags=["Tiprack", "ANSI/SLAS", "96 Well", "Labware"],
    #     )

    #TODO: bandaid for lack of opentrons resources, pop plate as it goes into flex, make a new one when need to grab from staging
    def pop_assay_plate_resource(
            self,
            location_name: str,
        ) -> None | Resource:
            associated_resource_id = self.location_client.get_location_by_name(location_name).resource_id
            resource_object = self.resource_client.get_resource(associated_resource_id)
            popped_plate, updated_parent = self.resource_client.pop(resource=associated_resource_id)
            print(popped_plate)
            popped_resource_id = popped_plate.resource_id
            data = self.resource_client.remove_resource(resource=popped_resource_id)

    def push_new_assay_plate_resource(
            self,
            location_name: str,
            labware_type: str,
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
            if len(resource_object.children) > 0:
                    # there is already a plate at this location
                    self.logger.log_info(f"A plate with ID {resource_object.child.resource_id} already exists at location: {location_name}")

                    # pop the old plate
                    popped_plate, updated_parent = self.resource_client.pop(resource=associated_resource_id)
                    self.logger.log_info(f"Popped plate with ID {resource_object.child.resource_id} from location: {location_name}")
                    old_plate = popped_plate
            
            # # Create a new assay plate resource and push it into the resource object associated with the given location.
            # lid_resource = Resource(
            #     resource_name = f"lid_for_plate_{plate_num}_expID_{experiment_id}",
            #     attributes={
            #         "lid": True
            #     }
            # )
            if labware_type == "pcr":
                new_plate = Collection(
                    # resource_id="01KT9Q9MJF3WPYQT6TBZ9QPQ5J",
                    resource_name="Z_PCR_CORRECT_ATTRIBUTES_PLATE_2",
                    resource_class="Microplate",
                    attributes={
                        # Common attributes
                        "plate_height": 14, 
                        "description": "TEST 96-well PLATE",
                        "catalog_number": "SP-2396",

                        # PF400 specific attributes
                        "pf400_grip_height": 6,

                        # SciClops specific attributes
                        "sciclops_grip_height": 1,
                    },
                )
            
            elif labware_type == "ot2_tiprack":
                 new_plate = Collection(
                    # resource_id="01KT9Q9MJF3WPYQT6TBZ9QPQ5J",
                    resource_name="Z_PCR_CORRECT_ATTRIBUTES_PLATE_2",
                    resource_class="Microplate",
                    attributes={
                        # Common attributes
                        "plate_height": 64, 
                        "description": "Opentrons OT-2 Tiprack",

                        # PF400 specific attributes
                        "pf400_grip_height": 23,

                        # SciClops specific attributes
                        "sciclops_grip_height": 23,
                    },
                )
            
            elif labware_type == "otflex_tiprack":
                 new_plate = Collection(
                    # resource_id="01KT9Q9MJF3WPYQT6TBZ9QPQ5J",
                    resource_name="Z_PCR_CORRECT_ATTRIBUTES_PLATE_2",
                    resource_class="Microplate",
                    attributes={
                        # Common attributes
                        "plate_height": 100, 
                        "description": "Opentrons FLEX Tiprack",

                        # PF400 specific attributes
                        "pf400_grip_height": 55,

                        # SciClops specific attributes
                        "sciclops_grip_height": 55,
                    },
                )
            
            elif labware_type == "flat_bottom":
                new_plate = Collection(
                    # resource_id="01K7T1QAXCMSAJ3MAK2GAS24ZK",
                    resource_name="CORRECT_ATTRIBUTES_PLATE",
                    resource_class="Microplate",
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
                )

            self.resource_client.add_resource(new_plate)
            self.logger.log_info(f"Created new plate resource {new_plate.resource_name}, {new_plate.resource_id}")

            self.resource_client.push(
                resource = associated_resource_id,
                child = new_plate.resource_id,
            )
            self.logger.log_info(f"Pushed new plate resource into location {location_name}")
            return new_plate, old_plate


            # create a new assay plate resource and push it into the resource object associated with the given location
            # if name == "opentrons_96_wellplate_200ul_pcr_full_skirt":

            # new_plate = self.resource_client.create_resource_from_template(
            #     template_name = name,
            #     resource_name = f"res_{experiment_id}_plate{plate_num}",
            # )

            # self.logger.log_info(f"Created new plate resource {new_plate.resource_name}, {new_plate.resource_id}")

            # self.resource_client.push(
            #     resource = associated_resource_id,
            #     child = new_plate.resource_id,
            # )
            # self.logger.log_info(f"Pushed new plate resource into location {location_name}")
            # return new_plate, old_plate
    
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

    def run_experiment(self) -> None:
        """main experiment function"""

        #intitialize resources #TODO make into seperate function


        # #fragments plate
        # new_plate, old_plate = self.push_new_assay_plate_resource(
        #     location_name="rack1_row1_nest1",
        #     labware_type="pcr"
        # )

        # #golden gate plate (empty)
        # new_plate, old_plate = self.push_new_assay_plate_resource(
        #     location_name="rack1_row1_nest2",
        #     labware_type="pcr"
        # )

        # #tip box 1 20ul
        # new_plate, old_plate = self.push_new_assay_plate_resource(
        #     location_name="ot2_patrick.deck_nest_1",
        #     labware_type="ot2_tiprack"
        # )

        # #tip box 3
        # new_plate, old_plate = self.push_new_assay_plate_resource(
        #     location_name="ot2_patrick.deck_nest_3",
        #     labware_type="ot2_tiprack"
        # )

        # # tip box
        # new_plate, old_plate = self.push_new_assay_plate_resource(
        #     location_name="rack1_row1_nest3",
        #     labware_type="ot2_tiprack"
        # )

        # #empty pcr
        # new_plate, old_plate = self.push_new_assay_plate_resource(
        #     location_name="rack1_row2_nest1",
        #     labware_type="pcr"
        # )


        # # Controls plate
        # new_plate, old_plate = self.push_new_assay_plate_resource(
        #     location_name="rack1_row3_nest1",
        #     labware_type="pcr"
        # )

        # # Sybrgreen plate 
        # new_plate, old_plate = self.push_new_assay_plate_resource(
        #     location_name="rack1_row3_nest2",
        #     labware_type="flat_bottom"
        # )


        # #empty diluted pcr plate
        # new_plate, old_plate = self.push_new_assay_plate_resource(
        #     location_name="rack1_row3_nest3",
        #     labware_type="pcr"
        # )


        # #RMF mixes
        # new_plate, old_plate = self.push_new_assay_plate_resource(
        #     location_name="rack1_row4_nest1",
        #     labware_type="pcr"
        # )

        # #Empty cfps plate
        # new_plate, old_plate = self.push_new_assay_plate_resource(
        #     location_name="rack1_row4_nest2",
        #     labware_type="pcr"
        # )


        # #fdglu (empty)
        # new_plate, old_plate = self.push_new_assay_plate_resource(
        #     location_name="rack1_row5_nest1",
        #     labware_type="flat_bottom"
        # )

        # # 50UL TIPRACK
        # new_plate, old_plate = self.push_new_assay_plate_resource(
        #     location_name="rack1_row5_nest2",
        #     labware_type="otflex_tiprack"
        # )

        



        # DEFINE PATHS AND VARIABLES ========
        run_robots = False  # if False, no robots will run
        run_resources = True
        test_prints = True  # if True, will print out extra info for testing purposes

        # Experiment ID and name
        experiment_id = self.experiment.experiment_id
            # resource_server_url = None  # "http://ip of the resource server"

            # resource_client = ResourceClient(resource_server_url = resource_server_url)
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
        run_thermo_gg = run_directory / "run_thermo_gg.yaml"
        run_thermo_pcr = run_directory / "run_thermo_pcr.yaml"
        open_thermo_wf = run_directory / "open_thermo.yaml"

        ot2_to_thermocycler = (
            transfers_directory / "ot2_to_thermocycler.yaml"
        )
        replace_tip_boxes_ot2_pcr = (
             transfers_directory / "replace_tip_boxes_ot2_pcr.yaml"
        )
        thermocycler_to_ot2 = (
             transfers_directory / "thermocycler_to_ot2.yaml"
        )

        fragments_to_flex = (
             transfers_directory / "fragments_to_flex.yaml"
        )

        empty_pcr_to_flex = (
             transfers_directory / "empty_pcr_to_flex.yaml"
        )

        pcr_plate_to_ot2_block = (
             transfers_directory / "pcr_plate_to_ot2_block.yaml"
        )

        pcr_plate_to_ot2_block_2 = (
             transfers_directory / "pcr_plate_to_ot2_block_2.yaml"
        )

        seal_and_thermocycle_gg = (
             transfers_directory / "seal_and_thermocycle_gg.yaml"
        )

        fragments_flex_to_exchange = (
            transfers_directory / "fragments_flex_to_exchange.yaml"
        )

        remove_plates = (
             transfers_directory / "remove_plates_pcr.yaml"
        )

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
             transfers_directory / "empty_pcr_to_ot2.yaml"
        )

        rmf_mixes_to_flex = (
             transfers_directory / "rmf_mixes_to_flex.yaml"
        )

        empty_cfps_to_flex = (
             transfers_directory / "empty_cfps_to_flex.yaml"
        )

        cfps_plate_to_ot2_block = (
             transfers_directory / "cfps_plate_to_ot2_block.yaml"
        )

        cfps_plate_to_ot2_block_2 = (
             transfers_directory / "cfps_plate_to_ot2_block_2.yaml"
        )

        seal_cfps_to_flex = (
             transfers_directory / "seal_cfps_to_flex.yaml"
        )

        controls_plate_to_flex = (
             transfers_directory / "controls_plate_to_flex.yaml"
        )

        fdglu_plate_to_flex = (
             transfers_directory / "fdglu_plate_to_flex.yaml"
        )

        cfps_plate_to_peeler_to_flex = (
             transfers_directory / "cfps_plate_to_peeler_to_flex.yaml"
        )

        cfps_plate_to_peeler_to_flex_2 = (
             transfers_directory / "cfps_plate_to_peeler_to_flex_2.yaml"
        )

        fdglu_to_hidex = (
             transfers_directory / "fdglu_to_hidex.yaml"
        )

        seal_and_thermocycle_pcr = (
             transfers_directory / "seal_and_thermocycle_pcr.yaml"
        )

        dd_controls_flex_to_ot2 = (
             transfers_directory / "dd_controls_to_flex.yaml"
        )

        sybrgreen_flex_to_hidex = (
             transfers_directory / "sybrgreen_flex_to_hidex.yaml"
        )

        sybrgreen_hidex_to_rack = (
             transfers_directory / "sybrgreen_hidex_to_rack.yaml"
        )

        dispose_diluted_and_rmf = (
             transfers_directory / "dispose_diluted_and_rmf.yaml"
        )

        fragments_and_gg_to_ot2 = (
             transfers_directory / "fragments_and_gg_to_ot2.yaml"
        )

        cfps_plate_to_peeler_to_ot2 = (
             transfers_directory / "cfps_plate_to_peeler_to_ot2.yaml"
        )

        pcr_products_to_rack = (
             transfers_directory / "pcr_products_to_rack.yaml"
        )

        replace_ot2_tip_box_113 = (
                transfers_directory / "replace_ot2_tip_box_113.yaml"
        )

        replace_flex_tip_box_152 = (
             transfers_directory / "replace_flex_tip_box_152.yaml"
        )





        # Protocol paths (for OT-2)
        A4_to_B1 = protocol_directory / "pcr_A4_to_B1.py"
        A4_to_C1 = protocol_directory / "pcr_A4_to_C1.py"
        C1_to_A4 = protocol_directory / "pcr_C1_to_A4.py"
        B1_to_A4 = protocol_directory / "pcr_B1_to_A4.py"
        A4_to_C2 = protocol_directory / "pcr_A4_to_C2.py"
        A4_to_D1 = protocol_directory / "pcr_A4_to_D1.py"
        A4_to_B3 = protocol_directory / "pcr_A4_to_B3.py"
        C2_to_A4 = protocol_directory / "pcr_C2_to_A4.py"
        A4_to_B2 = protocol_directory / "pcr_A4_to_B2.py"
        B3_to_A4 = protocol_directory / "pcr_B3_to_A4.py"
        D1_to_A4 = protocol_directory / "pcr_D1_to_A4.py"
        A2_to_A4 = protocol_directory / "pcr_A2_to_A4.py"
        A4_to_A2 = protocol_directory / "pcr_A2_to_A4.py"



        # Protocol paths (for OT-2)
        golden_gate_protocol = protocol_directory / "pd_golden_gate_ot2_v2.py"

        

        pcr_flex_protocol = protocol_directory / "pd_pcr_v2_flex.py"
        pcr_ot2_protocol = protocol_directory / "pd_pcr_v2_ot2.py"
        dd_flex_protocol = protocol_directory / "pd_dd_v2_flex.py"
        dd_ot2_protocol = protocol_directory / "pd_dd_v2_ot2.py"
        cfps_flex_protocol = protocol_directory / "cell_free_pd_flex_v2.py"
        cfps_ot2_protocol = protocol_directory / "cell_free_pd_ot2_v2.py"
        fdglu_flex_protocol = protocol_directory / "pd_fdglu_flex_v2.py"
        run_hidex = run_directory / "run_hidex.yaml"
        run_hidex_sybr = run_directory / "run_hidex_sybr.yaml"
        ot2_rmf_removal_protocol = protocol_directory / "pd_fdglu_ot2_rmf_removal.py"


        payload = {}

        combination_data = self.rest_handler.collect_combinations(oracle_id=1008)


        payload["combinations"] = combination_data["combinations"]
        payload["use_combinations"] = combination_data["use_combinations"]
        payload["non_combinatorial_sources"] = combination_data["non_combinatorial_sources"]

        print("COMBINATIONS", payload["combinations"])
        print("USE COMBINATIONS", payload["use_combinations"])
        print("non_combinatorial_sources", payload["non_combinatorial_sources"])

        # combination_data = [[1], [2, 2], [3, 3], [4, 4]]
        # combination_num = helper_functions.calculate_total_combinations(combination_data)
        
        # payload["combinations"] = combination_data
        # payload["use_combinations"] = True
        # payload["non_combinatorial_sources"] = False

        #STARTING TIP AMOUNTS
        # OT2: 2 20UL TIP RACKS 1 AND 3
        # FLEX: 1 200UL RACK A1 AND 2 50UL RACKS A2 AND A3


        # EXPERIMENT ACTIONS -------------------------------------------------------

        ###############
        ### GOLDEN GATE
        ##############
        input("Paused, verify combinations and press Enter...")
        


        # workflow = self.workcell_client.submit_workflow(
        #     fragments_and_gg_to_ot2.resolve(),
        # )

        # # run ot2 protocol step 1

        #TIPS USED: 1 COLUMN 20UL PER 8 COMBOS MASTER MIX
        # 4 COLUMNS 20UL PER 8 COMBOS FRAGMENTS
        # 8 COMBO RUN: 5 COLS OF 20ul tips
        # 24 COMBO RUN: 15 COLS OF 20UL TIPS

        # 8 COMBO:
        # OT2 7 COLS LEFT IN BOX 1 AND 12 IN BOX 2
        # FLEX: FULL

        # 24 COMBO:
        # OT2 BOX 1 EMPTY, 9 IN BOX 2
        # FLEX FULL



        ot2_replacement_variables = helper_functions.collect_ot2_replacement_variables(payload)
        temp_ot2_file_str = helper_functions.generate_ot2_protocol(golden_gate_protocol, ot2_replacement_variables)
        print(temp_ot2_file_str)
#         payload["current_ot2_protocol"] = temp_ot2_file_str
#         workflow = self.workcell_client.submit_workflow(
#             run_ot2_wf.resolve(),
#             file_inputs={
#                 "ot2_protocol": payload["current_ot2_protocol"],
#             },
#         )


        
        

#         # transfer destination plate to thermocycler and run
#         #WORKING 7-22
#         workflow = self.workcell_client.submit_workflow(
#             seal_and_thermocycle_gg.resolve(),
#         )

#         #run thermocycler
#         workflow = self.workcell_client.submit_workflow(
#             run_thermo_gg.resolve(),
#         )



#         #########
#         ### PCR
#         ########

#         # set temp blocks on both flex and ot2 to 4 deg

#         # # swap out one new p20 tip box on ot2, remove from D1 and D3
#         #WORKING 7-22
#         workflow = self.workcell_client.submit_workflow(
#             replace_tip_boxes_ot2_pcr.resolve(),
#         )

#         # move gg plate from thermocycler to temp block in ot2 deck 6
#         #WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             thermocycler_to_ot2.resolve(),
#         )

#         ##############
#         ############
#         #############

#         # # move fragment plate from deck 4 ot2 to flex and empty pcr plate to flex cooling blocks #TODO: maybe do this in ot2 instead
#         #WORKING 7-23

#         workflow = self.workcell_client.submit_workflow(
#             fragments_to_flex.resolve(),
#         )

#         #run flex A4 to temp block  B1
#         #WORKING 7-23
#         payload["current_flex_protocol"] = A4_to_B1
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         #WORKING 7-23
#         self.pop_assay_plate_resource("otflex_sandy.deck_nest_A4")

#         #WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             empty_pcr_to_flex.resolve(),
#         )

#         #run flex A4 to temp block C1
#         #WORKING 7-23
#         payload["current_flex_protocol"] = A4_to_C1
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )
#         self.pop_assay_plate_resource("otflex_sandy.deck_nest_A4")

#         # TIPS USED: 1  COLUMN 200UL PER 8 COMBOS
#         # 8 COMBO RUN: 1 COLUMN OF 200UL
#         # 24 COMBO RUN: 3 COLUMNS OF 200UL

        

#         ot2_replacement_variables = helper_functions.collect_ot2_replacement_variables(payload)
#         temp_ot2_file_str = helper_functions.generate_ot2_protocol(pcr_flex_protocol, ot2_replacement_variables)
#         payload["current_flex_protocol"] = temp_ot2_file_str
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         # 8 COMBO:
#         # OT2 7 COLS LEFT IN BOX 1 AND 12 IN BOX 2
#         # FLEX: 50ULS BOTH FULL 11 COLS IN 200UL

#         # 24 COMBO:
#         # OT2: 9 COLS LEFT IN BOX 2
#         # FLEX 50UL IS FULL, 9 COLS IN 200UL


#         # #move pcr plate to cooled block on ot2 position 4

#         #run flex temp block C1 to A4
#         #WORKING 7-23
#         payload["current_flex_protocol"] = C1_to_A4
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         new_plate, old_plate = self.push_new_assay_plate_resource(
#             location_name="otflex_sandy.deck_nest_A4",
#             labware_type="pcr"
#         )

#         # # #WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             pcr_plate_to_ot2_block.resolve(),
#         )


#         # # #WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             pcr_plate_to_ot2_block_2.resolve(),
#         )

#         # TIPS USED: 2 COLUMN 20UL PER 8 COMBOS
#         # 1 COLUMN FOR WATER 1 COLUMN FOR GG SAMPLES
#         # 8 COMBO RUN: 2 COLUMNS OF 20UL
#         # 24 COMBO RUN: 6 COLUMNS OF 20UL

#         ot2_replacement_variables = helper_functions.collect_ot2_replacement_variables(payload)
#         temp_ot2_file_str = helper_functions.generate_ot2_protocol(pcr_ot2_protocol, ot2_replacement_variables)
#         payload["current_ot2_protocol"] = temp_ot2_file_str
#         workflow = self.workcell_client.submit_workflow(
#             run_ot2_wf.resolve(),
#             file_inputs={
#                 "ot2_protocol": payload["current_ot2_protocol"],
#             },
#         )

#         # 8 COMBO:
#         # OT2 5 COLS LEFT IN BOX 1 AND 12 IN BOX 2
#         # FLEX: 50ULS BOTH FULL 11 COLS IN 200UL

#         # 24 COMBO:
#         # OT2: 3 COLS LEFT IN 20UL
#         # FLEX: 50UL IS FULL, 9 COLS IN 200UL

#         # # dilute golden gate products with 20ul of water and mix
#         # 1 ul of diluted golden gate product to cols 1-4 of pcr product plate, mix
 


#         #seal and thermocycle pcr product plate
#         #WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             seal_and_thermocycle_pcr.resolve(),
#         )


#         #run thermocycler
#         workflow = self.workcell_client.submit_workflow(
#             run_thermo_pcr.resolve(),
#         )

#         #TODO maybe wait until after plates are discarded
#         #WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             open_thermo_wf.resolve(),
#         )


#         # #trash fragment and golden gate plate

#         #remove fragments plate from flex B1
#         #WORKING 7-23
#         payload["current_flex_protocol"] = B1_to_A4
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         new_plate, old_plate = self.push_new_assay_plate_resource(
#             location_name="otflex_sandy.deck_nest_A4",
#             labware_type="pcr"
#         )

#         #WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             fragments_flex_to_exchange.resolve(),
#         )


#         #WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             remove_plates.resolve(),
#         )




#         ################
#         #### DETECT DILUTE
#         ################

#         #verify all temp blocks on flex and ot2 set to 4 deg

#         #move pcr plate to cool block in flex C1
#         workflow = self.workcell_client.submit_workflow(
#             thermocycler_to_flex.resolve(),
#         )

#         payload["current_flex_protocol"] = A4_to_C1
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         self.pop_assay_plate_resource("otflex_sandy.deck_nest_A4")

#         input("PAUSED: MOVE CONTROLS PLATE TO RACK 1 ROW 3 NEST 1")

#         #move controls plate (FROM?) to cool block in flex #TODO: needs to be cooled
#         #WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             controls_to_flex.resolve(),
#         )

#         payload["current_flex_protocol"] = A4_to_B1
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         self.pop_assay_plate_resource("otflex_sandy.deck_nest_A4")

#         #move empty sybrgreen plate to flex
#         #WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             sybrgreen_to_flex.resolve(),
#         )

#         payload["current_flex_protocol"] = A4_to_C2
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         self.pop_assay_plate_resource("otflex_sandy.deck_nest_A4")
        

#         #move empty diluted pcr plate to OT-2 (6)
#         #WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             empty_pcr_to_ot2.resolve(),
#         )


#         # TIPS USED: 
#         # WATER TO PCR: 1 COL ALWAYS, 200UL
#         # DILUTION: 1 COL PER 8 COMBOS: 50UL
#         # SYBRGREEN TO DEST: 1 COL ALWAYS: 200UL
#         # PCR TO DEST: 1 COL PER 8 COMBOS: 50UL
#         # CONTROLS TO SYBRGREEN: 1 COL always: 50UL
#         # 8 COMBO RUN: 2 COLS OF 200UL AND 3 COLS OF 50UL
#         # 24 COMBO RUN: 2 COLS OF 200UL AND 7 COLS OF 50UL

#         # #multichannel flex protocol
#         ot2_replacement_variables = helper_functions.collect_ot2_replacement_variables(payload)
#         temp_ot2_file_str = helper_functions.generate_ot2_protocol(dd_flex_protocol, ot2_replacement_variables)
#         payload["current_flex_protocol"] = temp_ot2_file_str
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         # 8 COMBO:
#         # OT2 5 COLS LEFT IN BOX 1 AND 12 IN BOX 2
#         # FLEX: 50ULS 9COLS IN 1 AND 12 IN 2,  9 COLS IN 200UL

#         # 24 COMBO:
#         # OT2 3 COLS LEFT IN 20UL
#         # FLEX: 5 COLS LEFT IN 50, 7 COLS LEFT IN 200

        


# # #move pcr products plate from flex to cool block in ot2 (4)
#         #WORKING 7-23
#         payload["current_flex_protocol"] = C1_to_A4
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         new_plate, old_plate = self.push_new_assay_plate_resource(
#             location_name="otflex_sandy.deck_nest_A4",
#             labware_type="pcr"
#         )

#         #WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             pcr_plate_to_ot2_block.resolve(),
#         )

#         #WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             pcr_plate_to_ot2_block_2.resolve(),
#         )


#         #move controls from flex to ot-2 B1 flex to D1
#         #WORKING 7-23
#         payload["current_flex_protocol"] = B1_to_A4
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         new_plate, old_plate = self.push_new_assay_plate_resource(
#             location_name="otflex_sandy.deck_nest_A4",
#             labware_type="pcr"
#         )

#         # #WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             pcr_plate_to_ot2_block.resolve(),
#         )

#         #TODO: grabbed plate really high for some reason?

#         workflow = self.workcell_client.submit_workflow(
#             dd_controls_flex_to_ot2.resolve(),
#         )


#         workflow = self.workcell_client.submit_workflow(
#                 replace_ot2_tip_box_113.resolve(),
#             )


#         #TIPS USED
#         # WATER TO PCR DILUTION: 1 COL ALWAYS: 20UL
#         # PCR TO WATER: 1 COL PER 8 COMBOS: 20UL
#         # CONTROLS TO PCR: 1 COL ALWAYS: 20UL
#         #8 COMBO RUN: 3 COLUMNS 20ul
#         # 24 COMBO RUN: 5 COLUMNS 20UL

#         #ot2 dilution protocol
#         ot2_replacement_variables = helper_functions.collect_ot2_replacement_variables(payload)
#         temp_ot2_file_str = helper_functions.generate_ot2_protocol(dd_ot2_protocol, ot2_replacement_variables)
#         payload["current_ot2_protocol"] = temp_ot2_file_str
#         workflow = self.workcell_client.submit_workflow(
#             run_ot2_wf.resolve(),
#             file_inputs={
#                 "ot2_protocol": payload["current_ot2_protocol"],
#             },
#         )

#         # 8 COMBO:
#         # OT2 2 COLS LEFT IN BOX 1 AND 12 IN BOX 2
#         # FLEX: 50ULS 9COLS IN 1 AND 12 IN 2,  9 COLS IN 200UL

#         # 24 COMBO:
#         # OT2: 7 COLS LEFT IN 20UL
#         # FLEX: 5 COLS LEFT IN 50, 7 COLS LEFT IN 200

#         #WORKING 7-23

#         payload["current_flex_protocol"] = C2_to_A4
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         new_plate, old_plate = self.push_new_assay_plate_resource(
#             location_name="otflex_sandy.deck_nest_A4",
#             labware_type="flat_bottom"
#         )


#         # move sybrgreen plate to the hidex
#         # WORKING 7-23
#         workflow = self.workcell_client.submit_workflow(
#             sybrgreen_flex_to_hidex.resolve(),
#         )

#         #run hidex protocol # TODO
#         workflow = self.workcell_client.submit_workflow(
#             run_hidex_sybr.resolve(),
#         )

#         workflow = self.workcell_client.submit_workflow(
#             sybrgreen_hidex_to_rack.resolve(),
#         )

#         workflow = self.workcell_client.submit_workflow(
#             pcr_products_to_rack.resolve(),
#         )

#         input("Script paused. Press Enter to continue...")









#         #################
#         ##### CELL FREE
#         #################

#         #add rmf mixes and empty cfps plate to cool block in flex
#         #WORKING 7-24
#         workflow = self.workcell_client.submit_workflow(
#             rmf_mixes_to_flex.resolve(),
#         )

#         payload["current_flex_protocol"] = A4_to_B1
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         self.pop_assay_plate_resource("otflex_sandy.deck_nest_A4")

#         #WORKING 7-24
#         workflow = self.workcell_client.submit_workflow(
#             empty_cfps_to_flex.resolve(),
#         )

#         payload["current_flex_protocol"] = A4_to_C1
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         self.pop_assay_plate_resource("otflex_sandy.deck_nest_A4")


#         # TIPS USED
#         # MIX A TO RMF: 8 + 8 = 2 COLS 200UL always***
#         # MIX B TO RMF: 1 COL ALWAYS  50UL
#         # 8 COMBO RUN: 1 COL 50UL, 2 COLS 200UL
#         # 24 COMBO RUN: 1 COL 50UL, 2 COLS 200UL

#         #cfps master mix protocol in flex
#         ot2_replacement_variables = helper_functions.collect_ot2_replacement_variables(payload)
#         temp_ot2_file_str = helper_functions.generate_ot2_protocol(cfps_flex_protocol, ot2_replacement_variables)
#         payload["current_flex_protocol"] = temp_ot2_file_str
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         # 8 COMBO:
#         # OT2 2 COLS LEFT IN BOX 1 AND 12 IN BOX 2
#         # FLEX: 50ULS 8COLS IN 1 AND 12 IN 2,  7 COLS IN 200UL

#         # 24 COMBO:
#         # OT2: 7 COLS LEFT IN 20UL
#         # FLEX: 4 COLS LEFT IN 50UL, 5 COLS LEFT IN 200


#         # #move cfps plate to cool block in ot2 (4)
#         # #WORKING 7-24
#         payload["current_flex_protocol"] = C1_to_A4
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         new_plate, old_plate = self.push_new_assay_plate_resource(
#             location_name="otflex_sandy.deck_nest_A4",
#             labware_type="pcr"
#         )

#         # #WORKING 7-24
#         workflow = self.workcell_client.submit_workflow(
#             cfps_plate_to_ot2_block.resolve(),
#         )


#         #WORKING 7-24
#         workflow = self.workcell_client.submit_workflow(
#             cfps_plate_to_ot2_block_2.resolve(),
#         )


#         #TIPS USED
#         # DILUTED PCR TO CFPS: 1 COL PER 8 COMBOS PLUS 1 EXTRA COL FOR CONTROLS
#         # 8 COMBO RUN: 2 COLUMNS 20UL
#         # 24 COMBO RUN: 4 COLUMNS 20UL

#         # pcr to cfps plate cols 1-5
#         # dilute golden gate products with 20ul of water and mix
#         # 1 ul of diluted golden gate product to cols 1-4 of pcr product plate, mix
#         ot2_replacement_variables = helper_functions.collect_ot2_replacement_variables(payload)
#         temp_ot2_file_str = helper_functions.generate_ot2_protocol(cfps_ot2_protocol, ot2_replacement_variables)
#         payload["current_ot2_protocol"] = temp_ot2_file_str
#         workflow = self.workcell_client.submit_workflow(
#             run_ot2_wf.resolve(),
#             file_inputs={
#                 "ot2_protocol": payload["current_ot2_protocol"],
#             },
#         )

#         # 8 COMBO:
#         # OT2 0 COLS LEFT IN BOX 1 AND 12 IN BOX 2
#         # FLEX: 50ULS 8COLS IN 1 AND 12 IN 2,  7 COLS IN 200UL

#         # 24 COMBO:
#         # OT2: 3 COL LEFT IN 20UL
#         # FLEX: 4 COLS LEFT IN 50UL, 5 COLS LEFT IN 200

        

#         # #seal cfps, move to flex heater-shaker, incubate at 37 deg for 2.5 hours
#         # #WORKING 7-24
#         workflow = self.workcell_client.submit_workflow(
#             seal_cfps_to_flex.resolve(),
#         )


#         # # #WORKING 7-24
#         payload["current_flex_protocol"] = A4_to_D1
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         self.pop_assay_plate_resource("otflex_sandy.deck_nest_A4")


#         #remove diluted pcr (ot2 6) and rmf (flex B1)
#         #WORKING 7-24
#         payload["current_flex_protocol"] = B1_to_A4
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         new_plate, old_plate = self.push_new_assay_plate_resource(
#             location_name="otflex_sandy.deck_nest_A4",
#             labware_type="pcr"
#         )

#         workflow = self.workcell_client.submit_workflow(
#             dispose_diluted_and_rmf.resolve(),
#         )



#         ################
#         #### FD GLU ASSAY
#         ################

#         # #move controls plate from? to cool block on flex
#         # #WORKING 7-24
#         workflow = self.workcell_client.submit_workflow(
#             controls_plate_to_flex.resolve(),
#         )

#         # #WORKING 7-24
#         payload["current_flex_protocol"] = A4_to_B1
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         self.pop_assay_plate_resource("otflex_sandy.deck_nest_A4")

#         # move empty fdglu assay plate to flex

#         # #WORKING 7-24
#         workflow = self.workcell_client.submit_workflow(
#             fdglu_plate_to_flex.resolve(),
#         )

#         payload["current_flex_protocol"] = A4_to_B3 
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         # cfps plate on heater shaker, peel and put back in flex (spin down?)
#         #TODO: flex didnt grip properly once
#         payload["current_flex_protocol"] = D1_to_A4 
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )
        
#         new_plate, old_plate = self.push_new_assay_plate_resource(
#             location_name="otflex_sandy.deck_nest_A4",
#             labware_type="pcr"
#         )

#         # #WORKING 7-24
#         workflow = self.workcell_client.submit_workflow(
#             cfps_plate_to_peeler_to_flex.resolve(),
#         )

#         # # #WORKING 7-24
#         workflow = self.workcell_client.submit_workflow(
#             cfps_plate_to_peeler_to_flex_2.resolve(),
#         )

#         # WORKING 7-24
#         payload["current_flex_protocol"] = A4_to_B2
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         # TODO: REPLACE 50UL TIPRACK\

#         input("PAUSED: REPLACE 50UL TIPRACK IN OT FLEX")

#         # # A2 TO A4
#         # payload["current_flex_protocol"] = A2_to_A4
#         # workflow = self.workcell_client.submit_workflow(
#         #     run_flex_wf.resolve(),
#         #     file_inputs={
#         #         "flex_protocol": payload["current_flex_protocol"],
#         #     },
#         # )

#         # new_plate, old_plate = self.push_new_assay_plate_resource(
#         #     location_name="otflex_sandy.deck_nest_A4",
#         #     labware_type="otflex_tiprack"
#         # )

#         # #REPLACE TIP RACK
#         # workflow = self.workcell_client.submit_workflow(
#         #     replace_flex_tip_box_152.resolve(),
#         # )

#         # # A4 TO A2
#         # payload["current_flex_protocol"] = A4_to_A2
#         # workflow = self.workcell_client.submit_workflow(
#         #     run_flex_wf.resolve(),
#         #     file_inputs={
#         #         "flex_protocol": payload["current_flex_protocol"],
#         #     },
#         # )



#         # # flex fdglu protocol
#         # TIPS USED
#         # RMF REMOVAL: ALWAYS 3 TIPS 50UL
#         # FDGLU TO PLATE: 1 COL ALWAYS 200UL
#         # CFPS TO DEST: 1 COL PER 8 COMBOS PLUS 1 FOR CONTROLS 50UL
#         # CONTROLS TO DEST: ALWAYS 3 TIPS FOR CONTROLS 50UL
#         # 8 COMBO RUN: 3 COLS 50UL AND 1 COL 200UL
#         # 24 COMBO RUN: 5 COLS 50UL AND 1 COL 200UL


#         ot2_replacement_variables = helper_functions.collect_ot2_replacement_variables(payload)
#         temp_ot2_file_str = helper_functions.generate_ot2_protocol(fdglu_flex_protocol, ot2_replacement_variables)
#         payload["current_flex_protocol"] = temp_ot2_file_str
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         # 8 COMBO:
#         # OT2 0 COLS LEFT IN BOX 1 AND 12 IN BOX 2
#         # FLEX: 50ULS 5COLS IN 1 AND 12 IN 2,  6 COLS IN 200UL

#         # 24 COMBO:
#         # OT2: 1  LEFT IN 20UL
#         # FLEX: 7 COLS LEFT IN 50 AND 4 COLS LEFT IN 200UL


#         #move fdglu assay plate to hidex
#         #WORKING 7-24
#         payload["current_flex_protocol"] = B3_to_A4
#         workflow = self.workcell_client.submit_workflow(
#             run_flex_wf.resolve(),
#             file_inputs={
#                 "flex_protocol": payload["current_flex_protocol"],
#             },
#         )

#         #run hidex 
#         #WORKING 7-24
#         workflow = self.workcell_client.submit_workflow(
#             cfps_plate_to_peeler_to_flex.resolve(),
#         )


#         #WORKING 7-24
#         workflow = self.workcell_client.submit_workflow(
#             fdglu_to_hidex.resolve(),
#         )

#         workflow = self.workcell_client.submit_workflow(
#             run_hidex.resolve(),
#         )

#         hidex_data_point = workflow.get_datapoint(label="file")
#         # print("HIDEX DATA POINT", hidex_data_point)
#         # print("HIDEX DATA POINT PATH", hidex_data_point.path)
#         path = hidex_data_point.path[12:]
#         # path.removeprefix("/home/madsci/")
#         correct_path = "/home/rpl/workspace/" + path
#         # print("CORRECT PATH", correct_path)

#         # self.rest_handler.upload_excel_file(correct_path)
#         oracle_id = self.rest_handler.upload_excel_file(correct_path)
#         print(oracle_id)
#         # /home/rpl/workspace/rapid446_sdl/.madsci/datapoints/2026/8/6

#         #TODO: REMOVE ALL LABWARE FROM OT2 AND FLEX

#         #open rack nests: 131, 132, 142, 143, 151, 152, 153









if __name__ == "__main__":
    # exp_app = PDApp()

    # current_time = datetime.now()

    # # Start experiment run
    # with exp_app.manage_experiment(
    #     run_name = f"PD_Experiment{current_time.strftime('%Y%m%d_%H%M%S')}",
    #     run_description = "PD experiment",
    # ):
    #     exp_app.start_app()


    # Start the experiment run.
    PDApp.main(
        lab_server_url="http://146.137.240.20:8000/",
    )
