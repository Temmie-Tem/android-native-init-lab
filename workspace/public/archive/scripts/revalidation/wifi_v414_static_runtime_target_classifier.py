#!/usr/bin/env python3
"""V414 host-only classifier for V413 Wi-Fi VINTF declarations.

This turns the broad V413 declaration inventory into ranked target candidates
for later V411 runtime-registration comparison.  It reads existing V413 evidence
only; it executes no bridge/device command and performs no device mutation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_V413_MANIFEST = Path("tmp/wifi/v413-vintf-live-20260520-120842/manifest.json")
DEFAULT_OUT_DIR = Path("tmp/wifi/v414-static-runtime-target-classifier")

WIFI_RE = re.compile(r"wifi|supplicant|hostapd", re.IGNORECASE)
NON_IWIFI_RE = re.compile(
    r"hostapd|supplicant|wifidisplay|keystore|offload|wifilearner|wifimyftm",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CandidateRecord:
    source_path: str
    source_kind: str
    root_tag: str
    root_type: str
    hal_format: str
    package: str
    version: str
    interface: str
    instance: str
    transport: str
    fqinstance: str
    runtime_match_patterns: list[str]
    role: str
    score: int
    score_reason: list[str]


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v413-manifest", type=Path, default=DEFAULT_V413_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    with resolved.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} is not a JSON object")
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(parent: ET.Element, name: str) -> str:
    for child in list(parent):
        if local_name(child.tag) == name and child.text:
            return child.text.strip()
    return ""


def children(parent: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(parent) if local_name(child.tag) == name]


def xml_payload(text: str) -> str:
    starts = [idx for idx in (text.find("<manifest"), text.find("<compatibility-matrix")) if idx >= 0]
    if not starts:
        return text
    return text[min(starts):]


def parse_xml(text: str) -> ET.Element | None:
    try:
        return ET.fromstring(xml_payload(text))
    except ET.ParseError:
        return None


def source_kind(source_path: str, root_tag: str, root_type: str) -> str:
    if "compatibility_matrix.device.xml" in source_path:
        return "device-compatibility-matrix"
    if "compatibility_matrix" in source_path:
        return "framework-compatibility-matrix"
    if "/system_ext/" in source_path or "/system/system_ext/" in source_path:
        return "system-ext-manifest"
    if root_tag == "manifest" and root_type:
        return f"{root_type}-manifest"
    if root_tag == "manifest":
        return "manifest"
    return root_tag or "unknown"


def infer_role(kind: str) -> str:
    if "compatibility-matrix" in kind:
        return "declared-requirement"
    if "manifest" in kind:
        return "declared-provider"
    return "unknown"


def combine_fqinstance(package: str, version: str, interface: str, instance: str) -> str:
    if package and version and interface and instance:
        return f"{package}@{version}::{interface}/{instance}"
    if package and interface and instance:
        return f"{package}::{interface}/{instance}"
    if package and version and interface:
        return f"{package}@{version}::{interface}"
    if package and interface:
        return f"{package}::{interface}"
    return package


def runtime_match_patterns(package: str, version: str, interface: str, instance: str) -> list[str]:
    if not package or not interface:
        return []
    versions: list[str] = []
    range_match = re.fullmatch(r"(\d+)\.(\d+)-(\d+)", version)
    single_match = re.fullmatch(r"(\d+)\.(\d+)", version)
    if range_match:
        major = range_match.group(1)
        start_minor = int(range_match.group(2))
        end_minor = int(range_match.group(3))
        versions = [f"{major}.{minor}" for minor in range(start_minor, end_minor + 1)]
    elif single_match:
        versions = [version]
    else:
        versions = [version] if version else [""]
    patterns: list[str] = []
    for item in versions:
        if item and instance:
            patterns.append(f"{package}@{item}::{interface}/{instance}")
        elif item:
            patterns.append(f"{package}@{item}::{interface}")
        elif instance:
            patterns.append(f"{package}::{interface}/{instance}")
        else:
            patterns.append(f"{package}::{interface}")
    return patterns


def normalize_fqname(package: str, fqname: str) -> tuple[str, str, str, str]:
    value = fqname.strip()
    version = ""
    interface = ""
    instance = ""
    if value.startswith("@") and "::" in value and "/" in value:
        version, rest = value[1:].split("::", 1)
        interface, instance = rest.split("/", 1)
    elif "::" in value and "/" in value:
        interface, instance = value.split("::", 1)[1].split("/", 1)
    elif "/" in value:
        interface, instance = value.split("/", 1)
    else:
        interface = value
    return package, version, interface, instance


def score_record(package: str, interface: str, instance: str, kind: str, role: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    combined = f"{package} {interface} {instance}"
    if kind == "device-compatibility-matrix":
        score += 40
        reasons.append("device-matrix")
    if role == "declared-provider":
        score += 25
        reasons.append("provider-manifest")
    if package == "vendor.samsung.hardware.wifi":
        score += 80
        reasons.append("samsung-primary-wifi-package")
    elif package == "android.hardware.wifi":
        score += 55
        reasons.append("android-primary-wifi-package")
    elif package.startswith("vendor.") and "wifi" in package:
        score += 30
        reasons.append("vendor-wifi-package")
    elif "wifi" in package:
        score += 15
        reasons.append("wifi-package")
    if interface in {"ISehWifi", "IWifi"}:
        score += 50
        reasons.append("primary-wifi-interface")
    if instance == "default":
        score += 15
        reasons.append("default-instance")
    if NON_IWIFI_RE.search(combined):
        score -= 70
        reasons.append("non-iwifi-domain")
    return score, reasons


def capture_source_path(command: str) -> str:
    parts = command.split()
    if len(parts) >= 2 and parts[0] == "cat":
        return parts[1]
    return ""


def parse_records_from_capture(source_path: str, text: str) -> list[CandidateRecord]:
    root = parse_xml(text)
    if root is None:
        return []
    root_tag = local_name(root.tag)
    root_type = root.attrib.get("type", "")
    kind = source_kind(source_path, root_tag, root_type)
    role = infer_role(kind)
    records: list[CandidateRecord] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for hal in root.iter():
        if local_name(hal.tag) != "hal":
            continue
        package = child_text(hal, "name")
        if not WIFI_RE.search(package):
            any_wifi_child = any(WIFI_RE.search((child.text or "")) for child in hal.iter())
            if not any_wifi_child:
                continue
        versions = [item.text.strip() for item in children(hal, "version") if item.text and item.text.strip()] or [""]
        transport = child_text(hal, "transport")
        hal_format = hal.attrib.get("format", "hidl")
        fqnames = [item.text.strip() for item in children(hal, "fqname") if item.text and item.text.strip()]
        for fqname in fqnames:
            fq_package, fq_version, interface, instance = normalize_fqname(package, fqname)
            version = fq_version or versions[0]
            fqinstance = combine_fqinstance(fq_package, version, interface, instance)
            if not WIFI_RE.search(fqinstance):
                continue
            key = (source_path, fqinstance, interface, instance, version)
            if key in seen:
                continue
            seen.add(key)
            score, reasons = score_record(fq_package, interface, instance, kind, role)
            records.append(CandidateRecord(source_path, kind, root_tag, root_type, hal_format, fq_package, version, interface, instance, transport, fqinstance, runtime_match_patterns(fq_package, version, interface, instance), role, score, reasons))
        for interface_node in children(hal, "interface"):
            interface = child_text(interface_node, "name")
            instances = [
                item.text.strip()
                for item in children(interface_node, "instance") + children(interface_node, "regex-instance")
                if item.text and item.text.strip()
            ] or [""]
            for version in versions:
                for instance in instances:
                    fqinstance = combine_fqinstance(package, version, interface, instance)
                    if not WIFI_RE.search(fqinstance):
                        continue
                    key = (source_path, fqinstance, interface, instance, version)
                    if key in seen:
                        continue
                    seen.add(key)
                    score, reasons = score_record(package, interface, instance, kind, role)
                    records.append(CandidateRecord(source_path, kind, root_tag, root_type, hal_format, package, version, interface, instance, transport, fqinstance, runtime_match_patterns(package, version, interface, instance), role, score, reasons))
    return records


def load_records(v413: dict[str, Any]) -> list[CandidateRecord]:
    if not v413.get("present"):
        return []
    base_dir = Path(str(v413["path"])).parent
    records: list[CandidateRecord] = []
    for capture in v413.get("captures", []):
        if not isinstance(capture, dict) or not str(capture.get("name", "")).startswith("cat-vintf-"):
            continue
        if not capture.get("ok"):
            continue
        rel_file = capture.get("file")
        source_path = capture_source_path(str(capture.get("command", "")))
        if not isinstance(rel_file, str) or not source_path:
            continue
        path = base_dir / rel_file
        if not path.exists():
            continue
        records.extend(parse_records_from_capture(source_path, path.read_text(encoding="utf-8", errors="replace")))
    deduped: list[CandidateRecord] = []
    seen: set[tuple[str, str, str, str]] = set()
    for record in sorted(records, key=lambda item: (-item.score, item.fqinstance, item.source_path)):
        key = (record.fqinstance, record.source_kind, record.source_path, record.role)
        if key not in seen:
            deduped.append(record)
            seen.add(key)
    return deduped


def add_check(checks: list[Check], name: str, status: str, detail: str, evidence: list[str], next_step: str) -> None:
    checks.append(Check(name, status, detail, evidence, next_step))


def build_checks(v413: dict[str, Any], records: list[CandidateRecord], primary: CandidateRecord | None) -> list[Check]:
    checks: list[Check] = []
    add_check(
        checks,
        "v413-source",
        "pass" if v413.get("decision") == "v413-vintf-wifi-declarations-ready" and v413.get("pass") else "blocked",
        f"decision={v413.get('decision')} pass={v413.get('pass')}",
        [str(v413.get("path", ""))],
        "rerun V413 read-only collector if stale or missing",
    )
    add_check(
        checks,
        "structured-records",
        "pass" if records else "blocked",
        f"record_count={len(records)}",
        [record.fqinstance for record in records[:12]],
        "inspect V413 XML captures if no records parse",
    )
    add_check(
        checks,
        "primary-target",
        "pass" if primary else "review",
        primary.fqinstance if primary else "no ranked primary target",
        [primary.source_path] if primary else [],
        "compare primary target against V411 runtime registration evidence",
    )
    return checks


def decide(v413: dict[str, Any], records: list[CandidateRecord], primary: CandidateRecord | None) -> tuple[str, bool, str, str]:
    if not v413.get("present"):
        return "v414-static-runtime-target-classifier-missing-v413", False, "V413 manifest missing", "run V413 read-only declaration collector"
    if not records:
        return "v414-static-runtime-target-classifier-no-records", False, "no structured Wi-Fi declaration records parsed", "inspect V413 XML captures"
    if primary:
        return (
            "v414-static-runtime-targets-ready",
            True,
            f"ranked {len(records)} static Wi-Fi declaration records; primary={primary.fqinstance}",
            "compare ranked static targets against V411 binderized runtime registrations after helper v27 deploy",
        )
    return (
        "v414-static-runtime-target-classifier-review",
        True,
        f"ranked {len(records)} records but no primary target crossed threshold",
        "manually inspect records before selecting micro query target",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# V414 Static Runtime Target Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- source_v413_manifest: `{manifest['source_v413_manifest']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Top Targets",
        "",
    ]
    for record in manifest["top_records"][:12]:
        lines.append(f"- score={record['score']} `{record['fqinstance']}` source=`{record['source_kind']}` reasons={','.join(record['score_reason'])}")
        if record["runtime_match_patterns"]:
            lines.append(f"  runtime_match={','.join(record['runtime_match_patterns'])}")
    lines.extend(["", "## Checks", ""])
    for check in manifest["checks"]:
        lines.append(f"- {check['status']} `{check['name']}`: {check['detail']}")
    return "\n".join(lines) + "\n"


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    source = repo_path(args.v413_manifest)
    v413 = load_json(args.v413_manifest)
    records = load_records(v413)
    primary = records[0] if records and records[0].score >= 100 else None
    checks = build_checks(v413, records, primary)
    decision, pass_ok, reason, next_step = decide(v413, records, primary)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "source_v413_manifest": str(source),
        "source_v413_decision": str(v413.get("decision") or ""),
        "record_count": len(records),
        "primary_target": asdict(primary) if primary else None,
        "top_records": [asdict(record) for record in records[:24]],
        "all_records": [asdict(record) for record in records],
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "explicitly_not_approved": [
            "helper deploy",
            "servicemanager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, driver bind/unbind, firmware mutation, Android partition write",
        ],
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"record_count: {manifest['record_count']}")
    if manifest["primary_target"]:
        print(f"primary_target: {manifest['primary_target']['fqinstance']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
