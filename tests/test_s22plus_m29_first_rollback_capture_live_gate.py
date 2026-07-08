import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m29_first_rollback_capture_live_gate.py")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m28_dep_complete_download_v0_1/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m29_first_rollback_capture_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM29FirstRollbackCaptureLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_marker_check_requires_new_m29_authorization(self):
        missing = self.module.missing_policy_markers(
            "S22+ M29 first-rollback retained-log capture boot+DTBO"
        )
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn(self.module.RESTORE_DTBO_ACK_TOKEN, missing)
        self.assertIn("first rollback boot capture before stock DTBO rollback", missing)
        self.assertIn("pre-candidate retained-log baseline capture", missing)
        self.assertIn("/proc/reset_summary", missing)
        self.assertIn("F43 remains unauthorized", missing)

    def test_current_agents_file_retires_m29_live_gate_policy(self):
        agents = Path("AGENTS.md").read_text(encoding="utf-8")
        missing = self.module.missing_policy_markers(agents)
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn(self.module.RESTORE_DTBO_ACK_TOKEN, missing)
        self.assertIn("Consumed exception (2026-07-09 KST / 2026-07-08 UTC, S22+ M29", agents)
        self.assertIn("manual-download contaminated / not a clean self-download proof", agents)

    def test_candidate_selection_is_s24_only(self):
        self.assertEqual([candidate.label for candidate in self.module.selected_candidates(None)], ["S24"])
        self.assertEqual([candidate.label for candidate in self.module.selected_candidates(["S24"])], ["S24"])
        with self.assertRaisesRegex(SystemExit, "F43 remains unauthorized"):
            self.module.selected_candidates(["F43"])
        with self.assertRaisesRegex(SystemExit, "exactly S24"):
            self.module.selected_candidates(["S24", "F43"])

    def test_retained_fingerprint_counts_candidate_and_android_signatures(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            pstore = run_dir / "android_pstore"
            pstore.mkdir()
            label = "first_post_m29_S24_rollback"
            payload = (
                b"S22_NATIVE_INIT_M28_DEP_COMPLETE_DOWNLOAD phase=module\n"
                b"init: Received sys.powerctl='reboot,download' from pid: 123\n"
                b"really_probe watchdog Unknown symbol Kernel panic\n"
            )
            (pstore / f"{label}_last_kmsg.bin").write_bytes(payload)
            log_path = run_dir / "log.txt"

            scan = self.module.retained_fingerprint(run_dir, log_path, label)

            self.assertEqual(scan["last_kmsg_bytes"], len(payload))
            self.assertEqual(scan["m29_marker_count"], 1)
            self.assertEqual(scan["s22_native_count"], 1)
            self.assertEqual(scan["android_reboot_download_count"], 1)
            self.assertEqual(scan["android_really_probe_count"], 1)
            self.assertEqual(scan["watchdog_count"], 1)
            self.assertEqual(scan["unknown_symbol_count"], 1)
            self.assertTrue((run_dir / f"{label}_last_kmsg_fingerprint.json").is_file())

    def test_compare_retained_fingerprints_reports_same_or_changed_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            before = {
                "last_kmsg_sha256": "a" * 64,
                "last_kmsg_bytes": 10,
                "m29_marker_count": 0,
                "s22_native_count": 0,
                "android_reboot_download_count": 1,
                "watchdog_count": 0,
                "kernel_panic_count": 0,
                "unknown_symbol_count": 0,
            }
            after = {
                "last_kmsg_sha256": "b" * 64,
                "last_kmsg_bytes": 20,
                "m29_marker_count": 1,
                "s22_native_count": 1,
                "android_reboot_download_count": 0,
                "watchdog_count": 2,
                "kernel_panic_count": 0,
                "unknown_symbol_count": 0,
            }
            (run_dir / "pre_last_kmsg_fingerprint.json").write_text(json.dumps(before), encoding="utf-8")
            (run_dir / "post_last_kmsg_fingerprint.json").write_text(json.dumps(after), encoding="utf-8")

            comparison = self.module.compare_retained_fingerprints(run_dir, run_dir / "log.txt", "pre", "post")

            self.assertFalse(comparison["same_sha256"])
            self.assertEqual(comparison["after_m29_marker_count"], 1)
            self.assertEqual(comparison["after_watchdog_count"], 2)

    def test_capture_surfaces_collects_pstore_before_reset_summary(self):
        order = []

        def fake_collect_pstore(*_args, **_kwargs):
            order.append("pstore")
            return True

        def fake_fingerprint(_run_dir, _log_path, label):
            order.append("fingerprint")
            return {"label": label, "last_kmsg_sha256": "0" * 64}

        def fake_collect_reset(run_dir, _serial):
            order.append("reset")
            return {"result": "ok", "run_dir_seen": str(run_dir)}

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "log.txt"
            with (
                patch.object(self.module.m28, "collect_android_pstore", fake_collect_pstore),
                patch.object(self.module, "retained_fingerprint", fake_fingerprint),
                patch.object(self.module, "collect_reset_reason", fake_collect_reset),
            ):
                summary = self.module.collect_retained_and_reset_surfaces(
                    run_dir,
                    log_path,
                    "ADB123",
                    "first_post_m29_S24_rollback",
                    timing="first-post-candidate-rollback-before-stock-dtbo-rollback",
                )

        self.assertEqual(order, ["pstore", "fingerprint", "reset"])
        self.assertTrue(summary["m29_marker_found"])
        self.assertEqual(summary["m29_capture_timing"], "first-post-candidate-rollback-before-stock-dtbo-rollback")

    @unittest.skipUnless(MANIFEST.exists(), "private M28/M29 manifest missing")
    def test_reused_m28_s24_manifest_verifies_for_m29(self):
        with patch.object(self.module.m28, "append_log", lambda *_args, **_kwargs: None):
            self.module.m28.verify_m28_top_manifest(MANIFEST, Path("/tmp/unused-m29-live-gate-test.log"))
            self.module.m28.verify_m28_variant_manifest(
                Path.cwd(),
                self.module.m28.EXPECTED_M28_BY_LABEL["S24"],
                Path("/tmp/unused-m29-live-gate-test.log"),
            )


if __name__ == "__main__":
    unittest.main()
