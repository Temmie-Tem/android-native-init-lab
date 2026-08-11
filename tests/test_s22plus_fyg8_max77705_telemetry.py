import copy
from dataclasses import replace
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPT_DIR / "s22plus_fyg8_max77705_telemetry.py"
DECODER = SCRIPT_DIR / "s22plus_fyg8_max77705_telemetry_decoder.py"
ADAPTER_FIXTURE = (
    SCRIPT_DIR / "s22plus_fyg8_max77705_process_v2_adapter_fixture.py"
)


def load_module():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_max77705_telemetry_tested", SCRIPT
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


def load_decoder():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_max77705_telemetry_decoder_tested", DECODER
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


def load_adapter_fixture():
    sys.path.insert(0, str(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "s22plus_fyg8_max77705_process_v2_adapter_fixture_tested",
            ADAPTER_FIXTURE,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(SCRIPT_DIR))


class S22PlusFyg8Max77705TelemetryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.decoder = load_decoder()
        cls.adapter_fixture = load_adapter_fixture()

    def binding(self, **changes):
        m = self.module
        values = {
            "loader_state": m.LOADER_STATES["FINIT_MODULE_RETURNED_SUCCESS"],
            "pre_exact_parent_present": 1,
            "pre_exact_parent_driver_state": m.DRIVER_STATES["UNBOUND"],
            "pre_matching_unbound_parent_count": 1,
            "pre_wrong_address_compatible_parent_count": 0,
            "post_exact_parent_driver_state": m.DRIVER_STATES["DIAGNOSTIC"],
            "post_diagnostic_bound_parent_count": 1,
            "post_exact_adapter_muic_0x25_client_count": 1,
            "post_foreign_0x25_client_count": 0,
        }
        values.update(changes)
        return m.BindingWitness(**values)

    def result(self, *, polls=(b"\x00\x00\x80", b"", b"\x80", b"\x80")):
        write_present = bool(polls[1])
        return self.module.DiagnosticResult(
            stage=10,
            rc=0,
            pmic_valid_mask=3,
            pmic_id=0x15,
            pmic_rev=0x02,
            initial_uic_valid=1,
            initial_uic=0x04,
            command_issued_mask=0x0F if write_present else 0x0D,
            response_seen_mask=0x0F if write_present else 0x0D,
            response_opcode=(0x05, 0x06 if write_present else 0, 0x05, 0x05),
            response_value=(0x3F, 0, 0x09, 0x09),
            poll_bytes=tuple(polls),
            write_attempted=1 if write_present else 0,
            write_ambiguous=0,
        )

    @staticmethod
    def uncompressible_poll():
        return bytes((*range(99), 0x80))

    def eagain_bindings(self):
        m = self.module
        absent = m.DRIVER_STATES["ABSENT"]
        unbound = m.DRIVER_STATES["UNBOUND"]
        other = m.DRIVER_STATES["OTHER_DRIVER"]
        diagnostic = m.DRIVER_STATES["DIAGNOSTIC"]
        success = m.LOADER_STATES["FINIT_MODULE_RETURNED_SUCCESS"]
        return {
            "probe_in_progress": self.binding(
                loader_state=m.LOADER_STATES["FINIT_MODULE_IN_PROGRESS"],
                pre_exact_parent_present=1,
                post_exact_parent_driver_state=unbound,
                post_diagnostic_bound_parent_count=0,
                post_exact_adapter_muic_0x25_client_count=0,
            ),
            "no_matching_parent": self.binding(
                loader_state=success,
                pre_exact_parent_present=0,
                pre_exact_parent_driver_state=absent,
                pre_matching_unbound_parent_count=0,
                pre_wrong_address_compatible_parent_count=0,
                post_exact_parent_driver_state=absent,
                post_diagnostic_bound_parent_count=0,
                post_exact_adapter_muic_0x25_client_count=0,
            ),
            "wrong_address_compatible_parent": self.binding(
                loader_state=success,
                pre_exact_parent_present=0,
                pre_exact_parent_driver_state=absent,
                pre_matching_unbound_parent_count=0,
                pre_wrong_address_compatible_parent_count=1,
                post_exact_parent_driver_state=absent,
                post_diagnostic_bound_parent_count=0,
                post_exact_adapter_muic_0x25_client_count=0,
            ),
            "exact_parent_owned_by_other_driver": self.binding(
                loader_state=success,
                pre_exact_parent_present=1,
                pre_exact_parent_driver_state=other,
                post_exact_parent_driver_state=other,
                post_diagnostic_bound_parent_count=0,
                post_exact_adapter_muic_0x25_client_count=0,
            ),
            "exact_parent_unbound_after_sync_return": self.binding(
                loader_state=success,
                pre_exact_parent_present=1,
                pre_exact_parent_driver_state=unbound,
                post_exact_parent_driver_state=unbound,
                post_diagnostic_bound_parent_count=0,
                post_exact_adapter_muic_0x25_client_count=0,
            ),
            "diagnostic_binding_ready_but_result_eagain": self.binding(
                loader_state=success,
                pre_exact_parent_present=1,
                pre_exact_parent_driver_state=unbound,
                post_exact_parent_driver_state=diagnostic,
                post_diagnostic_bound_parent_count=1,
                post_exact_adapter_muic_0x25_client_count=1,
                post_foreign_0x25_client_count=0,
            ),
        }

    def test_geometry_and_detail_bands(self):
        value = self.module.validate()
        self.assertEqual(value["record_count"], 1)
        self.assertEqual(value["retained_slot_count"], 2)
        self.assertEqual(value["envelope_size"], 128)
        self.assertEqual(value["overflow_poll_summary_size"], 44)
        self.assertEqual(value["overflow_summary_spare_bytes"], 32)
        self.assertTrue(value["post2_poll0_retention_axis"])
        self.assertEqual(value["terminal_bucket_count"], 9)
        self.assertFalse(value["full_lto_required"])

    def test_packbits_round_trip_and_corruption(self):
        m = self.module
        patterns = (
            b"",
            bytes(range(128)),
            b"\x00" * 100 + b"\x80",
            b"abc" * 30 + b"z" * 128,
        )
        for raw in patterns:
            with self.subTest(length=len(raw)):
                encoded = m.packbits_encode(raw)
                self.assertEqual(
                    m.packbits_decode(encoded, expected_size=len(raw)), raw
                )
        with self.assertRaises(m.TelemetryError):
            m.packbits_decode(b"\x82", expected_size=3)

    def test_all_observable_eagain_rows_have_unique_retained_vectors(self):
        m = self.module
        run_id = bytes.fromhex("31603160316031603160316031603160")
        records = {}
        for row, binding in self.eagain_bindings().items():
            envelope = m.encode_envelope(
                binding=binding,
                terminal_bucket=m.eagain_terminal_bucket(row),
            )
            record = m.encode_carrier_record(envelope, run_id=run_id)
            decoded = m.decode_carrier_record(record, run_id=run_id)
            self.assertEqual(decoded["eagain_row"], row)
            self.assertEqual(
                decoded["terminal_bucket"], m.eagain_terminal_bucket(row)
            )
            records[row] = record
        self.assertEqual(len(records), 6)
        self.assertEqual(len(set(records.values())), 6)

    def test_all_terminal_buckets_have_a_carrier_preimage(self):
        m = self.module
        run_id = bytes.fromhex("31613161316131613161316131613161")
        eagain_by_bucket = {}
        for row, binding in self.eagain_bindings().items():
            eagain_by_bucket.setdefault(m.eagain_terminal_bucket(row), binding)
        records = {}
        for bucket in m.TERMINAL_BUCKET_KEYS:
            if bucket == "result_payload_unrepresentable":
                polls = tuple(self.uncompressible_poll() for _ in range(4))
                envelope = m.encode_envelope(
                    binding=self.binding(),
                    mux_class="pre-nonusb-post-stable-usb",
                    result=self.result(polls=polls),
                )
            else:
                envelope = m.encode_envelope(
                    binding=eagain_by_bucket.get(bucket, self.binding()),
                    terminal_bucket=bucket,
                    result=(
                        self.result()
                        if bucket
                        in {
                            "probe_terminal_failure",
                            "matching_parent_identity_rejected",
                        }
                        else None
                    ),
                )
            record = m.encode_carrier_record(envelope, run_id=run_id)
            decoded = m.decode_carrier_record(record, run_id=run_id)
            self.assertEqual(decoded["terminal_bucket"], bucket)
            records[bucket] = record
        self.assertEqual(len(records), 9)
        self.assertEqual(len(set(records.values())), 9)

    def test_all_mux_device_classes_round_trip_losslessly(self):
        m = self.module
        run_id = bytes.fromhex("31623162316231623162316231623162")
        for name in m.MUX_DEVICE_CLASSES:
            with self.subTest(name=name):
                envelope = m.encode_envelope(
                    binding=self.binding(), mux_class=name, result=self.result()
                )
                decoded = m.decode_carrier_record(
                    m.encode_carrier_record(envelope, run_id=run_id),
                    run_id=run_id,
                )
                self.assertEqual(decoded["mux_class"], name)
                self.assertTrue(decoded["poll_lossless"])
                self.assertTrue(decoded["causal_result_allowed"])
                self.assertEqual(
                    tuple(decoded["result"]["poll_bytes"]),
                    self.result().poll_bytes,
                )

    def test_uncompressible_poll_bytes_fail_closed(self):
        m = self.module
        polls = tuple(self.uncompressible_poll() for _ in range(4))
        envelope = m.encode_envelope(
            binding=self.binding(),
            mux_class="pre-nonusb-post-stable-usb",
            result=self.result(polls=polls),
        )
        decoded = m.decode_envelope(envelope)
        self.assertEqual(
            decoded["terminal_bucket"], "result_payload_unrepresentable"
        )
        self.assertTrue(decoded["payload_overflow"])
        self.assertFalse(decoded["poll_lossless"])
        self.assertFalse(decoded["causal_result_allowed"])
        self.assertIsNone(decoded["mux_class"])
        self.assertEqual(decoded["poll_encoded_size"], 44)
        self.assertEqual(decoded["result"]["poll_or"], (0xFF,) * 4)
        self.assertEqual(decoded["result"]["poll0"], (0,) * 4)
        self.assertEqual(decoded["result"]["poll_nonzero_count"], (99,) * 4)

    def test_post2_control1_and_retention_poll0_form_four_explicit_rows(self):
        m = self.module
        cases = (
            (0x09, 0x80, "POST1_USB_POST2_USB_WITHOUT_RETENTION_DETECTION_LATCH"),
            (0x09, 0x88, "POST1_USB_POST2_USB_WITH_RETENTION_DETECTION_LATCH"),
            (0x3F, 0x82, "POST1_USB_POST2_NONUSB_WITH_RETENTION_DETECTION_LATCH"),
            (0x3F, 0x80, "POST1_USB_POST2_NONUSB_WITHOUT_RETENTION_DETECTION_LATCH"),
        )
        for post2, poll0, expected in cases:
            with self.subTest(post2=post2, poll0=poll0):
                result = replace(
                    self.result(),
                    response_value=(0x3F, 0, 0x09, post2),
                    poll_bytes=(b"\x80", b"", b"\x80", bytes((poll0,))),
                )
                decoded = m.decode_envelope(
                    m.encode_envelope(
                        binding=self.binding(),
                        mux_class="pre-nonusb-post-stable-usb",
                        result=result,
                    )
                )
                retention = decoded["result"]["post2_retention"]
                self.assertEqual(retention["classification"], expected)
                self.assertTrue(retention["event_presence_only"])
                self.assertFalse(retention["physical_switch_movement_proven"])
                self.assertFalse(retention["causal_trigger_proven"])

    def test_poll_summary_invariants_match_module_control_flow(self):
        m = self.module
        response_without_apcmd = replace(
            self.result(), poll_bytes=(b"\x01", b"", b"\x80", b"\x80")
        )
        with self.assertRaisesRegex(m.TelemetryError, "lacks APCmdResI"):
            m.encode_envelope(
                binding=self.binding(),
                mux_class="pre-nonusb-post-stable-usb",
                result=response_without_apcmd,
            )

        apcmd_without_response = replace(
            self.result(),
            stage=m.STAGE_WRITE,
            rc=-5,
            command_issued_mask=0x03,
            response_seen_mask=0x01,
            write_attempted=1,
            write_ambiguous=1,
            response_opcode=(0x05, 0, 0, 0),
            response_value=(0x3F, 0, 0, 0),
            poll_bytes=(b"\x80", b"\x80", b"", b""),
        )
        m.encode_envelope(
            binding=self.binding(),
            terminal_bucket="probe_terminal_failure",
            result=apcmd_without_response,
        )

        timeout = replace(
            self.result(),
            stage=m.STAGE_PRE,
            rc=m.RC_ETIMEDOUT,
            command_issued_mask=0x01,
            response_seen_mask=0,
            response_opcode=(0, 0, 0, 0),
            response_value=(0, 0, 0, 0),
            poll_bytes=(b"\x01" * 100, b"", b"", b""),
        )
        m.encode_envelope(
            binding=self.binding(),
            terminal_bucket="probe_terminal_failure",
            result=timeout,
        )
        with self.assertRaisesRegex(m.TelemetryError, "timed-out slot"):
            m.encode_envelope(
                binding=self.binding(),
                terminal_bucket="probe_terminal_failure",
                result=replace(timeout, poll_bytes=(b"\x01" * 99 + b"\x80", b"", b"", b"")),
            )

    def test_overflow_summary_semantic_tamper_fails_after_valid_crc(self):
        m = self.module
        polls = tuple(self.uncompressible_poll() for _ in range(4))
        envelope = bytearray(
            m.encode_envelope(
                binding=self.binding(),
                mux_class="pre-nonusb-post-stable-usb",
                result=self.result(polls=polls),
            )
        )
        envelope[m.PAYLOAD_AREA_OFFSET + 40] = 0
        crc = m.binascii.crc32(m.CRC_DOMAIN + envelope[: m.CRC_OFFSET]) & 0xFFFFFFFF
        m.struct.pack_into("<I", envelope, m.CRC_OFFSET, crc)
        with self.assertRaisesRegex(m.TelemetryError, "OR and nonzero count"):
            m.decode_envelope(bytes(envelope))

    def test_overflow_fixed_result_tamper_fails_after_valid_crc(self):
        m = self.module
        polls = tuple(self.uncompressible_poll() for _ in range(4))
        envelope = bytearray(
            m.encode_envelope(
                binding=self.binding(),
                mux_class="pre-nonusb-post-stable-usb",
                result=self.result(polls=polls),
            )
        )
        envelope[8] = 0
        crc = m.binascii.crc32(m.CRC_DOMAIN + envelope[: m.CRC_OFFSET]) & 0xFFFFFFFF
        m.struct.pack_into("<I", envelope, m.CRC_OFFSET, crc)
        with self.assertRaisesRegex(m.TelemetryError, "source-reachable"):
            m.decode_envelope(bytes(envelope))

    def test_overflow_poll_count_above_source_bound_fails_after_valid_crc(self):
        m = self.module
        polls = tuple(self.uncompressible_poll() for _ in range(4))
        envelope = bytearray(
            m.encode_envelope(
                binding=self.binding(),
                mux_class="pre-nonusb-post-stable-usb",
                result=self.result(polls=polls),
            )
        )
        envelope[30] = 101
        m.struct.pack_into("<H", envelope, 44, 401)
        crc = m.binascii.crc32(m.CRC_DOMAIN + envelope[: m.CRC_OFFSET]) & 0xFFFFFFFF
        m.struct.pack_into("<I", envelope, m.CRC_OFFSET, crc)
        with self.assertRaisesRegex(m.TelemetryError, "source bound"):
            m.decode_envelope(bytes(envelope))

    def test_overflow_requires_a_result_even_with_valid_crc(self):
        m = self.module
        polls = tuple(self.uncompressible_poll() for _ in range(4))
        envelope = bytearray(
            m.encode_envelope(
                binding=self.binding(),
                mux_class="pre-nonusb-post-stable-usb",
                result=self.result(polls=polls),
            )
        )
        envelope[7] &= ~m.FLAG_RESULT_PRESENT
        envelope[8:34] = bytes(26)
        m.struct.pack_into("<H", envelope, 44, 0)
        crc = m.binascii.crc32(m.CRC_DOMAIN + envelope[: m.CRC_OFFSET]) & 0xFFFFFFFF
        m.struct.pack_into("<I", envelope, m.CRC_OFFSET, crc)
        with self.assertRaisesRegex(m.TelemetryError, "overflow envelope"):
            m.decode_envelope(bytes(envelope))

    def test_result_absent_envelope_rejects_hidden_diagnostic_bytes(self):
        m = self.module
        envelope = bytearray(
            m.encode_envelope(
                binding=self.binding(),
                terminal_bucket="late_finit_module_failure",
            )
        )
        envelope[8] = m.STAGE_PRE
        crc = m.binascii.crc32(m.CRC_DOMAIN + envelope[: m.CRC_OFFSET]) & 0xFFFFFFFF
        m.struct.pack_into("<I", envelope, m.CRC_OFFSET, crc)
        with self.assertRaisesRegex(m.TelemetryError, "result-absent"):
            m.decode_envelope(bytes(envelope))

    def test_claim_busy_has_empty_decoder_preimage(self):
        m = self.module
        self.assertNotIn(
            "claim_busy_after_sync_return",
            m.surface.DIAG_EAGAIN_OBSERVABLE_ROWS,
        )
        self.assertNotIn(
            "claim_busy_after_sync_return",
            m.TERMINAL_CODE_BY_KEY,
        )
        with self.assertRaises(m.TelemetryError):
            m.eagain_terminal_bucket("claim_busy_after_sync_return")
        with self.assertRaises(m.TelemetryError):
            m.encode_envelope(
                binding=self.binding(),
                terminal_bucket="claim_busy_after_sync_return",
            )

    def test_crc_and_detail_cross_checks_fail_closed(self):
        m = self.module
        run_id = bytes.fromhex("31633163316331633163316331633163")
        envelope = m.encode_envelope(
            binding=self.binding(),
            mux_class="pre-usb-post-stable-usb",
            result=self.result(),
        )
        corrupted = bytearray(envelope)
        corrupted[20] ^= 1
        with self.assertRaisesRegex(m.TelemetryError, "CRC"):
            m.decode_envelope(bytes(corrupted))
        record = bytearray(m.encode_carrier_record(envelope, run_id=run_id))
        decoded = m.carrier.decode_record(
            bytes(record),
            expected_profile=m.fixed_spec.PROFILE,
            expected_run_id=run_id,
        )
        active = decoded["active"]
        self.assertEqual(active["detail"], m.MUX_DETAIL_BY_NAME["pre-usb-post-stable-usb"])

        second_generation = m.fixed_spec.SUMMARY_ORDINAL + 1
        slots = {slot["generation"]: slot for slot in decoded["valid_slots"]}
        second = slots[second_generation]
        changed = m.carrier.Slot(
            second["slot_id"],
            second["generation"],
            second["stage"],
            second["outcome"],
            second["item_index"],
            m.MUX_DETAIL_BY_NAME["post-visible-reversion"],
            second["payload_kind"],
            second["payload"],
        )
        header = bytes(record[: m.carrier.LONG_HEADER_SIZE])
        encoded = m.carrier._encode_slot(header, changed)  # noqa: SLF001
        start = m.carrier.LONG_HEADER_SIZE + second["slot_id"] * m.carrier.SLOT_SIZE
        record[start : start + m.carrier.SLOT_SIZE] = encoded
        with self.assertRaisesRegex(m.TelemetryError, "detail and envelope"):
            m.decode_carrier_record(bytes(record), run_id=run_id)

    def test_decoder_is_json_safe_and_accepts_one_causal_result(self):
        m = self.module
        decoder = self.decoder
        run_id = bytes.fromhex("31643164316431643164316431643164")
        envelope = m.encode_envelope(
            binding=self.binding(),
            mux_class="pre-nonusb-post-stable-usb",
            result=self.result(),
        )
        record = m.encode_carrier_record(envelope, run_id=run_id)
        decoded = decoder.decode_record(
            record,
            expected_profile=decoder.PROFILE,
            expected_run_id=run_id,
        )
        persisted = json.loads(json.dumps(decoded, sort_keys=True, allow_nan=False))
        self.assertEqual(
            persisted["max77705"]["mux_class"],
            "pre-nonusb-post-stable-usb",
        )
        classified = decoder.classify_observation(
            record,
            expected_profile=decoder.PROFILE,
            expected_run_id=run_id,
        )
        self.assertEqual(classified["classification"], "MAX77705_DIAGNOSTIC_RESULT")
        self.assertTrue(classified["accepted"])
        self.assertEqual(classified["telemetry_count"], 1)
        self.assertEqual(classified["contradiction_count"], 0)

    def test_decoder_preserves_no_proof_overflow(self):
        m = self.module
        decoder = self.decoder
        run_id = bytes.fromhex("31653165316531653165316531653165")
        polls = tuple(self.uncompressible_poll() for _ in range(4))
        envelope = m.encode_envelope(
            binding=self.binding(),
            mux_class="pre-nonusb-post-stable-usb",
            result=self.result(polls=polls),
        )
        classified = decoder.classify_observation(
            m.encode_carrier_record(envelope, run_id=run_id),
            expected_profile=decoder.PROFILE,
            expected_run_id=run_id,
        )
        self.assertEqual(
            classified["classification"],
            "NO_PROOF_OBSERVER_DIAGNOSTIC_PAYLOAD_OVERFLOW",
        )
        self.assertFalse(classified["accepted"])
        self.assertEqual(classified["telemetry_count"], 0)
        self.assertEqual(classified["contradiction_count"], 1)

    def test_decoder_authority_validation(self):
        value = self.decoder.validate()
        self.assertEqual(value["decoder_id"], self.decoder.DECODER_ID)
        self.assertEqual(value["policy_id"], self.decoder.POLICY_ID)
        self.assertTrue(value["initialized_record_json_safe"])
        self.assertTrue(value["verified"])

    def test_real_process_v2_adapter_covers_both_assertion_directions(self):
        value = self.adapter_fixture.audit()
        self.assertEqual(value["observable_eagain_rows"], 6)
        self.assertEqual(value["terminal_bucket_preimages"], 9)
        self.assertEqual(value["mux_class_preimages"], 5)
        self.assertEqual(value["post2_retention_matrix_rows"], 4)
        self.assertTrue(value["overflow_summary_round_trip"])
        self.assertTrue(value["claim_busy_decoder_preimage_empty"])
        self.assertTrue(value["unknown_overlay_rejected"])
        self.assertTrue(value["real_process_v2_adapter_round_trip"])
        self.assertTrue(value["persistence_round_trip"])
        self.assertTrue(value["verified"])


if __name__ == "__main__":
    unittest.main()
