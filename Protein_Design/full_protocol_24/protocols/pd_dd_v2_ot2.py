from opentrons import protocol_api
import itertools
from opentrons.protocol_api import SINGLE
import ast



metadata = {
    'protocolName': 'Protein Design Detection and Dilution',
    'author': 'LDRD team ',
    'description': 'Detection and Dilution for Protein Design reagents',
}

requirements = {"robotType": "OT-2", "apiLevel": "2.20"}


# Protocol Configuration
config = {
    # Combinatorial mixing
    'number_of_pcr_samples': 6,
    'pcr_sample_volume': 2,
    'water_volume': 18,
    # 'combinations': [[18,10],[11,19],[4,20],[21,13]],
    # 'combinations': [[1], [2, 2], [3, 3], [4, 4]],
    'combinations': "$combinations",
    'use_combinations': bool("$use_combinations"),
    'non_combinatorial_sources': "$non_combinatorial_sources",
    "num_controls": 5,
    'control_volume': 20,

    # Master mix and reagent settings
    'water_well': 1,
    'columns_to_move_for_dilute': 6,
    'control_volume': 20,
    'pcr_plate_control_column': 5,
    'tips_used_50': 0,


    # Temperature settings
    'temperature': 4,  # °C

    # Labware
    'pcr_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'diluted_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'reagent_plate_type': 'nest_12_reservoir_15ml',
    'tip_rack_type_20_01': 'opentrons_96_filtertiprack_20ul',
    'pipette_type_20': 'p20_single_gen2',
    'pipette_type_20_multi': 'p20_multi_gen2',
    'controls_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',

    # Deck positions
    'temp_module_01_position': 'C1',
    'temp_module_02_position': 'C3',
    'pcr_plate_position': 'C1',
    'diluted_plate_position': 'C3',
    'reagent_plate_position': 'A1',
    'tip_rack_position_20_01': 'D3',
    'controls_plate_position': 'D1',
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


def water_to_pcr_dilution_wells(protocol, diluted_pcr, reagent_plate, pipette, config):
    water_volume = config['water_volume']
    # combinations = config['combinations']
    # num_samples = calculate_total_combinations(combinations)
    if config['use_combinations'] is True:
        combinations = config['combinations']
        total_combinations = calculate_total_combinations(combinations)
        # Generate all possible combinations
        all_combinations = generate_all_combinations(combinations)
    else:
        all_combinations = config['non_combinatorial_sources']
        total_combinations = len(all_combinations)
    num_samples = total_combinations
    columns_needed = (num_samples + 7) // 8
    columns_to_move = config['columns_to_move_for_dilute']
    water_well = config['water_well']
    source_well = reagent_plate.wells()[water_well - 1]
    pipette.pick_up_tip()
    for col_idx in range(columns_needed):
        dest_well = diluted_pcr.columns()[col_idx]
        protocol.comment(f"\nTransferring to destination well {dest_well}:")
        pipette.transfer(
            water_volume,
            source_well,
            dest_well,
            new_tip='never',  # Use fresh tip for each transfer
            # mix_after = (3, 20)
        )
    pipette.drop_tip()
    config['tips_used_50']+=8


def pcr_to_water(protocol, pcr_plate, diluted_pcr, pipette, config):
    pcr_sample_volume = config['pcr_sample_volume']
    # combinations = config['combinations']
    # num_samples = calculate_total_combinations(combinations)
    if config['use_combinations'] is True:
        combinations = config['combinations']
        total_combinations = calculate_total_combinations(combinations)
        # Generate all possible combinations
        all_combinations = generate_all_combinations(combinations)
    else:
        all_combinations = config['non_combinatorial_sources']
        total_combinations = len(all_combinations)
    num_samples = total_combinations
    columns_needed = (num_samples + 7) // 8
    columns_to_move = config['columns_to_move_for_dilute']

    for col_idx in range(columns_needed):
        dest_well = diluted_pcr.columns()[col_idx]
        source_well = pcr_plate.columns()[col_idx]
        protocol.comment(f"\nTransferring to destination well {dest_well}:")
        pipette.transfer(
            pcr_sample_volume,
            source_well,
            dest_well,
            new_tip='always',  # Use fresh tip for each transfer
            mix_after = (3, 20)
        )
        config['tips_used_50']+=8

def controls_to_pcr(protocol, diluted_pcr, controls_plate, pipette, config): #TODO: make sure controls in column 4
    control_volume = config['control_volume']
    control_column = config['pcr_plate_control_column']
    # combinations = config['combinations']
    # num_samples = calculate_total_combinations(combinations)
    if config['use_combinations'] is True:
        combinations = config['combinations']
        total_combinations = calculate_total_combinations(combinations)
        # Generate all possible combinations
        all_combinations = generate_all_combinations(combinations)
    else:
        all_combinations = config['non_combinatorial_sources']
        total_combinations = len(all_combinations)
    num_samples = total_combinations
    columns_needed = (num_samples + 7) // 8
    source_well = controls_plate.columns()[0]
    dest_well = diluted_pcr.columns()[columns_needed]
    pipette.transfer(
        control_volume,
        source_well,
        dest_well,
        new_tip = "always"
    )
    config['tips_used_50']+=8

# def controls_to_pcr(protocol, diluted_pcr, controls_plate, pipette, config):
#     control_volume = config['control_volume']
#     num_controls = config['num_controls']
#     control_column = config['pcr_plate_control_column']

#     starting_dest_well = 88 # last col #TODO hardcoded

#     for well in range(1, num_controls + 1):
#         source_well = controls_plate.wells()[well-1]
#         dest_well = diluted_pcr.wells()[starting_dest_well]
#         pipette.transfer(
#             control_volume,
#             source_well,
#             dest_well,
#             new_tip='always',  # Use fresh tip for each transfer
#         )
#         starting_dest_well+=1

def run(protocol: protocol_api.ProtocolContext):
    combinations_string = config['combinations']
    combinations = ast.literal_eval(combinations_string)
    config['combinations'] = combinations
    non_combinations_string = config['non_combinatorial_sources']
    noncombinations = ast.literal_eval(non_combinations_string)
    config['non_combinatorial_sources'] = noncombinations
    # Load temperature module and adapter
    temp_mod_1 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_01_position'])
    temp_adapter_1 = temp_mod_1.load_adapter("opentrons_96_well_aluminum_block")

    temp_mod_2 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_02_position'])
    temp_adapter_2 = temp_mod_2.load_adapter("opentrons_96_well_aluminum_block")

    # Set temperature
    # temp_mod_1.set_temperature(config['temperature']) #TODO: make seperate, or just set earlier, only 1 hour with plate
    # temp_mod_2.set_temperature(config['temperature']) #TODO: make seperate, or just set earlier, only 1 hour with plate


    # chute = protocol.load_waste_chute()

    pcr_plate = temp_adapter_1.load_labware(config['pcr_plate_type'])
    pcr_plate.set_offset(x=0.4, y=0.4, z=0.0)

    diluted_plate = temp_adapter_2.load_labware(config['diluted_plate_type'])
    diluted_plate.set_offset(x=0.7, y=0.30, z=0.2)

    reagent_plate = protocol.load_labware(config['reagent_plate_type'], config['reagent_plate_position'])
    controls_plate = protocol.load_labware(config['controls_plate_type'], config['controls_plate_position'])

    tiprack_20_1 = protocol.load_labware(
        load_name=config['tip_rack_type_20_01'], location=config['tip_rack_position_20_01']
    )

    p50 = protocol.load_instrument('p20_multi_gen2', mount='right', tip_racks=[tiprack_20_1])
    p50s = protocol.load_instrument('p20_single_gen2', mount='left', tip_racks=[tiprack_20_1])

    p50.configure_nozzle_layout(style='COLUMN', start='A1', tip_racks=[tiprack_20_1])

    # p50.starting_tip = tiprack_20_1.well('A8')


    water_to_pcr_dilution_wells(protocol=protocol,
                                diluted_pcr=diluted_plate,
                                reagent_plate=reagent_plate,
                                pipette=p50,
                                config=config)

    pcr_to_water(protocol=protocol,
                 pcr_plate=pcr_plate,
                 diluted_pcr=diluted_plate,
                 pipette=p50,
                 config=config)


    controls_to_pcr(protocol=protocol,
                    diluted_pcr=diluted_plate,
                    controls_plate=controls_plate,
                    pipette=p50,
                    config=config)


    protocol.comment(f"tips used 50: {config['tips_used_50']}")