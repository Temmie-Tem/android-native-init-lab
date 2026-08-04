import argparse
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"

import sys

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import s22plus_fyg8_p301_candidate_contract as candidate_contract  # noqa: E402
import s22plus_fyg8_p301_overlay_contract as contract  # noqa: E402
import s22plus_fyg8_p301_overlay_intent as intent  # noqa: E402
import s22plus_fyg8_p301_userspace_build as userspace  # noqa: E402


class P301ContractTests(unittest.TestCase):
    def test_source_key_routes_are_complete_and_fixed_image_is_pinned(self):
        self.assertEqual(set(contract.SOURCE_PATHS), contract.SOURCE_KEYS)
        self.assertEqual(len(contract.SOURCE_KEYS), 9)
        self.assertTrue(all((ROOT / path).is_file() for path in contract.SOURCE_PATHS.values()))
        parent = contract.verify_parent(ROOT)
        self.assertEqual(parent["run_id"], "e324abaec60286102e4c9eb19fd80600")
        self.assertEqual(
            contract.EXPECTED_IMAGE["sha256"],
            "01457240881b432f725b0f2d795813c38ef7cca4365633f9b0fc7c3a62744a3f",
        )

    def test_overlay_intent_and_userspace_are_reproducible(self):
        with tempfile.TemporaryDirectory(prefix="p301-contract-") as temporary:
            directory = Path(temporary)
            intent_dir = directory / "intent"
            value = intent.create(ROOT, intent_dir)
            exact = candidate_contract.verify(
                ROOT,
                ROOT / contract.PARENT_SOURCE,
                intent_dir / "overlay-intent.json",
                ROOT / contract.PARENT_PATCH,
            )
            self.assertEqual(value["run_id"], exact["run_id"])
            self.assertEqual(exact["fixed_image"]["sha256"], contract.EXPECTED_IMAGE["sha256"])
            output = directory / "userspace"
            result = userspace.build_userspace(
                argparse.Namespace(
                    source=contract.PARENT_SOURCE,
                    intent=intent_dir / "overlay-intent.json",
                    patch=contract.PARENT_PATCH,
                    out=output,
                )
            )
            self.assertEqual(result["verdict"], userspace.VERDICT)
            self.assertTrue(result["two_build_byte_identical"])
            self.assertTrue(result["safety"]["fixed_p300_image"])
            self.assertEqual(
                result["candidate_contract"]["overlay_intent_sha256"],
                value["intent_sha256"],
            )


if __name__ == "__main__":
    unittest.main()
