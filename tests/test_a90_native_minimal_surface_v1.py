from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a90_native_minimal_surface_v1 as surface  # noqa: E402


class A90NativeMinimalSurfaceV1Tests(unittest.TestCase):
    def test_current_profile_has_exact_read_only_first_slice(self) -> None:
        value = surface.build_inventory(validate_private_pins=False)
        self.assertEqual(value["schema"], surface.SCHEMA)
        self.assertEqual(value["decision"], surface.DECISION)
        self.assertFalse(value["candidate_authority"])
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["device_effect"])
        self.assertFalse(value["artifact_write"])
        self.assertEqual(value["surface_counts"], surface.EXPECTED_COUNTS)
        first = value["first_removal_slice"]
        self.assertFalse(first["native_init_sources_changed"])
        self.assertFalse(first["native_init_cflags_changed"])
        self.assertFalse(first["helper_changed"])
        self.assertEqual(first["doom_sources_to_leave_product_closure"], 80)
        self.assertEqual(
            first["materialized_engine_sources_to_leave_product_closure"],
            3,
        )
        self.assertEqual(first["obsolete_ramdisk_engines_to_remove"], 22)
        self.assertTrue(first["builder_currently_requires_helper_and_engine"])

    def test_changed_surface_count_is_rejected(self) -> None:
        resolution = surface.buildlib.resolve_manifest(surface.DEFAULT_MANIFEST)
        changed = copy.deepcopy(resolution.data)
        changed["engine"]["doom_sources"] = changed["engine"][
            "doom_sources"
        ][:-1]
        with mock.patch.object(
            surface.buildlib,
            "resolve_manifest",
            return_value=surface.buildlib.ManifestResolution(
                data=changed,
                requested_path=resolution.requested_path,
                lineage=resolution.lineage,
                lineage_sha256=resolution.lineage_sha256,
                origins=resolution.origins,
                effective_sha256=resolution.effective_sha256,
            ),
        ):
            with self.assertRaisesRegex(
                surface.InventoryError,
                "resolved surface counts changed",
            ):
                surface.build_inventory(validate_private_pins=False)

    def test_candidate_authority_is_rejected(self) -> None:
        resolution = surface.buildlib.resolve_manifest(surface.DEFAULT_MANIFEST)
        changed = copy.deepcopy(resolution.data)
        changed["candidate_authority"] = True
        with mock.patch.object(
            surface.buildlib,
            "resolve_manifest",
            return_value=surface.buildlib.ManifestResolution(
                data=changed,
                requested_path=resolution.requested_path,
                lineage=resolution.lineage,
                lineage_sha256=resolution.lineage_sha256,
                origins=resolution.origins,
                effective_sha256=resolution.effective_sha256,
            ),
        ):
            with self.assertRaisesRegex(
                surface.InventoryError,
                "identity or authority changed",
            ):
                surface.build_inventory(validate_private_pins=False)


if __name__ == "__main__":
    unittest.main()
