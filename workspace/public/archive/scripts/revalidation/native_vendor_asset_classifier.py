#!/usr/bin/env python3
"""Classify native-visible vendor Wi-Fi/CNSS assets through a safe ro,noload mount."""

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


PROBE_PREFIX = "/tmp/a90-v210-"
EXPECTED_BLOCK = "sda29"
EXPECTED_MAJOR = "259"
EXPECTED_MINOR = "22"
V209_EXPECTED_DECISION = "vendor-assets-visible"

DECISIONS = {
    "asset-map-ready",
    "firmware-path-policy-needed",
    "service-dependency-gap",
    "vendor-assets-incomplete",
    "dependency-parser-unavailable",
    "cleanup-failed",
    "manual-review-required",
}

READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 15.0),
    ("status", ["status"], 25.0),
    ("bootstatus", ["bootstatus"], 25.0),
    ("pre-proc-mounts", ["cat", "/proc/mounts"], 20.0),
    ("proc-filesystems", ["cat", "/proc/filesystems"], 20.0),
    ("firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 20.0),
    ("sys-sda29-dev", ["cat", "/sys/class/block/sda29/dev"], 20.0),
    ("sys-sda29-size", ["cat", "/sys/class/block/sda29/size"], 20.0),
    ("sys-sda29-ro", ["cat", "/sys/class/block/sda29/ro"], 20.0),
    ("sys-dev-block-sda29", ["ls", "/sys/dev/block/259:22"], 20.0),
    ("dev-block-sda29-stat-before", ["stat", "/dev/block/sda29"], 20.0),
    ("tmp-root-before", ["ls", "/tmp"], 20.0),
)

FIRMWARE_PATHS = (
    "firmware",
    "firmware/wlan",
    "firmware/wlan/qca_cld",
    "firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini",
    "firmware/wlan/qca_cld/bdwlan.bin",
    "firmware/wlan/qca_cld/bdwlan.bin1",
    "firmware/wlan/qca_cld/bdwlan.bin1_old",
    "firmware/wlan/qca_cld/bdwlan.bin2",
    "firmware/wlan/qca_cld/bdwlan.bin2_old",
    "firmware/wlan/qca_cld/bdwlan.bin_old",
    "firmware/wlan/qca_cld/regdb.bin",
    "firmware/wlanmdsp.mbn",
    "firmware_mnt",
    "firmware_mnt/image",
    "firmware_mnt/image/WCNSS_qcom_cfg.ini",
    "firmware_mnt/image/bdwlan.bin",
    "firmware_mnt/image/regdb.bin",
    "bt_firmware",
    "firmware-modem",
)

INIT_RC_PATHS = (
    "etc/init",
    "etc/init/hw",
    "etc/init/hw/init.qcom.rc",
    "etc/init/hw/init.target.rc",
    "etc/init/android.hardware.wifi@1.0-service.rc",
    "etc/init/android.hardware.wifi.supplicant-service.rc",
    "etc/init/hostapd.android.rc",
    "etc/init/btcoex_cont_config.rc",
    "etc/init/vendor.samsung.hardware.wifi@2.0-service.rc",
    "etc/init/wifi_qcom.rc",
)

BINARY_PATHS = (
    "bin/cnss-daemon",
    "bin/cnss_diag",
    "bin/hw/android.hardware.wifi@1.0-service",
    "bin/hw/vendor.samsung.hardware.wifi@2.0-service",
    "bin/hw/wpa_supplicant",
    "bin/hw/hostapd",
    "bin/hostapd_cli",
    "bin/init.crda.sh",
    "bin/init.qcom.sdio.sh",
    "bin/wifi_ftmd",
)

LIBRARY_MODULE_PATHS = (
    "lib",
    "lib64",
    "lib/modules",
)

VINTF_PATHS = (
    "etc/vintf",
    "etc/vintf/manifest.xml",
    "etc/vintf/manifest",
    "etc/vintf/manifest/manifest.xml",
    "etc/vintf/manifest/android.hardware.wifi@1.0-service.xml",
    "etc/vintf/manifest/android.hardware.wifi.hostapd.xml",
    "etc/vintf/manifest/vendor.samsung.hardware.wifi@2.0-service.xml",
    "etc/vintf/manifest/vendor.samsung.hardware.wifi.hostapd.xml",
)

OTHER_PATHS = (
    "etc/wifi",
    "etc/hostapd",
)

STAT_PATHS = tuple(dict.fromkeys(FIRMWARE_PATHS + INIT_RC_PATHS + BINARY_PATHS + LIBRARY_MODULE_PATHS + VINTF_PATHS + OTHER_PATHS))

LIST_PATHS = {
    "bin",
    "bin/hw",
    "bt_firmware",
    "etc/hostapd",
    "etc/init",
    "etc/init/hw",
    "etc/vintf",
    "etc/vintf/manifest",
    "etc/wifi",
    "firmware",
    "firmware/wlan",
    "firmware/wlan/qca_cld",
    "firmware_mnt",
    "firmware_mnt/image",
    "firmware-modem",
    "lib/modules",
}

TEXT_FILE_PATHS = (
    "etc/init/hw/init.qcom.rc",
    "etc/init/hw/init.target.rc",
    "etc/init/android.hardware.wifi@1.0-service.rc",
    "etc/init/android.hardware.wifi.supplicant-service.rc",
    "etc/init/hostapd.android.rc",
    "etc/init/btcoex_cont_config.rc",
    "etc/init/vendor.samsung.hardware.wifi@2.0-service.rc",
    "etc/init/wifi_qcom.rc",
    "etc/vintf/manifest.xml",
    "etc/vintf/manifest/manifest.xml",
    "etc/vintf/manifest/android.hardware.wifi@1.0-service.xml",
    "etc/vintf/manifest/android.hardware.wifi.hostapd.xml",
    "etc/vintf/manifest/vendor.samsung.hardware.wifi@2.0-service.xml",
    "etc/vintf/manifest/vendor.samsung.hardware.wifi.hostapd.xml",
    "firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini",
)

FIND_ROOTS = (
    ("find-firmware", "firmware", "4"),
    ("find-init", "etc/init", "2"),
    ("find-vintf", "etc/vintf", "4"),
    ("find-bin-hw", "bin/hw", "2"),
    ("find-lib-modules", "lib/modules", "3"),
    ("find-etc-wifi", "etc/wifi", "2"),
)

REQUIRED_FIRMWARE = (
    "firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini",
    "firmware/wlan/qca_cld/bdwlan.bin",
    "firmware/wlan/qca_cld/regdb.bin",
    "firmware/wlanmdsp.mbn",
)

REQUIRED_INIT_RC = (
    "etc/init/hw/init.qcom.rc",
    "etc/init/hw/init.target.rc",
    "etc/init/android.hardware.wifi@1.0-service.rc",
    "etc/init/android.hardware.wifi.supplicant-service.rc",
    "etc/init/hostapd.android.rc",
    "etc/init/vendor.samsung.hardware.wifi@2.0-service.rc",
)

REQUIRED_BINARIES = (
    "bin/cnss-daemon",
    "bin/cnss_diag",
    "bin/hw/android.hardware.wifi@1.0-service",
    "bin/hw/vendor.samsung.hardware.wifi@2.0-service",
    "bin/hw/wpa_supplicant",
    "bin/hw/hostapd",
)

IMPORTANT_SERVICE_NAMES = (
    "cnss-daemon",
    "cnss_diag",
    "vendor.wifi_hal_legacy",
    "vendor.wifi_hal_ext",
    "wpa_supplicant",
    "hostapd",
)

ANDROID_PARITY_ITEMS = (
    ("cnss-daemon", "service", "bin/cnss-daemon"),
    ("cnss_diag", "service", "bin/cnss_diag"),
    ("vendor.wifi_hal_legacy", "service", "bin/hw/android.hardware.wifi@1.0-service"),
    ("vendor.wifi_hal_ext", "service", "bin/hw/vendor.samsung.hardware.wifi@2.0-service"),
    ("wpa_supplicant", "service", "bin/hw/wpa_supplicant"),
    ("hostapd", "service", "bin/hw/hostapd"),
    ("WCNSS_qcom_cfg.ini", "firmware", "firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini"),
    ("bdwlan.bin", "firmware", "firmware/wlan/qca_cld/bdwlan.bin"),
    ("regdb.bin", "firmware", "firmware/wlan/qca_cld/regdb.bin"),
    ("wlanmdsp.mbn", "firmware", "firmware/wlanmdsp.mbn"),
    ("android.hardware.wifi@1.0-service.rc", "init-rc", "etc/init/android.hardware.wifi@1.0-service.rc"),
    ("android.hardware.wifi.supplicant-service.rc", "init-rc", "etc/init/android.hardware.wifi.supplicant-service.rc"),
    ("hostapd.android.rc", "init-rc", "etc/init/hostapd.android.rc"),
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
    return REPO_ROOT / "tmp" / "wifi" / f"v210-vendor-asset-classifier-{stamp}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", "--bridge-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v209-manifest", type=Path, default=Path("tmp/wifi/v209-vendor-ro-mount-probe/manifest.json"))
    parser.add_argument("--v206-manifest", type=Path, default=Path("tmp/wifi/v206-android-icnss-cnss-map/manifest.json"))
    parser.add_argument("--run-id", default="", help="optional safe suffix for /tmp/a90-v210-<run-id>")
    parser.add_argument("--allow-non-v209-decision", action="store_true")
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
    return ProbePaths(run_id=run_id, base=base, node=f"{base}/{EXPECTED_BLOCK}", mountpoint=f"{base}/vendor")


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|serialno)=([^\s]+)", r"\1=<redacted>", text)
    return text


def is_under_probe_path(path: str, probe: ProbePaths) -> bool:
    return path == probe.base or path.startswith(probe.base + "/")


def is_under_mountpoint(path: str, probe: ProbePaths) -> bool:
    return path == probe.mountpoint or path.startswith(probe.mountpoint + "/")


def remote_path(probe: ProbePaths, rel_path: str) -> str:
    return f"{probe.mountpoint}/{rel_path}"


def allowed_global_read_path(path: str) -> bool:
    return (
        path in {"/proc/mounts", "/proc/filesystems", "/sys/module/firmware_class/parameters/path", "/tmp", "/dev/block/sda29"}
        or path.startswith("/sys/class/block/sda29/")
        or path == "/sys/dev/block/259:22"
    )


def validate_classifier_command(command: list[str], probe: ProbePaths) -> None:
    if not command:
        raise RuntimeError("empty classifier command")
    joined = " ".join(command)
    for pattern in ACTIVE_WIFI_PATTERNS + FORBIDDEN_STORAGE_PATTERNS:
        if pattern.search(joined):
            raise RuntimeError(f"forbidden command pattern {pattern.pattern!r}: {joined}")

    name = command[0]
    if name in {"version", "status", "bootstatus", "mounts"}:
        return
    if name in {"cat", "ls", "stat"}:
        if len(command) != 2:
            raise RuntimeError(f"unexpected {name} arity: {joined}")
        if allowed_global_read_path(command[1]) or is_under_probe_path(command[1], probe):
            return
        raise RuntimeError(f"{name} outside allowed read paths: {joined}")
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
            if len(command) < 4 or not is_under_mountpoint(command[3], probe):
                raise RuntimeError(f"find outside mounted vendor path: {joined}")
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
    ]
    for name, rel_path, maxdepth in FIND_ROOTS:
        commands.append((name, ["run", "/cache/bin/toybox", "find", remote_path(probe, rel_path), "-maxdepth", maxdepth], 45.0))
    for rel_path in STAT_PATHS:
        commands.append((f"asset-{safe_name(rel_path)}", ["stat", remote_path(probe, rel_path)], 20.0))
        if rel_path in LIST_PATHS:
            commands.append((f"list-{safe_name(rel_path)}", ["ls", remote_path(probe, rel_path)], 20.0))
    for rel_path in TEXT_FILE_PATHS:
        commands.append((f"cat-{safe_name(rel_path)}", ["cat", remote_path(probe, rel_path)], 25.0))
    return tuple(commands)


def build_cleanup_commands(probe: ProbePaths) -> tuple[tuple[str, list[str], float], ...]:
    return (
        ("cleanup-umount", ["umount", probe.mountpoint], 25.0),
        ("post-proc-mounts", ["cat", "/proc/mounts"], 20.0),
        ("tmp-base-after", ["ls", probe.base], 20.0),
    )


def validate_classifier_commands() -> None:
    probe = make_probe_paths("guard")
    for _, command, _ in READ_ONLY_COMMANDS + build_probe_commands(probe) + build_asset_commands(probe) + build_cleanup_commands(probe):
        validate_classifier_command(command, probe)


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
    validate_classifier_command(command, probe)
    capture = run_capture(args, name, command, timeout=timeout)
    body = capture.text if capture.text else f"{capture.error}\n"
    relative = write_capture(store, name, body)
    data = capture_to_manifest(capture)
    full_text = redact_text(body if capture.text else "")
    return CaptureRecord(
        name=name,
        command=" ".join(command),
        ok=bool(data["ok"]),
        rc=data.get("rc"),
        status=str(data.get("status", "missing")),
        duration_sec=float(data["duration_sec"]),
        file=relative,
        text=full_text,
        error=str(data.get("error", "")),
    )


def run_sequence(
    store: EvidenceStore,
    args: argparse.Namespace,
    probe: ProbePaths,
    sequence: tuple[tuple[str, list[str], float], ...],
    captures: list[CaptureRecord],
) -> None:
    for name, command, timeout in sequence:
        captures.append(capture_device(store, args, probe, name, command, timeout))


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


def capture_file_text(captures: list[CaptureRecord], rel_path: str) -> str:
    return capture_text(captures, f"cat-{safe_name(rel_path)}")


def path_visible(captures: list[CaptureRecord], probe: ProbePaths, rel_path: str) -> bool:
    stat_capture = capture_by_name(captures, f"asset-{safe_name(rel_path)}")
    if stat_capture is not None and stat_capture.ok:
        return True
    wanted = remote_path(probe, rel_path)
    for capture in captures:
        if not capture.ok or not capture.text:
            continue
        if wanted in strip_cmdv1_text(capture.text):
            return True
    return False


def visible_paths(captures: list[CaptureRecord], probe: ProbePaths) -> list[str]:
    return [path for path in STAT_PATHS if path_visible(captures, probe, path)]


def extract_android_vendor_paths(v206: dict[str, Any] | None) -> list[str]:
    if not v206:
        return []
    text = json.dumps(v206, ensure_ascii=False)
    paths = sorted(set(re.findall(r"/vendor/[A-Za-z0-9_./@+-]+", text)))
    interesting = []
    for path in paths:
        lower = path.lower()
        if any(token in lower for token in ("wifi", "wlan", "firmware", "cnss", "icnss", "qca", "hostapd", "supplicant", "init", "vintf")):
            interesting.append(path.rstrip(".,'\""))
    return interesting[:220]


def android_has_item(v206: dict[str, Any] | None, item: str) -> bool:
    if not v206:
        return False
    return item.lower() in json.dumps(v206, ensure_ascii=False).lower()


def parse_init_services(captures: list[CaptureRecord]) -> list[dict[str, Any]]:
    services: list[dict[str, Any]] = []
    for rel_path in TEXT_FILE_PATHS:
        if not rel_path.endswith(".rc"):
            continue
        text = capture_file_text(captures, rel_path)
        current: dict[str, Any] | None = None
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            service_match = re.match(r"^service\s+(\S+)\s+(\S+)(.*)$", stripped)
            if service_match:
                current = {
                    "source": rel_path,
                    "name": service_match.group(1),
                    "executable": service_match.group(2),
                    "args": service_match.group(3).strip(),
                    "class": [],
                    "user": None,
                    "group": [],
                    "capabilities": [],
                    "interfaces": [],
                    "flags": [],
                    "seclabel": None,
                    "interesting": False,
                }
                services.append(current)
                continue
            if raw_line and not raw_line[0].isspace():
                current = None
                continue
            if current is None:
                continue
            parts = stripped.split()
            if not parts:
                continue
            key = parts[0]
            values = parts[1:]
            if key == "class":
                current["class"].extend(values)
            elif key == "user" and values:
                current["user"] = values[0]
            elif key == "group":
                current["group"].extend(values)
            elif key == "capabilities":
                current["capabilities"].extend(values)
            elif key == "interface":
                current["interfaces"].append(" ".join(values))
            elif key in {"disabled", "oneshot", "critical"}:
                current["flags"].append(key)
            elif key == "seclabel" and values:
                current["seclabel"] = values[0]
        for item in services:
            interest_blob = " ".join(
                [
                    str(item["name"]),
                    str(item["executable"]),
                    str(item["args"]),
                    " ".join(item["class"]),
                    str(item["user"] or ""),
                    " ".join(item["group"]),
                    " ".join(item["capabilities"]),
                    " ".join(item["interfaces"]),
                    " ".join(item["flags"]),
                    str(item["seclabel"] or ""),
                ]
            ).lower()
            item["interesting"] = any(token in interest_blob for token in ("wifi", "wlan", "cnss", "hostapd", "supplicant"))
    return [item for item in services if item["interesting"]]


def extract_vintf_hits(captures: list[CaptureRecord], limit: int = 120) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for rel_path in TEXT_FILE_PATHS:
        if "vintf" not in rel_path:
            continue
        text = capture_file_text(captures, rel_path)
        for raw_line in text.splitlines():
            line = raw_line.strip()
            lower = line.lower()
            if any(token in lower for token in ("wifi", "wlan", "supplicant", "hostapd")):
                hits.append({"source": rel_path, "line": line})
                if len(hits) >= limit:
                    return hits
    return hits


def service_name_set(services: list[dict[str, Any]]) -> set[str]:
    return {str(item["name"]) for item in services}


def build_parity_matrix(captures: list[CaptureRecord], probe: ProbePaths, v206: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for android_item, category, native_rel_path in ANDROID_PARITY_ITEMS:
        visible = path_visible(captures, probe, native_rel_path)
        android_seen = android_has_item(v206, android_item) or android_has_item(v206, f"/vendor/{native_rel_path}")
        if visible:
            implication = "native-visible"
        elif android_seen:
            implication = "android-seen-native-missing"
        else:
            implication = "not-proven"
        rows.append(
            {
                "android_item": android_item,
                "category": category,
                "native_vendor_path": f"/vendor/{native_rel_path}",
                "visible": visible,
                "android_seen": android_seen,
                "implication": implication,
            }
        )
    return rows


def firmware_loader_analysis(captures: list[CaptureRecord], probe: ProbePaths) -> dict[str, Any]:
    raw_path = capture_text(captures, "firmware-class-path").strip()
    current_path = raw_path.splitlines()[0].strip() if raw_path.splitlines() else ""
    required_under_current: list[str] = []
    missing_under_current: list[str] = []
    for rel_path in REQUIRED_FIRMWARE:
        file_name = rel_path.rsplit("/", 1)[-1]
        if current_path.startswith("/vendor/"):
            current_rel = current_path.removeprefix("/vendor/").strip("/")
            candidate = f"{current_rel}/{file_name}" if current_rel else file_name
            visible = path_visible(captures, probe, candidate)
        elif current_path:
            visible = False
        else:
            visible = False
        if visible:
            required_under_current.append(rel_path)
        else:
            missing_under_current.append(rel_path)
    required_visible = [path for path in REQUIRED_FIRMWARE if path_visible(captures, probe, path)]
    policy_needed = bool(required_visible) and bool(missing_under_current)
    return {
        "firmware_class_path": current_path,
        "required_firmware_visible": required_visible,
        "required_firmware_missing": [path for path in REQUIRED_FIRMWARE if path not in required_visible],
        "required_under_current_loader_path": required_under_current,
        "missing_under_current_loader_path": missing_under_current,
        "policy_needed": policy_needed,
        "current_probe_mountpoint": probe.mountpoint,
        "reason": (
            "required firmware is visible under mounted vendor, but not under current firmware_class.path"
            if policy_needed
            else "current firmware_class.path appears compatible or required firmware is incomplete"
        ),
    }


def relevant_lines(text: str, probe: ProbePaths, limit: int = 220) -> list[str]:
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
        "hostapd",
        "supplicant",
        "sda29",
        probe.base,
        probe.mountpoint,
        "ro,noload",
        "norecovery",
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


def classify(
    captures: list[CaptureRecord],
    probe: ProbePaths,
    v209: dict[str, Any] | None,
    v206: dict[str, Any] | None,
    allow_non_v209_decision: bool,
) -> dict[str, Any]:
    basic_control_ok = capture_ok(captures, "version", "status")
    v209_decision = (v209.get("decision") or v209.get("classification", {}).get("decision")) if v209 else None
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
    visible = visible_paths(captures, probe)
    services = parse_init_services(captures)
    parsed_services = sorted(service_name_set(services))
    vintf_hits = extract_vintf_hits(captures)
    parity = build_parity_matrix(captures, probe, v206)
    firmware_loader = firmware_loader_analysis(captures, probe)
    missing_required_firmware = [path for path in REQUIRED_FIRMWARE if not path_visible(captures, probe, path)]
    missing_required_init_rc = [path for path in REQUIRED_INIT_RC if not path_visible(captures, probe, path)]
    missing_required_binaries = [path for path in REQUIRED_BINARIES if not path_visible(captures, probe, path)]
    service_gap_names = [name for name in IMPORTANT_SERVICE_NAMES if name not in parsed_services]
    library_module_visible = any(path_visible(captures, probe, path) for path in LIBRARY_MODULE_PATHS)
    dependency_parser = {
        "status": "not-run",
        "reason": "v210 keeps binary dependency inspection conservative; native helper availability not required for firmware path decision",
    }
    all_text = strip_all(captures)

    if not basic_control_ok:
        decision = "manual-review-required"
        reason = "native bridge/control commands did not return usable evidence"
    elif not allow_non_v209_decision and v209_decision != V209_EXPECTED_DECISION:
        decision = "manual-review-required"
        reason = f"v209 decision is {v209_decision!r}, expected {V209_EXPECTED_DECISION!r}"
    elif not expected_major_minor:
        decision = "manual-review-required"
        reason = "sda29 major/minor could not be confirmed as 259:22"
    elif not ext4_available:
        decision = "manual-review-required"
        reason = "ext4 is not listed in /proc/filesystems"
    elif mount_attempted and mount_capture is not None and not mount_ok and re.search(r"not found|no such file|invalid option|unknown option|bad option|usage", mount_capture.text + mount_capture.error, re.IGNORECASE):
        decision = "manual-review-required"
        reason = "safe ro,noload mount command path is unavailable or unsupported"
    elif leftover_mount:
        decision = "cleanup-failed"
        reason = "temporary vendor mount remained after cleanup"
    elif not mount_ok or not mounted_after_mount:
        decision = "manual-review-required"
        reason = "temporary vendor ro,noload mount did not produce a mounted filesystem"
    elif missing_required_firmware or missing_required_init_rc:
        decision = "vendor-assets-incomplete"
        reason = "required firmware or init rc assets are missing from the native-visible vendor mount"
    elif missing_required_binaries or service_gap_names or not library_module_visible:
        decision = "service-dependency-gap"
        reason = "firmware is visible, but service binaries, parsed service metadata, or library/module evidence are incomplete"
    elif firmware_loader["policy_needed"]:
        decision = "firmware-path-policy-needed"
        reason = "required firmware exists, but current firmware_class.path does not point at the visible vendor firmware layout"
    elif dependency_parser["status"] != "ok":
        decision = "dependency-parser-unavailable"
        reason = "asset map is visible, but binary dependency parser evidence is unavailable"
    else:
        decision = "asset-map-ready"
        reason = "firmware, init rc, service binaries, and loader path evidence are sufficient for read-only feasibility planning"

    return {
        "decision": decision,
        "reason": reason,
        "basic_control_ok": basic_control_ok,
        "v209_decision": v209_decision,
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
        "visible_paths": visible,
        "visible_count": len(visible),
        "missing_required_firmware": missing_required_firmware,
        "missing_required_init_rc": missing_required_init_rc,
        "missing_required_binaries": missing_required_binaries,
        "parsed_services": parsed_services,
        "service_blocks": services,
        "service_gap_names": service_gap_names,
        "vintf_hits": vintf_hits,
        "vintf_hit_count": len(vintf_hits),
        "library_module_visible": library_module_visible,
        "dependency_parser": dependency_parser,
        "firmware_loader": firmware_loader,
        "parity_matrix": parity,
        "android_vendor_path_sample": extract_android_vendor_paths(v206)[:60],
        "android_vendor_path_count": len(extract_android_vendor_paths(v206)),
        "mount_error_sample": ((mount_capture.text or mount_capture.error)[:1200] if mount_capture is not None and not mount_ok else ""),
        "evidence_lines": relevant_lines(all_text, probe),
    }


def build_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    loader = c["firmware_loader"]
    rows = [
        ["result", "PASS" if manifest["pass"] else "FAIL", c["reason"]],
        ["decision", c["decision"], "ro,noload only"],
        ["v209", str(c["v209_decision"]), ""],
        ["major_minor", str(c["major_minor"]), f"expected={c['expected_major_minor']}"],
        ["ext4", str(c["ext4_available"]), ""],
        ["mount", str(c["mount_ok"]), f"attempted={c['mount_attempted']} mounted={c['mounted_after_mount']}"],
        ["cleanup", str(not c["leftover_mount"]), f"attempted={c['cleanup_attempted']} rc={c['cleanup_rc']}"],
        ["visible_paths", str(c["visible_count"]), ""],
        ["required_firmware_missing", str(len(c["missing_required_firmware"])), ", ".join(c["missing_required_firmware"])],
        ["required_init_missing", str(len(c["missing_required_init_rc"])), ", ".join(c["missing_required_init_rc"])],
        ["required_binaries_missing", str(len(c["missing_required_binaries"])), ", ".join(c["missing_required_binaries"])],
        ["services", str(len(c["parsed_services"])), ", ".join(c["parsed_services"])],
        ["firmware_class.path", loader["firmware_class_path"] or "<empty>", f"policy_needed={loader['policy_needed']}"],
    ]
    parity_rows = [
        [
            item["android_item"],
            item["native_vendor_path"],
            str(item["visible"]),
            item["category"],
            item["implication"],
        ]
        for item in c["parity_matrix"]
    ]
    service_rows = [
        [
            item["name"],
            item["source"],
            item["executable"],
            " ".join(item["capabilities"]),
            " ".join(item["group"]),
            " ".join(item["flags"]),
        ]
        for item in c["service_blocks"][:40]
    ]
    lines = [
        "# v210 Vendor Wi-Fi/CNSS Asset Classifier\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{c['decision']}`\n",
        f"- reason: `{c['reason']}`\n\n",
        "## Summary Matrix\n\n",
        markdown_table(["area", "status", "detail"], rows),
        "\n\n## Android vs Native Parity\n\n",
        markdown_table(["android item", "native vendor path", "visible", "category", "next implication"], parity_rows),
        "\n\n## Parsed Service Blocks\n\n",
    ]
    if service_rows:
        lines.append(markdown_table(["service", "source", "exec", "capabilities", "groups", "flags"], service_rows))
        lines.append("\n")
    else:
        lines.append("- none\n")
    lines.append("\n## Firmware Loader Implication\n\n")
    lines.extend(
        [
            f"- firmware_class.path: `{loader['firmware_class_path'] or '<empty>'}`\n",
            f"- policy_needed: `{loader['policy_needed']}`\n",
            f"- visible required firmware: `{len(loader['required_firmware_visible'])}`\n",
            f"- missing under current loader path: `{len(loader['missing_under_current_loader_path'])}`\n",
            f"- reason: {loader['reason']}\n",
        ]
    )
    lines.append("\n## VINTF Hits\n\n")
    if c["vintf_hits"]:
        for item in c["vintf_hits"][:80]:
            lines.append(f"- `{item['source']}`: `{item['line']}`\n")
    else:
        lines.append("- none\n")
    lines.append("\n## Visible Paths\n\n")
    if c["visible_paths"]:
        lines.extend(f"- `{path}`\n" for path in c["visible_paths"])
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


def main() -> int:
    args = parse_args()
    validate_classifier_commands()
    run_id = make_run_id(args.run_id)
    probe = make_probe_paths(run_id)
    store = EvidenceStore(args.out_dir)
    store.mkdir("native", "commands")
    captures: list[CaptureRecord] = []

    for name, command, timeout in READ_ONLY_COMMANDS:
        captures.append(capture_device(store, args, probe, name, command, timeout))

    v209 = load_json(args.v209_manifest)
    v206 = load_json(args.v206_manifest)
    initial = classify(captures, probe, v209, v206, args.allow_non_v209_decision)
    should_probe = (
        initial["basic_control_ok"]
        and (args.allow_non_v209_decision or initial["v209_decision"] == V209_EXPECTED_DECISION)
        and initial["expected_major_minor"]
        and initial["ext4_available"]
    )

    if should_probe:
        run_sequence(store, args, probe, build_probe_commands(probe), captures)
        mounted_snapshot = classify(captures, probe, v209, v206, args.allow_non_v209_decision)
        if mounted_snapshot["mount_ok"] and mounted_snapshot["mounted_after_mount"]:
            run_sequence(store, args, probe, build_asset_commands(probe), captures)
        run_sequence(store, args, probe, build_cleanup_commands(probe), captures)
    elif initial["basic_control_ok"] and initial["expected_major_minor"]:
        run_sequence(store, args, probe, build_cleanup_commands(probe)[1:], captures)

    classification = classify(captures, probe, v209, v206, args.allow_non_v209_decision)
    manifest: dict[str, Any] = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": classification["decision"] in DECISIONS and classification["decision"] not in {"manual-review-required", "cleanup-failed"},
        "decision": classification["decision"],
        "reason": classification["reason"],
        "mode": "native-vendor-wifi-cnss-asset-classifier",
        "probe": asdict(probe),
        "classification": classification,
        "captures": [asdict(item) for item in captures],
        "v209_native": {
            "path": str(args.v209_manifest),
            "present": v209 is not None,
            "decision": (v209.get("decision") or v209.get("classification", {}).get("decision")) if v209 else None,
        },
        "v206_android": {
            "path": str(args.v206_manifest),
            "present": v206 is not None,
            "decision": (v206.get("decision") or v206.get("classification", {}).get("decision")) if v206 else None,
        },
        "guardrails": [
            "no plain mountfs ext4 ro",
            "mount requires ro,noload",
            "temporary node and mountpoint only under /tmp/a90-v210-*",
            "cleanup umount attempted for any mount attempt",
            "no Wi-Fi enablement",
            "no rfkill write",
            "no WLAN link-up",
            "no scan/connect",
            "no module load/unload",
            "no firmware path write",
            "no cnss-daemon/cnss_diag/wificond/HAL/supplicant/hostapd start",
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
