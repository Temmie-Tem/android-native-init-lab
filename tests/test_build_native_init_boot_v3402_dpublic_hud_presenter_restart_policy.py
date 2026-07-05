"""Regression tests for V3402 D-public HUD presenter restart policy source build."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3402_dpublic_hud_presenter_restart_policy")


class BuildNativeInitBootV3402DpublicHudPresenterRestartPolicyTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3402")
        self.assertEqual(builder.INIT_VERSION, "0.11.158")
        self.assertEqual(builder.INIT_BUILD, "v3402-dpublic-hud-presenter-restart-policy")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3402-dpublic-hud-presenter-restart-policy",
            b"0.11.158",
            b"A90WSTA146",
            b"restart-stop-start-stale-pid-cleanup",
            b"dpublic-hud-presenter-service [start|status|stop|restart]",
            b"start.stale_pid",
            b"status.restart_policy",
            b"restart.policy",
            b"restart.stop_rc",
            b"restart.start_rc",
            b"restart.done",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_previous_identity(self) -> None:
        text = builder._rewrite_v3402_text(
            "V3401 0.11.157 v3401-dpublic-hud-shared-run-bind "
            "a90-doomgeneric-v3401"
        )
        self.assertIn("V3402", text)
        self.assertIn("0.11.158", text)
        self.assertIn("v3402-dpublic-hud-presenter-restart-policy", text)
        self.assertIn("a90-doomgeneric-v3402", text)
        self.assertNotIn("v3401", text)
        self.assertNotIn("0.11.157", text)

    def test_source_contains_restart_and_stale_pid_cleanup_policy(self) -> None:
        source = Path("workspace/public/src/native-init/a90_server_distro.c").read_text(
            encoding="utf-8"
        )

        self.assertIn("A90_DPUBLIC_HUD_SERVICE_RESTART_TAG \"A90WSTA146\"", source)
        self.assertIn(
            "A90_DPUBLIC_HUD_SERVICE_RESTART_MODE \"restart-stop-start-stale-pid-cleanup\"",
            source,
        )
        self.assertIn("dpublic_hud_service_restart", source)
        self.assertIn("dpublic_hud_service_stop(opts)", source)
        self.assertIn("dpublic_hud_service_start(opts)", source)
        self.assertIn("start.stale_pid=%ld action=unlink", source)
        self.assertIn("stale-cleaned", source)
        self.assertIn("status.restart_policy=%s", source)
        self.assertIn("restart.policy=%s", source)
        self.assertIn("restart.stop_rc=%d", source)
        self.assertIn("restart.start_rc=%d", source)
        self.assertIn("restart.done=%d rc=%d", source)
        self.assertIn("[start|status|stop|restart]", source)

    def test_boot_audit_manifest_records_restart_policy_contract(self) -> None:
        manifest = builder._boot_audit_manifest()
        service = manifest["dpublic_hud_presenter_service"]

        self.assertEqual(manifest["rung"], "dpublic-hud-presenter-restart-policy")
        self.assertEqual(
            manifest["scope"],
            "native-root-owned-dpublic-hud-presenter-restart-policy",
        )
        self.assertEqual(service["restart_policy"], "restart-stop-start-stale-pid-cleanup")
        self.assertTrue(service["restart_command"])
        self.assertTrue(service["restart_releases_drm_before_start"])
        self.assertTrue(service["stale_pid_cleanup"])
        self.assertTrue(service["long_running_appliance_restart_policy"])
        self.assertTrue(service["handoff_shared_run_bind"])
        self.assertFalse(service["debian_direct_kms"])

    def test_candidate_manifest_records_restart_policy_type(self) -> None:
        manifest = {
            "boot_sha256": "a" * 64,
            "init_version": builder.INIT_VERSION,
            "init_build": builder.INIT_BUILD,
            "helper_sha256": "b" * 64,
            "boot_audit": builder._boot_audit_manifest(),
        }
        text = builder.json.dumps({
            "candidate_type": "dpublic-hud-presenter-restart-policy",
            "boot_sha256": manifest["boot_sha256"],
            "dpublic_hud_presenter_service": manifest["boot_audit"]["dpublic_hud_presenter_service"],
        })
        self.assertIn("dpublic-hud-presenter-restart-policy", text)
        self.assertIn("restart-stop-start-stale-pid-cleanup", text)
        self.assertIn("stale_pid_cleanup", text)


if __name__ == "__main__":
    unittest.main()
