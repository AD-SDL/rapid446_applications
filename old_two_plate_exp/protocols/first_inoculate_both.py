from opentrons import protocol_api

# TODO: TEST!!!!

# metadata
metadata = {
    "protocolName": "First Inoculate Both Protocol",
    "author": "Casey Stone",
    "description": "First OT-2 protcol for inoculating both plates",
}

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.12"}


# protocol run function
def run(protocol: protocol_api.ProtocolContext):

    # load culture stock plates
    culture_stock_1 = protocol.load_labware(
        "nest_96_wellplate_2ml_deep",
        location="4",
    )
    # culture_stock_2 = protocol.load_labware(
    #     "nest_96_wellplate_2ml_deep",
    #     location="6",
    # )

    # load substrate plates
    substrate_assay_plate_1 = protocol.load_labware(
        "corning_96_wellplate_360ul_flat",
        location="1",
    )
    substrate_assay_plate_2 = protocol.load_labware(
        "corning_96_wellplate_360ul_flat",
        location="3",
    )

    # load tip racks
    tip_rack_1_20uL = protocol.load_labware(
        "opentrons_96_tiprack_20ul",
        location="7",
    )
    tip_rack_2_20uL = protocol.load_labware(
        "opentrons_96_tiprack_20ul",
        location="9",
    )

    # set labware offsets (updated to new offsets 6/5/25)
    culture_stock_1.set_offset(x=-0.0, y=0.3, z=0.0)  # pos 4
    # culture_stock_2.set_offset(x=-0.2, y=1.1, z=0.0)  # pos 6
    tip_rack_1_20uL.set_offset(x=-0.0, y=1.0, z=0.0)  # pos 7
    tip_rack_2_20uL.set_offset(x=-0.0, y=0.3, z=0.0)  # pos 9
    substrate_assay_plate_1.set_offset(x=0.0,y=2.0,z=0.0)  # pos 1
    substrate_assay_plate_2.set_offset(x=0.0,y=0.5,z=0.0)   # pos 3

    # variables
    inoculation_volume = 20

    # * load pipettes
    left_pipette_20uL_multi = protocol.load_instrument(
        "p20_multi_gen2", mount="left", tip_racks=[tip_rack_1_20uL, tip_rack_2_20uL]
    )

    #* COMMANDS -------------------
    # First half of substrate plate 1
    """dispense 5ul from each column 2-6 of stock plate 1 
        into column 2-6 substrate plate 1, mixing before and after transfer"""
    source_columns = culture_stock_1.columns()[1:6]   # means column 2-6
    destination_columns = substrate_assay_plate_1.columns()[1:6]    # means column 2-6
    left_pipette_20uL_multi.transfer(
        inoculation_volume, 
        source_columns, 
        destination_columns, 
        new_tip="always",
        disposal_volume = 0, 
    )

    # Second half of substrate plate 1
    """dispense 5ul from each column 2-6 of stock plate 1
        into columns 7-11 of substrate plate 1, mixing before and after transfer"""
    destination_columns = substrate_assay_plate_1.columns()[6:11]    # means column 7-11
    left_pipette_20uL_multi.transfer(
        inoculation_volume, 
        source_columns, 
        destination_columns, 
        new_tip="always",
        disposal_volume = 0, 
    )

    # First half of substrate plate 2
    """dispense 5ul from each column 2-6 of stock plate 2
        into columns 7-11 of substrate plate 2, mixing before and after transfer"""
    source_columns = culture_stock_1.columns()[1:6]   # means column 2-6
    destination_columns = substrate_assay_plate_2.columns()[1:6]    # means column 2-6
    left_pipette_20uL_multi.transfer(
        inoculation_volume, 
        source_columns, 
        destination_columns, 
        new_tip="always",
        disposal_volume = 0, 
    )

    # Second half of substrate plate 2
    """dispense 5ul from each column 2-6 of stock plate 2
        into columns 7-11 of substrate plate 2, mixing before and after transfer"""
    destination_columns = substrate_assay_plate_2.columns()[6:11]    # means column 7-11
    left_pipette_20uL_multi.transfer(
        inoculation_volume, 
        source_columns, 
        destination_columns, 
        new_tip="always",
        disposal_volume = 0, 
    )

