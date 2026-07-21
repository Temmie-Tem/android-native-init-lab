import hashlib
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1e0_pid1_userspace_proof.py"
)
SPEC = importlib.util.spec_from_file_location("r4w1e0_pid1_userspace_proof", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class R4W1E0Pid1UserspaceProofTest(unittest.TestCase):
    def setUp(self):
        self.source = ROOT / MODULE.DEFAULT_SOURCE
        self.patch = ROOT / MODULE.DEFAULT_PATCH
        self.init = ROOT / MODULE.DEFAULT_INIT
        self.runtime_receipt = ROOT / MODULE.DEFAULT_RUNTIME_RECEIPT

    def test_protocol_identities_are_exact(self):
        self.assertEqual(len(MODULE.ENTRY_PROOF), 45)
        self.assertEqual(len(MODULE.USERSPACE_PROOF), 45)
        self.assertNotEqual(MODULE.ENTRY_PROOF, MODULE.USERSPACE_PROOF)
        self.assertEqual(
            hashlib.sha256(MODULE.ENTRY_PREIMAGE.encode("ascii")).hexdigest(),
            MODULE.ENTRY_SHA256,
        )
        self.assertEqual(
            hashlib.sha256(MODULE.USERSPACE_PREIMAGE.encode("ascii")).hexdigest(),
            MODULE.USERSPACE_SHA256,
        )
        self.assertTrue(MODULE.check_protocol()["verified"])
        self.assertEqual(
            hashlib.sha256(MODULE.PROBE_ID_PREIMAGE.encode("ascii")).digest()[:16],
            MODULE.PROBE_ID,
        )

    def test_entry_model_rejects_unproved_paths(self):
        cases = (
            {"exec_ok": False, "pid": 1, "magic": 0x4D474F4C, "idx": 0x300000},
            {"exec_ok": True, "pid": 2, "magic": 0x4D474F4C, "idx": 0x300000},
            {"exec_ok": True, "pid": 1, "magic": 0, "idx": 0x300000},
            {"exec_ok": True, "pid": 1, "magic": 0x4D474F4C, "idx": 1},
        )
        for case in cases:
            with self.subTest(case=case):
                state = MODULE.model_entry(**case, boot=4)
                self.assertFalse(state.ready)
                self.assertEqual(state.slot, b"")

    def _entry(self):
        return MODULE.model_entry(
            exec_ok=True,
            pid=1,
            magic=0x4D474F4C,
            idx=0x300000,
            boot=4,
        )

    def test_userspace_model_rejects_wrong_identity(self):
        mutations = (
            {"pid": 2},
            {"offset": 1},
            {"request": MODULE.REQUEST[:-1]},
            {"request": bytes([MODULE.REQUEST[0] ^ 1]) + MODULE.REQUEST[1:]},
            {"idx": 0x300001},
            {"boot": 5},
        )
        defaults = {
            "pid": 1,
            "offset": 0,
            "request": MODULE.REQUEST,
            "idx": 0x300000,
            "boot": 4,
        }
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                state = self._entry()
                self.assertLess(MODULE.model_write(state, **(defaults | mutation)), 0)
                self.assertEqual(state.slot, MODULE.ENTRY_PROOF)

    def test_userspace_model_requires_entry_slot(self):
        state = self._entry()
        state.slot = b"X" * len(MODULE.ENTRY_PROOF)
        result = MODULE.model_write(
            state,
            pid=1,
            offset=0,
            request=MODULE.REQUEST,
            idx=0x300000,
            boot=4,
        )
        self.assertLess(result, 0)
        self.assertFalse(state.userspace_proven)

    def test_userspace_model_exact_transition_is_one_shot(self):
        state = self._entry()
        arguments = {
            "pid": 1,
            "offset": 0,
            "request": MODULE.REQUEST,
            "idx": 0x300000,
            "boot": 4,
        }
        self.assertEqual(MODULE.model_write(state, **arguments), len(MODULE.REQUEST))
        self.assertEqual(state.slot, MODULE.USERSPACE_PROOF)
        self.assertTrue(state.userspace_proven)
        self.assertLess(MODULE.model_write(state, **arguments), 0)

    def test_observation_requires_clean_baseline_and_unique_identity(self):
        self.assertEqual(
            MODULE.classify_observation(b"prior", MODULE.ENTRY_PROOF),
            "ENTRY_ONLY",
        )
        self.assertEqual(
            MODULE.classify_observation(b"prior", MODULE.USERSPACE_PROOF),
            "USERSPACE_CALLBACK_REACHED",
        )
        with self.assertRaisesRegex(MODULE.CheckError, "pre-candidate"):
            MODULE.classify_observation(MODULE.ENTRY_PROOF, MODULE.USERSPACE_PROOF)
        with self.assertRaisesRegex(MODULE.CheckError, "cardinality"):
            MODULE.classify_observation(b"prior", b"no proof")
        with self.assertRaisesRegex(MODULE.CheckError, "cardinality"):
            MODULE.classify_observation(
                b"prior", MODULE.ENTRY_PROOF + MODULE.USERSPACE_PROOF
            )

    def test_patch_and_source_contract_pass(self):
        result = MODULE.run(self.source, self.patch, self.init)
        self.assertEqual(result["verdict"], MODULE.VERDICT)
        self.assertTrue(result["source"]["source_semantics"])
        self.assertTrue(result["runtime_artifact"]["two_build_byte_identical"])
        self.assertEqual(result["runtime_artifact"]["probe_id"], MODULE.PROBE_ID.hex())
        self.assertFalse(result["safety"]["device_contact"])
        self.assertFalse(result["safety"]["live_authorized"])

    def test_runtime_artifact_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_name:
            changed = Path(temp_name) / "init"
            changed.write_bytes(self.init.read_bytes() + b"X")
            with self.assertRaisesRegex(MODULE.CheckError, "SHA256 mismatch"):
                MODULE.check_runtime_artifact(changed, self.runtime_receipt)

    def test_runtime_receipt_reproduces_exact_artifacts(self):
        receipt, init_data, child_data = MODULE.reproduce_runtime(ROOT)
        encoded = MODULE.encode_runtime_receipt(receipt)
        self.assertEqual(encoded, self.runtime_receipt.read_bytes())
        self.assertEqual(init_data, self.init.read_bytes())
        self.assertEqual(
            hashlib.sha256(encoded).hexdigest(), MODULE.RUNTIME_RECEIPT_SHA256
        )
        self.assertEqual(
            hashlib.sha256(child_data).hexdigest(), receipt["child"]["sha256"]
        )

    def test_runtime_receipt_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_name:
            changed = Path(temp_name) / "runtime-receipt.json"
            changed.write_bytes(self.runtime_receipt.read_bytes() + b"\n")
            with self.assertRaisesRegex(MODULE.CheckError, "receipt SHA256 mismatch"):
                MODULE.check_runtime_artifact(self.init, changed)

    def test_patch_hash_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_name:
            changed = Path(temp_name) / "changed.patch"
            changed.write_bytes(self.patch.read_bytes() + b"\n")
            with self.assertRaisesRegex(MODULE.CheckError, "SHA256 mismatch"):
                MODULE.check_patch(changed)

    def test_forbidden_operation_is_rejected_after_identity_rebind(self):
        with tempfile.TemporaryDirectory() as temp_name:
            changed = Path(temp_name) / "changed.patch"
            changed.write_bytes(self.patch.read_bytes() + b"+panic();\n")
            original = MODULE.PATCH_SHA256
            MODULE.PATCH_SHA256 = MODULE.shared.sha256_file(changed)
            try:
                with self.assertRaisesRegex(MODULE.CheckError, "forbidden"):
                    MODULE.check_patch(changed)
            finally:
                MODULE.PATCH_SHA256 = original

    def test_base_source_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_name:
            source = Path(temp_name)
            for relative in MODULE.shared.BASE_FILES:
                destination = source / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self.source / relative, destination)
            main = source / "kernel_platform/common/init/main.c"
            main.write_bytes(main.read_bytes() + b"\n")
            with self.assertRaises(MODULE.shared.CheckError):
                MODULE.apply_and_check(source, self.patch)


if __name__ == "__main__":
    unittest.main()
