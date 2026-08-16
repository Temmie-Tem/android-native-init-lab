#!/usr/bin/env python3
"""Isolated exact-source bootstrap for the reusable A90 boot-only F1 owner.

This module has no device authority.  The future reviewed owner must bind and
revalidate every named source file before invoking this bootstrap.
"""

from __future__ import annotations

import hashlib
import os
import stat
import sys
import types
from pathlib import Path


LOCAL_MODULE_ORDER = (
    (
        "_workspace_bootstrap",
        "_workspace_bootstrap.py",
        1_255,
        "7a8322f9760c8aa3672e094b01df0231fb5b0a85ceaeb5ad73042fcd3f3a6ffe",
    ),
    (
        "a90_transition_contract_v2",
        "a90_transition_contract_v2.py",
        13_734,
        "64e640dfb54d016f8e5548aea0da167e7f6917bf40c02fbc971773ef181b1c7e",
    ),
    (
        "a90_observation_pipeline",
        "a90_observation_pipeline.py",
        24_478,
        "6fa353b4e28ad26e76ec98d0e2c30089b493356fb314b36b962ce97e34a00adb",
    ),
    (
        "a90_serial_lock",
        "a90_serial_lock.py",
        2_860,
        "663dd16f5121e35fc1047d563bdbe55148695224cf0c6ca5ab59c0433b6191c7",
    ),
    (
        "a90ctl",
        "a90ctl.py",
        16_380,
        "4d72b87b42ef49c5997ddcd24d0c6bb4fe94766c2c7fddaa21b07ff218009f8c",
    ),
)
HELPER_SPEC = (
    "native_init_flash.py",
    43_118,
    "366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53",
)


def _exact_source(
    base: Path,
    name: str,
    expected_size: int,
    expected_sha256: str,
) -> tuple[Path, bytes]:
    path = base / name
    descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_size != expected_size
        ):
            raise RuntimeError(f"bootstrap source identity mismatch: {name}")
        chunks: list[bytes] = []
        remaining = expected_size
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1 << 20))
            if not chunk:
                raise RuntimeError(f"bootstrap source ended early: {name}")
            chunks.append(chunk)
            remaining -= len(chunk)
        if os.read(descriptor, 1):
            raise RuntimeError(f"bootstrap source exceeds bound size: {name}")
        source = b"".join(chunks)
        if hashlib.sha256(source).hexdigest() != expected_sha256:
            raise RuntimeError(f"bootstrap source digest mismatch: {name}")
        return path, source
    finally:
        os.close(descriptor)


def _load_local_module(
    base: Path,
    module_name: str,
    file_name: str,
    expected_size: int,
    expected_sha256: str,
) -> None:
    if module_name in sys.modules:
        raise RuntimeError(f"bootstrap local module was preloaded: {module_name}")
    path, source = _exact_source(base, file_name, expected_size, expected_sha256)
    module = types.ModuleType(module_name)
    module.__file__ = str(path)
    module.__package__ = ""
    module.__cached__ = None
    sys.modules[module_name] = module
    try:
        exec(compile(source, str(path), "exec", dont_inherit=True), module.__dict__)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise


def main() -> None:
    if not sys.flags.isolated or not sys.flags.safe_path:
        raise RuntimeError("A90 F1 helper bootstrap requires Python isolated safe-path mode")
    if globals().get("__a90_bootstrap_fd_bound__") is not True:
        raise RuntimeError("A90 F1 helper bootstrap requires inherited-FD execution")

    invoked = Path(__file__)
    if not invoked.is_absolute() or invoked.resolve(strict=True) != invoked:
        raise RuntimeError("A90 F1 helper bootstrap path must be canonical and absolute")
    base = invoked.parent
    if any(Path(entry or ".").resolve() == base for entry in sys.path):
        raise RuntimeError("A90 F1 helper source directory entered sys.path")

    original_path = tuple(sys.path)
    for module_name, file_name, expected_size, expected_sha256 in LOCAL_MODULE_ORDER:
        _load_local_module(
            base,
            module_name,
            file_name,
            expected_size,
            expected_sha256,
        )
    if tuple(sys.path) != original_path:
        raise RuntimeError("A90 F1 helper bootstrap changed sys.path")

    helper_path, helper_source = _exact_source(base, *HELPER_SPEC)
    sys.argv[0] = str(helper_path)
    helper_globals = {
        "__name__": "__main__",
        "__file__": str(helper_path),
        "__package__": None,
        "__cached__": None,
    }
    exec(
        compile(helper_source, str(helper_path), "exec", dont_inherit=True),
        helper_globals,
    )


if __name__ == "__main__":
    main()
