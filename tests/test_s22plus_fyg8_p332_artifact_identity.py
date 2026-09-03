from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p332_artifact_identity as artifact  # noqa: E402


class P332ArtifactIdentityTests(unittest.TestCase):
    def test_fresh_identity_rejects_p330_and_p331(self) -> None:
        self.assertEqual(artifact.P332_RUN_ID_HEX, "c332f1e0a90b5e6d7c8a9b0c1d2e3f8b")
        self.assertEqual(
            artifact.P330_PREDECESSOR_RUN_ID_HEX,
            "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b",
        )
        self.assertEqual(
            artifact.P331_PREDECESSOR_RUN_ID_HEX,
            "c331f1e0a90b5e6d7c8a9b0c1d2e3f9b",
        )
        projection = artifact.validate_p332_identity()
        self.assertEqual(
            projection["predecessor_run_ids_rejected"],
            [artifact.P330_PREDECESSOR_RUN_ID_HEX, artifact.P331_PREDECESSOR_RUN_ID_HEX],
        )
        self.assertTrue(projection["boot_only"])
        self.assertTrue(projection["ab_must_match"])

    def test_private_key_projection_is_path_free(self) -> None:
        key = artifact.read_auth_key()
        metadata = artifact.validate_auth_key(key)
        self.assertEqual(metadata["size"], artifact.AUTH_KEY_SIZE)
        self.assertEqual(artifact.auth_key_identity(), metadata)
        self.assertNotIn("path", metadata)

    def test_consumed_p330_and_p331_aps_are_rejected_before_unpack(self) -> None:
        paths = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p330/"
            "stock-candidate-build-v1-20260903-07/candidate-a/odin4/AP.tar.md5",
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p331/"
            "stock-candidate-build-v1-20260903-03/candidate-a/odin4/AP.tar.md5",
        )
        for path in paths:
            with self.subTest(path=path):
                with self.assertRaises(artifact.ArtifactIdentityError):
                    artifact.inspect_ap(path)


if __name__ == "__main__":
    unittest.main()
