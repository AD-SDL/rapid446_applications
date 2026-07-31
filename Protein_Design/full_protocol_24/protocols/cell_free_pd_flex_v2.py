from opentrons import protocol_api
import itertools
from opentrons.protocol_api import SINGLE


metadata = {
    'protocolName': 'Protein Design CFPS 81 reagent Flex',
    'author': 'LDRD team ',
    'description': 'CFPS plate setup from PCR templates and standards followed by CFPS on the deck',
    'source': 'FlexAS/pd_cfps_81.py'
}

requirements = {"robotType": "Flex", "apiLevel": "2.20"}

config = {
    # 'combinations': [[18,10,2],[11,19,3],[4,20,12],[21,13,5]], # 1-indexed source well numbers (kept for total calculation)
    # 'combinations': [[1], [2, 2], [3, 3], [4, 4]],
    'combinations': "$combinations",
    'use_combinations': bool("$use_combinations"),
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
    'tip_rack_type_50_02': 'opentrons_flex_96_filtertiprack_50ul',
    'tip_rack_type_200_01': 'opentrons_flex_96_filtertiprack_200ul',
    'reagent_plate_type': 'nest_12_reservoir_15ml',
    'pcr_adapter_type': 'opentrons_96_pcr_adapter',

    'rmf_plate_position': 'B1',
    'cfps_plate_position': 'C1',
    'temp_module_01_position': 'B1',
    'temp_module_02_position': 'C1',
    'tip_rack_position_50_01': 'A2',
    'tip_rack_position_50_02': 'A3',
    'tip_rack_position_200_01': 'A1',
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



def mixA_to_rmf(protocol, rmf_plate, pipette, config):
    #mix at every step
    # mix 5 times, 120ul to col 4
    source_well = rmf_plate.columns()[0]
    dest_well = rmf_plate.columns()[3]
    pipette.pick_up_tip()

    pipette.transfer(
        120,
        source_well,
        dest_well,
        new_tip='never',
        mix_before = (5, 30)
    )
    pipette.drop_tip()
    config['tips_used_1000']+=8

    # source_well = rmf_plate.columns()[1]
    # dest_well = rmf_plate.columns()[4]
    # pipette.pick_up_tip()

    # pipette.transfer(
    #     120,
    #     source_well,
    #     dest_well,
    #     new_tip='never',
    #     mix_before = (5, 30)
    # )
    # pipette.drop_tip()

    # 54ul from col 3 into 4 and 5, mix after
    source_well = rmf_plate.columns()[2]
    dest_well = rmf_plate.columns()[3]
    # pipette.pick_up_tip()

    pipette.transfer(
        60,
        source_well,
        dest_well,
        new_tip='always',  # Use fresh tip for each transfer
        # mix_before = (5, 30),
        mix_after = (10, 30)
    )
    config['tips_used_1000']+=8

    # source_well = rmf_plate.columns()[2]
    # dest_well = rmf_plate.columns()[4]
    # # pipette.pick_up_tip()

    # pipette.transfer(
    #     60,
    #     source_well,
    #     dest_well,
    #     new_tip='always',  # Use fresh tip for each transfer
    #     # mix_before = (5, 30),
    #     mix_after = (10, 30)
    # )




def mixB_to_rmf(protocol, rmf_plate, cfps_plate, pipette, config):
    #mix at every step
    # 23ul from col 4 of starting plate to cols 1-6 of cfps plate
    combinations = config['combinations']
    num_samples = calculate_total_combinations(combinations)
    columns_needed = (num_samples + 7) // 8
    source_well = rmf_plate.columns()[3]
    pipette.pick_up_tip()
    for i in range(columns_needed+1):
        dest_well = cfps_plate.columns()[i]
        pipette.transfer(
            27.6,
            source_well,
            dest_well,
            new_tip='never',
            mix_before = (3, 15)
        )
    pipette.drop_tip()
    config['tips_used_50']+=8

    # # 23ul from col 5 of starting plate to cols 7-12 of cfps plate
    # source_well = rmf_plate.columns()[4]
    # pipette.pick_up_tip()
    # for i in range(6, 12):
    #     dest_well = cfps_plate.columns()[i]
    #     pipette.transfer(
    #         27.6,
    #         source_well,
    #         dest_well,
    #         new_tip='never',
    #         mix_before = (3, 15)
    #     )
    # pipette.drop_tip()



def run(protocol: protocol_api.ProtocolContext):
    # Load temperature module and adapter
    temp_mod1 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_01_position'])
    temp_adapter1 = temp_mod1.load_adapter("opentrons_96_well_aluminum_block")

    temp_mod2 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_02_position'])
    temp_adapter2 = temp_mod2.load_adapter("opentrons_96_well_aluminum_block")

    # Set temperature
    # temp_mod1.set_temperature(config['temperature']) #TODO: make seperate, or just set earlier, only 1 hour with plate
    # temp_mod2.set_temperature(config['temperature']) #TODO: make seperate, or just set earlier, only 1 hour with plate

    shaker_mod = protocol.load_module(module_name="heaterShakerModuleV1", location=config['shaker_module_position'])
    shaker_adapter = shaker_mod.load_adapter(config['pcr_adapter_type'])
    # shaker_mod.set_target_temperature(config['heater_shaker_temp'])

    # shaker_mod.open_labware_latch()

    chute = protocol.load_waste_chute()

    rmf_plate = temp_adapter1.load_labware(config['rmf_plate_type'])
    rmf_plate.set_offset(x=0.7, y=0.30, z=0.6)

    cfps_plate = temp_adapter2.load_labware(config['cfps_plate_type'])
    cfps_plate.set_offset(x=0.4, y=0.4, z=0.0)

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


    mixA_to_rmf(protocol=protocol,
                rmf_plate=rmf_plate,
                pipette=p1000,
                config=config)

    mixB_to_rmf(protocol=protocol,
                rmf_plate=rmf_plate,
                cfps_plate=cfps_plate,
                pipette=p50,
                config=config)
    
    protocol.comment(f"tips used 1000: {config['tips_used_1000']}")
    protocol.comment(f"tips used 50: {config['tips_used_50']}")