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
            [["nr_processes,nr_running"], ["get_taint", "test_taint"], ["vfs-bundle:soc-fingerprint"]],
            max_batch_size=30,
        )

        self.assertEqual(
            batches,
            (
                ("nr_processes", "nr_running"),
                ("get_taint", "test_taint"),
                ("vfs-bundle:soc-fingerprint",),
            ),
        )

    def test_parse_batches_rejects_unknown_and_oversized_batches(self) -> None:
        with self.assertRaisesRegex(resident.ResidentSessionError, "unsupported call-proof"):
            resident.parse_batches([["not_a_symbol"]], max_batch_size=30)

        with self.assertRaisesRegex(resident.ResidentSessionError, "max bounded size"):
            resident.parse_batches([["nr_processes", "nr_running"]], max_batch_size=1)

        with self.assertRaisesRegex(resident.ResidentSessionError, "unsupported"):
            resident.parse_batches([["vfs-bundle:not-a-bundle"]], max_batch_size=30)

    def test_parse_batches_rejects_single_target_resident_session(self) -> None:
        with self.assertRaisesRegex(resident.ResidentSessionError, "single-target resident runs are forbidden"):
            resident.parse_batches([["pid_task"]], max_batch_size=30)

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

    def test_run_health_check_retries_selftest_body_fragmentation(self) -> None:
        args = argparse.Namespace(
            host="127.0.0.1",
            port=54321,
            health_timeout=1.0,
            health_retries=1,
            bridge_restart_timeout=1.0,
        )
        calls: list[tuple[str, object]] = []
        original_run = resident.a90ctl.run_cmdv1_command
        original_restart = resident.run_subprocess

        def ok_result(command: str, text: str) -> object:
            return resident.a90ctl.ProtocolResult(
                begin={"cmd": command},
                end={"cmd": command, "rc": "0", "status": "ok"},
                text=text,
            )

        selftest_attempts = 0

        def fake_run_cmdv1(host, port, timeout, command):  # noqa: ANN001
            nonlocal selftest_attempts
            del host, port, timeout
            name = command[0]
            calls.append(("cmd", name))
            if name == "selftest":
                selftest_attempts += 1
                if selftest_attempts == 1:
                    return ok_result("selftest", "A90P1 END seq=1 cmd=selftest rc=0 status=ok")
                return ok_result("selftest", "selftest: pass=11 warn=1 fail=0\nA90P1 END")
            return ok_result(name, f"{name}: ok\nA90P1 END")

        def fake_run_subprocess(command, *, cwd, timeout, output_path):  # noqa: ANN001
            del cwd, timeout
            calls.append(("restart", Path(output_path).name))
            Path(output_path).write_text(json.dumps({"ok": True, "command": command}), encoding="utf-8")

        resident.a90ctl.run_cmdv1_command = fake_run_cmdv1
        resident.run_subprocess = fake_run_subprocess
        self.addCleanup(lambda: setattr(resident.a90ctl, "run_cmdv1_command", original_run))
        self.addCleanup(lambda: setattr(resident, "run_subprocess", original_restart))

        with tempfile.TemporaryDirectory() as td:
            payload = resident.run_health_check(args, Path(td), "rollback")
            self.assertIn("fail=0", payload["commands"]["selftest"]["text"])
            saved = json.loads((Path(td) / "rollback-health.json").read_text())
            self.assertEqual(len(saved["retry_errors"]["selftest"]), 1)
            self.assertEqual(
                saved["retry_errors"]["selftest"][0]["exception"],
                "rollback selftest did not report fail=0",
            )
        self.assertIn(("restart", "rollback-selftest-health-bridge-restart-01.json"), calls)

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

    def test_run_resident_session_flashes_once_and_warm_reboots_each_batch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            args = argparse.Namespace(
                run_dir=root,
                dry_run=False,
                candidate_image=Path("v1-repl.img"),
                candidate_sha256="c" * 64,
                rollback_image=Path("v2321.img"),
                rollback_sha256="r" * 64,
                map=Path("System.map"),
                image=Path("v1-repl.img"),
            )
            calls: list[tuple[str, object]] = []
            originals = {
                "preflight": resident.preflight,
                "run_health_check": resident.run_health_check,
                "run_flash": resident.run_flash,
                "run_repl_selftest": resident.run_repl_selftest,
                "send_warm_reboot": resident.send_warm_reboot,
                "restart_bridge_and_wait_health": resident.restart_bridge_and_wait_health,
                "run_one_batch": resident.run_one_batch,
                "run_rollback_flash": resident.run_rollback_flash,
                "load_system_map": resident.a90_repl.load_system_map,
                "load_static_image": resident.a90_repl.load_static_image,
            }

            def restore() -> None:
                resident.preflight = originals["preflight"]
                resident.run_health_check = originals["run_health_check"]
                resident.run_flash = originals["run_flash"]
                resident.run_repl_selftest = originals["run_repl_selftest"]
                resident.send_warm_reboot = originals["send_warm_reboot"]
                resident.restart_bridge_and_wait_health = originals["restart_bridge_and_wait_health"]
                resident.run_one_batch = originals["run_one_batch"]
                resident.run_rollback_flash = originals["run_rollback_flash"]
                resident.a90_repl.load_system_map = originals["load_system_map"]
                resident.a90_repl.load_static_image = originals["load_static_image"]

            self.addCleanup(restore)

            def fake_preflight(unused_args, batches):  # noqa: ANN001
                calls.append(("preflight", [list(batch) for batch in batches]))
                return {"ok": True, "batches": [list(batch) for batch in batches]}

            def fake_health(unused_args, unused_out_dir, label):  # noqa: ANN001
                calls.append(("health", label))
                return {"label": label}

            def fake_flash(unused_args, image, sha256, *, output_path, from_native):  # noqa: ANN001
                del output_path
                calls.append(("flash", (str(image), sha256, from_native)))

            def fake_selftest(unused_args, unused_symbols, unused_image, unused_out_dir, *, prefix):  # noqa: ANN001
                calls.append(("selftest", prefix))

            def fake_warm_reboot(unused_args, unused_out_dir, batch_index):  # noqa: ANN001
                calls.append(("warm_reboot", batch_index))

            def fake_restart_health(unused_args, unused_out_dir, label):  # noqa: ANN001
                calls.append(("warm_health", label))
                return {"label": label}

            def fake_batch(unused_args, unused_symbols, unused_image, batch, batch_index, unused_run_dir):  # noqa: ANN001
                calls.append(("batch", (batch_index, tuple(batch))))
                return {"ok": True, "completed_target_count": len(batch)}

            def fake_rollback(unused_args, unused_run_dir, stem):  # noqa: ANN001
                calls.append(("rollback", stem))

            resident.preflight = fake_preflight
            resident.run_health_check = fake_health
            resident.run_flash = fake_flash
            resident.run_repl_selftest = fake_selftest
            resident.send_warm_reboot = fake_warm_reboot
            resident.restart_bridge_and_wait_health = fake_restart_health
            resident.run_one_batch = fake_batch
            resident.run_rollback_flash = fake_rollback
            resident.a90_repl.load_system_map = lambda unused_path: {}
            resident.a90_repl.load_static_image = lambda unused_path: object()

            rc = resident.run_resident_session(args, (("nr_processes",), ("get_taint",)))

            self.assertEqual(rc, 0)
            self.assertEqual(
                [call for call in calls if call[0] == "flash"],
                [("flash", ("v1-repl.img", "c" * 64, True))],
            )
            self.assertEqual(
                [call for call in calls if call[0] == "rollback"],
                [("rollback", "rollback-flash")],
            )
            self.assertEqual(
                [call for call in calls if call[0] in {"warm_reboot", "batch"}],
                [
                    ("warm_reboot", 1),
                    ("batch", (1, ("nr_processes",))),
                    ("warm_reboot", 2),
                    ("batch", (2, ("get_taint",))),
                ],
            )
            timeline = json.loads((root / "timeline.json").read_text())
            self.assertEqual(set(timeline), {"events"})
            event_names = [event["name"] for event in timeline["events"]]
            for required in resident.REQUIRED_TIMELINE_EVENTS:
                self.assertIn(required, event_names)
            self.assertLess(event_names.index("batch_001_warm_reboot_start"),
                            event_names.index("batch_001_live_start"))
            self.assertLess(event_names.index("batch_002_warm_reboot_start"),
                            event_names.index("batch_002_live_start"))
            summary = json.loads((root / "resident-session-summary.json").read_text())
            self.assertEqual(summary["flash_count"], 2)
            self.assertTrue(summary["candidate_flashed_once"])
            self.assertTrue(summary["rollback_flashed_once"])
            self.assertTrue(summary["warm_reboot_between_batches"])

    def test_run_one_batch_dispatches_call_proofs_and_vfs_bundles_with_flush(self) -> None:
        args = argparse.Namespace(
            host="127.0.0.1",
            port=54321,
            repl_timeout=1.0,
            dmesg_tail=8,
            safe_op_retries=0,
            retry_delay_sec=0.0,
            alloc_size=0x1000,
            max_expected_return=None,
            source_root=Path("kernel-source"),
            gfp_header=Path("gfp.h"),
            gfp=None,
        )
        calls: list[tuple[str, str]] = []
        originals = {
            "run_call_proof": resident.a90_repl.run_call_proof,
            "run_vfs_read_bundle": resident.a90_repl.run_vfs_read_bundle,
        }

        def restore() -> None:
            resident.a90_repl.run_call_proof = originals["run_call_proof"]
            resident.a90_repl.run_vfs_read_bundle = originals["run_vfs_read_bundle"]

        self.addCleanup(restore)

        def fake_call_proof(unused_session, unused_symbols, unused_image, target, **kwargs):  # noqa: ANN001
            del kwargs
            calls.append(("call-proof", target))
            return {"ok": True, "decision": f"call-{target}", "target": target}, {"private": target}

        def fake_vfs_bundle(unused_session, unused_symbols, unused_image, bundle, **kwargs):  # noqa: ANN001
            del kwargs
            calls.append(("vfs-bundle", bundle))
            return {"ok": True, "decision": f"bundle-{bundle}", "bundle": bundle}, {"private": bundle}

        resident.a90_repl.run_call_proof = fake_call_proof
        resident.a90_repl.run_vfs_read_bundle = fake_vfs_bundle

        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            summary = resident.run_one_batch(
                args,
                {},
                object(),
                ("nr_processes", "vfs-bundle:soc-fingerprint"),
                1,
                run_dir,
            )

            self.assertTrue(summary["ok"])
            self.assertEqual(summary["completed_target_count"], 2)
            self.assertEqual(calls, [("call-proof", "nr_processes"), ("vfs-bundle", "soc-fingerprint")])
            first = json.loads((run_dir / "batch-001/target-results/001-nr_processes.json").read_text())
            second = json.loads(
                (run_dir / "batch-001/target-results/002-vfs-bundle_soc-fingerprint.json").read_text()
            )
            self.assertEqual(first["summary"]["decision"], "call-nr_processes")
            self.assertEqual(second["summary"]["decision"], "bundle-soc-fingerprint")


if __name__ == "__main__":
    unittest.main()
