import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_historical_eud_index_sweep.py"
)
SPEC = importlib.util.spec_from_file_location("p318_historical_eud_sweep_unbound", SOURCE)
assert SPEC is not None and SPEC.loader is not None
UNBOUND = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UNBOUND)
AUDIT = UNBOUND.load_bound_auditor()


class HistoricalEudIndexSweepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = AUDIT.build_receipt()

    def test_historical_indices_match_and_p318_alone_mismatches(self):
        rows = {row["campaign"]: row for row in self.receipt["campaigns"]}
        self.assertEqual(set(rows), {"p310", "p311", "p313", "p314", "p317", "p318"})
        for campaign in ("p310", "p311", "p313", "p314", "p317"):
            self.assertEqual(rows[campaign]["eud_index"], 37)
            self.assertEqual(rows[campaign]["cache_trigger_index"], 37)
            self.assertIs(rows[campaign]["index_matches"], True)
            self.assertEqual(rows[campaign]["latch_indices"], [])
            self.assertIs(rows[campaign]["cache_consumer_wrapper_bound"], True)
        self.assertEqual(rows["p318"]["eud_index"], 38)
        self.assertEqual(rows["p318"]["cache_trigger_index"], 37)
        self.assertIs(rows["p318"]["index_matches"], False)
        self.assertEqual(rows["p318"]["latch_indices"], [0])
        self.assertEqual(
            self.receipt["p317_to_p318_plan_delta"],
            {
                "p317_inherited_row_count": 69,
                "p318_row_count": 70,
                "p318_exact_latch_prefix_plus_p317": True,
            },
        )

    def test_observer_inventory_and_structural_records_are_exact(self):
        rows = {row["campaign"]: row for row in self.receipt["campaigns"]}
        self.assertEqual(
            {key: rows[key]["observer_file_count"] for key in rows},
            {"p310": 5, "p311": 4, "p313": 5, "p314": 5, "p317": 4, "p318": 4},
        )
        self.assertEqual(len(rows["p317"]["carrier_records"]), 3)
        for row in rows.values():
            self.assertIs(row["final_reads_byte_identical"], True)
            self.assertIs(row["final_observer_byte_identical"], True)
            self.assertEqual(len(row["final_observer_reads"]), 2)
            for record in row["carrier_records"]:
                self.assertIs(record["header_crc_valid"], True)
                self.assertEqual(len(record["slots"]), 2)
                self.assertTrue(all(slot["crc_valid"] is True for slot in record["slots"]))
        self.assertIn(
            "f1-2026-08-12T165954582328Z-1786553994582372233",
            rows["p317"]["final_observer_reads"][0]["path"],
        )

    def test_prior_semantic_recoveries_are_not_reclassified_by_this_sweep(self):
        conclusion = self.receipt["conclusion"]
        self.assertEqual(
            conclusion["known_prior_reviewed_semantic_mismatch_campaigns"],
            ["p311", "p313", "p318"],
        )
        self.assertEqual(conclusion["known_prior_reviewed_semantic_mismatch_cases"], 3)
        self.assertEqual(conclusion["known_prior_reviewed_semantic_mismatch_successes"], 3)
        self.assertEqual(conclusion["frozen_decoder_exposed_bad_body_cases"], 2)
        self.assertEqual(conclusion["frozen_decoder_exposed_bad_body_successes"], 2)
        self.assertIs(
            conclusion["p310_p314_p317_cross_version_agreement_audited"], False
        )
        self.assertIs(conclusion["separate_cross_version_audit_required"], True)
        self.assertEqual(conclusion["new_campaign_reclassifications"], 0)
        self.assertEqual(conclusion["p313_effective_class_remains"], "NO_PROOF_OBSERVER")
        self.assertIs(conclusion["p313_campaign_proof_correction_required"], False)
        self.assertIs(conclusion["diagnostic_bearing_yield_counts_p313_localization"], False)

    def test_module_plan_and_trigger_mutations_reject(self):
        campaign = next(row for row in AUDIT.CAMPAIGNS if row["name"] == "p318")
        paths = AUDIT._campaign_paths(campaign)
        plan = paths["plan"].read_bytes()
        runtime = paths["runtime"].read_bytes()
        wrapper = paths["wrapper"].read_bytes()
        inserted = plan.replace(
            b'    {"eud.ko", "eud", ""},\n',
            b'    {"attack.ko", "attack", ""},\n    {"eud.ko", "eud", ""},\n',
            1,
        )
        with self.assertRaisesRegex(AUDIT.SweepError, "effective module index"):
            AUDIT.audit_plan_runtime(inserted, runtime, wrapper, campaign)
        changed_trigger = runtime.replace(
            b"#define P307_EUD_MODULE_INDEX 37U",
            b"#define P307_EUD_MODULE_INDEX 38U",
            1,
        )
        with self.assertRaisesRegex(AUDIT.SweepError, "effective module index"):
            AUDIT.audit_plan_runtime(plan, changed_trigger, wrapper, campaign)
        missing_latch = plan.replace(
            b'    {"s22plus_dwc3_event_latch.ko", "s22plus_dwc3_event_latch", ""},\n',
            b"",
            1,
        )
        with self.assertRaisesRegex(AUDIT.SweepError, "effective module index"):
            AUDIT.audit_plan_runtime(missing_latch, runtime, wrapper, campaign)
        foreign_eud_path = plan.replace(
            b'{"eud.ko", "eud", ""}',
            b'{"eud.ko", "eud", "/foreign/eud.ko"}',
            1,
        )
        with self.assertRaisesRegex(AUDIT.SweepError, "effective module index"):
            AUDIT.audit_plan_runtime(foreign_eud_path, runtime, wrapper, campaign)
        foreign_latch_path = plan.replace(
            b'{"s22plus_dwc3_event_latch.ko", "s22plus_dwc3_event_latch", ""}',
            b'{"s22plus_dwc3_event_latch.ko", "s22plus_dwc3_event_latch", "/foreign/latch.ko"}',
            1,
        )
        with self.assertRaisesRegex(AUDIT.SweepError, "effective module index"):
            AUDIT.audit_plan_runtime(foreign_latch_path, runtime, wrapper, campaign)
        changed_condition = wrapper.replace(
            b"if (index == P307_EUD_MODULE_INDEX)",
            b"if (index == 38U)",
            1,
        )
        with self.assertRaisesRegex(AUDIT.SweepError, "EUD cache consumer"):
            AUDIT.audit_plan_runtime(plan, runtime, changed_condition, campaign)
        changed_call = wrapper.replace(
            b"p307_read_eud_cache()", b"p307_read_eud_cache_attack()", 1
        )
        with self.assertRaisesRegex(AUDIT.SweepError, "EUD cache consumer"):
            AUDIT.audit_plan_runtime(plan, runtime, changed_call, campaign)
        unreachable_trigger = wrapper.replace(
            b"#define S22_P241_GATE_STAGE_BASE 0x7cU",
            b"#define S22_P241_GATE_STAGE_BASE 0x60U",
            1,
        )
        with self.assertRaisesRegex(AUDIT.SweepError, "first module loop bound"):
            AUDIT.audit_plan_runtime(plan, runtime, unreachable_trigger, campaign)
        foreign_plan_include = wrapper.replace(
            b'#include "s22plus_fyg8_p286_e3_plan.h"',
            b'#include "foreign_plan.h"',
            1,
        )
        with self.assertRaisesRegex(AUDIT.SweepError, "materialized include chain"):
            AUDIT.audit_plan_runtime(plan, runtime, foreign_plan_include, campaign)
        foreign_runtime_include = wrapper.replace(
            b'#include "s22plus_fyg8_p290_e3_runtime.inc.c"',
            b'#include "foreign_runtime.inc.c"',
            1,
        )
        with self.assertRaisesRegex(AUDIT.SweepError, "materialized include chain"):
            AUDIT.audit_plan_runtime(plan, runtime, foreign_runtime_include, campaign)
        trigger_override = wrapper.replace(
            b'#include "s22plus_fyg8_p290_e3_runtime.inc.c"',
            b'#include "s22plus_fyg8_p290_e3_runtime.inc.c"\n'
            b'#define P307_EUD_MODULE_INDEX 38U',
            1,
        )
        with self.assertRaisesRegex(AUDIT.SweepError, "EUD cache consumer"):
            AUDIT.audit_plan_runtime(plan, runtime, trigger_override, campaign)
        p317 = next(row for row in AUDIT.CAMPAIGNS if row["name"] == "p317")
        p317_plan = AUDIT._campaign_paths(p317)["plan"].read_bytes()
        changed_inherited_row = plan.replace(
            b'{"i2c-msm-geni.ko", "i2c_msm_geni", ""}',
            b'{"foreign-i2c.ko", "foreign_i2c", ""}',
            1,
        )
        with self.assertRaisesRegex(AUDIT.SweepError, "exact latch-prefixed"):
            AUDIT.audit_p317_p318_plan_delta(p317_plan, changed_inherited_row)

    def test_raw_crc_and_foreign_family_mutations_reject(self):
        path = AUDIT.RUNS / (
            "p313-ready1-prepared-20260810-2/rollback-observer-1.bin"
        )
        payload = bytearray(path.read_bytes())
        offset = payload.find(AUDIT.LONG_FAMILY)
        self.assertGreaterEqual(offset, 0)
        payload[offset + AUDIT.HEADER_SIZE + AUDIT.SLOT_SIZE + 12] ^= 1
        with self.assertRaisesRegex(AUDIT.SweepError, "structurally valid slot"):
            AUDIT.decode_structural_records(bytes(payload))
        clean = path.read_bytes()
        with self.assertRaisesRegex(AUDIT.SweepError, "foreign Carrier family"):
            AUDIT.decode_structural_records(clean + AUDIT.LEGACY_FAMILIES[0])

    def test_strict_json_and_typed_identity_reference(self):
        with self.assertRaisesRegex(AUDIT.SweepError, "duplicate key"):
            AUDIT.strict_json(b'{"x":1,"x":2}', "fixture")
        with self.assertRaisesRegex(AUDIT.SweepError, "NaN"):
            AUDIT.strict_json(b'{"x":NaN}', "fixture")
        expected = {"sha256": "a" * 64, "size": 1}
        with self.assertRaisesRegex(AUDIT.SweepError, "authoritative identity"):
            AUDIT._require_identity_at_path(
                {"x": {"sha256": "a" * 64, "size": True}},
                ("x",),
                expected,
                "fixture",
            )

    def test_authoritative_receipt_paths_reject_stale_recursive_copies(self):
        p313 = next(row for row in AUDIT.CAMPAIGNS if row["name"] == "p313")
        paths = AUDIT._campaign_paths(p313)
        plan = paths["plan"].read_bytes()
        runtime = paths["runtime"].read_bytes()
        wrapper = paths["wrapper"].read_bytes()
        userspace = paths["userspace"].read_bytes()
        candidate = paths["candidate_a"].read_bytes()
        mutated_userspace = AUDIT.strict_json(userspace, "p313 fixture")
        mutated_userspace["candidate_contract"]["generated_artifacts"]["plan_header"] = {
            "sha256": "0" * 64,
            "size": 1,
        }
        with self.assertRaisesRegex(AUDIT.SweepError, "authoritative identity"):
            AUDIT.audit_package_chain(
                json.dumps(mutated_userspace).encode(),
                candidate,
                campaign=p313,
                plan_identity=AUDIT.identity(plan),
                runtime_identity=AUDIT.identity(runtime),
                wrapper_identity=AUDIT.identity(wrapper),
                userspace_identity=AUDIT.identity(userspace),
            )

        p310 = next(row for row in AUDIT.CAMPAIGNS if row["name"] == "p310")
        paths = AUDIT._campaign_paths(p310)
        plan = paths["plan"].read_bytes()
        runtime = paths["runtime"].read_bytes()
        wrapper = paths["wrapper"].read_bytes()
        userspace = paths["userspace"].read_bytes()
        mutated_userspace = AUDIT.strict_json(userspace, "p310 materialized fixture")
        mutated_userspace["candidate_contract"]["materialized_sources"][
            "runtime_wrapper"
        ]["sha256"] = "0" * 64
        with self.assertRaisesRegex(AUDIT.SweepError, "authoritative identity"):
            AUDIT.audit_package_chain(
                json.dumps(mutated_userspace).encode(),
                paths["candidate_a"].read_bytes(),
                campaign=p310,
                plan_identity=AUDIT.identity(plan),
                runtime_identity=AUDIT.identity(runtime),
                wrapper_identity=AUDIT.identity(wrapper),
                userspace_identity=AUDIT.identity(userspace),
            )
        mutated_candidate = AUDIT.strict_json(
            paths["candidate_a"].read_bytes(), "p310 fixture"
        )
        mutated_candidate["userspace_closure"]["result"] = {
            "sha256": "0" * 64,
            "size": 1,
        }
        with self.assertRaisesRegex(AUDIT.SweepError, "authoritative identity"):
            AUDIT.audit_package_chain(
                userspace,
                json.dumps(mutated_candidate).encode(),
                campaign=p310,
                plan_identity=AUDIT.identity(plan),
                runtime_identity=AUDIT.identity(runtime),
                wrapper_identity=AUDIT.identity(wrapper),
                userspace_identity=AUDIT.identity(userspace),
            )

    def test_receipt_has_no_device_authority(self):
        scope = self.receipt["scope"]
        self.assertIs(scope["host_only"], True)
        self.assertIs(scope["device_contact"], False)
        self.assertEqual(scope["adb_commands"], 0)
        self.assertEqual(scope["usb_actions"], 0)
        self.assertEqual(scope["odin_invocations"], 0)
        self.assertEqual(scope["candidate_transfers"], 0)
        self.assertEqual(scope["rollback_transfers"], 0)
        self.assertIs(scope["replay"], False)
        self.assertIs(scope["live_authority_created"], False)

    def test_live_result_binds_final_raw_identity_and_campaign_path(self):
        campaign = next(row for row in AUDIT.CAMPAIGNS if row["name"] == "p317")
        final_run = AUDIT.RUNS / campaign["final_run"]
        payload = (final_run / "live-result.json").read_bytes()
        base = AUDIT.strict_json(payload, "p317 fixture")
        attacks = (
            ("read", "sha256", "0" * 64, "final observer read"),
            (
                "read",
                "path",
                str(
                    (
                        AUDIT.RUNS
                        / "s22plus-fyg8-p318-live-1/rollback-observer-1.bin"
                    ).absolute()
                ),
                "final observer read",
            ),
            ("read", "read_to_eof", 1, "final observer read"),
            (
                "root",
                "manifest_id",
                "s22plus-fyg8-p318-process-v2-ready-1",
                "campaign identity",
            ),
        )
        for location, key, value, error in attacks:
            with self.subTest(key=key):
                mutated = json.loads(json.dumps(base))
                if location == "read":
                    mutated["live_state"]["final_evidence"]["observer"]["reads"][0][
                        key
                    ] = value
                else:
                    mutated[key] = value
                with self.assertRaisesRegex(AUDIT.SweepError, error):
                    AUDIT.audit_live_result_attribution(
                        json.dumps(mutated).encode(),
                        campaign=campaign,
                        final_run=final_run,
                    )

    def test_tracked_report_goal_and_pending_ledger_are_bounded(self):
        report = (ROOT / (
            "docs/reports/"
            "S22PLUS_FYG8_P310_P318_HISTORICAL_EUD_INDEX_SWEEP_H0_2026-08-17.md"
        )).read_text()
        goal = (ROOT / "GOAL.md").read_text()
        ledger = (ROOT / "docs/operations/CAMPAIGN_LEDGER_S22PLUS.md").read_text()
        target = (ROOT / "docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md").read_text()
        self.assertIn(
            "PASS_GO — S22PLUS_FYG8_P318_HISTORICAL_EUD_INDEX_SWEEP_"
            "H0_CAPABILITY_V2; H0 ONLY; NO LIVE AUTHORITY",
            report,
        )
        self.assertIn("P3.18 is the only checked campaign", report)
        self.assertIn(
            "known\n  prior-reviewed semantic mismatch recovery count is therefore **3/3**",
            report,
        )
        self.assertIn("that is not a semantic exemption", report)
        self.assertIn("separate host-only cross-version audit", report)
        self.assertIn("decision-bearing witness in the retained ring", report)
        self.assertIn("ACM may remain a supplemental observation channel", report)
        self.assertIn("receipt is not current review authority", report)
        self.assertIn("P3.13 needs no `CAMPAIGN_PROOF` correction", report)
        self.assertIn("Historical sweep proves\nP3.10/11/13/14/17", goal)
        self.assertIn("frozen-Carrier agreement remains a separate H0 question", goal)
        self.assertIn("keep ACM supplemental", goal)
        self.assertEqual(len(goal.splitlines()), 900)
        self.assertEqual(len(target.splitlines()), 260)
        pending = "h0-historical-eud-sweep-15"
        self.assertEqual(ledger.count(pending), 1)
        self.assertIn(
            "P310_P318_HISTORICAL_EUD_INDEX_SWEEP_IMPLEMENTED_REVIEW_PENDING",
            ledger,
        )
        review = "h0-historical-eud-sweep-review-15"
        self.assertEqual(ledger.count(review), 1)
        self.assertIn(
            "PASS_GO_P318_HISTORICAL_EUD_INDEX_SWEEP_H0_CAPABILITY_V2",
            ledger,
        )
        self.assertLess(ledger.index("h0-postlive-eud-index-review-14"), ledger.index(pending))
        self.assertLess(ledger.index(pending), ledger.index(review))

    def test_receipt_publication_normalizes_mode_and_rejects_widening(self):
        original_output = AUDIT.OUTPUT
        with tempfile.TemporaryDirectory() as directory:
            AUDIT.OUTPUT = Path(directory) / "receipt.json"
            previous = os.umask(0o777)
            try:
                AUDIT.write_receipt(self.receipt)
            finally:
                os.umask(previous)
            state = AUDIT.OUTPUT.lstat()
            self.assertEqual(stat.S_IMODE(state.st_mode), 0o400)
            self.assertEqual(state.st_nlink, 1)
            os.chmod(AUDIT.OUTPUT, 0o600)
            with self.assertRaisesRegex(AUDIT.SweepError, "identity differs"):
                AUDIT.write_receipt(self.receipt)
        AUDIT.OUTPUT = original_output

    def test_preserved_receipt_is_exact_regeneration(self):
        expected = AUDIT.encode_receipt(self.receipt)
        actual = AUDIT.OUTPUT.read_bytes()
        state = AUDIT.OUTPUT.lstat()
        self.assertEqual(actual, expected)
        self.assertEqual(stat.S_IMODE(state.st_mode), 0o400)
        self.assertEqual(state.st_nlink, 1)
        decoded = json.loads(actual.decode("utf-8"))
        self.assertEqual(decoded["schema"], "s22plus_fyg8_p318_historical_eud_index_sweep_v2")
        self.assertEqual(decoded["verdict"], AUDIT.VERDICT)


if __name__ == "__main__":
    unittest.main()
