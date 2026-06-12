"""Import helpers for the host-only regression test harness.

The analyzers under ``workspace/public/src/scripts/revalidation`` are standalone
scripts (not an installed package), and the shared library lives under
``workspace/public/src/harness/a90harness``. These helpers load either kind by
repo-relative path / package name without requiring an install step.

Used by every ``tests/test_*.py`` module. Pure host-side; touches no device.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
HARNESS_DIR = REPO_ROOT / "workspace" / "public" / "src" / "harness"
REVAL_DIR = REPO_ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"


def load_script(rel_path: str) -> ModuleType:
    """Load a standalone .py script by repo-relative path as a module object.

    The script must guard its CLI with ``if __name__ == "__main__"`` so that
    import does not execute it (14/15 analyzers already do).
    """
    path = (REPO_ROOT / rel_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"script not found: {path}")
    script_dir = str(path.parent)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    spec = importlib.util.spec_from_file_location(f"a90test_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot build import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_revalidation(name: str) -> ModuleType:
    """Load a revalidation analyzer by file name, e.g. 'a90_kernel_v2199_...'."""
    if not name.endswith(".py"):
        name = name + ".py"
    return load_script(str((REVAL_DIR / name).relative_to(REPO_ROOT)))


def load_harness(name: str) -> ModuleType:
    """Import a module from the a90harness package, e.g. load_harness('path_safety')."""
    harness_str = str(HARNESS_DIR)
    reval_str = str(REVAL_DIR)
    if harness_str not in sys.path:
        sys.path.insert(0, harness_str)
    if reval_str not in sys.path:
        sys.path.insert(0, reval_str)
    return importlib.import_module(f"a90harness.{name}")
