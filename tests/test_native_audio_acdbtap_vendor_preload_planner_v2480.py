from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import native_audio_acdbtap_vendor_preload_planner_v2480 as v2480


class V2480VendorPreloadPlannerTests(unittest.TestCase):
    def test_materialize_module_contains_only_vendor_lib_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "module"
            manifest = v2480.materialize_module(out)
            self.assertTrue(manifest["ok"])
            self.assertTrue((out / "module.prop").exists())
            self.assertTrue((out / "README.md").exists())
            self.assertTrue((out / "system/vendor/lib/libacdbtap.so").exists())
            for forbidden in ["service.sh", "post-fs-data.sh", "system.prop", "sepolicy.rule"]:
                self.assertFalse((out / forbidden).exists(), forbidden)
            self.assertEqual(manifest["module_id"], v2480.MODULE_ID)
            self.assertIn("/vendor/lib/libacdbtap.so", manifest["preload_candidates"])
            self.assertIn("/system/vendor/lib/libacdbtap.so", manifest["preload_candidates"])

    def test_command_plan_uses_direct_module_staging_and_exact_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = v2480.command_plan(Path(tmp) / "module")
            flat = json.dumps(plan, sort_keys=True)
            self.assertIn(v2480.REMOTE_MODULE_DIR, flat)
            self.assertIn(v2480.MODULE_LIB_REL, flat)
            self.assertIn("chmod 755", flat)
            self.assertIn("A90_ACDBTAP_V2480_INSTALL_OK", flat)
            self.assertIn("A90_ACDBTAP_V2480_CLEANUP_OK", flat)
            self.assertIn("/vendor/lib/libacdbtap.so", flat)
            self.assertIn("/system/vendor/lib/libacdbtap.so", flat)
            self.assertNotIn("magisk --install-module", flat)
            self.assertNotIn("setenforce 0", flat)
            self.assertNotIn("AUDIO_SET_CALIBRATION", flat)
            self.assertNotIn("tinyplay", flat)

    def test_command_safety_ignores_metadata_forbidden_names_but_rejects_command_usage(self) -> None:
        safe_payload = {
            "command_plan": v2480.command_plan(Path("workspace/private/builds/audio/unit")),
            "module": {"forbidden_files_absent": {"forbidden": ["service.sh"]}},
        }
        self.assertTrue(v2480.command_safety(safe_payload)["ok"])
        bad_payload = {"command_plan": {"bad": ["setenforce 0", "magisk --install-module x.zip"]}}
        findings = {item["name"] for item in v2480.command_safety(bad_payload)["findings"]}
        self.assertIn("silent_permissive", findings)
        self.assertIn("magisk_install_module", findings)


if __name__ == "__main__":
    unittest.main()
