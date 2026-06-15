from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import native_audio_acdbtap_wrapper_exec_planner_v2487 as v2487


class V2487WrapperExecPlannerTests(unittest.TestCase):
    def test_source_boundary_is_freestanding_and_measurement_only(self) -> None:
        state = v2487.source_state()
        self.assertTrue(state["required_ok"])
        self.assertTrue(state["prohibited_ok"])
        self.assertTrue(state["required"]["raw_syscalls_only"])
        self.assertTrue(state["required"]["no_libc_headers"])
        self.assertFalse(state["prohibited"]["libc_setenv"])

    def test_materialize_module_contains_wrapper_original_and_tap_only(self) -> None:
        if not v2487.ORIGINAL_HAL.exists() or not v2487.v2476.TAP_SO.exists():
            self.skipTest("private vendor HAL or V2475 tap artifact is not available")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "module"
            manifest = v2487.materialize_module(out, clang=v2487.TOOLCHAIN_ROOT / "bin/clang", lld=v2487.TOOLCHAIN_ROOT / "bin/ld.lld", file_cmd="file")
            self.assertTrue(manifest["ok"])
            wrapper = out / v2487.WRAPPER_REL
            original = out / v2487.ORIGINAL_REL
            tap = out / v2487.TAP_REL
            self.assertTrue(wrapper.exists())
            self.assertTrue(original.exists())
            self.assertTrue(tap.exists())
            self.assertEqual(v2487.sha256(original), v2487.ORIGINAL_HAL_SHA256)
            self.assertEqual(v2487.sha256(tap), v2487.v2476.TAP_SHA256)
            self.assertIn("ELF 32-bit", manifest["wrapper_build"]["artifact"]["file"])
            self.assertIn("interpreter /system/bin/linker", manifest["wrapper_build"]["artifact"]["file"])
            for forbidden in ["service.sh", "post-fs-data.sh", "system.prop", "sepolicy.rule"]:
                self.assertFalse((out / forbidden).exists(), forbidden)

    def test_command_plan_uses_wrapper_overlay_not_service_rc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = v2487.command_plan(Path(tmp) / "module")
            flat = json.dumps(plan, sort_keys=True)
            self.assertIn(v2487.MODULE_ID, flat)
            self.assertIn(v2487.WRAPPER_REL, flat)
            self.assertIn(v2487.ORIGINAL_REL, flat)
            self.assertIn(v2487.TAP_REL, flat)
            self.assertIn("A90_ACDBTAP_V2487_INSTALL_OK", flat)
            self.assertIn("A90_ACDBTAP_V2487_VERIFY_OK", flat)
            self.assertIn("A90_ACDBTAP_V2487_CLEANUP_OK", flat)
            self.assertNotIn("android.hardware.audio.service.rc", flat)
            self.assertNotIn("setenforce 0", flat)
            self.assertNotIn("magisk --install-module", flat)
            self.assertNotIn("AUDIO_SET_CALIBRATION", flat)

    def test_su_c_commands_are_host_shell_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = v2487.command_plan(Path(tmp) / "module")
            for key in ["stage_setup", "install_module_direct", "verify_wrapper_after_reboot", "cleanup_exact_module"]:
                shell_command = plan[key][2]
                result = subprocess.run(
                    ["sh", "-n", "-c", shell_command],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, f"{key}: {result.stderr}")

    def test_command_safety_rejects_policy_service_rc_and_native_calibration(self) -> None:
        safe_payload = {
            "command_plan": v2487.command_plan(Path("workspace/private/builds/audio/unit")),
            "module": {
                "module_id": v2487.MODULE_ID,
                "wrapper_rel": v2487.WRAPPER_REL,
                "original_rel": v2487.ORIGINAL_REL,
                "tap_rel": v2487.TAP_REL,
                "wrapper_path": v2487.WRAPPER_PATH,
                "original_path": v2487.ORIGINAL_PATH,
                "tap_path": v2487.TAP_PATH,
            },
        }
        self.assertTrue(v2487.command_safety(safe_payload)["ok"])
        bad_payload = {"command_plan": {"bad": ["setenforce 0", "android.hardware.audio.service.rc", "AUDIO_SET_CALIBRATION"]}}
        findings = {item["name"] for item in v2487.command_safety(bad_payload)["findings"]}
        self.assertIn("silent_permissive", findings)
        self.assertIn("rc_override", findings)
        self.assertIn("native_cal_set_symbol", findings)


if __name__ == "__main__":
    unittest.main()
