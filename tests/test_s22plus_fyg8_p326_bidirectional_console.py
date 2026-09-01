from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import socket
import sys
import threading
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))


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


class P326BidirectionalConsoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = load(
            "p326_console_runtime_test",
            REVALIDATION / "s22plus_fyg8_p326_bidirectional_console_runtime.py",
        )
        cls.observer = load(
            "p326_bidirectional_observer_test",
            REVALIDATION / "s22plus_fyg8_p326_bidirectional_acm_observer.py",
        )
        cls.artifact = load(
            "p326_artifact_test",
            REVALIDATION / "s22plus_fyg8_p326_artifact_identity.py",
        )
        cls.adapter = load(
            "p326_stock_adapter_test",
            REVALIDATION / "s22plus_fyg8_p326_stock_process_v2_adapter.py",
        )
        cls.builder = load(
            "p326_builder_test",
            ANALYSIS / "s22plus_fyg8_p326_stock_candidate_build.py",
        )

    def test_runtime_delta_is_exact_and_transcripts_are_small(self) -> None:
        path = (
            ROOT
            / "workspace/private/outputs/s22plus_fyg8_p325/stock-candidate-build-v1-20260901-02/stock-sources/s22plus_fyg8_p290_e3_runtime.inc.c"
        )
        before = path.read_bytes()
        after = self.runtime.transform_runtime_include(before)
        receipt = self.runtime.validate_transform(before, after)
        self.assertEqual(receipt["changed_anchors"], ["p319_stock_publish", "p326_console_helper"])
        self.assertEqual(len(self.runtime.HOST_TRANSCRIPT), 77)
        self.assertEqual(len(self.runtime.DEVICE_TRANSCRIPT), 145)
        self.assertIn(b"/bin/busybox", after)
        self.assertNotIn(b"ash -i", after)

    def test_socket_exchange_proves_both_directions(self) -> None:
        host, device = socket.socketpair()
        host.setblocking(False)
        errors: list[BaseException] = []

        def receive_exact(amount: int) -> bytes:
            value = bytearray()
            while len(value) < amount:
                value.extend(device.recv(amount - len(value)))
            return bytes(value)

        def simulate() -> None:
            try:
                device.sendall(self.runtime.DEVICE_BANNER)
                self.assertEqual(receive_exact(len(self.runtime.HOST_PING)), self.runtime.HOST_PING)
                device.sendall(self.runtime.DEVICE_PONG)
                self.assertEqual(receive_exact(len(self.runtime.HOST_SHELL)), self.runtime.HOST_SHELL)
                device.sendall(self.runtime.DEVICE_SHELL_OK)
            except BaseException as exc:  # pragma: no cover - surfaced below
                errors.append(exc)
            finally:
                device.close()

        thread = threading.Thread(target=simulate)
        thread.start()
        writer = Writer()
        audit = self.observer.RoundTripAudit()
        try:
            self.assertTrue(
                self.observer._exchange(host.fileno(), time.monotonic() + 2, writer, audit)
            )
        finally:
            host.close()
            thread.join(timeout=2)
        if errors:
            raise errors[0]
        self.assertEqual(bytes(audit.tx), self.runtime.HOST_TRANSCRIPT)
        self.assertEqual(bytes(writer.payload), self.runtime.DEVICE_TRANSCRIPT)
        self.assertTrue(audit.banner_seen and audit.pong_seen and audit.shell_ok_seen)

    def test_wrong_banner_stops_before_any_host_write(self) -> None:
        host, device = socket.socketpair()
        host.setblocking(False)
        device.sendall(b"X" * len(self.runtime.DEVICE_BANNER))
        device.close()
        writer = Writer()
        audit = self.observer.RoundTripAudit()
        try:
            self.assertFalse(
                self.observer._exchange(host.fileno(), time.monotonic() + 1, writer, audit)
            )
        finally:
            host.close()
        self.assertEqual(bytes(audit.tx), b"")

    def test_valid_transcript_with_trailing_bytes_is_rejected_and_retained(self) -> None:
        host, device = socket.socketpair()
        host.setblocking(False)
        extra = b"TRAILING"
        errors: list[BaseException] = []

        def receive_exact(amount: int) -> bytes:
            value = bytearray()
            while len(value) < amount:
                value.extend(device.recv(amount - len(value)))
            return bytes(value)

        def simulate() -> None:
            try:
                device.sendall(self.runtime.DEVICE_BANNER)
                self.assertEqual(
                    receive_exact(len(self.runtime.HOST_PING)),
                    self.runtime.HOST_PING,
                )
                device.sendall(self.runtime.DEVICE_PONG)
                self.assertEqual(
                    receive_exact(len(self.runtime.HOST_SHELL)),
                    self.runtime.HOST_SHELL,
                )
                device.sendall(self.runtime.DEVICE_SHELL_OK + extra)
            except BaseException as exc:  # pragma: no cover - surfaced below
                errors.append(exc)
            finally:
                device.close()

        thread = threading.Thread(target=simulate)
        thread.start()
        writer = Writer()
        audit = self.observer.RoundTripAudit()
        try:
            self.assertFalse(
                self.observer._exchange(
                    host.fileno(), time.monotonic() + 2, writer, audit
                )
            )
        finally:
            host.close()
            thread.join(timeout=2)
        if errors:
            raise errors[0]
        self.assertEqual(
            bytes(writer.payload), self.runtime.DEVICE_TRANSCRIPT + extra
        )
        self.assertEqual(bytes(audit.trailing_rx), extra)

    def test_fresh_image_and_predecessor_rejection(self) -> None:
        source = self.artifact.stable_bytes(
            self.artifact.P319_IMAGE,
            "P319 Image",
            64 << 20,
            self.artifact.P319_IMAGE_IDENTITY,
        )
        image, receipt = self.artifact.transform_image(source)
        self.assertEqual(receipt["target"]["run_id_hex"], self.artifact.P326_RUN_ID_HEX)
        self.assertEqual(self.artifact.validate_image(image)["run_id_hex"], self.artifact.P326_RUN_ID_HEX)
        p325_ap = ROOT / (
            "workspace/private/outputs/s22plus_fyg8_p325/stock-candidate-build-v1-20260901-02/"
            "candidate-a/odin4/AP.tar.md5"
        )
        with self.assertRaises(self.artifact.ArtifactIdentityError):
            self.artifact.inspect_ap(p325_ap)

    def test_stock_adapter_is_fresh_and_noncausal(self) -> None:
        value = self.adapter.acceptance_fixture()
        checked = self.adapter.validate_acceptance_item(value)
        self.assertEqual(checked["run_id"], self.adapter.P326_RUN_ID_HEX)
        self.assertEqual(checked["overlay_contract_id"], self.adapter.P326_OVERLAY_CONTRACT_ID)
        self.assertFalse(checked["candidate_success"])
        self.assertFalse(checked["causal_result_allowed"])
        with self.assertRaises(self.adapter.DecodeError):
            self.adapter.decode_record(
                self.adapter.P325_RUN_ID, expected_run_id=self.adapter.P325_RUN_ID
            )

    def test_builder_reopens_ab_boot_only_busybox_candidate(self) -> None:
        result = self.builder.audit_existing()
        candidate = result["phase2"]["candidate"]
        self.assertTrue(candidate["byte_identical"])
        self.assertTrue(candidate["differs_from_consumed_p325"])
        self.assertEqual(candidate["a"]["ap_tar_md5"], candidate["b"]["ap_tar_md5"])
        self.assertEqual(candidate["a"]["busybox"], self.builder.BUSYBOX_IDENTITY)
        self.assertEqual(candidate["a"]["package"]["members"], ["boot.img.lz4"])
        self.assertTrue(result["phase2"]["rollback"]["untouched"])
        self.assertFalse(result["scope"]["device_contact"])
        self.assertFalse(result["scope"]["live_authority_created"])

    def test_busybox_input_is_static_and_restricted(self) -> None:
        self.builder._validate_busybox_inputs()
        payload = self.builder.BUSYBOX_CONFIG.read_bytes()
        self.assertIn(b"CONFIG_STATIC=y\n", payload)
        self.assertIn(b"CONFIG_ASH=y\n", payload)
        self.assertNotIn(b"CONFIG_SU=y\n", payload)
        self.assertNotIn(b"CONFIG_GETTY=y\n", payload)


if __name__ == "__main__":
    unittest.main()
