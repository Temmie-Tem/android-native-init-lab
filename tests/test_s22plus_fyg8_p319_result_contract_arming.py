from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import struct
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_stock_process_v2_adapter.py"
)


def load_adapter():
    spec = importlib.util.spec_from_file_location("p319_result_contract_adapter", ADAPTER)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load P3.19 stock adapter")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    previous = list(sys.path)
    sys.path.insert(0, str(ADAPTER.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = previous
    return module


def carrier_envelope(adapter, raw: bytes) -> bytes:
    carrier = adapter.model
    offset = len(raw) - carrier.LONG_RECORD_SIZE
    record = raw[offset:]
    pieces = []
    body_size = carrier.SLOT_SIZE - 4
    for slot_id in (0, 1):
        slot_offset = carrier.LONG_HEADER_SIZE + slot_id * carrier.SLOT_SIZE
        body = carrier.SLOT_BODY_STRUCT.unpack(record[slot_offset:slot_offset + body_size])
        pieces.append(body[-1][:64])
    return b"".join(pieces)


def rewrite_carrier_envelope(adapter, raw: bytes, mutate) -> bytes:
    carrier = adapter.model
    offset = len(raw) - carrier.LONG_RECORD_SIZE
    record = bytearray(raw[offset:])
    body_size = carrier.SLOT_SIZE - 4
    envelope = bytearray(carrier_envelope(adapter, raw))
    mutate(envelope)
    struct.pack_into("<I", envelope, adapter.CRC_OFFSET, adapter._crc(bytes(envelope)))
    for slot_id in (0, 1):
        slot_offset = carrier.LONG_HEADER_SIZE + slot_id * carrier.SLOT_SIZE
        body = list(carrier.SLOT_BODY_STRUCT.unpack(record[slot_offset:slot_offset + body_size]))
        body[-1] = bytes(envelope[slot_id * 64:(slot_id + 1) * 64])
        encoded = carrier.SLOT_BODY_STRUCT.pack(*body)
        record[slot_offset:slot_offset + body_size] = encoded
        struct.pack_into(
            "<I", record, slot_offset + body_size,
            carrier._slot_crc(bytes(record[:carrier.LONG_HEADER_SIZE]), slot_id, encoded),
        )
    return raw[:offset] + bytes(record) + raw[offset + carrier.LONG_RECORD_SIZE:]


class P319ResultContractArmingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.adapter = load_adapter()
        cls.receipt = cls.adapter.audit_result_contract_arming()

    def test_admitted_terminals_are_derived_from_every_actual_encoder_state(self):
        states = {name for _detail, name in self.adapter.DETAILS.items()}
        admitted = {item["state"] for item in self.receipt["admitted_terminals"]}
        self.assertEqual(admitted, states)
        self.assertEqual(self.receipt["admitted_terminal_count"], len(states))
        self.assertEqual(
            {item["proof_class"] for item in self.receipt["admitted_terminals"]},
            {
                "NONCAUSAL_SUCCESS_PATH",
                "NO_PROOF_OBSERVER",
                "NO_PROOF_EXPERIMENT_PRECONDITION",
            },
        )
        self.assertEqual(
            self.receipt["enumeration_source"],
            "bound P3.19 C publisher selector -> exact C stock encoder -> 128-byte envelope -> real Carrier -> classify_observation",
        )
        self.assertTrue(self.receipt["unsynthesizable_or_undecodable_excluded"])
        self.assertTrue(self.receipt["publisher_reachable_states_only"])
        self.assertTrue(self.receipt["publisher_reachability_verified"])
        self.assertTrue(self.receipt["encoder_rejected_checked_mismatches"])
        self.assertTrue(self.receipt["publisher_selector_proves_unreachable"])
        unreachable = self.receipt["publisher_unreachable_direct_combinations"]
        self.assertEqual(
            unreachable["INCOMPLETE_PLUS_AMBIGUOUS"]["publisher_selected_state"], 2
        )
        self.assertEqual(
            unreachable["COMPLETE_PLUS_AMBIGUOUS"]["publisher_selected_state"], 2
        )
        self.assertTrue(
            unreachable["INCOMPLETE_PLUS_AMBIGUOUS"][
                "direct_encoder_accepts_terminal_incomplete"
            ]
        )
        self.assertTrue(
            unreachable["INCOMPLETE_PLUS_AMBIGUOUS"][
                "selected_encoder_accepts_terminal_ambiguous"
            ]
        )
        self.assertTrue(
            unreachable["COMPLETE_PLUS_AMBIGUOUS"][
                "direct_encoder_accepts_terminal_complete"
            ]
        )
        compiler = self.receipt["compiler_identity"]
        self.assertEqual(
            compiler["realpath"], self.adapter.c_arming.PINNED_COMPILER_REALPATH
        )
        self.assertEqual(compiler["size"], self.adapter.c_arming.PINNED_COMPILER_SIZE)
        self.assertEqual(compiler["sha256"], self.adapter.c_arming.PINNED_COMPILER_SHA256)
        self.assertTrue(compiler["version"].strip())
        self.assertEqual(
            compiler["version_sha256"],
            self.adapter.c_arming.PINNED_COMPILER_VERSION_SHA256,
        )

    def test_alternate_cc_is_rejected_before_native_arming(self):
        with tempfile.TemporaryDirectory(prefix="p319-alternate-cc-") as directory:
            alternate = Path(directory) / "alternate-cc"
            alternate.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            alternate.chmod(0o755)
            with mock.patch.dict(os.environ, {"CC": str(alternate)}):
                with self.assertRaises(self.adapter.c_arming.ArmingError):
                    self.adapter.c_arming._compiler_identity(os.environ["CC"])

    def test_each_terminal_uses_the_exact_retained_carrier_shape(self):
        actual = self.adapter.c_arming.execute_actual_stock_encoder()
        for encoded in actual["states"]:
            state = self.adapter.DETAILS[encoded["terminal_detail"]]
            raw = self.adapter._full_c_fixture(
                encoded["envelope"], detail=encoded["terminal_detail"]
            )
            self.assertEqual(len(raw), self.adapter.RAW_SIZE)
            decoded = self.adapter.classify_observation(raw)
            self.assertEqual(decoded["accepted"], state == "COMPLETE")
            self.assertEqual(self.adapter.proof_class(decoded), self.adapter.PROOF_CLASS_BY_STATE[state])
            self.assertEqual(decoded["proof_class"], self.adapter.PROOF_CLASS_BY_STATE[state])

    def test_no_proof_buckets_are_not_merged(self):
        items = {item["state"]: item for item in self.receipt["admitted_terminals"]}
        self.assertEqual(items["INCOMPLETE"]["proof_class"], "NO_PROOF_EXPERIMENT_PRECONDITION")
        self.assertEqual(items["AMBIGUOUS"]["proof_class"], "NO_PROOF_OBSERVER")
        self.assertNotEqual(items["INCOMPLETE"]["proof_class"], items["AMBIGUOUS"]["proof_class"])

    def test_incomplete_nonzero_required_module_result_is_experiment_precondition(self):
        actual = self.adapter.c_arming.execute_actual_stock_encoder()["states"][1]
        raw = self.adapter._full_c_fixture(
            actual["envelope"], detail=actual["terminal_detail"]
        )
        mutated = rewrite_carrier_envelope(
            self.adapter,
            raw,
            lambda envelope: struct.pack_into(
                "<h", envelope, self.adapter.PAYLOAD_OFFSET + 4, -19
            ),
        )
        decoded = self.adapter.classify_observation(mutated)
        stock = decoded["records"][0]["p319_stock"]["stock"]
        self.assertEqual(stock["module_results"], [-19, 0, 0])
        self.assertEqual(
            decoded["proof_class"], "NO_PROOF_EXPERIMENT_PRECONDITION"
        )
        self.assertEqual(
            self.adapter.proof_class(decoded), "NO_PROOF_EXPERIMENT_PRECONDITION"
        )

    def test_incomplete_zero_modules_requires_gap_free_record_accounting(self):
        actual = self.adapter.c_arming.execute_actual_stock_encoder()["states"][1]
        raw = self.adapter._full_c_fixture(
            actual["envelope"], detail=actual["terminal_detail"]
        )
        decoded = self.adapter.classify_observation(raw)
        stock = decoded["records"][0]["p319_stock"]["stock"]
        self.assertTrue(stock["module_results_all_zero"])
        self.assertEqual(
            (stock["record_count"], stock["record_bytes"],
             stock["first_sequence"], stock["last_sequence"]),
            (1, 1, 1, 1),
        )
        self.assertEqual(
            decoded["proof_class"], "NO_PROOF_EXPERIMENT_PRECONDITION"
        )

        corrupt = dict(decoded)
        corrupt["records"] = [dict(decoded["records"][0])]
        corrupt["records"][0]["p319_stock"] = dict(decoded["records"][0]["p319_stock"])
        corrupt["records"][0]["p319_stock"]["stock"] = dict(stock)
        corrupt["records"][0]["p319_stock"]["stock"]["record_count"] = 2
        self.assertEqual(
            self.adapter._proof_class_for_value(corrupt), "NO_PROOF_OBSERVER"
        )
        with self.assertRaises(self.adapter.DecodeError):
            self.adapter.proof_class(corrupt)

    def test_missing_required_module_evidence_is_observer_no_proof(self):
        actual = self.adapter.c_arming.execute_actual_stock_encoder()["states"][1]
        raw = self.adapter._full_c_fixture(
            actual["envelope"], detail=actual["terminal_detail"]
        )
        missing = rewrite_carrier_envelope(
            self.adapter,
            raw,
            lambda envelope: envelope.__setitem__(
                self.adapter.PAYLOAD_OFFSET + 2,
                envelope[self.adapter.PAYLOAD_OFFSET + 2] & ~(1 << 3),
            ),
        )
        decoded = self.adapter.classify_observation(missing)
        self.assertFalse(decoded["accepted"])
        self.assertEqual(decoded["proof_class"], "NO_PROOF_OBSERVER")

    def test_incomplete_without_zero_module_results_is_observer_no_proof(self):
        actual = self.adapter.c_arming.execute_actual_stock_encoder()["states"][1]
        raw = self.adapter._full_c_fixture(
            actual["envelope"], detail=actual["terminal_detail"]
        )
        decoded = self.adapter.classify_observation(raw)
        decoded["records"][0]["p319_stock"]["stock"]["module_results_all_zero"] = False
        self.assertEqual(
            self.adapter._proof_class_for_value(decoded), "NO_PROOF_OBSERVER"
        )
        with self.assertRaises(self.adapter.DecodeError):
            self.adapter.proof_class(decoded)

    def test_hostile_detail_state_and_proof_class_swaps_fail(self):
        hostile = self.receipt["hostile_tests"]
        self.assertEqual(
            hostile,
            {
                "detail_state_swap_rejected": True,
                "carrier_state_swap_rejected": True,
                "proof_class_swap_rejected": True,
            },
        )
        complete = self.adapter.classify_observation(self.adapter._full_fixture(state="COMPLETE"))
        mutated_state = self.adapter._mutate_envelope_state(
            self.adapter._full_fixture(state="COMPLETE"), "INCOMPLETE"
        )
        self.assertEqual(carrier_envelope(self.adapter, mutated_state)[:5], b"MXD5\x05")
        mutated_state_result = self.adapter.classify_observation(mutated_state)
        self.assertFalse(mutated_state_result["accepted"])
        self.assertEqual(mutated_state_result["proof_class"], "NO_PROOF_OBSERVER")
        with self.assertRaises(self.adapter.DecodeError):
            self.adapter.proof_class(complete, expected="NO_PROOF_OBSERVER")
        mutated = dict(complete)
        mutated["proof_class"] = "NO_PROOF_OBSERVER"
        with self.assertRaises(self.adapter.DecodeError):
            self.adapter.proof_class(mutated)

    def test_unsupported_state_and_detail_fail_closed(self):
        with self.assertRaises(self.adapter.DecodeError):
            self.adapter.encode_fixture(state="UNSUPPORTED")
        actual = self.adapter.c_arming.execute_actual_stock_encoder()["states"][0]
        raw = self.adapter._full_c_fixture(actual["envelope"], detail=0xFFFF)
        decoded = self.adapter.classify_observation(raw)
        self.assertFalse(decoded["accepted"])
        self.assertEqual(decoded["proof_class"], "NO_PROOF_OBSERVER")

    def test_arming_receipt_is_h0_only_and_binds_c_encoder_test_path(self):
        self.assertEqual(self.receipt["verdict"], "PASS_P319_RESULT_CONTRACT_ARMING_H0")
        self.assertFalse(self.receipt["causal_result_allowed"])
        self.assertFalse(self.receipt["candidate_success"])
        self.assertFalse(self.receipt["device_contact"])
        self.assertEqual(
            self.receipt["c_encoder_fixture_path"]["encoder_symbol"],
            "s22plus_max77705_p319_stock_encode",
        )
        self.assertEqual(
            self.receipt["c_encoder_fixture_path"]["sha256"],
            "0a12a9c0f148d58009ebc378b667733b5913d46ebf6466dff3f37bbb850c51a9",
        )


if __name__ == "__main__":
    unittest.main()
