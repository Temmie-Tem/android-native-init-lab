"""Read-only observer for A90 native-init host-side validation."""

from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass
from typing import Any

from a90harness.device import DeviceClient
from a90harness.evidence import EvidenceStore


DEFAULT_OBSERVER_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 20.0),
    ("status", ["status"], 20.0),
    ("selftest-verbose", ["selftest", "verbose"], 20.0),
    ("bootstatus", ["bootstatus"], 20.0),
    ("longsoak-status", ["longsoak", "status", "verbose"], 20.0),
    ("storage", ["storage"], 20.0),
    ("netservice-status", ["netservice", "status"], 20.0),
)


@dataclass
class ObserverSample:
    type: str
    seq: int
    cycle: int
    host_ts: float
    name: str
    command: list[str]
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    error: str
    text_excerpt: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ObserverSummary:
    ok: bool
    cycles: int
    samples: int
    failures: int
    duration_sec: float
    jsonl: str
    stop_reason: str = "duration"
    interrupted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def text_excerpt(text: str, limit: int = 8192) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n[truncated]\n"


def observe_cycle(client: DeviceClient,
                  store: EvidenceStore,
                  cycle: int,
                  seq_start: int,
                  *,
                  jsonl_name: str = "observer.jsonl") -> list[ObserverSample]:
    samples: list[ObserverSample] = []
    seq = seq_start
    for name, command, timeout in DEFAULT_OBSERVER_COMMANDS:
        record, text = client.run(name, command, timeout=timeout)
        sample = ObserverSample(
            type="observer_sample",
            seq=seq,
            cycle=cycle,
            host_ts=time.time(),
            name=name,
            command=command,
            ok=record.ok,
            rc=record.rc,
            status=record.status,
            duration_sec=record.duration_sec,
            error=record.error,
            text_excerpt=text_excerpt(text),
        )
        samples.append(sample)
        store.append_jsonl(jsonl_name, sample.to_dict())
        seq += 1
    return samples


def run_observer(client: DeviceClient,
                 store: EvidenceStore,
                 *,
                 duration_sec: float | None,
                 interval_sec: float,
                 max_cycles: int | None = None,
                 jsonl_name: str = "observer.jsonl",
                 stop_event: threading.Event | None = None) -> ObserverSummary:
    started = time.monotonic()
    deadline = None if duration_sec is None else started + duration_sec
    sample_count = 0
    failure_count = 0
    recent_failures: list[dict[str, Any]] = []
    cycle = 0
    seq = 0
    stop_reason = "duration"
    interrupted = False

    try:
        while True:
            if stop_event is not None and stop_event.is_set():
                stop_reason = "stop-event"
                break
            cycle += 1
            cycle_samples = observe_cycle(client, store, cycle, seq, jsonl_name=jsonl_name)
            seq += len(cycle_samples)
            sample_count += len(cycle_samples)
            for sample in cycle_samples:
                if not sample.ok:
                    failure_count += 1
                    recent_failures.append(sample.to_dict())
                    recent_failures = recent_failures[-16:]
            now = time.monotonic()
            store.write_json("heartbeat.json", {
                "cycle": cycle,
                "samples": sample_count,
                "failures": failure_count,
                "recent_failures": recent_failures,
                "host_ts": time.time(),
                "elapsed_sec": now - started,
                "duration_sec": duration_sec,
                "max_cycles": max_cycles,
            })
            if max_cycles is not None and cycle >= max_cycles:
                stop_reason = "max-cycles"
                break
            if deadline is not None and now >= deadline:
                stop_reason = "duration"
                break
            if deadline is None:
                sleep_sec = interval_sec
            else:
                sleep_sec = max(0.0, min(interval_sec, deadline - now))
            if stop_event is not None:
                if stop_event.wait(sleep_sec):
                    stop_reason = "stop-event"
                    break
            else:
                time.sleep(sleep_sec)
    except KeyboardInterrupt:
        stop_reason = "interrupt"
        interrupted = True

    summary = ObserverSummary(
        ok=failure_count == 0 and not interrupted,
        cycles=cycle,
        samples=sample_count,
        failures=failure_count,
        duration_sec=time.monotonic() - started,
        jsonl=str(store.path(jsonl_name)),
        stop_reason=stop_reason,
        interrupted=interrupted,
    )
    store.write_json("observer-summary.json", summary.to_dict())
    return summary
