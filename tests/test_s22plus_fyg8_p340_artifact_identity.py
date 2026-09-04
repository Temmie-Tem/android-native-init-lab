from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p340_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p339_artifact_identity as predecessor  # noqa: E402


class P340ArtifactIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.image = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p339/"
            "stock-candidate-build-v1-20260905-04/inputs/fixed-Image"
        ).read_bytes()

    def test_fresh_identity_is_boot_only_and_rejects_p339(self) -> None:
        value = artifact.validate_p340_identity()
        self.assertEqual(value["run_id_hex"], artifact.P340_RUN_ID_HEX)
        self.assertEqual(
            value["predecessor_run_id_rejected"],
            artifact.P339_PREDECESSOR_RUN_ID_HEX,
        )
        self.assertEqual(value["predecessor_ap_identity_rejected"], artifact.P339_AP_IDENTITY)
        self.assertTrue(value["boot_only"])
        self.assertTrue(value["ab_must_match"])
        self.assertFalse(value["auth_key_path_published"])
        self.assertIn(artifact.P339_AP_IDENTITY, artifact.STALE_AP_IDENTITIES)

    def test_identity_transform_preserves_image_geometry_and_sections(self) -> None:
        transformed, receipt = artifact.transform_image(self.image)
        self.assertEqual(len(transformed), len(self.image))
        self.assertEqual(receipt["method"], "identity_only_post_link_v1")
        self.assertEqual(receipt["source"]["run_id_hex"], artifact.P339_PREDECESSOR_RUN_ID_HEX)
        self.assertEqual(receipt["target"]["run_id_hex"], artifact.P340_RUN_ID_HEX)
        self.assertEqual(receipt["ikconfig"]["compressed_size"], 40_695)
        self.assertEqual(receipt["ikconfig"]["old_compressed"]["size"], 40_695)
        self.assertEqual(receipt["ikconfig"]["new_compressed"]["size"], 40_695)
        self.assertEqual(receipt["raw_rodata"]["size"], 32)
        self.assertTrue(all(receipt["preserved"].values()))
        checked = artifact.validate_image(transformed)
        self.assertEqual(checked["run_id_hex"], artifact.P340_RUN_ID_HEX)
        self.assertEqual(
            checked["sections"],
            predecessor.validate_image(self.image, expected_run_id=predecessor.P339_RUN_ID)["sections"],
        )
        self.assertNotIn(artifact.P339_PREDECESSOR_RUN_ID_HEX.encode("ascii"), transformed)

    def test_predecessor_image_and_ap_are_not_accepted_as_fresh(self) -> None:
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.transform_image(b"not-an-image")
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.validate_rollback_ap(
                ROOT
                / "workspace/private/outputs/s22plus_fyg8_p339/"
                "stock-candidate-build-v1-20260905-04/candidate-a/odin4/AP.tar.md5",
                artifact.P339_AP_IDENTITY,
            )


if __name__ == "__main__":
    unittest.main()
