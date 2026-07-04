from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta122_cloudflared_service_model.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta122_cloudflared_service_model.py")


class ServerDistroWsta122CloudflaredServiceModelTests(unittest.TestCase):
    def private_tmp(self):
        return tempfile.TemporaryDirectory(dir=runner.PRIVATE_ROOT)

    def args(self, root: Path, *extra: str):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta122"),
            *extra,
        ])

    def test_default_invocation_is_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.args(root))

        self.assertEqual(result["decision"], "wsta122-blocked-emit-cloudflared-model-required")
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["boot_flash"])
        self.assertFalse(result["safety"]["public_tunnel"])

    def test_model_defines_nonroot_outbound_default_off_service(self) -> None:
        model = runner.cloudflared_service_model()
        checks = runner.validate_model(model)

        self.assertTrue(runner.model_passes(checks))
        self.assertEqual(model["service"], "cloudflared-quick-tunnel")
        self.assertEqual(model["daemon_privilege_model"], "non-root-outbound-client")
        self.assertEqual(model["target_identity"]["user"], "a90tunnel")
        self.assertEqual(model["target_identity"]["uid"], 3902)
        self.assertEqual(model["target_identity"]["shell"], "/usr/sbin/nologin")
        self.assertEqual(model["default_exposure"]["public_default"], "off")
        self.assertEqual(
            model["default_exposure"]["start_requires_private_enable_file"],
            "/etc/a90-dpublic/cloudflared-quick-enable",
        )
        self.assertTrue(model["network"]["outbound_tunnel_client"])
        self.assertFalse(model["network"]["public_inbound_listener"])
        self.assertEqual(model["network"]["origin_url"], "http://127.0.0.1:8080")
        self.assertEqual(model["network"]["metrics_bind"], "127.0.0.1:0")

    def test_command_is_quick_tunnel_loopback_origin_without_autoupdate(self) -> None:
        command = runner.cloudflared_command()
        launcher = runner.launcher_command()

        self.assertEqual(command[0], "/usr/local/bin/cloudflared")
        self.assertIn("tunnel", command)
        self.assertIn("--no-autoupdate", command)
        self.assertIn("--url", command)
        self.assertIn("http://127.0.0.1:8080", command)
        self.assertIn("--metrics", command)
        self.assertIn("127.0.0.1:0", command)
        self.assertEqual(launcher[:2], ["/usr/local/bin/a90-service-launch", "cloudflared-quick-tunnel"])
        self.assertEqual(launcher[2:], command)

    def test_launch_plan_is_marker_only_and_public_url_safe(self) -> None:
        script = runner.launch_plan_shell()

        self.assertIn("A90WSTA122_CLOUDFLARED_MODEL_BEGIN", script)
        self.assertIn("A90WSTA122_CLOUDFLARED_MODEL_DONE", script)
        self.assertIn("A90WSTA122_QUICK_ENABLE_PRESENT=0", script)
        self.assertIn("A90WSTA122_EXPECT_USER=a90tunnel", script)
        self.assertIn("A90WSTA122_EXPECT_NO_NEW_PRIVS=1", script)
        self.assertIn("A90WSTA122_EXPECT_CAPEFF_ZERO=1", script)
        self.assertIn("/run/a90-dpublic/cloudflared-live.url", script)
        self.assertNotIn("trycloudflare.com", script)

    def test_emit_cloudflared_model_writes_private_source_pass(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.args(root, "--emit-cloudflared-model"))
            saved = root / "wsta122" / runner.RESULT_NAME
            saved_exists = saved.is_file()

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(saved_exists)
        self.assertTrue(result["checks"]["non_root_user_ok"])
        self.assertTrue(result["checks"]["default_public_off"])
        self.assertTrue(result["checks"]["launcher_no_new_privs_required"])
        self.assertTrue(result["checks"]["launcher_caps_zero_required"])
        self.assertTrue(result["checks"]["direct_root_start_rejected_for_always_on"])
        self.assertFalse(result["safety"]["device_action"])
        self.assertEqual(result["safety"]["secret_values_logged"], 0)

    def test_nonprivate_run_dir_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.run(self.args(Path(tmp), "--emit-cloudflared-model"))

        self.assertEqual(result["decision"], "wsta122-blocked-nonprivate-run-dir")

    def test_template_and_source_are_host_only_and_redacted(self) -> None:
        template = runner.template()
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--emit-cloudflared-model", template["command"])
        self.assertFalse(template["device_action"])
        self.assertFalse(template["public_tunnel"])
        self.assertIn("CLOUDFLARED_SERVICE_MODEL_SOURCE_DEFINED", source)
        self.assertIn("non-root-outbound-client", source)
        self.assertIn("not-acceptable-for-always-on-profile", source)
        self.assertIn("public_url_value_logged", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())
        self.assertNotIn("trycloudflare.com", source.lower())


if __name__ == "__main__":
    unittest.main()
