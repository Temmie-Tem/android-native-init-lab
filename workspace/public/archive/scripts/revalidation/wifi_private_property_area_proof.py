#!/usr/bin/env python3
"""Host-only proof model for a private read-only Android property area."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v308-private-property-area-proof")
DEFAULT_SEED = Path("tmp/wifi/v301-property-shim-seed-android/seed.json")
DEFAULT_V297 = Path("tmp/wifi/v297-android-property-capture-android/manifest.json")
DEFAULT_V307 = Path("tmp/wifi/v307-property-shim-design/manifest.json")
REQUIRED_KEYS = (
    "ro.build.version.sdk",
    "ro.product.name",
    "ro.hardware",
    "ro.vendor.build.version.sdk",
)
PROPERTY_VALUE_MAX = 92
PROPERTY_VALUE_PAYLOAD_MAX = PROPERTY_VALUE_MAX - 1
PROPERTY_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass
class SeedValidation:
    key: str
    state: str
    source: str
    value: str
    readonly: bool
    value_len: int
    status: str
    detail: str


@dataclass
class RuntimeEvidence:
    name: str
    status: str
    detail: str
    evidence: list[str]


@dataclass
class ProofCheck:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=Path, default=DEFAULT_SEED)
    parser.add_argument("--v297-manifest", type=Path, default=DEFAULT_V297)
    parser.add_argument("--v307-manifest", type=Path, default=DEFAULT_V307)
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


def read_capture_text(v297_manifest: dict[str, Any], relative_path: str) -> str:
    manifest_path = Path(str(v297_manifest.get("path", "")))
    if not manifest_path:
        return ""
    capture_path = manifest_path.parent / relative_path
    if not capture_path.exists():
        return ""
    return capture_path.read_text(encoding="utf-8", errors="replace")


def seed_entries(seed: dict[str, Any]) -> list[dict[str, Any]]:
    entries = seed.get("entries", [])
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def validate_seed(seed: dict[str, Any]) -> list[SeedValidation]:
    by_key = {str(entry.get("key")): entry for entry in seed_entries(seed)}
    validations: list[SeedValidation] = []
    for key in REQUIRED_KEYS:
        entry = by_key.get(key, {})
        value = str(entry.get("value") or "")
        state = str(entry.get("state") or "missing")
        source = str(entry.get("source") or "missing")
        readonly = key.startswith("ro.")
        value_len = len(value.encode("utf-8"))
        issues: list[str] = []
        if state != "ready":
            issues.append(f"state={state}")
        if not value:
            issues.append("empty-value")
        if not readonly:
            issues.append("not-readonly")
        if not PROPERTY_NAME_RE.match(key):
            issues.append("invalid-name-characters")
        if value_len > PROPERTY_VALUE_PAYLOAD_MAX:
            issues.append(f"value-too-long>{PROPERTY_VALUE_PAYLOAD_MAX}")
        if any(ord(ch) < 0x20 for ch in value):
            issues.append("control-character-in-value")
        status = "pass" if not issues else "fail"
        validations.append(
            SeedValidation(
                key=key,
                state=state,
                source=source,
                value=value,
                readonly=readonly,
                value_len=value_len,
                status=status,
                detail="ok" if not issues else ", ".join(issues),
            )
        )
    return validations


def collect_runtime_evidence(v297_manifest: dict[str, Any]) -> list[RuntimeEvidence]:
    runtime_paths = read_capture_text(v297_manifest, "commands/property-runtime-paths.txt")
    area_list = read_capture_text(v297_manifest, "commands/property-area-list.txt")
    required_props = read_capture_text(v297_manifest, "commands/required-props.txt")

    runtime_lines = [line for line in runtime_paths.splitlines() if line and not line.startswith("$")]
    area_lines = [
        line for line in area_list.splitlines()
        if line and not line.startswith("$") and not line.startswith("rc=")
    ]
    prop_lines = [
        line for line in required_props.splitlines()
        if line and not line.startswith("$") and not line.startswith("rc=")
    ]

    return [
        RuntimeEvidence(
            "android-property-dir-visible",
            "seen" if "/dev/__properties__" in runtime_paths else "missing",
            "Android capture showed /dev/__properties__ directory metadata"
            if "/dev/__properties__" in runtime_paths else "Android capture did not show /dev/__properties__",
            runtime_lines[:8],
        ),
        RuntimeEvidence(
            "android-property-service-socket-protected",
            "protected" if "property_service: Permission denied" in runtime_paths else "unknown",
            "Android capture could not inspect the property service socket as shell"
            if "property_service: Permission denied" in runtime_paths else "property service socket permission state is not proven",
            runtime_lines[:8],
        ),
        RuntimeEvidence(
            "android-property-area-files",
            "not-listed" if not area_lines else "listed",
            "find produced no visible files under /dev/__properties__; binary area layout remains unproven"
            if not area_lines else "capture listed property area files",
            area_lines[:20],
        ),
        RuntimeEvidence(
            "android-required-props",
            "captured" if len(prop_lines) >= len(REQUIRED_KEYS) else "partial",
            f"captured_lines={len(prop_lines)}",
            prop_lines[:8],
        ),
    ]


def build_checks(seed: dict[str, Any],
                 v297_manifest: dict[str, Any],
                 v307_manifest: dict[str, Any],
                 seed_checks: list[SeedValidation],
                 runtime: list[RuntimeEvidence]) -> list[ProofCheck]:
    checks: list[ProofCheck] = []
    seed_ok = bool(seed.get("present")) and all(item.status == "pass" for item in seed_checks)
    v297_ok = bool(v297_manifest.get("present")) and v297_manifest.get("decision") == "android-property-capture-pass"
    v307_ok = bool(v307_manifest.get("present")) and v307_manifest.get("selected_next_prototype") == "private-readonly-property-area"
    area_files = next((item for item in runtime if item.name == "android-property-area-files"), None)

    checks.append(ProofCheck(
        "android-backed-seed",
        "pass" if seed_ok else "blocked",
        "blocker" if not seed_ok else "info",
        "selected read-only seed keys are ready and within conservative property value limits"
        if seed_ok else "seed is missing or contains invalid selected entries",
        "rerun v300/v297/v298/v301 chain before any property shim proof" if not seed_ok else "",
    ))
    checks.append(ProofCheck(
        "capture-provenance",
        "pass" if v297_ok else "blocked",
        "blocker" if not v297_ok else "info",
        f"v297 decision={v297_manifest.get('decision')}",
        "refresh Android capture before trusting seed values" if not v297_ok else "",
    ))
    checks.append(ProofCheck(
        "design-selection",
        "pass" if v307_ok else "blocked",
        "blocker" if not v307_ok else "info",
        f"v307 selected={v307_manifest.get('selected_next_prototype')}",
        "rerun v307 design model before v308 proof" if not v307_ok else "",
    ))
    checks.append(ProofCheck(
        "private-readonly-scope",
        "pass" if seed_ok else "blocked",
        "blocker" if not seed_ok else "info",
        "all selected keys are ro.*; model forbids persist.*, ctl.*, property writes, and global /dev mutation",
        "keep runtime prototype inside private namespace only",
    ))
    checks.append(ProofCheck(
        "android-property-area-format",
        "not-proven" if area_files is None or area_files.status != "listed" else "needs-parser",
        "blocker",
        "Android capture did not expose property area files, so this repo still lacks a device-derived binary format sample"
        if area_files is None or area_files.status != "listed"
        else "property area files were listed, but parser/builder compatibility is still unproven",
        "build an AOSP-source-backed property area/property_info format proof before runtime node creation",
    ))
    checks.append(ProofCheck(
        "property-info-compatibility",
        "not-proven",
        "blocker",
        "property context parsing exists, but serialized property_info compatibility for bionic lookup is not proven",
        "derive or import a host-side property_info serializer proof before private runtime files",
    ))
    checks.append(ProofCheck(
        "runtime-safety-gate",
        "pass",
        "info",
        "v308 performs no ADB/device command, no /dev node creation, no socket creation, and no daemon execution",
        "separate approval is required for any future runtime prototype",
    ))
    return checks


def decide(checks: list[ProofCheck]) -> tuple[str, bool, str, str]:
    hard_seed_blockers = [
        check for check in checks
        if check.severity == "blocker" and check.status == "blocked"
    ]
    if hard_seed_blockers:
        names = ", ".join(check.name for check in hard_seed_blockers)
        return "private-property-area-proof-blocked", False, f"blocked checks: {names}", "refresh missing prerequisite artifacts"
    format_blockers = [
        check for check in checks
        if check.severity == "blocker" and check.status in {"not-proven", "needs-parser"}
    ]
    if format_blockers:
        names = ", ".join(check.name for check in format_blockers)
        return "private-property-area-proof-needs-format-source", True, f"seed is valid, but format proof is missing: {names}", "v309 AOSP property area/property_info format extractor"
    return "private-property-area-proof-ready-for-runtime-plan", True, "format proof gates passed", "plan private namespace runtime prototype"


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    seed = load_json(args.seed)
    v297 = load_json(args.v297_manifest)
    v307 = load_json(args.v307_manifest)
    seed_checks = validate_seed(seed)
    runtime = collect_runtime_evidence(v297)
    checks = build_checks(seed, v297, v307, seed_checks, runtime)
    decision, pass_ok, reason, next_step = decide(checks)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "seed": {"path": seed.get("path"), "present": bool(seed.get("present")), "schema": seed.get("schema"), "policy": seed.get("policy")},
            "v297": {"path": v297.get("path"), "present": bool(v297.get("present")), "decision": v297.get("decision"), "pass": v297.get("pass")},
            "v307": {"path": v307.get("path"), "present": bool(v307.get("present")), "decision": v307.get("decision"), "pass": v307.get("pass"), "selected_next": v307.get("selected_next_prototype")},
        },
        "model": {
            "scope": "host-only proof model",
            "runtime_files_created": False,
            "device_commands_executed": False,
            "property_value_payload_max": PROPERTY_VALUE_PAYLOAD_MAX,
            "private_namespace_only": True,
            "selected_keys": list(REQUIRED_KEYS),
        },
        "seed_checks": [asdict(item) for item in seed_checks],
        "android_runtime_evidence": [asdict(item) for item in runtime],
        "checks": [asdict(item) for item in checks],
        "allowed_next_actions": [
            "inspect AOSP bionic/system/core property area and property_info source",
            "build host-side format extractor/proof from source and captured contexts",
            "keep generated artifacts under tmp/wifi evidence directories",
        ],
        "blocked_actions": [
            "create global /dev/__properties__",
            "create /dev/socket/property_service",
            "write persist.* or ctl.* properties",
            "start service-manager, hwservicemanager, Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        ],
        "references": [
            "https://source.android.com/docs/core/architecture/configuration/sysprops-apis",
            "https://android.googlesource.com/platform/system/core.git/+/master/init/property_service.cpp",
            "https://android.googlesource.com/platform/bionic/+/master/libc/include/sys/system_properties.h",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    input_rows = [
        [name, str(item["present"]), str(item.get("decision", item.get("policy"))), str(item["path"])]
        for name, item in manifest["inputs"].items()
    ]
    seed_rows = [
        [item["key"], item["status"], item["source"], str(item["readonly"]), str(item["value_len"]), item["detail"]]
        for item in manifest["seed_checks"]
    ]
    runtime_rows = [
        [item["name"], item["status"], item["detail"], "<br>".join(item["evidence"][:4])]
        for item in manifest["android_runtime_evidence"]
    ]
    check_rows = [
        [item["name"], item["status"], item["severity"], item["detail"], item["next_step"]]
        for item in manifest["checks"]
    ]
    return "\n".join([
        "# v308 Private Property Area Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Inputs",
        "",
        markdown_table(["name", "present", "decision/policy", "path"], input_rows),
        "",
        "## Seed Validation",
        "",
        markdown_table(["key", "status", "source", "readonly", "value_len", "detail"], seed_rows),
        "",
        "## Android Runtime Evidence",
        "",
        markdown_table(["name", "status", "detail", "evidence"], runtime_rows),
        "",
        "## Proof Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next_step"], check_rows),
        "",
        "## Blocked Actions",
        "",
        "\n".join(f"- `{item}`" for item in manifest["blocked_actions"]),
        "",
        "## References",
        "",
        "\n".join(f"- <{item}>" for item in manifest["references"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    store = EvidenceStore(repo_path(args.out_dir))
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
