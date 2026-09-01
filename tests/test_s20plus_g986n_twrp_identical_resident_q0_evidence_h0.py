from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s20plus_g986n_twrp_identical_resident_q0_evidence_h0.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s20plus_g986n_twrp_identical_resident_q0_evidence_h0_tested",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S20PlusTwrpIdenticalResidentQ0EvidenceH0Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.run_id = "run-1234567890123456789"

    def success_stdout(self) -> bytes:
        m = self.module
        return (
            "schema=s20plus_g986n_twrp_identical_resident_write_backend_v1\n"
            "verdict=PROVED_IDENTICAL_RESIDENT_WRITE_READBACK\n"
            f"target={m.TARGET_PATH}\n"
            f"rdev={m.TARGET_RDEV}\n"
            "partname=boot\n"
            f"partition={m.TARGET_PARTITION}\n"
            f"size_bytes={m.TARGET_SIZE}\n"
            f"source_sha256={m.RESIDENT_SHA256}\n"
            f"preimage_sha256={m.RESIDENT_SHA256}\n"
            f"write_bytes={m.TARGET_SIZE}\n"
            "fsync_succeeded=1\n"
            f"readback_sha256={m.RESIDENT_SHA256}\n"
            "write_attempts=1\n"
            "reboot_count=0\n"
            "other_partition_writes=0\n"
        ).encode("ascii")

    def failure_stdout(
        self,
        *,
        stage: str = "preimage-hash",
        error: int = 84,
        write_started: int = 0,
        write_bytes: int = 0,
        fsync_attempted: int = 0,
        fsync_succeeded: int = 0,
    ) -> bytes:
        return (
            "schema=s20plus_g986n_twrp_identical_resident_write_backend_v1\n"
            "verdict=STOP_IDENTICAL_RESIDENT_WRITE_QUALIFICATION\n"
            f"stage={stage}\n"
            f"errno={error}\n"
            f"write_started={write_started}\n"
            f"write_bytes={write_bytes}\n"
            f"fsync_attempted={fsync_attempted}\n"
            f"fsync_succeeded={fsync_succeeded}\n"
            "reboot_count=0\n"
            "other_partition_writes=0\n"
        ).encode("ascii")

    def journal_payloads(
        self,
        capture: tuple[int, bytes, bytes] | None = None,
    ) -> list[dict]:
        m = self.module
        payloads = [
            {
                "target": m.TARGET,
                "backend_h0_owner_binding_sha256": m.BACKEND_H0_OWNER_BINDING_SHA256,
                "serial_sha256": "1" * 64,
                "topology_sha256": "2" * 64,
                "recovery_boot_id_sha256": "3" * 64,
                "prepared_at_ns": 1_000_000_000,
                "expires_at_ns": 901_000_000_000,
            },
            {
                "attempt": 1,
                "stage_dir": m.STAGE_DIR,
                "backend_sha256": m.BACKEND_SHA256,
                "resident_sha256": m.RESIDENT_SHA256,
            },
            {
                "attempt": 1,
                "stage_dir": m.STAGE_DIR,
                "child_names": [m.BACKEND_NAME, m.SOURCE_NAME],
                "backend_size": m.BACKEND_SIZE,
                "backend_sha256": m.BACKEND_SHA256,
                "backend_mode": "0500",
                "resident_size": m.TARGET_SIZE,
                "resident_sha256": m.RESIDENT_SHA256,
                "resident_mode": "0400",
                "partition_effects": 0,
            },
            {
                "attempt": 1,
                "source_boot_id_sha256": "3" * 64,
                "target_path": m.TARGET_PATH,
                "rdev": m.TARGET_RDEV,
                "partname": "boot",
                "partition_number": m.TARGET_PARTITION,
                "size_bytes": m.TARGET_SIZE,
                "preimage_sha256": m.RESIDENT_SHA256,
                "source_sha256": m.RESIDENT_SHA256,
                "backend_sha256": m.BACKEND_SHA256,
                "backend_invocations_max": 1,
                "replay_permitted": False,
            },
        ]
        if capture is not None:
            parsed = m.parse_backend_capture(*capture)
            payloads.append(
                {
                    "attempt": 1,
                    "capture": {
                        "returncode": parsed["command_returncode"],
                        "stdout_size": parsed["stdout_size"],
                        "stdout_sha256": parsed["stdout_sha256"],
                        "stderr_size": 0,
                    },
                    "parsed": parsed,
                }
            )
        return payloads

    def journal_nodes(
        self,
        count: int,
        capture: tuple[int, bytes, bytes] | None = None,
    ) -> list[bytes]:
        m = self.module
        payloads = self.journal_payloads(capture)
        nodes: list[bytes] = []
        predecessor = m.ZERO_HASH
        for index in range(count):
            node = m.make_node(
                self.run_id,
                index + 1,
                m.JOURNAL_KINDS[index],
                predecessor,
                payloads[index],
            )
            nodes.append(node)
            predecessor = hashlib.sha256(node).hexdigest()
        return nodes

    def test_exact_success_capture_is_proved_but_never_replayable(self):
        result = self.module.parse_backend_capture(0, self.success_stdout(), b"")
        self.assertEqual(
            result["classification"],
            "PROVED_IDENTICAL_RESIDENT_WRITE_READBACK",
        )
        self.assertTrue(result["write_started"])
        self.assertEqual(result["write_bytes"], self.module.TARGET_SIZE)
        self.assertTrue(result["fsync_succeeded"])
        self.assertTrue(result["readback_proved"])
        self.assertTrue(result["boot_partition_effect_proved"])
        self.assertFalse(result["backend_replay_permitted"])

    def test_success_framing_value_returncode_and_stderr_mutations_reject(self):
        exact = self.success_stdout()
        mutations = (
            (0, exact.replace(b"\n", b"\r\n", 1), b""),
            (0, exact[:-1], b""),
            (0, exact + b"extra=1\n", b""),
            (0, exact.replace(b"rdev=259:7", b"rdev=259:8"), b""),
            (0, exact.replace(self.module.RESIDENT_SHA256.encode(), b"0" * 64, 1), b""),
            (70, exact, b""),
            (0, exact, b"warning"),
            (True, exact, b""),
        )
        for capture in mutations:
            with self.subTest(capture=capture[0:1]):
                with self.assertRaises(self.module.EvidenceError):
                    self.module.parse_backend_capture(*capture)

    def test_pre_write_failure_is_zero_effect_but_backend_replay_false(self):
        result = self.module.parse_backend_capture(
            70, self.failure_stdout(), b""
        )
        self.assertEqual(
            result["classification"], "PRE_WRITE_REJECTED_ZERO_BOOT_EFFECT"
        )
        self.assertFalse(result["write_started"])
        self.assertEqual(result["write_bytes"], 0)
        self.assertFalse(result["fsync_attempted"])
        self.assertFalse(result["boot_partition_effect_proved"])
        self.assertFalse(result["backend_replay_permitted"])

    def test_write_and_post_write_failures_are_outcome_unproved(self):
        captures = (
            self.failure_stdout(
                stage="write",
                write_started=1,
                write_bytes=4096,
                fsync_attempted=1,
            ),
            self.failure_stdout(
                stage="write-fsync",
                write_started=1,
                write_bytes=self.module.TARGET_SIZE,
                fsync_attempted=1,
            ),
            self.failure_stdout(
                stage="write-fsync",
                write_started=1,
                write_bytes=self.module.TARGET_SIZE,
                fsync_attempted=1,
                fsync_succeeded=1,
            ),
            self.failure_stdout(
                stage="readback-hash",
                write_started=1,
                write_bytes=self.module.TARGET_SIZE,
                fsync_attempted=1,
                fsync_succeeded=1,
            ),
        )
        for stdout in captures:
            result = self.module.parse_backend_capture(70, stdout, b"")
            self.assertEqual(
                result["classification"], "WRITE_EFFECT_OUTCOME_UNPROVED"
            )
            self.assertFalse(result["boot_partition_effect_proved"])
            self.assertFalse(result["backend_replay_permitted"])

    def test_failure_counter_stage_and_decimal_inconsistency_reject(self):
        captures = (
            self.failure_stdout(stage="unknown"),
            self.failure_stdout(error=0),
            self.failure_stdout(write_started=0, write_bytes=1),
            self.failure_stdout(write_started=1, fsync_attempted=0),
            self.failure_stdout(
                stage="preimage-hash", write_started=1, fsync_attempted=1
            ),
            self.failure_stdout(
                stage="readback-hash",
                write_started=1,
                write_bytes=self.module.TARGET_SIZE - 1,
                fsync_attempted=1,
                fsync_succeeded=1,
            ),
            self.failure_stdout(error=84).replace(b"errno=84", b"errno=084"),
            self.failure_stdout(fsync_succeeded=1),
        )
        for stdout in captures:
            with self.assertRaises(self.module.EvidenceError):
                self.module.parse_backend_capture(70, stdout, b"")

    def test_empty_and_pre_write_prefixes_grant_no_authority(self):
        empty = self.module.validate_journal_prefix([])
        self.assertEqual(empty["state"], "EMPTY_NO_AUTHORITY")
        self.assertFalse(empty["write_attempt_consumed"])
        for count in (1, 2, 3):
            state = self.module.validate_journal_prefix(self.journal_nodes(count))
            self.assertEqual(state["state"], "BEFORE_WRITE_INTENT_NO_BOOT_EFFECT")
            self.assertFalse(state["write_attempt_consumed"])
            self.assertFalse(state["backend_replay_permitted"])
            self.assertFalse(state["system_boot_authorized_by_prefix"])

    def test_write_intent_without_result_consumes_attempt_and_forbids_replay(self):
        state = self.module.validate_journal_prefix(self.journal_nodes(4))
        self.assertEqual(
            state["state"],
            "WRITE_OUTCOME_UNPROVED_ATTEMPT_CONSUMED_NO_REPLAY",
        )
        self.assertTrue(state["write_attempt_consumed"])
        self.assertFalse(state["backend_replay_permitted"])
        self.assertFalse(state["boot_partition_effect_proved"])
        self.assertFalse(state["system_boot_authorized_by_prefix"])

    def test_success_result_prefix_is_pending_physical_health_not_terminal(self):
        capture = (0, self.success_stdout(), b"")
        state = self.module.validate_journal_prefix(
            self.journal_nodes(5, capture), backend_capture=capture
        )
        self.assertEqual(
            state["state"],
            "PROVED_BACKEND_WRITE_READBACK_PENDING_PHYSICAL_HEALTH",
        )
        self.assertTrue(state["write_attempt_consumed"])
        self.assertTrue(state["boot_partition_effect_proved"])
        self.assertFalse(state["backend_replay_permitted"])
        self.assertFalse(state["system_boot_authorized_by_prefix"])

    def test_zero_write_failure_after_intent_is_consumed_no_replay(self):
        capture = (70, self.failure_stdout(stage="source-hash"), b"")
        state = self.module.validate_journal_prefix(
            self.journal_nodes(5, capture), backend_capture=capture
        )
        self.assertEqual(
            state["state"],
            "PRE_WRITE_REJECTION_AFTER_CONSUMED_INTENT_NO_REPLAY",
        )
        self.assertTrue(state["write_attempt_consumed"])
        self.assertFalse(state["backend_replay_permitted"])

    def test_partial_write_result_is_unproved_and_no_replay(self):
        capture = (
            70,
            self.failure_stdout(
                stage="write",
                write_started=1,
                write_bytes=4096,
                fsync_attempted=1,
                fsync_succeeded=1,
            ),
            b"",
        )
        state = self.module.validate_journal_prefix(
            self.journal_nodes(5, capture), backend_capture=capture
        )
        self.assertEqual(state["state"], "WRITE_EFFECT_OUTCOME_UNPROVED_NO_REPLAY")
        self.assertTrue(state["write_attempt_consumed"])
        self.assertFalse(state["boot_partition_effect_proved"])

    def test_chain_ordinal_kind_run_id_and_canonical_mutations_reject(self):
        exact = self.journal_nodes(4)
        mutations: list[list[bytes]] = []
        value = json.loads(exact[1])
        value["predecessor_sha256"] = "f" * 64
        mutations.append([exact[0], self.module.canonical(value), *exact[2:]])
        value = json.loads(exact[2])
        value["ordinal"] = 2
        mutations.append([*exact[:2], self.module.canonical(value), exact[3]])
        value = json.loads(exact[2])
        value["kind"] = "write-intent"
        mutations.append([*exact[:2], self.module.canonical(value), exact[3]])
        value = json.loads(exact[2])
        value["run_id"] = "run-0000000000000000000"
        mutations.append([*exact[:2], self.module.canonical(value), exact[3]])
        mutations.append([b" " + exact[0], *exact[1:]])
        for nodes in mutations:
            with self.assertRaises(self.module.EvidenceError):
                self.module.validate_journal_prefix(nodes)

    def test_duplicate_key_payload_type_and_binding_mutations_reject(self):
        exact = self.journal_nodes(4)
        duplicate = exact[0].replace(
            b'{"kind":"prepared",',
            b'{"kind":"prepared","kind":"prepared",',
            1,
        )
        with self.assertRaisesRegex(self.module.EvidenceError, "duplicate"):
            self.module.strict_node(duplicate)
        mutations = []
        value = json.loads(exact[0])
        value["payload"]["backend_h0_owner_binding_sha256"] = "0" * 64
        mutations.append([self.module.canonical(value)])
        value = json.loads(exact[2])
        value["payload"]["partition_effects"] = False
        mutations.append([*exact[:2], self.module.canonical(value)])
        value = json.loads(exact[3])
        value["payload"]["replay_permitted"] = 0
        mutations.append([*exact[:3], self.module.canonical(value)])
        value = json.loads(exact[3])
        value["payload"]["source_boot_id_sha256"] = "4" * 64
        mutations.append([*exact[:3], self.module.canonical(value)])
        for nodes in mutations:
            with self.assertRaises(self.module.EvidenceError):
                self.module.validate_journal_prefix(nodes)

    def test_backend_result_bool_integer_substitutions_reject(self):
        capture = (0, self.success_stdout(), b"")
        exact = self.journal_nodes(5, capture)
        variants = []
        value = json.loads(exact[4])
        value["payload"]["capture"]["returncode"] = False
        variants.append([*exact[:4], self.module.canonical(value)])
        value = json.loads(exact[4])
        value["payload"]["parsed"]["write_started"] = 1
        value["payload"]["parsed"]["fsync_attempted"] = 1
        value["payload"]["parsed"]["fsync_succeeded"] = 1
        value["payload"]["parsed"]["readback_proved"] = 1
        value["payload"]["parsed"]["boot_partition_effect_proved"] = 1
        value["payload"]["parsed"]["backend_replay_permitted"] = 0
        variants.append([*exact[:4], self.module.canonical(value)])
        for nodes in variants:
            with self.assertRaises(self.module.EvidenceError):
                self.module.validate_journal_prefix(
                    nodes,
                    backend_capture=capture,
                )

    def test_orphan_missing_or_mismatched_backend_capture_rejects(self):
        success = (0, self.success_stdout(), b"")
        nodes = self.journal_nodes(5, success)
        with self.assertRaises(self.module.EvidenceError):
            self.module.validate_journal_prefix(nodes)
        with self.assertRaises(self.module.EvidenceError):
            self.module.validate_journal_prefix([], backend_capture=success)
        wrong = (70, self.failure_stdout(), b"")
        with self.assertRaises(self.module.EvidenceError):
            self.module.validate_journal_prefix(nodes, backend_capture=wrong)

    def test_render_plan_and_cli_are_host_only_inactive(self):
        plan = self.module.render_plan()
        self.assertEqual(plan["status"], "H0_PASS_GO_NOT_ACTIVE")
        self.assertFalse(plan["active"])
        self.assertFalse(plan["live_authority"])
        self.assertFalse(plan["backend_replay_permitted"])
        self.assertFalse(plan["system_boot_authorized"])
        self.assertFalse(plan["durable_publisher_implemented"])
        self.assertEqual(plan["device_commands"], [])
        self.assertEqual(plan["device_writes"], [])
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--render-plan"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            timeout=10,
            text=True,
        )
        self.assertEqual(json.loads(completed.stdout), plan)
        source = SCRIPT.read_text(encoding="utf-8")
        for forbidden in (
            "import subprocess",
            "os.system",
            "Popen(",
            "--connected",
            "--prepare",
            "--execute",
            "/usr/bin/adb",
            "odin4",
        ):
            self.assertNotIn(forbidden, source)
        with mock.patch.object(
            self.module,
            "render_plan",
            side_effect=AssertionError("invalid CLI must stop"),
        ):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                with mock.patch.object(sys, "argv", [str(SCRIPT)]):
                    self.module.main()


if __name__ == "__main__":
    unittest.main()
