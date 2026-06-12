"""Regression tests for the a90harness.runner module supervisor."""

import sys
import tempfile
import types
import unittest
from pathlib import Path

from _loader import load_harness

broker_stub = types.ModuleType("a90_broker")
broker_stub.PROTO = "A90B1"
broker_stub.connect_and_call = lambda *_args, **_kwargs: {}
sys.modules.setdefault("a90_broker", broker_stub)

runner = load_harness("runner")
module_contract = load_harness("module")


class FakeStore:
    def __init__(self, run_dir):
        self.run_dir = Path(run_dir)
        self.json_writes = []

    def mkdir(self, *parts):
        path = self.run_dir.joinpath(*parts)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_json(self, name, payload):
        self.json_writes.append((name, payload))


class SuccessfulModule(module_contract.TestModule):
    name = "successful"
    description = "successful module"
    cycle_label = "vtest-success"

    def __init__(self):
        self.events = []

    def prepare(self, ctx):
        self.events.append(("prepare", ctx.profile, ctx.expect_version, ctx.host, ctx.port, ctx.timeout))
        return module_contract.StepResult("prepare", True, "prepared", 0.0)

    def run(self, ctx):
        self.events.append(("run", str(ctx.repo_root), ctx.client))
        (ctx.module_dir / "artifact.txt").write_text("artifact", encoding="utf-8")
        return module_contract.StepResult("run", True, "ran", 0.0)

    def cleanup(self, ctx):
        self.events.append(("cleanup", ctx.module_dir.name))
        return module_contract.StepResult("cleanup", True, "cleaned", 0.0)

    def verify(self, ctx):
        self.events.append(("verify", ctx.module_dir.exists()))
        return module_contract.StepResult("verify", True, "verified", 0.0)


class SkippedThenFailingModule(module_contract.TestModule):
    name = "skipped-failing"

    def prepare(self, ctx):
        return module_contract.StepResult("prepare", True, "skipped setup", 0.0, skipped=True)

    def run(self, ctx):
        raise RuntimeError("run failed")

    def cleanup(self, ctx):
        return module_contract.StepResult("cleanup", True, "cleaned", 0.0)

    def verify(self, ctx):
        return module_contract.StepResult("verify", True, "verified", 0.0)


class ModuleRunnerTests(unittest.TestCase):
    def build_runner(self, store, client="client"):
        return runner.ModuleRunner(
            repo_root=Path("/repo"),
            store=store,
            client=client,
            expect_version="A90 test",
            host="127.0.0.1",
            port=54321,
            timeout=12.5,
        )

    def test_run_successful_module_writes_outcome_and_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FakeStore(tmp)
            test_module = SuccessfulModule()

            outcome, observer_summary = self.build_runner(store).run(
                test_module,
                profile="full",
                observer_duration_sec=0.0,
            )

            self.assertIsNone(observer_summary)
            self.assertTrue(outcome.ok)
            self.assertFalse(outcome.skipped)
            self.assertEqual([step.name for step in outcome.steps], ["prepare", "run", "cleanup", "verify"])
            self.assertEqual(outcome.artifacts, ["modules/successful/artifact.txt"])
            self.assertEqual(outcome.metadata["description"], "successful module")
            self.assertEqual(outcome.metadata["cycle_label"], "vtest-success")
            self.assertGreaterEqual(outcome.metadata["duration_sec"], 0)
            self.assertEqual(
                test_module.events,
                [
                    ("prepare", "full", "A90 test", "127.0.0.1", 54321, 12.5),
                    ("run", "/repo", "client"),
                    ("cleanup", "successful"),
                    ("verify", True),
                ],
            )
            self.assertEqual(store.json_writes[0][0], "modules/successful/module-result.json")
            self.assertTrue(store.json_writes[0][1]["ok"])

    def test_step_failure_is_captured_and_cleanup_verify_still_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FakeStore(tmp)

            outcome, observer_summary = self.build_runner(store).run(SkippedThenFailingModule())

            self.assertIsNone(observer_summary)
            self.assertFalse(outcome.ok)
            self.assertTrue(outcome.skipped)
            self.assertEqual([step.name for step in outcome.steps], ["prepare", "run", "cleanup", "verify"])
            run_step = outcome.steps[1]
            self.assertFalse(run_step.ok)
            self.assertEqual(run_step.detail, "RuntimeError: run failed")
            self.assertEqual(run_step.error, "RuntimeError: run failed")
            written = store.json_writes[0][1]
            self.assertEqual([step["name"] for step in written["failed_steps"]], ["run"])

    def test_observer_summary_is_optional_and_can_fail_overall_outcome(self):
        calls = []

        def fake_run_observer(client, store, *, duration_sec, interval_sec):
            calls.append((client, store, duration_sec, interval_sec))
            return runner.ObserverSummary(
                ok=False,
                cycles=1,
                samples=7,
                failures=1,
                duration_sec=0.5,
                jsonl="/fake/observer.jsonl",
            )

        original = runner.run_observer
        runner.run_observer = fake_run_observer
        try:
            with tempfile.TemporaryDirectory() as tmp:
                store = FakeStore(tmp)
                outcome, observer_summary = self.build_runner(store, client="observed").run(
                    SuccessfulModule(),
                    observer_duration_sec=3.0,
                    observer_interval_sec=0.25,
                )
        finally:
            runner.run_observer = original

        self.assertEqual(calls, [("observed", store, 3.0, 0.25)])
        self.assertIsNotNone(observer_summary)
        self.assertFalse(observer_summary.ok)
        self.assertFalse(outcome.ok)
        self.assertEqual(outcome.steps[1].name, "run")


if __name__ == "__main__":
    unittest.main()
