from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p318_cdc_acm_endpoint_transition.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("p318_endpoint_transition", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load P3.18 endpoint transition contract")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P318 = load_module()


class P318EndpointTransitionTest(unittest.TestCase):
    def authority(self):
        return {
            "schema": P318.AUTHORITY_SCHEMA,
            "target": P318.TARGET,
            "derivation": "sealed_p317_sidecar_topology_drift",
            "source_topology": "2-1.3",
            "source_usb_device_path": (
                "/devices/pci0000:00/0000:00:0d.0/usb2/2-1/2-1.3"
            ),
            "source_id_path": "pci-0000:00:0d.0-usb-0:1.3",
            "source_controller": "0000:00:0d.0",
            "candidate_topology": "3-1.3",
            "candidate_usb_device_path": (
                "/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1.3"
            ),
            "candidate_id_path": "pci-0000:00:14.0-usb-0:1.3",
            "candidate_controller": "0000:00:14.0",
            "candidate_identity": {
                "vendor": "04e8",
                "product": "6861",
                "serial_sha256": "a" * 64,
                "driver": "cdc_acm",
                "interface": "00",
            },
            "same_port_suffix": True,
            "same_controller": False,
            "generic_companion_inference_forbidden": True,
            "observed_transition_authorizes_selection": False,
            "approved_path_remains_frozen": True,
            "scope": "p317_topology_drift_localization_only",
        }

    def endpoint(self, **changes):
        value = {
            "tty_name": "ttyACM0",
            "topology": "3-1.3",
            "usb_device_path": (
                "/devices/pci0000:00/0000:00:14.0/usb3/3-1/3-1.3"
            ),
            "vendor": "04e8",
            "product": "6861",
            "serial_sha256": "a" * 64,
            "driver": "cdc_acm",
            "interface": "00",
        }
        value.update(changes)
        return value

    def build_default(self, **overrides):
        paths = {
            "prepared_data": P318.DEFAULT_PREPARED,
            "target_data": P318.DEFAULT_TARGET_PRIVATE,
            "observer_receipt_data": P318.DEFAULT_OBSERVER_RECEIPT,
            "sidecar_result_data": P318.DEFAULT_SIDECAR_RESULT,
            "kernel_data": P318.DEFAULT_KERNEL_LOG,
            "udev_data": P318.DEFAULT_UDEV_LOG,
            "observer_source_data": P318.DEFAULT_OBSERVER_SOURCE,
            "f_acm_data": P318.DEFAULT_F_ACM_SOURCE,
            "u_serial_data": P318.DEFAULT_U_SERIAL_SOURCE,
        }
        values = {
            key: (ROOT / path).read_bytes()
            for key, path in paths.items()
        }
        values["extractor_data"] = SCRIPT.read_bytes()
        values.update(overrides)
        return P318.build_contract(**values)

    def test_exact_p317_evidence_localizes_topology_drift(self):
        result = self.build_default()
        self.assertEqual(result["verdict"], P318.VERDICT)
        authority = result["authority"]
        self.assertEqual(authority["source_topology"], "2-1.3")
        self.assertEqual(authority["candidate_topology"], "3-1.3")
        self.assertEqual(authority["source_controller"], "0000:00:0d.0")
        self.assertEqual(authority["candidate_controller"], "0000:00:14.0")
        self.assertFalse(authority["same_controller"])
        self.assertTrue(authority["same_port_suffix"])
        self.assertEqual(
            result["frozen_observer"]["effective_classification"],
            "exact-candidate-topology-drift",
        )
        self.assertFalse(result["frozen_observer"]["tty_open_attempted"])
        self.assertEqual(
            result["topology_drift_assessment"]["classification"],
            "exact-candidate-topology-drift",
        )
        self.assertFalse(result["topology_drift_assessment"]["open_permitted"])
        continuity = result["successor_topology_continuity"]
        self.assertEqual(continuity["gate"]["designation"], "permanent_boundary")
        self.assertIsNone(continuity["gate"]["expiry"])
        self.assertFalse(continuity["widen_live_selector_on_drift"])
        self.assertFalse(continuity["rollback_against_drifted_path_authorized"])
        self.assertTrue(continuity["park_without_new_effects_until_reestablished"])
        self.assertTrue(continuity["candidate_replay_forbidden"])
        record = continuity["path_record_schema"]
        self.assertEqual(
            record["phases"],
            ["download_start", "candidate_end", "rollback_download"],
        )
        self.assertTrue(record["same_bytes_parsed_and_hashed"])
        self.assertTrue(record["raw_snapshot_private"])
        effects = continuity["phase_state_effects"]
        self.assertEqual(
            effects["download_start"]["drift_absent_ambiguous"],
            "pre_session_stop_no_run_proof_class",
        )
        self.assertIn(
            "classify_host_silent",
            effects["candidate_end"]["same_complete_absent_causal_ready"],
        )
        self.assertIn(
            "no_experiment_proof_reclassification",
            effects["rollback_download"]["absent_ambiguous_unavailable"],
        )
        self.assertEqual(
            continuity["rollback_transfer_requires_state"],
            "reestablished_exact_under_fresh_recovery_binding_id",
        )
        self.assertTrue(continuity["recovery_binding_may_differ_from_start_path"])
        self.assertTrue(
            continuity["recovery_binding_never_reclassifies_experiment_result"]
        )
        audit = continuity["phase_classifier_audit"]
        self.assertEqual(audit["domain_row_count"], 180)
        self.assertEqual(audit["unique_row_count"], 180)
        self.assertTrue(audit["all_non_reestablished_rollback_rows_park"])
        self.assertFalse(authority["observed_transition_authorizes_selection"])
        self.assertEqual(
            result["scope"]["effective_proof_class"],
            "NO_PROOF_EXPERIMENT_PRECONDITION",
        )
        self.assertGreater(
            result["causal_timing_boundary"]["capture_after_enumeration_sec"],
            30.0,
        )
        self.assertTrue(
            result["causal_timing_boundary"][
                "successor_requires_explicit_post1_or_post2_host_correlation"
            ]
        )
        self.assertTrue(result["scope"]["p317_only"])
        self.assertFalse(result["scope"]["prior_campaign_silence_reclassified"])
        self.assertFalse(result["dtr_source_audit"]["dtr_hypothesis_retained"])

    def test_phase_classifier_preserves_host_silent_and_recovery_boundaries(self):
        host_silent = P318.classify_topology_phase(
            phase="candidate_end",
            relationship="absent",
            authority_state="approved_exact",
            observation_complete=True,
            causal_terminal_ready=True,
        )
        self.assertEqual(host_silent["proof_class"], "DEVICE_RESULT_HOST_SILENT")
        self.assertFalse(host_silent["park"])
        rollback = P318.classify_topology_phase(
            phase="rollback_download",
            relationship="drift",
            authority_state="reestablished_exact",
            observation_complete=True,
            causal_terminal_ready=True,
        )
        self.assertTrue(rollback["rollback_resume"])
        self.assertFalse(rollback["experiment_proof_reclassified_by_rollback"])
        unapproved = P318.classify_topology_phase(
            phase="rollback_download",
            relationship="drift",
            authority_state="not_authorized",
            observation_complete=True,
            causal_terminal_ready=True,
        )
        self.assertTrue(unapproved["park"])
        self.assertFalse(unapproved["rollback_resume"])

    def test_phase_policy_mutations_fail_closed(self):
        mutations = (
            (
                "candidate drift retained",
                "candidate_end",
                "precondition",
                "retain_experiment_terminal_classification",
            ),
            (
                "rollback exact reclassifies",
                "rollback_download",
                "resume",
                "resume_and_reclassify_experiment",
            ),
            (
                "download unavailable eligible",
                "download_start",
                "observer",
                "pre_session_candidate_eligible",
            ),
        )
        for label, phase, key, value in mutations:
            with self.subTest(label=label):
                policy = copy.deepcopy(P318.PHASE_POLICY)
                policy[phase][key] = value
                with self.assertRaises(P318.TransitionError):
                    P318.audit_topology_phase_classifier(policy)

    def test_observed_exact_transition_is_topology_drift_and_not_selected(self):
        result = P318.classify_endpoints(self.authority(), [self.endpoint()])
        self.assertEqual(result["classification"], "exact-candidate-topology-drift")
        self.assertFalse(result["open_permitted"])
        self.assertEqual(result["exact_candidate_count"], 1)

    def test_exact_candidate_at_approved_path_is_selected(self):
        endpoint = self.endpoint(
            topology="2-1.3",
            usb_device_path=(
                "/devices/pci0000:00/0000:00:0d.0/usb2/2-1/2-1.3"
            ),
        )
        result = P318.classify_endpoints(self.authority(), [endpoint])
        self.assertEqual(result["classification"], "selected-exact-approved-path")
        self.assertTrue(result["open_permitted"])

    def test_same_suffix_on_other_controller_is_not_selected(self):
        endpoint = self.endpoint(
            topology="4-1.3",
            usb_device_path=(
                "/devices/pci0000:00/0000:00:1d.0/usb4/4-1/4-1.3"
            ),
        )
        result = P318.classify_endpoints(self.authority(), [endpoint])
        self.assertEqual(
            result["classification"], "exact-candidate-unrecognized-path"
        )
        self.assertFalse(result["open_permitted"])

    def test_different_samsung_device_is_not_selected(self):
        foreign = self.endpoint(
            tty_name="ttyACM7",
            topology="5-2",
            usb_device_path=(
                "/devices/pci0000:00/0000:00:1d.0/usb5/5-2/5-2"
            ),
            product="6860",
            serial_sha256="b" * 64,
        )
        result = P318.classify_endpoints(self.authority(), [foreign])
        self.assertEqual(result["classification"], "endpoint-absent")
        self.assertEqual(result["foreign_samsung_count"], 1)
        self.assertFalse(result["open_permitted"])

    def test_multiple_exact_candidates_are_ambiguous(self):
        duplicate = self.endpoint(
            tty_name="ttyACM8",
            topology="4-2",
            usb_device_path=(
                "/devices/pci0000:00/0000:00:1d.0/usb4/4-2/4-2"
            ),
        )
        result = P318.classify_endpoints(
            self.authority(), [self.endpoint(), duplicate]
        )
        self.assertEqual(result["classification"], "exact-candidate-ambiguous")
        self.assertEqual(result["exact_candidate_count"], 2)
        self.assertFalse(result["open_permitted"])

    def test_approved_path_with_wrong_identity_is_explicit(self):
        result = P318.classify_endpoints(
            self.authority(),
            [
                self.endpoint(
                    topology="2-1.3",
                    usb_device_path=(
                        "/devices/pci0000:00/0000:00:0d.0/usb2/2-1/2-1.3"
                    ),
                    serial_sha256="b" * 64,
                )
            ],
        )
        self.assertEqual(
            result["classification"], "approved-path-identity-mismatch"
        )
        self.assertFalse(result["open_permitted"])

    def test_generic_companion_inference_cannot_be_enabled(self):
        authority = self.authority()
        authority["generic_companion_inference_forbidden"] = False
        with self.assertRaisesRegex(P318.TransitionError, "semantics"):
            P318.classify_endpoints(authority, [self.endpoint()])

    def test_observed_transition_cannot_be_promoted_to_selection_authority(self):
        authority = self.authority()
        authority["observed_transition_authorizes_selection"] = True
        with self.assertRaisesRegex(P318.TransitionError, "semantics"):
            P318.classify_endpoints(authority, [self.endpoint()])

    def test_observer_topology_predicate_mutation_fails(self):
        source = (ROOT / P318.DEFAULT_OBSERVER_SOURCE).read_bytes()
        mutated = source.replace(
            b"        endpoint.topology == topology\n        and identity",
            b"        identity",
            1,
        )
        self.assertNotEqual(source, mutated)
        with self.assertRaisesRegex(P318.TransitionError, "source seam"):
            self.build_default(observer_source_data=mutated)

    def test_dtr_source_mutation_fails(self):
        source = (ROOT / P318.DEFAULT_U_SERIAL_SOURCE).read_bytes()
        start = source.index(b"static int gs_write(")
        location = source.index(b"if (port->port_usb)", start)
        mutated = (
            source[:location]
            + b"if (port->port_usb && port->port_handshake_bits)"
            + source[location + len(b"if (port->port_usb)") :]
        )
        self.assertNotEqual(source, mutated)
        with self.assertRaisesRegex(P318.TransitionError, "TX source seam"):
            self.build_default(u_serial_data=mutated)

    def test_sidecar_hash_mutation_fails(self):
        sidecar = json.loads((ROOT / P318.DEFAULT_SIDECAR_RESULT).read_text())
        sidecar["sources"]["udev"]["sha256"] = "0" * 64
        mutated = json.dumps(sidecar, sort_keys=True).encode()
        with self.assertRaisesRegex(P318.TransitionError, "udev authority"):
            self.build_default(sidecar_result_data=mutated)

    def test_sidecar_must_continue_beyond_enumeration(self):
        sidecar = json.loads((ROOT / P318.DEFAULT_SIDECAR_RESULT).read_text())
        sidecar["sources"]["kernel"]["ended_utc"] = (
            "2026-08-12T17:04:44.060317Z"
        )
        mutated = json.dumps(sidecar, sort_keys=True).encode()
        with self.assertRaisesRegex(P318.TransitionError, "continue 30 seconds"):
            self.build_default(sidecar_result_data=mutated)

    def test_contract_never_exports_raw_candidate_serial(self):
        prepared = json.loads((ROOT / P318.DEFAULT_PREPARED).read_text())
        serial = prepared["approval_binding"]["base_binding"]["observation"][
            "candidate_observer"
        ]["usb_serial"]
        payload = P318.encode_contract(self.build_default())
        self.assertNotIn(serial.encode(), payload)
        self.assertIn(P318.digest(self.build_default()["authority"]).encode(), payload)


if __name__ == "__main__":
    unittest.main()
