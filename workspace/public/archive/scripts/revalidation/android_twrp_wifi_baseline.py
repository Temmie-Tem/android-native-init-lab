#!/usr/bin/env python3
"""Collect Android/TWRP read-only Wi-Fi driver and firmware baseline evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


WIFI_KEYWORDS = (
    "wlan",
    "wifi",
    "qca",
    "qcacld",
    "cnss",
    "wcn",
    "wcnss",
    "ath",
    "bdwlan",
    "qwlan",
    "wlanmdsp",
    "wificond",
    "supplicant",
    "hostapd",
    "cfg80211",
    "nl80211",
    "mac80211",
)

ACTIVE_WIFI_PATTERNS = (
    re.compile(r"\brfkill\s+unblock\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\s+set-wifi-enabled\b", re.IGNORECASE),
    re.compile(r"(?:^|[;&]\s*)(?:wpa_supplicant|hostapd)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/class/rfkill", re.IGNORECASE),
)

EXCLUDED_DEFAULT_PATHS = (
    "/data/misc/wifi",
    "dumpsys wifi",
    "cmd wifi status",
    "wpa_cli",
)

COMMON_ADB_COMMANDS: tuple[tuple[str, str, int], ...] = (
    (
        "identity-props",
        "for p in ro.product.model ro.build.fingerprint ro.boot.verifiedbootstate "
        "ro.boot.vbmeta.device_state ro.boot.flash.locked ro.boot.warranty_bit "
        "ro.boot.hardware ro.boot.revision ro.boot.slot_suffix ro.boot.veritymode; "
        "do echo \"$p=$(getprop $p)\"; done",
        15,
    ),
    ("uname", "uname -a", 10),
    ("id", "id", 10),
    ("ip-link", "ip link", 20),
    ("netdev-fallback", "ifconfig -a 2>/dev/null || toybox ip link 2>/dev/null || true", 20),
    (
        "sysfs-net-rfkill",
        "ls -l /sys/class/net /sys/class/rfkill 2>/dev/null || true",
        20,
    ),
    (
        "rfkill-detail",
        "for n in /sys/class/rfkill/rfkill*; do "
        "[ -e \"$n\" ] || continue; "
        "echo \"node=$n\"; "
        "for f in name type state soft hard; do "
        "[ -e \"$n/$f\" ] && echo \"$f=$(cat \"$n/$f\" 2>/dev/null)\"; "
        "done; "
        "done",
        20,
    ),
    (
        "proc-modules-wifi",
        "cat /proc/modules 2>/dev/null | grep -Ei "
        "'wlan|wifi|qca|qcacld|cnss|wcn|wcnss|ath|cfg80211|mac80211' || true",
        20,
    ),
    ("proc-cmdline", "cat /proc/cmdline 2>/dev/null || true", 15),
    (
        "dmesg-wifi-tail",
        "dmesg 2>/dev/null | grep -Ei "
        "'wlan|wifi|qca|qcacld|cnss|wcn|wcnss|firmware|cfg80211|nl80211|mac80211' "
        "| tail -n 200 || true",
        30,
    ),
    (
        "wifi-props",
        "getprop | grep -Ei 'wifi|wlan|qca|qcacld|cnss|wcn|firmware' || true",
        20,
    ),
    (
        "wifi-paths",
        "find /vendor /odm /product /system -maxdepth 6 "
        "\\( -iname '*wifi*' -o -iname '*wlan*' -o -iname '*qca*' "
        "-o -iname '*qcacld*' -o -iname '*cnss*' -o -iname '*wcn*' "
        "-o -iname '*wcnss*' -o -iname '*bdwlan*' -o -iname '*qwlan*' "
        "-o -iname '*wlanmdsp*' -o -iname '*wificond*' "
        "-o -iname '*supplicant*' -o -iname '*hostapd*' \\) "
        "2>/dev/null | head -n 600 || true",
        45,
    ),
    (
        "vintf-wifi",
        "grep -RHiE 'android\\.hardware\\.wifi|vendor.*wifi|supplicant|hostapd|wificond' "
        "/vendor/etc/vintf /odm/etc/vintf /system/etc/vintf 2>/dev/null || true",
        30,
    ),
    (
        "initrc-wifi",
        "grep -RHiE 'wlan|wifi|qca|qcacld|cnss|wcn|wificond|supplicant|hostapd' "
        "/vendor/etc/init /odm/etc/init /system/etc/init 2>/dev/null || true",
        30,
    ),
    (
        "firmware-paths",
        "find /vendor/firmware /vendor/firmware_mnt /vendor/etc/wifi /odm/etc/wifi "
        "/product/etc/wifi /system/etc/wifi -maxdepth 6 "
        "\\( -iname '*wlan*' -o -iname '*wifi*' -o -iname '*qca*' "
        "-o -iname '*cnss*' -o -iname '*wcn*' -o -iname '*wcnss*' "
        "-o -iname '*bdwlan*' -o -iname '*qwlan*' -o -iname '*wlanmdsp*' "
        "-o -iname '*Data.msc*' \\) 2>/dev/null | head -n 400 || true",
        45,
    ),
)

DECISIONS = {
    "blocked-no-android-kernel-gate",
    "driver-candidate-found",
    "ready-for-readonly-nl80211-probe-plan",
    "manual-review-required",
}


@dataclass
class HostCapture:
    mode: str
    name: str
    command: str
    ok: bool
    rc: int | None
    duration_sec: float
    file: str
    text: str
    error: str


def default_out_dir() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "wifi" / f"v204-android-twrp-baseline-{stamp}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-adb", action="store_true", help="collect Android ADB read-only baseline")
    parser.add_argument("--twrp-adb", action="store_true", help="collect TWRP ADB read-only baseline")
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", help="optional adb serial")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v203-manifest", type=Path, default=Path("tmp/wifi/v203-baseline/manifest.json"))
    parser.add_argument("--include-sensitive", "--include-sensitive-default-off", dest="include_sensitive", action="store_true", help="reserved; default collector still avoids sensitive Wi-Fi material")
    return parser.parse_args()


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(psk|password|passphrase|ssid|bssid)=([^\s]+)", r"\1=<redacted>", text)
    text = re.sub(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|serialno)=([^\s]+)", r"\1=<redacted>", text)
    return text


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command.extend(["-s", args.serial])
    return command


def run_host_command(command: list[str], timeout: int) -> tuple[int, str, float]:
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout, time.monotonic() - started


def validate_no_active_wifi_commands() -> None:
    joined = "\n".join(command for _, command, _ in COMMON_ADB_COMMANDS)
    for excluded in EXCLUDED_DEFAULT_PATHS:
        if excluded in joined:
            raise RuntimeError(f"sensitive/default-excluded Wi-Fi command token found: {excluded}")
    for pattern in ACTIVE_WIFI_PATTERNS:
        if pattern.search(joined):
            raise RuntimeError(f"active Wi-Fi command pattern found: {pattern.pattern}")


def write_capture(store: EvidenceStore, mode: str, name: str, text: str) -> str:
    path = store.write_text(f"{mode}/commands/{safe_name(name)}.txt", text.rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def capture_adb_shell(store: EvidenceStore,
                      args: argparse.Namespace,
                      mode: str,
                      name: str,
                      shell_command: str,
                      timeout: int) -> HostCapture:
    full_command = [*adb_base(args), "shell", shell_command]
    try:
        rc, text, duration = run_host_command(full_command, timeout=max(timeout, args.timeout))
        error = ""
    except Exception as exc:  # noqa: BLE001 - evidence collector preserves failure detail
        rc = None
        text = ""
        error = str(exc)
        duration = float(max(timeout, args.timeout))
    body = f"$ {' '.join(full_command)}\n{redact_text(text if text else error)}\nrc={rc}\n"
    relative = write_capture(store, mode, name, body)
    manifest_text = redact_text(text)
    if len(manifest_text) > 4096:
        manifest_text = manifest_text[:4096] + "\n[truncated in manifest]\n"
    return HostCapture(
        mode=mode,
        name=name,
        command=" ".join(full_command),
        ok=rc == 0,
        rc=rc,
        duration_sec=duration,
        file=relative,
        text=manifest_text,
        error=error,
    )


def adb_wait(store: EvidenceStore, args: argparse.Namespace, mode: str) -> HostCapture:
    full_command = [*adb_base(args), "wait-for-device"]
    try:
        rc, text, duration = run_host_command(full_command, timeout=args.timeout)
        error = ""
    except Exception as exc:  # noqa: BLE001 - evidence collector preserves failure detail
        rc = None
        text = ""
        error = str(exc)
        duration = float(args.timeout)
    body = f"$ {' '.join(full_command)}\n{redact_text(text if text else error)}\nrc={rc}\n"
    relative = write_capture(store, mode, "adb-wait-for-device", body)
    return HostCapture(mode, "adb-wait-for-device", " ".join(full_command), rc == 0, rc, duration, relative, redact_text(text), error)


def collect_mode(store: EvidenceStore, args: argparse.Namespace, mode: str) -> list[HostCapture]:
    captures = [adb_wait(store, args, mode)]
    for name, command, timeout in COMMON_ADB_COMMANDS:
        captures.append(capture_adb_shell(store, args, mode, name, command, timeout))
    return captures


def load_v203_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    return {
        "present": True,
        "path": str(resolved),
        "pass": payload.get("pass"),
        "decision": payload.get("decision"),
        "missing_gates": payload.get("missing_gates", []),
        "candidate_paths": payload.get("candidate_paths", []),
        "reason": payload.get("reason"),
    }


def capture_lines(captures: list[HostCapture], names: tuple[str, ...]) -> list[str]:
    lines: list[str] = []
    for capture in captures:
        if capture.name not in names:
            continue
        for line in capture.text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("$"):
                continue
            if "grep -" in stripped or "find /" in stripped:
                continue
            lines.append(stripped)
    return lines


def unique_matches(lines: list[str], patterns: tuple[str, ...], limit: int = 80) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for line in lines:
        if any(pattern.search(line) for pattern in compiled):
            if line not in seen:
                seen.add(line)
                out.append(line)
            if len(out) >= limit:
                break
    return out


def classify_captures(captures: list[HostCapture]) -> dict[str, list[str]]:
    net_lines = capture_lines(captures, ("ip-link", "netdev-fallback", "sysfs-net-rfkill"))
    rfkill_lines = capture_lines(captures, ("rfkill-detail", "sysfs-net-rfkill"))
    module_lines = capture_lines(captures, ("proc-modules-wifi",))
    firmware_lines = capture_lines(captures, ("firmware-paths", "proc-cmdline"))
    hal_lines = capture_lines(captures, ("vintf-wifi", "wifi-paths"))
    init_lines = capture_lines(captures, ("initrc-wifi", "wifi-paths"))
    log_lines = capture_lines(captures, ("dmesg-wifi-tail",))
    wifi_rfkill = [
        line for line in unique_matches(rfkill_lines, (r"type=wifi", r"name=.*(?:wifi|wlan|80211|cnss)", r"(?:wifi|wlan|80211|cnss).*rfkill"))
        if "bt_power" not in line.lower() and "bluetooth" not in line.lower()
    ][:80]
    return {
        "interface_evidence": unique_matches(net_lines, (r"\b(?:wlan\d+|swlan\d+|p2p\d+|phy\d+|wifi-aware)\b",)),
        "rfkill_evidence": wifi_rfkill,
        "module_evidence": unique_matches(module_lines, (r"\b(?:wlan|qcacld|qca|cnss|wcn|wcnss|ath|cfg80211|mac80211)\b",)),
        "firmware_evidence": unique_matches(firmware_lines, (r"bdwlan", r"qwlan", r"wlanmdsp", r"Data\.msc", r"WCNSS", r"firmware_class\.path", r"/vendor/firmware", r"/vendor/etc/wifi")),
        "hal_evidence": unique_matches(hal_lines, (r"android\.hardware\.wifi", r"vendor.*wifi", r"supplicant", r"hostapd")),
        "init_service_evidence": unique_matches(init_lines, (r"/init/.*wifi", r"wifi\.rc", r"wificond\.rc", r"service .*wifi", r"service .*wlan", r"cnss")),
        "kernel_log_evidence": unique_matches(log_lines, (r"firmware", r"cfg80211", r"nl80211", r"qcacld", r"cnss", r"icnss", r"wlan", r"wifi")),
    }


def decide(classification: dict[str, list[str]], mode_count: int, ok_capture_count: int) -> tuple[str, str]:
    if mode_count == 0 or ok_capture_count == 0:
        return "manual-review-required", "no successful Android/TWRP ADB evidence capture"
    has_interface = bool(classification["interface_evidence"])
    has_rfkill = bool(classification["rfkill_evidence"])
    has_module = bool(classification["module_evidence"])
    has_kernel_log = bool(classification["kernel_log_evidence"])
    has_driver_candidate = any(
        classification[key]
        for key in ("module_evidence", "firmware_evidence", "hal_evidence", "init_service_evidence", "kernel_log_evidence")
    )
    if has_interface or has_rfkill or has_module:
        return "ready-for-readonly-nl80211-probe-plan", "Android/TWRP exposes WLAN interface, Wi-Fi rfkill, or loaded wireless module evidence"
    if has_driver_candidate:
        return "driver-candidate-found", "Android/TWRP exposes Wi-Fi driver/firmware/HAL/init/log candidates but native gate remains missing"
    return "blocked-no-android-kernel-gate", "Android/TWRP baseline did not expose WLAN/rfkill/module/log evidence"


def build_compare(v203: dict[str, Any], classification: dict[str, list[str]], decision: str, reason: str) -> dict[str, Any]:
    return {
        "v203": v203,
        "v204_decision": decision,
        "v204_reason": reason,
        "classification_counts": {key: len(value) for key, value in classification.items()},
        "native_missing_gates": v203.get("missing_gates", []),
        "android_twrp_kernel_gate_present": bool(
            classification["interface_evidence"] or
            classification["rfkill_evidence"] or
            classification["module_evidence"]
        ),
    }


def build_report(args: argparse.Namespace,
                 host_metadata: dict[str, Any],
                 v203: dict[str, Any],
                 captures: list[HostCapture],
                 classification: dict[str, list[str]],
                 decision: str,
                 reason: str,
                 pass_ok: bool) -> str:
    modes = []
    if args.android_adb:
        modes.append("android")
    if args.twrp_adb:
        modes.append("twrp")
    rows = [
        ["result", "PASS" if pass_ok else "FAIL", reason],
        ["decision", decision, "no active Wi-Fi approval"],
        ["modes", ", ".join(modes), f"captures={len(captures)}"],
        ["v203", str(v203.get("decision", "missing")), ", ".join(v203.get("missing_gates", []))],
    ]
    lines = [
        "# A90 Android/TWRP Wi-Fi Driver and Firmware Baseline",
        "",
        f"- generated: `{dt.datetime.now(dt.timezone.utc).isoformat()}`",
        f"- result: `{'PASS' if pass_ok else 'FAIL'}`",
        f"- decision: `{decision}`",
        f"- reason: `{reason}`",
        f"- modes: `{', '.join(modes)}`",
        "",
        "## Summary Matrix",
        "",
        markdown_table(["area", "status", "detail"], rows),
        "",
        "## Classification",
        "",
    ]
    for key, values in classification.items():
        lines.append(f"### {key}")
        lines.append("")
        if values:
            lines.extend(f"- `{value}`" for value in values[:40])
        else:
            lines.append("- none")
        lines.append("")
    lines.extend([
        "## Guardrails",
        "",
        "- no Wi-Fi enablement",
        "- no rfkill write",
        "- no WLAN link-up",
        "- no module load/unload",
        "- no firmware mutation",
        "- no supplicant/hostapd/vendor daemon start",
        "- no `/data/misc/wifi` default collection",
        "",
        "## Host Metadata",
        "",
        "```json",
        json.dumps(host_metadata, ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    validate_no_active_wifi_commands()
    if not args.android_adb and not args.twrp_adb:
        raise SystemExit("select at least one mode: --android-adb and/or --twrp-adb")
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    host_metadata = collect_host_metadata()
    v203 = load_v203_manifest(args.v203_manifest)
    captures: list[HostCapture] = []

    if args.android_adb:
        captures.extend(collect_mode(store, args, "android"))
    if args.twrp_adb:
        captures.extend(collect_mode(store, args, "twrp"))

    classification = classify_captures(captures)
    ok_capture_count = sum(1 for capture in captures if capture.ok)
    mode_count = int(args.android_adb) + int(args.twrp_adb)
    decision, reason = decide(classification, mode_count, ok_capture_count)
    compare = build_compare(v203, classification, decision, reason)
    pass_ok = decision in DECISIONS and ok_capture_count > 0

    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "modes": {
            "android_adb": args.android_adb,
            "twrp_adb": args.twrp_adb,
        },
        "include_sensitive": args.include_sensitive,
        "v203": v203,
        "classification": classification,
        "classification_counts": {key: len(value) for key, value in classification.items()},
        "captures": [asdict(capture) for capture in captures],
        "host_metadata": host_metadata,
        "guardrails": {
            "wifi_enablement": "forbidden",
            "rfkill_write": "forbidden",
            "wlan_link_up": "forbidden",
            "module_mutation": "forbidden",
            "firmware_mutation": "forbidden",
            "supplicant_hostapd_start": "forbidden",
            "sensitive_wifi_data_default": "excluded",
        },
    }
    report = build_report(args, host_metadata, v203, captures, classification, decision, reason, pass_ok)
    store.write_json("manifest.json", manifest)
    store.write_json("compare/v203-v204-matrix.json", compare)
    store.write_text("summary.md", report.rstrip() + "\n")
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
