#!/usr/bin/env python3
"""Binding attended boot-only S20+ recovery-canary B0 F1 owner.

This owner never addresses the recovery partition.  Its sole candidate and
rollback members are ``boot.img.lz4``.  Candidate and rollback effects are
one-shot and the resident Magisk boot is mandatory recovery after any consumed
candidate intent.  Global ADB inventory may contain foreign devices, but only
one exact S20+ model row may be selected and every target command uses its
serial selector.
"""

from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import tempfile
import time
from typing import Any, Sequence

import device_action_raw_capture_v1 as raw_capture
import s20plus_g986n_d0_inventory as base
import s22plus_boot_only_f1_transport as transport


VERSION = "s20plus-g986n-boot-recovery-canary-b0-f1-v2"
PLAN_SCHEMA = "s20plus_g986n_boot_recovery_canary_b0_f1_plan_v2"
B0_F1_ACTIVE = True
EXPECTED_REVIEWED_NORMALIZED_SHA256 = "e2d612fc14549d0b0838ba66473b203126342362480636f3599fd9ea1548ed40"

ROOT = Path(__file__).resolve().parents[5]
SCRIPT = Path(__file__).resolve()
RUN_ROOT = ROOT / "workspace/private/runs/s20plus-g986n-boot-recovery-canary-b0-f1"
CLAIM_ROOT = RUN_ROOT / "consumed-candidates"
SHARED_GUARD = ROOT / "workspace/private/runs/s20plus-g986n-routine-actions/active-action.json"

TARGET = {
    "model": "SM-G986N",
    "device": "y2q",
    "product": "y2qksx",
    "incremental": "G986NKSS8IYC2",
}
EXPECTED_ADB_METADATA = frozenset(
    {"model:SM_G986N", "device:y2q", "product:y2qksx"}
)
EXPECTED_ADB_MODEL = "model:SM_G986N"
EXPECTED_ANDROID_TOPOLOGY_SHA256 = (
    "3279d577ef7a789f8aac93664e3b45543e10522b08d29ebabc99564ca86295f1"
)
EXPECTED_DOWNLOAD_TOPOLOGY_SHA256 = frozenset(
    {
        "3279d577ef7a789f8aac93664e3b45543e10522b08d29ebabc99564ca86295f1",
        "ae90de878991480bf8aafc6e131953d185245aba4fa8d9cd8d0507810d2c96e1",
    }
)

ODIN = Path("/usr/bin/odin4")
ODIN_SIZE = 3_746_744
ODIN_SHA256 = "6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b"
ADB = base.EXPECTED_ADB_REALPATH
ADB_SIZE = 716_968
ADB_SHA256 = "05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226"
DASH = Path("/usr/bin/dash")
DASH_SIZE = 129_856
DASH_SHA256 = "c626229526bb58ec2d0f585f3c3ae1412e6f973b4353385042d11c38d8426917"
CAGE_SLEEP = Path("/usr/bin/busybox")
CAGE_SLEEP_SIZE = 2_190_672
CAGE_SLEEP_SHA256 = "df12634c17fcdca839ae5dc47d7627b7558511f7645de7c99ccf097a0f28ed5b"
ODIN_CAGE_ENTRY_MARKER = b"S20PLUS_B0_ODIN_CGROUP_ENTERED_V1\n"
ODIN_CAGE_ENTRY_SCRIPT = r"""set -eu
cage=$1
shift
printf '%s\n' "$$" > "$cage/cgroup.procs"
printf 'S20PLUS_B0_ODIN_CGROUP_ENTERED_V1\n'
exec "$@"
"""
CAGE_CAPABILITY_SCRIPT = r"""set -eu
cage=$1
sleeper=$2
printf '%s\n' "$$" > "$cage/cgroup.procs"
printf 'S20PLUS_B0_ODIN_CGROUP_ENTERED_V1\n'
(trap '' TERM HUP; exec "$sleeper" sleep 3) &
wait
"""
ODIN_FIXED_ENV = {
    "LANG": "C",
    "LC_ALL": "C",
    "PATH": "/usr/bin:/bin",
}

OUTPUT_ROOT = ROOT / "workspace/private/outputs/s20plus_g986n/boot_recovery_canary_b0_v1"
CANDIDATE_AP = OUTPUT_ROOT / "candidate/AP.tar.md5"
CANDIDATE_AP_SIZE = 36_198_441
CANDIDATE_AP_SHA256 = "a8ed52d314e3b0cf5820e99ecd55e97cacdbc8a943d2181886d52d42a1c177fa"
CANDIDATE_MEMBER_SIZE = 36_195_767
CANDIDATE_MEMBER_SHA256 = "d06b3175dff1ebb0d9f47cc5f4e4787b6a2ee27fe2f740e2c048b586063a7f84"
CANDIDATE_BOOT_SIZE = 67_108_864
CANDIDATE_BOOT_SHA256 = "b42ba829a4a45728951f688b7b4ef07140686ce07f111a751bba948d1d934b4c"

ROLLBACK_AP = OUTPUT_ROOT / "rollback/AP.tar.md5"
ROLLBACK_AP_SIZE = 25_835_561
ROLLBACK_AP_SHA256 = "1b33d098ea34b0396330cedf2e40c508704f1ba035b1f81e80a8526a637f1be2"
ROLLBACK_MEMBER_SIZE = 25_833_304
ROLLBACK_MEMBER_SHA256 = "2003a3db44c35e0a32b6b485ca0260c7feeab4d9c3031b8cf3ec64f87a8b19b5"
ROLLBACK_BOOT_SIZE = 67_108_864
ROLLBACK_BOOT_SHA256 = "d67d0af219d40d29f9e4d34da873e7aa33577d56fab68e2beccfe707418f7efc"

MANIFEST = OUTPUT_ROOT / "manifest.json"
MANIFEST_SIZE = 8_090
MANIFEST_SHA256 = "a93b8175b1d20ab3ee53ec05420259e99d8434efd2ae8673fb635d928a9c1128"
BUILDER = ROOT / "workspace/public/src/scripts/revalidation/build_s20plus_g986n_boot_recovery_canary_b0_h0.py"
BUILDER_SIZE = 27_216
BUILDER_SHA256 = "3ef1eed83bf51e2725c0da62f31378d5505f89dc064fdd8e614bbfb02f7a131c"

SOURCE_CLOSURE = {
    "inventory": (
        ROOT / "workspace/public/src/scripts/revalidation/s20plus_g986n_d0_inventory.py",
        21_474,
        "3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81",
    ),
    "transport": (
        ROOT / "workspace/public/src/scripts/revalidation/s22plus_boot_only_f1_transport.py",
        10_937,
        "f18e2e453e33078a184653722d4579a184c59b1c3ac10f9eb54d4a4ba437ffea",
    ),
    "boot_verify": (
        ROOT / "workspace/public/src/scripts/revalidation/s22plus_boot_verify.py",
        37_806,
        "e19d604039a744d14bcdbb495951e95f86666b6927061529e440aacb4b63381d",
    ),
    "raw_capture": (
        ROOT / "workspace/public/src/scripts/revalidation/device_action_raw_capture_v1.py",
        25_006,
        "410e260129c0c50dca29b008dc7cf1051ee007816ab18bea76aeae62505ca0e4",
    ),
}

PHYSICAL_RECOVERY_EVIDENCE = {
    "bootstrap_report": {
        "path": str(ROOT / "docs/reports/S20PLUS_G986N_MAGISK_BOOTSTRAP_F1_H0_2026-08-13.md"),
        "size": 17_013,
        "sha256": "485687f0e814ba73f310137b711f6645a511cf19a9acac4b6ffe31c8c4a0caf6",
    },
    "resident_report": {
        "path": str(ROOT / "docs/reports/S20PLUS_G986N_MAGISK_RESIDENT_F1_H0_2026-08-15.md"),
        "size": 6_519,
        "sha256": "ae6c56b6a8c96ae987cc56f3f34dfbc5796f8a21eb77bcc0c9400e2a492b916b",
    },
    "download_return_report": {
        "path": str(ROOT / "docs/reports/S20PLUS_G986N_DOWNLOAD_EXIT_CHANGED_ENDPOINT_FINALIZER_INCIDENT_2026-08-20.md"),
        "size": 6_902,
        "sha256": "5e921b8320a2b46b25666c478c9b092271771f5abd0cbeadf1ed979331f83b6b",
    },
    "scope": "historical exact-target boot rollback plus attended Download entry/return evidence",
    "live_fallback_still_attended": True,
}

DOWNLOAD_USB = {
    "idVendor": "04e8",
    "idProduct": "685d",
    "product": "SM8250",
    "manufacturer": "Samsung",
}
USBFS_RE = re.compile(r"/dev/bus/usb/([0-9]{3})/([0-9]{3})")
HEX64_RE = re.compile(r"[0-9a-f]{64}")
BOOT_ID_RE = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
SAFE_VALUE_RE = re.compile(r"[^\x00\r\n]{0,4096}")

MAX_JSON_BYTES = 1024 * 1024
MAX_RAW_BYTES = 8 * 1024 * 1024
MAX_ADB_BYTES = 64 * 1024
AT_EMPTY_PATH = 0x1000
_LIBC = ctypes.CDLL(None, use_errno=True)
_LINKAT = _LIBC.linkat
_LINKAT.argtypes = (
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
    ctypes.c_char_p,
    ctypes.c_int,
)
_LINKAT.restype = ctypes.c_int
_BOUND_LINKAT = _LINKAT
APPROVAL_LIFETIME_SECONDS = 15 * 60
RECOVERY_ARRIVAL_SECONDS = 45
DOWNLOAD_ARRIVAL_SECONDS = 180
ANDROID_ARRIVAL_SECONDS = 420
PHYSICAL_ARRIVAL_LIFETIME_SECONDS = 15 * 60

APPROVAL_PREFIX = "S20PLUS-G986N-BOOT-RECOVERY-CANARY-B0-F1-APPROVE:"
PHYSICAL_CONFIRM_PREFIX = "S20PLUS-G986N-B0-PHYSICAL-ROLLBACK-CONFIRM:"

PUBLIC_SNAPSHOT_KEYS = (
    "model",
    "device",
    "product_name",
    "incremental",
    "boot_completed",
    "bootanim",
    "selinux",
    "boot_id",
)
PUBLIC_SNAPSHOT_SCRIPT = """set -eu
emit_prop() {
    printf '%s=' "$1"
    /system/bin/getprop "$2"
}
emit_prop model ro.product.model
emit_prop device ro.product.device
emit_prop product_name ro.product.name
emit_prop incremental ro.build.version.incremental
emit_prop boot_completed sys.boot_completed
emit_prop bootanim init.svc.bootanim
printf 'selinux='; /system/bin/getenforce
printf 'boot_id='; /system/bin/cat /proc/sys/kernel/random/boot_id
"""

ROOT_OUTPUT_KEYS = (
    "boot_id",
    "uid",
    "gid",
    "context",
    "magisk_version",
    "magisk_version_code",
    "selinux",
    "pid1_exe",
    "pid1_context",
)
EXPECTED_ROOT_OUTPUT = {
    "uid": "0",
    "gid": "0",
    "context": "u:r:magisk:s0",
    "magisk_version": "30.7:MAGISK:R",
    "magisk_version_code": "30700",
    "selinux": "Enforcing",
    "pid1_exe": "/system/bin/init",
    "pid1_context": "u:r:init:s0",
}
ROOT_READ_SCRIPT = r"""set -eu
boot_id=$(/system/bin/cat /proc/sys/kernel/random/boot_id)
uid=$(/system/bin/id -u)
gid=$(/system/bin/id -g)
context=$(/system/bin/cat /proc/self/attr/current)
magisk_version=$(/data/adb/magisk/magisk -v)
magisk_version_code=$(/data/adb/magisk/magisk -V)
selinux=$(/system/bin/getenforce)
pid1_exe=$(/system/bin/readlink /proc/1/exe)
pid1_context=$(/system/bin/cat /proc/1/attr/current)
printf '%s\n' \
    "boot_id=$boot_id" \
    "uid=$uid" \
    "gid=$gid" \
    "context=$context" \
    "magisk_version=$magisk_version" \
    "magisk_version_code=$magisk_version_code" \
    "selinux=$selinux" \
    "pid1_exe=$pid1_exe" \
    "pid1_context=$pid1_context"
"""
RECOVERY_TRANSPORT_KEYS = (
    "model",
    "device",
    "product_name",
    "incremental",
    "boot_id",
    "uid",
    "gid",
    "service_adb_root",
    "usb_config",
    "adbd_state",
)
RECOVERY_TRANSPORT_SCRIPT = r"""set -eu
model=$(/system/bin/getprop ro.product.model)
device=$(/system/bin/getprop ro.product.device)
product_name=$(/system/bin/getprop ro.product.name)
incremental=$(/system/bin/getprop ro.build.version.incremental)
boot_id=$(/system/bin/cat /proc/sys/kernel/random/boot_id)
uid=$(/system/bin/id -u)
gid=$(/system/bin/id -g)
service_adb_root=$(/system/bin/getprop service.adb.root)
usb_config=$(/system/bin/getprop sys.usb.config)
adbd_state=$(/system/bin/getprop init.svc.adbd)
printf '%s\n' \
    "model=$model" \
    "device=$device" \
    "product_name=$product_name" \
    "incremental=$incremental" \
    "boot_id=$boot_id" \
    "uid=$uid" \
    "gid=$gid" \
    "service_adb_root=$service_adb_root" \
    "usb_config=$usb_config" \
    "adbd_state=$adbd_state"
"""

RECOVERY_CLAIM_KEYS = (
    "marker_state",
    "marker_meta",
    "marker_sha256",
    "pid1_exe",
    "pid1_cmdline_hex",
    "pid1_context",
    "ueventd_count",
    "ueventd_exe",
    "ueventd_cmdline_hex",
    "recovery_state",
    "recovery_pid_count",
)
RECOVERY_CLAIM_SCRIPT = r"""set -eu
marker=/init.s20plus_g986n_recovery_adb_canary
marker_state=absent
marker_meta=none
marker_sha256=none
if [ -L "$marker" ]; then
    marker_state=symlink
elif [ -f "$marker" ]; then
    marker_state=regular
    marker_meta=$(/system/bin/stat -c '%a:%u:%g:%h:%s' "$marker")
    marker_line=$(/system/bin/sha256sum "$marker")
    set -- $marker_line
    [ "$#" -eq 2 ] || exit 81
    [ "$2" = "$marker" ] || exit 82
    marker_sha256=$1
fi
pid1_exe=$(/system/bin/readlink /proc/1/exe)
pid1_cmdline_hex=$(/system/bin/xxd -p /proc/1/cmdline | /system/bin/tr -d '\n')
pid1_context=$(/system/bin/cat /proc/1/attr/current)
ueventd_pids=$(/system/bin/pidof ueventd || true)
set -- $ueventd_pids
ueventd_count=$#
ueventd_exe=none
ueventd_cmdline_hex=none
if [ "$ueventd_count" -eq 1 ]; then
    ueventd_exe=$(/system/bin/readlink "/proc/$1/exe")
    ueventd_cmdline_hex=$(/system/bin/xxd -p "/proc/$1/cmdline" | /system/bin/tr -d '\n')
fi
recovery_state=$(/system/bin/getprop init.svc.recovery)
[ -n "$recovery_state" ] || recovery_state=absent
recovery_pids=$(/system/bin/pidof recovery || true)
set -- $recovery_pids
recovery_pid_count=$#
printf '%s\n' \
    "marker_state=$marker_state" \
    "marker_meta=$marker_meta" \
    "marker_sha256=$marker_sha256" \
    "pid1_exe=$pid1_exe" \
    "pid1_cmdline_hex=$pid1_cmdline_hex" \
    "pid1_context=$pid1_context" \
    "ueventd_count=$ueventd_count" \
    "ueventd_exe=$ueventd_exe" \
    "ueventd_cmdline_hex=$ueventd_cmdline_hex" \
    "recovery_state=$recovery_state" \
    "recovery_pid_count=$recovery_pid_count"
"""

MARKER_SHA256 = "5aafd7ca6918bf82aef0b7de62346d8de1b17bb0c9ececafa15978cfae2c87b0"
PID1_CMDLINES = frozenset({"2f696e697400", "2f73797374656d2f62696e2f696e697400"})
UEVENTD_CMDLINES = frozenset(
    {
        "756576656e746400",
        "2f73797374656d2f62696e2f756576656e746400",
        "2f73797374656d2f62696e2f696e697400756576656e746400",
    }
)

RUN_NODE_NAMES = frozenset(
    {
        "preflight-root.stdout",
        "preflight-root.stderr",
        "preflight-root.capture.json",
        "preflight.json",
        "initial-download-baseline.json",
        "initial-download-intent.json",
        "initial-reboot.stdout",
        "initial-reboot.stderr",
        "initial-reboot.capture.json",
        "initial-download-result.json",
        "initial-download-arrival.json",
        "prepared.json",
        "approval.json",
        "candidate-adb-baseline.json",
        "candidate-claim-intent.json",
        "candidate-intent.json",
        "candidate.stdout",
        "candidate.stderr",
        "candidate-transfer.capture.json",
        "candidate-cage-quiescent.json",
        "candidate-result.json",
        "candidate-transfer-cut.json",
        "candidate-observation-intent.json",
        "candidate-transport.stdout",
        "candidate-transport.stderr",
        "candidate-transport.capture.json",
        "candidate-claim.stdout",
        "candidate-claim.stderr",
        "candidate-claim.capture.json",
        "candidate-observation.json",
        "candidate-android-root.stdout",
        "candidate-android-root.stderr",
        "candidate-android-root.capture.json",
        "rollback-download-baseline.json",
        "rollback-download-intent.json",
        "rollback-download-effect-baseline.json",
        "rollback-reboot.stdout",
        "rollback-reboot.stderr",
        "rollback-reboot.capture.json",
        "rollback-download-result.json",
        "rollback-download-observation-intent.json",
        "rollback-download-arrival.json",
        "rollback-source.stdout",
        "rollback-source.stderr",
        "rollback-source.capture.json",
        "rollback-source-root.stdout",
        "rollback-source-root.stderr",
        "rollback-source-root.capture.json",
        "physical-rollback-baseline.json",
        "physical-rollback-intent.json",
        "physical-confirmation-intent.json",
        "physical-observation-intent.json",
        "physical-resume-observation-intent.json",
        "physical-observation-miss.json",
        "physical-rollback-arrival.json",
        "rollback-intent.json",
        "rollback.stdout",
        "rollback.stderr",
        "rollback-transfer.capture.json",
        "rollback-cage-quiescent.json",
        "rollback-result.json",
        "final-root.stdout",
        "final-root.stderr",
        "final-root.capture.json",
        "final-health.json",
        "terminal.json",
        "abort-return-intent.json",
        "abort-return.stdout",
        "abort-return.stderr",
        "abort-return.capture.json",
        "abort-return-cage-quiescent.json",
        "abort-return-result.json",
    }
)
REPEATABLE_HEALTH_CAPTURE_RE = re.compile(
    r"(?:preflight-root|candidate-android-root|rollback-source-root|final-root)"
    r"(?:-resume-[0-9]{4})?"
    r"\.(?:stdout|stderr|capture\.json)"
)


class B0F1Error(RuntimeError):
    pass


class ProcessCageError(B0F1Error):
    pass


_BOUND_APIS = {
    "inventory.bounded_command": base.bounded_command,
    "inventory.parse_inventory": base.parse_inventory,
    "inventory.tool_receipt": base.tool_receipt,
    "transport.pin_regular_file": transport.pin_regular_file,
    "transport.pin_boot_only_ap": transport.pin_boot_only_ap,
    "transport.read_boot_only_member": transport.read_boot_only_member,
    "transport.build_odin_boot_only_command": transport.build_odin_boot_only_command,
    "transport.revalidate_pinned_path": transport.revalidate_pinned_path,
    "raw_capture.acquire_command": raw_capture.acquire_command,
    "raw_capture.read_stdout": raw_capture.read_stdout,
    "raw_capture.read_stderr": raw_capture.read_stderr,
    "raw_capture.load_handle": raw_capture.load_handle,
}
_BOUND_MODULES = {
    "transport.boot_verify": transport.boot_verify,
    "transport.raw_capture": transport.raw_capture,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise B0F1Error("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise B0F1Error(f"non-finite JSON constant: {value}")


def fsync_dir(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def open_direct_directory(path: Path) -> int:
    direct = path.absolute()
    if not direct.is_absolute() or ".." in direct.parts:
        raise B0F1Error("directory path is not canonical")
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in direct.parts[1:]:
            child = os.open(
                part,
                os.O_RDONLY
                | os.O_DIRECTORY
                | os.O_CLOEXEC
                | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _directory_identity(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_nlink,
        metadata.st_uid,
        metadata.st_gid,
    )


def _decode_canonical_json(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            payload.decode("utf-8", "strict"),
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise B0F1Error(f"{label} is malformed") from exc
    if not isinstance(value, dict) or payload != canonical_bytes(value):
        raise B0F1Error(f"{label} is not canonical typed JSON")
    return value


def _atomic_publish_at(
    parent_fd: int, name: str, payload: bytes, mode: int, label: str
) -> None:
    if _LINKAT is not _BOUND_LINKAT:
        raise B0F1Error("atomic publication API was rebound")
    if not getattr(os, "O_TMPFILE", 0):
        raise B0F1Error("O_TMPFILE is unavailable")
    descriptor = -1
    try:
        descriptor = os.open(
            ".",
            os.O_WRONLY | os.O_TMPFILE | os.O_CLOEXEC,
            mode,
            dir_fd=parent_fd,
        )
        os.fchmod(descriptor, mode)
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise B0F1Error(f"short {label} write")
            offset += written
        os.fsync(descriptor)
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 0
            or stat.S_IMODE(metadata.st_mode) != mode
            or metadata.st_size != len(payload)
        ):
            raise B0F1Error(f"staged {label} identity differs")
        if _LINKAT(
            descriptor,
            b"",
            parent_fd,
            os.fsencode(name),
            AT_EMPTY_PATH,
        ) != 0:
            number = ctypes.get_errno()
            raise OSError(number, os.strerror(number), name)
        linked = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if (
            linked.st_dev != metadata.st_dev
            or linked.st_ino != metadata.st_ino
            or linked.st_nlink != 1
            or stat.S_IMODE(linked.st_mode) != mode
            or linked.st_size != len(payload)
        ):
            raise B0F1Error(f"published {label} identity differs")
        os.fsync(parent_fd)
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def durable_json(path: Path, value: dict[str, Any]) -> None:
    payload = canonical_bytes(value)
    if len(payload) > MAX_JSON_BYTES:
        raise B0F1Error("journal record exceeds its bound")
    parent_fd = open_direct_directory(path.parent)
    try:
        _atomic_publish_at(parent_fd, path.name, payload, 0o400, "journal")
    finally:
        os.close(parent_fd)


def read_json(path: Path, label: str) -> dict[str, Any]:
    parent_fd = open_direct_directory(path.parent)
    try:
        descriptor = os.open(
            path.name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except OSError as exc:
        os.close(parent_fd)
        raise B0F1Error(f"{label} is unavailable") from exc
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_size > MAX_JSON_BYTES
        ):
            raise B0F1Error(f"{label} is not a bounded direct regular file")
        payload = bytearray()
        while len(payload) < metadata.st_size:
            block = os.read(descriptor, metadata.st_size - len(payload))
            if not block:
                break
            payload.extend(block)
        if len(payload) != metadata.st_size or os.read(descriptor, 1):
            raise B0F1Error(f"{label} changed during read")
    finally:
        os.close(descriptor)
        os.close(parent_fd)
    return _decode_canonical_json(bytes(payload), label)


def file_receipt(path: Path, size: int, sha256: str, label: str) -> dict[str, Any]:
    direct = path.absolute()
    if direct.resolve(strict=True) != direct or direct.is_symlink():
        raise B0F1Error(f"{label} path is indirect")
    descriptor = os.open(direct, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_nlink != 1
            or before.st_size != size
        ):
            raise B0F1Error(f"{label} identity differs")
        result = hashlib.sha256()
        total = 0
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            total += len(block)
            result.update(block)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    current = os.lstat(direct)
    identity = lambda item: (
        item.st_dev,
        item.st_ino,
        item.st_mode,
        item.st_nlink,
        item.st_size,
        item.st_mtime_ns,
        item.st_ctime_ns,
    )
    if (
        total != size
        or result.hexdigest() != sha256
        or identity(before) != identity(after)
        or identity(after) != identity(current)
    ):
        raise B0F1Error(f"{label} bytes or path identity differ")
    return {"path": str(direct), "size": size, "sha256": sha256}


def normalized_self_sha256() -> str:
    source = SCRIPT.read_bytes()
    source, active_count = re.subn(
        rb"^B0_F1_ACTIVE = (?:False|True)$",
        b"B0_F1_ACTIVE = <REVIEWED_ACTIVATION_BOOLEAN>",
        source,
        flags=re.MULTILINE,
    )
    source, hash_count = re.subn(
        rb'^EXPECTED_REVIEWED_NORMALIZED_SHA256 = "[0-9a-f]{64}"$',
        b'EXPECTED_REVIEWED_NORMALIZED_SHA256 = "' + b"0" * 64 + b'"',
        source,
        flags=re.MULTILINE,
    )
    if active_count != 1 or hash_count != 1:
        raise B0F1Error("runner normalization grammar changed")
    return hashlib.sha256(source).hexdigest()


def self_receipt() -> dict[str, Any]:
    metadata = SCRIPT.lstat()
    if (
        SCRIPT.is_symlink()
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or SCRIPT.resolve(strict=True) != SCRIPT.absolute()
    ):
        raise B0F1Error("runner source is indirect")
    normalized = normalized_self_sha256()
    if normalized != EXPECTED_REVIEWED_NORMALIZED_SHA256:
        raise B0F1Error("runner source is not the reviewed normalized identity")
    return {
        "path": str(SCRIPT),
        "size": metadata.st_size,
        "sha256": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
        "normalized_sha256": normalized,
    }


def _source_receipts(names: Sequence[str]) -> dict[str, Any]:
    modules = {
        "inventory": base,
        "transport": transport,
        "boot_verify": transport.boot_verify,
        "raw_capture": raw_capture,
    }
    receipts: dict[str, Any] = {}
    for name in names:
        path, size, sha256 = SOURCE_CLOSURE[name]
        try:
            module_path = Path(modules[name].__file__).resolve(strict=True)
        except (OSError, TypeError) as exc:
            raise B0F1Error(f"{name} module path is unavailable") from exc
        if module_path != path:
            raise B0F1Error(f"{name} module path differs")
        receipts[name] = file_receipt(path, size, sha256, f"closure {name}")
    return receipts


def _assert_bound_apis(names: Sequence[str]) -> None:
    current_apis = {
        "inventory.bounded_command": base.bounded_command,
        "inventory.parse_inventory": base.parse_inventory,
        "inventory.tool_receipt": base.tool_receipt,
        "transport.pin_regular_file": transport.pin_regular_file,
        "transport.pin_boot_only_ap": transport.pin_boot_only_ap,
        "transport.read_boot_only_member": transport.read_boot_only_member,
        "transport.build_odin_boot_only_command": transport.build_odin_boot_only_command,
        "transport.revalidate_pinned_path": transport.revalidate_pinned_path,
        "raw_capture.acquire_command": raw_capture.acquire_command,
        "raw_capture.read_stdout": raw_capture.read_stdout,
        "raw_capture.read_stderr": raw_capture.read_stderr,
        "raw_capture.load_handle": raw_capture.load_handle,
    }
    if any(current_apis[name] is not _BOUND_APIS[name] for name in names):
        raise B0F1Error("imported execution API was rebound")


def health_source_closure_receipts() -> dict[str, Any]:
    receipts = _source_receipts(("inventory", "raw_capture"))
    _assert_bound_apis(
        (
            "inventory.bounded_command",
            "inventory.parse_inventory",
            "inventory.tool_receipt",
            "raw_capture.acquire_command",
            "raw_capture.read_stdout",
            "raw_capture.read_stderr",
            "raw_capture.load_handle",
        )
    )
    receipts["adb"] = base.tool_receipt(ADB)
    return receipts


def source_closure_receipts() -> dict[str, Any]:
    receipts = _source_receipts(tuple(SOURCE_CLOSURE))
    _assert_bound_apis(tuple(_BOUND_APIS))
    if (
        transport.boot_verify is not _BOUND_MODULES["transport.boot_verify"]
        or transport.raw_capture is not _BOUND_MODULES["transport.raw_capture"]
        or transport.raw_capture is not raw_capture
    ):
        raise B0F1Error("transport dependency module was rebound")
    receipts["adb"] = base.tool_receipt(ADB)
    receipts["odin"] = file_receipt(ODIN, ODIN_SIZE, ODIN_SHA256, "Odin4")
    receipts["cage_shell"] = file_receipt(
        DASH, DASH_SIZE, DASH_SHA256, "process-cage shell"
    )
    receipts["cage_sleep"] = file_receipt(
        CAGE_SLEEP, CAGE_SLEEP_SIZE, CAGE_SLEEP_SHA256, "process-cage sleeper"
    )
    return receipts


def validate_manifest() -> dict[str, Any]:
    receipt = file_receipt(MANIFEST, MANIFEST_SIZE, MANIFEST_SHA256, "B0 manifest")
    try:
        value = json.loads(
            MANIFEST.read_text("utf-8"),
            object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise B0F1Error("B0 manifest is malformed") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema") != "s20plus_g986n_boot_recovery_canary_b0_build_v1"
        or value.get("target") != TARGET
        or value.get("tier") != "H0"
        or value.get("live_authority") is not False
        or value.get("candidate", {}).get("ap_tar_md5", {}).get("sha256")
        != CANDIDATE_AP_SHA256
        or value.get("candidate", {}).get("boot_img_lz4")
        != {"size": CANDIDATE_MEMBER_SIZE, "sha256": CANDIDATE_MEMBER_SHA256}
        or value.get("candidate", {}).get("boot_img")
        != {"size": CANDIDATE_BOOT_SIZE, "sha256": CANDIDATE_BOOT_SHA256}
        or value.get("rollback", {}).get("ap_tar_md5", {}).get("sha256")
        != ROLLBACK_AP_SHA256
        or value.get("rollback", {}).get("boot_img_lz4")
        != {"size": ROLLBACK_MEMBER_SIZE, "sha256": ROLLBACK_MEMBER_SHA256}
        or value.get("rollback", {}).get("boot_img")
        != {"size": ROLLBACK_BOOT_SIZE, "sha256": ROLLBACK_BOOT_SHA256}
        or value.get("safety", {}).get("boot_only_candidate") is not True
        or value.get("safety", {}).get("boot_only_rollback") is not True
        or value.get("safety", {}).get("recovery_partition_read") is not False
        or value.get("safety", {}).get("recovery_partition_write") is not False
        or value.get("safety", {}).get("recovery_partition_transfer") is not False
        or value.get("boot_carrier_safety_delta", {}).get("recovery_service_disabled")
        is not True
    ):
        raise B0F1Error("B0 manifest closure differs")
    return receipt


def audit_boot_ap(
    path: Path,
    size: int,
    sha256: str,
    member_size: int,
    member_sha256: str,
    decoded_size: int,
    decoded_sha256: str,
    label: str,
) -> dict[str, Any]:
    metadata = path.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) & 0o022
    ):
        raise B0F1Error(f"{label} is writable or indirect")
    with transport.pin_boot_only_ap(
        path,
        label=label,
        expected_size=size,
        expected_sha256=sha256,
        require_deterministic_metadata=True,
    ) as pinned:
        member = transport.read_boot_only_member(
            pinned,
            label=label,
            require_deterministic_metadata=True,
            maximum=64 * 1024 * 1024,
        )
        transport.revalidate_pinned_path(pinned)
        if len(member) != member_size or hashlib.sha256(member).hexdigest() != member_sha256:
            raise B0F1Error(f"{label} member identity differs")
        ap = pinned.receipt()
    return {
        "ap": ap,
        "member": {
            "name": "boot.img.lz4",
            "size": member_size,
            "sha256": member_sha256,
        },
        "decoded_boot": {
            "size": decoded_size,
            "sha256": decoded_sha256,
            "binding": "exact-member-plus-reviewed-manifest",
        },
    }


def physical_recovery_receipts() -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name in ("bootstrap_report", "resident_report", "download_return_report"):
        expected = PHYSICAL_RECOVERY_EVIDENCE[name]
        result[name] = file_receipt(
            Path(expected["path"]), expected["size"], expected["sha256"], name
        )
    result["scope"] = PHYSICAL_RECOVERY_EVIDENCE["scope"]
    result["live_fallback_still_attended"] = True
    return result


def validate_host_closure(*, include_candidate: bool = True, include_rollback: bool = True) -> dict[str, Any]:
    closure = {
        "runner": self_receipt(),
        "sources": source_closure_receipts(),
        "physical_recovery": physical_recovery_receipts(),
        "process_cage_capability": validate_process_cage_capability(),
    }
    if include_candidate:
        closure["builder"] = file_receipt(BUILDER, BUILDER_SIZE, BUILDER_SHA256, "B0 builder")
        closure["manifest"] = validate_manifest()
        closure["candidate"] = audit_boot_ap(
            CANDIDATE_AP,
            CANDIDATE_AP_SIZE,
            CANDIDATE_AP_SHA256,
            CANDIDATE_MEMBER_SIZE,
            CANDIDATE_MEMBER_SHA256,
            CANDIDATE_BOOT_SIZE,
            CANDIDATE_BOOT_SHA256,
            "B0 candidate",
        )
    if include_rollback:
        closure["rollback"] = audit_boot_ap(
            ROLLBACK_AP,
            ROLLBACK_AP_SIZE,
            ROLLBACK_AP_SHA256,
            ROLLBACK_MEMBER_SIZE,
            ROLLBACK_MEMBER_SHA256,
            ROLLBACK_BOOT_SIZE,
            ROLLBACK_BOOT_SHA256,
            "resident rollback",
        )
    return closure


def validate_rollback_closure() -> dict[str, Any]:
    return {
        "runner": self_receipt(),
        "sources": source_closure_receipts(),
        "rollback": audit_boot_ap(
            ROLLBACK_AP,
            ROLLBACK_AP_SIZE,
            ROLLBACK_AP_SHA256,
            ROLLBACK_MEMBER_SIZE,
            ROLLBACK_MEMBER_SHA256,
            ROLLBACK_BOOT_SIZE,
            ROLLBACK_BOOT_SHA256,
            "resident rollback",
        ),
    }


def validate_health_closure() -> dict[str, Any]:
    return {
        "runner": self_receipt(),
        "sources": health_source_closure_receipts(),
    }


def require_active() -> None:
    if not B0_F1_ACTIVE:
        raise B0F1Error("S20+ B0 F1 is not active")
    self_receipt()


def _decode(result: tuple[int, bytes, bytes], label: str) -> str:
    if type(result) is not tuple or len(result) != 3:
        raise B0F1Error(f"{label} envelope is malformed")
    returncode, stdout, stderr = result
    if (
        type(returncode) is not int
        or type(stdout) is not bytes
        or type(stderr) is not bytes
        or len(stdout) + len(stderr) > MAX_ADB_BYTES
        or returncode != 0
        or stderr
    ):
        raise B0F1Error(f"{label} failed")
    try:
        return stdout.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise B0F1Error(f"{label} output is malformed") from exc


def _ordered_output(
    result: tuple[int, bytes, bytes], keys: Sequence[str], label: str
) -> dict[str, str]:
    text = _decode(result, label)
    if not text.endswith("\n") or "\r" in text or "\x00" in text:
        raise B0F1Error(f"{label} framing differs")
    lines = text.splitlines()
    if len(lines) != len(keys):
        raise B0F1Error(f"{label} field count differs")
    values: dict[str, str] = {}
    for expected, line in zip(keys, lines, strict=True):
        key, separator, value = line.partition("=")
        if (
            separator != "="
            or key != expected
            or key in values
            or SAFE_VALUE_RE.fullmatch(value) is None
        ):
            raise B0F1Error(f"{label} field grammar differs")
        values[key] = value
    return values


def adb_inventory(*, health_only: bool = False) -> tuple[dict[str, Any], ...]:
    if health_only:
        health_source_closure_receipts()
    else:
        source_closure_receipts()
    text = _decode(
        base.bounded_command([str(ADB), "devices", "-l"], 10, MAX_ADB_BYTES),
        "ADB inventory",
    ).strip()
    try:
        return base.parse_inventory(text)
    except Exception as exc:
        raise B0F1Error("ADB inventory is malformed") from exc


def sanitized_inventory(rows: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    return [
        {
            "serial_sha256": hashlib.sha256(row["serial"].encode()).hexdigest(),
            "state": row["state"],
            "metadata": sorted(row["metadata"]),
        }
        for row in rows
    ]


def validate_sanitized_inventory(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > 64:
        raise B0F1Error(f"{label} is malformed")
    serials: set[str] = set()
    for row in value:
        if not isinstance(row, dict) or set(row) != {
            "serial_sha256",
            "state",
            "metadata",
        }:
            raise B0F1Error(f"{label} row is malformed")
        serial_sha256 = row.get("serial_sha256")
        state = row.get("state")
        metadata = row.get("metadata")
        if (
            not isinstance(serial_sha256, str)
            or HEX64_RE.fullmatch(serial_sha256) is None
            or serial_sha256 in serials
            or not isinstance(state, str)
            or SAFE_VALUE_RE.fullmatch(state) is None
            or not state
            or not isinstance(metadata, list)
            or len(metadata) > 64
            or any(
                not isinstance(item, str)
                or not item
                or SAFE_VALUE_RE.fullmatch(item) is None
                for item in metadata
            )
            or metadata != sorted(set(metadata))
        ):
            raise B0F1Error(f"{label} row fields are malformed")
        serials.add(serial_sha256)
    return value


def target_adb_rows(rows: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
    return tuple(row for row in rows if EXPECTED_ADB_MODEL in row["metadata"])


def exact_adb_row(
    rows: tuple[dict[str, Any], ...],
    expected_serial_sha256: str | None,
    expected_state: str,
) -> dict[str, Any]:
    matches = target_adb_rows(rows)
    if len(matches) != 1:
        raise B0F1Error("exact S20+ ADB inventory is absent or ambiguous")
    row = matches[0]
    serial_sha256 = hashlib.sha256(row["serial"].encode()).hexdigest()
    if (
        (expected_serial_sha256 is not None and serial_sha256 != expected_serial_sha256)
        or row["state"] != expected_state
        or not EXPECTED_ADB_METADATA <= row["metadata"]
    ):
        raise B0F1Error("ADB row is not the exact target state")
    return row


def candidate_adb_baseline_receipt(
    rows: tuple[dict[str, Any], ...], expected_serial_sha256: str
) -> dict[str, Any]:
    inventory = sanitized_inventory(rows)
    validate_sanitized_inventory(inventory, "candidate ADB baseline inventory")
    if any(
        row["serial_sha256"] == expected_serial_sha256
        or EXPECTED_ADB_MODEL in row["metadata"]
        for row in inventory
    ):
        raise B0F1Error("exact S20+ remains present in candidate ADB baseline")
    return {
        "inventory": inventory,
        "inventory_sha256": digest(inventory),
        "exact_target_present": False,
        "other_target_commands": 0,
    }


def adb_devpath(serial: str) -> str:
    text = _decode(
        base.bounded_command(
            [str(ADB), "-s", serial, "get-devpath"], 10, MAX_ADB_BYTES
        ),
        "ADB devpath",
    )
    if not text.endswith("\n") or text.count("\n") != 1:
        raise B0F1Error("ADB devpath framing differs")
    devpath = text[:-1]
    if (
        base.DEVPATH_RE.fullmatch(devpath) is None
        or hashlib.sha256(devpath.encode()).hexdigest()
        != EXPECTED_ANDROID_TOPOLOGY_SHA256
    ):
        raise B0F1Error("ADB topology differs")
    return devpath


def parse_public_snapshot(result: tuple[int, bytes, bytes]) -> dict[str, str]:
    values = _ordered_output(result, PUBLIC_SNAPSHOT_KEYS, "Android public health")
    expected = {
        "model": TARGET["model"],
        "device": TARGET["device"],
        "product_name": TARGET["product"],
        "incremental": TARGET["incremental"],
        "boot_completed": "1",
        "bootanim": "stopped",
        "selinux": "Enforcing",
    }
    if any(values[key] != expected_value for key, expected_value in expected.items()):
        raise B0F1Error("Android public health differs")
    if BOOT_ID_RE.fullmatch(values["boot_id"]) is None:
        raise B0F1Error("Android boot ID is malformed")
    return values


def parse_root_output(result: tuple[int, bytes, bytes]) -> dict[str, str]:
    values = _ordered_output(result, ROOT_OUTPUT_KEYS, "resident root health")
    if (
        BOOT_ID_RE.fullmatch(values["boot_id"]) is None
        or any(values[key] != expected for key, expected in EXPECTED_ROOT_OUTPUT.items())
    ):
        raise B0F1Error("resident root fields differ")
    return values


def resident_health_once(
    capture_dir: Path,
    capture_name: str,
    expected_serial_sha256: str | None = None,
) -> tuple[dict[str, Any], str]:
    closure = health_source_closure_receipts()
    first = adb_inventory(health_only=True)
    row = exact_adb_row(first, expected_serial_sha256, "device")
    serial = row["serial"]
    devpath = adb_devpath(serial)
    snapshot = parse_public_snapshot(
        base.bounded_command(
            [str(ADB), "-s", serial, "exec-out", "sh", "-c", PUBLIC_SNAPSHOT_SCRIPT],
            20,
            MAX_ADB_BYTES,
        )
    )
    candidate_names = [capture_name]
    candidate_names.extend(f"{capture_name}-resume-{ordinal:04d}" for ordinal in range(1, 10_000))
    selected_capture_name: str | None = None
    handle: raw_capture.RawCaptureHandle | None = None
    root_values: dict[str, str] | None = None
    for candidate_name in candidate_names:
        receipt_exists = os.path.lexists(capture_dir / f"{candidate_name}.capture.json")
        stdout_exists = os.path.lexists(capture_dir / f"{candidate_name}.stdout")
        stderr_exists = os.path.lexists(capture_dir / f"{candidate_name}.stderr")
        if receipt_exists:
            candidate_handle = raw_capture.load_handle(
                capture_dir / f"{candidate_name}.capture.json"
            )
            candidate_stdout = raw_capture.read_stdout(candidate_handle, maximum=4096)
            candidate_stderr = raw_capture.read_stderr(candidate_handle, maximum=4096)
            try:
                candidate_values = parse_root_output(
                    (candidate_handle.returncode, candidate_stdout, candidate_stderr)
                )
            except B0F1Error:
                continue
            if candidate_values["boot_id"] != snapshot["boot_id"]:
                continue
            selected_capture_name = candidate_name
            handle = candidate_handle
            root_values = candidate_values
            break
        if not stdout_exists and not stderr_exists:
            selected_capture_name = candidate_name
            break
    if selected_capture_name is None:
        raise B0F1Error("resident root read ordinal space is exhausted")
    capture_path = capture_dir / f"{selected_capture_name}.capture.json"
    if handle is None:
        handle = raw_capture.acquire_command(
            [
                str(ADB),
                "-s",
                serial,
                "shell",
                "su",
                "-c",
                shlex.quote(ROOT_READ_SCRIPT),
            ],
            capture_dir,
            selected_capture_name,
            timeout=30,
            stdout_maximum=4096,
            stderr_maximum=4096,
            stdout_name=f"{selected_capture_name}.stdout",
            stderr_name=f"{selected_capture_name}.stderr",
        )
        stdout = raw_capture.read_stdout(handle, maximum=4096)
        stderr = raw_capture.read_stderr(handle, maximum=4096)
        root_values = parse_root_output((handle.returncode, stdout, stderr))
    assert root_values is not None
    if root_values["boot_id"] != snapshot["boot_id"]:
        raise B0F1Error("resident root capture boot identity differs")
    second_snapshot = parse_public_snapshot(
        base.bounded_command(
            [str(ADB), "-s", serial, "exec-out", "sh", "-c", PUBLIC_SNAPSHOT_SCRIPT],
            20,
            MAX_ADB_BYTES,
        )
    )
    final = adb_inventory(health_only=True)
    final_row = exact_adb_row(final, hashlib.sha256(serial.encode()).hexdigest(), "device")
    if (
        second_snapshot != snapshot
        or sanitized_inventory(final) != sanitized_inventory(first)
        or adb_devpath(final_row["serial"]) != devpath
        or root_values["boot_id"] != second_snapshot["boot_id"]
        or health_source_closure_receipts() != closure
    ):
        raise B0F1Error("resident identity changed during root health")
    receipt = {
        "target": dict(TARGET),
        "serial_sha256": hashlib.sha256(serial.encode()).hexdigest(),
        "topology_sha256": hashlib.sha256(devpath.encode()).hexdigest(),
        "boot_id_sha256": hashlib.sha256(snapshot["boot_id"].encode()).hexdigest(),
        "public_health": {key: value for key, value in snapshot.items() if key != "boot_id"},
        "root_health": {
            key: value for key, value in root_values.items() if key != "boot_id"
        },
        "inventory_sha256": digest(sanitized_inventory(first)),
        "root_capture": {
            "path": str(handle.receipt_path),
            "size": handle.receipt_path.stat().st_size,
            "sha256": hashlib.sha256(handle.receipt_path.read_bytes()).hexdigest(),
        },
    }
    return receipt, serial


def parse_recovery_transport(result: tuple[int, bytes, bytes]) -> dict[str, str]:
    values = _ordered_output(result, RECOVERY_TRANSPORT_KEYS, "recovery transport")
    expected = {
        "model": TARGET["model"],
        "device": TARGET["device"],
        "product_name": TARGET["product"],
        "incremental": TARGET["incremental"],
        "uid": "0",
        "gid": "0",
        "service_adb_root": "1",
        "usb_config": "adb",
        "adbd_state": "running",
    }
    if any(values[key] != expected_value for key, expected_value in expected.items()):
        raise B0F1Error("recovery transport fields differ")
    if BOOT_ID_RE.fullmatch(values["boot_id"]) is None:
        raise B0F1Error("recovery boot ID is malformed")
    return values


def parse_recovery_claim(result: tuple[int, bytes, bytes]) -> tuple[str, dict[str, str]]:
    try:
        values = _ordered_output(result, RECOVERY_CLAIM_KEYS, "recovery claim")
    except B0F1Error:
        return "NO_PROOF", {}
    exact = (
        values["marker_state"] == "regular"
        and values["marker_meta"] == "444:0:0:1:159"
        and values["marker_sha256"] == MARKER_SHA256
        and values["pid1_exe"] == "/system/bin/init"
        and values["pid1_cmdline_hex"] in PID1_CMDLINES
        and values["pid1_context"] == "u:r:init:s0"
        and values["ueventd_count"] == "1"
        and values["ueventd_exe"] == "/system/bin/init"
        and values["ueventd_cmdline_hex"] in UEVENTD_CMDLINES
        and values["recovery_state"] in {"absent", "stopped"}
        and values["recovery_pid_count"] == "0"
    )
    return ("PROVED" if exact else "REFUTED"), values


def parse_download_listing(text: str) -> list[str]:
    rows = [line.strip() for line in text.splitlines() if line.strip()]
    if any(USBFS_RE.fullmatch(row) is None for row in rows) or len(set(rows)) != len(rows):
        raise B0F1Error("Odin Download listing is malformed")
    return sorted(rows)


def raw_dispatch_proved(
    handle: raw_capture.RawCaptureHandle, stderr: bytes
) -> bool:
    return (
        type(handle.returncode) is int
        and handle.returncode == 0
        and not stderr
        and handle.producer_error_type is None
        and not handle.timed_out
        and not handle.output_exceeded
    )


def enumerate_download() -> tuple[list[str], str]:
    source_closure_receipts()
    text = _bounded_odin_listing()
    return parse_download_listing(text), hashlib.sha256(text.encode()).hexdigest()


def download_baseline() -> dict[str, Any]:
    devices, listing_sha256 = enumerate_download()
    if devices:
        raise B0F1Error("Download baseline is not empty")
    return {
        "schema": "s20plus_g986n_b0_download_baseline_v1",
        "endpoint_count": 0,
        "listing_sha256": listing_sha256,
        "at": utc_now(),
    }


def validate_download_baseline(value: dict[str, Any], label: str) -> dict[str, Any]:
    if (
        set(value) != {"schema", "endpoint_count", "listing_sha256", "at"}
        or value.get("schema") != "s20plus_g986n_b0_download_baseline_v1"
        or type(value.get("endpoint_count")) is not int
        or value.get("endpoint_count") != 0
        or not isinstance(value.get("listing_sha256"), str)
        or HEX64_RE.fullmatch(value["listing_sha256"]) is None
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise B0F1Error(f"{label} is malformed")
    return value


def _read_small(path: Path) -> str | None:
    try:
        payload = path.read_bytes()
    except FileNotFoundError:
        return None
    if len(payload) > 512:
        raise B0F1Error("Download sysfs value is oversized")
    try:
        return payload.decode("utf-8", "strict").strip()
    except UnicodeError as exc:
        raise B0F1Error("Download sysfs value is malformed") from exc


def endpoint_stat(path: str) -> tuple[int, int, int, int]:
    metadata = os.stat(path, follow_symlinks=False)
    if not stat.S_ISCHR(metadata.st_mode) or metadata.st_nlink != 1:
        raise B0F1Error("Odin endpoint is not a direct character device")
    return metadata.st_dev, metadata.st_ino, metadata.st_rdev, metadata.st_ctime_ns


def identify_download() -> dict[str, Any]:
    devices, _listing = enumerate_download()
    if len(devices) != 1:
        raise B0F1Error("Download endpoint is absent or ambiguous")
    device = devices[0]
    identity = endpoint_stat(device)
    match = USBFS_RE.fullmatch(device)
    assert match is not None
    bus, dev = str(int(match.group(1))), str(int(match.group(2)))
    matches: list[tuple[Path, dict[str, str | None]]] = []
    for node in sorted(Path("/sys/bus/usb/devices").glob("[0-9]*-[0-9]*")):
        values = {
            name: _read_small(node / name)
            for name in ("busnum", "devnum", *DOWNLOAD_USB, "serial")
        }
        if values["busnum"] == bus and values["devnum"] == dev:
            matches.append((node, values))
    if len(matches) != 1:
        raise B0F1Error("Download sysfs identity is absent or ambiguous")
    node, values = matches[0]
    repeated = {name: _read_small(node / name) for name in values}
    if (
        repeated != values
        or any(values[key] != expected for key, expected in DOWNLOAD_USB.items())
        or values["serial"] not in (None, "")
        or endpoint_stat(device) != identity
    ):
        raise B0F1Error("Download USB identity changed or differs")
    topology = hashlib.sha256(f"usb:{node.name}".encode()).hexdigest()
    if topology not in EXPECTED_DOWNLOAD_TOPOLOGY_SHA256:
        raise B0F1Error("Download topology is not allowlisted")
    return {
        "device": device,
        "endpoint_identity": list(identity),
        "endpoint_sha256": hashlib.sha256(device.encode()).hexdigest(),
        "topology_sha256": topology,
        "usb": {**DOWNLOAD_USB, "serial_absent": True},
    }


def same_download_session(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left.get("device") == right.get("device")
        and left.get("endpoint_sha256") == right.get("endpoint_sha256")
        and left.get("endpoint_identity", [])[:3] == right.get("endpoint_identity", [])[:3]
        and left.get("topology_sha256") == right.get("topology_sha256")
        and left.get("usb") == right.get("usb")
    )


def wait_download(baseline: dict[str, Any], timeout: float = DOWNLOAD_ARRIVAL_SECONDS) -> dict[str, Any] | None:
    validate_download_baseline(baseline, "Download wait baseline")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            devices, listing_sha256 = enumerate_download()
        except B0F1Error:
            time.sleep(2)
            continue
        if len(devices) > 1:
            raise B0F1Error("Download endpoint became ambiguous")
        if len(devices) == 1:
            endpoint = identify_download()
            if endpoint["device"] == devices[0]:
                return {
                    "endpoint": endpoint,
                    "baseline_sha256": digest(baseline),
                    "arrival_listing_sha256": listing_sha256,
                    "at": utc_now(),
                }
        time.sleep(2)
    return None


def ensure_private_roots() -> None:
    parent = RUN_ROOT.parent.resolve(strict=True)
    if RUN_ROOT.exists():
        if RUN_ROOT.is_symlink() or RUN_ROOT.resolve(strict=True) != RUN_ROOT.absolute():
            raise B0F1Error("B0 run root is indirect")
    else:
        if RUN_ROOT.parent.absolute() != parent:
            raise B0F1Error("B0 run parent is indirect")
        RUN_ROOT.mkdir(mode=0o700)
        fsync_dir(RUN_ROOT.parent)
    if CLAIM_ROOT.exists():
        if CLAIM_ROOT.is_symlink() or CLAIM_ROOT.resolve(strict=True) != CLAIM_ROOT.absolute():
            raise B0F1Error("B0 claim root is indirect")
    else:
        CLAIM_ROOT.mkdir(mode=0o700)
        fsync_dir(RUN_ROOT)


def allocate_run_dir(requested: Path | None) -> Path:
    ensure_private_roots()
    target = requested or RUN_ROOT / f"run-{time.time_ns()}"
    target = target if target.is_absolute() else ROOT / target
    if target.parent != RUN_ROOT or target.exists() or target.is_symlink():
        raise B0F1Error("B0 run path is not a fresh direct child")
    target.mkdir(mode=0o700)
    fsync_dir(RUN_ROOT)
    return target


def validate_run_dir(run_dir: Path) -> Path:
    ensure_private_roots()
    if (
        run_dir.parent != RUN_ROOT
        or run_dir.is_symlink()
        or not run_dir.is_dir()
        or run_dir.resolve(strict=True) != run_dir.absolute()
    ):
        raise B0F1Error("B0 run directory is indirect")
    validate_namespace(run_dir)
    return run_dir


def _hex64(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64_RE.fullmatch(value) is None:
        raise B0F1Error(f"{label} is not a SHA-256 digest")
    return value


def _validate_endpoint(value: Any, label: str) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "device",
            "endpoint_identity",
            "endpoint_sha256",
            "topology_sha256",
            "usb",
        }
        or not isinstance(value.get("device"), str)
        or USBFS_RE.fullmatch(value["device"]) is None
        or value.get("endpoint_sha256")
        != hashlib.sha256(value["device"].encode()).hexdigest()
        or not isinstance(value.get("endpoint_identity"), list)
        or len(value["endpoint_identity"]) != 4
        or any(type(item) is not int for item in value["endpoint_identity"])
        or value.get("topology_sha256") not in EXPECTED_DOWNLOAD_TOPOLOGY_SHA256
        or value.get("usb") != {**DOWNLOAD_USB, "serial_absent": True}
    ):
        raise B0F1Error(f"{label} is malformed")
    return value


def _validate_transfer_intent(
    value: dict[str, Any], kind: str, binding_sha256: str
) -> None:
    ordinary = {
        "schema",
        "version",
        "kind",
        "binding_sha256",
        "ap_sha256",
        "endpoint",
        "process_cage",
        "attempt",
        "no_replay",
        "at",
    }
    claim_cut = (ordinary - {"process_cage"}) | {
        "backend_invoked",
        "global_claim_cut",
    }
    if (
        set(value) not in (ordinary, claim_cut)
        or value.get("schema") != "s20plus_g986n_b0_transfer_intent_v1"
        or value.get("version") != VERSION
        or value.get("kind") != kind
        or value.get("binding_sha256") != binding_sha256
        or value.get("ap_sha256")
        != (CANDIDATE_AP_SHA256 if kind == "candidate" else ROLLBACK_AP_SHA256)
        or type(value.get("attempt")) is not int
        or value.get("attempt") != 1
        or value.get("no_replay") is not True
        or not isinstance(value.get("at"), str)
        or not value["at"]
    ):
        raise B0F1Error(f"{kind} intent is malformed")
    _validate_endpoint(value.get("endpoint"), f"{kind} intent endpoint")
    if set(value) == claim_cut and (
        kind != "candidate"
        or value.get("backend_invoked") is not False
        or value.get("global_claim_cut") is not True
    ):
        raise B0F1Error("candidate global-claim cut intent is malformed")


def _validate_transfer_outcome(
    run_dir: Path, value: dict[str, Any], kind: str, binding_sha256: str
) -> None:
    complete_keys = {
        "schema",
        "version",
        "kind",
        "binding_sha256",
        "classification",
        "receipt",
        "stdout_sha256",
        "stderr_sha256",
        "host_process_quiescence_proved",
        "replay_permitted",
        "at",
    }
    failure_keys = {
        "schema",
        "version",
        "kind",
        "binding_sha256",
        "classification",
        "failure_class",
        "possible_partition_effect",
        "host_process_quiescence_proved",
        "replay_permitted",
        "at",
    }
    if (
        set(value) not in (complete_keys, failure_keys)
        or
        value.get("schema") != "s20plus_g986n_b0_transfer_result_v1"
        or value.get("version") != VERSION
        or value.get("kind") != kind
        or value.get("binding_sha256") != binding_sha256
        or value.get("classification")
        not in {
            "odin_transfer_completed",
            "odin_local_parse_failure",
            "odin_device_session_failure_or_unknown",
        }
        or value.get("replay_permitted") is not False
        or not isinstance(value.get("at"), str)
    ):
        raise B0F1Error(f"{kind} transfer result is malformed")
    if "receipt" in value:
        receipt = value["receipt"]
        intent = read_json(run_dir / f"{kind}-intent.json", f"{kind} intent")
        if (
            not isinstance(receipt, dict)
            or receipt.get("label") != kind
            or receipt.get("command_shape")
            != ["odin4", "--reboot", "-a", "AP.tar.md5", "-d", "USBFS"]
            or receipt.get("regular_path_inputs") is not True
            or receipt.get("anonymous_proc_fd_inputs") is not False
            or value.get("host_process_quiescence_proved") is not True
            or receipt.get("ap")
            != {
                "path": str(CANDIDATE_AP if kind == "candidate" else ROLLBACK_AP),
                "size": CANDIDATE_AP_SIZE if kind == "candidate" else ROLLBACK_AP_SIZE,
                "sha256": CANDIDATE_AP_SHA256
                if kind == "candidate"
                else ROLLBACK_AP_SHA256,
            }
            or receipt.get("odin")
            != {"path": str(ODIN), "size": ODIN_SIZE, "sha256": ODIN_SHA256}
            or receipt.get("endpoint_path_sha256")
            != hashlib.sha256(intent["endpoint"]["device"].encode()).hexdigest()
            or receipt.get("endpoint_pre_identity")
            != intent["endpoint"]["endpoint_identity"]
            or receipt.get("endpoint_post_state") not in {"same", "absent", "changed"}
            or (
                receipt.get("endpoint_post_state") == "same"
                and receipt.get("endpoint_post_identity")
                != intent["endpoint"]["endpoint_identity"]
            )
            or (
                receipt.get("endpoint_post_state") == "absent"
                and receipt.get("endpoint_post_identity") is not None
            )
        ):
            raise B0F1Error(f"{kind} transport receipt is malformed")
        handle = raw_capture.load_handle(run_dir / f"{kind}-transfer.capture.json")
        raw_receipt = receipt.get("raw_capture_receipt")
        if (
            handle.argv0_name != DASH.name
            or
            not isinstance(raw_receipt, dict)
            or raw_receipt.get("path") != str(handle.receipt_path)
            or raw_receipt.get("size") != handle.receipt_path.stat().st_size
            or raw_receipt.get("sha256")
            != hashlib.sha256(handle.receipt_path.read_bytes()).hexdigest()
        ):
            raise B0F1Error(f"{kind} raw capture receipt differs")
        stdout = raw_capture.read_stdout(handle, maximum=MAX_RAW_BYTES)
        stderr = raw_capture.read_stderr(handle, maximum=MAX_RAW_BYTES)
        if (
            hashlib.sha256(stdout).hexdigest()
            != _hex64(value.get("stdout_sha256"), f"{kind} stdout")
            or hashlib.sha256(stderr).hexdigest()
            != _hex64(value.get("stderr_sha256"), f"{kind} stderr")
        ):
            raise B0F1Error(f"{kind} raw evidence hash differs")
        derived = classify_odin_capture(handle, stdout, stderr)
        if receipt.get("endpoint_post_state") == "changed" and not endpoint_ctime_only_change(
            receipt
        ):
            derived = "odin_device_session_failure_or_unknown"
        if derived != value.get("classification"):
            raise B0F1Error(f"{kind} classification is not raw-derived")
    elif (
        value.get("classification") != "odin_device_session_failure_or_unknown"
        or type(value.get("possible_partition_effect")) is not bool
        or type(value.get("host_process_quiescence_proved")) is not bool
        or not isinstance(value.get("failure_class"), str)
        or not value["failure_class"]
    ):
        raise B0F1Error(f"{kind} failure result is malformed")


def _validate_candidate_observation(
    run_dir: Path,
    value: dict[str, Any],
    binding_sha256: str,
    initial_boot_id_sha256: str,
) -> None:
    environments = {
        "recovery-adb",
        "recovery-adb-unqualified",
        "resident-android",
        "android-unqualified",
        "download",
        "download-unquiesced",
        "download-ambiguous",
        "adb-malformed",
        "adb-ambiguous",
        "adb-foreign",
        "adb-wrong-state",
        "no-arrival",
        "observer-reporting-cut",
    }
    if (
        value.get("schema") != "s20plus_g986n_b0_candidate_observation_v1"
        or value.get("version") != VERSION
        or value.get("binding_sha256") != binding_sha256
        or value.get("environment") not in environments
        or type(value.get("transport_authorized")) is not bool
        or value.get("claim_verdict") not in {"PROVED", "REFUTED", "NO_PROOF"}
        or value.get("candidate_replay_permitted") is not False
    ):
        raise B0F1Error("candidate observation is malformed")
    if value["environment"] == "recovery-adb":
        if value["transport_authorized"] is not True:
            raise B0F1Error("qualified recovery transport lost authority")
        _hex64(value.get("serial_sha256"), "recovery serial")
        if value.get("topology_sha256") != EXPECTED_ANDROID_TOPOLOGY_SHA256:
            raise B0F1Error("recovery topology receipt differs")
        _hex64(value.get("boot_id_sha256"), "recovery boot ID")
        transport_handle = raw_capture.load_handle(
            run_dir / "candidate-transport.capture.json"
        )
        transport_stdout = raw_capture.read_stdout(transport_handle, maximum=4096)
        transport_stderr = raw_capture.read_stderr(transport_handle, maximum=4096)
        transport_values = parse_recovery_transport(
            (transport_handle.returncode, transport_stdout, transport_stderr)
        )
        claim_handle = raw_capture.load_handle(run_dir / "candidate-claim.capture.json")
        claim_stdout = raw_capture.read_stdout(claim_handle, maximum=4096)
        claim_stderr = raw_capture.read_stderr(claim_handle, maximum=4096)
        derived_verdict, claim_values = parse_recovery_claim(
            (claim_handle.returncode, claim_stdout, claim_stderr)
        )
        if value["boot_id_sha256"] == initial_boot_id_sha256:
            derived_verdict = "REFUTED"
        if (
            hashlib.sha256(transport_values["boot_id"].encode()).hexdigest()
            != value["boot_id_sha256"]
            or value.get("transport_values")
            != {
                key: item
                for key, item in transport_values.items()
                if key != "boot_id"
            }
            or value.get("claim_values") != claim_values
            or value.get("claim_verdict") != derived_verdict
        ):
            raise B0F1Error("recovery observation is not raw-derived")
    elif value["environment"] == "resident-android":
        health = value.get("resident_health")
        if value["transport_authorized"] is not True or not isinstance(health, dict):
            raise B0F1Error("resident-return observation is malformed")
        _validate_resident_health_receipt(
            run_dir,
            health,
            "candidate resident health",
            "candidate-android-root",
        )
        if health["boot_id_sha256"] == initial_boot_id_sha256:
            raise B0F1Error("resident candidate reused the prepared boot")
    elif value["environment"] == "download":
        if value["transport_authorized"] is not True:
            raise B0F1Error("Download observation lost transport authority")
        _validate_endpoint(value.get("endpoint"), "candidate Download endpoint")
    elif value["transport_authorized"] is not False:
        raise B0F1Error("unqualified candidate observation gained authority")


def _validate_resident_health_receipt(
    run_dir: Path, value: Any, label: str, capture_prefix: str
) -> dict[str, Any]:
    expected_keys = {
        "target",
        "serial_sha256",
        "topology_sha256",
        "boot_id_sha256",
        "public_health",
        "root_health",
        "inventory_sha256",
        "root_capture",
    }
    if (
        not isinstance(value, dict)
        or set(value) != expected_keys
        or value.get("target") != TARGET
        or value.get("topology_sha256") != EXPECTED_ANDROID_TOPOLOGY_SHA256
        or value.get("public_health")
        != {
            "model": TARGET["model"],
            "device": TARGET["device"],
            "product_name": TARGET["product"],
            "incremental": TARGET["incremental"],
            "boot_completed": "1",
            "bootanim": "stopped",
            "selinux": "Enforcing",
        }
        or value.get("root_health") != EXPECTED_ROOT_OUTPUT
    ):
        raise B0F1Error(f"{label} is malformed")
    _hex64(value.get("serial_sha256"), f"{label} serial")
    _hex64(value.get("boot_id_sha256"), f"{label} boot ID")
    _hex64(value.get("inventory_sha256"), f"{label} inventory")
    capture = value.get("root_capture")
    if not isinstance(capture, dict) or set(capture) != {"path", "size", "sha256"}:
        raise B0F1Error(f"{label} root capture is malformed")
    capture_path = Path(capture["path"])
    expected_capture_re = re.compile(
        rf"{re.escape(capture_prefix)}(?:-resume-[0-9]{{4}})?\.capture\.json"
    )
    if (
        capture_path.parent != run_dir
        or expected_capture_re.fullmatch(capture_path.name) is None
    ):
        raise B0F1Error(f"{label} root capture escaped its run")
    file_receipt(
        capture_path,
        capture["size"],
        _hex64(capture["sha256"], f"{label} root capture"),
        f"{label} root capture",
    )
    handle = raw_capture.load_handle(capture_path)
    stdout = raw_capture.read_stdout(handle, maximum=4096)
    stderr = raw_capture.read_stderr(handle, maximum=4096)
    parsed = parse_root_output((handle.returncode, stdout, stderr))
    if (
        hashlib.sha256(parsed["boot_id"].encode()).hexdigest()
        != value["boot_id_sha256"]
    ):
        raise B0F1Error(f"{label} root capture boot identity differs")
    return value


def _validate_process_cage_binding(
    value: Any, kind: str, binding_sha256: str
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise B0F1Error(f"{kind} process-cage binding is absent")
    parent = Path(value.get("parent", ""))
    expected_cage = parent / f"s20plus-b0-{kind}-{binding_sha256[:20]}"
    if (
        set(value)
        != {
            "schema",
            "version",
            "kind",
            "binding_sha256",
            "parent",
            "parent_identity",
            "cage",
            "host_boot_id_sha256",
            "cage_identity",
            "empty_before_backend",
            "at",
        }
        or value.get("schema") != "s20plus_g986n_b0_process_cage_binding_v1"
        or value.get("version") != VERSION
        or value.get("kind") != kind
        or value.get("binding_sha256") != binding_sha256
        or not parent.is_absolute()
        or parent.parts[:4] != ("/", "sys", "fs", "cgroup")
        or ".." in parent.parts
        or value.get("cage") != str(expected_cage)
        or not isinstance(value.get("parent_identity"), list)
        or len(value["parent_identity"]) != 5
        or any(type(item) is not int for item in value["parent_identity"])
        or not isinstance(value.get("cage_identity"), list)
        or len(value["cage_identity"]) != 5
        or any(type(item) is not int for item in value["cage_identity"])
        or HEX64_RE.fullmatch(str(value.get("host_boot_id_sha256"))) is None
        or value.get("empty_before_backend") is not True
    ):
        raise B0F1Error(f"{kind} process-cage binding is malformed")
    return value


def _validate_process_cage_quiescence(
    run_dir: Path,
    actual: set[str],
    kind: str,
    binding_sha256: str,
    cage_binding: dict[str, Any],
) -> dict[str, Any] | None:
    name = f"{kind}-cage-quiescent.json"
    if name not in actual:
        return None
    value = read_json(run_dir / name, f"{kind} process-cage quiescence")
    if (
        set(value)
        != {
            "schema",
            "version",
            "kind",
            "binding_sha256",
            "cage_binding_sha256",
            "kill_requested",
            "cage_absent_before_check",
            "empty_and_removed",
            "at",
        }
        or value.get("schema") != "s20plus_g986n_b0_process_cage_quiescent_v1"
        or value.get("version") != VERSION
        or value.get("kind") != kind
        or value.get("binding_sha256") != binding_sha256
        or value.get("cage_binding_sha256") != digest(cage_binding)
        or type(value.get("kill_requested")) is not bool
        or type(value.get("cage_absent_before_check")) is not bool
        or value.get("empty_and_removed") is not True
    ):
        raise B0F1Error(f"{kind} process-cage quiescence is malformed")
    return value


def validate_critical_records(run_dir: Path, actual: set[str]) -> None:
    if "abort-return-intent.json" in actual:
        intent = read_json(run_dir / "abort-return-intent.json", "abort return intent")
        if (
            set(intent)
            != {
                "schema",
                "version",
                "endpoint",
                "cage_binding_sha256",
                "process_cage",
                "command_shape",
                "no_payload",
                "attempt",
                "no_replay",
                "at",
            }
            or intent.get("schema") != "s20plus_g986n_b0_abort_return_intent_v1"
            or intent.get("version") != VERSION
            or intent.get("command_shape") != ["odin4", "--reboot", "-d", "USBFS"]
            or intent.get("cage_binding_sha256")
            != abort_return_cage_binding(run_dir, intent.get("endpoint"))
            or intent.get("no_payload") is not True
            or intent.get("attempt") != 1
            or type(intent.get("attempt")) is not int
            or intent.get("no_replay") is not True
        ):
            raise B0F1Error("abort return intent is malformed")
        _validate_endpoint(intent.get("endpoint"), "abort return endpoint")
        abort_cage_binding = _validate_process_cage_binding(
            intent.get("process_cage"),
            "abort-return",
            intent["cage_binding_sha256"],
        )
        abort_cage_quiescent = _validate_process_cage_quiescence(
            run_dir,
            actual,
            "abort-return",
            intent["cage_binding_sha256"],
            abort_cage_binding,
        )
    if "abort-return-result.json" in actual:
        result = read_json(run_dir / "abort-return-result.json", "abort return result")
        handle = raw_capture.load_handle(run_dir / "abort-return.capture.json")
        stdout = raw_capture.read_stdout(handle, maximum=MAX_ADB_BYTES)
        stderr = raw_capture.read_stderr(handle, maximum=MAX_ADB_BYTES)
        derived = "dispatched" if raw_dispatch_proved(handle, stderr) else "uncertain"
        if (
            result.get("schema") != "s20plus_g986n_b0_abort_return_result_v1"
            or result.get("version") != VERSION
            or result.get("returncode") != handle.returncode
            or result.get("stdout_sha256") != hashlib.sha256(stdout).hexdigest()
            or result.get("stderr_sha256") != hashlib.sha256(stderr).hexdigest()
            or result.get("outcome") != derived
            or result.get("replay_permitted") is not False
            or abort_cage_quiescent is None
            or handle.argv0_name != DASH.name
            or not stdout.startswith(ODIN_CAGE_ENTRY_MARKER)
        ):
            raise B0F1Error("abort return result is not raw-derived")
    if "prepared.json" not in actual:
        if any(
            name in actual
            for name in (
                "candidate-intent.json",
                "candidate-result.json",
                "candidate-transfer-cut.json",
                "candidate-observation.json",
                "rollback-intent.json",
                "rollback-result.json",
            )
        ):
            raise B0F1Error("effect journal exists without a prepared binding")
        if "final-health.json" in actual:
            final = read_json(run_dir / "final-health.json", "abort final health")
            if (
                final.get("schema") != "s20plus_g986n_b0_final_health_v1"
                or final.get("version") != VERSION
                or final.get("binding_sha256") is not None
                or final.get("rollback_transfer_completed") is not False
                or final.get("rollback_outcome_proved") is not False
                or final.get("resident_boot_healthy") is not True
            ):
                raise B0F1Error("abort final health is malformed")
            final_health = _validate_resident_health_receipt(
                run_dir,
                final.get("health"),
                "abort resident health",
                "final-root",
            )
            if "preflight.json" in actual:
                preflight_record = read_json(
                    run_dir / "preflight.json", "abort preflight"
                )
                preflight_health = {
                    key: value
                    for key, value in preflight_record.items()
                    if key not in {"schema", "version"}
                }
                _validate_resident_health_receipt(
                    run_dir,
                    preflight_health,
                    "abort preflight health",
                    "preflight-root",
                )
                if (
                    final_health["boot_id_sha256"]
                    == preflight_health["boot_id_sha256"]
                ):
                    raise B0F1Error("abort final health reused the preflight boot")
        if "terminal.json" in actual:
            terminal = read_json(run_dir / "terminal.json", "abort terminal")
            if (
                terminal.get("schema") != "s20plus_g986n_b0_terminal_v1"
                or terminal.get("version") != VERSION
                or terminal.get("binding_sha256") is not None
                or terminal.get("verdict")
                != "ABORTED_PRE_CANDIDATE_RESIDENT_HEALTHY"
                or terminal.get("experiment_pass") is not False
                or terminal.get("candidate_attempts") != 0
                or terminal.get("rollback_attempts") != 0
            ):
                raise B0F1Error("abort terminal is malformed")
        return
    prepared = read_json(run_dir / "prepared.json", "B0 prepared binding")
    binding = prepared.get("binding")
    if not isinstance(binding, dict) or prepared.get("binding_sha256") != digest(binding):
        raise B0F1Error("prepared binding digest differs")
    binding_sha256 = prepared["binding_sha256"]
    cage_bindings: dict[str, dict[str, Any] | None] = {
        "candidate": None,
        "rollback": None,
    }
    cage_quiescence: dict[str, dict[str, Any] | None] = {
        "candidate": None,
        "rollback": None,
    }
    if "approval.json" in actual:
        approval = read_json(run_dir / "approval.json", "B0 approval")
        if (
            set(approval)
            != {
                "schema",
                "version",
                "binding_sha256",
                "approval_sha256",
                "candidate_replay_permitted",
                "rollback_preapproved",
                "at",
            }
            or approval.get("schema") != "s20plus_g986n_b0_approval_v1"
            or approval.get("version") != VERSION
            or approval.get("binding_sha256") != binding_sha256
            or approval.get("approval_sha256")
            != hashlib.sha256(prepared["approval_token"].encode()).hexdigest()
            or approval.get("candidate_replay_permitted") is not False
            or approval.get("rollback_preapproved") is not True
        ):
            raise B0F1Error("B0 approval record is malformed")
    if "candidate-claim-intent.json" in actual:
        _candidate_claim_intent(run_dir, binding_sha256)
    if "candidate-adb-baseline.json" in actual:
        baseline = read_json(
            run_dir / "candidate-adb-baseline.json", "candidate ADB baseline"
        )
        baseline_inventory = validate_sanitized_inventory(
            baseline.get("inventory"), "candidate ADB baseline inventory"
        )
        if (
            set(baseline)
            != {
                "schema",
                "version",
                "inventory",
                "inventory_sha256",
                "exact_target_present",
                "other_target_commands",
                "at",
            }
            or baseline.get("schema")
            != "s20plus_g986n_b0_candidate_adb_baseline_v2"
            or baseline.get("version") != VERSION
            or baseline.get("inventory_sha256") != digest(baseline_inventory)
            or baseline.get("exact_target_present") is not False
            or baseline.get("other_target_commands") != 0
            or type(baseline.get("other_target_commands")) is not int
            or any(
                row["serial_sha256"] == binding["preflight"]["serial_sha256"]
                or EXPECTED_ADB_MODEL in row["metadata"]
                for row in baseline_inventory
            )
        ):
            raise B0F1Error("candidate ADB baseline is malformed")
    if "candidate-intent.json" in actual:
        candidate_intent = read_json(
            run_dir / "candidate-intent.json", "candidate intent"
        )
        _validate_transfer_intent(
            candidate_intent,
            "candidate",
            binding_sha256,
        )
        if candidate_intent.get("global_claim_cut") is not True:
            cage_bindings["candidate"] = _validate_process_cage_binding(
                candidate_intent.get("process_cage"),
                "candidate",
                binding_sha256,
            )
            cage_quiescence["candidate"] = _validate_process_cage_quiescence(
                run_dir,
                actual,
                "candidate",
                binding_sha256,
                cage_bindings["candidate"],
            )
    if "candidate-result.json" in actual:
        _validate_transfer_outcome(
            run_dir,
            read_json(run_dir / "candidate-result.json", "candidate result"),
            "candidate",
            binding_sha256,
        )
    if "candidate-transfer-cut.json" in actual:
        cut = read_json(run_dir / "candidate-transfer-cut.json", "candidate cut")
        if (
            cut.get("schema") != "s20plus_g986n_b0_candidate_transfer_cut_v1"
            or cut.get("version") != VERSION
            or cut.get("binding_sha256") != binding_sha256
            or cut.get("classification") != "odin_device_session_failure_or_unknown"
            or type(cut.get("possible_partition_effect")) is not bool
            or cut.get("candidate_replay_permitted") is not False
        ):
            raise B0F1Error("candidate transfer cut is malformed")
    if "candidate-observation-intent.json" in actual:
        intent = read_json(
            run_dir / "candidate-observation-intent.json",
            "candidate observation intent",
        )
        if (
            intent.get("schema")
            != "s20plus_g986n_b0_candidate_observation_intent_v1"
            or intent.get("version") != VERSION
            or intent.get("binding_sha256") != binding_sha256
            or type(intent.get("timeout_seconds")) is not int
            or intent.get("timeout_seconds") != RECOVERY_ARRIVAL_SECONDS
            or intent.get("candidate_replay_permitted") is not False
        ):
            raise B0F1Error("candidate observation intent is malformed")
    if "candidate-observation.json" in actual:
        _validate_candidate_observation(
            run_dir,
            read_json(run_dir / "candidate-observation.json", "candidate observation"),
            binding_sha256,
            binding.get("preflight", {}).get("boot_id_sha256", ""),
        )
    if "rollback-download-intent.json" in actual:
        intent = read_json(
            run_dir / "rollback-download-intent.json", "rollback Download intent"
        )
        if (
            intent.get("schema")
            != "s20plus_g986n_b0_rollback_download_intent_v1"
            or intent.get("version") != VERSION
            or intent.get("binding_sha256") != binding_sha256
            or intent.get("source_environment")
            not in {"recovery-adb", "resident-android", "already-download"}
            or intent.get("no_replay") is not True
            or type(intent.get("attempt")) is not int
            or intent.get("attempt") not in {0, 1}
        ):
            raise B0F1Error("rollback Download intent is malformed")
        if intent["source_environment"] == "already-download":
            if (
                intent.get("attempt") != 0
                or intent.get("action")
                != "bind-existing-download-for-mandatory-resident-rollback"
                or intent.get("baseline_sha256") is not None
            ):
                raise B0F1Error("already-Download rollback intent is malformed")
        else:
            if (
                intent.get("attempt") != 1
                or intent.get("action")
                != "adb-reboot-download-for-mandatory-resident-rollback"
                or HEX64_RE.fullmatch(str(intent.get("baseline_sha256"))) is None
                or not isinstance(intent.get("source_receipt"), dict)
            ):
                raise B0F1Error("ADB rollback Download intent is malformed")
    if "rollback-download-result.json" in actual:
        result = read_json(
            run_dir / "rollback-download-result.json", "rollback Download result"
        )
        if (
            result.get("schema")
            != "s20plus_g986n_b0_rollback_download_result_v1"
            or result.get("version") != VERSION
            or result.get("outcome") not in {"dispatched", "uncertain"}
            or result.get("replay_permitted") is not False
        ):
            raise B0F1Error("rollback Download result is malformed")
        if "capture_receipt" in result:
            handle = raw_capture.load_handle(run_dir / "rollback-reboot.capture.json")
            stdout = raw_capture.read_stdout(handle, maximum=MAX_ADB_BYTES)
            stderr = raw_capture.read_stderr(handle, maximum=MAX_ADB_BYTES)
            derived = "dispatched" if raw_dispatch_proved(handle, stderr) else "uncertain"
            if (
                result.get("returncode") != handle.returncode
                or result.get("stdout_sha256") != hashlib.sha256(stdout).hexdigest()
                or result.get("stderr_sha256") != hashlib.sha256(stderr).hexdigest()
                or result.get("outcome") != derived
            ):
                raise B0F1Error("rollback Download result is not raw-derived")
        elif not isinstance(result.get("failure_class"), str):
            raise B0F1Error("rollback Download cut lacks a failure class")
    if "rollback-download-effect-baseline.json" in actual:
        effect_baseline = read_json(
            run_dir / "rollback-download-effect-baseline.json",
            "rollback Download effect baseline",
        )
        rollback_download_intent = read_json(
            run_dir / "rollback-download-intent.json", "rollback Download intent"
        )
        if (
            set(effect_baseline)
            != {
                "schema",
                "version",
                "binding_sha256",
                "intent_sha256",
                "baseline",
                "at",
            }
            or effect_baseline.get("schema")
            != "s20plus_g986n_b0_rollback_download_effect_baseline_v1"
            or effect_baseline.get("version") != VERSION
            or effect_baseline.get("binding_sha256") != binding_sha256
            or effect_baseline.get("intent_sha256") != digest(rollback_download_intent)
            or not isinstance(effect_baseline.get("baseline"), dict)
        ):
            raise B0F1Error("rollback Download effect baseline is malformed")
        validate_download_baseline(
            effect_baseline["baseline"], "rollback Download effect baseline"
        )
    if "rollback-download-arrival.json" in actual:
        arrival = read_json(
            run_dir / "rollback-download-arrival.json", "rollback Download arrival"
        )
        if (
            arrival.get("schema")
            != "s20plus_g986n_b0_rollback_download_arrival_v1"
            or arrival.get("version") != VERSION
            or arrival.get("binding_sha256") != binding_sha256
            or arrival.get("branch") not in {"automatic-adb", "already-download"}
            or (
                arrival.get("branch") == "automatic-adb"
                and (
                    "rollback-download-effect-baseline.json" not in actual
                    or arrival.get("baseline_sha256")
                    != digest(effect_baseline["baseline"])
                )
            )
            or (
                arrival.get("branch") == "already-download"
                and arrival.get("baseline_sha256") is not None
            )
        ):
            raise B0F1Error("rollback Download arrival is malformed")
        _validate_endpoint(arrival.get("endpoint"), "rollback Download endpoint")
    if "physical-rollback-intent.json" in actual:
        arm = read_json(run_dir / "physical-rollback-intent.json", "physical rollback arm")
        core = {key: value for key, value in arm.items() if key != "confirmation_token"}
        if (
            set(arm)
            != {
                "schema",
                "version",
                "binding_sha256",
                "branch",
                "baseline",
                "baseline_sha256",
                "action",
                "action_attempt_maximum",
                "rollback_replay_permitted",
                "expires_unix",
                "at",
                "confirmation_token",
            }
            or arm.get("schema")
            != "s20plus_g986n_b0_physical_rollback_intent_v1"
            or arm.get("version") != VERSION
            or arm.get("binding_sha256") != binding_sha256
            or arm.get("branch") not in {"already-download", "attended-entry-required"}
            or arm.get("action")
            != "one-attended-physical-download-entry-if-not-already-present"
            or type(arm.get("action_attempt_maximum")) is not int
            or arm.get("action_attempt_maximum") != 1
            or arm.get("rollback_replay_permitted") is not False
            or type(arm.get("expires_unix")) is not int
            or (
                arm.get("branch") == "already-download"
                and (
                    arm.get("baseline") is not None
                    or arm.get("baseline_sha256") is not None
                )
            )
            or (
                arm.get("branch") == "attended-entry-required"
                and (
                    not isinstance(arm.get("baseline"), dict)
                    or validate_download_baseline(
                        arm["baseline"], "physical arm baseline"
                    )
                    != arm["baseline"]
                    or arm.get("baseline_sha256") != digest(arm["baseline"])
                )
            )
            or arm.get("confirmation_token") != PHYSICAL_CONFIRM_PREFIX + digest(core)
        ):
            raise B0F1Error("physical rollback arm is malformed")
    if "physical-confirmation-intent.json" in actual:
        confirmation_intent = read_json(
            run_dir / "physical-confirmation-intent.json",
            "physical confirmation intent",
        )
        if (
            set(confirmation_intent)
            != {
                "schema",
                "version",
                "binding_sha256",
                "arm_sha256",
                "confirmation_token_sha256",
                "confirmed_unix",
                "no_replay",
                "at",
            }
            or confirmation_intent.get("schema")
            != "s20plus_g986n_b0_physical_confirmation_intent_v1"
            or confirmation_intent.get("version") != VERSION
            or confirmation_intent.get("binding_sha256") != binding_sha256
            or confirmation_intent.get("arm_sha256") != digest(arm)
            or confirmation_intent.get("confirmation_token_sha256")
            != hashlib.sha256(arm["confirmation_token"].encode()).hexdigest()
            or type(confirmation_intent.get("confirmed_unix")) is not int
            or confirmation_intent.get("confirmed_unix") > arm.get("expires_unix")
            or confirmation_intent.get("no_replay") is not True
        ):
            raise B0F1Error("physical confirmation intent is malformed")
    if "physical-observation-intent.json" in actual:
        observation_intent = read_json(
            run_dir / "physical-observation-intent.json",
            "physical observation intent",
        )
        if (
            set(observation_intent)
            != {
                "schema",
                "version",
                "binding_sha256",
                "baseline_sha256",
                "attempt",
                "no_replay",
                "at",
            }
            or observation_intent.get("schema")
            != "s20plus_g986n_b0_physical_observation_intent_v1"
            or observation_intent.get("version") != VERSION
            or observation_intent.get("binding_sha256") != binding_sha256
            or observation_intent.get("baseline_sha256")
            != arm.get("baseline_sha256")
            or type(observation_intent.get("attempt")) is not int
            or observation_intent.get("attempt") != 1
            or observation_intent.get("no_replay") is not True
        ):
            raise B0F1Error("physical observation intent is malformed")
    if "physical-resume-observation-intent.json" in actual:
        resume_intent = read_json(
            run_dir / "physical-resume-observation-intent.json",
            "physical resume observation intent",
        )
        if (
            set(resume_intent)
            != {
                "schema",
                "version",
                "binding_sha256",
                "baseline_sha256",
                "expires_unix",
                "attempt",
                "mode",
                "no_replay",
                "at",
            }
            or resume_intent.get("schema")
            != "s20plus_g986n_b0_physical_resume_observation_intent_v1"
            or resume_intent.get("version") != VERSION
            or resume_intent.get("binding_sha256") != binding_sha256
            or resume_intent.get("baseline_sha256") != arm.get("baseline_sha256")
            or resume_intent.get("expires_unix") != arm.get("expires_unix")
            or type(resume_intent.get("attempt")) is not int
            or resume_intent.get("attempt") != 1
            or resume_intent.get("mode") != "one-current-read-after-reporting-cut"
            or resume_intent.get("no_replay") is not True
        ):
            raise B0F1Error("physical resume observation intent is malformed")
    if "physical-observation-miss.json" in actual:
        miss = read_json(
            run_dir / "physical-observation-miss.json", "physical observation miss"
        )
        if (
            set(miss)
            != {
                "schema",
                "version",
                "binding_sha256",
                "baseline_sha256",
                "expires_unix",
                "reason",
                "endpoint_count",
                "listing_sha256",
                "no_replay",
                "at",
            }
            or miss.get("schema")
            != "s20plus_g986n_b0_physical_observation_miss_v1"
            or miss.get("version") != VERSION
            or miss.get("binding_sha256") != binding_sha256
            or miss.get("baseline_sha256") != arm.get("baseline_sha256")
            or miss.get("expires_unix") != arm.get("expires_unix")
            or miss.get("reason")
            not in {
                "arm-expired",
                "absent",
                "ambiguous",
                "identity-unproved",
                "bounded-wait-expired",
            }
            or (
                miss.get("endpoint_count") is not None
                and type(miss.get("endpoint_count")) is not int
            )
            or (
                miss.get("listing_sha256") is not None
                and HEX64_RE.fullmatch(str(miss.get("listing_sha256"))) is None
            )
            or miss.get("no_replay") is not True
        ):
            raise B0F1Error("physical observation miss is malformed")
    if "physical-rollback-arrival.json" in actual:
        arrival = read_json(
            run_dir / "physical-rollback-arrival.json", "physical Download arrival"
        )
        if (
            set(arrival)
            != {
                "schema",
                "version",
                "binding_sha256",
                "branch",
                "endpoint",
                "baseline_sha256",
                "arrival_listing_sha256",
                "observed_unix",
                "at",
            }
            or arrival.get("schema")
            != "s20plus_g986n_b0_physical_rollback_arrival_v1"
            or arrival.get("version") != VERSION
            or arrival.get("binding_sha256") != binding_sha256
            or arrival.get("branch")
            not in {
                "already-download-at-arm",
                "reporting-cut-current-arrival",
                "already-download-resumed",
                "attended-entry",
            }
            or HEX64_RE.fullmatch(str(arrival.get("arrival_listing_sha256"))) is None
            or type(arrival.get("observed_unix")) is not int
            or arrival.get("observed_unix") > arm.get("expires_unix")
            or arrival.get("baseline_sha256") != arm.get("baseline_sha256")
        ):
            raise B0F1Error("physical Download arrival is malformed")
        _validate_endpoint(arrival.get("endpoint"), "physical Download endpoint")
    if "rollback-intent.json" in actual:
        rollback_intent = read_json(run_dir / "rollback-intent.json", "rollback intent")
        _validate_transfer_intent(
            rollback_intent,
            "rollback",
            binding_sha256,
        )
        cage_bindings["rollback"] = _validate_process_cage_binding(
            rollback_intent.get("process_cage"), "rollback", binding_sha256
        )
        cage_quiescence["rollback"] = _validate_process_cage_quiescence(
            run_dir,
            actual,
            "rollback",
            binding_sha256,
            cage_bindings["rollback"],
        )
    if "rollback-result.json" in actual:
        _validate_transfer_outcome(
            run_dir,
            read_json(run_dir / "rollback-result.json", "rollback result"),
            "rollback",
            binding_sha256,
        )
    for kind in ("candidate", "rollback"):
        result_name = f"{kind}-result.json"
        if result_name not in actual:
            continue
        result = read_json(run_dir / result_name, f"{kind} result")
        cage_bound = cage_bindings[kind]
        cage_quiescent = cage_quiescence[kind]
        if "receipt" in result:
            process_cage = result["receipt"].get("process_cage")
            stdout_handle = raw_capture.load_handle(
                run_dir / f"{kind}-transfer.capture.json"
            )
            stdout = raw_capture.read_stdout(stdout_handle, maximum=MAX_RAW_BYTES)
            if (
                cage_bound is None
                or cage_quiescent is None
                or not isinstance(process_cage, dict)
                or process_cage
                != {
                    "binding_sha256": digest(cage_bound),
                    "entry_marker": ODIN_CAGE_ENTRY_MARKER.decode("ascii").strip(),
                    "fixed_environment_sha256": digest(ODIN_FIXED_ENV),
                    "quiescence_sha256": digest(cage_quiescent),
                    "empty_and_removed": True,
                }
                or not stdout.startswith(ODIN_CAGE_ENTRY_MARKER)
            ):
                raise B0F1Error(f"{kind} process-cage proof differs")
        else:
            expected_possible_effect = cage_bound is not None
            if (
                result.get("possible_partition_effect") is not expected_possible_effect
                or (
                    result.get("host_process_quiescence_proved") is True
                    and cage_quiescent is None
                    and cage_bound is not None
                )
                or (
                    result.get("host_process_quiescence_proved") is False
                    and cage_bound is None
                )
            ):
                raise B0F1Error(f"{kind} failure process-cage state differs")
    if "final-health.json" in actual:
        final = read_json(run_dir / "final-health.json", "B0 final health")
        expected_final_keys = {
            "schema",
            "version",
            "binding_sha256",
            "health",
            "rollback_transfer_completed",
            "rollback_outcome_proved",
            "resident_boot_healthy",
            "at",
        }
        abort_branch = "candidate-intent.json" not in actual
        expected_binding = None if abort_branch else binding_sha256
        if (
            set(final) != expected_final_keys
            or final.get("schema") != "s20plus_g986n_b0_final_health_v1"
            or final.get("version") != VERSION
            or final.get("binding_sha256") != expected_binding
            or type(final.get("rollback_transfer_completed")) is not bool
            or final.get("rollback_outcome_proved")
            is not final.get("rollback_transfer_completed")
            or final.get("resident_boot_healthy") is not True
        ):
            raise B0F1Error("B0 final health is malformed")
        final_health = _validate_resident_health_receipt(
            run_dir,
            final.get("health"),
            "final resident health",
            "final-root",
        )
        prior_boot_ids = {binding["preflight"]["boot_id_sha256"]}
        if "candidate-observation.json" in actual:
            candidate_observation = read_json(
                run_dir / "candidate-observation.json", "candidate observation"
            )
            candidate_boot = candidate_observation.get("boot_id_sha256")
            if candidate_boot is None:
                candidate_boot = candidate_observation.get("resident_health", {}).get(
                    "boot_id_sha256"
                )
            if candidate_boot is not None:
                prior_boot_ids.add(candidate_boot)
        if final_health["boot_id_sha256"] in prior_boot_ids:
            raise B0F1Error("final resident health reused an earlier boot")
        derived_rollback_completed = False
        if "rollback-result.json" in actual:
            rollback_result = read_json(
                run_dir / "rollback-result.json", "rollback result"
            )
            derived_rollback_completed = (
                rollback_result.get("classification") == "odin_transfer_completed"
            )
        if final["rollback_transfer_completed"] is not derived_rollback_completed:
            raise B0F1Error("final rollback completion is not raw-derived")
    if "terminal.json" in actual:
        terminal = read_json(run_dir / "terminal.json", "B0 terminal")
        abort_branch = "candidate-intent.json" not in actual
        common_keys = {
            "schema",
            "version",
            "binding_sha256",
            "verdict",
            "experiment_pass",
            "candidate_attempts",
            "rollback_attempts",
            "candidate_replay_permitted",
            "rollback_replay_permitted",
            "recovery_partition_reads",
            "recovery_partition_writes",
            "recovery_partition_transfers",
            "other_target_commands",
            "at",
        }
        live_keys = common_keys | {
            "rollback_transfer_completed",
            "rollback_outcome_unproved_but_resident_healthy",
        }
        if (
            set(terminal) != (common_keys if abort_branch else live_keys)
            or terminal.get("schema") != "s20plus_g986n_b0_terminal_v1"
            or terminal.get("version") != VERSION
            or terminal.get("binding_sha256")
            != (None if abort_branch else binding_sha256)
            or terminal.get("candidate_replay_permitted") is not False
            or terminal.get("rollback_replay_permitted") is not False
            or any(
                type(terminal.get(name)) is not int or terminal.get(name) != 0
                for name in (
                    "recovery_partition_reads",
                    "recovery_partition_writes",
                    "recovery_partition_transfers",
                    "other_target_commands",
                )
            )
        ):
            raise B0F1Error("B0 terminal is malformed")
        if abort_branch:
            if (
                terminal.get("verdict") != "ABORTED_PRE_CANDIDATE_RESIDENT_HEALTHY"
                or terminal.get("experiment_pass") is not False
                or terminal.get("candidate_attempts") != 0
                or terminal.get("rollback_attempts") != 0
            ):
                raise B0F1Error("B0 abort terminal is malformed")
        else:
            candidate = (
                read_json(run_dir / "candidate-result.json", "candidate result")
                if "candidate-result.json" in actual
                else read_json(run_dir / "candidate-transfer-cut.json", "candidate cut")
            )
            observation = read_json(
                run_dir / "candidate-observation.json", "candidate observation"
            )
            final = read_json(run_dir / "final-health.json", "final health")
            expected_verdict, expected_pass = derive_terminal_verdict(
                candidate["classification"],
                observation["claim_verdict"],
                final["rollback_transfer_completed"],
            )
            if (
                terminal.get("verdict") != expected_verdict
                or terminal.get("experiment_pass") is not expected_pass
                or terminal.get("candidate_attempts") != 1
                or terminal.get("rollback_attempts") != 1
                or terminal.get("rollback_transfer_completed")
                is not final["rollback_transfer_completed"]
                or terminal.get("rollback_outcome_unproved_but_resident_healthy")
                is final["rollback_transfer_completed"]
            ):
                raise B0F1Error("B0 terminal taxonomy is not derived")


def validate_namespace(run_dir: Path) -> None:
    actual: set[str] = set()
    run_fd = open_direct_directory(run_dir)
    try:
        run_identity = _directory_identity(os.fstat(run_fd))
        with os.scandir(run_fd) as entries:
            for entry in entries:
                metadata = entry.stat(follow_symlinks=False)
                if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                    raise B0F1Error("B0 journal contains an indirect or non-regular node")
                actual.add(entry.name)
    finally:
        os.close(run_fd)
    unknown = {
        name
        for name in actual
        if name not in RUN_NODE_NAMES and REPEATABLE_HEALTH_CAPTURE_RE.fullmatch(name) is None
    }
    if unknown:
        raise B0F1Error("B0 journal contains an unknown node")
    dependencies = {
        "prepared.json": {
            "preflight.json",
            "initial-download-baseline.json",
            "initial-download-intent.json",
            "initial-download-result.json",
            "initial-download-arrival.json",
        },
        "approval.json": {"prepared.json"},
        "candidate-claim-intent.json": {"approval.json", "candidate-adb-baseline.json"},
        "candidate-intent.json": {
            "approval.json",
            "candidate-adb-baseline.json",
            "candidate-claim-intent.json",
        },
        "candidate-cage-quiescent.json": {"candidate-intent.json"},
        "candidate-result.json": {"candidate-intent.json"},
        "candidate-transfer-cut.json": {"candidate-intent.json"},
        "candidate-observation-intent.json": {"candidate-intent.json"},
        "candidate-observation.json": {"candidate-observation-intent.json"},
        "rollback-download-intent.json": {"candidate-observation.json"},
        "rollback-download-effect-baseline.json": {"rollback-download-intent.json"},
        "rollback-download-result.json": {
            "rollback-download-intent.json",
            "rollback-download-effect-baseline.json",
        },
        "rollback-download-observation-intent.json": {
            "rollback-download-result.json",
        },
        "rollback-download-arrival.json": {"candidate-observation.json"},
        "physical-rollback-intent.json": {"candidate-observation.json"},
        "physical-confirmation-intent.json": {"physical-rollback-intent.json"},
        "physical-observation-intent.json": {"physical-confirmation-intent.json"},
        "physical-resume-observation-intent.json": {"physical-observation-intent.json"},
        "physical-observation-miss.json": {"physical-observation-intent.json"},
        "physical-rollback-arrival.json": {"physical-rollback-intent.json"},
        "rollback-intent.json": {
            "candidate-observation.json",
        },
        "rollback-cage-quiescent.json": {"rollback-intent.json"},
        "rollback-result.json": {"rollback-intent.json"},
        "terminal.json": {"final-health.json"},
        "abort-return-intent.json": set(),
        "abort-return-result.json": {
            "abort-return-intent.json",
            "abort-return-cage-quiescent.json",
        },
        "abort-return-cage-quiescent.json": {"abort-return-intent.json"},
    }
    for node, required in dependencies.items():
        if node in actual and not required <= actual:
            raise B0F1Error(f"B0 journal dependency is missing for {node}")
    if "final-health.json" in actual and "rollback-intent.json" not in actual:
        if "candidate-intent.json" in actual:
            raise B0F1Error("B0 final health lacks rollback or pre-candidate provenance")
    if "candidate-result.json" in actual and "candidate-transfer-cut.json" in actual:
        raise B0F1Error("B0 candidate has two outcome records")
    if "rollback-intent.json" in actual and "rollback-download-arrival.json" not in actual and "physical-rollback-arrival.json" not in actual:
        raise B0F1Error("rollback intent has no bound Download arrival")
    if (
        "rollback-intent.json" in actual
        and "physical-rollback-arrival.json" in actual
        and "rollback-download-arrival.json" not in actual
        and "physical-confirmation-intent.json" not in actual
    ):
        raise B0F1Error("physical rollback lacks consumed confirmation")
    if (
        "physical-observation-miss.json" in actual
        and "physical-rollback-arrival.json" in actual
    ):
        raise B0F1Error("physical observation has both miss and arrival")
    validate_critical_records(run_dir, actual)
    if run_identity != _directory_identity(os.stat(run_dir, follow_symlinks=False)):
        raise B0F1Error("B0 run directory changed during validation")


def guard_value(run_dir: Path) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_boot_recovery_canary_b0_guard_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "candidate_sha256": CANDIDATE_AP_SHA256,
        "unresolved": True,
    }


def acquire_guard(run_dir: Path) -> None:
    payload = canonical_bytes(guard_value(run_dir))
    parent_fd = open_direct_directory(SHARED_GUARD.parent)
    try:
        parent_identity = _directory_identity(os.fstat(parent_fd))
        current_parent = os.stat(SHARED_GUARD.parent, follow_symlinks=False)
        if parent_identity != _directory_identity(current_parent):
            raise B0F1Error("shared guard parent changed before allocation")
        _atomic_publish_at(
            parent_fd, SHARED_GUARD.name, payload, 0o400, "shared guard"
        )
    except FileExistsError as exc:
        raise B0F1Error("another S20+ action remains unresolved") from exc
    finally:
        os.close(parent_fd)


def _read_guard_at(parent_fd: int) -> tuple[dict[str, Any], tuple[int, ...]]:
    try:
        descriptor = os.open(
            SHARED_GUARD.name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
    except OSError as exc:
        raise B0F1Error("shared B0 guard is unavailable") from exc
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or stat.S_IMODE(metadata.st_mode) != 0o400
            or metadata.st_size > MAX_JSON_BYTES
        ):
            raise B0F1Error("shared B0 guard is indirect or oversized")
        payload = bytearray()
        while len(payload) < metadata.st_size:
            block = os.read(descriptor, metadata.st_size - len(payload))
            if not block:
                break
            payload.extend(block)
        if len(payload) != metadata.st_size or os.read(descriptor, 1):
            raise B0F1Error("shared B0 guard changed during read")
        identity = (
            metadata.st_dev,
            metadata.st_ino,
            metadata.st_mode,
            metadata.st_nlink,
            metadata.st_size,
            metadata.st_mtime_ns,
            metadata.st_ctime_ns,
        )
        return _decode_canonical_json(bytes(payload), "shared B0 guard"), identity
    finally:
        os.close(descriptor)


def guard_present() -> bool:
    parent_fd = open_direct_directory(SHARED_GUARD.parent)
    try:
        try:
            os.stat(SHARED_GUARD.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return False
        return True
    finally:
        os.close(parent_fd)


def require_guard(run_dir: Path) -> None:
    parent_fd = open_direct_directory(SHARED_GUARD.parent)
    try:
        value, _identity = _read_guard_at(parent_fd)
        if value != guard_value(run_dir):
            raise B0F1Error("shared B0 guard differs")
    finally:
        os.close(parent_fd)


def release_guard(run_dir: Path) -> None:
    parent_fd = open_direct_directory(SHARED_GUARD.parent)
    try:
        parent_identity = _directory_identity(os.fstat(parent_fd))
        value, opened_identity = _read_guard_at(parent_fd)
        if value != guard_value(run_dir):
            raise B0F1Error("foreign shared guard will not be removed")
        current = os.stat(
            SHARED_GUARD.name, dir_fd=parent_fd, follow_symlinks=False
        )
        current_identity = (
            current.st_dev,
            current.st_ino,
            current.st_mode,
            current.st_nlink,
            current.st_size,
            current.st_mtime_ns,
            current.st_ctime_ns,
        )
        if opened_identity != current_identity:
            raise B0F1Error("shared guard changed before release")
        if parent_identity != _directory_identity(os.fstat(parent_fd)):
            raise B0F1Error("shared guard parent changed before release")
        os.unlink(SHARED_GUARD.name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def claim_path() -> Path:
    return CLAIM_ROOT / f"{CANDIDATE_AP_SHA256}.json"


def candidate_claim_present() -> bool:
    ensure_private_roots()
    parent_fd = open_direct_directory(CLAIM_ROOT)
    try:
        try:
            os.stat(claim_path().name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return False
        return True
    finally:
        os.close(parent_fd)


def _candidate_claim_intent(
    run_dir: Path, binding_sha256: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = run_dir / "candidate-claim-intent.json"
    if os.path.lexists(path):
        intent = read_json(path, "candidate claim intent")
        claim = intent.get("claim")
        if (
            set(intent)
            != {
                "schema",
                "version",
                "run_dir",
                "binding_sha256",
                "claim",
                "claim_sha256",
                "no_replay",
                "at",
            }
            or intent.get("schema")
            != "s20plus_g986n_b0_global_candidate_claim_intent_v1"
            or intent.get("version") != VERSION
            or intent.get("run_dir") != str(run_dir)
            or intent.get("binding_sha256") != binding_sha256
            or not isinstance(claim, dict)
            or set(claim)
            != {
                "schema",
                "version",
                "run_dir",
                "binding_sha256",
                "candidate_ap_sha256",
                "state",
                "candidate_replay_permitted",
                "at",
            }
            or claim.get("schema")
            != "s20plus_g986n_b0_global_candidate_consumed_v1"
            or claim.get("version") != VERSION
            or claim.get("run_dir") != str(run_dir)
            or claim.get("binding_sha256") != binding_sha256
            or claim.get("candidate_ap_sha256") != CANDIDATE_AP_SHA256
            or claim.get("state") != "uncertain-consumed-before-backend"
            or claim.get("candidate_replay_permitted") is not False
            or intent.get("claim_sha256") != digest(claim)
            or intent.get("no_replay") is not True
        ):
            raise B0F1Error("candidate claim intent is malformed")
        return intent, claim
    claim = {
        "schema": "s20plus_g986n_b0_global_candidate_consumed_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "binding_sha256": binding_sha256,
        "candidate_ap_sha256": CANDIDATE_AP_SHA256,
        "state": "uncertain-consumed-before-backend",
        "candidate_replay_permitted": False,
        "at": utc_now(),
    }
    intent = {
        "schema": "s20plus_g986n_b0_global_candidate_claim_intent_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "binding_sha256": binding_sha256,
        "claim": claim,
        "claim_sha256": digest(claim),
        "no_replay": True,
        "at": utc_now(),
    }
    durable_json(path, intent)
    return intent, claim


def consume_candidate_globally(run_dir: Path, binding_sha256: str) -> dict[str, Any]:
    _intent, value = _candidate_claim_intent(run_dir, binding_sha256)
    payload = canonical_bytes(value)
    ensure_private_roots()
    parent_fd = open_direct_directory(CLAIM_ROOT)
    try:
        _atomic_publish_at(
            parent_fd,
            claim_path().name,
            payload,
            0o400,
            "global candidate claim",
        )
    finally:
        os.close(parent_fd)
    return value


def require_candidate_claim(run_dir: Path, binding_sha256: str) -> dict[str, Any]:
    _intent, expected = _candidate_claim_intent(run_dir, binding_sha256)
    expected_payload = canonical_bytes(expected)
    ensure_private_roots()
    parent_fd = open_direct_directory(CLAIM_ROOT)
    try:
        descriptor = os.open(
            claim_path().name,
            os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=parent_fd,
        )
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_nlink != 1
                or stat.S_IMODE(metadata.st_mode) != 0o400
                or metadata.st_size > MAX_JSON_BYTES
            ):
                raise B0F1Error("global B0 candidate claim is indirect")
            payload = bytearray()
            while len(payload) < metadata.st_size:
                block = os.read(descriptor, metadata.st_size - len(payload))
                if not block:
                    break
                payload.extend(block)
            if len(payload) != metadata.st_size or os.read(descriptor, 1):
                raise B0F1Error("global B0 candidate claim changed")
        finally:
            os.close(descriptor)
    finally:
        os.close(parent_fd)
    actual_payload = bytes(payload)
    if actual_payload != expected_payload:
        if len(actual_payload) < len(expected_payload) and expected_payload.startswith(
            actual_payload
        ):
            return {
                **expected,
                "state": "uncertain-partial-global-claim",
                "candidate_replay_permitted": False,
            }
        raise B0F1Error("global B0 candidate claim differs from its intent")
    value = _decode_canonical_json(actual_payload, "global B0 candidate claim")
    if (
        value.get("run_dir") != str(run_dir)
        or value.get("binding_sha256") != binding_sha256
        or value.get("candidate_ap_sha256") != CANDIDATE_AP_SHA256
        or value.get("state") != "uncertain-consumed-before-backend"
        or value.get("candidate_replay_permitted") is not False
    ):
        raise B0F1Error("global B0 candidate claim differs")
    return value


def prepared_binding(
    run_dir: Path,
    preflight: dict[str, Any],
    endpoint: dict[str, Any],
    closure: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "s20plus_g986n_boot_recovery_canary_b0_binding_v1",
        "version": VERSION,
        "run_dir": str(run_dir),
        "target": dict(TARGET),
        "preflight": preflight,
        "endpoint": endpoint,
        "closure": closure,
        "candidate_attempt_maximum": 1,
        "rollback_attempt_maximum": 1,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
        "rollback_mandatory_after_candidate_intent": True,
        "recovery_partition_access": False,
        "expires_unix": int(time.time()) + APPROVAL_LIFETIME_SECONDS,
    }


def adb_reboot_download_capture(
    run_dir: Path, serial: str, capture_name: str
) -> dict[str, Any]:
    with transport.pin_regular_file(
        ADB,
        label="ADB",
        expected_size=ADB_SIZE,
        expected_sha256=ADB_SHA256,
    ) as adb:
        handle = raw_capture.acquire_command(
            [str(adb.path), "-s", serial, "reboot", "download"],
            run_dir,
            capture_name,
            timeout=20,
            stdout_maximum=MAX_ADB_BYTES,
            stderr_maximum=MAX_ADB_BYTES,
            stdout_name=f"{capture_name}.stdout",
            stderr_name=f"{capture_name}.stderr",
        )
        transport.revalidate_pinned_path(adb)
    stdout = raw_capture.read_stdout(handle, maximum=MAX_ADB_BYTES)
    stderr = raw_capture.read_stderr(handle, maximum=MAX_ADB_BYTES)
    return {
        "returncode": handle.returncode,
        "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
        "capture_receipt": {
            "path": str(handle.receipt_path),
            "size": handle.receipt_path.stat().st_size,
            "sha256": hashlib.sha256(handle.receipt_path.read_bytes()).hexdigest(),
        },
        "outcome": "dispatched" if raw_dispatch_proved(handle, stderr) else "uncertain",
    }


def prepare(requested: Path | None) -> Path:
    require_active()
    if candidate_claim_present():
        raise B0F1Error("the exact B0 candidate was already consumed")
    closure = validate_host_closure()
    run_dir = allocate_run_dir(requested)
    acquire_guard(run_dir)
    try:
        preflight, serial = resident_health_once(run_dir, "preflight-root")
        durable_json(
            run_dir / "preflight.json",
            {
                "schema": "s20plus_g986n_b0_preflight_v1",
                "version": VERSION,
                **preflight,
            },
        )
        baseline = download_baseline()
        durable_json(run_dir / "initial-download-baseline.json", baseline)
        intent = {
            "schema": "s20plus_g986n_b0_initial_download_intent_v1",
            "version": VERSION,
            "source_identity": {
                "serial_sha256": preflight["serial_sha256"],
                "topology_sha256": preflight["topology_sha256"],
                "boot_id_sha256": preflight["boot_id_sha256"],
            },
            "baseline_sha256": digest(baseline),
            "action": "adb-reboot-download-before-approval",
            "attempt": 1,
            "no_replay": True,
            "at": utc_now(),
        }
        durable_json(run_dir / "initial-download-intent.json", intent)
        try:
            captured = adb_reboot_download_capture(run_dir, serial, "initial-reboot")
            result = {
                "schema": "s20plus_g986n_b0_initial_download_result_v1",
                "version": VERSION,
                **captured,
                "replay_permitted": False,
                "at": utc_now(),
            }
        except Exception as exc:
            result = {
                "schema": "s20plus_g986n_b0_initial_download_result_v1",
                "version": VERSION,
                "outcome": "uncertain",
                "failure_class": type(exc).__name__,
                "replay_permitted": False,
                "at": utc_now(),
            }
        durable_json(run_dir / "initial-download-result.json", result)
        arrival = wait_download(baseline)
        if arrival is None:
            raise B0F1Error(f"initial Download arrival is unproved; recover run {run_dir}")
        durable_json(
            run_dir / "initial-download-arrival.json",
            {
                "schema": "s20plus_g986n_b0_initial_download_arrival_v1",
                "version": VERSION,
                **arrival,
            },
        )
        binding = prepared_binding(run_dir, preflight, arrival["endpoint"], closure)
        binding_sha256 = digest(binding)
        durable_json(
            run_dir / "prepared.json",
            {
                "schema": "s20plus_g986n_b0_prepared_v1",
                "version": VERSION,
                "binding": binding,
                "binding_sha256": binding_sha256,
                "approval_token": APPROVAL_PREFIX + binding_sha256,
                "at": utc_now(),
            },
        )
        return run_dir
    except Exception:
        if not os.path.lexists(run_dir / "initial-download-intent.json"):
            release_guard(run_dir)
        raise


def validate_prepared_history(
    run_dir: Path, binding: dict[str, Any]
) -> None:
    preflight_record = read_json(run_dir / "preflight.json", "B0 preflight")
    if (
        preflight_record.get("schema") != "s20plus_g986n_b0_preflight_v1"
        or preflight_record.get("version") != VERSION
        or {
            key: value
            for key, value in preflight_record.items()
            if key not in {"schema", "version"}
        }
        != binding["preflight"]
    ):
        raise B0F1Error("prepared preflight history differs")
    baseline = validate_download_baseline(
        read_json(run_dir / "initial-download-baseline.json", "initial baseline"),
        "initial Download baseline",
    )
    intent = read_json(run_dir / "initial-download-intent.json", "initial Download intent")
    expected_identity = {
        "serial_sha256": binding["preflight"]["serial_sha256"],
        "topology_sha256": binding["preflight"]["topology_sha256"],
        "boot_id_sha256": binding["preflight"]["boot_id_sha256"],
    }
    if (
        set(intent)
        != {
            "schema",
            "version",
            "source_identity",
            "baseline_sha256",
            "action",
            "attempt",
            "no_replay",
            "at",
        }
        or intent.get("schema") != "s20plus_g986n_b0_initial_download_intent_v1"
        or intent.get("version") != VERSION
        or intent.get("source_identity") != expected_identity
        or intent.get("baseline_sha256") != digest(baseline)
        or intent.get("action") != "adb-reboot-download-before-approval"
        or type(intent.get("attempt")) is not int
        or intent.get("attempt") != 1
        or intent.get("no_replay") is not True
    ):
        raise B0F1Error("initial Download intent is malformed")
    result = read_json(run_dir / "initial-download-result.json", "initial Download result")
    if (
        result.get("schema") != "s20plus_g986n_b0_initial_download_result_v1"
        or result.get("version") != VERSION
        or result.get("outcome") not in {"dispatched", "uncertain"}
        or result.get("replay_permitted") is not False
    ):
        raise B0F1Error("initial Download result is malformed")
    if "capture_receipt" in result:
        handle = raw_capture.load_handle(run_dir / "initial-reboot.capture.json")
        stdout = raw_capture.read_stdout(handle, maximum=MAX_ADB_BYTES)
        stderr = raw_capture.read_stderr(handle, maximum=MAX_ADB_BYTES)
        derived = "dispatched" if raw_dispatch_proved(handle, stderr) else "uncertain"
        if (
            result.get("returncode") != handle.returncode
            or result.get("stdout_sha256") != hashlib.sha256(stdout).hexdigest()
            or result.get("stderr_sha256") != hashlib.sha256(stderr).hexdigest()
            or result.get("outcome") != derived
        ):
            raise B0F1Error("initial Download result is not raw-derived")
    elif not isinstance(result.get("failure_class"), str):
        raise B0F1Error("initial Download failure lacks a class")
    arrival = read_json(run_dir / "initial-download-arrival.json", "initial Download arrival")
    if (
        arrival.get("schema") != "s20plus_g986n_b0_initial_download_arrival_v1"
        or arrival.get("version") != VERSION
        or arrival.get("baseline_sha256") != digest(baseline)
        or arrival.get("endpoint") != binding["endpoint"]
        or HEX64_RE.fullmatch(str(arrival.get("arrival_listing_sha256"))) is None
    ):
        raise B0F1Error("initial Download arrival is malformed")


def read_prepared(run_dir: Path, *, phase: str) -> dict[str, Any]:
    run_dir = validate_run_dir(run_dir)
    require_guard(run_dir)
    value = read_json(run_dir / "prepared.json", "B0 prepared binding")
    binding = value.get("binding")
    expected_binding_keys = {
        "schema",
        "version",
        "run_dir",
        "target",
        "preflight",
        "endpoint",
        "closure",
        "candidate_attempt_maximum",
        "rollback_attempt_maximum",
        "candidate_replay_permitted",
        "rollback_replay_permitted",
        "rollback_mandatory_after_candidate_intent",
        "recovery_partition_access",
        "expires_unix",
    }
    if (
        set(value) != {
            "schema",
            "version",
            "binding",
            "binding_sha256",
            "approval_token",
            "at",
        }
        or
        value.get("schema") != "s20plus_g986n_b0_prepared_v1"
        or value.get("version") != VERSION
        or not isinstance(binding, dict)
        or value.get("binding_sha256") != digest(binding)
        or value.get("approval_token") != APPROVAL_PREFIX + value["binding_sha256"]
        or binding.get("run_dir") != str(run_dir)
        or binding.get("target") != TARGET
        or set(binding) != expected_binding_keys
        or binding.get("schema")
        != "s20plus_g986n_boot_recovery_canary_b0_binding_v1"
        or binding.get("version") != VERSION
        or type(binding.get("candidate_attempt_maximum")) is not int
        or binding.get("candidate_attempt_maximum") != 1
        or type(binding.get("rollback_attempt_maximum")) is not int
        or binding.get("rollback_attempt_maximum") != 1
        or binding.get("candidate_replay_permitted") is not False
        or binding.get("rollback_replay_permitted") is not False
        or binding.get("rollback_mandatory_after_candidate_intent") is not True
        or binding.get("recovery_partition_access") is not False
        or type(binding.get("expires_unix")) is not int
    ):
        raise B0F1Error("B0 prepared binding is malformed")
    _validate_resident_health_receipt(
        run_dir,
        binding.get("preflight"),
        "prepared resident preflight",
        "preflight-root",
    )
    _validate_endpoint(binding.get("endpoint"), "prepared Download endpoint")
    validate_prepared_history(run_dir, binding)
    stored_closure = binding.get("closure")
    if (
        not isinstance(stored_closure, dict)
        or stored_closure.get("candidate", {}).get("ap", {}).get("sha256")
        != CANDIDATE_AP_SHA256
        or stored_closure.get("rollback", {}).get("ap", {}).get("sha256")
        != ROLLBACK_AP_SHA256
        or stored_closure.get("manifest", {}).get("sha256") != MANIFEST_SHA256
        or stored_closure.get("builder", {}).get("sha256") != BUILDER_SHA256
        or stored_closure.get("runner", {}).get("normalized_sha256")
        != EXPECTED_REVIEWED_NORMALIZED_SHA256
    ):
        raise B0F1Error("stored B0 closure is malformed")
    if phase == "candidate":
        if validate_host_closure() != binding.get("closure"):
            raise B0F1Error("B0 candidate closure drifted")
    elif phase == "rollback":
        validate_rollback_closure()
    elif phase == "health":
        validate_health_closure()
    else:
        raise B0F1Error("unknown B0 prepared phase")
    if os.path.lexists(run_dir / "candidate-intent.json"):
        require_candidate_claim(run_dir, value["binding_sha256"])
    return value


def classify_odin_output(returncode: int | None, stdout: bytes, stderr: bytes) -> str:
    if type(returncode) is not int:
        return "odin_device_session_failure_or_unknown"
    output = stdout + b"\n" + stderr
    session_markers = (
        b"Setup Connection",
        b"initializeConnection",
        b"Receive PIT Info",
        b"Upload Binaries",
        b"Close Connection",
    )
    if b"Fail parse" in output and not any(marker in output for marker in session_markers):
        return "odin_local_parse_failure"
    completed = (
        b"Setup Connection",
        b"Upload Binaries",
        b"boot.img.lz4",
        b"100%",
        b"Close Connection",
    )
    if returncode == 0 and all(marker in output for marker in completed):
        return "odin_transfer_completed"
    return "odin_device_session_failure_or_unknown"


def classify_odin_capture(
    handle: raw_capture.RawCaptureHandle, stdout: bytes, stderr: bytes
) -> str:
    if (
        type(handle.returncode) is not int
        or handle.producer_error_type is not None
        or handle.timed_out
        or handle.output_exceeded
    ):
        return "odin_device_session_failure_or_unknown"
    return classify_odin_output(handle.returncode, stdout, stderr)


def endpoint_ctime_only_change(receipt: dict[str, Any]) -> bool:
    before = receipt.get("endpoint_pre_identity")
    after = receipt.get("endpoint_post_identity")
    return (
        receipt.get("endpoint_post_state") == "changed"
        and isinstance(before, list)
        and isinstance(after, list)
        and len(before) == 4
        and len(after) == 4
        and all(type(item) is int for item in before + after)
        and before[:3] == after[:3]
        and before[3] != after[3]
    )


def _read_bounded_host_file(path: Path, maximum: int, label: str) -> bytes:
    descriptor = os.open(
        path,
        os.O_RDONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        payload = os.read(descriptor, maximum + 1)
        if len(payload) > maximum or os.read(descriptor, 1):
            raise ProcessCageError(f"{label} exceeds its bound")
        return payload
    finally:
        os.close(descriptor)


def _write_host_control(path: Path, payload: bytes, label: str) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
    except OSError as exc:
        raise ProcessCageError(f"{label} write failed") from exc
    finally:
        os.close(descriptor)


def _host_boot_id() -> str:
    try:
        value = _read_bounded_host_file(
            Path("/proc/sys/kernel/random/boot_id"), 128, "host boot ID"
        ).decode("ascii", "strict").strip()
    except (OSError, UnicodeError) as exc:
        raise ProcessCageError("host boot ID is unavailable") from exc
    if BOOT_ID_RE.fullmatch(value) is None:
        raise ProcessCageError("host boot ID is malformed")
    return value


def _current_cgroup_parent() -> Path:
    try:
        text = _read_bounded_host_file(
            Path("/proc/self/cgroup"), 4096, "host cgroup membership"
        ).decode("utf-8", "strict")
    except (OSError, UnicodeError) as exc:
        raise ProcessCageError("host cgroup membership is unavailable") from exc
    lines = text.splitlines()
    if len(lines) != 1 or not lines[0].startswith("0::/"):
        raise ProcessCageError("host is not in one cgroup-v2 domain")
    relative = Path(lines[0][3:])
    if not relative.is_absolute() or ".." in relative.parts:
        raise ProcessCageError("host cgroup path is non-canonical")
    parent = Path("/sys/fs/cgroup").joinpath(*relative.parts[1:])
    metadata = os.stat(parent, follow_symlinks=False)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or parent.resolve(strict=True) != parent
    ):
        raise ProcessCageError("host cgroup parent is indirect or unowned")
    return parent


def _cgroup_identity(path: Path) -> list[int]:
    metadata = os.stat(path, follow_symlinks=False)
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid():
        raise ProcessCageError("process cage is indirect or unowned")
    return [
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
    ]


def _cgroup_populated(path: Path) -> bool:
    try:
        events = _read_bounded_host_file(
            path / "cgroup.events", 4096, "process-cage events"
        ).decode("ascii", "strict")
        procs = _read_bounded_host_file(
            path / "cgroup.procs", 65536, "process-cage membership"
        ).decode("ascii", "strict")
    except (OSError, UnicodeError) as exc:
        raise ProcessCageError("process-cage state is unavailable") from exc
    parsed: dict[str, str] = {}
    for line in events.splitlines():
        key, separator, value = line.partition(" ")
        if separator != " " or key in parsed or not key or not value:
            raise ProcessCageError("process-cage events are malformed")
        parsed[key] = value
    if parsed.get("populated") not in {"0", "1"}:
        raise ProcessCageError("process-cage populated state is malformed")
    pids = [line for line in procs.splitlines() if line]
    if any(not value.isascii() or not value.isdecimal() for value in pids):
        raise ProcessCageError("process-cage PID list is malformed")
    if parsed["populated"] == "0" and pids:
        raise ProcessCageError("empty process cage still lists direct PIDs")
    return parsed["populated"] == "1"


def _quiesce_transient_cgroup(cage: Path) -> None:
    if _cgroup_populated(cage):
        _write_host_control(cage / "cgroup.kill", b"1\n", "transient cgroup kill")
    deadline = time.monotonic() + 10
    while _cgroup_populated(cage):
        if time.monotonic() >= deadline:
            raise ProcessCageError("transient Odin cgroup did not become empty")
        time.sleep(0.05)
    try:
        os.rmdir(cage)
    except OSError as exc:
        raise ProcessCageError("transient Odin cgroup could not be removed") from exc


def _remove_stale_bounded_cgroup(cage: Path, timeout: float, label: str) -> None:
    _cgroup_identity(cage)
    deadline = time.monotonic() + timeout
    while _cgroup_populated(cage) and time.monotonic() < deadline:
        time.sleep(0.05)
    if _cgroup_populated(cage):
        raise ProcessCageError(f"{label} is still populated")
    try:
        os.rmdir(cage)
    except OSError as exc:
        raise ProcessCageError(f"{label} could not be removed") from exc


def _bounded_odin_listing() -> str:
    ensure_private_roots()
    parent = _current_cgroup_parent()
    cage = parent / "s20plus-b0-odin-list"
    if os.path.lexists(cage):
        _remove_stale_bounded_cgroup(cage, 11, "earlier Odin listing cgroup")
    os.mkdir(cage, 0o700)
    if _cgroup_populated(cage):
        raise ProcessCageError("new Odin listing cgroup is not empty")
    handle: raw_capture.RawCaptureHandle | None = None
    stdout = b""
    stderr = b""
    try:
        with transport.pin_regular_file(
            ODIN,
            label="Odin4",
            expected_size=ODIN_SIZE,
            expected_sha256=ODIN_SHA256,
        ) as odin, transport.pin_regular_file(
            DASH,
            label="process-cage shell",
            expected_size=DASH_SIZE,
            expected_sha256=DASH_SHA256,
        ) as cage_shell, transport.pin_regular_file(
            CAGE_SLEEP,
            label="Odin listing watchdog",
            expected_size=CAGE_SLEEP_SIZE,
            expected_sha256=CAGE_SLEEP_SHA256,
        ) as watchdog, tempfile.TemporaryDirectory(
            prefix=".odin-list-", dir=RUN_ROOT
        ) as temporary:
            transport.revalidate_pinned_path(odin)
            transport.revalidate_pinned_path(cage_shell)
            transport.revalidate_pinned_path(watchdog)
            handle = raw_capture.acquire_command(
                [
                    str(cage_shell.path),
                    "-c",
                    ODIN_CAGE_ENTRY_SCRIPT,
                    "s20plus-b0-odin-list-cage",
                    str(cage),
                    str(watchdog.path),
                    "timeout",
                    "-s",
                    "KILL",
                    "10",
                    str(odin.path),
                    "-l",
                ],
                Path(temporary),
                "odin-list",
                timeout=12,
                stdout_maximum=MAX_ADB_BYTES,
                stderr_maximum=MAX_ADB_BYTES,
                env=ODIN_FIXED_ENV,
            )
            stdout = raw_capture.read_stdout(handle, maximum=MAX_ADB_BYTES)
            stderr = raw_capture.read_stderr(handle, maximum=MAX_ADB_BYTES)
            transport.revalidate_pinned_path(odin)
            transport.revalidate_pinned_path(cage_shell)
            transport.revalidate_pinned_path(watchdog)
    finally:
        if os.path.lexists(cage):
            _quiesce_transient_cgroup(cage)
    if handle is None or not raw_dispatch_proved(handle, stderr):
        raise B0F1Error("Odin enumeration failed")
    if not stdout.startswith(ODIN_CAGE_ENTRY_MARKER):
        raise ProcessCageError("Odin listing did not prove process-cage entry")
    try:
        return stdout[len(ODIN_CAGE_ENTRY_MARKER) :].decode("utf-8", "strict")
    except UnicodeError as exc:
        raise B0F1Error("Odin enumeration output is malformed") from exc


def validate_process_cage_capability() -> dict[str, Any]:
    ensure_private_roots()
    parent = _current_cgroup_parent()
    cage = parent / "s20plus-b0-cage-capability"
    if os.path.lexists(cage):
        _remove_stale_bounded_cgroup(
            cage, 4, "process-cage capability probe"
        )
    os.mkdir(cage, 0o700)
    handle: raw_capture.RawCaptureHandle | None = None
    stdout = b""
    try:
        with transport.pin_regular_file(
            DASH,
            label="process-cage shell",
            expected_size=DASH_SIZE,
            expected_sha256=DASH_SHA256,
        ) as cage_shell, transport.pin_regular_file(
            CAGE_SLEEP,
            label="process-cage sleeper",
            expected_size=CAGE_SLEEP_SIZE,
            expected_sha256=CAGE_SLEEP_SHA256,
        ) as cage_sleep, tempfile.TemporaryDirectory(
            prefix=".cage-capability-", dir=RUN_ROOT
        ) as temporary:
            handle = raw_capture.acquire_command(
                [
                    str(cage_shell.path),
                    "-c",
                    CAGE_CAPABILITY_SCRIPT,
                    "s20plus-b0-cage-capability",
                    str(cage),
                    str(cage_sleep.path),
                ],
                Path(temporary),
                "cage-capability",
                timeout=0.1,
                stdout_maximum=4096,
                stderr_maximum=4096,
                env=ODIN_FIXED_ENV,
            )
            stdout = raw_capture.read_stdout(handle, maximum=4096)
            transport.revalidate_pinned_path(cage_shell)
            transport.revalidate_pinned_path(cage_sleep)
        if (
            handle is None
            or not handle.timed_out
            or not stdout.startswith(ODIN_CAGE_ENTRY_MARKER)
            or not _cgroup_populated(cage)
        ):
            raise ProcessCageError("process-cage descendant survival probe differed")
    finally:
        if os.path.lexists(cage):
            _quiesce_transient_cgroup(cage)
    return {
        "schema": "s20plus_g986n_b0_process_cage_capability_v1",
        "cgroup_version": 2,
        "fixed_environment_sha256": digest(ODIN_FIXED_ENV),
        "descendant_survived_direct_parent_timeout": True,
        "cgroup_kill_emptied_descendants": True,
        "cgroup_removed": True,
    }


def process_cage_quiescent_path(run_dir: Path, kind: str) -> Path:
    if kind not in {"candidate", "rollback", "abort-return"}:
        raise ProcessCageError("unknown process-cage transfer kind")
    return run_dir / f"{kind}-cage-quiescent.json"


def prepare_process_cage(
    run_dir: Path, kind: str, binding_sha256: str
) -> tuple[Path, dict[str, Any]]:
    quiescent_path = process_cage_quiescent_path(run_dir, kind)
    if os.path.lexists(quiescent_path):
        raise ProcessCageError("process cage was already consumed")
    parent = _current_cgroup_parent()
    parent_identity = _cgroup_identity(parent)
    cage = parent / f"s20plus-b0-{kind}-{binding_sha256[:20]}"
    if os.path.lexists(cage):
        _cgroup_identity(cage)
        if _cgroup_populated(cage):
            raise ProcessCageError("unbound process-cage path is populated")
        os.rmdir(cage)
    try:
        os.mkdir(cage, 0o700)
    except OSError as exc:
        raise ProcessCageError("process-cage creation failed") from exc
    if _cgroup_identity(parent) != parent_identity or _cgroup_populated(cage):
        raise ProcessCageError("new process cage or parent differs")
    bound = {
        "schema": "s20plus_g986n_b0_process_cage_binding_v1",
        "version": VERSION,
        "kind": kind,
        "binding_sha256": binding_sha256,
        "parent": str(parent),
        "parent_identity": parent_identity,
        "cage": str(cage),
        "host_boot_id_sha256": hashlib.sha256(_host_boot_id().encode()).hexdigest(),
        "cage_identity": _cgroup_identity(cage),
        "empty_before_backend": True,
        "at": utc_now(),
    }
    return cage, bound


def quiesce_process_cage(
    run_dir: Path, kind: str, binding_sha256: str
) -> dict[str, Any] | None:
    quiescent_path = process_cage_quiescent_path(run_dir, kind)
    if os.path.lexists(quiescent_path):
        return read_json(quiescent_path, f"{kind} process-cage quiescence")
    intent_path = run_dir / (
        "abort-return-intent.json" if kind == "abort-return" else f"{kind}-intent.json"
    )
    if not os.path.lexists(intent_path):
        return None
    intent = read_json(intent_path, f"{kind} effect intent")
    bound = intent.get("process_cage")
    if (
        not isinstance(bound, dict)
        or bound.get("binding_sha256") != binding_sha256
    ):
        raise ProcessCageError("process-cage journal binding differs")
    cage = Path(bound["cage"])
    killed = False
    absent = not os.path.lexists(cage)
    if not absent:
        if _cgroup_identity(cage) != bound.get("cage_identity"):
            raise ProcessCageError("process-cage path identity changed")
        if _cgroup_populated(cage):
            _write_host_control(cage / "cgroup.kill", b"1\n", "process-cage kill")
            killed = True
        deadline = time.monotonic() + 10
        while _cgroup_populated(cage):
            if time.monotonic() >= deadline:
                raise ProcessCageError("process cage did not become empty")
            time.sleep(0.05)
        try:
            os.rmdir(cage)
        except OSError as exc:
            raise ProcessCageError("empty process cage could not be removed") from exc
    value = {
        "schema": "s20plus_g986n_b0_process_cage_quiescent_v1",
        "version": VERSION,
        "kind": kind,
        "binding_sha256": binding_sha256,
        "cage_binding_sha256": digest(bound),
        "kill_requested": killed,
        "cage_absent_before_check": absent,
        "empty_and_removed": True,
        "at": utc_now(),
    }
    durable_json(quiescent_path, value)
    return value


def preflight_odin_dispatch(
    run_dir: Path,
    kind: str,
    path: Path,
    size: int,
    sha256: str,
    endpoint: dict[str, Any],
    binding_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    current = identify_download()
    if not same_download_session(current, endpoint):
        raise B0F1Error("Download endpoint changed before transfer intent")
    with transport.pin_regular_file(
        ODIN,
        label="Odin4",
        expected_size=ODIN_SIZE,
        expected_sha256=ODIN_SHA256,
    ) as odin, transport.pin_boot_only_ap(
        path,
        label=kind,
        expected_size=size,
        expected_sha256=sha256,
        require_deterministic_metadata=True,
    ) as ap, transport.pin_regular_file(
        DASH,
        label="process-cage shell",
        expected_size=DASH_SIZE,
        expected_sha256=DASH_SHA256,
    ) as cage_shell:
        transport.build_odin_boot_only_command(odin.path, ap.path, current["device"])
        transport.revalidate_pinned_path(odin)
        transport.revalidate_pinned_path(ap)
        transport.revalidate_pinned_path(cage_shell)
        if endpoint_stat(current["device"]) != tuple(current["endpoint_identity"]):
            raise B0F1Error("Download endpoint changed during transfer preflight")
    _cage, cage_binding = prepare_process_cage(run_dir, kind, binding_sha256)
    return current, cage_binding


def execute_odin_exact(
    run_dir: Path,
    kind: str,
    path: Path,
    size: int,
    sha256: str,
    endpoint: dict[str, Any],
    binding_sha256: str,
) -> tuple[dict[str, Any], raw_capture.RawCaptureHandle]:
    expected_identity = tuple(endpoint["endpoint_identity"])
    with transport.pin_regular_file(
        ODIN,
        label="Odin4",
        expected_size=ODIN_SIZE,
        expected_sha256=ODIN_SHA256,
    ) as odin, transport.pin_boot_only_ap(
        path,
        label=kind,
        expected_size=size,
        expected_sha256=sha256,
        require_deterministic_metadata=True,
    ) as ap, transport.pin_regular_file(
        DASH,
        label="process-cage shell",
        expected_size=DASH_SIZE,
        expected_sha256=DASH_SHA256,
    ) as cage_shell:
        command = transport.build_odin_boot_only_command(
            odin.path, ap.path, endpoint["device"]
        )
        transport.revalidate_pinned_path(odin)
        transport.revalidate_pinned_path(ap)
        transport.revalidate_pinned_path(cage_shell)
        pre_identity = endpoint_stat(endpoint["device"])
        if pre_identity != expected_identity:
            raise B0F1Error("Download endpoint changed at Odin dispatch boundary")
        transfer_intent = read_json(run_dir / f"{kind}-intent.json", f"{kind} intent")
        cage_binding = transfer_intent.get("process_cage")
        if (
            not isinstance(cage_binding, dict)
            or cage_binding.get("binding_sha256") != binding_sha256
        ):
            raise ProcessCageError("Odin intent lacks a prepared process cage")
        cage = Path(cage_binding["cage"])
        if (
            not os.path.lexists(cage)
            or _cgroup_identity(cage) != cage_binding.get("cage_identity")
            or _cgroup_populated(cage)
        ):
            raise ProcessCageError("prepared Odin process cage changed before dispatch")
        handle: raw_capture.RawCaptureHandle | None = None
        quiescence: dict[str, Any] | None = None
        try:
            handle = raw_capture.acquire_command(
                [
                    str(cage_shell.path),
                    "-c",
                    ODIN_CAGE_ENTRY_SCRIPT,
                    "s20plus-b0-odin-cage",
                    str(cage),
                    *command,
                ],
                run_dir,
                f"{kind}-transfer",
                timeout=300,
                stdout_maximum=MAX_RAW_BYTES,
                stderr_maximum=MAX_RAW_BYTES,
                env=ODIN_FIXED_ENV,
                stdout_name=f"{kind}.stdout",
                stderr_name=f"{kind}.stderr",
                start_new_session=True,
            )
        finally:
            quiescence = quiesce_process_cage(
                run_dir, kind, binding_sha256
            )
        if handle is None or quiescence is None:
            raise ProcessCageError("Odin process-cage outcome is unavailable")
        captured_stdout = raw_capture.read_stdout(handle, maximum=MAX_RAW_BYTES)
        if not captured_stdout.startswith(ODIN_CAGE_ENTRY_MARKER):
            raise ProcessCageError("Odin did not prove process-cage entry")
        transport.revalidate_pinned_path(odin)
        transport.revalidate_pinned_path(ap)
        transport.revalidate_pinned_path(cage_shell)
        try:
            post_identity = endpoint_stat(endpoint["device"])
            post_state = "same" if post_identity == expected_identity else "changed"
        except FileNotFoundError:
            post_identity = None
            post_state = "absent"
        receipt = {
            "label": kind,
            "returncode": handle.returncode,
            "command_shape": ["odin4", "--reboot", "-a", "AP.tar.md5", "-d", "USBFS"],
            "regular_path_inputs": True,
            "anonymous_proc_fd_inputs": False,
            "odin": odin.receipt(),
            "ap": ap.receipt(),
            "endpoint_path_sha256": hashlib.sha256(endpoint["device"].encode()).hexdigest(),
            "endpoint_pre_identity": list(pre_identity),
            "endpoint_post_identity": None if post_identity is None else list(post_identity),
            "endpoint_post_state": post_state,
            "raw_capture_receipt": {
                "path": str(handle.receipt_path),
                "size": handle.receipt_path.stat().st_size,
                "sha256": hashlib.sha256(handle.receipt_path.read_bytes()).hexdigest(),
            },
            "process_cage": {
                "binding_sha256": digest(cage_binding),
                "entry_marker": ODIN_CAGE_ENTRY_MARKER.decode("ascii").strip(),
                "fixed_environment_sha256": digest(ODIN_FIXED_ENV),
                "quiescence_sha256": digest(quiescence),
                "empty_and_removed": True,
            },
        }
        return receipt, handle


def transfer_boot(run_dir: Path, kind: str, endpoint: dict[str, Any], binding_sha256: str) -> dict[str, Any]:
    if kind == "candidate":
        path, size, sha256 = CANDIDATE_AP, CANDIDATE_AP_SIZE, CANDIDATE_AP_SHA256
    elif kind == "rollback":
        path, size, sha256 = ROLLBACK_AP, ROLLBACK_AP_SIZE, ROLLBACK_AP_SHA256
    else:
        raise B0F1Error("unknown B0 transfer kind")
    current, cage_binding = preflight_odin_dispatch(
        run_dir,
        kind,
        path,
        size,
        sha256,
        endpoint,
        binding_sha256,
    )
    intent = {
        "schema": "s20plus_g986n_b0_transfer_intent_v1",
        "version": VERSION,
        "kind": kind,
        "binding_sha256": binding_sha256,
        "ap_sha256": sha256,
        "endpoint": current,
        "process_cage": cage_binding,
        "attempt": 1,
        "no_replay": True,
        "at": utc_now(),
    }
    durable_json(run_dir / f"{kind}-intent.json", intent)
    try:
        receipt, handle = execute_odin_exact(
            run_dir,
            kind,
            path,
            size,
            sha256,
            current,
            binding_sha256,
        )
        stdout = raw_capture.read_stdout(handle, maximum=MAX_RAW_BYTES)
        stderr = raw_capture.read_stderr(handle, maximum=MAX_RAW_BYTES)
        classification = classify_odin_capture(handle, stdout, stderr)
        if receipt["endpoint_post_state"] == "changed" and not endpoint_ctime_only_change(
            receipt
        ):
            classification = "odin_device_session_failure_or_unknown"
        result = {
            "schema": "s20plus_g986n_b0_transfer_result_v1",
            "version": VERSION,
            "kind": kind,
            "binding_sha256": binding_sha256,
            "classification": classification,
            "receipt": receipt,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "host_process_quiescence_proved": True,
            "replay_permitted": False,
            "at": utc_now(),
        }
    except Exception as exc:
        cage_quiescent = process_cage_quiescent_path(run_dir, kind)
        quiescent_exists = os.path.lexists(cage_quiescent)
        result = {
            "schema": "s20plus_g986n_b0_transfer_result_v1",
            "version": VERSION,
            "kind": kind,
            "binding_sha256": binding_sha256,
            "classification": "odin_device_session_failure_or_unknown",
            "failure_class": type(exc).__name__,
            "possible_partition_effect": True,
            "host_process_quiescence_proved": quiescent_exists,
            "replay_permitted": False,
            "at": utc_now(),
        }
    durable_json(run_dir / f"{kind}-result.json", result)
    return result


def require_transfer_process_quiescence(
    run_dir: Path, kind: str, binding_sha256: str
) -> None:
    intent = read_json(run_dir / f"{kind}-intent.json", f"{kind} intent")
    cage_binding = intent.get("process_cage")
    quiescent = process_cage_quiescent_path(run_dir, kind)
    capture = run_dir / f"{kind}-transfer.capture.json"
    if os.path.lexists(capture) and not isinstance(cage_binding, dict):
        raise ProcessCageError("Odin capture exists without a bound process cage")
    if not isinstance(cage_binding, dict):
        if intent.get("global_claim_cut") is True:
            return
        raise ProcessCageError("effect intent lacks a process cage")
    if not os.path.lexists(quiescent):
        quiesce_process_cage(run_dir, kind, binding_sha256)
    if not os.path.lexists(quiescent):
        raise ProcessCageError("Odin process quiescence is unproved")


def require_all_transfer_processes_quiescent(
    run_dir: Path, binding_sha256: str
) -> None:
    for kind in ("candidate", "rollback"):
        if os.path.lexists(run_dir / f"{kind}-intent.json"):
            require_transfer_process_quiescence(run_dir, kind, binding_sha256)


def recovery_probe(
    run_dir: Path,
    initial_rows: tuple[dict[str, Any], ...],
    row: dict[str, Any],
    prepared: dict[str, Any],
) -> dict[str, Any]:
    serial = row["serial"]
    serial_sha256 = hashlib.sha256(serial.encode()).hexdigest()
    expected = prepared["binding"]["preflight"]
    if serial_sha256 != expected["serial_sha256"]:
        raise B0F1Error("recovery serial differs")
    devpath = adb_devpath(serial)
    if hashlib.sha256(devpath.encode()).hexdigest() != expected["topology_sha256"]:
        raise B0F1Error("recovery topology differs")
    transport_handle = raw_capture.acquire_command(
        [str(ADB), "-s", serial, "exec-out", "sh", "-c", RECOVERY_TRANSPORT_SCRIPT],
        run_dir,
        "candidate-transport",
        timeout=20,
        stdout_maximum=4096,
        stderr_maximum=4096,
        stdout_name="candidate-transport.stdout",
        stderr_name="candidate-transport.stderr",
    )
    transport_stdout = raw_capture.read_stdout(transport_handle, maximum=4096)
    transport_stderr = raw_capture.read_stderr(transport_handle, maximum=4096)
    transport_values = parse_recovery_transport(
        (transport_handle.returncode, transport_stdout, transport_stderr)
    )
    claim_handle = raw_capture.acquire_command(
        [str(ADB), "-s", serial, "exec-out", "sh", "-c", RECOVERY_CLAIM_SCRIPT],
        run_dir,
        "candidate-claim",
        timeout=20,
        stdout_maximum=4096,
        stderr_maximum=4096,
        stdout_name="candidate-claim.stdout",
        stderr_name="candidate-claim.stderr",
    )
    claim_stdout = raw_capture.read_stdout(claim_handle, maximum=4096)
    claim_stderr = raw_capture.read_stderr(claim_handle, maximum=4096)
    verdict, claim_values = parse_recovery_claim(
        (claim_handle.returncode, claim_stdout, claim_stderr)
    )
    final = adb_inventory()
    final_row = exact_adb_row(final, serial_sha256, "recovery")
    if (
        sanitized_inventory(final) != sanitized_inventory(initial_rows)
        or adb_devpath(final_row["serial"]) != devpath
    ):
        raise B0F1Error("recovery ADB identity changed during observation")
    boot_id_sha256 = hashlib.sha256(transport_values["boot_id"].encode()).hexdigest()
    if boot_id_sha256 == expected["boot_id_sha256"]:
        verdict = "REFUTED"
    return {
        "environment": "recovery-adb",
        "transport_authorized": True,
        "claim_verdict": verdict,
        "serial_sha256": serial_sha256,
        "topology_sha256": hashlib.sha256(devpath.encode()).hexdigest(),
        "boot_id_sha256": boot_id_sha256,
        "transport_values": {
            key: value for key, value in transport_values.items() if key != "boot_id"
        },
        "claim_values": claim_values,
        "at": utc_now(),
    }


def observe_candidate(run_dir: Path, prepared: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    no_backend = False
    if os.path.lexists(run_dir / "candidate-transfer-cut.json"):
        cut = read_json(run_dir / "candidate-transfer-cut.json", "candidate transfer cut")
        no_backend = cut.get("possible_partition_effect") is False
    elif os.path.lexists(run_dir / "candidate-result.json"):
        result = read_json(run_dir / "candidate-result.json", "candidate result")
        no_backend = result.get("classification") == "odin_local_parse_failure"
    if no_backend:
        devices, listing_sha256 = enumerate_download()
        if len(devices) == 1:
            endpoint = identify_download()
            return {
                "environment": "download",
                "transport_authorized": True,
                "claim_verdict": "NO_PROOF",
                "endpoint": endpoint,
                "arrival_listing_sha256": listing_sha256,
                "reason": "candidate-backend-not-started",
                "at": utc_now(),
            }, None
        if len(devices) > 1:
            return {
                "environment": "download-ambiguous",
                "transport_authorized": False,
                "claim_verdict": "NO_PROOF",
                "reason": "download-row-count",
                "at": utc_now(),
            }, None
    deadline = time.monotonic() + RECOVERY_ARRIVAL_SECONDS
    departure_seen = False
    prepared_endpoint = prepared["binding"]["endpoint"]
    expected_serial = prepared["binding"]["preflight"]["serial_sha256"]
    while time.monotonic() < deadline:
        try:
            current_identity = endpoint_stat(prepared_endpoint["device"])
            if list(current_identity[:3]) != prepared_endpoint["endpoint_identity"][:3]:
                departure_seen = True
        except (FileNotFoundError, B0F1Error):
            departure_seen = True
        try:
            rows = adb_inventory()
        except B0F1Error:
            return {
                "environment": "adb-malformed",
                "transport_authorized": False,
                "claim_verdict": "NO_PROOF",
                "reason": "adb-inventory-malformed",
                "at": utc_now(),
            }, None
        matching_rows = target_adb_rows(rows)
        expected_rows = tuple(
            row
            for row in rows
            if hashlib.sha256(row["serial"].encode()).hexdigest() == expected_serial
        )
        if len(matching_rows) > 1:
            return {
                "environment": "adb-ambiguous",
                "transport_authorized": False,
                "claim_verdict": "NO_PROOF",
                "reason": "exact-target-row-count",
                "at": utc_now(),
            }, None
        if not matching_rows:
            if expected_rows:
                return {
                    "environment": "adb-wrong-state",
                    "transport_authorized": False,
                    "claim_verdict": "NO_PROOF",
                    "reason": "selected-serial-lacks-exact-target-metadata",
                    "at": utc_now(),
                }, None
            time.sleep(2)
            continue
        row = matching_rows[0]
        if hashlib.sha256(row["serial"].encode()).hexdigest() != expected_serial:
            return {
                "environment": "adb-foreign",
                "transport_authorized": False,
                "claim_verdict": "NO_PROOF",
                "reason": "serial-mismatch",
                "at": utc_now(),
            }, None
        if row["state"] == "recovery" and EXPECTED_ADB_METADATA <= row["metadata"]:
            try:
                return recovery_probe(run_dir, rows, row, prepared), row["serial"]
            except B0F1Error as exc:
                return {
                    "environment": "recovery-adb-unqualified",
                    "transport_authorized": False,
                    "claim_verdict": "NO_PROOF",
                    "reason_sha256": hashlib.sha256(str(exc).encode()).hexdigest(),
                    "at": utc_now(),
                }, None
        if row["state"] == "device" and EXPECTED_ADB_METADATA <= row["metadata"]:
            try:
                health, serial = resident_health_once(
                    run_dir, "candidate-android-root", expected_serial
                )
            except B0F1Error as exc:
                return {
                    "environment": "android-unqualified",
                    "transport_authorized": False,
                    "claim_verdict": "NO_PROOF",
                    "reason_sha256": hashlib.sha256(str(exc).encode()).hexdigest(),
                    "at": utc_now(),
                }, None
            return {
                "environment": "resident-android",
                "transport_authorized": True,
                "claim_verdict": "NO_PROOF",
                "resident_health": health,
                "at": utc_now(),
            }, serial
        return {
            "environment": "adb-wrong-state",
            "transport_authorized": False,
            "claim_verdict": "NO_PROOF",
            "reason": "state-or-metadata-mismatch",
            "at": utc_now(),
        }, None
    try:
        devices, listing_sha256 = enumerate_download()
        if len(devices) == 1:
            endpoint = identify_download()
            if not no_backend and not departure_seen:
                return {
                    "environment": "download-unquiesced",
                    "transport_authorized": False,
                    "claim_verdict": "NO_PROOF",
                    "endpoint_sha256": endpoint["endpoint_sha256"],
                    "reason": "no-endpoint-departure-after-uncertain-transfer",
                    "at": utc_now(),
                }, None
            return {
                "environment": "download",
                "transport_authorized": True,
                "claim_verdict": "NO_PROOF",
                "endpoint": endpoint,
                "arrival_listing_sha256": listing_sha256,
                "at": utc_now(),
            }, None
        if len(devices) > 1:
            return {
                "environment": "download-ambiguous",
                "transport_authorized": False,
                "claim_verdict": "NO_PROOF",
                "reason": "download-row-count",
                "at": utc_now(),
            }, None
    except B0F1Error:
        pass
    return {
        "environment": "no-arrival",
        "transport_authorized": False,
        "claim_verdict": "NO_PROOF",
        "reason": "bounded-observer-timeout",
        "at": utc_now(),
    }, None


def revalidate_rollback_source(
    run_dir: Path,
    prepared: dict[str, Any],
    observation: dict[str, Any],
    serial: str,
) -> dict[str, Any]:
    expected_serial = prepared["binding"]["preflight"]["serial_sha256"]
    if hashlib.sha256(serial.encode()).hexdigest() != expected_serial:
        raise B0F1Error("rollback source serial differs")
    if observation["environment"] == "recovery-adb":
        first = adb_inventory()
        row = exact_adb_row(first, expected_serial, "recovery")
        devpath = adb_devpath(serial)
        if os.path.lexists(run_dir / "rollback-source.capture.json") or os.path.lexists(
            run_dir / "rollback-source.stdout"
        ) or os.path.lexists(run_dir / "rollback-source.stderr"):
            raise B0F1Error(
                "recovery source capture preceded a cut; use physical rollback"
            )
        handle = raw_capture.acquire_command(
            [str(ADB), "-s", serial, "exec-out", "sh", "-c", RECOVERY_TRANSPORT_SCRIPT],
            run_dir,
            "rollback-source",
            timeout=20,
            stdout_maximum=4096,
            stderr_maximum=4096,
            stdout_name="rollback-source.stdout",
            stderr_name="rollback-source.stderr",
        )
        stdout = raw_capture.read_stdout(handle, maximum=4096)
        stderr = raw_capture.read_stderr(handle, maximum=4096)
        values = parse_recovery_transport((handle.returncode, stdout, stderr))
        if hashlib.sha256(values["boot_id"].encode()).hexdigest() != observation.get(
            "boot_id_sha256"
        ):
            raise B0F1Error("rollback recovery boot identity changed")
        final = adb_inventory()
        final_row = exact_adb_row(final, expected_serial, "recovery")
        if (
            sanitized_inventory(final) != sanitized_inventory(first)
            or adb_devpath(final_row["serial"]) != devpath
        ):
            raise B0F1Error("rollback recovery transport changed")
        return {
            "environment": "recovery-adb",
            "serial_sha256": expected_serial,
            "topology_sha256": hashlib.sha256(devpath.encode()).hexdigest(),
            "boot_id_sha256": hashlib.sha256(values["boot_id"].encode()).hexdigest(),
            "transport_stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "transport_stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "capture_receipt_sha256": hashlib.sha256(
                handle.receipt_path.read_bytes()
            ).hexdigest(),
        }
    if observation["environment"] == "resident-android":
        health, confirmed_serial = resident_health_once(
            run_dir, "rollback-source-root", expected_serial
        )
        if (
            confirmed_serial != serial
            or health["boot_id_sha256"]
            != observation.get("resident_health", {}).get("boot_id_sha256")
        ):
            raise B0F1Error("rollback Android source identity changed")
        return {
            "environment": "resident-android",
            "serial_sha256": expected_serial,
            "topology_sha256": health["topology_sha256"],
            "boot_id_sha256": health["boot_id_sha256"],
            "root_capture": health["root_capture"],
        }
    raise B0F1Error("candidate observation cannot authorize an ADB rollback transition")


def enter_rollback_download(
    run_dir: Path,
    prepared: dict[str, Any],
    observation: dict[str, Any],
    serial: str,
) -> dict[str, Any] | None:
    baseline_path = run_dir / "rollback-download-baseline.json"
    if os.path.lexists(baseline_path):
        if os.path.lexists(run_dir / "rollback-download-intent.json"):
            raise B0F1Error("rollback Download intent already exists; no replay")
        baseline = validate_download_baseline(
            read_json(baseline_path, "rollback Download baseline"),
            "rollback Download baseline",
        )
    else:
        baseline = download_baseline()
        durable_json(baseline_path, baseline)
    source_receipt = revalidate_rollback_source(
        run_dir, prepared, observation, serial
    )
    intent = {
        "schema": "s20plus_g986n_b0_rollback_download_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "source_environment": observation["environment"],
        "source_serial_sha256": hashlib.sha256(serial.encode()).hexdigest(),
        "source_boot_id_sha256": observation.get("boot_id_sha256")
        or observation.get("resident_health", {}).get("boot_id_sha256"),
        "source_receipt": source_receipt,
        "baseline_sha256": digest(baseline),
        "action": "adb-reboot-download-for-mandatory-resident-rollback",
        "attempt": 1,
        "no_replay": True,
        "at": utc_now(),
    }
    durable_json(run_dir / "rollback-download-intent.json", intent)
    effect_baseline = download_baseline()
    durable_json(
        run_dir / "rollback-download-effect-baseline.json",
        {
            "schema": "s20plus_g986n_b0_rollback_download_effect_baseline_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "intent_sha256": digest(intent),
            "baseline": effect_baseline,
            "at": utc_now(),
        },
    )
    try:
        captured = adb_reboot_download_capture(run_dir, serial, "rollback-reboot")
        result = {
            "schema": "s20plus_g986n_b0_rollback_download_result_v1",
            "version": VERSION,
            **captured,
            "replay_permitted": False,
            "at": utc_now(),
        }
    except Exception as exc:
        result = {
            "schema": "s20plus_g986n_b0_rollback_download_result_v1",
            "version": VERSION,
            "outcome": "uncertain",
            "failure_class": type(exc).__name__,
            "replay_permitted": False,
            "at": utc_now(),
        }
    durable_json(run_dir / "rollback-download-result.json", result)
    durable_json(
        run_dir / "rollback-download-observation-intent.json",
        {
            "schema": "s20plus_g986n_b0_rollback_download_observation_intent_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "attempt": 1,
            "no_replay": True,
            "at": utc_now(),
        },
    )
    arrival = wait_download(effect_baseline)
    if arrival is not None:
        durable_json(
            run_dir / "rollback-download-arrival.json",
            {
                "schema": "s20plus_g986n_b0_rollback_download_arrival_v1",
                "version": VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "branch": "automatic-adb",
                **arrival,
            },
        )
    return arrival


def bind_existing_download(run_dir: Path, prepared: dict[str, Any], observation: dict[str, Any]) -> dict[str, Any]:
    endpoint = observation["endpoint"]
    intent = {
        "schema": "s20plus_g986n_b0_rollback_download_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "source_environment": "already-download",
        "source_serial_sha256": None,
        "source_boot_id_sha256": None,
        "baseline_sha256": None,
        "action": "bind-existing-download-for-mandatory-resident-rollback",
        "attempt": 0,
        "no_replay": True,
        "at": utc_now(),
    }
    durable_json(run_dir / "rollback-download-intent.json", intent)
    durable_json(
        run_dir / "rollback-download-arrival.json",
        {
            "schema": "s20plus_g986n_b0_rollback_download_arrival_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "branch": "already-download",
            "endpoint": endpoint,
            "baseline_sha256": None,
            "arrival_listing_sha256": observation["arrival_listing_sha256"],
            "at": utc_now(),
        },
    )
    return endpoint


def derive_terminal_verdict(
    candidate_classification: str,
    claim_verdict: str,
    rollback_completed: bool,
) -> tuple[str, bool]:
    proved = (
        candidate_classification == "odin_transfer_completed"
        and claim_verdict == "PROVED"
        and rollback_completed is True
    )
    if proved:
        return "PROVED_B0_RETURNED_RESIDENT_HEALTHY", True
    if (
        candidate_classification == "odin_transfer_completed"
        and claim_verdict == "REFUTED"
    ):
        return "REFUTED_B0_RETURNED_RESIDENT_HEALTHY", False
    return "NO_PROOF_B0_RETURNED_RESIDENT_HEALTHY", False


def publish_terminal_from_final(
    run_dir: Path, prepared: dict[str, Any], final: dict[str, Any]
) -> dict[str, Any]:
    if os.path.lexists(run_dir / "terminal.json"):
        return read_json(run_dir / "terminal.json", "B0 terminal")
    initial_boot = prepared["binding"]["preflight"]["boot_id_sha256"]
    observation = read_json(run_dir / "candidate-observation.json", "candidate observation")
    health = final["health"]
    candidate_boot = observation.get("boot_id_sha256")
    if candidate_boot is None:
        candidate_boot = observation.get("resident_health", {}).get("boot_id_sha256")
    if health["boot_id_sha256"] == initial_boot or (
        candidate_boot is not None and health["boot_id_sha256"] == candidate_boot
    ):
        raise B0F1Error("final resident boot ID is not fresh")
    rollback_completed = final["rollback_transfer_completed"]
    candidate = (
        read_json(run_dir / "candidate-result.json", "candidate result")
        if os.path.lexists(run_dir / "candidate-result.json")
        else read_json(run_dir / "candidate-transfer-cut.json", "candidate cut")
    )
    claim_verdict = observation["claim_verdict"]
    verdict, proved = derive_terminal_verdict(
        candidate.get("classification", "odin_device_session_failure_or_unknown"),
        claim_verdict,
        rollback_completed,
    )
    terminal = {
        "schema": "s20plus_g986n_b0_terminal_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "verdict": verdict,
        "experiment_pass": proved,
        "candidate_attempts": 1,
        "rollback_attempts": 1,
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
        "rollback_transfer_completed": rollback_completed,
        "rollback_outcome_unproved_but_resident_healthy": not rollback_completed,
        "recovery_partition_reads": 0,
        "recovery_partition_writes": 0,
        "recovery_partition_transfers": 0,
        "other_target_commands": 0,
        "at": utc_now(),
    }
    durable_json(run_dir / "terminal.json", terminal)
    release_guard(run_dir)
    return terminal


def final_health_and_terminal(run_dir: Path, prepared: dict[str, Any]) -> dict[str, Any]:
    if os.path.lexists(run_dir / "terminal.json"):
        return read_json(run_dir / "terminal.json", "B0 terminal")
    if os.path.lexists(run_dir / "final-health.json"):
        final = read_json(run_dir / "final-health.json", "B0 final health")
        return publish_terminal_from_final(run_dir, prepared, final)
    deadline = time.monotonic() + ANDROID_ARRIVAL_SECONDS
    last_error: B0F1Error | None = None
    while time.monotonic() < deadline:
        try:
            health, _serial = resident_health_once(
                run_dir,
                "final-root",
                prepared["binding"]["preflight"]["serial_sha256"],
            )
            observation = read_json(
                run_dir / "candidate-observation.json", "candidate observation"
            )
            prior_boot_ids = {prepared["binding"]["preflight"]["boot_id_sha256"]}
            candidate_boot = observation.get("boot_id_sha256")
            if candidate_boot is None:
                candidate_boot = observation.get("resident_health", {}).get(
                    "boot_id_sha256"
                )
            if candidate_boot is not None:
                prior_boot_ids.add(candidate_boot)
            if health["boot_id_sha256"] in prior_boot_ids:
                raise B0F1Error("final resident boot ID is not fresh")
            break
        except B0F1Error as exc:
            last_error = exc
            time.sleep(3)
    else:
        raise B0F1Error("final resident health timed out") from last_error
    rollback = (
        read_json(run_dir / "rollback-result.json", "rollback result")
        if os.path.lexists(run_dir / "rollback-result.json")
        else None
    )
    rollback_completed = bool(
        rollback is not None and rollback.get("classification") == "odin_transfer_completed"
    )
    final = {
        "schema": "s20plus_g986n_b0_final_health_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "health": health,
        "rollback_transfer_completed": rollback_completed,
        "rollback_outcome_proved": rollback_completed,
        "resident_boot_healthy": True,
        "at": utc_now(),
    }
    durable_json(run_dir / "final-health.json", final)
    return publish_terminal_from_final(run_dir, prepared, final)


def rollback_from_arrival(run_dir: Path, prepared: dict[str, Any], endpoint: dict[str, Any]) -> dict[str, Any]:
    read_prepared(run_dir, phase="rollback")
    if os.path.lexists(run_dir / "rollback-intent.json"):
        raise B0F1Error("rollback intent already exists; replay forbidden")
    transfer_boot(run_dir, "rollback", endpoint, prepared["binding_sha256"])
    require_transfer_process_quiescence(
        run_dir, "rollback", prepared["binding_sha256"]
    )
    return final_health_and_terminal(run_dir, prepared)


def execute(run_dir: Path, approval: str) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir, phase="candidate")
    binding = prepared["binding"]
    if approval != prepared["approval_token"]:
        raise B0F1Error("fresh B0 approval does not match")
    if type(binding.get("expires_unix")) is not int or time.time() > binding["expires_unix"]:
        raise B0F1Error("B0 prepared approval expired; abort without candidate")
    if os.path.lexists(run_dir / "candidate-intent.json") or candidate_claim_present():
        raise B0F1Error("B0 candidate is already consumed; replay forbidden")
    current = identify_download()
    if not same_download_session(current, binding["endpoint"]):
        raise B0F1Error("prepared Download session changed")
    approval_value = {
            "schema": "s20plus_g986n_b0_approval_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "approval_sha256": hashlib.sha256(approval.encode()).hexdigest(),
            "candidate_replay_permitted": False,
            "rollback_preapproved": True,
            "at": utc_now(),
        }
    approval_path = run_dir / "approval.json"
    if os.path.lexists(approval_path):
        existing_approval = read_json(approval_path, "B0 approval")
        for key in (
            "schema",
            "version",
            "binding_sha256",
            "approval_sha256",
            "candidate_replay_permitted",
            "rollback_preapproved",
        ):
            if existing_approval.get(key) != approval_value[key]:
                raise B0F1Error("existing B0 approval differs")
    else:
        durable_json(approval_path, approval_value)
    baseline_path = run_dir / "candidate-adb-baseline.json"
    if os.path.lexists(baseline_path):
        baseline_value = read_json(baseline_path, "candidate ADB baseline")
        baseline_inventory = validate_sanitized_inventory(
            baseline_value.get("inventory"), "candidate ADB baseline inventory"
        )
        if (
            baseline_value.get("inventory_sha256") != digest(baseline_inventory)
            or baseline_value.get("exact_target_present") is not False
            or baseline_value.get("other_target_commands") != 0
            or any(
                row["serial_sha256"] == binding["preflight"]["serial_sha256"]
                or EXPECTED_ADB_MODEL in row["metadata"]
                for row in baseline_inventory
            )
        ):
            raise B0F1Error("candidate ADB baseline differs")
    else:
        durable_json(
            baseline_path,
            {
                "schema": "s20plus_g986n_b0_candidate_adb_baseline_v2",
                "version": VERSION,
                **candidate_adb_baseline_receipt(
                    adb_inventory(), binding["preflight"]["serial_sha256"]
                ),
                "at": utc_now(),
            },
        )
    candidate_adb_baseline_receipt(
        adb_inventory(), binding["preflight"]["serial_sha256"]
    )
    consume_candidate_globally(run_dir, prepared["binding_sha256"])
    require_candidate_claim(run_dir, prepared["binding_sha256"])
    transfer_boot(run_dir, "candidate", current, prepared["binding_sha256"])
    require_transfer_process_quiescence(
        run_dir, "candidate", prepared["binding_sha256"]
    )
    durable_json(
        run_dir / "candidate-observation-intent.json",
        {
            "schema": "s20plus_g986n_b0_candidate_observation_intent_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            "timeout_seconds": RECOVERY_ARRIVAL_SECONDS,
            "candidate_replay_permitted": False,
            "at": utc_now(),
        },
    )
    observation, serial = observe_candidate(run_dir, prepared)
    durable_json(
        run_dir / "candidate-observation.json",
        {
            "schema": "s20plus_g986n_b0_candidate_observation_v1",
            "version": VERSION,
            "binding_sha256": prepared["binding_sha256"],
            **observation,
            "candidate_replay_permitted": False,
        },
    )
    if observation["environment"] == "download" and observation["transport_authorized"]:
        endpoint = bind_existing_download(run_dir, prepared, observation)
        return rollback_from_arrival(run_dir, prepared, endpoint)
    if observation["transport_authorized"] and serial is not None:
        try:
            arrival = enter_rollback_download(run_dir, prepared, observation, serial)
        except B0F1Error:
            arrival = None
        if arrival is not None:
            return rollback_from_arrival(run_dir, prepared, arrival["endpoint"])
    return {
        "schema": "s20plus_g986n_b0_recovery_pending_v1",
        "run_dir": str(run_dir),
        "binding_sha256": prepared["binding_sha256"],
        "verdict": "RECOVERY_PENDING_PHYSICAL_DOWNLOAD",
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
    }


def resume_run(run_dir: Path) -> dict[str, Any]:
    """Continue only journal-authorized recovery; never repeat an effect."""
    require_active()
    run_dir = validate_run_dir(run_dir)
    if os.path.lexists(run_dir / "terminal.json"):
        return finalize_resident(run_dir)
    prepared = read_prepared(run_dir, phase="health")
    binding_sha256 = prepared["binding_sha256"]
    require_all_transfer_processes_quiescent(run_dir, binding_sha256)
    if not os.path.lexists(run_dir / "candidate-intent.json"):
        if not candidate_claim_present():
            return {
                "schema": "s20plus_g986n_b0_recovery_pending_v1",
                "run_dir": str(run_dir),
                "binding_sha256": binding_sha256,
                "verdict": "PRE_CANDIDATE_AWAITING_APPROVAL_OR_ABORT",
                "candidate_replay_permitted": False,
                "rollback_replay_permitted": False,
            }
        require_candidate_claim(run_dir, binding_sha256)
        durable_json(
            run_dir / "candidate-intent.json",
            {
                "schema": "s20plus_g986n_b0_transfer_intent_v1",
                "version": VERSION,
                "kind": "candidate",
                "binding_sha256": binding_sha256,
                "ap_sha256": CANDIDATE_AP_SHA256,
                "endpoint": prepared["binding"]["endpoint"],
                "attempt": 1,
                "backend_invoked": False,
                "global_claim_cut": True,
                "no_replay": True,
                "at": utc_now(),
            },
        )
    require_candidate_claim(run_dir, binding_sha256)
    require_transfer_process_quiescence(run_dir, "candidate", binding_sha256)
    if not os.path.lexists(run_dir / "candidate-result.json") and not os.path.lexists(
        run_dir / "candidate-transfer-cut.json"
    ):
        candidate_intent = read_json(
            run_dir / "candidate-intent.json", "candidate intent"
        )
        possible_effect = candidate_intent.get("global_claim_cut") is not True
        durable_json(
            run_dir / "candidate-transfer-cut.json",
            {
                "schema": "s20plus_g986n_b0_candidate_transfer_cut_v1",
                "version": VERSION,
                "binding_sha256": binding_sha256,
                "classification": "odin_device_session_failure_or_unknown",
                "possible_partition_effect": possible_effect,
                "candidate_replay_permitted": False,
                "reason": "intent-consumed-result-absent",
                "at": utc_now(),
            },
        )
    if not os.path.lexists(run_dir / "candidate-observation.json"):
        if os.path.lexists(run_dir / "candidate-observation-intent.json"):
            observation = {
                "environment": "observer-reporting-cut",
                "transport_authorized": False,
                "claim_verdict": "NO_PROOF",
                "reason": "observation-intent-consumed-result-absent",
                "at": utc_now(),
            }
            serial = None
        else:
            durable_json(
                run_dir / "candidate-observation-intent.json",
                {
                    "schema": "s20plus_g986n_b0_candidate_observation_intent_v1",
                    "version": VERSION,
                    "binding_sha256": binding_sha256,
                    "timeout_seconds": RECOVERY_ARRIVAL_SECONDS,
                    "candidate_replay_permitted": False,
                    "at": utc_now(),
                },
            )
            observation, serial = observe_candidate(run_dir, prepared)
        durable_json(
            run_dir / "candidate-observation.json",
            {
                "schema": "s20plus_g986n_b0_candidate_observation_v1",
                "version": VERSION,
                "binding_sha256": binding_sha256,
                **observation,
                "candidate_replay_permitted": False,
            },
        )
    else:
        observation = read_json(
            run_dir / "candidate-observation.json", "candidate observation"
        )
        serial = None
    if os.path.lexists(run_dir / "rollback-intent.json"):
        return final_health_and_terminal(run_dir, prepared)
    if os.path.lexists(run_dir / "physical-rollback-arrival.json"):
        arm = read_json(run_dir / "physical-rollback-intent.json", "physical rollback arm")
        return {
            "schema": "s20plus_g986n_b0_recovery_pending_v1",
            "run_dir": str(run_dir),
            "binding_sha256": binding_sha256,
            "verdict": "PHYSICAL_DOWNLOAD_BOUND_AWAITING_CONFIRMATION",
            "confirmation": arm["confirmation_token"],
            "candidate_replay_permitted": False,
            "rollback_replay_permitted": False,
        }
    if os.path.lexists(run_dir / "physical-observation-miss.json"):
        return {
            "schema": "s20plus_g986n_b0_recovery_pending_v1",
            "run_dir": str(run_dir),
            "binding_sha256": binding_sha256,
            "verdict": "PHYSICAL_DOWNLOAD_OBSERVATION_CONSUMED",
            "candidate_replay_permitted": False,
            "rollback_replay_permitted": False,
        }
    if os.path.lexists(run_dir / "physical-rollback-intent.json"):
        arm = read_json(run_dir / "physical-rollback-intent.json", "physical rollback arm")
        return {
            "schema": "s20plus_g986n_b0_recovery_pending_v1",
            "run_dir": str(run_dir),
            "binding_sha256": binding_sha256,
            "verdict": "PHYSICAL_DOWNLOAD_ACTION_OR_CONFIRMATION_PENDING",
            "confirmation": arm["confirmation_token"],
            "candidate_replay_permitted": False,
            "rollback_replay_permitted": False,
        }
    if os.path.lexists(run_dir / "rollback-download-arrival.json"):
        arrival = read_json(
            run_dir / "rollback-download-arrival.json", "rollback Download arrival"
        )
        return rollback_from_arrival(run_dir, prepared, arrival["endpoint"])
    if os.path.lexists(run_dir / "rollback-download-intent.json"):
        if not os.path.lexists(run_dir / "rollback-download-result.json"):
            if not os.path.lexists(
                run_dir / "rollback-download-effect-baseline.json"
            ):
                return {
                    "schema": "s20plus_g986n_b0_recovery_pending_v1",
                    "run_dir": str(run_dir),
                    "binding_sha256": binding_sha256,
                    "verdict": "ROLLBACK_DOWNLOAD_PRE_EFFECT_CUT_PHYSICAL_FALLBACK",
                    "candidate_replay_permitted": False,
                    "rollback_replay_permitted": False,
                }
            durable_json(
                run_dir / "rollback-download-result.json",
                {
                    "schema": "s20plus_g986n_b0_rollback_download_result_v1",
                    "version": VERSION,
                    "outcome": "uncertain",
                    "failure_class": "ReportingCut",
                    "replay_permitted": False,
                    "at": utc_now(),
                },
            )
        if os.path.lexists(run_dir / "rollback-download-observation-intent.json"):
            return {
                "schema": "s20plus_g986n_b0_recovery_pending_v1",
                "run_dir": str(run_dir),
                "binding_sha256": binding_sha256,
                "verdict": "ROLLBACK_DOWNLOAD_OBSERVATION_CONSUMED_PHYSICAL_FALLBACK",
                "candidate_replay_permitted": False,
                "rollback_replay_permitted": False,
            }
        return {
            "schema": "s20plus_g986n_b0_recovery_pending_v1",
            "run_dir": str(run_dir),
            "binding_sha256": binding_sha256,
            "verdict": "ROLLBACK_DOWNLOAD_CUT_PHYSICAL_FALLBACK",
            "candidate_replay_permitted": False,
            "rollback_replay_permitted": False,
        }
    if observation.get("environment") == "download" and observation.get(
        "transport_authorized"
    ):
        endpoint = bind_existing_download(run_dir, prepared, observation)
        return rollback_from_arrival(run_dir, prepared, endpoint)
    if observation.get("transport_authorized") and observation.get("environment") in {
        "recovery-adb",
        "resident-android",
    }:
        rows = adb_inventory()
        state = "recovery" if observation["environment"] == "recovery-adb" else "device"
        row = exact_adb_row(
            rows,
            prepared["binding"]["preflight"]["serial_sha256"],
            state,
        )
        serial = row["serial"]
        try:
            arrival_value = enter_rollback_download(
                run_dir, prepared, observation, serial
            )
        except B0F1Error:
            arrival_value = None
        if arrival_value is not None:
            return rollback_from_arrival(
                run_dir, prepared, arrival_value["endpoint"]
            )
    return {
        "schema": "s20plus_g986n_b0_recovery_pending_v1",
        "run_dir": str(run_dir),
        "binding_sha256": binding_sha256,
        "verdict": "RECOVERY_PENDING_PHYSICAL_DOWNLOAD",
        "candidate_replay_permitted": False,
        "rollback_replay_permitted": False,
    }


def arm_physical_rollback(run_dir: Path) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir, phase="rollback")
    require_candidate_claim(run_dir, prepared["binding_sha256"])
    require_all_transfer_processes_quiescent(
        run_dir, prepared["binding_sha256"]
    )
    if os.path.lexists(run_dir / "rollback-intent.json"):
        raise B0F1Error("rollback was already attempted; replay forbidden")
    if os.path.lexists(run_dir / "physical-observation-miss.json"):
        raise B0F1Error("physical Download observation was already consumed")
    if os.path.lexists(run_dir / "physical-rollback-intent.json"):
        arm = read_json(run_dir / "physical-rollback-intent.json", "physical rollback arm")
        return {
            "run_dir": str(run_dir),
            "confirmation": arm["confirmation_token"],
            "already_armed": True,
        }
    observation = read_json(
        run_dir / "candidate-observation.json", "candidate observation"
    )
    physical_baseline_path = run_dir / "physical-rollback-baseline.json"
    if os.path.lexists(physical_baseline_path):
        validate_download_baseline(
            read_json(physical_baseline_path, "physical rollback baseline"),
            "physical rollback baseline",
        )
        baseline = download_baseline()
        endpoint = None
        branch = "attended-entry-required"
        listing_sha256 = baseline["listing_sha256"]
    else:
        devices, listing_sha256 = enumerate_download()
        if len(devices) > 1:
            raise B0F1Error("physical fallback Download state is ambiguous")
        if len(devices) == 1:
            if observation.get("environment") == "download-unquiesced":
                raise B0F1Error(
                    "unquiesced Download must depart before physical fallback is armed"
                )
            endpoint = identify_download()
            baseline = None
            branch = "already-download"
        else:
            baseline = {
                "schema": "s20plus_g986n_b0_download_baseline_v1",
                "endpoint_count": 0,
                "listing_sha256": listing_sha256,
                "at": utc_now(),
            }
            durable_json(physical_baseline_path, baseline)
            endpoint = None
            branch = "attended-entry-required"
    arm_core = {
        "schema": "s20plus_g986n_b0_physical_rollback_intent_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "branch": branch,
        "baseline": baseline,
        "baseline_sha256": None if baseline is None else digest(baseline),
        "action": "one-attended-physical-download-entry-if-not-already-present",
        "action_attempt_maximum": 1,
        "rollback_replay_permitted": False,
        "expires_unix": int(time.time()) + PHYSICAL_ARRIVAL_LIFETIME_SECONDS,
        "at": utc_now(),
    }
    confirmation = PHYSICAL_CONFIRM_PREFIX + digest(arm_core)
    durable_json(
        run_dir / "physical-rollback-intent.json",
        {**arm_core, "confirmation_token": confirmation},
    )
    if endpoint is not None:
        durable_json(
            run_dir / "physical-rollback-arrival.json",
            {
                "schema": "s20plus_g986n_b0_physical_rollback_arrival_v1",
                "version": VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "branch": "already-download-at-arm",
                "endpoint": endpoint,
                "baseline_sha256": None,
                "arrival_listing_sha256": listing_sha256,
                "observed_unix": int(time.time()),
                "at": utc_now(),
            },
        )
    return {
        "run_dir": str(run_dir),
        "confirmation": confirmation,
        "physical_action_required": endpoint is None,
    }


def publish_physical_observation_miss(
    run_dir: Path,
    prepared: dict[str, Any],
    arm: dict[str, Any],
    reason: str,
    endpoint_count: int | None,
    listing_sha256: str | None,
) -> dict[str, Any]:
    path = run_dir / "physical-observation-miss.json"
    if os.path.lexists(path):
        return read_json(path, "physical observation miss")
    value = {
        "schema": "s20plus_g986n_b0_physical_observation_miss_v1",
        "version": VERSION,
        "binding_sha256": prepared["binding_sha256"],
        "baseline_sha256": arm["baseline_sha256"],
        "expires_unix": arm["expires_unix"],
        "reason": reason,
        "endpoint_count": endpoint_count,
        "listing_sha256": listing_sha256,
        "no_replay": True,
        "at": utc_now(),
    }
    durable_json(path, value)
    return value


def confirm_physical_rollback(run_dir: Path, confirmation: str) -> dict[str, Any]:
    require_active()
    prepared = read_prepared(run_dir, phase="rollback")
    require_all_transfer_processes_quiescent(
        run_dir, prepared["binding_sha256"]
    )
    arm = read_json(run_dir / "physical-rollback-intent.json", "physical rollback arm")
    if confirmation != arm.get("confirmation_token"):
        raise B0F1Error("physical rollback confirmation differs")
    confirmation_intent_path = run_dir / "physical-confirmation-intent.json"
    if not os.path.lexists(confirmation_intent_path):
        confirmed_unix = int(time.time())
        if confirmed_unix > arm["expires_unix"]:
            raise B0F1Error("physical rollback confirmation expired")
        durable_json(
            confirmation_intent_path,
            {
                "schema": "s20plus_g986n_b0_physical_confirmation_intent_v1",
                "version": VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "arm_sha256": digest(arm),
                "confirmation_token_sha256": hashlib.sha256(
                    confirmation.encode()
                ).hexdigest(),
                "confirmed_unix": confirmed_unix,
                "no_replay": True,
                "at": utc_now(),
            },
        )
    if os.path.lexists(run_dir / "rollback-intent.json"):
        raise B0F1Error("rollback was already attempted; replay forbidden")
    arrival_path = run_dir / "physical-rollback-arrival.json"
    if not os.path.lexists(arrival_path):
        if os.path.lexists(run_dir / "physical-observation-miss.json"):
            raise B0F1Error("physical Download observation was already consumed")
        observation_intent_path = run_dir / "physical-observation-intent.json"
        reporting_cut = os.path.lexists(observation_intent_path)
        if not reporting_cut:
            durable_json(
                observation_intent_path,
                {
                    "schema": "s20plus_g986n_b0_physical_observation_intent_v1",
                    "version": VERSION,
                    "binding_sha256": prepared["binding_sha256"],
                    "baseline_sha256": arm["baseline_sha256"],
                    "attempt": 1,
                    "no_replay": True,
                    "at": utc_now(),
                },
            )
        if time.time() > arm["expires_unix"]:
            publish_physical_observation_miss(
                run_dir, prepared, arm, "arm-expired", None, None
            )
            raise B0F1Error("physical rollback arm expired; observation consumed")
        if reporting_cut:
            resume_path = run_dir / "physical-resume-observation-intent.json"
            if os.path.lexists(resume_path):
                publish_physical_observation_miss(
                    run_dir, prepared, arm, "identity-unproved", None, None
                )
                raise B0F1Error(
                    "physical post-cut observation is uncertain-consumed"
                )
            durable_json(
                resume_path,
                {
                    "schema": "s20plus_g986n_b0_physical_resume_observation_intent_v1",
                    "version": VERSION,
                    "binding_sha256": prepared["binding_sha256"],
                    "baseline_sha256": arm["baseline_sha256"],
                    "expires_unix": arm["expires_unix"],
                    "attempt": 1,
                    "mode": "one-current-read-after-reporting-cut",
                    "no_replay": True,
                    "at": utc_now(),
                },
            )
            try:
                devices, listing_sha256 = enumerate_download()
            except B0F1Error:
                publish_physical_observation_miss(
                    run_dir, prepared, arm, "identity-unproved", None, None
                )
                raise
            if len(devices) != 1:
                reason = "absent" if not devices else "ambiguous"
                publish_physical_observation_miss(
                    run_dir,
                    prepared,
                    arm,
                    reason,
                    len(devices),
                    listing_sha256,
                )
                raise B0F1Error("physical current Download arrival is unproved")
            try:
                endpoint = identify_download()
            except B0F1Error:
                publish_physical_observation_miss(
                    run_dir,
                    prepared,
                    arm,
                    "identity-unproved",
                    1,
                    listing_sha256,
                )
                raise
            if endpoint["device"] != devices[0]:
                publish_physical_observation_miss(
                    run_dir,
                    prepared,
                    arm,
                    "identity-unproved",
                    1,
                    listing_sha256,
                )
                raise B0F1Error("physical Download identity changed")
            arrival = {
                "endpoint": endpoint,
                "baseline_sha256": arm["baseline_sha256"],
                "arrival_listing_sha256": listing_sha256,
                "at": utc_now(),
            }
            arrival_branch = "reporting-cut-current-arrival"
        elif arm["branch"] == "already-download":
            try:
                devices, listing_sha256 = enumerate_download()
                if len(devices) != 1:
                    reason = "absent" if not devices else "ambiguous"
                    publish_physical_observation_miss(
                        run_dir,
                        prepared,
                        arm,
                        reason,
                        len(devices),
                        listing_sha256,
                    )
                    raise B0F1Error("already-present Download endpoint changed")
                endpoint = identify_download()
            except B0F1Error:
                if not os.path.lexists(run_dir / "physical-observation-miss.json"):
                    publish_physical_observation_miss(
                        run_dir, prepared, arm, "identity-unproved", None, None
                    )
                raise
            arrival = {
                "endpoint": endpoint,
                "baseline_sha256": None,
                "arrival_listing_sha256": listing_sha256,
                "at": utc_now(),
            }
            arrival_branch = "already-download-resumed"
        else:
            baseline = validate_download_baseline(
                arm["baseline"], "physical rollback arm baseline"
            )
            try:
                remaining = max(0.0, arm["expires_unix"] - time.time())
                arrival = wait_download(
                    baseline, timeout=min(DOWNLOAD_ARRIVAL_SECONDS, remaining)
                )
            except B0F1Error:
                publish_physical_observation_miss(
                    run_dir, prepared, arm, "identity-unproved", None, None
                )
                raise
            if arrival is None:
                publish_physical_observation_miss(
                    run_dir, prepared, arm, "bounded-wait-expired", 0, None
                )
                raise B0F1Error(
                    "physical Download arrival was not proved; observation consumed"
                )
            arrival_branch = "attended-entry"
        observed_unix = int(time.time())
        if observed_unix > arm["expires_unix"]:
            publish_physical_observation_miss(
                run_dir, prepared, arm, "arm-expired", None, None
            )
            raise B0F1Error("physical arrival missed its arm deadline")
        durable_json(
            arrival_path,
            {
                "schema": "s20plus_g986n_b0_physical_rollback_arrival_v1",
                "version": VERSION,
                "binding_sha256": prepared["binding_sha256"],
                "branch": arrival_branch,
                "observed_unix": observed_unix,
                **arrival,
            },
        )
    arrival_value = read_json(arrival_path, "physical rollback arrival")
    endpoint = arrival_value["endpoint"]
    current = identify_download()
    if not same_download_session(current, endpoint):
        raise B0F1Error("physical rollback endpoint changed")
    return rollback_from_arrival(run_dir, prepared, current)


def finalize_resident(run_dir: Path) -> dict[str, Any]:
    require_active()
    validate_health_closure()
    run_dir = validate_run_dir(run_dir)
    if os.path.lexists(run_dir / "terminal.json"):
        terminal = read_json(run_dir / "terminal.json", "B0 terminal")
        if guard_present():
            release_guard(run_dir)
        return terminal
    prepared = read_prepared(run_dir, phase="health")
    require_all_transfer_processes_quiescent(
        run_dir, prepared["binding_sha256"]
    )
    if not os.path.lexists(run_dir / "rollback-intent.json"):
        raise B0F1Error("final health has no consumed rollback intent")
    return final_health_and_terminal(run_dir, prepared)


def abort_return_cage_binding(run_dir: Path, endpoint: Any) -> str:
    return digest(
        {
            "schema": "s20plus_g986n_b0_abort_return_cage_binding_v1",
            "run_dir": str(run_dir),
            "endpoint": endpoint,
        }
    )


def payload_free_return(run_dir: Path, endpoint: dict[str, Any]) -> None:
    cage_binding_sha256 = abort_return_cage_binding(run_dir, endpoint)
    intent = {
        "schema": "s20plus_g986n_b0_abort_return_intent_v1",
        "version": VERSION,
        "endpoint": endpoint,
        "cage_binding_sha256": cage_binding_sha256,
        "command_shape": ["odin4", "--reboot", "-d", "USBFS"],
        "no_payload": True,
        "attempt": 1,
        "no_replay": True,
        "at": utc_now(),
    }
    with transport.pin_regular_file(
        ODIN,
        label="Odin4",
        expected_size=ODIN_SIZE,
        expected_sha256=ODIN_SHA256,
    ) as odin, transport.pin_regular_file(
        DASH,
        label="process-cage shell",
        expected_size=DASH_SIZE,
        expected_sha256=DASH_SHA256,
    ) as cage_shell:
        if endpoint_stat(endpoint["device"]) != tuple(endpoint["endpoint_identity"]):
            raise B0F1Error("abort endpoint changed before payload-free return")
        cage, _cage_record = prepare_process_cage(
            run_dir, "abort-return", cage_binding_sha256
        )
        intent["process_cage"] = _cage_record
        transport.revalidate_pinned_path(odin)
        transport.revalidate_pinned_path(cage_shell)
        durable_json(run_dir / "abort-return-intent.json", intent)
        handle: raw_capture.RawCaptureHandle | None = None
        try:
            if endpoint_stat(endpoint["device"]) != tuple(
                endpoint["endpoint_identity"]
            ):
                raise B0F1Error("abort endpoint changed at Odin dispatch boundary")
            handle = raw_capture.acquire_command(
                [
                    str(cage_shell.path),
                    "-c",
                    ODIN_CAGE_ENTRY_SCRIPT,
                    "s20plus-b0-abort-return-cage",
                    str(cage),
                    str(odin.path),
                    "--reboot",
                    "-d",
                    endpoint["device"],
                ],
                run_dir,
                "abort-return",
                timeout=120,
                stdout_maximum=MAX_ADB_BYTES,
                stderr_maximum=MAX_ADB_BYTES,
                env=ODIN_FIXED_ENV,
                stdout_name="abort-return.stdout",
                stderr_name="abort-return.stderr",
            )
        finally:
            quiesce_process_cage(
                run_dir, "abort-return", cage_binding_sha256
            )
        if handle is None:
            raise ProcessCageError("abort-return capture is unavailable")
        transport.revalidate_pinned_path(odin)
        transport.revalidate_pinned_path(cage_shell)
    stdout = raw_capture.read_stdout(handle, maximum=MAX_ADB_BYTES)
    stderr = raw_capture.read_stderr(handle, maximum=MAX_ADB_BYTES)
    if not stdout.startswith(ODIN_CAGE_ENTRY_MARKER):
        raise ProcessCageError("abort-return did not prove process-cage entry")
    durable_json(
        run_dir / "abort-return-result.json",
        {
            "schema": "s20plus_g986n_b0_abort_return_result_v1",
            "version": VERSION,
            "returncode": handle.returncode,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "outcome": "dispatched"
            if raw_dispatch_proved(handle, stderr)
            else "uncertain",
            "replay_permitted": False,
            "at": utc_now(),
        },
    )


def publish_abort_terminal(run_dir: Path, health: dict[str, Any]) -> dict[str, Any]:
    if os.path.lexists(run_dir / "preflight.json"):
        preflight = read_json(run_dir / "preflight.json", "B0 abort preflight")
        if health["boot_id_sha256"] == preflight.get("boot_id_sha256"):
            raise B0F1Error("abort final resident boot ID is not fresh")
    if not os.path.lexists(run_dir / "final-health.json"):
        durable_json(
            run_dir / "final-health.json",
            {
                "schema": "s20plus_g986n_b0_final_health_v1",
                "version": VERSION,
                "binding_sha256": None,
                "health": health,
                "rollback_transfer_completed": False,
                "rollback_outcome_proved": False,
                "resident_boot_healthy": True,
                "at": utc_now(),
            },
        )
    if os.path.lexists(run_dir / "terminal.json"):
        terminal = read_json(run_dir / "terminal.json", "B0 abort terminal")
    else:
        terminal = {
            "schema": "s20plus_g986n_b0_terminal_v1",
            "version": VERSION,
            "binding_sha256": None,
            "verdict": "ABORTED_PRE_CANDIDATE_RESIDENT_HEALTHY",
            "experiment_pass": False,
            "candidate_attempts": 0,
            "rollback_attempts": 0,
            "candidate_replay_permitted": False,
            "rollback_replay_permitted": False,
            "recovery_partition_reads": 0,
            "recovery_partition_writes": 0,
            "recovery_partition_transfers": 0,
            "other_target_commands": 0,
            "at": utc_now(),
        }
        durable_json(run_dir / "terminal.json", terminal)
    if guard_present():
        release_guard(run_dir)
    return terminal


def derive_abort_return_result(run_dir: Path) -> None:
    if os.path.lexists(run_dir / "abort-return-result.json"):
        return
    receipt_path = run_dir / "abort-return.capture.json"
    if not os.path.lexists(receipt_path):
        return
    intent = read_json(run_dir / "abort-return-intent.json", "abort return intent")
    quiesce_process_cage(
        run_dir, "abort-return", intent["cage_binding_sha256"]
    )
    handle = raw_capture.load_handle(receipt_path)
    stdout = raw_capture.read_stdout(handle, maximum=MAX_ADB_BYTES)
    stderr = raw_capture.read_stderr(handle, maximum=MAX_ADB_BYTES)
    if not stdout.startswith(ODIN_CAGE_ENTRY_MARKER):
        raise ProcessCageError("abort-return capture lacks process-cage entry")
    durable_json(
        run_dir / "abort-return-result.json",
        {
            "schema": "s20plus_g986n_b0_abort_return_result_v1",
            "version": VERSION,
            "returncode": handle.returncode,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "outcome": "dispatched"
            if raw_dispatch_proved(handle, stderr)
            else "uncertain",
            "replay_permitted": False,
            "at": utc_now(),
        },
    )


def abort_pre_candidate(run_dir: Path) -> dict[str, Any]:
    require_active()
    validate_health_closure()
    run_dir = validate_run_dir(run_dir)
    if os.path.lexists(run_dir / "terminal.json"):
        terminal = read_json(run_dir / "terminal.json", "B0 abort terminal")
        if guard_present():
            release_guard(run_dir)
        return terminal
    require_guard(run_dir)
    if os.path.lexists(run_dir / "candidate-intent.json") or candidate_claim_present():
        raise B0F1Error("candidate is consumed; pre-candidate abort is closed")
    if os.path.lexists(run_dir / "final-health.json"):
        final = read_json(run_dir / "final-health.json", "B0 abort final health")
        return publish_abort_terminal(run_dir, final["health"])
    preflight = (
        read_json(run_dir / "preflight.json", "B0 preflight")
        if os.path.lexists(run_dir / "preflight.json")
        else None
    )
    expected_serial = None if preflight is None else preflight.get("serial_sha256")
    try:
        health, _serial = resident_health_once(
            run_dir,
            "final-root",
            expected_serial,
        )
    except B0F1Error:
        health = None
    if health is None:
        if os.path.lexists(run_dir / "abort-return-intent.json"):
            abort_intent = read_json(
                run_dir / "abort-return-intent.json", "abort return intent"
            )
            quiesce_process_cage(
                run_dir,
                "abort-return",
                abort_intent["cage_binding_sha256"],
            )
            derive_abort_return_result(run_dir)
        else:
            endpoint = identify_download()
            payload_free_return(run_dir, endpoint)
        deadline = time.monotonic() + ANDROID_ARRIVAL_SECONDS
        while time.monotonic() < deadline:
            try:
                health, _serial = resident_health_once(
                    run_dir,
                    "final-root",
                    expected_serial,
                )
                break
            except B0F1Error:
                time.sleep(3)
        else:
            return {
                "schema": "s20plus_g986n_b0_recovery_pending_v1",
                "run_dir": str(run_dir),
                "binding_sha256": None,
                "verdict": "PRE_CANDIDATE_RETURN_CONSUMED_HEALTH_PENDING",
                "candidate_replay_permitted": False,
                "rollback_replay_permitted": False,
            }
    return publish_abort_terminal(run_dir, health)


def render_plan() -> dict[str, Any]:
    return {
        "schema": PLAN_SCHEMA,
        "version": VERSION,
        "status": (
            "BINDING_ATTENDED_BOOT_ONLY_F1_ACTIVE"
            if B0_F1_ACTIVE
            else "H0_REVIEW_PENDING_NOT_ACTIVE"
        ),
        "active": B0_F1_ACTIVE,
        "live_authority": B0_F1_ACTIVE,
        "target": dict(TARGET),
        "adb_selection": {
            "global_inventory": True,
            "exact_target_match_count": 1,
            "foreign_rows_permitted": True,
            "selected_target_commands_require_serial": True,
            "other_target_commands": 0,
        },
        "candidate": {
            "partition": "boot",
            "ap_size": CANDIDATE_AP_SIZE,
            "ap_sha256": CANDIDATE_AP_SHA256,
            "member": "boot.img.lz4",
        },
        "rollback": {
            "partition": "boot",
            "mandatory": True,
            "ap_size": ROLLBACK_AP_SIZE,
            "ap_sha256": ROLLBACK_AP_SHA256,
            "member": "boot.img.lz4",
        },
        "forbidden": {
            "recovery_partition_read": True,
            "recovery_partition_write": True,
            "recovery_partition_transfer": True,
            "candidate_replay": True,
            "rollback_replay": True,
            "caller_selected_path": True,
            "caller_selected_command": True,
        },
        "approval_after_fresh_prepare": True,
        "shared_guard": str(SHARED_GUARD),
        "global_candidate_consumed_claim": str(claim_path()),
        "modes": [
            "render-plan",
            "validate-host",
            "prepare",
            "execute",
            "resume",
            "arm-physical-rollback",
            "confirm-physical-rollback",
            "finalize-resident",
            "abort-pre-candidate",
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--render-plan", action="store_true")
    modes.add_argument("--validate-host", action="store_true")
    modes.add_argument("--prepare", action="store_true")
    modes.add_argument("--execute", action="store_true")
    modes.add_argument("--resume", action="store_true")
    modes.add_argument("--arm-physical-rollback", action="store_true")
    modes.add_argument("--confirm-physical-rollback", action="store_true")
    modes.add_argument("--finalize-resident", action="store_true")
    modes.add_argument("--abort-pre-candidate", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--approval")
    parser.add_argument("--confirmation")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.render_plan:
        print(json.dumps(render_plan(), sort_keys=True))
        return 0
    if args.validate_host:
        try:
            closure = validate_host_closure()
        except Exception as exc:
            print(
                json.dumps(
                    {
                        "schema": PLAN_SCHEMA,
                        "verdict": "STOP_B0_HOST_CLOSURE",
                        "failure_class": type(exc).__name__,
                        "live_authority": False,
                    },
                    sort_keys=True,
                )
            )
            return 2
        print(
            json.dumps(
                {
                    "schema": PLAN_SCHEMA,
                    "verdict": "PASS_B0_HOST_CLOSURE_ONLY",
                    "closure_sha256": digest(closure),
                    "live_authority": False,
                },
                sort_keys=True,
            )
        )
        return 0
    if not B0_F1_ACTIVE:
        print("STOP_S20PLUS_G986N_BOOT_RECOVERY_CANARY_B0_F1_NOT_ACTIVE")
        return 3
    try:
        if args.prepare:
            run_dir = prepare(args.run_dir)
            prepared = read_prepared(run_dir, phase="candidate")
            print(f"run_dir={run_dir}")
            print(f"approval={prepared['approval_token']}")
            return 0
        if args.run_dir is None:
            raise B0F1Error("--run-dir is required")
        run_dir = args.run_dir.absolute()
        if args.execute:
            result = execute(run_dir, args.approval or "")
        elif args.resume:
            result = resume_run(run_dir)
        elif args.arm_physical_rollback:
            result = arm_physical_rollback(run_dir)
        elif args.confirm_physical_rollback:
            result = confirm_physical_rollback(run_dir, args.confirmation or "")
        elif args.finalize_resident:
            result = finalize_resident(run_dir)
        else:
            result = abort_pre_candidate(run_dir)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"STOP_B0_F1:{type(exc).__name__}:{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
