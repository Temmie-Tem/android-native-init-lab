import argparse
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))
try:
    INTENT = importlib.import_module("s22plus_fyg8_p234_candidate_intent")
    CONTRACT = importlib.import_module("s22plus_fyg8_p234_candidate_contract")
    USERSPACE = importlib.import_module("s22plus_fyg8_p234_userspace_build")
finally:
    sys.path.remove(str(SCRIPTS))


class S22PlusFyg8P234CandidateIdentityTest(unittest.TestCase):
    NONCE_A = "11" * 16
    NONCE_B = "22" * 16

    def _create(self, parent: Path, name: str, nonce: str):
        relative = Path(parent.relative_to(ROOT)) / name
        args = argparse.Namespace(
            source=INTENT.DEFAULT_SOURCE,
            base_patch=INTENT.DEFAULT_BASE_PATCH,
            out=relative,
            nonce_hex=nonce,
        )
        result = INTENT.create(args)
        output = ROOT / relative
        return result, output

    def _verify(self, output: Path):
        return CONTRACT.verify(
            ROOT,
            INTENT.resolve(ROOT, INTENT.DEFAULT_SOURCE),
            output / "candidate-intent.json",
            output / "candidate.patch",
        )

    def test_same_nonce_is_deterministic_and_contract_passes(self):
        private_tmp = ROOT / "workspace/private/tmp"
        private_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_tmp) as temporary:
            parent = Path(temporary)
            first, first_dir = self._create(parent, "first", self.NONCE_A)
            second, second_dir = self._create(parent, "second", self.NONCE_A)
            self.assertEqual(first["run_id"], second["run_id"])
            self.assertEqual(first["patch"], second["patch"])
            self.assertEqual(
                (first_dir / "candidate.patch").read_bytes(),
                (second_dir / "candidate.patch").read_bytes(),
            )
            verified = self._verify(first_dir)
            self.assertEqual(verified["verdict"], CONTRACT.VERDICT)
            self.assertEqual(
                verified["reachable_record_contract"]["reachable_slot_variants"],
                32769,
            )

    def test_different_nonce_changes_run_id_and_patch(self):
        private_tmp = ROOT / "workspace/private/tmp"
        private_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_tmp) as temporary:
            parent = Path(temporary)
            first, first_dir = self._create(parent, "first", self.NONCE_A)
            second, second_dir = self._create(parent, "second", self.NONCE_B)
            self.assertNotEqual(first["run_id"], second["run_id"])
            self.assertNotEqual(first["patch"]["sha256"], second["patch"]["sha256"])
            self.assertNotEqual(
                (first_dir / "candidate.patch").read_bytes(),
                (second_dir / "candidate.patch").read_bytes(),
            )

    def test_tampered_intent_and_patch_fail_closed(self):
        private_tmp = ROOT / "workspace/private/tmp"
        private_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_tmp) as temporary:
            parent = Path(temporary)
            result, output = self._create(parent, "source", self.NONCE_A)
            intent_value = json.loads(
                (output / "candidate-intent.json").read_text(encoding="ascii")
            )
            intent_value["run_id"] = "33" * 16
            bad_intent = parent / "bad-intent.json"
            bad_intent.write_text(
                json.dumps(intent_value, sort_keys=True), encoding="ascii"
            )
            with self.assertRaisesRegex(CONTRACT.ContractError, "run ID"):
                CONTRACT.verify(
                    ROOT,
                    INTENT.resolve(ROOT, INTENT.DEFAULT_SOURCE),
                    bad_intent,
                    output / "candidate.patch",
                )

            patch = (output / "candidate.patch").read_bytes()
            self.assertIn(result["run_id"].encode("ascii"), patch)
            bad_patch = parent / "bad.patch"
            bad_patch.write_bytes(
                patch.replace(
                    result["run_id"].encode("ascii"), b"44" * 16, 1
                )
            )
            with self.assertRaisesRegex(CONTRACT.ContractError, "exact regeneration"):
                CONTRACT.verify(
                    ROOT,
                    INTENT.resolve(ROOT, INTENT.DEFAULT_SOURCE),
                    output / "candidate-intent.json",
                    bad_patch,
                )

    def test_candidate_scope_is_exact_and_host_only(self):
        private_tmp = ROOT / "workspace/private/tmp"
        private_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_tmp) as temporary:
            result, output = self._create(Path(temporary), "candidate", self.NONCE_A)
            self.assertEqual(result["patch"]["targets"], sorted(INTENT.BASE_FILES))
            self.assertEqual(set(result["patch"]["base_files"]), set(INTENT.BASE_FILES))
            self.assertEqual(
                set(result["patch"]["patched_files"]), set(INTENT.BASE_FILES)
            )
            self.assertTrue(result["safety"]["host_only"])
            self.assertTrue(
                all(
                    value is False
                    for name, value in result["safety"].items()
                    if name != "host_only"
                )
            )
            self.assertTrue(self._verify(output)["verified"])

    def test_userspace_recipe_is_owned_by_p234(self):
        source = Path(USERSPACE.__file__).read_text(encoding="ascii")
        self.assertNotIn("s22plus_fyg8_r4w1e_e1_host_contract", source)
        self.assertEqual(USERSPACE.CHILD_EXIT, 23)
        self.assertEqual(
            USERSPACE.CHILD_TOKEN,
            b"S22PLUS_R4W1E_E1_CHILD_OK:4c3e58c0785b\n",
        )
        self.assertEqual(
            set(USERSPACE.FORBIDDEN_MODULE_NAMES),
            {
                "smem.ko",
                "minidump.ko",
                "qcom-scm.ko",
                "qcom_wdt_core.ko",
                "gh_virt_wdt.ko",
            },
        )


if __name__ == "__main__":
    unittest.main()
