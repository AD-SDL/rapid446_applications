from opentrons import protocol_api

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
    tip_rack_deck4= protocol.load_labware(
        "opentrons_96_tiprack_20ul",
        location="4",
    )
    tip_rack_deck5= protocol.load_labware(
        "opentrons_96_tiprack_20ul",
        location="5",
    )
    tip_rack_deck6= protocol.load_labware(
        "opentrons_96_tiprack_20ul",
        location="6",
    )
    tip_rack_deck7= protocol.load_labware(
        "opentrons_96_tiprack_20ul",
        location="7",
    )
    tip_rack_deck8= protocol.load_labware(
        "opentrons_96_tiprack_20ul",
        location="8",
    )
    tip_rack_deck9= protocol.load_labware(
        "opentrons_96_tiprack_20ul",
        location="9",
    )
    tip_rack_deck10= protocol.load_labware(
        "opentrons_96_tiprack_20ul",
        location="10",
    )
    tip_rack_deck11= protocol.load_labware(
        "opentrons_96_tiprack_20ul",
        location="11",
    )
    tip_rack_list = [
        tip_rack_deck4,
        tip_rack_deck5,
        tip_rack_deck6,
        tip_rack_deck7,
        tip_rack_deck8,
        tip_rack_deck9,
        tip_rack_deck10,
        tip_rack_deck11,
    ]

    # set labware offsets
    #tip_rack.set_offset(x=float("$x"), y=float("$y"), z=float("$z"))
    # substrate_assay_plate_new.set_offset(x=0.0,y=2.0,z=0.0)  # pos 1
    # substrate_assay_plate_old.set_offset(x=0.0,y=0.5,z=0.0)   # pos 3

    # variables
    inoculation_volume = 20  # in uL

    pipette_20uL_multi = protocol.load_instrument(
        "p20_multi_gen2", mount="right", tip_racks=tip_rack_list
    )

    # COMMANDS ------------------
    """Inoculate new substrate plate from old substrate plate"""

    # define variables
    source_columns = substrate_assay_plate_old.columns()[0:12]   # means all columns 1-12
    destination_columns = substrate_assay_plate_new.columns()[0:12]  # means all columns 1-12

    for i in range(96):
        pipette_20uL_multi.pick_up_tip()
        pipette_20uL_multi.transfer(
            inoculation_volume,
            source_columns[0],
            destination_columns[0],
            new_tip="never",
            disposal_volume = 0,
        )
        pipette_20uL_multi.drop_tip()





