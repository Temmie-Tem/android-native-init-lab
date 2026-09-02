from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"

import sys

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import device_action_f1_live_v2 as live  # noqa: E402


class P330LiveIntegrationTests(unittest.TestCase):
    def test_backend_selects_p330_before_p328_family_fallback(self) -> None:
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
            mock.patch.object(live, "_p329_bundle", return_value=False),
            mock.patch.object(live, "_p330_bundle", return_value=True),
            mock.patch.object(live, "_p328_bundle", return_value=True),
            mock.patch.object(
                live,
                "_p324_typec_lane_value",
                return_value=({"lane": True}, {"receipt": True}),
            ),
            mock.patch.object(
                live, "_p330_candidate_observer_session", return_value=sentinel
            ) as selected,
            mock.patch.object(live, "_p328_candidate_observer_session") as fallback,
        ):
            self.assertIs(backend.candidate_observer_session(prepared), sentinel)
        selected.assert_called_once()
        fallback.assert_not_called()

    def test_partial_timeout_receipt_keeps_actual_stage(self) -> None:
        failure = "TimeoutError"
        value = {
            "accepted": False,
            "diagnostics": [{"stage": 1, "code": 0}],
            "rng_eagain_retries": None,
            "partial_exchange": {
                "current_stage": "rng-diagnostic-read",
                "failure_stage": "rng-diagnostic-read",
                "failure_code": None,
                "exception_type": failure,
                "exception_sha256": hashlib.sha256(b"timeout").hexdigest(),
            },
        }
        projected = live._p330_validate_receipt_extras(value)
        self.assertEqual(projected["preauth_diagnostics"], value["diagnostics"])
        self.assertEqual(
            projected["partial_exchange"]["failure_stage"],
            "rng-diagnostic-read",
        )

    def test_p330_session_reads_through_bound_p330_artifact_helper(self) -> None:
        key = b"K" * 32
        key_identity = {
            "size": len(key),
            "sha256": hashlib.sha256(key).hexdigest(),
        }
        prepared = SimpleNamespace(
            prepared={"p328_auth_key_identity": key_identity},
            bundle=SimpleNamespace(
                manifest={
                    "observation": {
                        "acceptance": {
                            "userspace_overlay_contract_id": (
                                live.typed_evidence.P330_STOCK_OVERLAY_CONTRACT_ID
                            )
                        },
                        live.typed_evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: (
                            live.typed_evidence.CANDIDATE_AUTHENTICATED_DIAGNOSTIC_EXEC_ROLE
                        ),
                    }
                }
            ),
        )
        with (
            mock.patch.object(live, "_p330_bundle", return_value=True),
            mock.patch.object(live, "_p329_bundle", return_value=False),
            mock.patch.object(
                live.p330_artifact_identity, "read_auth_key", return_value=key
            ) as read,
            mock.patch.object(
                live.p330_artifact_identity,
                "validate_auth_key",
                return_value=key_identity,
            ),
            mock.patch.object(live.p328_artifact_identity, "read_auth_key") as stale,
        ):
            self.assertEqual(live._p328_read_auth_key(prepared), (key, key_identity["sha256"]))
        read.assert_called_once_with(live.p330_artifact_identity.DEFAULT_AUTH_KEY_PATH)
        stale.assert_not_called()


if __name__ == "__main__":
    unittest.main()
