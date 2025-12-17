from opentrons import protocol_api
from opentrons.protocol_api import SINGLE

metadata = {
    'protocolName': 'move A4 to B2',
    'author': 'Abe Stroka',
    'description': 'Automated Golden Gate Assembly using OT-Flex',
}

requirements = {"robotType": "Flex", "apiLevel": "2.20"}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    # source_plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 'B1')
    pcr_plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', 'B4')
    mastermix_tube = protocol.load_labware('nest_12_reservoir_15ml', 'B3') #TODO change
    water_reservoir = protocol.load_labware('nest_12_reservoir_15ml', 'A1')
    temp_mod = protocol.load_module(module_name="temperature module gen2", location="C1")
    temp_adapter = temp_mod.load_adapter("opentrons_96_well_aluminum_block")
    # dna = temp_adapter.load_labware('nest_96_wellplate_100ul_pcr_full_skirt')

    tiprack_50 = protocol.load_labware(
        load_name="opentrons_flex_96_tiprack_50ul", location="A2",
    )

    # tiprack_200 = protocol.load_labware(
    #     load_name="opentrons_flex_96_tiprack_200ul", location="A3"
    # )



    # Pipettes
    p50 = protocol.load_instrument('flex_8channel_50', mount='right', tip_racks=[tiprack_50])
    # p1000 = protocol.load_instrument('flex_8channel_1000', mount='left', tip_racks=[tiprack_200])

    # p50.configure_nozzle_layout(style=SINGLE, start='A1', tip_racks=[tiprack_50])
    # p1000.configure_nozzle_layout(style=SINGLE, start='A1', tip_racks=[tiprack_200])


    # load trash bin
    # _ = protocol.load_trash_bin("D1")
    chute = protocol.load_waste_chute()

    protocol.move_labware(labware=pcr_plate, new_location=temp_adapter, use_gripper=True)