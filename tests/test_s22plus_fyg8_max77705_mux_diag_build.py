import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_max77705_mux_diag_build.py"
)
PRIVATE_BUILD = (
    ROOT
    / "workspace/private/outputs/s22plus_fyg8_max77705_gate0/"
    "custom-module-build-20260812-07"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_fyg8_max77705_mux_diag_build_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8Max77705MuxDiagBuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def test_exact_p310_kmi_source_set_is_not_current_config_wildcard(self):
        self.assertEqual(len(self.module.KMI_SYMBOL_LISTS), 25)
        self.assertEqual(self.module.KMI_SYMBOL_LISTS[0], "abi_gki_aarch64")
        self.assertEqual(self.module.KMI_SYMBOL_LISTS[-1], "abi_gki_aarch64_zebra")
        for later_addition in (
            "abi_gki_aarch64_asus",
            "abi_gki_aarch64_transsion",
            "abi_gki_aarch64_tuxera",
            "abi_gki_aarch64_galaxy_grey",
            "abi_gki_aarch64_galaxy_presubmit",
        ):
            self.assertNotIn(later_addition, self.module.KMI_SYMBOL_LISTS)

    def test_parse_symvers_rejects_duplicate_and_malformed_rows(self):
        with self.assertRaisesRegex(self.module.BuildError, "duplicate"):
            self.module.parse_symvers(
                "0x12345678\tone\tvmlinux\tEXPORT_SYMBOL\t\n"
                "0x87654321\tone\tvmlinux\tEXPORT_SYMBOL\t\n"
            )
        with self.assertRaisesRegex(self.module.BuildError, "malformed"):
            self.module.parse_symvers("not-a-symvers-row\n")

    def test_parse_modversions_rejects_duplicate_and_malformed_rows(self):
        with self.assertRaisesRegex(self.module.BuildError, "duplicate"):
            self.module.parse_modversions("0x12345678 one\n0x12345678 one\n")
        with self.assertRaisesRegex(self.module.BuildError, "malformed"):
            self.module.parse_modversions("1234 one extra\n")

    def test_call_relocation_parser_counts_linked_calls_only(self):
        text = (
            "  Section (9) .rela.text {\n"
            "    0x10 R_AARCH64_CALL26 one 0x0\n"
            "    0x14 R_AARCH64_CALL26 one 0x0\n"
            "    0x18 R_AARCH64_ABS64 ignored 0x0\n"
            "    0x1C R_AARCH64_CALL26 two 0x0\n"
            "  }\n"
        )
        self.assertEqual(
            self.module.call_relocation_counts(text), {"one": 2, "two": 1}
        )

    def test_relocation_section_is_exact_and_missing_is_loud(self):
        text = (
            "Relocations [\n"
            "  Section (18) .rela.rodata.ops {\n"
            "    0x18 R_AARCH64_ABS64 .text 0x728\n"
            "  }\n"
            "]\n"
        )
        self.assertIn(
            "R_AARCH64_ABS64",
            self.module.relocation_section(text, ".rela.rodata.ops"),
        )
        with self.assertRaisesRegex(self.module.BuildError, "missing"):
            self.module.relocation_section(text, ".rela.data.driver")

    def test_parse_modinfo_preserves_repeated_fields(self):
        fields = self.module.parse_modinfo(
            "name: one\nalias: first\nalias: second\ndepends: \n"
        )
        self.assertEqual(fields["alias"], ["first", "second"])
        self.assertEqual(fields["depends"], [""])

    def test_source_and_patch_identities_are_current(self):
        for name, identity in self.module.MODULE_SOURCE_IDENTITIES.items():
            result = self.module.validate_file(
                ROOT / self.module.MODULE_SOURCE_DIR / name,
                identity,
                name,
            )
            self.assertEqual(result["sha256"], identity[1])
        patch = self.module.validate_file(
            ROOT / self.module.P310_PATCH,
            self.module.P310_PATCH_IDENTITY,
            "P3.10 patch",
        )
        self.assertEqual(patch["size"], 42_020)

    def test_source_contract_is_executed_before_compile(self):
        result = self.module.validate_precompile_source_contract(ROOT)
        self.assertTrue(result["verified_before_compile"])
        self.assertTrue(result["validation"]["source_contract_satisfied"])
        self.assertEqual(
            result["module_source_sha256"],
            self.module.MODULE_SOURCE_IDENTITIES[
                "s22plus_max77705_mux_diag.c"
            ][1],
        )
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertLess(
            source.index("precompile_source_contract = validate_precompile_source_contract"),
            source.index('source_root = output_dir / "source"'),
        )

    def test_atomic_json_replaces_result(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            self.module.atomic_json(path, {"value": 1})
            self.module.atomic_json(path, {"value": 2})
            self.assertEqual(path.read_text(encoding="ascii"), '{\n  "value": 2\n}\n')

    def test_source_copy_does_not_require_reflink_support(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('"--reflink=always"', source)
        self.assertIn('[\n            "/usr/bin/cp",\n            "-a",', source)

    def test_host_link_uses_pinned_lld_and_compiler_rt(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = self.module.build_environment(ROOT, Path(directory))
        self.assertIn("-fuse-ld=lld", environment["HOSTLDFLAGS"])
        self.assertIn("--rtlib=compiler-rt", environment["HOSTLDFLAGS"])

    @unittest.skipUnless(
        (PRIVATE_BUILD / "immutable-a/s22plus_max77705_mux_diag.ko").is_file(),
        "private FYG8 linked module unavailable",
    )
    def test_private_a_b_linked_surface_passes_real_audit(self):
        result = self.module.audit_build(ROOT, PRIVATE_BUILD)
        self.assertEqual(
            result["verdict"], "PASS_AB_REPRODUCIBLE_LINKED_ABI_AUDITED"
        )
        self.assertTrue(result["a_b_byte_identical"])
        self.assertEqual(
            result["modules"]["a"]["call_relocations"],
            self.module.EXPECTED_CALL_RELOCATIONS,
        )
        self.assertEqual(result["modules"]["a"]["exports"], [])


if __name__ == "__main__":
    unittest.main()
