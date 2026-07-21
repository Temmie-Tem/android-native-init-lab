import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1e0_build.py"
)
SPEC = importlib.util.spec_from_file_location("r4w1e0_build", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class R4W1E0BuildTest(unittest.TestCase):
    def _gate(self, image_bytes, vmlinux_bytes):
        with tempfile.TemporaryDirectory() as temp_name:
            temp = Path(temp_name)
            image = temp / "Image"
            vmlinux = temp / "vmlinux"
            image.write_bytes(image_bytes)
            vmlinux.write_bytes(vmlinux_bytes)
            original = MODULE.BASE_OUTPUT_GATE
            MODULE.BASE_OUTPUT_GATE = lambda _tree: {
                "image_path": str(image),
                "vmlinux_path": str(vmlinux),
                "verified": True,
            }
            try:
                return MODULE.output_gate(temp)
            finally:
                MODULE.BASE_OUTPUT_GATE = original

    def test_two_exact_proofs_pass_output_gate(self):
        payload = MODULE.proof.ENTRY_PROOF + MODULE.proof.USERSPACE_PROOF
        result = self._gate(payload, payload)
        self.assertTrue(result["verified"])
        self.assertEqual(result["image_userspace_proof_count"], 1)
        self.assertEqual(result["image_shared_family_count"], 2)

    def test_missing_userspace_proof_fails_output_gate(self):
        result = self._gate(MODULE.proof.ENTRY_PROOF, MODULE.proof.ENTRY_PROOF)
        self.assertFalse(result["verified"])
        self.assertEqual(result["image_userspace_proof_count"], 0)
        self.assertEqual(result["image_shared_family_count"], 1)

    def test_duplicate_shared_family_fails_output_gate(self):
        payload = (
            MODULE.proof.ENTRY_PROOF
            + MODULE.proof.USERSPACE_PROOF
            + MODULE.proof.USERSPACE_PROOF
        )
        result = self._gate(payload, payload)
        self.assertFalse(result["verified"])
        self.assertEqual(result["image_shared_family_count"], 3)

    def test_engine_binding_is_scoped_and_restored(self):
        original_schema = MODULE.engine.SCHEMA
        original_gate = MODULE.engine.witness_output_gate
        with MODULE.bind_engine():
            self.assertEqual(MODULE.engine.SCHEMA, MODULE.SCHEMA)
            self.assertIs(MODULE.engine.witness_output_gate, MODULE.output_gate)
            self.assertEqual(MODULE.engine.PROOF_BYTES, MODULE.proof.ENTRY_PROOF)
        self.assertEqual(MODULE.engine.SCHEMA, original_schema)
        self.assertIs(MODULE.engine.witness_output_gate, original_gate)

    def test_integrated_engine_gate_observes_exact_config_and_both_proofs(self):
        with tempfile.TemporaryDirectory() as temp_name:
            tree = Path(temp_name)
            dist = tree / "out/msm-waipio-waipio-gki/gki_kernel/dist"
            common = tree / "out/msm-waipio-waipio-gki/gki_kernel/common"
            dist.mkdir(parents=True)
            common.mkdir(parents=True)
            payload = MODULE.proof.ENTRY_PROOF + MODULE.proof.USERSPACE_PROOF
            (dist / "Image").write_bytes(payload + b"\0" * (4096 - len(payload)))
            (dist / "vmlinux").write_bytes(payload)
            (common / ".config").write_text(
                f"{MODULE.proof.CONFIG}=y\nCONFIG_CRYPTO_FIPS=y\n",
                encoding="ascii",
            )
            build_base = MODULE.engine.engine
            original_size = build_base.STOCK_IMAGE_SIZE
            original_capacity = build_base.FIXED_KERNEL_SLOT_CAPACITY
            try:
                build_base.STOCK_IMAGE_SIZE = 4096
                build_base.FIXED_KERNEL_SLOT_CAPACITY = 4096
                with MODULE.bind_engine():
                    result = MODULE.engine.witness_output_gate(tree)
            finally:
                build_base.STOCK_IMAGE_SIZE = original_size
                build_base.FIXED_KERNEL_SLOT_CAPACITY = original_capacity
            self.assertTrue(result["verified"])
            self.assertEqual(result["config_enable_count"], 1)
            self.assertEqual(result["image_shared_family_count"], 2)


if __name__ == "__main__":
    unittest.main()
