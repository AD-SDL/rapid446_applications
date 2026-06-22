
from madsci.client.resource_client import ResourceClient
from madsci.common.types.resource_types import Asset


# THIS WORKS!



resource_client = ResourceClient(resource_server_url = "http://146.137.240.20:8004/")
plate = Asset(
    resource_id="01K7T1QAXCMSAJ3MAK2GAS24ZK",
    resource_name="HEIGHT_TEST_PLATE3",
    resource_class="Microplate",
    attributes={
        "has_lid": False,
        "lid_height": 12,
        "grab_height_offset": 3,   # 10 if gripping high to go to the OT-2
        "description": "96-well microplate with lid",
    },
)

plate = resource_client.add_or_update_resource(plate)
print(f"Plate created with attributes: {plate.resource_id}")