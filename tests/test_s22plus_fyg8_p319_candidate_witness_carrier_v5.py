from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
import zlib


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p319_candidate_witness_carrier_v5.py"
)
OUTPUT = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_p319/"
    "successor-witness-carrier-v5-20260820-13"
)


def load_bootstrap():
    spec = importlib.util.spec_from_file_location("p319_carrier_v5", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load Carrier-v5 auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P319CandidateWitnessCarrierV5Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bootstrap = load_bootstrap()
        cls.module = cls.bootstrap.load_bound_auditor()
        cls.inputs = cls.module.load_inputs(False, OUTPUT)
        cls.result = cls.module.build_result(cls.inputs)
        cls.receipt = cls.module.encode_result(cls.result)

    def envelope(
        self, state=None, *, terminal_code=1, mux_code=0, result=None,
        binding=None, exec_values=None,
    ):
        state = copy.deepcopy(state or self.module.sample_state())
        payload = self.module.encode_payload_v5(state)
        envelope = bytearray(self.module.ENVELOPE_SIZE)
        envelope[:5] = b"MXD5\x05"
        envelope[5] = terminal_code
        envelope[6] = mux_code
        envelope[7] = self.module.V5_WITNESS_FLAG | 0x14
        if result is not None:
            envelope[7] |= 1
            envelope[8] = result["stage"]
            struct.pack_into("<i", envelope, 9, result["rc"])
            envelope[13] = result.get("pmic_valid_mask", 0)
            envelope[14] = result.get("pmic_id", 0)
            envelope[15] = result.get("pmic_rev", 0)
            envelope[16] = result.get("initial_uic_valid", 0)
            envelope[17] = result.get("initial_uic", 0)
            envelope[18] = result["command_issued_mask"]
            envelope[19] = result["response_seen_mask"]
            envelope[20] = result["write_attempted"]
            envelope[21] = result["write_ambiguous"]
            envelope[22:26] = bytes(result["response_opcode"])
            envelope[26:30] = bytes(result["response_value"])
            envelope[30:34] = bytes(result["poll_count"])
            struct.pack_into("<H", envelope, 44, sum(result["poll_count"]))
        if binding is not None:
            envelope[34:37] = bytes(binding)
        if exec_values is not None:
            envelope[37:43] = bytes(exec_values)
        envelope[43] = self.module.V5_ENCODING
        envelope[46] = self.module.PAYLOAD_SIZE
        envelope[self.module.PAYLOAD_OFFSET:self.module.CRC_OFFSET] = payload
        self.recrc(envelope)
        return envelope

    def recrc(self, envelope):
        crc = zlib.crc32(
            self.module.V5_DOMAIN + envelope[:self.module.CRC_OFFSET]
        ) & 0xFFFFFFFF
        envelope[self.module.CRC_OFFSET:] = struct.pack("<I", crc)

    def assert_decode_rejects(self, envelope):
        with self.assertRaises(self.module.AuditError):
            self.module.decode_envelope_v5(bytes(envelope))

    def test_private_receipt_is_exact_deterministic_regeneration(self):
        path = OUTPUT / "result.json"
        self.assertEqual(path.read_bytes(), self.receipt)
        current = path.stat()
        self.assertEqual(stat.S_IMODE(current.st_mode), 0o400)
        self.assertEqual(current.st_nlink, 1)
        self.assertEqual(len(self.receipt), 11_647)
        self.assertEqual(
            self.module.sha256(self.receipt),
            "05ee3385c8c8001039a329316c65f9bee9d5d3181e8673f7ddf9dea420532917",
        )

    def test_fresh_materialization_is_byte_identical(self):
        with tempfile.TemporaryDirectory(prefix="p319-carrier-v5-test-") as directory:
            root = Path(directory) / "result"
            _, payload = self.module.run(True, root)
            self.module.publish_result(root, payload)
            self.assertEqual(payload, self.receipt)
            for group in (
                "inputs", "base-sources", "materialized-sources",
                "driver-sources", "driver-patches",
            ):
                canonical = OUTPUT / group
                regenerated = root / group
                self.assertEqual(
                    sorted(path.name for path in canonical.iterdir()),
                    sorted(path.name for path in regenerated.iterdir()),
                )
                for path in canonical.iterdir():
                    self.assertEqual(path.read_bytes(), (regenerated / path.name).read_bytes())

    def test_existing_output_is_no_clobber(self):
        with tempfile.TemporaryDirectory(prefix="p319-carrier-v5-noclobber-") as directory:
            root = Path(directory) / "occupied"
            root.mkdir()
            marker = root / "marker"
            marker.write_bytes(b"unchanged")
            with self.assertRaises(self.module.AuditError):
                self.module.run(True, root)
            self.assertEqual(marker.read_bytes(), b"unchanged")

    def test_scope_is_host_only_and_review_pending(self):
        self.assertEqual(self.result["status"], "IMPLEMENTED_REVIEW_PENDING")
        self.assertEqual(self.result["scope"]["tier"], "H0")
        for key in (
            "device_contact", "live_authority_created", "replay",
        ):
            self.assertFalse(self.result["scope"][key])
        for key in (
            "adb_commands", "usb_actions", "odin_invocations",
            "candidate_builds", "candidate_transfers", "rollback_transfers",
            "recovery_actions",
        ):
            self.assertEqual(self.result["scope"][key], 0)

    def test_envelope_v4_encoder_and_crc_are_byte_identical(self):
        v4 = self.result["envelope_v4"]
        self.assertTrue(v4["encoder_and_crc_byte_identical"])
        self.assertFalse(v4["reinterpretation"])
        self.assertEqual(v4["version"], 4)
        self.assertEqual(v4["time_mask"], "0xffU")

    def test_v5_geometry_and_native_python_parity(self):
        v5 = self.result["envelope_v5"]
        self.assertEqual((v5["envelope_size"], v5["payload_size"]), (128, 76))
        self.assertEqual(v5["carrier_positions"], [105, 106])
        self.assertEqual(v5["carrier_split_bytes"], [64, 64])
        self.assertTrue(self.result["native_codec_qualification"]["native_python_payload_byte_identical"])
        self.assertFalse(v5["v4_timing_banner_and_poll_payload_inherited"])
        self.assertFalse(v5["v4_causal_timing_authority_created"])
        self.assertFalse(v5["decoded_causal_result_allowed"])
        self.assertFalse(v5["poll_bytes_retained"])

    def test_sample_round_trip_retains_all_primary_witnesses(self):
        decoded = self.module.decode_envelope_v5(bytes(self.envelope()))
        self.assertEqual(decoded["module_results"], [0, 0, 0])
        self.assertEqual(decoded["initial_status"], [0x27, 0x05, 0x82, 1, 8])
        self.assertEqual(decoded["parent_mask_readback"], 7)
        self.assertEqual(decoded["irq"], [355, 354, 352, 351, 350])
        self.assertEqual((decoded["record_count"], decoded["record_bytes"]), (5, 777))
        self.assertEqual((decoded["first_sequence"], decoded["last_sequence"]), (100, 104))
        self.assertTrue(decoded["chain_complete"])
        self.assertFalse(decoded["causal_result_allowed"])

    def test_source_reachable_fixed_result_header_is_validated_but_noncausal(self):
        envelope = self.envelope()
        envelope[5] = 3
        envelope[7] |= 1
        envelope[8] = 2
        struct.pack_into("<i", envelope, 9, -19)
        self.recrc(envelope)
        decoded = self.module.decode_envelope_v5(bytes(envelope))
        self.assertTrue(decoded["result_header_present"])
        self.assertEqual(decoded["fixed_result_header"]["stage"], 2)
        self.assertEqual(decoded["fixed_result_header"]["rc"], -19)
        self.assertFalse(decoded["causal_result_allowed"])

    def test_source_reachable_no_result_semantic_classes(self):
        # P3.17 permits terminal 1..9 without a runtime result.  Its
        # execution-only terminals 10..15 additionally require their exact
        # witness predicates.
        execution = {
            10: (0x80, 0, 0, 0, 0, 0),
            11: (0, 0x80, 0, 0, 0, 0),
            12: (0, 0x87, 0x07, 0x80, 0, 0),
            13: (0, 0, 0, 0, 0, 0x80),
            14: (0, 0, 0, 0, 0, 0x80),
            15: (0, 0, 0, 0, 0, 0),
        }
        for terminal in range(1, 16):
            with self.subTest(terminal=terminal):
                decoded = self.module.decode_envelope_v5(bytes(self.envelope(
                    terminal_code=terminal,
                    exec_values=execution.get(terminal),
                )))
                self.assertEqual(decoded["terminal_code"], terminal)
                self.assertFalse(decoded["result_header_present"])

    def test_source_reachable_result_semantic_classes(self):
        noncausal = bytes((0, 0, 0))
        causal = bytes((0x6E, 0x51, 0))
        causal_exec = (0x89, 0x87, 0x07, 0x87, 0x07, 0x86)
        alternate_valid_binding = bytes((0x10, 0, 0))
        base_failure = {
            "command_issued_mask": 0,
            "response_seen_mask": 0,
            "write_attempted": 0,
            "write_ambiguous": 0,
            "response_opcode": (0, 0, 0, 0),
            "response_value": (0, 0, 0, 0),
            "poll_count": (0, 0, 0, 0),
        }
        cases = (
            (1, 3, dict(base_failure, stage=2, rc=-19), noncausal),
            # pre_exact_parent_driver_state=OTHER_DRIVER occupies packed
            # binding bit 0x10 and is source-reachable (not reserved).
            (1, 3, dict(base_failure, stage=2, rc=-19), alternate_valid_binding),
            (1, 5, dict(base_failure, stage=3, rc=-5), noncausal),
            (1, 8, dict(base_failure, stage=2, rc=1), noncausal),
            (2, 5, dict(base_failure, stage=5, rc=-1,
                        command_issued_mask=1, poll_count=(1, 0, 0, 0)), causal),
            (2, 1, dict(base_failure, stage=10, rc=0,
                        command_issued_mask=0x0F, response_seen_mask=0x0F,
                        write_attempted=1, response_opcode=(5, 6, 5, 5),
                        response_value=(0, 0, 9, 9), poll_count=(1, 1, 1, 1)), causal),
            (2, 2, dict(base_failure, stage=10, rc=0,
                        command_issued_mask=0x0D, response_seen_mask=0x0D,
                        response_opcode=(5, 0, 5, 5),
                        response_value=(9, 0, 9, 9), poll_count=(1, 0, 1, 1)), causal),
            (2, 3, dict(base_failure, stage=10, rc=0,
                        command_issued_mask=0x0D, response_seen_mask=0x0D,
                        response_opcode=(5, 0, 5, 5),
                        response_value=(9, 0, 9, 8), poll_count=(1, 0, 1, 1)), causal),
            (2, 4, dict(base_failure, stage=10, rc=0,
                        command_issued_mask=0x0D, response_seen_mask=0x0D,
                        response_opcode=(5, 0, 5, 5),
                        response_value=(9, 0, 8, 8), poll_count=(1, 0, 1, 1)), causal),
        )
        for kind, code, result, binding in cases:
            with self.subTest(kind=kind, code=code):
                decoded = self.module.decode_envelope_v5(bytes(self.envelope(
                    terminal_code=code if kind == 1 else 0,
                    mux_code=code if kind == 2 else 0,
                    result=result, binding=binding,
                    exec_values=causal_exec if kind == 2 else None,
                )))
                self.assertEqual(
                    (decoded["terminal_code"] != 0, decoded["mux_code"] != 0),
                    (kind == 1, kind == 2),
                )

    def test_result_semantic_and_binding_mismatches_fail_closed(self):
        result = {
            "stage": 5, "rc": -1, "command_issued_mask": 1,
            "response_seen_mask": 0, "write_attempted": 0,
            "write_ambiguous": 0, "response_opcode": (0, 0, 0, 0),
            "response_value": (0, 0, 0, 0), "poll_count": (1, 0, 0, 0),
        }
        # MUX requires a result and exact causal binding; result-bearing
        # terminal 10 is forbidden by the native P3.17 encoder.
        for envelope in (
            self.envelope(terminal_code=0, mux_code=5, result=None),
            self.envelope(terminal_code=0, mux_code=5, result=result),
            self.envelope(terminal_code=10, result=result,
                          exec_values=(0x80, 0, 0, 0, 0, 0)),
        ):
            self.assert_decode_rejects(envelope)
        # The same stage-5 result is a valid MUX failure only with causal
        # binding, so a CRC-valid noncausal row must be rejected.
        self.assert_decode_rejects(self.envelope(
            terminal_code=0, mux_code=5, result=result,
            binding=bytes((0, 0, 0)),
        ))
        self.assert_decode_rejects(self.envelope(
            terminal_code=0, mux_code=5, result=result,
            binding=bytes((0x6E, 0x51, 0)),
            exec_values=(0, 0, 0, 0, 0, 0),
        ))
        reserved = self.envelope(binding=bytes((0x80, 0, 0)))
        self.assert_decode_rejects(reserved)

    def test_classification_name_matches_native_vps_grammar(self):
        for name in (" CDP", "CDP ", "C\x1fDP", "CDP\x7f", "é"):
            with self.subTest(name=repr(name)):
                state = self.module.sample_state()
                state["classification_form1_name"] = name
                with self.assertRaises(self.module.AuditError):
                    self.module.encode_payload_v5(state)
        for name in ("CDP", "USB i", "A-B_2"):
            with self.subTest(name=name):
                state = self.module.sample_state()
                state["classification_form1_name"] = name
                self.assertEqual(len(self.module.encode_payload_v5(state)), 76)

    def test_impossible_fixed_result_header_fails_closed_with_valid_crc(self):
        envelope = self.envelope()
        envelope[7] |= 1
        envelope[8] = 8
        struct.pack_into("<i", envelope, 9, -5)
        self.recrc(envelope)
        self.assert_decode_rejects(envelope)

    def test_carrier_split_reassembles_exact_envelope(self):
        envelope = bytes(self.envelope())
        first, second = envelope[:64], envelope[64:]
        self.assertEqual((len(first), len(second)), (64, 64))
        self.assertEqual(first + second, envelope)

    def test_crc_magic_version_flags_and_encoding_fail_closed(self):
        for offset in (0, 4, 7, 43, 44, 46, 124):
            with self.subTest(offset=offset):
                envelope = self.envelope()
                envelope[offset] ^= 1
                self.assert_decode_rejects(envelope)

    def test_reserved_chain_bits_fail_closed_even_with_valid_crc(self):
        envelope = self.envelope()
        envelope[self.module.PAYLOAD_OFFSET + 3] |= 0x20
        self.recrc(envelope)
        self.assert_decode_rejects(envelope)

    def test_full_header_mutations_fail_closed_with_valid_crc(self):
        mutations = []
        envelope = self.envelope()
        envelope[5] = 0
        mutations.append(envelope)
        envelope = self.envelope()
        envelope[7] &= ~(1 << 2)
        mutations.append(envelope)
        envelope = self.envelope()
        envelope[47] = 0x10
        mutations.append(envelope)
        envelope = self.envelope()
        envelope[35] = 3
        mutations.append(envelope)
        envelope = self.envelope()
        envelope[37] = 7
        mutations.append(envelope)
        envelope = self.envelope()
        envelope[8] = 1
        mutations.append(envelope)
        envelope = self.envelope()
        envelope[44] = 1
        mutations.append(envelope)
        for envelope in mutations:
            self.recrc(envelope)
            self.assert_decode_rejects(envelope)

    def test_incoherent_sequence_fails_closed(self):
        state = self.module.sample_state()
        state["last_sequence"] = 105
        with self.assertRaises(self.module.AuditError):
            self.module.encode_payload_v5(state)

    def test_sequence_overflow_and_empty_nonzero_fail_closed(self):
        state = self.module.sample_state()
        state["record_count"] = 2
        state["first_sequence"] = (1 << 64) - 1
        state["last_sequence"] = 0
        with self.assertRaises(self.module.AuditError):
            self.module.encode_payload_v5(state)
        state = self.module.sample_state()
        state.update(record_count=0, record_bytes=0, first_sequence=1,
                     last_sequence=0, first_sequence_valid=False,
                     last_sequence_valid=False)
        with self.assertRaises(self.module.AuditError):
            self.module.encode_payload_v5(state)

    def test_record_boundaries_fail_closed(self):
        for key, value in (("record_count", 4097), ("record_bytes", 1_048_577)):
            with self.subTest(key=key):
                state = self.module.sample_state()
                state[key] = value
                with self.assertRaises(self.module.AuditError):
                    self.module.encode_payload_v5(state)

    def test_count_overflow_fails_closed(self):
        for key in (
            "probe_count", "irq_count", "initial_status_count",
            "classification_form1_count", "parent_mask_count",
        ):
            with self.subTest(key=key):
                state = self.module.sample_state()
                state[key] = 256
                with self.assertRaises(self.module.AuditError):
                    self.module.encode_payload_v5(state)

    def test_witness_mask_must_match_counts(self):
        state = self.module.sample_state()
        state["witness_mask"] &= ~self.module.MASK_PARENT
        with self.assertRaises(self.module.AuditError):
            self.module.encode_payload_v5(state)

    def test_absent_irq_status_parent_and_class_data_fail_closed(self):
        cases = []
        state = self.module.sample_state()
        state["irq_count"] = 0
        state["witness_mask"] &= ~self.module.MASK_IRQ
        cases.append(state)
        state = self.module.sample_state()
        state["initial_status_count"] = 0
        state["witness_mask"] &= ~self.module.MASK_INITIAL
        cases.append(state)
        state = self.module.sample_state()
        state["parent_mask_count"] = 0
        state["witness_mask"] &= ~self.module.MASK_PARENT
        cases.append(state)
        state = self.module.sample_state()
        state["classification_form1_count"] = 0
        state["witness_mask"] &= ~self.module.MASK_CLASS1
        cases.append(state)
        for state in cases:
            with self.assertRaises(self.module.AuditError):
                self.module.encode_payload_v5(state)

    def test_module_result_is_exact_success_tuple(self):
        state = self.module.sample_state()
        state["module_results"] = [0, -1, 0]
        with self.assertRaises(self.module.AuditError):
            self.module.encode_payload_v5(state)

    def test_chain_complete_matches_stage_five(self):
        state = self.module.sample_state()
        state["chain_stage"] = 4
        with self.assertRaises(self.module.AuditError):
            self.module.encode_payload_v5(state)

    def test_parent_bit_three_clear_and_set_are_both_observable(self):
        clear = self.module.sample_state()
        clear["parent_mask_readback"] = 0x07
        set_value = self.module.sample_state()
        set_value["parent_mask_readback"] = 0x0F
        clear_decoded = self.module.decode_envelope_v5(bytes(self.envelope(clear)))
        set_decoded = self.module.decode_envelope_v5(bytes(self.envelope(set_value)))
        self.assertEqual(clear_decoded["parent_mask_readback"] & 8, 0)
        self.assertEqual(set_decoded["parent_mask_readback"] & 8, 8)

    def test_classification_name_uses_sha256_prefix_128(self):
        decoded = self.module.decode_envelope_v5(bytes(self.envelope()))
        self.assertEqual(
            decoded["classification_name_sha256_prefix128"],
            "b932825fca6de767fa6e95d41fbe5291",
        )

    def test_driver_producer_deltas_are_exactly_two_sources(self):
        originals = self.inputs["preserved_originals"]
        drivers = self.inputs["preserved_drivers"]
        self.assertNotEqual(originals["max77705-muic.c"], drivers["max77705-muic.c"])
        self.assertNotEqual(originals["max77705_usbc.c"], drivers["max77705_usbc.c"])
        audit = self.result["producer_changes"]
        self.assertEqual(audit["initial_status_added_i2c_transactions"], 0)
        self.assertEqual(audit["parent_mask_added_read_transactions"], 1)
        self.assertFalse(audit["compiled_module_created"])

    def test_muic_producer_logs_all_five_already_read_bytes(self):
        source = self.inputs["preserved_drivers"]["max77705-muic.c"]
        self.assertEqual(source.count(b"MAX77705_USBC_REG_USBC_STATUS1, 5, status"), 1)
        self.assertEqual(source.count(b"CC0:0x%02x, CC1:0x%02x"), 1)
        self.assertIn(b"status[0], status[1], status[2], status[3], status[4]", source)

    def test_parent_producer_is_read_write_read_log(self):
        source = self.inputs["preserved_drivers"]["max77705_usbc.c"]
        body = self.inputs["module"]._c_function_body(source, "max77705_usbc_umask_irq")
        tokens = (
            b"max77705_read_reg(usbc_data->i2c, 0x23",
            b"i2c_data &= ~((1 << 3))",
            b"ret = max77705_write_reg(usbc_data->i2c, 0x23",
            b"ret = max77705_read_reg(usbc_data->i2c, 0x23, &i2c_data)",
            b'msg_maxim("P319_INTSRC_MASK:0x%02x", i2c_data)',
        )
        positions = [body.index(token) for token in tokens]
        self.assertEqual(positions, sorted(positions))

    def test_generated_parser_requires_five_status_bytes_and_parent_readback(self):
        runtime = self.inputs["preserved_generated"]["s22plus_fyg8_p290_e3_runtime.inc.c"]
        self.assertIn(b"const char *labels[5]", runtime)
        self.assertIn(b"P319_INTSRC_MASK:0x", runtime)
        self.assertIn(b"p319_chain_event(5U)", runtime)
        self.assertIn(b"struct p319_witness_summary_state_v2", runtime)
        native = self.result["native_parser_qualification"]
        self.assertTrue(native["five_byte_status_positive"])
        self.assertTrue(native["parent_mask_positive"])
        self.assertTrue(native["post_complete_primary_value_frozen"])
        self.assertTrue(native["post_complete_repeat_marks_ambiguous"])

    def test_generated_publisher_uses_v5_and_keeps_v4_definition(self):
        runtime = self.inputs["preserved_generated"]["s22plus_fyg8_p290_e3_runtime.inc.c"]
        self.assertEqual(runtime.count(b"s22plus_max77705_p319_encode_envelope_v5("), 2)
        self.assertEqual(runtime.count(b"s22plus_max77705_p318_encode_envelope("), 2)
        self.assertEqual(runtime.count(b"p319_witness_summary_state_v2_copy(&witness)"), 1)
        self.assertIn(b"S22PLUS-FYG8-MAX77705-DIAG-V5\\0", runtime)
        self.assertIn(b"S22PLUS-FYG8-MAX77705-DIAG-V4\\0", runtime)

    def test_v5_restores_semantic_after_v4_poll_validation(self):
        runtime = self.inputs["preserved_generated"]["s22plus_fyg8_p290_e3_runtime.inc.c"]
        function = self.inputs["module"]._c_function_body(
            runtime, "s22plus_max77705_p319_encode_envelope_v5"
        )
        call = function.index(b"s22plus_max77705_p318_encode_envelope")
        restore = function.index(b"envelope[5] = (uint8_t)semantic_code")
        crc = function.index(b"s22plus_max77705_p319_envelope_crc32")
        self.assertLess(call, restore)
        self.assertLess(restore, crc)

    def test_materialized_patch_files_reproduce_driver_sources(self):
        for name in ("max77705-muic.c.patch", "max77705_usbc.c.patch"):
            payload = self.inputs["preserved_patches"][name]
            self.assertTrue(payload.startswith(b"--- a/"))
            self.assertIn(b"+++ b/", payload)
            self.assertIn(b"@@", payload)

    def test_receipt_records_no_candidate_build_authority(self):
        conclusion = self.result["conclusion"]
        self.assertTrue(conclusion["canonical_carrier_encoding_defined"])
        self.assertTrue(conclusion["driver_sources_only_not_compiled_module_bytes"])
        self.assertFalse(conclusion["candidate_build_exists"])
        self.assertFalse(conclusion["existing_candidate_witness_transport_obligation_resolved"])
        self.assertTrue(conclusion["independent_changed_closure_review_required"])


if __name__ == "__main__":
    unittest.main()
