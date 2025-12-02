#!/usr/bin/env python3
"""Experiment application for Chris and Nidhi's substrate experiment"""

from pathlib import Path

import helper_functions
from madsci.common.types.experiment_types import ExperimentDesign
from madsci.common.types.node_types import NodeDefinition
from madsci.experiment_application import (
    ExperimentApplication,
    ExperimentApplicationConfig,
)
from pydantic import AnyUrl


class DEMOApp(ExperimentApplication):
    """Demo Experiment Application"""

    experiment_design = ExperimentDesign(
        experiment_name="DEMO_App",
    )
    config = ExperimentApplicationConfig(node_url=AnyUrl("http://localhost:6000"))

    def run_experiment(self) -> None:
        """main experiment function"""

        # define paths
        app_directory = Path(__file__).parent.parent   # experiment app
        wf_directory = app_directory / "workflows"  # workflows
        protocol_directory = app_directory / "protocols"

        # workflows
        demo_workflow = wf_directory / "demo_wf.yaml"

        # protocols
        demo_inoculate_ot2_protocol = protocol_directory / "inoculate.py"

        exp1_variables = {
            "incubation_seconds": 15,  # 15 seconds for demo
            "lid_location": "lidnest1",
            "ot2_node": "ot2_spongebob",
            "ot2_new_plate_location": "ot2_spongebob_deck1_wide",
            "ot2_old_plate_location": "ot2_spongebob_deck3_wide",
            "ot2_safe_path": "safe_path_ot2_spongebob",
            "incubator_node": "inheco_irene_2.0",
            "incubator_location": "inheco_devID2_floor0_nest",
            "tip_box_location": 4,
            "new_stack": "stack1",
            "trash_stack": "stack4",
        }

        # initial payload setup  (experiment 1 focused at start)
        payload = {
            "ot2_node": exp1_variables["ot2_node"],
            "ot2_location": exp1_variables["ot2_new_plate_location"],
            "ot2_safe_path": exp1_variables["ot2_safe_path"],
            "tip_box_location": exp1_variables["tip_box_location"],
            "incubator_node": exp1_variables["incubator_node"],
            "incubator_location": exp1_variables["incubator_location"],
            "incubation_seconds": exp1_variables["incubation_seconds"],
            "current_ot2_protocol": None,
            "use_existing_resources": False,
            "bmg_assay_name": "NIDHI",
        }

        # edit the ot-2 protocol
        ot2_replacement_variables = helper_functions.collect_ot2_replacement_variables(payload)

        print("TESTING: OT-2 replacement variables:", ot2_replacement_variables)

        temp_ot2_file_str = helper_functions.generate_ot2_protocol(demo_inoculate_ot2_protocol, ot2_replacement_variables)

        print("TESTING: temp ot2 file str:", temp_ot2_file_str)

        payload["current_ot2_protocol"] = temp_ot2_file_str

        temp_path = Path(payload["current_ot2_protocol"])

        # run the demo workflow
        workflow = self.workcell_client.submit_workflow(
            demo_workflow.resolve(),
            json_inputs={
                "lid_location": "lidnest_3_narrow",
            },
            file_inputs={"ot2_protocol": temp_path.resolve()},
        )


if __name__ == "__main__":
    app = DEMOApp(
        node_definition=NodeDefinition(
            node_name="DEMO_app", module_name="DMEO_app"
        )
    )
    app.start_app()





