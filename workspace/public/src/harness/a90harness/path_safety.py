"""Shared safety checks for device-side test paths and raw command args."""

from __future__ import annotations

import posixpath
import string


_UNSAFE_RAW_CHARS = set("'\"\\;|&$`<>(){}[]!*?")
_SAFE_RAW_CHARS = set(string.ascii_letters + string.digits + "_./:@%+=,-")


def _require_text(value: str, label: str) -> str:
    if not isinstance(value, str):
        raise RuntimeError(f"{label} must be text")
    if not value:
        raise RuntimeError(f"{label} must not be empty")
    if "\0" in value:
        raise RuntimeError(f"{label} contains NUL")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise RuntimeError(f"{label} contains control characters")
    return value


def require_safe_component(value: str, label: str) -> str:
    """Validate a single path component supplied by the host operator."""

    value = _require_text(value, label)
    if value in {".", ".."}:
        raise RuntimeError(f"{label} must not be {value!r}")
    if "/" in value or "\\" in value:
        raise RuntimeError(f"{label} must be one path component")
    if any(ch.isspace() for ch in value):
        raise RuntimeError(f"{label} must not contain whitespace")
    if any(ch in _UNSAFE_RAW_CHARS for ch in value):
        raise RuntimeError(f"{label} contains unsafe shell characters")
    if not set(value) <= _SAFE_RAW_CHARS:
        raise RuntimeError(f"{label} contains unsupported characters")
    return value


def normalize_device_path(path: str, label: str) -> str:
    """Normalize and validate an absolute POSIX path used on the device."""

    path = _require_text(path, label)
    if not path.startswith("/"):
        raise RuntimeError(f"{label} must be absolute: {path}")
    if "\\" in path:
        raise RuntimeError(f"{label} must not contain backslashes: {path}")
    if any(ch.isspace() for ch in path):
        raise RuntimeError(f"{label} must not contain whitespace: {path}")
    if "//" in path:
        raise RuntimeError(f"{label} must not contain empty path segments: {path}")
    if path != "/" and path.endswith("/"):
        raise RuntimeError(f"{label} must not end with '/': {path}")
    parts = path.split("/")[1:]
    if any(part in {"", ".", ".."} for part in parts):
        raise RuntimeError(f"{label} contains unsafe path segments: {path}")
    normalized = posixpath.normpath(path)
    if normalized != path:
        raise RuntimeError(f"{label} is not normalized: {path}")
    return normalized


def require_path_under(path: str, root: str, label: str) -> str:
    """Require path to equal root or stay under root with a path boundary."""

    normalized_path = normalize_device_path(path, label)
    normalized_root = normalize_device_path(root, f"{label} root")
    if normalized_path != normalized_root and not normalized_path.startswith(normalized_root + "/"):
        raise RuntimeError(f"{label} must stay under {normalized_root}: {normalized_path}")
    return normalized_path


def require_run_child(root: str, run_id: str) -> str:
    """Build and validate a run directory directly below a safe root."""

    normalized_root = normalize_device_path(root, "test root")
    safe_run_id = require_safe_component(run_id, "run id")
    return require_path_under(posixpath.join(normalized_root, safe_run_id), normalized_root, "run root")


def require_safe_raw_arg(value: str, label: str) -> str:
    """Validate an argument before interpolating it into a raw bridge command."""

    value = _require_text(value, label)
    if any(ch.isspace() for ch in value):
        raise RuntimeError(f"{label} must not contain whitespace")
    if any(ch in _UNSAFE_RAW_CHARS for ch in value):
        raise RuntimeError(f"{label} contains unsafe shell characters")
    if not set(value) <= _SAFE_RAW_CHARS:
        raise RuntimeError(f"{label} contains unsupported characters")
    return value
