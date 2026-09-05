from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import s22plus_fyg8_p345_artifact_identity as artifact

class P345ArtifactTests(unittest.TestCase):
    def test_actual_image_transform_and_predecessor_rejection(self):
        original = artifact.stable_bytes(artifact.P344_IMAGE, "P344 Image")
        transformed, receipt = artifact.transform_image(original)
        self.assertEqual(artifact.identity(transformed), artifact.P345_IMAGE_IDENTITY)
        self.assertEqual(len(original), len(transformed))
        self.assertTrue(receipt["preserved"]["outside_declared_spans"])
        artifact.validate_image(transformed)
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.validate_image(original)
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.transform_image(transformed)

    def test_init_current_only(self):
        current = artifact.P345_RUN_ID_HEX.encode()
        artifact._validate_init(b"fixture:" + current)
        for old in artifact.predecessor._stale_counts(b""):
            with self.assertRaises(artifact.ArtifactIdentityError):
                artifact._validate_init(current + old.encode())

    def test_no_runtime_identity_only_or_lease_claim(self):
        value = artifact.validate_p345_identity()
        self.assertFalse(value["runtime_behavior_unchanged"])
        self.assertFalse(value["runtime_delta_identity_only"])
        self.assertIsNone(value["ap_identity"])
        self.assertEqual(value["initial_session_count"], 5)
        self.assertFalse(value["later_action_lease_active"])
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.validate_rollback_ap(Path("unused"), artifact.P344_AP_IDENTITY)

if __name__ == "__main__":
    unittest.main()
