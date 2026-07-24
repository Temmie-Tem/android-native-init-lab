import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"


def load_module(name):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"{name}_tested", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P234CandidateBuilderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if str(SCRIPTS) not in sys.path:
            sys.path.insert(0, str(SCRIPTS))
        cls.module = load_module("build_s22plus_fyg8_p234_candidate")

    def fixture(self, root):
        exact_contract = {"run_id": "ab" * 16}
        image = {"size": 4096, "sha256": "1" * 64}
        result = {
            "schema": self.module.repro.SCHEMA,
            "target": self.module.TARGET,
            "verdict": self.module.repro.VERDICT,
            "candidate_contract": exact_contract,
            "linked_audit": {"verified": True},
            "byte_identical_artifacts": {
                name: True
                for name in self.module.repro.ARTIFACT_LIMITS
                if name != "build-result.json"
            },
            "build_a": {"artifacts": {"Image": image}},
        }
        path = root / "repro.json"
        path.write_text(json.dumps(result), encoding="ascii")
        return path, exact_contract, image

    def test_repro_result_binds_exact_image_and_contract(self):
        with tempfile.TemporaryDirectory() as name:
            path, exact_contract, image = self.fixture(Path(name))
            result = self.module.verify_repro_result(path, image, exact_contract)
            self.assertTrue(result["two_clean_builds_byte_identical"])
            self.assertTrue(result["linked_audit_verified"])

    def test_repro_result_rejects_changed_image(self):
        with tempfile.TemporaryDirectory() as name:
            path, exact_contract, image = self.fixture(Path(name))
            changed = copy.deepcopy(image)
            changed["sha256"] = "2" * 64
            with self.assertRaisesRegex(self.module.BuildError, "Image differs"):
                self.module.verify_repro_result(path, changed, exact_contract)

    def test_repro_result_rejects_failed_linked_audit(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            path, exact_contract, image = self.fixture(root)
            result = json.loads(path.read_text(encoding="ascii"))
            result["linked_audit"]["verified"] = False
            path.write_text(json.dumps(result), encoding="ascii")
            with self.assertRaisesRegex(self.module.BuildError, "not accepted"):
                self.module.verify_repro_result(path, image, exact_contract)

    def test_p254_requires_exact_linked_adapter_and_store_dominance(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            path, exact_contract, image = self.fixture(root)
            exact_contract["source_contract_id"] = (
                "s22plus-fyg8-p254-e2-proof-bound-v1"
            )
            result = json.loads(path.read_text(encoding="ascii"))
            result["candidate_contract"] = exact_contract
            result["linked_audit"].update(
                {
                    "audit_adapter": (
                        "s22plus-fyg8-p253-linked-audit-v2"
                    ),
                    "source_contract_validator": {
                        "writer_guard": {
                            "guard_dominates_retained_stores": True
                        }
                    },
                }
            )
            path.write_text(json.dumps(result), encoding="ascii")
            self.module.verify_repro_result(path, image, exact_contract)

            for mutation in (
                lambda value: value["linked_audit"].pop("audit_adapter"),
                lambda value: value["linked_audit"][
                    "source_contract_validator"
                ]["writer_guard"].update(
                    {"guard_dominates_retained_stores": False}
                ),
            ):
                with self.subTest(mutation=mutation):
                    changed = copy.deepcopy(result)
                    mutation(changed)
                    path.write_text(json.dumps(changed), encoding="ascii")
                    with self.assertRaisesRegex(
                        self.module.BuildError, "P2.54 linked"
                    ):
                        self.module.verify_repro_result(
                            path, image, exact_contract
                        )

    def test_repro_result_rejects_partial_or_extra_artifact_map(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            path, exact_contract, image = self.fixture(root)
            result = json.loads(path.read_text(encoding="ascii"))
            result["byte_identical_artifacts"].pop("abi.xml")
            path.write_text(json.dumps(result), encoding="ascii")
            with self.assertRaisesRegex(self.module.BuildError, "not accepted"):
                self.module.verify_repro_result(path, image, exact_contract)
            result["byte_identical_artifacts"]["abi.xml"] = True
            result["byte_identical_artifacts"]["extra"] = True
            path.write_text(json.dumps(result), encoding="ascii")
            with self.assertRaisesRegex(self.module.BuildError, "not accepted"):
                self.module.verify_repro_result(path, image, exact_contract)


if __name__ == "__main__":
    unittest.main()
