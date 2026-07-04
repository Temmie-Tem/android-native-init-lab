from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta132_dpublic_hud_split_prototype.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta132_dpublic_hud_split_prototype.py")


class ServerDistroWsta132DpublicHudSplitPrototypeTests(unittest.TestCase):
    def private_tmp(self):
        return tempfile.TemporaryDirectory(dir=runner.PRIVATE_ROOT)

    def args(self, root: Path, *extra: str):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta132"),
            *extra,
        ])

    def test_default_invocation_is_inert(self) -> None:
        with self.private_tmp() as tmp:
            result = runner.run(self.args(Path(tmp)))

        self.assertEqual(result["decision"], "wsta132-blocked-emit-split-prototype-required")
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["boot_flash"])
        self.assertFalse(result["safety"]["native_reboot"])
        self.assertFalse(result["safety"]["public_tunnel"])
        self.assertFalse(result["safety"]["drm_open"])
        self.assertFalse(result["safety"]["kms_setcrtc"])

    def test_source_contract_splits_debian_intent_from_native_presenter(self) -> None:
        contract = runner.source_contract()

        self.assertTrue(contract["intent_source_present"])
        self.assertTrue(contract["presenter_source_present"])
        self.assertTrue(contract["intent_uses_atomic_rename"])
        self.assertTrue(contract["intent_chmod_0640"])
        self.assertTrue(contract["intent_no_drm"])
        self.assertTrue(contract["intent_no_network_api"])
        self.assertTrue(contract["presenter_has_strict_parser"])
        self.assertTrue(contract["presenter_bounds_intent"])
        self.assertTrue(contract["presenter_kms_owner_contract"])
        self.assertTrue(contract["presenter_no_exec_shell_network"])
        self.assertTrue(contract["schema_matches_wsta130"])
        self.assertFalse(contract["public_url_value_logged"])
        self.assertEqual(contract["secret_values_logged"], 0)

    def test_emit_split_prototype_builds_selftests_and_stages_arm64_binaries(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            run_dir = root / "wsta132"
            result = runner.run(self.args(root, "--emit-split-prototype"))
            saved = run_dir / runner.RESULT_NAME
            intent_json = run_dir / runner.INTENT_FILE
            staged_intent = run_dir / "rootfs-stage" / runner.INTENT_TARGET
            staged_presenter = run_dir / "rootfs-stage" / runner.PRESENTER_TARGET
            payload = json.loads(intent_json.read_text(encoding="utf-8"))
            evidence = {
                "saved_exists": saved.is_file(),
                "intent_json_exists": intent_json.is_file(),
                "staged_intent_exists": staged_intent.is_file(),
                "staged_presenter_exists": staged_presenter.is_file(),
                "payload": payload,
            }

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(evidence["saved_exists"])
        self.assertTrue(evidence["intent_json_exists"])
        self.assertTrue(evidence["staged_intent_exists"])
        self.assertTrue(evidence["staged_presenter_exists"])
        self.assertTrue(result["checks"]["source_contract_ok"])
        self.assertTrue(result["checks"]["host_build_ok"])
        self.assertTrue(result["checks"]["arm64_build_ok"])
        self.assertTrue(result["checks"]["host_selftest_ok"])
        self.assertTrue(result["checks"]["rootfs_stage_ok"])
        self.assertTrue(result["checks"]["default_public_off"])
        self.assertEqual(evidence["payload"]["schema"], "a90-dpublic-hud-intent-v1")
        self.assertEqual(evidence["payload"]["public_state"], "PUBLIC_OFF")
        for key in ("command", "argv", "path", "shell", "url", "ssid", "psk", "token", "secret"):
            self.assertNotIn(key, evidence["payload"])
        self.assertEqual(result["safety"]["secret_values_logged"], 0)

    def test_nonprivate_run_dir_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.run(self.args(Path(tmp), "--emit-split-prototype"))

        self.assertEqual(result["decision"], "wsta132-blocked-nonprivate-run-dir")

    def test_template_and_source_are_host_only_and_redacted(self) -> None:
        template = runner.template()
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--emit-split-prototype", template["command"])
        self.assertFalse(template["device_action"])
        self.assertFalse(template["public_tunnel"])
        self.assertFalse(template["drm_open"])
        self.assertFalse(template["kms_setcrtc"])
        self.assertIn("WSTA132 host-only", source)
        self.assertIn("a90_dpublic_hud_intent.c", source)
        self.assertIn("a90_dpublic_hud_presenter.c", source)
        self.assertIn("rootfs-stage", source)
        self.assertIn("public_url_value_logged", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())
        self.assertNotIn("trycloudflare.com", source.lower())


if __name__ == "__main__":
    unittest.main()
