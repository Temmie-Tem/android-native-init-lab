"""Host-only tests for the A90 on-device durable evidence contract.

The parsing tests are written as regressions against the observer defect class
that cost this campaign three automatic-handoff ordinals: every one of them was
a host-side over-specification of what normal device output looks like. Each
"permissive about shape" test below names the defect it stands in for.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/server-distro"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a90_ondevice_evidence_v1 as evidence  # noqa: E402


RUN = "a90-d1-attended-20260807-02"


def line(phase: str, uptime_ms: int, *, run: str = RUN, **overrides: str) -> str:
    fields = {
        "schema": evidence.SCHEMA,
        "phase": phase,
        "uptime_ms": str(uptime_ms),
        "run": run,
        "pid1_comm": "init",
        "proc1_exe": "/sbin/init",
        "drm_card0": "char",
        "drm_master": "1",
        "dropbear": "1",
        "display_ready": "1",
        "display_failure": "0",
    }
    fields.update(overrides)
    body = " ".join(f"{key}={value}" for key, value in fields.items())
    return f"{evidence.MARKER}{body}"


def complete_record(run: str = RUN) -> str:
    return "\n".join(
        [
            line("debian_pid1", 132_100, run=run),
            line("debian_drm_master", 133_400, run=run),
            line("debian_sshd", 134_900, run=run),
        ]
    ) + "\n"


class CompleteRecordTest(unittest.TestCase):
    def test_complete_record_proves_the_ordinal(self) -> None:
        result = evidence.evaluate(complete_record(), RUN)
        self.assertTrue(result["proof"], result["reason"])
        self.assertEqual(result["missing_phases"], [])
        self.assertEqual(result["records_selected"], 3)
        self.assertEqual(result["handoff_to_sshd_ms"], 2800)

    def test_uptime_lands_on_the_native_boottime_axis(self) -> None:
        result = evidence.evaluate(complete_record(), RUN)
        self.assertEqual(
            result["uptime_ms"],
            {
                "debian_drm_master": 133_400,
                "debian_pid1": 132_100,
                "debian_sshd": 134_900,
            },
        )


class PermissiveAboutShapeTest(unittest.TestCase):
    """Each case here is a defect that previously burned a live ordinal."""

    def test_crlf_is_counted(self) -> None:
        # An LF-only parser once counted one exact CRLF status line as zero.
        result = evidence.evaluate(complete_record().replace("\n", "\r\n"), RUN)
        self.assertTrue(result["proof"], result["reason"])

    def test_cumulative_earlier_boots_are_not_contamination(self) -> None:
        # An exactly-one global rule once rejected legitimate cumulative
        # unarmed-boot logs, and that rejection burned an F1 candidate flash.
        text = complete_record("a90-d1-attended-20260806-01") + complete_record()
        result = evidence.evaluate(text, RUN)
        self.assertTrue(result["proof"], result["reason"])
        self.assertEqual(result["records_total"], 6)
        self.assertEqual(result["records_selected"], 3)

    def test_unknown_keys_are_kept_not_rejected(self) -> None:
        # A host aggregate validator once rejected expected manifest
        # enrichment by demanding equality with a pre-staging shape.
        text = complete_record().replace(
            "phase=debian_sshd", "phase=debian_sshd future_key=future_value"
        )
        result = evidence.evaluate(text, RUN)
        self.assertTrue(result["proof"], result["reason"])
        self.assertEqual(
            result["phases"]["debian_sshd"]["future_key"], "future_value"
        )

    def test_interleaved_foreign_lines_are_skipped(self) -> None:
        text = (
            "A90BENCH schema=a90-boot-benchmark-v1 stage=switch_root_exec\n"
            + complete_record()
            + "a90:/# some console noise\n"
        )
        self.assertTrue(evidence.evaluate(text, RUN)["proof"])

    def test_truncated_tail_never_invalidates_complete_lines(self) -> None:
        # Power loss mid-append leaves a partial final line.
        text = complete_record() + evidence.MARKER + "schema=a90-ondev"
        result = evidence.evaluate(text, RUN)
        self.assertTrue(result["proof"], result["reason"])

    def test_marker_with_console_prefix_is_found(self) -> None:
        text = "\n".join(
            "[  132.100] " + row for row in complete_record().splitlines()
        )
        self.assertTrue(evidence.evaluate(text, RUN)["proof"])


class StrictAboutStateTest(unittest.TestCase):
    """The only failures allowed are positive evidence of a bad state."""

    def test_missing_phase_is_named_not_guessed(self) -> None:
        text = "\n".join(
            [line("debian_pid1", 132_100), line("debian_sshd", 134_900)]
        )
        result = evidence.evaluate(text, RUN)
        self.assertFalse(result["proof"])
        self.assertEqual(result["missing_phases"], ["debian_drm_master"])
        self.assertIn("debian_drm_master", result["reason"])

    def test_recorded_display_failure_fails(self) -> None:
        text = complete_record().replace(
            "phase=debian_drm_master uptime_ms=133400 run=" + RUN
            + " pid1_comm=init proc1_exe=/sbin/init drm_card0=char"
            " drm_master=1 dropbear=1 display_ready=1 display_failure=0",
            "phase=debian_drm_master uptime_ms=133400 run=" + RUN
            + " pid1_comm=init proc1_exe=/sbin/init drm_card0=char"
            " drm_master=1 dropbear=1 display_ready=0 display_failure=1",
        )
        result = evidence.evaluate(text, RUN)
        self.assertFalse(result["proof"])
        self.assertIn("display_failure=1", result["reason"])

    def test_wrong_pid1_fails(self) -> None:
        text = "\n".join(
            [
                line("debian_pid1", 132_100, pid1_comm="a90-init"),
                line("debian_drm_master", 133_400),
                line("debian_sshd", 134_900),
            ]
        )
        result = evidence.evaluate(text, RUN)
        self.assertFalse(result["proof"])
        self.assertIn("pid1_comm=a90-init", result["reason"])

    def test_dropbear_down_fails(self) -> None:
        text = "\n".join(
            [
                line("debian_pid1", 132_100),
                line("debian_drm_master", 133_400),
                line("debian_sshd", 134_900, dropbear="0"),
            ]
        )
        result = evidence.evaluate(text, RUN)
        self.assertFalse(result["proof"])
        self.assertIn("dropbear=0", result["reason"])

    def test_absent_drm_card_fails(self) -> None:
        text = "\n".join(
            [
                line("debian_pid1", 132_100),
                line("debian_drm_master", 133_400, drm_card0="absent"),
                line("debian_sshd", 134_900),
            ]
        )
        result = evidence.evaluate(text, RUN)
        self.assertFalse(result["proof"])
        self.assertIn("drm_card0=absent", result["reason"])

    def test_non_monotonic_phase_order_fails(self) -> None:
        text = "\n".join(
            [
                line("debian_pid1", 134_900),
                line("debian_drm_master", 133_400),
                line("debian_sshd", 132_100),
            ]
        )
        result = evidence.evaluate(text, RUN)
        self.assertFalse(result["proof"])
        self.assertIn("monotonic", result["reason"])

    def test_inconsistent_identity_within_a_run_fails(self) -> None:
        text = "\n".join(
            [
                line("debian_pid1", 132_100),
                line("debian_drm_master", 133_400, proc1_exe="/usr/lib/systemd"),
                line("debian_sshd", 134_900),
            ]
        )
        result = evidence.evaluate(text, RUN)
        self.assertFalse(result["proof"])
        self.assertIn("proc1_exe", result["reason"])

    def test_other_run_does_not_satisfy_this_run(self) -> None:
        result = evidence.evaluate(complete_record("some-other-run"), RUN)
        self.assertFalse(result["proof"])
        self.assertEqual(result["records_selected"], 0)
        self.assertEqual(list(result["missing_phases"]),
                         list(evidence.MANDATORY_PHASES))

    def test_malformed_run_identity_is_refused(self) -> None:
        with self.assertRaises(evidence.EvidenceError):
            evidence.evaluate(complete_record(), "run with spaces")


class RunIdentityTest(unittest.TestCase):
    def test_published_intent_is_accepted(self) -> None:
        intent = "a" * 64
        self.assertEqual(evidence.read_run_identity(intent + "\n"), intent)
        self.assertEqual(evidence.read_run_identity(f"  {intent}\r\n"), intent)

    def test_malformed_published_identity_is_refused(self) -> None:
        # This one field decides which boot's evidence gets graded, so a
        # malformed identity must never silently select the wrong records.
        for bad in ("", "\n", "not a run", "a" * 129):
            with self.assertRaises(evidence.EvidenceError):
                evidence.read_run_identity(bad)


class WriterScriptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.shell = shutil.which("sh")
        if self.shell is None:
            self.skipTest("no POSIX sh on this host")

    def test_generated_collector_is_valid_posix_sh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "collector"
            script.write_text(evidence.writer_script(), encoding="utf-8")
            done = subprocess.run(
                [self.shell, "-n", str(script)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_collector_output_round_trips_through_the_parser(self) -> None:
        """The producer and the consumer must agree, not merely coexist."""
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "runtime" / "evidence.log"
            script = Path(tmp) / "collector"
            script.write_text(
                evidence.writer_script(record_path=str(record)),
                encoding="utf-8",
            )
            script.chmod(0o755)
            done = subprocess.run(
                [self.shell, str(script), "debian_pid1", RUN],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertTrue(record.is_file())
            records = evidence.parse(record.read_text(encoding="utf-8"))

        self.assertEqual(len(records), 1)
        written = records[0]
        self.assertEqual(written["phase"], "debian_pid1")
        self.assertEqual(written["run"], RUN)
        self.assertEqual(written["schema"], evidence.SCHEMA)
        # Stamped from the real /proc/uptime of this host, on the same
        # CLOCK_BOOTTIME axis native-init uses.
        self.assertGreater(int(written["uptime_ms"]), 0)
        for field in evidence.TRISTATE_FIELDS:
            self.assertIn(field, written)

    def test_collector_appends_rather_than_truncating(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "evidence.log"
            script = Path(tmp) / "collector"
            script.write_text(
                evidence.writer_script(record_path=str(record)),
                encoding="utf-8",
            )
            for phase in evidence.MANDATORY_PHASES:
                subprocess.run(
                    [self.shell, str(script), phase, RUN],
                    capture_output=True,
                    check=True,
                )
            records = evidence.parse(record.read_text(encoding="utf-8"))
        self.assertEqual(
            [record["phase"] for record in records],
            list(evidence.MANDATORY_PHASES),
        )

    def test_collector_refuses_a_missing_phase_or_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "evidence.log"
            script = Path(tmp) / "collector"
            script.write_text(
                evidence.writer_script(record_path=str(record)),
                encoding="utf-8",
            )
            for argv in ([], ["debian_pid1"]):
                done = subprocess.run(
                    [self.shell, str(script), *argv],
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(done.returncode, 2)
            self.assertFalse(record.exists())

    def test_evidence_path_is_beside_the_image_not_inside_it(self) -> None:
        """The work-copy replacement makes the rootfs read-only.

        An evidence path inside the image would go read-only with it and kill
        the instrument exactly when the mount change most needs grading.
        """
        self.assertTrue(
            evidence.DEFAULT_RECORD_PATH.startswith("/mnt/sdext/a90/runtime/")
        )
        self.assertFalse(evidence.DEFAULT_RECORD_PATH.endswith(".img"))

    def test_collector_reads_the_published_run_when_none_is_passed(self) -> None:
        """The rootfs hook only has to know the phase.

        native-init publishes the arming intent_sha256 beside the record before
        it dispatches, because Debian cannot see the /cache enable or latch.
        """
        intent = "b" * 64
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "evidence.log"
            run_file = Path(tmp) / "evidence-run"
            run_file.write_text(intent + "\n", encoding="utf-8")
            script = Path(tmp) / "collector"
            script.write_text(
                evidence.writer_script(
                    record_path=str(record), run_path=str(run_file)
                ),
                encoding="utf-8",
            )
            done = subprocess.run(
                [self.shell, str(script), "debian_pid1"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(done.returncode, 0, done.stderr)
            records = evidence.parse(record.read_text(encoding="utf-8"))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["run"], intent)

    def test_explicit_run_argument_wins_over_the_published_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "evidence.log"
            run_file = Path(tmp) / "evidence-run"
            run_file.write_text("c" * 64 + "\n", encoding="utf-8")
            script = Path(tmp) / "collector"
            script.write_text(
                evidence.writer_script(
                    record_path=str(record), run_path=str(run_file)
                ),
                encoding="utf-8",
            )
            subprocess.run(
                [self.shell, str(script), "debian_pid1", RUN],
                capture_output=True,
                check=True,
            )
            records = evidence.parse(record.read_text(encoding="utf-8"))
        self.assertEqual(records[0]["run"], RUN)

    def test_collector_refuses_when_no_run_is_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "evidence.log"
            script = Path(tmp) / "collector"
            script.write_text(
                evidence.writer_script(
                    record_path=str(record),
                    run_path=str(Path(tmp) / "absent"),
                ),
                encoding="utf-8",
            )
            done = subprocess.run(
                [self.shell, str(script), "debian_pid1"],
                capture_output=True,
                check=False,
            )
            self.assertEqual(done.returncode, 2)
            self.assertFalse(record.exists())

    def test_dropbear_port_is_validated(self) -> None:
        for port in (0, -1, 65536, "2222"):
            with self.assertRaises(evidence.EvidenceError):
                evidence.writer_script(dropbear_port=port)  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
