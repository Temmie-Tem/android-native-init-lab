from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta119_dropbear_admin_model.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta119_dropbear_admin_model.py")


class ServerDistroWsta119DropbearAdminModelTests(unittest.TestCase):
    def private_tmp(self):
        return tempfile.TemporaryDirectory(dir=runner.PRIVATE_ROOT)

    def args(self, root: Path, *extra: str):
        return runner.build_arg_parser().parse_args([
            "--run-dir",
            str(root / "wsta119"),
            *extra,
        ])

    def test_default_invocation_is_inert(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.args(root))

        self.assertEqual(result["decision"], "wsta119-blocked-emit-admin-model-required")
        self.assertFalse(result["safety"]["device_action"])
        self.assertFalse(result["safety"]["boot_flash"])
        self.assertFalse(result["safety"]["public_tunnel"])

    def test_admin_model_disables_root_login_and_uses_usb_admin_account(self) -> None:
        model = runner.dropbear_admin_model()
        checks = runner.validate_model(model)

        self.assertTrue(runner.model_passes(checks))
        self.assertEqual(model["service"], "dropbear-admin-usb")
        self.assertEqual(model["daemon_privilege_model"], "root-boundary-auth-daemon")
        self.assertEqual(model["target_identity"]["user"], "a90admin")
        self.assertEqual(model["target_identity"]["home"], "/home/a90admin")
        self.assertEqual(model["target_identity"]["shell"], "/bin/sh")
        self.assertEqual(model["auth"]["root_login"], "disabled")
        self.assertEqual(model["auth"]["password_login"], "disabled")
        self.assertEqual(model["auth"]["root_authorized_keys"], "absent-required")
        self.assertEqual(model["listen"]["bind_ip"], "192.168.7.2")
        self.assertEqual(model["listen"]["port"], 2222)
        self.assertFalse(model["listen"]["public_tunnel_allowed"])
        self.assertIn("-s", model["dropbear_options"])
        self.assertIn("-w", model["dropbear_options"])
        self.assertIn("-j", model["dropbear_options"])
        self.assertIn("-k", model["dropbear_options"])

    def test_admin_stage_script_replaces_only_known_placeholder_and_removes_root_key(self) -> None:
        script = runner.admin_stage_script("ssh-ed25519 AAAATEST operator@example")

        self.assertIn("A90WSTA119_ADMIN_MODEL_STAGE_BEGIN", script)
        self.assertIn("A90WSTA119_ADMIN_MODEL_STAGE_DONE", script)
        self.assertIn("a90admin:x:3903:3903:A90 admin a90admin:/home/a90admin:/bin/sh", script)
        self.assertIn("a90admin:x:3903:3903:A90 service a90admin:/nonexistent:/usr/sbin/nologin", script)
        self.assertIn("A90WSTA119_ACCOUNT_CONFLICT", script)
        self.assertIn("/home/a90admin/.ssh/authorized_keys", script)
        self.assertIn("/root/.ssh/authorized_keys", script)
        self.assertIn('/bin/rm -f "$ROOT_KEYS"', script)
        self.assertIn('A90WSTA119_ROOT_AUTHORIZED_KEYS_ABSENT=1', script)
        self.assertIn('/bin/chown "$ADMIN_UID:$ADMIN_GID" "$ADMIN_KEYS"', script)
        self.assertIn("/bin/chmod 0600", script)
        self.assertIn("-s -w -j -k", script)

    def test_dropbear_command_is_keyonly_root_denied_and_forwarding_disabled(self) -> None:
        command = runner.dropbear_command()

        self.assertEqual(command[0], "/usr/sbin/dropbear")
        self.assertIn("192.168.7.2:2222", command)
        self.assertIn("-s", command)
        self.assertIn("-w", command)
        self.assertIn("-j", command)
        self.assertIn("-k", command)

    def test_emit_admin_model_writes_private_source_pass(self) -> None:
        with self.private_tmp() as tmp:
            root = Path(tmp)
            result = runner.run(self.args(root, "--emit-admin-model"))
            saved = root / "wsta119" / runner.RESULT_NAME
            saved_exists = saved.is_file()

        self.assertEqual(result["decision"], runner.PASS_DECISION)
        self.assertTrue(saved_exists)
        self.assertTrue(result["checks"]["root_login_disabled"])
        self.assertTrue(result["checks"]["root_authorized_keys_absent_required"])
        self.assertTrue(result["checks"]["admin_shell_login_capable"])
        self.assertEqual(result["dropbear_admin_model"]["target_identity"]["user"], "a90admin")
        self.assertFalse(result["safety"]["device_action"])
        self.assertEqual(result["safety"]["secret_values_logged"], 0)

    def test_nonprivate_run_dir_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = runner.run(self.args(Path(tmp), "--emit-admin-model"))

        self.assertEqual(result["decision"], "wsta119-blocked-nonprivate-run-dir")

    def test_template_and_source_are_host_only(self) -> None:
        template = runner.template()
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--emit-admin-model", template["command"])
        self.assertFalse(template["device_action"])
        self.assertFalse(template["boot_flash"])
        self.assertIn("DROPBEAR_ADMIN_MODEL_SOURCE_DEFINED", source)
        self.assertIn("root-boundary-auth-daemon", source)
        self.assertIn("root login is disabled", source)
        self.assertIn("admin_public_key_value_logged", source)
        self.assertNotIn("native_init_flash.py", source)


if __name__ == "__main__":
    unittest.main()
