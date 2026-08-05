#!/usr/bin/env python3
"""Focused tests for P3.03 HS-PHY telemetry and callsite proof."""

from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p303_callsite_audit as audit  # noqa: E402
import s22plus_fyg8_p301_overlay_contract as parent  # noqa: E402
import s22plus_fyg8_p303_telemetry_generator as generator  # noqa: E402
import s22plus_fyg8_p303_telemetry_decoder as decoder  # noqa: E402
import s22plus_fyg8_p303_telemetry_spec as spec  # noqa: E402
import s22plus_fyg8_p303_stock_log_baseline as stock_log  # noqa: E402
import s22plus_fyg8_p303_stock_log_baseline_binding as stock_binding  # noqa: E402


class P303TelemetryTests(unittest.TestCase):
    def test_descriptor_and_exact_ranges(self) -> None:
        result = spec.validate()
        self.assertTrue(result["verified"])
        self.assertEqual(result["callsite_count"], 12)
        self.assertEqual(result["clock_value_count"], 163)
        self.assertEqual(result["log_value_count"], 2048)
        self.assertEqual(spec.CLOCK_DETAIL_MAX, 0xDA2)
        self.assertEqual(spec.LOG_DETAIL_MAX, 0x4800)

    def test_clock_round_trip_and_missed_is_distinct_from_zero(self) -> None:
        self.assertEqual(spec.decode_clock(spec.encode_clock_missed())["branch"], "missed")
        for branch in ("eud", "normal"):
            for source in range(spec.CLOCK_RESULT_STATES):
                for ref in range(spec.CLOCK_RESULT_STATES):
                    detail = spec.encode_clock(branch, source, ref)
                    self.assertEqual(
                        spec.decode_clock(detail),
                        {"branch": branch, "ref_src_state": source, "ref_state": ref},
                    )

    def test_callsite_classifier_separates_hits_and_returns(self) -> None:
        self.assertEqual(spec.classify_clock([0] * 12, [0] * 12), 0xD00)
        self.assertEqual(
            spec.CONTRADICTION_DETAIL_NAMES[
                spec.DETAIL_CLOCK_INIT_PATH_CONTRADICTION
            ],
            "hsphy-init-path-contradiction",
        )
        hits = [0] * 12
        hits[6] = hits[7] = hits[8] = hits[9] = 1
        detail = spec.classify_clock(hits, [0] * 12)
        self.assertEqual(
            spec.decode_clock(detail),
            {"branch": "normal", "ref_src_state": 0, "ref_state": 0},
        )
        prepare_failed = hits.copy()
        prepare_failed[7] = 0
        returns = [0] * 12
        returns[6] = -5
        detail = spec.classify_clock(prepare_failed, returns)
        self.assertEqual(spec.decode_clock(detail)["ref_src_state"], 2)
        self.assertEqual(
            spec.classify_clock([2] + [0] * 11, [0] * 12),
            spec.DETAIL_CALLSITE_COUNT_CONTRADICTION,
        )

    def test_kmsg_round_trip(self) -> None:
        for count, offset, mask in ((0, 0, 0), (1, 0x24, 1), (3, 0x7C, 2), (8, 0x114, 3)):
            detail = spec.encode_log(
                readback_count=count, first_offset=offset, reset_mask=mask
            )
            decoded = spec.decode_log(detail)
            self.assertEqual(decoded["first_offset"], offset)
            self.assertEqual(decoded["count_bucket"], spec.readback_count_bucket(count))
            self.assertEqual(decoded["reset_mask"], mask)

    def test_stock_log_baseline_uses_candidate_summary_domain(self) -> None:
        payload = (
            b"phy-msm-snps-hs msm_hsphy_enable_clocks(): on = 1\n"
            b"msm_usb_write_readback: write: 4 to QSCRATCH: 24 FAILED\n"
            b"phy_reset deassert failed\n"
        )
        result = stock_log.parse(payload)
        self.assertTrue(result["valid"])
        self.assertEqual(result["readback_failure_count"], 1)
        self.assertEqual(result["first_readback_failure_offset"], 0x24)
        self.assertEqual(result["reset_failure_mask"], 2)
        self.assertEqual(
            result["candidate_domain_detail"],
            spec.encode_log(readback_count=1, first_offset=0x24, reset_mask=2),
        )
        with self.assertRaises(stock_log.BaselineError):
            stock_log.parse(b"unrelated stock log\n")
        same = decoder.compare_stock_baseline(
            result["candidate_domain_detail"], result
        )
        self.assertEqual(
            same["classification"],
            "CANDIDATE_SIGNATURE_PRESENT_IN_WORKING_STOCK",
        )
        self.assertFalse(same["candidate_failure_attributable"])
        clean = decoder.compare_stock_baseline(
            spec.encode_log(readback_count=0, first_offset=0, reset_mask=0),
            result,
        )
        self.assertEqual(clean["classification"], "CANDIDATE_LOGGED_PATHS_CLEAN")

    def test_bound_stock_baseline_requires_input_and_boot_window(self) -> None:
        raw = (
            b"[    0.000000] Linux version exact-stock\n"
            b"[    0.750000] phy-msm-snps-hs msm_hsphy_enable_clocks(): on = 1\n"
            b"[    1.000000] stock baseline complete\n"
        )
        private = ROOT / "workspace/private"
        with tempfile.TemporaryDirectory(prefix="p303-stock-test-", dir=private) as name:
            run = Path(name)
            raw_path = run / "stock-dmesg.bin"
            raw_path.write_bytes(raw)
            target = {
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
            }
            health = {
                "android_boot_completed": True,
                "root_verified": True,
                "boot_id_sha256": "3" * 64,
            }
            value = stock_binding.build_result(
                ROOT,
                raw_path,
                raw,
                target_evidence=target,
                health=health,
                adb_receipt={"sha256": "4" * 64, "size": 1},
                module_observation={
                    "observed_sha256": stock_binding.MODULE_SHA256,
                    "sha256sum_stdout": {"sha256": "5" * 64, "size": 96},
                    "verified": True,
                },
            )
            payload = (
                json.dumps(value, indent=2, sort_keys=True).encode("ascii") + b"\n"
            )
            relative = raw_path.relative_to(ROOT).as_posix()
            verified = stock_binding.verify_payloads(
                ROOT, raw, payload, expected_raw_path=relative
            )
            self.assertTrue(verified["boot_window_complete"])
            self.assertEqual(verified["baseline"]["input"]["path"], relative)
            changed = json.loads(payload.decode("ascii"))
            del changed["baseline"]["input"]
            changed_payload = json.dumps(changed, sort_keys=True).encode("ascii")
            with self.assertRaises(stock_binding.BindingError):
                stock_binding.verify_payloads(
                    ROOT, raw, changed_payload, expected_raw_path=relative
                )
        with self.assertRaises(stock_binding.BindingError):
            stock_binding.summarize_raw(
                b"msm_hsphy_enable_clocks(): marker-only-truncated\n"
            )
        with self.assertRaises(stock_binding.BindingError):
            stock_binding.summarize_raw(
                b"[    2.000000] msm_hsphy_enable_clocks(): late-only\n"
            )

    def test_materialized_checkpoint_accepts_p303_failure_bands(self) -> None:
        materialized = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p303/intent/"
            "materialized-sources"
        )
        header = (materialized / "s22plus_r4w1e_checkpoint.h").read_text(
            encoding="ascii"
        )
        client = (materialized / "s22plus_fyg8_p290_checkpoint.c").read_text(
            encoding="ascii"
        )
        self.assertIn("S22_P292_PUBLICATION_OPEN_BASE 0x4000U", header)
        self.assertIn("S22_P292_PUBLICATION_CLOSE_BASE 0x6000U", header)
        self.assertIn("S22_P292_PUBLICATION_ERRNO_MAX 0xfffL", header)
        wide = client.index("detail > S22_P292_PUBLICATION_OPEN_BASE")
        exact = client.index("sizeof(k_p288_detail_rules)")
        terminal = client.index("step->kind == S22_P248_STEP_TERMINAL")
        self.assertLess(wide, exact)
        self.assertLess(wide, terminal)
        for detail in (0x4001, 0x4800, 0x4FFF, 0x6001, 0x600F, 0x6FFF):
            base = 0x4000 if detail < 0x5000 else 0x6000
            self.assertTrue(base < detail <= base + 0xFFF)

    def test_exact_module_callsite_audit(self) -> None:
        result = audit.audit(
            ROOT,
            Path(spec.MODULE_PATH),
            "aarch64-linux-gnu-objdump",
            "readelf",
        )
        self.assertTrue(result["verified"])
        self.assertEqual(result["callsite_count"], 12)
        self.assertTrue(all(row["w0_unconsumed_at_probe"] for row in result["callsites"]))
        self.assertTrue(result["a_b_offset_identity"]["runtime_module_shared"])
        self.assertEqual(
            result["a_b_offset_identity"]["descriptor_offset_count"], 12
        )

    def test_generated_userspace_delta_keeps_fixed_kernel(self) -> None:
        exact = parent.verify_parent(ROOT)
        generated = generator.generate_bytes(
            ROOT,
            run_id=bytes.fromhex(exact["run_id"]),
            unsat_tag=bytes.fromhex(exact["unsat_tag_hex"]),
            profile=exact["profile"],
        )
        inherited = parent.generated_bytes(ROOT, exact)
        changed = {key for key in generated if generated[key] != inherited[key]}
        self.assertEqual(changed, generator.P301_DELTA_KEYS)
        self.assertEqual(generated["candidate_patch"], inherited["candidate_patch"])
        header = generated["trace_descriptor_header"]
        self.assertIn(b"#define P282_CYCLE_EVENT_COUNT 28U", header)
        self.assertEqual(header.count(b"msm_hsphy_init+0x"), 12)
        runtime = generated["p290_e3_runtime_include"]
        init_guard = runtime.index(b"!result->phy_init.entered")
        profile_guard = runtime.index(b"control->profile_hits[16U + index]")
        all_missed = runtime.index(b"if (!eud_active && !normal_active)")
        self.assertLess(init_guard, profile_guard)
        self.assertLess(profile_guard, all_missed)


if __name__ == "__main__":
    unittest.main()
