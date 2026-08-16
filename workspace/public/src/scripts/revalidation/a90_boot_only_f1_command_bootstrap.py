#!/usr/bin/env python3
"""Exact isolated producer for the four A90 boot-only F1 health commands.

The parent executes these bytes through the reviewed inherited-FD loader.  All
local dependencies are then opened from the separately verified private
runtime-source directory.  This program has no caller-selected command.
"""

from __future__ import annotations

import hashlib
import json
import os
import resource
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
COMMANDS = {
    "version": ("version",),
    "selftest": ("selftest",),
    "status": ("status",),
    "boot-id": ("cat", "/proc/sys/kernel/random/boot_id"),
}
MAX_OUTPUT_BYTES = 1 << 20


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
        path_metadata = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or not stat.S_ISREG(path_metadata.st_mode)
            or metadata.st_nlink != 1
            or path_metadata.st_nlink != 1
            or (metadata.st_dev, metadata.st_ino)
            != (path_metadata.st_dev, path_metadata.st_ino)
            or metadata.st_size != expected_size
        ):
            raise RuntimeError(f"command source identity mismatch: {name}")
        source = bytearray()
        while len(source) < expected_size:
            chunk = os.read(descriptor, min(1 << 20, expected_size - len(source)))
            if not chunk:
                raise RuntimeError(f"command source ended early: {name}")
            source.extend(chunk)
        if os.read(descriptor, 1):
            raise RuntimeError(f"command source exceeds bound size: {name}")
        raw = bytes(source)
        if hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise RuntimeError(f"command source digest mismatch: {name}")
        return path, raw
    finally:
        os.close(descriptor)


def _load_module(
    base: Path,
    module_name: str,
    file_name: str,
    expected_size: int,
    expected_sha256: str,
) -> types.ModuleType:
    if module_name in sys.modules:
        raise RuntimeError(f"command local module was preloaded: {module_name}")
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
    return module


def main() -> int:
    if not sys.flags.isolated or not sys.flags.safe_path:
        raise RuntimeError("A90 command bootstrap requires isolated safe-path mode")
    if globals().get("__a90_bootstrap_fd_bound__") is not True:
        raise RuntimeError("A90 command bootstrap requires inherited-FD execution")
    if len(sys.argv) != 3 or sys.argv[1] not in COMMANDS:
        raise RuntimeError("A90 command bootstrap received an unknown command")
    try:
        timeout_sec = int(sys.argv[2], 10)
    except ValueError as exc:
        raise RuntimeError("A90 command timeout is not an integer") from exc
    if not 1 <= timeout_sec <= 300:
        raise RuntimeError("A90 command timeout is outside its fixed bound")

    invoked = Path(__file__)
    if not invoked.is_absolute() or invoked.resolve(strict=True) != invoked:
        raise RuntimeError("A90 command bootstrap path is not canonical")
    base = invoked.parent
    if any(Path(entry or ".").resolve() == base for entry in sys.path):
        raise RuntimeError("A90 command source directory entered sys.path")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))

    original_path = tuple(sys.path)
    loaded: dict[str, types.ModuleType] = {}
    for specification in LOCAL_MODULE_ORDER:
        module = _load_module(base, *specification)
        loaded[specification[0]] = module
    if tuple(sys.path) != original_path:
        raise RuntimeError("A90 command bootstrap changed sys.path")
    # The staged tree intentionally lives outside the repository.  Keep the
    # transaction lock in its fixed private parent rather than asking the
    # loaded compatibility helper to rediscover a repository from __file__.
    loaded["a90_serial_lock"].repo_root = lambda: base.parent
    loaded["a90_serial_lock"].DEFAULT_LOCK_REL = "a90-serial-bridge.lock"

    command = list(COMMANDS[sys.argv[1]])
    result = loaded["a90ctl"].run_cmdv1_command(
        "127.0.0.1",
        54321,
        float(timeout_sec),
        command,
        retry_unsafe=False,
        input_mode="normal",
        require_prompt_after_end=True,
    )
    payload = {
        "command": command,
        "rc": result.rc,
        "status": result.status,
        "text": result.text,
    }
    print(
        json.dumps(
            payload,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ),
        flush=True,
    )
    return 0 if result.rc == 0 and result.status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
