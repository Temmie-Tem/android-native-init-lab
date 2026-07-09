import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_8/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m34_s8b1_beacon_probe_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM34S8B1BeaconProbeLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_markers_include_hashes_tokens_and_s8b1_semantics(self):
        markers = self.module.policy_required_markers()
        self.assertIn(self.module.LIVE_ACK_TOKEN, markers)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, markers)
        self.assertIn(self.module.EXPECTED_M34_AP_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M34_BOOT_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M34_INIT_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M34_TEMPLATE_SOURCE_SHA256, markers)
        self.assertIn("S8B1 keeps the S7A2 module recipe fixed", markers)
        self.assertIn("GENI I2C transport closure", markers)
        self.assertIn("stock max77705 PDIC altmode session-producer closure", markers)
        self.assertIn("module_count=86", markers)
        self.assertIn("session_producer_parity=1", markers)
        self.assertIn("max77705_session=1", markers)
        self.assertIn("geni_i2c_transport=1", markers)
        self.assertIn("typec_readback=0", markers)
        self.assertIn("role_write_discriminator=0", markers)
        self.assertIn("configfs_gadget=0", markers)
        self.assertIn("udc_bind=0", markers)
        self.assertIn("ssusb_mode_peripheral=0", markers)
        self.assertIn("s8_beacon_probe=typec_port_or_i2c_device", markers)
        self.assertIn("predicate=typec_port_or_i2c_device", markers)
        self.assertIn("/sys/class/typec/port0", markers)
        self.assertIn("/sys/bus/i2c/devices/57-0066", markers)
        self.assertIn("reboot_request=download", markers)
        self.assertIn("download_beacon=1", markers)
        self.assertIn("true_action=reboot_download", markers)
        self.assertIn("false_action=park", markers)
        self.assertIn("host-visible HIT = new Odin Download endpoint appears", markers)
        self.assertIn("MISS = no new Odin endpoint during bounded observation; manual Download rollback required", markers)
        self.assertIn("no configfs gadget setup", markers)
        self.assertIn("no UDC bind", markers)
        self.assertIn("no TypeC role write", markers)
        self.assertIn("no ssusb role write", markers)
        self.assertIn("no FunctionFS", markers)
        self.assertIn("no stock composite", markers)
        self.assertIn("sec_debug_region.ko present due stock charger dependency", markers)
        self.assertIn("requires_s7a_specific_live_risk_review", markers)

    def test_missing_policy_markers_fail_closed_for_empty_text(self):
        missing = self.module.missing_policy_markers("")
        self.assertIn(self.module.LIVE_ACK_TOKEN, missing)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, missing)
        self.assertIn(self.module.EXPECTED_M34_AP_SHA256, missing)
        self.assertIn(self.module.EXPECTED_M34_MARKER, missing)
        self.assertIn("s8_beacon_probe=typec_port_or_i2c_device", missing)
        self.assertIn("predicate=typec_port_or_i2c_device", missing)
        self.assertIn("reboot_request=download", missing)
        self.assertIn("download_beacon=1", missing)

    def test_missing_policy_markers_accept_exact_marker_set(self):
        text = " ".join(self.module.policy_required_markers())
        self.assertEqual(self.module.missing_policy_markers(text), [])

    def test_agents_exception_draft_satisfies_same_policy_markers(self):
        draft = self.module.agents_exception_draft()
        self.assertEqual(self.module.missing_policy_markers(draft), [])
        self.assertTrue(self.module.has_draft_only_m34_exception(draft))
        self.assertIn("DRAFT ONLY", draft)
        self.assertIn(self.module.LIVE_ACK_TOKEN, draft)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, draft)
        self.assertIn("This draft is not active authorization", draft)
        self.assertIn("s8_beacon_probe=typec_port_or_i2c_device", draft)
        self.assertIn("predicate=typec_port_or_i2c_device", draft)
        self.assertIn("reboot_request=download", draft)
        self.assertIn("download_beacon=1", draft)
        self.assertIn("no configfs gadget setup", draft)
        self.assertIn("does not authorize S1/S2/S3/S4/S5/S6/S7A/S7A2 repeat", " ".join(draft.split()))

    def test_agents_exception_active_template_passes_policy_gate(self):
        template = self.module.agents_exception_active_template()
        self.assertEqual(self.module.missing_policy_markers(template), [])
        self.assertFalse(self.module.has_draft_only_m34_exception(template))
        self.assertNotIn("DRAFT ONLY", template)
        self.assertNotIn("This draft is not active authorization", template)
        self.assertIn(self.module.LIVE_ACK_TOKEN, template)
        self.assertIn("Narrow operator-authorized exception", template)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(template, encoding="utf-8")
            log_path = Path(tmp) / "active_template_check.log"
            self.module.verify_agents_exception(root, log_path)
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("agents_exception_draft_only_present=0", text)
            self.assertIn("agents_exception_missing=[]", text)

    def test_verify_agents_exception_rejects_draft_only_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(self.module.agents_exception_draft(), encoding="utf-8")
            log_path = Path(tmp) / "draft_only_check.log"
            with self.assertRaises(SystemExit) as caught:
                self.module.verify_agents_exception(root, log_path)
            self.assertIn("draft-only M34 S8B1", str(caught.exception))
            self.assertIn("agents_exception_draft_only_present=1", log_path.read_text(encoding="utf-8"))

    @unittest.skipUnless(MANIFEST.exists(), "private M34 v0.8 manifest missing")
    def test_current_manifest_contract_matches_live_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "m34_s8b1_manifest_check.log"
            self.module.verify_m34_manifest(MANIFEST, log_path)
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("m34_s8b1_manifest_hashes=", text)
            self.assertIn("m34_manifest_safety=", text)
            self.assertIn("m34_s8b1_manifest_runtime_steps=", text)
            self.assertIn("m34_s8b1_manifest_closure=", text)
            self.assertEqual(len(self.module.EXPECTED_MODULES), 86)
            self.assertIn("dwc3-msm.ko", self.module.EXPECTED_MODULES)
            self.assertIn("usb_f_ss_acm.ko", self.module.EXPECTED_MODULES)
            self.assertIn("gpi.ko", self.module.EXPECTED_MODULES)
            self.assertIn("msm-geni-se.ko", self.module.EXPECTED_MODULES)
            self.assertIn("i2c-msm-geni.ko", self.module.EXPECTED_MODULES)
            self.assertIn("mfd_max77705.ko", self.module.EXPECTED_MODULES)
            self.assertIn("pdic_max77705.ko", self.module.EXPECTED_MODULES)
            self.assertIn("sec_debug_region.ko", self.module.EXPECTED_MODULES)

    def test_probe_result_strings_are_distinct(self):
        self.assertNotEqual("download-beacon-hit", "download-beacon-miss-parked-manual-download-required")
        self.assertIn("download-beacon-hit", self.module.agents_exception_draft())
        self.assertIn("manual Download rollback", self.module.agents_exception_draft())

    def test_run_android_readonly_preflight_checks_android_boot_and_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "readonly_preflight.log"
            with (
                mock.patch.object(self.module, "require_current_android", return_value="RFCT519XWGK") as require_android,
                mock.patch.object(self.module, "verify_android_stability") as verify_stability,
                mock.patch.object(self.module, "verify_partition_hash") as verify_hash,
                mock.patch.object(self.module, "host_snapshot", return_value={}) as snapshot,
            ):
                serial = self.module.run_android_readonly_preflight(
                    run_dir=run_dir,
                    log_path=log_path,
                    odin=Path("/no/odin"),
                    serial=None,
                    stability_samples=2,
                    stability_interval_sec=1.0,
                    snapshot_label="readonly_preflight_current",
                    agents_exception_checked=False,
                )

            self.assertEqual(serial, "RFCT519XWGK")
            require_android.assert_called_once_with(log_path, None)
            verify_stability.assert_called_once_with(log_path, "RFCT519XWGK", 2, 1.0)
            verify_hash.assert_called_once_with(
                log_path,
                "RFCT519XWGK",
                "boot",
                self.module.EXPECTED_M34_BASE_BOOT_SHA256,
                "current",
            )
            snapshot.assert_called_once_with(run_dir, log_path, "readonly_preflight_current", Path("/no/odin"))
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("android_readonly_preflight=ok", text)
            self.assertIn("agents_exception_checked=0", text)
            self.assertIn("current_boot_hash_checked=1", text)

    def test_readonly_preflight_cli_skips_agents_exception_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            run_dir = root / "run"
            with (
                mock.patch.object(self.module, "verify_m34_artifacts") as verify_artifacts,
                mock.patch.object(self.module, "verify_agents_exception", side_effect=AssertionError("AGENTS gate should be skipped")),
                mock.patch.object(self.module, "run_android_readonly_preflight", return_value="RFCT519XWGK") as readonly,
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = self.module.main(
                        [
                            "--readonly-preflight",
                            "--odin",
                            str(odin),
                            "--m34-ap",
                            str(root / "candidate.tar.md5"),
                            "--m34-manifest",
                            str(root / "manifest.json"),
                            "--magisk-rollback-ap",
                            str(root / "magisk.tar.md5"),
                            "--stock-rollback-ap",
                            str(root / "stock.tar.md5"),
                            "--run-dir",
                            str(run_dir),
                        ]
                    )

            self.assertEqual(rc, 0)
            verify_artifacts.assert_called_once()
            readonly.assert_called_once()
            self.assertFalse((run_dir / "timeline.json").exists())

    def test_observe_download_beacon_classifies_new_odin_endpoint_as_hit(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "observe_hit.log"
            clock = {"now": 0.0}

            with (
                mock.patch.object(self.module, "host_snapshot", return_value={}),
                mock.patch.object(self.module, "odin_devices", return_value=["ODIN_NEW"]),
                mock.patch.object(self.module, "adb_rows", return_value=[]),
                mock.patch.object(self.module.time, "monotonic", side_effect=lambda: clock["now"]),
                mock.patch.object(self.module.time, "sleep", side_effect=lambda sec: clock.__setitem__("now", clock["now"] + sec)),
            ):
                result, device = self.module.observe_download_beacon(
                    run_dir=run_dir,
                    log_path=log_path,
                    odin=Path("/no/odin"),
                    observe_sec=2,
                    snapshot_interval_sec=1.0,
                )

            self.assertEqual(result, "download-beacon-hit")
            self.assertEqual(device, "ODIN_NEW")
            self.assertIn("m34_s8b1_result=download-beacon-hit", log_path.read_text(encoding="utf-8"))

    def test_observe_download_beacon_miss_requires_manual_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "observe_miss.log"
            clock = {"now": 0.0}

            with (
                mock.patch.object(self.module, "host_snapshot", return_value={}),
                mock.patch.object(self.module, "odin_devices", return_value=[]),
                mock.patch.object(self.module, "adb_rows", return_value=[]),
                mock.patch.object(self.module.time, "monotonic", side_effect=lambda: clock["now"]),
                mock.patch.object(self.module.time, "sleep", side_effect=lambda sec: clock.__setitem__("now", clock["now"] + sec)),
            ):
                result, device = self.module.observe_download_beacon(
                    run_dir=run_dir,
                    log_path=log_path,
                    odin=Path("/no/odin"),
                    observe_sec=2,
                    snapshot_interval_sec=1.0,
                )

            self.assertEqual(result, "download-beacon-miss-parked-manual-download-required")
            self.assertIsNone(device)
            self.assertIn("m34_s8b1_result=download-beacon-miss-parked-manual-download-required", log_path.read_text(encoding="utf-8"))

    def test_observe_download_beacon_rejects_ambiguous_odin_endpoints(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "observe_ambiguous.log"
            clock = {"now": 0.0}

            with (
                mock.patch.object(self.module, "host_snapshot", return_value={}),
                mock.patch.object(self.module, "odin_devices", return_value=["ODIN_A", "ODIN_B"]),
                mock.patch.object(self.module, "adb_rows", return_value=[]),
                mock.patch.object(self.module.time, "monotonic", side_effect=lambda: clock["now"]),
                mock.patch.object(self.module.time, "sleep", side_effect=lambda sec: clock.__setitem__("now", clock["now"] + sec)),
            ):
                with self.assertRaises(SystemExit) as caught:
                    self.module.observe_download_beacon(
                        run_dir=run_dir,
                        log_path=log_path,
                        odin=Path("/no/odin"),
                        observe_sec=2,
                        snapshot_interval_sec=1.0,
                    )

            self.assertIn("refusing ambiguous Odin devices", str(caught.exception))

    def test_observe_download_beacon_classifies_adb_return_before_rollback_as_unexpected(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "observe_adb.log"
            clock = {"now": 0.0}

            with (
                mock.patch.object(self.module, "host_snapshot", return_value={}),
                mock.patch.object(self.module, "odin_devices", return_value=[]),
                mock.patch.object(self.module, "adb_rows", return_value=[("RFCT519XWGK", "device", "model:SM_S906N")]),
                mock.patch.object(self.module.time, "monotonic", side_effect=lambda: clock["now"]),
                mock.patch.object(self.module.time, "sleep", side_effect=lambda sec: clock.__setitem__("now", clock["now"] + sec)),
            ):
                result, device = self.module.observe_download_beacon(
                    run_dir=run_dir,
                    log_path=log_path,
                    odin=Path("/no/odin"),
                    observe_sec=2,
                    snapshot_interval_sec=1.0,
                )

            self.assertEqual(result, "unexpected-adb-before-rollback")
            self.assertIsNone(device)
            self.assertIn("m34_s8b1_result=unexpected-adb-before-rollback", log_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
