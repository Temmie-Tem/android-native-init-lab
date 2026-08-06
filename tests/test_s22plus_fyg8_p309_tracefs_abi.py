from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))

import s22plus_fyg8_p308_generator as parent  # noqa: E402
import s22plus_fyg8_p308_overlay_contract as parent_contract  # noqa: E402
import s22plus_fyg8_p309_descriptor_transform as transform  # noqa: E402
import s22plus_fyg8_p309_generator as generator  # noqa: E402
import s22plus_fyg8_p309_host_contract as contract  # noqa: E402
import s22plus_fyg8_p309_tracefs_abi_audit as audit  # noqa: E402


@lru_cache(maxsize=1)
def _parent_value() -> dict:
    return json.loads((ROOT / parent_contract.DEFAULT_INTENT).read_text("ascii"))


@lru_cache(maxsize=1)
def _baseline() -> dict[str, bytes]:
    value = _parent_value()
    return parent.generate_bytes(
        ROOT,
        run_id=bytes.fromhex(value["run_id"]),
        unsat_tag=bytes.fromhex(value["unsat_tag_hex"]),
        profile=value["profile"],
    )


@lru_cache(maxsize=1)
def _generated() -> dict[str, bytes]:
    value = _parent_value()
    return generator.generate_bytes(
        ROOT,
        run_id=bytes.fromhex(value["run_id"]),
        unsat_tag=bytes.fromhex(value["unsat_tag_hex"]),
        profile=value["profile"],
    )


@lru_cache(maxsize=1)
def _abi_result() -> dict:
    return audit.audit(ROOT, _generated()["trace_descriptor_header"])


class P309TracefsAbiTests(unittest.TestCase):
    def test_successor_delta_is_exactly_one_descriptor_artifact(self) -> None:
        changed = {
            key for key in _generated() if _generated()[key] != _baseline()[key]
        }
        self.assertEqual(changed, generator.DELTA_KEYS)
        descriptor = _generated()["trace_descriptor_header"]
        self.assertEqual(descriptor.count(b"rc=%x21:s32"), 1)
        self.assertNotIn(b"rc=%w21:s32", descriptor)
        self.assertEqual(
            transform.transform_descriptor(_baseline()["trace_descriptor_header"]),
            descriptor,
        )

    def test_source_and_linked_a_b_authorities_are_identical(self) -> None:
        result = _abi_result()
        self.assertTrue(result["verified"])
        for domain in ("registers", "fetch_types"):
            authority = result["authority"][domain]
            self.assertTrue(authority["source_equals_a_equals_b"])
            self.assertEqual(authority["source"], authority["linked_a"])
            self.assertEqual(authority["source"], authority["linked_b"])
        self.assertIn("x21", result["authority"]["registers"]["source"]["values"])
        self.assertNotIn("w21", result["authority"]["registers"]["source"]["values"])
        self.assertIn("lr", result["authority"]["registers"]["source"]["values"])
        self.assertIn("s32", result["authority"]["fetch_types"]["source"]["values"])

    def test_actual_generated_descriptor_is_exhaustively_validated(self) -> None:
        descriptor = _abi_result()["descriptor"]
        self.assertEqual(descriptor["event_count"], 48)
        self.assertEqual(
            descriptor["family_counts"], {"role": 4, "cycle": 29, "bind": 15}
        )
        self.assertEqual(descriptor["qscratch_trace_fetch_register"], "x21")
        qscratch = _abi_result()["qscratch"]
        self.assertEqual(qscratch["machine_readback_register"], "w21")
        self.assertTrue(qscratch["machine_w21_unmodified_to_probe"])
        self.assertTrue(qscratch["x21_lower_32_bits_are_w21"])

    def test_invalid_w_register_and_type_are_rejected(self) -> None:
        registers = audit.extract_source_registers((ROOT / audit.PTRACE).read_bytes())
        types = audit.extract_source_types((ROOT / audit.TRACE_PROBE).read_bytes())
        names = audit.extract_source_name_contract(
            (ROOT / audit.TRACE_H).read_bytes(),
            (ROOT / audit.TRACE_PROBE).read_bytes(),
            (ROOT / audit.TRACE_PROBE_H).read_bytes(),
        )
        bad_register = _generated()["trace_descriptor_header"].replace(
            b"rc=%x21:s32", b"rc=%w21:s32"
        )
        with self.assertRaisesRegex(audit.AuditError, "register is outside linked ABI"):
            audit.validate_descriptor(bad_register, registers, types, names)
        bad_type = _generated()["trace_descriptor_header"].replace(
            b"rc=%x21:s32", b"rc=%x21:not_a_type"
        )
        with self.assertRaisesRegex(audit.AuditError, "type is outside linked ABI"):
            audit.validate_descriptor(bad_type, registers, types, names)

    def test_register_tokens_bitfields_and_event_identity_fail_closed(self) -> None:
        registers = audit.extract_source_registers((ROOT / audit.PTRACE).read_bytes())
        types = audit.extract_source_types((ROOT / audit.TRACE_PROBE).read_bytes())
        names = audit.extract_source_name_contract(
            (ROOT / audit.TRACE_H).read_bytes(),
            (ROOT / audit.TRACE_PROBE).read_bytes(),
            (ROOT / audit.TRACE_PROBE_H).read_bytes(),
        )
        descriptor = _generated()["trace_descriptor_header"]
        malformed_register = descriptor.replace(b"on=%x1:s32", b"on=%21:s32", 1)
        with self.assertRaisesRegex(audit.AuditError, "register expression differs"):
            audit.validate_descriptor(malformed_register, registers, types, names)

        invalid_bitfield = descriptor.replace(b"b4@8/32", b"b999@999/999", 1)
        with self.assertRaisesRegex(audit.AuditError, "bitfield bounds differ"):
            audit.validate_descriptor(invalid_bitfield, registers, types, names)

        duplicate_event = descriptor.replace(
            b'{"resume_in", "p:p282/resume_in ',
            b'{"start_in", "p:p282/start_in ',
            1,
        )
        with self.assertRaisesRegex(audit.AuditError, "group/event is duplicated"):
            audit.validate_descriptor(duplicate_event, registers, types, names)

    def test_source_extractors_fail_on_unconsumed_entries_and_set_drift(self) -> None:
        ptrace = (ROOT / audit.PTRACE).read_bytes()
        missing_lr = ptrace.replace(
            b'\t{.name = "lr", .offset = offsetof(struct pt_regs, regs[30])},\n',
            b"",
            1,
        )
        source_without_lr = audit.extract_source_registers(missing_lr)
        self.assertNotIn("lr", source_without_lr)
        linked, _ = audit._linked_names(  # noqa: SLF001
            ROOT / audit.VMLINUX_A, "regoffset_table", 16
        )
        self.assertNotEqual(set(source_without_lr), set(linked))

        types = (ROOT / audit.TRACE_PROBE).read_bytes()
        unknown = types.replace(
            b"\n\tASSIGN_FETCH_TYPE_END\n",
            b"\n\tNEW_FETCH_TYPE_FORM(foo),\n\n\tASSIGN_FETCH_TYPE_END\n",
            1,
        )
        with self.assertRaisesRegex(audit.AuditError, "unconsumed fetch-type"):
            audit.extract_source_types(unknown)

    def test_bad_group_event_and_alias_names_are_rejected(self) -> None:
        registers = audit.extract_source_registers((ROOT / audit.PTRACE).read_bytes())
        types = audit.extract_source_types((ROOT / audit.TRACE_PROBE).read_bytes())
        names = audit.extract_source_name_contract(
            (ROOT / audit.TRACE_H).read_bytes(),
            (ROOT / audit.TRACE_PROBE).read_bytes(),
            (ROOT / audit.TRACE_PROBE_H).read_bytes(),
        )
        descriptor = _generated()["trace_descriptor_header"]
        bad_group = descriptor.replace(
            b"p:p282/p307_qscratch", b"p:bad-group/p307_qscratch"
        )
        with self.assertRaisesRegex(audit.AuditError, "definition grammar differs"):
            audit.validate_descriptor(bad_group, registers, types, names)
        bad_event = descriptor.replace(b"p:p282/p307_qscratch", b"p:p282/9bad")
        with self.assertRaisesRegex(audit.AuditError, "definition grammar differs"):
            audit.validate_descriptor(bad_event, registers, types, names)
        bad_alias = descriptor.replace(b"rc=%x21:s32", b"bad-alias=%x21:s32")
        with self.assertRaisesRegex(audit.AuditError, "fetch alias/type differs"):
            audit.validate_descriptor(bad_alias, registers, types, names)

    def test_host_contract_forbids_execution_and_requires_carrier_v2(self) -> None:
        result = contract.verify(ROOT)
        self.assertEqual(result["classification"], "TRACEFS_ABI_CROSS_AUTHORITY_FAILURE")
        self.assertFalse(result["execution"]["p308_replay_permitted"])
        self.assertFalse(result["execution"]["candidate_execution_permitted"])
        self.assertTrue(
            result["execution"]["carrier_v2_required_before_next_telemetry_rich_candidate"]
        )
        self.assertEqual(result["delta_keys"], ["trace_descriptor_header"])


if __name__ == "__main__":
    unittest.main()
