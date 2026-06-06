#!/usr/bin/env python3
"""Model native firmware path policy for A90 Wi-Fi/CNSS without enabling Wi-Fi."""

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


PROBE_PREFIX = "/tmp/a90-v211-"
EXPECTED_BLOCK = "sda29"
EXPECTED_MAJOR = "259"
EXPECTED_MINOR = "22"
V209_EXPECTED_DECISION = "vendor-assets-visible"
V210_EXPECTED_DECISION = "firmware-path-policy-needed"
DEFAULT_V209_MANIFEST = Path("tmp/wifi/v209-vendor-ro-mount-probe/manifest.json")
DEFAULT_V210_MANIFEST = Path("tmp/wifi/v210-vendor-asset-classifier/manifest.json")

DECISIONS = {
    "path-policy-ready",
    "request-name-unknown",
    "bind-layout-needed",
    "sysfs-path-update-needed",
    "vendor-layout-risk-too-high",
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
    ("tmp-root-before", ["ls", "/tmp"], 20.0),
)

REQUIRED_VENDOR_FIRMWARE = (
    "firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini",
    "firmware/wlan/qca_cld/bdwlan.bin",
    "firmware/wlan/qca_cld/regdb.bin",
    "firmware/wlanmdsp.mbn",
)

LIKELY_REQUEST_NAMES = (
    "wlan/qca_cld/WCNSS_qcom_cfg.ini",
    "wlan/qca_cld/bdwlan.bin",
    "wlan/qca_cld/regdb.bin",
    "wlanmdsp.mbn",
)

UNCERTAIN_REQUEST_NAMES = (
    "WCNSS_qcom_cfg.ini",
    "bdwlan.bin",
    "regdb.bin",
)

REQUEST_NAMES = LIKELY_REQUEST_NAMES + UNCERTAIN_REQUEST_NAMES

FIRMWARE_ROOT_DIRS = (
    "firmware",
    "firmware/wlan",
    "firmware/wlan/qca_cld",
    "firmware_mnt",
    "firmware_mnt/image",
)

FIND_ROOTS = (
    ("find-firmware", "firmware", "4"),
    ("find-firmware-mnt", "firmware_mnt", "4"),
)

ACTIVE_WIFI_PATTERNS = (
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r"\b(?:cnss-daemon|cnss_diag|wificond|hostapd|wpa_supplicant)\b", re.IGNORECASE),
)

FORBIDDEN_STORAGE_PATTERNS = (
    re.compile(r"\bmountfs\b", re.IGNORECASE),
    re.compile(r"\bmount\b.*\s--bind\b", re.IGNORECASE),
    re.compile(r"\bmount\b.*\s-o\s+bind\b", re.IGNORECASE),
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


@dataclass(frozen=True)
class PolicyCandidate:
    candidate_id: str
    description: str
    simulated_root: str
    future_runtime_path: str
    mutation_required: str
    status: str = "candidate"


def default_out_dir() -> Path:
    return REPO_ROOT / "tmp" / "wifi" / "v211-firmware-path-policy"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", "--bridge-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v209-manifest", type=Path, default=DEFAULT_V209_MANIFEST)
    parser.add_argument("--v210-manifest", type=Path, default=DEFAULT_V210_MANIFEST)
    parser.add_argument("--run-id", default="", help="optional safe suffix for /tmp/a90-v211-<run-id>")
    parser.add_argument("--allow-non-v209-decision", action="store_true")
    parser.add_argument("--allow-non-v210-decision", action="store_true")
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


def remote_path(probe: ProbePaths, rel_path: str) -> str:
    return f"{probe.mountpoint}/{rel_path.strip('/')}"


def rel_from_root(root_rel: str, request_name: str) -> str:
    root = root_rel.strip("/")
    request = request_name.strip("/")
    return f"{root}/{request}" if root else request


def is_under_probe_path(path: str, probe: ProbePaths) -> bool:
    return path == probe.base or path.startswith(probe.base + "/")


def is_under_mountpoint(path: str, probe: ProbePaths) -> bool:
    return path == probe.mountpoint or path.startswith(probe.mountpoint + "/")


def allowed_global_read_path(path: str) -> bool:
    return (
        path in {"/proc/mounts", "/proc/filesystems", "/sys/module/firmware_class/parameters/path", "/tmp"}
        or path.startswith("/sys/class/block/sda29/")
        or path == "/sys/dev/block/259:22"
    )


def validate_policy_command(command: list[str], probe: ProbePaths) -> None:
    if not command:
        raise RuntimeError("empty policy command")
    joined = " ".join(command)
    for pattern in ACTIVE_WIFI_PATTERNS + FORBIDDEN_STORAGE_PATTERNS:
        if pattern.search(joined):
            raise RuntimeError(f"forbidden command pattern {pattern.pattern!r}: {joined}")

    name = command[0]
    if name in {"version", "status", "bootstatus"}:
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
        if len(command) >= 3 and command[1] == "/cache/bin/toybox" and command[2] == "find":
            if len(command) < 4 or not is_under_mountpoint(command[3], probe):
                raise RuntimeError(f"find outside mounted vendor path: {joined}")
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


def candidate_rel_paths() -> tuple[str, ...]:
    paths: list[str] = []
    paths.extend(FIRMWARE_ROOT_DIRS)
    paths.extend(REQUIRED_VENDOR_FIRMWARE)
    for request in REQUEST_NAMES:
        paths.append(rel_from_root("firmware", request))
        paths.append(rel_from_root("firmware_mnt/image", request))
    return tuple(dict.fromkeys(path for path in paths if path))


def build_asset_commands(probe: ProbePaths) -> tuple[tuple[str, list[str], float], ...]:
    commands: list[tuple[str, list[str], float]] = [
        ("mounted-root", ["ls", probe.mountpoint], 20.0),
    ]
    for name, rel_path, maxdepth in FIND_ROOTS:
        commands.append((name, ["run", "/cache/bin/toybox", "find", remote_path(probe, rel_path), "-maxdepth", maxdepth], 45.0))
    for rel_path in candidate_rel_paths():
        commands.append((f"asset-{safe_name(rel_path)}", ["stat", remote_path(probe, rel_path)], 20.0))
        if rel_path in FIRMWARE_ROOT_DIRS:
            commands.append((f"list-{safe_name(rel_path)}", ["ls", remote_path(probe, rel_path)], 20.0))
    return tuple(commands)


def build_cleanup_commands(probe: ProbePaths) -> tuple[tuple[str, list[str], float], ...]:
    return (
        ("cleanup-umount", ["umount", probe.mountpoint], 25.0),
        ("post-proc-mounts", ["cat", "/proc/mounts"], 20.0),
        ("post-firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 20.0),
        ("tmp-base-after", ["ls", probe.base], 20.0),
    )


def validate_policy_commands() -> None:
    probe = make_probe_paths("guard")
    for _, command, _ in READ_ONLY_COMMANDS + build_probe_commands(probe) + build_asset_commands(probe) + build_cleanup_commands(probe):
        validate_policy_command(command, probe)


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
    validate_policy_command(command, probe)
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


def path_visible(captures: list[CaptureRecord], rel_path: str) -> bool:
    stat_capture = capture_by_name(captures, f"asset-{safe_name(rel_path)}")
    return stat_capture is not None and stat_capture.ok


def visible_paths(captures: list[CaptureRecord]) -> list[str]:
    return [path for path in candidate_rel_paths() if path_visible(captures, path)]


def firmware_class_path(captures: list[CaptureRecord], name: str = "firmware-class-path") -> str:
    raw_path = capture_text(captures, name).strip()
    return raw_path.splitlines()[0].strip() if raw_path.splitlines() else ""


def current_vendor_relative_root(current_path: str) -> str:
    if current_path.startswith("/vendor/"):
        return current_path.removeprefix("/vendor/").strip("/")
    return ""


def build_candidates(probe: ProbePaths, current_path: str) -> list[PolicyCandidate]:
    current_rel = current_vendor_relative_root(current_path)
    return [
        PolicyCandidate(
            candidate_id="current-firmware-class-path",
            description="keep current firmware_class.path and check the vendor-relative target",
            simulated_root=current_rel or "<non-vendor-current-path>",
            future_runtime_path=current_path or "<empty>",
            mutation_required="none",
        ),
        PolicyCandidate(
            candidate_id="isolated-vendor-firmware-root",
            description="future read-only vendor mount plus firmware_class.path pointing at its firmware directory",
            simulated_root="firmware",
            future_runtime_path="/mnt/vendor/firmware",
            mutation_required="guarded firmware_class.path write in a later version",
        ),
        PolicyCandidate(
            candidate_id="synthetic-firmware-mnt-image-bind",
            description="future temporary bind layout preserving the current firmware_class.path",
            simulated_root="firmware",
            future_runtime_path="/vendor/firmware_mnt/image",
            mutation_required="temporary bind layout in a later version",
        ),
        PolicyCandidate(
            candidate_id="copy-to-lib-firmware",
            description="copy vendor firmware into /lib/firmware",
            simulated_root="<not-simulated>",
            future_runtime_path="/lib/firmware",
            mutation_required="copy firmware files; rejected",
            status="rejected",
        ),
    ]


def score_candidate(captures: list[CaptureRecord], candidate: PolicyCandidate) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if candidate.status == "rejected":
        return {
            "candidate_id": candidate.candidate_id,
            "description": candidate.description,
            "simulated_root": candidate.simulated_root,
            "future_runtime_path": candidate.future_runtime_path,
            "mutation_required": candidate.mutation_required,
            "status": candidate.status,
            "likely_pass": False,
            "uncertain_pass": False,
            "resolved_likely": [],
            "missing_likely": list(LIKELY_REQUEST_NAMES),
            "resolved_uncertain": [],
            "missing_uncertain": list(UNCERTAIN_REQUEST_NAMES),
            "requests": [],
        }
    for request in REQUEST_NAMES:
        rel_path = rel_from_root(candidate.simulated_root, request)
        visible = candidate.simulated_root not in {"", "<non-vendor-current-path>"} and path_visible(captures, rel_path)
        rows.append(
            {
                "request": request,
                "kind": "likely" if request in LIKELY_REQUEST_NAMES else "uncertain",
                "candidate_relative_path": rel_path,
                "visible": visible,
            }
        )
    resolved_likely = [row["request"] for row in rows if row["kind"] == "likely" and row["visible"]]
    missing_likely = [request for request in LIKELY_REQUEST_NAMES if request not in resolved_likely]
    resolved_uncertain = [row["request"] for row in rows if row["kind"] == "uncertain" and row["visible"]]
    missing_uncertain = [request for request in UNCERTAIN_REQUEST_NAMES if request not in resolved_uncertain]
    return {
        "candidate_id": candidate.candidate_id,
        "description": candidate.description,
        "simulated_root": candidate.simulated_root,
        "future_runtime_path": candidate.future_runtime_path,
        "mutation_required": candidate.mutation_required,
        "status": candidate.status,
        "likely_pass": not missing_likely,
        "uncertain_pass": not missing_uncertain,
        "resolved_likely": resolved_likely,
        "missing_likely": missing_likely,
        "resolved_uncertain": resolved_uncertain,
        "missing_uncertain": missing_uncertain,
        "requests": rows,
    }


def relevant_lines(captures: list[CaptureRecord], probe: ProbePaths, limit: int = 180) -> list[str]:
    keywords = (
        "firmware_class",
        "firmware_mnt",
        "firmware/wlan",
        "bdwlan",
        "regdb",
        "wlanmdsp",
        "WCNSS",
        "sda29",
        probe.base,
        probe.mountpoint,
        "ro,noload",
    )
    lines: list[str] = []
    for capture in captures:
        text = strip_cmdv1_text(capture.text)
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if any(token.lower() in line.lower() for token in keywords) and line not in lines:
                lines.append(line)
            if len(lines) >= limit:
                return lines
    return lines


def manifest_decision(manifest: dict[str, Any] | None) -> str | None:
    if not manifest:
        return None
    return manifest.get("decision") or manifest.get("classification", {}).get("decision")


def classify(
    captures: list[CaptureRecord],
    probe: ProbePaths,
    v209: dict[str, Any] | None,
    v210: dict[str, Any] | None,
    allow_non_v209_decision: bool,
    allow_non_v210_decision: bool,
) -> dict[str, Any]:
    basic_control_ok = capture_ok(captures, "version", "status")
    v209_decision = manifest_decision(v209)
    v210_decision = manifest_decision(v210)
    sys_dev_text = capture_text(captures, "sys-sda29-dev")
    major_minor = parse_major_minor(sys_dev_text)
    expected_major_minor = major_minor == (EXPECTED_MAJOR, EXPECTED_MINOR)
    ext4_available = "ext4" in capture_text(captures, "proc-filesystems").split()
    current_path = firmware_class_path(captures)
    post_path = firmware_class_path(captures, "post-firmware-class-path")
    path_unchanged = not post_path or post_path == current_path
    mount_capture = capture_by_name(captures, "safe-ro-noload-mount")
    mount_attempted = mount_capture is not None
    mount_ok = mount_capture.ok if mount_capture is not None else False
    mounted_after_mount = mountpoint_in_text(capture_text(captures, "mounted-proc-mounts"), probe)
    cleanup_capture = capture_by_name(captures, "cleanup-umount")
    cleanup_attempted = cleanup_capture is not None
    cleanup_rc = cleanup_capture.rc if cleanup_capture is not None else None
    leftover_mount = mountpoint_in_text(capture_text(captures, "post-proc-mounts"), probe)
    missing_required_firmware = [path for path in REQUIRED_VENDOR_FIRMWARE if not path_visible(captures, path)]
    visible = visible_paths(captures)
    candidate_scores = [score_candidate(captures, candidate) for candidate in build_candidates(probe, current_path)]
    score_by_id = {score["candidate_id"]: score for score in candidate_scores}
    current_score = score_by_id["current-firmware-class-path"]
    isolated_score = score_by_id["isolated-vendor-firmware-root"]
    synthetic_score = score_by_id["synthetic-firmware-mnt-image-bind"]

    if not basic_control_ok:
        decision = "manual-review-required"
        reason = "native bridge/control commands did not return usable evidence"
    elif not allow_non_v210_decision and v210_decision != V210_EXPECTED_DECISION:
        decision = "manual-review-required"
        reason = f"v210 decision is {v210_decision!r}, expected {V210_EXPECTED_DECISION!r}"
    elif not allow_non_v209_decision and v209_decision != V209_EXPECTED_DECISION:
        decision = "manual-review-required"
        reason = f"v209 decision is {v209_decision!r}, expected {V209_EXPECTED_DECISION!r}"
    elif not expected_major_minor:
        decision = "manual-review-required"
        reason = "sda29 major/minor could not be confirmed as 259:22"
    elif not ext4_available:
        decision = "manual-review-required"
        reason = "ext4 is not listed in /proc/filesystems"
    elif mount_attempted and mount_capture is not None and not mount_ok and re.search(
        r"not found|no such file|invalid option|unknown option|bad option|usage",
        mount_capture.text + mount_capture.error,
        re.IGNORECASE,
    ):
        decision = "manual-review-required"
        reason = "safe ro,noload mount command path is unavailable or unsupported"
    elif leftover_mount:
        decision = "cleanup-failed"
        reason = "temporary vendor mount remained after cleanup"
    elif mount_attempted and (not mount_ok or not mounted_after_mount):
        decision = "manual-review-required"
        reason = "temporary vendor ro,noload mount did not produce a mounted filesystem"
    elif not path_unchanged:
        decision = "manual-review-required"
        reason = "firmware_class.path changed during a read-only policy probe"
    elif missing_required_firmware:
        decision = "vendor-layout-risk-too-high"
        reason = "required vendor firmware was not visible during policy modeling"
    elif current_score["likely_pass"]:
        decision = "path-policy-ready"
        reason = "current firmware_class.path model resolves all likely firmware request names"
    elif isolated_score["likely_pass"]:
        decision = "sysfs-path-update-needed"
        reason = "isolated vendor firmware root resolves likely request names; future implementation needs guarded firmware_class.path update"
    elif synthetic_score["likely_pass"]:
        decision = "bind-layout-needed"
        reason = "synthetic firmware_mnt image model resolves likely request names; future implementation needs bind layout"
    elif any(score["resolved_likely"] for score in candidate_scores):
        decision = "request-name-unknown"
        reason = "some request names resolve, but no candidate resolves the full likely request set"
    else:
        decision = "vendor-layout-risk-too-high"
        reason = "no modeled policy resolves likely firmware request names"

    return {
        "decision": decision,
        "reason": reason,
        "basic_control_ok": basic_control_ok,
        "v209_decision": v209_decision,
        "v210_decision": v210_decision,
        "major_minor": ":".join(major_minor) if major_minor else None,
        "expected_major_minor": expected_major_minor,
        "ext4_available": ext4_available,
        "mount_attempted": mount_attempted,
        "mount_ok": mount_ok,
        "mounted_after_mount": mounted_after_mount,
        "cleanup_attempted": cleanup_attempted,
        "cleanup_rc": cleanup_rc,
        "leftover_mount": leftover_mount,
        "firmware_class_path": current_path,
        "post_firmware_class_path": post_path,
        "firmware_class_path_unchanged": path_unchanged,
        "probe_base": probe.base,
        "probe_node": probe.node,
        "probe_mountpoint": probe.mountpoint,
        "required_firmware": list(REQUIRED_VENDOR_FIRMWARE),
        "missing_required_firmware": missing_required_firmware,
        "visible_paths": visible,
        "visible_count": len(visible),
        "likely_request_names": list(LIKELY_REQUEST_NAMES),
        "uncertain_request_names": list(UNCERTAIN_REQUEST_NAMES),
        "candidate_scores": candidate_scores,
        "recommended_next": recommended_next(decision),
        "evidence_lines": relevant_lines(captures, probe),
    }


def recommended_next(decision: str) -> str:
    if decision == "sysfs-path-update-needed":
        return "v212 guarded opt-in firmware_class.path update and rollback test"
    if decision == "bind-layout-needed":
        return "v212 temporary bind-layout proof under a synthetic path before touching /vendor"
    if decision == "request-name-unknown":
        return "collect kernel firmware request-name evidence before layout mutation"
    if decision == "path-policy-ready":
        return "confirm with a no-op loader-path regression, then plan Wi-Fi daemon preflight"
    if decision == "cleanup-failed":
        return "stop and clean temporary mount before any further Wi-Fi work"
    return "manual review before any firmware path mutation"


def build_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    rows = [
        ["result", "PASS" if manifest["pass"] else "FAIL", c["reason"]],
        ["decision", c["decision"], c["recommended_next"]],
        ["v209", str(c["v209_decision"]), ""],
        ["v210", str(c["v210_decision"]), ""],
        ["major_minor", str(c["major_minor"]), f"expected={c['expected_major_minor']}"],
        ["ext4", str(c["ext4_available"]), ""],
        ["mount", str(c["mount_ok"]), f"attempted={c['mount_attempted']} mounted={c['mounted_after_mount']}"],
        ["cleanup", str(not c["leftover_mount"]), f"attempted={c['cleanup_attempted']} rc={c['cleanup_rc']}"],
        ["firmware_class.path", c["firmware_class_path"] or "<empty>", f"unchanged={c['firmware_class_path_unchanged']}"],
        ["required_firmware_missing", str(len(c["missing_required_firmware"])), ", ".join(c["missing_required_firmware"])],
    ]
    candidate_rows = [
        [
            item["candidate_id"],
            item["future_runtime_path"],
            item["mutation_required"],
            str(item["likely_pass"]),
            ", ".join(item["missing_likely"]),
            str(item["uncertain_pass"]),
            ", ".join(item["missing_uncertain"]),
        ]
        for item in c["candidate_scores"]
    ]
    request_rows: list[list[str]] = []
    for item in c["candidate_scores"]:
        for request in item["requests"]:
            request_rows.append(
                [
                    item["candidate_id"],
                    request["request"],
                    request["kind"],
                    request["candidate_relative_path"],
                    str(request["visible"]),
                ]
            )
    lines = [
        "# v211 Firmware Path / Vendor Layout Policy Probe\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{c['decision']}`\n",
        f"- reason: `{c['reason']}`\n",
        f"- recommended next: `{c['recommended_next']}`\n\n",
        "## Summary Matrix\n\n",
        markdown_table(["area", "status", "detail"], rows),
        "\n\n## Candidate Scores\n\n",
        markdown_table(
            ["candidate", "future path", "mutation", "likely pass", "missing likely", "uncertain pass", "missing uncertain"],
            candidate_rows,
        ),
        "\n\n## Request Resolution Matrix\n\n",
        markdown_table(["candidate", "request", "kind", "relative path", "visible"], request_rows),
        "\n\n## Visible Paths\n\n",
    ]
    if c["visible_paths"]:
        lines.extend(f"- `{path}`\n" for path in c["visible_paths"])
    else:
        lines.append("- none\n")
    lines.append("\n## Evidence Lines\n\n")
    if c["evidence_lines"]:
        lines.extend(f"- `{line}`\n" for line in c["evidence_lines"])
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
    validate_policy_commands()
    run_id = make_run_id(args.run_id)
    probe = make_probe_paths(run_id)
    store = EvidenceStore(args.out_dir)
    store.mkdir("native", "commands")
    captures: list[CaptureRecord] = []

    run_sequence(store, args, probe, READ_ONLY_COMMANDS, captures)
    v209 = load_json(args.v209_manifest)
    v210 = load_json(args.v210_manifest)
    initial = classify(captures, probe, v209, v210, args.allow_non_v209_decision, args.allow_non_v210_decision)
    should_probe = (
        initial["basic_control_ok"]
        and (args.allow_non_v209_decision or initial["v209_decision"] == V209_EXPECTED_DECISION)
        and (args.allow_non_v210_decision or initial["v210_decision"] == V210_EXPECTED_DECISION)
        and initial["expected_major_minor"]
        and initial["ext4_available"]
    )

    if should_probe:
        run_sequence(store, args, probe, build_probe_commands(probe), captures)
        mounted_snapshot = classify(captures, probe, v209, v210, args.allow_non_v209_decision, args.allow_non_v210_decision)
        if mounted_snapshot["mount_ok"] and mounted_snapshot["mounted_after_mount"]:
            run_sequence(store, args, probe, build_asset_commands(probe), captures)
        run_sequence(store, args, probe, build_cleanup_commands(probe), captures)
    elif initial["basic_control_ok"] and initial["expected_major_minor"]:
        run_sequence(store, args, probe, build_cleanup_commands(probe)[1:], captures)

    classification = classify(captures, probe, v209, v210, args.allow_non_v209_decision, args.allow_non_v210_decision)
    manifest: dict[str, Any] = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": classification["decision"] in DECISIONS and classification["decision"] not in {"manual-review-required", "cleanup-failed", "vendor-layout-risk-too-high"},
        "decision": classification["decision"],
        "reason": classification["reason"],
        "mode": "native-firmware-path-policy-probe",
        "probe": asdict(probe),
        "classification": classification,
        "captures": [asdict(item) for item in captures],
        "v209_native": {
            "path": str(args.v209_manifest),
            "present": v209 is not None,
            "decision": manifest_decision(v209),
        },
        "v210_native": {
            "path": str(args.v210_manifest),
            "present": v210 is not None,
            "decision": manifest_decision(v210),
        },
        "guardrails": [
            "model only; no firmware_class.path write",
            "no bind mount outside /tmp/a90-v211-*",
            "no /vendor or /lib/firmware mutation",
            "mount requires ro,noload",
            "temporary node and mountpoint only under /tmp/a90-v211-*",
            "cleanup umount attempted for any mount attempt",
            "no Wi-Fi enablement",
            "no rfkill write",
            "no WLAN link-up",
            "no scan/connect",
            "no module load/unload",
            "no cnss-daemon/cnss_diag/wificond/HAL/supplicant/hostapd start",
            "no firmware file copy",
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
