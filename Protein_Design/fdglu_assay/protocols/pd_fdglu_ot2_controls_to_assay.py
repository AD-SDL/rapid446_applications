from opentrons import protocol_api
import itertools
from opentrons.protocol_api import SINGLE


metadata = {
    'protocolName': 'Protein Design Fdglu controls to assay',
    'author': 'LDRD team ',
    'description': 'PCR for Protein Design reagents',
    'source': 'FlexAS/pd_pcr_81.py'
}

requirements = {"robotType": "OT-2", "apiLevel": "2.20"}


# Protocol Configuration
config = {
    'combinations': [[1], [2], [3], [4]],

    # Temperature settings
    'temperature': 4,  # °C

    'controls_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'fdglu_plate_type': 'nest_96_wellplate_100ul_pcr_full_skirt',
    'reagent_plate_type': 'nest_12_reservoir_15ml',
    'tip_rack_type_20_01': 'opentrons_96_filtertiprack_20ul',
    'pipette_type_20': 'p20_single_gen2',
    'pipette_type_20_multi': 'p20_multi_gen2',

    # Deck positions
    'temp_module_01_position': 'C1',
    'temp_module_02_position': 'C3',
    'controls_plate_position': 'C1',
    'fdglu_plate_position': 'C3',
    'reagent_plate_position': 'A1',
    'tip_rack_position_20_01': 'D3',
}


def controls_to_dest(protocol, controls_plate, fdglu_plate, pipette, config):
   #controls in f3, g3, h3 into fdglu f12, g12, h12
   controls = [21, 22, 23]
   dest = [37, 38, 39]
   for i in range(3):
       source_well = controls_plate.wells()[controls[i]]
       dest_well = fdglu_plate.wells()[dest[i]]
       pipette.transfer(
        20,
        source_well,
        dest_well,
        new_tip='always',
        mix_after = (3, 18)
        )


def run(protocol: protocol_api.ProtocolContext):
    # Load temperature module and adapter
    temp_mod1 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_01_position'])
    temp_adapter1 = temp_mod1.load_adapter("opentrons_96_well_aluminum_block")

    temp_mod2 = protocol.load_module(module_name="temperature module gen2", location=config['temp_module_02_position'])
    temp_adapter2 = temp_mod2.load_adapter("opentrons_96_well_aluminum_block")

    # Set temperature
    temp_mod1.set_temperature(config['temperature']) #TODO: make seperate, or just set earlier, only 1 hour with plate
    temp_mod2.set_temperature(config['temperature'])

    controls_plate = temp_adapter1.load_labware(config['controls_plate_type'])
    controls_plate.set_offset(x=0.4, y=0.4, z=0.0)

    fdglu_plate = temp_adapter2.load_labware(config['fdglu_plate_type'])
    fdglu_plate.set_offset(x=0.4, y=0.4, z=0.0)

    reagent_plate = protocol.load_labware(config['reagent_plate_type'], config['reagent_plate_position'])

    tiprack_20_1 = protocol.load_labware(
        load_name=config['tip_rack_type_20_01'], location=config['tip_rack_position_20_01']
    )

    p50 = protocol.load_instrument('p20_multi_gen2', mount='right', tip_racks=[tiprack_20_1])
    p50s = protocol.load_instrument('p20_single_gen2', mount='left', tip_racks=[tiprack_20_1])

    p50.configure_nozzle_layout(style='COLUMN', start='A1', tip_racks=[tiprack_20_1])



    controls_to_dest(protocol=protocol,
                     controls_plate=controls_plate,
                     fdglu_plate=fdglu_plate,
                     pipette=p50s,
                     config=config)

