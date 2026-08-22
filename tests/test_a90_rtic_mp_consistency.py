"""Synthetic and optional private-artifact tests for the A90 RTIC validator."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/a90_rtic_mp_consistency.py"
STOCK = ROOT / "workspace/private/outputs/a90-stock-rebuild-1007-20260821/stock-carrier/kernel"
REBUILT = ROOT / "workspace/private/outputs/a90-stock-rebuild-1007-20260821/kernel-rebuilt-1007"

spec = importlib.util.spec_from_file_location("a90_rtic_mp_consistency", SCRIPT)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


def _pad4(value: bytes) -> bytes:
    return value + b"\0" * ((-len(value)) & 3)


def _fdt(properties: list[tuple[str, bytes]]) -> bytes:
    strings = bytearray()
    name_offsets: dict[str, int] = {}
    for name, _value in properties:
        if name not in name_offsets:
            name_offsets[name] = len(strings)
            strings.extend(name.encode("ascii") + b"\0")

    structure = bytearray(struct.pack(">I", validator.FDT_BEGIN_NODE))
    structure.extend(_pad4(b"\0"))
    for name, value in properties:
        structure.extend(
            struct.pack(">III", validator.FDT_PROP, len(value), name_offsets[name])
        )
        structure.extend(_pad4(value))
    structure.extend(struct.pack(">II", validator.FDT_END_NODE, validator.FDT_END))
    off_struct = validator.FDT_HEADER_SIZE + 16
    off_strings = off_struct + len(structure)
    total_size = off_strings + len(strings)
    header = struct.pack(
        ">10I",
        validator.FDT_MAGIC,
        total_size,
        off_struct,
        off_strings,
        validator.FDT_HEADER_SIZE,
        17,
        16,
        0,
        len(strings),
        len(structure),
    )
    return header + b"\0" * 16 + bytes(structure) + bytes(strings)


def _fixture(
    *,
    fdts: list[bytes] | None = None,
    image_size: int = 0x400,
    mp_offset: int = 0x100,
    mp_size: int = 64,
    interface: tuple[int, int] = (30, 3),
    marker: bytes = validator.RTIC_MARKER,
    va_delta: int = 0,
    expected_sha: bytes | None = None,
) -> bytes:
    image = bytearray((index * 17 + 3) & 0xFF for index in range(image_size))
    payload_extent = max(mp_size, len(validator.RTIC_MARKER) + 4)
    if mp_offset + payload_extent <= image_size:
        payload = bytearray(b"R" * payload_extent)
        payload[: len(marker)] = marker
        struct.pack_into("<HH", payload, len(validator.RTIC_MARKER), *interface)
        image[mp_offset : mp_offset + payload_extent] = payload
    actual_sha = hashlib.sha256(image[mp_offset : mp_offset + mp_size]).digest()
    digest = actual_sha if expected_sha is None else expected_sha
    mp_data = struct.pack(
        "<QQI32s",
        validator.RTIC_BASE_ADDRESS + mp_offset + va_delta,
        mp_offset,
        mp_size,
        digest,
    )
    if fdts is None:
        fdts = [
            _fdt(
                [
                    ("qcom,rtic-id", struct.pack(">I", 1)),
                    ("MP_DATA", mp_data),
                ]
            )
        ]
    return (
        validator.WRAPPER_MAGIC
        + struct.pack("<I", image_size)
        + bytes(image)
        + b"".join(fdts)
    )


class A90RticMpConsistencySyntheticTests(unittest.TestCase):
    def test_valid_wrapper_passes_and_result_is_deterministic(self) -> None:
        wrapper = _fixture()
        first = validator.validate_kernel_bytes(wrapper)
        second = validator.validate_kernel_bytes(wrapper)
        self.assertEqual(first, second)
        self.assertEqual(first["decision"], "PASS")
        self.assertEqual(first["reasons"], [])
        self.assertEqual(first["rtic"]["interface_major"], 30)
        self.assertEqual(first["rtic"]["interface_minor"], 3)
        self.assertEqual(first["rtic"]["mp_va_addr"], "0xffffff8008080100")
        self.assertTrue(first["rtic"]["base_relation"])

    def test_stale_mp_data_hash_fails(self) -> None:
        wrapper = _fixture(expected_sha=b"\xA5" * 32)
        result = validator.validate_kernel_bytes(wrapper)
        self.assertEqual(result["decision"], "FAIL")
        self.assertIn("mp-sha256-mismatch", result["reasons"])

    def test_mutated_image_bytes_fail_against_bound_hash(self) -> None:
        wrapper = bytearray(_fixture())
        image_offset = validator.WRAPPER_HEADER_SIZE
        wrapper[image_offset + 0x120] ^= 0x01
        result = validator.validate_kernel_bytes(bytes(wrapper))
        self.assertEqual(result["decision"], "FAIL")
        self.assertIn("mp-sha256-mismatch", result["reasons"])

    def test_marker_mismatch_is_reported_even_when_hash_matches(self) -> None:
        bad_marker = b"--==!!!RTIC MP!!!==?--\0\0\0"
        wrapper = _fixture(marker=bad_marker)
        result = validator.validate_kernel_bytes(wrapper)
        self.assertEqual(result["decision"], "FAIL")
        self.assertEqual(result["reasons"], ["rtic-marker-mismatch"])

    def test_interface_version_mismatch_is_reported_even_when_hash_matches(self) -> None:
        wrapper = _fixture(interface=(29, 3))
        result = validator.validate_kernel_bytes(wrapper)
        self.assertEqual(result["decision"], "FAIL")
        self.assertEqual(result["reasons"], ["rtic-interface-version-mismatch"])

    def test_interface_decode_is_bounded_by_declared_mp_range(self) -> None:
        wrapper = _fixture(mp_size=len(validator.RTIC_MARKER))
        result = validator.validate_kernel_bytes(wrapper)
        self.assertEqual(result["decision"], "FAIL")
        self.assertEqual(result["reasons"], ["mp-range-too-small-for-interface"])
        self.assertIsNone(result["rtic"]["interface_major"])
        self.assertIsNone(result["rtic"]["interface_minor"])

    def test_base_address_relation_is_required(self) -> None:
        wrapper = _fixture(va_delta=4)
        result = validator.validate_kernel_bytes(wrapper)
        self.assertEqual(result["decision"], "FAIL")
        self.assertIn("mp-va-offset-relation-invalid", result["reasons"])

    def test_mp_range_must_be_inside_raw_image(self) -> None:
        wrapper = _fixture(mp_offset=0x3F0, mp_size=64)
        result = validator.validate_kernel_bytes(wrapper)
        self.assertEqual(result["decision"], "FAIL")
        self.assertIn("mp-range-out-of-bounds", result["reasons"])

    def test_mp_data_property_must_be_exactly_52_bytes(self) -> None:
        fdt = _fdt(
            [
                ("qcom,rtic-id", struct.pack(">I", 1)),
                ("MP_DATA", b"X" * (validator.MP_DATA_SIZE - 1)),
            ]
        )
        wrapper = _fixture(fdts=[fdt])
        result = validator.validate_kernel_bytes(wrapper)
        self.assertEqual(result["decision"], "FAIL")
        self.assertIn("mp-data-size-invalid", result["reasons"])

    def test_absent_rtic_dtb_fails_closed(self) -> None:
        wrapper = _fixture(fdts=[_fdt([("model", b"synthetic-non-rtic\0")])])
        result = validator.validate_kernel_bytes(wrapper)
        self.assertEqual(result["decision"], "FAIL")
        self.assertIn("rtic-dtb-absent", result["reasons"])

    def test_multiple_rtic_dtbs_fail_closed(self) -> None:
        one = _fdt(
            [
                ("qcom,rtic-id", struct.pack(">I", 1)),
                (
                    "MP_DATA",
                    struct.pack(
                        "<QQI32s",
                        validator.RTIC_BASE_ADDRESS + 0x100,
                        0x100,
                        64,
                        hashlib.sha256(b"R" * 64).digest(),
                    ),
                ),
            ]
        )
        wrapper = _fixture(fdts=[one, one])
        result = validator.validate_kernel_bytes(wrapper)
        self.assertEqual(result["decision"], "FAIL")
        self.assertEqual(result["reasons"], ["multiple-rtic-dtbs"])

    def test_additional_rtic_metadata_in_other_fdt_fails_closed(self) -> None:
        for extra in (
            _fdt([("qcom,rtic-id", struct.pack(">I", 1))]),
            _fdt([("MP_DATA", b"X" * validator.MP_DATA_SIZE)]),
        ):
            with self.subTest(extra=extra[:8].hex()):
                result = validator.validate_kernel_bytes(_fixture(fdts=[_fdt([
                    ("qcom,rtic-id", struct.pack(">I", 1)),
                    ("MP_DATA", struct.pack(
                        "<QQI32s",
                        validator.RTIC_BASE_ADDRESS + 0x100,
                        0x100,
                        64,
                        hashlib.sha256(b"R" * 64).digest(),
                    )),
                ]), extra]))
                self.assertEqual(result["decision"], "FAIL")
                self.assertEqual(result["reasons"], ["additional-rtic-metadata"])

    def test_malformed_fdt_total_size_fails_before_property_use(self) -> None:
        good = bytearray(_fixture())
        fdt_offset = validator.WRAPPER_HEADER_SIZE + struct.unpack_from("<I", good, 16)[0]
        declared = struct.unpack_from(">I", good, fdt_offset + 4)[0]
        struct.pack_into(">I", good, fdt_offset + 4, declared + 1)
        result = validator.validate_kernel_bytes(bytes(good))
        self.assertEqual(result["decision"], "FAIL")
        self.assertEqual(result["reasons"], ["fdt-total-size-out-of-bounds"])

    def test_malformed_wrapper_image_length_fails(self) -> None:
        wrapper = bytearray(_fixture())
        struct.pack_into("<I", wrapper, 16, len(wrapper))
        result = validator.validate_kernel_bytes(bytes(wrapper))
        self.assertEqual(result["decision"], "FAIL")
        self.assertEqual(result["reasons"], ["wrapper-image-out-of-bounds"])

    def test_wrapper_magic_is_required(self) -> None:
        wrapper = b"RAW-IMAGE" + _fixture()[len(validator.WRAPPER_MAGIC) + 4 :]
        result = validator.validate_kernel_bytes(wrapper)
        self.assertEqual(result["decision"], "FAIL")
        self.assertEqual(result["reasons"], ["wrapper-magic-invalid"])

    def test_path_reader_rejects_symlink_without_device_access(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "kernel"
            target.write_bytes(_fixture())
            link = root / "link"
            link.symlink_to(target)
            result = validator.validate_kernel_path(link)
        self.assertEqual(result["decision"], "FAIL")
        self.assertEqual(result["reasons"], ["kernel-not-regular-file"])


class A90RticMpConsistencyPrivateArtifactTests(unittest.TestCase):
    def test_stock_carrier_kernel_passes_when_staged(self) -> None:
        if not STOCK.is_file():
            self.skipTest(f"private stock artifact is absent: {STOCK}")
        result = validator.validate_kernel_path(STOCK)
        self.assertEqual(result["decision"], "PASS")
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["rtic"]["mp_va_addr"], "0xffffff8009f00000")

    def test_rebuilt_1007_kernel_fails_for_rtic_inconsistency_when_staged(self) -> None:
        if not REBUILT.is_file():
            self.skipTest(f"private rebuilt artifact is absent: {REBUILT}")
        result = validator.validate_kernel_path(REBUILT)
        self.assertEqual(result["decision"], "FAIL")
        self.assertIn("mp-sha256-mismatch", result["reasons"])


if __name__ == "__main__":
    unittest.main()
