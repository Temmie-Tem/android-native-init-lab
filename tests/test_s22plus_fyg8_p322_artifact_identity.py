from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p322_artifact_identity.py"
)
SPEC = importlib.util.spec_from_file_location("p322_artifact_identity", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("P3.22 artifact identity source cannot be loaded")
artifact = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(artifact)


P321_AP = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p321/"
    "stock-candidate-build-v1-20260831-02/candidate-a/odin4/AP.tar.md5"
)
ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}


class P322ArtifactIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.image = artifact.stable_bytes(
            artifact.P319_IMAGE,
            "P319 source Image",
            64 * 1024 * 1024,
            artifact.P319_IMAGE_IDENTITY,
        )

    def test_delegate_source_and_run_defaults_are_exactly_rebound(self) -> None:
        self.assertEqual(artifact.P321_ARTIFACT_IDENTITY["size"], 26_923)
        self.assertEqual(
            artifact.P321_ARTIFACT_IDENTITY["sha256"],
            "dc303ef20175a7a6cbe350328fff499ef585edfba995735a990d0891e3570055",
        )
        self.assertEqual(
            artifact.validate_image.__kwdefaults__["expected_run_id"],
            artifact.P322_RUN_ID,
        )
        self.assertEqual(
            artifact.inspect_ap.__kwdefaults__["expected_run_id"],
            artifact.P322_RUN_ID,
        )

    def test_same_length_image_transform_is_deterministic_and_roundtrips(self) -> None:
        first, first_meta = artifact.transform_image(self.image)
        second, second_meta = artifact.transform_image(self.image)
        self.assertEqual(first, second)
        self.assertEqual(first_meta, second_meta)
        self.assertEqual(len(first), len(self.image))
        self.assertEqual(first_meta["target"]["run_id_hex"], artifact.P322_RUN_ID_HEX)
        self.assertEqual(
            first_meta["ikconfig"]["compressed_size"],
            artifact.IKCONFIG_COMPRESSED_SIZE,
        )
        self.assertEqual(artifact.validate_image(first)["run_id_hex"], artifact.P322_RUN_ID_HEX)
        self.assertEqual(artifact.validate_image(first)["identity"], artifact.identity(first))
        for old_id in (
            artifact.P319_RUN_ID_HEX,
            artifact.P320_RUN_ID_HEX,
            artifact.P321_RUN_ID_HEX,
        ):
            self.assertNotIn(old_id.encode("ascii"), first)

    def test_p319_p320_and_p321_image_ids_are_rejected(self) -> None:
        # The fixed source retains the P3.19 identity and cannot be accepted
        # as a P3.22 Image.
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.validate_image(self.image)

        transformed, _meta = artifact.transform_image(self.image)
        target_raw = artifact.P322_RUN_ID_HEX.encode("ascii")
        offset = transformed.find(target_raw)
        self.assertGreaterEqual(offset, 0)
        for old_id in (
            artifact.P319_RUN_ID_HEX,
            artifact.P320_RUN_ID_HEX,
            artifact.P321_RUN_ID_HEX,
        ):
            with self.subTest(old_id=old_id):
                stale = bytearray(transformed)
                stale[offset : offset + len(target_raw)] = old_id.encode("ascii")
                with self.assertRaises(artifact.ArtifactIdentityError):
                    artifact.validate_image(bytes(stale))

        for old_run_id in (
            artifact.P319_RUN_ID,
            artifact.P320_RUN_ID,
            artifact.P321_RUN_ID,
        ):
            with self.subTest(expected_run_id=old_run_id.hex()):
                with self.assertRaises(artifact.ArtifactIdentityError):
                    artifact.validate_image(transformed, expected_run_id=old_run_id)

    def test_boot_only_ap_inspection_rejects_predecessor_and_rollback_is_exact(self) -> None:
        # P3.21 is a real boot-only AP, but its predecessor Image identity must
        # not be attributed to P3.22 by the default inspection binding.
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.inspect_ap(P321_AP, label="P321 predecessor AP fixture")

        receipt = artifact.validate_rollback_ap(ROLLBACK_AP, ROLLBACK_IDENTITY)
        self.assertTrue(receipt["untouched"])
        self.assertEqual(receipt["ap_structure"]["member"]["name"], "boot.img.lz4")


if __name__ == "__main__":
    unittest.main()
