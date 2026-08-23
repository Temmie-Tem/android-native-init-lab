#!/usr/bin/env python3
"""Audit the exact FYD9-to-FYG8 source delta and its USB-only semantics.

This is a host-only P3.19 analysis.  It reads the pinned Samsung FYD9 base
archive, the pinned FYG8 overlay, and the already materialized P290 source
tree.  It never invokes a compiler, subprocess, device transport, ADB, USB,
Odin, or a partition tool and grants no connected or live authority.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import stat
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO


REPO = Path(__file__).resolve().parents[5]
PRIVATE = REPO / "workspace/private"
BASE_ARCHIVE = (
    PRIVATE
    / "inputs/s22plus_kernel_source/SM-S906N_15_base_osrc/Kernel.tar.gz"
)
DELTA_ARCHIVE = (
    PRIVATE
    / "inputs/s22plus_kernel_source/S906NKSS7FYG8_osrc/"
    "S906NKSS7FYG8_kernel.tar.gz"
)
BUILD_ROOT = PRIVATE / "work/s22plus_fyg8_kernel_build_p290_2ec2bbae"
KERNEL_ROOT = BUILD_ROOT / "kernel_platform/msm-kernel"
OUTPUT_ROOT = (
    PRIVATE
    / "outputs/s22plus_fyg8_p319/"
    "fyd9-fyg8-usb-delta-audit-20260823-03"
)
OUTPUT = OUTPUT_ROOT / "result.json"

STOCK_REPORT = (
    REPO
    / "docs/reports/"
    "S22PLUS_FYG8_P319_STOCK_USERSPACE_CHOREOGRAPHY_H0_2026-08-19.md"
)
ROLE_REPORT = (
    REPO
    / "docs/reports/"
    "S22PLUS_FYG8_NATURAL_ATTACH_ROLE_PRODUCER_CLOSURE_H0_2026-08-11.md"
)

SCHEMA = "s22plus-fyg8-p319-fyd9-fyg8-usb-delta-audit-v1"
VERDICT = "PASS_P319_FYD9_FYG8_USB_DELTA_H0"
STATUS = "IMPLEMENTED_REVIEW_PENDING"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"

EXPECTED_BASE = {
    "size": 566_244_738,
    "sha256": "86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf",
}
EXPECTED_DELTA = {
    "size": 1_421_025,
    "sha256": "23ef2b27de8843e271d41405b3c0b1a71bfa668615c8f0f12a1e5c4395ec851a",
}
EXPECTED_BASE_MEMBER_COUNT = 166_037
EXPECTED_DELTA_MEMBER_COUNT = 51
EXPECTED_CHANGED_FILE_COUNT = 22
EXPECTED_IDENTICAL_DIRECTORY_COUNT = 29

USB_NOTIFY = "kernel_platform/msm-kernel/drivers/usb/notify/usb_notify.c"
USB_SYSFS = "kernel_platform/msm-kernel/drivers/usb/notify/usb_notify_sysfs.c"
USB_PATHS = (USB_NOTIFY, USB_SYSFS)
USB_DIFFS = {
    USB_NOTIFY: {
        "bytes": 1_056,
        "sha256": "bd4cef5c1cee87a44109a2a4cb548054bffe4a14de225c5399b3c85620b54227",
        "added_lines": 8,
        "removed_lines": 1,
        "base_size": 96_378,
        "base_sha256": "f9b94f7ef92f66391402ed51d3010ded22e1dc576632cca23e168b32c987b7a9",
        "delta_size": 96_602,
        "delta_sha256": "cdb489a2aecd3dc4c7d00899421d827c2aa64cd865e931b3a6cc6a3aa540d02b",
    },
    USB_SYSFS: {
        "bytes": 1_484,
        "sha256": "24b438c505ade0ec9b5b5e829256aac828a02cabc7b11ac1c1c809629526a8bb",
        "added_lines": 27,
        "removed_lines": 3,
        "base_size": 31_527,
        "base_sha256": "f3eb53ba717db2eaf81116b755d7bf7e9b2dff5f89f73a4518ef663a65181c33",
        "delta_size": 31_895,
        "delta_sha256": "e538e7848a14d0e5bcc20b5f1763bc49018c5903341ed0a049fa7f16bb8067f5",
    },
}

DTS_REVISIONS = ("r01", "r02", "r04", "r05", "r06", "r07", "r08", "r09", "r10", "r11", "r12")
DTS_PATHS = tuple(
    "kernel_platform/msm-kernel/arch/arm64/boot/dts/samsung/rainbow/g0q/"
    f"g0q_kor_singlex_w00_{revision}.dts"
    for revision in DTS_REVISIONS
)

NFC_PATHS = (
    "kernel_platform/msm-kernel/drivers/nfc/snvm/hal/ese_hal.c",
    "kernel_platform/msm-kernel/drivers/nfc/snvm/protocol/ese_data.c",
    "kernel_platform/msm-kernel/drivers/nfc/snvm/protocol/ese_iso7816_t1.c",
    "kernel_platform/msm-kernel/drivers/nfc/snvm/sec_k250a.c",
    "kernel_platform/msm-kernel/drivers/nfc/snvm/sec_star.c",
)
MEDIA_PATHS = (
    "kernel_platform/common/drivers/media/platform/qcom/venus/hfi_venus.c",
    "kernel_platform/msm-kernel/drivers/media/platform/qcom/venus/hfi_venus.c",
)
DEFEX_PATHS = (
    "kernel_platform/common/security/samsung/defex_lsm/defex_packed_rules.bin",
    "kernel_platform/common/security/samsung/defex_lsm/defex_rules.c",
)
EXPECTED_CHANGED_PATHS = tuple(
    sorted((*DTS_PATHS, *USB_PATHS, *NFC_PATHS, *MEDIA_PATHS, *DEFEX_PATHS))
)


@dataclass(frozen=True)
class InputSpec:
    relative: str
    size: int
    sha256: str


AUXILIARY_SOURCES = {
    "kconfig": InputSpec(
        "kernel_platform/msm-kernel/drivers/usb/notify/Kconfig",
        4_427,
        "ec9312e5784723505bce9a1ff93abe76e22250ef1d9fa09966c8ec54795a9fbb",
    ),
    "waipio_gki_defconfig": InputSpec(
        "kernel_platform/msm-kernel/arch/arm64/configs/vendor/waipio-gki_defconfig",
        35_621,
        "de7373038099658387dea7f2168be3c63268c554c645067e255492cb836276c7",
    ),
    "waipio_sec_defconfig": InputSpec(
        "kernel_platform/msm-kernel/arch/arm64/configs/vendor/waipio_sec_defconfig",
        3_126,
        "9629cc3d886e7840b2106af881019a442806981eab24eb12716885f16552c7ba",
    ),
    "typec_manager": InputSpec(
        "kernel_platform/msm-kernel/drivers/usb/typec/manager/usb_typec_manager_notifier.c",
        54_169,
        "4a8c8b419e37184bb571f19474a0887f260aafeb174fec113c5549de50030d0c",
    ),
    "dwc3_core": InputSpec(
        "kernel_platform/msm-kernel/drivers/usb/dwc3/dwc3-msm-core.c",
        204_659,
        "1c8a3cea43337eebaf0601e01fe3a17e1260f2f768298b16f723534eee433021",
    ),
    "usb_notifier_qcom": InputSpec(
        "kernel_platform/msm-kernel/drivers/usb/notify/usb_notifier_qcom.c",
        16_840,
        "b6ecb5742539db17cf1d6d499c62c1e6f4103f960682ac54b078feabd568fd2a",
    ),
    "usb_notify_header": InputSpec(
        "kernel_platform/msm-kernel/include/linux/usb_notify.h",
        11_708,
        "ec002ba79febde8a63dc090caf48ac14916c3a98ecfd229ea991f68027852fff",
    ),
}

DOCUMENTS = {
    "stock_choreography": {
        "path": STOCK_REPORT,
        "size": 210_769,
        "sha256": "4c03f5b82a553cc16c669f5ae6fb9907b135314cc123e28a0b650989718a83cd",
    },
    "role_producer": {
        "path": ROLE_REPORT,
        "size": 12_755,
        "sha256": "503cec433b64d330fe09fb32f296cc1a50965fff0af6c7cdc8e86e16c88be5bb",
    },
}


class AuditError(RuntimeError):
    pass


def _receipt(data: bytes) -> dict[str, Any]:
    return {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_nlink,
        info.st_size,
        info.st_mtime_ns,
    )


def _stable_read(path: Path, label: str, limit: int = 4 * 1024 * 1024) -> bytes:
    try:
        before_l = path.lstat()
        before = path.stat()
    except OSError as exc:
        raise AuditError(f"{label} is unavailable: {path}") from exc
    if stat.S_ISLNK(before_l.st_mode) or not stat.S_ISREG(before.st_mode):
        raise AuditError(f"{label} is not a direct regular file")
    if before.st_nlink < 1 or not 0 <= before.st_size <= limit:
        raise AuditError(f"{label} size/link contract differs")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
        inside = os.fstat(stream.fileno())
    after = path.stat()
    if _identity(before) != _identity(inside) or _identity(inside) != _identity(after):
        raise AuditError(f"{label} changed while read")
    if len(data) != before.st_size or len(data) > limit:
        raise AuditError(f"{label} read length differs")
    return data


def _safe_member_path(name: str, *, delta: bool) -> str | None:
    if not name or name.startswith("/"):
        raise AuditError(f"unsafe archive member path: {name!r}")
    path = PurePosixPath(name.rstrip("/"))
    if any(part in ("", ".", "..") for part in path.parts):
        raise AuditError(f"unsafe archive member path: {name!r}")
    parts = list(path.parts)
    if delta:
        if not parts or parts[0] != "Kernel":
            raise AuditError(f"delta member lacks exact Kernel/ prefix: {name!r}")
        parts = parts[1:]
        if not parts:
            return None
    return PurePosixPath(*parts).as_posix()


def _verify_archive_identity(
    stream: BinaryIO,
    path: Path,
    before: os.stat_result,
    expected: dict[str, Any],
) -> None:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    observed = {"size": before.st_size, "sha256": digest.hexdigest()}
    if observed != expected:
        raise AuditError(f"archive identity differs: {path}: {observed}")
    stream.seek(0)


def _open_checked_archive(path: Path, expected: dict[str, Any]):
    before_l = path.lstat()
    before = path.stat()
    if stat.S_ISLNK(before_l.st_mode) or not stat.S_ISREG(before.st_mode):
        raise AuditError(f"archive is not a direct regular file: {path}")
    if before.st_nlink < 1:
        raise AuditError(f"archive link count differs: {path}")
    stream = path.open("rb")
    inside = os.fstat(stream.fileno())
    if _identity(before) != _identity(inside):
        stream.close()
        raise AuditError(f"archive changed before read: {path}")
    _verify_archive_identity(stream, path, before, expected)
    return stream, before


@dataclass
class OverlayClosure:
    base_member_count: int
    delta_members: dict[str, str]
    base_files: dict[str, bytes]
    delta_files: dict[str, bytes]


def load_overlay_closure() -> OverlayClosure:
    delta_stream, delta_before = _open_checked_archive(DELTA_ARCHIVE, EXPECTED_DELTA)
    delta_members: dict[str, str] = {}
    delta_files: dict[str, bytes] = {}
    try:
        with tarfile.open(fileobj=delta_stream, mode="r:gz") as archive:
            for info in archive:
                path = _safe_member_path(info.name, delta=True)
                if path is None:
                    continue
                if path in delta_members:
                    raise AuditError(f"duplicate normalized delta member: {path}")
                if info.isdir():
                    delta_members[path] = "directory"
                    continue
                if not info.isfile():
                    raise AuditError(f"unsupported delta member type: {info.name}")
                extracted = archive.extractfile(info)
                if extracted is None:
                    raise AuditError(f"could not read delta member: {info.name}")
                with extracted:
                    data = extracted.read()
                if len(data) != info.size:
                    raise AuditError(f"short delta member read: {info.name}")
                delta_members[path] = "file"
                delta_files[path] = data
        after = DELTA_ARCHIVE.stat()
        if _identity(delta_before) != _identity(after):
            raise AuditError("delta archive changed while read")
    finally:
        delta_stream.close()

    if len(delta_members) != EXPECTED_DELTA_MEMBER_COUNT:
        raise AuditError("delta member count differs")
    if len(delta_files) != EXPECTED_CHANGED_FILE_COUNT:
        raise AuditError("delta regular-file count differs")
    if sum(kind == "directory" for kind in delta_members.values()) != EXPECTED_IDENTICAL_DIRECTORY_COUNT:
        raise AuditError("delta directory count differs")

    wanted = set(delta_members)
    base_files: dict[str, bytes] = {}
    base_kinds: dict[str, str] = {}
    base_count = 0
    base_stream, base_before = _open_checked_archive(BASE_ARCHIVE, EXPECTED_BASE)
    try:
        with tarfile.open(fileobj=base_stream, mode="r:gz") as archive:
            for info in archive:
                path = _safe_member_path(info.name, delta=False)
                if path is None:
                    continue
                base_count += 1
                if path not in wanted:
                    continue
                if info.isdir():
                    base_kinds[path] = "directory"
                    continue
                if not info.isfile():
                    raise AuditError(f"selected base member is not file/directory: {path}")
                extracted = archive.extractfile(info)
                if extracted is None:
                    raise AuditError(f"could not read selected base member: {path}")
                with extracted:
                    data = extracted.read()
                if len(data) != info.size:
                    raise AuditError(f"short selected base member read: {path}")
                base_kinds[path] = "file"
                base_files[path] = data
        after = BASE_ARCHIVE.stat()
        if _identity(base_before) != _identity(after):
            raise AuditError("base archive changed while read")
    finally:
        base_stream.close()

    if base_count != EXPECTED_BASE_MEMBER_COUNT:
        raise AuditError(f"base member count differs: {base_count}")
    if set(base_kinds) != wanted:
        raise AuditError("delta contains a member absent from FYD9 base")
    if any(base_kinds[path] != kind for path, kind in delta_members.items()):
        raise AuditError("base/delta selected member types differ")
    if set(base_files) != set(delta_files):
        raise AuditError("base/delta regular-file sets differ")
    if any(base_files[path] == data for path, data in delta_files.items()):
        raise AuditError("a delta regular file is byte-identical to FYD9")

    return OverlayClosure(base_count, delta_members, base_files, delta_files)


def _diff_text(path: str, old: bytes, new: bytes) -> str:
    try:
        old_lines = old.decode("utf-8").splitlines()
        new_lines = new.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise AuditError(f"text diff input is not UTF-8: {path}") from exc
    return "\n".join(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"FYD9/{path}",
            tofile=f"FYG8/{path}",
            lineterm="",
        )
    ) + "\n"


def _changed_lines(old: bytes, new: bytes) -> tuple[list[str], list[str]]:
    old_lines = old.decode("utf-8").splitlines()
    new_lines = new.decode("utf-8").splitlines()
    removed: list[str] = []
    added: list[str] = []
    matcher = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
    for op, a0, a1, b0, b1 in matcher.get_opcodes():
        if op in ("replace", "delete"):
            removed.extend(old_lines[a0:a1])
        if op in ("replace", "insert"):
            added.extend(new_lines[b0:b1])
    return removed, added


def _require_once(text: str, token: str, label: str) -> None:
    count = text.count(token)
    if count != 1:
        raise AuditError(f"{label} occurrence count differs: {count}")


def audit_usb_delta(base_files: dict[str, bytes], delta_files: dict[str, bytes]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in USB_PATHS:
        old = base_files[path]
        new = delta_files[path]
        expected = USB_DIFFS[path]
        if _receipt(old) != {
            "size": expected["base_size"],
            "sha256": expected["base_sha256"],
        }:
            raise AuditError(f"FYD9 USB source identity differs: {path}")
        if _receipt(new) != {
            "size": expected["delta_size"],
            "sha256": expected["delta_sha256"],
        }:
            raise AuditError(f"FYG8 USB source identity differs: {path}")
        patch = _diff_text(path, old, new).encode("utf-8")
        patch_receipt = _receipt(patch)
        if patch_receipt != {"size": expected["bytes"], "sha256": expected["sha256"]}:
            raise AuditError(f"FYD9/FYG8 USB patch differs: {path}")
        removed, added = _changed_lines(old, new)
        if (len(added), len(removed)) != (expected["added_lines"], expected["removed_lines"]):
            raise AuditError(f"FYD9/FYG8 USB line counts differ: {path}")
        rows.append(
            {
                "path": path,
                "base": _receipt(old),
                "delta": _receipt(new),
                "unified_diff": patch_receipt,
                "added_lines": len(added),
                "removed_lines": len(removed),
            }
        )

    old_notify = base_files[USB_NOTIFY].decode("utf-8")
    new_notify = delta_files[USB_NOTIFY].decode("utf-8")
    reserve_hook = """\
\tif (u_noti->lock_state == USB_NOTIFY_INIT_STATE) {
\t\tu_noti->udev.first_restrict = true;
\t\tset_notify_disable(&u_noti->udev, NOTIFY_BLOCK_TYPE_HOST);
\t\tu_noti->skip_possible_usb = 1;
\t}
"""
    if reserve_hook in old_notify:
        raise AuditError("FYG8 reserve hook already exists in FYD9 source")
    _require_once(new_notify, reserve_hook, "FYG8 reserve hook")
    wake_predicate = """\
\twait_event_interruptible(u_noti->init_delay,
\t\t(u_noti->lock_state != USB_NOTIFY_INIT_STATE
\t\t\t|| u_noti->b_delay.reserve_state == NOTIFY_EVENT_VBUS));
"""
    _require_once(new_notify, wake_predicate, "reserve wake predicate")
    _require_once(
        new_notify,
        "if (!u_noti->skip_possible_usb)\n\t\tsend_external_notify(EXTERNAL_NOTIFY_POSSIBLE_USB, 1);",
        "POSSIBLE_USB suppression",
    )
    disable_start = new_notify.index("static int set_notify_disable(struct usb_notify_dev *udev, int disable)\n{")
    host_case_start = new_notify.index("case NOTIFY_BLOCK_TYPE_HOST:", disable_start)
    client_case_start = new_notify.index("case NOTIFY_BLOCK_TYPE_CLIENT:", host_case_start)
    host_case = new_notify[host_case_start:client_case_start]
    _require_once(
        host_case,
        "send_otg_notify(n, NOTIFY_EVENT_HOST_DISABLE, 1);",
        "HOST disable event",
    )
    if "NOTIFY_EVENT_CLIENT_DISABLE" in host_case or "NOTIFY_EVENT_ALL_DISABLE" in host_case:
        raise AuditError("HOST disable case widens to CLIENT or ALL")
    event_start = new_notify.index("case NOTIFY_EVENT_HOST_DISABLE:", client_case_start)
    event_end = new_notify.index("case NOTIFY_EVENT_CLIENT_DISABLE:", event_start)
    event_case = new_notify[event_start:event_end]
    _require_once(
        event_case,
        "clear_bit(NOTIFY_BLOCK_TYPE_CLIENT,\n\t\t\t\t&u_notify->udev.disable_state);",
        "HOST event clears CLIENT bit",
    )
    _require_once(
        event_case,
        "set_bit(NOTIFY_BLOCK_TYPE_HOST,\n\t\t\t\t&u_notify->udev.disable_state);",
        "HOST event sets HOST bit",
    )

    old_sysfs = base_files[USB_SYSFS].decode("utf-8")
    new_sysfs = delta_files[USB_SYSFS].decode("utf-8")
    _require_once(new_sysfs, "static bool valid_secure_lock_value(unsigned long secure_lock)", "usb_sl validator")
    for value in (
        "USB_NOTIFY_LOCK_USB_RESTRICT",
        "USB_NOTIFY_LOCK_USB_WORK",
        "USB_NOTIFY_UNLOCK",
    ):
        if new_sysfs.count(f"case {value}:") < 1:
            raise AuditError(f"usb_sl admitted value is absent: {value}")
    if "valid_secure_lock_value" in old_sysfs:
        raise AuditError("usb_sl validator unexpectedly exists in FYD9")
    old_release = "udev->first_restrict && prev_secure_lock == USB_NOTIFY_LOCK_USB_RESTRICT"
    new_release = """\
udev->first_restrict
\t\t\t\t\t&& (secure_lock == USB_NOTIFY_UNLOCK
\t\t\t\t\t\t\t|| secure_lock == USB_NOTIFY_LOCK_USB_WORK)"""
    _require_once(old_sysfs, old_release, "FYD9 release predecessor gate")
    if old_release in new_sysfs:
        raise AuditError("FYG8 usb_sl release still requires the predecessor state")
    _require_once(new_sysfs, new_release, "FYG8 first-restrict release gate")

    return {
        "changed_paths": list(USB_PATHS),
        "rows": rows,
        "reserve_state_check": {
            "wake_predicates": [
                "lock_state != USB_NOTIFY_INIT_STATE",
                "reserve_state == NOTIFY_EVENT_VBUS",
            ],
            "still_init_effects": [
                "first_restrict=true",
                "set_notify_disable(NOTIFY_BLOCK_TYPE_HOST)",
                "skip_possible_usb=1",
            ],
            "possible_usb_event_suppressed_when_skip_is_set": True,
            "host_disable_transition": {
                "emitted_event": "NOTIFY_EVENT_HOST_DISABLE",
                "client_bit_cleared": True,
                "host_bit_set": True,
                "widens_to_all": False,
            },
        },
        "usb_sl_store": {
            "accepted_values": [
                "USB_NOTIFY_LOCK_USB_RESTRICT",
                "USB_NOTIFY_LOCK_USB_WORK",
                "USB_NOTIFY_UNLOCK",
            ],
            "rejects_other_numeric_values": True,
            "release_requires_first_restrict": True,
            "release_requires_previous_restrict_state": False,
        },
    }


def audit_dts_delta(base_files: dict[str, bytes], delta_files: dict[str, bytes]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for revision, path in zip(DTS_REVISIONS, DTS_PATHS, strict=True):
        removed, added = _changed_lines(base_files[path], delta_files[path])
        if len(removed) != 13 or len(added) != 13:
            raise AuditError(f"DTS change count differs: {revision}")
        if {line.strip() for line in removed} != {"temperature = <0x14c08>;"}:
            raise AuditError(f"DTS removed values differ: {revision}")
        if {line.strip() for line in added} != {"temperature = <0x13880>;"}:
            raise AuditError(f"DTS added values differ: {revision}")
        rows.append(
            {
                "revision": revision,
                "path": path,
                "old_raw_value": "0x14c08",
                "old_decimal_value": 85_000,
                "new_raw_value": "0x13880",
                "new_decimal_value": 80_000,
                "replacement_count": 13,
                "other_changed_lines": 0,
                "usb_token_in_changed_lines": False,
            }
        )
    return rows


def _category(path: str) -> str:
    if path in DTS_PATHS:
        return "dts_thermal"
    if path in USB_PATHS:
        return "usb_notify"
    if path in NFC_PATHS:
        return "nfc_snvm"
    if path in MEDIA_PATHS:
        return "venus_media"
    if path in DEFEX_PATHS:
        return "defex"
    raise AuditError(f"uncategorized changed path: {path}")


def load_auxiliary_sources() -> dict[str, bytes]:
    loaded: dict[str, bytes] = {}
    for name, spec in AUXILIARY_SOURCES.items():
        data = _stable_read(BUILD_ROOT / spec.relative, f"auxiliary source {name}")
        if _receipt(data) != {"size": spec.size, "sha256": spec.sha256}:
            raise AuditError(f"auxiliary source identity differs: {name}")
        loaded[name] = data
    return loaded


def audit_auxiliary_sources(loaded: dict[str, bytes]) -> dict[str, Any]:
    text = {name: data.decode("utf-8") for name, data in loaded.items()}
    for name in ("waipio_gki_defconfig", "waipio_sec_defconfig"):
        _require_once(text[name], "CONFIG_USB_NOTIFY_LAYER=m", f"{name} USB_NOTIFY_LAYER")
        _require_once(text[name], "CONFIG_USB_NOTIFIER=m", f"{name} USB_NOTIFIER")
        if "CONFIG_DISABLE_LOCKSCREEN_USB_RESTRICTION" in text[name]:
            raise AuditError(f"{name} unexpectedly sets the restriction-disable option")

    kconfig = text["kconfig"]
    start = kconfig.index("config DISABLE_LOCKSCREEN_USB_RESTRICTION")
    end = kconfig.find("\nconfig ", start + 1)
    stanza = kconfig[start : len(kconfig) if end == -1 else end]
    if "\n\tdefault " in stanza:
        raise AuditError("restriction-disable Kconfig unexpectedly has a default")

    header = text["usb_notify_header"]
    _require_once(header, "NOTIFY_BLOCK_TYPE_HOST = (1 << 0)", "HOST block bit")
    _require_once(header, "NOTIFY_BLOCK_TYPE_CLIENT = (1 << 1)", "CLIENT block bit")

    manager = text["typec_manager"]
    possible_case = """\
case EXTERNAL_NOTIFY_POSSIBLE_USB:
\t\tpr_info("%s EXTERNAL_NOTIFY_POSSIBLE_USB, enable=%d\\n", __func__, enable);
\t\tmanager_set_alternate_mode(MANAGER_NOTIFY_PDIC_DELAY_DONE);"""
    _require_once(manager, possible_case, "POSSIBLE_USB downstream")

    dwc3 = text["dwc3_core"]
    mode_gate = """\
#ifdef CONFIG_USB_NOTIFIER
\tif (role == USB_ROLE_DEVICE) {
\t\tif (is_blocked(get_otg_notify(), NOTIFY_BLOCK_TYPE_CLIENT)) {"""
    _require_once(dwc3, mode_gate, "DWC3 module-value-inactive client gate")

    qcom = text["usb_notifier_qcom"]
    ufp_path = """\
case USB_STATUS_NOTIFY_ATTACH_UFP:
\t\tpr_info("%s: Turn On Device(UFP)\\n", __func__);"""
    _require_once(qcom, ufp_path, "UFP notifier path")
    ufp_start = qcom.index(ufp_path)
    ufp_end = qcom.index("case USB_STATUS_NOTIFY_DETACH:", ufp_start)
    ufp_block = qcom[ufp_start:ufp_end]
    _require_once(
        ufp_block,
        "send_otg_notify(o_notify, NOTIFY_EVENT_VBUS, 1);",
        "UFP VBUS notify",
    )
    disabled_client_gate = """\
#ifdef CONFIG_DISABLE_LOCKSCREEN_USB_RESTRICTION\t\t
\t\tif (is_blocked(o_notify, NOTIFY_BLOCK_TYPE_CLIENT))"""
    _require_once(ufp_block, disabled_client_gate, "restriction-disable client gate")

    return {
        "inputs": {
            name: {
                "path": spec.relative,
                **_receipt(loaded[name]),
            }
            for name, spec in AUXILIARY_SOURCES.items()
        },
        "configuration": {
            "waipio_gki": {"USB_NOTIFY_LAYER": "m", "USB_NOTIFIER": "m"},
            "waipio_sec": {"USB_NOTIFY_LAYER": "m", "USB_NOTIFIER": "m"},
            "DISABLE_LOCKSCREEN_USB_RESTRICTION_explicit": False,
            "DISABLE_LOCKSCREEN_USB_RESTRICTION_default": False,
            "target_defconfigs_do_not_disable_restriction_branch": True,
            "shipped_binary_reachability_proved_here": False,
        },
        "downstream": {
            "host_and_client_block_bits_are_distinct": True,
            "possible_usb_maps_to_pdic_delay_done": True,
            "dwc3_mode_store_client_gate_uses_ifdef_USB_NOTIFIER": True,
            "USB_NOTIFIER_module_value_satisfies_that_ifdef": False,
            "ufp_path_sends_vbus_before_disabled_client_gate": True,
        },
    }


def audit_documents() -> dict[str, Any]:
    loaded: dict[str, bytes] = {}
    identities: dict[str, Any] = {}
    for name, spec in DOCUMENTS.items():
        data = _stable_read(spec["path"], f"bound document {name}")
        expected = {"size": spec["size"], "sha256": spec["sha256"]}
        if _receipt(data) != expected:
            raise AuditError(f"bound document identity differs: {name}")
        loaded[name] = data
        identities[name] = {
            "path": str(spec["path"].relative_to(REPO)),
            **expected,
        }
    stock = loaded["stock_choreography"].decode("utf-8")
    role = loaded["role_producer"].decode("utf-8")
    for token in (
        "| **Download** | ABL → Odin | `MuicSetPath(1)` → `0x09` **COM_USB**, then enumeration |",
        "**No normal boot in the corpus writes `COM_USB`.**",
    ):
        _require_once(stock, token, "Download positive-control statement")
    if "first_restrict" in role or "skip_possible_usb" in role:
        raise AuditError("predecessor role report already names the FYG8 post-wait hook")
    _require_once(
        role,
        "`reserve_state_check()` waits until `lock_state` leaves\n   `USB_NOTIFY_INIT_STATE` for a HOST event.",
        "predecessor reserve-state wording",
    )
    return {
        "inputs": identities,
        "download_positive_control_already_documented": True,
        "normal_boot_com_open_and_download_com_usb_are_distinct": True,
        "predecessor_role_report_omits_fyg8_post_wait_hook": True,
        "correction_required": (
            "reserve_state_check can wake on reserved VBUS while lock_state is still INIT, "
            "then install the FYG8 HOST restriction and suppress POSSIBLE_USB"
        ),
    }


def _changed_rows(closure: OverlayClosure) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    build_matches = 0
    for path in sorted(closure.delta_files):
        if path not in EXPECTED_CHANGED_PATHS:
            raise AuditError(f"unexpected changed file: {path}")
        built = _stable_read(BUILD_ROOT / path, f"P290 applied source {path}")
        if built != closure.delta_files[path]:
            raise AuditError(f"P290 source differs from FYG8 delta: {path}")
        build_matches += 1
        old = closure.base_files[path]
        new = closure.delta_files[path]
        row: dict[str, Any] = {
            "path": path,
            "category": _category(path),
            "base": _receipt(old),
            "delta": _receipt(new),
            "p290_applied_match": True,
        }
        try:
            removed, added = _changed_lines(old, new)
        except UnicodeDecodeError:
            row["text_diff"] = False
        else:
            row.update(
                {
                    "text_diff": True,
                    "added_lines": len(added),
                    "removed_lines": len(removed),
                }
            )
        rows.append(row)
    if tuple(row["path"] for row in rows) != EXPECTED_CHANGED_PATHS:
        raise AuditError("changed-path set differs")
    if build_matches != EXPECTED_CHANGED_FILE_COUNT:
        raise AuditError("P290 applied-source match count differs")
    return rows


def build_result(
    closure: OverlayClosure | None = None,
    auxiliary: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    if closure is None:
        closure = load_overlay_closure()
    if auxiliary is None:
        auxiliary = load_auxiliary_sources()
    changed_rows = _changed_rows(closure)
    usb = audit_usb_delta(closure.base_files, closure.delta_files)
    dts = audit_dts_delta(closure.base_files, closure.delta_files)
    downstream = audit_auxiliary_sources(auxiliary)
    documents = audit_documents()
    categories: dict[str, int] = {}
    for row in changed_rows:
        category = str(row["category"])
        categories[category] = categories.get(category, 0) + 1
    if categories != {
        "defex": 2,
        "dts_thermal": 11,
        "nfc_snvm": 5,
        "usb_notify": 2,
        "venus_media": 2,
    }:
        raise AuditError(f"changed-file category census differs: {categories}")
    auditor = _stable_read(Path(__file__).resolve(), "auditor source")
    return {
        "schema": SCHEMA,
        "verdict": VERDICT,
        "status": STATUS,
        "target": TARGET,
        "auditor": {
            "path": str(Path(__file__).resolve().relative_to(REPO)),
            **_receipt(auditor),
        },
        "inputs": {
            "fyd9_base_archive": {
                "path": str(BASE_ARCHIVE.relative_to(REPO)),
                **EXPECTED_BASE,
            },
            "fyg8_delta_archive": {
                "path": str(DELTA_ARCHIVE.relative_to(REPO)),
                **EXPECTED_DELTA,
            },
            "p290_applied_source_root": str(BUILD_ROOT.relative_to(REPO)),
        },
        "overlay_census": {
            "base_members": closure.base_member_count,
            "delta_members": len(closure.delta_members),
            "changed_regular_files": len(closure.delta_files),
            "identical_directories": sum(
                kind == "directory" for kind in closure.delta_members.values()
            ),
            "added_members": 0,
            "changed_categories": categories,
            "changed_files": changed_rows,
            "p290_applied_matches": EXPECTED_CHANGED_FILE_COUNT,
        },
        "dts_delta": {
            "revision_count": len(dts),
            "revisions": dts,
            "all_changes_are_13_thermal_threshold_substitutions": True,
            "usb_related_change_count": 0,
            "r12_is_not_unique": True,
        },
        "usb_delta": usb,
        "source_configuration_and_downstream": downstream,
        "document_crosscheck": documents,
        "conclusion": {
            "fyg8_changed_usb_source_files": 2,
            "fyg8_usb_delta_is_notify_layer_only": True,
            "host_restriction_is_not_client_restriction": True,
            "direct_gadget_silence_cause_proved": False,
            "direct_source_effect": (
                "reserved-VBUS wake while lock_state remains INIT installs the HOST "
                "restriction and suppresses EXTERNAL_NOTIFY_POSSIBLE_USB"
            ),
            "downstream_source_effect": (
                "suppressed POSSIBLE_USB withholds PDIC_DELAY_DONE from alternate-mode readiness"
            ),
            "download_positive_control_was_not_missing": True,
            "max77705_reset_default_required_for_this_conclusion": False,
            "candidate_bytes_changed": False,
            "p319_integration_blockers_changed": False,
        },
        "authority": {
            "host_only": True,
            "ready_manifest_created": False,
            "run_manifest_created": False,
            "d0_authorized": False,
            "d1_authorized": False,
            "f1_authorized": False,
            "recovery_authorized": False,
            "replay_authorized": False,
            "device_contact": False,
            "live_authorized": False,
        },
    }


def encode(result: dict[str, Any]) -> bytes:
    return (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _ensure_private_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    current = path
    while True:
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise AuditError(f"private output parent is indirect: {current}")
        if current == path and stat.S_IMODE(info.st_mode) != 0o700:
            os.chmod(current, 0o700, follow_symlinks=False)
            info = current.lstat()
            if stat.S_IMODE(info.st_mode) != 0o700:
                raise AuditError(f"private output directory mode differs: {current}")
        if current == PRIVATE:
            break
        if PRIVATE not in current.parents:
            raise AuditError(f"private output parent escapes workspace/private: {current}")
        current = current.parent


def write_output(data: bytes) -> None:
    _ensure_private_dir(OUTPUT_ROOT)
    if OUTPUT.exists():
        existing = _stable_read(OUTPUT, "existing audit receipt")
        info = OUTPUT.stat()
        if existing != data or stat.S_IMODE(info.st_mode) != 0o400 or info.st_nlink != 1:
            raise AuditError("existing audit receipt differs")
        return
    descriptor = os.open(
        OUTPUT,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o400,
    )
    try:
        os.fchmod(descriptor, 0o400)
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise AuditError("short audit receipt write")
            view = view[written:]
        os.fsync(descriptor)
        info = os.fstat(descriptor)
        if (
            not stat.S_ISREG(info.st_mode)
            or stat.S_IMODE(info.st_mode) != 0o400
            or info.st_nlink != 1
            or info.st_size != len(data)
        ):
            raise AuditError("audit receipt metadata differs")
    finally:
        os.close(descriptor)
    directory = os.open(OUTPUT_ROOT, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def main() -> int:
    result = build_result()
    data = encode(result)
    write_output(data)
    print(
        json.dumps(
            {
                "result": "pass",
                "output": str(OUTPUT.relative_to(REPO)),
                "receipt": _receipt(data),
                "changed_files": result["overlay_census"]["changed_regular_files"],
                "usb_changed_files": result["conclusion"]["fyg8_changed_usb_source_files"],
                "device_contact": result["authority"]["device_contact"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditError, OSError, tarfile.TarError, UnicodeError) as exc:
        raise SystemExit(str(exc)) from exc
