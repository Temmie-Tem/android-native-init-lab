from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "workspace/public/src/scripts/analysis"
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
for directory in (ANALYSIS, REVALIDATION):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import device_action_f1_evidence_v2 as evidence  # noqa: E402
import device_action_f1_live_v2 as live  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402
import prepare_s22plus_fyg8_p339_process_v2 as prepare  # noqa: E402
import s22plus_fyg8_p336_long_idle_acm_observer as p336_observer  # noqa: E402
import s22plus_fyg8_p338_open_read_branch_acm_observer as p338_observer  # noqa: E402
import s22plus_fyg8_p338_open_read_branch_runtime as p338_runtime  # noqa: E402
import s22plus_fyg8_p339_artifact_identity as artifact  # noqa: E402
import s22plus_fyg8_p339_open_read_branch_acm_observer as observer  # noqa: E402
import s22plus_fyg8_p339_open_read_branch_runtime as runtime  # noqa: E402
import s22plus_fyg8_p339_process_v2_candidate_static as static  # noqa: E402
import s22plus_fyg8_p339_stock_candidate_build as builder  # noqa: E402
import s22plus_fyg8_p339_stock_process_v2_adapter as adapter  # noqa: E402


def _proof_fixture() -> dict[str, object]:
    commands = [
        {
            "size": len(command),
            "sha256": hashlib.sha256(command).hexdigest(),
        }
        for command in runtime.DEFAULT_COMMANDS
    ]
    sessions = []
    for index in range(observer.MAX_SESSIONS):
        sessions.append(
            {
                "session_index": index,
                "physical_reopen_index": 0 if index < 2 else 1,
                "challenge_nonce_sha256": hashlib.sha256(
                    f"nonce-{index}".encode("ascii")
                ).hexdigest(),
                "boot_id_sha256": hashlib.sha256(b"boot").hexdigest(),
                "auth_key_sha256": hashlib.sha256(b"auth-key").hexdigest(),
                "commands": [
                    {
                        "sequence": sequence,
                        "command_sha256": hashlib.sha256(command).hexdigest(),
                    }
                    for sequence, command in zip((3, 4, 5), runtime.DEFAULT_COMMANDS)
                ],
                "tx": {},
                "raw_tx": {},
                "rx": {},
                "raw_rx": {},
                "diagnostics": [],
                "pid1_authenticated_framed_exec_proof": True,
                "busybox_ash_command_proof": True,
                "interactive_pty_proof": False,
                "caller_selected_command": False,
            }
        )
    return {
        "schema": observer.SCHEMA,
        "contract_id": observer.CONTRACT_ID,
        "target": runtime.TARGET,
        "run_id_hex": runtime.P339_RUN_ID_HEX,
        "session_cap": observer.MAX_SESSIONS,
        "reconnect_cap": observer.MAX_RECONNECTS,
        "session_count": observer.MAX_SESSIONS,
        "successful_sessions": observer.MAX_SESSIONS,
        "reconnect_count": observer.MAX_RECONNECTS,
        "physical_reopen_count": observer.PHYSICAL_REOPEN_COUNT,
        "fixed_command_count": len(runtime.DEFAULT_COMMANDS),
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
        "fixed_commands": commands,
        "sessions": sessions,
    }


class P339ProcessV2Tests(unittest.TestCase):
    def test_ready_bundle_reaches_the_live_arrival_and_lane_dispatch(self) -> None:
        bundle = core.verify_bundle(ROOT, prepare.DEFAULT_MANIFEST)
        self.assertTrue(live._p324_lane_bundle(bundle))  # noqa: SLF001
        self.assertTrue(live._acm_primary_bundle(bundle))  # noqa: SLF001
        self.assertEqual(
            live._candidate_arrival_proof_role(bundle),  # noqa: SLF001
            evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
        )

    def test_exact_consumed_p338_baseline_is_the_only_d0_fast_path(self) -> None:
        acceptance = adapter.acceptance_fixture()
        acceptance["auth_key"] = dict(
            evidence.P339_AUTH_EXEC_AUTH_KEY_IDENTITY
        )
        raw = (
            ROOT
            / "workspace/private/runs/device-action-f1-live-v2/"
            "p338-ready3-prepared-20260905-4/rollback-observer-2.bin"
        ).read_bytes()
        baseline = evidence.classify_clean_baseline(raw, acceptance)
        self.assertEqual(
            baseline["classification"],
            "P339_CURRENT_RUN_ABSENT_P338_PREDECESSOR_EXACT",
        )
        self.assertTrue(baseline["baseline_clean"])
        changed = bytearray(raw)
        changed[0] ^= 1
        with self.assertRaisesRegex(
            evidence.EvidenceError,
            "P3.39 predecessor baseline raw identity differs",
        ):
            evidence.classify_clean_baseline(bytes(changed), acceptance)

    def test_first_open_failure_fixture_covers_all_five_branches(self) -> None:
        encoder = p336_observer.encode_frame
        for ordinal, classification in runtime.OPEN_READ_BRANCHES.items():
            with self.subTest(ordinal=ordinal):
                frame = encoder(
                    runtime.DIAGNOSTIC_FRAME_TYPE,
                    0,
                    observer.DIAGNOSTIC.pack(
                        runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT, ordinal
                    ),
                )
                value = observer.parse_retained_open_read_branch(
                    runtime.DEVICE_BANNER + frame
                )
                self.assertEqual(value["branch_ordinal"], ordinal)
                self.assertEqual(value["classification"], classification)
                self.assertFalse(value["causal_result_allowed"])
                self.assertFalse(value["candidate_success"])

    def test_p338_failure_fixture_is_not_relabelled_as_p339(self) -> None:
        frame = p336_observer.encode_frame(
            p338_runtime.DIAGNOSTIC_FRAME_TYPE,
            0,
            p338_observer.DIAGNOSTIC.pack(
                p338_runtime.DIAGNOSTIC_STAGE_OPEN_READ_RESULT, -71
            ),
        )
        with self.assertRaises(observer.P339ObserverBindingError):
            observer.parse_retained_open_read_branch(
                runtime.DEVICE_BANNER + frame
            )

    def test_p338_proof_is_rejected_before_compatibility_projection(self) -> None:
        stale = _proof_fixture()
        stale["schema"] = p338_observer.SCHEMA
        stale["contract_id"] = p338_observer.CONTRACT_ID
        stale["target"] = p338_runtime.TARGET
        stale["run_id_hex"] = p338_runtime.P338_RUN_ID_HEX
        with mock.patch.object(
            evidence,
            "validate_p338_open_read_branch_proof",
            side_effect=AssertionError("unexpected P338 projection"),
        ):
            with self.assertRaises(evidence.EvidenceError):
                evidence.validate_p339_open_read_branch_proof(stale)

    def test_fresh_proof_checks_every_command_and_session(self) -> None:
        value = _proof_fixture()
        self.assertIs(
            evidence.validate_p339_open_read_branch_proof(value), value
        )
        changed = copy.deepcopy(value)
        changed["sessions"][2]["commands"][1]["command_sha256"] = "0" * 64  # type: ignore[index]
        with self.assertRaises(evidence.EvidenceError):
            evidence.validate_p339_open_read_branch_proof(changed)

    def test_runtime_and_adapter_are_fresh_and_non_retrying(self) -> None:
        self.assertEqual(adapter.audit()["run_id"], runtime.P339_RUN_ID_HEX)
        self.assertEqual(
            adapter.audit()["predecessor_run_id_rejected"],
            runtime.P338_PREDECESSOR_RUN_ID_HEX,
        )
        self.assertEqual(
            runtime.audit_binding()["open_read_branch_count"], 5
        )
        self.assertFalse(runtime.audit_binding()["retry_added"])
        self.assertFalse(runtime.audit_binding()["timeout_changed"])
        self.assertFalse(observer.audit_binding()["device_contact"])

    def test_p339_receipt_keeps_own_namespace_and_no_retry(self) -> None:
        raw = json.loads(json.dumps({
            "first_open_failure_diagnostic": True,
            "open_read_diagnostic": {
                "stage": 3,
                "code": 2,
                "branch_ordinal": 2,
                "classification": "body-read-errno",
                "raw": {"size": 19, "sha256": "1" * 64},
                "frame_count": 1,
                "retained": {"size": 49, "sha256": "2" * 64},
                "reason_frame_index": 0,
                "header_word_stages": [4, 5, 6, 7],
                "header_word_count": 0,
                "header_snapshot_complete": False,
                "header_snapshot_hex": "",
                "header_snapshot": {
                    "size": 0,
                    "sha256": hashlib.sha256(b"").hexdigest(),
                },
                "header_fields": None,
                "mismatch": None,
                "causal_result_allowed": False,
                "candidate_success": False,
            },
            "open_read_branch_ordinals": dict(
                evidence.P339_AUTH_EXEC_OPEN_READ_BRANCH_ORDINALS
            ),
            "open_read_branch_count": len(runtime.OPEN_READ_BRANCHES),
            "open_header_word_stages": [4, 5, 6, 7],
            "open_header_size": 16,
            "open_header_capture_best_effort": True,
            "original_errno_returned_unchanged": True,
        }))
        with (
            mock.patch.object(live, "_read_json", return_value=raw),
            mock.patch.object(
                live,
                "_p332_validate_receipt",
                return_value={"accepted": False},
            ) as shared,
        ):
            value = live._p339_validate_receipt(  # noqa: SLF001
                object(), Path("/unused"), {}
            )
        self.assertFalse(value["accepted"])
        self.assertEqual(value["open_read_diagnostic"]["branch_ordinal"], 2)
        self.assertIn(
            "p339_authenticated_open_read_branch_resident",
            shared.call_args.kwargs["additional_keys"],
        )

    def test_candidate_arrival_branch_map_survives_json_roundtrip(self) -> None:
        prepared = mock.Mock()
        prepared.bundle = SimpleNamespace(manifest={
            "observation": {"acceptance": adapter.acceptance_fixture()},
        })
        prepared.private_target = {"topology": "usb:3-1.3"}
        durable = {
            "valid_receipt": True,
            "accepted": False,
            "classification": "authenticated-session-error",
            "topology_sha256": "0" * 64,
            "endpoint_identity_sha256": "1" * 64,
            "download_endpoint_absent": True,
            "receipt_sha256": "2" * 64,
        }
        with mock.patch.multiple(
            live,
            _candidate_arrival_proof_role=mock.Mock(
                return_value=evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
            ),
            _reopen_candidate_observation=mock.Mock(return_value=durable),
            _reopen_candidate_guard_release=mock.Mock(
                return_value={"status": "released", "released": True}
            ),
        ):
            projection = live._candidate_arrival_proof_projection(  # noqa: SLF001
                prepared,
                {
                    "candidate_classification": "odin_transfer_completed",
                    "candidate_completed": True,
                    "download_endpoint_absent": True,
                    "rollback_classification": "odin_transfer_completed",
                    "rollback_completed": True,
                    "final_verified": True,
                },
            )
        self.assertEqual(json.loads(json.dumps(projection)), projection)
        self.assertEqual(
            projection["open_read_branch_ordinals"],
            live.P339_OPEN_READ_BRANCH_ORDINALS,
        )

    def test_builder_static_and_ready_manifest_are_host_only(self) -> None:
        built = builder.audit_existing()
        self.assertEqual(built["phase2"]["candidate"]["a"], built["phase2"]["candidate"]["b"])
        self.assertEqual(
            built["phase2"]["candidate"]["a"]["package"]["members"],
            ["boot.img.lz4"],
        )
        self.assertNotEqual(
            built["phase2"]["candidate"]["a"]["ap_tar_md5"],
            artifact.P338_AP_IDENTITY,
        )
        static_value = static.build_result()
        self.assertEqual(static_value["run_id"], runtime.P339_RUN_ID_HEX)
        self.assertFalse(static_value["safety"]["device_contact"])
        bundle = __import__("device_action_f1_v2").verify_bundle(
            ROOT, prepare.DEFAULT_MANIFEST
        )
        self.assertEqual(
            bundle.manifest["observation"]["acceptance"]["run_id"],
            runtime.P339_RUN_ID_HEX,
        )
        self.assertEqual(
            bundle.receipt["observation_contract"]["verification"]["schema"],
            "device_action_f1_p339_stock_offline_contract_v1",
        )


if __name__ == "__main__":
    unittest.main()
