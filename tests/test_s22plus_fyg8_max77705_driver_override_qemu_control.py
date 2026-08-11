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
CORPUS = (
    ROOT
    / "tests/fixtures/s22plus_max77705_driver_override_qemu/"
    "replay-corpus-v1.json"
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

    def test_fail_terminal_requires_exact_guest_contract(self) -> None:
        valid = (
            b"MAX77705_DRIVER_OVERRIDE_QEMU result=FAIL "
            b"stage=mount-sysfs detail=5\r\n"
        )
        evaluated = self.module.evaluate_console_bytes(valid)
        self.assertEqual(
            evaluated,
            {
                "failure": {"detail": 5, "stage": "mount-sysfs"},
                "proof": None,
                "terminal_line_ending": "CRLF",
                "verdict": "FAIL_MAX77705_DRIVER_OVERRIDE_QEMU_HOST_ONLY",
            },
        )
        malformed = (
            b"MAX77705_DRIVER_OVERRIDE_QEMU result=FAIL garbage\n",
            b"MAX77705_DRIVER_OVERRIDE_QEMU result=FAIL stage=x\n",
            b"MAX77705_DRIVER_OVERRIDE_QEMU result=FAIL stage=x detail=zero\n",
            b"MAX77705_DRIVER_OVERRIDE_QEMU result=FAIL stage=x detail=0\n",
            b"MAX77705_DRIVER_OVERRIDE_QEMU result=FAIL stage=x detail=-1\n",
            b"MAX77705_DRIVER_OVERRIDE_QEMU result=FAIL "
            b"stage=x detail=2147483648\n",
        )
        for raw in malformed:
            with self.subTest(raw=raw), self.assertRaises(
                self.module.HarnessError
            ):
                self.module.evaluate_console_bytes(raw)

    def test_capture_manifest_replay_uses_exact_raw_bytes(self) -> None:
        raw = (
            b"boot\r\nMAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
            b"target=a.virtio_mmio blocked=b.virtio_mmio,c.virtio_mmio active=3\r\n"
        )
        chunks = [
            {
                "index": 0,
                "source": "select-read",
                "byte_start": 0,
                "byte_end": 6,
                "received_after_start_sec": 0.1,
            },
            {
                "index": 1,
                "source": "communicate-tail",
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
            manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            replay = self.module.replay_console_capture(
                raw_path,
                manifest_path,
                expected_manifest_sha256=manifest_sha256,
            )
            self.assertEqual(replay["verdict"], self.module.VERDICT)
            self.assertEqual(replay["raw_sha256"], hashlib.sha256(raw).hexdigest())

            raw_path.write_bytes(raw + b"drift")
            with self.assertRaisesRegex(
                self.module.HarnessError, "byte count mismatch"
            ):
                self.module.replay_console_capture(
                    raw_path,
                    manifest_path,
                    expected_manifest_sha256=manifest_sha256,
                )

            with self.assertRaisesRegex(
                self.module.HarnessError, "SHA256 mismatch"
            ):
                self.module.replay_console_capture(
                    raw_path,
                    manifest_path,
                    expected_manifest_sha256="0" * 64,
                )

    def test_replay_hashes_and_parses_one_manifest_byte_object(self) -> None:
        raw = (
            b"MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "
            b"target=a.virtio_mmio blocked=b.virtio_mmio,c.virtio_mmio active=3\n"
        )
        manifest = self.module._capture_manifest(
            raw=raw,
            chunks=[
                {
                    "index": 0,
                    "source": "select-read",
                    "byte_start": 0,
                    "byte_end": len(raw),
                    "received_after_start_sec": 0.1,
                }
            ],
            started=1.0,
        )
        original = json.dumps(manifest, sort_keys=True).encode("utf-8")
        forged = json.loads(original.decode("utf-8"))
        forged["capture_started_monotonic"] = 2.0
        forged_bytes = json.dumps(forged, sort_keys=True).encode("utf-8")

        class SwitchingManifestPath:
            def __init__(self):
                self.calls = 0

            def read_bytes(self):
                self.calls += 1
                return original if self.calls == 1 else forged_bytes

        with tempfile.TemporaryDirectory() as directory:
            raw_path = Path(directory) / self.module.RAW_CAPTURE_NAME
            raw_path.write_bytes(raw)
            manifest_path = SwitchingManifestPath()
            replay = self.module.replay_console_capture(
                raw_path,
                manifest_path,
                expected_manifest_sha256=hashlib.sha256(original).hexdigest(),
            )
        self.assertEqual(manifest_path.calls, 1)
        self.assertEqual(replay["verdict"], self.module.VERDICT)
        self.assertEqual(
            replay["capture_manifest_sha256"],
            hashlib.sha256(original).hexdigest(),
        )

    def test_capture_manifest_rejects_chunk_gap(self) -> None:
        raw = b"one\ntwo\n"
        manifest = self.module._capture_manifest(
            raw=raw,
            chunks=[
                {
                    "index": 0,
                    "source": "select-read",
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

    def test_capture_manifest_rejects_authority_mutations(self) -> None:
        raw = b"one\ntwo\n"
        chunks = [
            {
                "index": 0,
                "source": "select-read",
                "byte_start": 0,
                "byte_end": 4,
                "received_after_start_sec": 0.1,
            },
            {
                "index": 1,
                "source": "communicate-tail",
                "byte_start": 4,
                "byte_end": len(raw),
                "received_after_start_sec": 0.2,
            },
        ]
        manifest = self.module._capture_manifest(
            raw=raw, chunks=chunks, started=1.0
        )

        def clone():
            return json.loads(json.dumps(manifest))

        mutations = []
        value = clone()
        value["unexpected"] = True
        mutations.append(value)
        value = clone()
        value["source"] = "forged"
        mutations.append(value)
        value = clone()
        value["clock"] = "wall-clock"
        mutations.append(value)
        value = clone()
        del value["chunks"][0]["source"]
        mutations.append(value)
        value = clone()
        value["chunks"][0]["source"] = "communicate-tail"
        mutations.append(value)
        value = clone()
        value["chunks"][0]["received_after_start_sec"] = -1
        mutations.append(value)
        value = clone()
        value["chunks"][1]["received_after_start_sec"] = 0.05
        mutations.append(value)
        value = clone()
        value["chunks"][0]["received_after_start_sec"] = float("inf")
        mutations.append(value)

        for mutated in mutations:
            with self.subTest(mutated=mutated), self.assertRaises(
                self.module.HarnessError
            ):
                self.module.verify_capture_manifest(raw, mutated)

    def test_immutable_evidence_writer_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.raw"
            self.module._write_exclusive_bytes(path, b"first")
            with self.assertRaisesRegex(
                self.module.HarnessError, "already exists"
            ):
                self.module._write_exclusive_bytes(path, b"second")
            self.assertEqual(path.read_bytes(), b"first")

    def test_live_capture_keeps_one_exclusive_fd_through_tail(self) -> None:
        script = SCRIPT.read_bytes()
        self.assertEqual(script.count(b'raw_path.open("xb"'), 1)
        self.assertNotIn(b'raw_path.open("ab"', script)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.raw"
            with path.open("xb", buffering=0) as owner:
                self.module._write_all(owner, b"select")
                with self.assertRaises(FileExistsError):
                    path.open("xb", buffering=0)
                self.module._write_all(owner, b"tail")
            self.assertEqual(path.read_bytes(), b"selecttail")

    def test_named_failure_corpus_replays_exact_expected_outcomes(self) -> None:
        corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        self.assertEqual(
            corpus["schema"],
            "s22plus-max77705-driver-override-qemu-replay-corpus-v1",
        )
        entries = {entry["id"]: entry for entry in corpus["entries"]}
        self.assertEqual(
            set(entries),
            {
                "run01-truncated-terminal-representative",
                "run02-complete-crlf-representative",
            },
        )
        marker = b"MAX77705_DRIVER_OVERRIDE_QEMU result=PASS "

        truncated = entries["run01-truncated-terminal-representative"]
        self.assertIn("synthetic-representative", truncated["provenance"])
        truncated_raw = truncated["raw_text"].encode("ascii")
        self.assertFalse(
            self.module.complete_record_seen(truncated_raw, marker)
        )
        self.assertEqual(
            truncated["expected"],
            {
                "complete_record_seen": False,
                "error": "terminal record is incomplete",
                "outcome": "REJECT",
            },
        )
        with self.assertRaisesRegex(
            self.module.HarnessError, "terminal record is incomplete"
        ):
            self.module.evaluate_console_bytes(truncated_raw)

        crlf = entries["run02-complete-crlf-representative"]
        self.assertIn("synthetic-representative", crlf["provenance"])
        crlf_raw = crlf["raw_text"].encode("ascii")
        self.assertTrue(self.module.complete_record_seen(crlf_raw, marker))
        evaluated = self.module.evaluate_console_bytes(crlf_raw)
        self.assertEqual(evaluated["verdict"], self.module.VERDICT)
        self.assertEqual(evaluated["terminal_line_ending"], "CRLF")
        self.assertEqual(
            evaluated["proof"],
            {
                "active_count": 3,
                "blocked": ["b.virtio_mmio", "c.virtio_mmio"],
                "target": "a.virtio_mmio",
            },
        )
        self.assertEqual(
            crlf["expected"],
            {
                "active_count": 3,
                "blocked": ["b.virtio_mmio", "c.virtio_mmio"],
                "complete_record_seen": True,
                "outcome": self.module.VERDICT,
                "target": "a.virtio_mmio",
                "terminal_line_ending": "CRLF",
            },
        )

        private_success = corpus["private_success_reference"]
        self.assertEqual(private_success["raw_byte_count"], 1463)
        self.assertEqual(
            private_success["raw_sha256"],
            "904093a5216f8bfd5408ac6e500e4809fb763124bb8fc9948bc8af5c788156f3",
        )
        self.assertFalse(
            corpus["scope"]["candidate_runtime_15_device_schema_covered"]
        )

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
