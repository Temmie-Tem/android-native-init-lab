"""Host-only constraints for the exact H41 run-01 park closer."""

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/server-distro/a90_h41_pre_candidate_recovery_park_close_v1.py"


def load_module():
    sys.path.insert(0, str(SCRIPT.parent))
    spec = importlib.util.spec_from_file_location("a90_h41_park_close", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class H41ParkCloseTests(unittest.TestCase):
    def test_exact_consumed_prefix_and_absent_candidate_guard(self) -> None:
        module = load_module()
        self.assertEqual(module.RUN_ID, "a90-h41-f1-20260830-01")
        self.assertEqual(
            module.MANIFEST_SHA256,
            "9e36c570095f1b383c1c3bc16367eecd6d211173ddc27a8c6142dde3d8569d43",
        )
        self.assertEqual(
            tuple(module.JOURNAL_HASHES),
            (
                "00-prepared.json", "10-approved.json",
                "11-recovery-transition-intent.json",
                "13-recovery-transition-parked.json",
            ),
        )
        self.assertEqual(len(module.LOG_HASHES), 22)

    def test_wrapper_configures_read_only_one_shot_engine(self) -> None:
        module = load_module()
        engine = module.engine
        self.assertEqual(engine.CAPABILITY, module.CAPABILITY)
        self.assertEqual(engine.REVIEW_DATE, "2026-08-30")
        self.assertIs(engine.REQUIRE_INTENT_FOR_RESULT, True)
        source = module.ENGINE_PATH.read_text(encoding="utf-8")
        self.assertIn("backend.observe", source)
        self.assertIn("_require_candidate_guard_absent", source)
        self.assertNotIn("backend.flash", source)
        self.assertNotIn("/usr/bin/adb", source)
        execute = source[source.index("def execute(") : source.index("def main(")]
        self.assertLess(execute.index("publish_observation_intent("), execute.index("backend.observe"))
        self.assertIn("observation intent is consumed without a result; park", execute)

    def test_closure_binds_wrapper_test_contract_and_engine(self) -> None:
        module = load_module()
        self.assertRegex(module.closure_sha256(), r"^[0-9a-f]{64}$")
        self.assertEqual(module.engine.SELF_REL, module.SELF_REL)
        self.assertEqual(module.engine.TEST_REL, module.TEST_REL)
        self.assertEqual(
            module.engine.EXTRA_CLOSURE_RELS,
            (module.ENGINE_REL, module.REPORT_REL),
        )

    def test_consumed_observation_never_constructs_observer(self) -> None:
        module = load_module()
        engine = module.engine
        manifest = {"qualification": {"review": {"sha256": "3" * 64}}}
        manifest_raw = b"fixed-manifest"
        review_sha, closure = "4" * 64, "5" * 64
        approval = engine.APPROVAL_PREFIX + __import__("hashlib").sha256(manifest_raw).hexdigest() + ":" + review_sha + ":" + closure
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


if __name__ == "__main__":
    unittest.main()
