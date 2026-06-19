from __future__ import annotations

import hashlib
import shlex
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


tcpctl = load_script("workspace/public/src/scripts/revalidation/tcpctl_host.py")


class FakeSocket:
    def __init__(self, chunks: list[bytes] | None = None) -> None:
        self.chunks = list(chunks or [])
        self.sent = bytearray()
        self.timeouts: list[float] = []
        self.shutdown_calls: list[int] = []

    def __enter__(self) -> "FakeSocket":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def settimeout(self, timeout: float) -> None:
        self.timeouts.append(timeout)

    def sendall(self, data: bytes) -> None:
        self.sent.extend(data)

    def recv(self, _size: int) -> bytes:
        if self.chunks:
            return self.chunks.pop(0)
        return b""

    def shutdown(self, flag: int) -> None:
        self.shutdown_calls.append(flag)


class FileAndSafetyHelpers(unittest.TestCase):
    def test_sha256_file_hashes_payload_in_chunks(self) -> None:
        data = (b"a90-tcpctl" * 200_000) + b"tail"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.bin"
            path.write_bytes(data)

            self.assertEqual(tcpctl.sha256_file(path), hashlib.sha256(data).hexdigest())

    def test_validate_install_target_accepts_only_runtime_helper_roots(self) -> None:
        for path in [
            "/cache/bin/a90_tcpctl",
            "/cache/a90-acdb-setcal-replay-v2636/a90_acdb_setcal_replay_execute_v2635",
            "/cache/a90-runtime/bin/a90_tcpctl",
            "/cache/a90-runtime/pkg/audio/setcal/internal-speaker-safe/00-set-arg.bin",
            "/mnt/sdext/a90/bin/a90_tcpctl",
        ]:
            tcpctl.validate_install_target(path)

        for path in [
            "cache/bin/a90_tcpctl",
            "/cache/bin/../a90_tcpctl",
            "/vendor/bin/a90_tcpctl",
            "/cache/bin/a90 tcpctl",
            "/cache/bin/a90$tcpctl",
        ]:
            with self.subTest(path=path):
                with self.assertRaisesRegex(RuntimeError, "unsafe|refusing"):
                    tcpctl.validate_install_target(path)


class TokenAndCommandHelpers(unittest.TestCase):
    def test_parse_tcpctl_token_finds_hex_token_and_rejects_missing(self) -> None:
        token = "0123456789abcdefABCDEF0123456789"
        self.assertEqual(tcpctl.parse_tcpctl_token(f"noise tcpctl_token={token}\n"), token)
        with self.assertRaisesRegex(RuntimeError, "token was not found"):
            tcpctl.parse_tcpctl_token("tcpctl_token=short\n")

    def test_tcpctl_command_requires_auth_only_for_run_and_shutdown(self) -> None:
        self.assertTrue(tcpctl.tcpctl_command_requires_auth("run /bin/true"))
        self.assertTrue(tcpctl.tcpctl_command_requires_auth("  shutdown"))
        self.assertFalse(tcpctl.tcpctl_command_requires_auth("ping"))
        self.assertFalse(tcpctl.tcpctl_command_requires_auth("status"))
        self.assertFalse(tcpctl.tcpctl_command_requires_auth(""))

    def test_get_tcpctl_token_uses_cache_then_cli_then_device_command(self) -> None:
        args = SimpleNamespace(token="A" * 32)
        self.assertEqual(tcpctl.get_tcpctl_token(args), "A" * 32)
        args.token = "B" * 32
        self.assertEqual(tcpctl.get_tcpctl_token(args), "A" * 32)

        args = SimpleNamespace(token=None, token_command="netservice token show", bridge_timeout=3)
        with mock.patch.object(tcpctl, "device_command", return_value="tcpctl_token=" + "C" * 32) as device:
            self.assertEqual(tcpctl.get_tcpctl_token(args), "C" * 32)
            self.assertEqual(tcpctl.get_tcpctl_token(args), "C" * 32)
        device.assert_called_once_with(args, "netservice token show", timeout=3)

    def test_tcpctl_run_line_quotes_arguments_for_shell_safe_remote_run(self) -> None:
        expected = "run /cache/bin/tool " + "'two words' " + shlex.quote("quote'it")
        self.assertEqual(
            tcpctl.tcpctl_run_line(["/cache/bin/tool", "two words", "quote'it"]),
            expected,
        )

    def test_tcpctl_listen_command_uses_token_path_or_legacy_dash(self) -> None:
        args = SimpleNamespace(
            device_binary="/bin/a90_tcpctl",
            device_ip="192.168.7.2",
            tcp_port=2325,
            idle_timeout=60,
            max_clients=8,
            token_path="/cache/token",
            no_auth=False,
        )
        self.assertEqual(
            tcpctl.tcpctl_listen_command(args),
            "run /bin/a90_tcpctl listen 192.168.7.2 2325 60 8 /cache/token",
        )
        args.no_auth = True
        self.assertEqual(
            tcpctl.tcpctl_listen_command(args),
            "run /bin/a90_tcpctl listen 192.168.7.2 2325 60 8 -",
        )


class TcpRequestHelpers(unittest.TestCase):
    def test_tcpctl_request_prefixes_auth_for_protected_commands_and_reads_response(self) -> None:
        fake = FakeSocket([b"out\n", b"OK\n"])
        args = SimpleNamespace(
            device_ip="192.168.7.2",
            tcp_port=2325,
            tcp_timeout=5.0,
            no_auth=False,
            token="D" * 32,
        )

        with mock.patch.object(tcpctl.socket, "create_connection", return_value=fake) as create:
            output = tcpctl.tcpctl_request(args, "run /bin/true\n")

        create.assert_called_once_with(("192.168.7.2", 2325), timeout=5.0)
        self.assertEqual(fake.sent.decode(), "auth " + "D" * 32 + "\nrun /bin/true\n")
        self.assertEqual(output, "out\nOK\n")

    def test_tcpctl_request_skips_auth_for_ping_or_no_auth_mode(self) -> None:
        fake = FakeSocket([b"pong\nOK\n"])
        args = SimpleNamespace(
            device_ip="192.168.7.2",
            tcp_port=2325,
            tcp_timeout=4.0,
            no_auth=False,
            token="E" * 32,
        )
        with mock.patch.object(tcpctl.socket, "create_connection", return_value=fake):
            tcpctl.tcpctl_request(args, "ping")
        self.assertEqual(fake.sent.decode(), "ping\n")

        fake = FakeSocket([b"bye\nOK\n"])
        args.no_auth = True
        with mock.patch.object(tcpctl.socket, "create_connection", return_value=fake):
            tcpctl.tcpctl_request(args, "shutdown")
        self.assertEqual(fake.sent.decode(), "shutdown\n")

    def test_tcpctl_expect_ok_and_install_command_classify_ok_and_error_responses(self) -> None:
        args = SimpleNamespace()
        with mock.patch.object(tcpctl, "tcpctl_request", return_value="value\nOK\n"):
            self.assertEqual(tcpctl.tcpctl_expect_ok(args, "status"), "value\nOK\n")
            self.assertEqual(tcpctl.tcpctl_install_command(args, "run chmod"), "value\nOK\n")

        with mock.patch.object(tcpctl, "tcpctl_request", return_value="\nERR denied\n"):
            with self.assertRaisesRegex(RuntimeError, "did not end with OK"):
                tcpctl.tcpctl_expect_ok(args, "status")
            self.assertEqual(
                tcpctl.tcpctl_install_command(args, "run rm", allow_error=True),
                "\nERR denied\n",
            )
            with self.assertRaisesRegex(RuntimeError, "install command did not end with OK"):
                tcpctl.tcpctl_install_command(args, "run rm", allow_error=False)

    def test_wait_for_tcpctl_retries_until_pong_ok_or_reports_last_os_error(self) -> None:
        args = SimpleNamespace()
        with mock.patch.object(tcpctl, "tcpctl_request", side_effect=[OSError("down"), "pong\nOK\n"]), \
                mock.patch.object(tcpctl.time, "monotonic", side_effect=[0.0, 0.1, 0.2, 0.3]), \
                mock.patch.object(tcpctl.time, "sleep") as sleep:
            self.assertEqual(tcpctl.wait_for_tcpctl(args, 5.0), "pong\nOK\n")
        sleep.assert_called_once_with(0.5)

        with mock.patch.object(tcpctl, "tcpctl_request", side_effect=OSError("still down")), \
                mock.patch.object(tcpctl.time, "monotonic", side_effect=[0.0, 0.1, 2.0]), \
                mock.patch.object(tcpctl.time, "sleep"):
            with self.assertRaisesRegex(RuntimeError, "still down"):
                tcpctl.wait_for_tcpctl(args, 1.0)


class DeviceCommandHelpers(unittest.TestCase):
    def test_cmdv1_unavailable_classifies_only_transport_and_encoding_failures(self) -> None:
        self.assertTrue(tcpctl.cmdv1_unavailable(OSError("serial gone")))
        self.assertTrue(tcpctl.cmdv1_unavailable(RuntimeError("serial device is not connected")))
        self.assertTrue(tcpctl.cmdv1_unavailable(RuntimeError("unknown command: cmdv1")))
        self.assertTrue(tcpctl.cmdv1_unavailable(RuntimeError("cmdv1 cannot safely encode command")))
        self.assertFalse(tcpctl.cmdv1_unavailable(RuntimeError("remote rc=7")))

    def test_device_command_falls_back_to_raw_bridge_when_cmdv1_auto_unavailable(self) -> None:
        args = SimpleNamespace(
            bridge_host="127.0.0.1",
            bridge_port=54321,
            bridge_timeout=9.0,
            busy_retries=1,
            busy_retry_sleep=0.0,
            menu_hide_sleep=0.0,
            device_protocol="auto",
        )
        with mock.patch.object(tcpctl, "run_device_cmdv1", side_effect=RuntimeError("unknown command: cmdv1")), \
                mock.patch.object(tcpctl, "bridge_command", return_value="ok\n[done]\n") as bridge:
            self.assertEqual(tcpctl.device_command(args, "version"), "ok\n[done]\n")
        bridge.assert_called_once_with("127.0.0.1", 54321, "version", 9.0)

    def test_device_command_retries_busy_by_hiding_menu_then_returns_cmdv1_text(self) -> None:
        args = SimpleNamespace(
            bridge_host="127.0.0.1",
            bridge_port=54321,
            bridge_timeout=9.0,
            busy_retries=2,
            busy_retry_sleep=0.0,
            menu_hide_sleep=0.0,
            device_protocol="cmdv1",
        )
        busy = tcpctl.ProtocolResult({}, {"status": "busy", "rc": "0"}, "menu busy\n")
        ok = tcpctl.ProtocolResult({}, {"status": "ok", "rc": "0"}, "version text\n")
        with mock.patch.object(tcpctl, "run_device_cmdv1", side_effect=[busy, ok]), \
                mock.patch.object(tcpctl, "best_effort_hide_menu") as hide, \
                mock.patch.object(tcpctl.time, "sleep"), \
                mock.patch("builtins.print"):
            self.assertEqual(tcpctl.device_command(args, "version"), "version text\n")
        hide.assert_called_once_with(args)


class CliCommandHelpers(unittest.TestCase):
    def test_command_run_strips_separator_quotes_args_and_prints_tcp_response(self) -> None:
        args = SimpleNamespace(run_args=["--", "/cache/bin/tool", "two words"])
        with mock.patch.object(tcpctl, "tcpctl_request", return_value="done\nOK\n") as request, \
                mock.patch("builtins.print") as printer:
            self.assertEqual(tcpctl.command_run(args), 0)
        request.assert_called_once_with(args, "run /cache/bin/tool 'two words'")
        printer.assert_called_once_with("done\nOK\n", end="")

        with self.assertRaisesRegex(SystemExit, "run requires"):
            tcpctl.command_run(SimpleNamespace(run_args=[]))


if __name__ == "__main__":
    unittest.main()
