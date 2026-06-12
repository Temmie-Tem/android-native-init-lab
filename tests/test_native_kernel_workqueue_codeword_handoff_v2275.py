"""Regression tests for native_kernel_workqueue_codeword_handoff_v2275."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_revalidation

v2275 = load_revalidation("native_kernel_workqueue_codeword_handoff_v2275")


SLIDE = 0x100000
TARGET_STATIC = 0x1000
NON_TARGET_STATIC = 0x2000


def write_artifacts(root: Path, *, workqueue="", codeword="codeword\n", helper=""):
    root.mkdir(parents=True, exist_ok=True)
    paths = {
        "workqueue_log": root / "workqueue.cmdv1.txt",
        "codeword_log": root / "codeword.cmdv1.txt",
        "helper_result": root / "helper.cmdv1.txt",
        "summary": root / "summary.cmdv1.txt",
        "log": root / "log.cmdv1.txt",
    }
    paths["workqueue_log"].write_text(workqueue, encoding="utf-8")
    paths["codeword_log"].write_text(codeword, encoding="utf-8")
    paths["helper_result"].write_text(helper, encoding="utf-8")
    paths["summary"].write_text("", encoding="utf-8")
    paths["log"].write_text("", encoding="utf-8")
    return paths


def workqueue_log(*, result="v2273-workqueue-func-sample-ring-complete", total=2, stored=2, target=True):
    static = TARGET_STATIC if target else NON_TARGET_STATIC
    return (
        f"result={result}\n"
        f"stats total={total} stored={stored} dropped=0\n"
        f"sample index=0 kind=delayed function=0x{SLIDE + static:x} "
        "work=0xabc workqueue=0xdef pid=10 tgid=20\n"
        "sample index=1 kind=normal function=0x102080 "
        "work=0xabd workqueue=0xdf0 pid=11 tgid=21\n"
    )


def patch_codeword(*, accepted=True, slide=SLIDE):
    analysis = {
        "occupied_samples": 2,
        "capacity": 64,
        "codeword": {
            "accepted_symbolization_slide": accepted,
            "accepted_exact_codeword_slide": accepted,
            "accepted_near_exact_codeword_slide": False,
            "acceptance_reason": "unit-test",
            "best": {"slide": f"0x{slide:x}", "slide_hex": f"0x{slide:x}"},
        },
    }
    return mock.patch.multiple(
        v2275.codeword_v2216,
        parse_helper_stdout=mock.Mock(return_value={"samples": [{"pc": 1}, {"pc": 2}]}),
        analyze_probe=mock.Mock(return_value=analysis),
    )


def patch_symbol_map():
    addrs = [TARGET_STATIC, NON_TARGET_STATIC, 0x3000]
    names = ["request_firmware_work_func", "non_target_symbol", "last_symbol"]
    index = dict(zip(names, addrs))
    return mock.patch.object(v2275, "load_symbol_map", return_value=(addrs, names, index))


class ParsingHelpers(unittest.TestCase):
    def test_parse_key_values_preserves_duplicates_and_ignores_protocol_fields(self):
        values = v2275.parse_key_values(
            "A90P1 BEGIN rc=0\n"
            " helper_exit_code=20 \n"
            "helper_exit_code=0\n"
            "not-key-value\n"
            "=bad\n"
        )

        self.assertEqual(values["helper_exit_code"], ["20", "0"])
        self.assertEqual(v2275.last_value(values, "helper_exit_code"), "0")
        self.assertEqual(v2275.last_value(values, "missing", "fallback"), "fallback")
        self.assertEqual(v2275.int_value({"hex": ["0x20"]}, "hex"), 32)
        self.assertIsNone(v2275.int_value({"bad": ["not-int"]}, "bad"))
        self.assertNotIn("rc", values)

    def test_parse_workqueue_log_reads_stats_samples_and_result(self):
        parsed = v2275.parse_workqueue_log(
            "result=v2273-workqueue-func-sample-ring-complete\n"
            "stats total=0x2 stored=1 dropped=0\n"
            "sample index=0 kind=delayed function=0x101000 work=0xabc workqueue=0xdef pid=10 tgid=20\n"
            "sample index=1 kind=missing_function work=0x1\n"
        )

        self.assertEqual(parsed["result"], "v2273-workqueue-func-sample-ring-complete")
        self.assertEqual(parsed["stats"], {"total": 2, "stored": 1, "dropped": 0})
        self.assertEqual(len(parsed["samples"]), 1)
        self.assertEqual(parsed["samples"][0]["kind"], "delayed")
        self.assertEqual(parsed["samples"][0]["function"], 0x101000)

    def test_resolve_symbol_returns_containing_symbol_or_none_before_text(self):
        addrs = [0x1000, 0x2000, 0x3000]
        names = ["first", "second", "third"]

        self.assertEqual(v2275.resolve_symbol(0x2500, addrs, names)["symbol"], "second")
        self.assertEqual(v2275.resolve_symbol(0x2500, addrs, names)["offset"], 0x500)
        self.assertIsNone(v2275.resolve_symbol(0x500, addrs, names)["symbol"])


class CombinedArtifactClassification(unittest.TestCase):
    def test_classify_combined_artifacts_maps_target_hits_with_codeword_slide(self):
        helper = "wlan0_present=1\nsupervisor_result=wlan0-ready\nhelper_exit_code=0\nhelper_timed_out=0\n"
        with tempfile.TemporaryDirectory() as tmp, patch_codeword(), patch_symbol_map():
            paths = write_artifacts(Path(tmp), workqueue=workqueue_log(target=True), helper=helper)

            classification = v2275.classify_combined_artifacts(paths)

        self.assertEqual(classification["classification"], "workqueue-target-hit")
        self.assertEqual(classification["target_hit_count"], 1)
        self.assertEqual(classification["target_hits"][0]["symbol"], "request_firmware_work_func")
        self.assertEqual(classification["target_hits"][0]["function"], "0x0000000000101000")
        self.assertEqual(classification["workqueue"]["sample_count"], 2)
        self.assertEqual(classification["workqueue"]["kind_counts"], {"delayed": 1, "normal": 1})
        self.assertEqual(classification["codeword"]["slide"], SLIDE)
        self.assertTrue(classification["codeword"]["accepted_symbolization_slide"])
        self.assertEqual(classification["helper"]["supervisor_result"], "wlan0-ready")

    def test_classify_combined_artifacts_distinguishes_failure_and_no_hit_branches(self):
        cases = [
            ("", "codeword\n", True, "workqueue-log-missing"),
            (workqueue_log(result="still-running"), "codeword\n", True, "workqueue-sampler-incomplete"),
            (workqueue_log(), "", True, "codeword-log-missing"),
            (workqueue_log(), "codeword\n", False, "codeword-slide-unusable"),
            (workqueue_log(total=0, stored=0), "codeword\n", True, "workqueue-no-activity"),
            (workqueue_log(target=False), "codeword\n", True, "workqueue-no-target-hit"),
        ]

        for workqueue, codeword, accepted, expected in cases:
            with self.subTest(expected=expected):
                with tempfile.TemporaryDirectory() as tmp, patch_codeword(accepted=accepted), patch_symbol_map():
                    paths = write_artifacts(Path(tmp), workqueue=workqueue, codeword=codeword)

                    classification = v2275.classify_combined_artifacts(paths)

                self.assertEqual(classification["classification"], expected)


class CommandManifestAndReport(unittest.TestCase):
    def test_dry_run_commands_cover_verify_collect_flash_and_rollback(self):
        plan = v2275.dry_run_commands({
            "test_image_sha256": "test-sha",
            "rollback_image_sha256": "rollback-sha",
        })

        self.assertIn("--verify-only", plan["current_verify"])
        self.assertEqual(len(plan["collect"]), len(v2275.REMOTE_ARTIFACTS))
        self.assertIn("test-sha", plan["flash_test_boot"])
        self.assertIn("rollback-sha", plan["rollback"])
        self.assertEqual(len(plan["post_rollback"]), 3)

    def test_classify_manifest_covers_dry_run_and_live_branches(self):
        ready = v2275.classify_manifest({
            "execute": False,
            "preflight": {
                "build_manifest_exists": True,
                "test_image_exists": True,
                "test_image_sha_matches_manifest": True,
                "rollback_image_exists": True,
            },
        })
        blocked = v2275.classify_manifest({
            "execute": False,
            "preflight": {
                "build_manifest_exists": True,
                "test_image_exists": True,
                "test_image_sha_matches_manifest": False,
                "rollback_image_exists": True,
            },
        })

        self.assertEqual(ready["decision"], "v2275-workqueue-codeword-dry-run-ready")
        self.assertTrue(ready["pass"])
        self.assertEqual(blocked["decision"], "v2275-workqueue-codeword-dry-run-blocked")
        self.assertFalse(blocked["pass"])

        cases = [
            (
                {"execute": True, "rollback": {"selftest_ok": False}},
                "v2275-workqueue-codeword-rollback-selftest-failed",
                False,
            ),
            (
                {"execute": True, "rollback": {"selftest_ok": True}, "live_block": "preflight-current-baseline-failed"},
                "v2275-workqueue-codeword-preflight-failed-no-flash",
                False,
            ),
            (
                {"execute": True, "rollback": {"selftest_ok": True}, "live_block": "test-flash-failed"},
                "v2275-workqueue-codeword-test-flash-failed-rollback-pass",
                False,
            ),
            (
                {"execute": True, "rollback": {"selftest_ok": True}, "collect": {"classification": {"classification": "codeword-slide-unusable"}}},
                "v2275-workqueue-codeword-live-codeword-slide-unusable-rollback-pass",
                False,
            ),
            (
                {"execute": True, "rollback": {"selftest_ok": True}, "collect": {"classification": {"classification": "workqueue-no-target-hit"}}},
                "v2275-workqueue-codeword-live-pass-workqueue-no-target-hit",
                True,
            ),
            (
                {"execute": True, "rollback": {"selftest_ok": True}, "collect": {"classification": {"classification": "workqueue-target-hit"}}},
                "v2275-workqueue-codeword-live-pass-workqueue-target-hit",
                True,
            ),
        ]
        for manifest, decision, passed in cases:
            with self.subTest(decision=decision):
                classified = v2275.classify_manifest(manifest)
                self.assertEqual(classified["decision"], decision)
                self.assertEqual(classified["pass"], passed)

    def manifest(self, *, execute=False, classification="workqueue-target-hit", **overrides):
        manifest = {
            "result": {"decision": "v2275-workqueue-codeword-dry-run-ready", "pass": True, "reason": "ready"},
            "execute": execute,
            "out_dir": "workspace/private/runs/kernel/unit",
            "preflight": {
                "test_image": "workspace/private/inputs/boot_images/test.img",
                "test_image_sha256": "test-sha",
                "test_expect_version": v2275.TEST_EXPECT_VERSION,
                "rollback_image": "workspace/private/inputs/boot_images/rollback.img",
                "rollback_image_sha256": "rollback-sha",
                "rollback_expect_version": v2275.ROLLBACK_EXPECT_VERSION,
            },
            "dry_run_commands": {"collect": [["python3", "a90ctl.py", "cat", "/cache/log"]]},
            "current_preflight": {"verify_ok": True, "selftest_ok": True},
            "test_flash": {"ok": True},
            "test_health": {"version_ok": True, "status_ok": True, "selftest_ok": True},
            "rollback": {"ok": True, "attempt": "from-native", "version_ok": True, "status_ok": True, "selftest_ok": True},
            "collect": {
                "classification": {
                    "classification": classification,
                    "target_hit_count": 1 if classification == "workqueue-target-hit" else 0,
                    "target_hits": [{"symbol": "request_firmware_work_func"}] if classification == "workqueue-target-hit" else [],
                    "workqueue": {
                        "sample_count": 2,
                        "stats": {"total": 2, "stored": 2},
                        "result": "v2273-workqueue-func-sample-ring-complete",
                        "kind_counts": {"delayed": 1},
                        "symbol_counts_top": [["request_firmware_work_func", 1]],
                    },
                    "codeword": {
                        "accepted_symbolization_slide": True,
                        "slide_hex": "0x100000",
                        "acceptance_reason": "unit-test",
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

    def test_residual_state_marks_dry_run_no_touch_and_failed_rollback_cleanup(self):
        dry = v2275.residual_state({"execute": False})
        failed = v2275.residual_state({
            "execute": True,
            "steps": [{"name": "flash-v2274-from-native"}],
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

    def test_render_report_covers_dry_run_and_live_interpretation(self):
        dry_report = v2275.render_report(self.manifest(dry_run_commands={"collect": [["cat", "/cache/log"]]}))
        live_manifest = self.manifest(execute=True)
        live_manifest["result"] = {
            "decision": "v2275-workqueue-codeword-live-pass-workqueue-target-hit",
            "pass": True,
            "reason": "live pass",
        }

        live_report = v2275.render_report(live_manifest)

        self.assertIn("# Native Init V2275 Workqueue Codeword Live", dry_report)
        self.assertIn("Dry-Run Plan", dry_report)
        self.assertIn("/cache/log", dry_report)
        self.assertIn("Workqueue Classification", live_report)
        self.assertIn("Target hit count: `1`", live_report)
        self.assertIn("same-boot codeword slide classified", live_report)
        self.assertIn("Flash path is limited to boot partition", live_report)


if __name__ == "__main__":
    unittest.main()
