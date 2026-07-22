import importlib.util
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "s22plus_fyg8_p225_build.py"
OLD_VMLINUX = (
    ROOT
    / "workspace/private/outputs/s22plus_fyg8_p221_build/artifacts/vmlinux"
)
P225_VMLINUX = (
    ROOT
    / "workspace/private/outputs/s22plus_fyg8_p225_build/artifacts/vmlinux"
)


def load_module():
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_p225_build_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


class S22PlusFyg8P225BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_old_p221_vmlinux_fails_new_guard_audit(self):
        if not OLD_VMLINUX.is_file():
            self.skipTest("private P2.21 vmlinux is not present")
        with self.assertRaisesRegex(
            self.module.BuildAuditError, "vmlinux SHA256 mismatch"
        ):
            self.module.audit_linked_vmlinux(OLD_VMLINUX)

    def test_contract_adapter_binds_only_p225_patch(self):
        adapter = self.module._ContractAdapter
        self.assertEqual(adapter.CONFIG, self.module.contract.CONFIG)
        self.assertEqual(adapter.PATCH_SHA256, self.module.contract.PATCH_SHA256)
        self.assertEqual(adapter.DEFAULT_PATCH, self.module.contract.DEFAULT_PATCH)
        self.assertNotEqual(
            adapter.PATCH_SHA256, self.module.contract.p219.PATCH_SHA256
        )

    def test_instruction_bytes_normalize_gnu_and_llvm_formats(self):
        cases = (
            "ffffffc0080162fc:\td50b7e20 \tdc\tcivac, x0\n",
            "ffffffc0080162fc: 20 7e 0b d5   dc civac, x0\n",
        )
        normalized = [self.module._instruction_bytes(text) for text in cases]
        self.assertEqual(normalized, [bytes.fromhex("207e0bd5")] * 2)

    def test_symbol_ranges_share_next_distinct_address_for_aliases(self):
        symbols = "10 T first\n10 T alias\n20 T second\n30 T final\n"
        self.assertEqual(
            self.module._symbol_ranges(symbols),
            {"first": (0x10, 0x20), "alias": (0x10, 0x20), "second": (0x20, 0x30)},
        )

    def test_call_subsequence_is_ordered_but_allows_unrelated_calls(self):
        self.module._require_call_subsequence(
            ["first", "noise", "second"], ("first", "second"), "test"
        )
        with self.assertRaisesRegex(
            self.module.BuildAuditError, "call chain incomplete"
        ):
            self.module._require_call_subsequence(
                ["second", "first"], ("first", "second"), "test"
            )

    def test_exact_p225_vmlinux_passes_supplemental_linked_audit(self):
        if os.environ.get("S22PLUS_P225_LINKED_AUDIT") != "1":
            self.skipTest("set S22PLUS_P225_LINKED_AUDIT=1 for the private ELF audit")
        if not P225_VMLINUX.is_file():
            self.skipTest("private P2.25 vmlinux is not present")
        result = self.module.audit_linked_vmlinux(P225_VMLINUX)
        self.assertTrue(result["verified"])
        self.assertTrue(result["entry_copy_poc_flush_readback_linked"])
        self.assertTrue(result["userspace_copy_poc_flush_readback_linked"])
        self.assertFalse(result["reset_retention_proven"])

    def test_output_gate_requires_exact_wire_cardinality_and_linked_audit(self):
        source = Path(SCRIPT).read_text(encoding="ascii")
        for token in (
            '"image_userspace_count": 1',
            '"vmlinux_userspace_count": 1',
            '"image_unsat_count": 1',
            '"vmlinux_unsat_count": 1',
            '"p225_linked_audit"',
            '"p225_image_identity"',
            "image_sha256 == EXPECTED_IMAGE_SHA256",
            'linked.get("verified") is True',
        ):
            with self.subTest(token=token):
                self.assertIn(token, source)


if __name__ == "__main__":
    unittest.main()
