from __future__ import annotations

import hashlib
import json
from pathlib import Path
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
from tests import test_s22plus_fyg8_p335_retained_listener_acm_observer as observer_fixture  # noqa: E402


class P335CommonIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.acceptance = evidence.p335_stock_adapter.acceptance_fixture()
        self.acceptance["auth_key"] = dict(
            evidence.P335_AUTH_EXEC_AUTH_KEY_IDENTITY
        )
        self.observer = evidence.p335_authenticated_attended_resident_observer_spec()

    def test_exact_acceptance_observer_and_source_closure(self) -> None:
        self.assertEqual(
            evidence.validate_acceptance(self.acceptance), self.acceptance
        )
        self.assertEqual(
            evidence.validate_candidate_arrival_proof_role(
                evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE,
                self.observer,
                expected_run_id=evidence.P335_RUN_ID,
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
                "p335_retained_listener_acm_observer",
                "p335_retained_listener_runtime",
                "p335_artifact_identity",
                "p335_auth_key",
            }.issubset(receipts)
        )

    def test_p335_stock_projection_and_legacy_missing_acceptance(self) -> None:
        legacy = SimpleNamespace(
            manifest={"observation": {"candidate_observer": {}}}
        )
        self.assertIsNone(live._userspace_overlay_contract_id(legacy))

        adapter = evidence.p335_stock_adapter
        classified = evidence.classify_e1_latest_stage(
            bytes(adapter.RAW_SIZE), self.acceptance
        )
        projection = live._p320_terminal_projection(classified)
        self.assertEqual(projection["proof_class"], "NO_PROOF_OBSERVER")
        self.assertEqual(projection["stock"], [])
        self.assertTrue(projection["acm_primary"])
        self.assertFalse(projection["acm_supplemental"])
        self.assertTrue(projection["acm_required_for_acceptance"])

    def test_final_observer_parser_failure_keeps_p335_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            payload = b"p335-parser-failure-fixture"
            reads = []
            for index in (1, 2):
                path = run_dir / f"rollback-observer-{index}.bin"
                handle = live.raw_capture.publish_captured_bytes(
                    run_dir,
                    f"900{index}-observer-eof",
                    stdout=payload,
                    stdout_name=path.name,
                    stderr_name=path.name + ".stderr",
                )
                reads.append(
                    {
                        "path": str(path),
                        "bytes": len(payload),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "raw_capture": {
                            "path": str(handle.receipt_path),
                            "size": handle.receipt_path.stat().st_size,
                            "sha256": hashlib.sha256(
                                handle.receipt_path.read_bytes()
                            ).hexdigest(),
                        },
                        "read_to_eof": True,
                        "stderr_bytes": 0,
                        "elapsed_sec": 0.01,
                    }
                )
            expected_health = {
                "verified_boot_state": "orange",
                "boot_sha256": "11" * 32,
                "supporting_partition_sha256": "12" * 32,
            }
            private_target = {"serial": "private-serial", "topology": "usb:3-1"}
            prepared = SimpleNamespace(
                run_dir=run_dir,
                private_target=private_target,
                bundle=SimpleNamespace(
                    manifest={
                        "observation": {
                            "acceptance": self.acceptance,
                            "candidate_observer": self.observer,
                            evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: (
                                evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
                            ),
                        }
                    },
                    profile={"final_health": expected_health},
                ),
            )
            failure = live.F1LiveError("fixture parser rejection")
            stock_error = live._p335_stock_error(payload, failure)
            classification = live._p335_parser_failure_classification(
                payload, failure
            )
            health = {
                "android_boot_completed": True,
                "boot_animation_stopped": True,
                **expected_health,
                "root_verified": True,
                "odin_endpoint_absent": True,
                "kernel_release": "fixture-kernel",
                "boot_id_sha256": "13" * 32,
            }
            state = {
                "marker_accepted": False,
                "final_evidence": {
                    "health": health,
                    "target_evidence_sha256": core.json_sha256(
                        {
                            "serial": hashlib.sha256(
                                private_target["serial"].encode()
                            ).hexdigest(),
                            "topology": hashlib.sha256(
                                private_target["topology"].encode()
                            ).hexdigest(),
                        }
                    ),
                    "observer": {
                        "reads": reads,
                        "byte_identical": True,
                        "bytes": len(payload),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "exact_marker_count": 0,
                        "marker_family_count": 0,
                        "classification": classification,
                        "accepted": False,
                        "p335_stock_error": stock_error,
                    },
                    "rollback_verified": True,
                },
            }
            with mock.patch.object(
                live, "classify_acceptance", side_effect=failure
            ):
                live._validate_final_observer(prepared, state)

    def test_closed_live_result_uses_p335_terminal_namespace(self) -> None:
        role = evidence.CANDIDATE_AUTHENTICATED_LOGICAL_RESIDENT_EXEC_ROLE
        bundle = SimpleNamespace(
            sha256="21" * 32,
            manifest={
                "manifest_id": "p335-terminal-fixture",
                "observation": {
                    "acceptance": self.acceptance,
                    "candidate_observer": self.observer,
                    evidence.CANDIDATE_ARRIVAL_PROOF_ROLE_KEY: role,
                },
            },
        )
        prepared = SimpleNamespace(
            run_dir=Path("/unused/p335-terminal"),
            binding_sha256="22" * 32,
            bundle=bundle,
        )
        arrival_key = evidence.CANDIDATE_ARRIVAL_PROOF_STATE_KEY
        state = {
            "candidate_classification": "odin_transfer_completed",
            "candidate_completed": True,
            "rollback_classification": "odin_transfer_completed",
            "rollback_completed": True,
            "final_verified": True,
            arrival_key: {"proof": True},
        }
        timeline = {"events": [{"name": name} for name in core.TIMELINE]}
        journal_receipt = {"sha256": "23" * 32}
        journal = SimpleNamespace(
            records=lambda: [],
            receipt=lambda: journal_receipt,
            state=lambda: "CLOSED",
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
            "verdict": live.P335_SUCCESS_VERDICT,
            "outcome_class": live.P335_SUCCESS_OUTCOME,
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

    def test_backend_selects_p335_before_authenticated_fallback(self) -> None:
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
        selected = object()
        with (
            mock.patch.object(
                live,
                "_p324_typec_lane_value",
                return_value=({"lane": True}, {"receipt": True}),
            ),
            mock.patch.object(
                live, "_p335_candidate_observer_session", return_value=selected
            ) as p335,
            mock.patch.object(live, "_p328_candidate_observer_session") as fallback,
        ):
            self.assertIs(backend.candidate_observer_session(prepared), selected)
        p335.assert_called_once()
        fallback.assert_not_called()

    def test_live_observer_delegates_the_single_reopen_to_p335_codec(self) -> None:
        base = SimpleNamespace(dev_root=Path("/dev"), _raw_tty=lambda _fd: None)
        session = live._P335ObserverSession(
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
            sessions=[SimpleNamespace(result=final_exchange)], complete=True
        )
        proof = {
            "retained_listener_proof": True,
            "per_boot_identity_proof": True,
            "same_boot_id": True,
            "same_initial_fd": True,
            "descriptor_reopened": True,
            "physical_reopen_count": 1,
            "session_count": 3,
        }

        def exchange(descriptor, _key, *, reopen, timeout_sec, writer):
            self.assertEqual(descriptor, 23)
            self.assertEqual(reopen(), 24)
            self.assertGreater(timeout_sec, 0)
            self.assertIsNotNone(writer)
            return resident

        with (
            mock.patch.object(session, "_settle_guard_properties", return_value=None),
            mock.patch.object(session, "_endpoint_exact", return_value=True),
            mock.patch.object(live.os, "open", side_effect=[23, 24]) as opened,
            mock.patch.object(live.os, "close") as closed,
            mock.patch.object(live.fcntl, "ioctl"),
            mock.patch.object(
                live.p335_retained_observer,
                "exchange_retained",
                side_effect=exchange,
            ),
            mock.patch.object(
                live.p335_retained_observer,
                "validate_retained_proof",
                return_value=proof,
            ),
        ):
            self.assertEqual(
                session._read_endpoint(endpoint, 10**12, SimpleNamespace()),
                "accepted",
            )
        self.assertEqual(opened.call_count, 2)
        closed.assert_not_called()
        self.assertIs(session.exchange, final_exchange)

    def test_real_three_session_receipt_reopens_through_live_validator(self) -> None:
        helper = observer_fixture.P335RetainedListenerObserverTests(
            "test_two_same_fd_sessions_then_one_physical_reopen"
        )
        (
            initial_host,
            reopened_host,
            initial_peer,
            reopened_peer,
            initial_thread,
            reopened_thread,
            errors,
        ) = helper._success_fixture()  # noqa: SLF001
        try:
            resident = live.p335_retained_observer.exchange_retained(
                initial_host,
                observer_fixture.TEST_KEY,
                reopen=lambda: reopened_host,
                timeout_sec=5,
            )
            proof = live.p335_retained_observer.validate_retained_proof(resident)
        finally:
            initial_host.close()
            reopened_host.close()
            initial_thread.join(timeout=5)
            reopened_thread.join(timeout=5)
            initial_peer.close()
            reopened_peer.close()
        self.assertFalse(errors)

        session = live._P335ObserverSession(
            delegate=SimpleNamespace(),
            base=SimpleNamespace(),
            spec={},
            run_dir=Path("/unused"),
            lane_binding={},
            lane_binding_receipt={},
            usb_root=Path("/unused/usb"),
            typec_root=Path("/unused/typec"),
            auth_key=observer_fixture.TEST_KEY,
            auth_key_sha256=hashlib.sha256(observer_fixture.TEST_KEY).hexdigest(),
        )
        session.resident_result = resident
        session.proof = proof
        session.exchange = resident.sessions[-1].result
        captured: dict = {}
        base_value = {
            "binding": {},
            "spec_sha256": "01" * 32,
            "baseline_sha256": "02" * 32,
            "download_departure_sha256": "03" * 32,
            "download_endpoint_absent": True,
            "topology_sha256": "04" * 32,
            "endpoint_identity_sha256": "05" * 32,
            "guard_sha256": "06" * 32,
            "raw": {"path": "/unused/raw", "size": 1, "sha256": "07" * 32},
            "banner_seen": True,
            "ready_seen": True,
            "done_seen": True,
            "lane": {},
            "bounded": True,
            "elapsed_sec": 1.0,
            "classification": "accepted",
            "accepted": True,
        }
        with (
            mock.patch.object(
                live._P328ObserverSession,
                "_observe_value",
                return_value=(base_value, {}),
            ),
            mock.patch.object(
                session,
                "_publish_value",
                side_effect=lambda value, *_args, **_kwargs: captured.update(value),
            ),
        ):
            session.observe(
                timeout_sec=30,
                download_departure={
                    "download_endpoint_absent": True,
                    "absence_timed_out": False,
                    "sequence": 1,
                },
            )

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "candidate-observer.json"
            path.write_text(json.dumps(captured, sort_keys=True), encoding="utf-8")
            prepared = SimpleNamespace(run_dir=Path(temporary))
            key_identity = {
                "size": 32,
                "sha256": hashlib.sha256(observer_fixture.TEST_KEY).hexdigest(),
            }

            def validate_test_key(value):
                return live.p335_retained_observer.validate_proof_value(
                    value,
                    expected_auth_key_sha256=key_identity["sha256"],
                )

            with (
                mock.patch.object(
                    live,
                    "_p328_validate_common_receipt",
                    return_value=(
                        {
                            "both_topologies_inventory_complete": True,
                            "accepted_inventory_exact": True,
                            "same_run_typec_partner_continuity": True,
                            "accepted_for_p324": True,
                        },
                        "04" * 32,
                        "05" * 32,
                    ),
                ),
                mock.patch.object(
                    live, "_p328_bound_auth_key_identity", return_value=key_identity
                ),
                mock.patch.object(
                    live, "_p332_validate_raw_session_bindings", return_value=None
                ),
                mock.patch.object(
                    live.typed_evidence,
                    "validate_p335_attended_resident_proof",
                    side_effect=validate_test_key,
                ),
            ):
                reopened = live._p335_validate_receipt(prepared, path, {})
        self.assertTrue(reopened["accepted"])
        self.assertEqual(reopened["session_count"], 3)
        self.assertEqual(reopened["physical_reopen_count"], 1)

    def test_observed_event_precedes_durable_resident_lease(self) -> None:
        sequence: list[str] = []

        class Journal:
            def transition(self, state: str, _outcome: str, _details: dict) -> None:
                self.state = state
                sequence.append(state)

            def event(self, name: str, _details: dict | None = None) -> None:
                sequence.append(name)

            def records(self) -> list[dict[str, str]]:
                return [{"record_sha256": "18" * 32}]

        proof = {
            "sessions": [
                {"boot_id_sha256": "07" * 32},
                {"boot_id_sha256": "07" * 32},
                {"boot_id_sha256": "07" * 32},
            ]
        }
        durable = {
            "accepted": True,
            "download_endpoint_absent": True,
            "candidate_topology_sha256": "b2" * 32,
            "p335_authenticated_attended_resident": proof,
        }
        bundle = SimpleNamespace(
            receipt={
                "observation_contract": {
                    "verification": {
                        "ap_payload_closure": {
                            "boot_image": {"sha256": "c3" * 32}
                        }
                    }
                }
            },
            manifest={
                "candidate_ap": {"sha256": "d4" * 32},
                "rollback_ap": {"sha256": "f6" * 32},
            },
        )
        with tempfile.TemporaryDirectory() as temporary:
            prepared = SimpleNamespace(run_dir=Path(temporary), bundle=bundle)
            original_publish = live.p335_resident_session.ResidentLease.publish

            def publish(*args, **kwargs):
                sequence.append("lease-published")
                return original_publish(*args, **kwargs)

            with (
                mock.patch.object(
                    live, "_reopen_candidate_observation", return_value=durable
                ),
                mock.patch.object(live, "_p335_proof_ok", return_value=True),
                mock.patch.object(
                    live,
                    "_seal_p300_before_candidate_boot_ready",
                    side_effect=lambda _trace, journal, proof: journal.event(
                        "candidate_boot_ready", {"proof": proof}
                    ),
                ),
                mock.patch.object(
                    live.p335_resident_session.ResidentLease,
                    "publish",
                    side_effect=publish,
                ),
                mock.patch.object(live, "_state", return_value={}),
                mock.patch.object(live, "_save_state"),
            ):
                result = live._finish_p335_candidate_window_before_guard_release(
                    prepared,
                    Journal(),
                    SimpleNamespace(completed=True),
                    {},
                    SimpleNamespace(),
                )
            self.assertTrue(result["resident_session_active"])
            self.assertEqual(
                sequence[:3], ["OBSERVED", "candidate_boot_ready", "lease-published"]
            )
            self.assertTrue(
                (Path(temporary) / "p335-resident-session/lease.json").is_file()
            )
            self.assertEqual(result["snapshot"]["state"], "ACTIVE")


if __name__ == "__main__":
    unittest.main()
