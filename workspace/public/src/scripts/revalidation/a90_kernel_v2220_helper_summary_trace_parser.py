#!/usr/bin/env python3
"""Parse helper-owned a90 trace_uprobe summary artifacts.

V2218 proved BPF/perf attach is not the usable path for dynamic a90 trace_uprobe
events. V2219 added a read-only trace-buffer collector for the current window.
This V2220 parser normalizes older helper summary output, legacy manifest fields,
raw trace lines, and V2219 summaries into one event schema so boot-window helper
evidence can be compared without rerunning a flash/reboot cycle.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[5]
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/kernel"

DEFAULT_INPUTS = [
    "tmp/wifi/v2167-connect-dhcp-google-ping-handoff-v2168-hidl-exact-v8/helper.strings.txt",
    "tmp/wifi/v1998-helper-strings.txt",
    "tmp/wifi/v1719-cnss-peripheral-client-uprobe-handoff/manifest.json",
    "tmp/wifi/v1710-cnss-wlfw-pre-dms-microtrace-handoff/manifest.json",
    "tmp/wifi/v1705-cnss-wlfw-downstream-uprobe-handoff/manifest.json",
]

HELPER_EVENT_RE = re.compile(
    r"^wlan_pd_cnss_nonlog_control_flow\."
    r"(?P<surface>[A-Za-z0-9_]+)\."
    r"(?P<event>[A-Za-z0-9_]+)\."
    r"(?P<field>[A-Za-z0-9_]+)=(?P<value>.*)$"
)
HELPER_SURFACE_RE = re.compile(
    r"^wlan_pd_cnss_nonlog_control_flow\."
    r"(?P<surface>[A-Za-z0-9_]+)\."
    r"(?P<field>[A-Za-z0-9_]+)=(?P<value>.*)$"
)
LEGACY_NONLOG_SUFFIXES = (
    "first_hit_line",
    "hit_count",
    "enable_rc",
    "enabled",
    "name",
    "offset",
    "pc",
    "register_rc",
    "registered",
)
TRACE_LINE_RE = re.compile(
    r"^\s*(?P<task>.+?)-(?P<pid>\d+)\s+\[(?P<cpu>\d+)\]\s+"
    r"(?P<flags>\S+)\s+(?P<ts>\d+\.\d+):\s+"
    r"(?:(?P<group>a90cnss|a90libqmi|a90pmsrv):)?"
    r"(?P<event>[A-Za-z0-9_]+):\s+"
    r"\((?P<probe_ip>0x[0-9a-fA-F]+)\)(?P<args>.*)$"
)
TRACE_TS_RE = re.compile(r"\s(?P<ts>\d+\.\d+):\s")


SURFACE_TO_GROUP = {
    "uprobe": "a90cnss",
    "libqmi_uprobe": "a90libqmi",
    "pm_server_uprobe": "a90pmsrv",
    "pm_service_uprobe": "a90pmsrv",
    "peripheral_uprobe": "a90periph",
    "nonlog": "a90cnss",
}

KEY_EVENTS = {
    "wlfw_start",
    "wlfw_service_request",
    "wlfw_cap_qmi",
    "wlfw_bdf_entry",
    "wlfw_bdf_send_ret",
    "libqmi_client_init_instance_entry",
    "libqmi_get_service_list_lookup_call",
    "libqmi_get_service_list_lookup_ret",
    "pm_service_post_ack_qmi_restart_ind_call",
}


@dataclass
class ParsedEvent:
    source_path: str
    source_kind: str
    surface: str
    group: str
    event: str
    fields: dict[str, Any] = field(default_factory=dict)
    samples: list[str] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.surface}:{self.event}"

    @property
    def hit_count(self) -> int:
        return as_int(self.fields.get("hit_count"), 0)

    @property
    def first_hit_line(self) -> str:
        return str(self.fields.get("first_hit_line") or "")

    @property
    def first_ts(self) -> float | None:
        return extract_ts(self.first_hit_line)

    def to_json(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "source_kind": self.source_kind,
            "surface": self.surface,
            "group": self.group,
            "event": self.event,
            "hit_count": self.hit_count,
            "first_ts": self.first_ts,
            "first_hit_line": self.first_hit_line,
            "fields": self.fields,
            "samples": self.samples,
        }


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def as_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip(), 0)
    except (TypeError, ValueError):
        return default


def extract_ts(line: str) -> float | None:
    match = TRACE_TS_RE.search(line)
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def detect_json(path: Path) -> Any | None:
    if path.suffix.lower() != ".json":
        return None
    try:
        return json.loads(path.read_text(errors="replace"))
    except json.JSONDecodeError:
        return None


def flatten_json(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, inner in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            yield from flatten_json(inner, next_prefix)
    elif isinstance(value, list):
        for index, inner in enumerate(value):
            next_prefix = f"{prefix}.{index}" if prefix else str(index)
            yield from flatten_json(inner, next_prefix)
    else:
        yield prefix, value


def event_group(surface: str) -> str:
    return SURFACE_TO_GROUP.get(surface, surface)


def merge_field(
    events: dict[tuple[str, str], ParsedEvent],
    *,
    source_path: str,
    source_kind: str,
    surface: str,
    event: str,
    field_name: str,
    value: Any,
) -> None:
    key = (surface, event)
    if key not in events:
        events[key] = ParsedEvent(
            source_path=source_path,
            source_kind=source_kind,
            surface=surface,
            group=event_group(surface),
            event=event,
        )
    parsed = events[key]
    if field_name.startswith("sample_line_"):
        parsed.samples.append(str(value))
    else:
        parsed.fields[field_name] = value


def parse_legacy_nonlog_key(key: str) -> tuple[str, str] | None:
    base = key.split(".")[-1]
    if not base.startswith("nonlog_"):
        return None
    stem = base[len("nonlog_") :]
    for suffix in LEGACY_NONLOG_SUFFIXES:
        marker = f"_{suffix}"
        if stem.endswith(marker):
            return stem[: -len(marker)], suffix
    return None


def parse_text_lines(path: Path, lines: Iterable[str], source_kind: str) -> list[ParsedEvent]:
    source_path = rel(path)
    events: dict[tuple[str, str], ParsedEvent] = {}
    surface_seen: dict[str, int] = {}
    for raw_line in lines:
        line = raw_line.rstrip("\r\n")
        match = HELPER_EVENT_RE.match(line)
        if match:
            merge_field(
                events,
                source_path=source_path,
                source_kind=source_kind,
                surface=match.group("surface"),
                event=match.group("event"),
                field_name=match.group("field"),
                value=match.group("value"),
            )
            continue
        match = HELPER_SURFACE_RE.match(line)
        if match:
            surface = match.group("surface")
            surface_seen[surface] = surface_seen.get(surface, 0) + 1
            merge_field(
                events,
                source_path=source_path,
                source_kind=source_kind,
                surface=surface,
                event=f"_surface_{surface}",
                field_name=match.group("field"),
                value=match.group("value"),
            )
            continue
        match = TRACE_LINE_RE.match(line)
        if match:
            group = match.group("group") or "a90cnss"
            event = match.group("event")
            surface = {
                "a90cnss": "uprobe",
                "a90libqmi": "libqmi_uprobe",
                "a90pmsrv": "pm_server_uprobe",
            }.get(group, group)
            merge_field(
                events,
                source_path=source_path,
                source_kind="raw_trace_line",
                surface=surface,
                event=event,
                field_name="hit_count",
                value=events.get((surface, event), ParsedEvent(source_path, "raw_trace_line", surface, group, event)).hit_count + 1,
            )
            merge_field(
                events,
                source_path=source_path,
                source_kind="raw_trace_line",
                surface=surface,
                event=event,
                field_name="first_hit_line",
                value=events[(surface, event)].fields.get("first_hit_line") or line,
            )
            events[(surface, event)].samples.append(line)
    return list(events.values())


def parse_json_artifact(path: Path, data: Any) -> list[ParsedEvent]:
    source_path = rel(path)
    events: dict[tuple[str, str], ParsedEvent] = {}

    if isinstance(data, dict) and isinstance(data.get("hit_summary"), dict):
        hit_summary = data["hit_summary"]
        event_counts = hit_summary.get("event_counts") or {}
        first_hits = hit_summary.get("first_hits") or {}
        for event_name, count in event_counts.items():
            group, event = split_group_event(str(event_name))
            surface = group_to_surface(group)
            merge_field(
                events,
                source_path=source_path,
                source_kind="v2219_summary",
                surface=surface,
                event=event,
                field_name="hit_count",
                value=count,
            )
            if str(event_name) in first_hits:
                merge_field(
                    events,
                    source_path=source_path,
                    source_kind="v2219_summary",
                    surface=surface,
                    event=event,
                    field_name="first_hit_line",
                    value=first_hits[str(event_name)],
                )
        event_state = data.get("event_state") or {}
        if not event_counts and isinstance(event_state, dict):
            for event_name in event_state:
                group, event = split_group_event(str(event_name))
                surface = group_to_surface(group)
                merge_field(
                    events,
                    source_path=source_path,
                    source_kind="v2219_summary",
                    surface=surface,
                    event=event,
                    field_name="hit_count",
                    value=0,
                )

    for key, value in flatten_json(data):
        if not isinstance(value, (str, int, float, bool)):
            continue
        legacy = parse_legacy_nonlog_key(key)
        if legacy:
            event, field_name = legacy
            if event == "uprobe":
                event = "_surface_nonlog"
            merge_field(
                events,
                source_path=source_path,
                source_kind="legacy_manifest_nonlog",
                surface="nonlog",
                event=event,
                field_name=field_name,
                value=value,
            )
            continue
        if isinstance(value, str):
            line_events = parse_text_lines(path, [value], "json_embedded_trace_line")
            for line_event in line_events:
                for field_name, field_value in line_event.fields.items():
                    merge_field(
                        events,
                        source_path=source_path,
                        source_kind=line_event.source_kind,
                        surface=line_event.surface,
                        event=line_event.event,
                        field_name=field_name,
                        value=field_value,
                    )
                for sample in line_event.samples:
                    merge_field(
                        events,
                        source_path=source_path,
                        source_kind=line_event.source_kind,
                        surface=line_event.surface,
                        event=line_event.event,
                        field_name=f"sample_line_{len(events[(line_event.surface, line_event.event)].samples)}",
                        value=sample,
                    )

    return list(events.values())


def split_group_event(name: str) -> tuple[str, str]:
    if ":" in name:
        group, event = name.split(":", 1)
        return group, event
    return "a90cnss", name


def group_to_surface(group: str) -> str:
    return {
        "a90cnss": "uprobe",
        "a90libqmi": "libqmi_uprobe",
        "a90pmsrv": "pm_server_uprobe",
    }.get(group, group)


def parse_path(path: Path) -> list[ParsedEvent]:
    data = detect_json(path)
    if data is not None:
        return parse_json_artifact(path, data)
    text = path.read_text(errors="replace")
    return parse_text_lines(path, text.splitlines(), "helper_summary_text")


def discover_default_inputs() -> list[Path]:
    candidates = [REPO_ROOT / item for item in DEFAULT_INPUTS]
    candidates.extend(sorted(PRIVATE_RUNS.glob("v2219-a90-uprobe-trace-buffer-*/summary.json")))
    return [item for item in candidates if item.exists()]


def aggregate(events: list[ParsedEvent]) -> dict[str, Any]:
    by_key: dict[str, dict[str, Any]] = {}
    timeline: list[dict[str, Any]] = []
    for event in events:
        entry = by_key.setdefault(
            event.key,
            {
                "surface": event.surface,
                "group": event.group,
                "event": event.event,
                "total_hit_count": 0,
                "sources": [],
                "first_ts": None,
                "first_hit_line": "",
                "key_event": event.event in KEY_EVENTS,
            },
        )
        entry["total_hit_count"] += event.hit_count
        entry["sources"].append(
            {
                "source_path": event.source_path,
                "source_kind": event.source_kind,
                "hit_count": event.hit_count,
                "first_ts": event.first_ts,
                "first_hit_line": event.first_hit_line,
            }
        )
        if event.first_ts is not None and (
            entry["first_ts"] is None or event.first_ts < entry["first_ts"]
        ):
            entry["first_ts"] = event.first_ts
            entry["first_hit_line"] = event.first_hit_line
        if event.hit_count > 0 and event.first_ts is not None:
            timeline.append(
                {
                    "ts": event.first_ts,
                    "surface": event.surface,
                    "group": event.group,
                    "event": event.event,
                    "hit_count": event.hit_count,
                    "source_path": event.source_path,
                    "line": event.first_hit_line,
                }
            )

    timeline.sort(key=lambda item: (item["ts"], item["event"]))
    rollups = [item for item in by_key.values() if str(item["event"]).startswith("_surface_")]
    event_items = [item for item in by_key.values() if not str(item["event"]).startswith("_surface_")]
    hit_events = [item for item in event_items if item["total_hit_count"] > 0]
    key_hits = [item for item in hit_events if item["key_event"]]
    nohit_sources = sorted(
        {
            event.source_path
            for event in events
            if event.source_kind == "v2219_summary" and event.hit_count == 0
        }
    )
    return {
        "event_total": len(by_key),
        "surface_rollup_total": len(rollups),
        "hit_event_total": len(hit_events),
        "key_hit_event_total": len(key_hits),
        "total_hits": sum(item["total_hit_count"] for item in hit_events),
        "surface_rollup_hits": sum(item["total_hit_count"] for item in rollups),
        "sources_total": len({event.source_path for event in events}),
        "v2219_nohit_sources": nohit_sources,
        "top_hit_events": sorted(
            hit_events,
            key=lambda item: (-item["total_hit_count"], item["surface"], item["event"]),
        )[:20],
        "timeline": timeline[:200],
        "events_by_key": dict(sorted(by_key.items())),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="Artifact to parse. May be repeated. Defaults to known helper evidence plus V2219 summaries.",
    )
    parser.add_argument("--out-dir", default="", help="Output directory under repo root or absolute path.")
    parser.add_argument("--label", default="v2220-helper-summary-trace-parser")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.out_dir:
        out_dir = Path(args.out_dir)
        if not out_dir.is_absolute():
            out_dir = REPO_ROOT / out_dir
    else:
        out_dir = PRIVATE_RUNS / f"{args.label}-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)

    input_paths = [Path(item) if Path(item).is_absolute() else REPO_ROOT / item for item in args.input]
    if not input_paths:
        input_paths = discover_default_inputs()
    input_paths = [path for path in input_paths if path.exists()]

    events: list[ParsedEvent] = []
    errors: list[dict[str, str]] = []
    for path in input_paths:
        try:
            events.extend(parse_path(path))
        except OSError as exc:
            errors.append({"path": rel(path), "error": str(exc)})

    aggregate_summary = aggregate(events)
    decision = (
        "v2220-helper-summary-parser-validated-existing-hit-current-nohit"
        if aggregate_summary["hit_event_total"] > 0
        else "v2220-helper-summary-parser-no-hit-evidence-found"
    )
    pass_value = aggregate_summary["hit_event_total"] > 0 and not errors
    summary = {
        "label": args.label,
        "decision": decision,
        "pass": pass_value,
        "out_dir": rel(out_dir),
        "input_paths": [rel(path) for path in input_paths],
        "errors": errors,
        "safety": {
            "host_only": True,
            "device_io": False,
            "bpf_attach": False,
            "tracefs_control_write": False,
            "flash_reboot": False,
            "wifi_scan_connect": False,
            "network_route_change": False,
            "partition_write": False,
            "probe_write_user_executed": False,
        },
        **aggregate_summary,
    }

    events_path = out_dir / "events.json"
    timeline_path = out_dir / "timeline.json"
    summary_path = out_dir / "summary.json"
    events_path.write_text(
        json.dumps([event.to_json() for event in events], indent=2, sort_keys=True) + "\n"
    )
    timeline_path.write_text(json.dumps(aggregate_summary["timeline"], indent=2, sort_keys=True) + "\n")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if pass_value else 1


if __name__ == "__main__":
    raise SystemExit(main())
