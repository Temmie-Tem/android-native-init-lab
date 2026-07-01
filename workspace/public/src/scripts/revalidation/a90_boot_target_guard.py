#!/usr/bin/env python3
"""Fail-closed boot-target guard for the fast self-dd flash path (host-side reference logic).

This is the SAFETY-CRITICAL core of the self-dd boot-flash tool
(docs/plans/FAST_SELF_DD_BOOT_FLASH_TOOL_DESIGN_2026-07-02.md, rev.2). It encodes, as pure testable
Python, the decision logic the device-side native-init command must enforce: given a block device's
*identity* (canonical path, rdev major:minor, sysfs PARTNAME, size, is-block), decide whether it may
be written — accepting ONLY the pinned boot partition and refusing everything else fail-closed.

Two invariants from the Codex review are modeled explicitly:
  - TOCTOU: the identity verified at open MUST be byte-identical to the identity present at write
    time. On the device this is guaranteed by verifying + writing through the SAME open fd
    (rdev cannot change under an open fd); here it is modeled by `authorize_write`.
  - Single-writer: a second concurrent claim on the boot target while one is in flight is refused.

NO device access, NO write, NO dd — this module only decides accept/refuse. The device command ports
this logic and ties it to a real open fd; the host wrapper never re-resolves the path at write time.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

BOOT_PARTITION_SIZE_BYTES = 64 * 1024 * 1024  # A90 boot partition (by-name/boot -> sda24), 64 MiB.

# Positive allowlist: the ONLY acceptable partition name is exactly this.
ALLOWED_PARTNAME = "boot"

# Secondary belt-and-suspenders denylist (resolved numerically on-device; names here for clarity).
# A write that somehow presents any of these must be refused even if other checks were bypassed.
FORBIDDEN_PARTNAMES = frozenset({
    "efs", "sec_efs", "modem", "modem_a", "modem_b", "modemst1", "modemst2", "fsg", "fsc",
    "rpmb", "rpm", "keymaster", "keystore", "keystorage", "tz", "tzsec",
    "vbmeta", "vbmeta_system", "vbmeta_samsung", "vbmeta_vendor", "dsp", "keydata", "keyrefuge",
    "aboot", "abl", "xbl", "xbl_config", "xbl_a", "xbl_b", "sbl1", "bootloader", "uefi", "pmic",
    "cmnlib", "cmnlib64", "devcfg", "hyp", "persist", "param", "steady", "up_param", "dtbo",
    # not brick-class but must never be a boot-flash target — refuse explicitly
    "system", "system_a", "system_b", "vendor", "vendor_a", "vendor_b", "userdata", "cache",
    "recovery", "super", "metadata", "misc",
})


@dataclass(frozen=True)
class BlockIdentity:
    """The identity of a block device as observed through one open fd (fstat + sysfs).

    On device this MUST be built from the opened fd: st_rdev from fstat(fd), size from
    BLKGETSIZE64, PARTNAME/diskseq re-read from /sys/dev/block/<maj>:<min>/ using the fd's rdev —
    never re-stat the path string. This host dataclass is only the decision input.
    """
    canonical_path: str          # e.g. /dev/block/sda24 (readlink -f of the by-name target)
    rdev_major: int
    rdev_minor: int
    partname: str                # sysfs .../uevent PARTNAME
    size_bytes: int
    is_block: bool = True
    diskseq: int | None = None   # sysfs .../diskseq if the kernel exposes it (else None)


@dataclass(frozen=True)
class BootTargetPin:
    """Pinned expected identity of the boot partition. major:minor + canonical_path (+ diskseq) are
    confirmed once by the read-only boot-target-audit. A WRITE path requires a fully-confirmed pin
    (see pin_is_confirmed / authorize_write); only the read-only auditor may use an unconfirmed pin.
    """
    partname: str = ALLOWED_PARTNAME
    size_bytes: int = BOOT_PARTITION_SIZE_BYTES
    canonical_path: str | None = None   # e.g. /dev/block/sda24 (auditor-confirmed)
    rdev_major: int | None = None       # auditor-confirmed
    rdev_minor: int | None = None       # auditor-confirmed
    diskseq: int | None = None          # auditor-confirmed, enforced when set
    forbidden_rdevs: frozenset = frozenset()  # numeric (major,minor) denylist, auditor-populated


def pin_is_confirmed(pin: BootTargetPin) -> bool:
    """True only when the auditor has confirmed the physical identity (rdev + canonical path).
    A write path MUST refuse unless this is True — otherwise a fake PARTNAME=boot/64MiB node on
    any disk (e.g. /dev/block/dm-0) would pass on attributes alone.
    """
    return (pin.rdev_major is not None
            and pin.rdev_minor is not None
            and pin.canonical_path is not None)


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    reason: str


def _refuse(reason: str) -> GuardResult:
    return GuardResult(False, reason)


_ACCEPT = GuardResult(True, "boot-target verified")


def evaluate_boot_target(identity: BlockIdentity, pin: BootTargetPin = BootTargetPin()) -> GuardResult:
    """Fail-closed: refuse unless the identity is the pinned boot partition and nothing else.

    Every check below must pass; the first failure refuses. Order is defensive (cheap/strong
    refusals first). Returns accept ONLY for the exact boot partition.
    """
    if not identity.is_block:
        return _refuse("target is not a block device")
    # Numeric forbidden-rdev denylist first (auditor-populated) — strongest, name-independent.
    if (identity.rdev_major, identity.rdev_minor) in pin.forbidden_rdevs:
        return _refuse(f"forbidden rdev {identity.rdev_major}:{identity.rdev_minor}")
    partname = (identity.partname or "").strip().lower()
    if not partname:
        return _refuse("empty/whitespace PARTNAME")
    # Secondary denylist: a forbidden name is an instant, unambiguous refusal.
    if partname in FORBIDDEN_PARTNAMES:
        return _refuse(f"forbidden partition PARTNAME={partname!r}")
    # Positive allowlist: must be exactly the boot partition name.
    if partname != pin.partname:
        return _refuse(f"PARTNAME={partname!r} != expected {pin.partname!r}")
    if identity.size_bytes != pin.size_bytes:
        return _refuse(f"size {identity.size_bytes} != pinned {pin.size_bytes}")
    # rdev / canonical path / diskseq pins are enforced once confirmed by the auditor.
    if pin.rdev_major is not None and pin.rdev_minor is not None:
        if (identity.rdev_major, identity.rdev_minor) != (pin.rdev_major, pin.rdev_minor):
            return _refuse(
                f"rdev {identity.rdev_major}:{identity.rdev_minor} != pinned "
                f"{pin.rdev_major}:{pin.rdev_minor}")
    if pin.canonical_path is not None and identity.canonical_path != pin.canonical_path:
        return _refuse(f"canonical path {identity.canonical_path!r} != pinned {pin.canonical_path!r}")
    if pin.diskseq is not None and identity.diskseq != pin.diskseq:
        return _refuse(f"diskseq {identity.diskseq} != pinned {pin.diskseq}")
    return _ACCEPT


def authorize_write(open_identity: BlockIdentity,
                    write_identity: BlockIdentity,
                    pin: BootTargetPin = BootTargetPin()) -> GuardResult:
    """TOCTOU-safe WRITE authorization: the identity at write time must be byte-identical to the
    identity verified at open. Models "verify and write through the SAME fd". Both must
    independently pass, AND the pin MUST be auditor-confirmed — always, with no bypass.

    A confirmed pin (rdev + canonical path, see pin_is_confirmed) is an unconditional precondition:
    this closes the Codex-flagged gap where a fake PARTNAME=boot/64MiB node on any disk (e.g.
    /dev/block/dm-0) would pass on attributes alone under a default/unconfirmed pin. There is
    deliberately NO override parameter — the read-only auditor never authorizes a write, it only
    evaluates via evaluate_boot_target(), so no caller has a legitimate reason to bypass this.
    """
    if not pin_is_confirmed(pin):
        return _refuse("write authorization requires an auditor-confirmed pin (rdev + canonical path)")
    verified = evaluate_boot_target(open_identity, pin)
    if not verified.ok:
        return verified
    if write_identity != open_identity:
        return _refuse("identity changed between check and write (TOCTOU) — refusing")
    # Re-run the guard on the write-time identity too (defense in depth).
    return evaluate_boot_target(write_identity, pin)


class BootFlashClaim:
    """Single-writer exclusion: only one boot-target write may be in flight at a time. A second
    concurrent claim is refused (mirrors an on-device exclusive open / flock on the boot block).
    """
    _lock = threading.Lock()
    _in_flight = False

    def __enter__(self) -> "BootFlashClaim":
        with BootFlashClaim._lock:
            if BootFlashClaim._in_flight:
                raise BootFlashBusy("another boot-target write is already in flight")
            BootFlashClaim._in_flight = True
        return self

    def __exit__(self, *exc) -> None:
        with BootFlashClaim._lock:
            BootFlashClaim._in_flight = False


class BootFlashBusy(RuntimeError):
    """Raised when a concurrent boot-target claim is attempted."""
