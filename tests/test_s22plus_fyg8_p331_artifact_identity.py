from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p331_artifact_identity as artifact  # noqa: E402


class P331ArtifactIdentityTests(unittest.TestCase):
    def test_fresh_identity_rejects_consumed_p330(self) -> None:
        self.assertEqual(artifact.P331_RUN_ID_HEX, "c331f1e0a90b5e6d7c8a9b0c1d2e3f9b")
        self.assertEqual(
            artifact.P330_PREDECESSOR_RUN_ID_HEX,
            "c330f1e0a90b5e6d7c8a9b0c1d2e3f0b",
        )
        self.assertNotEqual(artifact.P331_RUN_ID, artifact.P330_PREDECESSOR_RUN_ID)
        self.assertEqual(
            artifact.validate_p331_identity()["predecessor_run_id_rejected"],
            artifact.P330_PREDECESSOR_RUN_ID_HEX,
        )

    def test_private_key_projection_is_path_free(self) -> None:
        key = artifact.read_auth_key()
        metadata = artifact.validate_auth_key(key)
        self.assertEqual(metadata["size"], artifact.AUTH_KEY_SIZE)
        self.assertEqual(artifact.auth_key_identity(), metadata)
        self.assertNotIn("path", metadata)

    def test_consumed_p330_image_is_not_accepted(self) -> None:
        image = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p330/"
            "stock-candidate-build-v1-20260903-07/inputs/fixed-Image"
        ).read_bytes()
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.validate_image(image)


if __name__ == "__main__":
    unittest.main()
