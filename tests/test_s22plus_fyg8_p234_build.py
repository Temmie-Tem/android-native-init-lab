import argparse
import importlib
import io
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))
try:
    INTENT = importlib.import_module("s22plus_fyg8_p234_candidate_intent")
    CONTRACT = importlib.import_module("s22plus_fyg8_p234_candidate_contract")
    BUILD = importlib.import_module("s22plus_fyg8_p234_build")
finally:
    sys.path.remove(str(SCRIPTS))


class S22PlusFyg8P234BuildTest(unittest.TestCase):
    def setUp(self):
        self.private_tmp = ROOT / "workspace/private/tmp"
        self.private_tmp.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=self.private_tmp)
        parent = Path(self.temporary.name)
        relative = Path(parent.relative_to(ROOT)) / "intent"
        args = argparse.Namespace(
            source=INTENT.DEFAULT_SOURCE,
            base_patch=INTENT.DEFAULT_BASE_PATCH,
            out=relative,
            nonce_hex="55" * 16,
        )
        INTENT.create(args)
        self.intent_dir = ROOT / relative
        self.contract = CONTRACT.verify(
            ROOT,
            INTENT.resolve(ROOT, INTENT.DEFAULT_SOURCE),
            self.intent_dir / "candidate-intent.json",
            self.intent_dir / "candidate.patch",
        )
        BUILD._ContractAdapter.bind(
            self.contract, self.intent_dir / "candidate-intent.json"
        )

    def tearDown(self):
        self.temporary.cleanup()

    def _tree(self, *, duplicate_run_id: bool = False) -> Path:
        tree = Path(self.temporary.name) / "output"
        dist = tree / "out/msm-waipio-waipio-gki/gki_kernel/dist"
        common = tree / "out/msm-waipio-waipio-gki/gki_kernel/common"
        dist.mkdir(parents=True)
        common.mkdir(parents=True)
        run_id = self.contract["run_id"].encode("ascii")
        unsat_tag = self.contract["unsat_tag_hex"].encode("ascii")
        payload = (
            BUILD.LONG_FAMILY
            + BUILD.UNSAT_FAMILY
            + BUILD.REQUEST_MAGIC
            + run_id
            + unsat_tag
            + b"".join(BUILD.INERT_REJECTION_FAMILIES)
        )
        if duplicate_run_id:
            payload += run_id
        (dist / "Image").write_bytes(payload + bytes(4096 - len(payload)))
        (dist / "vmlinux").write_bytes(payload)
        (common / ".config").write_text(
            "\n".join(self.contract["config_lines"])
            + "\nCONFIG_CRYPTO_FIPS=y\n",
            encoding="ascii",
        )
        return tree

    def _gate(self, tree: Path):
        inherited = BUILD.engine.engine
        old_size = inherited.STOCK_IMAGE_SIZE
        old_capacity = inherited.FIXED_KERNEL_SLOT_CAPACITY
        try:
            inherited.STOCK_IMAGE_SIZE = 4096
            inherited.FIXED_KERNEL_SLOT_CAPACITY = 4096
            with BUILD.bind_engine():
                return BUILD.engine.witness_output_gate(tree)
        finally:
            inherited.STOCK_IMAGE_SIZE = old_size
            inherited.FIXED_KERNEL_SLOT_CAPACITY = old_capacity

    def test_output_gate_binds_exact_candidate_identity(self):
        result = self._gate(self._tree())
        self.assertTrue(result["verified"])
        self.assertEqual(result["candidate_run_id"], self.contract["run_id"])
        self.assertEqual(
            set(result["candidate_config_counts"]),
            set(self.contract["config_lines"]),
        )
        self.assertEqual(
            result["candidate_binary_counts"]["image"]["request_magic"], 1
        )
        self.assertEqual(
            result["inert_rejection_family_counts"],
            {
                "[[S22P1U|": {"image": 1, "vmlinux": 1},
                "S22UNS1|": {"image": 1, "vmlinux": 1},
            },
        )

    def test_active_and_inert_historical_families_are_separate(self):
        self.assertEqual(
            BUILD.INERT_REJECTION_FAMILIES,
            (b"[[S22P1U|", b"S22UNS1|"),
        )
        self.assertTrue(
            set(BUILD.INERT_REJECTION_FAMILIES).isdisjoint(
                BUILD.HISTORICAL_FAMILIES
            )
        )

    def test_output_gate_rejects_duplicate_identity(self):
        result = self._gate(self._tree(duplicate_run_id=True))
        self.assertFalse(result["verified"])
        self.assertEqual(
            result["candidate_binary_counts"]["image"]["run_id_hex"], 2
        )

    def test_output_gate_accepts_profile3_and_uses_e2_source_check_id(self):
        parent = Path(self.temporary.name)
        relative = Path(parent.relative_to(ROOT)) / "e2-intent"
        INTENT.create(
            argparse.Namespace(
                source=INTENT.DEFAULT_SOURCE,
                base_patch=INTENT.E2_SOURCE_PATHS["base_patch"],
                out=relative,
                nonce_hex="66" * 16,
                profile="E2",
            )
        )
        intent_dir = ROOT / relative
        self.contract = CONTRACT.verify(
            ROOT,
            INTENT.resolve(ROOT, INTENT.DEFAULT_SOURCE),
            intent_dir / "candidate-intent.json",
            intent_dir / "candidate.patch",
        )
        BUILD._ContractAdapter.bind(
            self.contract, intent_dir / "candidate-intent.json"
        )
        result = self._gate(self._tree())
        self.assertTrue(result["verified"])
        self.assertEqual(self.contract["profile"], "E2")
        self.assertEqual(
            INTENT.source_check_run_id("E2"), INTENT.p241.RUN_ID
        )
        self.assertEqual(
            result["candidate_binary_counts"]["image"]["source_check_run_id"],
            0,
        )

    def test_adapter_accepts_exact_p245_contract(self):
        parent = Path(self.temporary.name)
        relative = Path(parent.relative_to(ROOT)) / "p245-intent"
        INTENT.create(
            argparse.Namespace(
                source=INTENT.DEFAULT_SOURCE,
                base_patch=INTENT.DEFAULT_BASE_PATCH,
                out=relative,
                nonce_hex="77" * 16,
                profile="E2",
                source_contract_id=INTENT.p245.CONTRACT_ID,
            )
        )
        intent_dir = ROOT / relative
        contract = CONTRACT.verify(
            ROOT,
            INTENT.resolve(ROOT, INTENT.DEFAULT_SOURCE),
            intent_dir / "candidate-intent.json",
            intent_dir / "candidate.patch",
        )
        BUILD._ContractAdapter.bind(
            contract, intent_dir / "candidate-intent.json"
        )
        self.assertEqual(contract["schema"], INTENT.p245.CONTRACT_SCHEMA)
        self.assertEqual(contract["verdict"], INTENT.p245.CONTRACT_VERDICT)
        self.assertEqual(
            BUILD._ContractAdapter._bound_result["source_contract_id"],
            INTENT.p245.CONTRACT_ID,
        )
        self.assertEqual(
            BUILD._ContractAdapter.VERDICT, INTENT.p245.CONTRACT_VERDICT
        )

        with self.assertRaises(BUILD.BuildError):
            BUILD._ContractAdapter.bind(
                {**contract, "verdict": CONTRACT.VERDICT},
                intent_dir / "candidate-intent.json",
            )

    def test_p245_main_preflight_composes_parser_binding_and_verdict_gate(self):
        parent = Path(self.temporary.name)
        relative = Path(parent.relative_to(ROOT)) / "p245-main-intent"
        INTENT.create(
            argparse.Namespace(
                source=INTENT.DEFAULT_SOURCE,
                base_patch=INTENT.DEFAULT_BASE_PATCH,
                out=relative,
                nonce_hex="88" * 16,
                profile="E2",
                source_contract_id=INTENT.p245.CONTRACT_ID,
            )
        )
        intent_path = relative / "candidate-intent.json"
        patch_path = relative / "candidate.patch"

        result_dir = Path(parent.relative_to(ROOT)) / "real-main-preflight"
        argv = [
            str(BUILD.__file__),
            "--mode",
            "preflight",
            "--work-tree",
            str(INTENT.DEFAULT_SOURCE),
            "--intent",
            str(intent_path),
            "--patch",
            str(patch_path),
            "--result-dir",
            str(result_dir),
        ]
        verified = {"verified": True}
        clean = {"verified": True, "path": "bounded-fixture-output"}
        preflight = {
            "schema": "bounded-preflight-fixture",
            "build_allowed": True,
            "provenance": {},
        }
        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(
                    BUILD.engine.engine,
                    "reexec_in_private_repo_namespace",
                    return_value=None,
                )
            )
            stack.enter_context(
                mock.patch.object(
                    BUILD.engine.engine,
                    "inspect_private_namespace",
                    return_value={
                        "verified": True,
                        "recorded_repo": str(ROOT),
                    },
                )
            )
            stack.enter_context(
                mock.patch.object(
                    BUILD.engine.engine,
                    "create_exclusive_result_dir",
                    side_effect=lambda path: path.mkdir(parents=True),
                )
            )
            stack.enter_context(
                mock.patch.object(
                    BUILD.engine.engine,
                    "inspect_clean_output_precondition",
                    return_value=clean,
                )
            )
            for name in (
                "inspect_kmi_path_control",
                "inspect_kernel_debug_control",
                "inspect_vdso_debug_control",
            ):
                stack.enter_context(
                    mock.patch.object(
                        BUILD.engine.engine, name, return_value=verified
                    )
                )
            stack.enter_context(
                mock.patch.object(
                    BUILD.engine.engine,
                    "rebase_recorded_paths",
                    side_effect=lambda value, **_kwargs: value,
                )
            )
            for name in (
                "prepare_host_tool_overrides",
                "run_overlay_audit",
                "inspect_timestamp_control",
                "inspect_stock_baseline",
            ):
                stack.enter_context(
                    mock.patch.object(
                        BUILD.engine.base, name, return_value=verified
                    )
                )
            stack.enter_context(
                mock.patch.object(
                    BUILD.engine.base,
                    "preflight",
                    return_value=preflight,
                )
            )
            stack.enter_context(
                mock.patch.object(BUILD.engine.base, "write_json")
            )
            stack.enter_context(
                mock.patch.object(
                    BUILD.engine,
                    "inspect_source_symlink_control",
                    return_value=verified,
                )
            )
            stack.enter_context(
                mock.patch.object(
                    BUILD.engine,
                    "qualify_recorded_source_clang_link",
                    return_value=verified,
                )
            )
            stack.enter_context(mock.patch.object(sys, "argv", argv))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(BUILD.main(), 0)
        self.assertEqual(BUILD._ContractAdapter.VERDICT, INTENT.p245.CONTRACT_VERDICT)

    def test_engine_binding_is_scoped(self):
        original = {
            "schema": BUILD.engine.SCHEMA,
            "contract": BUILD.engine.contract,
            "gate": BUILD.engine.witness_output_gate,
            "kernel_debug": BUILD.engine.engine.KERNEL_DEBUG_PATH_REPRODUCIBLE,
        }
        with BUILD.bind_engine():
            self.assertEqual(BUILD.engine.SCHEMA, BUILD.SCHEMA)
            self.assertIs(BUILD.engine.contract, BUILD._ContractAdapter)
            self.assertIs(BUILD.engine.witness_output_gate, BUILD.output_gate)
            self.assertEqual(
                BUILD.engine.CONTRACT_RESULT_KEY, "p234_candidate_contract"
            )
            self.assertEqual(BUILD.engine.BUILD_PASS_KEY, "p234_build_pass")
            self.assertEqual(
                BUILD.engine.engine.KERNEL_DEBUG_PATH_REPRODUCIBLE,
                BUILD.P234_KERNEL_DEBUG_PATH_REPRODUCIBLE,
            )
            self.assertIn(
                "$(realpath $(abs_srctree)/../../..)=/private-repo",
                BUILD.engine.engine.KERNEL_DEBUG_PATH_REPRODUCIBLE,
            )
        self.assertEqual(BUILD.engine.SCHEMA, original["schema"])
        self.assertIs(BUILD.engine.contract, original["contract"])
        self.assertIs(BUILD.engine.witness_output_gate, original["gate"])
        self.assertEqual(
            BUILD.engine.engine.KERNEL_DEBUG_PATH_REPRODUCIBLE,
            original["kernel_debug"],
        )


if __name__ == "__main__":
    unittest.main()
