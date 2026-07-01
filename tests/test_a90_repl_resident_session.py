"""Host-only tests for the REPL resident-session orchestrator."""

from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_script


resident = load_script("workspace/public/src/scripts/revalidation/a90_repl_resident_session.py")


def base_args() -> argparse.Namespace:
    return argparse.Namespace(
        host="127.0.0.1",
        port=54321,
        flash_bridge_timeout=180.0,
        recovery_timeout=180.0,
        bridge_restart_timeout=12.0,
    )


class A90ReplResidentSessionTests(unittest.TestCase):
    def test_parse_batches_accepts_repeated_and_comma_targets(self) -> None:
        batches = resident.parse_batches(
            [["nr_processes,nr_running"], ["get_taint", "test_taint"]],
            max_batch_size=30,
        )

        self.assertEqual(
            batches,
            (("nr_processes", "nr_running"), ("get_taint", "test_taint")),
        )

    def test_parse_batches_rejects_unknown_and_oversized_batches(self) -> None:
        with self.assertRaisesRegex(resident.ResidentSessionError, "unsupported call-proof"):
            resident.parse_batches([["not_a_symbol"]], max_batch_size=30)

        with self.assertRaisesRegex(resident.ResidentSessionError, "max bounded size"):
            resident.parse_batches([["nr_processes", "nr_running"]], max_batch_size=1)

    def test_flash_command_uses_checked_native_init_flash_helper(self) -> None:
        args = base_args()
        command = resident.flash_command(args, Path("candidate.img"), "a" * 64)

        self.assertIn("native_init_flash.py", command[1])
        self.assertIn("--from-native", command)
        self.assertIn("--verify-protocol", command)
        self.assertIn("selftest", command)
        self.assertIn("--adb", command)
        self.assertIn("--expect-sha256", command)
        self.assertIn("a" * 64, command)
        self.assertEqual(command[-1], "candidate.img")

        direct = resident.flash_command(args, Path("rollback.img"), "b" * 64, from_native=False)
        self.assertNotIn("--from-native", direct)
        self.assertIn("native_init_flash.py", direct[1])
        self.assertEqual(direct[-1], "rollback.img")

    def test_bridge_restart_command_places_options_after_subcommand(self) -> None:
        command = resident.bridge_restart_command(base_args())

        self.assertIn("a90_bridge.py", command[1])
        self.assertEqual(command[2], "restart")
        self.assertGreater(command.index("--host"), command.index("restart"))
        self.assertGreater(command.index("--port"), command.index("restart"))

    def test_mark_event_writes_only_canonical_events_schema(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            events: list[dict[str, str]] = []
            resident.mark_event(root, events, "candidate_flash_start")

            payload = json.loads((root / "timeline.json").read_text())
            self.assertEqual(set(payload), {"events"})
            self.assertEqual(set(payload["events"][0]), {"name", "timestamp_utc"})
            self.assertEqual(payload["events"][0]["name"], "candidate_flash_start")

    def test_flush_target_result_writes_per_target_json_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            batch_dir = Path(td)
            resident.flush_target_result(
                batch_dir,
                batch_index=1,
                ordinal=1,
                target="nr_processes",
                summary={"ok": True, "target": "nr_processes"},
                private={"runtime": "0xffffff8000000000"},
            )

            target_path = batch_dir / "target-results" / "001-nr_processes.json"
            payload = json.loads(target_path.read_text())
            self.assertTrue(payload["summary"]["ok"])
            self.assertEqual(payload["target"], "nr_processes")
            self.assertEqual(payload["_private"]["runtime"], "0xffffff8000000000")

            index_lines = (batch_dir / "target-results.jsonl").read_text().splitlines()
            self.assertEqual(len(index_lines), 1)
            index = json.loads(index_lines[0])
            self.assertEqual(index["path"], "target-results/001-nr_processes.json")
            self.assertTrue(index["ok"])

    def test_validate_timeline_requires_eight_session_phase_events(self) -> None:
        events = [{"name": name, "timestamp_utc": "2026-07-01T00:00:00+00:00"}
                  for name in resident.REQUIRED_TIMELINE_EVENTS]
        self.assertEqual(resident.validate_timeline(events), [])

        missing = events[:-1]
        errors = resident.validate_timeline(missing)
        self.assertTrue(any("rollback_boot_ready" in item for item in errors))

    def test_send_warm_reboot_rejects_busy_without_silent_batch_continue(self) -> None:
        args = argparse.Namespace(
            host="127.0.0.1",
            port=54321,
            warm_reboot_command_timeout=1.0,
        )
        calls: list[str] = []
        original = resident.a90ctl.bridge_exchange

        def fake_bridge_exchange(host, port, line, timeout, **kwargs):  # noqa: ANN001
            del host, port, timeout, kwargs
            calls.append(line)
            if line == "hide":
                return "[busy] auto menu active; hide requested"
            return "[busy] auto menu active; hide/q before dangerous command"

        resident.a90ctl.bridge_exchange = fake_bridge_exchange
        self.addCleanup(lambda: setattr(resident.a90ctl, "bridge_exchange", original))

        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(resident.ResidentSessionError, "warm reboot was rejected"):
                resident.send_warm_reboot(args, Path(td), 1)
            payload = json.loads((Path(td) / "batch-001-warm-reboot-send.json").read_text())
            self.assertIn("[busy]", payload["text"])
        self.assertEqual(calls, ["hide", "reboot"])


if __name__ == "__main__":
    unittest.main()
