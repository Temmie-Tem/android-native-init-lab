from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p321_artifact_identity.py"
)
SPEC = importlib.util.spec_from_file_location("p321_artifact_identity", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("P3.21 artifact identity source cannot be loaded")
artifact = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(artifact)


P321_OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p321/"
    "stock-candidate-build-v1-20260831-02"
)
P320_AP = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p320/"
    "stock-candidate-build-v1-20260830-04/candidate-a/odin4/AP.tar.md5"
)


class P321ArtifactIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = json.loads((P321_OUTPUT / "result.json").read_text(encoding="ascii"))
        cls.image = (P321_OUTPUT / "inputs/fixed-Image").read_bytes()
        cls.init = (P321_OUTPUT / "userspace-a/init").read_bytes()
        cls.child = (P321_OUTPUT / "userspace-a/s22-e1-child").read_bytes()

    def test_real_ap_unpack_joins_image_ikconfig_and_init_raw_id(self) -> None:
        candidate = self.result["phase2"]["candidate"]["a"]
        joined = artifact.inspect_ap(
            P321_OUTPUT / "candidate-a/odin4/AP.tar.md5",
            expected_run_id=artifact.P321_RUN_ID,
            expected_image=self.image,
            expected_init=self.init,
            expected_child=self.child,
            expected_ap=candidate["ap_tar_md5"],
            label="P321 test candidate A AP",
        )
        self.assertTrue(joined["boot_only"])
        self.assertTrue(joined["joined"])
        self.assertEqual(joined["run_id_hex"], artifact.P321_RUN_ID_HEX)
        self.assertEqual(joined["image"]["ikconfig"]["run_id_hex"], artifact.P321_RUN_ID_HEX)
        self.assertEqual(joined["init"]["counts"][artifact.P321_RUN_ID_HEX], 1)
        self.assertEqual(joined["init"]["counts"][artifact.P319_RUN_ID_HEX], 0)
        self.assertEqual(joined["init"]["counts"][artifact.P320_RUN_ID_HEX], 0)

    def test_p320_mixed_image_init_is_rejected(self) -> None:
        # The retained P3.20 AP is the concrete mixed artifact: its Image is
        # P3.19 while its ramdisk init carries P3.20.  A P3.20 expectation must
        # fail closed at the Image/config side of the join.
        with self.assertRaisesRegex(artifact.ArtifactIdentityError, "Image IKCONFIG run ID differs"):
            artifact.inspect_ap(
                P320_AP,
                expected_run_id=artifact.P320_RUN_ID,
                label="P320 mixed AP fixture",
            )

    def test_image_transform_is_same_length_and_a_b_reproducible(self) -> None:
        old = artifact.stable_bytes(
            artifact.P319_IMAGE,
            "P319 source Image",
            64 * 1024 * 1024,
            artifact.P319_IMAGE_IDENTITY,
        )
        first, metadata = artifact.transform_image(old)
        second, _ = artifact.transform_image(old)
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(old))
        self.assertEqual(metadata["raw_rodata"]["old_count_outside_ikconfig"], 1)
        self.assertEqual(metadata["ikconfig"]["compressed_size"], artifact.IKCONFIG_COMPRESSED_SIZE)
        self.assertEqual(metadata["ikconfig"]["os_byte"], 3)
        self.assertTrue(all(metadata["preserved"].values()))
        self.assertEqual(artifact.validate_image(first)["run_id_hex"], artifact.P321_RUN_ID_HEX)

    def test_rollback_is_exact_boot_only_and_untouched(self) -> None:
        receipt = artifact.validate_rollback_ap(
            ROOT / "workspace/private/outputs/s22plus_magisk_root_boot_only/AP.tar.md5",
            {"size": 23_367_721, "sha256": "d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56"},
        )
        self.assertTrue(receipt["untouched"])
        self.assertEqual(receipt["ap_structure"]["member"]["name"], "boot.img.lz4")


if __name__ == "__main__":
    unittest.main()
