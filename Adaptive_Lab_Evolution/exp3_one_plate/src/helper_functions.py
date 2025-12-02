"""Helper functions for OT-2 protocol generation and other utilities."""

import csv
import os
import tempfile

from ot2_offsets import ot2_patrick, ot2_spongebob


def generate_ot2_protocol(template_path, replacement_dict: dict) -> str:
    """Generates an OT-2 protocol by replacing variables in a template file."""

    # collect template contents and replace variables
    with template_path.open(mode="r") as f:
        edited_template_contents = f.read()
        for key in replacement_dict.keys():
            edited_template_contents = edited_template_contents.replace("$" + key, str(replacement_dict[key]))

    # write to another temp file
    output_file_name = None
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as fp:
        fp.write(edited_template_contents.encode('utf-8'))
        output_file_name = fp.name

    return output_file_name


def collect_ot2_replacement_variables(payload: dict) -> dict:
    """Collects OT-2 replacement variables based on the payload."""

    replacement_dict = {}
    if payload["ot2_node"] == "ot2_patrick":
        tip_box_location = payload["tip_box_location"]
        replacement_dict["tip_location"] = tip_box_location
        replacement_dict["x"] = ot2_patrick[tip_box_location][0]
        replacement_dict["y"] = ot2_patrick[tip_box_location][1]
        replacement_dict["z"] = ot2_patrick[tip_box_location][2]
    elif payload["ot2_node"] == "ot2_spongebob":
        tip_box_location = payload["tip_box_location"]
        replacement_dict["tip_location"] = tip_box_location
        replacement_dict["x"] = ot2_spongebob[tip_box_location][0]
        replacement_dict["y"] = ot2_spongebob[tip_box_location][1]
        replacement_dict["z"] = ot2_spongebob[tip_box_location][2]
    else:
        print("TESTING: unable to collect ot2 replacement variables")
    return replacement_dict


def write_timestamps_to_csv(
        csv_directory_path: str,
        experiment_id: str,
        bmg_filename: str,
        accurate_timestamp: str
    ):
    """Writes the more accurate timestamp data from each two plate
        substrate experiment to a file in the specified csv directory"""
    try:
        # format the file path
        csv_path = os.path.join(csv_directory_path, f"{experiment_id}.csv")

        # check if the file already exists
        already_exists = os.path.exists(csv_path)

        with open(csv_path, "a+") as f:
            csv_writer = csv.writer(f)

            # write header row if file was just created
            if not already_exists:
                csv_writer.writerow(["bmg filename", "utc timestamp"])

            # write the data to the csv
            csv_writer.writerow([bmg_filename, accurate_timestamp])


    except Exception as e:
        # DO NOT fail the experiment if data cannot write to csv file!
        print("Could not write bmg reading utc timestamp to file")
        print(e)





