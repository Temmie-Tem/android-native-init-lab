"""Regression tests for V3400 D-public HUD presenter stale-log dedupe source build."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3400_dpublic_hud_presenter_service_dedupe")


class BuildNativeInitBootV3400DpublicHudPresenterServiceDedupeTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3400")
        self.assertEqual(builder.INIT_VERSION, "0.11.156")
        self.assertEqual(builder.INIT_BUILD, "v3400-dpublic-hud-presenter-service-dedupe")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3400-dpublic-hud-presenter-service-dedupe",
            b"0.11.156",
            b"A90WSTA142",
            b"same-content-consumed-or-rejected",
            b"status.intent_dedupe",
            b"dpublic-hud-presenter-service",
            b"forked-native-child-survives-switch-root",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_previous_identity(self) -> None:
        text = builder._rewrite_v3400_text(
            "V3399 0.11.155 v3399-dpublic-hud-presenter-service "
            "a90-doomgeneric-v3399"
        )
        self.assertIn("V3400", text)
        self.assertIn("0.11.156", text)
        self.assertIn("v3400-dpublic-hud-presenter-service-dedupe", text)
        self.assertIn("a90-doomgeneric-v3400", text)
        self.assertNotIn("v3399", text)
        self.assertNotIn("0.11.155", text)

    def test_source_dedupes_consumed_and_rejected_intent_content(self) -> None:
        source = Path("workspace/public/src/native-init/a90_server_distro.c").read_text(
            encoding="utf-8"
        )

        self.assertIn("A90_DPUBLIC_HUD_SERVICE_DEDUP_TAG \"A90WSTA142\"", source)
        self.assertIn(
            "A90_DPUBLIC_HUD_SERVICE_DEDUP_MODE \"same-content-consumed-or-rejected\"",
            source,
        )
        self.assertIn("dpublic_hud_service_same_content", source)
        self.assertIn("consumed_json", source)
        self.assertIn("rejected_json", source)
        self.assertIn("memcmp(left, right, left_used)", source)
        self.assertIn("status.intent_dedupe=%s", source)

    def test_boot_audit_manifest_records_dedupe_contract(self) -> None:
        manifest = builder._boot_audit_manifest()
        service = manifest["dpublic_hud_presenter_service"]

        self.assertEqual(manifest["rung"], "dpublic-hud-presenter-service-dedupe")
        self.assertEqual(
            manifest["scope"],
            "native-root-owned-dpublic-hud-presenter-service-stale-log-dedupe",
        )
        self.assertEqual(service["intent_dedupe"], "same-content-consumed-or-rejected")
        self.assertTrue(service["stale_log_spam_fix"])
        self.assertTrue(service["rejected_content_dedupe"])
        self.assertTrue(service["consumed_content_dedupe"])
        self.assertFalse(service["debian_direct_kms"])
        self.assertEqual(service["runtime_dir_mode"], "1770")

    def test_candidate_manifest_records_dedupe_type(self) -> None:
        manifest = {
            "boot_sha256": "a" * 64,
            "init_version": builder.INIT_VERSION,
            "init_build": builder.INIT_BUILD,
            "helper_sha256": "b" * 64,
            "boot_audit": builder._boot_audit_manifest(),
        }
        text = builder.json.dumps({
            "candidate_type": "dpublic-hud-presenter-service-dedupe",
            "boot_sha256": manifest["boot_sha256"],
            "dpublic_hud_presenter_service": manifest["boot_audit"]["dpublic_hud_presenter_service"],
        })
        self.assertIn("dpublic-hud-presenter-service-dedupe", text)
        self.assertIn("same-content-consumed-or-rejected", text)
        self.assertIn("stale_log_spam_fix", text)


if __name__ == "__main__":
    unittest.main()
