import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m34_s8b1_beacon_probe_live_gate.py")
ANALYZER_SCRIPT = Path("workspace/public/src/scripts/revalidation/analyze_s22plus_m34_s8b1_result.py")
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


def load_analyzer():
    script_dir = str(ANALYZER_SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("analyze_s22plus_m34_s8b1_result", ANALYZER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_test_predicate_baseline(module, run_dir: Path, serial: str = "RFCT519XWGK") -> dict:
    payload = {
        "schema": "s22plus_m34_s8b1_android_predicate_baseline_v1",
        "timestamp_utc": "2026-07-09T00:00:00Z",
        "serial": serial,
        "probe": module.EXPECTED_PROBE,
        "probe_paths": module.EXPECTED_PROBE_PATHS,
        "paths": {
            "/sys/class/typec/port0": {"exists": True, "realpath": "/sys/devices/platform/soc/994000.i2c/typec/port0"},
            "/sys/bus/i2c/devices/57-0066": {"exists": True, "realpath": "/sys/devices/platform/soc/994000.i2c/i2c-57/57-0066"},
        },
        "values": {
            "/sys/class/typec/port0/data_role": "host [device] ",
            "/sys/class/typec/port0/power_role": "source [sink] ",
            "/sys/class/typec/port0/port_type": "[dual] ",
        },
        "future_b2_hints": {
            "typec_class_port0_exists": True,
            "max77705_i2c_device_exists": True,
            "candidate_paths": module.ANDROID_S8B2_HINT_PATHS,
            "paths": {
                module.ANDROID_MAX77705_USBC_ROOT: {"exists": True, "realpath": module.ANDROID_MAX77705_USBC_ROOT},
                module.ANDROID_MAX77705_USBC_TYPEC_PORT0: {
                    "exists": True,
                    "realpath": module.ANDROID_MAX77705_USBC_TYPEC_PORT0,
                },
                module.ANDROID_MAX77705_USBC_TYPEC_PARTNER: {
                    "exists": True,
                    "realpath": module.ANDROID_MAX77705_USBC_TYPEC_PARTNER,
                },
            },
            "value_paths": module.ANDROID_S8B2_HINT_VALUE_PATHS,
            "values": {
                f"{module.ANDROID_MAX77705_USBC_TYPEC_PORT0}/data_role": "host [device]",
                f"{module.ANDROID_MAX77705_USBC_TYPEC_PORT0}/power_role": "source [sink]",
                f"{module.ANDROID_MAX77705_USBC_TYPEC_PORT0}/port_type": "[dual] source sink",
                f"{module.ANDROID_MAX77705_USBC_TYPEC_PORT0}/power_operation_mode": "1.5A",
                f"{module.ANDROID_MAX77705_USBC_TYPEC_PARTNER}/supports_usb_power_delivery": "no",
                f"{module.ANDROID_MAX77705_USBC_TYPEC_PARTNER}/usb_power_delivery_revision": "0.0",
                f"{module.ANDROID_MAX77705_USBC_TYPEC_PARTNER}/accessory_mode": "none",
            },
        },
        "predicate_true": True,
    }
    module.android_predicate_baseline_path(run_dir).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def write_test_reset_context_baseline(module, run_dir: Path, serial: str = "RFCT519XWGK") -> dict:
    payload = {
        "schema": "s22plus_m34_s8b1_android_reset_context_baseline_v1",
        "timestamp_utc": "2026-07-09T00:00:00Z",
        "serial": serial,
        "summary": {
            "device_action": "read-only-adb-root",
            "writes_performed": False,
            "reboots_performed": False,
            "flashes_performed": False,
            "result": "pass",
            "checks": {
                "target_model": True,
                "target_device": True,
                "target_build": True,
                "android_booted": True,
                "normal_boot": True,
                "root_available": True,
                "boot_hash_baseline": True,
                "vendor_boot_hash_stock": True,
            },
            "reset_reason": {
                "proc_reset_reason_value": "MPON",
                "proc_reset_rwc_value": "41",
                "proc_store_lastkmsg_value": "1",
                "reset_history_upload_cause_count": 10,
                "reset_history_pmic_abnormal_count": 10,
                "reset_history_oem_reset_magic_count": 9,
            },
        },
    }
    module.android_reset_context_baseline_path(run_dir).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def readonly_preflight_stub(module, serial: str = "RFCT519XWGK"):
    def _stub(*, run_dir, **_kwargs):
        write_test_predicate_baseline(module, run_dir, serial)
        write_test_reset_context_baseline(module, run_dir, serial)
        return serial

    return _stub


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
            self.assertIn("agents_exception_exact_active_template_present=1", text)

    def test_verify_agents_exception_rejects_draft_only_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text(self.module.agents_exception_draft(), encoding="utf-8")
            log_path = Path(tmp) / "draft_only_check.log"
            with self.assertRaises(SystemExit) as caught:
                self.module.verify_agents_exception(root, log_path)
            self.assertIn("draft-only M34 S8B1", str(caught.exception))
            self.assertIn("agents_exception_draft_only_present=1", log_path.read_text(encoding="utf-8"))

    def test_verify_agents_exception_rejects_marker_complete_modified_active_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            modified = self.module.agents_exception_active_template().replace(
                "one bounded attended boot-partition-only M34 S8B1 live gate",
                "one unbounded attended boot-partition-only M34 S8B1 live gate",
                1,
            )
            self.assertEqual(self.module.missing_policy_markers(modified), [])
            (root / "AGENTS.md").write_text(modified, encoding="utf-8")
            log_path = Path(tmp) / "modified_active_template_check.log"
            with self.assertRaises(SystemExit) as caught:
                self.module.verify_agents_exception(root, log_path)
            self.assertIn("exact M34 S8B1 active authorization template is absent", str(caught.exception))
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("agents_exception_missing=[]", text)
            self.assertIn("agents_exception_exact_active_template_present=0", text)

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
                mock.patch.object(self.module, "collect_android_s8b1_predicate_baseline") as collect_baseline,
                mock.patch.object(self.module, "collect_android_reset_context_baseline") as collect_reset_context,
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
            collect_baseline.assert_called_once_with(run_dir=run_dir, log_path=log_path, serial="RFCT519XWGK")
            collect_reset_context.assert_called_once_with(run_dir=run_dir, log_path=log_path, serial="RFCT519XWGK")
            snapshot.assert_called_once_with(run_dir, log_path, "readonly_preflight_current", Path("/no/odin"))
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("android_readonly_preflight=ok", text)
            self.assertIn("agents_exception_checked=0", text)
            self.assertIn("current_boot_hash_checked=1", text)

    def test_verify_reset_context_summary_rejects_write_or_missing_reset_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = write_test_reset_context_baseline(self.module, Path(tmp))["summary"]
            payload["writes_performed"] = True
            with self.assertRaises(SystemExit) as caught:
                self.module.verify_reset_context_summary(payload)
            self.assertIn("not no-write", str(caught.exception))

            payload = write_test_reset_context_baseline(self.module, Path(tmp))["summary"]
            payload["reset_reason"].pop("proc_reset_rwc_value")
            with self.assertRaises(SystemExit) as caught:
                self.module.verify_reset_context_summary(payload)
            self.assertIn("missing proc_reset_rwc_value", str(caught.exception))

    def test_collect_android_s8b1_predicate_baseline_writes_true_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "baseline.log"
            stdout = "\n".join(
                [
                    "exists\t/sys/class/typec/port0\t0",
                    "exists\t/sys/bus/i2c/devices/57-0066\t1",
                    "realpath\t/sys/bus/i2c/devices/57-0066\t/sys/devices/platform/soc/994000.i2c/i2c-57/57-0066",
                    f"exists\t{self.module.ANDROID_MAX77705_USBC_ROOT}\t1",
                    f"realpath\t{self.module.ANDROID_MAX77705_USBC_ROOT}\t{self.module.ANDROID_MAX77705_USBC_ROOT}",
                    f"exists\t{self.module.ANDROID_MAX77705_USBC_TYPEC_PORT0}\t1",
                    f"realpath\t{self.module.ANDROID_MAX77705_USBC_TYPEC_PORT0}\t{self.module.ANDROID_MAX77705_USBC_TYPEC_PORT0}",
                    f"exists\t{self.module.ANDROID_MAX77705_USBC_TYPEC_PARTNER}\t1",
                    f"realpath\t{self.module.ANDROID_MAX77705_USBC_TYPEC_PARTNER}\t{self.module.ANDROID_MAX77705_USBC_TYPEC_PARTNER}",
                    "value\t/sys/class/typec/port0/data_role\thost [device] ",
                    "value\t/sys/class/typec/port0/power_role\tsource [sink] ",
                    "value\t/sys/class/typec/port0/port_type\t[dual] ",
                ]
            )
            proc = mock.Mock(returncode=0, stdout=stdout, stderr="")
            root_values = [
                "host [device]",
                "source [sink]",
                "[dual] source sink",
                "1.5A",
                "no",
                "0.0",
                "none",
            ]
            root_procs = [mock.Mock(returncode=0, stdout=f"{value}\n", stderr="") for value in root_values]
            with mock.patch.object(self.module, "run", side_effect=[proc, *root_procs]) as run:
                payload = self.module.collect_android_s8b1_predicate_baseline(
                    run_dir=run_dir,
                    log_path=log_path,
                    serial="RFCT519XWGK",
                )

            self.assertEqual(run.call_count, 1 + len(self.module.ANDROID_S8B2_HINT_VALUE_PATHS))
            self.assertTrue(payload["predicate_true"])
            self.assertFalse(payload["paths"]["/sys/class/typec/port0"]["exists"])
            self.assertTrue(payload["paths"]["/sys/bus/i2c/devices/57-0066"]["exists"])
            self.assertEqual(payload["values"]["/sys/class/typec/port0/data_role"], "host [device] ")
            hints = payload["future_b2_hints"]
            self.assertFalse(hints["typec_class_port0_exists"])
            self.assertTrue(hints["max77705_i2c_device_exists"])
            self.assertTrue(hints["paths"][self.module.ANDROID_MAX77705_USBC_TYPEC_PORT0]["exists"])
            self.assertTrue(hints["paths"][self.module.ANDROID_MAX77705_USBC_TYPEC_PARTNER]["exists"])
            self.assertEqual(hints["values"][f"{self.module.ANDROID_MAX77705_USBC_TYPEC_PORT0}/data_role"], "host [device]")
            self.assertEqual(hints["values"][f"{self.module.ANDROID_MAX77705_USBC_TYPEC_PORT0}/power_role"], "source [sink]")
            self.assertEqual(hints["values"][f"{self.module.ANDROID_MAX77705_USBC_TYPEC_PORT0}/port_type"], "[dual] source sink")
            self.assertEqual(hints["values"][f"{self.module.ANDROID_MAX77705_USBC_TYPEC_PARTNER}/accessory_mode"], "none")
            baseline_json = self.module.android_predicate_baseline_path(run_dir)
            self.assertEqual(json.loads(baseline_json.read_text(encoding="utf-8")), payload)
            self.assertIn("s8b1_android_predicate_baseline_json=", log_path.read_text(encoding="utf-8"))

    def test_readonly_preflight_cli_skips_agents_exception_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            run_dir = root / "run"
            with (
                mock.patch.object(self.module, "verify_m34_artifacts") as verify_artifacts,
                mock.patch.object(self.module, "verify_agents_exception", side_effect=AssertionError("AGENTS gate should be skipped")),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=readonly_preflight_stub(self.module)) as readonly,
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

    def test_print_live_runbook_skips_agents_and_android_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            run_dir = root / "run"
            with (
                mock.patch.object(self.module, "verify_m34_artifacts") as verify_artifacts,
                mock.patch.object(self.module, "verify_agents_exception", side_effect=AssertionError("AGENTS gate should be skipped")),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=AssertionError("Android gate should be skipped")),
            ):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    rc = self.module.main(
                        [
                            "--print-live-runbook",
                            "--serial",
                            "RFCT519XWGK",
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
            text = stdout.getvalue()
            self.assertIn("--readonly-preflight", text)
            self.assertIn("--print-agents-exception-active-template", text)
            self.assertIn("--write-agents-candidate '<candidate-AGENTS.md>'", text)
            self.assertIn("--verify-agents-candidate '<candidate-AGENTS.md>'", text)
            self.assertIn(f"--ack {self.module.LIVE_ACK_TOKEN}", text)
            self.assertIn(f"--ack {self.module.ROLLBACK_ACK_TOKEN}", text)
            self.assertIn("--require-advance", text)
            self.assertIn("--require-live-next-stage", text)
            self.assertIn("--serial RFCT519XWGK", text)
            self.assertIn("This command handles HIT rollback", text)
            self.assertIn("Fallback only: run this if step 6 exits after MISS without rollback", text)
            self.assertIn("cleanup evidence, not B1 proof", text)
            self.assertIn(str(root / "candidate.tar.md5"), text)
            self.assertIn(str(root / "manifest.json"), text)
            self.assertIn(str(root / "magisk.tar.md5"), text)
            self.assertIn(str(root / "stock.tar.md5"), text)
            self.assertIn(str(odin), text)
            self.assertIn(str(run_dir), text)
            self.assertIn(str(run_dir / "result.json"), text)
            for phase in ("preflight", "template", "dryrun", "rollback"):
                phase_dir = Path(f"{run_dir}_{phase}")
                self.assertIn(str(phase_dir), text)
                self.assertFalse(phase_dir.exists())
            self.assertNotIn("<run-dir>/result.json", text)
            self.assertFalse(run_dir.exists())
            self.assertFalse((run_dir / "timeline.json").exists())

    def test_print_only_exception_template_does_not_create_requested_run_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            run_dir = root / "run"
            with (
                mock.patch.object(self.module, "verify_m34_artifacts") as verify_artifacts,
                mock.patch.object(self.module, "verify_agents_exception", side_effect=AssertionError("AGENTS gate should be skipped")),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=AssertionError("Android gate should be skipped")),
            ):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    rc = self.module.main(
                        [
                            "--print-agents-exception-active-template",
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
            self.assertIn(self.module.LIVE_ACK_TOKEN, stdout.getvalue())
            self.assertFalse(run_dir.exists())

    def test_agents_candidate_text_inserts_exact_active_template_before_m34_consumed_block(self):
        source = (
            "header\n"
            f"{self.module.ACTIVE_EXCEPTION_INSERT_ANCHOR}"
            "   runtime-gadget boot-only live gate):** consumed\n"
        )
        candidate = self.module.agents_candidate_text(source)
        self.assertIn(self.module.agents_exception_active_template(), candidate)
        self.assertLess(candidate.index("S22+ M34 S8B1"), candidate.index("S22+ M34 S7A2"))
        self.assertFalse(self.module.has_draft_only_m34_exception(candidate))

    def test_write_agents_candidate_creates_full_verified_candidate_without_run_dir_or_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            (root / "AGENTS.md").write_text(
                "header\n"
                f"{self.module.ACTIVE_EXCEPTION_INSERT_ANCHOR}"
                "   runtime-gadget boot-only live gate):** consumed\n",
                encoding="utf-8",
            )
            candidate = root / "out" / "AGENTS.candidate.md"
            run_dir = root / "run"
            with (
                mock.patch.object(self.module, "repo_root", return_value=root),
                mock.patch.object(self.module, "verify_m34_artifacts") as verify_artifacts,
                mock.patch.object(self.module, "verify_agents_exception", side_effect=AssertionError("repo AGENTS gate should be skipped")),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=AssertionError("Android gate should be skipped")),
            ):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    rc = self.module.main(
                        [
                            "--write-agents-candidate",
                            str(candidate),
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
            self.assertTrue(candidate.is_file())
            self.module.verify_agents_text(
                candidate.read_text(encoding="utf-8"),
                root / "verify.log",
                source_label=str(candidate),
            )
            self.assertIn("write-agents-candidate ok", stdout.getvalue())
            self.assertFalse(run_dir.exists())

    def test_write_agents_candidate_refuses_to_write_repo_agents_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            agents = root / "AGENTS.md"
            agents.write_text(
                "header\n"
                f"{self.module.ACTIVE_EXCEPTION_INSERT_ANCHOR}"
                "   runtime-gadget boot-only live gate):** consumed\n",
                encoding="utf-8",
            )
            with (
                mock.patch.object(self.module, "repo_root", return_value=root),
                mock.patch.object(self.module, "verify_m34_artifacts") as verify_artifacts,
            ):
                with self.assertRaises(SystemExit) as caught:
                    self.module.main(
                        [
                            "--write-agents-candidate",
                            str(agents),
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
                        ]
                    )

            verify_artifacts.assert_called_once()
            self.assertIn("refuses to write AGENTS.md directly", str(caught.exception))

    def test_verify_agents_candidate_accepts_exact_active_template_without_run_dir_or_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            candidate = root / "AGENTS.candidate.md"
            candidate.write_text(self.module.agents_exception_active_template(), encoding="utf-8")
            run_dir = root / "run"
            with (
                mock.patch.object(self.module, "verify_m34_artifacts") as verify_artifacts,
                mock.patch.object(self.module, "verify_agents_exception", side_effect=AssertionError("repo AGENTS gate should be skipped")),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=AssertionError("Android gate should be skipped")),
            ):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    rc = self.module.main(
                        [
                            "--verify-agents-candidate",
                            str(candidate),
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
            self.assertIn("verify-agents-candidate ok", stdout.getvalue())
            self.assertFalse(run_dir.exists())

    def test_verify_agents_candidate_rejects_marker_complete_modified_active_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            modified = self.module.agents_exception_active_template().replace(
                "one bounded attended boot-partition-only M34 S8B1 live gate",
                "one unbounded attended boot-partition-only M34 S8B1 live gate",
                1,
            )
            self.assertEqual(self.module.missing_policy_markers(modified), [])
            candidate = root / "AGENTS.candidate.md"
            candidate.write_text(modified, encoding="utf-8")
            run_dir = root / "run"
            with (
                mock.patch.object(self.module, "verify_m34_artifacts") as verify_artifacts,
                mock.patch.object(self.module, "verify_agents_exception", side_effect=AssertionError("repo AGENTS gate should be skipped")),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=AssertionError("Android gate should be skipped")),
            ):
                with self.assertRaises(SystemExit) as caught:
                    self.module.main(
                        [
                            "--verify-agents-candidate",
                            str(candidate),
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

            verify_artifacts.assert_called_once()
            self.assertIn("exact M34 S8B1 active authorization template is absent", str(caught.exception))
            self.assertFalse(run_dir.exists())

    def test_prelive_packet_skips_agents_gate_and_writes_exact_run_material(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            run_dir = root / "run"
            with (
                mock.patch.object(self.module, "verify_m34_artifacts") as verify_artifacts,
                mock.patch.object(self.module, "verify_agents_exception", side_effect=AssertionError("AGENTS gate should be skipped")),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=readonly_preflight_stub(self.module)) as readonly,
            ):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    rc = self.module.main(
                        [
                            "--prelive-packet",
                            "--serial",
                            "RFCT519XWGK",
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
            self.assertIn("prelive-packet ok", stdout.getvalue())
            packet = json.loads((run_dir / "s22plus_m34_s8b1_prelive_packet.json").read_text(encoding="utf-8"))
            self.assertEqual(packet["schema"], "s22plus_m34_s8b1_prelive_packet_v1")
            self.assertFalse(packet["device_action"])
            self.assertFalse(packet["agents_exception_inserted"])
            self.assertFalse(packet["agents_exception_checked"])
            self.assertTrue(packet["android_checked"])
            self.assertEqual(packet["selected_serial"], "RFCT519XWGK")
            self.assertEqual(packet["live_ack_token"], self.module.LIVE_ACK_TOKEN)
            self.assertEqual(packet["rollback_ack_token"], self.module.ROLLBACK_ACK_TOKEN)
            planned_live_run_dir = Path(packet["planned_live_run_dir"])
            self.assertEqual(packet["packet_run_dir"], str(run_dir))
            self.assertEqual(planned_live_run_dir, Path(f"{run_dir}_live"))
            self.assertFalse(planned_live_run_dir.exists())
            self.assertEqual(packet["planned_result_json"], str(planned_live_run_dir / "result.json"))
            self.assertEqual(packet["planned_rollback_result_json"], str(Path(f"{planned_live_run_dir}_rollback") / "result.json"))
            self.assertEqual(packet["planned_phase_run_dirs"]["live"], str(planned_live_run_dir))
            self.assertIn(
                "handles MISS manual rollback internally",
                " ".join(packet["runbook_notes"]),
            )
            self.assertIn(
                "cleanup-only evidence",
                " ".join(packet["runbook_notes"]),
            )
            self.assertEqual(packet["runbook_options"]["observe_sec"], 90)
            self.assertEqual(packet["runbook_options"]["android_stability_samples"], 4)
            self.assertEqual(packet["runbook_options"]["android_stability_interval_sec"], 3.0)
            self.assertEqual(packet["android_s8b1_predicate_baseline"]["schema"], "s22plus_m34_s8b1_android_predicate_baseline_v1")
            self.assertTrue(packet["android_s8b1_predicate_baseline"]["predicate_true"])
            self.assertEqual(packet["android_s8b1_predicate_baseline"]["serial"], "RFCT519XWGK")
            hints = packet["android_s8b1_predicate_baseline"]["future_b2_hints"]
            self.assertEqual(hints["candidate_paths"], self.module.ANDROID_S8B2_HINT_PATHS)
            self.assertEqual(hints["value_paths"], self.module.ANDROID_S8B2_HINT_VALUE_PATHS)
            self.assertTrue(hints["paths"][self.module.ANDROID_MAX77705_USBC_TYPEC_PORT0]["exists"])
            self.assertEqual(
                packet["android_s8b1_predicate_baseline_json"],
                str(run_dir / "s22plus_m34_s8b1_android_predicate_baseline.json"),
            )
            self.assertEqual(
                packet["android_reset_context_baseline"]["schema"],
                "s22plus_m34_s8b1_android_reset_context_baseline_v1",
            )
            self.assertEqual(packet["android_reset_context_baseline"]["serial"], "RFCT519XWGK")
            self.assertEqual(
                packet["android_reset_context_baseline"]["summary"]["reset_reason"]["proc_reset_reason_value"],
                "MPON",
            )
            self.assertEqual(
                packet["android_reset_context_baseline_json"],
                str(run_dir / "s22plus_m34_s8b1_android_reset_context_baseline.json"),
            )
            self.assertEqual(
                set(packet["material_sha256"]),
                {
                    "runbook",
                    "active_exception_template",
                    "android_s8b1_predicate_baseline_json",
                    "android_reset_context_baseline_json",
                },
            )
            self.assertEqual(packet["material_sha256"]["runbook"], self.module.sha256_file(run_dir / "s22plus_m34_s8b1_live_runbook.txt"))
            self.assertEqual(
                packet["material_sha256"]["active_exception_template"],
                self.module.sha256_file(run_dir / "s22plus_m34_s8b1_active_exception_template.txt"),
            )
            self.assertEqual(
                packet["material_sha256"]["android_s8b1_predicate_baseline_json"],
                self.module.sha256_file(run_dir / "s22plus_m34_s8b1_android_predicate_baseline.json"),
            )
            self.assertEqual(
                packet["material_sha256"]["android_reset_context_baseline_json"],
                self.module.sha256_file(run_dir / "s22plus_m34_s8b1_android_reset_context_baseline.json"),
            )
            runbook = (run_dir / "s22plus_m34_s8b1_live_runbook.txt").read_text(encoding="utf-8")
            active_template = (run_dir / "s22plus_m34_s8b1_active_exception_template.txt").read_text(encoding="utf-8")
            self.assertIn(str(root / "candidate.tar.md5"), runbook)
            self.assertIn(str(root / "manifest.json"), runbook)
            self.assertIn(str(root / "magisk.tar.md5"), runbook)
            self.assertIn(str(root / "stock.tar.md5"), runbook)
            self.assertIn(str(odin), runbook)
            self.assertIn(str(planned_live_run_dir), runbook)
            self.assertIn(str(planned_live_run_dir / "result.json"), runbook)
            self.assertIn("--serial RFCT519XWGK", runbook)
            self.assertIn("Fallback only", runbook)
            self.assertIn("cleanup evidence, not B1 proof", runbook)
            for phase in ("preflight", "template", "dryrun", "rollback"):
                phase_dir = Path(f"{planned_live_run_dir}_{phase}")
                self.assertEqual(packet["planned_phase_run_dirs"][phase], str(phase_dir))
                self.assertIn(str(phase_dir), runbook)
                self.assertFalse(phase_dir.exists())
            self.assertNotIn(str(run_dir / "result.json"), runbook)
            self.assertIn(self.module.LIVE_ACK_TOKEN, runbook)
            self.assertIn(self.module.LIVE_ACK_TOKEN, active_template)
            self.assertNotIn("DRAFT ONLY", active_template)
            log_text = (run_dir / "s22plus_m34_s8b1_beacon_probe_live_gate.txt").read_text(encoding="utf-8")
            self.assertIn("prelive_packet=ok device_action=0 agents_exception_checked=0 android_checked=1", log_text)
            self.assertIn(f"prelive_packet_planned_live_run_dir={planned_live_run_dir}", log_text)
            self.assertFalse((run_dir / "timeline.json").exists())

    def test_prelive_packet_pins_selected_serial_when_serial_arg_is_omitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            run_dir = root / "run"
            with (
                mock.patch.object(self.module, "verify_m34_artifacts"),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=readonly_preflight_stub(self.module)),
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = self.module.main(
                        [
                            "--prelive-packet",
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
            packet = json.loads((run_dir / "s22plus_m34_s8b1_prelive_packet.json").read_text(encoding="utf-8"))
            self.assertEqual(packet["selected_serial"], "RFCT519XWGK")
            runbook = (run_dir / "s22plus_m34_s8b1_live_runbook.txt").read_text(encoding="utf-8")
            self.assertIn("--serial RFCT519XWGK", runbook)

    def test_verify_prelive_packet_skips_device_and_agents_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            run_dir = root / "run"
            path_args = [
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
            ]
            with (
                mock.patch.object(self.module, "verify_m34_artifacts"),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=readonly_preflight_stub(self.module)),
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.module.main(
                        [
                            "--prelive-packet",
                            *path_args,
                            "--android-stability-samples",
                            "2",
                            "--android-stability-interval-sec",
                            "1",
                            "--observe-sec",
                            "45",
                            "--run-dir",
                            str(run_dir),
                        ]
                    )

            packet_path = run_dir / "s22plus_m34_s8b1_prelive_packet.json"
            verify_dir = root / "verify"
            with (
                mock.patch.object(self.module, "verify_m34_artifacts") as verify_artifacts,
                mock.patch.object(self.module, "verify_agents_exception", side_effect=AssertionError("AGENTS gate should be skipped")),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=AssertionError("Android gate should be skipped")),
            ):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    rc = self.module.main(
                        [
                            "--verify-prelive-packet",
                            str(packet_path),
                            *path_args,
                            "--run-dir",
                            str(verify_dir),
                        ]
                    )

            self.assertEqual(rc, 0)
            verify_artifacts.assert_called_once()
            self.assertIn("verify-prelive-packet ok", stdout.getvalue())
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet["runbook_options"]["android_stability_samples"], 2)
            self.assertEqual(packet["runbook_options"]["android_stability_interval_sec"], 1.0)
            self.assertEqual(packet["runbook_options"]["observe_sec"], 45)
            log_text = (verify_dir / "s22plus_m34_s8b1_beacon_probe_live_gate.txt").read_text(encoding="utf-8")
            self.assertIn("prelive_packet_verify=ok device_action=0 agents_exception_checked=0 android_checked=0", log_text)
            self.assertFalse((verify_dir / "timeline.json").exists())

    def test_verify_prelive_packet_rejects_existing_planned_live_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            run_dir = root / "run"
            path_args = [
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
            ]
            with (
                mock.patch.object(self.module, "verify_m34_artifacts"),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=readonly_preflight_stub(self.module)),
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.module.main(["--prelive-packet", *path_args, "--run-dir", str(run_dir)])

            packet_path = run_dir / "s22plus_m34_s8b1_prelive_packet.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            Path(packet["planned_live_run_dir"]).mkdir()
            with mock.patch.object(self.module, "verify_m34_artifacts"):
                with self.assertRaises(SystemExit) as caught:
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.module.main(
                            [
                                "--verify-prelive-packet",
                                str(packet_path),
                                *path_args,
                                "--run-dir",
                                str(root / "verify"),
                            ]
                        )
            self.assertIn("planned run directory already exists", str(caught.exception))

    def test_verify_prelive_packet_after_dryrun_allows_only_dryrun_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            run_dir = root / "run"
            path_args = [
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
            ]
            with (
                mock.patch.object(self.module, "verify_m34_artifacts"),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=readonly_preflight_stub(self.module)),
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.module.main(["--prelive-packet", *path_args, "--run-dir", str(run_dir)])

            packet_path = run_dir / "s22plus_m34_s8b1_prelive_packet.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            dryrun_dir = Path(packet["planned_phase_run_dirs"]["dryrun"])
            dryrun_dir.mkdir()
            (dryrun_dir / "s22plus_m34_s8b1_beacon_probe_live_gate.txt").write_text(
                "\n".join(
                    [
                        "agents_exception_exact_active_template_present=1",
                        "android_stability_result=ok samples=2",
                        "current_boot_hash_rc=0",
                        self.module.EXPECTED_M34_BASE_BOOT_SHA256,
                        "android_readonly_preflight=ok device_action=0 agents_exception_checked=1 android_checked=1 current_boot_hash_checked=1",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            verify_dir = root / "verify-after-dryrun"
            with (
                mock.patch.object(self.module, "verify_m34_artifacts") as verify_artifacts,
                mock.patch.object(self.module, "verify_agents_exception", side_effect=AssertionError("AGENTS gate should be skipped")),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=AssertionError("Android gate should be skipped")),
            ):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    rc = self.module.main(
                        [
                            "--verify-prelive-packet-after-dryrun",
                            str(packet_path),
                            *path_args,
                            "--run-dir",
                            str(verify_dir),
                        ]
                    )

            self.assertEqual(rc, 0)
            verify_artifacts.assert_called_once()
            self.assertIn("verify-prelive-packet-after-dryrun ok", stdout.getvalue())
            log_text = (verify_dir / "s22plus_m34_s8b1_beacon_probe_live_gate.txt").read_text(encoding="utf-8")
            self.assertIn("prelive_packet_verify_after_dryrun=ok", log_text)
            self.assertIn(f"prelive_packet_verify_after_dryrun_dir={dryrun_dir}", log_text)
            self.assertFalse((verify_dir / "timeline.json").exists())

            Path(packet["planned_live_run_dir"]).mkdir()
            with mock.patch.object(self.module, "verify_m34_artifacts"):
                with self.assertRaises(SystemExit) as caught:
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.module.main(
                            [
                                "--verify-prelive-packet-after-dryrun",
                                str(packet_path),
                                *path_args,
                                "--run-dir",
                                str(root / "verify-after-live-dir"),
                            ]
                        )
            self.assertIn("planned run directory already exists", str(caught.exception))

    def test_verify_prelive_packet_after_dryrun_rejects_missing_dryrun_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            run_dir = root / "run"
            path_args = [
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
            ]
            with (
                mock.patch.object(self.module, "verify_m34_artifacts"),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=readonly_preflight_stub(self.module)),
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.module.main(["--prelive-packet", *path_args, "--run-dir", str(run_dir)])

            packet_path = run_dir / "s22plus_m34_s8b1_prelive_packet.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            dryrun_dir = Path(packet["planned_phase_run_dirs"]["dryrun"])
            dryrun_dir.mkdir()
            (dryrun_dir / "s22plus_m34_s8b1_beacon_probe_live_gate.txt").write_text(
                "android_stability_result=ok samples=2\n",
                encoding="utf-8",
            )
            with mock.patch.object(self.module, "verify_m34_artifacts"):
                with self.assertRaises(SystemExit) as caught:
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.module.main(
                            [
                                "--verify-prelive-packet-after-dryrun",
                                str(packet_path),
                                *path_args,
                                "--run-dir",
                                str(root / "verify-after-dryrun"),
                            ]
                        )
            self.assertIn("missing dry-run evidence markers", str(caught.exception))

    def test_verify_prelive_packet_rejects_moved_packet_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            run_dir = root / "run"
            path_args = [
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
            ]
            with (
                mock.patch.object(self.module, "verify_m34_artifacts"),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=readonly_preflight_stub(self.module)),
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.module.main(["--prelive-packet", *path_args, "--run-dir", str(run_dir)])

            moved_dir = root / "moved"
            moved_dir.mkdir()
            moved_packet = moved_dir / "s22plus_m34_s8b1_prelive_packet.json"
            moved_packet.write_text(
                (run_dir / "s22plus_m34_s8b1_prelive_packet.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            with mock.patch.object(self.module, "verify_m34_artifacts"):
                with self.assertRaises(SystemExit) as caught:
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.module.main(
                            [
                                "--verify-prelive-packet",
                                str(moved_packet),
                                *path_args,
                                "--run-dir",
                                str(root / "verify"),
                            ]
                        )
            self.assertIn("packet_run_dir does not match packet location", str(caught.exception))

    def test_verify_prelive_packet_rejects_missing_future_b2_hints(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            run_dir = root / "run"
            path_args = [
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
            ]
            with (
                mock.patch.object(self.module, "verify_m34_artifacts"),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=readonly_preflight_stub(self.module)),
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.module.main(["--prelive-packet", *path_args, "--run-dir", str(run_dir)])

            packet_path = run_dir / "s22plus_m34_s8b1_prelive_packet.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            packet["android_s8b1_predicate_baseline"].pop("future_b2_hints")
            packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with mock.patch.object(self.module, "verify_m34_artifacts"):
                with self.assertRaises(SystemExit) as caught:
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.module.main(
                            [
                                "--verify-prelive-packet",
                                str(packet_path),
                                *path_args,
                                "--run-dir",
                                str(root / "verify"),
                            ]
                        )
            self.assertIn("missing future_b2_hints", str(caught.exception))

    def test_verify_prelive_packet_rejects_missing_reset_context_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            run_dir = root / "run"
            path_args = [
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
            ]
            with (
                mock.patch.object(self.module, "verify_m34_artifacts"),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=readonly_preflight_stub(self.module)),
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.module.main(["--prelive-packet", *path_args, "--run-dir", str(run_dir)])

            packet_path = run_dir / "s22plus_m34_s8b1_prelive_packet.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            packet.pop("android_reset_context_baseline")
            packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with mock.patch.object(self.module, "verify_m34_artifacts"):
                with self.assertRaises(SystemExit) as caught:
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.module.main(
                            [
                                "--verify-prelive-packet",
                                str(packet_path),
                                *path_args,
                                "--run-dir",
                                str(root / "verify"),
                            ]
                        )
            self.assertIn("missing Android reset-context baseline", str(caught.exception))

    def test_verify_prelive_packet_rejects_material_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            odin = root / "odin4"
            odin.write_text("#!/bin/sh\n", encoding="utf-8")
            run_dir = root / "run"
            path_args = [
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
            ]
            with (
                mock.patch.object(self.module, "verify_m34_artifacts"),
                mock.patch.object(self.module, "run_android_readonly_preflight", side_effect=readonly_preflight_stub(self.module)),
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.module.main(["--prelive-packet", *path_args, "--run-dir", str(run_dir)])

            packet_path = run_dir / "s22plus_m34_s8b1_prelive_packet.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            packet["material_sha256"]["runbook"] = "0" * 64
            packet_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with mock.patch.object(self.module, "verify_m34_artifacts"):
                with self.assertRaises(SystemExit) as caught:
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.module.main(
                            [
                                "--verify-prelive-packet",
                                str(packet_path),
                                *path_args,
                                "--run-dir",
                                str(root / "verify"),
                            ]
                        )
            self.assertIn("material hash mismatch: runbook", str(caught.exception))

    def test_planned_live_run_dir_avoids_existing_siblings(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet_dir = Path(tmp) / "packet"
            packet_dir.mkdir()
            first = Path(f"{packet_dir}_live")
            first.mkdir()
            planned = self.module.planned_live_run_dir(packet_dir)
            self.assertEqual(planned, Path(f"{packet_dir}_live_00"))
            self.assertFalse(planned.exists())

    def test_runbook_phase_run_dir_keeps_live_result_dir_unique(self):
        base = Path("/tmp/s8b1-live")
        self.assertEqual(self.module.runbook_phase_run_dir(base, "live"), base)
        self.assertEqual(self.module.runbook_phase_run_dir(base, "preflight"), Path("/tmp/s8b1-live_preflight"))
        self.assertEqual(self.module.runbook_phase_run_dir(base, "template"), Path("/tmp/s8b1-live_template"))
        self.assertIsNone(self.module.runbook_phase_run_dir(None, "live"))
        self.assertEqual(
            self.module.runbook_phase_run_dirs(base),
            {
                "preflight": "/tmp/s8b1-live_preflight",
                "template": "/tmp/s8b1-live_template",
                "dryrun": "/tmp/s8b1-live_dryrun",
                "live": "/tmp/s8b1-live",
                "rollback": "/tmp/s8b1-live_rollback",
            },
        )

    def test_write_result_summary_creates_machine_readable_result_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "result.log"
            self.module.write_result_summary(
                run_dir,
                log_path,
                result="download-beacon-hit",
                rc=0,
                rollback_target=self.module.ROLLBACK_MAGISK,
                rollback_device="/dev/bus/usb/001/002",
                android_serial="RFCT519XWGK",
            )

            payload = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["schema"], "s22plus_m34_s8b1_result_v1")
            self.assertEqual(payload["target"], self.module.EXPECTED_TARGET)
            self.assertEqual(payload["stage"], "S8B1")
            self.assertEqual(payload["result"], "download-beacon-hit")
            self.assertEqual(payload["rc"], 0)
            self.assertEqual(payload["rollback_target"], self.module.ROLLBACK_MAGISK)
            self.assertEqual(payload["rollback_device"], "/dev/bus/usb/001/002")
            self.assertEqual(payload["android_serial"], "RFCT519XWGK")
            self.assertEqual(payload["candidate_ap_sha256"], self.module.EXPECTED_M34_AP_SHA256)
            self.assertEqual(payload["candidate_boot_sha256"], self.module.EXPECTED_M34_BOOT_SHA256)
            self.assertEqual(payload["candidate_init_sha256"], self.module.EXPECTED_M34_INIT_SHA256)
            self.assertEqual(payload["base_boot_sha256"], self.module.EXPECTED_M34_BASE_BOOT_SHA256)
            analysis = json.loads((run_dir / "s22plus_m34_s8b1_result_analysis.json").read_text(encoding="utf-8"))
            self.assertEqual(analysis["decision"], "s22plus-m34-s8b1-no-b1-proof")
            self.assertIsNone(analysis["timeline_json"])
            log_text = log_path.read_text(encoding="utf-8")
            self.assertIn("result_summary=", log_text)
            self.assertIn("result_analysis_json=", log_text)

    def test_rollback_boot_only_records_canonical_timeline_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "rollback.log"
            with (
                mock.patch.object(self.module, "flash_ap", return_value=0),
                mock.patch.object(self.module, "poll_android", return_value="RFCT519XWGK"),
                mock.patch.object(self.module, "verify_partition_hash"),
                mock.patch.object(self.module, "collect_android_pstore", return_value=False),
            ):
                rollback = self.module.rollback_boot_only_from_download(
                    odin=Path("/no/odin"),
                    rollback_ap=Path("/magisk.tar.md5"),
                    stock_boot_fallback_ap=Path("/stock.tar.md5"),
                    odin_device="/dev/bus/usb/001/002",
                    run_dir=run_dir,
                    log_path=log_path,
                    rollback_target=self.module.ROLLBACK_MAGISK,
                    android_wait_sec=1,
                    label="beacon_hit",
                )

            self.assertEqual(rollback.rc, 0)
            self.assertEqual(rollback.android_serial, "RFCT519XWGK")
            self.assertEqual(rollback.rollback_target, self.module.ROLLBACK_MAGISK)
            self.assertEqual(rollback.rollback_device, "/dev/bus/usb/001/002")
            timeline = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))
            self.assertEqual(set(timeline), {"events"})
            names = [event["name"] for event in timeline["events"]]
            self.assertIn("rollback_flash_start", names)
            self.assertIn("rollback_flash_done", names)
            self.assertIn("rollback_boot_ready", names)
            self.assertIn("beacon_hit_rollback_flash_start", names)
            self.assertIn("beacon_hit_rollback_flash_done", names)
            self.assertIn("beacon_hit_rollback_boot_ready", names)

    def test_rollback_boot_only_records_actual_stock_fallback_target_and_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "rollback_fallback.log"
            with (
                mock.patch.object(self.module, "flash_ap", side_effect=[9, 0]) as flash,
                mock.patch.object(self.module, "wait_for_odin", return_value="/dev/bus/usb/001/003"),
                mock.patch.object(self.module, "poll_android", return_value="RFCT519XWGK") as poll_android,
                mock.patch.object(self.module, "verify_partition_hash") as verify_hash,
                mock.patch.object(self.module, "collect_android_pstore", return_value=False),
            ):
                rollback = self.module.rollback_boot_only_from_download(
                    odin=Path("/no/odin"),
                    rollback_ap=Path("/magisk.tar.md5"),
                    stock_boot_fallback_ap=Path("/stock.tar.md5"),
                    odin_device="/dev/bus/usb/001/002",
                    run_dir=run_dir,
                    log_path=log_path,
                    rollback_target=self.module.ROLLBACK_MAGISK,
                    android_wait_sec=1,
                    label="beacon_hit",
                )

            self.assertEqual(rollback.rc, 0)
            self.assertEqual(rollback.android_serial, "RFCT519XWGK")
            self.assertEqual(rollback.rollback_target, self.module.ROLLBACK_STOCK)
            self.assertEqual(rollback.rollback_device, "/dev/bus/usb/001/003")
            self.assertEqual(flash.call_count, 2)
            poll_android.assert_called_once_with(log_path, 1, expect_root=False)
            verify_hash.assert_not_called()
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("magisk_rollback_failed_attempting_stock_fallback=1", text)
            self.assertIn("boot_restore_hash_check=skipped rollback_target=stock", text)
            timeline = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))
            names = [event["name"] for event in timeline["events"]]
            self.assertLess(
                names.index("beacon_hit_stock_fallback_flash_done"),
                names.index("rollback_flash_done"),
            )

    def test_rollback_from_download_result_json_uses_actual_fallback_target_and_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "rollback_only.log"
            fallback = self.module.RollbackResult(
                rc=0,
                android_serial="RFCT519XWGK",
                rollback_target=self.module.ROLLBACK_STOCK,
                rollback_device="/dev/bus/usb/001/003",
            )
            with (
                mock.patch.object(self.module, "odin_devices", return_value=["/dev/bus/usb/001/002"]),
                mock.patch.object(self.module, "rollback_boot_only_from_download", return_value=fallback),
            ):
                rc = self.module.rollback_from_download(
                    odin=Path("/no/odin"),
                    rollback_ap=Path("/magisk.tar.md5"),
                    stock_boot_fallback_ap=Path("/stock.tar.md5"),
                    run_dir=run_dir,
                    log_path=log_path,
                    rollback_target=self.module.ROLLBACK_MAGISK,
                    android_wait_sec=1,
                )

            self.assertEqual(rc, 0)
            payload = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "rollback-from-download-completed")
            self.assertEqual(payload["rollback_target"], self.module.ROLLBACK_STOCK)
            self.assertEqual(payload["rollback_device"], "/dev/bus/usb/001/003")
            self.assertEqual(payload["android_serial"], "RFCT519XWGK")

    def test_helper_result_and_timeline_are_accepted_by_s8b1_analyzer_for_hit(self):
        analyzer = load_analyzer()
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "result.log"
            for name in analyzer.REQUIRED_LIVE_PROOF_EVENTS:
                self.module.record_timeline_event(run_dir, name)
            self.module.write_result_summary(
                run_dir,
                log_path,
                result="download-beacon-hit",
                rc=0,
                rollback_target=self.module.ROLLBACK_MAGISK,
                rollback_device="/dev/bus/usb/001/002",
                android_serial="RFCT519XWGK",
            )

            result_payload = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            timeline_payload = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))
            analysis = analyzer.classify_result(result_payload, timeline_payload)
            written_analysis = json.loads(
                (run_dir / "s22plus_m34_s8b1_result_analysis.json").read_text(encoding="utf-8")
            )

            self.assertEqual(analysis["decision"], analyzer.DECISION_PROCEED_B2)
            self.assertTrue(analysis["ok_to_advance"])
            self.assertEqual(analysis["next_stage"], "S8B2")
            self.assertEqual(analysis["next_probe"], "port0_partner_exists")
            self.assertEqual(written_analysis["decision"], analyzer.DECISION_PROCEED_B2)
            self.assertTrue(written_analysis["ok_to_live_next_stage"])
            with contextlib.redirect_stdout(io.StringIO()):
                rc = analyzer.main([str(run_dir / "result.json"), "--require-live-next-stage"])
            self.assertEqual(rc, 0)

    def test_helper_result_and_timeline_are_accepted_by_s8b1_analyzer_for_miss(self):
        analyzer = load_analyzer()
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            log_path = run_dir / "result.log"
            for name in analyzer.REQUIRED_LIVE_PROOF_EVENTS:
                self.module.record_timeline_event(run_dir, name)
            self.module.write_result_summary(
                run_dir,
                log_path,
                result="download-beacon-miss-parked-manual-download-required",
                rc=0,
                rollback_target=self.module.ROLLBACK_MAGISK,
                rollback_device="/dev/bus/usb/001/002",
                android_serial="RFCT519XWGK",
            )

            result_payload = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            timeline_payload = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))
            analysis = analyzer.classify_result(result_payload, timeline_payload)
            written_analysis = json.loads(
                (run_dir / "s22plus_m34_s8b1_result_analysis.json").read_text(encoding="utf-8")
            )

            self.assertEqual(analysis["decision"], analyzer.DECISION_B1_MISS_STOP)
            self.assertFalse(analysis["ok_to_advance"])
            self.assertIsNone(analysis["next_stage"])
            self.assertEqual(written_analysis["decision"], analyzer.DECISION_B1_MISS_STOP)
            self.assertFalse(written_analysis["ok_to_advance"])
            with contextlib.redirect_stdout(io.StringIO()):
                rc = analyzer.main([str(run_dir / "result.json"), "--require-advance"])
            self.assertEqual(rc, 2)

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
