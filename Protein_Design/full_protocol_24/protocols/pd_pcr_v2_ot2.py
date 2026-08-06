from opentrons import protocol_api
import itertools
from opentrons.protocol_api import SINGLE
import ast


metadata = {
    'protocolName': 'Protein Design PCR 8 channel',
    'author': 'LDRD team ',
    'description': 'PCR for Protein Design reagents',
    'source': 'FlexAS/pd_pcr_81.py'
}

requirements = {"robotType": "OT-2", "apiLevel": "2.20"}


# Protocol Configuration
config = {
    # Combinatorial mixing
    'transfer_volume': 2,  # µL from each gg well
    # 'number_of_gg_samples': 6,
    # 'combinations': [[18,10],[11,19],[4,20],[21,13]],
    # 'combinations': [[1], [2, 2], [3, 3], [4, 4]],
    # 'use_combinations': True,

    'combinations': "$combinations",
    'use_combinations': bool("$use_combinations"),
    'non_combinatorial_sources': "$non_combinatorial_sources",

    # Master mix and reagent settings
    'pcr_master_mix_well_volume': 100,
    'water_volume': 20,
    'pcr_master_mix_volume': 24,
    'water_well': 1,
    'master_mix_start_well': 48,
    'tips_used': 0,


    # Temperature settings
    'temperature': 4,  # °C

    # Labware
    'pcr_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'gg_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'reagent_plate_type': 'nest_12_reservoir_15ml',
    'tip_rack_type_20_01': 'opentrons_96_filtertiprack_20ul',
    'pipette_type_20': 'p20_single_gen2',
    'pipette_type_20_multi': 'p20_multi_gen2',

    # Deck positions
    'temp_module_01_position': 'C1',
    'temp_module_02_position': 'C3',
    'pcr_plate_position': 'C1',
    'gg_plate_position': 'C3',
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

def transfer_water_to_gg(protocol, reagent_plate, gg_plate, pipette, config):
    water_volume = config['water_volume']
    # gg_wells = config['number_of_gg_samples']
    water_well = reagent_plate.wells()[config['water_well'] - 1]
    # protocol.comment(f"Total wells to add water to: {gg_wells}")
    combinations = config['combinations']

    gg_wells = calculate_total_combinations(combinations)
    columns_needed = (gg_wells + 7) // 8

    for col_idx in range(columns_needed):
        dest_well = gg_plate.columns()[col_idx]
        protocol.comment(f"\nTransferring to destination well {dest_well}:")
        pipette.transfer(
            water_volume,
            water_well,
            dest_well,
            new_tip='always',  # Use fresh tip for each transfer
            mix_after = (3, 10)
        )

        config['tips_used']+=8

    # for well in range(1, gg_wells + 1):
    #     dest_well = gg_plate.wells()[well - 1]
    #     protocol.comment(f"\nTransferring to destination well {dest_well}:")
    #     pipette.transfer(
    #         water_volume,
    #         water_well,
    #         dest_well,
    #         new_tip='always',  # Use fresh tip for each transfer
    #         mix_after = (3, 10)
    #     )



def gg_to_pcr_plate(protocol, gg_plate, pcr_plate, pipette, config):

    # gg_wells = config['number_of_gg_samples']
    combinations = config['combinations']
    gg_wells = calculate_total_combinations(combinations)
    transfer_volume = config['transfer_volume']
    columns_needed = (gg_wells + 7) // 8

    for col_idx in range(columns_needed):
        dest_well = pcr_plate.columns()[col_idx]
        source_well = gg_plate.columns()[col_idx]
        pipette.transfer(
            transfer_volume,
            source_well,
            dest_well,
            new_tip='always',  # Use fresh tip for each transfer
            mix_before = (3, 10),
            mix_after = (3, 10)
        )

        config['tips_used']+=8



    # for well in range(1, gg_wells + 1):
    #     dest_well = pcr_plate.wells()[well - 1]
    #     source_well = gg_plate.wells()[well - 1]

    #     pipette.transfer(
    #         transfer_volume,
    #         source_well,
    #         dest_well,
    #         new_tip='always',  # Use fresh tip for each transfer
    #         mix_before = (3, 10),
    #         mix_after = (3, 10)
    #     )








def run(protocol: protocol_api.ProtocolContext):
    combinations_string = config['combinations']
    combinations = ast.literal_eval(combinations_string)
    config['combinations'] = combinations
    # Load temperature module and adapter
    temp_mod_1 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_01_position'])
    temp_adapter_1 = temp_mod_1.load_adapter("opentrons_96_well_aluminum_block")

    temp_mod_2 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_02_position'])
    temp_adapter_2 = temp_mod_2.load_adapter("opentrons_96_well_aluminum_block")

    # Set temperature
    # temp_mod_1.set_temperature(config['temperature']) #TODO: make seperate, or just set earlier, only 1 hour with plate
    # temp_mod_2.set_temperature(config['temperature']) #TODO: make seperate, or just set earlier, only 1 hour with plate



    # Load destination plate
    # pcr_plate = protocol.load_labware(config['pcr_plate_type'], config['pcr_plate_position'])
    pcr_plate = temp_adapter_1.load_labware(config['pcr_plate_type'])
    pcr_plate.set_offset(x=0.4, y=0.4, z=0.0)

    # gg_plate = protocol.load_labware(config['gg_plate_type'], config['gg_plate_position'])
    gg_plate = temp_adapter_2.load_labware(config['gg_plate_type'])
    gg_plate.set_offset(x=0.7, y=0.30, z=0.2)

    reagent_plate = protocol.load_labware(config['reagent_plate_type'], config['reagent_plate_position'])


    tiprack_20_1 = protocol.load_labware(
        load_name=config['tip_rack_type_20_01'], location=config['tip_rack_position_20_01']
    )


    # Pipettes
    p50 = protocol.load_instrument('p20_multi_gen2', mount='right', tip_racks=[tiprack_20_1])
    p50s = protocol.load_instrument('p20_single_gen2', mount='left', tip_racks=[tiprack_20_1])

    p50.configure_nozzle_layout(style='COLUMN', start='A1', tip_racks=[tiprack_20_1])
    # p1000.configure_nozzle_layout(style=SINGLE, start='A1', tip_racks=[tiprack_200])

    p50.starting_tip = tiprack_20_1.well('A4')



    # Perform combinatorial transfers #TODO: SWAP?  so adding small vols into large quant of master mix
    transfer_water_to_gg(
        protocol=protocol,
        reagent_plate=reagent_plate,
        gg_plate=gg_plate,
        pipette=p50,
        config=config
    )

    gg_to_pcr_plate(
        protocol=protocol,
        gg_plate=gg_plate,
        pcr_plate=pcr_plate,
        pipette=p50,
        config=config
    )

    protocol.comment(f"tips used: {config['tips_used']}")

