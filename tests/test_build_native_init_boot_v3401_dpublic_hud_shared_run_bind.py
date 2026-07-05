"""Regression tests for V3401 D-public HUD shared run-dir bind source build."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3401_dpublic_hud_shared_run_bind")


class BuildNativeInitBootV3401DpublicHudSharedRunBindTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3401")
        self.assertEqual(builder.INIT_VERSION, "0.11.157")
        self.assertEqual(builder.INIT_BUILD, "v3401-dpublic-hud-shared-run-bind")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3401-dpublic-hud-shared-run-bind",
            b"0.11.157",
            b"A90WSTA144",
            b"shared-run-dir-bind-before-switch-root",
            b"shared_run_bind=ok",
            b"stop=dpublic-hud-shared-run-bind",
            b"same-content-consumed-or-rejected",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_previous_identity(self) -> None:
        text = builder._rewrite_v3401_text(
            "V3400 0.11.156 v3400-dpublic-hud-presenter-service-dedupe "
            "a90-doomgeneric-v3400"
        )
        self.assertIn("V3401", text)
        self.assertIn("0.11.157", text)
        self.assertIn("v3401-dpublic-hud-shared-run-bind", text)
        self.assertIn("a90-doomgeneric-v3401", text)
        self.assertNotIn("v3400", text)
        self.assertNotIn("0.11.156", text)

    def test_source_mounts_and_binds_shared_hud_run_dir(self) -> None:
        source = Path("workspace/public/src/native-init/a90_server_distro.c").read_text(
            encoding="utf-8"
        )

        self.assertIn("A90_DPUBLIC_HUD_SERVICE_SHARED_TAG \"A90WSTA144\"", source)
        self.assertIn(
            "A90_DPUBLIC_HUD_SERVICE_SHARED_MODE \"shared-run-dir-bind-before-switch-root\"",
            source,
        )
        self.assertIn("dpublic_hud_service_mount_shared_run_dir", source)
        self.assertIn('"tmpfs"', source)
        self.assertIn('"mode=1770,uid=0,gid=3904,size=256k"', source)
        self.assertIn("d4_bind_dpublic_hud_run_dir", source)
        self.assertIn("MS_BIND", source)
        self.assertIn("shared_run_bind=ok", source)
        self.assertIn("stop=dpublic-hud-shared-run-bind", source)

    def test_boot_audit_manifest_records_shared_run_contract(self) -> None:
        manifest = builder._boot_audit_manifest()
        service = manifest["dpublic_hud_presenter_service"]

        self.assertEqual(manifest["rung"], "dpublic-hud-shared-run-bind")
        self.assertEqual(
            manifest["scope"],
            "native-root-owned-dpublic-hud-presenter-shared-intent-run-dir",
        )
        self.assertEqual(service["shared_run_dir"], "tmpfs-root-a90hud-1770")
        self.assertTrue(service["shared_run_dir_mount"])
        self.assertTrue(service["handoff_shared_run_bind"])
        self.assertEqual(
            service["handoff_shared_run_mode"],
            "shared-run-dir-bind-before-switch-root",
        )
        self.assertTrue(service["stale_log_spam_fix"])
        self.assertFalse(service["debian_direct_kms"])

    def test_candidate_manifest_records_shared_run_bind_type(self) -> None:
        manifest = {
            "boot_sha256": "a" * 64,
            "init_version": builder.INIT_VERSION,
            "init_build": builder.INIT_BUILD,
            "helper_sha256": "b" * 64,
            "boot_audit": builder._boot_audit_manifest(),
        }
        text = builder.json.dumps({
            "candidate_type": "dpublic-hud-shared-run-bind",
            "boot_sha256": manifest["boot_sha256"],
            "dpublic_hud_presenter_service": manifest["boot_audit"]["dpublic_hud_presenter_service"],
        })
        self.assertIn("dpublic-hud-shared-run-bind", text)
        self.assertIn("handoff_shared_run_bind", text)
        self.assertIn("tmpfs-root-a90hud-1770", text)


if __name__ == "__main__":
    unittest.main()
