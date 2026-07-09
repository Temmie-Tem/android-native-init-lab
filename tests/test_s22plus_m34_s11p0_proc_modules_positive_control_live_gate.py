import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path("workspace/public/src/scripts/revalidation/s22plus_m34_s11p0_proc_modules_positive_control_live_gate.py")
MANIFEST = Path("workspace/private/outputs/s22plus_native_init/m34_runtime_gadget_split_v0_14/manifest.json")


def load_module():
    script_dir = str(SCRIPT.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location("s22plus_m34_s11p0_proc_modules_positive_control_live_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusM34S11P0ProcModulesPositiveControlLiveGateTest(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_policy_markers_include_hashes_tokens_and_s11p0_semantics(self):
        markers = self.module.policy_required_markers()
        self.assertIn(self.module.LIVE_ACK_TOKEN, markers)
        self.assertIn(self.module.ROLLBACK_ACK_TOKEN, markers)
        self.assertIn(self.module.EXPECTED_M34_AP_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M34_BOOT_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M34_INIT_SHA256, markers)
        self.assertIn(self.module.EXPECTED_M34_TEMPLATE_SOURCE_SHA256, markers)
        self.assertIn(self.module.EXPECTED_MAGISK_AP_SHA256, markers)
        self.assertIn(self.module.EXPECTED_STOCK_BOOT_AP_SHA256, markers)
        self.assertIn("S11P0 keeps the S10C0/S9 module recipe", markers)
        self.assertIn("S11P0 positive-controls native-init /proc/modules with watchdog modules", markers)
        self.assertIn("module_load_probe=finit_cmd_db_accepted_and_watchdog_proc_visible", markers)
        self.assertIn("predicate=cmd_db_finit_accepted_and_watchdog_proc_visible", markers)
        self.assertIn("phase=s11_proc_modules_positive_control_probe", markers)
        self.assertIn("proc_modules=1", markers)
        self.assertIn("positive_control_proc_names=qcom_wdt_core,gh_virt_wdt", markers)
        self.assertIn("positive_control_modules=qcom_wdt_core.ko,gh_virt_wdt.ko", markers)
        self.assertIn("cmd_db_proc_seen=", markers)
        self.assertIn("qcom_wdt_core_proc_seen=", markers)
        self.assertIn("gh_virt_wdt_proc_seen=", markers)
        self.assertIn("watchdog_proc_seen=", markers)
        self.assertIn("true_action=reboot_download", markers)
        self.assertIn("false_action=park", markers)
        self.assertIn("HIT means native-init /proc/modules can see a watchdog positive control", markers)

    def test_active_template_is_exactly_verifiable(self):
        active = self.module.agents_exception_active_template()
        self.assertEqual(self.module.missing_policy_markers(active), [])
        self.assertIn("Narrow operator-authorized exception", active)
        self.assertIn(self.module.LIVE_ACK_TOKEN, active)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_path = root / "agents.log"
            (root / "AGENTS.md").write_text(active, encoding="utf-8")
            self.module.verify_agents_exception(root, log_path)
            text = log_path.read_text(encoding="utf-8")
            self.assertIn("agents_exception_missing=[]", text)
            self.assertIn("agents_exception_exact_active_template_present=1", text)

    @unittest.skipUnless(MANIFEST.exists(), "private M34 v0.14 manifest missing")
    def test_current_manifest_contract_matches_s11p0_live_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.module.verify_m34_manifest(MANIFEST, Path(tmp) / "manifest.log")

        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        by_label = {stage["label"]: stage for stage in data["stages"]}
        self.assertEqual(
            by_label["S11P0"]["hashes"]["ap_tar_md5"],
            self.module.EXPECTED_M34_AP_SHA256,
        )
        self.assertEqual(
            by_label["S11P0"]["runtime_steps"]["module_load_probe"],
            self.module.M34_S11P0_MODULE_LOAD_PROBE,
        )
        self.assertEqual(
            by_label["S11P0"]["ramdisk"]["added_subset_entry"],
            self.module.EXPECTED_MODULE_ENTRY,
        )

    @unittest.skipUnless(MANIFEST.exists(), "private M34 v0.14 manifest missing")
    def test_offline_check_verifies_artifacts_without_agents_or_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "offline"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = self.module.main(["--offline-check", "--run-dir", str(run_dir)])
            self.assertEqual(rc, 0)
            self.assertIn("offline-check ok", stdout.getvalue())
            log_text = (run_dir / "s22plus_m34_s11p0_proc_modules_positive_control_live_gate.txt").read_text(
                encoding="utf-8"
            )
            self.assertIn("offline_check=ok device_action=0 agents_exception_checked=0 android_checked=0", log_text)
            self.assertFalse((run_dir / "result.json").exists())
            self.assertFalse((run_dir / "timeline.json").exists())


if __name__ == "__main__":
    unittest.main()
