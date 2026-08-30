from __future__ import annotations

import binascii
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p320_stock_process_v2_adapter.py"
)


def load_adapter():
    spec = importlib.util.spec_from_file_location(
        "p320_stock_process_v2_adapter_test", ADAPTER
    )
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load P3.20 stock adapter")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class P320StockProcessV2AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.adapter = load_adapter()
        cls.observer = cls.adapter._observer()
        compiler = shutil.which("gcc")
        if compiler is None:
            raise AssertionError("host C compiler is unavailable")
        cls.tempdir = tempfile.TemporaryDirectory(prefix="p320-stock-adapter-")
        source = Path(cls.tempdir.name) / "observer_fixture.c"
        source.write_bytes(cls.observer.host_fixture_source())
        cls.c_fixture = Path(cls.tempdir.name) / "observer_fixture"
        completed = subprocess.run(
            [compiler, "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wno-unused-function", "-O2", "-o", str(cls.c_fixture), str(source)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError((completed.stdout + completed.stderr).decode())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    def full(self, *, state: str = "COMPLETE", observer_error=None) -> bytes:
        if observer_error is None:
            return self.adapter._full_fixture(state=state)
        return self.adapter._full_fixture(state=state, observer_error=observer_error)

    def test_lineage_binds_exact_p320_observer_and_p310_parent_sources(self):
        bound = self.adapter.bind_exact_sources()
        self.assertEqual(bound["overlay_contract_id"], self.adapter.OVERLAY_CONTRACT_ID)
        self.assertNotEqual(
            bound["overlay_contract_id"], self.adapter.P319_OVERLAY_CONTRACT_ID
        )
        self.assertEqual(
            bound["parent_source_contract_id"],
            "s22plus-fyg8-p310-carrier-v2-hsphy-attribution-v1",
        )
        self.assertEqual(bound["run_id"], self.adapter.P320_STOCK_RUN_ID.hex())
        self.assertEqual(
            bound["predecessor_run_id_rejected"],
            self.adapter.P319_STOCK_RUN_ID.hex(),
        )
        self.assertTrue(bound["exact_p310_carrier_model_bound"])
        self.assertTrue(bound["exact_p308_telemetry_spec_bound"])
        self.assertTrue(bound["whole_observer_hash_pinned"])
        self.assertEqual(bound["observer_contract_base_commit"], "b37d630098")
        self.assertEqual(bound["observer_contract_commit"], "b37d630098")
        observer_file = self.adapter.P320_OBSERVER_SOURCE.read_bytes()
        self.assertEqual(
            bound["sources"]["p320_observer_contract"],
            self.adapter.P320_OBSERVER_SOURCE_IDENTITY,
        )
        self.assertEqual(bound["observer_public_payload_layout"]["payload_abi"], 4)
        self.assertEqual(
            bound["observer_public_payload_layout"]["predecessor_payload_abi_rejected"],
            3,
        )
        self.assertEqual(
            set(bound["sources"]),
            {"p320_observer_contract", "p310_carrier_model", "p308_telemetry_spec"},
        )
        self.assertEqual(
            bound["sources"]["p310_carrier_model"], self.adapter.P310_MODEL_IDENTITY
        )
        self.assertEqual(
            bound["sources"]["p308_telemetry_spec"], self.adapter.P308_SPEC_IDENTITY
        )

    def test_distinct_contract_rejects_p319_overlay_or_abi3_identity(self):
        contract = self.adapter.acceptance_fixture()
        value = {
            "userspace_overlay_contract_id": self.adapter.OVERLAY_CONTRACT_ID,
            "decoder": self.adapter.DECODER_ID,
            "policy_id": self.adapter.POLICY_ID,
            "profile": self.adapter.PROFILE,
            "source_contract_id": self.adapter.PARENT_SOURCE_CONTRACT_ID,
            "observer_contract_id": self.adapter.OBSERVER_CONTRACT_ID,
            "payload_abi": 4,
            "observer_receipt_size": 15,
            "causal_result_allowed": False,
            "candidate_success": False,
        }
        self.assertEqual(self.adapter.validate_contract(value), value)
        self.assertEqual(contract["userspace_overlay_contract_id"], self.adapter.OVERLAY_CONTRACT_ID)
        self.assertEqual(self.adapter.validate_acceptance_item(contract), contract)
        for mutation in (
            {**value, "userspace_overlay_contract_id": self.adapter.P319_OVERLAY_CONTRACT_ID},
            {**value, "payload_abi": 3},
            {**value, "payload_abi": True},
            {**value, "causal_result_allowed": 0},
        ):
            with self.assertRaises(self.adapter.ContractError):
                self.adapter.validate_contract(mutation)
        bad_acceptance = dict(contract)
        bad_acceptance["userspace_overlay_contract_id"] = self.adapter.P319_OVERLAY_CONTRACT_ID
        with self.assertRaises(self.adapter.ContractError):
            self.adapter.validate_acceptance_item(bad_acceptance)

    def test_clean_complete_and_incomplete_have_zero_receipt(self):
        for state, accepted, proof in (
            ("COMPLETE", True, "NONCAUSAL_SUCCESS_PATH"),
            ("INCOMPLETE", False, "NO_PROOF_EXPERIMENT_PRECONDITION"),
        ):
            with self.subTest(state=state):
                value = self.adapter.classify_observation(self.full(state=state))
                stock = value["records"][0]["p320_stock"]["stock"]
                self.assertIs(value["accepted"], accepted)
                self.assertEqual(value["proof_class"], proof)
                self.assertIsNone(stock["observer_receipt"])
                self.assertEqual(stock["observer_receipt_bytes"]["size"], 15)
                self.assertIs(value["causal_result_allowed"], False)
                self.assertIs(value["candidate_success"], False)

    def test_clean_ambiguous_and_observer_error_ambiguous_are_no_proof(self):
        clean = self.adapter.classify_observation(
            self.adapter._full_fixture(state="AMBIGUOUS", observer_error=False)
        )
        clean_stock = clean["records"][0]["p320_stock"]["stock"]
        self.assertEqual(clean["proof_class"], "NO_PROOF_OBSERVER")
        self.assertIsNone(clean_stock["observer_receipt"])

        observed = self.adapter.classify_observation(self.full(state="AMBIGUOUS"))
        stock = observed["records"][0]["p320_stock"]["stock"]
        self.assertEqual(observed["proof_class"], "NO_PROOF_OBSERVER")
        self.assertIs(observed["accepted"], False)
        self.assertIsInstance(stock["observer_receipt"], dict)
        self.assertEqual(stock["observer_receipt"]["kind"], "WITNESS")
        for field in (
            "causal_result_allowed", "candidate_success",
            "mux_result_claimable", "host_silent_claimable",
        ):
            self.assertIs(observed[field], False)

    def test_abi3_payload_and_legacy_detail_are_rejected(self):
        with self.assertRaises(self.adapter.DecodeError):
            self.adapter._decode_payload_v4(
                self.adapter._base_payload(state="COMPLETE"),
                detail=self.adapter.STOCK_DETAIL_COMPLETE,
            )
        legacy = self.adapter._mutate_terminal_detail(
            self.full(state="COMPLETE"), 0x6020
        )
        value = self.adapter.classify_observation(legacy)
        self.assertIs(value["accepted"], False)
        self.assertEqual(value["proof_class"], "NO_PROOF_OBSERVER")
        self.assertIs(value["integrity_issue"], True)

    def test_p319_run_id_is_rejected_by_the_p320_outer_carrier_binding(self):
        payload = self.adapter._observer().encode_stock_payload_v4(
            self.adapter._base_payload(state="COMPLETE")
        )
        foreign = self.adapter._carrier_record_from_envelope(
            self.adapter._envelope_from_payload(payload),
            detail=self.adapter.STOCK_DETAIL_COMPLETE,
            run_id=self.adapter.P319_STOCK_RUN_ID,
        )
        with self.assertRaises(self.adapter.DecodeError):
            self.adapter.decode_record(foreign)
        with self.assertRaises(self.adapter.DecodeError):
            self.adapter.classify_observation(
                bytes(self.adapter.RAW_SIZE - len(foreign)) + foreign,
                expected_run_id=self.adapter.P319_STOCK_RUN_ID,
            )

    def test_receipt_reserved_bits_and_typed_fields_are_fail_closed(self):
        observer = self.adapter._observer()
        error = self.adapter.observer_error_fixture()
        receipt = observer.encode_error_receipt(error)
        decoded = self.adapter.decode_error_receipt(receipt)
        self.assertEqual(decoded.as_dict(), error.as_dict())
        mutations = (
            bytes((receipt[0], receipt[1] | 0x80)) + receipt[2:],
            bytes((receipt[0], receipt[1] | 0x04, ord("x"))) + receipt[3:],
            bytes((receipt[0], receipt[1] | 0x02, receipt[2], 0xFF)) + receipt[4:],
            bytes((receipt[0], receipt[1] & ~0x01)) + receipt[2:],
        )
        for mutated in mutations:
            with self.subTest(receipt=mutated.hex()):
                with self.assertRaises(self.adapter.DecodeError):
                    self.adapter.decode_error_receipt(mutated)
        with self.assertRaises((self.adapter.DecodeError, observer.ReceiptError)):
            observer.encode_error_receipt({"kind": "WITNESS", "record_length": True})

    def test_error_kind_validation_follows_current_observer_enum(self):
        observer = self.adapter._observer()
        for kind in observer.ObserverErrorKind:
            if kind.name == "NONE":
                continue
            with self.subTest(kind=kind.name):
                error = observer.make_observer_error(
                    kind,
                    record=b"6,10,25,c;observer-error\n",
                    flag="c",
                    active_module_index=72,
                    sequence=10,
                )
                receipt = observer.encode_error_receipt(error)
                self.assertEqual(
                    self.adapter.decode_error_receipt(receipt).as_dict(),
                    error.as_dict(),
                )

    def test_carrier_crc_and_slot_corruption_do_not_become_success(self):
        raw = self.full(state="COMPLETE")
        header_bad = bytearray(raw)
        header_bad[-self.adapter.carrier.LONG_RECORD_SIZE] ^= 1
        slot_bad = bytearray(raw)
        slot_bad[-1] ^= 1
        for mutated, integrity in (
            (bytes(header_bad), False),
            (bytes(slot_bad), True),
        ):
            with self.subTest(integrity=integrity):
                value = self.adapter.classify_observation(mutated)
                self.assertIs(value["accepted"], False)
                self.assertEqual(value["proof_class"], "NO_PROOF_OBSERVER")
                self.assertIs(value["integrity_issue"], integrity)

    def test_bool_integer_substitution_cannot_change_the_proof_class(self):
        value = self.adapter.classify_observation(self.full(state="COMPLETE"))
        changed = copy.deepcopy(value)
        changed["accepted"] = 1
        self.assertEqual(
            self.adapter._proof_class_for_value(changed), "NO_PROOF_OBSERVER"
        )
        changed = copy.deepcopy(value)
        changed["records"][0]["p320_stock"]["stock"]["chain_complete"] = 1
        self.assertEqual(
            self.adapter._proof_class_for_value(changed), "NO_PROOF_OBSERVER"
        )

    def test_python_and_c_observer_receipts_feed_the_same_carrier_decoder(self):
        observer = self.adapter._observer()
        record = b"6,10,25,c;observer-failure\n"
        fields = self.run_c("module=72", "witness=-7", record)
        c_receipt = bytes.fromhex(fields[8])
        c_payload = bytes.fromhex(fields[9])
        state = observer.ObserverState()
        state.set_active_module(72)
        state.observe(record, witness_return_code=-7)
        expected_receipt = state.receipt()
        self.assertEqual(c_receipt, expected_receipt)
        self.assertEqual(c_payload[0], self.adapter.P320_PAYLOAD_ABI)
        self.assertEqual(c_payload[61:], c_receipt)

        error_payload = observer.encode_stock_payload_v4(
            self.adapter._base_payload(state="COMPLETE"), state.first_error
        )
        full = self.adapter._full_c_fixture(
            error_payload, detail=self.adapter.STOCK_DETAIL_AMBIGUOUS
        )
        decoded = self.adapter.classify_observation(full)
        stock = decoded["records"][0]["p320_stock"]["stock"]
        self.assertEqual(stock["observer_receipt"]["record_checksum"], c_receipt[14])
        self.assertEqual(decoded["proof_class"], "NO_PROOF_OBSERVER")

    def test_audit_receipt_is_json_safe_and_non_authorizing(self):
        value = self.adapter.audit()
        self.assertEqual(value["schema"], self.adapter.SCHEMA)
        self.assertEqual(value["verdict"], "PASS_P320_STOCK_PROCESS_V2_ADAPTER_H0")
        self.assertTrue(value["verified"])
        self.assertTrue(value["p319_payload_abi_rejected"])
        self.assertTrue(value["observer_error_ambiguous_no_proof"])
        self.assertIs(value["causal_result_allowed"], False)
        self.assertIs(value["candidate_success"], False)
        json.dumps(value, sort_keys=True, allow_nan=False)

    def run_c(self, *tokens: str | bytes) -> list[str]:
        args = [
            token if isinstance(token, str) else binascii.hexlify(token).decode("ascii")
            for token in tokens
        ]
        completed = subprocess.run(
            [str(self.c_fixture), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"C fixture failed ({completed.returncode}): "
                f"{completed.stdout}{completed.stderr}"
            )
        return completed.stdout.strip().split()


if __name__ == "__main__":
    unittest.main()
