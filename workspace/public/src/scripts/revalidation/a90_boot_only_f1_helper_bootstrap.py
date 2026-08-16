#!/usr/bin/env python3
"""Isolated exact-source bootstrap for the reusable A90 boot-only F1 owner.

This module has no device authority.  The future reviewed owner must bind and
revalidate every named source file before invoking this bootstrap.
"""

from __future__ import annotations

import stat
import sys
import types
from pathlib import Path


LOCAL_MODULE_ORDER = (
    ("_workspace_bootstrap", "_workspace_bootstrap.py"),
    ("a90_transition_contract_v2", "a90_transition_contract_v2.py"),
    ("a90_observation_pipeline", "a90_observation_pipeline.py"),
    ("a90_serial_lock", "a90_serial_lock.py"),
    ("a90ctl", "a90ctl.py"),
)
HELPER_NAME = "native_init_flash.py"


def _exact_source(base: Path, name: str) -> tuple[Path, bytes]:
    path = base / name
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise RuntimeError(f"bootstrap source is not a direct regular file: {name}")
    return path, path.read_bytes()


def _load_local_module(base: Path, module_name: str, file_name: str) -> None:
    if module_name in sys.modules:
        raise RuntimeError(f"bootstrap local module was preloaded: {module_name}")
    path, source = _exact_source(base, file_name)
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

    invoked = Path(__file__)
    if not invoked.is_absolute() or invoked.resolve(strict=True) != invoked:
        raise RuntimeError("A90 F1 helper bootstrap path must be canonical and absolute")
    base = invoked.parent
    if any(Path(entry or ".").resolve() == base for entry in sys.path):
        raise RuntimeError("A90 F1 helper source directory entered sys.path")

    original_path = tuple(sys.path)
    for module_name, file_name in LOCAL_MODULE_ORDER:
        _load_local_module(base, module_name, file_name)
    if tuple(sys.path) != original_path:
        raise RuntimeError("A90 F1 helper bootstrap changed sys.path")

    helper_path, helper_source = _exact_source(base, HELPER_NAME)
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
