from opentrons import protocol_api
import itertools
from opentrons.protocol_api import SINGLE


metadata = {
    'protocolName': 'Protein Design PCR 81 8 channel',
    'author': 'LDRD team ',
    'description': 'PCR for Protein Design 81 reagents',
    'source': 'FlexAS/pd_pcr_81.py'
}

requirements = {"robotType": "Flex", "apiLevel": "2.20"}


# Protocol Configuration
config = {
    # Combinatorial mixing
    'transfer_volume': 1,  # µL from each gg well
    # 'number_of_gg_samples': 6,
    # 'combinations': [[18,10,2],[11,19,3],[4,20,12],[21,13,5]],
    'combinations': [[1], [2], [3], [4]],

    # Master mix and reagent settings
    'pcr_master_mix_well_volume': 100,
    'water_volume': 20,
    'pcr_master_mix_volume': 24,
    'water_well': 1,
    'master_mix_start_well': 72,


    # Temperature settings
    'temperature': 4,  # °C

    # Labware
    'fragments_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'pcr_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'reagent_plate_type': 'nest_12_reservoir_15ml',
    'tip_rack_type_50_01': 'opentrons_flex_96_tiprack_50ul',
    'tip_rack_type_50_02': 'opentrons_flex_96_tiprack_50ul',
    'tip_rack_type_200_01': 'opentrons_flex_96_tiprack_200ul',
    'pipette_type_50': 'flex_8channel_50',
    'pipette_type_1000': 'flex_8channel_1000',

    # Deck positions
    'temp_module_01_position': 'B1',
    'temp_module_02_position': 'C1',
    'fragments_plate_initial_position': 'B1',
    'pcr_plate_position': 'C1',
    'tip_rack_position_50_01': 'A2',
    'tip_rack_position_50_02': 'A3',
    'tip_rack_position_200_01': 'A1',
    'reagent_plate_position': 'D2'
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


def master_mix_to_pcr_plate(protocol, source_plate, pcr_plate, pipette, config):
    master_mix_volume = config['pcr_master_mix_volume']
    # gg_wells = config['number_of_gg_samples']
    # protocol.comment(f"Total wells to add master mix to: {gg_wells}")
    pcr_master_mix_well_volume = config["pcr_master_mix_well_volume"]
    master_mix_well_volume = config["pcr_master_mix_volume"]
    master_mix_start_well = config["master_mix_start_well"]
    combinations = config['combinations']

    gg_wells = calculate_total_combinations(combinations)
    columns_needed = (gg_wells + 7) // 8

    dispenses_per_well = pcr_master_mix_well_volume // master_mix_volume
    protocol.comment(f"Each master mix well ({master_mix_well_volume}µL) can serve {dispenses_per_well} destination wells")

    master_mix_wells_needed = (gg_wells + dispenses_per_well - 1) // dispenses_per_well

    current_master_mix_well = master_mix_start_well
    remaining_dispenses = dispenses_per_well
    protocol.comment(f"\nAdding {master_mix_volume}µL master mix to each destination well:")
# #######################
    for col_idx in range(columns_needed):
        if remaining_dispenses == 0:
            current_master_mix_well += 8
            remaining_dispenses = dispenses_per_well
            protocol.comment(f"  Switching to master mix well {current_master_mix_well + 1} (0-indexed: {current_master_mix_well})")

        dest_well = pcr_plate.columns()[col_idx]
        master_mix_well = source_plate.wells()[current_master_mix_well]
        protocol.comment(f"  Dest well {col_idx}: Adding {master_mix_volume}µL from master mix well {current_master_mix_well + 1} (0-indexed: {current_master_mix_well})")
        # Transfer master mix
        pipette.transfer(
            master_mix_volume,
            master_mix_well,
            dest_well,
            new_tip='always',  # Use fresh tip for each master mix transfer
            mix_before=(3, 10),
            mix_after=(3, 10)
        )
        # Update remaining dispenses
        remaining_dispenses -= 1

    protocol.comment(f"\nMaster mix addition complete. Used wells {master_mix_start_well + 1} to {current_master_mix_well + 1} (0-indexed: {master_mix_start_well} to {current_master_mix_well})")


    # for dest_well_number in range(1, gg_wells + 1):
    #     # Check if we need to switch to next master mix well
    #     if remaining_dispenses == 0:
    #         current_master_mix_well += 1
    #         remaining_dispenses = dispenses_per_well
    #         protocol.comment(f"  Switching to master mix well {current_master_mix_well + 1} (0-indexed: {current_master_mix_well})")

    #     # Get the destination well
    #     dest_well = pcr_plate.wells()[dest_well_number - 1]  # Convert to 0-based index

    #     # Get the current master mix well
    #     master_mix_well = source_plate.wells()[current_master_mix_well]

    #     protocol.comment(f"  Dest well {dest_well_number}: Adding {master_mix_volume}µL from master mix well {current_master_mix_well + 1} (0-indexed: {current_master_mix_well})")

    #     # Transfer master mix
    #     pipette.transfer(
    #         master_mix_volume,
    #         master_mix_well,
    #         dest_well,
    #         new_tip='always',  # Use fresh tip for each master mix transfer
    #         mix_before=(3, 10),
    #         mix_after=(3, 10)
    #     )

    #     # Update remaining dispenses
    #     remaining_dispenses -= 1

    # protocol.comment(f"\nMaster mix addition complete. Used wells {master_mix_start_well + 1} to {current_master_mix_well + 1} (0-indexed: {master_mix_start_well} to {current_master_mix_well})")

    return current_master_mix_well  # Return the last used well









def run(protocol: protocol_api.ProtocolContext):
    # Load temperature module and adapter
    temp_mod_1 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_01_position'])
    temp_adapter_1 = temp_mod_1.load_adapter("opentrons_96_well_aluminum_block")

    temp_mod_2 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_02_position'])
    temp_adapter_2 = temp_mod_2.load_adapter("opentrons_96_well_aluminum_block")

    # Set temperature
    temp_mod_1.set_temperature(config['temperature']) #TODO: make seperate, or just set earlier, only 1 hour with plate
    temp_mod_2.set_temperature(config['temperature']) #TODO: make seperate, or just set earlier, only 1 hour with plate

    # Load source plate initially on A4
    # source_plate = protocol.load_labware(config['source_plate_type'], config['source_plate_initial_position'])
    source_plate = temp_adapter_1.load_labware(config['fragments_plate_type'])
    pcr_plate = temp_adapter_2.load_labware(config['pcr_plate_type'])

    chute = protocol.load_waste_chute()

    source_plate.set_offset(x=0.7, y=0.30, z=0.2)


    # Load destination plate
    # pcr_plate = protocol.load_labware(config['pcr_plate_type'], config['pcr_plate_position'])
    # pcr_plate.set_offset(x=0.4, y=0.4, z=0.0)

    # gg_plate = protocol.load_labware(config['gg_plate_type'], config['gg_plate_position'])
    pcr_plate.set_offset(x=0.7, y=0.30, z=0.2)

    reagent_plate = protocol.load_labware(config['reagent_plate_type'], config['reagent_plate_position'])


    tiprack_50_1 = protocol.load_labware(
        load_name=config['tip_rack_type_50_01'], location=config['tip_rack_position_50_01']
    )
    tiprack_50_2 = protocol.load_labware(
        load_name=config['tip_rack_type_50_02'], location=config['tip_rack_position_50_02']
    )
    tiprack_200_1 = protocol.load_labware(
        load_name=config['tip_rack_type_200_01'], location=config['tip_rack_position_200_01']
    )



    # Pipettes
    p50 = protocol.load_instrument('flex_8channel_50', mount='right', tip_racks=[tiprack_50_1, tiprack_50_2])
    p1000 = protocol.load_instrument('flex_8channel_1000', mount='left', tip_racks=[tiprack_200_1])

    p50.configure_nozzle_layout(style='COLUMN', start='A1', tip_racks=[tiprack_50_1, tiprack_50_2])
    p1000.configure_nozzle_layout(style='COLUMN', start='A1', tip_racks=[tiprack_200_1])
    # p1000.configure_nozzle_layout(style=SINGLE, start='A1', tip_racks=[tiprack_200])



    # Add master mix to each destination well
    last_master_mix_well = master_mix_to_pcr_plate(
        protocol=protocol,
        source_plate=source_plate,
        pcr_plate=pcr_plate,
        pipette=p1000,
        config=config
    )

