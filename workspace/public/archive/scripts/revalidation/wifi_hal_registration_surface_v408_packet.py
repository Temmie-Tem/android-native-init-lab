#!/usr/bin/env python3
"""V408 Wi-Fi HAL registration/service-surface evidence packet.

This is a host-only evidence classifier.  It consumes the already-approved V407
composite HAL start-only transcript and decides whether the captured process,
Binder/HwBinder, hwservice context, and library-map evidence is strong enough to
route the next gate.

It never contacts the device, starts daemons, starts the Wi-Fi HAL, scans,
connects, links up, writes credentials, changes routing, or mutates partitions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_V407_MANIFEST = Path("tmp/wifi/v407-composite-hal-start-only-retry-live-20260520-101410/manifest.json")
DEFAULT_OUT_PARENT = Path("tmp/wifi")
DECISION_PASS = "v408-hal-registration-service-surface-evidence-ready"
DECISION_BLOCKED = "v408-hal-registration-service-surface-evidence-blocked"


@dataclass(frozen=True)
class LineHit:
    line: int
    text: str


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v407-manifest", type=Path, default=DEFAULT_V407_MANIFEST)
    parser.add_argument("--transcript", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    return parser.parse_args()


def latest_v407_manifest() -> Path:
    candidates = sorted(DEFAULT_OUT_PARENT.glob("v407-composite-hal-start-only-retry-live-*/manifest.json"))
    if not candidates:
        return DEFAULT_V407_MANIFEST
    return candidates[-1]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a JSON object")
    return data


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def parse_kv(lines: Iterable[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    key_re = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
    for line in lines:
        match = key_re.match(line.strip())
        if match:
            parsed[match.group(1)] = match.group(2)
    return parsed


def find_hits(lines: Iterable[str], patterns: Iterable[str]) -> list[LineHit]:
    compiled = [re.compile(pattern) for pattern in patterns]
    hits: list[LineHit] = []
    for line_no, line in enumerate(lines, start=1):
        if any(pattern.search(line) for pattern in compiled):
            hits.append(LineHit(line_no, line.strip()))
    return hits


def has_all(text: str, needles: Iterable[str]) -> tuple[bool, list[str]]:
    missing = [needle for needle in needles if needle not in text]
    return not missing, missing


def add_check(checks: list[Check], name: str, passed: bool, severity: str, detail: str,
              evidence: Iterable[str], next_step: str) -> None:
    checks.append(Check(name, "pass" if passed else "blocked", severity, detail, list(evidence), next_step))


def collect_host_metadata() -> dict[str, str]:
    return {
        "cwd": str(Path.cwd()),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": platform.python_version(),
    }


def child_capture_ok(kv: dict[str, str], child: str) -> bool:
    prefix = f"wifi_hal_composite_start.child.{child}."
    required = ("child_started", "observable", "proc_status_captured", "fd_summary_captured", "maps_summary_captured", "postflight_safe")
    return all(kv.get(prefix + key) == "1" for key in required)


def build_manifest(v407_manifest_path: Path, transcript_path: Path, out_dir: Path) -> dict[str, Any]:
    v407 = load_json(v407_manifest_path)
    lines = read_lines(transcript_path)
    text = "\n".join(lines)
    kv = parse_kv(lines)

    checks: list[Check] = []

    v407_pass = (
        v407.get("decision") == "v407-composite-hal-start-only-retry-pass"
        and v407.get("pass") is True
        and v407.get("wifi_bringup_executed") is False
        and (v407.get("postflight") or {}).get("clean") is True
        and (v407.get("live_result") or {}).get("helper_result") == "start-only-pass"
    )
    add_check(
        checks,
        "v407-start-only-pass",
        v407_pass,
        "blocker",
        f"decision={v407.get('decision')} pass={v407.get('pass')} wifi_bringup={v407.get('wifi_bringup_executed')}",
        [str(v407_manifest_path)],
        "rerun or inspect V407 before classifying service surface",
    )

    boundary_needles = [
        "wifi_hal_composite_start.scan_connect_linkup=0",
        "wifi_hal_composite_start.wificond=0",
        "wifi_hal_composite_start.supplicant=0",
        "wifi_hal_composite_start.hostapd=0",
        "wifi_hal_composite_start.cnss_diag=0",
    ]
    boundary_ok, boundary_missing = has_all(text, boundary_needles)
    add_check(
        checks,
        "no-bringup-boundary",
        boundary_ok,
        "blocker",
        "required zero-action markers present" if boundary_ok else "missing " + ", ".join(boundary_missing),
        [hit.text for hit in find_hits(lines, [r"wifi_hal_composite_start\.(scan_connect_linkup|wificond|supplicant|hostapd|cnss_diag)="])],
        "do not route beyond start-only without explicit scan/connect/link-up gate",
    )

    manager_ok = all(kv.get(f"wifi_hal_composite_start.child.{child}.child_started") == "1" for child in ("servicemanager", "hwservicemanager", "wifi_hal"))
    add_check(
        checks,
        "composite-children-started",
        manager_ok,
        "blocker",
        "servicemanager/hwservicemanager/wifi_hal child_started=1 expected",
        [hit.text for hit in find_hits(lines, [r"wifi_hal_composite_start\.child\.(servicemanager|hwservicemanager|wifi_hal)\.child_started="])],
        "keep composite namespace gate before service-surface classification",
    )

    binder_needles = [
        "context.dev_binder.exists=1",
        "context.dev_binder.rdev=10:81",
        "context.dev_hwbinder.exists=1",
        "context.dev_hwbinder.rdev=10:80",
        "context.dev_vndbinder.exists=1",
        "context.dev_vndbinder.rdev=10:79",
    ]
    binder_ok, binder_missing = has_all(text, binder_needles)
    add_check(
        checks,
        "private-binder-devnodes",
        binder_ok,
        "blocker",
        "private Binder/HwBinder/VndBinder nodes present" if binder_ok else "missing " + ", ".join(binder_missing),
        [hit.text for hit in find_hits(lines, [r"context\.dev_(binder|hwbinder|vndbinder)\.(exists|rdev)="])],
        "fix private devnode provisioning before further HAL work",
    )

    hwservice_needles = [
        "context.plat_hwservice_contexts.exists=1",
        "context.system_ext_hwservice_contexts.exists=1",
        "context.vendor_hwservice_contexts.exists=1",
    ]
    hwservice_ok, hwservice_missing = has_all(text, hwservice_needles)
    add_check(
        checks,
        "hwservice-context-inputs",
        hwservice_ok,
        "blocker",
        "plat/system_ext/vendor hwservice context files present" if hwservice_ok else "missing " + ", ".join(hwservice_missing),
        [hit.text for hit in find_hits(lines, [r"context\.(plat|system_ext|vendor)_hwservice_contexts\.exists="])],
        "restore hwservice context inputs before registration proof",
    )

    wifi_hal_capture_ok = child_capture_ok(kv, "wifi_hal")
    hwsm_capture_ok = child_capture_ok(kv, "hwservicemanager")
    add_check(
        checks,
        "wifi-hal-observable-capture",
        wifi_hal_capture_ok,
        "blocker",
        "wifi_hal child started, observable, proc/fd/maps captured, postflight safe",
        [hit.text for hit in find_hits(lines, [r"wifi_hal_composite_start\.child\.wifi_hal\.(child_started|observable|proc_status_captured|fd_summary_captured|maps_summary_captured|postflight_safe)="])],
        "extend helper capture before using this as service-surface evidence",
    )
    add_check(
        checks,
        "hwservicemanager-observable-capture",
        hwsm_capture_ok,
        "blocker",
        "hwservicemanager child started, observable, proc/fd/maps captured, postflight safe",
        [hit.text for hit in find_hits(lines, [r"wifi_hal_composite_start\.child\.hwservicemanager\.(child_started|observable|proc_status_captured|fd_summary_captured|maps_summary_captured|postflight_safe)="])],
        "extend helper capture before querying registration state",
    )

    map_needles = [
        "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service",
        "/root/dev/hwbinder",
        "/lib64/libhidlbase.so",
        "/lib64/android.hardware.wifi@1.0.so",
        "/vendor/lib64/vendor.samsung.hardware.wifi@2.0.so",
    ]
    maps_ok, maps_missing = has_all(text, map_needles)
    add_check(
        checks,
        "wifi-hal-hidl-hwbinder-maps",
        maps_ok,
        "blocker",
        "HAL maps include target, hwbinder, libhidlbase, Android Wi-Fi HIDL, Samsung Wi-Fi HIDL" if maps_ok else "missing " + ", ".join(maps_missing),
        [hit.text for hit in find_hits(lines, [
            r"vendor\.samsung\.hardware\.wifi@2\.0-service",
            r"/dev/hwbinder",
            r"libhidlbase\.so",
            r"android\.hardware\.wifi@1\.0\.so",
            r"vendor\.samsung\.hardware\.wifi@2\.0\.so",
        ])[:20]],
        "do not attempt registration proof until HAL maps show HIDL/HwBinder surface",
    )

    fatal_hits = find_hits(lines, [
        r"CANNOT LINK EXECUTABLE",
        r"\blibrary .* not found\b",
        r"\bFatal signal\b",
        r"\bSegmentation fault\b",
        r"\bAborted\b",
        r"\bavc: denied\b",
    ])
    add_check(
        checks,
        "fatal-runtime-noise-absent",
        not fatal_hits,
        "blocker",
        f"fatal_hit_count={len(fatal_hits)}",
        [f"{hit.line}: {hit.text}" for hit in fatal_hits[:12]],
        "classify runtime blocker before any broader Wi-Fi gate",
    )

    postflight_ok = (
        (v407.get("postflight") or {}).get("clean") is True
        and (v407.get("live_result") or {}).get("all_postflight_safe") is True
        and kv.get("wifi_hal_composite_start.all_postflight_safe") == "1"
    )
    add_check(
        checks,
        "postflight-clean",
        postflight_ok,
        "blocker",
        "helper and host postflight clean expected",
        [hit.text for hit in find_hits(lines, [r"wifi_hal_composite_start\.all_postflight_safe=", r"wifi_hal_composite_start\.result=", r"wifi_hal_composite_start\.reason="])],
        "recover or reboot before further live Wi-Fi probes",
    )

    blockers = [check.name for check in checks if check.status != "pass" and check.severity == "blocker"]
    decision = DECISION_BLOCKED if blockers else DECISION_PASS
    pass_ok = not blockers

    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": "all V407 registration/service-surface evidence checks passed" if pass_ok else "blocked by " + ", ".join(blockers),
        "next_step": "plan V409 bounded hwservicemanager/service-list registration query; keep Wi-Fi bring-up blocked",
        "host": collect_host_metadata(),
        "source": {
            "v407_manifest": str(v407_manifest_path),
            "transcript": str(transcript_path),
            "out_dir": str(out_dir),
        },
        "v407": {
            "decision": v407.get("decision"),
            "pass": v407.get("pass"),
            "reason": v407.get("reason"),
            "wifi_bringup_executed": v407.get("wifi_bringup_executed"),
            "helper_result": (v407.get("live_result") or {}).get("helper_result"),
        },
        "checks": [asdict(check) for check in checks],
        "evidence_limits": [
            "This packet proves service-surface readiness from process, fd/map, and context evidence.",
            "It does not prove actual hwservicemanager publication/listing.",
            "It does not start wificond, supplicant, hostapd, scan, connect, link-up, DHCP, routing, or credentials.",
        ],
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
    }


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    def clean(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", "<br>")

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(clean(str(value)) for value in row) + " |")
    return "\n".join(lines)


def render_readme(manifest: dict[str, Any]) -> str:
    rows = [
        [
            check["name"],
            check["status"],
            check["severity"],
            check["detail"],
            "<br>".join(check["evidence"][:6]),
            check["next_step"],
        ]
        for check in manifest["checks"]
    ]
    return "\n".join([
        "# V408 Wi-Fi HAL Registration/Service-Surface Evidence Packet",
        "",
        "## Summary",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "- device_commands_executed: `False`",
        "- device_mutations: `False`",
        "- wifi_bringup_executed: `False`",
        "",
        "## Source",
        "",
        f"- V407 manifest: `{manifest['source']['v407_manifest']}`",
        f"- V407 transcript: `{manifest['source']['transcript']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "severity", "detail", "evidence", "next"], rows),
        "",
        "## Boundary",
        "",
        "- This packet classifies existing V407 evidence only.",
        "- Actual hwservicemanager service publication/listing remains a later gate.",
        "- Scan/connect/link-up, credentials, DHCP, routing, and Wi-Fi bring-up remain blocked.",
        "",
    ])


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=False)
    os.chmod(path, 0o700)


def safe_write_text(path: Path, text: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def main() -> int:
    args = parse_args()
    v407_manifest = args.v407_manifest
    if v407_manifest == DEFAULT_V407_MANIFEST and not v407_manifest.exists():
        v407_manifest = latest_v407_manifest()
    transcript = args.transcript or v407_manifest.parent / "native" / "run-composite-hal.txt"
    out_dir = args.out_dir or DEFAULT_OUT_PARENT / f"v408-hal-registration-surface-packet-{now_stamp()}"
    if not v407_manifest.exists():
        raise FileNotFoundError(v407_manifest)
    if not transcript.exists():
        raise FileNotFoundError(transcript)

    ensure_private_dir(out_dir)
    manifest = build_manifest(v407_manifest, transcript, out_dir)
    safe_write_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    safe_write_text(out_dir / "README.md", render_readme(manifest))
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "reason": manifest["reason"],
        "out_dir": str(out_dir),
        "device_commands_executed": manifest["device_commands_executed"],
        "wifi_bringup_executed": manifest["wifi_bringup_executed"],
    }, indent=2, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
