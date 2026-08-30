from __future__ import annotations

import binascii
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/analysis/"
    "s22plus_fyg8_p320_observer_contract.py"
)
SPEC = importlib.util.spec_from_file_location("s22plus_fyg8_p320_observer_contract", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
contract = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = contract
SPEC.loader.exec_module(contract)


def record_hex(record: bytes) -> str:
    return binascii.hexlify(record).decode("ascii")


class P320ObserverContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        compiler = shutil.which("gcc")
        if compiler is None:
            raise AssertionError("host C compiler is unavailable")
        cls.tempdir = tempfile.TemporaryDirectory(prefix="p320-observer-contract-")
        source = Path(cls.tempdir.name) / "fixture.c"
        source.write_bytes(contract.host_fixture_source())
        cls.fixture = Path(cls.tempdir.name) / "fixture"
        completed = subprocess.run(
            [
                compiler,
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-O2",
                "-o",
                str(cls.fixture),
                str(source),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError((completed.stdout + completed.stderr).decode())
        lifecycle_source = Path(cls.tempdir.name) / "lifecycle-fixture.c"
        lifecycle_source.write_bytes(contract.host_lifecycle_fixture_source())
        cls.lifecycle_fixture = Path(cls.tempdir.name) / "lifecycle-fixture"
        completed = subprocess.run(
            [
                compiler,
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-O2",
                "-o",
                str(cls.lifecycle_fixture),
                str(lifecycle_source),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError((completed.stdout + completed.stderr).decode())
        runtime_source = Path(cls.tempdir.name) / "runtime-fixture.c"
        runtime_source.write_bytes(contract.host_runtime_fixture_source())
        cls.runtime_fixture = Path(cls.tempdir.name) / "runtime-fixture"
        completed = subprocess.run(
            [
                compiler,
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-O2",
                "-o",
                str(cls.runtime_fixture),
                str(runtime_source),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError((completed.stdout + completed.stderr).decode())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tempdir.cleanup()

    @staticmethod
    def _base_payload(*, complete: bool = True) -> bytes:
        payload = bytearray(contract.STOCK_PAYLOAD_SIZE)
        payload[0] = contract.P319_PAYLOAD_ABI
        payload[3] = 0x0C if complete else 0x04
        payload[56:59] = bytes((3, 1, 1))
        return bytes(payload)

    @classmethod
    def run_c(cls, *tokens: str | bytes) -> list[str]:
        args = [
            token if isinstance(token, str) else record_hex(token)
            for token in tokens
        ]
        completed = subprocess.run(
            [str(cls.fixture), *args],
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

    @classmethod
    def run_runtime_c(cls, *tokens: str) -> list[str]:
        completed = subprocess.run(
            [str(cls.runtime_fixture), *tokens],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"runtime C fixture failed ({completed.returncode}): "
                f"{completed.stdout}{completed.stderr}"
            )
        return completed.stdout.strip().split()

    @classmethod
    def run_lifecycle_c(cls, *tokens: str) -> list[str]:
        completed = subprocess.run(
            [str(cls.lifecycle_fixture), *tokens],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"lifecycle C fixture failed ({completed.returncode}): "
                f"{completed.stdout}{completed.stderr}"
            )
        return completed.stdout.strip().split()

    def test_exact_target_lineage_binds_runtime_envelope_and_wiring(self) -> None:
        result = contract.bind_exact_sources()
        self.assertEqual(result["target"], contract.TARGET)
        self.assertEqual(result["runtime_abi"], 2)
        self.assertEqual(result["raw_checkpoint_source"], "/proc/last_kmsg")
        self.assertTrue(result["exact_runtime_bound"])
        self.assertTrue(result["envelope_source_bound"])
        self.assertTrue(result["wiring_source_bound"])
        self.assertEqual(
            result["sources"]["p319_runtime"]["sha256"],
            "0a12a9c0f148d58009ebc378b667733b5913d46ebf6466dff3f37bbb850c51a9",
        )

    def test_dictionary_extension_and_c_flag_reach_witness_as_human_message_only(self) -> None:
        record = (
            b"7,160,424069,c,future=1,caller=T42;plain human message\n"
            b" SUBSYSTEM=acpi\n DEVICE=+acpi:PNP0A03:00\n"
        )
        state = contract.ObserverState()
        state.set_active_module(72)
        outcome = state.observe(record)
        self.assertTrue(outcome.accepted)
        self.assertEqual(outcome.human_message, b"plain human message")
        self.assertIsNone(state.first_error)
        self.assertEqual(state.receipt(), bytes(contract.OBSERVER_RECEIPT_SIZE))

        fields = self.run_c("module=72", record)
        self.assertEqual(fields[0:3], ["1", "0", "0"])
        self.assertEqual(fields[8], "000000000000000000000000000000")
        self.assertEqual(bytes.fromhex(fields[10]), b"plain human message")

    def test_each_failure_kind_is_consumed_and_preserves_first_receipt(self) -> None:
        cases = (
            (
                contract.ObserverErrorKind.ENVELOPE,
                (b"",),
                (),
            ),
            (
                contract.ObserverErrorKind.HEADER,
                (b"not-a-kmsg-record\n",),
                (),
            ),
            (
                contract.ObserverErrorKind.BODY,
                (b"6,10,25,-;message\nnot-a-dictionary\n",),
                (),
            ),
            (
                contract.ObserverErrorKind.SEQUENCE,
                (
                    b"6,10,25,-;first\n",
                    b"6,12,25,-;gap\n",
                ),
                (),
            ),
            (
                contract.ObserverErrorKind.WITNESS,
                (b"6,10,25,c;witness-fails\n",),
                ("witness=-9",),
            ),
        )
        for kind, records, controls in cases:
            with self.subTest(kind=kind.name):
                state = contract.ObserverState()
                state.set_active_module(72)
                for record in records:
                    outcome = state.observe(
                        record,
                        witness_return_code=-9 if kind == contract.ObserverErrorKind.WITNESS else 0,
                    )
                self.assertFalse(outcome.accepted)
                self.assertEqual(state.first_error.kind, kind)
                self.assertTrue(state.chain_ambiguous)
                expected_receipt = state.receipt()
                fields = self.run_c(*controls, "module=72", *records)
                self.assertEqual(fields[0:3][1:], ["1", "1"])
                self.assertEqual(bytes.fromhex(fields[8]), expected_receipt)
                self.assertEqual(bytes.fromhex(fields[9])[0], contract.P320_PAYLOAD_ABI)
                self.assertEqual(
                    bytes.fromhex(fields[9])[3] & (1 << 4),
                    1 << 4,
                )
                self.assertEqual(
                    contract.terminal_detail_for_payload(
                        contract.encode_stock_payload_v4(
                            self._base_payload(), state.first_error
                        )
                    ),
                    contract.STOCK_DETAIL_AMBIGUOUS,
                )

    def test_first_error_is_one_shot_and_later_errors_do_not_replace_it(self) -> None:
        first_record = b"6,10,25,c;first\n"
        second_record = b"6,11,25,-;message\nnot-a-dictionary\n"
        state = contract.ObserverState()
        state.set_active_module(71)
        state.observe(first_record, witness_return_code=-1)
        first = state.first_error
        state.observe(second_record)
        self.assertIs(state.first_error, first)
        self.assertEqual(first.kind, contract.ObserverErrorKind.WITNESS)
        fields = self.run_c("module=71", "witness=-1", first_record, second_record)
        self.assertEqual(bytes.fromhex(fields[8]), state.receipt())
        self.assertEqual(int(fields[0]), 1)

    def test_body_failure_keeps_known_header_sequence_and_flag(self) -> None:
        record = b"6,10,25,c;missing-terminal-newline"
        state = contract.ObserverState()
        state.set_active_module(72)
        outcome = state.observe(record)
        self.assertFalse(outcome.accepted)
        self.assertEqual(outcome.error.kind, contract.ObserverErrorKind.BODY)
        self.assertEqual(outcome.error.sequence, 10)
        self.assertEqual(outcome.error.flag, "c")
        fields = self.run_c("module=72", record)
        self.assertEqual(bytes.fromhex(fields[8]), state.receipt())

    def test_observer_source_has_no_early_failure_publisher(self) -> None:
        self.assertNotIn(b"p290_fail_next", contract.P320_C_OBSERVER_SOURCE.encode())
        self.assertNotIn(b"p290_fail_next", contract.P320_C_RECORD_SOURCE.encode())
        composed = contract.compose_runtime()
        self.assertIn(b"(void)p320_observer_record_continue(record, length);", composed)
        self.assertIn(b"p320_observer_note_successful_module(", composed)
        module_calls = []
        cursor = 0
        while True:
            found = composed.find(b"p320_observer_note_successful_module(", cursor)
            if found < 0:
                break
            module_calls.append(found)
            cursor = found + 1
        self.assertEqual(len(module_calls), 2)
        module_call = module_calls[-1]
        module_assignment = composed.index(
            b"g_p319_witness.active_module_index = (uint32_t)index;"
        )
        self.assertLess(module_call, module_assignment)
        self.assertIn(
            b"witness->malformed_count != 0U && !p320_observer_error_latched() ||",
            composed,
        )
        self.assertIn(b"p320_observer_chain_ambiguous()", composed)
        self.assertIn(
            b"#define S22PLUS_MAX77705_P319_STOCK_PAYLOAD_ABI 4U",
            composed,
        )

    def test_wrapper_composition_replaces_observer_failures_but_keeps_load_fail_fast(self) -> None:
        wrapper = contract.compose_wrapper()
        self.assertIn(
            b"static long p319_after_module_load(size_t index, long load_rc)",
            wrapper,
        )
        self.assertIn(b"if (load_rc != 0L) return load_rc;", wrapper)
        self.assertIn(b"p320_observer_transport_failure()", wrapper)
        self.assertIn(
            b"(void)p320_observer_set_active_module(0U, 0);", wrapper
        )
        self.assertNotIn(
            b"return P319_DETAIL_WITNESS_BOUNDARY;",
            contract.P320_C_AFTER_MODULE_SOURCE.encode(),
        )

    def test_record_and_budget_boundaries_latch_without_parsing_or_legacy_detail(self) -> None:
        normal = b"6,10,25,-;x\n"
        cases = {
            "empty": contract.ObserverError(
                contract.ObserverErrorKind.ENVELOPE,
                None,
                72,
                0,
                None,
                0,
            ),
            "oversize": contract.ObserverError(
                contract.ObserverErrorKind.ENVELOPE,
                None,
                72,
                contract.MAX_RECORD_BYTES + 1,
                None,
                0,
            ),
            "drain-record": contract.make_observer_error(
                contract.ObserverErrorKind.ENVELOPE,
                record=normal,
                active_module_index=72,
            ),
            "drain-bytes": contract.make_observer_error(
                contract.ObserverErrorKind.ENVELOPE,
                record=normal,
                active_module_index=72,
            ),
            "total-record": contract.make_observer_error(
                contract.ObserverErrorKind.ENVELOPE,
                record=normal,
                active_module_index=72,
            ),
            "total-bytes": contract.make_observer_error(
                contract.ObserverErrorKind.ENVELOPE,
                record=normal,
                active_module_index=72,
            ),
            "underflow-drain": contract.make_observer_error(
                contract.ObserverErrorKind.ENVELOPE,
                record=normal,
                active_module_index=72,
            ),
            "underflow-total": contract.make_observer_error(
                contract.ObserverErrorKind.ENVELOPE,
                record=normal,
                active_module_index=72,
            ),
        }
        self.assertNotIn(
            b"return P319_DETAIL_WITNESS_BOUNDARY;",
            contract.P320_C_RECORD_SOURCE.encode(),
        )
        for mode, expected in cases.items():
            with self.subTest(mode=mode):
                fields = self.run_runtime_c("module-note=72", mode)
                self.assertEqual(fields[0], "0")
                self.assertEqual(fields[1], "0")
                self.assertEqual(fields[2], "0" if mode in {"empty", "oversize"} else "1")
                self.assertEqual(
                    contract.decode_error_receipt(bytes.fromhex(fields[4])),
                    expected,
                )

    def test_compiled_runtime_module_seam_binds_error_to_active_row(self) -> None:
        fields = self.run_runtime_c("module-note=72", "witness=-7", "normal")
        self.assertEqual(fields[0:4], ["0", "1", "0", "0"])
        error = contract.decode_error_receipt(bytes.fromhex(fields[4]))
        self.assertEqual(error.kind, contract.ObserverErrorKind.WITNESS)
        self.assertEqual(error.active_module_index, 72)
        self.assertEqual(error.sequence, 10)

    def test_budget_boundary_stops_current_and_future_flood_drains(self) -> None:
        for mode in ("flood-record", "flood-bytes"):
            with self.subTest(mode=mode):
                fields = self.run_runtime_c(mode)
                self.assertEqual(fields[0], "0")
                self.assertEqual(
                    fields[1],
                    "2" if mode == "flood-record" else "1",
                )
                self.assertEqual(fields[2], "1")
                self.assertEqual(
                    int(fields[3]),
                    3 if mode == "flood-record" else 2,
                )
                error = contract.decode_error_receipt(bytes.fromhex(fields[4]))
                self.assertEqual(error.kind, contract.ObserverErrorKind.ENVELOPE)
                self.assertIsNone(error.active_module_index)
                self.assertEqual(error.record_length, len(b"6,10,25,-;x\n"))
                self.assertTrue(
                    contract.decode_error_receipt(bytes.fromhex(fields[4]))
                )

    def test_full_kmsg_lifecycle_fail_soft_uses_transport_kind_and_finalizes(self) -> None:
        failure_modes = (
            ("begin-open-fail", 0),
            ("begin-lseek-fail", 0),
            ("drain-read-fail", 1),
            ("drain-ring-fail", 1),
            ("drain-count-fail", 0),
            ("finish-close-fail", 1),
        )
        for mode, expected_reads in failure_modes:
            with self.subTest(mode=mode):
                fields = self.run_lifecycle_c(mode)
                self.assertEqual(fields[0], "0")
                self.assertEqual(int(fields[1]), expected_reads)
                self.assertEqual(fields[2:4], ["1", "1"])
                self.assertEqual(fields[4], "-1")
                error = contract.decode_error_receipt(bytes.fromhex(fields[5]))
                self.assertIsNotNone(error)
                assert error is not None
                self.assertEqual(error.kind, contract.ObserverErrorKind.TRANSPORT)
                self.assertIsNone(error.active_module_index)
                self.assertEqual(error.record_length, 0)
                self.assertEqual(error.record_checksum, 0)
        clean = self.run_lifecycle_c("clean")
        self.assertEqual(clean[:5], ["0", "1", "0", "1", "-1"])
        self.assertIsNone(contract.decode_error_receipt(bytes.fromhex(clean[5])))

    def test_module_wrapper_preserves_load_fail_fast_and_clears_row_after_drain(self) -> None:
        row_failure = self.run_lifecycle_c("module-drain-fail")
        self.assertEqual(row_failure[:5], ["0", "1", "1", "1", "-1"])
        error = contract.decode_error_receipt(bytes.fromhex(row_failure[5]))
        self.assertIsNotNone(error)
        assert error is not None
        self.assertEqual(error.kind, contract.ObserverErrorKind.TRANSPORT)
        self.assertEqual(error.active_module_index, 72)

        final_poll_failure = self.run_lifecycle_c("module-final-poll-fail")
        self.assertEqual(final_poll_failure[:5], ["0", "2", "1", "1", "-1"])
        error = contract.decode_error_receipt(bytes.fromhex(final_poll_failure[5]))
        self.assertIsNotNone(error)
        assert error is not None
        self.assertEqual(error.kind, contract.ObserverErrorKind.TRANSPORT)
        self.assertIsNone(error.active_module_index)

        eud_failure = self.run_lifecycle_c("module-eud-fail")
        self.assertEqual(eud_failure[:5], ["0", "1", "1", "1", "-1"])
        error = contract.decode_error_receipt(bytes.fromhex(eud_failure[5]))
        self.assertIsNotNone(error)
        assert error is not None
        self.assertEqual(error.kind, contract.ObserverErrorKind.TRANSPORT)
        self.assertIsNone(error.active_module_index)

        load_failure = self.run_lifecycle_c("module-load-fail")
        self.assertEqual(load_failure[:5], ["-9", "0", "0", "0", "-1"])
        self.assertIsNone(contract.decode_error_receipt(bytes.fromhex(load_failure[5])))

    def test_abi3_is_rejected_abi4_clean_and_ambiguous_are_accepted(self) -> None:
        base = self._base_payload()
        clean = contract.encode_stock_payload_v4(base)
        clean_summary = contract.validate_stock_payload_v4(clean)
        self.assertEqual(clean_summary["state"], "COMPLETE")
        self.assertEqual(
            clean_summary["terminal_detail"], contract.STOCK_DETAIL_COMPLETE
        )
        self.assertTrue(clean_summary["observer_receipt_zero"])

        with self.assertRaises(contract.ContractError):
            contract.validate_stock_payload_v4(base)

        error = contract.make_observer_error(
            contract.ObserverErrorKind.WITNESS,
            record=b"6,10,25,c;failure\n",
            flag="c",
            active_module_index=72,
            sequence=10,
        )
        ambiguous = contract.encode_stock_payload_v4(base, error)
        summary = contract.validate_stock_payload_v4(ambiguous)
        self.assertEqual(summary["state"], "AMBIGUOUS")
        self.assertEqual(
            summary["terminal_detail"], contract.STOCK_DETAIL_AMBIGUOUS
        )
        self.assertEqual(summary["observer_receipt"], error)
        self.assertEqual(
            contract.decode_error_receipt(ambiguous[61:76]),
            error,
        )

    def test_python_and_c_receipts_and_payloads_are_byte_identical(self) -> None:
        record = b"6,10,25,c;failure\n"
        error = contract.make_observer_error(
            contract.ObserverErrorKind.WITNESS,
            record=record,
            flag="c",
            active_module_index=72,
            sequence=10,
        )
        expected_payload = contract.encode_stock_payload_v4(
            self._base_payload(), error
        )
        fields = self.run_c("module=72", "witness=-7", record)
        self.assertEqual(bytes.fromhex(fields[8]), contract.encode_error_receipt(error))
        self.assertEqual(bytes.fromhex(fields[9]), expected_payload)
        self.assertEqual(int(fields[4]), 7)
        self.assertEqual(fields[5], str(ord("c")))
        self.assertEqual(fields[6], "72")
        self.assertEqual(int(fields[7]), len(record))

    def test_receipt_hostile_shapes_are_rejected(self) -> None:
        clean = bytes(contract.OBSERVER_RECEIPT_SIZE)
        self.assertIsNone(contract.decode_error_receipt(clean))
        for mutated in (
            bytes((0, 1)) + bytes(13),
            bytes((5, 0x80, 0, 0xFF)) + bytes(11),
            bytes((5, 0, ord("x"), 0xFF)) + bytes(11),
            bytes((5, 0, 0, 0)) + bytes(11),
        ):
            with self.assertRaises(contract.ReceiptError):
                contract.decode_error_receipt(mutated)

    def test_record_checksum_is_small_and_deterministic(self) -> None:
        record = b"6,10,25,-;x\n"
        self.assertEqual(contract.fnv1a8(record), contract.fnv1a8(record))
        error = contract.make_observer_error(
            contract.ObserverErrorKind.BODY,
            record=record,
        )
        self.assertEqual(
            contract.decode_error_receipt(contract.encode_error_receipt(error)),
            error,
        )


if __name__ == "__main__":
    unittest.main()
