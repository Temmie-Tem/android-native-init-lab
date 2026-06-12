"""Regression tests for the a90harness.observer read-only sampler."""

import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

from _loader import load_harness

broker_stub = types.ModuleType("a90_broker")
broker_stub.PROTO = "A90B1"
broker_stub.connect_and_call = lambda *_args, **_kwargs: {}
sys.modules.setdefault("a90_broker", broker_stub)

observer = load_harness("observer")


class FakeStore:
    def __init__(self):
        self.jsonl_rows = []
        self.json_writes = []

    def append_jsonl(self, name, payload):
        self.jsonl_rows.append((name, payload))

    def write_json(self, name, payload):
        self.json_writes.append((name, payload))

    def path(self, name):
        return Path("/fake/run") / name


class FakeClient:
    def __init__(self, failures=None):
        self.calls = []
        self.failures = set(failures or [])

    def run(self, name, command, timeout):
        self.calls.append((name, command, timeout))
        ok = name not in self.failures
        record = SimpleNamespace(
            ok=ok,
            rc=0 if ok else 7,
            status="ok" if ok else "failed",
            duration_sec=0.25,
            error="" if ok else f"{name} failed",
        )
        return record, f"{name} output"


class ObserverDataclasses(unittest.TestCase):
    def test_observer_sample_to_dict_serializes_all_fields(self):
        sample = observer.ObserverSample(
            type="observer_sample",
            seq=1,
            cycle=2,
            host_ts=3.0,
            name="status",
            command=["status"],
            ok=True,
            rc=0,
            status="ok",
            duration_sec=0.5,
            error="",
            text_excerpt="status output",
        )

        self.assertEqual(
            sample.to_dict(),
            {
                "type": "observer_sample",
                "seq": 1,
                "cycle": 2,
                "host_ts": 3.0,
                "name": "status",
                "command": ["status"],
                "ok": True,
                "rc": 0,
                "status": "ok",
                "duration_sec": 0.5,
                "error": "",
                "text_excerpt": "status output",
            },
        )

    def test_observer_summary_to_dict_serializes_defaults_and_flags(self):
        summary = observer.ObserverSummary(
            ok=False,
            cycles=1,
            samples=7,
            failures=1,
            duration_sec=2.0,
            jsonl="/fake/run/observer.jsonl",
            stop_reason="interrupt",
            interrupted=True,
        )

        self.assertEqual(
            summary.to_dict(),
            {
                "ok": False,
                "cycles": 1,
                "samples": 7,
                "failures": 1,
                "duration_sec": 2.0,
                "jsonl": "/fake/run/observer.jsonl",
                "stop_reason": "interrupt",
                "interrupted": True,
            },
        )


class TextExcerpt(unittest.TestCase):
    def test_text_excerpt_returns_short_text_unchanged(self):
        self.assertEqual(observer.text_excerpt("abc", limit=3), "abc")

    def test_text_excerpt_truncates_long_text_with_marker(self):
        self.assertEqual(observer.text_excerpt("abcdef", limit=3), "abc\n[truncated]\n")


class ObserveCycle(unittest.TestCase):
    def test_observe_cycle_runs_default_commands_and_appends_jsonl(self):
        client = FakeClient(failures={"selftest-verbose"})
        store = FakeStore()

        samples = observer.observe_cycle(client, store, cycle=4, seq_start=10, jsonl_name="obs.jsonl")

        self.assertEqual(len(samples), len(observer.DEFAULT_OBSERVER_COMMANDS))
        self.assertEqual([sample.seq for sample in samples], list(range(10, 10 + len(samples))))
        self.assertEqual({sample.cycle for sample in samples}, {4})
        self.assertEqual(samples[0].name, "version")
        self.assertEqual(samples[0].command, ["version"])
        self.assertFalse(next(sample for sample in samples if sample.name == "selftest-verbose").ok)
        self.assertEqual(client.calls, list(observer.DEFAULT_OBSERVER_COMMANDS))
        self.assertEqual(len(store.jsonl_rows), len(samples))
        self.assertTrue(all(name == "obs.jsonl" for name, _payload in store.jsonl_rows))
        self.assertTrue(all(payload["type"] == "observer_sample" for _name, payload in store.jsonl_rows))


class RunObserver(unittest.TestCase):
    def test_run_observer_max_cycles_writes_heartbeat_and_summary(self):
        client = FakeClient(failures={"status", "storage"})
        store = FakeStore()

        summary = observer.run_observer(
            client,
            store,
            duration_sec=None,
            interval_sec=99.0,
            max_cycles=1,
            jsonl_name="obs.jsonl",
        )

        self.assertFalse(summary.ok)
        self.assertEqual(summary.cycles, 1)
        self.assertEqual(summary.samples, len(observer.DEFAULT_OBSERVER_COMMANDS))
        self.assertEqual(summary.failures, 2)
        self.assertEqual(summary.stop_reason, "max-cycles")
        self.assertFalse(summary.interrupted)
        self.assertEqual(summary.jsonl, "/fake/run/obs.jsonl")
        heartbeat = next(payload for name, payload in store.json_writes if name == "heartbeat.json")
        self.assertEqual(heartbeat["cycle"], 1)
        self.assertEqual(heartbeat["samples"], len(observer.DEFAULT_OBSERVER_COMMANDS))
        self.assertEqual(heartbeat["failures"], 2)
        self.assertEqual([item["name"] for item in heartbeat["recent_failures"]], ["status", "storage"])
        written_summary = next(payload for name, payload in store.json_writes if name == "observer-summary.json")
        self.assertEqual(written_summary["stop_reason"], "max-cycles")

    def test_run_observer_pre_set_stop_event_exits_without_sampling(self):
        event = observer.threading.Event()
        event.set()
        client = FakeClient()
        store = FakeStore()

        summary = observer.run_observer(
            client,
            store,
            duration_sec=10.0,
            interval_sec=1.0,
            max_cycles=None,
            stop_event=event,
        )

        self.assertTrue(summary.ok)
        self.assertEqual(summary.cycles, 0)
        self.assertEqual(summary.samples, 0)
        self.assertEqual(summary.failures, 0)
        self.assertEqual(summary.stop_reason, "stop-event")
        self.assertEqual(client.calls, [])
        self.assertEqual([name for name, _payload in store.json_writes], ["observer-summary.json"])


if __name__ == "__main__":
    unittest.main()
