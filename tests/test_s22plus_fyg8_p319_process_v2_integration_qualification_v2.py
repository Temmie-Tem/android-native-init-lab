from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_process_v2_integration_qualification_v2.py"
)
V1_SCRIPT = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p319_process_v2_integration_qualification.py"
)


def load_module_from(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load P3.19 integration qualification")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_module():
    return load_module_from(SCRIPT, "p319_process_v2_integration_v2_test")


class _StrictFreshBaselineFixture:
    """Minimal fixture validator; never accepts an arbitrary normalized object."""

    @staticmethod
    def validate_result(value):
        if type(value) is not dict or set(value) != {"fixture"} or value["fixture"] is not True:
            raise ValueError("fixture normalized result is malformed")
        return dict(value)


class _IdentityDriftCapability:
    @staticmethod
    def validate_published_result(_path):
        return {
            "authoritative": True,
            "identity": {"path": "foreign", "size": 2, "sha256": "d" * 64},
            "result": {"fixture": True},
        }


class _MatchingIdentityCapability:
    identity = None

    @classmethod
    def validate_published_result(cls, _path):
        return {
            "authoritative": True,
            "identity": cls.identity,
            "result": {"fixture": True},
        }


class P319ProcessV2IntegrationQualificationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.arming = cls.module._run_arming()

    @classmethod
    def real_result(cls):
        """Cache one current host-only integration evaluation for hostile checks."""
        if not hasattr(cls, "_real_result"):
            cls._real_result = cls.module.build_result()
        return copy.deepcopy(cls._real_result)

    def closure(self, *, pending: bool = True, blocker: bool = False):
        value = {
            "schema": "closure",
            "verdict": "PASS_P319_EXPERIMENT_EXECUTABILITY_CLOSURE_H0",
            "status": "PASS_SOURCE_CLOSURE_RUNTIME_GATES_PENDING",
            "runtime_evaluability_witnesses": {
                "witness": {
                    "status": "PENDING_FRESH_CANDIDATE_RUN" if pending else "SATISFIED"
                }
            },
            "runtime_gate_satisfied": not pending,
            "device_contact": False,
            "candidate_success": False,
            "causal_result_allowed": False,
            "scope": {"device_contact": False},
        }
        if blocker:
            return {
                "name": "experiment_executability",
                "status": "BLOCKED",
                "source_closure_pass": False,
                "runtime_classification_gate_pending": False,
            }, [{"code": "EXECUTABILITY_SOURCE_CLOSURE_BLOCKED", "detail": "fixture blocked"}]
        return {
            **self.module._summary("experiment_executability", value),
            "source_closure_pass": True,
            "runtime_classification_gate_pending": pending,
            "device_contact": False,
            "causal_result_allowed": False,
            "candidate_success": False,
        }, []

    def prerequisite(self):
        return {
            "name": "prerequisite_audit",
            "schema": "prerequisite",
            "status": "PASS",
            "verdict": "PASS_P319_PREREQUISITE_H0",
            "api": "build_receipt",
            "projection_policy": {
                "excluded_fields": ["all_revalidation_python_files_scanned", "subprocess_modules_scanned"]
            },
            "global_registry_proof": {
                "present": True,
                "runner_consumes_it": True,
                "capability_authoritative": True,
                "runner_registry_consumption_proved": True,
                "runner_recovery_closed": False,
                "runner_ready": False,
            },
            "registry_capability_authoritative": True,
            "runner_registry_consumption_proved": True,
            "runner_recovery_closed": False,
        }, []

    def adapter_pin_fixture(self):
        summary = {
            "count": 2,
            "digest": "e" * 64,
            "keys": ["adapter", self.module.REQUIRED_ARMING_SOURCE_KEY],
        }
        source_keys = {
            "pinned": summary,
            "current": dict(summary),
            "mismatch_count": 0,
            "mismatch_keys": [],
            "exact_match": True,
            "pinned_digest": "e" * 64,
            "current_digest": "e" * 64,
            "required_arming_source_key": self.module.REQUIRED_ARMING_SOURCE_KEY,
            "required_arming_key_present_pinned": True,
            "required_arming_key_present_current": True,
        }
        return {
            "pinned": {"size": 1, "sha256": "d" * 64},
            "current": {"size": 1, "sha256": "d" * 64},
            "source_keys": source_keys,
        }, []

    def recovery_fixture(self):
        sources = {
            name: {
                "path": self.module._relative(path),
                "size": index + 1,
                "sha256": f"{index + 1:064x}",
            }
            for index, (name, path) in enumerate(
                self.module.DOWNLOAD_REQUEST_RECOVERY_SOURCES.items()
            )
        }
        return {
            "name": "download_request_recovery",
            "status": "PASS_HOST_ONLY_RUNNER_FIXTURES",
            "sources": sources,
            "source_closure_sha256": self.module._identity(
                self.module._canonical(sources)
            )["sha256"],
            "tests": list(self.module.DOWNLOAD_REQUEST_RECOVERY_TESTS),
            "run_count": len(self.module.DOWNLOAD_REQUEST_RECOVERY_TESTS),
            "failures": 0,
            "errors": 0,
            "device_contact": False,
            "request_download_replayed": False,
            "candidate_backend_called": False,
            "candidate_claim_created_by_recovery": False,
            "candidate_attempt_synthesized_by_recovery": False,
            "rollback_and_final_health_path_exercised": True,
        }, []

    def cross_binding_fixture(self):
        return {
            "name": "candidate_baseline_cross_binding",
            "status": "PASS_AUTHORITATIVE",
            "authoritative": True,
            "fixture": True,
        }, []

    def pass_environment(self, *, pending: bool = True, normalized=None):
        closure, closure_blockers = self.closure(pending=pending)
        baseline = {
            "status": "PRESENT",
            "identity": {"size": 1, "sha256": "a" * 64},
            "authoritative": True,
            "normalized": {"fixture": True} if normalized is None else normalized,
        }
        registry = {"status": "PRESENT", "identity": {"size": 1, "sha256": "b" * 64}}
        provenance = {
            "path": "docs/operations/DEVICE_ACTION_PROCESS_V2.md",
            "size": 1,
            "sha256": "c" * 64,
            "sections": {
                "result_contract_arming": {"matched": True},
                "experiment_executability": {"matched": True},
                "recovery": {"matched": True},
            },
        }
        return mock.patch.multiple(
            self.module,
            _run_arming=mock.Mock(return_value=self.arming),
            _run_executability=mock.Mock(return_value=(closure, closure_blockers)),
            _run_prerequisite=mock.Mock(return_value=self.prerequisite()),
            _run_download_request_recovery=mock.Mock(
                return_value=self.recovery_fixture()
            ),
            _adapter_pin=mock.Mock(return_value=self.adapter_pin_fixture()),
            _candidate_baseline_cross_binding=mock.Mock(
                return_value=self.cross_binding_fixture()
            ),
            _required_private_receipt=mock.Mock(side_effect=[(baseline, []), (registry, [])]),
            _contract_provenance=mock.Mock(return_value=(provenance, [])),
            _load_local=mock.Mock(return_value=_StrictFreshBaselineFixture()),
        )

    def test_real_arming_output_is_consumed_and_has_three_proof_classes(self):
        admitted = self.arming["admitted_terminals"]
        self.assertEqual(self.arming["admitted_terminal_count"], len(admitted))
        self.assertEqual(
            {item["proof_class"] for item in admitted},
            self.module.PROOF_CLASSES,
        )
        self.assertEqual(self.arming["admitted_digest"], self.module._identity(self.module._canonical(admitted))["sha256"])

    def test_v1_remains_bound_to_missing_v2_baseline(self):
        v1 = load_module_from(V1_SCRIPT, "p319_process_v2_integration_v1_reference")
        self.assertEqual(
            v1.SCHEMA,
            "s22plus_fyg8_p319_process_v2_integration_qualification_v1",
        )
        self.assertEqual(v1.FRESH_BASELINE.name, "result.json")
        self.assertEqual(v1.FRESH_BASELINE.parent.name, "fresh-baseline-v2")
        self.assertFalse(v1.FRESH_BASELINE.exists())
        self.assertNotEqual(v1.FRESH_BASELINE, self.module.FRESH_BASELINE)

    def test_v2_reopens_exact_authoritative_v3_baseline(self):
        self.assertEqual(
            self.module.FRESH_BASELINE_CAPABILITY.name,
            "s22plus_fyg8_p319_fresh_baseline_capability_v3.py",
        )
        self.assertEqual(self.module.FRESH_BASELINE.parent.name, "fresh-baseline-v3")
        value, identity = self.module._json_receipt(
            self.module.FRESH_BASELINE, "exact V3 fresh baseline"
        )
        self.assertEqual(value["schema"], "s22plus_fyg8_p319_fresh_baseline_v3")
        self.assertEqual(identity["size"], 56_204)
        self.assertEqual(
            identity["sha256"],
            "fba4dc9f17e3b209d582c0f47fd387163f25ac731fb86d02819d3ced4c1b77c2",
        )
        component, blockers = self.module._required_private_receipt(
            self.module.FRESH_BASELINE,
            "fresh baseline",
            "s22plus_fyg8_p319_fresh_baseline_v3",
        )
        self.assertEqual(blockers, [])
        self.assertEqual(component["status"], "PRESENT")
        self.assertTrue(component["authoritative"])
        self.assertEqual(component["normalized"]["schema"], "s22plus_fyg8_p319_fresh_baseline_v3")
        self.assertEqual(component["identity"], identity)

    def test_v2_current_result_is_not_ready_with_runtime_witnesses_pending(self):
        result = self.real_result()
        self.assertEqual(result["schema"], "s22plus_fyg8_p319_process_v2_integration_qualification_v2")
        self.assertEqual(result["verdict"], self.module.NOT_READY_VERDICT)
        self.assertEqual(result["status"], "SOURCE_CLOSURE_PASS_RUNTIME_CLASSIFICATION_PENDING")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["blocker_count"], 0)
        self.assertTrue(result["fresh_baseline_present"])
        self.assertTrue(result["components"]["fresh_baseline"]["authoritative"])
        self.assertTrue(result["source_closure_pass"])
        self.assertTrue(result["runtime_classification_gate_pending"])
        self.assertTrue(result["registry_capability_authoritative"])
        self.assertTrue(result["runner_registry_consumption_proved"])
        self.assertTrue(result["runner_recovery_closed"])
        for key in (
            "ready", "runner_ready", "ready_manifest_created", "run_manifest_created",
            "approval_created", "live_authorized", "d0_authorized", "d1_authorized",
            "f1_authorized", "replay_authorized", "candidate_success",
            "causal_result_allowed", "device_contact",
        ):
            self.assertIs(result[key], False, key)

    def test_v2_binds_current_intent_and_preserves_previous_result(self):
        result = self.real_result()
        self.assertEqual(self.module.INTENT.parent.name, "candidate-qualification-v1-20260821-11")
        _value, identity = self.module._json_receipt(
            self.module.INTENT, "current qualification intent"
        )
        self.assertEqual(
            {key: identity[key] for key in ("size", "sha256")},
            self.module.INTENT_IDENTITY,
        )
        self.assertEqual(result["predecessor_result"], self.module.PREVIOUS_RESULT)
        self.assertEqual(
            self.module.DEFAULT_OUTPUT.parent.name,
            "process-v2-integration-qualification-v2-20260829-04",
        )

    def test_v2_cross_binds_baseline_and_current_candidate_bytes(self):
        result = self.real_result()
        binding = result["components"]["candidate_baseline_cross_binding"]
        self.assertEqual(binding["status"], "PASS_AUTHORITATIVE")
        self.assertTrue(binding["authoritative"])
        self.assertEqual(
            binding["source_key_delta"]["changed_keys"], ["target_contract"]
        )
        self.assertTrue(binding["phases"]["phase1"]["byte_identical"])
        self.assertTrue(binding["phases"]["phase2"]["byte_identical"])
        self.assertEqual(
            binding["artifacts"]["candidate"]["ap_tar_md5"]["sha256"],
            "db5666ac794dfbf6f64192d7ea341ed79ff330f03db74c57da5ef61f659032f6",
        )
        self.assertEqual(
            binding["artifacts"]["userspace"]["init"]["sha256"],
            "f6e6ea932c6c5297e18a932197e2fe1a131fac93c9caff9416d8fb873b055acb",
        )
        self.assertEqual(
            binding["artifact_files"]["baseline"]["candidate"]["a"]
            ["ap_tar_md5"]["sha256"],
            binding["artifacts"]["candidate"]["ap_tar_md5"]["sha256"],
        )
        self.assertEqual(
            binding["artifact_files"]["current"]["userspace"]["b"]
            ["child"]["sha256"],
            binding["artifacts"]["userspace"]["child"]["sha256"],
        )

    def test_v2_rejects_missing_forged_or_wrong_predecessor_cross_binding(self):
        result = self.real_result()
        removed = result["components"].pop("candidate_baseline_cross_binding")
        with self.assertRaises(self.module.IntegrationAuditError):
            self.module.validate_result(result)
        result["components"]["candidate_baseline_cross_binding"] = removed
        result["components"]["candidate_baseline_cross_binding"]["authoritative"] = False
        with self.assertRaises(self.module.IntegrationAuditError):
            self.module.validate_result(result)
        result = self.real_result()
        result["predecessor_result"] = {**result["predecessor_result"], "size": 1}
        with self.assertRaises(self.module.IntegrationAuditError):
            self.module.validate_result(result)

    def test_v2_candidate_or_phase_drift_creates_explicit_blocker(self):
        fresh = self.real_result()["components"]["fresh_baseline"]
        original = self.module._pinned_json

        def source_key_drift(path, label, expected):
            value, receipt = original(path, label, expected)
            if path == self.module.INTENT:
                value = copy.deepcopy(value)
                value["source_keys"]["unexpected"] = {"size": 1, "sha256": "f" * 64}
            if path == self.module.CURRENT_QUALIFICATION:
                value = copy.deepcopy(value)
                value["intent"]["source_keys"]["unexpected"] = {
                    "size": 1,
                    "sha256": "f" * 64,
                }
            return value, receipt

        with mock.patch.object(
            self.module, "_pinned_json", side_effect=source_key_drift
        ):
            component, blockers = self.module._candidate_baseline_cross_binding(fresh)
        self.assertFalse(component["authoritative"])
        self.assertEqual(
            [item["code"] for item in blockers],
            [self.module.CANDIDATE_CROSS_BINDING_BLOCKER],
        )

    def test_v2_rejects_paired_forged_artifact_identities(self):
        fresh = self.real_result()["components"]["fresh_baseline"]
        original = self.module._pinned_json

        def paired_forgery(path, label, expected):
            value, receipt = original(path, label, expected)
            if path in {
                self.module.BASELINE_PHASES["phase2"],
                self.module.CURRENT_PHASES["phase2"],
            }:
                value = copy.deepcopy(value)
                forged_candidate = {
                    name: {"size": index + 1, "sha256": f"{index:064x}"}
                    for index, name in enumerate(
                        ("ap_tar_md5", "boot_img", "boot_img_lz4")
                    )
                }
                forged_userspace = {
                    name: {"size": index + 4, "sha256": f"{index + 3:064x}"}
                    for index, name in enumerate(("init", "child"))
                }
                for side in ("a", "b"):
                    value["phase2"]["candidate"][side].update(
                        copy.deepcopy(forged_candidate)
                    )
                    value["phase2"]["userspace"][side].update(
                        copy.deepcopy(forged_userspace)
                    )
            return value, receipt

        with mock.patch.object(
            self.module, "_pinned_json", side_effect=paired_forgery
        ):
            component, blockers = self.module._candidate_baseline_cross_binding(fresh)
        self.assertFalse(component["authoritative"])
        self.assertEqual(
            [item["code"] for item in blockers],
            [self.module.CANDIDATE_CROSS_BINDING_BLOCKER],
        )

        def artifact_drift(path, label, expected):
            value, receipt = original(path, label, expected)
            if path == self.module.CURRENT_PHASES["phase2"]:
                value = copy.deepcopy(value)
                value["phase2"]["candidate"]["a"]["ap_tar_md5"]["sha256"] = "0" * 64
            return value, receipt

        with mock.patch.object(
            self.module, "_pinned_json", side_effect=artifact_drift
        ):
            component, blockers = self.module._candidate_baseline_cross_binding(fresh)
        self.assertFalse(component["authoritative"])
        self.assertEqual(
            [item["code"] for item in blockers],
            [self.module.CANDIDATE_CROSS_BINDING_BLOCKER],
        )

    def test_v2_rejects_v1_v2_and_forged_normalized_data(self):
        result = self.real_result()
        for schema in (
            "s22plus_fyg8_p319_fresh_baseline_v1",
            "s22plus_fyg8_p319_fresh_baseline_v2",
        ):
            forged = copy.deepcopy(result)
            forged["components"]["fresh_baseline"]["normalized"]["schema"] = schema
            with self.subTest(schema=schema), self.assertRaises(self.module.IntegrationAuditError):
                self.module.validate_result(forged)
        forged = copy.deepcopy(result)
        forged["components"]["fresh_baseline"]["normalized"]["clean"] = False
        with self.assertRaises(self.module.IntegrationAuditError):
            self.module.validate_result(forged)

    def test_real_download_request_recovery_runs_bound_runner_closure(self):
        component, blockers = self.module._run_download_request_recovery()
        self.assertEqual(blockers, [])
        self.assertEqual(component["status"], "PASS_HOST_ONLY_RUNNER_FIXTURES")
        self.assertEqual(
            set(component["sources"]), set(self.module.DOWNLOAD_REQUEST_RECOVERY_SOURCES)
        )
        self.assertEqual(
            component["run_count"], len(self.module.DOWNLOAD_REQUEST_RECOVERY_TESTS)
        )
        self.assertTrue(component["rollback_and_final_health_path_exercised"])

    def test_runtime_pending_is_separate_from_source_closure_pass(self):
        with self.pass_environment(pending=True):
            result = self.module.build_result()
        self.assertTrue(result["source_closure_pass"])
        self.assertTrue(result["runtime_classification_gate_pending"])
        self.assertNotIn(
            "RUNTIME_WITNESS_PENDING",
            {item["code"] for item in result["blockers"]},
        )
        self.assertNotIn(
            "BLOCKED_DOWNLOAD_REQUEST_CUT_RECOVERY",
            {item["code"] for item in result["blockers"]},
        )
        self.assertTrue(result["registry_capability_authoritative"])
        self.assertTrue(result["runner_registry_consumption_proved"])
        self.assertTrue(result["runner_recovery_closed"])
        self.assertFalse(result["download_request_cut_recovery_blocked"])
        self.assertFalse(result["runner_ready"])
        self.assertFalse(result["ready"])
        self.assertFalse(result["approval_created"])

    def test_blocked_component_is_explicit_and_never_ready(self):
        with self.pass_environment(pending=False):
            self.module._run_executability.return_value = self.closure(blocker=True)
            result = self.module.build_result()
        self.assertEqual(result["verdict"], self.module.BLOCKED_VERDICT)
        self.assertIn("EXECUTABILITY_SOURCE_CLOSURE_BLOCKED", {item["code"] for item in result["blockers"]})
        self.assertFalse(result["ready"])
        self.assertFalse(result["run_manifest_created"])

    def test_integration_fixture_validator_rejects_malformed_normalized_data(self):
        with self.pass_environment(normalized={"fixture": False}):
            with self.assertRaises(self.module.IntegrationAuditError):
                self.module.build_result()

    def test_fresh_baseline_identity_is_bound_across_validation(self):
        value = {"schema": "s22plus_fyg8_p319_fresh_baseline_v3"}
        first_identity = {"path": "workspace/private/result.json", "size": 1, "sha256": "a" * 64}
        with mock.patch.object(self.module, "_json_receipt", return_value=(value, first_identity)), mock.patch.object(
            self.module, "_load_local", return_value=_IdentityDriftCapability()
        ):
            component, blockers = self.module._required_private_receipt(
                self.module.FRESH_BASELINE, "fresh baseline", "s22plus_fyg8_p319_fresh_baseline_v3"
            )
        self.assertEqual(component["status"], "BLOCKED_INVALID")
        self.assertEqual(blockers[0]["code"], "FRESH_BASELINE_INVALID")
        self.assertEqual(component["error_type"], "ReceiptIdentityChanged")

    def test_fresh_baseline_replace_after_validation_is_rejected(self):
        value = {"schema": "s22plus_fyg8_p319_fresh_baseline_v3"}
        first_identity = {"path": "workspace/private/result.json", "size": 1, "sha256": "a" * 64}
        final_identity = {"path": "workspace/private/result.json", "size": 2, "sha256": "b" * 64}
        _MatchingIdentityCapability.identity = first_identity
        with mock.patch.object(
            self.module,
            "_json_receipt",
            side_effect=[(value, first_identity), (value, final_identity)],
        ), mock.patch.object(
            self.module, "_load_local", return_value=_MatchingIdentityCapability()
        ):
            component, blockers = self.module._required_private_receipt(
                self.module.FRESH_BASELINE, "fresh baseline", "s22plus_fyg8_p319_fresh_baseline_v3"
            )
        self.assertEqual(component["status"], "BLOCKED_INVALID")
        self.assertEqual(component["error_type"], "ReceiptChangedAfterValidation")
        self.assertEqual(blockers[0]["code"], "FRESH_BASELINE_INVALID")

    def test_missing_prerequisite_and_baseline_registry_are_blockers(self):
        with tempfile.TemporaryDirectory(prefix="p319-prerequisite-missing-") as directory:
            with mock.patch.object(self.module, "PREREQUISITE", Path(directory) / "missing.py"):
                prerequisite, blockers = self.module._run_prerequisite()
        self.assertEqual(prerequisite["status"], "BLOCKED_MISSING_SOURCE")
        self.assertEqual(blockers[0]["code"], "PREREQUISITE_AUDIT_MISSING")
        with mock.patch.object(self.module, "_run_arming", return_value=self.arming), mock.patch.object(
            self.module, "_run_executability", return_value=self.closure(pending=True)
        ), mock.patch.object(self.module, "_run_prerequisite", return_value=(prerequisite, blockers)), mock.patch.object(
            self.module, "_adapter_pin", return_value=self.adapter_pin_fixture()
        ), mock.patch.object(
            self.module, "_required_private_receipt", side_effect=[
                ({"status": "BLOCKED_MISSING"}, [{"code": "FRESH_BASELINE_MISSING", "detail": "missing"}]),
                ({"status": "BLOCKED_MISSING"}, [{"code": "CONSUMED_CANDIDATE_REGISTRY_MISSING", "detail": "missing"}]),
            ]
        ), mock.patch.object(self.module, "_contract_provenance", return_value=({}, [])):
            result = self.module.build_result()
        codes = {item["code"] for item in result["blockers"]}
        self.assertTrue({"PREREQUISITE_AUDIT_MISSING", "FRESH_BASELINE_MISSING", "CONSUMED_CANDIDATE_REGISTRY_MISSING"} <= codes)
        self.assertFalse(result["ready"])

    def test_prerequisite_build_receipt_api_and_projection_are_consumed(self):
        fake = {
            "schema": "prerequisite",
            "verdict": "BLOCKED_MISSING_GLOBAL_CONSUMED_REGISTRY",
            "status": "BLOCKED_MISSING_GLOBAL_CONSUMED_REGISTRY",
            "global_registry_blocker": "BLOCKED_MISSING_GLOBAL_CONSUMED_REGISTRY",
            "recovery_usability_provenance": {"demonstrated_download_path": True},
            "no_replay": {
                "new_live_run_id_absent": True,
                "candidate_pair_absent": True,
                "global_consumed_run_registry": {
                    "present": False,
                    "runner_consumes_it": False,
                    "capability_authoritative": False,
                    "runner_registry_consumption_proved": False,
                    "runner_recovery_closed": False,
                    "runner_ready": False,
                },
            },
            "restart_durability": {"third_attempt_rejected": True},
            "raw_first_execution_closure": {
                "semantic_projection_omits_only": [
                    "all_revalidation_python_files_scanned",
                    "subprocess_modules_scanned",
                ],
                "baseline": {"projection_sha256": "a" * 64},
            },
        }
        with tempfile.TemporaryDirectory(prefix="p319-prerequisite-api-") as directory:
            source = Path(directory) / "prerequisite.py"
            source.write_text("# fixture\n")
            with mock.patch.object(self.module, "PREREQUISITE", source), mock.patch.object(
                self.module,
                "_load_local",
                return_value=type("Prerequisite", (), {"build_receipt": staticmethod(lambda: fake)})(),
            ):
                component, blockers = self.module._run_prerequisite()
        self.assertEqual(component["api"], "build_receipt")
        self.assertFalse(blockers == [])
        self.assertFalse(
            component["global_registry_proof"]["capability_authoritative"]
        )
        self.assertIn(
            "raw_first_execution_closure.semantic_projection_omits_only",
            component["projection_policy"],
        )
        self.assertEqual(
            component["recovery_usability_provenance"]["demonstrated_download_path"],
            True,
        )

    def test_registry_presence_without_prerequisite_authority_stays_blocked(self):
        with self.pass_environment(pending=True):
            self.module._run_prerequisite.return_value = (
                {
                    "name": "prerequisite_audit",
                    "status": "PASS",
                    "registry_capability_authoritative": False,
                    "runner_registry_consumption_proved": False,
                    "runner_recovery_closed": False,
                    "global_registry_proof": {
                        "present": True,
                        "runner_consumes_it": False,
                        "capability_authoritative": False,
                        "runner_registry_consumption_proved": False,
                        "runner_recovery_closed": False,
                        "runner_ready": False,
                    },
                },
                [],
            )
            result = self.module.build_result()
        self.assertIn(
            "BLOCKED_MISSING_GLOBAL_CONSUMED_REGISTRY",
            {item["code"] for item in result["blockers"]},
        )
        self.assertFalse(result["global_consumed_candidate_registry_present"])
        self.assertFalse(result["ready"])

    def test_adapter_pin_mismatch_and_false_match_do_not_hide_drift(self):
        with tempfile.TemporaryDirectory(prefix="p319-integration-pin-") as directory:
            root = Path(directory)
            intent = root / "intent.json"
            current = self.module.ADAPTER.read_bytes()
            payload = {
                "source_keys": {
                    "adapter": {
                        "logical_path": self.module._relative(self.module.ADAPTER),
                        "size": len(current) + 1,
                        "sha256": self.module._identity(current)["sha256"],
                    }
                }
            }
            intent.write_bytes(self.module._canonical(payload))
            intent.chmod(0o400)
            with mock.patch.object(self.module, "INTENT", intent), mock.patch.object(
                self.module, "INTENT_IDENTITY", self.module._identity(intent.read_bytes())
            ):
                value, blockers = self.module._adapter_pin()
            self.assertEqual(value["pinned"]["sha256"], value["current"]["sha256"])
            self.assertEqual(blockers[0]["code"], "REQUALIFICATION_REQUIRED")

    def test_arming_source_only_drift_requires_requalification(self):
        qualifier = self.module._load_local(
            self.module.CANDIDATE_QUALIFICATION, "P3.19 candidate qualification test"
        )
        current_source_keys = copy.deepcopy(qualifier._source_keys())
        current_source_keys.pop(self.module.REQUIRED_ARMING_SOURCE_KEY)
        payload = {"source_keys": current_source_keys}
        with tempfile.TemporaryDirectory(prefix="p319-arming-source-drift-") as directory:
            intent = Path(directory) / "intent.json"
            intent.write_bytes(self.module._canonical(payload))
            intent.chmod(0o400)
            with mock.patch.object(self.module, "INTENT", intent), mock.patch.object(
                self.module, "INTENT_IDENTITY", self.module._identity(intent.read_bytes())
            ):
                value, blockers = self.module._adapter_pin()
        self.assertIn("REQUALIFICATION_REQUIRED", {item["code"] for item in blockers})
        comparison = value["source_keys"]
        self.assertEqual(comparison["mismatch_count"], 1)
        self.assertEqual(comparison["pinned_digest"], comparison["pinned"]["digest"])
        self.assertEqual(comparison["current_digest"], comparison["current"]["digest"])
        self.assertEqual(
            comparison["mismatch_keys"], [self.module.REQUIRED_ARMING_SOURCE_KEY]
        )
        self.assertFalse(comparison["required_arming_key_present_pinned"])
        self.assertTrue(comparison["required_arming_key_present_current"])

    def test_admitted_or_blocker_deletion_and_ready_injection_fail_closed(self):
        with self.pass_environment(pending=True):
            result = self.module.build_result()
        removed = result["components"]["arming"]["admitted_terminals"].pop()
        with self.assertRaises(self.module.IntegrationAuditError):
            self.module.validate_result(result)
        result["components"]["arming"]["admitted_terminals"].append(removed)
        result["blockers"].append({"code": "FORGED", "detail": "forged"})
        with self.assertRaises(self.module.IntegrationAuditError):
            self.module.validate_result(result)
        with self.pass_environment(pending=True):
            result = self.module.build_result()
        result["ready"] = True
        with self.assertRaises(self.module.IntegrationAuditError):
            self.module.validate_result(result)

    def test_exclusive_writer_reopens_0400_single_link_receipt(self):
        with tempfile.TemporaryDirectory(prefix="p319-integration-publish-") as directory:
            output = Path(directory) / "nested" / "result.json"
            payload = b'{"ok":false}\n'
            self.module.publish_exclusive(output, payload)
            info = output.stat()
            self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
            self.assertEqual(info.st_nlink, 1)
            self.assertEqual(output.read_bytes(), payload)
            with self.assertRaises(self.module.IntegrationAuditError):
                self.module.publish_exclusive(output, payload)

    def test_v2_publication_is_canonical_0400_single_link_and_no_clobber(self):
        value = {
            "schema": "s22plus_fyg8_p319_process_v2_integration_qualification_v2",
            "ready": False,
        }
        payload = self.module.encode(value)
        self.assertEqual(payload, b'{"ready":false,"schema":"s22plus_fyg8_p319_process_v2_integration_qualification_v2"}\n')
        with tempfile.TemporaryDirectory(prefix="p319-integration-v2-publish-") as directory:
            output = Path(directory) / "nested" / "result.json"
            self.module.publish_exclusive(output, payload)
            info = output.stat()
            self.assertEqual(stat.S_IMODE(info.st_mode), 0o400)
            self.assertEqual(info.st_nlink, 1)
            self.assertEqual(json.loads(output.read_text()), value)
            self.assertEqual(output.read_bytes(), payload)
            with self.assertRaises(self.module.IntegrationAuditError):
                self.module.publish_exclusive(output, b'{"forged":true}\n')
            self.assertEqual(output.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
