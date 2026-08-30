"""Host-only constraints for the fixed H38 run-01 park closer."""

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/server-distro/a90_h38_pre_candidate_recovery_park_close_v1.py"


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("a90_h38_park_close", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class H38ParkCloseTest(unittest.TestCase):
    def test_fixed_scope_and_exact_consumed_prefix(self) -> None:
        module = load_module()
        self.assertEqual(module.RUN_ID, "a90-h38-f1-20260829-01")
        self.assertEqual(module.MANIFEST_SHA256, "f4c6175d92b71ff52089ff4bbdc507643cccd751fac2c00ec93d9dcb5eff4255")
        self.assertEqual(
            set(module.JOURNAL_HASHES),
            {"00-prepared.json", "10-approved.json", "11-recovery-transition-intent.json", "13-recovery-transition-parked.json"},
        )
        self.assertEqual(len(module.LOG_HASHES), 22)

    def test_wrapper_configures_read_only_engine(self) -> None:
        module = load_module()
        self.assertEqual(module.engine.CAPABILITY, module.CAPABILITY)
        self.assertEqual(module.engine.RESULT_SCHEMA, module.RESULT_SCHEMA)
        self.assertIs(module.engine.REQUIRE_INTENT_FOR_RESULT, True)
        source = module.ENGINE_PATH.read_text(encoding="utf-8")
        self.assertIn("backend.observe", source)
        self.assertIn("_require_candidate_guard_absent", source)
        self.assertNotIn("backend.flash", source)
        self.assertNotIn("/usr/bin/adb", source)
        self.assertNotIn("while True", source)
        execute = source[source.index("def execute(") : source.index("def main(")]
        self.assertLess(
            execute.index("publish_observation_intent("),
            execute.index("backend.observe"),
        )
        self.assertIn("observation intent is consumed without a result; park", execute)
        self.assertIn('payload["observationIntentSha256"] = intent_sha', execute)

    def test_closure_binds_wrapper_test_contract_and_owner(self) -> None:
        module = load_module()
        self.assertEqual(len(module.closure_sha256()), 64)
        self.assertEqual(module.engine.SELF_REL, module.SELF_REL)
        self.assertEqual(module.engine.TEST_REL, module.TEST_REL)
        self.assertEqual(module.engine.EXTRA_CLOSURE_RELS, (module.ENGINE_REL,))
        self.assertEqual(
            module.ENGINE_PATH,
            module.owner.REPO_ROOT / module.ENGINE_REL,
        )

    def test_closure_is_sensitive_to_execution_engine_bytes(self) -> None:
        module = load_module()
        original = module.owner.REPO_ROOT
        engine_bytes = module.ENGINE_PATH.read_bytes()
        with tempfile.TemporaryDirectory() as name:
            fake_root = Path(name)
            for relative in (
                module.SELF_REL,
                module.TEST_REL,
                module.engine.CONTRACT_REL,
                module.ENGINE_REL,
            ):
                target = fake_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((module.owner.REPO_ROOT / relative).read_bytes())
            module.engine.owner.REPO_ROOT = fake_root
            try:
                with mock.patch.object(
                    module.engine.owner, "execution_closure_sha256", return_value="0" * 64
                ):
                    before = module.closure_sha256()
                    (fake_root / module.ENGINE_REL).write_bytes(engine_bytes + b"\n")
                    after = module.closure_sha256()
            finally:
                module.engine.owner.REPO_ROOT = original
            self.assertNotEqual(before, after)

    def test_consumed_intent_without_result_never_constructs_observer(self) -> None:
        module = load_module()
        engine = module.engine
        manifest = {"qualification": {"review": {"sha256": "3" * 64}}}
        manifest_raw = b"fixed-manifest"
        review_sha = "4" * 64
        closure = "5" * 64
        approval = (
            engine.APPROVAL_PREFIX
            + __import__("hashlib").sha256(manifest_raw).hexdigest()
            + ":" + review_sha + ":" + closure
        )
        with tempfile.TemporaryDirectory() as name:
            side = Path(name) / "side"
            side.mkdir(mode=0o700)
            (side / "observation-intent.json").write_text("consumed", encoding="utf-8")
            with (
                mock.patch.object(engine, "SIDE_ROOT", side),
                mock.patch.object(engine, "RESULT", side / "result.json"),
                mock.patch.object(engine, "fixed_inputs", return_value=(manifest_raw, manifest)),
                mock.patch.object(engine, "review_lease", return_value=(b"review", review_sha)),
                mock.patch.object(engine, "closure_sha256", return_value=closure),
                mock.patch.object(engine.adapter, "HostRunner") as host_runner,
            ):
                with self.assertRaisesRegex(engine.CloseError, "consumed without a result"):
                    engine.execute(approval)
                host_runner.assert_not_called()

    def test_result_without_required_intent_never_releases_guard(self) -> None:
        module = load_module()
        engine = module.engine
        manifest = {"qualification": {"review": {"sha256": "3" * 64}}}
        manifest_raw = b"fixed-manifest"
        review_sha = "4" * 64
        closure = "5" * 64
        approval = (
            engine.APPROVAL_PREFIX
            + __import__("hashlib").sha256(manifest_raw).hexdigest()
            + ":" + review_sha + ":" + closure
        )
        with tempfile.TemporaryDirectory() as name:
            side = Path(name) / "side"
            side.mkdir(mode=0o700)
            result = side / "result.json"
            result.write_text("present", encoding="utf-8")
            with (
                mock.patch.object(engine, "SIDE_ROOT", side),
                mock.patch.object(engine, "RESULT", result),
                mock.patch.object(engine, "fixed_inputs", return_value=(manifest_raw, manifest)),
                mock.patch.object(engine, "review_lease", return_value=(b"review", review_sha)),
                mock.patch.object(engine, "closure_sha256", return_value=closure),
                mock.patch.object(engine.owner, "_release_active_guard") as release,
            ):
                with self.assertRaisesRegex(engine.CloseError, "without required observation intent"):
                    engine.execute(approval)
                release.assert_not_called()


if __name__ == "__main__":
    unittest.main()
