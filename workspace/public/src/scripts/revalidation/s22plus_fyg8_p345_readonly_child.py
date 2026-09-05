#!/usr/bin/env python3
"""H0-only P3.45 fixed read-only BusyBox ash child boundary.

The child entry point is a C fragment with the intentionally narrow API
``p345_enter_readonly_child(void)``.  It has no command, path, descriptor or
environment arguments.  The existing runtime worker inserts one exact hook
after its child has established stdio and closed the transport TTY, before
constructing the ash argv.  This module performs no device, ADB, Odin or
transport operation.

The view is a finite set of regular text snapshots plus one static BusyBox
bind.  It is not a procfs/sysfs mount and does not expose process roots, fd,
mem, kcore, block devices or control files.  The source is H0 validation
material; integrating it into a candidate and any later F1 activation require
their own reviewed identities and authority.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[5]
SOURCE = ROOT / "workspace/public/src/native-init/s22plus_fyg8_p345_readonly_child.inc.c"
SCHEMA = "s22plus_fyg8_p345_readonly_child_v1"
CONTRACT_ID = SCHEMA
API = "p345_enter_readonly_child(void)"
HOOK_EXIT_STATUS = 126


def identity(payload: bytes) -> dict[str, Any]:
    return {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _load_source() -> bytes:
    try:
        payload = SOURCE.read_bytes()
    except OSError as exc:
        raise RuntimeError("P345 child source is unavailable") from exc
    if not payload:
        raise RuntimeError("P345 child source is empty")
    return payload


CHILD_SOURCE = _load_source()
P345_CHILD_SOURCE = CHILD_SOURCE
P345_C_FRAGMENT = CHILD_SOURCE
P345_SOURCE = SOURCE
SOURCE_IDENTITY = {
    "size": 21_792,
    "sha256": "a053e6796a83767e5de97ed714080a10888e2c9a9ef99dbb06e3aabf1633ae29",
}
if identity(CHILD_SOURCE) != SOURCE_IDENTITY:
    raise RuntimeError("P345 child source identity differs")
P345_SOURCE_IDENTITY = dict(SOURCE_IDENTITY)


# Fixed source and destination names are part of the child boundary.  Each
# source is copied as bounded text before chroot/remount; no live proc/sys
# mount enters the view.
SNAPSHOT_FILES: tuple[dict[str, Any], ...] = (
    {
        "name": "memory",
        "source": "/proc/meminfo",
        "view": "/proc/meminfo",
        "max_bytes": 16_384,
    },
    {
        "name": "kernel",
        "source": "/proc/cpuinfo",
        "view": "/proc/cpuinfo",
        "max_bytes": 16_384,
    },
    {
        "name": "uptime",
        "source": "/proc/uptime",
        "view": "/proc/uptime",
        "max_bytes": 128,
    },
    {
        "name": "kernel-version",
        "source": "/proc/version",
        "view": "/proc/version",
        "max_bytes": 1_024,
    },
    {
        "name": "mounts",
        "source": "/proc/mounts",
        "view": "/proc/mounts",
        "max_bytes": 32_768,
    },
    {
        "name": "usb-state",
        "source": "/sys/class/udc/a600000.dwc3/state",
        "view": "/sys/class/udc/a600000.dwc3/state",
        "max_bytes": 128,
    },
)

CATALOG: tuple[str, ...] = (
    "kernel",
    "processes",
    "mounts",
    "memory",
    "usb-state",
)
PROCESS_VIEW: tuple[str, ...] = ()
FIXED_BUSYBOX_SOURCE = "/bin/busybox"
FIXED_BUSYBOX_VIEW = "/bin/busybox"
FIXED_ROOT_VIEW = "/dev/p345-root"

FORBIDDEN_VIEW_ENTRIES: tuple[str, ...] = (
    "/proc/*/root",
    "/proc/*/fd",
    "/proc/*/mem",
    "/proc/kcore",
    "/dev",
    "/sys/kernel/debug",
    "/sys/kernel/tracing",
    "/sys/class/udc/*/device",
    "/sys/class/udc/*/function",
    "/sys/class/udc/*/uevent",
    "/block",
    "/config",
)

DENIED_CATEGORIES: tuple[str, ...] = (
    "openat2-and-unqualified-open",
    "writable-create-truncate-append-open-modes",
    "filesystem-mutation",
    "ioctl-and-device-control",
    "network",
    "ptrace-and-process-memory",
    "io-uring",
    "mount-and-namespace",
    "setsid-and-setpgid-after-setup",
    "group-uid-gid-capability-escape",
    "reboot-and-module-loading",
)

ALLOWED_SYSCALL_LABELS: tuple[str, ...] = (
    "read",
    "write-output-pipes-only",
    "close",
    "openat-readonly-flags-only",
    "fstat",
    "newfstatat",
    "lseek",
    "mmap",
    "munmap",
    "mprotect",
    "mremap",
    "brk",
    "rt_sigaction",
    "rt_sigprocmask",
    "rt_sigreturn",
    "sigaltstack",
    "exit",
    "exit_group",
    "execve-fixed-view-only",
    "clone-no-namespace-flags-process-limit-bound",
    "wait4",
    "pipe2",
    "dup",
    "dup3",
    "fcntl",
    "chdir-inside-chroot",
    "getcwd-inside-chroot",
    "getpid",
    "getppid",
    "getuid",
    "geteuid",
    "getgid",
    "getegid",
    "gettid",
    "set_tid_address",
    "set_robust_list",
    "futex",
    "clock_gettime",
    "nanosleep",
    "uname",
    "getrandom",
    "statx",
    "readlinkat",
    "getdents64",
    "faccessat",
    "madvise",
    "rseq",
    "sched_yield",
    "ppoll",
)

RESOURCE_BOUNDS: Mapping[str, int] = {
    "cpu_seconds": 15,
    "address_space_bytes": 64 * 1024 * 1024,
    "processes": 16,
    "file_descriptors": 32,
    "regular_file_bytes": 65_536,
    "tmpfs_bytes": 1 * 1024 * 1024,
}


class P345ChildSourceError(ValueError):
    """The exact child seam or fragment source is not present."""


_TTY_CLOSE_TO_ARGV_SEAM = (
    b"        (void)sys_close(tty_fd);\n"
    b"        char *const argv[] = {"
)
_HOOK = (
    b"        (void)sys_close(tty_fd);\n"
    b"        if (p345_enter_readonly_child() != 0) sys_exit(126);\n"
    b"        char *const argv[] = {"
)
_HOOK_MARKER = b"p345_enter_readonly_child()"


def validate_child_source(source: bytes) -> bytes:
    """Return *source* after checking the fixed no-input C API markers."""

    if type(source) is not bytes:
        raise P345ChildSourceError("child source must be bytes")
    required = (
        b"static long p345_enter_readonly_child(void)",
        b"P345_NR_UNSHARE",
        b"P345_NR_CLOSE_RANGE",
        b"P345_PR_SET_NO_NEW_PRIVS",
        b"P345_NR_SECCOMP",
        b"P345_BUSYBOX_SOURCE \"/bin/busybox\"",
        b"/proc/meminfo",
        b"/proc/cpuinfo",
        b"/proc/uptime",
        b"/proc/version",
        b"/proc/mounts",
        b"/sys/class/udc/a600000.dwc3/state",
        b"P345_SECCOMP_RET_ERRNO",
        b"P345_O_WRITE_MASK",
    )
    missing = [marker for marker in required if marker not in source]
    if missing:
        raise P345ChildSourceError(
            "child source is missing required marker: " + repr(missing[0])
        )
    if source.count(b"p345_enter_readonly_child(void)") != 1:
        raise P345ChildSourceError("child API must have one fixed no-input definition")
    if source.count(_HOOK_MARKER):
        raise P345ChildSourceError("child fragment must not contain an integration hook")
    return source


def child_source() -> bytes:
    """Return the exact reviewed C fragment bytes for a host build worker."""

    payload = _load_source()
    if identity(payload) != SOURCE_IDENTITY:
        raise P345ChildSourceError("P345 child source identity differs")
    return validate_child_source(payload)


def integrate_child_source(runtime_source: bytes) -> bytes:
    """Insert the one fixed hook after tty close and before ash argv.

    This accepts C source bytes, never shell text.  It rejects ambiguous or
    already-integrated sources so a worker cannot silently insert a second
    child boundary or patch the wrong runtime function.
    """

    if type(runtime_source) is not bytes:
        raise P345ChildSourceError("runtime source must be bytes")
    if runtime_source.count(_TTY_CLOSE_TO_ARGV_SEAM) != 1:
        raise P345ChildSourceError("runtime child stdio/tty seam is not unique")
    if runtime_source.count(_HOOK_MARKER):
        raise P345ChildSourceError("runtime source already contains P345 hook")
    return runtime_source.replace(_TTY_CLOSE_TO_ARGV_SEAM, _HOOK, 1)


def validate_integration(runtime_source: bytes) -> bytes:
    """Validate an already transformed runtime source without relabeling it."""

    if type(runtime_source) is not bytes:
        raise P345ChildSourceError("runtime source must be bytes")
    if runtime_source.count(_HOOK) != 1:
        raise P345ChildSourceError("P345 hook is not exactly once at the fixed seam")
    if runtime_source.count(_TTY_CLOSE_TO_ARGV_SEAM):
        raise P345ChildSourceError("untransformed child seam remains")
    return runtime_source


# Short aliases keep the worker API discoverable without duplicating the
# transform implementation.
insert_child_hook = integrate_child_source
integrate_runtime_source = integrate_child_source
validate_runtime_source = validate_integration


# Names kept explicit for small registration/build workers that consume a
# source fragment rather than the Python helper itself.
P345_CHILD_SOURCE = CHILD_SOURCE
P345_INTEGRATION_HOOK = _HOOK
P345_INTEGRATION_SEAM = _TTY_CLOSE_TO_ARGV_SEAM


def audit() -> dict[str, Any]:
    """Return machine-readable H0 qualification metadata."""

    child_source()
    return {
        "schema": SCHEMA,
        "contract_id": CONTRACT_ID,
        "api": API,
        "source": {"path": str(SOURCE), **SOURCE_IDENTITY},
        "fixed_no_input": True,
        "fixed_busybox_source": FIXED_BUSYBOX_SOURCE,
        "fixed_busybox_view": FIXED_BUSYBOX_VIEW,
        "fixed_root_view": FIXED_ROOT_VIEW,
        "snapshot_files": [dict(item) for item in SNAPSHOT_FILES],
        "catalog": list(CATALOG),
        "process_view": list(PROCESS_VIEW),
        "forbidden_view_entries": list(FORBIDDEN_VIEW_ENTRIES),
        "allowed_syscalls": list(ALLOWED_SYSCALL_LABELS),
        "denied_categories": list(DENIED_CATEGORIES),
        "resource_bounds": dict(RESOURCE_BOUNDS),
        "closes_inherited_fds_above": 2,
        "drops_groups_uid_gid_caps": True,
        "no_new_privs": True,
        "seccomp_default": "ERRNO(EPERM)",
        "unsupported_syscall_policy": "fail-closed-before-ash",
        "hook_order": "after-setsid-stdio-and-tty-close-before-execve",
        "parent_transport_outside_filter": True,
        "runtime_behavior_unchanged": False,
        "behavior_delta": "new-fixed-readonly-child-boundary",
        "validator_only": False,
        "host_only": True,
        "device_contact": False,
        "f1_ready": False,
    }


__all__ = [
    "ALLOWED_SYSCALL_LABELS",
    "API",
    "CATALOG",
    "CHILD_SOURCE",
    "CONTRACT_ID",
    "DENIED_CATEGORIES",
    "FIXED_BUSYBOX_SOURCE",
    "FIXED_BUSYBOX_VIEW",
    "FIXED_ROOT_VIEW",
    "FORBIDDEN_VIEW_ENTRIES",
    "HOOK_EXIT_STATUS",
    "P345_C_FRAGMENT",
    "P345_CHILD_SOURCE",
    "P345_INTEGRATION_HOOK",
    "P345_INTEGRATION_SEAM",
    "P345_SOURCE",
    "P345_SOURCE_IDENTITY",
    "PROCESS_VIEW",
    "RESOURCE_BOUNDS",
    "SCHEMA",
    "SNAPSHOT_FILES",
    "SOURCE",
    "SOURCE_IDENTITY",
    "P345ChildSourceError",
    "audit",
    "child_source",
    "identity",
    "insert_child_hook",
    "integrate_runtime_source",
    "integrate_child_source",
    "validate_child_source",
    "validate_integration",
    "validate_runtime_source",
]
