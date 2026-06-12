#!/usr/bin/env python3
"""V2241 user-space uprobe offset/base mapper.

V2240 proved a90* __probe_ip values are user-space addresses. This host-only
postprocessor closes the next identity layer by joining those runtime probe IPs
with the static uprobe offsets embedded in a90_android_execns_probe.c. The result
is a per-run load-bias map for cnss-daemon, pm-service, and libqmi_cci.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
HELPER_SOURCE = REPO_ROOT / "workspace/public/src/native-init/helpers/a90_android_execns_probe.c"
DEFAULT_PARSER_SUMMARIES = [
    PRIVATE_RUNS / "v2229-live-20260612-080114/parser/summary.json",
    PRIVATE_RUNS / "v2231-live-20260612-081302/parser/summary.json",
    PRIVATE_RUNS / "v2233-live-20260612-083738/parser/summary.json",
]
DEFAULT_V2240 = PRIVATE_RUNS / "v2240-codepath-identity-boundary-20260612-110740/summary.json"
DEFAULT_ELFS = {
    "a90cnss": REPO_ROOT / "tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon",
    "a90pmsrv": REPO_ROOT / "tmp/wifi/v1942-qcril-radio-vendor-artifact-export/vendor-source/bin/pm-service",
    "a90libqmi": REPO_ROOT / "tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libqmi_cci.so",
}

ADDRESS_RE = re.compile(r"\((0x[0-9a-fA-F]+)\)")
MACRO_EVENT_RE = re.compile(r'CNSS_WLFW_UPROBE_EVENT(?:_FETCH)?\("(?P<name>[^"]+)",\s*"(?P<key>[^"]+)",\s*(?P<offset>0x[0-9a-fA-F]+)ULL')
BRACE_EVENT_RE = re.compile(r'\{\s*"(?P<name>[^"]+)",\s*"(?P<key>[^"]+)",\s*(?P<offset>0x[0-9a-fA-F]+)ULL')

ARRAY_STARTS = {
    "cnss_wlfw_uprobe_events": "a90cnss",
    "cnss_peripheral_uprobe_events": "a90cnss",
    "pm_service_uprobe_events": "a90pmsrv",
    "libqmi_cci_uprobe_events": "a90libqmi",
}
A90_GROUPS = {"a90cnss", "a90libqmi", "a90pmsrv"}


@dataclass(frozen=True)
class UprobeSpec:
    group: str
    name: str
    key: str
    offset: int
    offset_hex: str
    source_line: int


@dataclass(frozen=True)
class RuntimeProbe:
    run_id: str
    group: str
    event: str
    address: int
    address_hex: str
    ts: float | None
    source_path: str | None


@dataclass(frozen=True)
class BiasObservation:
    run_id: str
    group: str
    event: str
    runtime: str
    static_offset: str
    load_bias: int
    load_bias_hex: str
    page_aligned: bool


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def infer_run_id(path: Path) -> str:
    for part in path.parts:
        if part.startswith("v") and "-" in part:
            return part.split("-", 1)[0]
    return path.parent.name


def parse_uprobe_specs(source: Path) -> dict[tuple[str, str], UprobeSpec]:
    specs: dict[tuple[str, str], UprobeSpec] = {}
    current_group: str | None = None
    current_array: str | None = None
    for lineno, line in enumerate(source.read_text(errors="replace").splitlines(), start=1):
        for array_name, group in ARRAY_STARTS.items():
            if array_name in line and "=" in line and "{" in line:
                current_array = array_name
                current_group = group
                break
        if current_group is None:
            continue
        match = MACRO_EVENT_RE.search(line) or BRACE_EVENT_RE.search(line)
        if match:
            name = match.group("name")
            key = match.group("key")
            offset = int(match.group("offset"), 16)
            specs[(current_group, name)] = UprobeSpec(current_group, name, key, offset, hex(offset), lineno)
        if current_array and line.strip() == "};":
            current_array = None
            current_group = None
    return specs


def extract_runtime_probes(path: Path) -> list[RuntimeProbe]:
    data = read_json(path)
    timeline = data.get("timeline")
    if not isinstance(timeline, list) or not timeline:
        raise ValueError(f"missing timeline in {path}")
    run_id = infer_run_id(path)
    seen: set[tuple[str, str]] = set()
    probes: list[RuntimeProbe] = []
    for item in timeline:
        group = str(item.get("group") or "")
        event = str(item.get("event") or "")
        if group not in A90_GROUPS or event.startswith("_surface_"):
            continue
        key = (group, event)
        if key in seen:
            continue
        seen.add(key)
        line = str(item.get("line") or "")
        match = ADDRESS_RE.search(line)
        if not match:
            continue
        address = int(match.group(1), 16)
        probes.append(RuntimeProbe(
            run_id=run_id,
            group=group,
            event=event,
            address=address,
            address_hex=hex(address),
            ts=round(float(item["ts"]), 6) if item.get("ts") is not None else None,
            source_path=item.get("source_path"),
        ))
    return probes


def elf_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": rel(path), "exists": False}
    completed = subprocess.run(["readelf", "-h", "-lW", str(path)], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    file_info = subprocess.run(["file", str(path)], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    load_segments: list[dict[str, Any]] = []
    for raw in completed.stdout.splitlines():
        line = raw.strip()
        if not line.startswith("LOAD"):
            continue
        parts = line.split()
        if len(parts) < 8:
            continue
        try:
            load_segments.append({
                "offset": parts[1],
                "virt_addr": parts[2],
                "phys_addr": parts[3],
                "file_size": parts[4],
                "mem_size": parts[5],
                "flags": parts[6] if len(parts) > 6 else "",
                "align": parts[7] if len(parts) > 7 else "",
            })
        except Exception:
            continue
    return {
        "path": rel(path),
        "exists": True,
        "file": file_info.stdout.strip(),
        "readelf_rc": completed.returncode,
        "load_segments": load_segments,
    }


def build_bias_observations(
    probes: list[RuntimeProbe],
    specs: dict[tuple[str, str], UprobeSpec],
) -> tuple[list[BiasObservation], list[dict[str, Any]], list[dict[str, Any]]]:
    observations: list[BiasObservation] = []
    missing: list[dict[str, Any]] = []
    aliases: list[dict[str, Any]] = []
    valid_identity = {
        (probe.run_id, probe.event, probe.address)
        for probe in probes
        if (probe.group, probe.event) in specs
    }
    for probe in probes:
        spec = specs.get((probe.group, probe.event))
        if spec is None:
            if (probe.run_id, probe.event, probe.address) in valid_identity:
                alias = asdict(probe)
                alias["reason"] = "same run/event/address also appears under a group with a static spec"
                aliases.append(alias)
                continue
            missing.append(asdict(probe))
            continue
        bias = probe.address - spec.offset
        observations.append(BiasObservation(
            run_id=probe.run_id,
            group=probe.group,
            event=probe.event,
            runtime=probe.address_hex,
            static_offset=spec.offset_hex,
            load_bias=bias,
            load_bias_hex=hex(bias),
            page_aligned=(bias % 0x1000) == 0,
        ))
    return observations, missing, aliases


def summarize_biases(observations: list[BiasObservation]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[BiasObservation]] = defaultdict(list)
    for obs in observations:
        grouped[(obs.run_id, obs.group)].append(obs)
    out: dict[str, Any] = {}
    for (run_id, group), rows in sorted(grouped.items()):
        counts = Counter(row.load_bias for row in rows)
        dominant_bias, dominant_count = counts.most_common(1)[0]
        mismatches = [asdict(row) for row in rows if row.load_bias != dominant_bias]
        out[f"{run_id}:{group}"] = {
            "run_id": run_id,
            "group": group,
            "matched_events": len(rows),
            "unique_load_biases": len(counts),
            "dominant_load_bias": hex(dominant_bias),
            "dominant_count": dominant_count,
            "all_page_aligned": all(row.page_aligned for row in rows),
            "mismatches": mismatches,
        }
    return out


def build_summary(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    specs = parse_uprobe_specs(args.helper_source)
    probes: list[RuntimeProbe] = []
    for path in args.parser_summaries:
        probes.extend(extract_runtime_probes(path))
    observations, missing, aliases = build_bias_observations(probes, specs)
    bias_summary = summarize_biases(observations)
    all_groups_expected = {f"{infer_run_id(path)}:{group}" for path in args.parser_summaries for group in sorted(A90_GROUPS)}
    groups_seen = set(bias_summary)
    complete_groups = all_groups_expected <= groups_seen
    all_unique = all(row["unique_load_biases"] == 1 for row in bias_summary.values())
    all_aligned = all(row["all_page_aligned"] for row in bias_summary.values())
    decision = "v2241-user-uprobe-offset-base-map-pass"
    if not (complete_groups and all_unique and all_aligned):
        decision = "v2241-user-uprobe-offset-base-map-incomplete"
    return {
        "label": args.label,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "decision": decision,
        "pass": decision.endswith("-pass"),
        "out_dir": rel(out_dir),
        "safety": {
            "host_only": True,
            "device_io": False,
            "bpf_attach": False,
            "tracefs_control_write": False,
            "probe_write_user_executed": False,
            "wifi_scan_connect": False,
            "network_route_change": False,
            "flash_reboot": False,
            "partition_write": False,
            "private_raw_log_copied_to_public": False,
        },
        "inputs": {
            "helper_source": rel(args.helper_source),
            "parser_summaries": [rel(path) for path in args.parser_summaries],
            "v2240_boundary": rel(args.v2240),
        },
        "v2240_decision": read_json(args.v2240).get("decision"),
        "static_spec_counts": dict(sorted(Counter(spec.group for spec in specs.values()).items())),
        "runtime_probe_counts": dict(sorted(Counter(probe.group for probe in probes).items())),
        "matched_observation_count": len(observations),
        "missing_static_spec_count": len(missing),
        "missing_static_specs": missing[:20],
        "alias_duplicate_count": len(aliases),
        "alias_duplicates": aliases[:20],
        "bias_summary": bias_summary,
        "elf_metadata": {group: elf_metadata(path) for group, path in args.elf.items()},
        "identity_contract": {
            "static_offset_source": "a90_android_execns_probe.c uprobe offset tables",
            "runtime_ip_source": "V2229/V2231/V2233 parser timeline first-hit a90* __probe_ip values",
            "load_bias_formula": "load_bias = runtime_probe_ip - static_uprobe_offset",
            "expected_invariant": "for each run and mapped user object, all matched events share one page-aligned load bias",
            "next_if_needed": "symbolize within stripped user ELFs by file offset/disassembly around static offsets, not by kernel System.map",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2241-user-uprobe-offset-base-map")
    parser.add_argument("--helper-source", type=Path, default=HELPER_SOURCE)
    parser.add_argument("--parser-summary", action="append", type=Path, dest="parser_summaries")
    parser.add_argument("--v2240", type=Path, default=DEFAULT_V2240)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--elf", action="append", default=[], help="group=path override, e.g. a90cnss=/path/cnss-daemon")
    args = parser.parse_args()
    args.parser_summaries = args.parser_summaries or DEFAULT_PARSER_SUMMARIES
    elf_map = dict(DEFAULT_ELFS)
    for item in args.elf:
        if "=" not in item:
            raise SystemExit(f"invalid --elf {item!r}; expected group=path")
        group, value = item.split("=", 1)
        elf_map[group] = Path(value)
    args.elf = elf_map
    return args


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir or PRIVATE_RUNS / f"{args.label}-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = build_summary(args, out_dir)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": summary["decision"],
        "pass": summary["pass"],
        "out_dir": rel(out_dir),
        "summary": rel(summary_path),
        "static_spec_counts": summary["static_spec_counts"],
        "runtime_probe_counts": summary["runtime_probe_counts"],
        "bias_groups": len(summary["bias_summary"]),
        "missing_static_spec_count": summary["missing_static_spec_count"],
    }, indent=2, sort_keys=True))
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
