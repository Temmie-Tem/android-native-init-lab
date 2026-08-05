#!/usr/bin/env python3
"""Focused tests for the P3.03 Process-v2 source and decoder binding."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


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
import s22plus_fyg8_p303_stock_log_d0 as stock_d0  # noqa: E402
import s22plus_fyg8_p303_telemetry_decoder as decoder  # noqa: E402
import s22plus_fyg8_p303_telemetry_spec as telemetry_spec  # noqa: E402


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
        acceptance = self.acceptance()
        acceptance["contract"] = {
            "candidate_static": {},
            "run_manifest": {},
            "static_check": {},
            "stock_baseline_raw": {},
            "stock_baseline_result": {},
        }
        verification = {
            "p303_stock_baseline": {
                "campaign_binding": {
                    "manifest_id": stock_binding.MANIFEST_ID,
                    "live_run_id": stock_binding.LIVE_RUN_ID,
                }
            }
        }
        process_v2.verify_p303_campaign_binding(
            acceptance,
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
                    acceptance,
                    verification,
                    manifest_id=manifest_id,
                    live_run_id=live_run_id,
                )

        clock_only = self.acceptance()
        clock_only["contract"] = {
            "candidate_static": {},
            "run_manifest": {},
            "static_check": {},
        }
        process_v2.verify_p303_campaign_binding(
            clock_only,
            {"p303_stock_baseline": None},
            manifest_id=stock_binding.MANIFEST_ID,
            live_run_id=stock_binding.LIVE_RUN_ID,
        )
        with self.assertRaisesRegex(
            process_v2.F1V2Error, "unbound stock baseline"
        ):
            process_v2.verify_p303_campaign_binding(
                clock_only,
                verification,
                manifest_id=stock_binding.MANIFEST_ID,
                live_run_id=stock_binding.LIVE_RUN_ID,
            )

    def test_stock_d0_selects_only_exact_s22_from_multi_target_inventory(self) -> None:
        inventory = """List of devices attached
A90SERIAL device product:a90 model:SM_A908N device:a90q transport_id:1
S22SERIAL device product:g0qksx model:SM_S906N device:g0q transport_id:2
"""
        self.assertEqual(
            stock_d0._exact_serial_from_inventory(inventory),
            ("S22SERIAL", 2),
        )
        with self.assertRaisesRegex(stock_d0.CaptureError, "found 2"):
            stock_d0._exact_serial_from_inventory(
                inventory
                + "S22OTHER device model:SM_S906N device:g0q transport_id:3\n"
            )

        class NoForeignCommandClient:
            def __init__(self) -> None:
                self.commands: list[tuple[str, str]] = []

            def topology(self, serial: str) -> str:
                self.commands.append(("topology", serial))
                return "usb:1-1"

            def properties(self, serial: str) -> dict[str, str]:
                self.commands.append(("properties", serial))
                return {}

        client = NoForeignCommandClient()
        with mock.patch.object(
            stock_d0,
            "_select_exact_serial",
            return_value=("REPLACEMENT_S22", 2),
        ):
            with self.assertRaisesRegex(stock_d0.CaptureError, "selection changed"):
                stock_d0._final_target_snapshot(
                    client, Path("/usr/bin/adb"), "BOUND_S22", 2
                )
        self.assertEqual(client.commands, [])

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

    def test_clock_only_classification_disables_log_causality(self) -> None:
        run_id = bytes.fromhex("00112233445566778899aabbccddeeff")
        model = decoder.model
        record = model.initialize_record(telemetry_spec.PROFILE, run_id)
        for generation, position in enumerate(
            decoder.inherited.spec.POSITIONS, 1
        ):
            if generation == telemetry_spec.CLOCK_ORDINAL + 1:
                outcome = telemetry_spec.OUTCOME_PROGRESS
                detail = telemetry_spec.encode_clock("normal", 0, 0)
            elif generation == telemetry_spec.LOG_ORDINAL + 1:
                outcome = telemetry_spec.OUTCOME_FAILURE
                detail = telemetry_spec.encode_log(
                    readback_count=0, first_offset=0, reset_mask=0
                )
            else:
                outcome = model.OUTCOME_PROGRESS
                detail = 0
            request = model.encode_request(
                telemetry_spec.PROFILE,
                position.stage,
                run_id=run_id,
                outcome=outcome,
                item_index=position.item_index,
                detail=detail,
            )
            record = model.apply_request(record, request)

        artifact = {
            "path": "workspace/private/p303-evidence.json",
            "size": 1,
            "sha256": "1" * 64,
        }
        acceptance = {
            "kind": evidence.E1_LATEST_STAGE_KIND,
            "source": evidence.CHECKPOINT_SOURCE,
            "decoder": decoder.DECODER_ID,
            "policy_id": decoder.POLICY_ID,
            "profile": telemetry_spec.PROFILE,
            "source_contract_id": overlay.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": overlay.CONTRACT_ID,
            "run_id": run_id.hex(),
            "long_family_hex": model.LONG_FAMILY.hex(),
            "unsat_family_hex": model.UNSAT_FAMILY.hex(),
            "terminal_stage": decoder.inherited.TERMINAL_POSITION[0],
            "minimum_success_count": 1,
            "clean_baseline_required": True,
            "contract": {
                name: artifact
                for name in ("candidate_static", "run_manifest", "static_check")
            },
        }
        result = evidence.classify_e1_latest_stage(record, acceptance)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["telemetry_count"], 1)
        self.assertEqual(
            result["p303_stock_baseline"],
            {
                "available": False,
                "causal_attribution_permitted": False,
                "comparisons": [],
                "comparison_count": 0,
            },
        )

    def test_ready_rehearsal_allows_clock_only_or_exact_stock_pair(self) -> None:
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
            base_arguments = [
                "--candidate-static",
                str(ROOT / adapter.DEFAULT_OUT / "candidate-static.json"),
                "--run-manifest",
                str(ROOT / adapter.DEFAULT_OUT / "run-manifest.json"),
                "--static-check",
                str(ROOT / adapter.DEFAULT_OUT / "static-check-result.json"),
                "--candidate-ap",
                str(ROOT / adapter.DEFAULT_CANDIDATE_AP),
                "--verify-only",
            ]
            self.assertEqual(ready.main(base_arguments), 0)
            self.assertFalse(output.exists())
            self.assertEqual(
                ready.main(
                    base_arguments
                    + ["--stock-baseline-raw", str(raw_path)]
                ),
                2,
            )
            self.assertFalse(output.exists())
            arguments = [
                *base_arguments[:-1],
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

    def test_direct_manifest_derivation_rejects_partial_stock_inputs(self) -> None:
        output = ROOT / adapter.DEFAULT_OUT
        run_manifest_path = output / "run-manifest.json"
        base_paths = {
            "candidate_static": output / "candidate-static.json",
            "run_manifest": run_manifest_path,
            "static_check": output / "static-check-result.json",
        }
        base_receipts = {
            name: ready.receipt(path.read_bytes())
            for name, path in base_paths.items()
        }
        stock_paths = {
            "stock_baseline_raw": ROOT / "workspace/private/raw.bin",
            "stock_baseline_result": ROOT / "workspace/private/result.json",
        }
        stock_receipts = {
            name: {"size": 1, "sha256": "1" * 64}
            for name in stock_paths
        }
        artifact = {
            "path": "workspace/private/p303/AP.tar.md5",
            "size": 1,
            "sha256": "2" * 64,
        }
        cases = (
            (
                {**base_paths, "stock_baseline_raw": stock_paths["stock_baseline_raw"]},
                {**base_receipts, "stock_baseline_raw": stock_receipts["stock_baseline_raw"]},
            ),
            (
                {**base_paths, **stock_paths},
                {**base_receipts, "stock_baseline_raw": stock_receipts["stock_baseline_raw"]},
            ),
            (
                base_paths,
                {**base_receipts, **stock_receipts},
            ),
        )
        for paths, receipts in cases:
            with self.subTest(path_keys=sorted(paths), receipt_keys=sorted(receipts)):
                with self.assertRaisesRegex(
                    ready.ManifestError, "absent or an exact pair"
                ):
                    ready.derive_manifest(
                        root=ROOT,
                        run_manifest=json.loads(
                            run_manifest_path.read_text(encoding="ascii")
                        ),
                        evidence_paths=paths,
                        evidence_receipts=receipts,
                        candidate_ap=artifact,
                        rollback_ap={**artifact, "sha256": "3" * 64},
                        target_profile=ROOT / ready.DEFAULT_TARGET_PROFILE,
                        manifest_id=ready.DEFAULT_MANIFEST_ID,
                        live_run_id=ready.DEFAULT_LIVE_RUN_ID,
                        timeout_sec=ready.DEFAULT_TIMEOUT_SEC,
                    )


if __name__ == "__main__":
    unittest.main()
