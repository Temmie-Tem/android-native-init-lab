#!/usr/bin/env python3
"""V1919 modem RFS .jsn gate classifier.

This collector is intentionally read-only:

* host-only reparse of retained normal-Android tftp/rmtfs captures;
* temporary native sda29 vendor snapshot via ext4 ro,noload;
* one of the requested modem-jsn labels.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


CYCLE = "V1919"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1919-modem-jsn-rfs-gate")
DEFAULT_REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1919_MODEM_JSN_RFS_GATE_2026-06-03.md")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
PROBE_PREFIX = "/tmp/a90-v1919-"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
TOYBOX = "/cache/bin/toybox"
REPO_ROOT = repo_path(".")

ANDROID_ROOT_PATTERNS = (
    "tmp/wifi/v1753-android-good-wlan-pd-firmware-request",
    "tmp/wifi/v1897-android-normal-pm-msg22-edge-handoff*",
    "tmp/wifi/v1897-live*-v1888-*",
    "tmp/wifi/v1897-live*-v1894-*",
    "tmp/wifi/v1899-android-cnss-qrtr-stateup*",
    "tmp/wifi/v1909-android-servloc-domain-handoff*",
)

TEXT_SUFFIXES = {
    ".txt",
    ".log",
    ".json",
    ".md",
}

TRACE_NAME_RE = re.compile(
    r"(?i)(tftp_server|tqftp|rmt_storage|rmtfs|logcat-filtered|request-lines|request-summary)"
)
JSN_RE = re.compile(
    r"(?i)(modemuw\.jsn|(?:^|[\s\[\"'=:])(?:/?[A-Za-z0-9_.@+-]+/)*[A-Za-z0-9_.@+-]+\.jsn\b|rfs config)"
)
MODEMUW_RE = re.compile(r"(?i)modemuw\.jsn")
WLANMDSP_RE = re.compile(r"(?i)wlanmdsp\.mbn")
TFTP_PATH_RE = re.compile(r"(?i)(/vendor/rfs/msm/mpss/[^\]\s\"']+|readonly/vendor/[^\]\s\"']+)")
SECRET_RE = re.compile(r"t[e]mmie[0-9A-Za-z_@.-]*")

LABEL_ANDROID_NO_JSN = "android-modem-no-jsn-read"
LABEL_ANDROID_NATIVE_MISSING = "modem-jsn-served-android-absent-native"
LABEL_PRESENT_NOT_REQUESTED = "modem-jsn-present-but-not-requested"


@dataclass(frozen=True)
class ProbePaths:
    run_id: str
    base: str
    node: str
    mountpoint: str


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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--skip-native-snapshot", action="store_true")
    parser.set_defaults(hide_on_busy=True)
    return parser.parse_args(argv)


def redact(text: str) -> str:
    text = SECRET_RE.sub("[REDACTED]", text)
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?i)(serialno|androidboot\.serialno|androidboot\.ap_serial|ro\.serialno)=([^\s]+)", r"\1=<redacted>", text)
    return text


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def relpath(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def make_run_id(value: str = "") -> str:
    run_id = value or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not re.fullmatch(r"[A-Za-z0-9_.+-]{1,64}", run_id):
        raise RuntimeError(f"unsafe run id: {run_id!r}")
    return run_id


def make_probe_paths(run_id: str) -> ProbePaths:
    base = f"{PROBE_PREFIX}{run_id}"
    return ProbePaths(run_id=run_id, base=base, node=f"{base}/sda29", mountpoint=f"{base}/vendor")


def is_under_probe_path(path: str, probe: ProbePaths) -> bool:
    return path == probe.base or path.startswith(probe.base + "/")


def parse_major_minor(text: str) -> tuple[str, str] | None:
    match = re.search(r"\b(\d+):(\d+)\b", strip_cmdv1_text(text))
    if not match:
        return None
    return match.group(1), match.group(2)


def command_is_readonly(command: list[str], probe: ProbePaths, major_minor: tuple[str, str] | None = None) -> bool:
    if not command:
        return False
    if command[0] in {"version", "status", "selftest", "bootstatus", "cat", "ls", "stat", "umount"}:
        if command[0] == "umount":
            return command == ["umount", probe.mountpoint]
        if command[0] in {"ls", "stat"} and len(command) >= 2:
            return command[1].startswith("/sys/") or command[1].startswith("/proc/") or is_under_probe_path(command[1], probe)
        if command[0] == "cat" and len(command) >= 2:
            return command[1].startswith("/sys/") or command[1].startswith("/proc/")
        return True
    if command[0] == "mkdir":
        return len(command) == 2 and is_under_probe_path(command[1], probe)
    if command[0] == "mknodb":
        return major_minor is not None and command == ["mknodb", probe.node, major_minor[0], major_minor[1]]
    if command[:2] == ["run", TOYBOX]:
        if len(command) >= 3 and command[2] == "mount":
            expected = ["run", TOYBOX, "mount", "-t", "ext4", "-o", "ro,noload", probe.node, probe.mountpoint]
            return command == expected
        if len(command) >= 4 and command[2] == "find":
            return is_under_probe_path(command[3], probe)
    return False


def validate_command(command: list[str], probe: ProbePaths, major_minor: tuple[str, str] | None = None) -> None:
    joined = " ".join(command)
    forbidden = (
        "/dev/subsys_esoc0",
        "subsys_esoc0",
        "pcie",
        "mhi",
        "gdsc",
        "pmic",
        "gpio",
        "regulator",
        "wpa_supplicant",
        "wificond",
        "android.hardware.wifi",
        "scan",
        "connect",
        "dhcp",
        "ping",
        "mountfs",
        "remount",
        "rw",
    )
    if any(token in joined.lower() for token in forbidden):
        raise RuntimeError(f"forbidden command fragment in {joined!r}")
    if not command_is_readonly(command, probe, major_minor):
        raise RuntimeError(f"unexpected non-whitelisted command: {joined}")


def capture_device(
    store: EvidenceStore,
    args: argparse.Namespace,
    probe: ProbePaths,
    name: str,
    command: list[str],
    timeout: float,
    major_minor: tuple[str, str] | None = None,
) -> CaptureRecord:
    validate_command(command, probe, major_minor)
    capture = run_capture(args, name, command, timeout=timeout)
    body = capture.text if capture.text else f"{capture.error}\\n"
    body = redact(body)
    path = store.write_text(f"native/commands/{safe_name(name)}.txt", body.rstrip() + "\n")
    data = capture_to_manifest(capture)
    return CaptureRecord(
        name=name,
        command=" ".join(command),
        ok=bool(data["ok"]),
        rc=data.get("rc"),
        status=str(data.get("status", "missing")),
        duration_sec=float(data["duration_sec"]),
        file=str(path.relative_to(store.run_dir)),
        text=redact(data.get("text", "")),
        error=redact(str(data.get("error", ""))),
    )


def expand_android_roots() -> list[Path]:
    roots: list[Path] = []
    for pattern in ANDROID_ROOT_PATTERNS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if path.is_dir() and path not in roots:
                roots.append(path)
    return roots


def should_scan_file(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    relative = str(path)
    return bool(TRACE_NAME_RE.search(path.name) or TRACE_NAME_RE.search(relative))


def read_text(path: Path) -> str:
    data = path.read_bytes()
    if b"\0" in data[:4096]:
        return data.decode("utf-8", errors="replace").replace("\0", "\\n")
    return data.decode("utf-8", errors="replace")


def line_hits(regex: re.Pattern[str], lines: list[str]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        if regex.search(line):
            hits.append({"line": index, "text": redact(line.strip())[:600]})
    return hits


def extract_tftp_paths(lines: list[str]) -> list[str]:
    paths: list[str] = []
    for line in lines:
        for match in TFTP_PATH_RE.finditer(line):
            path = match.group(1).rstrip(".,;:")
            if path not in paths:
                paths.append(path)
    return paths


def scan_android_captures() -> dict[str, Any]:
    roots = expand_android_roots()
    files: list[dict[str, Any]] = []
    total_pre_jsn = 0
    total_all_jsn = 0
    total_pre_modemuw = 0
    total_wlanmdsp = 0
    first_wlanmdsp: dict[str, Any] | None = None
    served_paths: list[str] = []

    for root in roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or not should_scan_file(path):
                continue
            try:
                text = read_text(path)
            except OSError as exc:
                files.append({"path": relpath(path), "error": str(exc)})
                continue
            lines = text.splitlines()
            wlan_hits = line_hits(WLANMDSP_RE, lines)
            first_wlan_line = int(wlan_hits[0]["line"]) if wlan_hits else None
            pre_lines = lines[: first_wlan_line - 1] if first_wlan_line else lines
            pre_jsn_hits = line_hits(JSN_RE, pre_lines)
            all_jsn_hits = line_hits(JSN_RE, lines)
            pre_modemuw_hits = line_hits(MODEMUW_RE, pre_lines)
            total_pre_jsn += len(pre_jsn_hits)
            total_all_jsn += len(all_jsn_hits)
            total_pre_modemuw += len(pre_modemuw_hits)
            total_wlanmdsp += len(wlan_hits)
            if wlan_hits and first_wlanmdsp is None:
                first_wlanmdsp = {"path": relpath(path), **wlan_hits[0]}
            for candidate in extract_tftp_paths(lines):
                if candidate not in served_paths:
                    served_paths.append(candidate)
            if pre_jsn_hits or all_jsn_hits or wlan_hits or "tftp_server.strace" in path.name or "rmt_storage.strace" in path.name:
                files.append(
                    {
                        "path": relpath(path),
                        "root": relpath(root),
                        "line_count": len(lines),
                        "first_wlanmdsp_line": first_wlan_line,
                        "wlanmdsp_count": len(wlan_hits),
                        "pre_wlanmdsp_jsn_count": len(pre_jsn_hits),
                        "all_jsn_count": len(all_jsn_hits),
                        "pre_wlanmdsp_modemuw_count": len(pre_modemuw_hits),
                        "pre_wlanmdsp_jsn_hits": pre_jsn_hits[:20],
                        "all_jsn_hits": all_jsn_hits[:20],
                        "wlanmdsp_hits": wlan_hits[:8],
                    }
                )

    return {
        "roots": [relpath(path) for path in roots],
        "root_count": len(roots),
        "scanned_file_count": len(files),
        "pre_wlanmdsp_jsn_count": total_pre_jsn,
        "all_jsn_count": total_all_jsn,
        "pre_wlanmdsp_modemuw_count": total_pre_modemuw,
        "wlanmdsp_count": total_wlanmdsp,
        "first_wlanmdsp": first_wlanmdsp,
        "served_path_sample": served_paths[:80],
        "served_path_count": len(served_paths),
        "files": files,
    }


def capture_text(captures: list[CaptureRecord], name: str) -> str:
    for capture in captures:
        if capture.name == name:
            return strip_cmdv1_text(capture.text)
    return ""


def capture_ok(captures: list[CaptureRecord], name: str) -> bool:
    for capture in captures:
        if capture.name == name:
            return capture.ok
    return False


def capture_by_name(captures: list[CaptureRecord], name: str) -> CaptureRecord | None:
    for capture in captures:
        if capture.name == name:
            return capture
    return None


def result_lines(capture: CaptureRecord | None) -> list[str]:
    if capture is None:
        return []
    lines: list[str] = []
    for raw_line in strip_cmdv1_text(capture.text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(("a90:/#", "A90P1 ", "run: ", "[exit", "[done]", "[err]")):
            continue
        if line.startswith("stat: ") and "No such file or directory" in line:
            continue
        lines.append(line)
    return lines


def find_output_paths(captures: list[CaptureRecord], name: str, probe: ProbePaths, suffix_re: re.Pattern[str]) -> list[str]:
    paths: list[str] = []
    for line in result_lines(capture_by_name(captures, name)):
        if line.startswith(probe.mountpoint + "/") and suffix_re.search(line):
            paths.append(line)
    return sorted(set(paths))


def successful_stat_paths(captures: list[CaptureRecord], names_to_paths: dict[str, str]) -> list[str]:
    paths: list[str] = []
    for name, path in names_to_paths.items():
        if capture_ok(captures, name):
            paths.append(path)
    return sorted(set(paths))


def mountpoint_leftover(text: str, probe: ProbePaths) -> bool:
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == probe.mountpoint:
            return True
    return False


def native_snapshot(store: EvidenceStore, args: argparse.Namespace, probe: ProbePaths) -> dict[str, Any]:
    captures: list[CaptureRecord] = []
    basic_commands: tuple[tuple[str, list[str], float], ...] = (
        ("version", ["version"], 15.0),
        ("status", ["status"], 25.0),
        ("selftest", ["selftest"], 25.0),
        ("pre-proc-mounts", ["cat", "/proc/mounts"], 20.0),
        ("proc-filesystems", ["cat", "/proc/filesystems"], 20.0),
        ("sys-sda29-dev", ["cat", "/sys/class/block/sda29/dev"], 20.0),
        ("sys-sda29-ro", ["cat", "/sys/class/block/sda29/ro"], 20.0),
    )
    for name, command, timeout in basic_commands:
        captures.append(capture_device(store, args, probe, name, command, timeout))

    major_minor = parse_major_minor(capture_text(captures, "sys-sda29-dev"))
    mounted = False
    if capture_ok(captures, "version") and major_minor and "ext4" in capture_text(captures, "proc-filesystems").split():
        setup_commands: tuple[tuple[str, list[str], float], ...] = (
            ("mkdir-base", ["mkdir", probe.base], 20.0),
            ("mkdir-mountpoint", ["mkdir", probe.mountpoint], 20.0),
            ("mknodb-sda29", ["mknodb", probe.node, major_minor[0], major_minor[1]], 20.0),
            ("temp-node-stat", ["stat", probe.node], 20.0),
            ("safe-ro-noload-mount", ["run", TOYBOX, "mount", "-t", "ext4", "-o", "ro,noload", probe.node, probe.mountpoint], 45.0),
            ("mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0),
        )
        for name, command, timeout in setup_commands:
            captures.append(capture_device(store, args, probe, name, command, timeout, major_minor=major_minor))
        mounted = capture_ok(captures, "safe-ro-noload-mount") and mountpoint_leftover(capture_text(captures, "mounted-proc-mounts"), probe)

    if mounted:
        rfs = f"{probe.mountpoint}/rfs"
        mpss = f"{probe.mountpoint}/rfs/msm/mpss"
        asset_commands: tuple[tuple[str, list[str], float], ...] = (
            ("mounted-root-ls", ["ls", probe.mountpoint], 20.0),
            ("mounted-rfs-stat", ["stat", rfs], 20.0),
            ("mounted-rfs-msm-mpss-stat", ["stat", mpss], 20.0),
            ("find-jsn", ["run", TOYBOX, "find", probe.mountpoint, "-name", "*.jsn"], 45.0),
            ("find-wlanmdsp", ["run", TOYBOX, "find", probe.mountpoint, "-name", "wlanmdsp.mbn"], 45.0),
            ("find-rfs-shallow", ["run", TOYBOX, "find", rfs, "-maxdepth", "5"], 45.0),
            ("find-mpss-shallow", ["run", TOYBOX, "find", mpss, "-maxdepth", "10"], 45.0),
            ("stat-mpss-fw-wlanmdsp", ["stat", f"{mpss}/readonly/vendor/firmware/wlanmdsp.mbn"], 20.0),
            ("stat-mpss-fwmnt-wlanmdsp", ["stat", f"{mpss}/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn"], 20.0),
            ("stat-mpss-fw-modemuw-jsn", ["stat", f"{mpss}/readonly/vendor/firmware/modemuw.jsn"], 20.0),
            ("stat-mpss-fwmnt-modemuw-jsn", ["stat", f"{mpss}/readonly/vendor/firmware_mnt/image/modemuw.jsn"], 20.0),
        )
        for name, command, timeout in asset_commands:
            captures.append(capture_device(store, args, probe, name, command, timeout, major_minor=major_minor))

    if mounted:
        captures.append(capture_device(store, args, probe, "cleanup-umount", ["umount", probe.mountpoint], 25.0, major_minor=major_minor))
    captures.append(capture_device(store, args, probe, "post-proc-mounts", ["cat", "/proc/mounts"], 20.0, major_minor=major_minor))

    jsn_paths = find_output_paths(captures, "find-jsn", probe, re.compile(r"\.jsn$", re.IGNORECASE))
    stat_modemuw_paths = successful_stat_paths(
        captures,
        {
            "stat-mpss-fw-modemuw-jsn": f"{probe.mountpoint}/rfs/msm/mpss/readonly/vendor/firmware/modemuw.jsn",
            "stat-mpss-fwmnt-modemuw-jsn": f"{probe.mountpoint}/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/modemuw.jsn",
        },
    )
    jsn_paths = sorted(set(jsn_paths + stat_modemuw_paths))
    modemuw_paths = [path for path in jsn_paths if path.lower().endswith("/modemuw.jsn")]
    mpss_jsn_paths = [path for path in jsn_paths if "/rfs/msm/mpss/" in path]
    vendor_wlanmdsp_paths = find_output_paths(captures, "find-wlanmdsp", probe, re.compile(r"/wlanmdsp\.mbn$", re.IGNORECASE))
    stat_mpss_wlanmdsp_paths = successful_stat_paths(
        captures,
        {
            "stat-mpss-fw-wlanmdsp": f"{probe.mountpoint}/rfs/msm/mpss/readonly/vendor/firmware/wlanmdsp.mbn",
            "stat-mpss-fwmnt-wlanmdsp": f"{probe.mountpoint}/rfs/msm/mpss/readonly/vendor/firmware_mnt/image/wlanmdsp.mbn",
        },
    )
    vendor_wlanmdsp_paths = sorted(set(vendor_wlanmdsp_paths + stat_mpss_wlanmdsp_paths))
    served_wlanmdsp_paths = [path for path in vendor_wlanmdsp_paths if "/rfs/msm/mpss/" in path]
    post_mounts = capture_text(captures, "post-proc-mounts")
    cleanup_leftover = mountpoint_leftover(post_mounts, probe)

    return {
        "skipped": False,
        "probe": asdict(probe),
        "major_minor": ":".join(major_minor) if major_minor else None,
        "ext4_available": "ext4" in capture_text(captures, "proc-filesystems").split(),
        "version_ok": capture_ok(captures, "version"),
        "status_ok": capture_ok(captures, "status"),
        "selftest_ok": capture_ok(captures, "selftest"),
        "mount_ok": capture_ok(captures, "safe-ro-noload-mount"),
        "mounted": mounted,
        "cleanup_leftover_mount": cleanup_leftover,
        "jsn_paths": jsn_paths,
        "jsn_count": len(jsn_paths),
        "modemuw_paths": modemuw_paths,
        "modemuw_count": len(modemuw_paths),
        "mpss_jsn_paths": mpss_jsn_paths,
        "mpss_jsn_count": len(mpss_jsn_paths),
        "vendor_wlanmdsp_paths": vendor_wlanmdsp_paths,
        "vendor_wlanmdsp_count": len(vendor_wlanmdsp_paths),
        "served_wlanmdsp_paths": served_wlanmdsp_paths,
        "served_wlanmdsp_count": len(served_wlanmdsp_paths),
        "captures": [asdict(capture) for capture in captures],
    }


def classify(android: dict[str, Any], native: dict[str, Any]) -> dict[str, Any]:
    if android["pre_wlanmdsp_jsn_count"] == 0:
        return {
            "label": LABEL_ANDROID_NO_JSN,
            "reason": "existing normal-Android tftp/rmtfs captures request wlanmdsp.mbn with zero pre-wlanmdsp .jsn/modemuw.jsn hits",
            "pass": not native.get("cleanup_leftover_mount", False),
        }
    native_has_relevant_jsn = bool(native.get("modemuw_count") or native.get("mpss_jsn_count"))
    if not native_has_relevant_jsn:
        return {
            "label": LABEL_ANDROID_NATIVE_MISSING,
            "reason": "Android pre-wlanmdsp .jsn reads exist, but native sda29 RFS snapshot lacks modemuw/.jsn under the served MPSS tree",
            "pass": not native.get("cleanup_leftover_mount", False),
        }
    return {
        "label": LABEL_PRESENT_NOT_REQUESTED,
        "reason": "Android pre-wlanmdsp .jsn reads exist and native has MPSS .jsn content, so the retained requested_wlanmdsp=0 symptom is not an absent-file gate",
        "pass": not native.get("cleanup_leftover_mount", False),
    }


def build_summary(manifest: dict[str, Any]) -> str:
    android = manifest["android"]
    native = manifest["native"]
    c = manifest["classification"]
    rows = [
        ["label", c["label"], c["reason"]],
        ["android_roots", android["root_count"], ", ".join(android["roots"][:6])],
        ["android_wlanmdsp", android["wlanmdsp_count"], str(android["first_wlanmdsp"])],
        ["android_pre_jsn", android["pre_wlanmdsp_jsn_count"], f"modemuw={android['pre_wlanmdsp_modemuw_count']} all_jsn={android['all_jsn_count']}"],
        ["native_mount", native.get("mount_ok"), f"mounted={native.get('mounted')} leftover={native.get('cleanup_leftover_mount')}"],
        ["native_jsn", native.get("jsn_count"), f"modemuw={native.get('modemuw_count')} mpss_jsn={native.get('mpss_jsn_count')}"],
        ["native_wlanmdsp", native.get("served_wlanmdsp_count"), f"rfs_mpss={native.get('served_wlanmdsp_count')} vendor_snapshot={native.get('vendor_wlanmdsp_count')}"],
    ]
    lines = [
        "# Native Init V1919 Modem JSN/RFS Gate\n\n",
        "## Summary\n\n",
        f"- Cycle: `{CYCLE}`\n",
        f"- Label: `{c['label']}`\n",
        f"- Pass: `{manifest['pass']}`\n",
        f"- Reason: {c['reason']}\n",
        f"- Evidence: `{manifest['out_dir']}`\n\n",
        "## Matrix\n\n",
        markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in rows]),
        "\n\n## Android Host Reparse\n\n",
        f"- Roots scanned: `{android['root_count']}`\n",
        f"- Trace-like files retained in manifest: `{android['scanned_file_count']}`\n",
        f"- `wlanmdsp.mbn` hits: `{android['wlanmdsp_count']}`\n",
        f"- Pre-`wlanmdsp.mbn` `.jsn` hits: `{android['pre_wlanmdsp_jsn_count']}`\n",
        f"- Pre-`wlanmdsp.mbn` `modemuw.jsn` hits: `{android['pre_wlanmdsp_modemuw_count']}`\n",
        f"- All-window `.jsn` hits: `{android['all_jsn_count']}`\n",
        f"- First `wlanmdsp.mbn`: `{android['first_wlanmdsp']}`\n\n",
        "## Native Read-Only Served Set\n\n",
        f"- sda29 mount: `ro,noload`, mounted `{native.get('mounted')}`, cleanup leftover `{native.get('cleanup_leftover_mount')}`\n",
        f"- `.jsn` files under vendor snapshot: `{native.get('jsn_count')}`\n",
        f"- `modemuw.jsn` files: `{native.get('modemuw_count')}`\n",
        f"- MPSS `.jsn` files: `{native.get('mpss_jsn_count')}`\n",
        f"- RFS MPSS `wlanmdsp.mbn` served paths: `{native.get('served_wlanmdsp_count')}`\n",
        f"- Raw vendor snapshot `wlanmdsp.mbn` files: `{native.get('vendor_wlanmdsp_count')}`\n\n",
        "## Native JSN Paths\n\n",
    ]
    jsn_paths = native.get("jsn_paths", [])
    if jsn_paths:
        lines.extend(f"- `{path}`\n" for path in jsn_paths[:120])
    else:
        lines.append("- none\n")
    lines.append("\n## Native Wlanmdsp Paths\n\n")
    wlanmdsp_paths = native.get("vendor_wlanmdsp_paths", [])
    if wlanmdsp_paths:
        lines.extend(f"- `{path}`\n" for path in wlanmdsp_paths[:120])
    else:
        lines.append("- none\n")
    lines.append("\n## Android Served Path Sample\n\n")
    served = android.get("served_path_sample", [])
    if served:
        lines.extend(f"- `{path}`\n" for path in served[:80])
    else:
        lines.append("- none\n")
    lines.extend(
        [
            "\n## Safety\n\n",
            "- Host-only Android reparse; no Android boot was started.\n",
            "- Native side used only temporary `/tmp/a90-v1919-*` node/mountpoint and `ext4 ro,noload` for `/dev/block/sda29` visibility.\n",
            "- No firmware/partition write, remount-write, `/dev/subsys_esoc0`, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCIe/MHI/eSoC, Wi-Fi HAL/scan/connect, credentials, DHCP/routes, or external ping action was requested.\n",
        ]
    )
    return "".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("host")
    store.mkdir("native", "commands")
    android = scan_android_captures()
    store.write_json("host/android-jsn-reparse.json", android)

    run_id = make_run_id(args.run_id)
    probe = make_probe_paths(run_id)
    if args.skip_native_snapshot:
        native: dict[str, Any] = {"skipped": True, "cleanup_leftover_mount": False}
    else:
        native = native_snapshot(store, args, probe)
    store.write_json("native/native-served-set.json", native)

    classification = classify(android, native)
    host_metadata = collect_host_metadata()
    host_metadata["repo"] = "."
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": str(args.out_dir),
        "pass": bool(classification["pass"]),
        "label": classification["label"],
        "reason": classification["reason"],
        "classification": classification,
        "android": android,
        "native": native,
        "host_metadata": host_metadata,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    report_path = repo_path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_summary(manifest), encoding="utf-8")
    print(
        f"{'PASS' if manifest['pass'] else 'FAIL'} "
        f"label={classification['label']} "
        f"android_pre_jsn={android['pre_wlanmdsp_jsn_count']} "
        f"native_jsn={native.get('jsn_count')} "
        f"out_dir={args.out_dir}"
    )
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
