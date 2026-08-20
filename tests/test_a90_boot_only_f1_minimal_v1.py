from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py"
)
SPEC = importlib.util.spec_from_file_location("a90_boot_only_f1_minimal_v1", SOURCE)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


class FakeBackend:
    def __init__(self, start: M.Snapshot, flashes=None, observations=None):
        self.preflights = [start]
        self.flashes = list(flashes or [])
        self.observations = list(observations or [])
        self.flash_calls = []

    def preflight(self, _manifest):
        if len(self.preflights) > 1:
            return self.preflights.pop(0)
        return self.preflights[0]

    def flash(self, artifact, *, rollback, timeout_sec):
        self.flash_calls.append((artifact["sha256"], rollback, timeout_sec))
        result = self.flashes.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    def observe(self, _expected, *, timeout_sec):
        del timeout_sec
        result = self.observations.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


class MinimalF1Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.candidate = self.root / "candidate.img"
        self.rollback = self.root / "rollback.img"
        self.candidate.write_bytes(b"candidate")
        self.rollback.write_bytes(b"rollback")
        os.chmod(self.candidate, 0o600)
        os.chmod(self.rollback, 0o600)
        self.manifest = {
            "schema": M.MANIFEST_SCHEMA,
            "capability": M.CAPABILITY,
            "targetProfile": M.TARGET_PROFILE,
            "partition": "boot",
            "runId": "a90-minimal-001",
            "expectedStart": {"version": "old", "build": "old-build"},
            "candidate": self._artifact(self.candidate, "new", "new-build"),
            "rollback": self._artifact(self.rollback, "old", "old-build"),
            "timeouts": {"flashSec": 60, "healthSec": 90},
        }
        self.raw = M.canonical_json(self.manifest)
        self.start = self._snapshot("old", "old-build", receipt=HEX_A)

    def tearDown(self):
        self.temp.cleanup()

    def _artifact(self, path: Path, version: str, build: str):
        raw = path.read_bytes()
        return {
            "path": str(path),
            "size": len(raw),
            "sha256": M.sha256_bytes(raw),
            "version": version,
            "build": build,
        }

    def _snapshot(
        self,
        version: str,
        build: str,
        *,
        boot: str = "boot-one",
        receipt: str = HEX_B,
        healthy: bool = True,
    ):
        return M.Snapshot(
            target_evidence_sha256=HEX_C,
            boot_id=boot,
            version=version,
            build=build,
            healthy=healthy,
            recovery_available=True,
            other_targets_untouched=True,
            receipt_sha256=receipt,
        )

    def _prepare(self, backend=None):
        backend = backend or FakeBackend(self.start)
        run = self.root / "run"
        token = M.prepare(self.raw, self.manifest, run, backend)
        return run, token

    @staticmethod
    def _effect(*, completed=True, quiescent=True, rc=0, receipt=HEX_A):
        return M.EffectResult(rc, completed, quiescent, receipt)

    def test_manifest_accepts_only_exact_boot_contract(self):
        self.assertEqual(M.validate_manifest(self.manifest), self.manifest)
        for field, value in (("partition", "vendor_boot"), ("targetProfile", "OTHER")):
            bad = dict(self.manifest)
            bad[field] = value
            with self.assertRaises(M.ContractError):
                M.validate_manifest(bad)

    def test_manifest_rejects_bool_integer_and_extra_field(self):
        bad = json.loads(json.dumps(self.manifest))
        bad["candidate"]["size"] = True
        with self.assertRaises(M.ContractError):
            M.validate_manifest(bad)
        bad = dict(self.manifest, command="flash")
        with self.assertRaises(M.ContractError):
            M.validate_manifest(bad)

    def test_canonical_parser_rejects_duplicate_and_trailing_newline(self):
        with self.assertRaises(M.ContractError):
            M.parse_canonical(b'{"a":1,"a":1}', "duplicate")
        with self.assertRaises(M.ContractError):
            M.parse_canonical(b'{"a":1}\n', "newline")

    def test_artifact_binding_rejects_symlink(self):
        link = self.root / "link.img"
        link.symlink_to(self.candidate)
        value = self._artifact(self.candidate, "new", "new-build")
        value["path"] = str(link)
        with self.assertRaises(M.ContractError):
            M.BoundArtifact.open(value, "candidate")

    def test_prepare_binds_target_artifacts_and_approval(self):
        run, token = self._prepare()
        records = M.read_records(run)
        prepared = records["00-prepared.json"]["payload"]
        self.assertEqual(prepared["candidate"]["sha256"], self.manifest["candidate"]["sha256"])
        self.assertEqual(prepared["snapshot"]["bootId"], "boot-one")
        self.assertTrue(token.startswith(M.APPROVAL_PREFIX))
        self.assertEqual(M.recovery_decision(run), "PRE_EFFECT_NO_DEVICE_EFFECT")

    def test_manifest_bytes_cannot_authorize_a_different_object(self):
        changed = json.loads(json.dumps(self.manifest))
        changed["candidate"]["version"] = "substituted"
        with self.assertRaisesRegex(M.ContractError, "execution object differ"):
            M.prepare(self.raw, changed, self.root / "run", FakeBackend(self.start))

    def test_success_flashes_candidate_once_and_accepts_fresh_receipt(self):
        run, token = self._prepare()
        backend = FakeBackend(
            self._snapshot("old", "old-build", receipt=HEX_B),
            flashes=[self._effect()],
            observations=[self._snapshot("new", "new-build")],
        )
        result = M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(result["terminal"], "PASS_A90_RESIDENT_INSTALLED")
        self.assertEqual(len(backend.flash_calls), 1)
        self.assertFalse(backend.flash_calls[0][1])
        self.assertEqual(M.recovery_decision(run), "TERMINAL_COMPLETE")

    def test_wrong_approval_causes_no_effect(self):
        run, _token = self._prepare()
        backend = FakeBackend(self.start)
        with self.assertRaises(M.ContractError):
            M.execute(self.raw, self.manifest, run, "wrong", backend)
        self.assertEqual(backend.flash_calls, [])
        self.assertEqual(set(M.read_records(run)), {"00-prepared.json"})

    def test_changed_boot_causes_no_effect(self):
        run, token = self._prepare()
        backend = FakeBackend(self._snapshot("old", "old-build", boot="boot-two"))
        with self.assertRaises(M.ContractError):
            M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(backend.flash_calls, [])

    def test_changed_candidate_causes_no_effect(self):
        run, token = self._prepare()
        self.candidate.write_bytes(b"substitute")
        with self.assertRaises(M.ContractError):
            M.execute(self.raw, self.manifest, run, token, FakeBackend(self.start))

    def test_unhealthy_candidate_rolls_back_once(self):
        run, token = self._prepare()
        backend = FakeBackend(
            self.start,
            flashes=[self._effect(rc=1, completed=False), self._effect()],
            observations=[
                self._snapshot("old", "old-build", healthy=False),
                self._snapshot("old", "old-build"),
            ],
        )
        result = M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(result["terminal"], "NO_PROOF_ROLLED_BACK")
        self.assertEqual([call[1] for call in backend.flash_calls], [False, True])

    def test_observer_failure_rolls_back_instead_of_claiming_success(self):
        run, token = self._prepare()
        backend = FakeBackend(
            self.start,
            flashes=[self._effect(), self._effect()],
            observations=[RuntimeError("observer lost"), self._snapshot("old", "old-build")],
        )
        result = M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(result["terminal"], "NO_PROOF_ROLLED_BACK")
        self.assertEqual([call[1] for call in backend.flash_calls], [False, True])

    def test_unproved_rollback_requires_recovery(self):
        run, token = self._prepare()
        backend = FakeBackend(
            self.start,
            flashes=[self._effect(rc=1, completed=False), self._effect(rc=1, completed=False)],
            observations=[
                self._snapshot("old", "old-build", healthy=False),
                self._snapshot("old", "old-build", healthy=False),
            ],
        )
        result = M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")

    def test_nonquiescent_candidate_does_not_overlap_rollback(self):
        run, token = self._prepare()
        backend = FakeBackend(self.start, flashes=[self._effect(quiescent=False)])
        result = M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertEqual(len(backend.flash_calls), 1)

    def test_second_execute_cannot_replay_candidate(self):
        run, token = self._prepare()
        backend = FakeBackend(
            self.start,
            flashes=[self._effect()],
            observations=[self._snapshot("new", "new-build")],
        )
        M.execute(self.raw, self.manifest, run, token, backend)
        with self.assertRaises(M.ContractError):
            M.execute(self.raw, self.manifest, run, token, backend)

    def test_flash_exception_leaves_candidate_consumed(self):
        run, token = self._prepare()
        backend = FakeBackend(self.start, flashes=[RuntimeError("transport lost")])
        with self.assertRaises(RuntimeError):
            M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(M.recovery_decision(run), "CANDIDATE_CONSUMED_ROLLBACK_ONLY")

    def test_recovery_decisions_cover_rollback_prefixes(self):
        run, _token = self._prepare()
        digest = M.sha256_bytes(self.raw)
        for name in (
            "10-approved.json",
            "20-candidate-intent.json",
            "21-candidate-launched.json",
            "22-candidate-result.json",
            "30-rollback-intent.json",
        ):
            M.publish_record(run, name, M._record(M.RECORD_KINDS[name], digest, {}))
        self.assertEqual(M.recovery_decision(run), "SAME_ROLLBACK_MAY_LAUNCH_ONCE")
        M.publish_record(
            run,
            "31-rollback-launched.json",
            M._record("ROLLBACK_LAUNCHED", digest, {}),
        )
        self.assertEqual(M.recovery_decision(run), "PARK_ROLLBACK_NO_REPLAY")

    def test_journal_rejects_gap_wrong_kind_and_mixed_manifest(self):
        digest = M.sha256_bytes(self.raw)
        for mutation in ("gap", "kind", "manifest"):
            run = self.root / mutation
            run.mkdir(mode=0o700)
            M.publish_record(run, "00-prepared.json", M._record("PREPARED", digest, {}))
            if mutation == "gap":
                M.publish_record(run, "20-candidate-intent.json", M._record("CANDIDATE_INTENT", digest, {}))
            else:
                kind = "WRONG" if mutation == "kind" else "APPROVED"
                sha = HEX_A if mutation == "manifest" else digest
                M.publish_record(run, "10-approved.json", M._record(kind, sha, {}))
            with self.assertRaises(M.ContractError, msg=mutation):
                M.read_records(run)

    def test_live_cli_is_hard_disabled(self):
        self.assertFalse(M.LIVE_EXECUTION_ENABLED)
        with self.assertRaisesRegex(M.ContractError, "live execution is disabled"):
            M.main(["execute", str(self.root / "manifest.json"), str(self.root / "run")])


class MinimalSurfaceTest(unittest.TestCase):
    def test_minimal_source_and_test_surface_stays_bounded(self):
        design = ROOT / "docs/plans/A90_BOOT_ONLY_F1_MINIMAL_V1_DESIGN_2026-08-20.md"
        self.assertLessEqual(len(SOURCE.read_text().splitlines()), 900)
        self.assertLessEqual(len(Path(__file__).read_text().splitlines()), 400)
        self.assertLessEqual(len(design.read_text().splitlines()), 180)

    def test_retired_owner_runtime_is_not_an_active_dependency(self):
        retired = (
            "a90_boot_only_f1_owner_v1.py",
            "a90_boot_only_f1_contract_v1.py",
            "a90_boot_only_f1_runtime_v1.py",
            "a90_boot_only_f1_observer_v1.py",
            "a90_boot_only_f1_source_package_v1.py",
            "a90_boot_only_f1_runtime_qualification_v1.json",
            "a90_boot_only_f1_command_bootstrap.py",
            "a90_boot_only_f1_helper_bootstrap.py",
        )
        active_files = (
            SOURCE,
            ROOT / "docs/plans/A90_BOOT_ONLY_F1_MINIMAL_V1_DESIGN_2026-08-20.md",
        )
        active_text = "\n".join(path.read_text() for path in active_files)
        for name in retired:
            self.assertNotIn(name, active_text)


if __name__ == "__main__":
    unittest.main()
