
from madsci.client.resource_client import ResourceClient
from madsci.common.types.resource_types import Asset, Resource, Collection, Slot


resource_server_url = None  # "http://ip of the resource server"

resource_client = ResourceClient(resource_server_url = resource_server_url)
plate = Collection(
    # resource_id="01KT9Q9MJF3WPYQT6TBZ9QPQ5J",
    resource_name="Z_PCR_CORRECT_ATTRIBUTES_PLATE_2",
    resource_class="Microplate",
    attributes={
        # Common attributes
        "plate_height": 14, 
        "description": "TEST 96-well PLATE",
        "catalog_number": "SP-2396",

        # PF400 specific attributes
        "pf400_grip_height": 6,

        # SciClops specific attributes
        "sciclops_grip_height": 1,
    },
)

plate = resource_client.add_or_update_resource(plate)
print(f"Plate created with attributes: {plate.resource_id}")


