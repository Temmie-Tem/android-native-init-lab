from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path
import socket
from types import SimpleNamespace
import sys
import tempfile
import threading
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import device_action_f1_live_v2 as live  # noqa: E402


TEST_KEY = bytes(range(32))
TEST_KEY_SHA256 = hashlib.sha256(TEST_KEY).hexdigest()


def _observer() -> dict[str, object]:
    return live.typed_evidence.p328_authenticated_framed_observer_spec()


def _prepared(run_dir: Path, *, key_sha256: str = TEST_KEY_SHA256) -> live.PreparedRun:
    acceptance = dict(live.typed_evidence.p328_stock_adapter.acceptance_fixture())
    acceptance["run_id"] = live.p328_auth_runtime.P328_RUN_ID_HEX
    manifest = {
        "manifest_id": "p328-live-test",
        "candidate_ap": {"sha256": "a" * 64},
        "observation": {
            "acceptance": acceptance,
            "candidate_observer": _observer(),
            live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: (
                live.typed_evidence.CANDIDATE_AUTHENTICATED_FRAMED_EXEC_ROLE
            ),
        },
    }
    bundle = SimpleNamespace(
        manifest=manifest,
        sha256="b" * 64,
        profile={"target": {"download": {}}},
    )
    prepared = {
        "approval_binding_sha256": "c" * 64,
        "p328_auth_key_identity": {"size": 32, "sha256": key_sha256},
        "approval_binding": {
            "p328_auth_key_identity": {"size": 32, "sha256": key_sha256}
        },
    }
    return live.PreparedRun(
        ROOT,
        run_dir,
        bundle,
        prepared,
        {
            "schema": live.PRIVATE_TARGET_SCHEMA,
            "serial": "fixture",
            "topology": live.p324_typec_lane.SOURCE_TOPOLOGY,
        },
    )


def _lane(candidate_digest: str = "e" * 64) -> dict[str, object]:
    source = live.p324_typec_lane.SOURCE_TOPOLOGY
    candidate = live.p324_typec_lane.CANDIDATE_TOPOLOGY
    return {
        "schema": live.p324_cdc_observer.SCHEMA,
        "contract_id": live.p324_cdc_observer.CONTRACT_ID,
        "target": live.p324_cdc_observer.TARGET,
        "lane_binding": {"fixture": True},
        "lane_binding_sha256": "f" * 64,
        "arm": {"arm": True},
        "source_topology": source,
        "candidate_topology": candidate,
        "selector_topology_count": 1,
        "partner_before": {"fixture": 1},
        "partner_after": {"fixture": 1},
        "partner_poll_count": 1,
        "partner_continuous": True,
        "end_inventory": {
            "scan_complete": True,
            "all_endpoint_count": 1,
            "all_endpoint_identity_sha256": [candidate_digest],
            "foreign_candidate_like_count": 0,
            "foreign_candidate_like_identity_sha256": [],
            "rows": {
                source: {
                    "topology_sha256": hashlib.sha256(b"2-1.3").hexdigest(),
                    "endpoint_count": 0,
                    "exact_candidate_count": 0,
                    "candidate_like_count": 0,
                    "endpoint_identity_sha256": [],
                    "present": False,
                },
                candidate: {
                    "topology_sha256": hashlib.sha256(b"3-1.3").hexdigest(),
                    "endpoint_count": 1,
                    "exact_candidate_count": 1,
                    "candidate_like_count": 1,
                    "endpoint_identity_sha256": [candidate_digest],
                    "present": True,
                },
            },
        },
        "both_topologies_inventory_complete": True,
        "accepted_inventory_exact": True,
        "same_run_typec_partner_continuity": True,
        "accepted_for_p324": True,
        "opens_only_candidate_topology": True,
        "device_commands": False,
    }


def _write_common_receipts(run_dir: Path) -> None:
    live.cdc_acm_observer.persist_json(
        run_dir / "candidate-observer-baseline.json", {"baseline": True}
    )
    live.cdc_acm_observer.persist_json(
        run_dir / "candidate-observer-guard.json", {"guard": True}
    )


def _receive_frame(peer: socket.socket) -> live.p328_auth_observer.Frame:
    header = bytearray()
    while len(header) < live.p328_auth_observer.HEADER.size:
        header.extend(peer.recv(live.p328_auth_observer.HEADER.size - len(header)))
    length = live.p328_auth_observer.HEADER.unpack(bytes(header))[3]
    payload = bytearray(header)
    while len(payload) < live.p328_auth_observer.HEADER.size + length:
        payload.extend(
            peer.recv(live.p328_auth_observer.HEADER.size + length - len(payload))
        )
    return live.p328_auth_observer.decode_frame(bytes(payload))


def _serve(peer: socket.socket, errors: list[BaseException]) -> None:
    observer = live.p328_auth_observer
    runtime = live.p328_auth_runtime
    nonce = bytes(range(1, 33))
    outputs = (
        b"uid=0(root) gid=0(root) groups=0(root)\n",
        b"Linux s22plus 5.10.198 aarch64 GNU/Linux\n",
        f"P328-NONCE {runtime.P328_RUN_ID_HEX}\n".encode("ascii"),
    )
    try:
        peer.sendall(runtime.DEVICE_BANNER)
        opened = _receive_frame(peer)
        assert opened == observer.Frame(runtime.FRAME_OPEN, 0, runtime.P328_RUN_ID)
        peer.sendall(observer.encode_frame(runtime.FRAME_CHALLENGE, 0, nonce))
        auth = _receive_frame(peer)
        assert auth.frame_type == runtime.FRAME_AUTH and auth.sequence == 1
        assert auth.payload == observer.compute_open_tag(
            TEST_KEY, runtime.P328_RUN_ID, nonce
        )
        peer.sendall(
            observer.encode_frame(
                runtime.FRAME_READY,
                1,
                observer.compute_ready_tag(TEST_KEY, runtime.P328_RUN_ID, nonce),
            )
        )
        for sequence, (command, output) in enumerate(
            zip(observer.DEFAULT_COMMANDS, outputs, strict=True), start=2
        ):
            request = _receive_frame(peer)
            assert request.frame_type == runtime.FRAME_EXEC
            assert request.sequence == sequence
            assert request.payload[32:] == command
            assert request.payload[:32] == observer.compute_exec_tag(
                TEST_KEY, runtime.P328_RUN_ID, nonce, sequence, command
            )
            peer.sendall(observer.encode_frame(runtime.FRAME_DATA, sequence, output))
            peer.sendall(
                observer.encode_frame(
                    runtime.FRAME_EXIT,
                    sequence,
                    observer.EXIT.pack(0, 0, 0, len(output), 1),
                )
            )
        close_sequence = len(observer.DEFAULT_COMMANDS) + 2
        closed = _receive_frame(peer)
        assert closed.frame_type == runtime.FRAME_CLOSE
        assert closed.sequence == close_sequence
        assert closed.payload == observer.compute_close_tag(
            TEST_KEY, runtime.P328_RUN_ID, nonce, close_sequence
        )
        peer.sendall(
            observer.encode_frame(
                runtime.FRAME_DONE,
                close_sequence,
                observer.DONE.pack(3),
            )
        )
    except BaseException as exc:  # pragma: no cover - surfaced below
        errors.append(exc)


class P328LiveIntegrationTests(unittest.TestCase):
    def test_p328_publishes_once_and_final_result_has_a_separate_bound(self) -> None:
        source = inspect.getsource(live._P328ObserverSession.observe)
        self.assertIn("super()._observe_value", source)
        self.assertNotIn("unlink", source)
        value = {"payload": "x" * (live.core.MAX_RECORD + 1)}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(live.core.F1V2Error):
                live.core._write_atomic(root / "ordinary.json", value)
            live._write_live_result(root / "live-result.json", value)
            self.assertLess(
                (root / "live-result.json").stat().st_size,
                live.MAX_LIVE_RESULT_RECORD,
            )
            with self.assertRaises(live.core.F1V2Error):
                live.core._write_live_result(
                    root / "unbounded.json",
                    {"payload": "small"},
                )
            oversized = root / "oversized"
            oversized.mkdir()
            with self.assertRaises(live.core.F1V2Error):
                live.core._write_live_result(
                    oversized / "live-result.json",
                    {"payload": "x" * live.MAX_LIVE_RESULT_RECORD},
                )

    def test_backend_selects_p328_before_p327(self) -> None:
        run_dir = Path(tempfile.mkdtemp())
        prepared = _prepared(run_dir)
        backend = live.SamsungOdinBackend.__new__(live.SamsungOdinBackend)
        backend.usb_root = Path("/unused/usb")
        backend.typec_root = Path("/unused/typec")
        sentinel = object()
        with (
            mock.patch.object(
                live,
                "_p324_typec_lane_value",
                return_value=({"lane": True}, {"receipt": True}),
            ),
            mock.patch.object(
                live, "_p328_candidate_observer_session", return_value=sentinel
            ) as selected,
        ):
            result = backend.candidate_observer_session(prepared)
        self.assertIs(result, sentinel)
        self.assertEqual(selected.call_args.args[0], prepared)

    def test_session_reads_fixed_key_before_protocol_and_keeps_receipt_path_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            run_dir.mkdir()
            key_path = Path(temporary) / "auth-key-v1.bin"
            key_path.write_bytes(TEST_KEY)
            key_path.chmod(0o400)
            prepared = _prepared(run_dir)
            _write_common_receipts(run_dir)
            with mock.patch.object(live, "P328_AUTH_KEY_PATH", key_path):
                key, digest = live._p328_read_auth_key(prepared)
            self.assertEqual(key, TEST_KEY)
            self.assertEqual(digest, TEST_KEY_SHA256)
            serialized = json.dumps(prepared.prepared, sort_keys=True)
            self.assertNotIn(TEST_KEY.hex(), serialized)
            self.assertNotIn(str(key_path), serialized)

    def test_authenticated_receipt_reopens_without_rereading_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            run_dir.mkdir()
            prepared = _prepared(run_dir)
            _write_common_receipts(run_dir)
            host, peer = socket.socketpair()
            host.setblocking(False)
            errors: list[BaseException] = []
            thread = threading.Thread(target=_serve, args=(peer, errors))
            thread.start()
            guard = SimpleNamespace(
                healthy=lambda **_kwargs: True,
                matches_node=lambda _node: True,
            )
            inherited = SimpleNamespace(
                delegate=SimpleNamespace(
                    partner_before={"fixture": 1},
                    partner_continuous=True,
                    partner_poll_count=1,
                    class_tty=Path("/unused/class-tty"),
                    arm_receipt={"arm": True},
                ),
                guard=guard,
                _select=lambda: (
                    "accepted",
                    SimpleNamespace(identity_sha256="e" * 64),
                ),
            )
            base = SimpleNamespace(
                guard=guard,
                binding=live._candidate_observer_binding(prepared),
                dev_root=Path("/unused/dev"),
                _raw_tty=lambda _descriptor: None,
            )
            session = live._P328ObserverSession(
                inherited,
                base,
                live._p327_inherited_spec(_observer()),
                run_dir,
                {"lane": True},
                {"receipt": True},
                Path("/unused/usb"),
                Path("/unused/typec"),
                auth_key=TEST_KEY,
                auth_key_sha256=TEST_KEY_SHA256,
            )
            session._lane_supplement = lambda _accepted: _lane()
            def read_endpoint(_endpoint, _deadline, writer):
                session.exchange = live.p328_auth_observer.exchange_commands(
                    host.fileno(), TEST_KEY, writer=writer, timeout_sec=5
                )
                session.proof = live.p328_auth_observer.validate_default_proof(
                    session.exchange
                )
                return "accepted"
            session._read_endpoint = read_endpoint
            try:
                session.observe(
                    timeout_sec=1,
                    download_departure={
                        "download_endpoint_absent": True,
                        "absence_timed_out": False,
                        "sequence": 1,
                    },
                )
            finally:
                host.close()
                thread.join(timeout=5)
                peer.close()
            if thread.is_alive():
                self.fail("simulated P328 peer did not terminate")
            if errors:
                raise errors[0]
            reopened = live._reopen_candidate_observation(prepared)
            self.assertTrue(reopened["valid_receipt"])
            self.assertTrue(reopened["accepted"])
            self.assertTrue(reopened["hmac_authenticated"])
            self.assertTrue(reopened["pid1_authenticated_framed_exec_proof"])
            self.assertTrue(reopened["busybox_ash_command_proof"])
            self.assertTrue(reopened["framed_session_closed"])
            self.assertTrue(reopened["caller_selected_command"])
            self.assertEqual(reopened["command_count"], 3)
            self.assertEqual(reopened["max_commands"], 16)
            with mock.patch.object(
                live.p328_artifact_identity,
                "read_auth_key",
                side_effect=AssertionError("reopen reread the key"),
            ):
                self.assertTrue(live._p328_validate_receipt(
                    prepared,
                    run_dir / "candidate-observer.json",
                    _observer(),
                )["accepted"])

    def test_wrong_key_stops_before_observer_arm_or_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            run_dir.mkdir()
            prepared = _prepared(run_dir)
            key_path = Path(temporary) / "wrong-auth-key.bin"
            key_path.write_bytes(b"W" * 32)
            key_path.chmod(0o400)
            with (
                mock.patch.object(live, "P328_AUTH_KEY_PATH", key_path),
                mock.patch.object(
                    live.p325_guard_adapter,
                    "observer_session",
                    side_effect=AssertionError("wrong key armed the observer"),
                ),
                self.assertRaises(live.F1LiveError),
            ):
                with live._p328_candidate_observer_session(
                    prepared,
                    _observer(),
                    lane_value={"lane": True},
                    lane_receipt={"receipt": True},
                    usb_root=Path("/unused/usb"),
                    typec_root=Path("/unused/typec"),
                ):
                    self.fail("wrong key opened a P328 observer session")
            self.assertFalse((run_dir / "candidate-observer.json").exists())


if __name__ == "__main__":
    unittest.main()
