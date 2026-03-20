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
    'pcr_sample_volume': 3,
    'pcr_to_sybrgreen_volume': 6,
    'sybrgreen_volume': 194,
    'sybrgreen_well': 3,
    'water_volume': 97,
    'combinations': [[18,10,2],[11,19,3],[4,20,12],[21,13,5]],
    "num_controls": 5,

    # Master mix and reagent settings
    'water_well': 1,
    'columns_to_move_for_dilute': 6,
    'controls_sample_volume': 6,
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
    'tip_rack_position_50_01': 'A2',
    'tip_rack_position_50_02': 'A3',
    'tip_rack_position_300_01': 'A1',
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



def water_to_pcr_products(protocol, reagent_plate, pcr_plate, pipette, config):
    water_volume = config['water_volume']
    water_well = config['water_well']
    combinations = config['combinations']
    num_samples = calculate_total_combinations(combinations)
    columns_needed = (num_samples + 7) // 8
    reagent_plate_well = reagent_plate.wells()[config['water_well']-1]
    pipette.pick_up_tip()
    pcr_plate_dest_cols = [5, 6, 7, 8]

    for col_idx in pcr_plate_dest_cols:
        dest_well = pcr_plate.columns()[col_idx-1]
        pipette.transfer(
            water_volume,
            water_well,
            dest_well,
            new_tip='never'
        )
    
    pipette.drop_tip()


def intermediate_dilution(protocol, pcr_plate, pipette, config):
    pcr_sample_volume = config['pcr_sample_volume']
    num_cols = 4
    
    for col_idx in range(num_cols):
        pipette.pick_up_tip()
        source_well = pcr_plate.columns()[col_idx]
        dest_well = pcr_plate.columns()[col_idx+4]
        pipette.transfer(
            pcr_sample_volume,
            source_well,
            dest_well,
            new_tip = 'always',
            mix_after = (3, 20),
        )


def sybrgreen_to_dest(protocol, reagent_plate, sybrgreen_plate, pipette, config):
    sybrgreen_volume = config['sybrgreen_volume']
    # num_samples = config["number_of_pcr_samples"]
    combinations = config['combinations']
    num_samples = calculate_total_combinations(combinations)
    columns_needed = (num_samples + 7) // 8
    columns_needed = columns_needed+1
    sybrgreen_well = reagent_plate.wells()[config['sybrgreen_well'] - 1]
    pipette.pick_up_tip()

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
    pcr_sample_volume = config['pcr_to_sybrghreen_volume']
    # num_samples = config["number_of_pcr_samples"]
    combinations = config['combinations']
    num_samples = calculate_total_combinations(combinations)
    columns_needed = (num_samples + 7) // 8
    columns = [5, 6, 7, 8]

    for col_idx in range(columns_needed):
        source_well = pcr_plate.columns()[col_idx+4]
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
    controls_volume = config['controls_sample_volume']
    source_well = controls_plate.columns()[5]
    dest_well = sybrgreen_plate.columns()[4]
    pipette.transfer(
        controls_volume,
        source_well,
        dest_well,
        new_tip='always',  # Use fresh tip for each transfer
        mix_after = (3, 20)
    )



def run(protocol: protocol_api.ProtocolContext):
    # Load temperature module and adapter
    temp_mod1 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_01_position'])
    temp_adapter1 = temp_mod1.load_adapter("opentrons_96_well_aluminum_block")

    temp_mod2 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_02_position'])
    temp_adapter2 = temp_mod2.load_adapter("opentrons_96_well_aluminum_block")

    # Set temperature
    temp_mod1.set_temperature(config['temperature'])
    temp_mod2.set_temperature(config['temperature']) 

    chute = protocol.load_waste_chute()

    # pcr_plate = protocol.load_labware(config['pcr_plate_type'], config['pcr_plate_position'])
    # pcr_plate.set_offset(x=0.4, y=0.4, z=0.2)

    sybrgreen_plate = protocol.load_labware(config['sybrgreen_plate_type'], config['sybrgreen_plate_position'])

    reagent_plate = protocol.load_labware(config['reagent_plate_type'], config['reagent_plate_position'])

    controls_plate = temp_adapter1.load_labware(config['controls_plate_type'])
    pcr_plate = temp_adapter2.load_labware(config['pcr_plate_type'])
    pcr_plate.set_offset(x=0.4, y=0.4, z=0.2)


    tiprack_50_1 = protocol.load_labware(
        load_name=config['tip_rack_type_50_01'], location=config['tip_rack_position_50_01']
    )
    tiprack_50_2 = protocol.load_labware(
        load_name=config['tip_rack_type_50_02'], location=config['tip_rack_position_50_02']
    )
    tiprack_200_1 = protocol.load_labware(
        load_name=config['tip_rack_type_200_01'], location=config['tip_rack_position_200_01']
    )


    p50 = protocol.load_instrument('flex_8channel_50', mount='right', tip_racks=[tiprack_50_1, tiprack_50_2])
    p1000 = protocol.load_instrument('flex_8channel_1000', mount='left', tip_racks=[tiprack_200_1])

    p50.configure_nozzle_layout(style='COLUMN', start='A1', tip_racks=[tiprack_50_1, tiprack_50_2])
    p1000.configure_nozzle_layout(style='COLUMN', start='A1', tip_racks=[tiprack_200_1])

    water_to_pcr_products(protocol=protocol,
                          reagent_plate=reagent_plate,
                          pcr_plate=pcr_plate,
                          pipette=p1000,
                          config=config)

    intermediate_dilution(protocol=protocol,
                          pcr_plate=pcr_plate,
                          pipette=p50,
                          config=config)

    sybrgreen_to_dest(protocol=protocol,
                      reagent_plate=reagent_plate,
                      sybrgreen_plate=sybrgreen_plate,
                      pipette=p1000,
                      config=config)

    pcr_to_dest(protocol=protocol,
                pcr_plate=pcr_plate,
                sybrgreen_plate=sybrgreen_plate,
                pipette=p50,
                config=config)

    controls_to_sybrgreen(protocol=protocol,
                          controls_plate=controls_plate,
                          sybrgreen_plate=sybrgreen_plate,
                          pipette=p50,
                          config=config)