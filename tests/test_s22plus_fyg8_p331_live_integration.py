from __future__ import annotations

import copy
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import tempfile
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import device_action_f1_live_v2 as live  # noqa: E402


class P331LiveIntegrationTests(unittest.TestCase):
    def test_backend_selects_p331_before_authenticated_family_fallback(self) -> None:
        backend = live.SamsungOdinBackend.__new__(live.SamsungOdinBackend)
        backend.usb_root = Path("/unused/usb")
        backend.typec_root = Path("/unused/typec")
        prepared = SimpleNamespace(
            bundle=SimpleNamespace(
                manifest={"observation": {"candidate_observer": {}}}
            )
        )
        sentinel = object()
        with (
            mock.patch.object(live, "_p331_bundle", return_value=True),
            mock.patch.object(
                live,
                "_p324_typec_lane_value",
                return_value=({"lane": True}, {"receipt": True}),
            ),
            mock.patch.object(
                live, "_p331_candidate_observer_session", return_value=sentinel
            ) as selected,
            mock.patch.object(live, "_p330_candidate_observer_session") as p330,
            mock.patch.object(live, "_p328_candidate_observer_session") as p328,
        ):
            self.assertIs(backend.candidate_observer_session(prepared), sentinel)
        selected.assert_called_once()
        p330.assert_not_called()
        p328.assert_not_called()

    def _proof(self) -> dict[str, object]:
        command = {
            "size": len(live.p331_resident_runtime.HEARTBEAT_COMMAND),
            "sha256": hashlib.sha256(
                live.p331_resident_runtime.HEARTBEAT_COMMAND
            ).hexdigest(),
        }
        output = {
            "size": len(live.p331_resident_runtime.HEARTBEAT_OUTPUT),
            "sha256": hashlib.sha256(
                live.p331_resident_runtime.HEARTBEAT_OUTPUT
            ).hexdigest(),
        }
        sessions = []
        for index, nonce in enumerate(("a" * 64, "b" * 64)):
            sessions.append(
                {
                    "session_index": index,
                    "reconnect_index": index,
                    "challenge_nonce_sha256": nonce,
                    "auth_key_sha256": live.typed_evidence.P331_AUTH_EXEC_AUTH_KEY_IDENTITY[
                        "sha256"
                    ],
                    "tx": {"size": 10, "sha256": "1" * 64},
                    "rx": {"size": 20, "sha256": "2" * 64},
                    "authenticated": True,
                    "clean_close": True,
                    "command": command,
                    "output": output,
                }
            )
        return {
            "schema": live.p331_resident_observer.SCHEMA,
            "contract_id": live.p331_resident_observer.CONTRACT_ID,
            "target": live.p331_resident_runtime.TARGET,
            "run_id_hex": live.p331_resident_runtime.P331_RUN_ID_HEX,
            "session_cap": 2,
            "reconnect_cap": 1,
            "session_count": 2,
            "successful_sessions": 2,
            "reconnect_count": 1,
            "sessions": sessions,
            "banner_attempts": 2,
            "banner_scope": "resident_loop_per_session",
            "fixed_heartbeat_status": True,
            "caller_selected_command": False,
            "interactive_pty": False,
            "arbitrary_file_transfer": False,
            "persistent_state": False,
            "resident_loop_proof": True,
            "partial_raw_retention": True,
        }

    def _receipt(self) -> dict[str, object]:
        proof = self._proof()
        complete = {
            "session_index": 0,
            "current_stage": "complete",
            "failure_stage": None,
            "failure_code": None,
            "exception_type": None,
            "exception_sha256": None,
        }
        return {
            "schema": live.P331_OBSERVER_RECEIPT_SCHEMA,
            "contract_id": live.p331_resident_observer.CONTRACT_ID,
            "target": live.p331_resident_runtime.TARGET,
            "binding": {},
            "spec_sha256": "0" * 64,
            "baseline_sha256": "1" * 64,
            "download_departure_sha256": "2" * 64,
            "download_endpoint_absent": True,
            "topology_sha256": "3" * 64,
            "endpoint_identity_sha256": "4" * 64,
            "guard_sha256": "5" * 64,
            "raw": {},
            "banner_hex": live.p331_resident_runtime.DEVICE_BANNER.hex(),
            "tx": {"size": 20, "sha256": "6" * 64},
            "session_tx_hex": ["00" * 10, "00" * 10],
            "rx": {"size": 40, "sha256": "7" * 64},
            "trailing_rx": {
                "size": 0,
                "sha256": hashlib.sha256(b"").hexdigest(),
            },
            "trailing_bytes_seen": 0,
            "banner_seen": True,
            "ready_seen": True,
            "done_seen": True,
            "proof": proof,
            "lane": {},
            "expected_size": len(live.p331_resident_runtime.DEVICE_BANNER) * 2,
            "exact": True,
            "extra_byte": False,
            "classification": "accepted",
            "accepted": True,
            "bounded": True,
            "elapsed_sec": 1.0,
            "diagnostics": [
                [{"stage": 1, "code": 0}, {"stage": 2, "code": 0}],
                [{"stage": 1, "code": 0}, {"stage": 2, "code": 0}],
            ],
            "rng_eagain_retries": [0, 0],
            "partial_sessions": [complete, {**complete, "session_index": 1}],
            "auth_algorithm": "hmac-sha256",
            "auth_tag_size": live.p331_resident_runtime.AUTH_TAG_SIZE,
            "auth_key_sha256": live.typed_evidence.P331_AUTH_EXEC_AUTH_KEY_IDENTITY[
                "sha256"
            ],
            "hmac_authenticated": True,
            "pid1_authenticated_framed_exec_proof": True,
            "busybox_ash_command_proof": True,
            "framed_session_closed": True,
            "resident_loop_proof": True,
            "fixed_heartbeat_status": True,
            "session_count": 2,
            "successful_sessions": 2,
            "session_cap": 2,
            "reconnect_count": 1,
            "reconnect_cap": 1,
            "commands_per_session": 1,
            "command_count": 2,
            "max_commands": live.p331_resident_runtime.MAX_COMMANDS,
            "interactive_pty_proof": False,
            "caller_selected_command": False,
            "arbitrary_file_transfer": False,
            "persistent_state": False,
        }

    def test_receipt_requires_two_distinct_authenticated_heartbeat_sessions(self) -> None:
        value = self._receipt()
        lane = {
            "both_topologies_inventory_complete": True,
            "accepted_inventory_exact": True,
            "same_run_typec_partner_continuity": True,
            "accepted_for_p324": True,
        }
        prepared = SimpleNamespace(run_dir=Path("/unused"))
        bound = dict(live.typed_evidence.P331_AUTH_EXEC_AUTH_KEY_IDENTITY)
        with (
            mock.patch.object(live, "_read_json", return_value=value),
            mock.patch.object(
                live,
                "_p328_validate_common_receipt",
                return_value=(lane, "3" * 64, "4" * 64),
            ),
            mock.patch.object(
                live, "_p328_bound_auth_key_identity", return_value=bound
            ),
            mock.patch.object(live, "_p331_validate_raw_session_bindings"),
            mock.patch.object(
                live, "_receipt", return_value={"sha256": "8" * 64}
            ),
        ):
            accepted = live._p331_validate_receipt(prepared, Path("/unused"), {})
            self.assertTrue(live._p331_proof_ok(accepted))
            duplicate = copy.deepcopy(value)
            duplicate["proof"]["sessions"][1]["challenge_nonce_sha256"] = "a" * 64
            with mock.patch.object(live, "_read_json", return_value=duplicate):
                with self.assertRaises(live.p331_resident_observer.AuthObserverError):
                    live._p331_validate_receipt(prepared, Path("/unused"), {})
            for label, mutate in (
                ("float-session-cap", lambda item: item.__setitem__("session_cap", 2.0)),
                ("bool-command-count", lambda item: item.__setitem__("command_count", True)),
                (
                    "bool-session-index",
                    lambda item: item["partial_sessions"][0].__setitem__(
                        "session_index", False
                    ),
                ),
            ):
                malformed = copy.deepcopy(value)
                mutate(malformed)
                with self.subTest(label=label), mock.patch.object(
                    live, "_read_json", return_value=malformed
                ):
                    with self.assertRaises(
                        live.p331_resident_observer.AuthObserverError
                    ):
                        live._p331_validate_receipt(
                            prepared, Path("/unused"), {}
                        )
            for label, mutate in (
                (
                    "string-trailing-count",
                    lambda item: item.__setitem__("trailing_bytes_seen", "0"),
                ),
                (
                    "missing-nested-rx",
                    lambda item: item["proof"]["sessions"][0].pop("rx"),
                ),
            ):
                malformed = copy.deepcopy(value)
                mutate(malformed)
                with self.subTest(label=label), mock.patch.object(
                    live, "_read_json", return_value=malformed
                ):
                    with self.assertRaises(
                        live.p331_resident_observer.AuthObserverError
                    ):
                        live._p331_validate_receipt(
                            prepared, Path("/unused"), {}
                        )

    def test_durable_session_hashes_and_nonce_reopen_from_raw_bytes(self) -> None:
        nonces = (b"A" * 32, b"B" * 32)
        rx_segments = tuple(
            live.p331_resident_runtime.DEVICE_BANNER
            + live.p331_resident_observer.encode_frame(
                live.p331_resident_runtime.FRAME_CHALLENGE, 0, nonce
            )
            for nonce in nonces
        )
        tx_segments = (b"first-host-session", b"second-host-session")
        proof = self._proof()
        for index, row in enumerate(proof["sessions"]):
            row["challenge_nonce_sha256"] = hashlib.sha256(nonces[index]).hexdigest()
            row["tx"] = live._p327_identity(tx_segments[index])
            row["rx"] = live._p327_identity(rx_segments[index])
        raw_payload = b"".join(rx_segments)
        with tempfile.TemporaryDirectory(prefix="p331-raw-binding-") as name:
            path = Path(name) / "candidate-observer.raw"
            path.write_bytes(raw_payload)
            value = {
                "raw": {
                    "path": str(path),
                    "size": len(raw_payload),
                    "sha256": hashlib.sha256(raw_payload).hexdigest(),
                },
                "session_tx_hex": [segment.hex() for segment in tx_segments],
                "tx": live._p327_identity(b"".join(tx_segments)),
            }
            prepared = SimpleNamespace(run_dir=Path(name))
            live._p331_validate_raw_session_bindings(prepared, value, proof)
            for label, mutate in (
                (
                    "nested-rx-hash",
                    lambda item: item["sessions"][0]["rx"].__setitem__(
                        "sha256", "0" * 64
                    ),
                ),
                (
                    "nonce-hash",
                    lambda item: item["sessions"][0].__setitem__(
                        "challenge_nonce_sha256", "c" * 64
                    ),
                ),
                (
                    "nested-tx-hash",
                    lambda item: item["sessions"][0]["tx"].__setitem__(
                        "sha256", "0" * 64
                    ),
                ),
            ):
                changed = copy.deepcopy(proof)
                mutate(changed)
                with self.subTest(label=label), self.assertRaises(
                    live.p331_resident_observer.AuthObserverError
                ):
                    live._p331_validate_raw_session_bindings(
                        prepared, value, changed
                    )

    def test_durable_stock_projection_reuses_final_evidence_without_duplicate(self) -> None:
        projection = {"proof_class": "NO_PROOF_OBSERVER"}
        state = {
            "p331_proof_class": "NO_PROOF_OBSERVER",
            "final_evidence": {"observer": {"p331_stock": projection}},
        }
        self.assertIs(live._p320_durable_projection(state), projection)
        state["p331_proof_class"] = "NONCAUSAL_SUCCESS_PATH"
        with self.assertRaises(live.F1LiveError):
            live._p320_durable_projection(state)

    def test_trailing_probe_runs_only_after_the_second_session(self) -> None:
        base = SimpleNamespace(dev_root=Path("/dev"), _raw_tty=lambda _fd: None)
        session = live._P331ObserverSession(
            delegate=SimpleNamespace(),
            base=base,
            spec={},
            run_dir=Path("/unused"),
            lane_binding={},
            lane_binding_receipt={},
            usb_root=Path("/unused/usb"),
            typec_root=Path("/unused/typec"),
            auth_key=b"K" * 32,
            auth_key_sha256="a" * 64,
        )
        endpoint = SimpleNamespace(tty_name="ttyACM0")

        def result(index: int) -> SimpleNamespace:
            return SimpleNamespace(
                audit=SimpleNamespace(
                    tx=bytearray(b"tx"),
                    rx=bytearray(b"rx"),
                    nonce=bytes([index + 1]) * 32,
                    authenticated=True,
                    done_seen=True,
                )
            )

        proof = {
            "resident_loop_proof": True,
            "fixed_heartbeat_status": True,
            "session_count": 2,
            "reconnect_count": 1,
        }
        with (
            mock.patch.object(session, "_settle_guard_properties", return_value=None),
            mock.patch.object(session, "_endpoint_exact", return_value=True),
            mock.patch.object(live.os, "open", side_effect=(10, 11)),
            mock.patch.object(live.os, "close"),
            mock.patch.object(live.fcntl, "ioctl"),
            mock.patch.object(
                live.p331_resident_observer,
                "exchange_session",
                side_effect=(result(0), result(1)),
            ),
            mock.patch.object(
                live.p331_resident_observer,
                "validate_resident_proof",
                return_value=proof,
            ),
            mock.patch.object(
                live, "_p327_trailing_probe", return_value=b""
            ) as trailing,
        ):
            self.assertEqual(
                session._read_endpoint(endpoint, 10**12, SimpleNamespace()),
                "accepted",
            )
        trailing.assert_called_once_with(11, mock.ANY)


if __name__ == "__main__":
    unittest.main()
