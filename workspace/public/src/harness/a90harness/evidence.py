"""Private evidence output helpers for A90 host-side validation."""

from __future__ import annotations

import json
import os
import re
import stat
import time
from pathlib import Path
from typing import Any


PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600
PUBLIC_DIR_MODE = 0o755
PUBLIC_FILE_MODE = 0o644
DEFAULT_MAX_EVIDENCE_READ_BYTES = 16 * 1024 * 1024


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError(f"could not locate repo root from {current}")


REPO_ROOT = repo_root()
WORKSPACE_ROOT = REPO_ROOT / "workspace"
WORKSPACE_PRIVATE_ROOT = WORKSPACE_ROOT / "private"
WORKSPACE_PUBLIC_ROOT = WORKSPACE_ROOT / "public"
WORKSPACE_PRIVATE_INPUT_ROOT = WORKSPACE_PRIVATE_ROOT / "inputs"
WORKSPACE_PRIVATE_BUILD_ROOT = WORKSPACE_PRIVATE_ROOT / "builds"
WORKSPACE_PRIVATE_INPUT_KINDS = frozenset(
    {"firmware", "boot_images", "toolchains", "external_tools", "kernel_source"}
)
WORKSPACE_PRIVATE_BUILD_KINDS = frozenset(
    {"native-init", "boot_images", "ramdisks", "helpers", "wifi"}
)
WORKSPACE_INPUT_ENV = {
    "firmware": "A90_FIRMWARE_ROOT",
    "boot_images": "A90_BOOT_IMAGE_ROOT",
    "toolchains": "A90_TOOLCHAIN_ROOT",
    "external_tools": "A90_EXTERNAL_TOOLS_ROOT",
    "kernel_source": "A90_KERNEL_SOURCE_ROOT",
}
WORKSPACE_BUILD_ENV = "A90_BUILD_ROOT"
LEGACY_INPUT_ROOTS = {
    "firmware": REPO_ROOT / "firmware",
    "boot_images": REPO_ROOT / "stage3",
    "toolchains": REPO_ROOT / "toolchains",
    "external_tools": REPO_ROOT / "external_tools",
    "kernel_source": REPO_ROOT / "kernel_build",
}
TMP_ROOT = REPO_ROOT / "tmp"
TMP_LOG_ROOT = TMP_ROOT / "logs"
WIFI_TMP_ROOT = REPO_ROOT / "tmp" / "wifi"
DOC_ARTIFACT_ROOT = REPO_ROOT / "docs" / "artifacts"
WIFI_ARTIFACT_KINDS = frozenset({"runs", "builds", "cache", "bench", "scratch", "archive"})
TMP_LOG_KINDS = frozenset({"bridge", "host", "device", "kernel", "supplicant", "net", "archive"})
SAFE_ARTIFACT_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def nofollow_flag() -> int:
    return getattr(os, "O_NOFOLLOW", 0)


def cloexec_flag() -> int:
    return getattr(os, "O_CLOEXEC", 0)


def ensure_private_dir(path: Path) -> None:
    path.mkdir(parents=True, mode=PRIVATE_DIR_MODE, exist_ok=True)
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"refusing non-directory output path: {path}")
    path.chmod(PRIVATE_DIR_MODE)


def ensure_public_dir(path: Path) -> None:
    path.mkdir(parents=True, mode=PUBLIC_DIR_MODE, exist_ok=True)
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"refusing non-directory output path: {path}")
    path.chmod(PUBLIC_DIR_MODE)


def write_private_bytes(path: Path, data: bytes) -> None:
    ensure_private_dir(path.parent)
    try:
        info = path.lstat()
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"refusing symlink destination: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | cloexec_flag() | nofollow_flag()
    fd = os.open(path, flags, PRIVATE_FILE_MODE)
    try:
        with os.fdopen(fd, "wb") as file_obj:
            fd = -1
            file_obj.write(data)
    finally:
        if fd >= 0:
            os.close(fd)
    path.chmod(PRIVATE_FILE_MODE)


def write_private_text(path: Path, text: str) -> None:
    write_private_bytes(path, text.encode("utf-8"))


def append_private_text(path: Path, text: str) -> None:
    ensure_private_dir(path.parent)
    try:
        info = path.lstat()
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"refusing symlink destination: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | cloexec_flag() | nofollow_flag()
    fd = os.open(path, flags, PRIVATE_FILE_MODE)
    try:
        with os.fdopen(fd, "a", encoding="utf-8") as file_obj:
            fd = -1
            file_obj.write(text)
    finally:
        if fd >= 0:
            os.close(fd)
    path.chmod(PRIVATE_FILE_MODE)


def append_private_jsonl(path: Path, payload: dict[str, Any]) -> None:
    append_private_text(path, json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def write_private_json(path: Path, payload: dict[str, Any]) -> None:
    write_private_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_public_bytes(path: Path, data: bytes) -> None:
    ensure_public_dir(path.parent)
    try:
        info = path.lstat()
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"refusing symlink destination: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | cloexec_flag() | nofollow_flag()
    fd = os.open(path, flags, PUBLIC_FILE_MODE)
    try:
        with os.fdopen(fd, "wb") as file_obj:
            fd = -1
            file_obj.write(data)
    finally:
        if fd >= 0:
            os.close(fd)
    path.chmod(PUBLIC_FILE_MODE)


def write_public_text(path: Path, text: str) -> None:
    write_public_bytes(path, text.encode("utf-8"))


def write_public_json(path: Path, payload: dict[str, Any]) -> None:
    write_public_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def read_bounded_bytes(path: Path, *, max_bytes: int = DEFAULT_MAX_EVIDENCE_READ_BYTES) -> bytes:
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        raise RuntimeError(f"refusing symlink input: {path}")
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError(f"refusing non-regular input: {path}")
    if info.st_size > max_bytes:
        raise RuntimeError(f"input exceeds bounded read limit: {path} size={info.st_size} limit={max_bytes}")
    fd = os.open(path, os.O_RDONLY | cloexec_flag() | nofollow_flag())
    try:
        chunks: list[bytes] = []
        remaining = max_bytes + 1
        while remaining > 0:
            chunk = os.read(fd, min(1024 * 1024, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
    finally:
        os.close(fd)
    if len(data) > max_bytes:
        raise RuntimeError(f"input exceeds bounded read limit while reading: {path}")
    return data


def read_bounded_text(path: Path,
                      *,
                      max_bytes: int = DEFAULT_MAX_EVIDENCE_READ_BYTES,
                      encoding: str = "utf-8",
                      errors: str = "replace") -> str:
    return read_bounded_bytes(path, max_bytes=max_bytes).decode(encoding, errors=errors)


def read_bounded_json(path: Path, *, max_bytes: int = DEFAULT_MAX_EVIDENCE_READ_BYTES) -> Any:
    return json.loads(read_bounded_text(path, max_bytes=max_bytes))


def artifact_timestamp() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def safe_artifact_label(raw: str, *, default: str = "default", max_len: int = 96) -> str:
    label = SAFE_ARTIFACT_RE.sub("-", raw.strip()).strip(".-")
    if not label:
        label = default
    return label[:max_len].strip(".-") or default


def wifi_artifact_root(kind: str) -> Path:
    if kind not in WIFI_ARTIFACT_KINDS:
        raise ValueError(f"unknown wifi artifact kind: {kind}")
    return WIFI_TMP_ROOT / kind


def wifi_artifact_dir(kind: str, label: str, *, timestamp: bool = False) -> Path:
    safe_label = safe_artifact_label(label)
    if timestamp:
        safe_label = f"{safe_label}-{artifact_timestamp()}"
    return wifi_artifact_root(kind) / safe_label


def tmp_log_root(kind: str) -> Path:
    if kind not in TMP_LOG_KINDS:
        raise ValueError(f"unknown tmp log kind: {kind}")
    return TMP_LOG_ROOT / kind


def tmp_log_dir(kind: str, label: str, *, timestamp: bool = False) -> Path:
    safe_label = safe_artifact_label(label)
    if timestamp:
        safe_label = f"{safe_label}-{artifact_timestamp()}"
    return tmp_log_root(kind) / safe_label


def legacy_wifi_artifact_dir(label: str) -> Path:
    return WIFI_TMP_ROOT / safe_artifact_label(label)


def docs_artifact_path(label: str, *, suffix: str = ".json") -> Path:
    safe_label = safe_artifact_label(label)
    normalized_suffix = suffix if suffix.startswith(".") else f".{suffix}"
    return DOC_ARTIFACT_ROOT / f"{safe_label}{normalized_suffix}"


def workspace_private_input_root(kind: str) -> Path:
    if kind not in WORKSPACE_PRIVATE_INPUT_KINDS:
        raise ValueError(f"unknown workspace private input kind: {kind}")
    override = os.environ.get(WORKSPACE_INPUT_ENV[kind], "").strip()
    if override:
        return Path(override).expanduser()
    return WORKSPACE_PRIVATE_INPUT_ROOT / kind


def workspace_private_input_path(kind: str, *parts: str, legacy_fallback: bool = True) -> Path:
    primary = workspace_private_input_root(kind).joinpath(*parts)
    if primary.exists() or not legacy_fallback:
        return primary
    legacy = LEGACY_INPUT_ROOTS[kind].joinpath(*parts)
    if legacy.exists():
        return legacy
    return primary


def workspace_private_build_root(kind: str) -> Path:
    if kind not in WORKSPACE_PRIVATE_BUILD_KINDS:
        raise ValueError(f"unknown workspace private build kind: {kind}")
    override = os.environ.get(WORKSPACE_BUILD_ENV, "").strip()
    if override:
        return Path(override).expanduser() / kind
    return WORKSPACE_PRIVATE_BUILD_ROOT / kind


def workspace_private_build_path(kind: str, *parts: str) -> Path:
    return workspace_private_build_root(kind).joinpath(*parts)


def workspace_public_path(kind: str, label: str, *, suffix: str = ".json") -> Path:
    safe_kind = safe_artifact_label(kind, default="manifests", max_len=48)
    safe_label = safe_artifact_label(label)
    normalized_suffix = suffix if suffix.startswith(".") else f".{suffix}"
    return WORKSPACE_PUBLIC_ROOT / safe_kind / f"{safe_label}{normalized_suffix}"


class EvidenceStore:
    """Run-scoped private evidence directory."""

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        ensure_private_dir(run_dir.parent)
        ensure_private_dir(run_dir)

    def path(self, *parts: str) -> Path:
        return self.run_dir.joinpath(*parts)

    def log_relative_path(self, section: str, filename: str) -> str:
        safe_section = safe_artifact_label(section, default="host", max_len=48)
        safe_filename = safe_artifact_label(filename, default="log.txt", max_len=160)
        return str(Path("logs") / safe_section / safe_filename)

    def log_path(self, section: str, filename: str) -> Path:
        return self.path(self.log_relative_path(section, filename))

    def mkdir(self, *parts: str) -> Path:
        path = self.path(*parts)
        ensure_private_dir(path)
        return path

    def write_text(self, relative_path: str, text: str) -> Path:
        path = self.path(relative_path)
        write_private_text(path, text)
        return path

    def write_log(self, section: str, filename: str, text: str) -> Path:
        path = self.log_path(section, filename)
        write_private_text(path, text)
        return path

    def write_json(self, relative_path: str, payload: dict[str, Any]) -> Path:
        path = self.path(relative_path)
        write_private_json(path, payload)
        return path

    def append_jsonl(self, relative_path: str, payload: dict[str, Any]) -> Path:
        path = self.path(relative_path)
        append_private_jsonl(path, payload)
        return path
