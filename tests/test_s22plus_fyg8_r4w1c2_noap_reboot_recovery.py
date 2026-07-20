import contextlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_r4w1c2_noap_reboot_recovery.py"
)


def load_module():
    import sys

    source = str(SCRIPT.parent)
    if source not in sys.path:
        sys.path.insert(0, source)
    spec = importlib.util.spec_from_file_location("r4w1c2_noap_recovery_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class NoApRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    @contextlib.contextmanager
    def opened_directory(self, path):
        descriptor = os.open(
            path,
            os.O_RDONLY
            | os.O_DIRECTORY
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            yield descriptor
        finally:
            os.close(descriptor)

    def test_parse_failure_preimage_matches_live_digest(self):
        module = self.module
        self.assertEqual(len(module.PARSE_FAILURE_STDOUT), 51)
        self.assertEqual(
            module.PARSE_FAILURE_SHA256,
            "7f6162459d49213e9d36485eaa1e7748492b484f4538db45ef50ab4d9f31adb4",
        )
        self.assertNotIn(b"Setup Connection", module.PARSE_FAILURE_STDOUT)

    def test_live_incident_offline_contract(self):
        result = self.module.offline_check(ROOT)
        self.assertEqual(
            result["verdict"],
            "PASS_R4W1C2_NOAP_REBOOT_RECOVERY_SOURCE_HOST_ONLY",
        )
        self.assertTrue(result["incident"]["no_completed_transfer_receipt"])
        self.assertFalse(result["device_contact"])
        self.assertFalse(result["flash"])

    def test_all_three_logs_are_exact_parse_failure(self):
        module = self.module
        for key, (label, ap_sha256) in module.FAILED_LOGS.items():
            _, payload = module.pinned_file(ROOT, key)
            module.validate_failed_log(
                json.loads(payload), label=label, ap_sha256=ap_sha256
            )

    def test_failed_log_rejects_success(self):
        module = self.module
        value = {
            "label": "r4w1c-candidate",
            "returncode": 0,
            "stdout_bytes": 51,
            "stderr_bytes": 0,
            "stdout_sha256": module.PARSE_FAILURE_SHA256,
            "stderr_sha256": module.EMPTY_SHA256,
            "odin_sha256": module.connected.EXPECTED_ODIN_SHA256,
            "ap_sha256": module.connected.EXPECTED_CANDIDATE_AP_SHA256,
            "sealed_inputs": True,
        }
        with self.assertRaisesRegex(module.RecoveryError, "parse failure"):
            module.validate_failed_log(
                value,
                label="r4w1c-candidate",
                ap_sha256=module.connected.EXPECTED_CANDIDATE_AP_SHA256,
            )

    def test_reboot_command_has_no_transfer_argument(self):
        module = self.module
        seen = {}

        def runner(command, **kwargs):
            seen["command"] = command
            seen["kwargs"] = kwargs
            stdout = (
                b"Reboot into normal mode\n/dev/bus/usb/002/027\n"
                b"Setup Connection\ninitializeConnection\nReceive PIT Info\n"
                b"success getpit\nUpload Binaries\nClose Connection\n"
            )
            return subprocess.CompletedProcess(command, 0, stdout, b"")

        with tempfile.TemporaryDirectory() as temporary, self.opened_directory(
            temporary
        ) as output_fd:
            completed, command, _ = module.run_noap_odin(
                9,
                "/dev/bus/usb/002/027",
                output_dir_fd=output_fd,
                stdout_path=Path(temporary) / "stdout",
                stderr_path=Path(temporary) / "stderr",
                outcome_path=Path(temporary) / "outcome.json",
                runner=runner,
            )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(
            command,
            ["/proc/self/fd/9", "--reboot", "-d", "/dev/bus/usb/002/027"],
        )
        self.assertEqual(seen["kwargs"]["pass_fds"], (9,))
        self.assertEqual(seen["kwargs"]["stdin"], subprocess.DEVNULL)
        self.assertEqual(seen["kwargs"]["env"], module.ODIN_ENV)
        self.assertNotIn("LD_PRELOAD", seen["kwargs"]["env"])
        self.assertNotIn("LD_LIBRARY_PATH", seen["kwargs"]["env"])
        for forbidden in ("-a", "-b", "-c", "-s", "-u", "-e", "-V"):
            self.assertNotIn(forbidden, command)

    def test_reboot_rejects_nonzero(self):
        module = self.module

        def runner(command, **_kwargs):
            return subprocess.CompletedProcess(command, 1, b"fail\n", b"")

        with tempfile.TemporaryDirectory() as temporary, self.opened_directory(
            temporary
        ) as output_fd:
            outcome_path = Path(temporary) / "outcome.json"
            with self.assertRaisesRegex(module.RecoveryError, "failed rc=1"):
                module.run_noap_odin(
                    9,
                    "/dev/bus/usb/002/027",
                    output_dir_fd=output_fd,
                    stdout_path=Path(temporary) / "stdout",
                    stderr_path=Path(temporary) / "stderr",
                    outcome_path=outcome_path,
                    runner=runner,
                )
            outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
            self.assertTrue(outcome["attempted"])
            self.assertTrue(outcome["returned"])
            self.assertEqual(outcome["returncode"], 1)
            self.assertTrue(outcome["reaped"])

    def test_reboot_rejects_stderr(self):
        module = self.module
        stdout = (
            b"Reboot into normal mode\n/dev/bus/usb/002/027\n"
            b"Setup Connection\ninitializeConnection\nReceive PIT Info\n"
            b"success getpit\nUpload Binaries\nClose Connection\n"
        )

        def runner(command, **_kwargs):
            return subprocess.CompletedProcess(command, 0, stdout, b"warning\n")

        with tempfile.TemporaryDirectory() as temporary, self.opened_directory(
            temporary
        ) as output_fd, self.assertRaisesRegex(module.RecoveryError, "stderr"):
            module.run_noap_odin(
                9,
                "/dev/bus/usb/002/027",
                output_dir_fd=output_fd,
                stdout_path=Path(temporary) / "stdout",
                stderr_path=Path(temporary) / "stderr",
                outcome_path=Path(temporary) / "outcome.json",
                runner=runner,
            )

    def test_reboot_rejects_missing_success_line(self):
        module = self.module

        def runner(command, **_kwargs):
            return subprocess.CompletedProcess(
                command,
                0,
                b"Reboot into normal mode\n/dev/bus/usb/002/027\n",
                b"",
            )

        with tempfile.TemporaryDirectory() as temporary, self.opened_directory(
            temporary
        ) as output_fd, self.assertRaisesRegex(module.RecoveryError, "success shape"):
            module.run_noap_odin(
                9,
                "/dev/bus/usb/002/027",
                output_dir_fd=output_fd,
                stdout_path=Path(temporary) / "stdout",
                stderr_path=Path(temporary) / "stderr",
                outcome_path=Path(temporary) / "outcome.json",
                runner=runner,
            )

    def test_bounded_runner_persists_at_most_exact_cap(self):
        module = self.module
        command = [
            "/usr/bin/python3",
            "-c",
            f"import os; os.write(1, b'x' * {module.MAX_ODIN_OUTPUT + 8192})",
        ]
        with self.assertRaises(module.BoundedOdinError) as raised:
            module.bounded_odin_runner(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                pass_fds=(),
                env=dict(module.ODIN_ENV),
                timeout=10,
                check=False,
            )
        error = raised.exception
        self.assertTrue(error.output_overflow)
        self.assertEqual(len(error.stdout) + len(error.stderr), module.MAX_ODIN_OUTPUT)

    def test_bounded_cleanup_never_uses_unbounded_wait(self):
        module = self.module

        class StuckProcess:
            def __init__(self):
                self.killed = False
                self.wait_timeouts = []

            def poll(self):
                return None

            def kill(self):
                self.killed = True

            def wait(self, timeout=None):
                self.wait_timeouts.append(timeout)
                raise subprocess.TimeoutExpired(["odin4"], timeout)

        process = StuckProcess()
        with mock.patch.object(module.time, "monotonic", return_value=10.25):
            kill_sent, reaped, cleanup_error = module.bounded_kill_reap(
                process, 11.0
            )
        self.assertTrue(kill_sent)
        self.assertFalse(reaped)
        self.assertTrue(process.killed)
        self.assertEqual(process.wait_timeouts, [0.75])
        self.assertIn("bounded reap failed", cleanup_error)

    def test_post_spawn_read_error_preserves_output_and_truthful_outcome(self):
        module = self.module

        class Pipe:
            def close(self):
                pass

        class Process:
            def __init__(self):
                self.stdout = Pipe()
                self.stderr = Pipe()
                self.returncode = None
                self.killed = False
                self.reaped = False

            def poll(self):
                return self.returncode

            def kill(self):
                self.killed = True

            def wait(self, timeout=None):
                self.reaped = True
                self.returncode = -9
                return self.returncode

        class Selector:
            def __init__(self):
                self.key = SimpleNamespace(fd=101, fileobj=object(), data="stdout")
                self.active = True

            def register(self, *_args):
                pass

            def get_map(self):
                return {101: self.key} if self.active else {}

            def select(self, _timeout):
                return [(self.key, 1)]

            def unregister(self, _fileobj):
                self.active = False

            def close(self):
                pass

        process = Process()
        observed = b"observed-before-error"
        reads = iter((observed, OSError("injected pipe read failure")))
        real_read = module.os.read

        def read(fd, size):
            if fd != 101:
                return real_read(fd, size)
            value = next(reads)
            if isinstance(value, BaseException):
                raise value
            return value

        with tempfile.TemporaryDirectory() as temporary, self.opened_directory(
            temporary
        ) as output_fd, mock.patch.object(
            module.subprocess, "Popen", return_value=process
        ), mock.patch.object(
            module.selectors, "DefaultSelector", side_effect=Selector
        ), mock.patch.object(module.os, "read", side_effect=read):
            root = Path(temporary)
            stdout_path = root / "stdout"
            outcome_path = root / "outcome.json"
            with self.assertRaisesRegex(module.RecoveryError, "after process start"):
                module.run_noap_odin(
                    9,
                    "/dev/bus/usb/002/027",
                    output_dir_fd=output_fd,
                    stdout_path=stdout_path,
                    stderr_path=root / "stderr",
                    outcome_path=outcome_path,
                )
            outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
            self.assertEqual(stdout_path.read_bytes(), observed)
            self.assertEqual(
                outcome["runner_error"],
                "no-AP Odin reboot runner failed after process start",
            )
            self.assertTrue(outcome["kill_sent"])
            self.assertTrue(outcome["reaped"])
            self.assertIsNone(outcome["cleanup_error"])
            self.assertNotIn("spawn_error", outcome)
        self.assertTrue(process.killed)
        self.assertTrue(process.reaped)

    def test_post_spawn_non_oserror_preserves_truthful_outcome(self):
        module = self.module

        class Pipe:
            def close(self):
                pass

        class Process:
            def __init__(self):
                self.stdout = Pipe()
                self.stderr = Pipe()
                self.returncode = None
                self.killed = False

            def poll(self):
                return self.returncode

            def kill(self):
                self.killed = True

            def wait(self, timeout=None):
                self.returncode = -9
                return self.returncode

        class Selector:
            def register(self, *_args):
                pass

            def get_map(self):
                return {1: 1}

            def select(self, _timeout):
                raise ValueError("injected selector failure")

            def close(self):
                pass

        process = Process()
        with tempfile.TemporaryDirectory() as temporary, self.opened_directory(
            temporary
        ) as output_fd, mock.patch.object(
            module.subprocess, "Popen", return_value=process
        ), mock.patch.object(
            module.selectors, "DefaultSelector", side_effect=Selector
        ):
            root = Path(temporary)
            outcome_path = root / "outcome.json"
            with self.assertRaisesRegex(module.RecoveryError, "ValueError"):
                module.run_noap_odin(
                    9,
                    "/dev/bus/usb/002/027",
                    output_dir_fd=output_fd,
                    stdout_path=root / "stdout",
                    stderr_path=root / "stderr",
                    outcome_path=outcome_path,
                )
            outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
        self.assertTrue(process.killed)
        self.assertTrue(outcome["kill_sent"])
        self.assertTrue(outcome["reaped"])
        self.assertIn("ValueError", outcome["runner_error"])

    def test_sealed_enumeration_runner_sanitizes_child_contract(self):
        module = self.module
        seen = {}
        outcomes = []

        def bounded(command, **kwargs):
            seen["command"] = command
            seen["kwargs"] = kwargs
            return subprocess.CompletedProcess(command, 0, b"", b"")

        external = Path("/proc/123/fd/9")
        with tempfile.TemporaryDirectory() as temporary, self.opened_directory(
            temporary
        ) as output_fd, mock.patch.object(
            module, "bounded_odin_runner", side_effect=bounded
        ):
            output_dir = Path(temporary)
            completed = module.sealed_enumeration_runner(
                9,
                external,
                output_dir_fd=output_fd,
                output_dir=output_dir,
                outcomes=outcomes,
            )([str(external), "-l"], 10.0)
            outcome = json.loads(
                (output_dir / "odin-enumeration-000000-outcome.json").read_text(
                    encoding="utf-8"
                )
            )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(seen["command"], ["/proc/self/fd/9", "-l"])
        self.assertEqual(seen["kwargs"]["stdin"], subprocess.DEVNULL)
        self.assertEqual(seen["kwargs"]["pass_fds"], (9,))
        self.assertEqual(seen["kwargs"]["env"], module.ODIN_ENV)
        self.assertNotIn("LD_PRELOAD", seen["kwargs"]["env"])
        self.assertNotIn("LD_LIBRARY_PATH", seen["kwargs"]["env"])
        self.assertTrue(outcome["returned"])
        self.assertTrue(outcome["reaped"])
        self.assertFalse(outcome["output_overflow"])
        self.assertEqual(outcomes[0]["returncode"], 0)

    def test_sealed_enumeration_failure_persists_streams_and_cleanup(self):
        module = self.module
        external = Path("/proc/123/fd/9")
        outcomes = []
        error = module.BoundedOdinError(
            "injected sealed enumeration selector fault",
            b"enum-stdout-before-fault",
            b"enum-stderr-before-fault",
            runner_error=True,
            kill_sent=True,
            reaped=True,
            cleanup_error=None,
        )
        with tempfile.TemporaryDirectory() as temporary, self.opened_directory(
            temporary
        ) as output_fd, mock.patch.object(
            module, "bounded_odin_runner", side_effect=error
        ):
            output_dir = Path(temporary)
            runner = module.sealed_enumeration_runner(
                9,
                external,
                output_dir_fd=output_fd,
                output_dir=output_dir,
                outcomes=outcomes,
            )
            with self.assertRaisesRegex(module.BoundedOdinError, "selector fault"):
                runner([str(external), "-l"], 10.0)
            outcome = json.loads(
                (output_dir / "odin-enumeration-000000-outcome.json").read_text(
                    encoding="utf-8"
                )
            )
            stdout = (output_dir / "odin-enumeration-000000.stdout").read_bytes()
            stderr = (output_dir / "odin-enumeration-000000.stderr").read_bytes()
        self.assertEqual(stdout, b"enum-stdout-before-fault")
        self.assertEqual(stderr, b"enum-stderr-before-fault")
        self.assertFalse(outcome["returned"])
        self.assertTrue(outcome["kill_sent"])
        self.assertTrue(outcome["reaped"])
        self.assertIn("selector fault", outcome["runner_error"])
        self.assertEqual(outcomes[0]["stdout"]["sha256"], module.sha256_bytes(stdout))

    def test_injected_oserror_is_not_claimed_as_spawn_failure(self):
        module = self.module

        def runner(_command, **_kwargs):
            raise OSError("injected runner failure")

        with tempfile.TemporaryDirectory() as temporary, self.opened_directory(
            temporary
        ) as output_fd:
            root = Path(temporary)
            outcome_path = root / "outcome.json"
            with self.assertRaisesRegex(module.RecoveryError, "before a return"):
                module.run_noap_odin(
                    9,
                    "/dev/bus/usb/002/027",
                    output_dir_fd=output_fd,
                    stdout_path=root / "stdout",
                    stderr_path=root / "stderr",
                    outcome_path=outcome_path,
                    runner=runner,
                )
            outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
            self.assertEqual(outcome["runner_error"], "injected runner failure")
            self.assertFalse(outcome["kill_sent"])
            self.assertFalse(outcome["reaped"])
            self.assertNotIn("spawn_error", outcome)

    def test_injected_oversize_result_is_capped_before_persistence(self):
        module = self.module

        def runner(command, **_kwargs):
            return subprocess.CompletedProcess(
                command,
                0,
                b"x" * (module.MAX_ODIN_OUTPUT + 17),
                b"overflow",
            )

        with tempfile.TemporaryDirectory() as temporary, self.opened_directory(
            temporary
        ) as output_fd:
            root = Path(temporary)
            stdout_path = root / "stdout"
            stderr_path = root / "stderr"
            outcome_path = root / "outcome.json"
            with self.assertRaisesRegex(module.RecoveryError, "exceeded"):
                module.run_noap_odin(
                    9,
                    "/dev/bus/usb/002/027",
                    output_dir_fd=output_fd,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    outcome_path=outcome_path,
                    runner=runner,
                )
            self.assertEqual(
                stdout_path.stat().st_size + stderr_path.stat().st_size,
                module.MAX_ODIN_OUTPUT,
            )
            outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
            self.assertTrue(outcome["output_overflow"])

    def test_injected_oversize_timeout_is_capped_before_persistence(self):
        module = self.module

        def runner(command, **_kwargs):
            raise subprocess.TimeoutExpired(
                command,
                60,
                output=b"x" * (module.MAX_ODIN_OUTPUT + 23),
                stderr=b"timeout-overflow",
            )

        with tempfile.TemporaryDirectory() as temporary, self.opened_directory(
            temporary
        ) as output_fd:
            root = Path(temporary)
            stdout_path = root / "stdout"
            stderr_path = root / "stderr"
            outcome_path = root / "outcome.json"
            with self.assertRaisesRegex(module.RecoveryError, "timed out"):
                module.run_noap_odin(
                    9,
                    "/dev/bus/usb/002/027",
                    output_dir_fd=output_fd,
                    stdout_path=stdout_path,
                    stderr_path=stderr_path,
                    outcome_path=outcome_path,
                    runner=runner,
                )
            self.assertEqual(
                stdout_path.stat().st_size + stderr_path.stat().st_size,
                module.MAX_ODIN_OUTPUT,
            )
            outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
            self.assertTrue(outcome["timed_out"])
            self.assertTrue(outcome["output_overflow"])

    def test_policy_must_equal_exact_draft_bytes(self):
        module = self.module
        draft = f"{module.POLICY_BEGIN}\nexact body\n{module.POLICY_END}\n".encode()
        agents = draft.replace(b"exact body", b"changed body")

        def stable(path, **_kwargs):
            return agents if path.name == "AGENTS.md" else draft

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            module, "stable_bytes", side_effect=stable
        ), mock.patch.object(
            module, "helper_identity", return_value={"sha256": "a" * 64}
        ), mock.patch.object(
            module, "test_identity", return_value={"sha256": "b" * 64}
        ), mock.patch.object(module, "dependency_identities", return_value={}):
            with self.assertRaisesRegex(module.RecoveryError, "exact reviewed draft"):
                module.policy_status(Path(temporary))

    def test_dependency_graph_rejects_changed_bytes(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            relative = Path("dependency.py")
            (root / relative).write_bytes(b"other")
            with mock.patch.object(
                module,
                "DEPENDENCY_FILES",
                {"dependency": (relative, 5, module.sha256_bytes(b"exact"))},
            ), mock.patch.object(module, "ABSOLUTE_DEPENDENCIES", {}):
                with self.assertRaisesRegex(module.RecoveryError, "identity changed"):
                    module.dependency_identities(root)

    def test_runtime_dependency_graph_rejects_unpinned_transitive_import(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "src"
            source.mkdir()
            (source / "entry.py").write_text("import child\n", encoding="utf-8")
            (source / "child.py").write_text("import unpinned\n", encoding="utf-8")
            (source / "unpinned.py").write_text("VALUE = 1\n", encoding="utf-8")
            with mock.patch.object(
                module, "SCRIPT_RELATIVE", Path("src/entry.py")
            ), mock.patch.object(
                module,
                "DEPENDENCY_FILES",
                {
                    "child": (
                        Path("src/child.py"),
                        len(b"import unpinned\n"),
                        module.sha256_bytes(b"import unpinned\n"),
                    )
                },
            ):
                with self.assertRaisesRegex(module.RecoveryError, "unpinned"):
                    module.validate_runtime_dependency_graph(root)

    def test_runtime_dependency_graph_includes_m3_observable(self):
        module = self.module
        identity = module.DEPENDENCY_FILES["m3_observable"]
        self.assertEqual(identity[1], 24686)
        self.assertEqual(
            identity[2],
            "1f093d78a110925440c98741399d8828201cce38265a5c941ac2f71b6c104305",
        )
        module.validate_runtime_dependency_graph(ROOT)

    def run_mocked_post_android_live(
        self,
        root,
        *,
        absence_result=None,
        absence_error=None,
        publish_bytes=None,
        transaction_error=None,
        enumeration_error=None,
        default_layout=False,
    ):
        module = self.module
        offline = {
            "recovery_consumed": False,
            "incident": {
                "android_serial": "RFCT519XWGK",
                "usb_binding": {
                    "topology": "2-1.3",
                    "serial_sha256": "c" * 64,
                    "download_serial_state": "absent",
                },
                "files": {
                    "consumed": {"sha256": "d" * 64},
                    "stock_intent": {"sha256": "e" * 64},
                },
            },
            "helper": {"sha256": "1" * 64},
            "test": {"sha256": "2" * 64},
            "dependencies": {},
            "policy_draft": {"sha256": "f" * 64},
        }
        policy = {"active": True, "sha256": "a" * 64}
        args = SimpleNamespace(
            ack=module.LIVE_ACK,
            odin=module.connected.DEFAULT_ODIN,
            endpoint_wait_sec=1.0,
            android_wait_sec=1.0,
            odin_absence_wait_sec=1.0,
        )
        ticket = SimpleNamespace(
            device="/dev/bus/usb/002/027",
            device_identity="identity",
            generation=1,
            snapshot_sequence=0,
            snapshot_receipt="mock",
            snapshot_receipt_sha256="b" * 64,
        )

        @contextlib.contextmanager
        def odin_session(_path):
            yield 9, Path("/mock/sealed-odin")

        @contextlib.contextmanager
        def transaction(_run_dir):
            yield object()
            if transaction_error is not None:
                raise transaction_error

        def noap(
            _fd,
            device,
            *,
            output_dir_fd,
            stdout_path,
            stderr_path,
            outcome_path,
        ):
            module.durable_create_bytes_at_idempotent(
                output_dir_fd,
                stdout_path.name,
                b"ok",
                display_path=stdout_path,
            )
            module.durable_create_bytes_at_idempotent(
                output_dir_fd,
                stderr_path.name,
                b"",
                display_path=stderr_path,
            )
            module.durable_create_json_at_idempotent(
                output_dir_fd,
                outcome_path.name,
                {
                    "created_at_utc": module.core.utc_now(),
                    "attempted": True,
                    "returned": True,
                    "returncode": 0,
                },
                display_path=outcome_path,
            )
            command = ["/proc/self/fd/9", "--reboot", "-d", device]
            return (
                subprocess.CompletedProcess(command, 0, b"", b""),
                command,
                list(module.ODIN_SUCCESS_LINES),
            )

        (root / module.RECOVERY_RUN_ROOT).mkdir(parents=True)
        state_relative = (
            module.RECOVERY_STATE if default_layout else Path("state/consumed.json")
        )
        (root / state_relative.parent).mkdir(parents=True, exist_ok=True)
        with contextlib.ExitStack() as stack:
            if not default_layout:
                stack.enter_context(
                    mock.patch.object(module, "RECOVERY_STATE", state_relative)
                )
            stack.enter_context(mock.patch.object(module, "offline_check", return_value=offline))
            stack.enter_context(mock.patch.object(module, "policy_status", return_value=policy))
            stack.enter_context(mock.patch.object(module.time, "strftime", return_value="scenario"))
            stack.enter_context(
                mock.patch.object(
                    module.measured, "pinned_odin_session", side_effect=odin_session
                )
            )
            stack.enter_context(
                mock.patch.object(
                    module.odin_core, "transaction_session", side_effect=transaction
                )
            )
            stack.enter_context(
                mock.patch.object(
                    module, "wait_for_endpoint_hardened", return_value=(ticket, 1)
                )
            )
            stack.enter_context(
                mock.patch.object(
                    module.measured,
                    "require_ticket_usb_binding",
                    return_value={"topology": "2-1.3"},
                )
            )
            stack.enter_context(
                mock.patch.object(
                    module,
                    "revalidate_ticket_hardened",
                    return_value=(ticket.device, 2, {"mock": True}),
                )
            )
            stack.enter_context(mock.patch.object(module, "run_noap_odin", side_effect=noap))
            stack.enter_context(
                mock.patch.object(
                    module.measured,
                    "wait_magisk_android",
                    return_value=(
                        "RFCT519XWGK",
                        {"model": "SM-S906N", "root": "uid=0(root)"},
                    ),
                )
            )
            absence = mock.patch.object(module.odin_core, "wait_for_no_live_endpoint")
            absence_mock = stack.enter_context(absence)
            if absence_error is not None:
                absence_mock.side_effect = absence_error
            elif enumeration_error is not None:
                stack.enter_context(
                    mock.patch.object(
                        module, "bounded_odin_runner", side_effect=enumeration_error
                    )
                )

                def fail_enumeration(odin, _run_dir, *, runner, **_kwargs):
                    return runner([str(odin), "-l"], 1.0)

                absence_mock.side_effect = fail_enumeration
            else:
                absence_mock.return_value = absence_result or SimpleNamespace(
                    absent=True, timed_out=False
                )
            if publish_bytes is not None:
                stack.enter_context(
                    mock.patch.object(
                        module, "durable_create_bytes_at", side_effect=publish_bytes
                    )
                )
            return module.live_run(root, args)

    def test_android_proof_survives_no_odin_observer_failure(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rc = self.run_mocked_post_android_live(
                root,
                absence_error=module.odin_core.OdinTransitionError(
                    "injected no-Odin observer failure"
                ),
            )
            run_dir = root / module.RECOVERY_RUN_ROOT / (
                "s22plus-r4w1c2-noap-reboot-recovery-scenario"
            )
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(rc, 20)
        self.assertTrue(result["reboot"])
        self.assertEqual(result["android_serial"], "RFCT519XWGK")
        self.assertEqual(result["final_android"]["model"], "SM-S906N")
        self.assertIsNone(result["no_odin_endpoint"])
        self.assertEqual(
            result["timeline_phase_semantics"]["rollback_boot_ready"],
            "exact Android ready",
        )

    def test_failed_enumeration_evidence_is_bound_into_final_result(self):
        module = self.module
        error = module.BoundedOdinError(
            "injected sealed enumeration selector fault",
            b"enum-stdout-before-fault",
            b"enum-stderr-before-fault",
            runner_error=True,
            kill_sent=True,
            reaped=True,
            cleanup_error=None,
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rc = self.run_mocked_post_android_live(
                root, enumeration_error=error
            )
            run_dir = root / module.RECOVERY_RUN_ROOT / (
                "s22plus-r4w1c2-noap-reboot-recovery-scenario"
            )
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            stdout = (run_dir / "odin-enumeration-000000.stdout").read_bytes()
            stderr = (run_dir / "odin-enumeration-000000.stderr").read_bytes()
        self.assertEqual(rc, 20)
        self.assertEqual(stdout, b"enum-stdout-before-fault")
        self.assertEqual(stderr, b"enum-stderr-before-fault")
        self.assertEqual(len(result["odin_enumerations"]), 1)
        enumeration = result["odin_enumerations"][0]
        self.assertTrue(enumeration["kill_sent"])
        self.assertTrue(enumeration["reaped"])
        self.assertIn("selector fault", enumeration["runner_error"])

    def test_transient_result_publication_failure_is_retried_without_losing_pass(self):
        module = self.module
        real_publish = module.durable_create_bytes_at
        failed = False

        def publish(directory_fd, name, payload, *, display_path):
            nonlocal failed
            if name == "result.json" and not failed:
                failed = True
                raise OSError("injected first result publication failure")
            return real_publish(
                directory_fd, name, payload, display_path=display_path
            )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rc = self.run_mocked_post_android_live(root, publish_bytes=publish)
            run_dir = root / module.RECOVERY_RUN_ROOT / (
                "s22plus-r4w1c2-noap-reboot-recovery-scenario"
            )
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            timeline = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))
            state_exists = (root / "state" / "consumed.json").is_file()
        self.assertEqual(rc, 0)
        self.assertTrue(failed)
        self.assertTrue(state_exists)
        self.assertEqual(result["verdict"], module.PASS_VERDICT)
        self.assertEqual(result["timeline"]["events"], timeline["events"])
        self.assertEqual(
            [event["name"] for event in timeline["events"]],
            list(module.core.TIMELINE_NAMES),
        )

    def test_failure_finalization_retries_transient_timeline_and_result_errors(self):
        module = self.module
        real_publish = module.durable_create_bytes_at
        failed_names = set()

        def publish(directory_fd, name, payload, *, display_path):
            if name in {"timeline.json", "result.json"} and name not in failed_names:
                failed_names.add(name)
                raise OSError(f"injected first {name} publication failure")
            return real_publish(
                directory_fd, name, payload, display_path=display_path
            )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rc = self.run_mocked_post_android_live(
                root,
                absence_error=module.odin_core.OdinTransitionError(
                    "injected no-Odin observer failure"
                ),
                publish_bytes=publish,
            )
            run_dir = root / module.RECOVERY_RUN_ROOT / (
                "s22plus-r4w1c2-noap-reboot-recovery-scenario"
            )
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            timeline = json.loads((run_dir / "timeline.json").read_text(encoding="utf-8"))
        self.assertEqual(rc, 20)
        self.assertEqual(failed_names, {"timeline.json", "result.json"})
        self.assertEqual(result["verdict"], module.FAIL_VERDICT)
        self.assertEqual(result["timeline"]["events"], timeline["events"])

    def test_state_parent_swap_after_publish_stops_before_usb_observation(self):
        module = self.module
        real_publish = module.durable_create_bytes_at
        swapped = False

        def publish(directory_fd, name, payload, *, display_path):
            nonlocal swapped
            record = real_publish(
                directory_fd, name, payload, display_path=display_path
            )
            if name == "consumed.json" and not swapped:
                swapped = True
                state_dir = display_path.parent
                moved = state_dir.with_name("state-held")
                state_dir.rename(moved)
                state_dir.mkdir()
            return record

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rc = self.run_mocked_post_android_live(
                root, publish_bytes=publish
            )
            run_dir = root / module.RECOVERY_RUN_ROOT / (
                "s22plus-r4w1c2-noap-reboot-recovery-scenario"
            )
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(rc, 20)
        self.assertTrue(swapped)
        self.assertFalse(result["reboot_attempted"])
        self.assertFalse((run_dir / "odin-reboot-attempt.json").exists())

    def test_state_parent_swap_after_last_prelaunch_check_cannot_restore_retry(self):
        module = self.module
        real_revalidate = module.revalidate_bound_file_path
        swapped = False

        def revalidate(directory_fd, directory, name, payload):
            nonlocal swapped
            value = real_revalidate(directory_fd, directory, name, payload)
            if name == "odin-reboot-attempt.json" and not swapped:
                state_dir = root / "state"
                state_dir.rename(root / "state-held")
                state_dir.mkdir()
                swapped = True
            return value

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(
                module, "revalidate_bound_file_path", side_effect=revalidate
            ):
                rc = self.run_mocked_post_android_live(root)
            run_dir = root / module.RECOVERY_RUN_ROOT / (
                "s22plus-r4w1c2-noap-reboot-recovery-scenario"
            )
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            guard = root / ".consumed.json.guard"
            guard_exists = guard.is_file()
            guard_bytes = guard.read_bytes()
            held_state_bytes = (root / "state-held" / "consumed.json").read_bytes()
        self.assertEqual(rc, 20)
        self.assertTrue(swapped)
        self.assertTrue(result["reboot_attempted"])
        self.assertEqual(result["verdict"], module.FAIL_VERDICT)
        self.assertTrue(guard_exists)
        self.assertEqual(guard_bytes, held_state_bytes)

    def test_common_private_parent_swap_cannot_restore_retry_authority(self):
        module = self.module
        real_revalidate = module.revalidate_bound_file_path
        swapped = False

        def revalidate(directory_fd, directory, name, payload):
            nonlocal swapped
            value = real_revalidate(directory_fd, directory, name, payload)
            if name == "odin-reboot-attempt.json" and not swapped:
                private = root / "workspace/private"
                private.rename(root / "workspace/private-held")
                (root / "workspace/private/runs").mkdir(parents=True)
                (root / "workspace/private/state").mkdir()
                swapped = True
            return value

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(
                module, "revalidate_bound_file_path", side_effect=revalidate
            ):
                rc = self.run_mocked_post_android_live(root, default_layout=True)
            held_run = root / "workspace/private-held/runs" / (
                "s22plus-r4w1c2-noap-reboot-recovery-scenario"
            )
            result = json.loads((held_run / "result.json").read_text(encoding="utf-8"))
            guard = module.recovery_guard_path(root)
            guard_exists = guard.is_file()
            consumed = module.recovery_consumed(root)
            canonical_state_exists = (root / module.RECOVERY_STATE).exists()
        self.assertEqual(rc, 20)
        self.assertTrue(swapped)
        self.assertTrue(result["reboot_attempted"])
        self.assertEqual(result["verdict"], module.FAIL_VERDICT)
        self.assertTrue(guard_exists)
        self.assertTrue(consumed)
        self.assertFalse(canonical_state_exists)

    def test_run_parent_swap_after_observation_cannot_publish_pass(self):
        module = self.module

        class SwapOnAbsent:
            def __init__(self, root):
                self.root = root
                self.did_swap = False

            @property
            def absent(self):
                if not self.did_swap:
                    run_dir = self.root / module.RECOVERY_RUN_ROOT / (
                        "s22plus-r4w1c2-noap-reboot-recovery-scenario"
                    )
                    run_dir.rename(run_dir.with_name(f"{run_dir.name}-held"))
                    run_dir.mkdir()
                    self.did_swap = True
                return True

            @property
            def timed_out(self):
                return False

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            observer = SwapOnAbsent(root)
            rc = self.run_mocked_post_android_live(root, absence_result=observer)
            canonical = root / module.RECOVERY_RUN_ROOT / (
                "s22plus-r4w1c2-noap-reboot-recovery-scenario"
            )
            held = canonical.with_name(f"{canonical.name}-held")
            result = json.loads((held / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(rc, 20)
        self.assertTrue(observer.did_swap)
        self.assertEqual(result["verdict"], module.FAIL_VERDICT)
        self.assertFalse((canonical / "result.json").exists())

    def test_context_teardown_failure_occurs_before_pass_publication(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rc = self.run_mocked_post_android_live(
                root, transaction_error=RuntimeError("injected transaction teardown")
            )
            run_dir = root / module.RECOVERY_RUN_ROOT / (
                "s22plus-r4w1c2-noap-reboot-recovery-scenario"
            )
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(rc, 20)
        self.assertEqual(result["verdict"], module.FAIL_VERDICT)
        self.assertIn("transaction teardown", result["error"])

    def test_summary_sink_failure_cannot_invalidate_canonical_pass(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch("builtins.print", side_effect=BrokenPipeError("closed")):
                rc = self.run_mocked_post_android_live(root)
            run_dir = root / module.RECOVERY_RUN_ROOT / (
                "s22plus-r4w1c2-noap-reboot-recovery-scenario"
            )
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(rc, 0)
        self.assertEqual(result["verdict"], module.PASS_VERDICT)

    def test_consumes_before_first_endpoint_observation_and_cannot_retry(self):
        module = self.module
        offline = {
            "recovery_consumed": False,
            "incident": {
                "android_serial": "RFCT519XWGK",
                "usb_binding": {
                    "topology": "2-1.3",
                    "serial_sha256": "c" * 64,
                    "download_serial_state": "absent",
                },
                "files": {
                    "consumed": {"sha256": "d" * 64},
                    "stock_intent": {"sha256": "e" * 64},
                },
            },
            "helper": {"sha256": "1" * 64},
            "test": {"sha256": "2" * 64},
            "dependencies": {},
            "policy_draft": {"sha256": "f" * 64},
        }
        policy = {"active": True, "sha256": "a" * 64}
        args = SimpleNamespace(
            ack=module.LIVE_ACK,
            odin=module.connected.DEFAULT_ODIN,
            endpoint_wait_sec=1.0,
            android_wait_sec=1.0,
            odin_absence_wait_sec=1.0,
        )

        @contextlib.contextmanager
        def odin_session(_path):
            yield 9, Path("/proc/self/fd/9")

        @contextlib.contextmanager
        def transaction(_run_dir):
            yield object()

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / module.RECOVERY_RUN_ROOT).mkdir(parents=True)
            (root / "state").mkdir()
            original_strftime = module.time.strftime
            run_names = iter(("run-one", "run-two"))

            def named_runs(format_string, *values):
                if format_string == "%Y%m%dT%H%M%SZ":
                    return next(run_names)
                return original_strftime(format_string, *values)

            with mock.patch.object(module, "RECOVERY_STATE", Path("state/consumed.json")), mock.patch.object(
                module, "offline_check", return_value=offline
            ), mock.patch.object(
                module, "policy_status", return_value=policy
            ), mock.patch.object(
                module, "helper_identity", return_value={"sha256": "1" * 64}
            ), mock.patch.object(
                module, "test_identity", return_value={"sha256": "2" * 64}
            ), mock.patch.object(
                module.measured, "pinned_odin_session", side_effect=odin_session
            ), mock.patch.object(
                module.odin_core, "transaction_session", side_effect=transaction
            ), mock.patch.object(
                module,
                "wait_for_endpoint_hardened",
                side_effect=module.measured.GateError("endpoint unavailable"),
            ) as wait, mock.patch.object(
                module.time, "strftime", side_effect=named_runs
            ):
                self.assertEqual(module.live_run(root, args), 20)
                first_run = root / module.RECOVERY_RUN_ROOT / (
                    "s22plus-r4w1c2-noap-reboot-recovery-run-one"
                )
                first_result = json.loads(
                    (first_run / "result.json").read_text(encoding="utf-8")
                )
                self.assertFalse(first_result["reboot_attempted"])
                self.assertFalse(first_result["reboot_command_returned"])
                self.assertEqual(
                    [event["name"] for event in first_result["timeline"]["events"]],
                    list(module.core.TIMELINE_NAMES),
                )
                state = root / module.RECOVERY_STATE
                self.assertTrue(state.is_file())
                record = json.loads(state.read_text(encoding="utf-8"))
                self.assertEqual(
                    record["physical_continuity_basis"],
                    module.PHYSICAL_CONTINUITY_BASIS,
                )
                self.assertEqual(wait.call_count, 1)
                self.assertEqual(module.live_run(root, args), 20)
                self.assertEqual(wait.call_count, 1)

    def test_timeline_is_single_events_schema(self):
        events = self.module.exact_timeline(
            "2026-07-20T00:00:00.000000Z",
            "2026-07-20T00:00:01.000000Z",
            "2026-07-20T00:00:02.000000Z",
            "2026-07-20T00:00:03.000000Z",
        )
        self.assertEqual([event["name"] for event in events], list(self.module.core.TIMELINE_NAMES))
        self.assertTrue(all(set(event) == {"name", "timestamp_utc"} for event in events))

    def test_policy_absence_is_inactive(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "AGENTS.md").write_text("no policy\n", encoding="utf-8")
            with mock.patch.object(module, "stable_bytes", return_value=b"no policy\n"):
                self.assertFalse(module.policy_status(root)["active"])

    def test_guard_alone_permanently_marks_recovery_consumed(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(
            module, "RECOVERY_STATE", Path("state/consumed.json")
        ):
            root = Path(temporary)
            guard = module.recovery_guard_path(root)
            guard.write_text("consumed\n", encoding="ascii")
            self.assertTrue(module.recovery_consumed(root))
            self.assertFalse((root / module.RECOVERY_STATE).exists())

    def test_duplicate_policy_marker_is_rejected(self):
        module = self.module
        text = f"{module.POLICY_BEGIN}\n{module.POLICY_END}\n{module.POLICY_END}"
        with self.assertRaisesRegex(module.RecoveryError, "duplicate"):
            module.extract_policy(text)

    def test_descriptor_evidence_rejects_hardlink_alias(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary, self.opened_directory(
            temporary
        ) as directory_fd:
            root = Path(temporary)
            payload = b"private-evidence"
            (root / "record").write_bytes(payload)
            os.link(root / "record", root / "alias")
            with self.assertRaisesRegex(module.RecoveryError, "not private"):
                module.exact_record_at(
                    directory_fd,
                    "record",
                    payload,
                    display_path=root / "record",
                )

    def test_recovery_state_is_exclusive(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / module.RECOVERY_RUN_ROOT / "run"
            run_dir.mkdir(parents=True)
            state = root / module.RECOVERY_STATE
            state.parent.mkdir(parents=True)
            state.write_text("{}\n", encoding="ascii")
            with self.opened_directory(run_dir) as run_dir_fd, self.opened_directory(
                state.parent
            ) as state_dir_fd, self.opened_directory(
                module.recovery_guard_path(root).parent
            ) as guard_dir_fd, self.assertRaisesRegex(
                module.RecoveryError, "already consumed"
            ):
                module.create_recovery_state(
                    root,
                    run_dir_fd=run_dir_fd,
                    state_dir_fd=state_dir_fd,
                    guard_dir_fd=guard_dir_fd,
                    policy={"sha256": "a" * 64},
                    incident={
                        "files": {
                            "consumed": {"sha256": "b" * 64},
                            "stock_intent": {"sha256": "c" * 64},
                        }
                    },
                    run_dir=run_dir,
                    helper={"sha256": "1" * 64},
                    test={"sha256": "2" * 64},
                    dependencies={},
                    policy_draft={"sha256": "d" * 64},
                )

    def test_recovery_state_rejects_indirect_state_directory(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_dir = root / module.RECOVERY_RUN_ROOT / "run"
            run_dir.mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            (root / "state").symlink_to(outside, target_is_directory=True)
            with mock.patch.object(module, "RECOVERY_STATE", Path("state/consumed.json")):
                with self.assertRaisesRegex(module.RecoveryError, "direct directory"):
                    module.open_bound_directory(root, root / "state")

    def test_run_directory_rejects_indirect_run_root(self):
        module = self.module
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "workspace" / "private").mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            (root / module.RECOVERY_RUN_ROOT).symlink_to(
                outside, target_is_directory=True
            )
            with self.assertRaisesRegex(module.RecoveryError, "direct directory"):
                module.allocate_recovery_run_dir(root)

    def test_old_consumed_policy_must_be_exactly_retired(self):
        module = self.module
        active = (
            f"{module.OLD_POLICY_BEGIN}\n{module.OLD_POLICY_ACTIVE}\n"
            f"{module.OLD_POLICY_END}\n"
        )
        with self.assertRaisesRegex(module.RecoveryError, "not exactly retired"):
            module.require_old_policy_retired(active)
        retired = active.replace(
            module.OLD_POLICY_ACTIVE, module.OLD_POLICY_RETIRED
        )
        module.require_old_policy_retired(retired)
        with self.assertRaisesRegex(module.RecoveryError, "not exactly retired"):
            module.require_old_policy_retired(
                retired + f"stray={module.OLD_POLICY_ACTIVE}\n"
            )

    def test_live_rejects_inactive_policy_before_device_contact(self):
        module = self.module
        args = SimpleNamespace(
            ack=module.LIVE_ACK,
            odin=Path("/usr/bin/odin4"),
            endpoint_wait_sec=1.0,
            android_wait_sec=1.0,
            odin_absence_wait_sec=1.0,
        )
        offline = {
            "recovery_consumed": False,
            "incident": {"usb_binding": {}},
        }
        with mock.patch.object(module, "offline_check", return_value=offline), mock.patch.object(
            module, "policy_status", return_value={"active": False}
        ), mock.patch.object(module.measured, "wait_for_endpoint") as wait:
            with self.assertRaisesRegex(module.RecoveryError, "inactive"):
                module.live_run(ROOT, args)
        wait.assert_not_called()


if __name__ == "__main__":
    unittest.main()
