from opentrons import protocol_api
import itertools
from opentrons.protocol_api import SINGLE
import ast


metadata = {
    'protocolName': 'Turn on temp blocks Ot2',
    'author': 'LDRD team ',
    'description': 'Detection and Dilution for Protein Design reagents',
}

requirements = {"robotType": "OT-2", "apiLevel": "2.20"}


config = {
    # 'combinations': [[18,10,2],[11,19,3],[4,20,12],[21,13,5]], # 1-indexed source well numbers (kept for total calculation)
    # 'combinations': [[1], [2, 2], [3, 3], [4, 4]],
    'combinations': "$combinations",
    'use_combinations': "$use_combinations",
    'non_combinatorial_sources': "$non_combinatorial_sources",
    'tips_used': 0,

    'temperature' : 4,

    'heater_shaker_temp': 37,     # °C for heater/shaker
    'shaking_duration': 180,      # minutes (3 hours) for shaking (CFPS)
    'shaking_speed': 200,

    'cfps_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'diluted_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'tip_rack_type_20_01': 'opentrons_96_filtertiprack_20ul',
    'reagent_plate_type': 'nest_12_reservoir_15ml',

    'temp_module_01_position': 'C1',
    'temp_module_02_position': 'C3',
    'cfps_plate_position': 'C1',
    'diluted_plate_position': 'C3',
    'reagent_plate_position': 'A1',
    'tip_rack_position_20_01': 'D3',
}

def run(protocol: protocol_api.ProtocolContext):

    temp_mod1 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_01_position'])
    temp_adapter1 = temp_mod1.load_adapter("opentrons_96_well_aluminum_block")

    temp_mod2 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_02_position'])
    temp_adapter2 = temp_mod2.load_adapter("opentrons_96_well_aluminum_block")

    # Set temperature
    temp_mod1.set_temperature(config['temperature'])
    temp_mod2.set_temperature(config['temperature'])