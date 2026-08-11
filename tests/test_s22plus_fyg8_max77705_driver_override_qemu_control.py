from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_max77705_driver_override_qemu_control.py"
)
SOURCE = (
    ROOT
    / "workspace/public/src/native-init/"
    "s22plus_fyg8_max77705_driver_override_qemu_control.c"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "max77705_driver_override_qemu", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Max77705DriverOverrideQemuControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()
        cls.source = SOURCE.read_bytes()

    def test_current_source_contract_passes(self) -> None:
        self.module.verify_source(self.source)

    def test_override_after_driver_registration_rejects(self) -> None:
        first = self.source.find(
            b"\tcontrol_set_override(active.names[1], CONTROL_OVERRIDE"
        )
        second_load = self.source.find(b"\tcontrol_load_module();", first)
        self.assertGreaterEqual(first, 0)
        self.assertGreater(second_load, first)
        line_end = self.source.find(b"\n", second_load) + 1
        load_line = self.source[second_load:line_end]
        mutated = (
            self.source[:first]
            + load_line
            + self.source[first:second_load]
            + self.source[line_end:]
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "proof order"
        ):
            self.module.verify_source(mutated)

    def test_missing_second_blocker_rejects(self) -> None:
        mutated = self.source.replace(
            b"\tcontrol_set_override(active.names[2], CONTROL_OVERRIDE \"\\n\");\n",
            b"",
            1,
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "proof order"
        ):
            self.module.verify_source(mutated)

    def test_direct_bind_or_unbind_shortcut_rejects(self) -> None:
        marker = b"int main(void)\n{"
        mutated = self.source.replace(
            marker,
            marker + b'\n\tconst char *forbidden = "/unbind";',
            1,
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "forbidden shortcut"
        ):
            self.module.verify_source(mutated)

    def test_guest_config_requires_module_unload_and_virtio_mmio(self) -> None:
        valid = "\n".join(self.module.REQUIRED_CONFIG).encode("ascii") + b"\n"
        self.module.verify_guest_config(valid)
        for removed in (b"CONFIG_MODULE_UNLOAD=y\n", b"CONFIG_VIRTIO_MMIO=m\n"):
            with self.subTest(removed=removed), self.assertRaisesRegex(
                self.module.HarnessError, "lacks required"
            ):
                self.module.verify_guest_config(valid.replace(removed, b""))

    def test_pass_line_requires_three_unique_platform_devices(self) -> None:
        result = self.module.parse_pass_line(
            "MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
            "target=a.virtio_mmio blocked=b.virtio_mmio,c.virtio_mmio active=3\r\n"
        )
        self.assertEqual(result["active_count"], 3)
        self.assertEqual(result["blocked"], ["b.virtio_mmio", "c.virtio_mmio"])
        bad = (
            "MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
            "target=a.virtio_mmio blocked=a.virtio_mmio,c.virtio_mmio active=3\n"
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "invalid device cardinality"
        ):
            self.module.parse_pass_line(bad)

    def test_pl011_codec_accepts_lf_and_crlf_and_preserves_geometry(self) -> None:
        raw = b"prefix\nfirst\r\nsecond\n"
        decoded = self.module.decode_pl011_console(raw)
        self.assertEqual(
            [record.text for record in decoded.records],
            ["prefix", "first", "second"],
        )
        self.assertEqual(
            [record.line_ending for record in decoded.records],
            ["LF", "CRLF", "LF"],
        )
        self.assertEqual(decoded.records[1].byte_start, len(b"prefix\n"))
        self.assertEqual(decoded.records[-1].byte_end, len(raw))
        self.assertEqual(decoded.incomplete_suffix, "")

    def test_pl011_codec_rejects_bare_cr_nul_and_invalid_utf8(self) -> None:
        cases = (
            (b"bad\rline\n", "bare CR"),
            (b"bad\x00line\n", "NUL"),
            (b"bad\xffline\n", "valid UTF-8"),
        )
        for raw, message in cases:
            with self.subTest(raw=raw), self.assertRaisesRegex(
                self.module.HarnessError, message
            ):
                self.module.decode_pl011_console(raw)

    def test_exact_console_evaluator_replays_lf_and_crlf(self) -> None:
        line = (
            b"MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
            b"target=a.virtio_mmio blocked=b.virtio_mmio,c.virtio_mmio active=3"
        )
        lf = self.module.evaluate_console_bytes(b"boot\n" + line + b"\n")
        crlf = self.module.evaluate_console_bytes(b"boot\r\n" + line + b"\r\n")
        self.assertEqual(lf["verdict"], self.module.VERDICT)
        self.assertEqual(lf["proof"], crlf["proof"])
        self.assertEqual(lf["terminal_line_ending"], "LF")
        self.assertEqual(crlf["terminal_line_ending"], "CRLF")

    def test_incomplete_terminal_record_is_not_replayable(self) -> None:
        raw = (
            b"MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
            b"target=a.virtio_mmio blocked=b.virtio_mmio,c.virtio_mmio active=3"
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "terminal record is incomplete"
        ):
            self.module.evaluate_console_bytes(raw)

    def test_duplicate_or_malformed_terminal_record_rejects(self) -> None:
        valid = (
            b"MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
            b"target=a.virtio_mmio blocked=b.virtio_mmio,c.virtio_mmio active=3\n"
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "exactly one complete terminal record"
        ):
            self.module.evaluate_console_bytes(valid + valid)

        malformed = valid.replace(b" active=3", b" active=4")
        with self.assertRaisesRegex(
            self.module.HarnessError, "invalid device cardinality"
        ):
            self.module.evaluate_console_bytes(malformed)

    def test_capture_manifest_replay_uses_exact_raw_bytes(self) -> None:
        raw = (
            b"boot\r\nMAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
            b"target=a.virtio_mmio blocked=b.virtio_mmio,c.virtio_mmio active=3\r\n"
        )
        chunks = [
            {
                "index": 0,
                "source": "fixture",
                "byte_start": 0,
                "byte_end": 6,
                "received_after_start_sec": 0.1,
            },
            {
                "index": 1,
                "source": "fixture",
                "byte_start": 6,
                "byte_end": len(raw),
                "received_after_start_sec": 0.2,
            },
        ]
        manifest = self.module._capture_manifest(
            raw=raw, chunks=chunks, started=1.0
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_path = root / self.module.RAW_CAPTURE_NAME
            manifest_path = root / self.module.CAPTURE_MANIFEST_NAME
            raw_path.write_bytes(raw)
            manifest_path.write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            replay = self.module.replay_console_capture(raw_path, manifest_path)
            self.assertEqual(replay["verdict"], self.module.VERDICT)
            self.assertEqual(replay["raw_sha256"], hashlib.sha256(raw).hexdigest())

            raw_path.write_bytes(raw + b"drift")
            with self.assertRaisesRegex(
                self.module.HarnessError, "byte count mismatch"
            ):
                self.module.replay_console_capture(raw_path, manifest_path)

    def test_capture_manifest_rejects_chunk_gap(self) -> None:
        raw = b"one\ntwo\n"
        manifest = self.module._capture_manifest(
            raw=raw,
            chunks=[
                {
                    "index": 0,
                    "source": "fixture",
                    "byte_start": 0,
                    "byte_end": len(raw),
                    "received_after_start_sec": 0.1,
                }
            ],
            started=1.0,
        )
        manifest["chunks"][0]["byte_start"] = 1
        with self.assertRaisesRegex(
            self.module.HarnessError, "chunk geometry mismatch"
        ):
            self.module.verify_capture_manifest(raw, manifest)

    def test_immutable_evidence_writer_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.raw"
            self.module._write_exclusive_bytes(path, b"first")
            with self.assertRaisesRegex(
                self.module.HarnessError, "already exists"
            ):
                self.module._write_exclusive_bytes(path, b"second")
            self.assertEqual(path.read_bytes(), b"first")

    def test_partial_terminal_marker_does_not_stop_observer(self) -> None:
        marker = b"MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
        partial = marker + b"target=a.virtio_mmio active=3"
        self.assertFalse(self.module.complete_record_seen(partial, marker))
        self.assertTrue(self.module.complete_record_seen(partial + b"\n", marker))

    def test_qemu_version_is_exact(self) -> None:
        self.assertEqual(
            self.module.verify_qemu_version_result(
                0, self.module.PINNED_QEMU_VERSION + "\n"
            ),
            self.module.PINNED_QEMU_VERSION,
        )
        with self.assertRaisesRegex(self.module.HarnessError, "version mismatch"):
            self.module.verify_qemu_version_result(0, "QEMU wrong\n")


if __name__ == "__main__":
    unittest.main()
