import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s20plus_n3u0_attended_f1_evidence_h0.py"
)


def load_module():
    specification = importlib.util.spec_from_file_location(
        "s20plus_n3u0_attended_f1_evidence_h0_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


class S20PlusN3U0EvidenceH0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.journal = cls.module._load_journal()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.runs = self.root / "runs"
        self.evidence = self.root / "evidence"
        self.runs.mkdir(mode=0o700)
        self.evidence.mkdir(mode=0o700)
        self.patches = [
            mock.patch.object(self.module, "JOURNAL_RUNS_ROOT", self.runs),
            mock.patch.object(self.module, "EVIDENCE_ROOT", self.evidence),
        ]
        for patch in self.patches:
            patch.start()
        self.run_dir = self.journal.create_prepared(
            self.runs,
            {
                "serial_sha256": "1" * 64,
                "topology_sha256": "2" * 64,
                "boot_id_sha256": "3" * 64,
            },
            "4" * 64,
        )
        self.journal.begin_initial_download(self.run_dir)
        self.active = mock.patch.object(self.module, "EVIDENCE_ACTIVE", True)

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.temporary.cleanup()

    def publish(self, **changes):
        values = {
            "run_dir": self.run_dir,
            "operation": "initial-download-reboot",
            "ordinal": 1,
            "argv": ["/fixed/adb", "-s", "PRIVATE_SERIAL", "reboot", "download"],
            "timeout_seconds": 20,
            "output_limit": 65536,
            "returncode": 0,
            "stdout": b"",
            "stderr": b"",
        }
        values.update(changes)
        return self.module.publish_command_result(**values)

    def test_render_plan_is_dormant_and_non_authorizing(self):
        plan = self.module.render_plan()
        self.assertEqual(
            plan["status"], "H0_DURABLE_EVIDENCE_PASS_GO_NOT_ACTIVE"
        )
        self.assertFalse(plan["active"])
        self.assertFalse(plan["live_authority"])
        self.assertFalse(plan["backend_exposed"])
        self.assertTrue(plan["raw_evidence_durable"])
        self.assertFalse(plan["integrated_live_consumer"])
        self.assertEqual(plan["cli"], ["--render-plan"])
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["partition_transfers"], [])

    def test_unmocked_render_plan_loads_exact_closure(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--render-plan"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn('"active": false', completed.stdout)
        self.assertIn('"raw_evidence_durable": true', completed.stdout)

    def test_publication_and_inspection_gate_before_any_write(self):
        before = list(self.evidence.iterdir())
        with self.assertRaisesRegex(self.module.EvidenceError, "not active"):
            self.publish()
        with self.assertRaisesRegex(self.module.EvidenceError, "not active"):
            self.module.inspect_operation(
                self.run_dir, "initial-download-reboot", 1
            )
        self.assertEqual(list(self.evidence.iterdir()), before)

    def test_direct_file_helpers_gate_and_reject_path_escape(self):
        valid = (
            self.evidence
            / self.run_dir.name
            / "initial-download-reboot-01.stdout"
        )
        with self.assertRaisesRegex(self.module.EvidenceError, "not active"):
            self.module._ensure_evidence_run(self.run_dir.name)
        with self.assertRaisesRegex(self.module.EvidenceError, "not active"):
            self.module._durable_blob(valid, b"X")
        with self.assertRaisesRegex(self.module.EvidenceError, "not active"):
            self.module._read_blob(valid, "probe")
        self.assertEqual(list(self.evidence.iterdir()), [])
        with self.active:
            with self.assertRaisesRegex(self.module.EvidenceError, "run ID is malformed"):
                self.module._ensure_evidence_run("../escaped")
            evidence_run = self.module._ensure_evidence_run(self.run_dir.name)
            with self.assertRaisesRegex(
                self.module.EvidenceError, "outside the fixed namespace"
            ):
                self.module._durable_blob(evidence_run / "arbitrary-name", b"X")
            foreign = self.root / "foreign" / self.run_dir.name
            foreign.mkdir(parents=True, mode=0o700)
            with self.assertRaisesRegex(
                self.module.EvidenceError, "outside the fixed namespace"
            ):
                self.module._durable_blob(
                    foreign / "initial-download-reboot-01.stdout", b"X"
                )

    def test_complete_command_evidence_binds_raw_bytes_and_intent(self):
        with self.active:
            written = self.publish(stdout=b"OUT", stderr=b"ERR")
            state = self.module.inspect_operation(
                self.run_dir, "initial-download-reboot", 1
            )
        self.assertEqual(state["state"], "complete")
        self.assertFalse(state["replay_permitted"])
        self.assertEqual(state["result"], written)
        evidence_run = self.evidence / self.run_dir.name
        self.assertEqual(
            (evidence_run / "initial-download-reboot-01.stdout").read_bytes(), b"OUT"
        )
        self.assertEqual(
            (evidence_run / "initial-download-reboot-01.stderr").read_bytes(), b"ERR"
        )
        for child in evidence_run.iterdir():
            self.assertEqual(stat.S_IMODE(child.stat().st_mode), 0o400)

    def test_complete_read_api_returns_exact_raw_and_supports_odin_bound(self):
        with self.active:
            self.publish(
                output_limit=8 * 1024 * 1024,
                stdout=b"ODIN_OK",
                stderr=b"",
            )
            complete = self.module.read_complete_operation(
                self.run_dir, "initial-download-reboot", 1
            )
        self.assertEqual(complete["inspection"]["state"], "complete")
        self.assertEqual(complete["stdout"], b"ODIN_OK")
        self.assertEqual(complete["stderr"], b"")

    def test_existing_evidence_forbids_command_republication(self):
        with self.active:
            self.publish()
            with self.assertRaisesRegex(self.module.EvidenceError, "replay is forbidden"):
                self.publish()

    def test_intent_without_evidence_is_consumed_not_replayable(self):
        with self.active:
            state = self.module.inspect_operation(
                self.run_dir, "initial-download-reboot", 1
            )
        self.assertEqual(state["state"], "intent-consumed-evidence-absent")
        self.assertFalse(state["replay_permitted"])

    def test_stdout_only_and_stdout_stderr_cuts_are_uncertain_consumed(self):
        with self.active:
            evidence_run = self.module._ensure_evidence_run(self.run_dir.name)
            stdout = evidence_run / "initial-download-reboot-01.stdout"
            stderr = evidence_run / "initial-download-reboot-01.stderr"
            self.module._durable_blob(stdout, b"OUT")
            first = self.module.inspect_operation(
                self.run_dir, "initial-download-reboot", 1
            )
            self.assertEqual(first["state"], "uncertain-consumed")
            self.assertEqual(first["published"], [stdout.name])
            self.module._durable_blob(stderr, b"ERR")
            second = self.module.inspect_operation(
                self.run_dir, "initial-download-reboot", 1
            )
        self.assertEqual(second["state"], "uncertain-consumed")
        self.assertFalse(second["replay_permitted"])

    def test_stderr_without_stdout_is_impossible(self):
        with self.active, self.assertRaisesRegex(
            self.module.EvidenceError, "publication order is impossible"
        ):
            evidence_run = self.module._ensure_evidence_run(self.run_dir.name)
            self.module._durable_blob(
                evidence_run / "initial-download-reboot-01.stderr", b"ERR"
            )
            self.module.inspect_operation(
                self.run_dir, "initial-download-reboot", 1
            )

    def test_result_without_both_raw_files_is_impossible(self):
        with self.active, self.assertRaisesRegex(
            self.module.EvidenceError, "publication order is impossible"
        ):
            evidence_run = self.module._ensure_evidence_run(self.run_dir.name)
            self.module._durable_blob(
                evidence_run / "initial-download-reboot-01.result.json", b"{}\n"
            )
            self.module.inspect_operation(
                self.run_dir, "initial-download-reboot", 1
            )

    def test_raw_byte_drift_rejects_complete_receipt(self):
        with self.active:
            self.publish(stdout=b"OUT")
        path = self.evidence / self.run_dir.name / "initial-download-reboot-01.stdout"
        path.chmod(0o600)
        path.write_bytes(b"FORGED")
        path.chmod(0o400)
        with self.active, self.assertRaisesRegex(
            self.module.EvidenceError, "raw bytes differ"
        ):
            self.module.inspect_operation(
                self.run_dir, "initial-download-reboot", 1
            )

    def test_run_and_all_files_cannot_drift_from_root_owner_group(self):
        with self.active:
            self.publish()
        evidence_run = self.evidence / self.run_dir.name
        alternate_groups = [value for value in os.getgroups() if value != os.getgid()]
        self.assertTrue(alternate_groups, "host fixture requires a supplementary group")
        alternate = alternate_groups[0]
        for child in evidence_run.iterdir():
            os.chown(child, -1, alternate)
        os.chown(evidence_run, -1, alternate)
        with self.active, self.assertRaisesRegex(
            self.module.EvidenceError, "run owner differs"
        ):
            self.module.inspect_operation(
                self.run_dir, "initial-download-reboot", 1
            )

    def test_duplicate_json_key_and_bool_integer_substitution_reject(self):
        with self.active:
            self.publish()
        result = (
            self.evidence
            / self.run_dir.name
            / "initial-download-reboot-01.result.json"
        )
        value = json.loads(result.read_text())
        duplicate = result.read_text().replace(
            '"ordinal":1', '"ordinal":1,"ordinal":1'
        )
        result.chmod(0o600)
        result.write_text(duplicate)
        result.chmod(0o400)
        with self.active, self.assertRaisesRegex(self.module.EvidenceError, "malformed"):
            self.module.inspect_operation(
                self.run_dir, "initial-download-reboot", 1
            )
        result.chmod(0o600)
        value["returncode"] = False
        result.write_bytes(self.module.canonical_bytes(value))
        result.chmod(0o400)
        with self.active, self.assertRaisesRegex(self.module.EvidenceError, "malformed"):
            self.module.inspect_operation(
                self.run_dir, "initial-download-reboot", 1
            )

    def test_symlink_hardlink_and_unknown_node_reject(self):
        with self.active:
            evidence_run = self.module._ensure_evidence_run(self.run_dir.name)
        target = self.root / "target"
        target.write_bytes(b"x")
        symlink = evidence_run / "initial-download-reboot-01.stdout"
        symlink.symlink_to(target)
        with self.active, self.assertRaisesRegex(self.module.EvidenceError, "indirect"):
            self.module.inspect_operation(
                self.run_dir, "initial-download-reboot", 1
            )
        symlink.unlink()
        target.chmod(0o400)
        os.link(target, symlink)
        with self.active, self.assertRaisesRegex(self.module.EvidenceError, "indirect"):
            self.module.inspect_operation(
                self.run_dir, "initial-download-reboot", 1
            )
        symlink.unlink()
        unknown = evidence_run / "foreign"
        unknown.write_bytes(b"x")
        unknown.chmod(0o400)
        with self.active, self.assertRaisesRegex(self.module.EvidenceError, "unknown"):
            self.module.inspect_operation(
                self.run_dir, "initial-download-reboot", 1
            )

    def test_atomic_link_failure_exposes_no_final_name(self):
        with self.active:
            evidence_run = self.module._ensure_evidence_run(self.run_dir.name)
            path = evidence_run / "initial-download-reboot-01.stdout"
            with mock.patch.object(self.module, "_LINKAT", return_value=-1):
                with self.assertRaises(OSError):
                    self.module._durable_blob(path, b"OUT")
        self.assertFalse(os.path.lexists(path))

    def test_wrong_run_path_and_missing_predecessor_reject(self):
        foreign = self.root / self.run_dir.name
        foreign.mkdir(mode=0o700)
        with self.active, self.assertRaisesRegex(self.module.EvidenceError, "path is not fixed"):
            self.module.publish_command_result(
                foreign,
                "initial-download-reboot",
                1,
                ["x"],
                1,
                1,
                0,
                b"",
                b"",
            )
        with self.active, self.assertRaisesRegex(
            self.module.EvidenceError, "lacks its durable predecessor"
        ):
            self.module.publish_command_result(
                self.run_dir,
                "candidate-transfer",
                1,
                ["x"],
                1,
                1,
                0,
                b"",
                b"",
            )

    def test_source_drift_rejects_binding(self):
        changed = dict(self.module.SOURCES["backend"])
        changed["sha256"] = "0" * 64
        with mock.patch.dict(self.module.SOURCES, {"backend": changed}, clear=False):
            with self.assertRaisesRegex(self.module.EvidenceError, "hash differs"):
                self.module.source_receipts()
            with self.active, self.assertRaisesRegex(
                self.module.EvidenceError, "hash differs"
            ):
                self.publish()
            self.assertEqual(list(self.evidence.iterdir()), [])

    def test_source_drift_prevents_complete_evidence_certification(self):
        with self.active:
            self.publish()
        changed = dict(self.module.SOURCES["integration"])
        changed["sha256"] = "0" * 64
        with mock.patch.dict(
            self.module.SOURCES, {"integration": changed}, clear=False
        ):
            with self.active, self.assertRaisesRegex(
                self.module.EvidenceError, "hash differs"
            ):
                self.module.inspect_operation(
                    self.run_dir, "initial-download-reboot", 1
                )


if __name__ == "__main__":
    unittest.main()
