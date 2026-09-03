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


class P334CommonIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.acceptance = evidence.p334_stock_adapter.acceptance_fixture()
        self.acceptance["auth_key"] = dict(
            evidence.P334_AUTH_EXEC_AUTH_KEY_IDENTITY
        )
        self.observer = evidence.p334_authenticated_logical_resident_observer_spec()

    def test_exact_role_sources_and_consumed_p333_baseline(self) -> None:
        self.assertEqual(
            evidence.validate_acceptance(self.acceptance), self.acceptance
        )
        self.assertEqual(
            evidence.validate_candidate_arrival_proof_role(
                evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
                self.observer,
                expected_run_id=evidence.P334_RUN_ID,
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
                "p334_first_read_rc_acm_observer",
                "p334_first_read_rc_runtime",
                "p334_artifact_identity",
                "p334_auth_key",
            }.issubset(receipts)
        )
        path = ROOT / (
            "workspace/private/runs/device-action-f1-live-v2/"
            "p333-ready1-prepared-20260904-1/rollback-observer-2.bin"
        )
        raw = path.read_bytes()
        baseline = evidence.classify_clean_baseline(raw, self.acceptance)
        self.assertEqual(
            baseline["classification"],
            "P334_CURRENT_RUN_ABSENT_P333_PREDECESSOR_EXACT",
        )
        self.assertTrue(baseline["baseline_clean"])
        changed = bytearray(raw)
        changed[0] ^= 1
        with self.assertRaisesRegex(
            evidence.EvidenceError,
            "P3.34 predecessor baseline raw identity differs",
        ):
            evidence.classify_clean_baseline(bytes(changed), self.acceptance)

    def test_entry_diagnostic_contract_is_exact_and_predecessors_fail(self) -> None:
        self.assertEqual(
            self.observer["diagnostic_stages"],
            [
                {"stage": 0, "name": "console-enter"},
                {"stage": 1, "name": "open-parsed"},
                {"stage": 2, "name": "rng"},
            ],
        )
        self.assertTrue(self.observer["entry_diagnostic_before_console"])
        self.assertTrue(self.observer["first_console_return_checkpoint_only"])
        self.assertEqual(self.observer["first_console_return_detail_prefix"], 0xB000)
        self.assertEqual(self.observer["first_console_return_detail_sentinel"], 0xBFFF)
        for run_id in (evidence.P333_RUN_ID, evidence.P332_RUN_ID, evidence.P331_RUN_ID):
            with self.subTest(run_id=run_id), self.assertRaises(
                evidence.EvidenceError
            ):
                evidence.validate_candidate_arrival_proof_role(
                    evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
                    self.observer,
                    expected_run_id=run_id,
                )
        for key, value in (
            ("entry_diagnostic_stage", 1),
            ("entry_diagnostic_before_console", False),
            ("diagnostic_stages", self.observer["diagnostic_stages"][1:]),
            ("first_console_return_detail_prefix", 0xA000),
            ("first_read_attribution_requires_stage0_without_stage1", False),
        ):
            changed = copy.deepcopy(self.observer)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(evidence.EvidenceError):
                evidence.validate_candidate_arrival_proof_role(
                    evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
                    changed,
                    expected_run_id=evidence.P334_RUN_ID,
                )

    def test_backend_selects_p334_before_authenticated_fallback(self) -> None:
        manifest = {
            "observation": {
                "acceptance": self.acceptance,
                "candidate_observer": self.observer,
                evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: (
                    evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
                ),
            }
        }
        prepared = SimpleNamespace(bundle=SimpleNamespace(manifest=manifest))
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
                live, "_p334_candidate_observer_session", return_value=sentinel
            ) as selected,
            mock.patch.object(live, "_p328_candidate_observer_session") as fallback,
        ):
            self.assertIs(backend.candidate_observer_session(prepared), sentinel)
        selected.assert_called_once()
        fallback.assert_not_called()

    def test_live_session_uses_p334_observer_on_one_tty(self) -> None:
        base = SimpleNamespace(dev_root=Path("/dev"), _raw_tty=lambda _fd: None)
        session = live._P334ObserverSession(
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
            sessions=[
                SimpleNamespace(result=SimpleNamespace()),
                SimpleNamespace(result=final_exchange),
            ],
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
            mock.patch.object(live.os, "open", return_value=23) as opened,
            mock.patch.object(live.os, "close") as closed,
            mock.patch.object(live.fcntl, "ioctl"),
            mock.patch.object(
                live.p334_first_read_observer,
                "exchange_resident",
                return_value=resident,
            ) as exchanged,
            mock.patch.object(
                live.p334_first_read_observer,
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
            23,
            b"K" * 32,
            timeout_sec=mock.ANY,
            writer=mock.ANY,
        )
        closed.assert_called_once_with(23)
        self.assertIs(session.exchange, final_exchange)


if __name__ == "__main__":
    unittest.main()
