import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))
try:
    MODULE = importlib.import_module("s22plus_fyg8_p234_build_repro_check")
finally:
    sys.path.remove(str(SCRIPTS))


class S22PlusFyg8P234BuildReproCheckTest(unittest.TestCase):
    def p280_contract(self):
        return {
            "run_id": "ab" * 16,
            "source_contract_id": MODULE.P280_SOURCE_CONTRACT_ID,
        }

    def p280_qualification(self):
        return {
            "schema": MODULE.P280_QUALIFICATION_SCHEMA,
            "verdict": MODULE.P280_QUALIFICATION_VERDICT,
            "build_allowed": True,
            "run_id": "ab" * 16,
            "source_contract_id": MODULE.P280_SOURCE_CONTRACT_ID,
            "qualification_repo_path": "workspace/private/qualification.json",
            "intent_repo_path": "workspace/private/intent.json",
            "patch_repo_path": "workspace/private/candidate.patch",
            "qualification": {
                "path": "/namespace/qualification.json",
                "size": 10,
                "sha256": "1" * 64,
            },
            "gate_result_receipts": {
                name: {"size": 11, "sha256": str(index) * 64}
                for index, name in enumerate(
                    sorted(MODULE.P280_GATE_RESULTS), start=2
                )
            },
            "verified": True,
        }

    def test_symbol_ranges_use_next_distinct_address(self):
        symbols = "10 t first\n10 t alias\n20 t second\n30 t last\n"
        self.assertEqual(
            MODULE._symbol_ranges(symbols),
            {
                "first": (0x10, 0x20),
                "alias": (0x10, 0x20),
                "second": (0x20, 0x30),
            },
        )

    def test_call_parser_normalizes_pi_and_memcpy(self):
        text = """
10: 94000000 bl 20 <__pi___flush_dcache_area>
14: 94000000 bl 24 <__memcpy+0x4>
"""
        self.assertEqual(MODULE._calls(text), ["__flush_dcache_area", "memcpy"])

    def test_linked_data_symbol_dump_is_exact_and_bounded(self):
        dump = """
Contents of section .rodata:
 100 10111213 14151617 18191a1b 1c1d1e1f  ................
"""
        with mock.patch.object(MODULE, "_run", return_value=dump):
            data = MODULE._dump_symbol_bytes(
                Path("/tool/objdump"),
                Path("/tmp/vmlinux"),
                {"table": (0x100, 0x120)},
                "table",
                10,
            )
        self.assertEqual(data, bytes(range(0x10, 0x1A)))
        with mock.patch.object(MODULE, "_run", return_value=" 100 10111213\n"):
            with self.assertRaisesRegex(MODULE.CheckError, "dump is short"):
                MODULE._dump_symbol_bytes(
                    Path("/tool/objdump"),
                    Path("/tmp/vmlinux"),
                    {"table": (0x100, 0x120)},
                    "table",
                    8,
                )

    def test_wrapper_result_accepts_only_final_or_exact_legacy_false_negative(self):
        final = {
            "returncode": 0,
            "p234_build_pass": True,
            "witness_output_gate": {"verified": True},
        }
        self.assertEqual(MODULE._classify_wrapper_result(final), "final-wrapper-pass")

        historical = {
            family.decode("ascii"): {"image": 0, "vmlinux": 0}
            for family in MODULE.build.HISTORICAL_FAMILIES
        }
        inert = {
            family.decode("ascii"): {"image": 1, "vmlinux": 1}
            for family in MODULE.build.INERT_REJECTION_FAMILIES
        }
        legacy = {
            "returncode": 7,
            "p234_build_pass": False,
            "witness_output_gate": {
                "verified": False,
                "historical_family_counts": {**historical, **inert},
                "candidate_binary_counts": {
                    name: {
                        "long_family": 1,
                        "unsat_family": 1,
                        "request_magic": 1,
                        "run_id_hex": 1,
                        "unsat_tag_hex": 1,
                        "model_run_id": 0,
                        "source_check_run_id": 0,
                    }
                    for name in ("image", "vmlinux")
                },
                "candidate_config_counts": {"x": 1},
                "historical_config_enable_counts": {"old": 0},
                "exact_stock_image_size": True,
                "fits_fixed_ramdisk_layout": True,
                "preserves_fixed_ramdisk_start": True,
                "image_proof_count": 1,
                "vmlinux_proof_count": 1,
                "image_proof_family_count": 1,
                "vmlinux_proof_family_count": 1,
                "config_enable_count": 1,
                "fips_enable_count": 1,
            },
        }
        self.assertEqual(
            MODULE._classify_wrapper_result(legacy),
            "legacy-inert-literal-false-negative-requalified",
        )
        legacy["witness_output_gate"]["historical_family_counts"][
            "S22UNS1|"
        ]["image"] = 2
        with self.assertRaises(MODULE.CheckError):
            MODULE._classify_wrapper_result(legacy)

    def test_source_delta_hashes_ignores_recorded_metadata_but_not_identity(self):
        rows = {"init/main.c": {"sha256": "a" * 64, "mode": 0o444}}
        self.assertEqual(
            MODULE._source_delta_hashes(rows, "test"),
            {"init/main.c": "a" * 64},
        )
        rows["init/main.c"]["sha256"] = "bad"
        with self.assertRaises(MODULE.CheckError):
            MODULE._source_delta_hashes(rows, "test")

    def test_p280_qualification_normalizes_paths_but_binds_receipts(self):
        first = self.p280_qualification()
        second = self.p280_qualification()
        second["qualification"]["path"] = "/other/qualification.json"
        self.assertEqual(
            MODULE.p280_qualification_identity(first, self.p280_contract()),
            MODULE.p280_qualification_identity(second, self.p280_contract()),
        )
        second["gate_result_receipts"]["userspace"]["sha256"] = "f" * 64
        self.assertNotEqual(
            MODULE.p280_qualification_identity(first, self.p280_contract()),
            MODULE.p280_qualification_identity(second, self.p280_contract()),
        )

    def test_p280_qualification_rejects_missing_gate_provenance(self):
        value = self.p280_qualification()
        value["gate_result_receipts"].pop("userspace")
        with self.assertRaisesRegex(MODULE.CheckError, "incomplete"):
            MODULE.p280_qualification_identity(value, self.p280_contract())

    def test_p280_qualification_file_rejects_forged_summary_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            relative = Path("workspace/private/qualification.json")
            path = root / relative
            path.parent.mkdir(parents=True)
            path.write_text(
                json.dumps(
                    {
                        "candidate": {
                            "intent_repo_path": "workspace/private/intent.json",
                            "patch_repo_path": "workspace/private/patch",
                        }
                    }
                ),
                encoding="ascii",
            )
            value = self.p280_qualification()
            value["qualification_repo_path"] = str(relative)
            with self.assertRaisesRegex(
                MODULE.CheckError, "file receipt mismatch"
            ):
                MODULE.verify_p280_qualification_file(
                    value,
                    self.p280_contract(),
                    intent_path=root / "workspace/private/intent.json",
                    patch_path=root / "workspace/private/candidate.patch",
                    root=root,
                )

    def test_p280_qualification_rejects_different_selected_input_path(self):
        value = self.p280_qualification()
        with self.assertRaisesRegex(
            MODULE.CheckError, "differs from selection"
        ):
            MODULE.verify_p280_qualification_file(
                value,
                self.p280_contract(),
                intent_path=Path("/tmp/repo/workspace/private/other.json"),
                patch_path=Path("/tmp/repo/workspace/private/candidate.patch"),
                root=Path("/tmp/repo"),
            )

    def test_repro_check_rejects_different_ab_qualifications(self):
        qualification_a = MODULE.p280_qualification_identity(
            self.p280_qualification(), self.p280_contract()
        )
        changed = self.p280_qualification()
        changed["qualification"]["sha256"] = "f" * 64
        qualification_b = MODULE.p280_qualification_identity(
            changed, self.p280_contract()
        )
        artifacts = {
            name: {"size": 1, "sha256": "a" * 64}
            for name in MODULE.ARTIFACT_LIMITS
            if name != "build-result.json"
        }
        bundles = [
            {
                "artifacts": artifacts,
                "pre_lto_qualification": qualification_a,
            },
            {
                "artifacts": artifacts,
                "pre_lto_qualification": qualification_b,
            },
        ]
        args = SimpleNamespace(
            source=Path("source"),
            intent=Path("intent"),
            patch=Path("patch"),
            build_a=Path("a"),
            build_b=Path("b"),
            nm=Path("nm"),
            objdump=Path("objdump"),
        )
        with mock.patch.object(
            MODULE.candidate_contract,
            "verify",
            return_value=self.p280_contract(),
        ), mock.patch.object(
            MODULE, "verify_bundle", side_effect=bundles
        ):
            with self.assertRaisesRegex(
                MODULE.CheckError, "A/B pre-LTO qualification mismatch"
            ):
                MODULE.check(args)

    def test_call_subsequence_is_ordered(self):
        MODULE._subsequence(["first", "noise", "second"], ("first", "second"), "x")
        with self.assertRaisesRegex(MODULE.CheckError, "call order mismatch"):
            MODULE._subsequence(["second", "first"], ("first", "second"), "x")

    def test_stable_receipt_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.write_bytes(b"payload")
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaises(OSError):
                MODULE.stable_receipt(link, "link", 1024)

    def test_repro_contract_requires_six_exact_artifacts(self):
        self.assertEqual(
            set(MODULE.ARTIFACT_LIMITS) - {"build-result.json"},
            {"Image", "vmlinux", ".config", "System.map", "vmlinux.symvers", "abi.xml"},
        )
        self.assertIn("s22_fyg8_e1_head", MODULE.REQUIRED_SYMBOLS)
        self.assertIn(
            "s22_fyg8_e1_record_families_allowed", MODULE.REQUIRED_SYMBOLS
        )
        self.assertIn("s22_fyg8_e1_write", MODULE.REQUIRED_SYMBOLS)
        self.assertIn("__pi___flush_dcache_area", MODULE.REQUIRED_SYMBOLS)
        self.assertNotIn("s22_fyg8_e1_store", MODULE.REQUIRED_SYMBOLS)
        self.assertEqual(
            MODULE.RANDOM_PRIVATE_PATH_PREFIX,
            b"/tmp/s22-r4w1b-private-",
        )

    def test_linked_audit_uses_only_captured_staged_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            vmlinux = root / "vmlinux"
            nm = root / "nm"
            objdump = root / "objdump"
            original = b"linked-kernel-before-swap"
            vmlinux.write_bytes(original)
            nm.write_bytes(b"captured-nm")
            objdump.write_bytes(b"captured-objdump")
            expected = MODULE.candidate_contract.intent.receipt(original)
            symbols = {
                name: 0x100 + index * 0x100
                for index, name in enumerate(MODULE.REQUIRED_SYMBOLS)
            }
            symbol_table = "".join(
                f"{address:x} t {name}\n" for name, address in symbols.items()
            ) + "700 t audit_end\n"
            seen = []

            def disassembly_calls(names):
                return "".join(
                    f"0: 94000000 bl 10 <{name}>\n" for name in names
                )

            def fake_run(command, label):
                seen.append(tuple(command))
                self.assertNotEqual(Path(command[0]), nm)
                self.assertNotEqual(Path(command[0]), objdump)
                self.assertNotEqual(Path(command[-1]), vmlinux)
                self.assertEqual(Path(command[-1]).read_bytes(), original)
                if label == "nm":
                    vmlinux.write_bytes(b"swapped-after-capture")
                    return symbol_table
                start = int(
                    next(value for value in command if value.startswith("--start-address="))
                    .split("=", 1)[1],
                    16,
                )
                symbol = next(name for name, address in symbols.items() if address == start)
                if symbol == "kernel_init":
                    return disassembly_calls(
                        (
                            "run_init_process",
                            "strcmp",
                            "s22_fyg8_e1_head",
                            "__pi___flush_dcache_area",
                            "crc32_le",
                            "s22_fyg8_e1_record_families_allowed",
                            "__pi___flush_dcache_area",
                        )
                    )
                if symbol == "s22_fyg8_e1_write":
                    return disassembly_calls(
                        (
                            "_copy_from_user",
                            "__pi___flush_dcache_area",
                            "crc32_le",
                            "s22_fyg8_e1_head",
                            "crc32_le",
                            "s22_fyg8_e1_record_families_allowed",
                            "__pi___flush_dcache_area",
                            "__pi___flush_dcache_area",
                        )
                    )
                if symbol == "__pi___flush_dcache_area":
                    return "0: dc civac, x0\n4: dsb sy\n"
                return ""

            with mock.patch.object(MODULE, "_run", side_effect=fake_run):
                result = MODULE.audit_linked(vmlinux, nm, objdump, expected)
            self.assertTrue(result["verified"])
            self.assertEqual(
                result["staged_input_receipts"]["vmlinux"], expected
            )
            self.assertEqual(vmlinux.read_bytes(), b"swapped-after-capture")
            self.assertEqual(len(seen), 1 + len(MODULE.REQUIRED_SYMBOLS))


if __name__ == "__main__":
    unittest.main()
