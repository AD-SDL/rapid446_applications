from opentrons import protocol_api

# TODO: TEST!!!!

# metadata
metadata = {
    "protocolName": "Inoculate Protocol for 2 plate substrate experiment",
    "author": "Casey Stone",
    "description": "OT-2 protocol for inoculating whole substrate plate",
}

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.12"}


# protocol run function
def run(protocol: protocol_api.ProtocolContext):
    # load substrate plates
    substrate_assay_plate_new = protocol.load_labware(
        "corning_96_wellplate_360ul_flat",
        location="1",
    )
    substrate_assay_plate_old = protocol.load_labware(
        "corning_96_wellplate_360ul_flat",
        location="3",
    )

    # load tip racks
    tip_rack= protocol.load_labware(
        "opentrons_96_tiprack_20ul",
        location="$tip_location",
    )

    # set labware offsets
    tip_rack.set_offset(x=float("$x"), y=float("$y"), z=float("$z")) 
    substrate_assay_plate_new.set_offset(x=0.0,y=2.0,z=0.0)  # pos 1
    substrate_assay_plate_old.set_offset(x=0.0,y=0.5,z=0.0)   # pos 3

    # variables
    inoculation_volume = 20

    left_pipette_20uL_multi = protocol.load_instrument(
        "p20_multi_gen2", mount="left", tip_racks=[
            tip_rack, 
        ]
    )

    # COMMANDS ------------------
    """Inoculate new substrate plate from old substrate plate"""

    # define variables
    source_columns = substrate_assay_plate_old.columns()[0:12]   # means all columns 1-12
    destination_columns = substrate_assay_plate_new.columns()[0:12]  # means all columns 1-12

    # trash the tips from the first transfer
    left_pipette_20uL_multi.pick_up_tip()
    left_pipette_20uL_multi.transfer(
        inoculation_volume,
        source_columns[0], 
        destination_columns[0], 
        new_tip="never",
        disposal_volume = 0,
    )
    left_pipette_20uL_multi.drop_tip()

    # return the tips from the rest of the transfers to conserve trash space
    for i in range(1, len(source_columns)):  # (1,12) means columns 2-12
        left_pipette_20uL_multi.pick_up_tip()
        left_pipette_20uL_multi.transfer(
            inoculation_volume,
            source_columns[i], 
            destination_columns[i], 
            new_tip = "never",
            disposal_volume = 0
        )
        left_pipette_20uL_multi.return_tip()





