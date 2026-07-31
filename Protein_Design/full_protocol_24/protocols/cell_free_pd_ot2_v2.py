from opentrons import protocol_api
import itertools
from opentrons.protocol_api import SINGLE


metadata = {
    'protocolName': 'Protein Design Cell Free Ot2',
    'author': 'LDRD team ',
    'description': 'Detection and Dilution for Protein Design reagents',
}

requirements = {"robotType": "OT-2", "apiLevel": "2.20"}


config = {
    # 'combinations': [[18,10,2],[11,19,3],[4,20,12],[21,13,5]], # 1-indexed source well numbers (kept for total calculation)
    # 'combinations': [[1], [2, 2], [3, 3], [4, 4]],
    'combinations': "$combinations",
    'use_combinations': bool("$use_combinations"),
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

def calculate_total_combinations(combinations):
    """Calculate total number of combinations without generating them"""
    total = 1
    for sublist in combinations:
        total *= len(sublist)
    return total


def generate_all_combinations(combinations):
    """Generate all possible combinations from the jagged array"""
    return list(itertools.product(*combinations))

def diluted_pcr_to_cfps(protocol, diluted_pcr_plate, cfps_plate, pipette, config):
    # add 2ul of diluted dna to cfps plate
    # can probably just 8 channel all through, check with others
    combinations = config['combinations']
    num_samples = calculate_total_combinations(combinations)
    columns_needed = (num_samples + 7) // 8
    columns_needed = columns_needed
    for i in range(columns_needed+1):
        source_well = diluted_pcr_plate.columns()[i]
        dest_well = cfps_plate.columns()[i]
        pipette.transfer(
            2.4,
            source_well,
            dest_well,
            new_tip='always',  # Use fresh tip for each transfer
            mix_before = (3, 10),
            mix_after = (3, 15)
        )

        config['tips_used']+=8


def run(protocol: protocol_api.ProtocolContext):
    # Load temperature module and adapter
    temp_mod1 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_01_position'])
    temp_adapter1 = temp_mod1.load_adapter("opentrons_96_well_aluminum_block")

    temp_mod2 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_02_position'])
    temp_adapter2 = temp_mod2.load_adapter("opentrons_96_well_aluminum_block")

    # Set temperature
    # temp_mod1.set_temperature(config['temperature']) #TODO: make seperate, or just set earlier, only 1 hour with plate
    # temp_mod2.set_temperature(config['temperature']) #TODO: make seperate, or just set earlier, only 1 hour with plate

    cfps_plate = temp_adapter1.load_labware(config['cfps_plate_type'])
    cfps_plate.set_offset(x=0.4, y=0.4, z=0.0)

    diluted_plate = temp_adapter2.load_labware(config['diluted_plate_type'])
    diluted_plate.set_offset(x=0.7, y=0.30, z=0.2)

    reagent_plate = protocol.load_labware(config['reagent_plate_type'], config['reagent_plate_position'])

    tiprack_20_1 = protocol.load_labware(
        load_name=config['tip_rack_type_20_01'], location=config['tip_rack_position_20_01']
    )

    p50 = protocol.load_instrument('p20_multi_gen2', mount='right', tip_racks=[tiprack_20_1])
    p50s = protocol.load_instrument('p20_single_gen2', mount='left', tip_racks=[tiprack_20_1])

    p50.configure_nozzle_layout(style='COLUMN', start='A1', tip_racks=[tiprack_20_1])

    p50.flow_rate.aspirate = 20
    p50.flow_rate.dispense = 20

    diluted_pcr_to_cfps(protocol=protocol,
                        diluted_pcr_plate=diluted_plate,
                        cfps_plate=cfps_plate,
                        pipette=p50,
                        config=config)
    
    protocol.comment(f"tips used: {config['tips_used']}")