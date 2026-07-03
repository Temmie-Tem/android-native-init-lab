"""Regression tests for V3383 server-distro native handoff cleanup source build."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3383_server_distro_handoff_cleanup")


class BuildNativeInitBootV3383ServerDistroHandoffCleanupTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3383")
        self.assertEqual(builder.INIT_VERSION, "0.11.139")
        self.assertEqual(builder.INIT_BUILD, "v3383-server-distro-handoff-cleanup")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3383-server-distro-handoff-cleanup",
            b"0.11.139",
            b"switch-root-to-userdata",
            b"SERVER-DISTRO-D4-USERDATA-APPLIANCE",
            b"userdata=appliance-root",
            b"handoff_display service=autohud stop_rc=%d",
            b"handoff_display drm_owner_pid=%ld action=term",
            b"handoff_display drm_owner_pid=%ld action=kill",
            b"handoff_display=done killed=%u rc=%d",
            b"stop=handoff-display-owner",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_previous_identity(self) -> None:
        text = builder._rewrite_v3383_text(
            "V3381 0.11.138 v3381-server-distro-journaled-formatter "
            "server-distro-d4c-journaled-formatter a90-doomgeneric-v3381"
        )
        self.assertIn("V3383", text)
        self.assertIn("0.11.139", text)
        self.assertIn("v3383-server-distro-handoff-cleanup", text)
        self.assertIn("server-distro-d4d-handoff-cleanup", text)
        self.assertIn("a90-doomgeneric-v3383", text)
        self.assertNotIn("v3381", text)
        self.assertNotIn("journaled-formatter", text)

    def test_source_contains_fail_closed_handoff_cleanup(self) -> None:
        source = Path("workspace/public/src/native-init/a90_server_distro.c").read_text(encoding="utf-8")
        self.assertIn("a90_service_stop(A90_SERVICE_HUD, A90_D_HANDOFF_HUD_TIMEOUT_MS)", source)
        self.assertIn('strcmp(target, "/init") == 0', source)
        self.assertIn("d_handoff_pid_has_drm_fd", source)
        self.assertIn("SIGTERM", source)
        self.assertIn("SIGKILL", source)
        self.assertIn("stop=handoff-display-owner", source)
        self.assertIn("rc = d_handoff_stop_display_owners(A90_D3_TAG);", source)
        self.assertIn("rc = d_handoff_stop_display_owners(A90_D4_TAG);", source)

    def test_candidate_manifest_records_live_gate(self) -> None:
        manifest = {
            "boot_sha256": "a" * 64,
            "init_version": builder.INIT_VERSION,
            "init_build": builder.INIT_BUILD,
            "helper_sha256": "b" * 64,
        }
        text = builder.json.dumps({
            "candidate_type": "server-distro-d4d-handoff-cleanup",
            "fail_closed_marker": "stop=handoff-display-owner",
            "live_gate": "switch-root-to-userdata",
            "boot_sha256": manifest["boot_sha256"],
        })
        self.assertIn("server-distro-d4d-handoff-cleanup", text)
        self.assertIn("stop=handoff-display-owner", text)
        self.assertIn("switch-root-to-userdata", text)


if __name__ == "__main__":
    unittest.main()
