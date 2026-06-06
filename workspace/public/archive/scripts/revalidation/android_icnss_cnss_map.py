#!/usr/bin/env python3
"""Collect Android read-only ICNSS/CNSS Wi-Fi dependency map evidence."""

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

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


ACTIVE_WIFI_PATTERNS = (
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\s+set-wifi-enabled\b", re.IGNORECASE),
    re.compile(r"(?:^|[;&]\s*)(?:/[^ ]*/)?(?:wpa_supplicant|hostapd|cnss-daemon|wificond)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/class/rfkill", re.IGNORECASE),
    re.compile(r">\s*/sys/module/firmware_class/parameters/path", re.IGNORECASE),
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
)

ADB_COMMANDS: tuple[tuple[str, str, int], ...] = (
    (
        "identity-props",
        "for p in ro.product.model ro.build.fingerprint ro.build.version.release "
        "ro.boot.hardware ro.boot.slot_suffix ro.boot.verifiedbootstate "
        "ro.boot.vbmeta.device_state ro.boot.flash.locked sys.boot_completed; "
        "do echo \"$p=$(getprop $p)\"; done",
        15,
    ),
    ("id", "id", 10),
    ("uname", "uname -a", 10),
    (
        "mounts-core",
        "cat /proc/mounts 2>/dev/null | grep -Ei ' /(?:system|vendor|odm|product|system_ext|apex)|firmware' || true",
        20,
    ),
    (
        "wifi-props-init-state",
        "getprop | grep -Ei '(^\\[init\\.svc\\..*(wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|qca))|"
        "(^\\[ro\\.boottime\\..*(wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|qca))|"
        "(wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|wcn|qca|qcacld|qmi|firmware)' || true",
        25,
    ),
    (
        "processes-wifi",
        "ps -AZ 2>/dev/null | grep -Ei 'wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|wcn|qca|qcacld|qmi|qrtr' || "
        "ps -A 2>/dev/null | grep -Ei 'wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|wcn|qca|qcacld|qmi|qrtr' || true",
        25,
    ),
    (
        "initrc-wifi-files",
        "find /system/etc/init /system_ext/etc/init /vendor/etc/init /odm/etc/init /product/etc/init "
        "-maxdepth 2 -type f -name '*.rc' 2>/dev/null | sort | "
        "grep -Ei 'wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|wcn|qca|qti|vendor' || true",
        25,
    ),
    (
        "initrc-wifi-grep",
        "grep -RHiE 'service .*("
        "wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|wcn|qca|qmi)|"
        "on property:.*(wifi|wlan|cnss|icnss|wcn|qca)|"
        "class_start .*wifi|class .*wifi|capabilities .*NET_(RAW|ADMIN)|group .*net_(raw|admin)|"
        "firmware|vendor\\.wifi|android\\.hardware\\.wifi' "
        "/system/etc/init /system_ext/etc/init /vendor/etc/init /odm/etc/init /product/etc/init 2>/dev/null || true",
        35,
    ),
    (
        "vintf-wifi-hal",
        "grep -RHiE 'android\\.hardware\\.wifi|vendor.*wifi|supplicant|hostapd|wificond|qti.*wifi' "
        "/vendor/etc/vintf /odm/etc/vintf /system/etc/vintf /system_ext/etc/vintf /product/etc/vintf 2>/dev/null || true",
        30,
    ),
    (
        "sysfs-net-icnss",
        "for p in /sys/devices/platform/soc/18800000.qcom,icnss "
        "/sys/class/net/wlan0 /sys/class/net/swlan0 /sys/class/net/p2p0 /sys/class/net/wifi-aware0 "
        "/sys/class/ieee80211 /sys/class/rfkill; do "
        "echo \"path=$p\"; ls -ld \"$p\" 2>/dev/null || true; "
        "readlink -f \"$p\" 2>/dev/null || true; done",
        25,
    ),
    (
        "netdev-details",
        "for n in wlan0 swlan0 p2p0 wifi-aware0; do "
        "base=/sys/class/net/$n; [ -e \"$base\" ] || continue; echo \"netdev=$n\"; "
        "for f in operstate carrier type mtu ifindex address; do "
        "[ -e \"$base/$f\" ] && echo \"$f=$(cat \"$base/$f\" 2>/dev/null)\"; done; "
        "readlink -f \"$base/device\" 2>/dev/null || true; done",
        25,
    ),
    (
        "rfkill-detail",
        "for r in /sys/class/rfkill/rfkill*; do "
        "[ -e \"$r\" ] || continue; echo \"node=$r\"; "
        "for f in name type state soft hard persistent; do "
        "[ -e \"$r/$f\" ] && echo \"$f=$(cat \"$r/$f\" 2>/dev/null)\"; done; "
        "readlink -f \"$r/device\" 2>/dev/null || true; done",
        25,
    ),
    (
        "ieee80211-tree",
        "find /sys/class/ieee80211 -maxdepth 5 2>/dev/null | sort || true",
        25,
    ),
    (
        "icnss-tree",
        "find /sys/devices/platform/soc/18800000.qcom,icnss -maxdepth 6 2>/dev/null | sort || true",
        35,
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
        "firmware-candidate-stat",
        "for f in "
        "/vendor/firmware_mnt/image/bdwlan.bin "
        "/vendor/firmware_mnt/image/regdb.bin "
        "/vendor/firmware/bdwlan.bin "
        "/vendor/firmware/regdb.bin "
        "/vendor/etc/wifi/bdwlan.bin "
        "/vendor/etc/wifi/regdb.bin; do "
        "[ -e \"$f\" ] && stat \"$f\" 2>/dev/null; done",
        25,
    ),
    (
        "devnodes-sockets-wifi",
        "ls -l /dev/cnss* /dev/qrtr* /dev/qmi* /dev/adsprpc* /dev/socket 2>/dev/null | "
        "grep -Ei 'wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|qmi|qrtr|qca|vendor' || true",
        25,
    ),
    (
        "proc-modules-wifi",
        "cat /proc/modules 2>/dev/null | grep -Ei 'wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|wcn|qca|qcacld|cfg80211|mac80211|ath' || true",
        25,
    ),
    (
        "proc-net-wireless",
        "cat /proc/net/wireless 2>/dev/null || true",
        15,
    ),
    (
        "dmesg-wifi-cnss-tail",
        "dmesg 2>/dev/null | grep -Ei 'wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|wcn|qca|qcacld|firmware|qmi|qrtr|bdf|bdwlan|regdb|nl80211|cfg80211' | tail -n 500 || true",
        45,
    ),
    (
        "logcat-wifi-cnss-tail",
        "logcat -d -v threadtime 2>/dev/null | grep -Ei 'wifi|wlan|wificond|supplicant|hostapd|cnss|icnss|wcn|qca|qcacld|firmware|qmi|qrtr|bdf|bdwlan|regdb|nl80211|cfg80211' | tail -n 500 || true",
        60,
    ),
)

DECISIONS = {
    "ready-for-native-preflight-plan",
    "android-cnss-map-complete",
    "missing-firmware-map",
    "missing-service-map",
    "native-replay-prereq-missing",
    "manual-review-required",
}


@dataclass
class CaptureRecord:
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
    return REPO_ROOT / "tmp" / "wifi" / f"v206-android-icnss-cnss-map-{stamp}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--android-adb", action="store_true", help="collect Android ADB read-only dependency map")
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", help="optional adb serial")
    parser.add_argument("--su", action="store_true", help="run Android shell captures through su -c")
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v204-android-manifest", type=Path, default=Path("tmp/wifi/v204-android-baseline/manifest.json"))
    parser.add_argument("--v205-manifest", type=Path, default=Path("tmp/wifi/v205-icnss-nl80211-readonly/manifest.json"))
    return parser.parse_args()


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command.extend(["-s", args.serial])
    return command


def adb_shell_command(args: argparse.Namespace, shell_command: str) -> list[str]:
    if args.su:
        return [*adb_base(args), "shell", "su", "-c", shlex.quote(shell_command)]
    return [*adb_base(args), "shell", shell_command]


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(psk|password|passphrase|ssid|bssid)=([^\s]+)", r"\1=<redacted>", text)
    text = re.sub(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|ro\.boot\.serialno|serialno)=([^\s]+)", r"\1=<redacted>", text)
    text = re.sub(r"(?i)(ifname=)(wlan\d+|swlan\d+|p2p\d+|wifi-aware\d+)", r"\1\2", text)
    return text


def validate_no_active_wifi_commands() -> None:
    joined = "\n".join(command for _, command, _ in ADB_COMMANDS)
    for token in SENSITIVE_DEFAULT_EXCLUDES:
        if token in joined:
            raise RuntimeError(f"sensitive/default-excluded Wi-Fi command token found: {token}")
    for pattern in ACTIVE_WIFI_PATTERNS:
        if pattern.search(joined):
            raise RuntimeError(f"active Wi-Fi command pattern found: {pattern.pattern}")


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


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    path = store.write_text(f"android/commands/{safe_name(name)}.txt", redact_text(text).rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def capture_adb_shell(store: EvidenceStore,
                      args: argparse.Namespace,
                      name: str,
                      shell_command: str,
                      timeout: int) -> CaptureRecord:
    full_command = adb_shell_command(args, shell_command)
    try:
        rc, text, duration = run_host_command(full_command, timeout=max(timeout, args.timeout))
        error = ""
    except Exception as exc:  # noqa: BLE001 - evidence collector preserves failure detail
        rc = None
        text = ""
        error = str(exc)
        duration = float(max(timeout, args.timeout))
    body = f"$ {' '.join(full_command)}\n{redact_text(text if text else error)}\nrc={rc}\n"
    relative = write_capture(store, name, body)
    manifest_text = redact_text(text)
    if len(manifest_text) > 8192:
        manifest_text = manifest_text[:8192] + "\n[truncated in manifest]\n"
    return CaptureRecord(
        name=name,
        command=" ".join(full_command),
        ok=rc == 0,
        rc=rc,
        duration_sec=duration,
        file=relative,
        text=manifest_text,
        error=error,
    )


def adb_wait(store: EvidenceStore, args: argparse.Namespace) -> CaptureRecord:
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
    relative = write_capture(store, "adb-wait-for-device", body)
    return CaptureRecord("adb-wait-for-device", " ".join(full_command), rc == 0, rc, duration, relative, redact_text(text), error)


def collect_android(store: EvidenceStore, args: argparse.Namespace) -> list[CaptureRecord]:
    captures = [adb_wait(store, args)]
    for name, command, timeout in ADB_COMMANDS:
        captures.append(capture_adb_shell(store, args, name, command, timeout))
    return captures


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    return {
        "present": True,
        "path": str(resolved),
        "pass": payload.get("pass"),
        "decision": payload.get("decision") or payload.get("classification", {}).get("decision"),
        "reason": payload.get("reason") or payload.get("classification", {}).get("reason"),
        "classification_counts": payload.get("classification_counts"),
        "classification": payload.get("classification"),
    }


def capture_text(captures: list[CaptureRecord], names: tuple[str, ...]) -> str:
    return "\n".join(capture.text for capture in captures if capture.name in names and capture.text)


def unique_lines(text: str, patterns: tuple[str, ...], limit: int = 120) -> list[str]:
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


def classify(captures: list[CaptureRecord], v204: dict[str, Any], v205: dict[str, Any]) -> dict[str, Any]:
    process_text = capture_text(captures, ("processes-wifi", "wifi-props-init-state"))
    init_text = capture_text(captures, ("initrc-wifi-files", "initrc-wifi-grep"))
    firmware_text = capture_text(captures, ("firmware-candidates", "firmware-candidate-stat", "firmware-class-path"))
    sysfs_text = capture_text(captures, ("sysfs-net-icnss", "netdev-details", "rfkill-detail", "ieee80211-tree", "icnss-tree"))
    log_text = capture_text(captures, ("dmesg-wifi-cnss-tail", "logcat-wifi-cnss-tail"))
    qmi_text = capture_text(captures, ("devnodes-sockets-wifi", "processes-wifi", "dmesg-wifi-cnss-tail", "logcat-wifi-cnss-tail"))
    hal_text = capture_text(captures, ("vintf-wifi-hal", "initrc-wifi-grep", "processes-wifi"))
    mount_text = capture_text(captures, ("mounts-core",))

    service_evidence = unique_lines(process_text + "\n" + init_text, (r"cnss", r"icnss", r"wificond", r"wifi.*hal", r"supplicant", r"hostapd"))
    init_evidence = unique_lines(init_text, (r"service ", r"on property:", r"capabilities", r"group .*net_", r"class "))
    firmware_evidence = unique_lines(firmware_text, (r"bdwlan", r"regdb", r"wlanmdsp", r"WCNSS", r"firmware_mnt", r"/vendor/firmware", r"/vendor/etc/wifi"))
    interface_evidence = unique_lines(sysfs_text, (r"wlan0", r"swlan0", r"p2p0", r"wifi-aware0", r"ieee80211", r"phy[0-9]"))
    icnss_evidence = unique_lines(sysfs_text + "\n" + log_text, (r"icnss", r"cnss", r"18800000\.qcom,icnss"))
    qmi_evidence = unique_lines(qmi_text, (r"qmi", r"qrtr", r"QMI", r"Server Connected"))
    hal_evidence = unique_lines(hal_text, (r"android\.hardware\.wifi", r"vendor.*wifi", r"IWifi", r"wifi.*hal", r"supplicant", r"hostapd"))
    log_evidence = unique_lines(log_text, (r"FW is ready", r"BDF", r"bdwlan", r"regdb", r"firmware", r"wlan", r"wifi", r"cnss", r"icnss", r"qmi"))
    mount_evidence = unique_lines(mount_text, (r"/vendor", r"/odm", r"firmware", r"/system", r"/product"))

    has_service = bool(service_evidence and init_evidence)
    has_firmware = bool(firmware_evidence)
    has_interface = bool(interface_evidence)
    has_icnss = bool(icnss_evidence)
    has_qmi_or_log = bool(qmi_evidence or log_evidence)
    has_mounts = bool(mount_evidence)
    android_ready = v204.get("decision") == "ready-for-readonly-nl80211-probe-plan"
    native_gap = v205.get("decision") in {"native-icnss-present-no-wiphy", "android-only-driver-ready"}
    map_complete = has_service and has_firmware and has_interface and has_icnss and has_qmi_or_log and has_mounts

    if not any(capture.ok for capture in captures):
        decision = "manual-review-required"
        reason = "no successful Android ADB capture"
    elif map_complete and android_ready and native_gap:
        decision = "ready-for-native-preflight-plan"
        reason = "Android dependency map is complete enough to design native read-only preflight"
    elif map_complete:
        decision = "android-cnss-map-complete"
        reason = "Android ICNSS/CNSS service, firmware, interface, log, and mount evidence mapped"
    elif not has_firmware:
        decision = "missing-firmware-map"
        reason = "Android capture did not map required firmware/regdb/BDF candidates"
    elif not has_service:
        decision = "missing-service-map"
        reason = "Android capture did not map enough service/init trigger evidence"
    else:
        decision = "native-replay-prereq-missing"
        reason = "Android evidence is partial; native replay prerequisites remain uncertain"

    return {
        "decision": decision,
        "reason": reason,
        "android_ready_from_v204": android_ready,
        "native_gap_from_v205": native_gap,
        "map_complete": map_complete,
        "has_service": has_service,
        "has_firmware": has_firmware,
        "has_interface": has_interface,
        "has_icnss": has_icnss,
        "has_qmi_or_log": has_qmi_or_log,
        "has_mounts": has_mounts,
        "service_evidence": service_evidence,
        "init_evidence": init_evidence,
        "firmware_evidence": firmware_evidence,
        "interface_evidence": interface_evidence,
        "icnss_evidence": icnss_evidence,
        "qmi_evidence": qmi_evidence,
        "hal_evidence": hal_evidence,
        "log_evidence": log_evidence,
        "mount_evidence": mount_evidence,
    }


def build_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    rows = [
        ["result", "PASS" if manifest["pass"] else "FAIL", classification["reason"]],
        ["decision", classification["decision"], "read-only dependency map"],
        ["v204 android", str(classification["android_ready_from_v204"]), str(manifest["v204_android"].get("decision"))],
        ["v205 native gap", str(classification["native_gap_from_v205"]), str(manifest["v205_native"].get("decision"))],
        ["service/init", str(classification["has_service"]), f"service={len(classification['service_evidence'])} init={len(classification['init_evidence'])}"],
        ["firmware", str(classification["has_firmware"]), str(len(classification["firmware_evidence"]))],
        ["interface", str(classification["has_interface"]), str(len(classification["interface_evidence"]))],
        ["icnss", str(classification["has_icnss"]), str(len(classification["icnss_evidence"]))],
        ["qmi/log", str(classification["has_qmi_or_log"]), f"qmi={len(classification['qmi_evidence'])} log={len(classification['log_evidence'])}"],
        ["mounts", str(classification["has_mounts"]), str(len(classification["mount_evidence"]))],
    ]
    lines = [
        "# v206 Android ICNSS/CNSS Dependency Map",
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
        "hal_evidence",
        "log_evidence",
        "mount_evidence",
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
        "## Guardrails",
        "",
    ])
    lines.extend(f"- {item}" for item in manifest["guardrails"])
    lines.extend([
        "",
        "## Captures",
        "",
    ])
    for item in manifest["captures"]:
        lines.append(f"- {'OK' if item['ok'] else 'FAIL'} `{item['name']}` rc={item['rc']} file=`{item['file']}`")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    args = parse_args()
    validate_no_active_wifi_commands()
    if not args.android_adb:
        raise SystemExit("select --android-adb; v206 maps Android-side ICNSS/CNSS dependencies")
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    store.mkdir("android", "commands")

    captures = collect_android(store, args)
    v204 = load_manifest(args.v204_android_manifest)
    v205 = load_manifest(args.v205_manifest)
    classification = classify(captures, v204, v205)
    pass_ok = classification["decision"] in DECISIONS and any(capture.ok for capture in captures)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": classification["decision"],
        "reason": classification["reason"],
        "mode": "android-adb",
        "su": args.su,
        "v204_android": v204,
        "v205_native": v205,
        "classification": classification,
        "captures": [asdict(capture) for capture in captures],
        "guardrails": [
            "no Wi-Fi enablement",
            "no rfkill write",
            "no WLAN link-up",
            "no scan/connect",
            "no module load/unload",
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
