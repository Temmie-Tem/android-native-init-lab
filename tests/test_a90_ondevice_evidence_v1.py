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


# The run identity is the arming intent_sha256, nothing looser.
RUN = "0123456789abcdef" * 4


def line(phase: str, uptime_ms: int, *, run: str = RUN, **overrides: str) -> str:
    fields = {
        "schema": evidence.SCHEMA,
        "phase": phase,
        "uptime_ms": str(uptime_ms),
        "run": run,
        "pid1_comm": "init",
        "proc1_exe": "/usr/sbin/init",
        "drm_card0": "char",
        "drm_master": "1",
        "dropbear": "1",
        "display_ready": "1",
        "display_failure": "0",
        "wifi_ready": "1",
        "wifi_failure": "0",
        "wifi_companion": "1",
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
        self.assertEqual(result["pid1_to_sshd_ms"], 2800)
        self.assertEqual(result["pid1_to_debian_ready_ms"], 2800)

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

    def test_historical_three_phase_record_remains_qualified(self) -> None:
        text = complete_record().replace(
            " wifi_ready=1 wifi_failure=0 wifi_companion=1",
            "",
        )
        result = evidence.evaluate(text, RUN)
        self.assertTrue(result["proof"], result["reason"])
        self.assertNotIn("debian_wifi", result["phases"])

    def test_optional_wifi_phase_is_graded_when_present(self) -> None:
        text = complete_record() + line("debian_wifi", 135_100) + "\n"
        result = evidence.evaluate(text, RUN)
        self.assertTrue(result["proof"], result["reason"])
        self.assertEqual(result["phases"]["debian_wifi"]["wifi_ready"], "1")
        self.assertEqual(result["phases"]["debian_wifi"]["wifi_companion"], "1")


class PermissiveAboutShapeTest(unittest.TestCase):
    """Each case here is a defect that previously burned a live ordinal."""

    def test_crlf_is_counted(self) -> None:
        # An LF-only parser once counted one exact CRLF status line as zero.
        result = evidence.evaluate(complete_record().replace("\n", "\r\n"), RUN)
        self.assertTrue(result["proof"], result["reason"])

    def test_cumulative_earlier_boots_are_not_contamination(self) -> None:
        # An exactly-one global rule once rejected legitimate cumulative
        # unarmed-boot logs, and that rejection burned an F1 candidate flash.
        text = complete_record("f" * 64) + complete_record()
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
        text = "\n".join(
            [
                line("debian_pid1", 132_100),
                line(
                    "debian_drm_master",
                    133_400,
                    display_ready="0",
                    display_failure="1",
                ),
                line("debian_sshd", 134_900),
            ]
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

    def test_absent_drm_master_fails(self) -> None:
        text = "\n".join(
            [
                line("debian_pid1", 132_100),
                line("debian_drm_master", 133_400, drm_master="0"),
                line("debian_sshd", 134_900),
            ]
        )
        result = evidence.evaluate(text, RUN)
        self.assertFalse(result["proof"])
        self.assertIn("drm_master=0", result["reason"])

    def test_wifi_failure_record_fails(self) -> None:
        text = complete_record() + line(
            "debian_wifi",
            135_100,
            wifi_ready="0",
            wifi_failure="1",
        ) + "\n"
        result = evidence.evaluate(text, RUN)
        self.assertFalse(result["proof"])
        self.assertIn("wifi_failure=1", result["reason"])

    def test_wifi_phase_without_ready_fact_fails(self) -> None:
        text = complete_record() + line(
            "debian_wifi",
            135_100,
            wifi_ready="0",
            wifi_failure="0",
        ) + "\n"
        result = evidence.evaluate(text, RUN)
        self.assertFalse(result["proof"])
        self.assertIn("wifi_ready=0", result["reason"])

    def test_wifi_phase_without_live_companion_fails(self) -> None:
        text = complete_record() + line(
            "debian_wifi",
            135_100,
            wifi_companion="0",
        ) + "\n"
        result = evidence.evaluate(text, RUN)
        self.assertFalse(result["proof"])
        self.assertIn("wifi_companion=0", result["reason"])

    def test_duplicate_key_cannot_overwrite_a_contradiction(self) -> None:
        drm = line("debian_drm_master", 133_400).replace(
            "drm_master=1",
            "drm_master=0 drm_master=1",
        )
        text = "\n".join(
            [
                line("debian_pid1", 132_100),
                drm,
                line("debian_sshd", 134_900),
            ]
        )
        result = evidence.evaluate(text, RUN)
        self.assertFalse(result["proof"])
        self.assertEqual(result["missing_phases"], ["debian_drm_master"])

    def test_pid1_must_be_the_earliest_stamp(self) -> None:
        text = "\n".join(
            [
                line("debian_pid1", 134_900),
                line("debian_drm_master", 133_400),
                line("debian_sshd", 132_100),
            ]
        )
        result = evidence.evaluate(text, RUN)
        self.assertFalse(result["proof"])
        self.assertIn("earliest", result["reason"])

    def test_sshd_before_drm_is_a_normal_boot_not_a_failure(self) -> None:
        """The network service signals before the display launcher.

        inittab runs the network/SSH service as a blocking entry and the
        display launcher after it, so Dropbear is listening first on a healthy
        boot. Demanding a fixed order between the two would be exactly the
        over-specification that has been failing normal boots.
        """
        text = "\n".join(
            [
                line("debian_pid1", 132_100),
                line("debian_sshd", 133_400),
                line("debian_drm_master", 134_900),
            ]
        )
        result = evidence.evaluate(text, RUN)
        self.assertTrue(result["proof"], result["reason"])

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
        result = evidence.evaluate(complete_record("e" * 64), RUN)
        self.assertFalse(result["proof"])
        self.assertEqual(result["records_selected"], 0)
        self.assertEqual(list(result["missing_phases"]),
                         list(evidence.MANDATORY_PHASES))

    def test_malformed_run_identity_is_refused(self) -> None:
        # The grading entry point must enforce the same strict identity the
        # run file does; a permissive check here would let a loose --run
        # select records it should never have matched.
        for bad in ("run with spaces", "a90-d1-attended-20260807-02", "A" * 64):
            with self.assertRaises(evidence.EvidenceError):
                evidence.evaluate(complete_record(), bad)

    def test_a_phase_line_with_no_health_fields_is_not_proof(self) -> None:
        bare = "\n".join(
            f"{evidence.MARKER}schema={evidence.SCHEMA} phase={phase} "
            f"uptime_ms={100 + index} run={RUN}"
            for index, phase in enumerate(evidence.MANDATORY_PHASES)
        )
        result = evidence.evaluate(bare, RUN)
        self.assertFalse(result["proof"])
        self.assertIn("carries no", result["reason"])

    def test_a_wrong_pid1_executable_is_not_proof(self) -> None:
        text = complete_record().replace(
            "proc1_exe=/usr/sbin/init", "proc1_exe=/bin/sh", 1
        )
        result = evidence.evaluate(text, RUN)
        self.assertFalse(result["proof"])
        self.assertIn("proc1_exe=/bin/sh", result["reason"])


class RunIdentityTest(unittest.TestCase):
    def test_published_intent_is_accepted(self) -> None:
        intent = "0123456789abcdef" * 4
        self.assertEqual(evidence.read_run_identity(intent + "\n"), intent)
        self.assertEqual(evidence.read_run_identity(f"  {intent}\r\n"), intent)

    def test_malformed_published_identity_is_refused(self) -> None:
        # This one field decides which boot's evidence gets graded, so a
        # malformed identity must never silently select the wrong records.
        for bad in ("", "\n", "not a run", "a" * 129,
                    "a90-d1-attended-20260807-02", "A" * 64, "0" * 63):
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

    def test_the_two_views_address_the_same_bytes(self) -> None:
        """Debian and native see the record under different absolute paths.

        Only /proc, /sys and /dev cross switch_root, so a native-namespace path
        would resolve inside the read-only image on the Debian side and every
        write would fail silently. native-init bind-mounts its evidence
        directory onto the image's empty /mnt, so Debian writes /mnt/... while
        native reads /mnt/sdext/a90/runtime/evidence/... -- the same bytes.
        """
        for debian, native in (
            (evidence.DEFAULT_RECORD_PATH, evidence.NATIVE_RECORD_PATH),
            (evidence.DEFAULT_RUN_PATH, evidence.NATIVE_RUN_PATH),
        ):
            self.assertTrue(debian.startswith("/mnt/"))
            self.assertFalse(debian.startswith("/mnt/sdext/"))
            self.assertTrue(
                native.startswith("/mnt/sdext/a90/runtime/evidence/")
            )
            self.assertEqual(
                debian.rsplit("/", 1)[-1], native.rsplit("/", 1)[-1]
            )
            self.assertFalse(debian.endswith(".img"))

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

    def test_hook_is_valid_posix_sh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "hook"
            script.write_text(evidence.hook_script(), encoding="utf-8")
            done = subprocess.run(
                [self.shell, "-n", str(script)],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_hook_stamps_sshd_before_drm_matching_inittab_order(self) -> None:
        text = evidence.hook_script()
        self.assertLess(
            text.index("record debian_sshd"),
            text.index("record debian_drm_master"),
        )
        self.assertLess(
            text.index("record debian_pid1"), text.index("record debian_sshd")
        )
        self.assertLess(
            text.index("record debian_drm_master"),
            text.index("record debian_wifi"),
        )

    def test_hook_waits_are_validated(self) -> None:
        self.assertIn(
            "wait_for_any 100 /run/a90-wifi/ready /run/a90-wifi/failure",
            evidence.hook_script(),
        )
        for kwargs in (
            {"display_wait_sec": 0},
            {"sshd_wait_sec": -1},
            {"wifi_wait_sec": 0},
        ):
            with self.assertRaises(evidence.EvidenceError):
                evidence.hook_script(**kwargs)  # type: ignore[arg-type]

    def test_dropbear_port_is_validated(self) -> None:
        for port in (0, -1, 65536, "2222"):
            with self.assertRaises(evidence.EvidenceError):
                evidence.writer_script(dropbear_port=port)  # type: ignore[arg-type]


class RootfsCarrierTest(unittest.TestCase):
    """The rootfs profile must carry exactly what this module generates.

    The module is the single source for the collector and the hook; a copy
    embedded in the firstboot script is only useful if it cannot drift from it.
    """

    PROFILE = SCRIPT_DIR / "phase3_network_ssh_v1"
    SERVICE = PROFILE / "a90_debian_network_ssh_v1.sh"

    def test_service_carries_the_generated_block_exactly_once(self) -> None:
        """A second copy silently defeats the first.

        Restoring the service from git and re-inserting once left two blocks,
        the later one still pointing at the old unreachable path, and it
        overwrote the collector the earlier block had just unpacked.
        """
        text = self.SERVICE.read_text(encoding="utf-8")
        block = evidence.service_block()
        self.assertIn(block, text)
        self.assertEqual(text.count(block), 1)
        self.assertEqual(text.count("A90_ONDEV_EOF"), 4)
        self.assertEqual(text.count(f"RECORD={evidence.DEFAULT_RECORD_PATH}"), 1)
        self.assertNotIn("RECORD=/mnt/sdext/", text)

    def test_service_does_not_chmod_the_read_only_root(self) -> None:
        """chmod on /root/.ssh returns EROFS and the fatal handler kills it.

        No writable-set probe can predict that: the path is not in the set and
        must not be, since a tmpfs over /root/.ssh would hide authorized_keys.
        """
        text = self.SERVICE.read_text(encoding="utf-8")
        self.assertNotIn('chmod 0700 "$RUN_DIR" /root/.ssh', text)
        self.assertIn("SSH_DIR_META=", text)
        self.assertIn("ssh-dir-metadata", text)

    def test_service_pin_matches_the_manifest(self) -> None:
        import hashlib
        import tomllib

        manifest = tomllib.loads(
            (self.PROFILE / "manifest.toml").read_text(encoding="utf-8")
        )
        digest = hashlib.sha256(self.SERVICE.read_bytes()).hexdigest()
        self.assertEqual(manifest["sources"]["service_sha256"], digest)

    def test_service_is_valid_posix_sh(self) -> None:
        shell = shutil.which("sh")
        if shell is None:
            self.skipTest("no POSIX sh on this host")
        done = subprocess.run(
            [shell, "-n", str(self.SERVICE)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_evidence_is_backgrounded_and_never_gates_the_boot(self) -> None:
        block = evidence.service_block()
        self.assertIn(f"{evidence.HOOK_RUN_PATH} >/dev/null 2>&1 &", block)
        # Nothing in the block may abort the boot on failure.
        for row in block.splitlines():
            if row.startswith(("cat > ", "chmod ")):
                self.assertTrue(row.endswith("|| true"), row)

    def test_unpack_targets_are_tmpfs_not_the_image(self) -> None:
        """The builder only replaces files already in its pinned base image.

        Unpacking to /run also survives the read-only rootfs that the work-copy
        replacement will introduce.
        """
        self.assertTrue(evidence.COLLECTOR_RUN_PATH.startswith("/run/"))
        self.assertTrue(evidence.HOOK_RUN_PATH.startswith("/run/"))

    def test_heredoc_delimiter_collision_is_refused(self) -> None:
        with self.assertRaises(evidence.EvidenceError):
            evidence.service_block(record_path="x\nA90_ONDEV_EOF\ny")


if __name__ == "__main__":
    unittest.main()
