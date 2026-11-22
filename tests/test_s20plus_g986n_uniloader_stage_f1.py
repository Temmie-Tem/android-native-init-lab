"""S20+ first-return pstore reader and owner regression tests, host only."""

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import s20plus_g986n_uniloader_stage_f1 as stage

reader = stage.reader
TAG = "a" * 64
BOOT_ID = "dca2d85e-6a46-4e14-9c9d-de01b2cd96d2"
BOOT = hashlib.sha256(BOOT_ID.encode()).hexdigest()


class RootReaderTests(unittest.TestCase):
    def setUp(self):
        base = tempfile.TemporaryDirectory()
        self.addCleanup(base.cleanup)
        self.path = Path(base.name)
        self.directory = self.path / "pstore"
        self.directory.mkdir()
        (self.path / "chosen").mkdir()
        (self.path / "boot_id").write_text(BOOT_ID + "\n")
        (self.path / "mounts").write_text(f"pstore {self.directory} pstore rw 0 0\n")
        identity = self.path / "id"
        identity.write_text("#!/bin/sh\nprintf 0")
        identity.chmod(0o700)
        self.pmsg = self.directory / "pmsg-ramoops-0"
        self.console = self.directory / "console-ramoops-0"

    def acquire(self, expected_boot=BOOT):
        script = reader.script(TAG, expected_boot)
        if (self.path / "head").exists():
            script = script.replace("/system/bin/head", str(self.path / "head"))
        for old, new in (
            ("/system/bin/id", self.path / "id"), ("/system/bin/", "/usr/bin/"),
            ("/proc/self/mounts", self.path / "mounts"),
            ("/proc/sys/kernel/random/boot_id", self.path / "boot_id"),
            ("/sys/firmware/devicetree/base/chosen", self.path / "chosen"),
            ("/sys/fs/pstore", self.directory),
        ):
            script = script.replace(old, str(new))
        capture = subprocess.run(["/usr/bin/bash", "-c", script], capture_output=True, timeout=4)
        return reader.decode(capture.returncode, capture.stdout, capture.stderr, BOOT), capture

    def test_ordered_exact_pmsg_and_samsung_console(self):
        for count in (1, 2, 3):
            with self.subTest(count=count):
                self.pmsg.write_text("".join(f"Y2Q-STAGE-V1 {TAG} {name}\n" for name in reader.STAGES[:count]))
                line = (f"[    0.000000]  [0:        swapper:    0] Kernel command line: "
                        f"codex.y2q_trace={TAG} private=never-export\n")
                self.console.write_text(line)
                result, capture = self.acquire()
                self.assertEqual(result["loader_stages"], list(reader.STAGES[:count]), capture)
                self.assertTrue(result["vendor_kernel_command_line"], capture)
                self.assertNotIn(b"private", capture.stdout)

    def test_duplicate_stale_oversized_indirect_and_wrong_boot_do_not_prove(self):
        line = f"Kernel command line: codex.y2q_trace={TAG}\n"
        self.console.write_text(line * 2)
        self.pmsg.write_text(f"Y2Q-STAGE-V1 {TAG} fdt-marked\n")
        result, _ = self.acquire()
        self.assertEqual((result["pmsg"], result["console"]), ("UNMATCHED", "UNMATCHED"))
        self.console.write_bytes(b"a" * (reader.CONSOLE + 1))
        self.pmsg.unlink()
        self.pmsg.symlink_to(self.console)
        self.assertEqual(self.acquire()[0]["pmsg"], "UNAVAILABLE")
        self.assertEqual(self.acquire()[0]["console"], "UNAVAILABLE")
        self.assertEqual(self.acquire(expected_boot="0" * 64)[1].returncode, 64)
        self.pmsg.unlink()
        self.console.unlink()
        self.assertEqual(self.acquire()[0]["pmsg"], "MISSING")
        (self.path / "mounts").write_text(f"tmpfs {self.directory} tmpfs rw 0 0\n")
        self.assertEqual(self.acquire()[0]["pmsg"], "UNAVAILABLE")

    def test_candidate_fdt_stops_reader_before_records(self):
        (self.path / "chosen/codex,y2q-uniloader-android-v1").touch()
        self.assertEqual(self.acquire()[1].returncode, 64)

    def test_failed_record_producer_cannot_publish_a_match(self):
        head = self.path / "head"
        head.write_text(f'#!/bin/sh\n/usr/bin/head "$@"\n[ "$2" != {reader.CONSOLE + 1} ]\n')
        head.chmod(0o700)
        self.console.write_text(f"Kernel command line: codex.y2q_trace={TAG}\n")
        self.assertEqual(self.acquire()[0]["console"], "UNAVAILABLE")


class OwnerTests(unittest.TestCase):
    def test_runtime_isolation_keeps_original_source_and_owner_binding(self):
        self.assertEqual(hashlib.sha256(stage.TEMPLATE.read_bytes()).hexdigest(), stage.TEMPLATE_SHA)
        source = stage.retained_runtime_source()
        self.assertIn(str(stage.SCRIPT.relative_to(ROOT)).encode(), source)
        self.assertNotIn(str(stage.TEMPLATE.relative_to(ROOT)).encode(), source)

    def test_fence_accepts_only_fixed_serial_argv_after_owned_return(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            health = {"serial_sha256": reader.sha256(b"fixture"), "boot_id_sha256": BOOT}
            final = {"health": health}
            intent = {"boot_sha256": BOOT}
            records = {"final-health.json": final, "prepared.json": {}, stage.INTENT: intent}
            engine = SimpleNamespace(read_json=lambda path, _label: records[path.name])
            runtime = Mock()
            runtime._require_live_transaction.return_value = {"run_dir": str(run)}
            argv = reader.argv("fixture", TAG, BOOT)
            with (patch.object(stage.owner, "engine", engine, create=True),
                  patch.object(stage.owner, "runtime", runtime, create=True),
                  patch.object(stage.owner, "pair", {"retained_stage": {"tag": TAG}}, create=True),
                  patch.object(stage.owner, "require_active"),
                  patch.object(stage, "make_intent", return_value=intent)):
                options = stage.capture_options()
                self.assertTrue(stage.allow_read(argv, run, stage.CAPTURE, options))
                with self.assertRaisesRegex(stage.owner.Stop, "command or binding"):
                    stage.allow_read(reader.argv("different", TAG, BOOT), run, stage.CAPTURE, options)
                with self.assertRaisesRegex(stage.owner.Stop, "command or binding"):
                    stage.allow_read(argv[:-1] + ["different"], run, stage.CAPTURE, options)
                (run / stage.RAW_NODE).touch()
                with self.assertRaisesRegex(stage.owner.Stop, "escaped exact final capture"):
                    stage.allow_read(argv, run, stage.CAPTURE, options)

    def test_read_is_attempted_once_before_healthy_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            final = {"rollback_transfer_completed": True, "health": {"boot_id_sha256": BOOT}}
            prepared = {"binding_sha256": "b" * 64, "binding": {"preflight": {}}}
            records = {}
            engine = SimpleNamespace(durable_json=lambda path, value: (path.touch(), records.update({path: value})),
                                     read_json=lambda path, _label: records[path],
                                     raw_capture=Mock())
            evidence = {"status": "CAPTURE_CUT"}
            with (patch.object(stage.owner, "engine", engine, create=True),
                  patch.object(stage.owner, "pair", {"retained_stage": {"tag": TAG}}, create=True),
                  patch.object(stage, "eligible_candidate", return_value="candidate"),
                  patch.object(stage, "make_intent", return_value={"boot_sha256": BOOT}),
                  patch.object(stage, "derive_evidence", return_value=evidence),
                  patch.object(stage.owner, "validated_current_serial", return_value="fixture"),
                  patch.object(stage.owner, "checked_terminal", return_value="final") as terminal):
                self.assertEqual(stage.checked_terminal(run, prepared, final), "final")
                self.assertEqual(stage.checked_terminal(run, prepared, final), "final")
                engine.raw_capture.acquire_command.assert_called_once()
                self.assertEqual(records[run / stage.EVIDENCE], evidence)
                self.assertEqual(terminal.call_count, 2)


if __name__ == "__main__":
    unittest.main()
