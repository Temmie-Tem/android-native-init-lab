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

    def _create(
        self, parent: Path, name: str, nonce: str, profile: str = "E1A"
    ):
        relative = Path(parent.relative_to(ROOT)) / name
        args = argparse.Namespace(
            source=INTENT.DEFAULT_SOURCE,
            base_patch=INTENT.DEFAULT_BASE_PATCH,
            out=relative,
            nonce_hex=nonce,
            profile=profile,
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

    def test_e1b_uses_distinct_profile_bound_identity(self):
        private_tmp = ROOT / "workspace/private/tmp"
        private_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_tmp) as temporary:
            parent = Path(temporary)
            e1a, _e1a_dir = self._create(parent, "e1a", self.NONCE_A)
            e1b, e1b_dir = self._create(
                parent, "e1b", self.NONCE_A, profile="E1B"
            )
            verified = self._verify(e1b_dir)
            self.assertNotEqual(e1a["run_id"], e1b["run_id"])
            self.assertEqual(verified["profile"], "E1B")
            self.assertEqual(verified["profile_number"], 2)
            self.assertIn(
                "CONFIG_S22PLUS_FYG8_E1_PROFILE=2", verified["config_lines"]
            )
            self.assertEqual(
                verified["reachable_record_contract"]["profiles"], ["E1B"]
            )
            self.assertEqual(
                verified["reachable_record_contract"]["reachable_slot_variants"],
                57345,
            )

    def test_e2_uses_profile3_sources_and_reachable_contract(self):
        private_tmp = ROOT / "workspace/private/tmp"
        private_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_tmp) as temporary:
            parent = Path(temporary)
            e1b, _e1b_dir = self._create(
                parent, "e1b", self.NONCE_A, profile="E1B"
            )
            e2, e2_dir = self._create(
                parent, "e2", self.NONCE_A, profile="E2"
            )
            verified = self._verify(e2_dir)
            self.assertNotEqual(e1b["run_id"], e2["run_id"])
            self.assertEqual(verified["profile"], "E2")
            self.assertEqual(verified["profile_number"], 3)
            self.assertIn(
                "CONFIG_S22PLUS_FYG8_E1_PROFILE=3", verified["config_lines"]
            )
            self.assertEqual(
                verified["reachable_record_contract"]["profiles"], ["E2"]
            )
            self.assertEqual(
                verified["reachable_record_contract"]["reachable_slot_variants"],
                307201,
            )
            sources = e2["identity_preimage"]["sources"]
            self.assertIn("plan_header", sources)
            self.assertIn("stock_closure", sources)
            self.assertNotEqual(
                sources["base_patch"],
                e1b["identity_preimage"]["sources"]["base_patch"],
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

    def test_e1b_userspace_two_builds_are_profile_bound(self):
        private_tmp = ROOT / "workspace/private/tmp"
        private_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_tmp) as temporary:
            parent = Path(temporary)
            _intent, intent_dir = self._create(
                parent, "intent", self.NONCE_B, profile="E1B"
            )
            output = parent / "userspace"
            result = USERSPACE.build_userspace(
                argparse.Namespace(
                    source=INTENT.DEFAULT_SOURCE,
                    intent=intent_dir / "candidate-intent.json",
                    patch=intent_dir / "candidate.patch",
                    out=output,
                )
            )
            self.assertEqual(result["profile"], "E1B")
            self.assertEqual(result["verdict"], USERSPACE.E1B_VERDICT)
            self.assertTrue(result["two_build_byte_identical"])
            self.assertEqual(
                result["outputs"]["init"]["module_string_counts"],
                {name: 1 for name in USERSPACE.FORBIDDEN_MODULE_NAMES},
            )

    def test_e2_userspace_two_builds_bind_all_plan_modules(self):
        private_tmp = ROOT / "workspace/private/tmp"
        private_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=private_tmp) as temporary:
            parent = Path(temporary)
            _intent, intent_dir = self._create(
                parent, "intent", self.NONCE_B, profile="E2"
            )
            output = parent / "userspace"
            result = USERSPACE.build_userspace(
                argparse.Namespace(
                    source=INTENT.DEFAULT_SOURCE,
                    intent=intent_dir / "candidate-intent.json",
                    patch=intent_dir / "candidate.patch",
                    out=output,
                )
            )
            module_files = USERSPACE._e2_module_files(ROOT)
            self.assertEqual(result["profile"], "E2")
            self.assertEqual(result["verdict"], USERSPACE.E2_VERDICT)
            self.assertTrue(result["two_build_byte_identical"])
            self.assertEqual(len(module_files), 59)
            self.assertEqual(
                result["outputs"]["init"]["module_string_counts"],
                {name: 1 for name in module_files},
            )
            self.assertEqual(
                result["source_contract"]["module_files"], list(module_files)
            )


if __name__ == "__main__":
    unittest.main()
