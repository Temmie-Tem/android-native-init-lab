import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/s22plus_fyg8_p221_build.py"
)
SPEC = importlib.util.spec_from_file_location("p221_build", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class S22PlusFyg8P221BuildTest(unittest.TestCase):
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

    def test_exact_three_record_contract_passes(self):
        payload = (
            MODULE.contract.ENTRY_PROOF
            + MODULE.contract.USERSPACE_PROOF
            + MODULE.contract.UNSAT_PROOF
        )
        result = self._gate(payload, payload)
        self.assertTrue(result["verified"])
        self.assertEqual(result["image_long_family_count"], 2)
        self.assertEqual(result["image_unsat_family_count"], 1)

    def test_missing_or_duplicate_record_fails(self):
        exact = (
            MODULE.contract.ENTRY_PROOF
            + MODULE.contract.USERSPACE_PROOF
            + MODULE.contract.UNSAT_PROOF
        )
        for payload in (
            exact.removesuffix(MODULE.contract.UNSAT_PROOF),
            exact + MODULE.contract.USERSPACE_PROOF,
            exact + MODULE.contract.UNSAT_PROOF,
        ):
            with self.subTest(size=len(payload)):
                self.assertFalse(self._gate(payload, payload)["verified"])

    def test_retired_e0_record_fails(self):
        payload = (
            MODULE.contract.ENTRY_PROOF
            + MODULE.contract.USERSPACE_PROOF
            + MODULE.contract.UNSAT_PROOF
            + MODULE.contract.OLD_E0_ENTRY_PROOF
        )
        result = self._gate(payload, payload)
        self.assertFalse(result["verified"])
        self.assertEqual(result["image_old_e0_entry_count"], 1)

    def test_engine_binding_is_scoped_and_restored(self):
        original_schema = MODULE.engine.SCHEMA
        original_contract = MODULE.engine.contract
        original_gate = MODULE.engine.witness_output_gate
        with MODULE.bind_engine():
            self.assertEqual(MODULE.engine.SCHEMA, MODULE.SCHEMA)
            self.assertIs(MODULE.engine.contract, MODULE._ContractAdapter)
            self.assertIs(MODULE.engine.witness_output_gate, MODULE.output_gate)
            self.assertEqual(MODULE.engine.PROOF_BYTES, MODULE.contract.ENTRY_PROOF)
        self.assertEqual(MODULE.engine.SCHEMA, original_schema)
        self.assertIs(MODULE.engine.contract, original_contract)
        self.assertIs(MODULE.engine.witness_output_gate, original_gate)

    def test_integrated_gate_checks_config_and_all_records(self):
        with tempfile.TemporaryDirectory() as temp_name:
            tree = Path(temp_name)
            dist = tree / "out/msm-waipio-waipio-gki/gki_kernel/dist"
            common = tree / "out/msm-waipio-waipio-gki/gki_kernel/common"
            dist.mkdir(parents=True)
            common.mkdir(parents=True)
            payload = (
                MODULE.contract.ENTRY_PROOF
                + MODULE.contract.USERSPACE_PROOF
                + MODULE.contract.UNSAT_PROOF
            )
            (dist / "Image").write_bytes(payload + b"\0" * (4096 - len(payload)))
            (dist / "vmlinux").write_bytes(payload)
            (common / ".config").write_text(
                f"{MODULE.contract.CONFIG}=y\nCONFIG_CRYPTO_FIPS=y\n",
                encoding="ascii",
            )
            inherited = MODULE.engine.engine
            original_size = inherited.STOCK_IMAGE_SIZE
            original_capacity = inherited.FIXED_KERNEL_SLOT_CAPACITY
            try:
                inherited.STOCK_IMAGE_SIZE = 4096
                inherited.FIXED_KERNEL_SLOT_CAPACITY = 4096
                with MODULE.bind_engine():
                    result = MODULE.engine.witness_output_gate(tree)
            finally:
                inherited.STOCK_IMAGE_SIZE = original_size
                inherited.FIXED_KERNEL_SLOT_CAPACITY = original_capacity
            self.assertTrue(result["verified"])
            self.assertEqual(result["config_enable_count"], 1)
            self.assertEqual(result["image_long_family_count"], 2)
            self.assertEqual(result["image_unsat_family_count"], 1)


if __name__ == "__main__":
    unittest.main()
