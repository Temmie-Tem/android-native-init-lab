from __future__ import annotations

from pathlib import Path
import unittest
import sys


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p344_artifact_identity as artifact  # noqa: E402


class P344ArtifactIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output = ROOT / (
            "workspace/private/outputs/s22plus_fyg8_p344/"
            "stock-candidate-build-v1-20260905-01"
        )

    def test_identity_is_fresh_boot_only_and_rejects_consumed_p343(self) -> None:
        value = artifact.validate_p344_identity()
        self.assertEqual(value["run_id_hex"], artifact.P344_RUN_ID_HEX)
        self.assertEqual(
            value["predecessor_run_id_rejected"],
            artifact.P343_PREDECESSOR_RUN_ID_HEX,
        )
        self.assertEqual(
            value["predecessor_ap_identity_rejected"], artifact.P343_AP_IDENTITY
        )
        self.assertEqual(value["image_identity"], artifact.P344_IMAGE_IDENTITY)
        self.assertEqual(value["ap_identity"], artifact.P344_AP_IDENTITY)
        self.assertTrue(value["boot_only"])
        self.assertTrue(value["ab_must_match"])
        self.assertTrue(value["runtime_behavior_unchanged"])
        self.assertTrue(value["catalog_unchanged"])
        self.assertIn(artifact.P343_AP_IDENTITY, artifact.STALE_AP_IDENTITIES)

    def test_identity_transform_preserves_40695_byte_gzip_geometry(self) -> None:
        original = artifact.P343_IMAGE.read_bytes()
        transformed, receipt = artifact.transform_image(original)
        self.assertEqual(len(transformed), len(original))
        self.assertEqual(artifact.identity(transformed), artifact.P344_IMAGE_IDENTITY)
        self.assertEqual(receipt["method"], "identity_only_post_link_v1")
        self.assertEqual(
            receipt["source"]["run_id_hex"],
            artifact.P343_PREDECESSOR_RUN_ID_HEX,
        )
        self.assertEqual(receipt["target"]["run_id_hex"], artifact.P344_RUN_ID_HEX)
        self.assertEqual(receipt["ikconfig"]["compressed_size"], 40_695)
        self.assertTrue(all(receipt["preserved"].values()))
        self.assertEqual(
            artifact.validate_image(transformed)["run_id_hex"], artifact.P344_RUN_ID_HEX
        )
        self.assertNotIn(
            artifact.P343_PREDECESSOR_RUN_ID_HEX.encode("ascii"), transformed
        )

    def test_real_built_ab_joins_fresh_image_init_and_child(self) -> None:
        image = (self.output / "inputs/fixed-Image").read_bytes()
        init = (self.output / "userspace-a/init").read_bytes()
        child = (self.output / "userspace-a/s22-e1-child").read_bytes()
        for label in ("a", "b"):
            value = artifact.inspect_ap(
                self.output / f"candidate-{label}/odin4/AP.tar.md5",
                expected_run_id=artifact.P344_RUN_ID,
                expected_image=image,
                expected_init=init,
                expected_child=child,
                expected_ap=artifact.P344_AP_IDENTITY,
                label=f"P344 candidate {label} AP",
            )
            self.assertTrue(value["joined"])
            self.assertEqual(value["run_id_hex"], artifact.P344_RUN_ID_HEX)

    def test_consumed_p343_ap_is_not_rollback(self) -> None:
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.validate_rollback_ap(
                self.output / "candidate-a/odin4/AP.tar.md5",
                artifact.P343_AP_IDENTITY,
            )


if __name__ == "__main__":
    unittest.main()
