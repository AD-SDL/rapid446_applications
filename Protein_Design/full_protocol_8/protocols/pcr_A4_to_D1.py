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
    'combinations': [[18,10,2],[11,19,3],[4,20,12],[21,13,5]],

    # Master mix and reagent settings
    'pcr_master_mix_well_volume': 100,
    'water_volume': 20,
    'pcr_master_mix_volume': 24,
    'water_well': 1,
    'master_mix_start_well': 48,
    'heater_shaker_temp': 37,


    # Temperature settings
    'temperature': 4,  # °C

    # Labware
    'fragments_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'pcr_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'reagent_plate_type': 'nest_12_reservoir_15ml',
    'tip_rack_type_50_01': 'opentrons_flex_96_tiprack_50ul',
    'tip_rack_type_50_02': 'opentrons_flex_96_tiprack_50ul',
    'tip_rack_type_300_01': 'opentrons_flex_96_tiprack_300ul',
    'pipette_type_50': 'flex_8channel_50',
    'pipette_type_1000': 'flex_8channel_1000',
    'pcr_adapter_type': 'opentrons_96_pcr_adapter',

    # Deck positions
    'temp_module_01_position': 'B1',
    'temp_module_02_position': 'C1',
    'fragments_plate_initial_position': 'B1',
    'pcr_plate_position': 'C1',
    'tip_rack_position_50_01': 'A2',
    'tip_rack_position_50_02': 'A3',
    'tip_rack_position_300_01': 'A1',
    'reagent_plate_position': 'D2',
    'shaker_module_position': 'D1',
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






def run(protocol: protocol_api.ProtocolContext):
    # Load temperature module and adapter
    temp_mod_1 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_01_position'])
    temp_adapter_1 = temp_mod_1.load_adapter("opentrons_96_well_aluminum_block")

    temp_mod_2 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_02_position'])
    temp_adapter_2 = temp_mod_2.load_adapter("opentrons_96_well_aluminum_block")

    shaker_mod = protocol.load_module(module_name="heaterShakerModuleV1", location=config['shaker_module_position'])
    shaker_adapter = shaker_mod.load_adapter(config['pcr_adapter_type'])
    shaker_mod.set_target_temperature(config['heater_shaker_temp'])
    shaker_mod.open_labware_latch()



    chute = protocol.load_waste_chute()

    pcr_plate = protocol.load_labware('nest_96_wellplate_100ul_pcr_full_skirt', "A4")




    # Load destination plate
    # pcr_plate = protocol.load_labware(config['pcr_plate_type'], config['pcr_plate_position'])
    # pcr_plate.set_offset(x=0.4, y=0.4, z=0.0)

    # gg_plate = protocol.load_labware(config['gg_plate_type'], config['gg_plate_position'])
    # pcr_plate.set_offset(x=0.7, y=0.30, z=0.2)

    # reagent_plate = protocol.load_labware(config['reagent_plate_type'], config['reagent_plate_position'])


    # tiprack_50_1 = protocol.load_labware(
    #     load_name=config['tip_rack_type_50_01'], location=config['tip_rack_position_50_01']
    # )
    # tiprack_50_2 = protocol.load_labware(
    #     load_name=config['tip_rack_type_50_02'], location=config['tip_rack_position_50_02']
    # )
    # tiprack_300_1 = protocol.load_labware(
    #     load_name=config['tip_rack_type_300_01'], location=config['tip_rack_position_300_01']
    # )



    # # Pipettes
    # p50 = protocol.load_instrument('flex_8channel_50', mount='right', tip_racks=[tiprack_50_1, tiprack_50_2])
    # p1000 = protocol.load_instrument('flex_8channel_1000', mount='left', tip_racks=[tiprack_300_1])

    # p50.configure_nozzle_layout(style='COLUMN', start='A1', tip_racks=[tiprack_50_1, tiprack_50_2])
    # p1000.configure_nozzle_layout(style='COLUMN', start='A1', tip_racks=[tiprack_300_1])
    # p1000.configure_nozzle_layout(style=SINGLE, start='A1', tip_racks=[tiprack_200])



    protocol.move_labware(labware=pcr_plate, new_location=shaker_adapter, use_gripper=True)
    shaker_mod.close_labware_latch()
    shaker_mod.set_and_wait_for_shake_speed(200)
    protocol.delay(minutes = 1)
    # shaker_mod.deactivate_shaker()
    # shaker_mod.open_labware_latch()


