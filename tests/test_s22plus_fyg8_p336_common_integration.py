from __future__ import annotations

import hashlib
import json
from pathlib import Path
import socket
import threading
from types import SimpleNamespace
from unittest import mock
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_live_v2 as live  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402


def _identity(seed: str) -> dict[str, object]:
    return {"size": 1, "sha256": seed * 64}


def _proof() -> dict[str, object]:
    commands = [
        {
            "sequence": sequence,
            "command_sha256": hashlib.sha256(command).hexdigest(),
            "output": _identity("a"),
            "exit_code": 0,
            "term_signal": 0,
            "duration_ms": 1,
        }
        for sequence, command in zip(
            (3, 4, 5), evidence.p336_long_idle_runtime.DEFAULT_COMMANDS
        )
    ]
    sessions = [
        {
            "session_index": index,
            "physical_reopen_index": 0 if index < 2 else 1,
            "challenge_nonce_sha256": f"{index + 1:064x}",
            "boot_id_sha256": "44" * 32,
            "auth_key_sha256": evidence.P336_AUTH_EXEC_AUTH_KEY_IDENTITY[
                "sha256"
            ],
            "commands": commands,
            "tx": _identity("b"),
            "rx": _identity("c"),
            "raw_tx": _identity("d"),
            "raw_rx": _identity("e"),
            "diagnostics": [],
            "pid1_authenticated_framed_exec_proof": True,
            "busybox_ash_command_proof": True,
            "interactive_pty_proof": False,
            "caller_selected_command": False,
        }
        for index in range(3)
    ]
    return {
        "schema": evidence.p336_long_idle_acm_observer.SCHEMA,
        "contract_id": evidence.P336_AUTH_EXEC_OBSERVER_CONTRACT_ID,
        "target": evidence.p336_long_idle_runtime.TARGET,
        "run_id_hex": evidence.P336_RUN_ID,
        "session_cap": 3,
        "reconnect_cap": 1,
        "session_count": 3,
        "successful_sessions": 3,
        "reconnect_count": 1,
        "physical_reopen_count": 1,
        "fixed_command_count": 3,
        "hmac_authenticated": True,
        "pid1_authenticated_framed_exec_proof": True,
        "busybox_ash_command_proof": True,
        "diagnostic_order_proof": True,
        "per_boot_identity_proof": True,
        "same_initial_fd": True,
        "same_tty_fd": True,
        "same_boot_id": True,
        "descriptor_reopened": True,
        "retained_listener_proof": True,
        "partial_raw_retention": True,
        "caller_selected_command": False,
        "interactive_pty": False,
        "arbitrary_file_transfer": False,
        "persistent_state": False,
        "listener_replays_commands": False,
        "fixed_commands": [
            {"size": len(command), "sha256": hashlib.sha256(command).hexdigest()}
            for command in evidence.p336_long_idle_runtime.DEFAULT_COMMANDS
        ],
        "sessions": sessions,
    }


class P336CommonIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.acceptance = evidence.p336_stock_adapter.acceptance_fixture()
        self.acceptance["auth_key"] = dict(
            evidence.P336_AUTH_EXEC_AUTH_KEY_IDENTITY
        )
        self.observer = evidence.p336_authenticated_long_idle_observer_spec()

    def test_p336_acceptance_uses_logical_role_and_action_closure(self) -> None:
        self.assertEqual(
            evidence.validate_acceptance(self.acceptance), self.acceptance
        )
        role = evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
        self.assertEqual(
            evidence.validate_candidate_arrival_proof_role(
                role, self.observer, expected_run_id=evidence.P336_RUN_ID
            ),
            role,
        )
        core.verify_candidate_observer_binding(self.acceptance, self.observer)
        receipts = core.execution_critical_source_receipts(
            self.acceptance,
            candidate_arrival_proof_role=role,
            bind_private_inputs=False,
        )
        self.assertTrue(
            {
                "p336_long_idle_acm_observer",
                "p336_long_idle_runtime",
                "p336_artifact_identity",
                "p336_long_idle_action",
                "p336_long_idle_action_activation",
                "p336_auth_key",
            }.issubset(receipts)
        )

    def test_p336_initial_three_session_proof_is_strict_and_bound(self) -> None:
        proof = _proof()
        self.assertEqual(evidence.validate_p336_long_idle_proof(proof), proof)
        value = {
            "proof": proof,
            "hmac_authenticated": True,
            "pid1_authenticated_framed_exec_proof": True,
            "busybox_ash_command_proof": True,
            "framed_session_closed": True,
            "logical_resident_proof": True,
            "same_tty_fd": True,
            "fixed_p330_commands": True,
            "physical_reopen_count": 1,
            "interactive_pty_proof": False,
            "caller_selected_command": False,
            "arbitrary_file_transfer": False,
            "persistent_state": False,
            "session_count": 3,
            "successful_sessions": 3,
            "session_cap": 3,
            "reconnect_count": 1,
            "reconnect_cap": 1,
            "commands_per_session": 3,
            "command_count": 9,
            "max_commands": evidence.p336_long_idle_runtime.MAX_COMMANDS,
        }
        self.assertTrue(live._p336_proof_ok(value))
        replay = dict(proof)
        replay["sessions"] = [dict(item) for item in proof["sessions"]]
        replay["sessions"][1]["challenge_nonce_sha256"] = replay["sessions"][0][
            "challenge_nonce_sha256"
        ]
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_p336_long_idle_proof(replay)

    def test_p336_socket_receipt_uses_p336_codec_and_reopens_once(self) -> None:
        observer = live._P336_INITIAL_OBSERVER
        runtime = live.p336_long_idle_runtime
        key = bytes(range(runtime.AUTH_KEY_SIZE))
        boot_id = b"B" * runtime.P335_BOOT_ID_SIZE
        initial_host, initial_peer = socket.socketpair()
        reopened_host, reopened_peer = socket.socketpair()
        errors: list[BaseException] = []

        def receive_exact(peer: socket.socket, size: int) -> bytes:
            value = bytearray()
            while len(value) < size:
                chunk = peer.recv(size - len(value))
                if not chunk:
                    raise RuntimeError("fixture peer EOF")
                value.extend(chunk)
            return bytes(value)

        def receive_frame(peer: socket.socket):
            header = receive_exact(peer, observer.HEADER.size)
            length = observer.HEADER.unpack(header)[3]
            return observer.decode_frame(
                header + receive_exact(peer, length)
            )

        def send_frame(peer: socket.socket, frame_type: int, sequence: int, payload: bytes) -> None:
            peer.sendall(observer.encode_frame(frame_type, sequence, payload))

        def serve_session(peer: socket.socket, index: int) -> None:
            peer.sendall(runtime.DEVICE_BANNER)
            opened = receive_frame(peer)
            self.assertEqual(
                opened,
                observer.Frame(runtime.FRAME_OPEN, 0, runtime.P336_RUN_ID),
            )
            for stage in (
                runtime.DIAGNOSTIC_STAGE_CONSOLE_ENTER,
                runtime.DIAGNOSTIC_STAGE_OPEN_PARSED,
                runtime.DIAGNOSTIC_STAGE_RNG,
            ):
                send_frame(
                    peer,
                    runtime.DIAGNOSTIC_FRAME_TYPE,
                    0,
                    observer.DIAGNOSTIC.pack(stage, 0),
                )
            nonce = bytes([0x41 + index]) * runtime.NONCE_SIZE
            send_frame(peer, runtime.FRAME_CHALLENGE, 0, nonce)
            auth = receive_frame(peer)
            self.assertEqual(
                auth.payload,
                observer.compute_open_tag(key, runtime.P336_RUN_ID, nonce),
            )
            send_frame(
                peer,
                runtime.FRAME_READY,
                1,
                observer.compute_ready_tag(key, runtime.P336_RUN_ID, nonce),
            )
            send_frame(
                peer,
                runtime.FRAME_BOOT_ID,
                runtime.P335_BOOT_ID_SEQUENCE,
                boot_id
                + observer.compute_boot_id_tag(
                    key, runtime.P336_RUN_ID, nonce, boot_id
                ),
            )
            outputs = (
                b"uid=0(root) gid=0(root)\n",
                b"Linux p336 5.10 aarch64 GNU/Linux\n",
                f"P328-NONCE {runtime.P336_RUN_ID_HEX}\n".encode("ascii"),
            )
            for sequence, (command, output) in enumerate(
                zip(runtime.DEFAULT_COMMANDS, outputs), start=3
            ):
                request = receive_frame(peer)
                self.assertEqual(request.frame_type, runtime.FRAME_EXEC)
                self.assertEqual(request.sequence, sequence)
                self.assertEqual(
                    request.payload,
                    observer.compute_exec_tag(
                        key, runtime.P336_RUN_ID, nonce, sequence, command
                    )
                    + command,
                )
                send_frame(peer, runtime.FRAME_DATA, sequence, output)
                send_frame(
                    peer,
                    runtime.FRAME_EXIT,
                    sequence,
                    observer.EXIT.pack(0, 0, 0, len(output), 1),
                )
            close_sequence = runtime.P335_BOOT_ID_SEQUENCE + 3 + 1
            close = receive_frame(peer)
            self.assertEqual(close.frame_type, runtime.FRAME_CLOSE)
            self.assertEqual(close.sequence, close_sequence)
            send_frame(
                peer,
                runtime.FRAME_DONE,
                close_sequence,
                observer.DONE.pack(3),
            )

        def serve() -> None:
            try:
                for index in range(2):
                    serve_session(initial_peer, index)
                serve_session(reopened_peer, 2)
            except BaseException as exc:  # surfaced after the bounded exchange
                errors.append(exc)
            finally:
                initial_peer.close()
                reopened_peer.close()

        thread = threading.Thread(target=serve)
        thread.start()
        try:
            result = observer.exchange_retained(
                initial_host,
                key,
                reopen=lambda: reopened_host,
                timeout_sec=3,
            )
        finally:
            initial_host.close()
            reopened_host.close()
            thread.join(timeout=5)
        self.assertFalse(errors, errors)
        self.assertTrue(result.complete)
        self.assertEqual(result.session_count, 3)
        self.assertEqual(result.sessions[0].descriptor, result.sessions[1].descriptor)
        self.assertEqual(result.sessions[0].physical_reopen_index, 0)
        self.assertEqual(result.sessions[1].physical_reopen_index, 0)
        self.assertEqual(result.sessions[2].physical_reopen_index, 1)
        proof = live._p336_repin_proof(observer.validate_retained_proof(result))
        self.assertEqual(proof["schema"], evidence.p336_long_idle_acm_observer.SCHEMA)
        self.assertEqual(proof["run_id_hex"], runtime.P336_RUN_ID_HEX)
        self.assertEqual(proof["target"], runtime.TARGET)
        self.assertEqual(evidence.validate_p336_long_idle_proof(proof), proof)
        stale = dict(proof)
        stale["run_id_hex"] = evidence.P335_RUN_ID
        with self.assertRaises(live.F1LiveError):
            live._p336_repin_proof(stale)
        for session in proof["sessions"]:
            self.assertGreater(session["tx"]["size"], 0)
            self.assertGreater(session["rx"]["size"], 0)
            self.assertEqual(session["tx"], session["raw_tx"])
            self.assertEqual(session["rx"], session["raw_rx"])

    def test_p336_empty_stock_projection_is_acm_primary(self) -> None:
        classified = evidence.classify_e1_latest_stage(
            bytes(evidence.p336_stock_adapter.RAW_SIZE), self.acceptance
        )
        projection = live._p320_terminal_projection(classified)
        self.assertEqual(projection["proof_class"], "NO_PROOF_OBSERVER")
        self.assertEqual(projection["stock"], [])
        self.assertTrue(projection["acm_primary"])
        self.assertTrue(projection["acm_required_for_acceptance"])
        self.assertFalse(projection["acm_supplemental"])

    def test_p336_e2_payload_dispatch_precedes_p335(self) -> None:
        closure = {
            "source_contract_id": evidence.p336_stock_adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": evidence.P336_STOCK_OVERLAY_CONTRACT_ID,
        }
        expected = {"p336": True}
        with (
            mock.patch.object(
                evidence, "_validate_p336_e2_ap_payload", return_value=expected
            ) as p336,
            mock.patch.object(evidence, "_validate_p335_e2_ap_payload") as p335,
        ):
            self.assertEqual(evidence.validate_e2_ap_payload(b"fixture", closure), expected)
        p336.assert_called_once_with(b"fixture", closure)
        p335.assert_not_called()

    def test_p336_backend_dispatch_precedes_p335_and_generic_fallback(self) -> None:
        role = evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
        manifest = {
            "observation": {
                "acceptance": self.acceptance,
                "candidate_observer": self.observer,
                evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: role,
            }
        }
        prepared = SimpleNamespace(bundle=SimpleNamespace(manifest=manifest))
        backend = live.SamsungOdinBackend.__new__(live.SamsungOdinBackend)
        backend.usb_root = Path("/unused/usb")
        backend.typec_root = Path("/unused/typec")
        selected = object()
        with (
            mock.patch.object(
                live, "_p324_typec_lane_value", return_value=({}, {})
            ),
            mock.patch.object(
                live, "_p336_candidate_observer_session", return_value=selected
            ) as p336,
            mock.patch.object(live, "_p335_candidate_observer_session") as p335,
            mock.patch.object(live, "_p328_candidate_observer_session") as fallback,
        ):
            self.assertIs(backend.candidate_observer_session(prepared), selected)
        p336.assert_called_once()
        p335.assert_not_called()
        fallback.assert_not_called()

    def test_p336_parser_failure_keeps_distinct_raw_first_namespace(self) -> None:
        payload = b"p336-parser-failure"
        error = live.F1LiveError("fixture parser rejection")
        diagnostic = live._p336_stock_error(payload, error)
        classification = live._p336_parser_failure_classification(payload, error)
        self.assertEqual(diagnostic["schema"], "device_action_f1_p336_stock_error_v1")
        self.assertEqual(diagnostic["payload_sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(classification["p336_stock_error"], diagnostic)
        self.assertFalse(classification["accepted"])

    def test_p336_common_binding_matches_action_resident_proxy(self) -> None:
        import s22plus_fyg8_p336_long_idle_action as action  # noqa: E402

        proof = _proof()
        prepared = SimpleNamespace(
            prepared={
                "p336_auth_key_identity": dict(
                    evidence.P336_AUTH_EXEC_AUTH_KEY_IDENTITY
                )
            },
            private_target={"topology": "usb:3-1", "serial": "fixture"},
            bundle=SimpleNamespace(
                receipt={
                    "observation_contract": {
                        "verification": {
                            "ap_payload_closure": {
                                "boot_image": {"sha256": "55" * 32}
                            }
                        }
                    }
                },
                manifest={
                    "candidate_ap": {"sha256": "66" * 32},
                    "rollback_ap": {"sha256": "77" * 32},
                },
            ),
        )
        observation = {
            "candidate_topology_sha256": "88" * 32,
            "endpoint_identity_sha256": "99" * 32,
            "p336_authenticated_attended_resident": proof,
        }
        common = live._p336_resident_binding(prepared, observation)
        action_binding = action._p336_resident_binding(prepared, observation)
        self.assertEqual(common, action_binding)
        self.assertEqual(common["target"], action.resident.TARGET)
        self.assertEqual(common["candidate"]["run_id"], evidence.P336_RUN_ID)
        self.assertEqual(common["recovery"]["owner"], "s22plus-fyg8-p336-long-idle")

    def test_p336_prepared_auth_key_uses_p336_name_end_to_end(self) -> None:
        role = evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
        bundle = SimpleNamespace(
            manifest={
                "observation": {
                    "acceptance": self.acceptance,
                    "candidate_observer": self.observer,
                    evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: role,
                }
            }
        )
        prepared: dict[str, object] = {"approval_binding": {}}
        live._bind_prepared_auth_key_identity(bundle, prepared)
        live._bind_prepared_auth_key_identity(
            bundle, prepared["approval_binding"]
        )
        self.assertEqual(
            prepared["p336_auth_key_identity"],
            evidence.P336_AUTH_EXEC_AUTH_KEY_IDENTITY,
        )
        self.assertNotIn("p328_auth_key_identity", prepared)
        live._validate_prepared_auth_key_identity(bundle, prepared)
        prepared["p336_auth_key_identity"] = dict(
            prepared["p336_auth_key_identity"]
        )
        prepared["p336_auth_key_identity"]["sha256"] = "00" * 32
        with self.assertRaisesRegex(
            live.F1LiveError, "prepared auth-key identity differs"
        ):
            live._validate_prepared_auth_key_identity(bundle, prepared)

    def test_closed_p336_result_uses_p336_terminal_namespace(self) -> None:
        role = evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
        bundle = SimpleNamespace(
            sha256="21" * 32,
            manifest={
                "manifest_id": "p336-terminal-fixture",
                "observation": {
                    "acceptance": self.acceptance,
                    "candidate_observer": self.observer,
                    evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: role,
                },
            },
        )
        prepared = SimpleNamespace(
            run_dir=Path("/unused/p336-terminal"),
            binding_sha256="22" * 32,
            bundle=bundle,
        )
        state = {
            "candidate_classification": "odin_transfer_completed",
            "candidate_completed": True,
            "rollback_classification": "odin_transfer_completed",
            "rollback_completed": True,
            "final_verified": True,
            evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY: {"proof": True},
        }
        timeline = {"events": [{"name": name} for name in core.TIMELINE]}
        journal_receipt = {"sha256": "23" * 32}
        journal = SimpleNamespace(
            records=lambda: [], receipt=lambda: journal_receipt, state=lambda: "CLOSED"
        )
        result = {
            "schema": live.LIVE_RESULT_SCHEMA,
            "adapter_version": live.ADAPTER_VERSION,
            "manifest_id": bundle.manifest["manifest_id"],
            "bundle_sha256": bundle.sha256,
            "approval_binding_sha256": prepared.binding_sha256,
            "journal": journal_receipt,
            "current_state": "CLOSED",
            "timeline": timeline,
            "live_state": state,
            "verdict": live.P336_SUCCESS_VERDICT,
            "outcome_class": live.P336_SUCCESS_OUTCOME,
            "recovery_required": False,
        }
        with (
            mock.patch.object(live.core.Journal, "reopen", return_value=journal),
            mock.patch.object(live, "_state", return_value=state),
            mock.patch.object(live.core, "timeline", return_value=timeline),
            mock.patch.object(live, "_validate_p300_usb_trace_state"),
            mock.patch.object(live, "_validate_candidate_arrival_proof_state"),
            mock.patch.object(live, "_validate_candidate_observer_state"),
            mock.patch.object(live, "_validate_final_observer"),
            mock.patch.object(
                live,
                "_validate_transfer_evidence",
                return_value={"classification": "odin_transfer_completed"},
            ),
            mock.patch.object(live, "_request_cut_transition", return_value=None),
        ):
            self.assertEqual(live.validate_live_result(result, prepared), result)


if __name__ == "__main__":
    unittest.main()
