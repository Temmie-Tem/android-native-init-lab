#!/usr/bin/env python3
"""V485 compare Android boot-complete Wi-Fi HAL surface against native crash surface.

This is an offline evidence reducer. It reads prior Android boot-complete
inventory evidence and the latest native V484 crash evidence, then classifies
which runtime gaps should be tested before any Wi-Fi scan/connect/link-up.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ANDROID_DIR = Path("tmp/wifi/v425-settled-handoff-live-20260520-134752/v423-android-hwservice-bootcomplete-run")
DEFAULT_NATIVE_MANIFEST = Path("tmp/wifi/v484-samsung-abort-run-rerun-20260521-045432/manifest.json")
DEFAULT_OUT_DIR = Path("tmp/wifi/v485-native-android-hal-surface-compare")
WIFI_TERMS = (
    "vendor.samsung.hardware.wifi@2.0-service",
    "android.hardware.wifi@1.0-service",
    "servicemanager",
    "hwservicemanager",
    "vndservicemanager",
    "cnss-daemon",
    "cnss_diag",
    "wificond",
    "wpa_supplicant",
)


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("$") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.:-]+", key):
            values[key] = value.strip()
    return values


def process_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("$"):
            continue
        if any(term in line for term in WIFI_TERMS):
            lines.append(line)
    return lines


def find_lines(lines: list[str], term: str) -> list[str]:
    return [line for line in lines if term in line]


def first_context(lines: list[str], term: str) -> str:
    for line in lines:
        if term in line:
            return line.split()[0] if line.split() else ""
    return ""


def first_user(lines: list[str], term: str) -> str:
    for line in lines:
        parts = line.split()
        if term in line and len(parts) >= 2:
            return parts[1]
    return ""


def native_transcript_path(native_manifest_path: Path, manifest: dict[str, Any]) -> Path:
    live = manifest.get("live_result") or {}
    rel = live.get("file")
    if isinstance(rel, str) and rel:
        candidate = native_manifest_path.parent / rel
        if candidate.exists():
            return candidate
    return native_manifest_path.parent / "native/run-iwifi-registration.txt"


def classify(android: dict[str, Any], native: dict[str, Any], checks: list[Check]) -> tuple[str, bool, str, str]:
    missing_blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if missing_blockers:
        return (
            "v485-hal-surface-compare-blocked",
            False,
            "missing required evidence: " + ", ".join(missing_blockers),
            "restore Android reference and V484 native evidence before selecting the next live experiment",
        )

    android_samsung_ok = bool(android["samsung_hal_lines"])
    android_base_ok = bool(android["base_hal_lines"])
    native_crash = native["wifi_hal_signal"] == "6" and native["crash_captured"]
    native_selinux_kernel = native["wifi_hal_selinux_current"] == "kernel" or native["wifi_hal_selinux_exec"] == "kernel"
    android_hal_context_ok = android["samsung_hal_context"] == "u:r:hal_wifi_default:s0"
    companion_gap = android_base_ok and not native["starts_base_hal"]
    vndservice_gap = bool(android["vndservicemanager_lines"]) and not native["starts_vndservicemanager"]

    if android_samsung_ok and android_hal_context_ok and native_crash and native_selinux_kernel:
        next_step = (
            "prioritize SELinux domain handoff proof or Android HAL process surface capture; "
            "dual-HAL/vndservicemanager experiments should stay bounded and no-scan"
        )
        reason = (
            "Android Samsung HAL runs as hal_wifi_default, while native HAL aborts with SELinux context still kernel"
        )
        if companion_gap:
            reason += "; Android also has android.hardware.wifi@1.0-service running"
        if vndservice_gap:
            reason += "; Android also has vndservicemanager running"
        return "v485-hal-surface-domain-and-companion-gap", True, reason, next_step

    if android_samsung_ok and native_crash:
        return (
            "v485-hal-surface-native-crash-android-present",
            True,
            "Android Samsung HAL is present but native HAL still aborts; compare process surface before connect",
            "capture Android HAL /proc details or test missing companion processes with bounded no-scan smoke",
        )

    return (
        "v485-hal-surface-review-required",
        False,
        "comparison did not produce a dominant gap",
        "inspect raw evidence before widening runtime scope",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    android_manifest_path = args.android_dir / "manifest.json"
    android_manifest = load_json(android_manifest_path)
    native_manifest = load_json(args.native_manifest)
    native_text_path = native_transcript_path(args.native_manifest, native_manifest)
    native_text = read_text(native_text_path)
    native_kv = parse_key_values(native_text)
    live = native_manifest.get("live_result") or {}
    capture_keys = live.get("capture_keys") or {}
    composite_keys = live.get("keys") or {}

    process_text = read_text(args.android_dir / "commands/service-processes.txt")
    props_text = read_text(args.android_dir / "commands/identity-props.txt")
    lshal_text = read_text(args.android_dir / "commands/lshal-wifi-filter.txt")
    processes = process_lines(process_text)
    props = parse_key_values(props_text)

    android = {
        "manifest_path": str(android_manifest_path),
        "decision": android_manifest.get("decision") or (android_manifest.get("classification") or {}).get("decision"),
        "pass": android_manifest.get("pass") if "pass" in android_manifest else (android_manifest.get("classification") or {}).get("pass"),
        "process_file": str(args.android_dir / "commands/service-processes.txt"),
        "props_file": str(args.android_dir / "commands/identity-props.txt"),
        "lshal_file": str(args.android_dir / "commands/lshal-wifi-filter.txt"),
        "samsung_hal_lines": find_lines(processes, "vendor.samsung.hardware.wifi@2.0-service"),
        "base_hal_lines": find_lines(processes, "android.hardware.wifi@1.0-service"),
        "vndservicemanager_lines": find_lines(processes, "vndservicemanager"),
        "hwservicemanager_lines": find_lines(processes, "hwservicemanager"),
        "cnss_daemon_lines": find_lines(processes, "cnss-daemon"),
        "cnss_diag_lines": find_lines(processes, "cnss_diag"),
        "wificond_lines": find_lines(processes, "wificond"),
        "supplicant_lines": find_lines(processes, "wpa_supplicant"),
        "samsung_hal_context": first_context(processes, "vendor.samsung.hardware.wifi@2.0-service"),
        "samsung_hal_user": first_user(processes, "vendor.samsung.hardware.wifi@2.0-service"),
        "base_hal_context": first_context(processes, "android.hardware.wifi@1.0-service"),
        "base_hal_user": first_user(processes, "android.hardware.wifi@1.0-service"),
        "props": {
            key: props.get(key, "")
            for key in (
                "sys.boot_completed",
                "init.svc.servicemanager",
                "init.svc.hwservicemanager",
                "init.svc.wificond",
                "init.svc.wpa_supplicant",
                "init.svc.vendor.wifi_hal_ext",
                "init.svc.vendor.wifi_hal",
            )
        },
        "lshal_samsung_lines": [
            line.strip() for line in lshal_text.splitlines()
            if "vendor.samsung.hardware.wifi" in line or "ISehWifi" in line
        ],
    }

    native = {
        "manifest_path": str(args.native_manifest),
        "transcript_path": str(native_text_path),
        "decision": native_manifest.get("decision"),
        "pass": native_manifest.get("pass"),
        "helper_result": live.get("helper_result"),
        "helper_reason": live.get("helper_reason"),
        "micro_query_result": live.get("micro_query_result"),
        "crash_captured": bool(live.get("crash_captured")),
        "wifi_hal_signal": composite_keys.get("child.wifi_hal.signal", ""),
        "wifi_hal_traced": composite_keys.get("child.wifi_hal.traced", ""),
        "wifi_hal_capture_crash": composite_keys.get("child.wifi_hal.capture_crash", ""),
        "wifi_hal_uid": native_kv.get("wifi_hal.identity.after.uid.effective", ""),
        "wifi_hal_gid": native_kv.get("wifi_hal.identity.after.gid.effective", ""),
        "wifi_hal_groups": native_kv.get("wifi_hal.identity.after.groups.values", ""),
        "wifi_hal_selinux_current": native_kv.get("wifi_hal_composite_child.wifi_hal.selinux.current", ""),
        "wifi_hal_selinux_exec": native_kv.get("wifi_hal_composite_child.wifi_hal.selinux.exec", ""),
        "wifi_hal_selinux_target": native_kv.get("wifi_hal_composite_child.wifi_hal.selinux_exec.target_context", ""),
        "property_shim_ready": (
            composite_keys.get("property_service_shim.request.1.name") == "hwservicemanager.ready"
            and composite_keys.get("property_service_shim.request.1.result") == "0x00000000"
        ),
        "postflight_clean": bool((native_manifest.get("postflight") or {}).get("clean")),
        "wifi_bringup_executed": bool(native_manifest.get("wifi_bringup_executed")),
        "starts_base_hal": "android.hardware.wifi@1.0-service" in native_text,
        "starts_vndservicemanager": "vndservicemanager" in native_text,
        "crash_pc_path": capture_keys.get("crash.maprow.pc.path", ""),
        "crash_pc_offset": capture_keys.get("crash.maprow.pc.relative_offset", ""),
        "crash_lr_path": capture_keys.get("crash.maprow.lr.path", ""),
        "crash_lr_offset": capture_keys.get("crash.maprow.lr.relative_offset", ""),
        "crash_frame_paths": [
            {
                "index": index,
                "path": capture_keys.get(f"crash.maprow.frame{index}_ra.path", ""),
                "offset": capture_keys.get(f"crash.maprow.frame{index}_ra.relative_offset", ""),
            }
            for index in range(7)
            if capture_keys.get(f"crash.maprow.frame{index}_ra.path")
        ],
    }

    checks = [
        Check(
            "android-reference-manifest",
            "pass" if android_manifest_path.exists() and android["pass"] else "blocked",
            "blocker",
            f"decision={android['decision']} pass={android['pass']}",
            [str(android_manifest_path)],
            "rerun Android boot-complete hwservice inventory",
        ),
        Check(
            "android-samsung-hal-process",
            "pass" if android["samsung_hal_lines"] else "blocked",
            "blocker",
            f"context={android['samsung_hal_context']} user={android['samsung_hal_user']}",
            android["samsung_hal_lines"][:3],
            "capture Android boot-complete process list with SELinux labels",
        ),
        Check(
            "native-v484-crash",
            "pass" if native["crash_captured"] and native["wifi_hal_signal"] == "6" else "blocked",
            "blocker",
            f"decision={native['decision']} signal={native['wifi_hal_signal']} crash={native['crash_captured']}",
            [str(args.native_manifest), str(native_text_path)],
            "rerun V484 bounded ptrace capture",
        ),
        Check(
            "no-wifi-bringup",
            "pass" if not native["wifi_bringup_executed"] else "blocked",
            "blocker",
            f"wifi_bringup_executed={native['wifi_bringup_executed']}",
            [],
            "do not use this comparison evidence as connect/ping proof",
        ),
        Check(
            "native-postflight-clean",
            "pass" if native["postflight_clean"] else "blocked",
            "blocker",
            f"postflight_clean={native['postflight_clean']}",
            [],
            "recover native runtime before additional HAL experiments",
        ),
        Check(
            "selinux-domain-difference",
            "gap" if native["wifi_hal_selinux_current"] == "kernel" else "pass",
            "finding",
            f"android={android['samsung_hal_context']} native_current={native['wifi_hal_selinux_current']} native_exec={native['wifi_hal_selinux_exec']} target={native['wifi_hal_selinux_target']}",
            android["samsung_hal_lines"][:1],
            "prove real post-exec domain transition before scan/connect",
        ),
        Check(
            "android-base-hal-companion",
            "gap" if android["base_hal_lines"] and not native["starts_base_hal"] else "pass",
            "finding",
            f"android_base_hal={bool(android['base_hal_lines'])} native_starts_base_hal={native['starts_base_hal']}",
            android["base_hal_lines"][:1],
            "test bounded dual-HAL start only if domain handoff remains unresolved",
        ),
        Check(
            "android-vndservicemanager-companion",
            "gap" if android["vndservicemanager_lines"] and not native["starts_vndservicemanager"] else "pass",
            "finding",
            f"android_vndservicemanager={bool(android['vndservicemanager_lines'])} native_starts_vndservicemanager={native['starts_vndservicemanager']}",
            android["vndservicemanager_lines"][:1],
            "consider bounded vndservicemanager start-only only after HAL/domain analysis",
        ),
    ]
    decision, pass_ok, reason, next_step = classify(android, native, checks)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "inputs": {
            "android_dir": str(args.android_dir),
            "native_manifest": str(args.native_manifest),
            "native_transcript": str(native_text_path),
        },
        "android": android,
        "native": native,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest["checks"]
    rows = "\n".join(
        f"| {check['name']} | {check['status']} | {check['detail']} |"
        for check in checks
    )
    native = manifest["native"]
    android = manifest["android"]
    frames = "\n".join(
        f"- frame{item['index']}: `{item['path']}` `{item['offset']}`"
        for item in native["crash_frame_paths"]
    ) or "- none"
    return "\n".join(
        [
            "# V485 Native/Android HAL Surface Compare",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            "## Android Surface",
            "",
            f"- Samsung HAL context/user: `{android['samsung_hal_context']}` / `{android['samsung_hal_user']}`",
            f"- Base HAL context/user: `{android['base_hal_context']}` / `{android['base_hal_user']}`",
            f"- Props: `{json.dumps(android['props'], sort_keys=True)}`",
            "",
            "## Native Surface",
            "",
            f"- native decision: `{native['decision']}`",
            f"- HAL uid/gid/groups: `{native['wifi_hal_uid']}` / `{native['wifi_hal_gid']}` / `{native['wifi_hal_groups']}`",
            f"- HAL SELinux current/exec/target: `{native['wifi_hal_selinux_current']}` / `{native['wifi_hal_selinux_exec']}` / `{native['wifi_hal_selinux_target']}`",
            f"- crash pc/lr: `{native['crash_pc_path']}:{native['crash_pc_offset']}` / `{native['crash_lr_path']}:{native['crash_lr_offset']}`",
            "",
            "## Crash Frames",
            "",
            frames,
            "",
            "## Checks",
            "",
            "| Check | Status | Detail |",
            "| --- | --- | --- |",
            rows,
            "",
            "## Safety",
            "",
            "- This comparison executed no device commands.",
            "- It is not Wi-Fi connect or external ping proof.",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-dir", type=Path, default=DEFAULT_ANDROID_DIR)
    parser.add_argument("--native-manifest", type=Path, default=DEFAULT_NATIVE_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.command == "plan":
        manifest = {
            "generated_at": now_iso(),
            "decision": "v485-hal-surface-compare-plan-ready",
            "pass": True,
            "reason": "plan-only; no files parsed and no device command executed",
            "next_step": "run V485 comparison against Android reference and V484 native evidence",
            "inputs": {
                "android_dir": str(args.android_dir),
                "native_manifest": str(args.native_manifest),
            },
            "device_commands_executed": False,
            "device_mutations": False,
            "wifi_bringup_executed": False,
            "external_ping_executed": False,
        }
    else:
        manifest = build_manifest(args)
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.out_dir / "summary.md").write_text(render_summary(manifest) if args.command == "run" else "# V485 HAL Surface Compare Plan\n", encoding="utf-8")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print("device_commands_executed: False")
    print("wifi_bringup_executed: False")
    print(f"evidence: {args.out_dir.resolve()}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
