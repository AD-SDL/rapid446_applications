from opentrons import protocol_api
import itertools
from opentrons.protocol_api import SINGLE


metadata = {
    'protocolName': 'Protein Design Fdglu rmf removal',
    'author': 'LDRD team ',
    'description': 'PCR for Protein Design reagents',
    'source': 'FlexAS/pd_pcr_81.py'
}

requirements = {"robotType": "OT-2", "apiLevel": "2.20"}


# Protocol Configuration
config = {
    # 'combinations': [[1], [2], [3], [4]],
    'combinations': "$combinations",
    'use_combinations': bool("$use_combinations"),
    'non_combinatorial_sources': "$non_combinatorial_sources",

    # Temperature settings
    'temperature': 4,  # °C

    'cfps_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'reagent_plate_type': 'nest_12_reservoir_15ml',
    'tip_rack_type_20_01': 'opentrons_96_filtertiprack_20ul',
    'pipette_type_20': 'p20_single_gen2',
    'pipette_type_20_multi': 'p20_multi_gen2',

    # Deck positions
    'temp_module_01_position': 'C1',
    'temp_module_02_position': 'C3',
    'cfps_plate_position': 'C1',
    'diluted_plate_position': 'C3',
    'reagent_plate_position': 'A1',
    'tip_rack_position_20_01': 'D3',
    'tips_used': 0,
}


def remove_rmf(protocol, cfps_plate, reagent_plate, pipette, config):

    wells_to_remove = [37, 38, 39]
    dest_well = reagent_plate.wells()[11] # last col of reagent plate
    for well in wells_to_remove:
        source_well = cfps_plate.wells()[well]
        pipette.transfer(
        27.6,
        source_well,
        dest_well,
        new_tip='always',  # Use fresh tip for each transfer
        )
        config["tips_used"]+=2



def run(protocol: protocol_api.ProtocolContext):
    # Load temperature module and adapter
    temp_mod1 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_01_position'])
    temp_adapter1 = temp_mod1.load_adapter("opentrons_96_well_aluminum_block")

    temp_mod2 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_02_position'])
    temp_adapter2 = temp_mod2.load_adapter("opentrons_96_well_aluminum_block")

    # Set temperature
    temp_mod1.set_temperature(config['temperature']) #TODO: make seperate, or just set earlier, only 1 hour with plate
    temp_mod2.set_temperature(config['temperature'])

    cfps_plate = temp_adapter1.load_labware(config['cfps_plate_type'])
    cfps_plate.set_offset(x=0.4, y=0.4, z=0.0)

    reagent_plate = protocol.load_labware(config['reagent_plate_type'], config['reagent_plate_position'])

    tiprack_20_1 = protocol.load_labware(
        load_name=config['tip_rack_type_20_01'], location=config['tip_rack_position_20_01']
    )

    p50 = protocol.load_instrument('p20_multi_gen2', mount='right', tip_racks=[tiprack_20_1])
    p50s = protocol.load_instrument('p20_single_gen2', mount='left', tip_racks=[tiprack_20_1])

    p50.configure_nozzle_layout(style='COLUMN', start='A1', tip_racks=[tiprack_20_1])



    remove_rmf(protocol=protocol,
               cfps_plate=cfps_plate,
               reagent_plate=reagent_plate,
               pipette=p50s,
               config = config)
    
    protocol.comment(f"tips used: {config['tips_used']}")

