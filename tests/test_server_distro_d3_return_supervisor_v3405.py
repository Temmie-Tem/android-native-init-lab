from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from _loader import load_script


builder = load_script(
    "workspace/public/src/scripts/server-distro/"
    "prepare_d3_return_diagnostic_v3405.py"
)
SOURCE = Path(
    "workspace/public/src/scripts/server-distro/"
    "a90_d3_return_supervisor_v3405.c"
)


class D3ReturnSupervisorV3405Tests(unittest.TestCase):
    def test_firstboot_arms_supervisor_before_rootfs_activity(self) -> None:
        text = builder.firstboot_script(
            "192.168.7.2",
            "192.168.7.1",
            2222,
            120,
            20,
        )

        self.assertEqual(builder.validate_firstboot(text), ())
        arm = text.index('RETURN_SUPERVISOR_PID=$("$RETURN_SUPERVISOR" --arm 120 20)')
        for later in (
            "mkdir -p",
            "$IP addr replace",
            "A90D3_MARKER",
            "/usr/sbin/dropbear",
        ):
            self.assertLess(arm, text.index(later))
        self.assertNotIn("\nsync\n", text)
        self.assertNotIn("/sbin/reboot", text)
        self.assertNotIn("/proc/sysrq-trigger", text)

    def test_supervisor_has_preopened_b_only_no_exec_contract(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertEqual(builder.validate_supervisor_source(source), ())
        self.assertIn('#define A90_SYSRQ_PATH "/proc/sysrq-trigger"', source)
        self.assertIn('write_all(io->sysrq_fd, "b\\n", 2U)', source)
        self.assertNotIn('"s\\n"', source)
        self.assertNotIn("LINUX_REBOOT_CMD_RESTART2", source)
        for forbidden in ("execve(", "execl(", "execvp(", "system(", "popen("):
            self.assertNotIn(forbidden, source)
        self.assertLess(source.index("preopen_interfaces(&io)"), source.index("mlockall("))
        self.assertLess(source.index("mlockall("), source.index("phase=armed"))

    def test_supervisor_diagnostic_child_and_proc_evidence_order(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("sync();", source)
        self.assertIn('"/proc/%ld/stat"', source)
        self.assertIn('"/proc/%ld/wchan"', source)
        self.assertIn("state_from_stat(stat_text)", source)
        evidence_child = builder.c_function_body(
            builder.strip_c_comments(source), "evidence_child"
        )
        evidence_parent = builder.c_function_body(
            builder.strip_c_comments(source), "collect_evidence_then_b"
        )
        self.assertIsNotNone(evidence_child)
        self.assertIsNotNone(evidence_parent)
        self.assertIn("read_sync_evidence(", evidence_child)
        self.assertIn("phase=sync-timeout", evidence_child)
        self.assertNotIn("read_sync_evidence(", evidence_parent)
        self.assertNotIn("emit_marker(", evidence_parent)
        self.assertIn("wait_child_until(evidence_pid", evidence_parent)
        self.assertIn('trigger_b_only(io, "sync-timeout")', evidence_parent)

    def test_source_gate_rejects_emergency_sync_late_exec_and_comment_decoy(
        self,
    ) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        emergency_sync = source.replace(
            'write_all(io->sysrq_fd, "b\\n", 2U)',
            'write_all(io->sysrq_fd, "s\\n", 2U)',
            1,
        )
        late_exec = source + '\nstatic void forbidden(void) { execve("/bin/true", 0, 0); }\n'
        comment_decoy = source.replace(
            'write_all(io->sysrq_fd, "b\\n", 2U)',
            'write_all(io->sysrq_fd, "x\\n", 2U); '
            '/* write_all(io->sysrq_fd, "b\\\\n", 2U) */',
            1,
        )

        emergency_issues = builder.validate_supervisor_source(emergency_sync)
        exec_issues = builder.validate_supervisor_source(late_exec)
        decoy_issues = builder.validate_supervisor_source(comment_decoy)
        self.assertTrue(
            any("forbidden supervisor token" in issue for issue in emergency_issues)
        )
        self.assertTrue(
            any("forbidden supervisor token" in issue for issue in exec_issues)
        )
        self.assertTrue(
            any("one exact b-only write" in issue for issue in decoy_issues),
            decoy_issues,
        )

    def test_firstboot_rejects_shell_injection_and_bad_port(self) -> None:
        for local, peer, port in (
            ("192.168.7.2; /bin/sync #", "192.168.7.1", 2222),
            ("192.168.7.2", "192.168.7.1; reboot -f #", 2222),
            ("192.168.7.2", "192.168.7.1", 0),
            ("192.168.7.2", "192.168.8.1", 2222),
        ):
            with self.subTest(local=local, peer=peer, port=port):
                with self.assertRaises(RuntimeError):
                    builder.firstboot_script(local, peer, port, 120, 20)
        for delay, grace in (("120; reboot -f #", 20), (120, "20; sync #"), (0, 20)):
            with self.subTest(delay=delay, grace=grace):
                with self.assertRaises(RuntimeError):
                    builder.firstboot_script(
                        "192.168.7.2",
                        "192.168.7.1",
                        2222,
                        delay,
                        grace,
                    )

    def test_run_id_and_base_provenance_reject_escape_or_substitution(self) -> None:
        for run_id in (
            "../../../public/escaped",
            "/tmp/escaped",
            "UPPERCASE",
            ".hidden",
            "contains space",
        ):
            self.assertIsNone(builder.RUN_ID_PATTERN.fullmatch(run_id))
        with tempfile.TemporaryDirectory() as temporary:
            substituted = Path(temporary) / "rootfs"
            substituted.mkdir()
            issues = builder.validate_base_provenance(substituted)
            self.assertTrue(any("exact pinned" in issue for issue in issues))
            alias = Path(temporary) / "base-image-alias"
            alias.symlink_to(builder.DEFAULT_BASE_IMAGE)
            alias_issues = builder.validate_base_provenance(alias)
            self.assertTrue(any("exact pinned absolute" in issue for issue in alias_issues))

    def test_pinned_base_image_identity_ownership_and_credentials_pass(self) -> None:
        self.assertEqual(
            builder.sha256_file(builder.BASE_SUMMARY),
            builder.EXPECTED_BASE_SUMMARY_SHA256,
        )
        self.assertEqual(
            builder.validate_base_provenance(builder.DEFAULT_BASE_IMAGE), ()
        )
        init_stat = builder.debugfs_stat(builder.DEFAULT_BASE_IMAGE, "/sbin/init")
        firstboot_stat = builder.debugfs_stat(
            builder.DEFAULT_BASE_IMAGE, "/etc/a90-d3-firstboot"
        )
        self.assertEqual(
            (init_stat["mode"], init_stat["uid"], init_stat["gid"]),
            (0o755, 0, 0),
        )
        self.assertEqual(
            (firstboot_stat["mode"], firstboot_stat["uid"], firstboot_stat["gid"]),
            (0o755, 0, 0),
        )
        for target in (
            "/root/.ssh/authorized_keys",
            "/etc/dropbear/dropbear_ed25519_host_key",
            "/run/a90-d3-marker",
        ):
            self.assertIsNone(builder.debugfs_stat(builder.DEFAULT_BASE_IMAGE, target))

    @unittest.skipUnless(
        shutil.which("mke2fs") and shutil.which("debugfs"),
        "ext4 host tools unavailable",
    )
    def test_ext4_overlay_write_sets_exact_root_metadata_and_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            image = temp / "test.img"
            source = temp / "source"
            source.write_bytes(b"overlay-test\n")
            subprocess.run(
                ["mke2fs", "-q", "-t", "ext4", str(image), "32M"],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            builder.debugfs_text(image, "mkdir /etc", writable=True)
            with self.assertRaises(RuntimeError):
                builder.replace_ext4_file(
                    image,
                    source,
                    "/etc/../escaped",
                    mode=0o755,
                )

            result = builder.replace_ext4_file(
                image,
                source,
                "/etc/overlay-test",
                mode=0o755,
            )

            self.assertEqual(result["mode"], "0o755")
            self.assertEqual(result["uid"], 0)
            self.assertEqual(result["gid"], 0)
            self.assertEqual(
                builder.debugfs_bytes(image, "cat /etc/overlay-test"),
                source.read_bytes(),
            )
            fsck = subprocess.run(
                ["e2fsck", "-fn", str(image)],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(fsck.returncode, 0, fsck.stdout + fsck.stderr)

    def test_install_contract_stages_only_versioned_helper_and_firstboot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            rootfs = Path(temporary) / "rootfs"
            helper = Path(temporary) / "helper"
            helper.write_bytes(b"static-helper-placeholder")
            helper.chmod(0o755)

            result = builder.install_contract(
                rootfs,
                helper,
                ncm_ip="192.168.7.2",
                ncm_peer="192.168.7.1",
                ssh_port=2222,
                delay_sec=120,
                grace_sec=20,
            )

            staged_helper = rootfs / builder.SUPERVISOR_TARGET
            firstboot = rootfs / builder.FIRSTBOOT_TARGET
            stage = rootfs / builder.STAGE_TARGET
            self.assertEqual(staged_helper.read_bytes(), helper.read_bytes())
            self.assertEqual(staged_helper.stat().st_mode & 0o777, 0o755)
            self.assertEqual(firstboot.stat().st_mode & 0o777, 0o755)
            self.assertIn(
                "pmsg-retention=must-be-proven-by-this-run",
                stage.read_text(encoding="utf-8"),
            )
            self.assertEqual(result["helper_mode"], "0o755")

    @unittest.skipUnless(
        shutil.which("aarch64-linux-gnu-gcc"),
        "aarch64 cross compiler unavailable",
    )
    def test_production_helper_cross_compiles_static_aarch64(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "supervisor"
            subprocess.run(
                [
                    "aarch64-linux-gnu-gcc",
                    "-static",
                    "-Os",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    str(SOURCE),
                    "-o",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            file_output = subprocess.run(
                ["file", str(output)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout

            self.assertIn("ARM aarch64", file_output)
            self.assertIn("statically linked", file_output)

    @unittest.skipUnless(shutil.which("gcc"), "host compiler unavailable")
    def test_reboot_child_return_is_failure_and_parent_writes_only_b(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            binary = self._compile_test_helper(temp)
            paths = self._make_test_paths(temp)
            env = self._test_env(paths)
            env["A90_TEST_SYNC_MODE"] = "return"

            result = subprocess.run(
                [str(binary), "--test-foreground", "0", "1"],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                timeout=5,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            phases = paths["pmsg"].read_text(encoding="utf-8")
            self.assertLess(phases.index("phase=sync-enter"), phases.index("phase=sync-return"))
            self.assertIn("phase=reboot-enter", phases)
            self.assertEqual(paths["action"].read_text(encoding="utf-8"), "reboot\n")
            self.assertEqual(paths["sysrq"].read_bytes(), b"b\n")

    @unittest.skipUnless(shutil.which("gcc"), "host compiler unavailable")
    def test_blocked_path_captures_d_state_wchan_then_writes_only_b(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            binary = self._compile_test_helper(temp)
            paths = self._make_test_paths(temp)
            paths["stat"].write_text("123 (sync) D 1 2 3 4 5\n", encoding="utf-8")
            paths["wchan"].write_text("wb_wait_for_completion\n", encoding="utf-8")
            env = self._test_env(paths)
            env["A90_TEST_SYNC_MODE"] = "block"
            env["A90_TEST_PROC_STAT"] = str(paths["stat"])
            env["A90_TEST_PROC_WCHAN"] = str(paths["wchan"])

            result = subprocess.run(
                [str(binary), "--test-foreground", "0", "1"],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                timeout=5,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            evidence = paths["pmsg"].read_text(encoding="utf-8")
            timeout_marker = (
                "phase=sync-timeout stat_read=1 state=D "
                "wchan_read=1 wchan=wb_wait_for_completion"
            )
            self.assertIn(timeout_marker, evidence)
            self.assertEqual(paths["sysrq"].read_bytes(), b"b\n")
            self.assertNotIn(b"s", paths["sysrq"].read_bytes())

    @unittest.skipUnless(shutil.which("gcc"), "host compiler unavailable")
    def test_reboot_child_block_has_absolute_parent_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            binary = self._compile_test_helper(temp)
            paths = self._make_test_paths(temp)
            env = self._test_env(paths)
            env["A90_TEST_SYNC_MODE"] = "return"
            env["A90_TEST_REBOOT_MODE"] = "block"

            started = time.monotonic()
            result = subprocess.run(
                [str(binary), "--test-foreground", "0", "1"],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                timeout=5,
            )
            elapsed = time.monotonic() - started

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertLess(elapsed, 2.0)
            self.assertIn(
                "phase=reboot-enter", paths["pmsg"].read_text(encoding="utf-8")
            )
            self.assertEqual(paths["action"].read_bytes(), b"")
            self.assertEqual(paths["sysrq"].read_bytes(), b"b\n")

    @unittest.skipUnless(shutil.which("gcc"), "host compiler unavailable")
    def test_evidence_child_block_cannot_delay_b_beyond_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            binary = self._compile_test_helper(temp)
            paths = self._make_test_paths(temp)
            env = self._test_env(paths)
            env["A90_TEST_SYNC_MODE"] = "block"
            env["A90_TEST_EVIDENCE_MODE"] = "block"

            started = time.monotonic()
            result = subprocess.run(
                [str(binary), "--test-foreground", "0", "1"],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                timeout=5,
            )
            elapsed = time.monotonic() - started

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertLess(elapsed, 3.0)
            self.assertEqual(paths["sysrq"].read_bytes(), b"b\n")

    @unittest.skipUnless(shutil.which("gcc"), "host compiler unavailable")
    def test_background_arm_waits_for_ready_then_returns_only_supervisor_pid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            binary = self._compile_test_helper(temp)
            paths = self._make_test_paths(temp)
            env = self._test_env(paths)
            env["A90_TEST_SYNC_MODE"] = "return"

            result = subprocess.run(
                [str(binary), "--arm", "1", "1"],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                timeout=5,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertRegex(result.stdout, r"^[0-9]+\n$")
            for _attempt in range(40):
                if paths["sysrq"].read_bytes() == b"b\n":
                    break
                time.sleep(0.05)
            self.assertEqual(paths["action"].read_text(encoding="utf-8"), "reboot\n")
            self.assertEqual(paths["sysrq"].read_bytes(), b"b\n")

    @unittest.skipUnless(shutil.which("gcc"), "host compiler unavailable")
    def test_background_ready_timeout_is_absolute_and_writes_only_b(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            binary = self._compile_test_helper(temp)
            paths = self._make_test_paths(temp)
            env = self._test_env(paths)
            env["A90_TEST_READY_MODE"] = "block"

            started = time.monotonic()
            result = subprocess.run(
                [str(binary), "--arm", "1", "1"],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                timeout=3,
            )
            elapsed = time.monotonic() - started

            self.assertEqual(result.returncode, 1)
            self.assertLess(elapsed, 1.0)
            self.assertEqual(paths["sysrq"].read_bytes(), b"b\n")

    @unittest.skipUnless(shutil.which("gcc"), "host compiler unavailable")
    def test_arm_failure_uses_parent_preopened_b_without_waiting_for_child(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temp = Path(temporary)
            binary = self._compile_test_helper(temp)
            paths = self._make_test_paths(temp)
            paths["pmsg"].unlink()
            proc_devices = temp / "proc-devices"
            proc_devices.write_text("Character devices:\n1 mem\n", encoding="utf-8")
            env = self._test_env(paths)
            env["A90_TEST_PROC_DEVICES"] = str(proc_devices)

            result = subprocess.run(
                [str(binary), "--arm", "1", "1"],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                timeout=5,
            )

            self.assertEqual(result.returncode, 1)
            self.assertEqual(paths["sysrq"].read_bytes(), b"b\n")

    def _compile_test_helper(self, temporary: Path) -> Path:
        output = temporary / "supervisor-test"
        subprocess.run(
            [
                "gcc",
                "-DA90_D3_SUPERVISOR_TESTING=1",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                str(SOURCE),
                "-o",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return output

    def _make_test_paths(self, temporary: Path) -> dict[str, Path]:
        paths = {
            name: temporary / name
            for name in ("sysrq", "pmsg", "kmsg", "action", "stat", "wchan")
        }
        for name in ("sysrq", "pmsg", "kmsg", "action"):
            paths[name].touch()
        return paths

    def _test_env(self, paths: dict[str, Path]) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "A90_TEST_SYSRQ": str(paths["sysrq"]),
                "A90_TEST_PMSG": str(paths["pmsg"]),
                "A90_TEST_KMSG": str(paths["kmsg"]),
                "A90_TEST_ACTION": str(paths["action"]),
            }
        )
        return env


if __name__ == "__main__":
    unittest.main()
