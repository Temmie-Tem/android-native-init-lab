"""Regression tests for native_kernel_workqueue_exec_stack_handoff_v2278."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_revalidation

v2278 = load_revalidation("native_kernel_workqueue_exec_stack_handoff_v2278")


SLIDE = 0x100000
TARGET_STATIC = 0x1000
NON_TARGET_STATIC = 0x2000


def write_artifacts(root: Path, *, stack="", codeword="codeword\n", helper=""):
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "workqueue_stack_log": root / "workqueue_stack.cmdv1.txt",
        "codeword_log": root / "codeword.cmdv1.txt",
        "helper_result": root / "helper.cmdv1.txt",
        "summary": root / "summary.cmdv1.txt",
        "log": root / "log.cmdv1.txt",
    }
    paths["workqueue_stack_log"].write_text(stack, encoding="utf-8")
    paths["codeword_log"].write_text(codeword, encoding="utf-8")
    paths["helper_result"].write_text(helper, encoding="utf-8")
    paths["summary"].write_text("", encoding="utf-8")
    paths["log"].write_text("", encoding="utf-8")
    return paths


def stack_log(
    *,
    result="v2277-workqueue-exec-stack-sample-ring-complete",
    total=2,
    stored=2,
    printed=2,
    target_function=True,
    target_stack=True,
    overflow=0,
):
    function_static = TARGET_STATIC if target_function else NON_TARGET_STATIC
    stack_static = TARGET_STATIC if target_stack else NON_TARGET_STATIC
    return (
        f"result={result}\n"
        f"stats total={total} stored={stored} overflow={overflow}\n"
        f"sample index=0 seq=7 pid=10 tgid=20 work=0xabc function=0x{SLIDE + function_static:x}\n"
        f"stack_ip sample=0 index=0 value=0x{SLIDE + stack_static:x} kernelish=1\n"
        "stack_ip sample=0 index=1 value=0x0 kernelish=0\n"
        + (
            f"sample index=1 seq=8 pid=11 tgid=21 work=0xabd function=0x{SLIDE + NON_TARGET_STATIC:x}\n"
            if printed > 1
            else ""
        )
    )


def patch_codeword(*, accepted=True, slide=SLIDE):
    return mock.patch.object(
        v2278,
        "analyze_codeword",
        return_value={
            "accepted": accepted,
            "slide": slide,
            "slide_hex": f"0x{slide:x}",
            "accepted_existing": False,
            "patch_aware_accepted": accepted,
            "acceptance_reason": "unit-test",
            "counts": {
                "pc_readable": 1,
                "pc_match": 0,
                "lr_prev_readable": 1,
                "lr_prev_match": 1,
                "lr_readable": 1,
                "lr_match": 1,
            },
            "mismatch_count": 1 if accepted else 0,
            "mismatch_classes": ["uao_user_alternative_str_to_sttr"] if accepted else [],
            "printed_samples": 1,
            "occupied_samples": 1,
            "capacity": 64,
        },
    )


def patch_symbols():
    return mock.patch.object(
        v2278.codeword_v2216,
        "load_text_symbols",
        return_value=[
            (TARGET_STATIC, "request_firmware_work_func"),
            (NON_TARGET_STATIC, "non_target_symbol"),
            (0x3000, "end_symbol"),
        ],
    )


class ParsingHelpers(unittest.TestCase):
    def test_parse_scalar_fields_and_int_helpers(self):
        self.assertEqual(v2278.parse_scalar_fields("total=0x2 ignored stored=3"), {"total": "0x2", "stored": "3"})
        self.assertEqual(v2278.parse_int("0x20"), 32)
        self.assertEqual(v2278.parse_int(7), 7)

    def test_parse_key_values_preserves_last_values_and_skips_protocol(self):
        values = v2278.parse_key_values(
            "A90P1 BEGIN rc=0\n"
            "helper_exit_code=20\n"
            "helper_exit_code=0\n"
            "not-key-value\n"
            "=bad\n"
        )

        self.assertEqual(values["helper_exit_code"], ["20", "0"])
        self.assertEqual(v2278.last_value(values, "helper_exit_code"), "0")
        self.assertEqual(v2278.last_value(values, "missing", "fallback"), "fallback")
        self.assertNotIn("rc", values)

    def test_parse_workqueue_stack_log_reads_stats_samples_stack_ips_and_result(self):
        parsed = v2278.parse_workqueue_stack_log(
            "result=v2277-workqueue-exec-stack-sample-ring-complete\n"
            "stats total=0x2 stored=1 overflow=0\n"
            "sample index=1 seq=7 pid=10 tgid=20 work=0xabc function=0x101000\n"
            "stack_ip sample=1 index=0 value=0x101000 kernelish=1\n"
            "stack_ip sample=1 index=1 value=0 kernelish=0\n"
            "sample seq=missing-index function=0x1\n"
        )

        self.assertEqual(parsed["result"], "v2277-workqueue-exec-stack-sample-ring-complete")
        self.assertEqual(parsed["stats"], {"total": 2, "stored": 1, "overflow": 0})
        self.assertEqual(len(parsed["samples"]), 1)
        self.assertEqual(parsed["samples"][0]["index"], 1)
        self.assertEqual(parsed["samples"][0]["function"], 0x101000)
        self.assertEqual(parsed["samples"][0]["stack_ips"][0]["value"], 0x101000)


class CodewordAndSymbolHelpers(unittest.TestCase):
    def test_symbol_resolver_returns_containing_symbol_and_none_before_text(self):
        with patch_symbols():
            resolve, symbol_index = v2278.symbol_resolver()

        self.assertEqual(symbol_index["request_firmware_work_func"], TARGET_STATIC)
        self.assertEqual(resolve(TARGET_STATIC + 0x10)["symbol"], "request_firmware_work_func")
        self.assertEqual(resolve(TARGET_STATIC + 0x10)["offset"], 0x10)
        self.assertIsNone(resolve(0x500)["symbol"])

    def test_analyze_codeword_accepts_v2276_uao_patch_aware_slide(self):
        probe = {"samples": [{"seq": 1}]}
        analysis = {
            "occupied_samples": 1,
            "capacity": 64,
            "codeword": {
                "accepted_symbolization_slide": False,
                "accepted_exact_codeword_slide": False,
                "best": {"slide": f"0x{SLIDE:x}", "slide_hex": f"0x{SLIDE:x}"},
            },
        }
        counts = {
            "pc_readable": 1,
            "pc_match": 0,
            "lr_prev_readable": 1,
            "lr_prev_match": 1,
            "lr_readable": 1,
            "lr_match": 1,
        }
        with mock.patch.multiple(
            v2278.codeword_v2216,
            parse_helper_stdout=mock.Mock(return_value=probe),
            analyze_probe=mock.Mock(return_value=analysis),
        ), mock.patch.object(
            v2278.v2276,
            "mismatch_rows",
            return_value=([{"uao_patch_class": "uao_user_alternative_str_to_sttr"}], counts),
        ):
            result = v2278.analyze_codeword("helper stdout")

        self.assertTrue(result["accepted"])
        self.assertTrue(result["patch_aware_accepted"])
        self.assertEqual(result["acceptance_reason"], "uao_patch_aware")
        self.assertEqual(result["mismatch_count"], 1)
        self.assertEqual(result["mismatch_classes"], ["uao_user_alternative_str_to_sttr"])


class ArtifactClassification(unittest.TestCase):
    def test_classify_artifacts_reports_function_and_stack_target_hits(self):
        helper = "wlan0_present=1\nsupervisor_result=wlan0-ready\nhelper_exit_code=0\nhelper_timed_out=0\n"
        with tempfile.TemporaryDirectory() as tmp, patch_codeword(), patch_symbols():
            paths = write_artifacts(
                Path(tmp),
                stack=stack_log(target_function=True, target_stack=True),
                helper=helper,
            )

            classification = v2278.classify_artifacts(paths)

        self.assertEqual(classification["classification"], "workqueue-exec-stack-target-hit")
        self.assertEqual(classification["target_hit_count"], 2)
        self.assertEqual(classification["function_target_hit_count"], 1)
        self.assertEqual(classification["stack_target_hit_count"], 1)
        self.assertEqual(classification["function_target_hits"][0]["function_symbol"], "request_firmware_work_func")
        self.assertEqual(classification["stack_target_hits"][0]["symbol"], "request_firmware_work_func")
        self.assertEqual(classification["workqueue"]["sample_count"], 2)
        self.assertEqual(classification["codeword"]["slide"], SLIDE)
        self.assertEqual(classification["helper"]["supervisor_result"], "wlan0-ready")

    def test_classify_artifacts_covers_reject_no_activity_and_partial_branches(self):
        cases = [
            ("", "codeword\n", True, "workqueue-stack-log-missing"),
            (stack_log(result="still-running"), "codeword\n", True, "workqueue-stack-sampler-incomplete"),
            (stack_log(), "", True, "codeword-log-missing"),
            (stack_log(), "codeword\n", False, "codeword-slide-unusable"),
            (stack_log(total=0, stored=0), "codeword\n", True, "workqueue-stack-no-activity"),
            (stack_log(target_function=False, target_stack=False), "codeword\n", True, "workqueue-exec-stack-no-target-hit"),
            (
                stack_log(total=3, stored=3, printed=1, target_function=False, target_stack=False, overflow=1),
                "codeword\n",
                True,
                "workqueue-exec-stack-no-target-hit-partial-coverage",
            ),
        ]

        for stack, codeword, accepted, expected in cases:
            with self.subTest(expected=expected):
                with tempfile.TemporaryDirectory() as tmp, patch_codeword(accepted=accepted), patch_symbols():
                    paths = write_artifacts(Path(tmp), stack=stack, codeword=codeword)

                    classification = v2278.classify_artifacts(paths)

                self.assertEqual(classification["classification"], expected)


class ManifestReportAndResidual(unittest.TestCase):
    def test_dry_run_commands_cover_verify_collect_flash_and_rollback(self):
        plan = v2278.dry_run_commands({
            "test_image_sha256": "test-sha",
            "rollback_image_sha256": "rollback-sha",
        })

        self.assertIn("--verify-only", plan["current_verify"])
        self.assertEqual(len(plan["collect"]), len(v2278.REMOTE_ARTIFACTS))
        self.assertIn("test-sha", plan["flash_test_boot"])
        self.assertIn("rollback-sha", plan["rollback"])

    def test_classify_manifest_covers_dry_run_live_failure_and_success_branches(self):
        ready = v2278.classify_manifest({
            "execute": False,
            "preflight": {
                "build_manifest_exists": True,
                "test_image_exists": True,
                "test_image_sha_matches_manifest": True,
                "rollback_image_exists": True,
            },
        })
        blocked = v2278.classify_manifest({
            "execute": False,
            "preflight": {
                "build_manifest_exists": True,
                "test_image_exists": False,
                "test_image_sha_matches_manifest": True,
                "rollback_image_exists": True,
            },
        })

        self.assertEqual(ready["decision"], "v2278-workqueue-exec-stack-dry-run-ready")
        self.assertTrue(ready["pass"])
        self.assertEqual(blocked["decision"], "v2278-workqueue-exec-stack-dry-run-blocked")
        self.assertFalse(blocked["pass"])

        cases = [
            (
                {"execute": True, "rollback": {"selftest_ok": False}},
                "v2278-workqueue-exec-stack-rollback-selftest-failed",
                False,
            ),
            (
                {"execute": True, "rollback": {"selftest_ok": True}, "live_block": "preflight-current-baseline-failed"},
                "v2278-workqueue-exec-stack-preflight-failed-no-flash",
                False,
            ),
            (
                {"execute": True, "rollback": {"selftest_ok": True}, "live_block": "test-flash-failed"},
                "v2278-workqueue-exec-stack-test-flash-failed-rollback-pass",
                False,
            ),
            (
                {"execute": True, "rollback": {"selftest_ok": True}, "collect": {"classification": {"classification": "codeword-slide-unusable"}}},
                "v2278-workqueue-exec-stack-live-codeword-slide-unusable-rollback-pass",
                False,
            ),
            (
                {"execute": True, "rollback": {"selftest_ok": True}, "collect": {"classification": {"classification": "workqueue-exec-stack-no-target-hit"}}},
                "v2278-workqueue-exec-stack-live-pass-workqueue-exec-stack-no-target-hit",
                True,
            ),
            (
                {"execute": True, "rollback": {"selftest_ok": True}, "collect": {"classification": {"classification": "workqueue-exec-stack-target-hit"}}},
                "v2278-workqueue-exec-stack-live-pass-workqueue-exec-stack-target-hit",
                True,
            ),
        ]
        for manifest, decision, passed in cases:
            with self.subTest(decision=decision):
                classified = v2278.classify_manifest(manifest)
                self.assertEqual(classified["decision"], decision)
                self.assertEqual(classified["pass"], passed)

    def manifest(self, *, execute=False, classification="workqueue-exec-stack-target-hit", **overrides):
        manifest = {
            "result": {"decision": "v2278-workqueue-exec-stack-dry-run-ready", "pass": True, "reason": "ready"},
            "execute": execute,
            "out_dir": "workspace/private/runs/kernel/unit",
            "preflight": {
                "test_image": "workspace/private/inputs/boot_images/test.img",
                "test_image_sha256": "test-sha",
                "test_expect_version": v2278.TEST_EXPECT_VERSION,
                "rollback_image": "workspace/private/inputs/boot_images/rollback.img",
                "rollback_image_sha256": "rollback-sha",
                "rollback_expect_version": v2278.ROLLBACK_EXPECT_VERSION,
            },
            "dry_run_commands": {"collect": [["python3", "a90ctl.py", "cat", "/cache/log"]]},
            "current_preflight": {"verify_ok": True, "selftest_ok": True},
            "test_flash": {"ok": True},
            "test_health": {"version_ok": True, "status_ok": True, "selftest_ok": True},
            "rollback": {"ok": True, "attempt": "from-native", "version_ok": True, "status_ok": True, "selftest_ok": True},
            "collect": {
                "classification": {
                    "classification": classification,
                    "target_hit_count": 2 if classification == "workqueue-exec-stack-target-hit" else 0,
                    "function_target_hit_count": 1 if classification == "workqueue-exec-stack-target-hit" else 0,
                    "stack_target_hit_count": 1 if classification == "workqueue-exec-stack-target-hit" else 0,
                    "function_target_hits": [{"function_symbol": "request_firmware_work_func"}] if classification == "workqueue-exec-stack-target-hit" else [],
                    "stack_target_hits": [{"symbol": "request_firmware_work_func"}] if classification == "workqueue-exec-stack-target-hit" else [],
                    "workqueue": {
                        "sample_count": 2,
                        "stats": {"total": 2, "stored": 2},
                        "result": "v2277-workqueue-exec-stack-sample-ring-complete",
                        "function_symbol_counts_top": [["request_firmware_work_func", 1]],
                        "stack_symbol_counts_top": [["request_firmware_work_func", 1]],
                    },
                    "codeword": {
                        "accepted": True,
                        "slide_hex": "0x100000",
                        "acceptance_reason": "unit-test",
                        "patch_aware_accepted": True,
                    },
                    "helper": {
                        "supervisor_result": "wlan0-ready",
                        "helper_exit_code": "0",
                        "helper_timed_out": "0",
                        "wlan0_present": "1",
                    },
                }
            },
        }
        manifest.update(overrides)
        return manifest

    def test_render_report_covers_dry_run_and_live_interpretation(self):
        dry_report = v2278.render_report(self.manifest(dry_run_commands={"collect": [["cat", "/cache/log"]]}))
        live_manifest = self.manifest(execute=True)
        live_manifest["result"] = {
            "decision": "v2278-workqueue-exec-stack-live-pass-workqueue-exec-stack-target-hit",
            "pass": True,
            "reason": "live pass",
        }

        live_report = v2278.render_report(live_manifest)

        self.assertIn("# Native Init V2278 Workqueue Execute Stack Live", dry_report)
        self.assertIn("Dry-Run Plan", dry_report)
        self.assertIn("/cache/log", dry_report)
        self.assertIn("Workqueue Stack Classification", live_report)
        self.assertIn("Target hits: total=`2` function=`1` stack=`1`", live_report)
        self.assertIn("same-boot stack/callsite oracle intersects", live_report)
        self.assertIn("Flash path is limited to boot partition", live_report)

    def test_residual_state_marks_dry_run_no_touch_and_failed_rollback_cleanup(self):
        dry = v2278.residual_state({"execute": False})
        failed = v2278.residual_state({
            "execute": True,
            "steps": [{"name": "flash-v2277-from-native"}],
            "test_flash": {"ok": True},
            "rollback": {"ok": False, "selftest_ok": False, "attempt": "from-recovery"},
        })

        self.assertFalse(dry["device_touched"])
        self.assertEqual(dry["rollback_attempt"], "not-needed-no-flash")
        self.assertTrue(dry["selftest_ok"])
        self.assertTrue(failed["device_touched"])
        self.assertTrue(failed["cleanup_required"])
        self.assertEqual(failed["residual_risk"], "rollback-or-selftest-incomplete")
        self.assertTrue(failed["partition_write"])


if __name__ == "__main__":
    unittest.main()
