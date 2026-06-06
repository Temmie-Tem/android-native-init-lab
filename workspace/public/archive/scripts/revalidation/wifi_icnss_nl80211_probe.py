#!/usr/bin/env python3
"""Collect native read-only ICNSS/WCNSS/QCA and nl80211 Wi-Fi evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
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
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore


WIFI_KEYWORDS = (
    "wlan",
    "wifi",
    "qca",
    "qcacld",
    "cnss",
    "icnss",
    "wcn",
    "wcnss",
    "ath",
    "cfg80211",
    "nl80211",
    "mac80211",
    "bdwlan",
    "wlanmdsp",
)

ACTIVE_PATTERNS = (
    re.compile(r"\brfkill\s+unblock\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\bNL80211_CMD_TRIGGER_SCAN\b", re.IGNORECASE),
    re.compile(r"\bNL80211_CMD_SET_INTERFACE\b", re.IGNORECASE),
    re.compile(r"\bNL80211_CMD_SET_WIPHY\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\s+set-wifi-enabled\b", re.IGNORECASE),
    re.compile(r"(?:^|[;&]\s*)(?:wpa_supplicant|hostapd|cnss-daemon)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/class/rfkill", re.IGNORECASE),
)

DEVICE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 15.0),
    ("status", ["status"], 25.0),
    ("wifiinv-full", ["wifiinv", "full"], 60.0),
    ("wififeas-full", ["wififeas", "full"], 60.0),
    ("sys-class-net", ["ls", "/sys/class/net"], 20.0),
    ("sys-class-rfkill", ["ls", "/sys/class/rfkill"], 20.0),
    ("sys-class-ieee80211", ["ls", "/sys/class/ieee80211"], 20.0),
    ("icnss-stat", ["stat", "/sys/devices/platform/soc/18800000.qcom,icnss"], 20.0),
    ("proc-cmdline", ["run", "/cache/bin/toybox", "cat", "/proc/cmdline"], 20.0),
    ("proc-modules", ["run", "/cache/bin/toybox", "cat", "/proc/modules"], 30.0),
    ("proc-net-wireless", ["run", "/cache/bin/toybox", "cat", "/proc/net/wireless"], 20.0),
    (
        "firmware-class-path",
        ["run", "/cache/bin/toybox", "cat", "/sys/module/firmware_class/parameters/path"],
        20.0,
    ),
    (
        "rfkill0-name",
        ["cat", "/sys/class/rfkill/rfkill0/name"],
        20.0,
    ),
    ("rfkill0-type", ["cat", "/sys/class/rfkill/rfkill0/type"], 20.0),
    ("rfkill0-state", ["cat", "/sys/class/rfkill/rfkill0/state"], 20.0),
    ("rfkill1-name", ["cat", "/sys/class/rfkill/rfkill1/name"], 20.0),
    ("rfkill1-type", ["cat", "/sys/class/rfkill/rfkill1/type"], 20.0),
    (
        "wlan0-operstate",
        ["cat", "/sys/class/net/wlan0/operstate"],
        20.0,
    ),
    ("swlan0-operstate", ["cat", "/sys/class/net/swlan0/operstate"], 20.0),
    ("p2p0-operstate", ["cat", "/sys/class/net/p2p0/operstate"], 20.0),
    ("wifi-aware0-operstate", ["cat", "/sys/class/net/wifi-aware0/operstate"], 20.0),
    (
        "icnss-tree",
        [
            "run",
            "/cache/bin/toybox",
            "find",
            "/sys/devices/platform/soc/18800000.qcom,icnss",
            "-maxdepth",
            "5",
        ],
        35.0,
    ),
    (
        "ieee80211-tree",
        ["run", "/cache/bin/toybox", "find", "/sys/class/ieee80211", "-maxdepth", "4"],
        25.0,
    ),
    (
        "mounted-system-init",
        ["run", "/cache/bin/toybox", "find", "/mnt/system/system/etc/init", "-maxdepth", "1"],
        35.0,
    ),
    ("mounted-vendor-firmware-stat", ["stat", "/mnt/system/vendor/firmware"], 20.0),
    ("mounted-vendor-firmware-mnt-stat", ["stat", "/mnt/system/vendor/firmware_mnt"], 20.0),
    ("mounted-vendor-etc-wifi-stat", ["stat", "/mnt/system/vendor/etc/wifi"], 20.0),
)

NL80211_HELPER_REMOTE = "/cache/bin/a90_nl80211_ro"
NL80211_HELPER_LOCAL = REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_nl80211_ro"

DECISIONS = {
    "no-native-icnss",
    "native-icnss-present-no-wiphy",
    "native-wiphy-readonly-ok",
    "android-only-driver-ready",
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
    return REPO_ROOT / "tmp" / "wifi" / f"v205-icnss-nl80211-readonly-{stamp}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", "--bridge-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v203-manifest", type=Path, default=Path("tmp/wifi/v203-baseline/manifest.json"))
    parser.add_argument("--v204-android-manifest", type=Path, default=Path("tmp/wifi/v204-android-baseline/manifest.json"))
    parser.add_argument("--helper-remote", default=NL80211_HELPER_REMOTE)
    parser.add_argument("--helper-local", type=Path, default=NL80211_HELPER_LOCAL)
    parser.add_argument("--skip-helper", action="store_true")
    parser.add_argument("--native-bridge", action="store_true", help="document intent; native bridge is the only current mode")
    return parser.parse_args()


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|serialno)=([^\s]+)", r"\1=<redacted>", text)
    return text


def validate_no_active_wifi_commands() -> None:
    command_text = "\n".join(" ".join(argv) for _, argv, _ in DEVICE_COMMANDS)
    command_text += f"\nrun {NL80211_HELPER_REMOTE}"
    for pattern in ACTIVE_PATTERNS:
        if pattern.search(command_text):
            raise RuntimeError(f"active Wi-Fi command pattern found: {pattern.pattern}")


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    path = store.write_text(f"native/commands/{safe_name(name)}.txt", redact_text(text).rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def capture_device(store: EvidenceStore,
                   args: argparse.Namespace,
                   name: str,
                   command: list[str],
                   timeout: float) -> CaptureRecord:
    capture = run_capture(args, name, command, timeout=timeout)
    body = capture.text if capture.text else f"{capture.error}\n"
    relative = write_capture(store, name, body)
    data = capture_to_manifest(capture)
    text = redact_text(data.get("text", ""))
    return CaptureRecord(
        name=name,
        command=" ".join(command),
        ok=bool(data["ok"]),
        rc=data.get("rc"),
        status=str(data.get("status", "missing")),
        duration_sec=float(data["duration_sec"]),
        file=relative,
        text=text,
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
    }


def maybe_capture_helper(store: EvidenceStore, args: argparse.Namespace) -> CaptureRecord | None:
    if args.skip_helper:
        return None
    stat_capture = capture_device(store, args, "nl80211-helper-stat", ["stat", args.helper_remote], 20.0)
    if not stat_capture.ok:
        return stat_capture
    return capture_device(store, args, "nl80211-helper-run", ["run", args.helper_remote], 30.0)


def relevant_lines(text: str, keywords: tuple[str, ...] = WIFI_KEYWORDS, limit: int = 80) -> list[str]:
    lines: list[str] = []
    lowered_keywords = tuple(item.lower() for item in keywords)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if any(keyword in lower for keyword in lowered_keywords):
            if line not in lines:
                lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def capture_text(captures: list[CaptureRecord]) -> str:
    return "\n".join(strip_cmdv1_text(item.text) for item in captures if item.text)


def capture_by_name(captures: list[CaptureRecord], name: str) -> CaptureRecord | None:
    for capture in captures:
        if capture.name == name:
            return capture
    return None


def positive_text(captures: list[CaptureRecord], names: tuple[str, ...]) -> str:
    chunks: list[str] = []
    for name in names:
        capture = capture_by_name(captures, name)
        if capture is not None and capture.ok:
            chunks.append(strip_cmdv1_text(capture.text))
    return "\n".join(chunks)


def extract_native_interfaces(captures: list[CaptureRecord], helper: CaptureRecord | None) -> list[str]:
    evidence = positive_text(captures, ("sys-class-net", "icnss-tree", "sys-class-ieee80211", "ieee80211-tree"))
    if helper is not None and helper.ok:
        evidence += "\n" + strip_cmdv1_text(helper.text)
    found: set[str] = set()
    for line in evidence.splitlines():
        line = line.strip()
        if "No such file" in line or not line:
            continue
        for match in re.finditer(r"(?:^|[/\s])(wlan[0-9]*|swlan[0-9]*|p2p[0-9]*|wifi-aware[0-9]*|phy[0-9]+)(?:$|[/\s:])", line.lower()):
            found.add(match.group(1))
        helper_match = re.search(r"\bifname=([A-Za-z0-9_.:-]+)", line)
        if helper_match:
            name = helper_match.group(1).lower()
            if re.match(r"^(wlan[0-9]*|swlan[0-9]*|p2p[0-9]*|wifi-aware[0-9]*)$", name):
                found.add(name)
    return sorted(found)


def has_native_wiphy(captures: list[CaptureRecord], helper: CaptureRecord | None, native_interfaces: list[str]) -> bool:
    evidence = positive_text(captures, ("sys-class-ieee80211", "ieee80211-tree", "icnss-tree"))
    if helper is not None and helper.ok:
        evidence += "\n" + strip_cmdv1_text(helper.text)
    lower = evidence.lower()
    return "wiphy[" in lower or "/ieee80211/phy" in lower or any(name.startswith("phy") for name in native_interfaces)


def classify(captures: list[CaptureRecord], helper: CaptureRecord | None, v204: dict[str, Any] | None) -> dict[str, Any]:
    text = capture_text(captures + ([helper] if helper is not None else []))
    lower = text.lower()
    native_interfaces = extract_native_interfaces(captures, helper)
    native_icnss = "icnss" in lower or "18800000.qcom,icnss" in lower
    native_wifi_rfkill = False
    for line in lower.splitlines():
        if "rfkill" not in line and "type=" not in line and "name=" not in line:
            continue
        if "type=wifi" in line or "type=wlan" in line:
            native_wifi_rfkill = True
            break
        name_match = re.search(r"\bname=([^\s]+)", line)
        if name_match:
            name_value = name_match.group(1)
            if name_value != "bt_power" and re.search(r"(wifi|wlan|phy)", name_value):
                native_wifi_rfkill = True
                break
        if "/ieee80211/" in line and "/rfkill" in line:
            native_wifi_rfkill = True
            break
    native_wiphy = has_native_wiphy(captures, helper, native_interfaces)
    nl80211_family = "family nl80211" in lower or "nl80211=missing" in lower
    nl80211_missing = "nl80211=missing" in lower or "family=no" in lower
    android_ready = bool(v204 and v204.get("decision") == "ready-for-readonly-nl80211-probe-plan")
    android_counts = v204.get("classification_counts", {}) if v204 else {}

    if native_wiphy or any(name.startswith(("wlan", "swlan", "p2p", "wifi-aware")) for name in native_interfaces):
        decision = "native-wiphy-readonly-ok"
        reason = "native read-only probe exposed WLAN/wiphy/interface evidence"
    elif native_icnss or native_wifi_rfkill:
        decision = "native-icnss-present-no-wiphy"
        reason = "native sees ICNSS or Wi-Fi rfkill hints but no read-only wiphy/interface"
    elif android_ready:
        decision = "android-only-driver-ready"
        reason = "Android exposes WLAN/ICNSS readiness while native still lacks ICNSS/wiphy gates"
    else:
        decision = "no-native-icnss"
        reason = "native read-only probe found no ICNSS, wiphy, WLAN netdev, or Wi-Fi rfkill evidence"

    return {
        "decision": decision,
        "reason": reason,
        "native_interfaces": native_interfaces,
        "native_icnss": native_icnss,
        "native_wifi_rfkill": native_wifi_rfkill,
        "native_wiphy": native_wiphy,
        "nl80211_family_seen": nl80211_family,
        "nl80211_missing": nl80211_missing,
        "android_ready": android_ready,
        "android_classification_counts": android_counts,
        "native_evidence_lines": relevant_lines(text, limit=120),
    }


def build_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    rows = [
        ["result", "PASS" if manifest["pass"] else "FAIL", classification["reason"]],
        ["decision", classification["decision"], "no active Wi-Fi approval"],
        ["native_icnss", str(classification["native_icnss"]), ""],
        ["native_wiphy", str(classification["native_wiphy"]), ""],
        ["native_wifi_rfkill", str(classification["native_wifi_rfkill"]), ""],
        ["nl80211", "missing" if classification["nl80211_missing"] else str(classification["nl80211_family_seen"]), ""],
        ["android_ready", str(classification["android_ready"]), str(classification["android_classification_counts"])],
    ]
    lines = [
        "# v205 ICNSS/WCNSS/QCA + nl80211 Read-Only Probe\n\n",
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

    helper = maybe_capture_helper(store, args)
    if helper is not None:
        captures.append(helper)

    v203 = load_json(args.v203_manifest)
    v204 = load_json(args.v204_android_manifest)
    classification = classify(captures, helper, v204)
    manifest: dict[str, Any] = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": classification["decision"] in DECISIONS,
        "classification": classification,
        "captures": [asdict(item) for item in captures],
        "helper": helper_metadata(args),
        "v203": {
            "path": str(args.v203_manifest),
            "present": v203 is not None,
            "decision": v203.get("decision") if v203 else None,
            "missing_gates": v203.get("missing_gates") if v203 else None,
        },
        "v204_android": {
            "path": str(args.v204_android_manifest),
            "present": v204 is not None,
            "decision": v204.get("decision") if v204 else None,
            "classification_counts": v204.get("classification_counts") if v204 else None,
        },
        "guardrails": [
            "no Wi-Fi enablement",
            "no rfkill write",
            "no WLAN link-up",
            "no scan/connect",
            "no module load/unload",
            "no firmware mutation",
            "no Android Wi-Fi service/supplicant/hostapd start",
            "nl80211 helper is GET-only when present",
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
