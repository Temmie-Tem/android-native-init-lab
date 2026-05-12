#!/usr/bin/env python3
"""Probe native vendor partition visibility through a safe temporary ro,noload mount."""

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


PROBE_PREFIX = "/tmp/a90-v209-"
EXPECTED_BLOCK = "sda29"
EXPECTED_MAJOR = "259"
EXPECTED_MINOR = "22"
V208_EXPECTED_DECISION = "vendor-block-candidate-found"

DECISIONS = {
    "vendor-assets-visible",
    "vendor-mounted-no-wifi-assets",
    "vendor-mount-failed",
    "candidate-node-missing",
    "unsafe-ro-noload-unavailable",
    "cleanup-failed",
    "manual-review-required",
}

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 15.0),
    ("status", ["status"], 25.0),
    ("bootstatus", ["bootstatus"], 25.0),
    ("pre-proc-mounts", ["cat", "/proc/mounts"], 20.0),
    ("proc-filesystems", ["cat", "/proc/filesystems"], 20.0),
    ("sys-sda29-dev", ["cat", "/sys/class/block/sda29/dev"], 20.0),
    ("sys-sda29-size", ["cat", "/sys/class/block/sda29/size"], 20.0),
    ("sys-sda29-ro", ["cat", "/sys/class/block/sda29/ro"], 20.0),
    ("sys-dev-block-sda29", ["ls", "/sys/dev/block/259:22"], 20.0),
    ("dev-block-sda29-stat-before", ["stat", "/dev/block/sda29"], 20.0),
    ("tmp-root-before", ["ls", "/tmp"], 20.0),
)

ASSET_RELATIVE_PATHS = (
    "etc/init",
    "etc/init/hw",
    "etc/init/android.hardware.wifi.supplicant-service.rc",
    "etc/init/android.hardware.wifi@1.0-service.rc",
    "etc/init/hostapd.android.rc",
    "etc/init/hw/init.qcom.rc",
    "etc/wifi",
    "firmware",
    "firmware/wlan",
    "firmware/wlan/qca_cld",
    "firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini",
    "firmware/wlan/qca_cld/bdwlan.bin",
    "firmware/wlan/qca_cld/regdb.bin",
    "firmware/wlanmdsp.mbn",
    "firmware_mnt",
    "firmware_mnt/image",
    "firmware_mnt/image/bdwlan.bin",
    "firmware_mnt/image/regdb.bin",
    "lib/modules",
)

ACTIVE_WIFI_PATTERNS = (
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
)

FORBIDDEN_STORAGE_PATTERNS = (
    re.compile(r"\bmountfs\b", re.IGNORECASE),
    re.compile(r"\b(?:dd|mkfs|sgdisk|parted|fsck|e2fsck)\b", re.IGNORECASE),
    re.compile(r"\bblockdev\s+--set", re.IGNORECASE),
    re.compile(r"\bdmsetup\s+(?:create|remove|load|reload|suspend|resume)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/module/firmware_class/parameters/path", re.IGNORECASE),
)


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


@dataclass(frozen=True)
class ProbePaths:
    run_id: str
    base: str
    node: str
    mountpoint: str


def default_out_dir() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return REPO_ROOT / "tmp" / "wifi" / f"v209-vendor-ro-mount-probe-{stamp}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", "--bridge-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v208-manifest", type=Path, default=Path("tmp/wifi/v208-vendor-firmware-mount/manifest.json"))
    parser.add_argument("--v206-manifest", type=Path, default=Path("tmp/wifi/v206-android-icnss-cnss-map/manifest.json"))
    parser.add_argument("--run-id", default="", help="optional safe suffix for /tmp/a90-v209-<run-id>")
    parser.add_argument("--allow-non-v208-decision", action="store_true")
    parser.add_argument("--native-bridge", action="store_true", help="document intent; native bridge is the current mode")
    return parser.parse_args()


def make_run_id(value: str = "") -> str:
    if value:
        run_id = value
    else:
        run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"[A-Za-z0-9_.+-]{1,64}", run_id):
        raise RuntimeError(f"unsafe run id: {run_id!r}")
    return run_id


def make_probe_paths(run_id: str) -> ProbePaths:
    base = f"{PROBE_PREFIX}{run_id}"
    return ProbePaths(run_id=run_id, base=base, node=f"{base}/sda29", mountpoint=f"{base}/vendor")


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|serialno)=([^\s]+)", r"\1=<redacted>", text)
    return text


def is_under_probe_path(path: str, probe: ProbePaths) -> bool:
    return path == probe.base or path.startswith(probe.base + "/")


def validate_probe_command(command: list[str], probe: ProbePaths) -> None:
    if not command:
        raise RuntimeError("empty probe command")
    joined = " ".join(command)
    for pattern in ACTIVE_WIFI_PATTERNS + FORBIDDEN_STORAGE_PATTERNS:
        if pattern.search(joined):
            raise RuntimeError(f"forbidden command pattern {pattern.pattern!r}: {joined}")

    name = command[0]
    if name in {"version", "status", "bootstatus", "cat", "ls", "stat", "mounts"}:
        return
    if name == "mkdir":
        if len(command) != 2 or not is_under_probe_path(command[1], probe):
            raise RuntimeError(f"mkdir outside probe path: {joined}")
        return
    if name == "mknodb":
        if command != ["mknodb", probe.node, EXPECTED_MAJOR, EXPECTED_MINOR]:
            raise RuntimeError(f"unexpected mknodb command: {joined}")
        return
    if name == "umount":
        if command != ["umount", probe.mountpoint]:
            raise RuntimeError(f"unexpected umount command: {joined}")
        return
    if name == "run":
        if len(command) >= 3 and command[1] == "/cache/bin/toybox" and command[2] == "find":
            if len(command) < 4 or not is_under_probe_path(command[3], probe):
                raise RuntimeError(f"find outside probe path: {joined}")
            return
        expected_mount = [
            "run",
            "/cache/bin/toybox",
            "mount",
            "-t",
            "ext4",
            "-o",
            "ro,noload",
            probe.node,
            probe.mountpoint,
        ]
        if command == expected_mount:
            return
        if len(command) >= 3 and command[1] == "/cache/bin/toybox" and command[2] == "mount":
            raise RuntimeError(f"mount command must be exact ro,noload probe mount: {joined}")
        raise RuntimeError(f"unexpected run command: {joined}")
    raise RuntimeError(f"unexpected command: {joined}")


def build_probe_commands(probe: ProbePaths) -> tuple[tuple[str, list[str], float], ...]:
    return (
        ("mkdir-base", ["mkdir", probe.base], 20.0),
        ("mkdir-mountpoint", ["mkdir", probe.mountpoint], 20.0),
        ("mknodb-sda29", ["mknodb", probe.node, EXPECTED_MAJOR, EXPECTED_MINOR], 20.0),
        ("temp-node-stat", ["stat", probe.node], 20.0),
        ("safe-ro-noload-mount", ["run", "/cache/bin/toybox", "mount", "-t", "ext4", "-o", "ro,noload", probe.node, probe.mountpoint], 45.0),
        ("mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0),
    )


def build_asset_commands(probe: ProbePaths) -> tuple[tuple[str, list[str], float], ...]:
    commands: list[tuple[str, list[str], float]] = [
        ("mounted-root", ["ls", probe.mountpoint], 20.0),
        ("mounted-find-shallow", ["run", "/cache/bin/toybox", "find", probe.mountpoint, "-maxdepth", "3"], 45.0),
    ]
    for rel_path in ASSET_RELATIVE_PATHS:
        remote_path = f"{probe.mountpoint}/{rel_path}"
        commands.append((f"asset-{safe_name(rel_path)}", ["stat", remote_path], 20.0))
        if rel_path in {"etc/init", "etc/init/hw", "etc/wifi", "firmware", "firmware/wlan", "firmware/wlan/qca_cld", "firmware_mnt", "firmware_mnt/image", "lib/modules"}:
            commands.append((f"list-{safe_name(rel_path)}", ["ls", remote_path], 20.0))
    return tuple(commands)


def build_cleanup_commands(probe: ProbePaths) -> tuple[tuple[str, list[str], float], ...]:
    return (
        ("cleanup-umount", ["umount", probe.mountpoint], 25.0),
        ("post-proc-mounts", ["cat", "/proc/mounts"], 20.0),
        ("tmp-base-after", ["ls", probe.base], 20.0),
    )


def validate_probe_commands() -> None:
    probe = make_probe_paths("guard")
    for _, command, _ in READ_ONLY_COMMANDS + build_probe_commands(probe) + build_asset_commands(probe) + build_cleanup_commands(probe):
        validate_probe_command(command, probe)


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    path = store.write_text(f"native/commands/{safe_name(name)}.txt", redact_text(text).rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def capture_device(
    store: EvidenceStore,
    args: argparse.Namespace,
    probe: ProbePaths,
    name: str,
    command: list[str],
    timeout: float,
) -> CaptureRecord:
    validate_probe_command(command, probe)
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


def strip_all(captures: list[CaptureRecord]) -> str:
    return "\n".join(strip_cmdv1_text(capture.text) for capture in captures if capture.text)


def parse_major_minor(text: str) -> tuple[str, str] | None:
    match = re.search(r"\b(\d+):(\d+)\b", text)
    if not match:
        return None
    return match.group(1), match.group(2)


def mountpoint_in_text(text: str, probe: ProbePaths) -> bool:
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == probe.mountpoint:
            return True
    return False


def extract_android_vendor_paths(v206: dict[str, Any] | None) -> list[str]:
    if not v206:
        return []
    text = json.dumps(v206, ensure_ascii=False)
    paths = sorted(set(re.findall(r"/vendor/[A-Za-z0-9_./@+-]+", text)))
    interesting = []
    for path in paths:
        lower = path.lower()
        if any(token in lower for token in ("wifi", "wlan", "firmware", "cnss", "icnss", "qca", "hostapd", "supplicant", "init")):
            interesting.append(path.rstrip(".,'\""))
    return interesting[:160]


def visible_asset_paths(captures: list[CaptureRecord], probe: ProbePaths) -> list[str]:
    visible: list[str] = []
    prefix = probe.mountpoint + "/"
    for capture in captures:
        if not capture.name.startswith(("asset-", "list-", "mounted-")):
            continue
        text = strip_cmdv1_text(capture.text)
        if not capture.ok:
            continue
        for rel_path in ASSET_RELATIVE_PATHS:
            remote_path = prefix + rel_path
            if remote_path in capture.command or remote_path in text:
                if rel_path not in visible:
                    visible.append(rel_path)
    return visible


def firmware_asset_count(visible: list[str]) -> int:
    return sum(1 for path in visible if any(token in path.lower() for token in ("bdwlan", "regdb", "wlanmdsp", "firmware", "wifi", "wlan", "hostapd", "supplicant")))


def classify(
    captures: list[CaptureRecord],
    probe: ProbePaths,
    v208: dict[str, Any] | None,
    v206: dict[str, Any] | None,
    allow_non_v208_decision: bool,
) -> dict[str, Any]:
    basic_control_ok = capture_ok(captures, "version", "status")
    v208_decision = (v208.get("decision") or v208.get("classification", {}).get("decision")) if v208 else None
    v206_decision = (v206.get("decision") or v206.get("classification", {}).get("decision")) if v206 else None
    sys_dev_text = capture_text(captures, "sys-sda29-dev")
    major_minor = parse_major_minor(sys_dev_text)
    expected_major_minor = major_minor == (EXPECTED_MAJOR, EXPECTED_MINOR)
    ext4_available = "ext4" in capture_text(captures, "proc-filesystems").split()
    mount_capture = capture_by_name(captures, "safe-ro-noload-mount")
    mount_attempted = mount_capture is not None
    mount_ok = mount_capture.ok if mount_capture is not None else False
    mounted_text = capture_text(captures, "mounted-proc-mounts")
    mounted_after_mount = mountpoint_in_text(mounted_text, probe)
    cleanup_capture = capture_by_name(captures, "cleanup-umount")
    cleanup_attempted = cleanup_capture is not None
    cleanup_rc = cleanup_capture.rc if cleanup_capture is not None else None
    post_mounts_text = capture_text(captures, "post-proc-mounts")
    leftover_mount = mountpoint_in_text(post_mounts_text, probe)
    visible = visible_asset_paths(captures, probe)
    firmware_count = firmware_asset_count(visible)
    android_paths = extract_android_vendor_paths(v206)
    all_text = strip_all(captures)

    if not basic_control_ok:
        decision = "manual-review-required"
        reason = "native bridge/control commands did not return usable evidence"
    elif not allow_non_v208_decision and v208_decision != V208_EXPECTED_DECISION:
        decision = "manual-review-required"
        reason = f"v208 decision is {v208_decision!r}, expected {V208_EXPECTED_DECISION!r}"
    elif not expected_major_minor:
        decision = "candidate-node-missing"
        reason = "sda29 major/minor could not be confirmed as 259:22"
    elif not ext4_available:
        decision = "unsafe-ro-noload-unavailable"
        reason = "ext4 is not listed in /proc/filesystems"
    elif mount_attempted and mount_capture is not None and not mount_ok and re.search(r"not found|no such file|invalid option|unknown option|bad option|usage", mount_capture.text + mount_capture.error, re.IGNORECASE):
        decision = "unsafe-ro-noload-unavailable"
        reason = "safe ro,noload mount command path is unavailable or unsupported"
    elif leftover_mount:
        decision = "cleanup-failed"
        reason = "temporary vendor mount remained after cleanup"
    elif mount_ok and mounted_after_mount and firmware_count > 0:
        decision = "vendor-assets-visible"
        reason = "safe ro,noload mount exposed vendor firmware/init assets"
    elif mount_ok and mounted_after_mount:
        decision = "vendor-mounted-no-wifi-assets"
        reason = "safe ro,noload mount succeeded but expected Wi-Fi/CNSS assets were not visible"
    elif mount_attempted:
        decision = "vendor-mount-failed"
        reason = "temporary block node existed but safe ro,noload mount did not expose a mounted filesystem"
    else:
        decision = "manual-review-required"
        reason = "probe did not reach a mount decision"

    return {
        "decision": decision,
        "reason": reason,
        "basic_control_ok": basic_control_ok,
        "v208_decision": v208_decision,
        "v206_decision": v206_decision,
        "major_minor": ":".join(major_minor) if major_minor else None,
        "expected_major_minor": expected_major_minor,
        "ext4_available": ext4_available,
        "mount_attempted": mount_attempted,
        "mount_ok": mount_ok,
        "mounted_after_mount": mounted_after_mount,
        "cleanup_attempted": cleanup_attempted,
        "cleanup_rc": cleanup_rc,
        "leftover_mount": leftover_mount,
        "probe_base": probe.base,
        "probe_node": probe.node,
        "probe_mountpoint": probe.mountpoint,
        "visible_asset_paths": visible,
        "visible_asset_count": len(visible),
        "firmware_asset_count": firmware_count,
        "android_vendor_path_sample": android_paths[:40],
        "android_vendor_path_count": len(android_paths),
        "mount_error_sample": ((mount_capture.text or mount_capture.error)[:1200] if mount_capture is not None and not mount_ok else ""),
        "evidence_lines": relevant_lines(all_text, probe),
    }


def relevant_lines(text: str, probe: ProbePaths, limit: int = 180) -> list[str]:
    keywords = (
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
        "sda29",
        probe.base,
        probe.mountpoint,
        "ro,noload",
        "ext4",
    )
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if any(term.lower() in lower for term in keywords):
            if line not in lines:
                lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def build_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    rows = [
        ["result", "PASS" if manifest["pass"] else "FAIL", c["reason"]],
        ["decision", c["decision"], "ro,noload only"],
        ["v208", str(c["v208_decision"]), ""],
        ["major_minor", str(c["major_minor"]), f"expected={c['expected_major_minor']}"],
        ["ext4", str(c["ext4_available"]), ""],
        ["mount", str(c["mount_ok"]), f"attempted={c['mount_attempted']} mounted={c['mounted_after_mount']}"],
        ["cleanup", str(not c["leftover_mount"]), f"attempted={c['cleanup_attempted']} rc={c['cleanup_rc']}"],
        ["assets", str(c["visible_asset_count"]), f"firmware_like={c['firmware_asset_count']}"],
        ["probe_base", c["probe_base"], ""],
    ]
    lines = [
        "# v209 Vendor Read-Only Mount Probe\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{c['decision']}`\n",
        f"- reason: `{c['reason']}`\n\n",
        "## Summary Matrix\n\n",
        markdown_table(["area", "status", "detail"], rows),
        "\n\n## Visible Asset Paths\n\n",
    ]
    if c["visible_asset_paths"]:
        lines.extend(f"- `{path}`\n" for path in c["visible_asset_paths"])
    else:
        lines.append("- none\n")
    lines.append("\n## Android Vendor Path Sample\n\n")
    if c["android_vendor_path_sample"]:
        lines.extend(f"- `{path}`\n" for path in c["android_vendor_path_sample"])
    else:
        lines.append("- none\n")
    lines.append("\n## Evidence Lines\n\n")
    if c["evidence_lines"]:
        lines.extend(f"- `{line}`\n" for line in c["evidence_lines"])
    else:
        lines.append("- none\n")
    if c["mount_error_sample"]:
        lines.extend(["\n## Mount Error Sample\n\n", "```text\n", c["mount_error_sample"].rstrip() + "\n", "```\n"])
    lines.append("\n## Captures\n\n")
    for item in manifest["captures"]:
        lines.append(f"- {'OK' if item['ok'] else 'FAIL'} `{item['name']}` rc={item['rc']} file=`{item['file']}`\n")
    lines.append("\n## Guardrails\n\n")
    for item in manifest["guardrails"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def run_sequence(
    store: EvidenceStore,
    args: argparse.Namespace,
    probe: ProbePaths,
    sequence: tuple[tuple[str, list[str], float], ...],
    captures: list[CaptureRecord],
) -> None:
    for name, command, timeout in sequence:
        captures.append(capture_device(store, args, probe, name, command, timeout))


def main() -> int:
    args = parse_args()
    validate_probe_commands()
    run_id = make_run_id(args.run_id)
    probe = make_probe_paths(run_id)
    store = EvidenceStore(args.out_dir)
    store.mkdir("native", "commands")
    captures: list[CaptureRecord] = []

    for name, command, timeout in READ_ONLY_COMMANDS:
        captures.append(capture_device(store, args, probe, name, command, timeout))

    v208 = load_json(args.v208_manifest)
    v206 = load_json(args.v206_manifest)
    initial = classify(captures, probe, v208, v206, args.allow_non_v208_decision)
    should_probe = (
        initial["basic_control_ok"]
        and (args.allow_non_v208_decision or initial["v208_decision"] == V208_EXPECTED_DECISION)
        and initial["expected_major_minor"]
        and initial["ext4_available"]
    )

    if should_probe:
        run_sequence(store, args, probe, build_probe_commands(probe), captures)
        mounted_snapshot = classify(captures, probe, v208, v206, args.allow_non_v208_decision)
        if mounted_snapshot["mount_ok"] and mounted_snapshot["mounted_after_mount"]:
            run_sequence(store, args, probe, build_asset_commands(probe), captures)
        run_sequence(store, args, probe, build_cleanup_commands(probe), captures)
    elif initial["basic_control_ok"] and initial["expected_major_minor"]:
        run_sequence(store, args, probe, build_cleanup_commands(probe)[1:], captures)

    classification = classify(captures, probe, v208, v206, args.allow_non_v208_decision)
    manifest: dict[str, Any] = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": classification["decision"] in DECISIONS and classification["decision"] not in {"manual-review-required", "cleanup-failed"},
        "decision": classification["decision"],
        "reason": classification["reason"],
        "mode": "native-vendor-ro-noload-mount-probe",
        "probe": asdict(probe),
        "classification": classification,
        "captures": [asdict(item) for item in captures],
        "v208_native": {
            "path": str(args.v208_manifest),
            "present": v208 is not None,
            "decision": (v208.get("decision") or v208.get("classification", {}).get("decision")) if v208 else None,
        },
        "v206_android": {
            "path": str(args.v206_manifest),
            "present": v206 is not None,
            "decision": (v206.get("decision") or v206.get("classification", {}).get("decision")) if v206 else None,
        },
        "guardrails": [
            "no plain mountfs ext4 ro",
            "mount requires ro,noload",
            "temporary node and mountpoint only under /tmp/a90-v209-*",
            "cleanup umount attempted for any mount attempt",
            "no Wi-Fi enablement",
            "no rfkill write",
            "no WLAN link-up",
            "no scan/connect",
            "no module load/unload",
            "no firmware path write",
            "no cnss-daemon/wificond/HAL/supplicant/hostapd start",
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
