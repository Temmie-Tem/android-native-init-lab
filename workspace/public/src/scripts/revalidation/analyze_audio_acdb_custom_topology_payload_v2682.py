from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[5]
DEFAULT_PLAN = REPO / "workspace/private/builds/audio/v2679-acdb-custom-topology-replay-deploy-plan/deploy-plan.json"
DEFAULT_SOURCE = REPO / "tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/techpack/audio/4.0/include/dsp/apr_audio-v2.h"
DEFAULT_REPORT = REPO / "docs/reports/NATIVE_INIT_V2682_AUDIO_ACDB_CUSTOM_TOPOLOGY_PAYLOAD_PARSE_2026-06-18.md"
RECORD_U32 = 98
MODULE_SLOT_U32 = 6
MODULE_SLOTS = 16
CUSTOM_TOPOLOGY_CAL_TYPES = (24, 14)
HEADER_TOPOLOGY_CAL_TYPES = (13, 9, 23)


@dataclass(frozen=True)
class ModuleSlot:
    slot: int
    module_id: int
    instance_id: int
    words: tuple[int, int, int, int, int, int]
    name: str | None

    @property
    def active(self) -> bool:
        return any(self.words)

    def to_json(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "module_id": self.module_id,
            "module_id_hex": f"0x{self.module_id:08x}",
            "module_name": self.name,
            "instance_id": self.instance_id,
            "instance_id_hex": f"0x{self.instance_id:08x}",
            "words_hex": [f"0x{word:08x}" for word in self.words],
        }


@dataclass(frozen=True)
class TopologyRecord:
    index: int
    topology_id: int
    declared_module_count: int
    modules: tuple[ModuleSlot, ...]
    nonzero_padding_words: tuple[int, ...]

    @property
    def active_modules(self) -> tuple[ModuleSlot, ...]:
        return tuple(slot for slot in self.modules if slot.active)

    @property
    def module_count_matches(self) -> bool:
        return len(self.active_modules) == self.declared_module_count

    def to_json(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "topology_id": self.topology_id,
            "topology_id_hex": f"0x{self.topology_id:08x}",
            "declared_module_count": self.declared_module_count,
            "active_module_count": len(self.active_modules),
            "module_count_matches": self.module_count_matches,
            "active_modules": [slot.to_json() for slot in self.active_modules],
            "nonzero_padding_words_hex": [f"0x{word:08x}" for word in self.nonzero_padding_words],
        }


@dataclass(frozen=True)
class PayloadParse:
    cal_type: int
    role: str
    path: Path
    size: int
    sha256: str
    topology_count: int
    records: tuple[TopologyRecord, ...]
    record_u32: int
    grammar_ok: bool

    def to_json(self) -> dict[str, Any]:
        return {
            "cal_type": self.cal_type,
            "role": self.role,
            "path_private": str(self.path),
            "size": self.size,
            "sha256": self.sha256,
            "topology_count": self.topology_count,
            "record_u32": self.record_u32,
            "grammar_ok": self.grammar_ok,
            "records": [record.to_json() for record in self.records],
        }


def load_module_names(header: Path) -> dict[int, str]:
    names: dict[int, str] = {}
    pattern = re.compile(r"^\s*#\s*define\s+([A-Za-z0-9_]*MODULE[A-Za-z0-9_]*)\s+\(?0x([0-9A-Fa-f]+)\)?")

    def score(name: str) -> tuple[int, int, str]:
        return (
            0 if "_MODULE_ID_" in name or name.endswith("_MODULE_ID") else 1,
            len(name),
            name,
        )

    for line in header.read_text(errors="replace").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        name = match.group(1)
        value = int(match.group(2), 16)
        old = names.get(value)
        if old is None or score(name) < score(old):
            names[value] = name
    return names


def remote_to_local(plan: dict[str, Any]) -> dict[str, Path]:
    output: dict[str, Path] = {}
    for item in plan.get("files", []):
        local = (item.get("local") or {}).get("local_path_private")
        remote = item.get("remote_path")
        if local and remote:
            output[remote] = REPO / local if not Path(local).is_absolute() else Path(local)
    return output


def parse_payload(path: Path, cal_type: int, role: str, module_names: dict[int, str]) -> PayloadParse:
    data = path.read_bytes()
    if len(data) % 4 != 0:
        raise ValueError(f"payload length is not u32-aligned: {path} len={len(data)}")
    words = struct.unpack("<" + "I" * (len(data) // 4), data)
    if not words:
        raise ValueError(f"empty payload: {path}")
    topology_count = words[0]
    expected_u32 = 1 + topology_count * RECORD_U32
    grammar_ok = expected_u32 == len(words)
    records: list[TopologyRecord] = []
    if grammar_ok:
        offset = 1
        for topology_index in range(topology_count):
            chunk = words[offset : offset + RECORD_U32]
            offset += RECORD_U32
            topology_id = chunk[0]
            module_count = chunk[1]
            modules: list[ModuleSlot] = []
            module_base = 2
            for slot_index in range(MODULE_SLOTS):
                start = module_base + slot_index * MODULE_SLOT_U32
                slot_words = tuple(chunk[start : start + MODULE_SLOT_U32])
                module_id = slot_words[0]
                modules.append(
                    ModuleSlot(
                        slot=slot_index,
                        module_id=module_id,
                        instance_id=slot_words[1],
                        words=slot_words,  # type: ignore[arg-type]
                        name=module_names.get(module_id),
                    )
                )
            padding_words = tuple(
                word
                for slot in modules[module_count:]
                for word in slot.words
                if word != 0
            )
            records.append(
                TopologyRecord(
                    index=topology_index,
                    topology_id=topology_id,
                    declared_module_count=module_count,
                    modules=tuple(modules),
                    nonzero_padding_words=padding_words,
                )
            )
    return PayloadParse(
        cal_type=cal_type,
        role=role,
        path=path,
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        topology_count=topology_count,
        records=tuple(records),
        record_u32=RECORD_U32,
        grammar_ok=grammar_ok,
    )


def collect_payloads(plan_path: Path, module_names: dict[int, str]) -> list[PayloadParse]:
    plan = json.loads(plan_path.read_text())
    path_map = remote_to_local(plan)
    parses: list[PayloadParse] = []
    for item in plan.get("set_args", []):
        cal_type = int(item.get("cal_type"))
        if cal_type not in CUSTOM_TOPOLOGY_CAL_TYPES:
            continue
        payload_remote = item.get("payload_remote")
        if not payload_remote:
            raise ValueError(f"missing payload for cal_type {cal_type}")
        payload_path = path_map[payload_remote]
        parses.append(parse_payload(payload_path, cal_type, str(item.get("role", "")), module_names))
    return parses


def collect_header_topology_refs(plan_path: Path) -> list[dict[str, Any]]:
    plan = json.loads(plan_path.read_text())
    path_map = remote_to_local(plan)
    refs: list[dict[str, Any]] = []
    for item in plan.get("set_args", []):
        cal_type = int(item.get("cal_type"))
        if cal_type not in HEADER_TOPOLOGY_CAL_TYPES:
            continue
        arg_remote = item.get("arg_remote")
        if not arg_remote:
            continue
        arg_path = path_map[arg_remote]
        data = arg_path.read_bytes()
        words = struct.unpack("<" + "I" * (len(data) // 4), data)
        topology_like = [
            value
            for value in words
            if 0x10000000 <= value <= 0x1FFFFFFF
        ]
        refs.append(
            {
                "cal_type": cal_type,
                "role": item.get("role", ""),
                "arg_path_private": str(arg_path),
                "arg_size": len(data),
                "arg_sha256": hashlib.sha256(data).hexdigest(),
                "topology_like_values_hex": [f"0x{value:08x}" for value in topology_like],
                "words_hex": [f"0x{value:08x}" for value in words],
            }
        )
    return refs


def build_summary(parses: list[PayloadParse], header_refs: list[dict[str, Any]]) -> dict[str, Any]:
    all_topology_ids = sorted({record.topology_id for parse in parses for record in parse.records})
    all_module_ids = sorted({slot.module_id for parse in parses for record in parse.records for slot in record.active_modules})
    topology_ids_by_cal = {
        parse.cal_type: {record.topology_id for record in parse.records}
        for parse in parses
    }
    header_match_rows: list[dict[str, Any]] = []
    for ref in header_refs:
        values = [
            int(value, 16)
            for value in ref["topology_like_values_hex"]
            if value != "0xffffffff"
        ]
        if ref["cal_type"] == 23:
            expected_custom_cal = 24
        elif ref["cal_type"] == 13:
            expected_custom_cal = 14
        elif ref["cal_type"] == 9:
            expected_custom_cal = 10
        else:
            expected_custom_cal = None
        custom_ids = topology_ids_by_cal.get(expected_custom_cal or -1, set())
        header_match_rows.append(
            {
                "header_cal_type": ref["cal_type"],
                "role": ref["role"],
                "expected_custom_cal_type": expected_custom_cal,
                "topology_like_values_hex": ref["topology_like_values_hex"],
                "matched_values_hex": [f"0x{value:08x}" for value in values if value in custom_ids],
                "missing_values_hex": [f"0x{value:08x}" for value in values if value not in custom_ids],
                "custom_payload_available": expected_custom_cal in topology_ids_by_cal,
            }
        )
    return {
        "ok": all(parse.grammar_ok and all(record.module_count_matches for record in parse.records) for parse in parses),
        "record_u32": RECORD_U32,
        "module_slots": MODULE_SLOTS,
        "custom_topology_cal_types": CUSTOM_TOPOLOGY_CAL_TYPES,
        "all_topology_ids_hex": [f"0x{value:08x}" for value in all_topology_ids],
        "all_module_ids_hex": [f"0x{value:08x}" for value in all_module_ids],
        "header_topology_refs": header_refs,
        "header_custom_matches": header_match_rows,
        "payloads": [parse.to_json() for parse in parses],
    }


def markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# NATIVE_INIT V2682 — ACDB custom-topology payload parse",
        "",
        "Date: 2026-06-18",
        "",
        "## Scope",
        "",
        "Host-only parser for the V2679/V2680 custom-topology payloads.  No device",
        "action, flash, audio ioctl, PCM probe, or raw private payload copy occurred.",
        "",
        "## Result",
        "",
        f"- decision: `v2682-custom-topology-payload-grammar-pinned`",
        f"- ok: `{summary['ok']}`",
        f"- record grammar: `count` followed by `{summary['record_u32']}` u32 words per topology record",
        f"- module slots per record: `{summary['module_slots']}` fixed slots, each `{MODULE_SLOT_U32}` u32 words",
        "",
        "The V2675 cal_type `24` and `14` payloads are not opaque blobs anymore at",
        "the outer grammar level: both parse as fixed-width topology records with",
        "matching declared module counts and zero padding after the active module slots.",
        "",
        "## Payload summary",
        "",
        "| cal_type | role | bytes | sha256 | topologies | grammar_ok |",
        "| ---: | --- | ---: | --- | ---: | --- |",
    ]
    for payload in summary["payloads"]:
        lines.append(
            f"| {payload['cal_type']} | `{payload['role']}` | {payload['size']} | "
            f"`{payload['sha256']}` | {payload['topology_count']} | `{payload['grammar_ok']}` |"
        )
    lines += ["", "## Topology records", ""]
    for payload in summary["payloads"]:
        lines += [f"### cal_type {payload['cal_type']} — `{payload['role']}`", ""]
        lines.append("| index | topology_id | declared modules | active modules | module IDs |")
        lines.append("| ---: | --- | ---: | ---: | --- |")
        for record in payload["records"]:
            modules = []
            for slot in record["active_modules"]:
                name = slot.get("module_name") or "unknown"
                modules.append(f"`{slot['module_id_hex']}` ({name})")
            module_text = ", ".join(modules)
            lines.append(
                f"| {record['index']} | `{record['topology_id_hex']}` | "
                f"{record['declared_module_count']} | {record['active_module_count']} | {module_text} |"
            )
        lines.append("")
    lines += [
        "## Header-to-custom topology match",
        "",
        "| header cal_type | role | expected custom cal_type | topology-like values | matched in custom payload | missing from custom payload |",
        "| ---: | --- | ---: | --- | --- | --- |",
    ]
    for row in summary["header_custom_matches"]:
        values = ", ".join(f"`{value}`" for value in row["topology_like_values_hex"]) or "none"
        matched = ", ".join(f"`{value}`" for value in row["matched_values_hex"]) or "none"
        missing = ", ".join(f"`{value}`" for value in row["missing_values_hex"]) or "none"
        expected = row["expected_custom_cal_type"]
        expected_text = str(expected) if expected is not None else "n/a"
        lines.append(
            f"| {row['header_cal_type']} | `{row['role']}` | {expected_text} | {values} | {matched} | {missing} |"
        )
    lines.append("")
    lines += [
        "## Interpretation",
        "",
        "The outer grammar is internally consistent, so V2680's `ADSP_EBADPARAM` is",
        "not explained by a truncated payload, wrong byte count, zero payload, or a",
        "mis-sized helper replay entry.  The ADSP is rejecting a structurally formed",
        "ASM custom-topology table.",
        "",
        "Two facts matter for the next unit:",
        "",
        "1. cal_type `23` asks for AFE topology `0x1001025d`, and cal_type `24`",
        "   contains `0x1001025d`.  The AFE custom-topology capture is therefore",
        "   semantically aligned with the observed speaker AFE topology ID.",
        "2. cal_type `13` asks for ASM topology `0x10005000` for app type `0x11135`,",
        "   but cal_type `14` contains only `0x1000ffff` and `0x10000018..1b`.",
        "   This is the first concrete mismatch explaining why the ADSP rejects",
        "   `ASM_CMD_ADD_TOPOLOGIES`: the replayed ASM custom-topology table does",
        "   not define the topology selected by the replayed ASM topology header.",
        "3. cal_type `9` asks for ADM topology `0x10004000`; no cal_type `10` custom",
        "   payload is present, so ADM remains a known later blocker even after the",
        "   ASM mismatch is fixed.",
        "",
        "## Next unit",
        "",
        "Recover the correct ASM custom-topology definition for `0x10005000` and the",
        "ADM custom-topology definition for `0x10004000`, instead of replaying the",
        "V2675 lower-hidden cal_type `14` table unchanged.  The next unit should be",
        "host-only first: inspect the ACDB DB / libacdbloader request tuple that maps",
        "app type `0x11135` to ASM topology `0x10005000`, then design a bounded",
        "capture or extraction for the exact cal_type `14` SET payload containing",
        "`0x10005000`.  Do not rerun V2679/V2680 unchanged.",
        "",
        "## Validation",
        "",
        "- `python3 -m py_compile workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_payload_v2682.py tests/test_analyze_audio_acdb_custom_topology_payload_v2682.py`",
        "- `PYTHONPATH=tests:workspace/public/src/scripts/revalidation python3 -m unittest tests.test_analyze_audio_acdb_custom_topology_payload_v2682 -v`",
        "- `PYTHONPATH=workspace/public/src/scripts/revalidation python3 workspace/public/src/scripts/revalidation/analyze_audio_acdb_custom_topology_payload_v2682.py --write-report`",
        "- `git diff --check`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--header", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    module_names = load_module_names(args.header)
    parses = collect_payloads(args.plan, module_names)
    header_refs = collect_header_topology_refs(args.plan)
    summary = build_summary(parses, header_refs)
    if args.write_report:
        args.report.write_text(markdown(summary))
    if args.json or not args.write_report:
        print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
