from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import native_audio_acdbtap_service_env_planner_v2484 as v2484


class V2484ServiceEnvPlannerTests(unittest.TestCase):
    def test_materialize_module_contains_lib_and_rc_override_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "module"
            manifest = v2484.materialize_module(out)
            self.assertTrue(manifest["ok"])
            self.assertTrue((out / "module.prop").exists())
            self.assertTrue((out / "README.md").exists())
            self.assertTrue((out / v2484.MODULE_LIB_REL).exists())
            rc = out / v2484.MODULE_RC_REL
            self.assertTrue(rc.exists())
            text = rc.read_text()
            self.assertIn(v2484.RC_MARKER, text)
            self.assertIn("service vendor.audio-hal /vendor/bin/hw/android.hardware.audio.service", text)
            self.assertIn(f"setenv LD_PRELOAD {v2484.VENDOR_LIB_PATH}", text)
            self.assertIn(f"setenv A90_ACDBTAP_DIR {v2484.CAPTURE_DIR}", text)
            for forbidden in ["service.sh", "post-fs-data.sh", "system.prop", "sepolicy.rule"]:
                self.assertFalse((out / forbidden).exists(), forbidden)

    def test_command_plan_stages_rc_override_and_uses_exact_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = v2484.command_plan(Path(tmp) / "module")
            flat = json.dumps(plan, sort_keys=True)
            self.assertIn(v2484.REMOTE_MODULE_DIR, flat)
            self.assertIn(v2484.MODULE_LIB_REL, flat)
            self.assertIn(v2484.MODULE_RC_REL, flat)
            self.assertIn(v2484.RC_MARKER, flat)
            self.assertIn("A90_ACDBTAP_V2484_INSTALL_OK", flat)
            self.assertIn("A90_ACDBTAP_V2484_VERIFY_OK", flat)
            self.assertIn("A90_ACDBTAP_V2484_CLEANUP_OK", flat)
            self.assertNotIn("magisk --install-module", flat)
            self.assertNotIn("setenforce 0", flat)
            self.assertNotIn("AUDIO_SET_CALIBRATION", flat)
            self.assertNotIn("tinyplay", flat)

    def test_su_c_commands_are_host_shell_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = v2484.command_plan(Path(tmp) / "module")
            for key in ["stage_setup", "install_module_direct", "verify_service_env_after_reboot", "cleanup_exact_module"]:
                shell_command = plan[key][2]
                result = subprocess.run(
                    ["sh", "-n", "-c", shell_command],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, f"{key}: {result.stderr}")

    def test_command_safety_requires_service_env_and_rejects_unsafe_tokens(self) -> None:
        safe_payload = {
            "command_plan": v2484.command_plan(Path("workspace/private/builds/audio/unit")),
            "module": {
                "module_id": v2484.MODULE_ID,
                "module_lib_rel": v2484.MODULE_LIB_REL,
                "module_rc_rel": v2484.MODULE_RC_REL,
                "vendor_lib_path": v2484.VENDOR_LIB_PATH,
                "vendor_rc_path": v2484.VENDOR_RC_PATH,
                "rc_marker": v2484.RC_MARKER,
                "rc": "setenv LD_PRELOAD\nsetenv A90_ACDBTAP_DIR",
            },
        }
        self.assertTrue(v2484.command_safety(safe_payload)["ok"])
        bad_payload = {"command_plan": {"bad": ["setenforce 0", "magisk --install-module x.zip", "AUDIO_SET_CALIBRATION"]}}
        findings = {item["name"] for item in v2484.command_safety(bad_payload)["findings"]}
        self.assertIn("silent_permissive", findings)
        self.assertIn("magisk_install_module", findings)
        self.assertIn("native_calibration", findings)


if __name__ == "__main__":
    unittest.main()
