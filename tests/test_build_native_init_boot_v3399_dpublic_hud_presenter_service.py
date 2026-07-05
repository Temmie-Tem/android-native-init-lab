"""Regression tests for V3399 durable D-public HUD presenter service source build."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3399_dpublic_hud_presenter_service")


class BuildNativeInitBootV3399DpublicHudPresenterServiceTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3399")
        self.assertEqual(builder.INIT_VERSION, "0.11.155")
        self.assertEqual(builder.INIT_BUILD, "v3399-dpublic-hud-presenter-service")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3399-dpublic-hud-presenter-service",
            b"0.11.155",
            b"dpublic-hud-presenter-service",
            b"A90WSTA140",
            b"forked-native-child-survives-switch-root",
            b"preserve-dpublic-hud-presenter",
            b"start.done=1",
            b"stop.done=1",
            b"status.debian_direct_kms=0",
            b"survives_handoff=1",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_previous_identity(self) -> None:
        text = builder._rewrite_v3399_text(
            "V3398 0.11.154 v3398-dpublic-hud-presenter "
            "dpublic-hud-presenter a90-doomgeneric-v3398"
        )
        self.assertIn("V3399", text)
        self.assertIn("0.11.155", text)
        self.assertIn("v3399-dpublic-hud-presenter-service", text)
        self.assertIn("a90-doomgeneric-v3399", text)
        self.assertNotIn("v3398", text)
        self.assertNotIn("0.11.154", text)

    def test_source_contains_service_control_and_handoff_preserve(self) -> None:
        source = Path("workspace/public/src/native-init/a90_server_distro.c").read_text(encoding="utf-8")
        dispatch = Path("workspace/public/src/native-init/v319/80_shell_dispatch.inc.c").read_text(
            encoding="utf-8"
        )
        header = Path("workspace/public/src/native-init/a90_server_distro.h").read_text(
            encoding="utf-8"
        )

        self.assertIn("A90_DPUBLIC_HUD_SERVICE_TAG \"A90WSTA140\"", source)
        self.assertIn("A90_DPUBLIC_HUD_GROUP_GID 3904", source)
        self.assertIn("A90_DPUBLIC_HUD_RUN_DIR_MODE 01770", source)
        self.assertIn("owner=root:a90hud mode=1770", source)
        self.assertIn("a90_server_distro_dpublic_hud_presenter_service_cmd", source)
        self.assertIn("dpublic_hud_service_child_loop", source)
        self.assertIn("forked-native-child-survives-switch-root", source)
        self.assertIn("dpublic_hud_service_pid_is_default(pid)", source)
        self.assertIn("action=preserve-dpublic-hud-presenter", source)
        self.assertIn("status.debian_direct_kms=0", source)
        self.assertIn("start.done=1", source)
        self.assertIn("stop.done=1", source)
        self.assertIn('"dpublic-hud-presenter-service"', dispatch)
        self.assertIn("handle_dpublic_hud_presenter_service", dispatch)
        self.assertIn("a90_server_distro_dpublic_hud_presenter_service_cmd", header)

    def test_boot_audit_manifest_records_service_contract(self) -> None:
        manifest = builder._boot_audit_manifest()
        service = manifest["dpublic_hud_presenter_service"]

        self.assertEqual(manifest["rung"], "dpublic-hud-presenter-service")
        self.assertEqual(service["command"], "dpublic-hud-presenter-service [start|status|stop] [options]")
        self.assertEqual(service["service"], "native-dpublic-hud-presenter")
        self.assertEqual(service["process_model"], "forked-native-child-survives-switch-root")
        self.assertEqual(service["pid_file"], "/run/a90-dpublic/hud-presenter.pid")
        self.assertEqual(service["status_file"], "/run/a90-dpublic/hud-presenter.status")
        self.assertEqual(service["intent"], "/run/a90-dpublic/hud-intent.json")
        self.assertEqual(service["runtime_dir"], "/run/a90-dpublic")
        self.assertEqual(service["runtime_dir_owner"], "root:a90hud")
        self.assertEqual(service["runtime_dir_mode"], "1770")
        self.assertEqual(service["intent_file_mode"], "0640")
        self.assertFalse(service["debian_direct_kms"])
        self.assertEqual(service["handoff_cleanup"], "preserve-dpublic-hud-presenter-when-armed")
        self.assertTrue(service["stop_releases_drm"])

    def test_candidate_manifest_records_service_type(self) -> None:
        manifest = {
            "boot_sha256": "a" * 64,
            "init_version": builder.INIT_VERSION,
            "init_build": builder.INIT_BUILD,
            "helper_sha256": "b" * 64,
            "boot_audit": builder._boot_audit_manifest(),
        }
        text = builder.json.dumps({
            "candidate_type": "dpublic-hud-presenter-service",
            "boot_sha256": manifest["boot_sha256"],
            "dpublic_hud_presenter_service": manifest["boot_audit"]["dpublic_hud_presenter_service"],
        })
        self.assertIn("dpublic-hud-presenter-service", text)
        self.assertIn("native-dpublic-hud-presenter", text)
        self.assertIn("preserve-dpublic-hud-presenter-when-armed", text)


if __name__ == "__main__":
    unittest.main()
