from __future__ import annotations

import contextlib
import dataclasses
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "workspace/public/src/scripts/server-distro"
sys.path.insert(0, str(MODULE_DIR))


def load(name: str):
    if name in sys.modules:
        return sys.modules[name]
    source = MODULE_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


OWNER = load("a90_boot_only_f1_minimal_v1")
R = load("a90_h28_physical_system_return_reconcile_v1")


class ObserveOnlyBackend:
    def __init__(self, snapshot, mutation=None, error=None):
        self.snapshot = snapshot
        self.mutation = mutation
        self.error = error
        self.observe_calls = 0
        self.flash_calls = 0

    def observe(self, expected, fresh_state, *, require_fresh_state, timeout_sec):
        self.observe_calls += 1
        if (
            expected["version"] != "0.9.285"
            or require_fresh_state is not False
            or fresh_state["enablePath"]
            != "/cache/a90-auto-handoff-phase3-minimal-h28.enable"
            or timeout_sec != 300
        ):
            raise AssertionError("wrong read-only observation binding")
        if self.mutation:
            self.mutation()
        if self.error:
            raise self.error
        return self.snapshot

    def flash(self, *_args, **_kwargs):
        self.flash_calls += 1
        raise AssertionError("H28 physical return attempted a flash")


class H28PhysicalReturnTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.side_root = base / "sidecar"
        self.review_path = base / "review.json"
        self.run_root = base / "runs"
        self.run_root.mkdir(mode=0o700)
        self.run_directory = self.run_root / R.RUN_ID
        self.run_directory.mkdir(mode=0o700)
        self.old = {
            "owner_root": OWNER.RUN_ROOT,
            "side_root": R.SIDE_ROOT,
            "review_path": R.CURRENT_REVIEW_PATH,
            "manifest_sha": R.MANIFEST_SHA256,
            "terminal_sha": R.TERMINAL_SHA256,
            "incident": R.INCIDENT_RECORD_SHA256,
            "active_sha": R.ACTIVE_GUARD_SHA256,
            "candidate_sha": R.CANDIDATE_GUARD_SHA256,
            "owner_sources": OWNER.EXECUTION_SOURCE_RELS,
        }
        OWNER.RUN_ROOT = self.run_root
        R.SIDE_ROOT = self.side_root
        R.CURRENT_REVIEW_PATH = self.review_path
        R.MANIFEST_SHA256 = "d" * 64
        R.TERMINAL_SHA256 = "e" * 64
        self.manifest = {
            "runId": R.RUN_ID,
            "candidate": {"sha256": "1" * 64},
            "rollback": {
                "sha256": "2" * 64,
                "version": "0.9.285",
                "build": "v2321-usb-clean-identity-rodata",
            },
            "qualification": {
                "freshState": {
                    "enablePath": "/cache/a90-auto-handoff-phase3-minimal-h28.enable",
                    "latchPath": "/cache/a90-auto-handoff-phase3-minimal-h28.done",
                },
                "review": {"path": str(self.review_path), "size": 0, "sha256": "0" * 64},
            },
            "timeouts": {"healthSec": 300},
        }
        self.manifest_raw = OWNER.canonical_json(self.manifest)
        R.INCIDENT_RECORD_SHA256 = {}
        self._write_incident()
        active_path, active_raw = OWNER._active_guard(self.manifest)
        candidate_path, candidate_raw = OWNER._candidate_guard(self.manifest)
        active_path.write_bytes(active_raw)
        candidate_path.write_bytes(candidate_raw)
        active_path.chmod(0o600)
        candidate_path.chmod(0o600)
        R.ACTIVE_GUARD_SHA256 = R._sha(active_raw)
        R.CANDIDATE_GUARD_SHA256 = R._sha(candidate_raw)
        self._write_review()
        self.snapshot = OWNER.Snapshot(
            target_evidence_sha256="3" * 64,
            boot_id="01234567-89ab-cdef-0123-456789abcdef",
            version="0.9.285",
            build="v2321-usb-clean-identity-rodata",
            healthy=True,
            recovery_available=True,
            recovery_evidence_sha256=self.review_sha,
            fresh_state_observed=False,
            fresh_state_absent=False,
            other_targets_untouched=True,
            receipt_sha256="4" * 64,
        )
        self.addCleanup(self._restore)

    @property
    def review_sha(self):
        return R._sha(self.review_path.read_bytes())

    def _restore(self):
        OWNER.RUN_ROOT = self.old["owner_root"]
        R.SIDE_ROOT = self.old["side_root"]
        R.CURRENT_REVIEW_PATH = self.old["review_path"]
        R.MANIFEST_SHA256 = self.old["manifest_sha"]
        R.TERMINAL_SHA256 = self.old["terminal_sha"]
        R.INCIDENT_RECORD_SHA256 = self.old["incident"]
        R.ACTIVE_GUARD_SHA256 = self.old["active_sha"]
        R.CANDIDATE_GUARD_SHA256 = self.old["candidate_sha"]

    def _write_incident(self):
        terminal = {
            "schema": OWNER.RESULT_SCHEMA,
            "terminal": "RECOVERY_REQUIRED",
            "reason": "ROLLBACK_HEALTH_UNPROVED",
            "snapshot": None,
            "candidateReplay": False,
        }
        payloads = {
            "20-candidate-intent.json": {"sha256": self.manifest["candidate"]["sha256"]},
            "30-rollback-intent.json": {"sha256": self.manifest["rollback"]["sha256"]},
            "40-terminal.json": terminal,
        }
        for name in R.INCIDENT_NAMES:
            record = OWNER._record(
                OWNER.RECORD_KINDS[name],
                R.MANIFEST_SHA256,
                payloads.get(name, {}),
            )
            path = self.run_directory / name
            path.write_bytes(OWNER.canonical_json(record))
            path.chmod(0o600)
        self.records = OWNER.read_records(self.run_directory)
        R.INCIDENT_RECORD_SHA256 = {
            name: R._json_sha(record) for name, record in self.records.items()
        }

    def _write_review(self, **changes):
        review = {
            "schema": R.REVIEW_SCHEMA,
            "capability": R.CAPABILITY,
            "verdict": "PASS_GO",
            "runId": R.RUN_ID,
            "manifestSha256": R.MANIFEST_SHA256,
            "terminalSha256": R.TERMINAL_SHA256,
            "executionClosureSha256": R.execution_closure_sha256(),
            "findings": {"high": [], "medium": [], "low": []},
            "contacts": {
                "device": 0,
                "dev": 0,
                "usb": 0,
                "network": 0,
                "workspacePrivate": 0,
                "otherTargets": 0,
                "writes": 0,
            },
            "liveAuthority": False,
        }
        review.update(changes)
        self.review_path.write_bytes(OWNER.canonical_json(review))
        self.review_path.chmod(0o600)

    @contextlib.contextmanager
    def fixed(self, backend=None):
        with mock.patch.object(
            R, "_load_manifest", return_value=(self.manifest_raw, self.manifest)
        ), mock.patch.object(OWNER, "_live_backend", return_value=backend):
            yield

    def prepare(self):
        with self.fixed():
            return R.prepare()

    def authorize(self, token):
        with self.fixed(), contextlib.redirect_stdout(io.StringIO()) as output:
            R.authorize(token)
        return output.getvalue()

    def arm(self):
        token = self.prepare()
        self.authorize(token)
        return token

    def finalize(self, backend):
        with self.fixed(backend):
            return R.finalize(
                operator_attended=True,
                physical_system_return_confirmed=True,
            )

    def publish_observation_intent(self):
        with self.fixed():
            state = R._state(require_active=True)
            value = {
                "schema": R.OBSERVATION_SCHEMA,
                "capability": R.CAPABILITY,
                "runId": R.RUN_ID,
                "manifestSha256": R.MANIFEST_SHA256,
                "terminalSha256": R.TERMINAL_SHA256,
                "physicalSystemReturnIntentSha256": state.intent[2],
                "currentReviewSha256": state.review_sha256,
                "executionClosureSha256": state.closure_sha256,
                "operatorAttended": True,
                "physicalSystemReturnConfirmed": True,
            }
            return R._publish_observation_intent(value)

    def test_prepare_is_host_only_and_preserves_owner_closure(self):
        before = self.side_root.exists()
        token = self.prepare()
        self.assertTrue(token.startswith(R.APPROVAL_PREFIX))
        self.assertEqual(before, self.side_root.exists())
        self.assertEqual(OWNER.EXECUTION_SOURCE_RELS, self.old["owner_sources"])
        self.assertIn(R._H28_SOURCE_RELS[0], R.EXECUTION_SOURCE_RELS)

    def test_wrong_approval_does_not_write_or_instruct(self):
        self.prepare()
        with self.assertRaises(R.ContractError), contextlib.redirect_stdout(io.StringIO()) as output:
            with self.fixed():
                R.authorize(R.APPROVAL_PREFIX + "0" * 64)
        self.assertEqual(output.getvalue(), "")
        self.assertFalse(self.side_root.exists())

    def test_authorize_publishes_one_instruction_and_second_is_rejected(self):
        token = self.prepare()
        output = self.authorize(token)
        self.assertEqual(output, R.INSTRUCTION + "\n")
        self.assertTrue((self.side_root / R.INTENT_NAME).is_file())
        with self.assertRaises(R.ContractError):
            self.authorize(token)

    def test_sidecar_collision_and_extra_entry_are_rejected(self):
        for extra in ("collision", "extra.json"):
            with self.subTest(extra=extra):
                self.side_root.mkdir(mode=0o700)
                (self.side_root / extra).write_bytes(b"x")
                with self.assertRaises(R.ContractError):
                    self.prepare()
                self.side_root = Path(self.temp.name) / f"sidecar-{extra}"
                R.SIDE_ROOT = self.side_root

    def test_changed_incident_and_terminal_are_rejected(self):
        for name in ("22-candidate-result.json", "40-terminal.json"):
            with self.subTest(name=name):
                path = self.run_directory / name
                value = OWNER.parse_canonical(path.read_bytes(), "record")
                value["payload"]["changed"] = True
                path.write_bytes(OWNER.canonical_json(value))
                with self.assertRaises(R.ContractError):
                    self.prepare()
                self._write_incident()

    def test_review_shape_findings_contacts_authority_and_closure_are_rejected(self):
        cases = (
            {"findings": {"high": ["x"], "medium": [], "low": []}},
            {"contacts": {"device": 1, "dev": 0, "usb": 0, "network": 0, "workspacePrivate": 0, "otherTargets": 0, "writes": 0}},
            {"liveAuthority": True},
            {"executionClosureSha256": "f" * 64},
            {"unexpected": 1},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                self._write_review(**changes)
                with self.assertRaises(R.ContractError):
                    self.prepare()
                self._write_review()

    def test_malformed_review_is_rejected(self):
        self.review_path.write_bytes(b"not canonical json")
        with self.assertRaises(R.ContractError):
            self.prepare()

    def test_missing_active_or_candidate_guard_is_rejected(self):
        for kind in ("active", "candidate"):
            with self.subTest(kind=kind):
                active, _ = OWNER._active_guard(self.manifest)
                candidate, _ = OWNER._candidate_guard(self.manifest)
                (active if kind == "active" else candidate).unlink()
                with self.assertRaises(R.ContractError):
                    self.prepare()
                self._write_guards()

    def _write_guards(self):
        active, active_raw = OWNER._active_guard(self.manifest)
        candidate, candidate_raw = OWNER._candidate_guard(self.manifest)
        active.write_bytes(active_raw)
        candidate.write_bytes(candidate_raw)
        active.chmod(0o600)
        candidate.chmod(0o600)

    def test_finalize_requires_intent_and_both_flags(self):
        with self.assertRaises(R.ContractError):
            with self.fixed(ObserveOnlyBackend(self.snapshot)):
                R.finalize(operator_attended=True, physical_system_return_confirmed=True)
        with self.assertRaises(R.ContractError):
            R.finalize(operator_attended=False, physical_system_return_confirmed=True)
        with self.assertRaises(R.ContractError):
            R.finalize(operator_attended=True, physical_system_return_confirmed=False)

    def test_wrong_or_unhealthy_v2321_keeps_both_guards(self):
        variants = (
            dataclasses.replace(self.snapshot, healthy=False),
            dataclasses.replace(self.snapshot, version="wrong"),
            dataclasses.replace(self.snapshot, other_targets_untouched=False),
            dataclasses.replace(self.snapshot, recovery_evidence_sha256="f" * 64),
        )
        for snapshot in variants:
            with self.subTest(snapshot=snapshot):
                self.arm()
                with self.assertRaises(R.ContractError):
                    self.finalize(ObserveOnlyBackend(snapshot))
                self.assertTrue(OWNER._active_guard(self.manifest)[0].exists())
                self.assertTrue(OWNER._candidate_guard(self.manifest)[0].exists())
                (self.side_root / R.INTENT_NAME).unlink()
                (self.side_root / R.OBSERVATION_INTENT_NAME).unlink()
                self.side_root.rmdir()

    def test_backend_observation_failure_keeps_guards_and_no_record(self):
        self.arm()
        with self.assertRaises(RuntimeError):
            self.finalize(ObserveOnlyBackend(self.snapshot, error=RuntimeError("observer")))
        self.assertFalse((self.run_directory / R.RECOVERY_NAME).exists())
        self.assertTrue(OWNER._active_guard(self.manifest)[0].exists())
        self.assertTrue(OWNER._candidate_guard(self.manifest)[0].exists())

    def test_guard_loss_during_observation_keeps_other_guard_and_no_record(self):
        for removed in ("active", "candidate"):
            with self.subTest(removed=removed):
                self.arm()
                active, _ = OWNER._active_guard(self.manifest)
                candidate, _ = OWNER._candidate_guard(self.manifest)
                target = active if removed == "active" else candidate
                with self.assertRaises(R.ContractError):
                    self.finalize(ObserveOnlyBackend(self.snapshot, mutation=target.unlink))
                self.assertFalse((self.run_directory / R.RECOVERY_NAME).exists())
                other = candidate if removed == "active" else active
                self.assertTrue(other.exists())
                (self.side_root / R.INTENT_NAME).unlink()
                (self.side_root / R.OBSERVATION_INTENT_NAME).unlink()
                self.side_root.rmdir()
                self._write_guards()

    def test_record_publication_failure_keeps_guards(self):
        self.arm()
        with mock.patch.object(OWNER, "publish_record", side_effect=R.ContractError("publish")):
            with self.assertRaises(R.ContractError):
                self.finalize(ObserveOnlyBackend(self.snapshot))
        self.assertTrue(OWNER._active_guard(self.manifest)[0].exists())
        self.assertTrue(OWNER._candidate_guard(self.manifest)[0].exists())

    def test_record_readback_drift_keeps_guards(self):
        self.arm()
        original = OWNER.publish_record

        def publish_then_drift(directory, name, value):
            original(directory, name, value)
            path = directory / name
            changed = OWNER.parse_canonical(path.read_bytes(), name)
            changed["payload"]["bootWriteCount"] = 1
            path.write_bytes(OWNER.canonical_json(changed))
            path.chmod(0o600)

        with mock.patch.object(OWNER, "publish_record", side_effect=publish_then_drift):
            with self.assertRaises(R.ContractError):
                self.finalize(ObserveOnlyBackend(self.snapshot))
        self.assertTrue(OWNER._active_guard(self.manifest)[0].exists())
        self.assertTrue(OWNER._candidate_guard(self.manifest)[0].exists())

    def test_exact_recovery_with_active_guard_present_parks(self):
        self.arm()
        with mock.patch.object(OWNER, "_release_active_guard", side_effect=R.ContractError("cut")):
            with self.assertRaises(R.ContractError):
                self.finalize(ObserveOnlyBackend(self.snapshot))
        self.assertTrue(OWNER._active_guard(self.manifest)[0].exists())
        backend = ObserveOnlyBackend(self.snapshot)
        with self.assertRaises(R.ContractError):
            self.finalize(backend)
        self.assertEqual(backend.observe_calls, 0)

    def test_exact_recovery_with_active_absent_is_idempotent_without_observer(self):
        self.arm()
        first_backend = ObserveOnlyBackend(self.snapshot)
        self.finalize(first_backend)
        self.assertEqual(first_backend.flash_calls, 0)
        backend = ObserveOnlyBackend(self.snapshot)
        result = self.finalize(backend)
        self.assertEqual(backend.observe_calls, 0)
        self.assertTrue(result["physicalSystemReturnConfirmed"])
        self.assertEqual(
            result["observationIntentSha256"],
            R._sha((self.side_root / R.OBSERVATION_INTENT_NAME).read_bytes()),
        )
        self.assertTrue(OWNER._candidate_guard(self.manifest)[0].exists())

    def test_failed_first_observation_consumes_observation_intent(self):
        self.arm()
        with self.assertRaises(RuntimeError):
            self.finalize(ObserveOnlyBackend(self.snapshot, error=RuntimeError("observer")))
        self.assertTrue((self.side_root / R.OBSERVATION_INTENT_NAME).exists())
        second = ObserveOnlyBackend(self.snapshot)
        with self.assertRaises(R.ContractError):
            self.finalize(second)
        self.assertEqual(second.observe_calls, 0)

    def test_wrong_first_observation_consumes_observation_intent(self):
        self.arm()
        wrong = dataclasses.replace(self.snapshot, healthy=False)
        with self.assertRaises(R.ContractError):
            self.finalize(ObserveOnlyBackend(wrong))
        self.assertTrue((self.side_root / R.OBSERVATION_INTENT_NAME).exists())
        second = ObserveOnlyBackend(self.snapshot)
        with self.assertRaises(R.ContractError):
            self.finalize(second)
        self.assertEqual(second.observe_calls, 0)

    def test_observation_intent_publication_cut_prevents_backend_creation(self):
        self.arm()
        original = R._publish_observation_intent

        def cut(value):
            original(value)
            raise R.ContractError("cut after observation intent")

        with mock.patch.object(R, "_publish_observation_intent", side_effect=cut), mock.patch.object(OWNER, "_live_backend") as backend:
            with self.assertRaises(R.ContractError):
                with self.fixed():
                    R.finalize(operator_attended=True, physical_system_return_confirmed=True)
        backend.assert_not_called()
        self.assertTrue((self.side_root / R.OBSERVATION_INTENT_NAME).exists())

    def test_observation_intent_mutation_extra_and_partial_states_reject(self):
        self.arm()
        observation_path = self.side_root / R.OBSERVATION_INTENT_NAME
        self.publish_observation_intent()
        value = OWNER.parse_canonical(observation_path.read_bytes(), "observation")
        value["executionClosureSha256"] = "f" * 64
        observation_path.write_bytes(OWNER.canonical_json(value))
        with self.assertRaises(R.ContractError):
            self.finalize(ObserveOnlyBackend(self.snapshot))
        observation_path.unlink()
        observation_path.write_bytes(b"partial")
        observation_path.chmod(0o600)
        with self.assertRaises(R.ContractError):
            self.finalize(ObserveOnlyBackend(self.snapshot))
        observation_path.unlink()
        self.publish_observation_intent()
        (self.side_root / "extra").write_bytes(b"x")
        with self.assertRaises(R.ContractError):
            self.finalize(ObserveOnlyBackend(self.snapshot))

    def test_payload_replay_count_outcome_and_snapshot_mutations_are_rejected(self):
        self.arm()
        self.finalize(ObserveOnlyBackend(self.snapshot))
        path = self.run_directory / R.RECOVERY_NAME
        original = OWNER.parse_canonical(path.read_bytes(), "recovery")
        for key, value in (
            ("candidateReplay", True),
            ("rollbackReplay", True),
            ("originalTwrpReturnOutcome", "PROVED"),
            ("hostRecoveryCommandCount", 1),
            ("observationIntentSha256", "f" * 64),
            ("physicalSystemReturnConfirmed", False),
        ):
            with self.subTest(key=key):
                changed = json.loads(json.dumps(original))
                changed["payload"][key] = value
                path.write_bytes(OWNER.canonical_json(changed))
                with self.assertRaises(R.ContractError):
                    self.finalize(ObserveOnlyBackend(self.snapshot))
                path.write_bytes(OWNER.canonical_json(original))
        changed = json.loads(json.dumps(original))
        changed["payload"]["recoveredSnapshot"]["bootId"] = "bad"
        path.write_bytes(OWNER.canonical_json(changed))
        with self.assertRaises(R.ContractError):
            self.finalize(ObserveOnlyBackend(self.snapshot))

    def test_intent_binding_mutation_is_rejected(self):
        token = self.arm()
        path = self.side_root / R.INTENT_NAME
        intent = OWNER.parse_canonical(path.read_bytes(), "intent")
        intent["executionClosureSha256"] = "f" * 64
        path.write_bytes(OWNER.canonical_json(intent))
        with self.assertRaises(R.ContractError):
            self.finalize(ObserveOnlyBackend(self.snapshot))
        self.assertTrue(OWNER._active_guard(self.manifest)[0].exists())
        self.assertTrue(token.startswith(R.APPROVAL_PREFIX))

    def test_closure_drift_after_observation_keeps_active(self):
        self.arm()
        original = R._require_closure
        calls = {"count": 0}

        def drift(lease):
            calls["count"] += 1
            if calls["count"] == 3:
                raise R.ContractError("closure drift after observe")
            return original(lease)

        with mock.patch.object(R, "_require_closure", side_effect=drift):
            with self.assertRaises(R.ContractError):
                self.finalize(ObserveOnlyBackend(self.snapshot))
        self.assertTrue(OWNER._active_guard(self.manifest)[0].exists())
        self.assertFalse((self.run_directory / R.RECOVERY_NAME).exists())

    def test_closure_drift_after_publication_keeps_active(self):
        self.arm()
        original = R._require_closure
        calls = {"count": 0}

        def drift(lease):
            calls["count"] += 1
            if calls["count"] == 6:
                raise R.ContractError("closure drift after publication")
            return original(lease)

        with mock.patch.object(R, "_require_closure", side_effect=drift):
            with self.assertRaises(R.ContractError):
                self.finalize(ObserveOnlyBackend(self.snapshot))
        self.assertTrue(OWNER._active_guard(self.manifest)[0].exists())
        self.assertTrue((self.run_directory / R.RECOVERY_NAME).exists())

    def test_cli_output_cardinality(self):
        with mock.patch.object(R, "_require_launch_contract"):
            with mock.patch.object(R, "prepare", return_value="TOKEN"):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    R.main(["prepare"])
        self.assertEqual(output.getvalue(), "TOKEN\n")
        with mock.patch.object(R, "_require_launch_contract"):
            with mock.patch.object(R, "authorize", side_effect=lambda _token: print(R.INSTRUCTION)):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    R.main(["authorize", "--approval", "TOKEN"])
        self.assertEqual(output.getvalue(), R.INSTRUCTION + "\n")
        result = {"b": 1, "a": 2}
        with mock.patch.object(R, "_require_launch_contract"):
            with mock.patch.object(R, "finalize", return_value=result):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    R.main(["finalize", "--operator-attended", "--physical-system-return-confirmed"])
        self.assertEqual(output.getvalue(), json.dumps(result, sort_keys=True) + "\n")
        self.assertEqual(len(output.getvalue().splitlines()), 1)

    def test_real_fixed_python_help_launch_contract(self):
        env = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "LANG": "C", "LC_ALL": "C"}
        result = subprocess.run(
            [R.FIXED_PYTHON, "-B", "-s", "-E", R.FIXED_SCRIPT, "--help"],
            cwd=R.FIXED_CWD,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("{prepare,authorize,finalize}", result.stdout)
        self.assertNotIn("manifest", result.stdout)

    def test_wrong_direct_launch_rejects_before_owner_or_h28_pyc(self):
        pycache = Path(R.FIXED_SCRIPT_DIR) / "__pycache__"
        pyc_paths = (
            pycache / "a90_h28_physical_system_return_reconcile_v1.cpython-314.pyc",
            pycache / "a90_boot_only_f1_minimal_v1.cpython-314.pyc",
        )
        for path in pyc_paths:
            path.unlink(missing_ok=True)
        env = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "LANG": "C", "LC_ALL": "C"}
        no_b = subprocess.run(
            [R.FIXED_PYTHON, "-s", "-E", R.FIXED_SCRIPT, "--help"],
            cwd=R.FIXED_CWD,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        wrong_cwd = subprocess.run(
            [R.FIXED_PYTHON, "-B", "-s", "-E", R.FIXED_SCRIPT, "--help"],
            cwd="/tmp",
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(no_b.returncode, 0)
        self.assertNotEqual(wrong_cwd.returncode, 0)
        self.assertIn("pre-import launch contract", no_b.stderr)
        self.assertIn("pre-import launch contract", wrong_cwd.stderr)
        self.assertTrue(all(not path.exists() for path in pyc_paths))

    def test_launch_contract_rejects_hostile_identity_before_action_or_stdout(self):
        good_path = list(sys.path)
        mode = stat.S_IFREG | 0o600
        good_stat = types.SimpleNamespace(st_mode=mode, st_nlink=1, st_uid=os.getuid(), st_gid=os.getgid())
        cases = (
            ("interpreter", mock.patch.object(sys, "executable", "/bad/python")),
            ("user-site", mock.patch.object(sys, "flags", types.SimpleNamespace(no_user_site=0, ignore_environment=1))),
            ("environment", mock.patch.object(sys, "flags", types.SimpleNamespace(no_user_site=1, ignore_environment=0))),
            ("cwd", mock.patch.object(os, "getcwd", return_value="/bad/cwd")),
            ("argv0", mock.patch.object(sys, "argv", ["relative.py"])),
            ("sys-path", mock.patch.object(sys, "path", ["/bad/path", *good_path[1:]])),
            ("symlink", mock.patch("os.lstat", return_value=types.SimpleNamespace(st_mode=stat.S_IFLNK, st_nlink=1, st_uid=os.getuid(), st_gid=os.getgid()))),
            ("writable", mock.patch("os.lstat", return_value=types.SimpleNamespace(st_mode=stat.S_IFREG | 0o602, st_nlink=1, st_uid=os.getuid(), st_gid=os.getgid()))),
            ("wrong-owner", mock.patch("os.lstat", return_value=types.SimpleNamespace(st_mode=mode, st_nlink=1, st_uid=os.getuid() + 1, st_gid=os.getgid()))),
            ("owner-alias", mock.patch.dict(sys.modules, {"owner_alias": OWNER})),
            ("foreign-owner-alias", mock.patch.dict(sys.modules, {"foreign_owner": types.SimpleNamespace(__file__=R.FIXED_OWNER)})),
        )
        for label, hostile in cases:
            with self.subTest(label=label):
                with hostile:
                    with mock.patch.object(R, "prepare") as action, contextlib.redirect_stdout(io.StringIO()) as output:
                        with self.assertRaises(R.ContractError):
                            R.main(["prepare"])
                action.assert_not_called()
                self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
