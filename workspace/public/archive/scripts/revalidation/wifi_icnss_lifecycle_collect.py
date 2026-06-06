#!/usr/bin/env python3
"""Collect read-only ICNSS/CNSS lifecycle evidence for native Wi-Fi planning."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    DEFAULT_EXPECT_VERSION,
    REPO_ROOT,
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
)
from a90harness.evidence import EvidenceStore


ICNSS_NODE = "/sys/devices/platform/soc/18800000.qcom,icnss"
ICNSS_DRIVER = "/sys/bus/platform/drivers/icnss"

ACTIVE_PATTERNS = (
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\bNL80211_CMD_TRIGGER_SCAN\b", re.IGNORECASE),
    re.compile(r"\bNL80211_CMD_SET_INTERFACE\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\s+set-wifi-enabled\b", re.IGNORECASE),
    re.compile(r">\s*/sys/class/rfkill", re.IGNORECASE),
    re.compile(r">\s*/sys/module/firmware_class/parameters/path", re.IGNORECASE),
    re.compile(r">\s*/sys/bus/platform/drivers/icnss/(?:bind|unbind)", re.IGNORECASE),
    re.compile(
        r"(?:^|[;&]\s*)(?:/[^ ]*/)?(?:cnss-daemon|cnss_diag|wificond|wpa_supplicant|hostapd)\b",
        re.IGNORECASE,
    ),
)

SENSITIVE_DEFAULT_EXCLUDES = (
    "/data/misc/wifi",
    "cmd wifi status",
    "dumpsys wifi",
    "wpa_cli",
)

WIFI_TERMS = (
    "wifi",
    "wlan",
    "wificond",
    "supplicant",
    "hostapd",
    "cnss",
    "icnss",
    "wcn",
    "wcnss",
    "qca",
    "qcacld",
    "qmi",
    "qrtr",
    "firmware",
    "bdwlan",
    "regdb",
    "bdf",
    "nl80211",
    "cfg80211",
    "pdr",
    "ssr",
    "ramdump",
)

NATIVE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 15.0),
    ("status", ["status"], 25.0),
    ("bootstatus", ["bootstatus"], 25.0),
    ("firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 20.0),
    ("icnss-uevent", ["cat", f"{ICNSS_NODE}/uevent"], 20.0),
    ("icnss-node", ["ls", ICNSS_NODE], 20.0),
    ("icnss-driver", ["ls", ICNSS_DRIVER], 20.0),
    ("icnss-tree", ["run", "/cache/bin/toybox", "find", ICNSS_NODE, "-maxdepth", "6"], 35.0),
    ("debug-root", ["ls", "/sys/kernel/debug"], 20.0),
    ("debug-icnss-tree", ["run", "/cache/bin/toybox", "find", "/sys/kernel/debug", "-maxdepth", "5"], 45.0),
    ("sys-class-net", ["ls", "/sys/class/net"], 20.0),
    ("sys-class-rfkill", ["ls", "/sys/class/rfkill"], 20.0),
    ("sys-class-ieee80211", ["ls", "/sys/class/ieee80211"], 20.0),
    ("proc-modules", ["run", "/cache/bin/toybox", "cat", "/proc/modules"], 30.0),
    ("proc-net-wireless", ["run", "/cache/bin/toybox", "cat", "/proc/net/wireless"], 20.0),
    ("dmesg", ["run", "/cache/bin/toybox", "dmesg"], 60.0),
)

ADB_COMMANDS: tuple[tuple[str, str, int], ...] = (
    (
        "identity-props",
        "for p in ro.product.model ro.build.fingerprint ro.boot.hardware "
        "ro.boot.verifiedbootstate ro.boot.vbmeta.device_state sys.boot_completed; "
        "do echo \"$p=$(getprop $p)\"; done",
        15,
    ),
    (
        "wifi-cnss-props",
        "getprop | grep -Ei 'init\\.svc\\..*(wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|qca)|"
        "ro\\.boottime\\..*(wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|qca)|"
        "wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|wcn|qca|qcacld|qmi|qrtr|"
        "qmiproxy|sysmon|service-notifier|rmtfs|rmt_storage|pd-mapper|tqftp|tftp|tftp_server|firmware' || true",
        25,
    ),
    (
        "processes-wifi-cnss",
        "ps -AZ 2>/dev/null | grep -Ei 'wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|wcn|qca|qcacld|qmi|qrtr|"
        "qmiproxy|sysmon|service-notifier|rmtfs|rmt_storage|pd-mapper|tqftp|tftp|tftp_server|perfd|servicemanager' || "
        "ps -A 2>/dev/null | grep -Ei 'wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|wcn|qca|qcacld|qmi|qrtr|"
        "qmiproxy|sysmon|service-notifier|rmtfs|rmt_storage|pd-mapper|tqftp|tftp|tftp_server|perfd|servicemanager' || true",
        25,
    ),
    (
        "initrc-wifi-cnss",
        "grep -RHiE 'service .*("
        "wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|wcn|qca|qmi|qrtr|qmiproxy|"
        "sysmon|service-notifier|rmtfs|rmt_storage|pd-mapper|tqftp|tftp|tftp_server|perfd)|"
        "on property:.*(wifi|wlan|cnss|icnss|wcn|qca|qmi|qrtr|rmtfs|rmt_storage|pd-mapper|tqftp|tftp)|"
        "class_start .*wifi|class .*wifi|capabilities .*NET_(RAW|ADMIN)|group .*net_(raw|admin)|"
        "firmware|vendor\\.wifi|android\\.hardware\\.wifi|wlan_pd|pdr|service_notifier' "
        "/system/etc/init /system_ext/etc/init /vendor/etc/init /odm/etc/init /product/etc/init 2>/dev/null || true",
        45,
    ),
    (
        "sysfs-icnss-net",
        f"for p in {ICNSS_NODE} /sys/class/net/wlan0 /sys/class/net/swlan0 "
        "/sys/class/net/p2p0 /sys/class/net/wifi-aware0 /sys/class/ieee80211 /sys/class/rfkill; do "
        "echo \"path=$p\"; ls -ld \"$p\" 2>/dev/null || true; readlink -f \"$p\" 2>/dev/null || true; done",
        25,
    ),
    (
        "icnss-tree",
        f"find {ICNSS_NODE} -maxdepth 7 2>/dev/null | sort || true",
        35,
    ),
    (
        "rfkill-detail",
        "for r in /sys/class/rfkill/rfkill*; do [ -e \"$r\" ] || continue; echo \"node=$r\"; "
        "for f in name type state soft hard persistent; do [ -e \"$r/$f\" ] && echo \"$f=$(cat \"$r/$f\" 2>/dev/null)\"; done; "
        "readlink -f \"$r/device\" 2>/dev/null || true; done",
        25,
    ),
    (
        "ieee80211-tree",
        "find /sys/class/ieee80211 -maxdepth 5 2>/dev/null | sort || true",
        25,
    ),
    (
        "firmware-class-path",
        "cat /sys/module/firmware_class/parameters/path 2>/dev/null || true",
        15,
    ),
    (
        "firmware-candidates",
        "find /vendor/firmware_mnt /vendor/firmware /vendor/etc/wifi /odm/etc/wifi "
        "/product/etc/wifi /system/etc/wifi -maxdepth 8 "
        "\\( -iname '*wlan*' -o -iname '*wifi*' -o -iname '*qca*' -o -iname '*qcacld*' "
        "-o -iname '*cnss*' -o -iname '*icnss*' -o -iname '*wcn*' -o -iname '*wcnss*' "
        "-o -iname '*bdwlan*' -o -iname '*regdb*' -o -iname '*qwlan*' -o -iname '*wlanmdsp*' "
        "-o -iname '*Data.msc*' \\) 2>/dev/null | sort | head -n 800 || true",
        45,
    ),
    (
        "devnodes-sockets-wifi",
        "ls -l /dev/cnss* /dev/qrtr* /dev/qmi* /dev/adsprpc* /dev/socket 2>/dev/null | "
        "grep -Ei 'wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|qmi|qrtr|qca|vendor' || true",
        25,
    ),
    (
        "dmesg-wifi-cnss-tail",
        "dmesg 2>/dev/null | grep -Ei 'wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|wcn|qca|qcacld|firmware|qmi|qrtr|"
        "qmiproxy|sysmon|service-notifier|wlan_pd|rmtfs|rmt_storage|pd-mapper|tqftp|tftp|tftp_server|bdf|bdwlan|regdb|nl80211|cfg80211|pdr|ssr' | tail -n 800 || true",
        60,
    ),
    (
        "logcat-wifi-cnss-tail",
        "logcat -d -v threadtime 2>/dev/null | grep -Ei 'wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|wcn|qca|qcacld|firmware|qmi|qrtr|"
        "qmiproxy|sysmon|service-notifier|wlan_pd|rmtfs|rmt_storage|pd-mapper|tqftp|tftp|tftp_server|bdf|bdwlan|regdb|nl80211|cfg80211|pdr|ssr' | tail -n 800 || true",
        75,
    ),
)

DECISIONS = {
    "lifecycle-map-ready",
    "android-only-required",
    "insufficient-live-evidence",
    "manual-review-required",
}


@dataclass
class CaptureRecord:
    mode: str
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    text: str
    error: str


def default_out_dir() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "wifi" / f"v215-icnss-cnss-lifecycle-{stamp}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native-bridge", action="store_true", help="collect native read-only bridge evidence")
    parser.add_argument("--android-adb", action="store_true", help="collect Android ADB read-only evidence")
    parser.add_argument("--twrp-adb", action="store_true", help="collect TWRP ADB read-only evidence")
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", help="optional adb serial")
    parser.add_argument("--su", action="store_true", help="run Android shell captures through su -c")
    parser.add_argument("--host", "--bridge-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v204-android-manifest", type=Path, default=Path("tmp/wifi/v204-android-baseline/manifest.json"))
    parser.add_argument("--v206-manifest", type=Path, default=Path("tmp/wifi/v206-android-icnss-cnss-map/manifest.json"))
    parser.add_argument("--v214-manifest", type=Path, default=Path("tmp/wifi/v214-icnss-reprobe/manifest.json"))
    return parser.parse_args()


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(psk|password|passphrase|ssid|bssid)=([^\s]+)", r"\1=<redacted>", text)
    text = re.sub(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|ro\.boot\.serialno|serialno)=([^\s]+)", r"\1=<redacted>", text)
    return text


def validate_no_active_commands() -> None:
    joined = "\n".join(" ".join(argv) for _, argv, _ in NATIVE_COMMANDS)
    joined += "\n" + "\n".join(command for _, command, _ in ADB_COMMANDS)
    for token in SENSITIVE_DEFAULT_EXCLUDES:
        if token in joined:
            raise RuntimeError(f"sensitive/default-excluded Wi-Fi command token found: {token}")
    for pattern in ACTIVE_PATTERNS:
        if pattern.search(joined):
            raise RuntimeError(f"active command pattern found: {pattern.pattern}")


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command.extend(["-s", args.serial])
    return command


def adb_shell_command(args: argparse.Namespace, shell_command: str) -> list[str]:
    if args.su:
        return [*adb_base(args), "shell", "su", "-c", shlex.quote(shell_command)]
    return [*adb_base(args), "shell", shell_command]


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


def write_capture(store: EvidenceStore, mode: str, name: str, text: str) -> str:
    path = store.write_text(f"{mode}/commands/{safe_name(name)}.txt", redact_text(text).rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def truncate_manifest_text(text: str, limit: int = 8192) -> str:
    text = redact_text(text)
    if len(text) > limit:
        return text[:limit] + "\n[truncated in manifest]\n"
    return text


def capture_native(store: EvidenceStore,
                   args: argparse.Namespace,
                   name: str,
                   command: list[str],
                   timeout: float) -> CaptureRecord:
    capture = run_capture(args, name, command, timeout=timeout)
    body = capture.text if capture.text else f"{capture.error}\n"
    relative = write_capture(store, "native", name, body)
    data = capture_to_manifest(capture)
    return CaptureRecord(
        mode="native",
        name=name,
        command=" ".join(command),
        ok=bool(data["ok"]),
        rc=data.get("rc"),
        status=str(data.get("status", "missing")),
        duration_sec=float(data["duration_sec"]),
        file=relative,
        text=truncate_manifest_text(str(data.get("text", ""))),
        error=str(data.get("error", "")),
    )


def capture_adb(store: EvidenceStore,
                args: argparse.Namespace,
                mode: str,
                name: str,
                shell_command: str,
                timeout: int) -> CaptureRecord:
    full_command = adb_shell_command(args, shell_command)
    try:
        rc, text, duration = run_host_command(full_command, timeout=max(timeout, int(args.timeout)))
        error = ""
    except Exception as exc:  # noqa: BLE001 - evidence collector preserves failure detail
        rc = None
        text = ""
        error = str(exc)
        duration = float(max(timeout, int(args.timeout)))
    body = f"$ {' '.join(full_command)}\n{redact_text(text if text else error)}\nrc={rc}\n"
    relative = write_capture(store, mode, name, body)
    return CaptureRecord(
        mode=mode,
        name=name,
        command=" ".join(full_command),
        ok=rc == 0,
        rc=rc,
        status="ok" if rc == 0 else "missing",
        duration_sec=duration,
        file=relative,
        text=truncate_manifest_text(text),
        error=error,
    )


def adb_wait(store: EvidenceStore, args: argparse.Namespace, mode: str) -> CaptureRecord:
    full_command = [*adb_base(args), "wait-for-device"]
    try:
        rc, text, duration = run_host_command(full_command, timeout=int(args.timeout))
        error = ""
    except Exception as exc:  # noqa: BLE001 - evidence collector preserves failure detail
        rc = None
        text = ""
        error = str(exc)
        duration = float(args.timeout)
    body = f"$ {' '.join(full_command)}\n{redact_text(text if text else error)}\nrc={rc}\n"
    relative = write_capture(store, mode, "adb-wait-for-device", body)
    return CaptureRecord(mode, "adb-wait-for-device", " ".join(full_command), rc == 0, rc, "ok" if rc == 0 else "missing", duration, relative, truncate_manifest_text(text), error)


def collect_native(store: EvidenceStore, args: argparse.Namespace) -> list[CaptureRecord]:
    return [capture_native(store, args, name, command, timeout) for name, command, timeout in NATIVE_COMMANDS]


def collect_adb_mode(store: EvidenceStore, args: argparse.Namespace, mode: str) -> list[CaptureRecord]:
    captures = [adb_wait(store, args, mode)]
    for name, command, timeout in ADB_COMMANDS:
        captures.append(capture_adb(store, args, mode, name, command, timeout))
    return captures


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    classification = payload.get("classification") or {}
    return {
        "present": True,
        "path": str(resolved),
        "pass": payload.get("pass"),
        "decision": payload.get("decision") or classification.get("decision"),
        "reason": payload.get("reason") or classification.get("reason"),
        "classification_counts": payload.get("classification_counts"),
        "classification": classification,
    }


def values_from_manifest(manifest: dict[str, Any], key: str) -> list[str]:
    classification = manifest.get("classification")
    if not isinstance(classification, dict):
        return []
    values = classification.get(key)
    if not isinstance(values, list):
        return []
    return [str(value) for value in values]


def capture_text(captures: list[CaptureRecord], names: tuple[str, ...] | None = None, modes: tuple[str, ...] | None = None) -> str:
    parts: list[str] = []
    for capture in captures:
        if names is not None and capture.name not in names:
            continue
        if modes is not None and capture.mode not in modes:
            continue
        parts.append(capture.text)
    return "\n".join(parts)


def unique_lines(text: str, patterns: tuple[str, ...] = WIFI_TERMS, limit: int = 160) -> list[str]:
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    result: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("$"):
            continue
        if "grep -" in line or "find /" in line:
            continue
        if not any(pattern.search(line) for pattern in compiled):
            continue
        if line in seen:
            continue
        seen.add(line)
        result.append(line)
        if len(result) >= limit:
            break
    return result


def classify(v204: dict[str, Any],
             v206: dict[str, Any],
             v214: dict[str, Any],
             captures: list[CaptureRecord]) -> dict[str, Any]:
    v206_class = v206.get("classification") if isinstance(v206.get("classification"), dict) else {}
    v214_class = v214.get("classification") if isinstance(v214.get("classification"), dict) else {}

    live_text = capture_text(captures)
    live_android_text = capture_text(captures, modes=("android", "twrp"))
    live_service = unique_lines(live_android_text, (r"init\.svc", r"cnss", r"wificond", r"wifi.*hal", r"supplicant", r"hostapd"), 120)
    live_icnss = unique_lines(live_text, (r"icnss", r"18800000\.qcom,icnss", r"DRIVER=icnss", r"Driver is already initialized"), 120)
    live_debug = unique_lines(live_text, (r"debug", r"recovery", r"ramdump", r"pdr", r"ssr", r"fw_debug", r"stats"), 120)
    live_wlan = unique_lines(live_text, (r"wlan0", r"swlan0", r"p2p0", r"wifi-aware0", r"ieee80211", r"rfkill", r"phy[0-9]"), 120)
    live_firmware = unique_lines(live_text, (r"bdwlan", r"regdb", r"wlanmdsp", r"WCNSS", r"firmware_class", r"/vendor/firmware"), 120)

    service_evidence = values_from_manifest(v206, "service_evidence") + live_service
    init_evidence = values_from_manifest(v206, "init_evidence") + live_service
    firmware_evidence = values_from_manifest(v206, "firmware_evidence") + values_from_manifest(v204, "firmware_evidence") + live_firmware
    interface_evidence = values_from_manifest(v206, "interface_evidence") + values_from_manifest(v204, "interface_evidence") + live_wlan
    icnss_evidence = values_from_manifest(v206, "icnss_evidence") + live_icnss
    qmi_evidence = values_from_manifest(v206, "qmi_evidence")
    log_evidence = values_from_manifest(v206, "log_evidence") + live_icnss

    v204_ready = v204.get("decision") == "ready-for-readonly-nl80211-probe-plan"
    v206_ready = v206.get("decision") in {"ready-for-native-preflight-plan", "android-cnss-map-complete"}
    v214_failed_as_expected = v214.get("decision") == "icnss-rebind-failed"
    v214_recovered = v214_class.get("rolled_back_firmware_class_path") == "/vendor/firmware_mnt/image"
    has_service_chain = bool(service_evidence and init_evidence)
    has_firmware = bool(firmware_evidence)
    has_android_wlan = bool(interface_evidence)
    has_icnss = bool(icnss_evidence) or bool(v214_class.get("icnss_bound"))
    has_qmi_or_log = bool(qmi_evidence or log_evidence)
    live_modes = sorted({capture.mode for capture in captures})
    live_ok = sum(1 for capture in captures if capture.ok)

    if not (v204.get("present") and v206.get("present") and v214.get("present")):
        decision = "insufficient-live-evidence"
        reason = "required v204/v206/v214 manifests are missing"
    elif not v214_failed_as_expected:
        decision = "manual-review-required"
        reason = f"v214 decision is {v214.get('decision')!r}, expected icnss-rebind-failed"
    elif v206_ready and has_service_chain and has_firmware and has_android_wlan and has_icnss and has_qmi_or_log:
        decision = "lifecycle-map-ready"
        reason = "Android lifecycle evidence plus v214 failure are sufficient for v216 service replay modeling"
    elif v204_ready and v214_failed_as_expected and not has_service_chain:
        decision = "android-only-required"
        reason = "Android exposes WLAN state but service/init lifecycle evidence is insufficient for native modeling"
    elif live_modes and live_ok == 0:
        decision = "insufficient-live-evidence"
        reason = "live mode selected but no live captures succeeded"
    else:
        decision = "manual-review-required"
        reason = "lifecycle evidence is incomplete or inconsistent"

    return {
        "decision": decision,
        "reason": reason,
        "v204_ready": v204_ready,
        "v206_ready": v206_ready,
        "v214_failed_as_expected": v214_failed_as_expected,
        "v214_recovered": v214_recovered,
        "has_service_chain": has_service_chain,
        "has_firmware": has_firmware,
        "has_android_wlan": has_android_wlan,
        "has_icnss": has_icnss,
        "has_qmi_or_log": has_qmi_or_log,
        "live_modes": live_modes,
        "live_ok_captures": live_ok,
        "live_total_captures": len(captures),
        "service_evidence": service_evidence[:160],
        "init_evidence": init_evidence[:160],
        "firmware_evidence": firmware_evidence[:160],
        "interface_evidence": interface_evidence[:160],
        "icnss_evidence": icnss_evidence[:160],
        "qmi_evidence": qmi_evidence[:160],
        "log_evidence": log_evidence[:160],
        "debug_recovery_candidates": live_debug[:160],
        "v214_failure": {
            "decision": v214.get("decision"),
            "reason": v214.get("reason"),
            "icnss_bind": "failed",
            "dmesg": [
                "icnss: Driver is already initialized",
                "probe of 18800000.qcom,icnss failed with error -17",
            ],
            "rolled_back_firmware_class_path": v214_class.get("rolled_back_firmware_class_path"),
        },
        "recommended_v216_inputs": [
            "service_evidence",
            "init_evidence",
            "firmware_evidence",
            "interface_evidence",
            "icnss_evidence",
            "qmi_evidence",
            "log_evidence",
        ],
    }


def evidence_count(value: Any) -> str:
    if isinstance(value, list):
        return str(len(value))
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def build_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    rows = [
        ["result", "PASS" if manifest["pass"] else "FAIL", classification["reason"]],
        ["decision", classification["decision"], "read-only lifecycle map"],
        ["v204 ready", evidence_count(classification["v204_ready"]), str(manifest["v204_android"].get("decision"))],
        ["v206 ready", evidence_count(classification["v206_ready"]), str(manifest["v206_android"].get("decision"))],
        ["v214 failure", evidence_count(classification["v214_failed_as_expected"]), str(manifest["v214_native"].get("decision"))],
        ["service/init", evidence_count(classification["has_service_chain"]), f"service={len(classification['service_evidence'])} init={len(classification['init_evidence'])}"],
        ["firmware", evidence_count(classification["has_firmware"]), str(len(classification["firmware_evidence"]))],
        ["android wlan", evidence_count(classification["has_android_wlan"]), str(len(classification["interface_evidence"]))],
        ["icnss", evidence_count(classification["has_icnss"]), str(len(classification["icnss_evidence"]))],
        ["qmi/log", evidence_count(classification["has_qmi_or_log"]), f"qmi={len(classification['qmi_evidence'])} log={len(classification['log_evidence'])}"],
        ["live captures", str(classification["live_ok_captures"]), f"total={classification['live_total_captures']} modes={','.join(classification['live_modes']) or 'manifest-only'}"],
    ]
    lines = [
        "# v215 ICNSS/CNSS Lifecycle Research",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{classification['decision']}`",
        f"- reason: `{classification['reason']}`",
        "",
        "## Summary Matrix",
        "",
        markdown_table(["area", "status", "detail"], rows),
        "",
    ]
    for key in (
        "service_evidence",
        "init_evidence",
        "firmware_evidence",
        "interface_evidence",
        "icnss_evidence",
        "qmi_evidence",
        "log_evidence",
        "debug_recovery_candidates",
    ):
        lines.append(f"## {key}")
        lines.append("")
        values = classification[key]
        if values:
            lines.extend(f"- `{value}`" for value in values[:80])
        else:
            lines.append("- none")
        lines.append("")
    lines.extend([
        "## v214 Failure Correlation",
        "",
        "```json",
        json.dumps(classification["v214_failure"], ensure_ascii=False, indent=2, sort_keys=True),
        "```",
        "",
        "## Guardrails",
        "",
    ])
    lines.extend(f"- {item}" for item in manifest["guardrails"])
    lines.extend([
        "",
        "## Captures",
        "",
    ])
    if manifest["captures"]:
        for item in manifest["captures"]:
            lines.append(f"- {'OK' if item['ok'] else 'FAIL'} `{item['mode']}:{item['name']}` rc={item['rc']} status={item['status']} file=`{item['file']}`")
    else:
        lines.append("- manifest-only run; no live captures")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    validate_no_active_commands()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)

    captures: list[CaptureRecord] = []
    if args.native_bridge:
        captures.extend(collect_native(store, args))
    if args.android_adb:
        captures.extend(collect_adb_mode(store, args, "android"))
    if args.twrp_adb:
        captures.extend(collect_adb_mode(store, args, "twrp"))

    v204 = load_manifest(args.v204_android_manifest)
    v206 = load_manifest(args.v206_manifest)
    v214 = load_manifest(args.v214_manifest)
    classification = classify(v204, v206, v214, captures)
    pass_ok = classification["decision"] in {"lifecycle-map-ready", "android-only-required"}
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": classification["decision"],
        "reason": classification["reason"],
        "mode": {
            "native_bridge": args.native_bridge,
            "android_adb": args.android_adb,
            "twrp_adb": args.twrp_adb,
            "su": args.su,
        },
        "v204_android": v204,
        "v206_android": v206,
        "v214_native": v214,
        "classification": classification,
        "captures": [asdict(capture) for capture in captures],
        "guardrails": [
            "no ICNSS bind/unbind",
            "no Wi-Fi enablement",
            "no rfkill write",
            "no WLAN link-up",
            "no scan/connect",
            "no module load/unload",
            "no firmware_class.path write",
            "no firmware mutation",
            "no Android Wi-Fi service/supplicant/hostapd/cnss-daemon start",
            "no /data/misc/wifi default collection",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    print(
        f"{'PASS' if pass_ok else 'FAIL'} "
        f"out_dir={out_dir} "
        f"decision={classification['decision']} "
        f"reason={classification['reason']}"
    )
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
