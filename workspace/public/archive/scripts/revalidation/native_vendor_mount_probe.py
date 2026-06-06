#!/usr/bin/env python3
"""Collect native read-only vendor/firmware mount visibility evidence."""

from __future__ import annotations

import argparse
import datetime as dt
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


VENDOR_KEYWORDS = (
    "vendor",
    "firmware",
    "firmware_mnt",
    "bdwlan",
    "regdb",
    "wlanmdsp",
    "wifi",
    "wlan",
    "cnss",
    "icnss",
    "super",
    "dm-",
    "sda29",
    "sda30",
    "sda32",
    "by-name",
)

MUTATING_PATTERNS = (
    re.compile(r"\bmountfs\b", re.IGNORECASE),
    re.compile(r"\bumount\b", re.IGNORECASE),
    re.compile(r"\bmount\s+", re.IGNORECASE),
    re.compile(r"\bdd\s+", re.IGNORECASE),
    re.compile(r"\bmkfs(?:\.[A-Za-z0-9_+-]+)?\b", re.IGNORECASE),
    re.compile(r"\bsgdisk\b", re.IGNORECASE),
    re.compile(r"\bparted\b", re.IGNORECASE),
    re.compile(r"\bblockdev\s+--set", re.IGNORECASE),
    re.compile(r"\bdmsetup\s+(?:create|remove|load|reload|suspend|resume)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/module/firmware_class/parameters/path", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\b", re.IGNORECASE),
)

DEVICE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 15.0),
    ("status", ["status"], 25.0),
    ("bootstatus", ["bootstatus"], 25.0),
    ("mounts", ["mounts"], 20.0),
    ("proc-mounts", ["cat", "/proc/mounts"], 20.0),
    ("proc-partitions", ["cat", "/proc/partitions"], 20.0),
    ("dev-block-root", ["ls", "/dev/block"], 20.0),
    ("dev-block-by-name", ["ls", "/dev/block/by-name"], 20.0),
    ("dev-block-bootdevice-by-name", ["ls", "/dev/block/bootdevice/by-name"], 20.0),
    ("dev-block-platform", ["run", "/cache/bin/toybox", "find", "/dev/block/platform", "-maxdepth", "5"], 35.0),
    ("sys-class-block", ["run", "/cache/bin/toybox", "find", "/sys/class/block", "-maxdepth", "3"], 45.0),
    ("sys-block", ["run", "/cache/bin/toybox", "find", "/sys/block", "-maxdepth", "3"], 45.0),
    ("dev-sda28-stat", ["stat", "/dev/block/sda28"], 20.0),
    ("dev-sda29-stat", ["stat", "/dev/block/sda29"], 20.0),
    ("dev-sda30-stat", ["stat", "/dev/block/sda30"], 20.0),
    ("dev-sda32-stat", ["stat", "/dev/block/sda32"], 20.0),
    ("dev-super-stat", ["stat", "/dev/block/super"], 20.0),
    ("dev-metadata-stat", ["stat", "/dev/block/metadata"], 20.0),
    ("sys-sda28-dev", ["cat", "/sys/class/block/sda28/dev"], 20.0),
    ("sys-sda28-size", ["cat", "/sys/class/block/sda28/size"], 20.0),
    ("sys-sda29-dev", ["cat", "/sys/class/block/sda29/dev"], 20.0),
    ("sys-sda29-size", ["cat", "/sys/class/block/sda29/size"], 20.0),
    ("sys-sda29-ro", ["cat", "/sys/class/block/sda29/ro"], 20.0),
    ("sys-sda30-dev", ["cat", "/sys/class/block/sda30/dev"], 20.0),
    ("sys-sda30-size", ["cat", "/sys/class/block/sda30/size"], 20.0),
    ("sys-sda32-dev", ["cat", "/sys/class/block/sda32/dev"], 20.0),
    ("sys-sda32-size", ["cat", "/sys/class/block/sda32/size"], 20.0),
    ("dm-0-name", ["cat", "/sys/class/block/dm-0/dm/name"], 20.0),
    ("dm-1-name", ["cat", "/sys/class/block/dm-1/dm/name"], 20.0),
    ("dm-2-name", ["cat", "/sys/class/block/dm-2/dm/name"], 20.0),
    ("dm-3-name", ["cat", "/sys/class/block/dm-3/dm/name"], 20.0),
    ("dm-4-name", ["cat", "/sys/class/block/dm-4/dm/name"], 20.0),
    ("dm-5-name", ["cat", "/sys/class/block/dm-5/dm/name"], 20.0),
    ("mnt-system-root", ["ls", "/mnt/system"], 20.0),
    ("mnt-system-vendor", ["ls", "/mnt/system/vendor"], 20.0),
    ("mnt-system-vendor-init", ["ls", "/mnt/system/vendor/etc/init"], 20.0),
    ("mnt-system-vendor-init-hw", ["ls", "/mnt/system/vendor/etc/init/hw"], 20.0),
    ("mnt-system-vendor-firmware", ["ls", "/mnt/system/vendor/firmware"], 20.0),
    ("mnt-system-vendor-firmware-mnt", ["ls", "/mnt/system/vendor/firmware_mnt"], 20.0),
    ("mnt-system-vendor-etc-wifi", ["ls", "/mnt/system/vendor/etc/wifi"], 20.0),
    ("root-vendor", ["ls", "/vendor"], 20.0),
    ("root-vendor-firmware", ["ls", "/vendor/firmware"], 20.0),
    ("root-vendor-firmware-mnt", ["ls", "/vendor/firmware_mnt"], 20.0),
    ("root-vendor-firmware-mnt-image", ["ls", "/vendor/firmware_mnt/image"], 20.0),
    ("firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 20.0),
)

DECISIONS = {
    "vendor-visible-existing-mount",
    "vendor-block-candidate-found",
    "dynamic-partition-mapping-required",
    "vendor-path-still-missing",
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
    return REPO_ROOT / "tmp" / "wifi" / f"v208-vendor-firmware-mount-{stamp}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", "--bridge-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v207-manifest", type=Path, default=Path("tmp/wifi/v207-native-wifi-preflight/manifest.json"))
    parser.add_argument("--v206-manifest", type=Path, default=Path("tmp/wifi/v206-android-icnss-cnss-map/manifest.json"))
    parser.add_argument("--native-bridge", action="store_true", help="document intent; native bridge is the current mode")
    return parser.parse_args()


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|serialno)=([^\s]+)", r"\1=<redacted>", text)
    return text


def validate_no_mutating_commands() -> None:
    command_text = "\n".join(" ".join(argv) for _, argv, _ in DEVICE_COMMANDS)
    for pattern in MUTATING_PATTERNS:
        if pattern.search(command_text):
            raise RuntimeError(f"mutating command pattern found: {pattern.pattern}")


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


def has_partition(text: str, name: str) -> bool:
    return re.search(rf"\b{name}\b", text) is not None


def has_vendor_byname(text: str) -> bool:
    for line in text.splitlines():
        lower = line.lower()
        if "vendor" in lower and ("by-name" in lower or " vendor" in lower or lower.endswith("vendor")):
            return True
    return False


def dm_names(captures: list[CaptureRecord]) -> list[str]:
    names: list[str] = []
    for capture in captures:
        if not capture.name.startswith("dm-") or not capture.name.endswith("-name") or not capture.ok:
            continue
        text = strip_cmdv1_text(capture.text).strip()
        if text:
            names.append(text)
    return sorted(set(names))


def relevant_lines(text: str, limit: int = 160) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if any(term in lower for term in VENDOR_KEYWORDS):
            if line not in lines:
                lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def classify(captures: list[CaptureRecord], v207: dict[str, Any] | None, v206: dict[str, Any] | None) -> dict[str, Any]:
    all_text = strip_all(captures)
    lower = all_text.lower()
    basic_control_ok = capture_ok(captures, "version", "status")
    partitions_text = capture_text(captures, "proc-partitions")
    byname_text = capture_text(captures, "dev-block-by-name", "dev-block-bootdevice-by-name", "dev-block-platform")
    mount_text = capture_text(captures, "proc-mounts", "mounts")
    sys_block_text = capture_text(captures, "sys-class-block", "sys-block")
    dm_name_list = dm_names(captures)

    existing_vendor_mount = (
        capture_ok(captures, "mnt-system-vendor-init", "mnt-system-vendor-firmware", "mnt-system-vendor-etc-wifi")
        or capture_ok(captures, "root-vendor-firmware", "root-vendor-firmware-mnt", "root-vendor-firmware-mnt-image")
    )
    existing_android_firmware_path = any(
        token in lower
        for token in (
            "bdwlan.bin",
            "regdb.bin",
            "wlanmdsp.mbn",
            "/vendor/firmware_mnt/image",
        )
    ) and existing_vendor_mount
    known_physical_vendor = (
        has_partition(partitions_text, "sda29")
        or capture_ok(captures, "dev-sda29-stat", "sys-sda29-dev", "sys-sda29-size")
        or "/sys/class/block/sda29" in sys_block_text
    )
    product_or_omr_candidates = (
        has_partition(partitions_text, "sda30")
        or has_partition(partitions_text, "sda32")
        or capture_ok(captures, "dev-sda30-stat", "dev-sda32-stat", "sys-sda30-dev", "sys-sda32-dev")
    )
    byname_vendor = has_vendor_byname(byname_text)
    dm_vendor = any("vendor" in name.lower() for name in dm_name_list)
    dm_or_super_present = (
        bool(dm_name_list)
        or re.search(r"(?:^|[/\s])dm-[0-9]+(?:$|[/\s])", sys_block_text) is not None
        or has_partition(partitions_text, "super")
        or "/sys/class/block/super" in sys_block_text
        or capture_ok(captures, "dev-super-stat")
    )
    firmware_class_path = capture_text(captures, "firmware-class-path").strip()
    v207_decision = (v207.get("decision") or v207.get("classification", {}).get("decision")) if v207 else None
    v206_decision = (v206.get("decision") or v206.get("classification", {}).get("decision")) if v206 else None

    if not basic_control_ok:
        decision = "manual-review-required"
        reason = "native bridge/control commands did not return usable evidence"
    elif existing_vendor_mount or existing_android_firmware_path:
        decision = "vendor-visible-existing-mount"
        reason = "vendor firmware/init assets are visible from an existing native mount path"
    elif known_physical_vendor or byname_vendor or dm_vendor:
        decision = "vendor-block-candidate-found"
        reason = "a plausible vendor block candidate exists, but default native mounts do not expose vendor assets"
    elif dm_or_super_present:
        decision = "dynamic-partition-mapping-required"
        reason = "super/dm evidence exists but no vendor-specific logical path is visible"
    else:
        decision = "vendor-path-still-missing"
        reason = "no plausible vendor block or mount candidate was found"

    return {
        "decision": decision,
        "reason": reason,
        "basic_control_ok": basic_control_ok,
        "existing_vendor_mount": existing_vendor_mount,
        "existing_android_firmware_path": existing_android_firmware_path,
        "known_physical_vendor": known_physical_vendor,
        "product_or_omr_candidates": product_or_omr_candidates,
        "byname_vendor": byname_vendor,
        "dm_vendor": dm_vendor,
        "dm_or_super_present": dm_or_super_present,
        "dm_names": dm_name_list,
        "firmware_class_path": firmware_class_path,
        "v207_decision": v207_decision,
        "v206_decision": v206_decision,
        "mount_evidence_lines": relevant_lines(mount_text, limit=80),
        "block_evidence_lines": relevant_lines(partitions_text + "\n" + byname_text + "\n" + sys_block_text, limit=160),
        "path_evidence_lines": relevant_lines(all_text, limit=160),
    }


def build_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    rows = [
        ["result", "PASS" if manifest["pass"] else "FAIL", classification["reason"]],
        ["decision", classification["decision"], "no mount/write by default"],
        ["basic_control", str(classification["basic_control_ok"]), ""],
        ["existing_vendor_mount", str(classification["existing_vendor_mount"]), ""],
        ["known_physical_vendor", str(classification["known_physical_vendor"]), "sda29/by-name/dm vendor candidate"],
        ["product_or_omr", str(classification["product_or_omr_candidates"]), "sda30/sda32 reference candidates"],
        ["byname_vendor", str(classification["byname_vendor"]), ""],
        ["dm_vendor", str(classification["dm_vendor"]), ",".join(classification["dm_names"])],
        ["dm_or_super", str(classification["dm_or_super_present"]), ""],
        ["firmware_class_path", classification["firmware_class_path"], ""],
        ["v207", str(classification["v207_decision"]), ""],
        ["v206", str(classification["v206_decision"]), ""],
    ]
    lines = [
        "# v208 Native Vendor/Firmware Mount Visibility\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{classification['decision']}`\n",
        f"- reason: `{classification['reason']}`\n\n",
        "## Summary Matrix\n\n",
        markdown_table(["area", "status", "detail"], rows),
        "\n\n## Mount Evidence Lines\n\n",
    ]
    if classification["mount_evidence_lines"]:
        lines.extend(f"- `{line}`\n" for line in classification["mount_evidence_lines"])
    else:
        lines.append("- none\n")
    lines.append("\n## Block Evidence Lines\n\n")
    if classification["block_evidence_lines"]:
        lines.extend(f"- `{line}`\n" for line in classification["block_evidence_lines"])
    else:
        lines.append("- none\n")
    lines.append("\n## Path Evidence Lines\n\n")
    if classification["path_evidence_lines"]:
        lines.extend(f"- `{line}`\n" for line in classification["path_evidence_lines"])
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
    validate_no_mutating_commands()
    store = EvidenceStore(args.out_dir)
    store.mkdir("native", "commands")
    captures: list[CaptureRecord] = []

    for name, command, timeout in DEVICE_COMMANDS:
        captures.append(capture_device(store, args, name, command, timeout))

    v207 = load_json(args.v207_manifest)
    v206 = load_json(args.v206_manifest)
    classification = classify(captures, v207, v206)
    manifest: dict[str, Any] = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": classification["decision"] in DECISIONS and classification["decision"] != "manual-review-required",
        "decision": classification["decision"],
        "reason": classification["reason"],
        "mode": "native-readonly-vendor-firmware-mount-visibility",
        "classification": classification,
        "captures": [asdict(item) for item in captures],
        "v207_native": {
            "path": str(args.v207_manifest),
            "present": v207 is not None,
            "decision": (v207.get("decision") or v207.get("classification", {}).get("decision")) if v207 else None,
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
            "no module load/unload",
            "no firmware path write",
            "no firmware mutation",
            "no cnss-daemon/wificond/HAL/supplicant/hostapd start",
            "no vendor/product/system writes",
            "no mount/umount by default",
            "no destructive storage commands",
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
