#!/usr/bin/env python3

"""Golden Gate Experiment"""

from pathlib import Path

from wei import ExperimentClient
from wei.types.experiment_types import CampaignDesign, ExperimentDesign


def main() -> None:
    """Runs the Substrate Experiment Application"""

    # INITIAL EXPERIMENT SETUP ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    # define the ExperimentDesign object that will be used to register the experiment
    experiment_design = ExperimentDesign(
        experiment_name="GG_Experiment",
        experiment_description="Golden Gate Experiment",
    )

    # define a campaign object (useful if we want to group many of these substrate experiments together)
    campaign = CampaignDesign(
        campaign_name="ProteinDesign_Campaign",
        campaign_description="Protein Design Campaign",
    )

    # define the experiment client object that will communicate with the WEI server
    experiment_client = ExperimentClient(
        server_host="localhost",
        server_port="8000",
        experiment=experiment_design,
        campaign=campaign,
    )

    # DEFINING PATHS AND VARIABLES -------------------------------

    # directory path(s)
    app_directory = Path(__file__).parent.parent
    wf_directory = app_directory / "workflows"
    wf_run_instrument_directory = wf_directory / "run_instrument"
    wf_transfers_directory = wf_directory / "transfers"
    protocol_directory = app_directory / "protocols"

    # workflow paths (run instruments)
    run_thermocycler_wf = wf_run_instrument_directory / "run_thermocycler.yaml"
    run_flex_wf = wf_run_instrument_directory / "run_flex.yaml"

    # # workflow paths (set up and tear down related)

    # # workflow paths (pf400 transfers)
    remove_lid_move_to_flex = wf_transfers_directory / "remove_lid_move_to_flex.yaml"
    flex_to_thermocycler_wf = wf_transfers_directory / "flex_to_thermo_wf.yaml"
    thermocycler_to_flex_wf = wf_transfers_directory / "thermo_to_flex_wf.yaml"
    flexA_sealer_flexA_wf = wf_transfers_directory / "flexA_sealer_flexA_wf.yaml"
    flexA_sealer_wait_wf = wf_transfers_directory / "flexA_sealer_wf.yaml"

    # protocol paths (for OT-Flex)
    # run_gg = protocol_directory / "gg_flex.py"
    run_gg = protocol_directory / "pd_golden_gate_81.py"
    cool_block_protocol = protocol_directory / "cool_block_to_4.py"

    move_gg_to_staging_protocol = protocol_directory / "move_to_staging_C1_A4.py"
    move_source_to_staging_protocol = protocol_directory / "move_to_staging_B1_A4.py"
    move_dest_to_staging_protocol = protocol_directory / "move_to_staging_B2_A4.py"
    move_from_staging_protocol = protocol_directory / "move_from_staging_A4_C1.py"
    move_A4_B1_protocol = protocol_directory / "move_from_staging_A4_B1.py"
    move_B4_C1_protocol = protocol_directory / "move_from_staging_B4_C1.py"
    #TODO: possibly break up in future when running multiple plates, ie make large quantity of master mix and use repeatedly

    payload = {"current_flex_protocol": str(cool_block_protocol)}

    # # important variables
    # experiment_client.start_run(
    #     run_flex_wf.resolve(),
    #     payload=payload,
    #     blocking=True,
    #     simulate=False,
    # )

    payload = {"current_flex_protocol": str(move_A4_B1_protocol)}

    # important variables
    experiment_client.start_run(
        run_flex_wf.resolve(),
        payload=payload,
        blocking=True,
        simulate=False,
    )


    payload = {"current_flex_protocol": str(move_B4_C1_protocol)}

    # important variables
    experiment_client.start_run(
        run_flex_wf.resolve(),
        payload=payload,
        blocking=True,
        simulate=False,
    )

    # EXPERIMENT STEPS: ----------------------------------------------

    payload = {"current_flex_protocol": str(run_gg)}
    #run golden gate experiement on flex
    experiment_client.start_run(
        run_flex_wf.resolve(),
        payload=payload,
        blocking=True,
        simulate=False,
    )

    #seal and return source plate
    payload = {"current_flex_protocol": str(move_source_to_staging_protocol)}

    experiment_client.start_run(
        run_flex_wf.resolve(),
        payload=payload,
        blocking=True,
        simulate=False,
    )

    experiment_client.start_run(
        flexA_sealer_flexA_wf.resolve(),
        payload=payload,
        blocking=True,
        simulate=False,
    )

    payload = {"current_flex_protocol": str(move_A4_B1_protocol)}

    # important variables
    experiment_client.start_run(
        run_flex_wf.resolve(),
        payload=payload,
        blocking=True,
        simulate=False,
    )

    #seal destination plate (B2) and leave for thermocycling #TODO add thermocycler use

    payload = {"current_flex_protocol": str(move_gg_to_staging_protocol)}

    experiment_client.start_run(
        run_flex_wf.resolve(),
        payload=payload,
        blocking=True,
        simulate=False,
    )
    experiment_client.start_run(
        flex_to_thermocycler_wf.resolve(),
        payload=payload,
        blocking=True,
        simulate=False,
    )


    # # #run thermo
    # # TODO: figure out biometra protocol number and app closure issue
    # # experiment_client.start_run(
    # #     run_thermocycler_wf.resolve(),
    # #     payload=payload,
    # #     blocking=True,
    # #     simulate=False,
    # # )


    # # move thermo to flex
    # experiment_client.start_run(
    #     thermocycler_to_flex_wf.resolve(),
    #     payload=payload,
    #     blocking=True,
    #     simulate=False,
    # )

    # payload = {"current_flex_protocol": str(move_from_staging_protocol)}

    # # #move from flex staging A back to flex B2
    # experiment_client.start_run(
    #     run_flex_wf.resolve(),
    #     payload=payload,
    #     blocking=True,
    #     simulate=False,
    # )

    #TODO: if no thermo, peel and return to flex



if __name__ == "__main__":
    main()
