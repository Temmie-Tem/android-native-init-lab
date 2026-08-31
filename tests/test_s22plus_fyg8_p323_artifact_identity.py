from __future__ import annotations

import importlib.util
from pathlib import Path
import stat
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p323_artifact_identity.py"
)
P322_AP = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p322/"
    "stock-candidate-build-v1-20260831-02/candidate-a/odin4/AP.tar.md5"
)
ROLLBACK_AP = ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5"
ROLLBACK_IDENTITY = {
    "size": 23_367_721,
    "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56",
}


def load_module():
    spec = importlib.util.spec_from_file_location("p323_artifact_identity", SOURCE)
    if spec is None or spec.loader is None:
        raise AssertionError("P323 artifact helper cannot load")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class P323ArtifactIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact = load_module()
        cls.image = cls.artifact.stable_bytes(
            cls.artifact.P319_IMAGE,
            "P319 source Image",
            64 * 1024 * 1024,
            cls.artifact.P319_IMAGE_IDENTITY,
        )

    def test_fresh_image_transform_is_deterministic_and_exactly_bound(self) -> None:
        first, first_meta = self.artifact.transform_image(self.image)
        second, second_meta = self.artifact.transform_image(self.image)
        self.assertEqual(first, second)
        self.assertEqual(first_meta, second_meta)
        self.assertEqual(len(first), len(self.image))
        self.assertEqual(first_meta["target"]["run_id_hex"], self.artifact.P323_RUN_ID_HEX)
        self.assertEqual(
            self.artifact.validate_image(first)["run_id_hex"],
            self.artifact.P323_RUN_ID_HEX,
        )
        for old in (
            self.artifact.P319_RUN_ID_HEX,
            self.artifact.P320_RUN_ID_HEX,
            self.artifact.P321_RUN_ID_HEX,
            self.artifact.P322_RUN_ID_HEX,
        ):
            self.assertNotIn(old.encode("ascii"), first)

    def test_old_image_and_predecessor_ap_are_rejected(self) -> None:
        with self.assertRaises(self.artifact.ArtifactIdentityError):
            self.artifact.validate_image(self.image)
        with self.assertRaises(self.artifact.ArtifactIdentityError):
            self.artifact.inspect_ap(P322_AP, label="P322 predecessor AP")

    def test_rollback_is_boot_only_and_private_identity_is_stable(self) -> None:
        receipt = self.artifact.validate_rollback_ap(ROLLBACK_AP, ROLLBACK_IDENTITY)
        self.assertTrue(receipt["untouched"])
        self.assertEqual(receipt["ap_structure"]["member"]["name"], "boot.img.lz4")
        rollback_stat = ROLLBACK_AP.stat()
        self.assertTrue(stat.S_ISREG(rollback_stat.st_mode))
        self.assertEqual(rollback_stat.st_nlink, 1)
        self.assertEqual(stat.S_IMODE(rollback_stat.st_mode) & 0o077, 0)


if __name__ == "__main__":
    unittest.main()
