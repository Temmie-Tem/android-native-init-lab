from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
EVIDENCE = SCRIPTS / "device_action_f1_evidence_v2.py"


def load_evidence():
    sys.path.insert(0, str(SCRIPTS))
    try:
        spec = importlib.util.spec_from_file_location(
            "device_action_f1_evidence_v2_p335_tested", EVIDENCE
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPTS))


class P335AdapterErrorBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence = load_evidence()
        cls.adapter = cls.evidence.p334_stock_adapter
        cls.carrier = cls.adapter.carrier
        cls.acceptance = dict(cls.adapter.acceptance_fixture())
        cls.acceptance["auth_key"] = dict(
            cls.evidence.P334_AUTH_EXEC_AUTH_KEY_IDENTITY
        )

    @classmethod
    def p334_missing_return_record(cls) -> bytes:
        base = next(
            item
            for item in cls.adapter._modules(cls.adapter._P333)
            if hasattr(item, "_full_fixture")
        )
        payload = base._full_fixture(state="AMBIGUOUS")
        offset = payload.find(cls.carrier.LONG_FAMILY)
        record = bytearray(payload[offset : offset + cls.carrier.LONG_RECORD_SIZE])
        header = bytes(record[: cls.carrier.LONG_HEADER_SIZE])
        slot_offset = cls.carrier.LONG_HEADER_SIZE + cls.carrier.SLOT_SIZE
        record[slot_offset : slot_offset + cls.carrier.SLOT_SIZE] = (
            cls.carrier._encode_slot(  # noqa: SLF001
                header,
                cls.carrier.Slot(
                    1,
                    105,
                    146,
                    cls.carrier.OUTCOME_PROGRESS,
                    0,
                    0,
                ),
            )
        )
        return (
            payload[:offset]
            + bytes(record)
            + payload[offset + cls.carrier.LONG_RECORD_SIZE :]
        )

    def test_p334_missing_generation_and_stage_is_evidence_error(self) -> None:
        payload = self.p334_missing_return_record()
        with self.assertRaises(self.evidence.EvidenceError) as raised:
            self.evidence.classify_e1_latest_stage(payload, self.acceptance)
        self.assertEqual(
            str(raised.exception),
            "P3.34 first-console return record is not exact",
        )
        self.assertIsInstance(
            raised.exception.__cause__, self.adapter.AdapterIdentityError
        )

    def test_mutated_and_foreign_records_keep_the_identity_boundary(self) -> None:
        payload = bytearray(self.p334_missing_return_record())
        payload[0] ^= 1
        with self.assertRaises(self.evidence.EvidenceError):
            self.evidence.classify_e1_latest_stage(bytes(payload), self.acceptance)

        predecessor = self.evidence.p333_stock_adapter
        base = next(
            item
            for item in predecessor._modules(predecessor._P332)
            if hasattr(item, "_full_fixture")
        )
        foreign = base._full_fixture(state="AMBIGUOUS")
        with self.assertRaises(self.evidence.EvidenceError):
            self.evidence.classify_e1_latest_stage(foreign, self.acceptance)

    def test_foreign_value_error_is_not_normalized(self) -> None:
        payload = self.p334_missing_return_record()
        with mock.patch.object(
            self.adapter,
            "classify_observation",
            side_effect=ValueError("foreign parser failure"),
        ):
            with self.assertRaisesRegex(ValueError, "foreign parser failure"):
                self.evidence.classify_e1_latest_stage(payload, self.acceptance)

    def test_predecessor_classification_remains_unchanged(self) -> None:
        predecessor = self.evidence.p333_stock_adapter
        base = next(
            item
            for item in predecessor._modules(predecessor._P332)
            if hasattr(item, "_full_fixture")
        )
        payload = base._full_fixture(state="AMBIGUOUS")
        acceptance = dict(predecessor.acceptance_fixture())
        acceptance["auth_key"] = dict(
            self.evidence.P333_AUTH_EXEC_AUTH_KEY_IDENTITY
        )
        classified = self.evidence.classify_e1_latest_stage(payload, acceptance)
        self.assertEqual(
            classified["classification"],
            "P320_STOCK_WITNESS_AMBIGUOUS_NO_PROOF",
        )
        self.assertFalse(classified["accepted"])


if __name__ == "__main__":
    unittest.main()
