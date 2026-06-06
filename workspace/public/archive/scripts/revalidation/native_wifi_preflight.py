#!/usr/bin/env python3
"""Collect native read-only Wi-Fi preflight evidence for ICNSS/CNSS bring-up planning."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    DEFAULT_EXPECT_VERSION,
    REPO_ROOT,
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore


WIFI_KEYWORDS = (
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
    "ieee80211",
    "rfkill",
)

ACTIVE_WIFI_PATTERNS = (
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\bNL80211_CMD_TRIGGER_SCAN\b", re.IGNORECASE),
    re.compile(r"\bNL80211_CMD_SET_INTERFACE\b", re.IGNORECASE),
    re.compile(r"\bNL80211_CMD_SET_WIPHY\b", re.IGNORECASE),
    re.compile(r"\bNL80211_CMD_CONNECT\b", re.IGNORECASE),
    re.compile(r"\bNL80211_CMD_DISCONNECT\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bdumpsys\s+wifi\b", re.IGNORECASE),
    re.compile(r"(?:^|[;&]\s*)(?:/[^ ]*/)?(?:wpa_supplicant|hostapd|cnss-daemon|wificond)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/class/rfkill", re.IGNORECASE),
    re.compile(r">\s*/sys/module/firmware_class/parameters/path", re.IGNORECASE),
)

DEVICE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 15.0),
    ("status", ["status"], 25.0),
    ("bootstatus", ["bootstatus"], 25.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 45.0),
    ("mounts", ["mounts"], 20.0),
    ("mnt-system-root", ["ls", "/mnt/system"], 25.0),
    ("mnt-system-system-init", ["ls", "/mnt/system/system/etc/init"], 25.0),
    ("mnt-system-vendor-root", ["ls", "/mnt/system/vendor"], 25.0),
    ("mnt-system-vendor-init", ["ls", "/mnt/system/vendor/etc/init"], 25.0),
    ("mnt-system-vendor-init-hw", ["ls", "/mnt/system/vendor/etc/init/hw"], 25.0),
    ("mnt-system-vendor-firmware", ["ls", "/mnt/system/vendor/firmware"], 25.0),
    ("mnt-system-vendor-firmware-mnt", ["ls", "/mnt/system/vendor/firmware_mnt"], 25.0),
    ("mnt-system-vendor-etc-wifi", ["ls", "/mnt/system/vendor/etc/wifi"], 25.0),
    ("init-qcom-rc-stat", ["stat", "/mnt/system/vendor/etc/init/hw/init.qcom.rc"], 20.0),
    ("wifi-hal-rc-stat", ["stat", "/mnt/system/vendor/etc/init/android.hardware.wifi@1.0-service.rc"], 20.0),
    ("wificond-rc-stat", ["stat", "/mnt/system/system/etc/init/wificond.rc"], 20.0),
    ("supplicant-rc-stat", ["stat", "/mnt/system/system/etc/init/wpa_supplicant.rc"], 20.0),
    ("firmware-bdwlan-stat", ["stat", "/mnt/system/vendor/firmware/wlan/qca_cld/bdwlan.bin"], 20.0),
    ("firmware-regdb-stat", ["stat", "/mnt/system/vendor/firmware/wlan/qca_cld/regdb.bin"], 20.0),
    ("firmware-wlanmdsp-stat", ["stat", "/mnt/system/vendor/firmware/wlanmdsp.mbn"], 20.0),
    (
        "firmware-candidates",
        [
            "run",
            "/cache/bin/toybox",
            "find",
            "/mnt/system/vendor/firmware",
            "/mnt/system/vendor/firmware_mnt",
            "/mnt/system/vendor/etc/wifi",
            "-maxdepth",
            "8",
        ],
        45.0,
    ),
    ("icnss-stat", ["stat", "/sys/devices/platform/soc/18800000.qcom,icnss"], 20.0),
    (
        "icnss-tree",
        [
            "run",
            "/cache/bin/toybox",
            "find",
            "/sys/devices/platform/soc/18800000.qcom,icnss",
            "-maxdepth",
            "6",
        ],
        45.0,
    ),
    ("sys-class-net", ["ls", "/sys/class/net"], 20.0),
    ("sys-class-ieee80211", ["ls", "/sys/class/ieee80211"], 20.0),
    ("ieee80211-tree", ["run", "/cache/bin/toybox", "find", "/sys/class/ieee80211", "-maxdepth", "5"], 25.0),
    ("sys-class-rfkill", ["ls", "/sys/class/rfkill"], 20.0),
    ("rfkill0-name", ["cat", "/sys/class/rfkill/rfkill0/name"], 20.0),
    ("rfkill0-type", ["cat", "/sys/class/rfkill/rfkill0/type"], 20.0),
    ("rfkill1-name", ["cat", "/sys/class/rfkill/rfkill1/name"], 20.0),
    ("rfkill1-type", ["cat", "/sys/class/rfkill/rfkill1/type"], 20.0),
    ("wlan0-stat", ["stat", "/sys/class/net/wlan0"], 20.0),
    ("swlan0-stat", ["stat", "/sys/class/net/swlan0"], 20.0),
    ("p2p0-stat", ["stat", "/sys/class/net/p2p0"], 20.0),
    ("wifi-aware0-stat", ["stat", "/sys/class/net/wifi-aware0"], 20.0),
    ("proc-net-wireless", ["run", "/cache/bin/toybox", "cat", "/proc/net/wireless"], 20.0),
    ("proc-modules", ["run", "/cache/bin/toybox", "cat", "/proc/modules"], 35.0),
    (
        "firmware-class-path",
        ["run", "/cache/bin/toybox", "cat", "/sys/module/firmware_class/parameters/path"],
        20.0,
    ),
    ("kernel-hotplug", ["run", "/cache/bin/toybox", "cat", "/proc/sys/kernel/hotplug"], 20.0),
)

NL80211_HELPER_REMOTE = "/cache/bin/a90_nl80211_ro"
NL80211_HELPER_LOCAL = REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_nl80211_ro"

DECISIONS = {
    "native-preflight-ready",
    "userspace-service-gap-confirmed",
    "missing-mounted-vendor",
    "missing-firmware-path",
    "missing-icnss-sysfs",
    "missing-nl80211-helper",
    "missing-wiphy-netdev",
    "manual-review-required",
}


@dataclass
class CaptureRecord:
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
    return REPO_ROOT / "tmp" / "wifi" / f"v207-native-wifi-preflight-{stamp}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", "--bridge-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v205-manifest", type=Path, default=Path("tmp/wifi/v205-icnss-nl80211-readonly/manifest.json"))
    parser.add_argument("--v206-manifest", type=Path, default=Path("tmp/wifi/v206-android-icnss-cnss-map/manifest.json"))
    parser.add_argument("--helper-remote", default=NL80211_HELPER_REMOTE)
    parser.add_argument("--helper-local", type=Path, default=NL80211_HELPER_LOCAL)
    parser.add_argument("--skip-helper", action="store_true")
    parser.add_argument("--native-bridge", action="store_true", help="document intent; native bridge is the current mode")
    return parser.parse_args()


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|serialno)=([^\s]+)", r"\1=<redacted>", text)
    return text


def validate_no_active_wifi_commands() -> None:
    command_text = "\n".join(" ".join(argv) for _, argv, _ in DEVICE_COMMANDS)
    command_text += f"\nstat {NL80211_HELPER_REMOTE}\nrun {NL80211_HELPER_REMOTE}"
    for pattern in ACTIVE_WIFI_PATTERNS:
        if pattern.search(command_text):
            raise RuntimeError(f"active Wi-Fi command pattern found: {pattern.pattern}")


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    path = store.write_text(f"native/commands/{safe_name(name)}.txt", redact_text(text).rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def capture_device(
    store: EvidenceStore,
    args: argparse.Namespace,
    name: str,
    command: list[str],
    timeout: float,
) -> CaptureRecord:
    capture = run_capture(args, name, command, timeout=timeout)
    body = capture.text if capture.text else f"{capture.error}\n"
    relative = write_capture(store, name, body)
    data = capture_to_manifest(capture)
    return CaptureRecord(
        name=name,
        command=" ".join(command),
        ok=bool(data["ok"]),
        rc=data.get("rc"),
        status=str(data.get("status", "missing")),
        duration_sec=float(data["duration_sec"]),
        file=relative,
        text=redact_text(data.get("text", "")),
        error=str(data.get("error", "")),
    )


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def helper_metadata(args: argparse.Namespace) -> dict[str, Any]:
    local = args.helper_local if args.helper_local.is_absolute() else REPO_ROOT / args.helper_local
    return {
        "remote_path": args.helper_remote,
        "local_path": str(local),
        "local_exists": local.exists(),
        "local_sha256": sha256_file(local),
        "default_deploy": False,
    }


def maybe_capture_helper(store: EvidenceStore, args: argparse.Namespace) -> list[CaptureRecord]:
    if args.skip_helper:
        return []
    stat_capture = capture_device(store, args, "nl80211-helper-stat", ["stat", args.helper_remote], 20.0)
    captures = [stat_capture]
    if stat_capture.ok:
        captures.append(capture_device(store, args, "nl80211-helper-run", ["run", args.helper_remote], 30.0))
    return captures


def strip_all(captures: list[CaptureRecord]) -> str:
    return "\n".join(strip_cmdv1_text(item.text) for item in captures if item.text)


def capture_by_name(captures: list[CaptureRecord], name: str) -> CaptureRecord | None:
    for capture in captures:
        if capture.name == name:
            return capture
    return None


def capture_ok(captures: list[CaptureRecord], *names: str) -> bool:
    return any((capture := capture_by_name(captures, name)) is not None and capture.ok for name in names)


def capture_text(captures: list[CaptureRecord], *names: str) -> str:
    chunks: list[str] = []
    for name in names:
        capture = capture_by_name(captures, name)
        if capture is not None:
            chunks.append(strip_cmdv1_text(capture.text))
    return "\n".join(chunks)


def extract_native_interfaces(captures: list[CaptureRecord]) -> list[str]:
    text = capture_text(captures, "sys-class-net", "icnss-tree", "ieee80211-tree", "nl80211-helper-run")
    found: set[str] = set()
    for line in text.splitlines():
        lowered = line.strip().lower()
        if not lowered or "no such file" in lowered:
            continue
        for match in re.finditer(r"(?:^|[/\s])(wlan[0-9]*|swlan[0-9]*|p2p[0-9]*|wifi-aware[0-9]*|phy[0-9]+)(?:$|[/\s:])", lowered):
            found.add(match.group(1))
        helper_match = re.search(r"\bifname=([A-Za-z0-9_.:-]+)", line)
        if helper_match:
            found.add(helper_match.group(1).lower())
    return sorted(found)


def has_wifi_rfkill(captures: list[CaptureRecord]) -> bool:
    text = capture_text(captures, "sys-class-rfkill", "rfkill0-name", "rfkill0-type", "rfkill1-name", "rfkill1-type", "icnss-tree")
    lower = text.lower()
    if "type=wifi" in lower or "type=wlan" in lower:
        return True
    for line in lower.splitlines():
        if "bt_power" in line:
            continue
        if "rfkill" in line and re.search(r"(wifi|wlan|phy|icnss)", line):
            return True
    return False


def relevant_lines(text: str, limit: int = 140) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if any(term in lower for term in WIFI_KEYWORDS):
            if line not in lines:
                lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def classify(captures: list[CaptureRecord], v205: dict[str, Any] | None, v206: dict[str, Any] | None) -> dict[str, Any]:
    text = strip_all(captures)
    lower = text.lower()
    native_interfaces = extract_native_interfaces(captures)
    native_wiphy = (
        capture_ok(captures, "sys-class-ieee80211", "ieee80211-tree", "nl80211-helper-run")
        and ("/ieee80211/phy" in lower or re.search(r"(?:^|[/\s])phy[0-9]+(?:$|[/\s:])", lower) is not None)
    )
    native_wifi_rfkill = has_wifi_rfkill(captures)
    mountsystem_ok = capture_ok(captures, "mountsystem-ro")
    mounted_vendor_visible = capture_ok(
        captures,
        "mnt-system-vendor-init",
        "mnt-system-vendor-init-hw",
        "mnt-system-vendor-firmware",
        "mnt-system-vendor-firmware-mnt",
        "mnt-system-vendor-etc-wifi",
        "init-qcom-rc-stat",
        "wifi-hal-rc-stat",
        "firmware-bdwlan-stat",
        "firmware-regdb-stat",
        "firmware-wlanmdsp-stat",
    )
    mounted_system_visible = capture_ok(captures, "mnt-system-root", "mnt-system-system-init", "wificond-rc-stat")
    firmware_visible = all(
        capture_ok(captures, name)
        for name in ("firmware-bdwlan-stat", "firmware-regdb-stat", "firmware-wlanmdsp-stat")
    )
    native_icnss = capture_ok(captures, "icnss-stat", "icnss-tree") or "18800000.qcom,icnss" in lower
    helper_stat = capture_by_name(captures, "nl80211-helper-stat")
    helper_run = capture_by_name(captures, "nl80211-helper-run")
    helper_present = bool(helper_stat and helper_stat.ok)
    helper_ran = bool(helper_run and helper_run.ok)
    sysfs_wiphy_checked = any(capture_by_name(captures, name) is not None for name in ("sys-class-ieee80211", "ieee80211-tree"))
    basic_control_ok = capture_ok(captures, "version", "status")
    android_ready = bool(v206 and (v206.get("decision") or v206.get("classification", {}).get("decision")) == "ready-for-native-preflight-plan")
    v205_decision = v205.get("classification", {}).get("decision") if v205 else None
    v206_decision = v206.get("decision") or v206.get("classification", {}).get("decision") if v206 else None

    if not basic_control_ok:
        decision = "manual-review-required"
        reason = "native bridge/control commands did not return usable version/status evidence"
    elif not mountsystem_ok or not (mounted_vendor_visible and mounted_system_visible):
        decision = "missing-mounted-vendor"
        reason = "native mounted-system/vendor paths are not reliably visible"
    elif not native_icnss:
        decision = "missing-icnss-sysfs"
        reason = "native ICNSS platform sysfs node is not visible"
    elif not firmware_visible:
        decision = "missing-firmware-path"
        reason = "Android-mapped Wi-Fi firmware files are not all visible from native"
    elif native_wiphy or any(name.startswith(("wlan", "swlan", "p2p", "wifi-aware")) for name in native_interfaces):
        decision = "native-preflight-ready"
        reason = "native read-only preflight can see WLAN netdev or wiphy surfaces"
    elif not helper_present and not sysfs_wiphy_checked:
        decision = "missing-nl80211-helper"
        reason = "no nl80211 helper or sysfs wiphy evidence path was available"
    elif android_ready and native_icnss and firmware_visible:
        decision = "userspace-service-gap-confirmed"
        reason = "Android maps Wi-Fi readiness, but native still lacks WLAN netdev/wiphy/rfkill after read-only checks"
    else:
        decision = "missing-wiphy-netdev"
        reason = "native prerequisites are partially visible but no WLAN netdev or wiphy state exists"

    return {
        "decision": decision,
        "reason": reason,
        "basic_control_ok": basic_control_ok,
        "mountsystem_ok": mountsystem_ok,
        "mounted_vendor_visible": mounted_vendor_visible,
        "mounted_system_visible": mounted_system_visible,
        "firmware_visible": firmware_visible,
        "native_icnss": native_icnss,
        "native_interfaces": native_interfaces,
        "native_wiphy": native_wiphy,
        "native_wifi_rfkill": native_wifi_rfkill,
        "nl80211_helper_present": helper_present,
        "nl80211_helper_ran": helper_ran,
        "android_ready_from_v206": android_ready,
        "v205_decision": v205_decision,
        "v206_decision": v206_decision,
        "native_evidence_lines": relevant_lines(text),
    }


def build_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    rows = [
        ["result", "PASS" if manifest["pass"] else "FAIL", classification["reason"]],
        ["decision", classification["decision"], "no active Wi-Fi approval"],
        ["basic_control", str(classification["basic_control_ok"]), ""],
        ["mountsystem", str(classification["mountsystem_ok"]), ""],
        ["mounted_vendor", str(classification["mounted_vendor_visible"]), ""],
        ["firmware", str(classification["firmware_visible"]), ""],
        ["native_icnss", str(classification["native_icnss"]), ""],
        ["native_wiphy", str(classification["native_wiphy"]), ""],
        ["native_wifi_rfkill", str(classification["native_wifi_rfkill"]), ""],
        ["nl80211_helper", str(classification["nl80211_helper_present"]), f"ran={classification['nl80211_helper_ran']}"],
        ["android_ready_v206", str(classification["android_ready_from_v206"]), str(classification["v206_decision"])],
    ]
    lines = [
        "# v207 Native Read-Only Wi-Fi Preflight\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{classification['decision']}`\n",
        f"- reason: `{classification['reason']}`\n\n",
        "## Summary Matrix\n\n",
        markdown_table(["area", "status", "detail"], rows),
        "\n\n## Native Interfaces\n\n",
    ]
    if classification["native_interfaces"]:
        lines.extend(f"- `{item}`\n" for item in classification["native_interfaces"])
    else:
        lines.append("- none\n")
    lines.append("\n## Native Evidence Lines\n\n")
    if classification["native_evidence_lines"]:
        lines.extend(f"- `{line}`\n" for line in classification["native_evidence_lines"])
    else:
        lines.append("- none\n")
    lines.append("\n## Captures\n\n")
    for item in manifest["captures"]:
        lines.append(f"- {'OK' if item['ok'] else 'FAIL'} `{item['name']}` rc={item['rc']} file=`{item['file']}`\n")
    lines.append("\n## Guardrails\n\n")
    for item in manifest["guardrails"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def main() -> int:
    args = parse_args()
    validate_no_active_wifi_commands()
    store = EvidenceStore(args.out_dir)
    store.mkdir("native", "commands")
    captures: list[CaptureRecord] = []

    for name, command, timeout in DEVICE_COMMANDS:
        captures.append(capture_device(store, args, name, command, timeout))
    captures.extend(maybe_capture_helper(store, args))

    v205 = load_json(args.v205_manifest)
    v206 = load_json(args.v206_manifest)
    classification = classify(captures, v205, v206)
    manifest: dict[str, Any] = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": classification["decision"] in DECISIONS and classification["decision"] != "manual-review-required",
        "decision": classification["decision"],
        "reason": classification["reason"],
        "mode": "native-readonly-wifi-preflight",
        "classification": classification,
        "captures": [asdict(item) for item in captures],
        "helper": helper_metadata(args),
        "v205_native": {
            "path": str(args.v205_manifest),
            "present": v205 is not None,
            "decision": v205.get("classification", {}).get("decision") if v205 else None,
        },
        "v206_android": {
            "path": str(args.v206_manifest),
            "present": v206 is not None,
            "decision": (v206.get("decision") or v206.get("classification", {}).get("decision")) if v206 else None,
        },
        "guardrails": [
            "no Wi-Fi enablement",
            "no rfkill write",
            "no WLAN link-up",
            "no scan/connect",
            "no active nl80211 set/scan/connect commands",
            "no module load/unload",
            "no firmware path write",
            "no firmware mutation",
            "no cnss-daemon/wificond/HAL/supplicant/hostapd start",
            "default mode does not deploy helper or write device files",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    print(
        f"{'PASS' if manifest['pass'] else 'FAIL'} "
        f"out_dir={store.run_dir} "
        f"decision={classification['decision']} "
        f"reason={classification['reason']}"
    )
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
