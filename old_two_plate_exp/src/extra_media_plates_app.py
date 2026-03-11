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

    # capture the expriment ID
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
    prep_dispense_media_protocol = protocol_directory / "prep_dispense_media.py"

    # experiment 1: incubation = 1 hr cycles, transfers every 10 hours
    exp1_variables = {
        "incubation_seconds": 720,   # TESTING
        "lid_location": "lidnest1",
        "ot2_node": "ot2biobeta",
        "ot2_new_plate_location": "ot2biobeta_deck1_wide", 
        "ot2_old_plate_location": "ot2biobeta_deck3_wide",
        "ot2_safe_path": "safe_path_ot2biobeta", 
        "incubator_node": "inheco_devID2_floor0",
        "incubator_location": "inheco_devID2_floor0_nest",
        "tip_box_location": 4,
        "new_stack": "stack1",
        "trash_stack": "stack4",
    }

    # experiment 2: incubation = 2 hr cycles, transfers every 20 hours
    exp2_variables = {
        "incubation_seconds": 200,   # TESTING
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

    # # payload variables for ot2biobeta
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


    # # payload variables for ot2bioalpha
    # payload = {   
    #     "ot2_node": exp2_variables["ot2_node"],
    #     "ot2_location": exp2_variables["ot2_new_plate_location"],
    #     "ot2_safe_path": exp2_variables["ot2_safe_path"],
    #     "tip_box_location": exp2_variables["tip_box_location"],
    #     "stack": exp2_variables["new_stack"],
    #     "lid_location": exp2_variables["lid_location"],
    #     "incubator_node": exp2_variables["incubator_node"],
    #     "incubator_location": exp2_variables["incubator_location"],
    #     "incubation_seconds": exp2_variables["incubation_seconds"],  
    #     "trash_stack": exp2_variables["trash_stack"],
    #     "current_ot2_protocol": None,    # defined later
    #     "use_existing_resources": False,
    #     "bmg_assay_name": "NIDHI", 
    # }


    # EXPERIMENT STEPS: ------------------------------------------------------------------------------
    """Before running this experiment, extra substrate plates should be prepped 
        by running extra_media_plates_app.py. The prepped plates for experiment 1 should 
        be placed in ScoClops stack 1, and the prepped plates for experiment 2 should be
        placed in SciClops stack2. The OT-2 deck of ot2biobeta should be prepped for 
        first_inoculate_both.py"""


    payload["current_ot2_protocol"] = str(prep_dispense_media_protocol)
    edited_ot2_wf = helper_functions.replace_wf_node_names(
        workflow = run_ot2_wf, 
        payload = payload
    )
    experiment_client.start_run(   
        edited_ot2_wf,
        payload=payload,
        blocking=True,
        simulate=False,
    )



if __name__ == "__main__":
    main()
