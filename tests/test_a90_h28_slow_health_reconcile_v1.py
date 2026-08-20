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
ADAPTER = load("a90_boot_only_f1_adapter_v1")
PRIOR = load("a90_h28_physical_system_return_reconcile_v1")
R = load("a90_h28_slow_health_reconcile_v1")


class FakeObserver:
    def __init__(self, snapshot=None, error=None):
        self.snapshot = snapshot
        self.error = error
        self.observe_calls = 0

    def observe(self, *_args, **_kwargs):
        self.observe_calls += 1
        if self.error:
            raise self.error
        return self.snapshot


class SlowHealthTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.run_root = base / "runs"
        self.run_root.mkdir(mode=0o700)
        self.run_directory = self.run_root / R.RUN_ID
        self.run_directory.mkdir(mode=0o700)
        self.prior_side_root = base / "prior-sidecar"
        self.prior_side_root.mkdir(mode=0o700)
        self.side_root = base / "slow-sidecar"
        self.review_path = base / "slow-review.json"
        self.first_logs = base / "first-observer-logs"
        self.first_logs.mkdir(mode=0o700)
        self.slow_logs = base / "slow-observer-logs"
        self.old = {
            "run_root": OWNER.RUN_ROOT,
            "prior_side": R.PRIOR_SIDE_ROOT,
            "side": R.SIDE_ROOT,
            "review": R.CURRENT_REVIEW_PATH,
            "first_logs": R.FIRST_LOG_DIRECTORY,
            "slow_logs": R.SLOW_LOG_DIRECTORY,
            "manifest_sha": R.MANIFEST_SHA256,
            "terminal_sha": R.TERMINAL_SHA256,
            "prior_physical": R.PRIOR_PHYSICAL_INTENT_SHA256,
            "prior_observation": R.PRIOR_OBSERVATION_INTENT_SHA256,
            "incident": R.INCIDENT_RECORD_SHA256,
            "active": R.ACTIVE_GUARD_SHA256,
            "candidate": R.CANDIDATE_GUARD_SHA256,
        }
        OWNER.RUN_ROOT = self.run_root
        R.PRIOR_SIDE_ROOT = self.prior_side_root
        R.SIDE_ROOT = self.side_root
        R.CURRENT_REVIEW_PATH = self.review_path
        R.FIRST_LOG_DIRECTORY = self.first_logs
        R.SLOW_LOG_DIRECTORY = self.slow_logs
        self.manifest = {
            "runId": R.RUN_ID,
            "candidate": {"sha256": "1" * 64},
            "rollback": {
                "sha256": OWNER.V2321_ROLLBACK_SHA256,
                "version": OWNER.V2321_ROLLBACK_VERSION,
                "build": OWNER.V2321_ROLLBACK_BUILD,
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
        self._write_incident()
        self._write_guards()
        self._write_prior_sidecar()
        self._write_first_logs()
        self._write_review()
        self.snapshot = OWNER.Snapshot(
            target_evidence_sha256="3" * 64,
            boot_id="01234567-89ab-cdef-0123-456789abcdef",
            version=OWNER.V2321_ROLLBACK_VERSION,
            build=OWNER.V2321_ROLLBACK_BUILD,
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
        OWNER.RUN_ROOT = self.old["run_root"]
        R.PRIOR_SIDE_ROOT = self.old["prior_side"]
        R.SIDE_ROOT = self.old["side"]
        R.CURRENT_REVIEW_PATH = self.old["review"]
        R.FIRST_LOG_DIRECTORY = self.old["first_logs"]
        R.SLOW_LOG_DIRECTORY = self.old["slow_logs"]
        R.MANIFEST_SHA256 = self.old["manifest_sha"]
        R.TERMINAL_SHA256 = self.old["terminal_sha"]
        R.PRIOR_PHYSICAL_INTENT_SHA256 = self.old["prior_physical"]
        R.PRIOR_OBSERVATION_INTENT_SHA256 = self.old["prior_observation"]
        R.INCIDENT_RECORD_SHA256 = self.old["incident"]
        R.ACTIVE_GUARD_SHA256 = self.old["active"]
        R.CANDIDATE_GUARD_SHA256 = self.old["candidate"]

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
            record = OWNER._record(OWNER.RECORD_KINDS[name], R.MANIFEST_SHA256, payloads.get(name, {}))
            path = self.run_directory / name
            path.write_bytes(OWNER.canonical_json(record))
            path.chmod(0o600)
        records = OWNER.read_records(self.run_directory)
        R.INCIDENT_RECORD_SHA256 = {name: R._json_sha(record) for name, record in records.items()}

    def _write_guards(self):
        for path, raw, role in (
            (*OWNER._active_guard(self.manifest), "active"),
            (*OWNER._candidate_guard(self.manifest), "candidate"),
        ):
            path.write_bytes(raw)
            path.chmod(0o600)
            if role == "active":
                R.ACTIVE_GUARD_SHA256 = R._sha(raw)
            else:
                R.CANDIDATE_GUARD_SHA256 = R._sha(raw)

    def _write_prior_sidecar(self):
        physical = {
            "schema": PRIOR.INTENT_SCHEMA,
            "capability": PRIOR.CAPABILITY,
            "runId": R.RUN_ID,
            "manifestSha256": PRIOR.MANIFEST_SHA256,
            "terminalSha256": PRIOR.TERMINAL_SHA256,
            "currentReviewSha256": "a" * 64,
            "executionClosureSha256": "b" * 64,
            "approvalSha256": "c" * 64,
        }
        physical_raw = OWNER.canonical_json(physical)
        observation = {
            "schema": PRIOR.OBSERVATION_SCHEMA,
            "capability": PRIOR.CAPABILITY,
            "runId": R.RUN_ID,
            "manifestSha256": PRIOR.MANIFEST_SHA256,
            "terminalSha256": PRIOR.TERMINAL_SHA256,
            "physicalSystemReturnIntentSha256": R._sha(physical_raw),
            "currentReviewSha256": "a" * 64,
            "executionClosureSha256": "b" * 64,
            "operatorAttended": True,
            "physicalSystemReturnConfirmed": True,
        }
        for name, value in ((PRIOR.INTENT_NAME, physical), (PRIOR.OBSERVATION_INTENT_NAME, observation)):
            path = self.prior_side_root / name
            path.write_bytes(OWNER.canonical_json(value))
            path.chmod(0o600)
        R.PRIOR_PHYSICAL_INTENT_SHA256 = R._sha((self.prior_side_root / PRIOR.INTENT_NAME).read_bytes())
        R.PRIOR_OBSERVATION_INTENT_SHA256 = R._sha((self.prior_side_root / PRIOR.OBSERVATION_INTENT_NAME).read_bytes())

    def _write_first_logs(self):
        version = {
            "begin": {"seq": 1, "cmd": "version", "argc": 1, "flags": "0x0"},
            "end": {"cmd": "version", "rc": 0, "status": "ok"},
            "rc": 0,
            "status": "ok",
            "trust": "A90P1_V1_STRUCTURAL_ONLY",
            "text": "version: 0.9.285 build=v2321-usb-clean-identity-rodata",
        }
        values = {"003-version.stdout": OWNER.canonical_json(version)}
        for name, (size, _digest) in R.FIRST_LOG_HASHES.items():
            if name not in values:
                values[name] = b"" if size == 0 else b"x" * size
        hashes = {}
        for name, raw in values.items():
            path = self.first_logs / name
            path.write_bytes(raw)
            path.chmod(0o600)
            hashes[name] = (len(raw), R._sha(raw))
        R.FIRST_LOG_HASHES = hashes

    def _write_review(self, **changes):
        review = {
            "schema": R.REVIEW_SCHEMA,
            "capability": R.CAPABILITY,
            "runId": R.RUN_ID,
            "manifestSha256": R.MANIFEST_SHA256,
            "terminalSha256": R.TERMINAL_SHA256,
            "priorPhysicalIntentSha256": R.PRIOR_PHYSICAL_INTENT_SHA256,
            "priorObservationIntentSha256": R.PRIOR_OBSERVATION_INTENT_SHA256,
            "executionClosureSha256": R.execution_closure_sha256(),
            "verdict": "PASS_GO",
            "findings": {"high": [], "medium": [], "low": []},
            "contacts": {"device": 0, "dev": 0, "usb": 0, "network": 0, "workspacePrivate": 0, "otherTargets": 0, "writes": 0},
            "liveAuthority": False,
        }
        review.update(changes)
        self.review_path.write_bytes(OWNER.canonical_json(review))
        self.review_path.chmod(0o600)

    @contextlib.contextmanager
    def fixed(self, observer=None):
        with mock.patch.object(R, "_load_manifest", return_value=(self.manifest_raw, self.manifest)):
            if observer is None:
                yield
            else:
                with mock.patch.object(R, "SlowObserver", return_value=observer):
                    yield

    def prepare(self):
        with self.fixed():
            return R.prepare()

    def execute(self, approval, observer=None):
        with self.fixed(observer):
            return R.execute(approval)

    def arm(self):
        token = self.prepare()
        return token, self.execute(token, FakeObserver(self.snapshot))

    def test_real_fixed_python_help_launch_contract(self):
        for path in (R.FIXED_SCRIPT, R.FIXED_OWNER, R.FIXED_ADAPTER, R.FIXED_PRIOR):
            os.chmod(path, 0o600)
        env = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "LANG": "C", "LC_ALL": "C"}
        result = subprocess.run([R.FIXED_PYTHON, "-B", "-s", "-E", R.FIXED_SCRIPT, "--help"], cwd=R.FIXED_CWD, env=env, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("{prepare,execute}", result.stdout)
        self.assertNotIn("manifest", result.stdout)

    def test_wrong_direct_launch_no_b_or_wrong_cwd_fails_before_owner(self):
        env = {"PATH": "/usr/bin:/bin", "HOME": "/nonexistent", "LANG": "C", "LC_ALL": "C"}
        for argv, cwd in (([R.FIXED_PYTHON, "-s", "-E", R.FIXED_SCRIPT, "--help"], R.FIXED_CWD), ([R.FIXED_PYTHON, "-B", "-s", "-E", R.FIXED_SCRIPT, "--help"], "/tmp")):
            result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("pre-import", result.stderr)

    def test_prepare_is_write_free_and_binds_prior_inputs(self):
        token = self.prepare()
        self.assertTrue(token.startswith(R.APPROVAL_PREFIX))
        self.assertFalse(self.side_root.exists())

    def test_wrong_approval_is_rejected_without_sidecar(self):
        self.prepare()
        with self.assertRaises(R.ContractError):
            self.execute(R.APPROVAL_PREFIX + "0" * 64)
        self.assertFalse(self.side_root.exists())

    def test_prior_sidecar_drift_is_rejected(self):
        path = self.prior_side_root / PRIOR.INTENT_NAME
        value = OWNER.parse_canonical(path.read_bytes(), "prior")
        value["approvalSha256"] = "d" * 64
        path.write_bytes(OWNER.canonical_json(value))
        with self.assertRaises(R.ContractError):
            self.prepare()

    def test_first_observer_log_drift_is_rejected(self):
        path = self.first_logs / "001-usb-inventory.stdout"
        path.write_bytes(b"drift")
        with self.assertRaises(R.ContractError):
            self.prepare()

    def test_first_selftest_nonempty_drift_is_rejected(self):
        path = self.first_logs / "004-selftest.stdout"
        path.write_bytes(b"unexpected")
        with self.assertRaises(R.ContractError):
            self.prepare()

    def test_journal_and_guard_drift_are_rejected(self):
        path = self.run_directory / "22-candidate-result.json"
        value = OWNER.parse_canonical(path.read_bytes(), "record")
        value["payload"]["changed"] = True
        path.write_bytes(OWNER.canonical_json(value))
        with self.assertRaises(R.ContractError):
            self.prepare()
        self._write_incident(); self._write_guards()
        active, _ = OWNER._active_guard(self.manifest)
        active.unlink()
        with self.assertRaises(R.ContractError):
            self.prepare()

    def test_missing_candidate_guard_is_rejected(self):
        candidate, _ = OWNER._candidate_guard(self.manifest)
        candidate.unlink()
        with self.assertRaises(R.ContractError):
            self.prepare()

    def test_review_findings_contacts_live_authority_and_closure_drift(self):
        cases = (
            {"findings": {"high": ["x"], "medium": [], "low": []}},
            {"contacts": {"device": 1, "dev": 0, "usb": 0, "network": 0, "workspacePrivate": 0, "otherTargets": 0, "writes": 0}},
            {"liveAuthority": True},
            {"executionClosureSha256": "f" * 64},
        )
        for changes in cases:
            with self.subTest(changes=changes):
                self._write_review(**changes)
                with self.assertRaises(R.ContractError):
                    self.prepare()
                self._write_review()

    def test_execute_writes_one_slow_intent_and_observes_once(self):
        token = self.prepare()
        observer = FakeObserver(self.snapshot)
        result = self.execute(token, observer)
        self.assertEqual(observer.observe_calls, 1)
        self.assertTrue((self.side_root / R.INTENT_NAME).is_file())
        self.assertEqual(result["slowHealthIntentSha256"], R._sha((self.side_root / R.INTENT_NAME).read_bytes()))
        self.assertFalse(OWNER._active_guard(self.manifest)[0].exists())
        self.assertTrue(OWNER._candidate_guard(self.manifest)[0].exists())

    def test_failed_first_session_parks_without_second_observer(self):
        token = self.prepare()
        first = FakeObserver(error=RuntimeError("slow observer"))
        with self.assertRaises(RuntimeError):
            self.execute(token, first)
        second = FakeObserver(self.snapshot)
        with self.assertRaises(R.ContractError):
            self.execute(token, second)
        self.assertEqual(second.observe_calls, 0)
        self.assertTrue(OWNER._active_guard(self.manifest)[0].exists())

    def test_wrong_health_consumes_session(self):
        token = self.prepare()
        wrong = dataclasses.replace(self.snapshot, healthy=False)
        with self.assertRaises(R.ContractError):
            self.execute(token, FakeObserver(wrong))
        second = FakeObserver(self.snapshot)
        with self.assertRaises(R.ContractError):
            self.execute(token, second)
        self.assertEqual(second.observe_calls, 0)

    def test_wrong_version_or_other_target_consumes_session(self):
        for wrong in (
            dataclasses.replace(self.snapshot, version="wrong"),
            dataclasses.replace(self.snapshot, other_targets_untouched=False),
        ):
            with self.subTest(wrong=wrong):
                token = self.prepare()
                with self.assertRaises(R.ContractError):
                    self.execute(token, FakeObserver(wrong))
                second = FakeObserver(self.snapshot)
                with self.assertRaises(R.ContractError):
                    self.execute(token, second)
                self.assertEqual(second.observe_calls, 0)
                (self.side_root / R.INTENT_NAME).unlink()
                self.side_root.rmdir()

    def test_existing_slow_intent_without_41_parks_before_observer(self):
        token = self.prepare()
        with self.assertRaises(RuntimeError):
            self.execute(token, FakeObserver(error=RuntimeError("first")))

    def test_observer_command_argv_is_slow_and_closed(self):
        observer = R.SlowObserver.__new__(R.SlowObserver)
        observer._json_command = mock.Mock(return_value={})
        commands = (["version"], ["selftest"], ["status"], ["cat", "/proc/sys/kernel/random/boot_id"])
        for command in commands:
            observer._a90ctl("fixed", list(command), 15)
            argv = observer._json_command.call_args.args[1]
            self.assertIn("--input-mode", argv)
            self.assertEqual(argv[argv.index("--input-mode") + 1], "slow")
            self.assertEqual(list(argv[argv.index("--") + 1:]), list(command))
            self.assertNotIn("--retry-unsafe", argv)
            self.assertNotIn("flash", argv)

    def test_observer_rejects_truncated_or_no_end_receipt(self):
        class Runner:
            def run(self, *_args):
                return ADAPTER.CommandResult(0, b"truncated", b"", True)
        observer = R.SlowObserver.__new__(R.SlowObserver)
        observer.runner = Runner()
        with self.assertRaises(ADAPTER.ContractError):
            observer._json_command("truncated", ("fixed",), 1)

    def test_observer_effect_method_is_forbidden(self):
        observer = R.SlowObserver.__new__(R.SlowObserver)
        with self.assertRaises(R.ContractError):
            observer.flash(None)

    def test_slow_intent_mutation_is_rejected_before_observer(self):
        token = self.prepare()
        with self.assertRaises(RuntimeError):
            self.execute(token, FakeObserver(error=RuntimeError("consume")))
        path = self.side_root / R.INTENT_NAME
        value = OWNER.parse_canonical(path.read_bytes(), "intent")
        value["executionClosureSha256"] = "f" * 64
        path.write_bytes(OWNER.canonical_json(value))
        observer = FakeObserver(self.snapshot)
        with self.assertRaises(R.ContractError):
            self.execute(token, observer)
        self.assertEqual(observer.observe_calls, 0)

    def test_slow_sidecar_extra_and_partial_states_reject(self):
        self.prepare()
        self.side_root.mkdir(mode=0o700)
        (self.side_root / "extra").write_bytes(b"x")
        with self.assertRaises(R.ContractError):
            self.prepare()
        self.side_root = Path(self.temp.name) / "partial-sidecar"
        R.SIDE_ROOT = self.side_root
        self.prepare()
        self.side_root.mkdir(mode=0o700)
        (self.side_root / R.INTENT_NAME).write_bytes(b"partial")
        with self.assertRaises(R.ContractError):
            self.execute("unused")

    def test_publication_failure_keeps_both_guards(self):
        token = self.prepare()
        with mock.patch.object(OWNER, "publish_record", side_effect=R.ContractError("publish")):
            with self.assertRaises(R.ContractError):
                self.execute(token, FakeObserver(self.snapshot))
        self.assertTrue(OWNER._active_guard(self.manifest)[0].exists())
        self.assertTrue(OWNER._candidate_guard(self.manifest)[0].exists())

    def test_readback_failure_keeps_both_guards(self):
        token = self.prepare()
        original = OWNER.publish_record

        def drift(directory, name, record):
            original(directory, name, record)
            value = OWNER.parse_canonical((directory / name).read_bytes(), name)
            value["payload"]["deviceEffectCount"] = 1
            (directory / name).write_bytes(OWNER.canonical_json(value))

        with mock.patch.object(OWNER, "publish_record", side_effect=drift):
            with self.assertRaises(R.ContractError):
                self.execute(token, FakeObserver(self.snapshot))
        self.assertTrue(OWNER._active_guard(self.manifest)[0].exists())

    def test_closure_drift_after_intent_before_observer_keeps_session_consumed(self):
        token = self.prepare()
        original = R._require_closure
        calls = {"count": 0}

        def drift(lease):
            calls["count"] += 1
            if calls["count"] == 3:
                raise R.ContractError("closure drift after slow intent")
            return original(lease)

        with mock.patch.object(R, "_require_closure", side_effect=drift):
            with self.assertRaises(R.ContractError):
                self.execute(token, FakeObserver(self.snapshot))
        self.assertTrue((self.side_root / R.INTENT_NAME).exists())
        observer = FakeObserver(self.snapshot)
        with self.assertRaises(R.ContractError):
            self.execute(token, observer)
        self.assertEqual(observer.observe_calls, 0)

    def test_exact_41_active_present_parks_without_observer(self):
        token = self.prepare()
        with mock.patch.object(OWNER, "_release_active_guard", side_effect=R.ContractError("cut")):
            with self.assertRaises(R.ContractError):
                self.execute(token, FakeObserver(self.snapshot))
        observer = FakeObserver(self.snapshot)
        with self.assertRaises(R.ContractError):
            self.execute(token, observer)
        self.assertEqual(observer.observe_calls, 0)

    def test_exact_41_active_absent_is_idempotent_without_observer(self):
        token = self.prepare()
        self.execute(token, FakeObserver(self.snapshot))
        observer = FakeObserver(self.snapshot)
        result = self.execute(token, observer)
        self.assertEqual(observer.observe_calls, 0)
        self.assertEqual(result["decision"], "V2321_HEALTHY_AFTER_SLOW_INPUT_OBSERVER_REPAIR")

    def test_payload_replay_counts_and_snapshot_mutations_reject(self):
        token = self.prepare()
        self.execute(token, FakeObserver(self.snapshot))
        path = self.run_directory / R.RECOVERY_NAME
        original = OWNER.parse_canonical(path.read_bytes(), "recovery")
        for key, value in (("candidateReplay", True), ("rollbackReplay", True), ("deviceEffectCount", 1), ("priorObserverOutcome", "PROVED"), ("slowHealthIntentSha256", "f" * 64)):
            changed = json.loads(json.dumps(original)); changed["payload"][key] = value
            path.write_bytes(OWNER.canonical_json(changed))
            with self.assertRaises(R.ContractError):
                self.execute(token, FakeObserver(self.snapshot))
            path.write_bytes(OWNER.canonical_json(original))
        changed = json.loads(json.dumps(original)); changed["payload"]["recoveredSnapshot"]["bootId"] = "bad"
        path.write_bytes(OWNER.canonical_json(changed))
        with self.assertRaises(R.ContractError):
            self.execute(token, FakeObserver(self.snapshot))

    def test_cli_output_cardinality(self):
        with mock.patch.object(R, "_post_import_launch_contract"):
            with mock.patch.object(R, "prepare", return_value="TOKEN"):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    R.main(["prepare"])
        self.assertEqual(output.getvalue(), "TOKEN\n")
        result = {"b": 1, "a": 2}
        with mock.patch.object(R, "_post_import_launch_contract"):
            with mock.patch.object(R, "execute", return_value=result):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    R.main(["execute", "--approval", "TOKEN"])
        self.assertEqual(output.getvalue(), json.dumps(result, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
