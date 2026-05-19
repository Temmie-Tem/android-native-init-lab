#!/usr/bin/env python3
"""Fetch and classify AOSP property area/property_info format source facts."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import re
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v309-property-format-source-probe")
DEFAULT_SEED = Path("tmp/wifi/v301-property-shim-seed-android/seed.json")
DEFAULT_V308 = Path("tmp/wifi/v308-private-property-area-proof/manifest.json")
DEFAULT_AOSP_REF = "android-12.0.0_r34"
GITILES_BASE = "https://android.googlesource.com/platform"


@dataclass(frozen=True)
class SourceSpec:
    name: str
    project: str
    path: str
    required_patterns: tuple[str, ...]


@dataclass
class SourceFact:
    name: str
    project: str
    path: str
    url: str
    fetched: bool
    sha256: str
    bytes: int
    missing_patterns: list[str]
    matched_lines: list[str]
    error: str


@dataclass
class FormatCheck:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


SOURCE_SPECS: tuple[SourceSpec, ...] = (
    SourceSpec(
        "bionic-system-property-private-header",
        "bionic",
        "libc/include/sys/_system_properties.h",
        (
            'PROP_FILENAME "/dev/__properties__"',
        ),
    ),
    SourceSpec(
        "bionic-system-property-public-header",
        "bionic",
        "libc/include/sys/system_properties.h",
        (
            "PROP_VALUE_MAX",
        ),
    ),
    SourceSpec(
        "bionic-system-property-api",
        "bionic",
        "libc/bionic/system_property_api.cpp",
        (
            "__system_properties_init",
            "system_properties.Init(PROP_FILENAME)",
            "__system_property_area_init",
        ),
    ),
    SourceSpec(
        "bionic-system-properties-routing",
        "bionic",
        "libc/system_properties/system_properties.cpp",
        (
            'access("/dev/__properties__/property_info", R_OK)',
            "ContextsSerialized",
            "SystemProperties::Init",
        ),
    ),
    SourceSpec(
        "bionic-contexts-serialized",
        "bionic",
        "libc/system_properties/contexts_serialized.cpp",
        (
            "LoadDefaultPath",
            "MapSerialPropertyArea",
            "GetPropAreaForName",
            "properties_serial",
        ),
    ),
    SourceSpec(
        "bionic-prop-area-header",
        "bionic",
        "libc/system_properties/include/system_properties/prop_area.h",
        (
            "uint32_t magic_",
            "uint32_t version_",
            "uint32_t bytes_used_",
            "char data_[0]",
        ),
    ),
    SourceSpec(
        "bionic-prop-area-impl",
        "bionic",
        "libc/system_properties/prop_area.cpp",
        (
            "PROP_AREA_MAGIC = 0x504f5250",
            "PROP_AREA_VERSION = 0xfc6ed0ab",
            "PA_SIZE = 128 * 1024",
            "O_NOFOLLOW | O_RDONLY",
        ),
    ),
    SourceSpec(
        "bionic-prop-info",
        "bionic",
        "libc/system_properties/include/system_properties/prop_info.h",
        (
            "atomic_uint_least32_t serial",
            "char value[PROP_VALUE_MAX]",
            "char name[0]",
            "long_value",
        ),
    ),
    SourceSpec(
        "property-info-parser-header",
        "system/core",
        "property_service/libpropertyinfoparser/include/property_info_parser/property_info_parser.h",
        (
            "PropertyInfoAreaHeader",
            "current_version",
            "minimum_supported_version",
            "contexts_offset",
            "types_offset",
            "root_offset",
        ),
    ),
    SourceSpec(
        "property-info-parser-impl",
        "system/core",
        "property_service/libpropertyinfoparser/property_info_parser.cpp",
        (
            'LoadPath("/dev/__properties__/property_info")',
            "minimum_supported_version() > 1",
            "size() != mmap_size",
            "GetPropertyInfoIndexes",
        ),
    ),
    SourceSpec(
        "property-info-serializer",
        "system/core",
        "property_service/libpropertyinfoserializer/trie_serializer.cpp",
        (
            "header->current_version = 1",
            "header->minimum_supported_version = 1",
            "header->contexts_offset",
            "header->types_offset",
            "header->root_offset",
        ),
    ),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--v308-manifest", type=Path, default=DEFAULT_V308)
    parser.add_argument("--aosp-ref", default=DEFAULT_AOSP_REF)
    parser.add_argument("--timeout", type=float, default=20.0)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def source_url(spec: SourceSpec, ref: str) -> str:
    return f"{GITILES_BASE}/{spec.project}/+/{ref}/{spec.path}?format=TEXT"


def fetch_source(url: str, timeout: float) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        encoded = response.read()
    return base64.b64decode(encoded).decode("utf-8", errors="replace")


def compact_line(line_number: int, line: str) -> str:
    return f"L{line_number}: {line.strip()[:220]}"


def collect_source_fact(spec: SourceSpec, ref: str, timeout: float) -> SourceFact:
    url = source_url(spec, ref)
    try:
        text = fetch_source(url, timeout)
    except Exception as exc:  # noqa: BLE001 - evidence records source fetch failure
        return SourceFact(
            spec.name,
            spec.project,
            spec.path,
            url,
            False,
            "",
            0,
            list(spec.required_patterns),
            [],
            str(exc),
        )

    matched_lines: list[str] = []
    missing_patterns: list[str] = []
    lines = text.splitlines()
    for pattern in spec.required_patterns:
        matches = [
            compact_line(index, line)
            for index, line in enumerate(lines, start=1)
            if pattern in line
        ]
        if matches:
            matched_lines.extend(matches[:3])
        else:
            missing_patterns.append(pattern)
    return SourceFact(
        spec.name,
        spec.project,
        spec.path,
        url,
        True,
        hashlib.sha256(text.encode("utf-8")).hexdigest(),
        len(text.encode("utf-8")),
        missing_patterns,
        matched_lines,
        "",
    )


def seed_sdk(seed: dict[str, Any]) -> str:
    for entry in seed.get("entries", []):
        if isinstance(entry, dict) and entry.get("key") == "ro.build.version.sdk":
            return str(entry.get("value") or "")
    return ""


def source_by_name(facts: list[SourceFact], name: str) -> SourceFact | None:
    return next((fact for fact in facts if fact.name == name), None)


def build_checks(seed: dict[str, Any],
                 v308: dict[str, Any],
                 facts: list[SourceFact],
                 aosp_ref: str) -> list[FormatCheck]:
    checks: list[FormatCheck] = []
    sdk = seed_sdk(seed)
    all_fetched = all(fact.fetched for fact in facts)
    all_patterns = all(not fact.missing_patterns for fact in facts)
    prop_area = source_by_name(facts, "bionic-prop-area-impl")
    property_info_parser = source_by_name(facts, "property-info-parser-header")
    property_info_serializer = source_by_name(facts, "property-info-serializer")
    routing = source_by_name(facts, "bionic-system-properties-routing")

    checks.append(FormatCheck(
        "target-aosp-ref",
        "pass" if sdk == "31" and aosp_ref.startswith("android-12") else "warn",
        "warning" if sdk != "31" or not aosp_ref.startswith("android-12") else "info",
        f"seed_sdk={sdk}; selected_ref={aosp_ref}",
        [],
        "use an Android 12 AOSP ref for SDK 31 devices",
    ))
    checks.append(FormatCheck(
        "v308-prerequisite",
        "pass" if v308.get("decision") == "private-property-area-proof-needs-format-source" else "warn",
        "warning" if v308.get("decision") != "private-property-area-proof-needs-format-source" else "info",
        f"v308_decision={v308.get('decision')}",
        [str(v308.get("path", ""))],
        "refresh v308 before using this source map" if v308.get("decision") != "private-property-area-proof-needs-format-source" else "",
    ))
    checks.append(FormatCheck(
        "source-fetch",
        "pass" if all_fetched else "blocked",
        "blocker" if not all_fetched else "info",
        f"fetched={sum(1 for fact in facts if fact.fetched)}/{len(facts)}",
        [fact.name for fact in facts if not fact.fetched],
        "restore network or pin source files before continuing" if not all_fetched else "",
    ))
    checks.append(FormatCheck(
        "source-patterns",
        "pass" if all_patterns else "blocked",
        "blocker" if not all_patterns else "info",
        "all required property format markers were found" if all_patterns else "required markers missing in one or more source files",
        [f"{fact.name}: {', '.join(fact.missing_patterns)}" for fact in facts if fact.missing_patterns],
        "inspect changed AOSP source layout before deriving a builder" if not all_patterns else "",
    ))
    checks.append(FormatCheck(
        "prop-area-constants",
        "pass" if prop_area and not prop_area.missing_patterns else "blocked",
        "blocker" if not prop_area or prop_area.missing_patterns else "info",
        "source map confirms prop area magic/version/size and read-only O_NOFOLLOW mapping",
        prop_area.matched_lines if prop_area else [],
        "derive a host-side prop_area file builder from these constants",
    ))
    checks.append(FormatCheck(
        "serialized-property-info",
        "pass" if property_info_parser and property_info_serializer and not property_info_parser.missing_patterns and not property_info_serializer.missing_patterns else "blocked",
        "blocker" if not property_info_parser or not property_info_serializer or property_info_parser.missing_patterns or property_info_serializer.missing_patterns else "info",
        "source map confirms property_info header fields and serializer version 1",
        (property_info_parser.matched_lines if property_info_parser else []) + (property_info_serializer.matched_lines if property_info_serializer else []),
        "derive a host-side property_info serializer/parser compatibility proof",
    ))
    checks.append(FormatCheck(
        "bionic-read-path",
        "pass" if routing and not routing.missing_patterns else "blocked",
        "blocker" if not routing or routing.missing_patterns else "info",
        "source map confirms bionic switches to ContextsSerialized when property_info exists",
        routing.matched_lines if routing else [],
        "future runtime prototype must provide private property_info plus per-context property files",
    ))
    checks.append(FormatCheck(
        "runtime-safety-gate",
        "pass",
        "info",
        "v309 fetches public source only; it performs no device command and creates no runtime property files",
        [],
        "keep v310 host-only until serializer/builder proof passes",
    ))
    return checks


def decide(checks: list[FormatCheck]) -> tuple[str, bool, str, str]:
    blockers = [check for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        names = ", ".join(check.name for check in blockers)
        return "property-format-source-map-blocked", False, f"blocked checks: {names}", "fix source fetch/pattern extraction"
    return (
        "property-format-source-map-ready",
        True,
        "AOSP source facts identify the required property area and property_info structures",
        "v310 host-side property_info/prop_area serializer compatibility proof",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    seed = load_json(args.seed)
    v308 = load_json(args.v308_manifest)
    facts = [collect_source_fact(spec, args.aosp_ref, args.timeout) for spec in SOURCE_SPECS]
    checks = build_checks(seed, v308, facts, args.aosp_ref)
    decision, pass_ok, reason, next_step = decide(checks)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "seed": {"path": seed.get("path"), "present": bool(seed.get("present")), "schema": seed.get("schema"), "policy": seed.get("policy"), "sdk": seed_sdk(seed)},
            "v308": {"path": v308.get("path"), "present": bool(v308.get("present")), "decision": v308.get("decision"), "pass": v308.get("pass")},
            "aosp_ref": args.aosp_ref,
        },
        "model": {
            "scope": "host-only AOSP source map",
            "device_commands_executed": False,
            "runtime_files_created": False,
            "source_count": len(facts),
        },
        "source_facts": [asdict(fact) for fact in facts],
        "checks": [asdict(check) for check in checks],
        "derived_requirements_for_v310": [
            "create a host-only serializer/parser proof for property_info header version 1",
            "create a host-only prop_area file builder proof using magic 0x504f5250, version 0xfc6ed0ab, and PA_SIZE 128 KiB",
            "model private namespace file layout with property_info, properties_serial, and per-context property files",
            "continue blocking global /dev/__properties__, property_service socket, daemon starts, and Wi-Fi bring-up",
        ],
        "blocked_actions": [
            "create global /dev/__properties__",
            "create /dev/socket/property_service",
            "run service-manager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    source_rows = [
        [
            fact["name"],
            fact["project"],
            fact["path"],
            str(fact["fetched"]),
            str(len(fact["missing_patterns"])),
            fact["sha256"][:12],
        ]
        for fact in manifest["source_facts"]
    ]
    check_rows = [
        [check["name"], check["status"], check["severity"], check["detail"], "<br>".join(check["evidence"][:4])]
        for check in manifest["checks"]
    ]
    return "\n".join([
        "# v309 Property Format Source Probe",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- aosp_ref: `{manifest['inputs']['aosp_ref']}`",
        "",
        "## Source Facts",
        "",
        markdown_table(["name", "project", "path", "fetched", "missing", "sha256"], source_rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence"], check_rows),
        "",
        "## Derived Requirements For v310",
        "",
        "\n".join(f"- {item}" for item in manifest["derived_requirements_for_v310"]),
        "",
        "## Blocked Actions",
        "",
        "\n".join(f"- `{item}`" for item in manifest["blocked_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    store = EvidenceStore(repo_path(args.out_dir))
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    source_index = {
        fact["name"]: {
            "url": fact["url"],
            "sha256": fact["sha256"],
            "matched_lines": fact["matched_lines"],
            "missing_patterns": fact["missing_patterns"],
        }
        for fact in manifest["source_facts"]
    }
    store.write_json("source-index.json", source_index)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
