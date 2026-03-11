#!/usr/bin/env python3
"""Experiment application for Chris and Nidhi's substrate experiment"""

from pathlib import Path

from wei import ExperimentClient
from wei.types.experiment_types import CampaignDesign, ExperimentDesign
from wei.types.workflow_types import Workflow

from ot2_offsets import ot2biobeta, ot2bioalpha
import helper_functions
import time
import csv
from datetime import datetime



"""
TODO:
- FIX SLEEP TIMES -> How long to sleep after plate 1 stops circulating. Check inner and outer loops.
- Improve comments (continue with numbering steps)
- alter inoculation protocol to only drop tip the first transfer but replace tips the rest of the transfers
- why does the pf400 move before sciclops remove lid is done?
- does incubator prevent other communication during a incubation if counting down?
- why is ot2bioalpha not connecting?
- recalibrate bmg nest (small dropping sound needs to be fixed)
- inheco logging
- how to return accurate timestamps from bmg readings?

"""


def main() -> None:
    """Runs the OT-2 protocol to create extra media plates"""

    # INITIAL EXPERIMENT SETUP ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # define the ExperimentDesign object that will be used to register the experiment
    experiment_design = ExperimentDesign(
        experiment_name="Substrate_Experiment_Prep_Extra_Media_Plates",
        experiment_description="Experiment application to prep 5 extra media plates for the substrate application",
    )
    # define a campaign object (useful if we want to group many of these substrate experiments together)
    campaign = CampaignDesign(
        campaign_name="Substrate_Campaign",
        campaign_description="Campaign to collect all substrate experiments",
    )
    # define the experiment client object that will communicate with the WEI server
    experiment_client = ExperimentClient(
        server_host="localhost",
        server_port="8000",
        experiment=experiment_design,
        campaign=campaign,
    )

    # DEFINE PATHS AND VARIABLES ---------------------------------

    # # capture the expriment ID
    experiment_id = experiment_client.experiment.experiment_id

    # directory paths
    app_directory = Path(__file__).parent.parent
    wf_directory = app_directory / "workflows"
    wf_run_instrument_directory = wf_directory / "run_instrument"
    wf_set_up_tear_down_directory = wf_directory / "set_up_tear_down"
    wf_transfers_directory = wf_directory / "transfers"
    protocol_directory = app_directory / "protocols"

    # workflow paths (run instruments)
    setup_for_first_inoculation_wf = wf_set_up_tear_down_directory / "setup_for_first_inoculation_wf.yaml"
    run_ot2_wf = wf_run_instrument_directory / "run_ot2_wf.yaml"
    ot2_to_run_bmg_wf = wf_run_instrument_directory / "ot2_to_run_bmg_wf.yaml"
    bmg_to_run_incubator_wf = wf_run_instrument_directory / "bmg_to_run_incubator_wf.yaml"
    incubator_to_run_bmg_wf = wf_run_instrument_directory / "incubator_to_run_bmg_wf.yaml"
    incubator_to_run_bmg_PF400_LID_wf = wf_run_instrument_directory / "incubator_to_run_bmg_PF400_LID_wf.yaml"
    get_new_plate_wf = wf_set_up_tear_down_directory / "get_new_plate_wf.yaml"
    replace_ot2_old_wf = wf_transfers_directory / "replace_ot2_old_wf.yaml"
    remove_old_substrate_plate_wf = wf_set_up_tear_down_directory / "remove_old_substrate_plate_wf.yaml"
    at_end_bmg_to_trash_wf = wf_set_up_tear_down_directory / "at_end_bmg_to_trash_wf.yaml"


    # protocol paths (for OT-2)
    first_inoculate_both_protocol = protocol_directory / "first_inoculate_both.py"
    inoculate_protocol = protocol_directory / "inoculate.py"

    # experiment 1: incubation = 1 hr cycles, transfers every 10 hours
    exp1_variables = {
        "incubation_seconds": 20,   # 60 minutes (1 hr) = 3600 seconds
        "lid_location": "lidnest1",
        "ot2_node": "ot2biobeta",
        "ot2_new_plate_location": "ot2biobeta_deck1_wide",
        "ot2_old_plate_location": "ot2biobeta_deck3_wide",
        "ot2_safe_path": "safe_path_ot2biobeta",
        "incubator_node": "inheco_devID2_floor1",  # CHANGED FOR DEMO
        "incubator_location": "inheco_devID2_floor1_nest",   # CHANGED FOR DEMO
        "tip_box_location": 4,
        "new_stack": "stack1",
        "trash_stack": "stack4",
    }

    # experiment 2: incubation = 2 hr cycles, transfers every 20 hours
    exp2_variables = {
        "incubation_seconds": 20,   # 120 minutes (2 hrs) = 7200 seconds
        "lid_location": "lidnest2",
        "ot2_node": "ot2bioalpha",
        "ot2_new_plate_location": "ot2bioalpha_deck1_wide",
        "ot2_old_plate_location": "ot2bioalpha_deck3_wide",
        "ot2_safe_path": "safe_path_ot2bioalpha",
        "incubator_node": "inheco_devID2_floor1",
        "incubator_location": "inheco_devID2_floor1_nest",
        "tip_box_location": 4,
        "new_stack": "stack2",
        "trash_stack": "stack5",
    }

    # other variables (for loop tracking)
    csv_data_direcory = "/home/rpl/workspace/Nidhi_data"
    experiment_label = "2a"
    transfer_loop_num = 0       # outer loop
    incubation_loop_num = 0     # inner loop
    exp1_reading_num_in_plate = 1
    exp2_reading_num_in_plate = 1
    exp1_plate_num = 1
    exp2_plate_num = 1
    exp1_into_incubator_time = None
    exp2_into_incubator_time = None
    total_transfers = 20
    continue_exp1 = True
    continue_exp2 = True

    # initial payload setup  (experiment 1 focused at start)
    payload = {
        "ot2_node": exp1_variables["ot2_node"],
        "ot2_location": exp1_variables["ot2_new_plate_location"],
        "ot2_safe_path": exp1_variables["ot2_safe_path"],
        "tip_box_location": exp1_variables["tip_box_location"],
        "stack": exp1_variables["new_stack"],
        "lid_location": exp1_variables["lid_location"],
        "incubator_node": exp1_variables["incubator_node"],
        "incubator_location": exp1_variables["incubator_location"],
        "incubation_seconds": exp1_variables["incubation_seconds"],
        "trash_stack": exp1_variables["trash_stack"],
        "current_ot2_protocol": None,    # defined later
        "use_existing_resources": False,
        "bmg_assay_name": "NIDHI",
    }


    # EXPERIMENT STEPS: ------------------------------------------------------------------------------
    """Before running this experiment, extra substrate plates should be prepped
        by running extra_media_plates_app.py. The prepped plates for experiment 1 should
        be placed in ScoClops stack 1, and the prepped plates for experiment 2 should be
        placed in SciClops stack2. The OT-2 deck of ot2biobeta should be prepped for
        first_inoculate_both.py"""

    # TESTING
    print(app_directory)
    print(wf_directory)
    print(wf_set_up_tear_down_directory)
    print(setup_for_first_inoculation_wf)

    # WF: Transfer a new plate from each experiment stack to ot2biobeta for first inoculation
    experiment_client.start_run(
        setup_for_first_inoculation_wf.resolve(),
        payload=payload,
        blocking=True,
        simulate=False,
    )


    # # TESTING
    # print("\nSetting up for first inoculation. New plates from stacks 1 and 2 into ot2biobeta decks 1 and 3")
    # print("\tvariables hardcoded")
    # print(f"\tpayload: {payload}")

    # # WF: Run first_inoculate_both OT-2 protocol
    # payload["current_ot2_protocol"] = str(first_inoculate_both_protocol)
    # edited_ot2_wf = helper_functions.replace_wf_node_names(
    #     workflow = run_ot2_wf,
    #     payload = payload
    # )
    # experiment_client.start_run(
    #     edited_ot2_wf,
    #     payload=payload,
    #     blocking=True,
    #     simulate=False,
    # )

    # # TESTING
    # print("\nRan Inoculate both OT-2 protocol")
    # print(f"\tot2 protocol: {payload["current_ot2_protocol"]}")
    # print("\t\tnot specified yet")
    # print(f"\tot2 node: {payload["ot2_node"]}")
    # print(f"\tpayload: {payload}")

    # # WFs: Transfer experiment 1 plate to bmg, read, then place into incubator
    # # TESTING
    # print("\nTransfer from ot2 to bmg, read, then incubate")

    # timestamp_now = int(datetime.now().timestamp())
    # payload["bmg_data_output_name"] = (
    #     f"{experiment_label}_{timestamp_now}_{experiment_id}_exp1_{exp1_plate_num}_{exp1_reading_num_in_plate}.txt"
    # )
    # # ot2 to bmg
    # run_info = experiment_client.start_run(
    #     ot2_to_run_bmg_wf.resolve(),
    #     payload=payload,
    #     blocking=True,
    #     simulate=False,
    # )
    # # TESTING
    # print("\tot2 to bmg")
    # print(f"\tpayload: {payload}")
    # print(f"\tot2 grab location: {payload["ot2_node"]} (hardcoded) @ {payload["ot2_node"]}, {payload['current_ot2_protocol']}")
    # print(f"\tbmg reading name: {payload['bmg_data_output_name']}")

    # exp1_reading_num_in_plate += 1

    # # TESTING
    # print(f"\tincreasing exp1 reading in plate number: {exp1_reading_num_in_plate}")

    # # write utc bmg timestamp to csv data file
    # helper_functions.write_timestamps_to_csv(
    #     csv_directory_path=csv_data_direcory,
    #     experiment_id=experiment_id,
    #     bmg_filename=payload["bmg_data_output_name"],
    #     accurate_timestamp=run_info.steps[4].end_time,  # index 4 = bmg reading
    # )

    # # Testing
    # print(f"\twriting data to csv: {payload["bmg_data_output_name"]}, with timestamp")

    # # bmg to inheco incubator
    # edited_to_inheco_wf = helper_functions.replace_wf_node_names(
    #     workflow=bmg_to_run_incubator_wf,
    #     payload=payload
    # )
    # experiment_client.start_run(
    #     edited_to_inheco_wf,
    #     payload=payload,
    #     blocking=True,
    #     simulate=False,
    # )

    # # TESTING
    # print(f"\n\tbmg to inheco")
    # print(f"\tpayload: {payload}")
    # print(f"\tinheco node: {payload["incubator_node"]} @ {payload["incubator_location"]}, inc time = {payload['incubation_seconds']}")

    # # capture incubation start time
    # exp1_into_incubator_time = time.time()

    # # TESTING
    # print(f"\texperiment 1: incubation started at {exp1_into_incubator_time}")

    # # increase variables
    # transfer_loop_num += 1

    # print(f"\ttransfer loop number increased: {transfer_loop_num}")

    # # sleep until experiment 1 plate is ready for next reading (1 hr total)
    # while time.time() - exp1_into_incubator_time < exp1_variables["incubation_seconds"]:
    #     print(f"will continue in... {int(exp1_variables["incubation_seconds"]-(time.time() - exp1_into_incubator_time))} seconds")
    #     time.sleep(5) # 5 seconds

    # # TESTING
    # print("\nSleeping until plate 1 has incubated for 1 hour")
    # print(f"\tsleeping for: {int(exp1_variables["incubation_seconds"]-(time.time() - exp1_into_incubator_time))} seconds")

    # """Now that both experiment plates are in the incubator,
    #     we can start the both the outer transfers loop and
    #     the inner incubation loop."""

    # # LOOP START -----------------------------------------------------------

    # # # TESTING:
    # # print("\nSTARTING LOOPS")

    # while incubation_loop_num < 2:

    #     if continue_exp1:
    #         # WFs: Transfer experiment 1 plate from incubator, to bmg, read, and return to incubator

    #         # TESTING
    #         print("\tEXP1: taking reading and returning to incubator")
    #         print(f"\n\t\tcontinue exp1?: {continue_exp1}")

    #         # update payload variables
    #         payload["ot2_location"] = exp1_variables["ot2_new_plate_location"]
    #         payload["lid_location"] = exp1_variables["lid_location"]
    #         payload["incubator_node"] = exp1_variables["incubator_node"]
    #         payload["incubator_location"] = exp1_variables["incubator_location"]
    #         payload["incubation_seconds"] = exp1_variables["incubation_seconds"]

    #         # inheco incubator to bmg
    #         timestamp_now = int(datetime.now().timestamp())
    #         payload["bmg_data_output_name"] = (
    #             f"{experiment_label}_{timestamp_now}_{experiment_id}_exp1_{exp1_plate_num}_{exp1_reading_num_in_plate}.txt"
    #         )
    #         edited_to_bmg_wf = helper_functions.replace_wf_node_names(
    #             workflow=incubator_to_run_bmg_wf,
    #             payload=payload
    #         )
    #         run_info = experiment_client.start_run(
    #             edited_to_bmg_wf,
    #             payload=payload,
    #             blocking=True,
    #             simulate=False,
    #         )

    #         # TESTING
    #         print(f"\t\tinheco to bmg and read")
    #         print(f"\t\tinheco node: {payload['incubator_node']} @ {payload["incubator_location"]}")
    #         print(f"\t\tbmg data filename: {payload['bmg_data_output_name']}")

    #         # write utc bmg timestamp to csv data file
    #         helper_functions.write_timestamps_to_csv(
    #             csv_directory_path=csv_data_direcory,
    #             experiment_id=experiment_id,
    #             bmg_filename=payload["bmg_data_output_name"],
    #             accurate_timestamp=run_info.steps[7].end_time,  # index 7 = bmg reading
    #         )
    #         # TESTING
    #         print("\t\t writing timestamp to csv")

    #         exp1_reading_num_in_plate += 1

    #         # bmg to inheco incubator
    #         edited_to_inheco_wf = helper_functions.replace_wf_node_names(
    #             workflow=bmg_to_run_incubator_wf,
    #             payload=payload
    #         )
    #         experiment_client.start_run(
    #             edited_to_inheco_wf,
    #             payload=payload,
    #             blocking=True,
    #             simulate=False,
    #         )
    #         # TESTING
    #         print(f"\t\tbmg to inheco")
    #         print(f"\t\tinheco node: {payload["incubator_node"]} @ {payload["incubator_location"]}, inc time = {payload['incubation_seconds']}")

    #         exp1_into_incubator_time = time.time()
    #         print(f"\t\texperiment 1 into incubator time: {exp1_into_incubator_time}")

    #         print("\n\tsleeping to incubate")
    #         if continue_exp1:
    #             print("\t\tcontinue exp 1 = True")
    #             while (time.time() - exp1_into_incubator_time) < exp1_variables["incubation_seconds"]:
    #                 print(f"will continue in... {int(exp1_variables["incubation_seconds"]-(time.time() - exp1_into_incubator_time))} seconds")
    #                 time.sleep(5)

    #     incubation_loop_num += 1

    # incubation_loop_num = 0  # reset inner loop number


    # # OUTER LOOP ACTIONS - TRANSFERS HANDLING -------------------------------------------------
    # """One loop in the transfers loop (outer loop, is roughly
    #     10 hours or 10 incubation loops (inner loops)"""

    # # testing
    # print(f"exp1 plate num: {exp1_plate_num}")
    # print(f"exp2 plate num: {exp2_plate_num}")


    # if continue_exp1:
    #     # TESTING
    #     print("\nTransfering exp 1 plate")

    #     # set up variables
    #     payload["ot2_node"] = exp1_variables["ot2_node"]
    #     payload["ot2_location"] = exp1_variables["ot2_old_plate_location"]
    #     payload["ot2_safe_path"] = exp1_variables["ot2_safe_path"]
    #     payload["stack"] = exp1_variables["new_stack"]
    #     payload["lid_location"] = exp1_variables["lid_location"]
    #     payload["tip_box_location"] = exp1_variables["tip_box_location"]
    #     payload["incubator_node"] = exp1_variables["incubator_node"]
    #     payload["incubator_location"] = exp1_variables["incubator_location"]
    #     payload["incubation_seconds"] = exp1_variables["incubation_seconds"]

    #     # inheco incubator to bmg (BUT REPLACE LID ON PF400 lidnest 3 narrow)

    #     # TESTING
    #     print("\n\tinheco incubator to bmg (BUT REPLACE LID ON PF400 lidnest 3 narrow)")
    #     timestamp_now = int(datetime.now().timestamp())
    #     payload["bmg_data_output_name"] = (
    #         f"{experiment_label}_{timestamp_now}_{experiment_id}_exp1_{exp1_plate_num}_{exp1_reading_num_in_plate}.txt"
    #     )
    #     edited_to_bmg_wf = helper_functions.replace_wf_node_names(
    #         workflow=incubator_to_run_bmg_PF400_LID_wf,
    #         payload=payload
    #     )
    #     run_info = experiment_client.start_run(
    #         edited_to_bmg_wf,
    #         payload=payload,
    #         blocking=True,
    #         simulate=False,
    #     )
    #     # TESTING
    #     print(f"\t\tinheco to bmg and read")
    #     print(f"\t\tinheco node: {payload['incubator_node']} @ {payload["incubator_location"]}")
    #     print(f"\t\tbmg data filename: {payload["bmg_data_output_name"]}")

    #     # write utc bmg timestamp to csv data file
    #     helper_functions.write_timestamps_to_csv(
    #         csv_directory_path=csv_data_direcory,
    #         experiment_id=experiment_id,
    #         bmg_filename=payload["bmg_data_output_name"],
    #         accurate_timestamp=run_info.steps[7].end_time,  # index 7 = bmg reading
    #     )
    #     # TESTING
    #     print("\t\t writing timestamp to csv")

    #     exp1_reading_num_in_plate += 1

    #     # bmg to OLD OT-2 location
    #     experiment_client.start_run(
    #         replace_ot2_old_wf.resolve(),
    #         payload=payload,
    #         blocking=True,
    #         simulate=False,
    #     )
    #     print(f"\n\t\tbmg to old ot2 location: {payload["ot2_node"]}, {payload["ot2_location"]}, {payload["ot2_safe_path"]}")  # TESTING

    #     # get a new plate from the stack
    #     payload["ot2_location"] = exp1_variables["ot2_new_plate_location"]   # NEEDED TO ADD IN DEMO!
    #     edited_get_new_plate_wf = helper_functions.replace_wf_node_names(
    #         workflow=get_new_plate_wf,
    #         payload=payload
    #     )
    #     experiment_client.start_run(
    #         edited_get_new_plate_wf,
    #         payload=payload,
    #         blocking=True,
    #         simulate=False,
    #     )
    #     # TESTING
    #     print(f"\t\tget a new plate from the stack: {payload["stack"]}, lid location: {payload["lid_location"]}")
    #     print(f"\t\tto ot2: {payload["ot2_node"]}, {payload["ot2_location"]}, {payload["ot2_safe_path"]}")

    #     # run ot2 inoculation protocol
    #     ot2_replacement_variables = helper_functions.collect_ot2_replacement_variables(payload)
    #     temp_ot2_file_str = helper_functions.generate_ot2_protocol(inoculate_protocol, ot2_replacement_variables)
    #     payload["current_ot2_protocol"] = temp_ot2_file_str

    #     edited_ot2_wf = helper_functions.replace_wf_node_names(
    #         workflow=run_ot2_wf,
    #         payload=payload
    #     )
    #     experiment_client.start_run(
    #         edited_ot2_wf,
    #         payload=payload,
    #         blocking=True,
    #         simulate=False,
    #     )
    #     # TESTING
    #     print("\n\t\trun ot2 inoculation protocol")
    #     print(f"\t\tot2: {payload["ot2_node"]}, {payload["ot2_location"]}, {payload["ot2_safe_path"]}")
    #     print(f"\t\ttip location: {payload["tip_box_location"]}")

    #     # increase variables
    #     exp1_plate_num += 1
    #     exp1_variables["tip_box_location"] += 1

    #     # reset variables if necessary
    #     exp1_reading_num_in_plate = 1
    #     if exp1_variables["tip_box_location"] == 12:
    #         exp1_variables["tip_box_location"] = 4

    #     # ot2 to bmg (new plate)
    #     payload["ot2_location"] = exp1_variables["ot2_new_plate_location"]
    #     timestamp_now = int(datetime.now().timestamp())
    #     payload["bmg_data_output_name"] = (
    #         f"{experiment_label}_{timestamp_now}_{experiment_id}_exp1_{exp1_plate_num}_{exp1_reading_num_in_plate}.txt"
    #     )
    #     run_info = experiment_client.start_run(
    #         ot2_to_run_bmg_wf.resolve(),
    #         payload=payload,
    #         blocking=True,
    #         simulate=False,
    #     )
    #     # TESTING
    #     print(f"\n\t\tnew plate ot2 to bmg: {payload["ot2_node"]}, {payload["ot2_location"]}, {payload["ot2_safe_path"]}")
    #     print(f"\t\tbmg filename: {payload["bmg_data_output_name"]}")

    #     exp1_reading_num_in_plate += 1

    #     # write utc bmg timestamp to csv data file
    #     helper_functions.write_timestamps_to_csv(
    #         csv_directory_path=csv_data_direcory,
    #         experiment_id=experiment_id,
    #         bmg_filename=payload["bmg_data_output_name"],
    #         accurate_timestamp=run_info.steps[4].end_time,  # index 4 = bmg reading
    #     )
    #     # TESTING
    #     print("\t\t writing timestamp to csv")

    #     # bmg to inheco incubator
    #     payload["incubator_node"] = exp1_variables["incubator_node"]  # redundant but feels safer
    #     payload["incubator_location"] = exp1_variables["incubator_location"]
    #     payload["incubation_seconds"] = exp1_variables["incubation_seconds"]
    #     edited_to_inheco_wf = helper_functions.replace_wf_node_names(
    #         workflow=bmg_to_run_incubator_wf,
    #         payload=payload
    #     )
    #     experiment_client.start_run(
    #         edited_to_inheco_wf,
    #         payload=payload,
    #         blocking=True,
    #         simulate=False,
    #     )
    #     # # TESTING
    #     print(f"\n\t\tbmg to inheco")
    #     print(f"\t\tinheco node: {payload["incubator_node"]} @ {payload["incubator_location"]}, inc time = {payload['incubation_seconds']}")

    #     exp1_into_incubator_time = time.time()
    #     print(f"\t\texperiment 1 into incubator time: {exp1_into_incubator_time}")

    #     # remove the old plate to trash stack
    #     payload["trash_stack"] = exp1_variables["trash_stack"]
    #     payload["ot2_location"] = exp1_variables["ot2_old_plate_location"]
    #     edited_old_to_trash_wf = helper_functions.replace_wf_node_names(
    #         workflow=remove_old_substrate_plate_wf,
    #         payload=payload
    #     )
    #     experiment_client.start_run(
    #         edited_old_to_trash_wf,
    #         payload=payload,
    #         blocking=True,
    #         simulate=False,
    #     )
    #     # TESTING
    #     print(f"\n\t\tremove old plate to trash stack")
    #     print(f"\t\tot2: {payload["ot2_node"]}, {payload["ot2_location"]}, {payload["ot2_safe_path"]}")
    #     print(f"\t\ttrash stack: {payload["trash_stack"]}, lid location: {payload["lid_location"]}")

    # # ANOTHER READNG/INCUBATION LOOP --------------------------------------------------------------------------
    # while incubation_loop_num < 2:

    #     if continue_exp1:
    #         # WFs: Transfer experiment 1 plate from incubator, to bmg, read, and return to incubator

    #         # TESTING
    #         print("\tEXP1: taking reading and returning to incubator")
    #         print(f"\n\t\tcontinue exp1?: {continue_exp1}")

    #         # update payload variables
    #         payload["ot2_location"] = exp1_variables["ot2_new_plate_location"]
    #         payload["lid_location"] = exp1_variables["lid_location"]
    #         payload["incubator_node"] = exp1_variables["incubator_node"]
    #         payload["incubator_location"] = exp1_variables["incubator_location"]
    #         payload["incubation_seconds"] = exp1_variables["incubation_seconds"]

    #         # inheco incubator to bmg
    #         timestamp_now = int(datetime.now().timestamp())
    #         payload["bmg_data_output_name"] = (
    #             f"{experiment_label}_{timestamp_now}_{experiment_id}_exp1_{exp1_plate_num}_{exp1_reading_num_in_plate}.txt"
    #         )
    #         edited_to_bmg_wf = helper_functions.replace_wf_node_names(
    #             workflow=incubator_to_run_bmg_wf,
    #             payload=payload
    #         )
    #         run_info = experiment_client.start_run(
    #             edited_to_bmg_wf,
    #             payload=payload,
    #             blocking=True,
    #             simulate=False,
    #         )

    #         # TESTING
    #         print(f"\t\tinheco to bmg and read")
    #         print(f"\t\tinheco node: {payload['incubator_node']} @ {payload["incubator_location"]}")
    #         print(f"\t\tbmg data filename: {payload['bmg_data_output_name']}")

    #         # write utc bmg timestamp to csv data file
    #         helper_functions.write_timestamps_to_csv(
    #             csv_directory_path=csv_data_direcory,
    #             experiment_id=experiment_id,
    #             bmg_filename=payload["bmg_data_output_name"],
    #             accurate_timestamp=run_info.steps[7].end_time,  # index 7 = bmg reading
    #         )
    #         # TESTING
    #         print("\t\t writing timestamp to csv")

    #         exp1_reading_num_in_plate += 1

    #         # bmg to inheco incubator
    #         edited_to_inheco_wf = helper_functions.replace_wf_node_names(
    #             workflow=bmg_to_run_incubator_wf,
    #             payload=payload
    #         )
    #         experiment_client.start_run(
    #             edited_to_inheco_wf,
    #             payload=payload,
    #             blocking=True,
    #             simulate=False,
    #         )
    #         # TESTING
    #         print(f"\t\tbmg to inheco")
    #         print(f"\t\tinheco node: {payload["incubator_node"]} @ {payload["incubator_location"]}, inc time = {payload['incubation_seconds']}")

    #         exp1_into_incubator_time = time.time()
    #         print(f"\t\texperiment 1 into incubator time: {exp1_into_incubator_time}")

    #         print("\n\tsleeping to incubate")
    #         if continue_exp1:
    #             print("\t\tcontinue exp 1 = True")
    #             while (time.time() - exp1_into_incubator_time) < exp1_variables["incubation_seconds"]:
    #                 print(f"will continue in... {int(exp1_variables["incubation_seconds"]-(time.time() - exp1_into_incubator_time))} seconds")
    #                 time.sleep(5)

    #     incubation_loop_num += 1

    # incubation_loop_num = 0 # reset inner loop number


    # # TRASH PLATE -----------------------------------------------------------------------------------------------------------
    # """means final incubaton cycle on experiment 1 plate is complete.
    #     Need to complete the final absorbance reading on the final
    #     plate in experiment 1."""

    # # TESTING
    # print(f"\nLAST EXP1 PLATE = {exp1_plate_num}")
    # continue_exp1 = False

    # # change variables
    # payload["lid_location"] = exp1_variables["lid_location"]
    # payload["incubator_node"] = exp1_variables["incubator_node"]
    # payload["incubator_location"] = exp1_variables["incubator_location"]
    # payload["incubation_seconds"] = exp1_variables["incubation_seconds"]
    # payload["trash_stack"] = exp1_variables["trash_stack"]

    # # inheco incubator to bmg
    # timestamp_now = int(datetime.now().timestamp())
    # payload["bmg_data_output_name"] = (
    #     f"{experiment_label}_{timestamp_now}_{experiment_id}_exp1_{exp1_plate_num}_{exp1_reading_num_in_plate}.txt"
    # )
    # edited_to_bmg_wf = helper_functions.replace_wf_node_names(
    #     workflow=incubator_to_run_bmg_wf,
    #     payload=payload
    # )
    # run_info = experiment_client.start_run(
    #     edited_to_bmg_wf,
    #     payload=payload,
    #     blocking=True,
    #     simulate=False,
    # )
    # # TESTING
    # print(f"\t\tinheco to bmg and read")
    # print(f"\t\tinheco node: {payload['incubator_node']} @ {payload["incubator_location"]}")
    # print(f"\t\tbmg data filename: {payload['bmg_data_output_name']}")

    # # write utc bmg timestamp to csv data file
    # helper_functions.write_timestamps_to_csv(
    #     csv_directory_path=csv_data_direcory,
    #     experiment_id=experiment_id,
    #     bmg_filename=payload["bmg_data_output_name"],
    #     accurate_timestamp=run_info.steps[7].end_time,  # index 7 = bmg reading
    # )
    # # TESTING
    # print("\t\t writing timestamp to csv")

    # exp1_reading_num_in_plate += 1
    # print(f"\t\texperiment 1 into incubator time: {exp1_into_incubator_time}")

    # # bmg to trash stack
    # experiment_client.start_run(
    #     at_end_bmg_to_trash_wf.resolve(),
    #     payload=payload,
    #     blocking=True,
    #     simulate=False,
    # )
    # # TESTING
    # print("\t\tbmg to trash stack")
    # print(f"\t\tlid location: {payload["lid_location"]}")
    # print(f"\t\ttrash stack: {payload["trash_stack"]}")

    # exp1_plate_num += 1  # important


if __name__ == "__main__":
    main()
