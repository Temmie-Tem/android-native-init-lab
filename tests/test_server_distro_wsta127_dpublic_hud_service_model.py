from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta127_dpublic_hud_service_model.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta127_dpublic_hud_service_model.py")


class ServerDistroWsta127DpublicHudServiceModelTests(unittest.TestCase):
    def private_tmp(self):
        return tempfile.TemporaryDirectory(dir=runner.PRIVATE_ROOT)

    def args(self, root: Path, *extra: str):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta127"),
            *extra,
        ])

    def test_default_invocation_is_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.args(root))

        self.assertEqual(result["decision"], "wsta127-blocked-emit-hud-model-required")
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["boot_flash"])
        self.assertFalse(result["safety"]["public_tunnel"])
        self.assertFalse(result["safety"]["drm_open"])
        self.assertFalse(result["safety"]["kms_setcrtc"])

    def test_model_defines_nonroot_no_network_drm_hud(self) -> None:
        model = runner.hud_service_model()
        checks = runner.validate_model(model)

        self.assertTrue(runner.model_passes(checks))
        self.assertEqual(model["service"], "dpublic-hud")
        self.assertEqual(model["daemon_privilege_model"], "non-root-drm-client")
        self.assertEqual(model["target_identity"]["user"], "a90hud")
        self.assertEqual(model["target_identity"]["uid"], 3904)
        self.assertEqual(model["target_identity"]["gid"], 3904)
        self.assertEqual(model["target_identity"]["shell"], "/usr/sbin/nologin")
        self.assertEqual(model["network"]["network_intent"], "no-network-drm-output-only")
        self.assertFalse(model["network"]["opens_tcp_listener"])
        self.assertFalse(model["network"]["opens_udp_socket"])
        self.assertFalse(model["network"]["public_inbound_listener"])
        self.assertEqual(model["display"]["device_node"], "/dev/dri/card0")
        self.assertEqual(model["display"]["device_source"], "/sys/class/drm/card0/dev")
        self.assertTrue(model["display"]["drm_master_required"])
        self.assertEqual(model["display"]["kms_surface"], "dumb-framebuffer-xbgr8888")

    def test_command_uses_launcher_without_network_url_or_token(self) -> None:
        command = runner.hud_command()
        launcher = runner.launcher_command()

        self.assertEqual(command, ["/usr/local/bin/a90-dpublic-hud"])
        self.assertEqual(launcher[:2], ["/usr/local/bin/a90-service-launch", "dpublic-hud"])
        self.assertEqual(launcher[2:], command)
        rendered = " ".join(launcher)
        self.assertNotIn("http://", rendered)
        self.assertNotIn("https://", rendered)
        self.assertNotIn("token", rendered.lower())

    def test_launch_plan_is_marker_only_and_hud_safe(self) -> None:
        script = runner.launch_plan_shell()

        self.assertIn("A90WSTA127_HUD_MODEL_BEGIN", script)
        self.assertIn("A90WSTA127_HUD_MODEL_DONE", script)
        self.assertIn("A90WSTA127_EXPECT_USER=a90hud", script)
        self.assertIn("A90WSTA127_EXPECT_NO_NEW_PRIVS=1", script)
        self.assertIn("A90WSTA127_EXPECT_CAPEFF_ZERO=1", script)
        self.assertIn("A90WSTA127_EXPECT_DRM_NODE=/dev/dri/card0", script)
        self.assertIn("A90WSTA127_EXPECT_NETWORK=none", script)
        self.assertNotIn("trycloudflare.com", script)
        self.assertNotIn("ssid=", script.lower())
        self.assertNotIn("psk=", script.lower())

    def test_emit_hud_model_writes_private_source_pass(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.args(root, "--emit-hud-model"))
            saved = root / "wsta127" / runner.RESULT_NAME
            saved_exists = saved.is_file()

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(saved_exists)
        self.assertTrue(result["checks"]["non_root_user_ok"])
        self.assertTrue(result["checks"]["no_network_listener"])
        self.assertTrue(result["checks"]["drm_node_policy_defined"])
        self.assertTrue(result["checks"]["launcher_no_new_privs_required"])
        self.assertTrue(result["checks"]["launcher_caps_zero_required"])
        self.assertTrue(result["checks"]["direct_root_start_rejected_for_always_on"])
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["drm_open"])
        self.assertEqual(result["safety"]["secret_values_logged"], 0)

    def test_nonprivate_run_dir_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.run(self.args(Path(tmp), "--emit-hud-model"))

        self.assertEqual(result["decision"], "wsta127-blocked-nonprivate-run-dir")

    def test_template_and_source_are_host_only_and_redacted(self) -> None:
        template = runner.template()
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--emit-hud-model", template["command"])
        self.assertFalse(template["device_action"])
        self.assertFalse(template["public_tunnel"])
        self.assertFalse(template["drm_open"])
        self.assertFalse(template["kms_setcrtc"])
        self.assertIn("DPUBLIC_HUD_SERVICE_MODEL_SOURCE_DEFINED", source)
        self.assertIn("non-root-drm-client", source)
        self.assertIn("not-acceptable-for-always-on-profile", source)
        self.assertIn("public_url_value_logged", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())
        self.assertNotIn("trycloudflare.com", source.lower())


if __name__ == "__main__":
    unittest.main()
