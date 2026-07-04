from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta130_dpublic_hud_presenter_model.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta130_dpublic_hud_presenter_model.py")


class ServerDistroWsta130DpublicHudPresenterModelTests(unittest.TestCase):
    def private_tmp(self):
        return tempfile.TemporaryDirectory(dir=runner.PRIVATE_ROOT)

    def args(self, root: Path, *extra: str):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta130"),
            *extra,
        ])

    def test_default_invocation_is_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.args(root))

        self.assertEqual(result["decision"], "wsta130-blocked-emit-presenter-model-required")
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["boot_flash"])
        self.assertFalse(result["safety"]["public_tunnel"])
        self.assertFalse(result["safety"]["drm_open"])
        self.assertFalse(result["safety"]["kms_setcrtc"])

    def test_model_replaces_direct_nonroot_kms_with_native_presenter(self) -> None:
        model = runner.presenter_architecture_model()
        checks = runner.validate_model(model)

        self.assertTrue(runner.model_passes(checks))
        self.assertEqual(model["state"], "DPUBLIC_HUD_PRESENTER_MODEL_SOURCE_DEFINED")
        self.assertEqual(model["supersedes"]["wsta129_live_boundary"], "setcrtc-permission-denied")
        self.assertEqual(model["supersedes"]["direct_nonroot_kms"], "rejected-for-live-path")

        producer = model["debian_intent_producer"]
        self.assertEqual(producer["privilege_model"], "non-root-intent-producer")
        self.assertEqual(producer["target_identity"]["user"], "a90hud")
        self.assertEqual(producer["target_identity"]["uid"], 3904)
        self.assertFalse(producer["display_access"]["opens_drm"])
        self.assertFalse(producer["display_access"]["kms_setcrtc_allowed"])
        self.assertFalse(producer["network"]["opens_tcp_listener"])
        self.assertFalse(producer["network"]["opens_udp_socket"])

        presenter = model["presenter"]
        self.assertEqual(presenter["owner"], "native-init")
        self.assertEqual(presenter["privilege_model"], "root-owned-kms-presenter")
        self.assertTrue(presenter["kms_master_owner"])
        self.assertEqual(presenter["device_node"], "/dev/dri/card0")
        self.assertIn("DRM_IOCTL_MODE_SETCRTC", presenter["allowed_kms_ops"])
        self.assertIn("DRM_IOCTL_MODE_PAGE_FLIP", presenter["allowed_kms_ops"])
        self.assertIn("backlight-pmic-gpio-regulator", presenter["forbidden_ops"])

    def test_intent_schema_is_bounded_atomic_and_secret_averse(self) -> None:
        schema = runner.intent_schema()

        self.assertEqual(schema["schema"], "a90-dpublic-hud-intent-v1")
        self.assertLessEqual(schema["max_bytes"], 4096)
        self.assertLessEqual(schema["stale_after_ms"], 2000)
        self.assertEqual(schema["atomic_update"]["operation"], "write-fsync-rename")
        self.assertEqual(schema["atomic_update"]["final_path"], "/run/a90-dpublic/hud-intent.json")
        self.assertIn("sequence", schema["required_fields"])
        self.assertIn("monotonic_ms", schema["required_fields"])
        for field in ("url", "ssid", "psk", "token", "secret", "command", "path"):
            self.assertIn(field, schema["forbidden_fields"])

    def test_intent_producer_command_uses_launcher_without_drm_or_network_args(self) -> None:
        command = runner.intent_producer_command()
        rendered = " ".join(command)

        self.assertEqual(command[:2], ["/usr/local/bin/a90-service-launch", "dpublic-hud"])
        self.assertIn("/usr/local/bin/a90-dpublic-hud-intent", command)
        self.assertIn("--output", command)
        self.assertIn("/run/a90-dpublic/hud-intent.json", command)
        self.assertNotIn("/dev/dri/card0", rendered)
        self.assertNotIn("setcrtc", rendered.lower())
        self.assertNotIn("http://", rendered)
        self.assertNotIn("https://", rendered)

    def test_contract_plan_is_marker_only_and_boundary_specific(self) -> None:
        script = runner.contract_plan_shell()

        self.assertIn("A90WSTA130_HUD_PRESENTER_MODEL_BEGIN", script)
        self.assertIn("A90WSTA130_WSTA129_BOUNDARY=setcrtc-permission-denied", script)
        self.assertIn("A90WSTA130_DIRECT_NONROOT_KMS=rejected", script)
        self.assertIn("A90WSTA130_PRESENTER_OWNER=native-init", script)
        self.assertIn("A90WSTA130_PRESENTER_KMS_MASTER=1", script)
        self.assertIn("A90WSTA130_PRODUCER_DRM_OPEN=0", script)
        self.assertIn("A90WSTA130_PRODUCER_NETWORK=none", script)
        self.assertIn("A90WSTA130_HUD_PRESENTER_MODEL_DONE", script)
        self.assertNotIn("trycloudflare.com", script)
        self.assertNotIn("ssid=", script.lower())
        self.assertNotIn("psk=", script.lower())

    def test_emit_presenter_model_writes_private_source_pass(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.args(root, "--emit-presenter-model"))
            saved = root / "wsta130" / runner.RESULT_NAME
            saved_exists = saved.is_file()

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(saved_exists)
        self.assertTrue(result["checks"]["wsta129_boundary_acknowledged"])
        self.assertTrue(result["checks"]["direct_nonroot_kms_rejected"])
        self.assertTrue(result["checks"]["producer_no_drm_or_kms"])
        self.assertTrue(result["checks"]["producer_no_network"])
        self.assertTrue(result["checks"]["presenter_root_native_owner"])
        self.assertTrue(result["checks"]["intent_secret_fields_forbidden"])
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["drm_open"])
        self.assertEqual(result["safety"]["secret_values_logged"], 0)

    def test_nonprivate_run_dir_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.run(self.args(Path(tmp), "--emit-presenter-model"))

        self.assertEqual(result["decision"], "wsta130-blocked-nonprivate-run-dir")

    def test_template_and_source_are_host_only_and_redacted(self) -> None:
        template = runner.template()
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--emit-presenter-model", template["command"])
        self.assertFalse(template["device_action"])
        self.assertFalse(template["public_tunnel"])
        self.assertFalse(template["drm_open"])
        self.assertFalse(template["kms_setcrtc"])
        self.assertIn("DPUBLIC_HUD_PRESENTER_MODEL_SOURCE_DEFINED", source)
        self.assertIn("root-owned-kms-presenter", source)
        self.assertIn("non-root-intent-producer", source)
        self.assertIn("setcrtc-permission-denied", source)
        self.assertIn("public_url_value_logged", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())
        self.assertNotIn("trycloudflare.com", source.lower())


if __name__ == "__main__":
    unittest.main()
