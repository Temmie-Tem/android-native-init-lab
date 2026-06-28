"""Regression tests for a90_stock_kallsyms_extract.

Uses small synthetic kallsyms-like token/name/address tables to pin pure decode
and layout validation helpers. No real kernel image or private artifact needed.
"""

import struct
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

extract = load_revalidation("a90_stock_kallsyms_extract")
REPO_ROOT = Path(__file__).resolve().parents[1]
V2321_BOOT = (
    REPO_ROOT
    / "workspace"
    / "private"
    / "inputs"
    / "boot_images"
    / "boot_linux_v2321_usb_clean_identity_rodata.img"
)


def make_token_table_blob() -> tuple[bytes, list[int], list[bytes], int]:
    blob = bytearray()
    cumulative: list[int] = []
    tokens: list[bytes] = []
    for index in range(256):
        cumulative.append(len(blob))
        token = b"" if index == 0 else f"tok{index}".encode()
        tokens.append(token)
        blob += token + b"\0"
    table_end = len(blob)
    blob += b"\xaa\xbb"
    for value in cumulative:
        blob += struct.pack("<H", value)
    return bytes(blob), cumulative, tokens, table_end


class KernelImageAndScalarHelpers(unittest.TestCase):
    def test_sha_and_little_endian_reads(self):
        data = bytes(range(16))
        self.assertEqual(extract.sha256_bytes(b""), "e3b0c44298fc1c149afbf4c8996fb924"
                                                  "27ae41e4649b934ca495991b7852b855")
        self.assertEqual(extract.u16(data, 1), 0x0201)
        self.assertEqual(extract.u32(data, 2), 0x05040302)
        self.assertEqual(extract.u64(data, 4), 0x0b0a090807060504)

    def test_unwrap_kernel_accepts_raw_and_uncompressed_img_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_path = root / "Image"
            raw_payload = b"raw-kernel"
            raw_path.write_bytes(raw_payload)

            raw_image = extract.unwrap_kernel(raw_path)
            self.assertEqual(raw_image.raw, raw_payload)
            self.assertEqual(raw_image.raw_offset, 0)
            self.assertEqual(raw_image.wrapper_size, len(raw_payload))
            self.assertEqual(raw_image.wrapper_sha256, extract.sha256_bytes(raw_payload))

            wrapper_path = root / "wrapped"
            wrapper = b"UNCOMPRESSED_IMG" + struct.pack("<I", len(raw_payload)) + raw_payload
            wrapper_path.write_bytes(wrapper)

            wrapped_image = extract.unwrap_kernel(wrapper_path)
            self.assertEqual(wrapped_image.raw, raw_payload)
            self.assertEqual(wrapped_image.raw_offset, 20)
            self.assertEqual(wrapped_image.wrapper_size, len(wrapper))
            self.assertEqual(wrapped_image.wrapper_sha256, extract.sha256_bytes(wrapper))
            self.assertEqual(wrapped_image.raw_sha256, extract.sha256_bytes(raw_payload))

    def test_unwrap_kernel_accepts_android_boot_wrapped_uncompressed_img(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw_payload = b"raw-kernel"
            kernel_blob = b"UNCOMPRESSED_IMG" + struct.pack("<I", len(raw_payload)) + raw_payload
            page_size = 0x1000
            header = bytearray(page_size)
            header[:8] = b"ANDROID!"
            struct.pack_into(
                "<10I",
                header,
                8,
                len(kernel_blob),
                0,
                0,
                0,
                0,
                0,
                0,
                page_size,
                0,
                0,
            )
            boot_path = root / "boot.img"
            boot_path.write_bytes(bytes(header) + kernel_blob)

            image = extract.unwrap_kernel(boot_path)

            self.assertEqual(image.raw, raw_payload)
            self.assertEqual(image.raw_offset, page_size + 20)
            self.assertEqual(image.wrapper_size, page_size + len(kernel_blob))

    def test_unwrap_kernel_rejects_short_or_truncated_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            short = root / "short"
            short.write_bytes(b"UNCOMPRESSED_IMG")
            with self.assertRaises(ValueError):
                extract.unwrap_kernel(short)

            truncated = root / "truncated"
            truncated.write_bytes(b"UNCOMPRESSED_IMG" + struct.pack("<I", 8) + b"abc")
            with self.assertRaises(ValueError):
                extract.unwrap_kernel(truncated)


class TokenTableHelpers(unittest.TestCase):
    def test_printable_token_rejects_non_printable_bytes(self):
        self.assertTrue(extract.printable_token(b"abc_DEF\t"))
        self.assertFalse(extract.printable_token(b"abc\x01"))

    def test_parse_token_run_and_token_table_with_padding(self):
        data, cumulative, tokens, table_end = make_token_table_blob()

        parsed = extract.parse_token_run(data, 0)
        self.assertIsNotNone(parsed)
        parsed_end, parsed_cumulative, parsed_tokens = parsed
        self.assertEqual(parsed_end, table_end)
        self.assertEqual(parsed_cumulative, cumulative)
        self.assertEqual(parsed_tokens, tokens)

        table = extract.token_table_at(data, 0)
        self.assertIsNotNone(table)
        self.assertEqual(table.table_start, 0)
        self.assertEqual(table.table_end, table_end)
        self.assertEqual(table.index_start, table_end + 2)
        self.assertEqual(table.token_index, cumulative)
        self.assertEqual(table.tokens, tokens)

    def test_parse_token_run_rejects_short_or_bad_tokens(self):
        self.assertIsNone(extract.parse_token_run(b"a\0b\0", 0))

        data, _, _, _ = make_token_table_blob()
        bad = bytearray(data)
        bad[bad.find(b"tok1")] = 0x01
        self.assertIsNone(extract.parse_token_run(bytes(bad), 0))


class NameAndMarkerHelpers(unittest.TestCase):
    def test_marker_candidate_requires_monotonic_reasonable_offsets(self):
        start = 0x20
        values = [0] + [6000 + index * 32768 for index in range(35)]
        token_table_start = start + 8 * len(values)
        data = bytearray(token_table_start + 32)
        for index, value in enumerate(values):
            struct.pack_into("<Q", data, start + 8 * index, value)

        self.assertEqual(extract.marker_candidate(bytes(data), start, token_table_start), values)

        non_monotonic = bytearray(data)
        struct.pack_into("<Q", non_monotonic, start + 8 * 2, 1)
        self.assertIsNone(extract.marker_candidate(bytes(non_monotonic), start, token_table_start))

    def test_parse_record_offsets_handles_padding_and_rejects_bad_records(self):
        records = bytes([2, 1, 2, 1, 3])
        self.assertEqual(extract.parse_record_offsets(records, 0, len(records)), ([0, 3], 5))

        padded = records + b"\0\0"
        self.assertEqual(
            extract.parse_record_offsets(padded, 0, len(padded), allow_zero_padding=True),
            ([0, 3], 5),
        )
        self.assertIsNone(extract.parse_record_offsets(padded, 0, len(padded)))
        self.assertIsNone(extract.parse_record_offsets(bytes([129]) + b"x" * 129, 0, 130))

    def test_parse_record_offsets_handles_two_byte_uleb128_lengths(self):
        records = bytes([0x81, 0x01]) + bytes([1]) * 129 + bytes([1, 2])
        self.assertEqual(extract.parse_record_offsets(records, 0, len(records)), ([0, 131], 133))

    def test_decode_names_joins_token_bytes(self):
        records = bytes([2, 1, 2, 1, 3])
        tokens = [b"", b"T", b"_text", b"foo"] + [b""] * 252
        self.assertEqual(extract.decode_names(records, 0, [0, 3], tokens), ["T_text", "foo"])

    def test_decode_names_handles_two_byte_uleb128_lengths(self):
        records = bytes([0x81, 0x01]) + bytes([1]) * 129
        tokens = [b"", b"a"] + [b""] * 254
        self.assertEqual(extract.decode_names(records, 0, [0], tokens), ["a" * 129])

    def test_find_num_syms_position_finds_preceding_qword(self):
        data = b"prefix" + struct.pack("<Q", 1234) + b"names"
        self.assertEqual(extract.find_num_syms_position(data, len(b"prefix") + 8, 1234), len(b"prefix"))
        with self.assertRaises(RuntimeError):
            extract.find_num_syms_position(data, len(data), 999)


class AddressAndRenderingHelpers(unittest.TestCase):
    def test_find_address_table_validates_monotonic_offsets_and_sets_synthetic_base(self):
        num_syms = 4101
        relative_base_pos = 4 * num_syms
        num_syms_pos = relative_base_pos + 8
        data = bytearray(num_syms_pos + 8)
        for index in range(num_syms):
            struct.pack_into("<I", data, 4 * index, index * 4)
        struct.pack_into("<Q", data, relative_base_pos, 0xabcdef)
        struct.pack_into("<Q", data, num_syms_pos, num_syms)
        names = ["T_text"] + [f"Tsym{index}" for index in range(1, num_syms)]
        name_table = extract.NameTable(
            names_start=num_syms_pos + 8,
            names_end=num_syms_pos + 8,
            marker_start=num_syms_pos + 8,
            marker_count=17,
            num_syms_pos=num_syms_pos,
            num_syms=num_syms,
            names=names,
            record_offsets=list(range(num_syms)),
        )

        addresses = extract.find_address_table(bytes(data), name_table, 0x100000)

        self.assertEqual(addresses.offsets_start, 0)
        self.assertEqual(addresses.relative_base_pos, relative_base_pos)
        self.assertEqual(addresses.relative_base, 0xabcdef)
        self.assertEqual(addresses.low_offsets[:3], [0, 4, 8])
        self.assertEqual(addresses.text_offset, 0)
        self.assertEqual(addresses.synthetic_base, 0x100000)

        bad = bytearray(data)
        for index in range(num_syms):
            struct.pack_into("<I", bad, 4 * index, num_syms - index)
        with self.assertRaises(RuntimeError):
            extract.find_address_table(bytes(bad), name_table, 0x100000)

    def test_render_system_map_skips_empty_rows_and_strips_kind_prefix(self):
        names = extract.NameTable(
            names_start=0,
            names_end=0,
            marker_start=0,
            marker_count=0,
            num_syms_pos=0,
            num_syms=4,
            names=["T_text", "", "T", "tworker"],
            record_offsets=[0, 1, 2, 3],
        )
        addresses = extract.AddressTable(
            offsets_start=0,
            relative_base_pos=0,
            relative_base=0,
            low_offsets=[0x10, 0x20, 0x30, 0x40],
            synthetic_base=0x1000,
            text_offset=0x10,
        )

        self.assertEqual(
            extract.render_system_map(names, addresses),
            "0000000000001010 T _text\n0000000000001040 t worker\n",
        )


@unittest.skipUnless(V2321_BOOT.exists(), "v2321 private boot image not present")
class V2321KallsymsRegression(unittest.TestCase):
    def test_v2321_ground_truth_symbols_are_stage_c_file_vaddrs(self):
        image = extract.unwrap_kernel(V2321_BOOT)
        token_table = extract.find_token_table(image.raw, [0x2103100])
        marker_start, markers = extract.find_marker_table(image.raw, token_table.table_start, [0x2101F00])
        names = extract.find_names(image.raw, token_table, marker_start, markers, [0x1F10700])
        addresses = extract.find_address_table(image.raw, names, extract.DEFAULT_TEXT_ADDRESS)
        overrides, sources = extract.build_semantic_overrides(image.raw, extract.DEFAULT_TEXT_ADDRESS)
        addresses = extract.apply_semantic_overrides(addresses, names, overrides, sources)

        symbol_map: dict[str, int] = {}
        for line in extract.render_system_map(names, addresses).splitlines():
            address, _kind, symbol = line.split(maxsplit=2)
            symbol_map[symbol] = int(address, 16)

        self.assertEqual(symbol_map["kgsl_pwrctrl_num_pwrlevels_show"], 0xFFFFFF80089262DC)
        self.assertEqual(symbol_map["kgsl_pwrctrl_gpu_busy_percentage_show"], 0xFFFFFF800892790C)
        self.assertEqual(symbol_map["kgsl_pwrctrl_force_no_nap_store"], 0xFFFFFF80089273B4)
        self.assertEqual(symbol_map["kgsl_pwrctrl_force_no_nap_show"], 0xFFFFFF8008927344)
        self.assertEqual(symbol_map["printk"], 0xFFFFFF800813D8CC)
        self.assertEqual(symbol_map["__kmalloc"], 0xFFFFFF80082724BC)
        self.assertEqual(symbol_map["kfree"], 0xFFFFFF800827276C)
        self.assertEqual(symbol_map["kallsyms_lookup_name"], 0xFFFFFF800818452C)

        source_by_symbol = {
            name[1:]: addresses.decoded_address_sources[index]
            for index, name in enumerate(names.names)
            if name and name[1:]
        }
        self.assertEqual(source_by_symbol["kgsl_pwrctrl_num_pwrlevels_show"], "rkp-ropp-local-run")
        self.assertEqual(source_by_symbol["kgsl_pwrctrl_gpu_busy_percentage_show"], "rkp-ropp-local-run")
        self.assertEqual(source_by_symbol["kgsl_pwrctrl_force_no_nap_store"], "rkp-ropp-local-run")
        self.assertEqual(source_by_symbol["kgsl_pwrctrl_force_no_nap_show"], "rkp-ropp-local-run")
        self.assertEqual(source_by_symbol["printk"], "plain-printk-variadic-wrapper-signature")
        self.assertEqual(source_by_symbol["__kmalloc"], "base-relative")

        num_off = symbol_map["kgsl_pwrctrl_num_pwrlevels_show"] - extract.DEFAULT_TEXT_ADDRESS
        busy_off = symbol_map["kgsl_pwrctrl_gpu_busy_percentage_show"] - extract.DEFAULT_TEXT_ADDRESS
        store_off = symbol_map["kgsl_pwrctrl_force_no_nap_store"] - extract.DEFAULT_TEXT_ADDRESS
        self.assertEqual(extract.u32(image.raw, num_off + 0x44), 0x51000503)
        busy_words = extract.function_body_words(image.raw, busy_off)
        self.assertIn(0x1B0A7D29, busy_words)  # mul w9, w9, w10
        self.assertIn(0x1AC80923, busy_words)  # udiv w3, w9, w8
        self.assertIn(0x52820001, busy_words)  # mov w1, #0x1000
        self.assertEqual(extract.u32(image.raw, store_off), 0xD10103FF)
        self.assertEqual(extract.u32(image.raw, store_off + 4), 0xCA1103D0)


if __name__ == "__main__":
    unittest.main()
