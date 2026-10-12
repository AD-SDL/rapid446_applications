
from madsci.client.resource_client import ResourceClient
from madsci.common.types.resource_types import Asset, Resource, Collection, Slot

test_lid = Resource(
    resource_name = "TEST_LID",
    attributes={
        "lid": True
    }
)

resource_server_url = None  # "http://ip of the resource server"

resource_client = ResourceClient(resource_server_url = resource_server_url)

plate = Collection(
    # resource_id="01K7T1QAXCMSAJ3MAK2GAS24ZK",
    resource_name="CORRECT_ATTRIBUTES_PLATE",
    resource_class="Microplate",
    attributes={
        # Common attributes
        "plate_height": 14, 
        "lid_height": 10,
        "plate_height_with_lid": 16,
        "description": "96-well microplate with or without lid",

        # PF400 specific attributes
        "pf400_grip_height": 3,
        "pf400_lid_only_grip_height":4,
        "pf400_lid_removal_grip_height": 10,

        # SciClops specific attributes
        "sciclops_grip_height": 1, 
        "sciclops_lid_grip_height": 4, 
        "sciclops_lid_removal_grip_height": 12,
    },
    children={
        "lid_slot": Slot(
            resource_name = "lid slot resource on test plate",
            children=[test_lid]
        )
    }
)

plate = resource_client.add_or_update_resource(plate)
print(f"Plate created with attributes: {plate.resource_id}")


