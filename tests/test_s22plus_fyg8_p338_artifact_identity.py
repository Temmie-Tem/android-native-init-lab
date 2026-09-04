from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p338_artifact_identity as artifact  # noqa: E402


class P338ArtifactIdentityTests(unittest.TestCase):
    def test_fresh_identity_is_boot_only_and_rejects_p337(self) -> None:
        value = artifact.validate_p338_identity()
        self.assertEqual(value["run_id_hex"], artifact.P338_RUN_ID_HEX)
        self.assertEqual(
            value["predecessor_run_id_rejected"],
            artifact.P337_PREDECESSOR_RUN_ID_HEX,
        )
        self.assertEqual(
            value["predecessor_ap_identity_rejected"],
            artifact.P337_AP_IDENTITY,
        )
        self.assertTrue(value["boot_only"])
        self.assertTrue(value["ab_must_match"])
        self.assertFalse(value["auth_key_path_published"])
        self.assertIn(artifact.P337_AP_IDENTITY, artifact.STALE_AP_IDENTITIES)

    def test_source_pin_and_fresh_run_are_exact(self) -> None:
        self.assertEqual(
            artifact.SOURCE.name,
            "s22plus_fyg8_p337_artifact_identity.py",
        )
        self.assertEqual(
            artifact.identity(artifact.SOURCE.read_bytes()),
            artifact.P337_SOURCE_IDENTITY,
        )
        self.assertEqual(artifact.P338_RUN_ID, bytes.fromhex(artifact.P338_RUN_ID_HEX))

    def test_consumed_p337_candidate_is_not_a_rollback(self) -> None:
        path = ROOT / (
            "workspace/private/outputs/s22plus_fyg8_p337/"
            "stock-candidate-build-v1-20260904-06/candidate-a/odin4/AP.tar.md5"
        )
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.validate_rollback_ap(path, artifact.P337_AP_IDENTITY)

    def test_wrong_run_binding_rejects_before_delegation(self) -> None:
        with self.assertRaises(artifact.ArtifactIdentityError):
            artifact.validate_image(b"not-an-image", expected_run_id=artifact.P337_RUN_ID)


if __name__ == "__main__":
    unittest.main()
