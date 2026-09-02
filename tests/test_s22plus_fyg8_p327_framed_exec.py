from __future__ import annotations

import importlib.util
from pathlib import Path
import socket
import sys
import threading
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class Writer:
    def __init__(self) -> None:
        self.payload = bytearray()

    def write_stdout(self, value: bytes) -> None:
        self.payload.extend(value)


class P327FramedExecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = load(
            "p327_framed_runtime_test",
            REVALIDATION / "s22plus_fyg8_p327_framed_exec_runtime.py",
        )
        cls.observer = load(
            "p327_framed_observer_test",
            REVALIDATION / "s22plus_fyg8_p327_framed_acm_observer.py",
        )
        cls.predecessor = ROOT / (
            "workspace/private/outputs/s22plus_fyg8_p326/"
            "stock-candidate-build-v1-20260902-08/stock-sources/"
            "s22plus_fyg8_p290_e3_runtime.inc.c"
        )

    @staticmethod
    def _receive_exact(peer: socket.socket, size: int) -> bytes:
        output = bytearray()
        while len(output) < size:
            chunk = peer.recv(size - len(output))
            if not chunk:
                raise AssertionError("unexpected peer EOF")
            output.extend(chunk)
        return bytes(output)

    def _receive_frame(self, peer: socket.socket):
        header = self._receive_exact(peer, self.observer.HEADER.size)
        length = int.from_bytes(header[6:8], "little")
        return self.observer.decode_frame(
            header + self._receive_exact(peer, length)
        )

    @staticmethod
    def _send_fragmented(peer: socket.socket, value: bytes) -> None:
        cursor = 0
        widths = (1, 3, 7, 13)
        index = 0
        while cursor < len(value):
            width = widths[index % len(widths)]
            peer.sendall(value[cursor : cursor + width])
            cursor += width
            index += 1

    def _serve(
        self,
        peer: socket.socket,
        commands: tuple[bytes, ...],
        outputs: tuple[bytes, ...],
        statuses: tuple[tuple[int, int, int, int], ...] | None = None,
    ) -> None:
        self._send_fragmented(peer, self.runtime.DEVICE_BANNER)
        opened = self._receive_frame(peer)
        self.assertEqual(
            opened,
            self.observer.Frame(
                self.runtime.FRAME_OPEN, 0, self.runtime.P327_RUN_ID
            ),
        )
        self._send_fragmented(
            peer,
            self.observer.encode_frame(
                self.runtime.FRAME_READY, 0, self.runtime.P327_RUN_ID
            ),
        )
        selected_statuses = statuses or tuple((0, 0, 0, 2) for _ in commands)
        for sequence, (command, output, status) in enumerate(
            zip(commands, outputs, selected_statuses, strict=True), start=1
        ):
            request = self._receive_frame(peer)
            self.assertEqual(
                request,
                self.observer.Frame(self.runtime.FRAME_EXEC, sequence, command),
            )
            for offset in range(0, len(output), self.runtime.MAX_FRAME_PAYLOAD):
                self._send_fragmented(
                    peer,
                    self.observer.encode_frame(
                        self.runtime.FRAME_DATA,
                        sequence,
                        output[offset : offset + self.runtime.MAX_FRAME_PAYLOAD],
                    ),
                )
            flags, exit_code, signal_number, duration_ms = status
            exit_payload = self.observer.EXIT.pack(
                flags,
                exit_code,
                signal_number,
                len(output),
                duration_ms,
            )
            self._send_fragmented(
                peer,
                self.observer.encode_frame(
                    self.runtime.FRAME_EXIT, sequence, exit_payload
                ),
            )
        closed = self._receive_frame(peer)
        self.assertEqual(
            closed,
            self.observer.Frame(
                self.runtime.FRAME_CLOSE, len(commands) + 1, b""
            ),
        )
        self._send_fragmented(
            peer,
            self.observer.encode_frame(
                self.runtime.FRAME_DONE,
                len(commands) + 1,
                self.observer.DONE.pack(len(commands)),
            ),
        )

    def _exchange(
        self,
        commands: tuple[bytes, ...],
        outputs: tuple[bytes, ...],
        statuses: tuple[tuple[int, int, int, int], ...] | None = None,
    ):
        host, device = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []

        def run() -> None:
            try:
                self._serve(device, commands, outputs, statuses)
            except BaseException as exc:  # pragma: no cover - surfaced below
                errors.append(exc)
            finally:
                device.close()

        thread = threading.Thread(target=run)
        thread.start()
        writer = Writer()
        try:
            result = self.observer.exchange_commands(
                host.fileno(), commands, timeout_sec=5, writer=writer
            )
        finally:
            host.close()
            thread.join(timeout=5)
        if thread.is_alive():
            self.fail("simulated P327 peer did not terminate")
        if errors:
            raise errors[0]
        self.assertEqual(bytes(writer.payload), bytes(result.audit.rx))
        return result

    def test_runtime_delta_is_exact_and_bounded(self) -> None:
        before = self.predecessor.read_bytes()
        after = self.runtime.transform_runtime_include(before)
        receipt = self.runtime.validate_transform(before, after)
        self.assertEqual(
            receipt["changed_anchors"],
            ["p326_console_helper", "p319_stock_publish"],
        )
        self.assertEqual(receipt["max_commands"], 3)
        self.assertEqual(receipt["command_timeout_sec"], 10)
        self.assertEqual(receipt["max_output_bytes"], 128 * 1024)
        self.assertTrue(receipt["child_kill_and_reap"])
        self.assertTrue(receipt["child_session_isolated"])
        self.assertTrue(receipt["descendant_group_cleanup"])
        self.assertFalse(receipt["caller_selected_command"])
        self.assertEqual(
            receipt["command_policy"], "fixed_three_command_proof_v1"
        )
        self.assertFalse(receipt["interactive_pty"])
        self.assertNotIn(self.runtime.p326.P326_HELPER, after)
        self.assertNotIn(b"ash -i", after)
        self.assertIn(b"source == target ? target : sys_dup3", after)
        exec_start = after.index(b"static long p327_exec_command")
        positive_read = after.index(b"if (amount > 0)", exec_start)
        negative_read = after.index(b"if (amount < 0", positive_read)
        self.assertNotIn(b"continue;", after[positive_read:negative_read])

    def test_frame_codec_reuses_o0_shape_with_fresh_magic(self) -> None:
        payload = b"/bin/busybox id"
        encoded = self.observer.encode_frame(
            self.runtime.FRAME_EXEC, 7, payload
        )
        self.assertEqual(len(encoded), 16 + len(payload))
        self.assertEqual(encoded[:4], b"S327")
        self.assertEqual(
            self.observer.decode_frame(encoded),
            self.observer.Frame(self.runtime.FRAME_EXEC, 7, payload),
        )
        corrupted = encoded[:-1] + bytes([encoded[-1] ^ 1])
        with self.assertRaises(self.observer.FramedObserverError):
            self.observer.decode_frame(corrupted)

    def test_default_proof_exchange_handles_fragmented_frames(self) -> None:
        outputs = (
            b"uid=0(root) gid=0(root) groups=0(root)\n",
            b"Linux s22plus 5.10.198 #1 SMP PREEMPT aarch64 GNU/Linux\n",
            f"P327-NONCE {self.runtime.P327_RUN_ID_HEX}\n".encode("ascii"),
        )
        result = self._exchange(self.observer.DEFAULT_COMMANDS, outputs)
        receipt = self.observer.validate_default_proof(result)
        self.assertEqual(receipt["command_count"], 3)
        self.assertTrue(receipt["pid1_framed_exec_proof"])
        self.assertFalse(receipt["interactive_pty_proof"])
        self.assertNotIn(outputs[0].decode("ascii"), str(receipt))

    def test_output_streaming_accepts_multiple_data_frames(self) -> None:
        outputs = (
            bytes(index & 0xFF for index in range(2500)),
            b"Linux s22plus\n",
            f"P327-NONCE {self.runtime.P327_RUN_ID_HEX}\n".encode("ascii"),
        )
        result = self._exchange(self.observer.DEFAULT_COMMANDS, outputs)
        self.assertEqual(result.commands[0].output, outputs[0])
        self.assertEqual(result.commands[0].sequence, 1)

    def test_timeout_and_truncation_status_are_explicit(self) -> None:
        output = b"X" * self.runtime.MAX_OUTPUT_BYTES
        flags = self.observer.FLAG_TIMEOUT | self.observer.FLAG_TRUNCATED
        outputs = (
            output,
            b"Linux s22plus\n",
            f"P327-NONCE {self.runtime.P327_RUN_ID_HEX}\n".encode("ascii"),
        )
        statuses = ((flags, -1, 9, 10_012), (0, 0, 0, 2), (0, 0, 0, 2))
        result = self._exchange(self.observer.DEFAULT_COMMANDS, outputs, statuses)
        item = result.commands[0]
        self.assertEqual(item.flags, flags)
        self.assertEqual(item.exit_code, -1)
        self.assertEqual(item.term_signal, 9)
        self.assertFalse(item.ok)

    def test_exec_failure_flag_must_match_exit_status(self) -> None:
        payload = self.observer.EXIT.pack(
            self.observer.FLAG_EXEC_FAILURE, 126, 0, 0, 1
        )
        self.assertEqual(self.observer._parse_exit(payload, 0)[1], 126)
        inconsistent = self.observer.EXIT.pack(0, 126, 0, 0, 1)
        with self.assertRaises(self.observer.FramedObserverError):
            self.observer._parse_exit(inconsistent, 0)

    def test_only_fixed_proof_commands_are_accepted(self) -> None:
        self.assertEqual(
            self.observer.validate_commands(self.observer.DEFAULT_COMMANDS),
            self.observer.DEFAULT_COMMANDS,
        )
        for commands in (
            (),
            (b"",),
            (b"bad\ncommand",),
            (b"x" * (self.runtime.MAX_COMMAND_SIZE + 1),),
            self.observer.DEFAULT_COMMANDS + (b"/bin/busybox true",),
            (b"/bin/busybox setsid /bin/busybox sleep 99",)
            + self.observer.DEFAULT_COMMANDS[1:],
        ):
            with self.assertRaises(self.observer.FramedObserverError):
                self.observer.validate_commands(commands)

    def test_wrong_ready_sequence_fails_without_exec(self) -> None:
        host, device = socket.socketpair()
        host.setblocking(False)

        def run() -> None:
            try:
                device.sendall(self.runtime.DEVICE_BANNER)
                self._receive_frame(device)
                device.sendall(
                    self.observer.encode_frame(
                        self.runtime.FRAME_READY, 9, self.runtime.P327_RUN_ID
                    )
                )
            finally:
                device.close()

        thread = threading.Thread(target=run)
        thread.start()
        try:
            with self.assertRaises(self.observer.FramedObserverError):
                self.observer.exchange_commands(
                    host.fileno(), self.observer.DEFAULT_COMMANDS, timeout_sec=2
                )
        finally:
            host.close()
            thread.join(timeout=2)

    def test_timeout_must_be_positive_and_finite(self) -> None:
        for timeout in (
            float("nan"),
            float("inf"),
            float("-inf"),
            0,
            -1,
            121,
            10**1000,
            True,
        ):
            with self.assertRaises(self.observer.FramedObserverError):
                self.observer.exchange_commands(
                    0, self.observer.DEFAULT_COMMANDS, timeout_sec=timeout
                )


if __name__ == "__main__":
    unittest.main()
