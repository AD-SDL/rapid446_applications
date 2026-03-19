from opentrons import protocol_api
import itertools
from opentrons.protocol_api import SINGLE


metadata = {
    'protocolName': 'Protein Design Detection and Dilution on Flex',
    'author': 'LDRD team ',
    'description': 'Detection and Dilution for Protein Design reagents',
}

requirements = {"robotType": "Flex", "apiLevel": "2.20"}


config = {
    # Combinatorial mixing
    'number_of_pcr_samples': 6,
    'pcr_sample_volume': 2,
    'water_volume': 18,
    'combinations': [[18,10,2],[11,19,3],[4,20,12],[21,13,5]],
    "num_controls": 5,

    # Master mix and reagent settings
    'water_well': 1,
    'columns_to_move_for_dilute': 6,
    'control_volume': 20,
    'pcr_plate_control_column': 1,


    # Temperature settings
    'temperature': 4,  # °C

    # Labware
    'pcr_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'sybrgreen_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'reagent_plate_type': 'nest_12_reservoir_15ml',
    'tip_rack_type_20_01': 'opentrons_96_filtertiprack_20ul',
    'pipette_type_20': 'p20_single_gen2',
    'pipette_type_20_multi': 'p20_multi_gen2',
    'controls_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',

    # Deck positions
    'temp_module_01_position': 'B1',
    'temp_module_02_position': 'C1',
    'pcr_plate_position': 'C1',
    'sybrgreen_plate_position': 'C2',
    'reagent_plate_position': 'D2',
    'tip_rack_position_20_01': 'D3',
    'controls_plate_position': 'B1',
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


def sybrgreen_to_dest(protocol, reagent_plate, sybrgreen_plate, pipette, config):
    sybrgreen_volume = config['sybrgreen_volume'] / 4
    # num_samples = config["number_of_pcr_samples"]
    combinations = config['combinations']
    num_samples = calculate_total_combinations(combinations)
    columns_needed = (num_samples + 7) // 8
    columns_needed = columns_needed+1
    sybrgreen_well = reagent_plate.wells()[config['sybrgreen_well'] - 1]
    pipette.pick_up_tip()
    # first 50
    for col_idx in range(columns_needed):
        dest_well = sybrgreen_plate.columns()[col_idx]
        protocol.comment(f"\nTransferring to destination well {dest_well}:")
        pipette.transfer(
            sybrgreen_volume,
            sybrgreen_well,
            dest_well,
            new_tip='never',  # Use fresh tip for each transfer
        )
    # 100
    for col_idx in range(columns_needed):
        dest_well = sybrgreen_plate.columns()[col_idx]
        protocol.comment(f"\nTransferring to destination well {dest_well}:")
        pipette.transfer(
            sybrgreen_volume,
            sybrgreen_well,
            dest_well,
            new_tip='never',  # Use fresh tip for each transfer
        )
    # change well!
    sybrgreen_well = reagent_plate.wells()[config['sybrgreen_well']]
    # 150
    for col_idx in range(columns_needed):
        dest_well = sybrgreen_plate.columns()[col_idx]
        protocol.comment(f"\nTransferring to destination well {dest_well}:")
        pipette.transfer(
            sybrgreen_volume,
            sybrgreen_well,
            dest_well,
            new_tip='never',  # Use fresh tip for each transfer
        )
    #200
    for col_idx in range(columns_needed):
        dest_well = sybrgreen_plate.columns()[col_idx]
        protocol.comment(f"\nTransferring to destination well {dest_well}:")
        pipette.transfer(
            sybrgreen_volume,
            sybrgreen_well,
            dest_well,
            new_tip='never',  # Use fresh tip for each transfer
        )
    pipette.drop_tip()





def pcr_to_dest(protocol, pcr_plate, sybrgreen_plate, pipette, config):
    pcr_sample_volume = config['pcr_sample_volume']
    # num_samples = config["number_of_pcr_samples"]
    combinations = config['combinations']
    num_samples = calculate_total_combinations(combinations)
    columns_needed = (num_samples + 7) // 8

    for col_idx in range(columns_needed):
        source_well = pcr_plate.columns()[col_idx]
        dest_well = sybrgreen_plate.columns()[col_idx]
        protocol.comment(f"\nTransferring to destination well {dest_well}:")
        pipette.transfer(
            pcr_sample_volume,
            source_well,
            dest_well,
            new_tip='always',  # Use fresh tip for each transfer
            mix_after = (3, 20)
        )

def controls_to_sybrgreen(protocol, controls_plate, sybrgreen_plate, pipette, config):
    pcr_sample_volume = config['pcr_sample_volume']
    source_well = controls_plate.columns()[4]
    dest_well = sybrgreen_plate.columns()[11]
    pipette.transfer(
        pcr_sample_volume,
        source_well,
        dest_well,
        new_tip='always',  # Use fresh tip for each transfer
        mix_after = (3, 20)
    )
