#!/usr/bin/env python3
"""V2238 source/live audit for static tracepoint object-chain feasibility.

This is read-only. It does not attach BPF, write tracefs controls, trigger Wi-Fi,
change routes, reboot, flash, or write partitions. It answers whether the static
WLAN-adjacent tracepoint records retain raw object pointers that can be used as
BPF probe_read anchors, or only scalarized identifiers.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
DEFAULT_SOURCE_ROOT = REPO_ROOT / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source"

CONTROL_LINE_RE = re.compile(r"^(a90:/#|A90P1 BEGIN|A90P1 END|\[done\]|\[exit |run: pid=|cmdv1x )")
LINKER_WARNING_RE = re.compile(r"^(WARNING: )?linker: Warning: failed to find generated linker configuration")
FIELD_RE = re.compile(
    r"field:(?P<type>[^;]+?)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]+\])?);"
    r"\s*offset:(?P<offset>\d+);\s*size:(?P<size>\d+);\s*signed:(?P<signed>[01]);"
)
TRACE_START_RE = re.compile(r"^\s*(TRACE_EVENT|DECLARE_EVENT_CLASS|DEFINE_EVENT)\s*\(")
POINTER_PARAM_RE = re.compile(r"(?P<type>(?:const\s+)?(?:struct\s+)?[A-Za-z_][A-Za-z0-9_\s]*?)\s*\*\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*$")
FIELD_SOURCE_RE = re.compile(r"__field\s*\(\s*(?P<type>[^,]+?)\s*,\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\)")
ARRAY_SOURCE_RE = re.compile(r"__(?:dynamic_)?array\s*\(\s*(?P<type>[^,]+?)\s*,\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*,")

TARGET_FILES = {
    "cfg80211": "net/wireless/trace.h",
    "msm_pil_event": "include/trace/events/trace_msm_pil_event.h",
    "dfc": "include/trace/events/dfc.h",
}

IMPORTANT_EVENT_NAMES = {
    "cfg80211_scan_done",
    "cfg80211_send_rx_assoc",
    "cfg80211_connect_result",
    "cfg80211_roamed",
    "cfg80211_disconnected",
    "cfg80211_inform_bss_frame",
    "cfg80211_rdev_return_int",
    "rdev_scan",
    "rdev_connect",
    "rdev_return_int",
    "pil_event",
    "pil_notif",
    "dfc_qmi_tc",
    "dfc_flow_ind",
}

SCALARIZED_MACROS = {
    "WIPHY_ENTRY": "wiphy_name string only; original struct wiphy pointer is not retained",
    "WDEV_ENTRY": "wireless_dev identifier only; original struct wireless_dev pointer is not retained",
    "NETDEV_ENTRY": "netdev name and ifindex only; original struct net_device pointer is not retained",
    "CHAN_ENTRY": "channel band and frequency only; original channel pointer is not retained",
    "CHAN_DEF_ENTRY": "channel definition scalar fields only",
    "MAC_ENTRY": "MAC bytes only; source pointer is not retained",
    "SINFO_ENTRY": "station_info selected counters only; original station_info pointer is not retained",
    "MESH_CFG_ENTRY": "mesh config scalar fields only",
    "QOS_MAP_ENTRY": "QoS map copied arrays only",
}


@dataclass
class HostStep:
    name: str
    command: list[str]
    returncode: int
    elapsed_sec: float
    stdout_path: str
    stderr_path: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def run_host(out_dir: Path, steps: list[HostStep], name: str, command: list[str], timeout: float = 60.0, allow_error: bool = False) -> str:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    elapsed = time.monotonic() - started
    stdout_path = out_dir / f"{name}.stdout.txt"
    stderr_path = out_dir / f"{name}.stderr.txt"
    stdout_path.write_text(completed.stdout)
    stderr_path.write_text(completed.stderr)
    step = HostStep(name, command, completed.returncode, round(elapsed, 3), rel(stdout_path), rel(stderr_path))
    steps.append(step)
    if completed.returncode != 0 and not allow_error:
        raise RuntimeError(f"{name} failed rc={completed.returncode}: {completed.stderr or completed.stdout}")
    return completed.stdout


def a90ctl(out_dir: Path, steps: list[HostStep], name: str, argv: list[str], host: str, port: int, timeout: float, allow_error: bool = False) -> str:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "a90ctl.py"),
        "--host",
        host,
        "--port",
        str(port),
        "--timeout",
        str(timeout),
    ]
    if allow_error:
        command.append("--allow-error")
    command.extend(argv)
    return run_host(out_dir, steps, name, command, timeout=timeout + 10, allow_error=allow_error)


def clean_cmdv1_text(text: str) -> str:
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip("\r")
        if CONTROL_LINE_RE.match(line):
            continue
        if LINKER_WARNING_RE.match(line):
            continue
        if not line:
            continue
        lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def split_top_level_args(text: str) -> list[str]:
    args: list[str] = []
    start = 0
    depth = 0
    in_string: str | None = None
    escape = False
    for idx, char in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == in_string:
                in_string = None
            continue
        if char in {'"', "'"}:
            in_string = char
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}" and depth > 0:
            depth -= 1
        elif char == "," and depth == 0:
            args.append(text[start:idx].strip())
            start = idx + 1
    tail = text[start:].strip()
    if tail:
        args.append(tail)
    return args


def extract_macro_call(block: str, macro: str) -> str:
    marker = f"{macro}("
    start = block.find(marker)
    if start < 0:
        return ""
    pos = start + len(marker)
    depth = 1
    in_string: str | None = None
    escape = False
    for idx in range(pos, len(block)):
        char = block[idx]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == in_string:
                in_string = None
            continue
        if char in {'"', "'"}:
            in_string = char
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return block[pos:idx]
    return ""


def extract_trace_blocks(path: Path) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    lines = path.read_text(errors="replace").splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        match = TRACE_START_RE.match(line)
        if not match:
            idx += 1
            continue
        kind = match.group(1)
        start_line = idx + 1
        body_lines: list[str] = []
        depth = 0
        started = False
        while idx < len(lines):
            current = lines[idx]
            body_lines.append(current)
            for char in current:
                if char == "(":
                    depth += 1
                    started = True
                elif char == ")" and started:
                    depth -= 1
            idx += 1
            if started and depth <= 0:
                break
        block = "\n".join(body_lines)
        inner = block[block.find("(") + 1 : block.rfind(")")]
        args = split_top_level_args(inner)
        name = args[0].strip() if args else ""
        event_name = args[1].strip() if kind == "DEFINE_EVENT" and len(args) > 1 else name
        blocks.append({"kind": kind, "name": name, "event_name": event_name, "block": block, "line": start_line})
    return blocks


def pointer_params(proto: str) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for arg in split_top_level_args(proto):
        cleaned = " ".join(arg.replace("\n", " ").split())
        match = POINTER_PARAM_RE.match(cleaned)
        if not match:
            continue
        typ = " ".join(match.group("type").split())
        name = match.group("name")
        category = "struct_pointer" if "struct " in typ else "byte_or_string_pointer"
        output.append({"type": typ, "name": name, "category": category})
    return output


def source_fields(struct_body: str) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for match in FIELD_SOURCE_RE.finditer(struct_body):
        fields.append({"kind": "field", "type": " ".join(match.group("type").split()), "name": match.group("name")})
    for match in ARRAY_SOURCE_RE.finditer(struct_body):
        fields.append({"kind": "array", "type": " ".join(match.group("type").split()), "name": match.group("name")})
    return fields


def parse_live_format(text: str) -> dict[str, Any]:
    fields: list[dict[str, Any]] = []
    for match in FIELD_RE.finditer(text):
        name = match.group("name")
        if "[" in name:
            name = name.split("[", 1)[0]
        typ = " ".join(match.group("type").split())
        fields.append(
            {
                "type": typ,
                "name": name,
                "offset": int(match.group("offset")),
                "size": int(match.group("size")),
                "signed": match.group("signed") == "1",
            }
        )
    raw_pointer_fields = [field for field in fields if "*" in field["type"] or field["name"].endswith("_ptr")]
    return {"fields": fields, "raw_pointer_fields": raw_pointer_fields, "field_names": [field["name"] for field in fields]}


def event_source_summary(group: str, path: Path) -> dict[str, Any]:
    class_defs: dict[str, dict[str, Any]] = {}
    events: dict[str, dict[str, Any]] = {}
    blocks = extract_trace_blocks(path)
    for block in blocks:
        proto = extract_macro_call(block["block"], "TP_PROTO")
        struct_body = extract_macro_call(block["block"], "TP_STRUCT__entry")
        fields = source_fields(struct_body)
        macro_tokens = sorted({token for token in SCALARIZED_MACROS if token in struct_body})
        raw_pointer_fields = [field for field in fields if "*" in field["type"]]
        summary = {
            "group": group,
            "source": rel(path),
            "line": block["line"],
            "kind": block["kind"],
            "template": block["name"] if block["kind"] == "DEFINE_EVENT" else None,
            "event": block["event_name"],
            "proto_pointer_params": pointer_params(proto),
            "source_fields": fields,
            "scalarized_macros": macro_tokens,
            "scalarized_macro_meanings": {token: SCALARIZED_MACROS[token] for token in macro_tokens},
            "source_raw_pointer_fields": raw_pointer_fields,
        }
        if block["kind"] == "DECLARE_EVENT_CLASS":
            class_defs[block["name"]] = summary
        elif block["kind"] == "TRACE_EVENT":
            events[block["event_name"]] = summary
        elif block["kind"] == "DEFINE_EVENT":
            template = class_defs.get(block["name"])
            if template:
                merged = dict(template)
                merged.update({"kind": "DEFINE_EVENT", "template": block["name"], "event": block["event_name"], "line": block["line"]})
                events[block["event_name"]] = merged
            else:
                events[block["event_name"]] = summary
    return {"group": group, "events": events, "classes": class_defs, "source": rel(path)}


def classify_event(event: dict[str, Any], live: dict[str, Any] | None) -> dict[str, Any]:
    proto_struct_pointers = [p for p in event["proto_pointer_params"] if p["category"] == "struct_pointer"]
    source_raw = event["source_raw_pointer_fields"]
    live_raw = (live or {}).get("raw_pointer_fields", [])
    scalarized = event["scalarized_macros"]
    if live_raw or source_raw:
        feasibility = "record-pointer-chain-possible"
        reason = "trace record retains at least one raw pointer-sized field"
        score = 3
    elif proto_struct_pointers and scalarized:
        feasibility = "caller-pointer-record-scalarized"
        reason = "TP_PROTO receives struct pointers, but TP_STRUCT__entry copies scalar identifiers/macros instead of retaining the pointer"
        score = 1
    elif proto_struct_pointers:
        feasibility = "caller-pointer-not-retained"
        reason = "TP_PROTO receives struct pointers, but no raw pointer field is visible in source/live format"
        score = 1
    else:
        feasibility = "scalar-only"
        reason = "event arguments and record fields are scalar/string/array only"
        score = 0
    return {
        "feasibility": feasibility,
        "score": score,
        "reason": reason,
        "proto_struct_pointer_count": len(proto_struct_pointers),
        "source_raw_pointer_count": len(source_raw),
        "live_raw_pointer_count": len(live_raw),
        "scalarized_macro_count": len(scalarized),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2238-static-tracepoint-object-chain-audit")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--skip-device", action="store_true")
    args = parser.parse_args()

    out_dir = PRIVATE_RUNS / f"{args.label}-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[HostStep] = []
    summary: dict[str, Any] = {
        "label": args.label,
        "out_dir": rel(out_dir),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_root": rel(args.source_root),
        "safety": {
            "host_only_source_analysis": bool(args.skip_device),
            "tracefs_control_write": False,
            "bpf_attach": False,
            "probe_write_user_executed": False,
            "wifi_scan_connect": False,
            "network_route_change": False,
            "flash_reboot": False,
            "partition_write": False,
        },
    }

    try:
        source_groups: dict[str, Any] = {}
        for group, relative in TARGET_FILES.items():
            path = args.source_root / relative
            if not path.exists():
                raise FileNotFoundError(path)
            source_groups[group] = event_source_summary(group, path)

        live_events: list[str] = []
        live_formats: dict[str, Any] = {}
        status_text = ""
        selftest_text = ""
        live_tracefs_readable: bool | None = None
        if not args.skip_device:
            status_text = a90ctl(out_dir, steps, "status", ["status"], args.bridge_host, args.bridge_port, args.timeout, allow_error=True)
            available = a90ctl(
                out_dir,
                steps,
                "available-events",
                [
                    "run",
                    "/cache/bin/busybox",
                    "sh",
                    "-c",
                    "cat /sys/kernel/tracing/available_events 2>/dev/null || cat /sys/kernel/debug/tracing/available_events 2>/dev/null",
                ],
                args.bridge_host,
                args.bridge_port,
                args.timeout,
                allow_error=True,
            )
            available_clean = clean_cmdv1_text(available)
            (out_dir / "available_events.txt").write_text(available_clean)
            for line in available_clean.splitlines():
                if ":" in line:
                    live_events.append(line.strip())
            live_tracefs_readable = bool(live_events)
            selected = []
            for group, group_summary in source_groups.items():
                for event in group_summary["events"]:
                    full = f"{group}:{event}"
                    if full in live_events and (event in IMPORTANT_EVENT_NAMES or group in {"msm_pil_event", "dfc"}):
                        selected.append((group, event))
            selected = selected[:80]
            for group, event in selected:
                fmt = a90ctl(
                    out_dir,
                    steps,
                    f"format-{group}-{event}",
                    [
                        "run",
                        "/cache/bin/busybox",
                        "sh",
                        "-c",
                        f"cat /sys/kernel/tracing/events/{group}/{event}/format 2>/dev/null || cat /sys/kernel/debug/tracing/events/{group}/{event}/format 2>/dev/null",
                    ],
                    args.bridge_host,
                    args.bridge_port,
                    args.timeout,
                    allow_error=True,
                )
                clean = clean_cmdv1_text(fmt)
                live_formats[f"{group}:{event}"] = parse_live_format(clean)
            selftest_text = a90ctl(out_dir, steps, "selftest", ["selftest"], args.bridge_host, args.bridge_port, args.timeout, allow_error=True)

        assessments: list[dict[str, Any]] = []
        for group, group_summary in source_groups.items():
            for event_name, event_summary in sorted(group_summary["events"].items()):
                full = f"{group}:{event_name}"
                live = live_formats.get(full)
                classification = classify_event(event_summary, live)
                assessments.append(
                    {
                        "event": full,
                        "source": event_summary["source"],
                        "line": event_summary["line"],
                        "kind": event_summary["kind"],
                        "template": event_summary["template"],
                        "live_available": full in live_events if live_events else None,
                        "important": event_name in IMPORTANT_EVENT_NAMES,
                        "classification": classification,
                        "proto_pointer_params": event_summary["proto_pointer_params"],
                        "scalarized_macros": event_summary["scalarized_macros"],
                        "source_raw_pointer_fields": event_summary["source_raw_pointer_fields"],
                        "live_raw_pointer_fields": (live or {}).get("raw_pointer_fields", []),
                        "live_field_names": (live or {}).get("field_names", []),
                    }
                )

        by_feasibility: dict[str, int] = {}
        for item in assessments:
            key = item["classification"]["feasibility"]
            by_feasibility[key] = by_feasibility.get(key, 0) + 1
        pointer_possible = [item for item in assessments if item["classification"]["feasibility"] == "record-pointer-chain-possible"]
        scalarized_important = [
            item for item in assessments
            if item["important"] and item["classification"]["feasibility"] in {"caller-pointer-record-scalarized", "caller-pointer-not-retained"}
        ]
        qrtr_trace_sources = sorted(
            str(path.relative_to(args.source_root))
            for path in args.source_root.rglob("*qrtr*")
            if path.is_file() and "out" not in path.relative_to(args.source_root).parts
        )[:80]
        qrtr_trace_defs = []
        for path in args.source_root.rglob("*qrtr*"):
            if path.is_file() and "out" not in path.relative_to(args.source_root).parts:
                text = path.read_text(errors="ignore")
                if "TRACE_EVENT" in text or "trace_" in text:
                    qrtr_trace_defs.append(str(path.relative_to(args.source_root)))

        decision = "v2238-static-tracepoint-object-chain-audit-pass"
        if pointer_possible:
            decision = "v2238-static-tracepoint-pointer-anchors-found"
        summary.update(
            {
                "decision": decision,
                "pass": True,
                "status_version_seen": "A90 Linux init" in status_text if status_text else None,
                "selftest_fail0": "fail=0" in selftest_text if selftest_text else None,
                "live_tracefs_readable": live_tracefs_readable,
                "live_available_events_total": len(live_events) if live_events else None,
                "source_group_counts": {group: len(data["events"]) for group, data in source_groups.items()},
                "assessment_count": len(assessments),
                "classification_counts": by_feasibility,
                "pointer_anchor_events": pointer_possible,
                "important_scalarized_events": scalarized_important,
                "qrtr_trace_source_candidates": qrtr_trace_sources,
                "qrtr_trace_defs": qrtr_trace_defs,
                "conclusion": {
                    "static_cfg80211_object_chain_read": "not_viable_from_trace_record",
                    "reason": "cfg80211 TP_PROTO receives rich object pointers, but trace records scalarize them into names, ifindex, identifiers, MACs, channel/frequency, counters, and arrays; raw object pointers are not retained.",
                    "pil_object_chain_read": "not_viable_from_trace_record",
                    "qrtr_static_tracepoints": "absent_or_not_exposed_in_trace_events",
                    "safe_next_t1": "use static tracepoints for scalar lifecycle correlation and a90 trace_uprobe tracefs records for WLFW/QMI edges; do not spend another BPF tracepoint iteration trying to dereference cfg80211/QRTR objects from scalarized records.",
                },
            }
        )
        if not args.skip_device:
            summary["pass"] = bool(summary["selftest_fail0"])
    except Exception as exc:  # noqa: BLE001
        summary.update({"decision": "v2238-static-tracepoint-object-chain-audit-failed", "pass": False, "error": str(exc)})
    finally:
        summary["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        summary["steps"] = [asdict(step) | {"ok": step.ok} for step in steps]
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(json.dumps({
            "decision": summary.get("decision"),
            "pass": summary.get("pass"),
            "out_dir": summary.get("out_dir"),
            "classification_counts": summary.get("classification_counts"),
            "pointer_anchor_events": len(summary.get("pointer_anchor_events") or []),
            "important_scalarized_events": len(summary.get("important_scalarized_events") or []),
            "live_available_events_total": summary.get("live_available_events_total"),
            "live_tracefs_readable": summary.get("live_tracefs_readable"),
            "selftest_fail0": summary.get("selftest_fail0"),
            "error": summary.get("error"),
        }, indent=2, sort_keys=True))
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
