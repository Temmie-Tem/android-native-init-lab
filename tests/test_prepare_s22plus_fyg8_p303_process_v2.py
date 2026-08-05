#!/usr/bin/env python3
"""Focused tests for the P3.03 Process-v2 source and decoder binding."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPT_DIR))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_v2 as process_v2  # noqa: E402
import prepare_s22plus_fyg8_p303_process_v2 as adapter  # noqa: E402
import prepare_s22plus_fyg8_p303_ready_manifest as ready  # noqa: E402
import s22plus_fyg8_p301_overlay_contract as parent_overlay  # noqa: E402
import s22plus_fyg8_p303_overlay_contract as overlay  # noqa: E402
import s22plus_fyg8_p303_stock_log_baseline_binding as stock_binding  # noqa: E402
import s22plus_fyg8_p303_telemetry_decoder as decoder  # noqa: E402


class P303ProcessV2OverlayTest(unittest.TestCase):
    def acceptance(self) -> dict[str, str]:
        return {
            "kind": evidence.E1_LATEST_STAGE_KIND,
            "profile": overlay.PROFILE,
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
        }

    def test_decoder_selection_and_terminal_inheritance(self) -> None:
        selected = evidence._latest_stage_observation_decoder(
            overlay.PARENT_SOURCE_CONTRACT_ID,
            overlay.PROFILE,
            overlay.CONTRACT_ID,
        )
        self.assertIs(selected, decoder)
        self.assertEqual(
            evidence._latest_stage_terminal(selected, overlay.PROFILE),
            decoder.inherited.TERMINAL_POSITION[0],
        )

    def test_defaults_and_promoted_evidence_are_p303_bound(self) -> None:
        args = adapter.parse_args([])
        ready_args = ready.parse_args([])
        self.assertTrue(
            all(
                "s22plus_fyg8_p303" in value.as_posix()
                for value in (args.candidate_static, args.candidate_ap, args.out)
            )
        )
        self.assertTrue(
            all(
                "s22plus_fyg8_p303" in value.as_posix()
                for value in (
                    ready_args.candidate_static,
                    ready_args.run_manifest,
                    ready_args.static_check,
                    ready_args.candidate_ap,
                    ready_args.out,
                )
            )
        )
        output = ROOT / adapter.DEFAULT_OUT
        for name in ("run-manifest.json", "static-check-result.json"):
            value = json.loads((output / name).read_text(encoding="ascii"))
            self.assertEqual(
                value["userspace_overlay_contract_id"], overlay.CONTRACT_ID
            )
            self.assertEqual(
                value["source_contract_id"], overlay.PARENT_SOURCE_CONTRACT_ID
            )
            self.assertEqual(value["decoder"], decoder.DECODER_ID)
            self.assertEqual(value["policy_id"], decoder.POLICY_ID)

    def test_execution_receipts_bind_parent_and_p303_sources(self) -> None:
        receipts = process_v2.execution_critical_source_receipts(self.acceptance())
        p301 = {
            name: value
            for name, value in receipts.items()
            if name.startswith("p301_overlay_source_")
        }
        p303 = {
            name: value
            for name, value in receipts.items()
            if name.startswith("p303_overlay_source_")
        }
        self.assertEqual(len(p301), len(parent_overlay.SOURCE_KEYS))
        self.assertEqual(len(p303), len(overlay.SOURCE_KEYS))
        self.assertIn("p301_overlay_intent", receipts)
        self.assertIn("p303_overlay_intent", receipts)
        self.assertIn("p303_stock_baseline_binding", receipts)
        self.assertIn("p303_stock_log_d0", receipts)

    def test_execution_binding_rejects_parent_or_p303_source_drift(self) -> None:
        contract = overlay.verify_intent(ROOT, ROOT / overlay.DEFAULT_INTENT)
        verification = {
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
            "candidate_source_receipts": evidence.validate_candidate_source_preimage(
                contract["parent_candidate_contract"],
                overlay.PROFILE,
                contract["run_id"],
            ),
            "p301_overlay_source_receipts": contract["parent_overlay_contract"][
                "source_receipts"
            ],
            "p303_overlay_source_receipts": contract["source_receipts"],
        }
        execution = process_v2.execution_critical_source_receipts(self.acceptance())
        process_v2.verify_candidate_source_binding(
            self.acceptance(), verification, execution
        )
        for prefix, keys in (
            ("p301", parent_overlay.SOURCE_KEYS),
            ("p303", overlay.SOURCE_KEYS),
        ):
            changed = copy.deepcopy(execution)
            first = sorted(keys)[0]
            changed[f"{prefix}_overlay_source_{first}"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(
                process_v2.F1V2Error, "overlay source differs"
            ):
                process_v2.verify_candidate_source_binding(
                    self.acceptance(), verification, changed
                )

    def test_campaign_binding_matches_outer_manifest_and_live_run(self) -> None:
        verification = {
            "p303_stock_baseline": {
                "campaign_binding": {
                    "manifest_id": stock_binding.MANIFEST_ID,
                    "live_run_id": stock_binding.LIVE_RUN_ID,
                }
            }
        }
        process_v2.verify_p303_campaign_binding(
            self.acceptance(),
            verification,
            manifest_id=stock_binding.MANIFEST_ID,
            live_run_id=stock_binding.LIVE_RUN_ID,
        )
        for manifest_id, live_run_id in (
            ("s22plus-fyg8-p303-other", stock_binding.LIVE_RUN_ID),
            (stock_binding.MANIFEST_ID, "s22plus-fyg8-p303-other"),
        ):
            with self.assertRaisesRegex(
                process_v2.F1V2Error, "different campaign"
            ):
                process_v2.verify_p303_campaign_binding(
                    self.acceptance(),
                    verification,
                    manifest_id=manifest_id,
                    live_run_id=live_run_id,
                )

    def test_static_result_binds_post_bl_and_hit_zero_contract(self) -> None:
        result = json.loads(
            (ROOT / adapter.DEFAULT_STATIC).read_text(encoding="ascii")
        )
        self.assertEqual(result["p303_callsite_audit"]["callsite_count"], 12)
        self.assertTrue(
            all(
                row["w0_unconsumed_at_probe"]
                for row in result["p303_callsite_audit"]["callsites"]
            )
        )
        self.assertTrue(
            result["p303_offset_probe_rule"]["p300_epilogue_rejection_preserved"]
        )
        self.assertTrue(
            result["p303_offset_probe_rule"]["hit_zero_distinct_from_rc_zero"]
        )

    def test_ready_rehearsal_requires_and_binds_complete_stock_baseline(self) -> None:
        raw = (
            b"[    0.000000] exact stock boot start\n"
            b"[    0.500000] phy-msm-snps-hs msm_hsphy_enable_clocks(): on = 1\n"
            b"[    1.000000] exact stock capture end\n"
        )
        private = ROOT / "workspace/private"
        with tempfile.TemporaryDirectory(prefix="p303-ready-stock-", dir=private) as name:
            directory = Path(name)
            raw_path = directory / "stock-dmesg.bin"
            result_path = directory / "stock-hsphy-baseline.json"
            raw_path.write_bytes(raw)
            value = stock_binding.build_result(
                ROOT,
                raw_path,
                raw,
                target_evidence={
                    "schema": "device_action_f1_target_evidence_v2",
                    "targets": [{
                        "model": "SM-S906N",
                        "device": "g0q",
                        "firmware_incremental": "S906NKSS7FYG8",
                        "android_transport": "adb",
                        "adb_serial_sha256": "1" * 64,
                        "usb_topology_sha256": "2" * 64,
                    }],
                    "odin_endpoint_absent": True,
                },
                health={
                    "android_boot_completed": True,
                    "root_verified": True,
                    "boot_id_sha256": "3" * 64,
                },
                adb_receipt={"sha256": "4" * 64, "size": 1},
                module_observation={
                    "observed_sha256": stock_binding.MODULE_SHA256,
                    "sha256sum_stdout": {"sha256": "5" * 64, "size": 96},
                    "verified": True,
                },
            )
            result_path.write_text(
                json.dumps(value, indent=2, sort_keys=True) + "\n",
                encoding="ascii",
            )
            output = ROOT / ready.DEFAULT_OUT
            self.assertFalse(output.exists())
            arguments = [
                "--candidate-static",
                str(ROOT / adapter.DEFAULT_OUT / "candidate-static.json"),
                "--run-manifest",
                str(ROOT / adapter.DEFAULT_OUT / "run-manifest.json"),
                "--static-check",
                str(ROOT / adapter.DEFAULT_OUT / "static-check-result.json"),
                "--candidate-ap",
                str(ROOT / adapter.DEFAULT_CANDIDATE_AP),
                "--stock-baseline-raw",
                str(raw_path),
                "--stock-baseline-result",
                str(result_path),
                "--verify-only",
            ]
            self.assertEqual(
                ready.main(
                    arguments
                    + ["--manifest-id", "s22plus-fyg8-p303-other"]
                ),
                2,
            )
            self.assertFalse(output.exists())
            rc = ready.main(arguments)
            self.assertEqual(rc, 0)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
