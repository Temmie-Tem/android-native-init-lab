from __future__ import annotations

import hashlib
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


def _observer() -> dict[str, object]:
    run_id = live.p327_framed_runtime.P327_RUN_ID_HEX
    return {
        "kind": "exact_cdc_acm_framed_fixed_commands_v1",
        "usb_vendor_id": "04e8",
        "usb_product_id": "6861",
        "usb_serial": "S22E3" + run_id,
        "usb_driver": "cdc_acm",
        "usb_interface_number": "00",
        "banner_hex": live.p327_framed_runtime.DEVICE_BANNER.hex(),
        "protocol_contract": live.p327_framed_observer.CONTRACT_ID,
        "wire_magic": "S327",
        "frame_header_size": 16,
        "max_frame_payload": 1024,
        "max_commands": 3,
        "command_timeout_sec": 10,
        "max_output_bytes": 128 * 1024,
        "commands": [
            {
                "size": len(command),
                "sha256": hashlib.sha256(command).hexdigest(),
            }
            for command in live.p327_framed_observer.DEFAULT_COMMANDS
        ],
        "caller_selected_command": False,
        "interactive_pty": False,
    }


def _prepared() -> live.PreparedRun:
    run_id = live.p327_framed_runtime.P327_RUN_ID_HEX
    acceptance = dict(live.typed_evidence.p327_stock_adapter.acceptance_fixture())
    acceptance["run_id"] = run_id
    manifest = {
        "manifest_id": "p327-live-test",
        "candidate_ap": {"sha256": "a" * 64},
        "observation": {
            "acceptance": acceptance,
            "candidate_observer": _observer(),
            live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: (
                live.typed_evidence.CANDIDATE_FRAMED_FIXED_COMMAND_ROLE
            ),
        },
    }
    bundle = SimpleNamespace(
        manifest=manifest,
        sha256="b" * 64,
        profile={"target": {"download": {}}},
    )
    return live.PreparedRun(
        ROOT,
        ROOT / "workspace/private/p327-live-test",
        bundle,
        {"approval_binding_sha256": "c" * 64},
        {
            "schema": live.PRIVATE_TARGET_SCHEMA,
            "serial": "fixture",
            "topology": live.p324_typec_lane.SOURCE_TOPOLOGY,
        },
    )


class _Writer:
    def __init__(self) -> None:
        self.payload = bytearray()

    def write_stdout(self, payload: bytes) -> None:
        self.payload.extend(payload)


class P327LiveIntegrationTests(unittest.TestCase):
    def test_backend_selects_p327_before_p326(self) -> None:
        prepared = _prepared()
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
                live, "_p327_candidate_observer_session", return_value=sentinel
            ) as selected,
        ):
            result = backend.candidate_observer_session(prepared)
        self.assertIs(result, sentinel)
        self.assertEqual(selected.call_args.args[0], prepared)

    def test_trailing_probe_forwards_one_byte_before_reject(self) -> None:
        import select

        host, peer = socket.socketpair()
        try:
            host.setblocking(False)
            peer.sendall(b"!")
            writer = _Writer()
            self.assertEqual(
                live._p327_trailing_probe(host.fileno(), writer),  # noqa: SLF001
                b"!",
            )
            self.assertEqual(bytes(writer.payload), b"!")
            self.assertEqual(select.select([host.fileno()], [], [], 0)[0], [])
        finally:
            host.close()
            peer.close()

    def test_framed_receipt_reopens_after_real_exchange(self) -> None:
        prepared_template = _prepared()
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary) / "run"
            run_dir.mkdir()
            prepared = live.PreparedRun(
                Path(temporary),
                run_dir,
                prepared_template.bundle,
                prepared_template.prepared,
                prepared_template.private_target,
            )
            binding = live._candidate_observer_binding(prepared)
            live.cdc_acm_observer.persist_json(
                run_dir / "candidate-observer-baseline.json", {"baseline": True}
            )
            live.cdc_acm_observer.persist_json(
                run_dir / "candidate-observer-guard.json", {"guard": True}
            )

            host, peer = socket.socketpair()
            host.setblocking(False)
            peer.setblocking(True)
            errors: list[BaseException] = []

            def read_frame() -> live.p327_framed_observer.Frame:
                payload = bytearray()
                while len(payload) < live.p327_framed_observer.HEADER.size:
                    payload.extend(peer.recv(live.p327_framed_observer.HEADER.size - len(payload)))
                header = bytes(payload)
                length = live.p327_framed_observer.HEADER.unpack(header)[3]
                while len(payload) < live.p327_framed_observer.HEADER.size + length:
                    payload.extend(peer.recv(length + live.p327_framed_observer.HEADER.size - len(payload)))
                return live.p327_framed_observer.decode_frame(bytes(payload))

            def serve() -> None:
                try:
                    peer.sendall(live.p327_framed_runtime.DEVICE_BANNER)
                    opened = read_frame()
                    self.assertEqual(
                        opened.frame_type, live.p327_framed_runtime.FRAME_OPEN
                    )
                    peer.sendall(
                        live.p327_framed_observer.encode_frame(
                            live.p327_framed_runtime.FRAME_READY,
                            0,
                            live.p327_framed_runtime.P327_RUN_ID,
                        )
                    )
                    outputs = (
                        b"uid=0(root) gid=0(root)\n",
                        b"Linux p327\n",
                        (
                            "P327-NONCE "
                            + live.p327_framed_runtime.P327_RUN_ID_HEX
                            + "\n"
                        ).encode("ascii"),
                    )
                    for sequence, output in enumerate(outputs, 1):
                        request = read_frame()
                        self.assertEqual(
                            request.frame_type,
                            live.p327_framed_runtime.FRAME_EXEC,
                        )
                        peer.sendall(
                            live.p327_framed_observer.encode_frame(
                                live.p327_framed_runtime.FRAME_DATA,
                                sequence,
                                output,
                            )
                        )
                        peer.sendall(
                            live.p327_framed_observer.encode_frame(
                                live.p327_framed_runtime.FRAME_EXIT,
                                sequence,
                                live.p327_framed_observer.EXIT.pack(
                                    0, 0, 0, len(output), 1
                                ),
                            )
                        )
                    closed = read_frame()
                    self.assertEqual(
                        closed.frame_type, live.p327_framed_runtime.FRAME_CLOSE
                    )
                    peer.sendall(
                        live.p327_framed_observer.encode_frame(
                            live.p327_framed_runtime.FRAME_DONE,
                            4,
                            live.p327_framed_observer.DONE.pack(3),
                        )
                    )
                except BaseException as exc:  # pragma: no cover - surfaced below
                    errors.append(exc)

            thread = threading.Thread(target=serve)
            thread.start()
            try:
                guard = SimpleNamespace(
                    healthy=lambda **_kwargs: True,
                    matches_node=lambda _node: True,
                )
                p324_session = SimpleNamespace(
                    partner_before={"fixture": 1},
                    partner_continuous=True,
                    partner_poll_count=1,
                    class_tty=Path("/unused/class-tty"),
                    arm_receipt={"arm": True},
                )
                inherited = SimpleNamespace(
                    delegate=p324_session,
                    guard=guard,
                    _select=lambda: (
                        "accepted",
                        SimpleNamespace(identity_sha256="e" * 64),
                    ),
                )
                base = SimpleNamespace(
                    guard=guard,
                    binding=binding,
                    dev_root=Path("/unused/dev"),
                )
                session = live._P327ObserverSession(
                    inherited,
                    base,
                    live._p327_inherited_spec(
                        prepared.bundle.manifest["observation"][
                            "candidate_observer"
                        ]
                    ),
                    run_dir,
                    {"lane": True},
                    {"receipt": True},
                    Path("/unused/usb"),
                    Path("/unused/typec"),
                )
                candidate_digest = "e" * 64
                session._lane_supplement = lambda _accepted: {
                    "schema": live.p324_cdc_observer.SCHEMA,
                    "contract_id": live.p324_cdc_observer.CONTRACT_ID,
                    "target": live.p324_cdc_observer.TARGET,
                    "lane_binding": {"receipt": True},
                    "lane_binding_sha256": "f" * 64,
                    "arm": {"arm": True},
                    "source_topology": live.p324_typec_lane.SOURCE_TOPOLOGY,
                    "candidate_topology": live.p324_typec_lane.CANDIDATE_TOPOLOGY,
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
                            live.p324_typec_lane.SOURCE_TOPOLOGY: {
                                "topology_sha256": hashlib.sha256(
                                    b"2-1.3"
                                ).hexdigest(),
                                "endpoint_count": 0,
                                "exact_candidate_count": 0,
                                "candidate_like_count": 0,
                                "endpoint_identity_sha256": [],
                                "present": False,
                            },
                            live.p324_typec_lane.CANDIDATE_TOPOLOGY: {
                                "topology_sha256": hashlib.sha256(
                                    b"3-1.3"
                                ).hexdigest(),
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
                session._read_endpoint = lambda _endpoint, _deadline, writer: (
                    setattr(
                        session,
                        "exchange",
                        live.p327_framed_observer.exchange_commands(
                            host.fileno(),
                            live.p327_framed_observer.DEFAULT_COMMANDS,
                            timeout_sec=5,
                            writer=writer,
                        ),
                    )
                    or setattr(
                        session,
                        "proof",
                        live.p327_framed_observer.validate_default_proof(
                            session.exchange
                        ),
                    )
                    or "accepted"
                )
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
            self.assertFalse(errors)
            reopened = live._reopen_candidate_observation(prepared)
            self.assertTrue(reopened["valid_receipt"])
            self.assertTrue(reopened["accepted"])
            self.assertTrue(reopened["pid1_framed_exec_proof"])
            self.assertTrue(reopened["busybox_ash_command_proof"])
            self.assertTrue(reopened["framed_session_closed"])

    def test_projection_requires_all_framed_proof_flags(self) -> None:
        prepared = _prepared()
        candidate_topology = hashlib.sha256(b"3-1.3").hexdigest()
        durable = {
            "classification": "accepted",
            "accepted": True,
            "receipt_sha256": "d" * 64,
            "valid_receipt": True,
            "download_endpoint_absent": True,
            "endpoint_identity_sha256": "e" * 64,
            "topology_sha256": candidate_topology,
            "bounded": True,
            "source_topology_sha256": hashlib.sha256(b"2-1.3").hexdigest(),
            "candidate_topology_sha256": candidate_topology,
            "both_topologies_inventory_complete": True,
            "accepted_inventory_exact": True,
            "same_run_typec_partner_continuity": True,
            "accepted_for_p324": True,
            "pid1_framed_exec_proof": True,
            "busybox_ash_command_proof": True,
            "framed_session_closed": True,
            "interactive_pty_proof": False,
            "caller_selected_command": False,
        }
        state = {
            "candidate_classification": "odin_transfer_completed",
            "candidate_completed": True,
            "download_endpoint_absent": True,
            "rollback_classification": "odin_transfer_completed",
            "rollback_completed": True,
            "final_verified": True,
        }
        with (
            mock.patch.object(
                live, "_reopen_candidate_observation", return_value=durable
            ),
            mock.patch.object(
                live,
                "_reopen_candidate_guard_release",
                return_value={"status": "released", "released": True},
            ),
        ):
            self.assertTrue(
                live._candidate_arrival_proof_projection(prepared, state)[
                    "proof"
                ]
            )
            changed = dict(durable)
            changed["framed_session_closed"] = False
            with mock.patch.object(
                live, "_reopen_candidate_observation", return_value=changed
            ):
                self.assertFalse(
                    live._candidate_arrival_proof_projection(prepared, state)[
                        "proof"
                    ]
                )

    def test_final_mapping_is_p327_specific(self) -> None:
        prepared = _prepared()
        with mock.patch.object(
            live,
            "_state",
            return_value={
                live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY: {
                    "proof": True
                }
            },
        ):
            self.assertEqual(
                live._closed_terminal_classification(prepared),
                (
                    live.typed_evidence.P327_FRAMED_EXEC_VERDICT,
                    live.typed_evidence.P327_FRAMED_EXEC_OUTCOME,
                ),
            )
        with mock.patch.object(
            live,
            "_state",
            return_value={
                live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY: {
                    "proof": False
                }
            },
        ):
            self.assertEqual(
                live._closed_terminal_classification(prepared),
                (
                    "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK",
                    live.typed_evidence.P327_FRAMED_EXEC_NO_PROOF_OUTCOME,
                ),
            )


if __name__ == "__main__":
    unittest.main()
