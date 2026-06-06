#!/usr/bin/env python3
"""Export a minimal private vendor root evidence bundle for Wi-Fi analysis."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import (
    EvidenceStore,
    PRIVATE_FILE_MODE,
    cloexec_flag,
    ensure_private_dir,
    nofollow_flag,
)


DEFAULT_V210_MANIFEST = Path("tmp/wifi/v210-vendor-asset-classifier/manifest.json")
DEFAULT_V221_MANIFEST = Path("tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json")
TARGET_REQUIRED_RELS = ("bin/cnss-daemon", "bin/cnss_diag")
DEFAULT_MAX_FILES = 5000
DEFAULT_MAX_TOTAL_BYTES = 512 * 1024 * 1024

CONTEXT_FILES = (
    "etc/init/android.hardware.wifi@1.0-service.rc",
    "etc/init/android.hardware.wifi.hostapd@1.0-service.rc",
    "etc/init/android.hardware.wifi.supplicant@1.0-service.rc",
    "etc/init/cnss-daemon.rc",
    "etc/init/hw/init.qcom.rc",
    "etc/init/hw/init.target.rc",
    "etc/wifi/WCNSS_qcom_cfg.ini",
)

ACTIVE_PATTERNS = (
    re.compile(r"\b(?:cnss-daemon|cnss_diag|wificond|wpa_supplicant|hostapd)\b", re.IGNORECASE),
    re.compile(r"\bctl\.(?:start|restart)\b|\bclass_start\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/", re.IGNORECASE),
)

NO_DEVICE_COMMANDS: tuple[tuple[str, list[str]], ...] = ()


def default_out_dir() -> Path:
    return REPO_ROOT / "tmp" / "wifi" / "v222-vendor-root-evidence-export"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--source-vendor-root", type=Path, default=None)
    parser.add_argument("--v210-manifest", type=Path, default=DEFAULT_V210_MANIFEST)
    parser.add_argument("--v221-manifest", type=Path, default=DEFAULT_V221_MANIFEST)
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-total-bytes", type=int, default=DEFAULT_MAX_TOTAL_BYTES)
    return parser.parse_args()


def validate_no_active_commands() -> None:
    command_text = "\n".join(" ".join(argv) for _, argv in NO_DEVICE_COMMANDS)
    for pattern in ACTIVE_PATTERNS:
        if pattern.search(command_text):
            raise AssertionError(f"active command pattern present: {pattern.pattern}")


def load_json(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def normalize_vendor_rel(value: str) -> str:
    value = value.strip()
    if value.startswith("<vendor-root>/"):
        value = value.removeprefix("<vendor-root>/")
    if value.startswith("/system/vendor/"):
        value = value.removeprefix("/system/vendor/")
    elif value.startswith("/vendor/"):
        value = value.removeprefix("/vendor/")
    return value.lstrip("/")


def is_safe_rel(value: str) -> bool:
    rel = Path(value)
    return bool(value) and not rel.is_absolute() and ".." not in rel.parts


def required_paths_from_v221(v221: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in v221.get("required_vendor_paths", []):
        if not isinstance(item, dict):
            continue
        rel = str(item.get("vendor_relative_path") or "")
        if not rel:
            rel = normalize_vendor_rel(str(item.get("expected_host_path") or ""))
        rel = normalize_vendor_rel(rel)
        if not is_safe_rel(rel):
            continue
        rows.append({
            "service": str(item.get("service") or Path(rel).name),
            "vendor_relative_path": rel,
            "expected_host_path": f"<vendor-root>/{rel}",
        })
    seen = {row["vendor_relative_path"] for row in rows}
    for rel in TARGET_REQUIRED_RELS:
        if rel not in seen:
            rows.append({
                "service": Path(rel).name,
                "vendor_relative_path": rel,
                "expected_host_path": f"<vendor-root>/{rel}",
            })
    return rows


def normalize_source_root(path: Path | None) -> tuple[Path | None, str]:
    if path is None:
        return None, "not-provided"
    root = repo_path(path)
    try:
        info = root.lstat()
    except FileNotFoundError:
        return root, "missing"
    if stat.S_ISLNK(info.st_mode):
        return root, "symlink-root-denied"
    if not stat.S_ISDIR(info.st_mode):
        return root, "not-directory"
    return root.resolve(), "ok"


def should_skip_rel(rel: str) -> str | None:
    parts = Path(rel).parts
    lowered = rel.lower()
    if not is_safe_rel(rel):
        return "unsafe-relative-path"
    if parts and parts[0] == "data":
        return "credential-data-path-denied"
    if "misc/wifi" in lowered or "wpa_supplicant.conf" in lowered:
        return "credential-path-denied"
    return None


def collect_candidate_rels(root: Path, required_paths: list[dict[str, str]]) -> tuple[list[str], list[dict[str, str]]]:
    candidates: set[str] = set()
    skipped: list[dict[str, str]] = []

    for item in required_paths:
        rel = item["vendor_relative_path"]
        reason = should_skip_rel(rel)
        if reason:
            skipped.append({"path": rel, "reason": reason})
        else:
            candidates.add(rel)

    for top in ("lib", "lib64"):
        base = root / top
        if not base.exists():
            continue
        for path in base.rglob("*"):
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISDIR(info.st_mode):
                continue
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                continue
            reason = should_skip_rel(rel)
            if reason:
                skipped.append({"path": rel, "reason": reason})
            else:
                candidates.add(rel)

    for rel in CONTEXT_FILES:
        if (root / rel).exists():
            candidates.add(rel)

    return sorted(candidates), skipped


def resolve_source_file(root: Path, rel: str) -> tuple[Path | None, str]:
    candidate = root / rel
    try:
        info = candidate.lstat()
    except FileNotFoundError:
        return None, "missing"
    if stat.S_ISLNK(info.st_mode):
        target = os.readlink(candidate)
        if target.startswith("/vendor/"):
            mapped = root / target.removeprefix("/vendor/")
        elif target.startswith("/system/vendor/"):
            mapped = root / target.removeprefix("/system/vendor/")
        elif target.startswith("/"):
            return None, f"external-symlink:{target}"
        else:
            mapped = candidate.parent / target
        try:
            resolved = mapped.resolve()
            resolved.relative_to(root)
        except (FileNotFoundError, ValueError):
            return None, f"unsafe-symlink:{target}"
        if not resolved.exists():
            return None, f"broken-symlink:{target}"
        if not resolved.is_file():
            return None, f"symlink-target-not-regular:{target}"
        return resolved, "symlink"
    if not stat.S_ISREG(info.st_mode):
        return None, "not-regular"
    return candidate, "regular"


def ensure_private_child_dir(base: Path, path: Path) -> None:
    ensure_private_dir(base)
    try:
        rel_parts = path.relative_to(base).parts
    except ValueError as exc:
        raise RuntimeError(f"destination escapes private base: {path}") from exc
    current = base
    for part in rel_parts:
        if part in {"", ".", ".."}:
            raise RuntimeError(f"unsafe destination directory component: {path}")
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            current.mkdir(mode=0o700)
            current.chmod(0o700)
            continue
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise RuntimeError(f"refusing non-directory output path: {current}")
        current.chmod(0o700)


def sha256_copy_private(source: Path, dest: Path, private_base: Path) -> tuple[int, str]:
    ensure_private_child_dir(private_base, dest.parent)
    try:
        info = dest.lstat()
    except FileNotFoundError:
        pass
    else:
        if stat.S_ISLNK(info.st_mode):
            raise RuntimeError(f"refusing symlink destination: {dest}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | cloexec_flag() | nofollow_flag()
    digest = hashlib.sha256()
    total = 0
    fd = os.open(dest, flags, PRIVATE_FILE_MODE)
    try:
        with source.open("rb") as src, os.fdopen(fd, "wb") as dst:
            fd = -1
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                digest.update(chunk)
                dst.write(chunk)
                total += len(chunk)
    finally:
        if fd >= 0:
            os.close(fd)
    dest.chmod(PRIVATE_FILE_MODE)
    return total, digest.hexdigest()


def plan_copy(root: Path,
              candidate_rels: list[str],
              required_paths: list[dict[str, str]],
              max_files: int,
              max_total_bytes: int) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, Any]], list[str], str | None]:
    planned: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    missing_required: list[dict[str, Any]] = []
    total_bytes = 0
    required_rels = {item["vendor_relative_path"] for item in required_paths}
    resolved_required: set[str] = set()

    for rel in candidate_rels:
        source, source_kind = resolve_source_file(root, rel)
        if source is None:
            skipped.append({"path": rel, "reason": source_kind})
            if rel in required_rels:
                missing_required.append({"path": rel, "reason": source_kind})
            continue
        size = source.stat().st_size
        total_bytes += size
        planned.append({
            "relative_path": rel,
            "source_path": str(source),
            "source_kind": source_kind,
            "size": size,
        })
        if rel in required_rels:
            resolved_required.add(rel)

    for item in required_paths:
        rel = item["vendor_relative_path"]
        if rel not in resolved_required and not any(entry["path"] == rel for entry in missing_required):
            missing_required.append({"path": rel, "reason": "not-in-copy-plan"})

    if len(planned) > max_files:
        return planned, skipped, missing_required, [], f"copy plan has {len(planned)} files > max_files {max_files}"
    if total_bytes > max_total_bytes:
        return planned, skipped, missing_required, [], f"copy plan has {total_bytes} bytes > max_total_bytes {max_total_bytes}"
    return planned, skipped, missing_required, sorted(resolved_required), None


def copy_plan(planned: list[dict[str, Any]], vendor_root_out: Path) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    ensure_private_dir(vendor_root_out)
    for item in planned:
        rel = item["relative_path"]
        dest = vendor_root_out / rel
        size, digest = sha256_copy_private(Path(item["source_path"]), dest, vendor_root_out)
        copied.append({
            "relative_path": rel,
            "dest": str(dest),
            "size": size,
            "sha256": digest,
            "source_kind": item["source_kind"],
        })
    return copied


def build_v221_rerun_command(vendor_root_out: Path) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_vendor_elf_library_closure.py",
        "--vendor-root",
        str(vendor_root_out.relative_to(REPO_ROOT) if vendor_root_out.is_relative_to(REPO_ROOT) else vendor_root_out),
        "--out-dir",
        "tmp/wifi/v221-host-vendor-elf-library-evidence-rerun",
    ]


def decide(source_status: str,
           limit_error: str | None,
           missing_required: list[dict[str, Any]],
           copied: list[dict[str, Any]],
           library_file_count: int) -> tuple[str, str, bool]:
    if source_status == "not-provided":
        return "export-source-required", "source vendor root is required for export", True
    if source_status != "ok":
        return "vendor-export-blocked", f"source vendor root is not usable: {source_status}", False
    if limit_error:
        return "vendor-export-blocked", limit_error, False
    if missing_required:
        return "vendor-export-blocked", "required vendor paths are missing", False
    if not copied:
        return "vendor-export-blocked", "copy plan is empty", False
    if library_file_count == 0:
        return "manual-review-required", "required binaries copied but no vendor lib/lib64 files were found", False
    return "vendor-root-ready", "minimal vendor root evidence is ready for v221 rerun", True


def build_export_plan(required_paths: list[dict[str, str]], v221_rerun_command: list[str]) -> dict[str, Any]:
    return {
        "mode": "vendor-root-evidence-export",
        "required_paths": required_paths,
        "allowlist": {
            "required_binaries": TARGET_REQUIRED_RELS,
            "recursive_dirs": ["lib/**", "lib64/**"],
            "context_files": CONTEXT_FILES,
        },
        "source_modes": [
            "operator-provided --source-vendor-root",
            "future TWRP/Android ADB pull into private host dir",
            "future reviewed native read-only export helper",
        ],
        "v221_rerun_command": v221_rerun_command,
    }


def build_summary(manifest: dict[str, Any]) -> str:
    required_rows = [
        [item["service"], item["expected_host_path"]]
        for item in manifest["required_paths"]
    ]
    copied_rows = [
        [item["relative_path"], str(item["size"]), item["sha256"][:16]]
        for item in manifest["copied_files"][:40]
    ]
    if len(manifest["copied_files"]) > 40:
        copied_rows.append(["...", f"{len(manifest['copied_files']) - 40} more", ""])
    skipped_rows = [
        [item["path"], item["reason"]]
        for item in manifest["skipped_files"][:40]
    ]
    lines = [
        "# v222 Vendor Root Evidence Export / Extraction",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        f"- source_root_status: `{manifest['source_root_status']}`",
        f"- copied_files: `{manifest['copied_file_count']}`",
        f"- copied_total_bytes: `{manifest['copied_total_bytes']}`",
        "",
        "## Required Vendor Paths",
        "",
        markdown_table(["service", "expected host path"], required_rows),
        "",
        "## Copied Files",
        "",
        markdown_table(["path", "size", "sha256 prefix"], copied_rows or [["none", "0", ""]]),
        "",
        "## Skipped Files",
        "",
        markdown_table(["path", "reason"], skipped_rows or [["none", "none"]]),
        "",
        "## v221 Rerun",
        "",
        "```bash",
        " ".join(manifest["v221_rerun_command"]),
        "```",
        "",
        "## Guardrails",
        "",
    ]
    for guardrail in manifest["guardrails"]:
        lines.append(f"- {guardrail}")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- `export-source-required` is a successful planning result when no source vendor root is available.",
        "- `vendor-root-ready` means the output can be passed to v221 `--vendor-root`.",
        "- This tool does not execute vendor binaries or start Wi-Fi services.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    validate_no_active_commands()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)

    v210 = load_json(args.v210_manifest)
    v221 = load_json(args.v221_manifest)
    required_paths = required_paths_from_v221(v221)
    source_root, source_status = normalize_source_root(args.source_vendor_root)
    vendor_root_out = out_dir / "vendor-root"
    v221_rerun_command = build_v221_rerun_command(vendor_root_out)

    copied_files: list[dict[str, Any]] = []
    skipped_files: list[dict[str, str]] = []
    planned_files: list[dict[str, Any]] = []
    missing_required: list[dict[str, Any]] = []
    resolved_required: list[str] = []
    limit_error: str | None = None

    if source_status == "ok" and source_root is not None:
        candidate_rels, skipped_files = collect_candidate_rels(source_root, required_paths)
        planned_files, skipped_more, missing_required, resolved_required, limit_error = plan_copy(
            source_root,
            candidate_rels,
            required_paths,
            args.max_files,
            args.max_total_bytes,
        )
        skipped_files.extend(skipped_more)
        if limit_error is None and not missing_required:
            copied_files = copy_plan(planned_files, vendor_root_out)

    library_file_count = sum(
        1
        for item in copied_files
        if item["relative_path"].startswith("lib/") or item["relative_path"].startswith("lib64/")
    )
    copied_total_bytes = sum(int(item["size"]) for item in copied_files)
    decision, reason, pass_ok = decide(source_status, limit_error, missing_required, copied_files, library_file_count)
    export_plan = build_export_plan(required_paths, v221_rerun_command)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "mode": "vendor-root-evidence-export",
        "source_root": str(source_root) if source_root else None,
        "source_root_status": source_status,
        "output_vendor_root": str(vendor_root_out) if copied_files else None,
        "inputs": {
            "v210_manifest": str(repo_path(args.v210_manifest)),
            "v221_manifest": str(repo_path(args.v221_manifest)),
            "v210_decision": v210.get("decision"),
            "v221_decision": v221.get("decision"),
        },
        "required_paths": required_paths,
        "resolved_required_paths": resolved_required,
        "missing_required_paths": missing_required,
        "planned_file_count": len(planned_files),
        "copied_file_count": len(copied_files),
        "copied_total_bytes": copied_total_bytes,
        "library_file_count": library_file_count,
        "copy_limits": {
            "max_files": args.max_files,
            "max_total_bytes": args.max_total_bytes,
            "limit_error": limit_error,
        },
        "copied_files": copied_files,
        "skipped_files": skipped_files,
        "v221_rerun_command": v221_rerun_command,
        "guardrails": [
            "no live device commands by default",
            "no full partition dump",
            "no device writes",
            "no vendor binary execution",
            "private output directory",
            "no-follow destination writes",
            "no Wi-Fi credential paths",
            "no rfkill write",
            "no link-up",
            "no scan/connect",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_json("export-plan.json", export_plan)
    store.write_text("summary.md", build_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
