import contextlib
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"


def load(name, file_name):
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / file_name)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class R4W1E0CandidateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load(
            "build_s22plus_fyg8_r4w1e0_candidate_tested",
            "build_s22plus_fyg8_r4w1e0_candidate.py",
        )
        cls.checker = load(
            "s22plus_fyg8_r4w1e0_candidate_static_checker_tested",
            "s22plus_fyg8_r4w1e0_candidate_static_checker.py",
        )
        cls.image_path = ROOT / cls.builder.DEFAULT_IMAGE
        cls.result_path = ROOT / cls.builder.DEFAULT_KERNEL_RESULT
        cls.candidate = ROOT / cls.builder.DEFAULT_OUT

    def test_immutable_build_artifacts_match_private_inputs(self):
        image = self.image_path.read_bytes()
        result = self.result_path.read_bytes()
        self.assertEqual(len(image), self.builder.artifact.IMAGE_SIZE)
        self.assertEqual(
            hashlib.sha256(image).hexdigest(), self.builder.artifact.IMAGE_SHA256
        )
        self.assertEqual(len(result), self.builder.artifact.KERNEL_BUILD_RESULT_SIZE)
        self.assertEqual(
            hashlib.sha256(result).hexdigest(),
            self.builder.artifact.KERNEL_BUILD_RESULT_SHA256,
        )

    def test_image_and_kernel_result_contracts_pass(self):
        image = self.image_path.read_bytes()
        result = self.result_path.read_bytes()
        classified = self.builder.classify_image(image)
        self.assertEqual(classified["entry_proof_count"], 1)
        self.assertEqual(classified["userspace_proof_count"], 1)
        self.assertEqual(classified["shared_family_count"], 2)
        checked = self.builder.verify_kernel_build(result, image)
        self.assertTrue(checked["verified"])
        self.assertEqual(checked["patch_sha256"], self.builder.proof.PATCH_SHA256)

    def test_image_or_kernel_result_mutation_fails_closed(self):
        image = self.image_path.read_bytes()
        result = self.result_path.read_bytes()
        with self.assertRaises(self.builder.engine.BuildError):
            self.builder.verify_kernel_build(result, image[:-1] + bytes([image[-1] ^ 1]))
        with self.assertRaises(self.builder.engine.BuildError):
            self.builder.verify_kernel_build(result + b"\n", image)

    def test_fixed_manifest_and_binding_are_exact(self):
        manifest = json.loads((self.candidate / "run-manifest.json").read_text())
        encoded = self.builder.engine.canonical_json(manifest)
        binding = self.builder.candidate_run_binding(
            encoded, self.builder.proof.PROBE_ID
        )
        self.assertEqual(binding["run_id"], self.builder.proof.PROBE_ID.hex())
        self.assertEqual(
            binding["derivation"], "fixed-probe-id-from-r4w1e0-contract"
        )
        self.assertTrue(binding["clean_baseline_required"])
        self.assertEqual(manifest["observation_contract"]["baseline_family_count"], 0)
        self.assertEqual(manifest["observation_contract"]["post_family_count"], 1)

    def test_caller_nonce_and_wrong_run_binding_are_rejected(self):
        with self.assertRaises(self.builder.engine.BuildError):
            self.builder.fixed_probe("00" * 16)
        with self.assertRaises(self.builder.engine.BuildError):
            self.builder.candidate_run_binding(b"manifest", b"X" * 16)
        with self.assertRaises(self.checker.engine.CheckError):
            self.checker.verify_candidate_run_binding({}, b"manifest", b"X" * 16)

    def test_builder_engine_binding_is_scoped(self):
        names = (
            "SCHEMA",
            "e1",
            "checkpoint",
            "verify_kernel_build",
            "classify_image",
            "derive_run_manifest",
            "candidate_run_binding",
            "parse_args",
        )
        before = {name: getattr(self.builder.engine, name) for name in names}
        with self.builder.bind_engine():
            self.assertEqual(self.builder.engine.SCHEMA, self.builder.SCHEMA)
            self.assertIs(self.builder.engine.e1, self.builder.runtime)
            self.assertIs(
                self.builder.engine.candidate_run_binding,
                self.builder.candidate_run_binding,
            )
        for name, value in before.items():
            self.assertIs(getattr(self.builder.engine, name), value)

    def test_checker_engine_binding_is_scoped(self):
        names = (
            "SCHEMA",
            "e1",
            "checkpoint",
            "verify_kernel_result",
            "verify_run_manifest",
            "classify_image",
            "verify_candidate_run_binding",
            "run_binding_evidence",
            "parse_args",
        )
        before = {name: getattr(self.checker.engine, name) for name in names}
        with self.checker.bind_engine():
            self.assertEqual(self.checker.engine.SCHEMA, self.checker.SCHEMA)
            self.assertIs(self.checker.engine.e1, self.checker.contract.runtime)
            self.assertIs(
                self.checker.engine.verify_candidate_run_binding,
                self.checker.verify_candidate_run_binding,
            )
        for name, value in before.items():
            self.assertIs(getattr(self.checker.engine, name), value)

    def test_base_run_binding_extension_defaults_are_unchanged(self):
        encoded = b"canonical"
        run_id = b"R" * 16
        binding = self.builder.engine.candidate_run_binding(encoded, run_id)
        self.assertEqual(binding["run_id"], run_id.hex())
        self.assertEqual(binding["derivation"], "sha256(canonical-run-manifest)[:16]")
        self.checker.engine.verify_candidate_run_binding(binding, encoded, run_id)
        evidence = self.checker.engine.run_binding_evidence(encoded, run_id)
        self.assertTrue(evidence["fresh_non_model_id"])

    def test_runtime_recompilation_matches_fixed_receipt(self):
        root = self.builder.proof.shared.repo_root()
        receipt = self.builder.proof.check_runtime_artifact(
            root / self.builder.proof.DEFAULT_INIT,
            root / self.builder.proof.DEFAULT_RUNTIME_RECEIPT,
        )
        self.assertEqual(receipt["probe_id"], self.builder.proof.PROBE_ID.hex())
        with tempfile.TemporaryDirectory() as temporary:
            source, _rows = self.builder.engine.exact_source_data(root)
            tools = self.builder.BASE_E1.require_tools()
            compiled = self.builder.runtime.compile_one(
                Path(temporary),
                source["runtime"],
                source["child"],
                source["client"],
                source["header"],
                self.builder.proof.PROBE_ID,
                tools,
            )
        self.assertEqual(compiled["init"]["sha256"], receipt["sha256"])

    def test_proof_contract_errors_translate_to_inherited_fail_closed_type(self):
        with mock.patch.object(
            self.builder.proof,
            "check_runtime_artifact",
            side_effect=self.builder.proof.CheckError("tampered runtime receipt"),
        ):
            with self.assertRaisesRegex(
                self.builder.BASE_E1.CheckError, "tampered runtime receipt"
            ):
                self.builder._proof_call(
                    self.builder.proof.check_runtime_artifact,
                    Path("unused-init"),
                    Path("unused-receipt"),
                )

    def test_proof_contract_errors_are_structured_by_both_clis(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            cases = (
                (self.builder, ["--out", str(output / "candidate")]),
                (self.checker, ["--out", str(output / "check.json")]),
            )
            for module, arguments in cases:
                with self.subTest(module=module.SCHEMA):
                    stream = io.StringIO()
                    with mock.patch.object(
                        self.builder.proof,
                        "check_runtime_artifact",
                        side_effect=self.builder.proof.CheckError(
                            "tampered runtime receipt"
                        ),
                    ), contextlib.redirect_stdout(stream):
                        returncode = module.main(arguments)
                    result = json.loads(stream.getvalue())
                    self.assertEqual(returncode, 1)
                    self.assertEqual(result["schema"], module.SCHEMA)
                    self.assertEqual(result["verdict"], "FAIL_CLOSED")
                    self.assertEqual(result["error"], "tampered runtime receipt")

    def test_candidate_manifest_and_static_result_are_host_only(self):
        manifest = json.loads((self.candidate / "manifest.json").read_text())
        result = json.loads(
            (
                ROOT
                / "workspace/private/outputs/s22plus_fyg8_r4w1e0_candidate/"
                "static-check-result.json"
            ).read_text()
        )
        self.assertEqual(manifest["safety"]["ap_members"], ["boot.img.lz4"])
        self.assertFalse(manifest["safety"]["device_contact"])
        self.assertFalse(manifest["safety"]["live_authorized"])
        self.assertEqual(result["verdict"], self.checker.VERDICT)
        self.assertFalse(result["safety"]["device_contact"])
        self.assertFalse(result["safety"]["live_authorized"])

    def test_new_scripts_have_no_device_execution_path(self):
        for name in (
            "build_s22plus_fyg8_r4w1e0_candidate.py",
            "s22plus_fyg8_r4w1e0_candidate_static_checker.py",
        ):
            text = (SCRIPTS / name).read_text(encoding="ascii")
            self.assertNotIn("run_odin", text)
            self.assertNotIn('"adb"', text.lower())
            self.assertNotIn("fastboot", text.lower())


if __name__ == "__main__":
    unittest.main()
