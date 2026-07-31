#!/usr/bin/env python3
"""Master Protein Design Experiment: Golden Gate → PCR → Detect/Dilute → CFPS → FDGlu"""

import itertools
import math
import time
from datetime import datetime
from pathlib import Path

from madsci.common.types.experiment_types import ExperimentDesign
from madsci.client import ExperimentClient, WorkcellClient, LocationClient, ResourceClient
from madsci.common.types.resource_types import Resource
from madsci.experiment_application import ExperimentApplication, ExperimentApplicationConfig
from pydantic import AnyUrl


COMBINATIONS = [[1], [2, 2], [3, 3], [4, 4]]

TIPS_PER_RACK   = 96
TIPS_PER_COLUMN = 8


def _num_combos(combinations):
    total = 1
    for s in combinations:
        total *= len(s)
    return total

def _cols_needed(combinations):
    return math.ceil(_num_combos(combinations) / 8)

def wait_minutes(minutes, reason):
    total = int(minutes * 60)
    end = time.time() + total
    while time.time() < end:
        time.sleep(60)


class TipTracker:
    def __init__(self, rack_count, tips_per_rack=TIPS_PER_RACK):
        self.remaining = rack_count * tips_per_rack
        self._rack_count = rack_count
        self._tips_per_rack = tips_per_rack

    def use(self, n):        self.remaining = max(0, self.remaining - n)
    def use_cols(self, n):   self.use(n * TIPS_PER_COLUMN)
    def has(self, n):        return self.remaining >= n
    def reset(self, rack_count=None):
        if rack_count: self._rack_count = rack_count
        self.remaining = self._rack_count * self._tips_per_rack


class MasterPDApp(ExperimentApplication):

    experiment_design = ExperimentDesign(experiment_name="MasterPD_App")
    config            = ExperimentApplicationConfig(node_url=AnyUrl("http://localhost:6000"))
    experiment_client = ExperimentClient()
    workcell_client   = WorkcellClient()
    location_client   = LocationClient()
    resource_client   = ResourceClient()

    # Timing constants (minutes)
    TEMP_EQ_MIN       = 5
    GG_THERMO_MIN     = 60
    PCR_THERMO_MIN    = 45
    CFPS_INCUBATE_MIN = 150
    FDGLU_SETTLE_MIN  = 10

    def __init__(self):
        super().__init__()
        self._init_templates()
        self._plate_num = 1
        self.tips_ot2_20ul   = TipTracker(rack_count=2)
        self.tips_flex_50ul  = TipTracker(rack_count=2)
        self.tips_flex_200ul = TipTracker(rack_count=1)

    # ------------------------------------------------------------------
    # Resource helpers (unchanged from originals)
    # ------------------------------------------------------------------

    def _init_templates(self):
        defs = [
            ("opentrons_96_wellplate_200ul_pcr_full_skirt", "NEST PCR plate 200ul",
             "Template for 200ul PCR plate", ["Plate","ANSI/SLAS","96 Well","PCR","Labware"]),
            ("opentrons_96_filtertiprack_20ul", "ot2 20ul tiprack",
             "Template for ot2 20ul tiprack", ["Tiprack","ANSI/SLAS","96 Well","Labware"]),
            ("opentrons_flex_96_filtertiprack_50ul", "otflex 50ul tiprack",
             "Template for OT-Flex 50ul tiprack", ["Tiprack","ANSI/SLAS","96 Well","Labware"]),
            ("opentrons_flex_96_filtertiprack_200ul", "otflex 200ul tiprack",
             "Template for 200ul OT-Flex tiprack", ["Tiprack","ANSI/SLAS","96 Well","Labware"]),
        ]
        for template_name, desc, full_desc, tags in defs:
            self.resource_client.create_template(
                resource=Resource(resource_description=desc),
                template_name=template_name,
                description=full_desc,
                tags=tags,
            )

    def push_new_assay_plate_resource(self, plate_num, location_name, experiment_id, name):
        associated_resource_id = self.location_client.get_location_by_name(location_name).resource_id
        resource_object = self.resource_client.get_resource(associated_resource_id)
        old_plate = None
        if resource_object.child:
            popped_plate, _ = self.resource_client.pop(resource=associated_resource_id)
            old_plate = popped_plate
        new_plate = self.resource_client.create_resource_from_template(
            template_name=name,
            resource_name=f"res_{experiment_id}_plate{plate_num}",
        )
        self.resource_client.push(resource=associated_resource_id, child=new_plate.resource_id)
        return new_plate, old_plate

    def _push_plate(self, location_name, name="opentrons_96_wellplate_200ul_pcr_full_skirt"):
        new_plate, old_plate = self.push_new_assay_plate_resource(
            self._plate_num, location_name, self.experiment.experiment_id, name
        )
        self._plate_num += 1
        return new_plate, old_plate

    # ------------------------------------------------------------------
    # Tip replenishment
    # ------------------------------------------------------------------

    def _check_ot2_20ul(self, needed, transfers_dir, rack_count=2):
        if not self.tips_ot2_20ul.has(needed):
            self.workcell_client.submit_workflow(
                (transfers_dir / "replace_tip_boxes_ot2_20ul.yaml").resolve()
            )
            self.tips_ot2_20ul.reset(rack_count)

    def _check_flex_50ul(self, needed, transfers_dir, rack_count=2):
        if not self.tips_flex_50ul.has(needed):
            self.workcell_client.submit_workflow(
                (transfers_dir / "replace_tip_boxes_flex_50ul.yaml").resolve()
            )
            self.tips_flex_50ul.reset(rack_count)

    def _check_flex_200ul(self, needed, transfers_dir, rack_count=1):
        if not self.tips_flex_200ul.has(needed):
            self.workcell_client.submit_workflow(
                (transfers_dir / "replace_tip_boxes_flex_200ul.yaml").resolve()
            )
            self.tips_flex_200ul.reset(rack_count)

    # ------------------------------------------------------------------
    # run_experiment
    # ------------------------------------------------------------------

    def run_experiment(self):

        combinations = COMBINATIONS
        cols = _cols_needed(combinations)
        total_combos = _num_combos(combinations)
        sources_per_combo = max(len(s) for s in combinations)

        experiment_id   = self.experiment.experiment_id
        app_directory   = Path(__file__).parent.parent
        wf_directory    = app_directory / "workflows"
        run_dir         = wf_directory / "run_instrument"
        transfers_dir   = wf_directory / "transfers"
        protocol_dir    = app_directory / "protocols"

        run_ot2_wf  = run_dir / "run_ot2_wf.yaml"
        run_flex_wf = run_dir / "run_flex.yaml"
        run_thermo  = run_dir / "run_thermo.yaml"
        open_thermo = run_dir / "open_thermo.yaml"
        run_hidex   = run_dir / "run_hidex.yaml"

        payload = {"combinations": combinations}

        # ── Initial labware ───────────────────────────────────────────
        plate_num = 1
        for location, name in [
            ("ot2_patrick_nest4_temp_block_wide", "opentrons_96_wellplate_200ul_pcr_full_skirt"),
            ("ot2_patrick_nest1_wide",            "opentrons_96_filtertiprack_20ul"),
            ("ot2_patrick_nest3_wide",            "opentrons_96_filtertiprack_20ul"),
            ("rack_row1_nest3",                   "opentrons_96_filtertiprack_20ul"),
            ("rack_row2_nest1",                   "opentrons_96_wellplate_200ul_pcr_full_skirt"),
            ("bio_biometra3_nest",                "opentrons_96_wellplate_200ul_pcr_full_skirt"),
        ]:
            self.push_new_assay_plate_resource(plate_num, location, experiment_id, name)
            plate_num += 1
        self._plate_num = plate_num

        wait_minutes(self.TEMP_EQ_MIN, "initial temp block equilibration")

        # ══════════════════════════════════════════════════════════════
        # STAGE 1 — Golden Gate Assembly (OT-2)
        # ══════════════════════════════════════════════════════════════
        # Tips: master_mix (multi, cols cols) + combinatorial (single, total_combos*sources_per_combo)
        self._check_ot2_20ul(
            cols * TIPS_PER_COLUMN + total_combos * sources_per_combo,
            transfers_dir, rack_count=2
        )

        self.workcell_client.submit_workflow(
            run_ot2_wf.resolve(),
            file_inputs={"ot2_protocol": (protocol_dir / "pd_golden_gate_ot2_v2.py").resolve()},
            payload=payload,
        )
        self.tips_ot2_20ul.use_cols(cols)
        self.tips_ot2_20ul.use(total_combos * sources_per_combo)

        self.workcell_client.submit_workflow((transfers_dir / "ot2_to_thermocycler.yaml").resolve())
        self.workcell_client.submit_workflow(run_thermo.resolve())
        wait_minutes(self.GG_THERMO_MIN, "Golden Gate thermocycle")

        # ══════════════════════════════════════════════════════════════
        # STAGE 2 — PCR (Flex master mix + OT-2 GG dilution)
        # ══════════════════════════════════════════════════════════════
        self.workcell_client.submit_workflow((transfers_dir / "thermocycler_to_ot2.yaml").resolve())
        wait_minutes(self.TEMP_EQ_MIN, "OT-2 temp block equilibration after GG transfer")

        self.workcell_client.submit_workflow((transfers_dir / "replace_tip_boxes_ot2_pcr.yaml").resolve())
        self.tips_ot2_20ul.reset(rack_count=1)

        self.workcell_client.submit_workflow((transfers_dir / "fragments_to_flex.yaml").resolve())
        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_A4_to_B1.py").resolve()},
        )
        self.workcell_client.submit_workflow((transfers_dir / "empty_pcr_to_flex.yaml").resolve())
        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_A4_to_C1.py").resolve()},
        )

        # Flex: master mix → PCR plate (p1000 multi, cols col-tips)
        self._check_flex_200ul(cols * TIPS_PER_COLUMN, transfers_dir)
        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pd_pcr_v2_flex.py").resolve()},
            payload=payload,
        )
        self.tips_flex_200ul.use_cols(cols)

        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_C1_to_A4.py").resolve()},
        )
        self.workcell_client.submit_workflow((transfers_dir / "pcr_plate_to_ot2_block.yaml").resolve())
        self._push_plate("exchange_nest_low_narrow")
        self.workcell_client.submit_workflow((transfers_dir / "pcr_plate_to_ot2_block_2.yaml").resolve())

        # OT-2: water to GG wells + GG → PCR plate (2 × cols col-tips)
        self._check_ot2_20ul(2 * cols * TIPS_PER_COLUMN, transfers_dir, rack_count=1)
        self.workcell_client.submit_workflow(
            run_ot2_wf.resolve(),
            file_inputs={"ot2_protocol": (protocol_dir / "pd_pcr_v2_ot2.py").resolve()},
            payload=payload,
        )
        self.tips_ot2_20ul.use_cols(2 * cols)

        self.workcell_client.submit_workflow((transfers_dir / "seal_and_thermocycle_pcr.yaml").resolve())
        self.workcell_client.submit_workflow(run_thermo.resolve())
        wait_minutes(self.PCR_THERMO_MIN, "PCR thermocycle")
        self.workcell_client.submit_workflow(open_thermo.resolve())

        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_B1_to_A4.py").resolve()},
        )
        self.workcell_client.submit_workflow((transfers_dir / "fragments_flex_to_exchange.yaml").resolve())
        self._push_plate("exchange_nest_low_narrow")
        self.workcell_client.submit_workflow((transfers_dir / "remove_plates_pcr.yaml").resolve())

        # ══════════════════════════════════════════════════════════════
        # STAGE 3 — Detect & Dilute (Flex + OT-2)
        # ══════════════════════════════════════════════════════════════
        self.workcell_client.submit_workflow((transfers_dir / "thermocycler_to_flex.yaml").resolve())
        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_A4_to_C1.py").resolve()},
        )
        self.workcell_client.submit_workflow((transfers_dir / "controls_to_flex.yaml").resolve())
        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_A4_to_B1.py").resolve()},
        )
        self.workcell_client.submit_workflow((transfers_dir / "sybrgreen_to_flex.yaml").resolve())
        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_A4_to_C2.py").resolve()},
        )
        wait_minutes(self.TEMP_EQ_MIN, "Flex temp block equilibration before Detect/Dilute")

        # Flex DD: water+sybrgreen (p1000, 2 col-tips) + dilution+pcr+controls (p50, 2*cols+1 col-tips)
        self._check_flex_200ul(2 * TIPS_PER_COLUMN, transfers_dir)
        self._check_flex_50ul((2 * cols + 1) * TIPS_PER_COLUMN, transfers_dir)
        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pd_dd_v2_flex.py").resolve()},
            payload=payload,
        )
        self.tips_flex_200ul.use_cols(2)
        self.tips_flex_50ul.use_cols(2 * cols + 1)

        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_C1_to_A4.py").resolve()},
        )
        self.workcell_client.submit_workflow((transfers_dir / "pcr_plate_to_ot2_block.yaml").resolve())
        self._push_plate("exchange_nest_low_narrow")
        self.workcell_client.submit_workflow((transfers_dir / "pcr_plate_to_ot2_block_2.yaml").resolve())

        # OT-2 DD: water + pcr→water + controls (cols+2 col-tips)
        self._check_ot2_20ul((cols + 2) * TIPS_PER_COLUMN, transfers_dir, rack_count=1)
        self.workcell_client.submit_workflow(
            run_ot2_wf.resolve(),
            file_inputs={"ot2_protocol": (protocol_dir / "pd_dd_v2_ot2.py").resolve()},
            payload=payload,
        )
        self.tips_ot2_20ul.use_cols(cols + 2)

        # ══════════════════════════════════════════════════════════════
        # STAGE 4 — Cell-Free Protein Synthesis (Flex + OT-2)
        # ══════════════════════════════════════════════════════════════
        self.workcell_client.submit_workflow((transfers_dir / "rmf_mixes_to_flex.yaml").resolve())
        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_A4_to_B1.py").resolve()},
        )
        self.workcell_client.submit_workflow((transfers_dir / "empty_cfps_to_flex.yaml").resolve())
        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_A4_to_C1.py").resolve()},
        )
        wait_minutes(self.TEMP_EQ_MIN, "Flex temp block equilibration before CFPS master-mix")

        # Flex CFPS: mixA p1000 (1 col-tip) + mixA p50 (1 col-tip) + mixB p50 (1 col-tip)
        self._check_flex_200ul(TIPS_PER_COLUMN, transfers_dir)
        self._check_flex_50ul(2 * TIPS_PER_COLUMN, transfers_dir)
        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "cell_free_pd_flex_v2.py").resolve()},
            payload=payload,
        )
        self.tips_flex_200ul.use_cols(1)
        self.tips_flex_50ul.use_cols(2)

        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_C1_to_A4.py").resolve()},
        )
        self.workcell_client.submit_workflow((transfers_dir / "cfps_plate_to_ot2_block.yaml").resolve())
        self._push_plate("exchange_nest_low_narrow")
        self.workcell_client.submit_workflow((transfers_dir / "cfps_plate_to_ot2_block_2.yaml").resolve())

        # OT-2 CFPS: diluted PCR → CFPS wells (cols+1 col-tips, +1 per original code)
        self._check_ot2_20ul((cols + 1) * TIPS_PER_COLUMN, transfers_dir, rack_count=1)
        self.workcell_client.submit_workflow(
            run_ot2_wf.resolve(),
            file_inputs={"ot2_protocol": (protocol_dir / "cell_free_pd_ot2_v2.py").resolve()},
            payload=payload,
        )
        self.tips_ot2_20ul.use_cols(cols + 1)

        self.workcell_client.submit_workflow((transfers_dir / "seal_cfps_to_flex.yaml").resolve())
        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_A4_to_D1.py").resolve()},
        )
        wait_minutes(self.CFPS_INCUBATE_MIN, "CFPS incubation at 37 °C")

        # ══════════════════════════════════════════════════════════════
        # STAGE 5 — FDGlu Fluorescence Assay (Flex + OT-2)
        # ══════════════════════════════════════════════════════════════
        self.workcell_client.submit_workflow((transfers_dir / "rmf_mixes_to_flex.yaml").resolve())
        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_A4_to_B1.py").resolve()},
        )
        self.workcell_client.submit_workflow((transfers_dir / "fdglu_plate_to_flex.yaml").resolve())
        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_A4_to_B3.py").resolve()},
        )

        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_D1_to_A4.py").resolve()},
        )
        self.workcell_client.submit_workflow((transfers_dir / "cfps_plate_to_peeler_to_flex.yaml").resolve())
        self._push_plate("exchange_nest_low_narrow")
        self.workcell_client.submit_workflow((transfers_dir / "cfps_plate_to_peeler_to_flex2.yaml").resolve())

        # OT-2: RMF removal (3 single tips)
        self._check_ot2_20ul(3, transfers_dir, rack_count=1)
        self.workcell_client.submit_workflow(
            run_ot2_wf.resolve(),
            file_inputs={"ot2_protocol": (protocol_dir / "pd_fdglu_ot2_rmf_removal.py").resolve()},
        )
        self.tips_ot2_20ul.use(3)

        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_A4_to_B2.py").resolve()},
        )
        wait_minutes(self.TEMP_EQ_MIN, "CFPS plate equilibration before FDGlu dispensing")

        # Flex FDGlu: fdglu_to_plate p1000 (1 col-tip) + cfps_to_dest p50 (12 col-tips)
        self._check_flex_200ul(TIPS_PER_COLUMN, transfers_dir)
        self._check_flex_50ul(12 * TIPS_PER_COLUMN, transfers_dir)
        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pd_fdglu_flex_v2.py").resolve()},
            payload=payload,
        )
        self.tips_flex_200ul.use_cols(1)
        self.tips_flex_50ul.use_cols(12)

        # OT-2: controls to FDGlu assay plate (3 single tips)
        self._check_ot2_20ul(3, transfers_dir, rack_count=1)
        self.workcell_client.submit_workflow(
            run_ot2_wf.resolve(),
            file_inputs={"ot2_protocol": (protocol_dir / "pd_fdglu_ot2_controls_to_assay.py").resolve()},
        )
        self.tips_ot2_20ul.use(3)

        self.workcell_client.submit_workflow(
            run_flex_wf.resolve(),
            file_inputs={"flex_protocol": (protocol_dir / "pcr_B3_to_A4.py").resolve()},
        )
        self.workcell_client.submit_workflow((transfers_dir / "cfps_plate_to_peeler_to_flex.yaml").resolve())
        self.workcell_client.submit_workflow((transfers_dir / "fdglu_to_hidex.yaml").resolve())
        wait_minutes(self.FDGLU_SETTLE_MIN, "FDGlu plate settling before Hidex read")
        self.workcell_client.submit_workflow(run_hidex.resolve())


if __name__ == "__main__":
    exp_app = MasterPDApp()
    current_time = datetime.now()
    with exp_app.manage_experiment(
        run_name=f"MasterPD_{current_time.strftime('%Y%m%d_%H%M%S')}",
        run_description="Golden Gate → PCR → Detect/Dilute → CFPS → FDGlu",
    ):
        exp_app.start_app()
