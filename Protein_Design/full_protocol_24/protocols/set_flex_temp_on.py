from opentrons import protocol_api
import itertools
from opentrons.protocol_api import SINGLE
import ast


metadata = {
    'protocolName': 'Turn temp blocks on Flex',
    'author': 'LDRD team ',
    'description': 'CFPS plate setup from PCR templates and standards followed by CFPS on the deck',
    'source': 'FlexAS/pd_cfps_81.py'
}

requirements = {"robotType": "Flex", "apiLevel": "2.20"}


config = {
    # 'combinations': [[18,10,2],[11,19,3],[4,20,12],[21,13,5]], # 1-indexed source well numbers (kept for total calculation)
    # 'combinations': [[1], [2, 2], [3, 3], [4, 4]],
    # 'combinations': [[1], [2, 2], [3, 3], [4, 4]],
    # 'use_combinations': False,
    # 'non_combinatorial_sources': [[1, 10, 3, 28], [5, 6, 7, 40], [9, 10, 3, 28], [5, 6, 7, 8], [9, 10, 3, 28], [5, 6, 7, 40], [25, 6, 7, 28], [9, 10, 3, 4], [1, 10, 3, 4], [5, 6, 7, 28], [5, 6, 7, 28], [9, 10, 3, 28], [5, 6, 7, 8], [25, 6, 7, 28], [5, 6, 7, 40], [9, 10, 3, 4], [1, 10, 3, 4], [1, 10, 3, 28], [5, 6, 7, 28], [5, 6, 7, 8], [1, 10, 3, 4], [25, 6, 7, 28], [9, 10, 3, 4], [1, 10, 3, 28]],
    'combinations': "$combinations",
    'use_combinations': "$use_combinations",
    'non_combinatorial_sources': "$non_combinatorial_sources",
    'temperature' : 4,
    'tips_used_1000': 0,
    'tips_used_50': 0,

    'heater_shaker_temp': 37,     # °C for heater/shaker
    'shaking_duration': 180,      # minutes (3 hours) for shaking (CFPS)
    'shaking_speed': 200,

    'rmf_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'cfps_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'tip_rack_type_50_01': 'opentrons_flex_96_filtertiprack_50ul',
    # 'tip_rack_type_50_02': 'opentrons_flex_96_filtertiprack_50ul',
    'tip_rack_type_200_01': 'opentrons_flex_96_filtertiprack_200ul',
    'reagent_plate_type': 'nest_12_reservoir_15ml',
    'pcr_adapter_type': 'opentrons_96_pcr_adapter',

    'rmf_plate_position': 'B1',
    'cfps_plate_position': 'C1',
    'temp_module_01_position': 'B1',
    'temp_module_02_position': 'C1',
    'tip_rack_position_50_01': 'A2',
    'tip_rack_position_200_01': 'A1',
    'reagent_plate_position': 'D2',
    'shaker_module_position': 'D1',

}


def run(protocol: protocol_api.ProtocolContext):

    temp_mod1 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_01_position'])
    temp_adapter1 = temp_mod1.load_adapter("opentrons_96_well_aluminum_block")

    temp_mod2 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_02_position'])
    temp_adapter2 = temp_mod2.load_adapter("opentrons_96_well_aluminum_block")

    # Set temperature
    temp_mod1.set_temperature(config['temperature'])
    temp_mod2.set_temperature(config['temperature']) 

    # shaker_mod = protocol.load_module(module_name="heaterShakerModuleV1", location=config['shaker_module_position'])
    # shaker_adapter = shaker_mod.load_adapter(config['pcr_adapter_type'])

    chute = protocol.load_waste_chute()