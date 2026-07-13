import importlib.util
import os
import struct
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1a_marker_oracle.py"
)


def load():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_r4w1a_marker_oracle_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_report(module, path, body, source="/proc/last_kmsg", extra=None):
    main_name = "bugreport-FYG8-test.txt"
    main = (
        f"------ LAST KMSG ({source}) ------\n".encode("ascii")
        + body
        + b"\n------ NEXT SECTION ------\nnext\n"
    )
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("version.txt", "2.0")
        archive.writestr("main_entry.txt", main_name)
        archive.writestr(main_name, main)
        for name, data in extra or []:
            archive.writestr(name, data)


class S22PlusFyg8R4W1AMarkerOracleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.oracle = load()

    def test_parses_exact_marker_once_in_complete_last_kmsg(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "bugreport.zip"
            make_report(self.oracle, archive, b"prefix\n" + self.oracle.EXPECTED_MARKER + b"\nsuffix\n")
            result = self.oracle.parse_bugreport(archive, "exact")
            self.assertEqual(
                result["marker"]["classification"], "EXACT_MARKER_ONCE_IN_LAST_KMSG"
            )
            self.assertTrue(result["zip"]["all_entries_crc_checked"])
            self.assertEqual(result["last_kmsg"]["source"], "/proc/last_kmsg")

    def test_accepts_marker_absent_baseline(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "baseline.zip"
            make_report(self.oracle, archive, b"ordinary kernel log\n")
            result = self.oracle.parse_bugreport(archive, "absent")
            self.assertEqual(result["marker"]["classification"], "MARKER_FAMILY_ABSENT")

    def test_rejects_pstore_source_and_marker_in_other_entry(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pstore = root / "pstore.zip"
            make_report(
                self.oracle,
                pstore,
                self.oracle.EXPECTED_MARKER,
                source="/sys/fs/pstore/console-ramoops",
            )
            with self.assertRaisesRegex(self.oracle.OracleError, "exact /proc/last_kmsg"):
                self.oracle.parse_bugreport(pstore, "exact")

            foreign = root / "foreign.zip"
            make_report(
                self.oracle,
                foreign,
                self.oracle.EXPECTED_MARKER,
                extra=[("FS/data/duplicate.txt", self.oracle.EXPECTED_MARKER)],
            )
            with self.assertRaisesRegex(self.oracle.OracleError, "cardinality mismatch"):
                self.oracle.parse_bugreport(foreign, "exact")

    def test_rejects_partial_marker_at_section_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tail = root / "partial-tail.zip"
            make_report(self.oracle, tail, b"log\n" + self.oracle.EXPECTED_MARKER[:40])
            with self.assertRaisesRegex(self.oracle.OracleError, "partial R4W1 marker"):
                self.oracle.parse_bugreport(tail, "exact")

            head = root / "partial-head.zip"
            make_report(self.oracle, head, self.oracle.EXPECTED_MARKER[-40:] + b"\nlog")
            with self.assertRaisesRegex(self.oracle.OracleError, "partial R4W1 marker"):
                self.oracle.parse_bugreport(head, "exact")

    def test_finds_foreign_marker_across_stream_chunk_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / "boundary.zip"
            padding = b"A" * (self.oracle.SCAN_CHUNK_SIZE - 7)
            make_report(
                self.oracle,
                archive,
                self.oracle.EXPECTED_MARKER,
                extra=[("FS/data/boundary.bin", padding + self.oracle.EXPECTED_MARKER)],
            )
            with self.assertRaisesRegex(self.oracle.OracleError, "cardinality mismatch"):
                self.oracle.parse_bugreport(archive, "exact")

    def test_rejects_duplicate_member_and_crc_corruption(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            duplicate = root / "duplicate.zip"
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(duplicate, "w") as archive:
                    archive.writestr("version.txt", "2.0")
                    archive.writestr("version.txt", "2.0")
                    archive.writestr("main_entry.txt", "report.txt")
                    archive.writestr("report.txt", b"report")
            with self.assertRaisesRegex(self.oracle.OracleError, "duplicate ZIP"):
                self.oracle.parse_bugreport(duplicate, "absent")

            corrupted = root / "corrupted.zip"
            make_report(self.oracle, corrupted, self.oracle.EXPECTED_MARKER)
            raw = bytearray(corrupted.read_bytes())
            with zipfile.ZipFile(corrupted) as archive:
                info = archive.getinfo("bugreport-FYG8-test.txt")
                offset = info.header_offset
            name_len, extra_len = struct.unpack_from("<HH", raw, offset + 26)
            payload = offset + 30 + name_len + extra_len
            raw[payload + 3] ^= 0x01
            corrupted.write_bytes(raw)
            with self.assertRaisesRegex(self.oracle.OracleError, "CRC-checked read"):
                self.oracle.parse_bugreport(corrupted, "exact")

    def test_text_contract_closes_exact_service_and_snapshot_order(self):
        dumpstate = b"\0".join(
            (
                b"/proc/last_kmsg",
                b"/sys/fs/pstore/console-ramoops",
                b"/sys/fs/pstore/console-ramoops-0",
                b"LAST KMSG",
                b"main_entry.txt",
                b"version.txt",
                b"/bugreports",
            )
        ) + b"\0-s: write zipped file to control socket (for init)"
        bugreportz = (
            b"ctl.start\0dumpstate\0-s: stream content to standard output\0"
            b"Failed to write data to stdout\0dumpstate.is_running\0"
        )
        rc = b"""service dumpstate /system/bin/dumpstate -s
    class main
    socket dumpstate stream 0660 shell log
    disabled
    oneshot
    user root
"""
        contexts = b"/system/bin/dumpstate u:object_r:dumpstate_exec:s0\n"
        main = " ".join(
            (
                "DEVICE_BUILDER(__log_buf_prepare_buffer, NULL)",
                "DEVICE_BUILDER(__last_kmsg_alloc_buffer, __last_kmsg_free_buffer)",
                "DEVICE_BUILDER(__last_kmsg_pull_last_log, NULL)",
                "DEVICE_BUILDER(__last_kmsg_procfs_create, __last_kmsg_procfs_remove)",
                "DEVICE_BUILDER(__log_buf_pull_early_buffer, NULL)",
                "DEVICE_BUILDER(__log_buf_logger_init, __log_buf_logger_exit)",
                "DEVICE_BUILDER(__ap_klog_proc_init, __ap_klog_proc_exit)",
            )
        ).encode()
        last = " ".join(
            (
                "last_kmsg->size = __log_buf_copy_to_buffer(buf);",
                "count = min(len, (size_t)(last_kmsg->size - pos));",
                "copy_to_user(buf, last_kmsg->buf + pos, count)",
                "proc_create_data(LAST_LOG_BUF_NODE, 0444, NULL,"
                " &last_kmsg_buf_pops, last_kmsg)",
            )
        ).encode()
        result = self.oracle.check_text_contract(
            dumpstate, bugreportz, rc, contexts, main, last
        )
        self.assertTrue(result["snapshot_before_current_logger"])
        self.assertEqual(result["snapshot_proc_mode_octal"], "0444")

    def test_refuses_symlink_archive_and_source_has_no_transport(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "bugreport.zip"
            make_report(self.oracle, archive, b"ordinary log\n")
            link = root / "link.zip"
            os.symlink(archive, link)
            with self.assertRaisesRegex(self.oracle.OracleError, "symlink input refused"):
                self.oracle.parse_bugreport(link, "absent")
        source = SCRIPT.read_text(encoding="utf-8").lower()
        self.assertNotIn("subprocess", source)
        self.assertNotIn("pyusb", source)
        self.assertIn('"device_contact": false', source)
        self.assertIn('"live_authorized": false', source)


if __name__ == "__main__":
    unittest.main()
