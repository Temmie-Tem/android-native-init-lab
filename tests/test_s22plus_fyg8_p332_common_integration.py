from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_live_v2 as live  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402


class P332CommonIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.acceptance = evidence.p332_stock_adapter.acceptance_fixture()
        self.acceptance["auth_key"] = dict(
            evidence.P332_AUTH_EXEC_AUTH_KEY_IDENTITY
        )
        self.observer = evidence.p332_authenticated_logical_resident_observer_spec()

    def test_exact_role_sources_and_consumed_p331_baseline(self) -> None:
        self.assertEqual(
            evidence.validate_acceptance(self.acceptance), self.acceptance
        )
        self.assertEqual(
            evidence.validate_candidate_arrival_proof_role(
                evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
                self.observer,
                expected_run_id=evidence.P332_RUN_ID,
            ),
            evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
        )
        core.verify_candidate_observer_binding(self.acceptance, self.observer)
        receipts = core.execution_critical_source_receipts(
            self.acceptance,
            candidate_arrival_proof_role=(
                evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
            ),
            bind_private_inputs=False,
        )
        self.assertTrue(
            {
                "p332_logical_resident_acm_observer",
                "p332_logical_resident_exec_runtime",
                "p332_artifact_identity",
                "p332_auth_key",
            }.issubset(receipts)
        )
        path = ROOT / (
            "workspace/private/runs/device-action-f1-live-v2/"
            "p331-ready3-prepared-20260903-1/rollback-observer-2.bin"
        )
        raw = path.read_bytes()
        baseline = evidence.classify_clean_baseline(raw, self.acceptance)
        self.assertEqual(
            baseline["classification"],
            "P332_CURRENT_RUN_ABSENT_P331_PREDECESSOR_EXACT",
        )
        self.assertTrue(baseline["baseline_clean"])
        changed = bytearray(raw)
        changed[0] ^= 1
        with self.assertRaisesRegex(
            evidence.EvidenceError,
            "P3.32 predecessor baseline raw identity differs",
        ):
            evidence.classify_clean_baseline(bytes(changed), self.acceptance)

    def test_predecessor_identity_and_same_fd_contract_fail_closed(self) -> None:
        for predecessor in (evidence.P331_RUN_ID, evidence.P330_RUN_ID):
            with self.assertRaises(evidence.EvidenceError):
                evidence.validate_candidate_arrival_proof_role(
                    evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
                    self.observer,
                    expected_run_id=predecessor,
                )
        for key, value in (
            ("same_tty_fd_required", False),
            ("host_tty_close_reopen", True),
            ("fixed_p330_commands", False),
        ):
            changed = copy.deepcopy(self.observer)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(evidence.EvidenceError):
                evidence.validate_candidate_arrival_proof_role(
                    evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
                    changed,
                    expected_run_id=evidence.P332_RUN_ID,
                )

    def test_backend_selects_p332_before_authenticated_family_fallback(self) -> None:
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
            mock.patch.object(live, "_p331_bundle", return_value=False),
            mock.patch.object(live, "_p329_bundle", return_value=False),
            mock.patch.object(live, "_p330_bundle", return_value=False),
            mock.patch.object(live, "_p332_bundle", return_value=True),
            mock.patch.object(
                live,
                "_p324_typec_lane_value",
                return_value=({"lane": True}, {"receipt": True}),
            ),
            mock.patch.object(
                live, "_p332_candidate_observer_session", return_value=sentinel
            ) as selected,
            mock.patch.object(live, "_p328_candidate_observer_session") as fallback,
        ):
            self.assertIs(backend.candidate_observer_session(prepared), sentinel)
        selected.assert_called_once()
        fallback.assert_not_called()

    def test_live_session_opens_and_closes_the_tty_once(self) -> None:
        base = SimpleNamespace(dev_root=Path("/dev"), _raw_tty=lambda _fd: None)
        session = live._P332ObserverSession(
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
        final_exchange = SimpleNamespace()
        resident = SimpleNamespace(
            sessions=[SimpleNamespace(result=SimpleNamespace()), SimpleNamespace(result=final_exchange)],
            complete=True,
            successful_sessions=2,
        )
        proof = {
            "logical_resident_proof": True,
            "same_tty_fd": True,
            "physical_reopen_count": 0,
            "session_count": 2,
        }
        with (
            mock.patch.object(session, "_settle_guard_properties", return_value=None),
            mock.patch.object(session, "_endpoint_exact", return_value=True),
            mock.patch.object(live.os, "open", return_value=19) as opened,
            mock.patch.object(live.os, "close") as closed,
            mock.patch.object(live.fcntl, "ioctl"),
            mock.patch.object(
                live.p332_logical_resident_observer,
                "exchange_resident",
                return_value=resident,
            ) as exchanged,
            mock.patch.object(
                live.p332_logical_resident_observer,
                "validate_resident_proof",
                return_value=proof,
            ),
            mock.patch.object(live, "_p327_trailing_probe", return_value=b""),
        ):
            self.assertEqual(
                session._read_endpoint(endpoint, 10**12, SimpleNamespace()),
                "accepted",
            )
        opened.assert_called_once()
        exchanged.assert_called_once_with(
            19,
            b"K" * 32,
            timeout_sec=mock.ANY,
            writer=mock.ANY,
        )
        closed.assert_called_once_with(19)
        self.assertIs(session.exchange, final_exchange)

    def test_physical_reopen_count_requires_integer_zero(self) -> None:
        value = {
            "hmac_authenticated": True,
            "pid1_authenticated_framed_exec_proof": True,
            "busybox_ash_command_proof": True,
            "framed_session_closed": True,
            "logical_resident_proof": True,
            "same_tty_fd": True,
            "physical_reopen_count": False,
            "fixed_p330_commands": True,
            "interactive_pty_proof": False,
            "caller_selected_command": False,
            "arbitrary_file_transfer": False,
            "persistent_state": False,
            "session_count": 2,
            "successful_sessions": 2,
            "session_cap": 2,
            "reconnect_count": 0,
            "reconnect_cap": 0,
            "commands_per_session": 3,
            "command_count": 6,
            "max_commands": 16,
        }
        self.assertFalse(live._p332_proof_ok(value))
        value["physical_reopen_count"] = 0
        self.assertTrue(live._p332_proof_ok(value))


if __name__ == "__main__":
    unittest.main()
