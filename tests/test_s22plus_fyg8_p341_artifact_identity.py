from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p341_artifact_identity as artifact  # noqa: E402


class P341ArtifactIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.image = artifact.P340_IMAGE.read_bytes()

    def test_fresh_identity_is_boot_only_and_rejects_consumed_p340(self) -> None:
        value = artifact.validate_p341_identity()
        self.assertEqual(value["run_id_hex"], artifact.P341_RUN_ID_HEX)
        self.assertEqual(
            value["predecessor_run_id_rejected"], artifact.P340_PREDECESSOR_RUN_ID_HEX
        )
        self.assertEqual(value["predecessor_ap_identity_rejected"], artifact.P340_AP_IDENTITY)
        self.assertTrue(value["boot_only"])
        self.assertTrue(value["ab_must_match"])
        self.assertTrue(value["host_first_open"])
        self.assertFalse(value["auth_key_path_published"])
        self.assertIn(artifact.P340_AP_IDENTITY, artifact.STALE_AP_IDENTITIES)

    def test_identity_transform_keeps_image_and_gzip_geometry(self) -> None:
        transformed, receipt = artifact.transform_image(self.image)
        self.assertEqual(len(transformed), len(self.image))
        self.assertEqual(artifact.identity(transformed), artifact.P341_IMAGE_IDENTITY)
        self.assertEqual(receipt["method"], "identity_only_post_link_v1")
        self.assertEqual(receipt["source"]["run_id_hex"], artifact.P340_PREDECESSOR_RUN_ID_HEX)
        self.assertEqual(receipt["target"]["run_id_hex"], artifact.P341_RUN_ID_HEX)
        self.assertEqual(receipt["ikconfig"]["compressed_size"], 40_695)
        self.assertEqual(receipt["ikconfig"]["old_compressed"]["size"], 40_695)
        self.assertEqual(receipt["ikconfig"]["new_compressed"]["size"], 40_695)
        self.assertEqual(receipt["raw_rodata"]["size"], 32)
        self.assertTrue(all(receipt["preserved"].values()))
        self.assertEqual(artifact.validate_image(transformed)["run_id_hex"], artifact.P341_RUN_ID_HEX)
        self.assertNotIn(artifact.P340_PREDECESSOR_RUN_ID_HEX.encode("ascii"), transformed)

    def test_consumed_p340_ap_is_not_rollback(self) -> None:
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.validate_rollback_ap(
                ROOT
                / "workspace/private/outputs/s22plus_fyg8_p340/"
                "stock-candidate-build-v1-20260905-01/candidate-a/odin4/AP.tar.md5",
                artifact.P340_AP_IDENTITY,
            )


if __name__ == "__main__":
    unittest.main()
