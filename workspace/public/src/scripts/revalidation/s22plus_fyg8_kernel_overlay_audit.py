#!/usr/bin/env python3
"""Audit the FYD9 base plus FYG8 kernel-source overlay without device access.

The tool reconstructs the final source manifest directly from the two pinned
archives. It never trusts an existing extracted tree as the source of truth and
never invokes a compiler, image tool, ADB, Odin, or a device transport.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import stat
import tarfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO


SCHEMA = "s22plus_fyg8_kernel_overlay_audit_v1"
TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
SOURCE_DATE_EPOCH = 1754027756
DEFAULT_BASE = Path(
    "workspace/private/inputs/s22plus_kernel_source/"
    "SM-S906N_15_base_osrc/Kernel.tar.gz"
)
DEFAULT_DELTA = Path(
    "workspace/private/inputs/s22plus_kernel_source/"
    "S906NKSS7FYG8_osrc/S906NKSS7FYG8_kernel.tar.gz"
)
DEFAULT_RESIDENT = Path("workspace/private/work/s22plus_fyg8_kernel_rebuild_r0")
DEFAULT_OUT = Path(
    "workspace/private/outputs/s22plus_fyg8_kernel_rebuild_r0/overlay-audit"
)
EXPECTED_BASE_SHA256 = "86e2f73412c65fadff0b15bbf0eac9140610f70250514ac0bddbf3b53fb5f7bf"
EXPECTED_DELTA_SHA256 = "23ef2b27de8843e271d41405b3c0b1a71bfa668615c8f0f12a1e5c4395ec851a"
class AuditError(ValueError):
    pass


@dataclass(frozen=True)
class Member:
    path: str
    type: str
    mode: int
    size: int
    sha256: str | None
    link_target: str | None


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "GOAL.md").is_file() and (parent / "AGENTS.md").is_file():
            return parent
    raise AuditError("repository root not found")


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else (root / path).resolve()


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path.resolve())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_stream(handle: BinaryIO) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def safe_path(name: str, *, delta: bool) -> str | None:
    if not name or name.startswith("/"):
        raise AuditError(f"unsafe archive member path: {name!r}")
    raw = PurePosixPath(name.rstrip("/"))
    if any(part in ("", ".", "..") for part in raw.parts):
        raise AuditError(f"unsafe archive member path: {name!r}")
    parts = list(raw.parts)
    if delta:
        if not parts or parts[0] != "Kernel":
            raise AuditError(f"delta member lacks exact Kernel/ prefix: {name!r}")
        parts = parts[1:]
        if not parts:
            return None
    return PurePosixPath(*parts).as_posix()


def safe_link_target(member_path: str, target: str, *, delta: bool, kind: str) -> str:
    if not target:
        raise AuditError(f"unsafe link target for {member_path}: {target!r}")
    if target.startswith("/"):
        if kind == "symlink":
            return target
        raise AuditError(f"unsafe absolute hardlink target for {member_path}: {target!r}")
    output_target = target
    target_path = PurePosixPath(target)
    if delta and kind == "hardlink" and target_path.parts and target_path.parts[0] == "Kernel":
        target_path = PurePosixPath(*target_path.parts[1:])
        output_target = target.removeprefix("Kernel/")
    if kind == "hardlink":
        normalized = posixpath.normpath(target_path.as_posix())
    else:
        normalized = posixpath.normpath(
            posixpath.join(posixpath.dirname(member_path), target_path.as_posix())
        )
    if normalized == ".." or normalized.startswith("../"):
        raise AuditError(f"link target escapes archive root for {member_path}: {target!r}")
    return output_target


def member_type(info: tarfile.TarInfo) -> str:
    if info.isfile():
        return "file"
    if info.isdir():
        return "directory"
    if info.issym():
        return "symlink"
    if info.islnk():
        return "hardlink"
    raise AuditError(f"unsupported archive member type for {info.name!r}: {info.type!r}")


def inspect_archive(path: Path, *, delta: bool) -> dict[str, Member]:
    members: dict[str, Member] = {}
    with tarfile.open(path, "r:gz") as archive:
        for info in archive:
            normalized = safe_path(info.name, delta=delta)
            if normalized is None:
                continue
            if normalized in members:
                raise AuditError(f"duplicate normalized archive member: {normalized}")
            kind = member_type(info)
            content_sha: str | None = None
            link_target: str | None = None
            if kind == "file":
                extracted = archive.extractfile(info)
                if extracted is None:
                    raise AuditError(f"could not read archive member: {info.name}")
                with extracted:
                    content_sha = sha256_stream(extracted)
            elif kind in ("symlink", "hardlink"):
                link_target = safe_link_target(
                    normalized,
                    info.linkname,
                    delta=delta,
                    kind=kind,
                )
            members[normalized] = Member(
                path=normalized,
                type=kind,
                mode=stat.S_IMODE(info.mode),
                size=info.size,
                sha256=content_sha,
                link_target=link_target,
            )
    links = {
        name
        for name, member in members.items()
        if member.type in ("symlink", "hardlink")
    }
    for name in members:
        parent = PurePosixPath(name).parent
        while parent != PurePosixPath("."):
            if parent.as_posix() in links:
                raise AuditError(
                    f"archive member traverses a link ancestor: {name} via {parent}"
                )
            parent = parent.parent
    resolving: set[str] = set()

    def resolve_hardlink(name: str) -> Member:
        member = members[name]
        if member.type != "hardlink":
            return member
        if name in resolving:
            raise AuditError(f"hardlink cycle detected at {name}")
        resolving.add(name)
        target_name = member.link_target or ""
        target = members.get(target_name)
        if target is None:
            raise AuditError(f"hardlink target is absent: {name} -> {target_name}")
        target = resolve_hardlink(target_name)
        if target.type not in ("file", "hardlink") or target.sha256 is None:
            raise AuditError(f"hardlink target is not a regular file: {name} -> {target_name}")
        resolved = Member(
            path=member.path,
            type="hardlink",
            mode=member.mode,
            size=target.size,
            sha256=target.sha256,
            link_target=member.link_target,
        )
        members[name] = resolved
        resolving.remove(name)
        return resolved

    for name in tuple(members):
        resolve_hardlink(name)
    return members


def equivalent(left: Member, right: Member) -> bool:
    return (
        left.type,
        left.mode,
        left.size,
        left.sha256,
        left.link_target,
    ) == (
        right.type,
        right.mode,
        right.size,
        right.sha256,
        right.link_target,
    )


def render_jsonl(rows: list[dict[str, object]]) -> str:
    return "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)


def inspect_resident(final: dict[str, Member], resident: Path) -> dict[str, object]:
    missing: list[str] = []
    mismatched: list[str] = []
    checked = 0
    for name, expected in sorted(final.items()):
        candidate = resident / name
        checked += 1
        if expected.type == "directory":
            matched = candidate.is_dir() and not candidate.is_symlink()
        elif expected.type == "symlink":
            matched = candidate.is_symlink() and os.readlink(candidate) == expected.link_target
        elif expected.type == "hardlink":
            matched = candidate.is_file() and not candidate.is_symlink()
            if matched:
                matched = candidate.stat().st_size == expected.size and sha256_file(candidate) == expected.sha256
        else:
            matched = candidate.is_file() and not candidate.is_symlink()
            if matched:
                matched = candidate.stat().st_size == expected.size and sha256_file(candidate) == expected.sha256
        if not candidate.exists() and not candidate.is_symlink():
            missing.append(name)
        elif not matched:
            mismatched.append(name)
    return {
        "checked_members": checked,
        "match": not missing and not mismatched,
        "missing_count": len(missing),
        "mismatch_count": len(mismatched),
        "missing_sample": missing[:20],
        "mismatch_sample": mismatched[:20],
    }


def build_artifacts(
    root: Path,
    base_path: Path,
    delta_path: Path,
    resident: Path | None,
) -> dict[str, str]:
    base_sha = sha256_file(base_path)
    delta_sha = sha256_file(delta_path)
    if base_sha != EXPECTED_BASE_SHA256:
        raise AuditError(f"base archive SHA256 mismatch: {base_sha}")
    if delta_sha != EXPECTED_DELTA_SHA256:
        raise AuditError(f"delta archive SHA256 mismatch: {delta_sha}")

    base = inspect_archive(base_path, delta=False)
    delta = inspect_archive(delta_path, delta=True)
    final = dict(base)
    overlay_rows: list[dict[str, object]] = []
    counts = {"added": 0, "replaced_identical": 0, "replaced_changed": 0}
    for name, member in sorted(delta.items()):
        previous = base.get(name)
        if previous is None:
            classification = "added"
        elif equivalent(previous, member):
            classification = "replaced_identical"
        else:
            classification = "replaced_changed"
        counts[classification] += 1
        overlay_rows.append(
            {
                **asdict(member),
                "classification": classification,
                "base_sha256": previous.sha256 if previous else None,
                "base_type": previous.type if previous else None,
            }
        )
        final[name] = member

    base_rows = [asdict(base[name]) for name in sorted(base)]
    delta_rows = [asdict(delta[name]) for name in sorted(delta)]
    final_rows = [
        {
            **asdict(final[name]),
            "source": "delta" if name in delta else "base",
        }
        for name in sorted(final)
    ]
    artifacts = {
        "base-members.jsonl": render_jsonl(base_rows),
        "delta-members.jsonl": render_jsonl(delta_rows),
        "overlay-members.jsonl": render_jsonl(overlay_rows),
        "reconstructed-final-members.jsonl": render_jsonl(final_rows),
    }
    resident_result: dict[str, object] = {"checked": False}
    if resident is not None:
        if not resident.is_dir():
            raise AuditError(f"resident tree missing: {resident}")
        resident_result = {
            "checked": True,
            "path": display_path(root, resident),
            **inspect_resident(final, resident),
        }
    manifest = {
        "schema": SCHEMA,
        "target": TARGET,
        "generated_epoch": SOURCE_DATE_EPOCH,
        "host_only": True,
        "inputs": [
            {"path": display_path(root, base_path), "sha256": base_sha, "size": base_path.stat().st_size},
            {"path": display_path(root, delta_path), "sha256": delta_sha, "size": delta_path.stat().st_size},
        ],
        "summary": {
            "base_members": len(base),
            "delta_members": len(delta),
            "final_members": len(final),
            **counts,
            "base_absolute_symlinks": sum(
                1
                for member in base.values()
                if member.type == "symlink" and (member.link_target or "").startswith("/")
            ),
            "delta_absolute_symlinks": sum(
                1
                for member in delta.values()
                if member.type == "symlink" and (member.link_target or "").startswith("/")
            ),
            "deletion_detectable": False,
            "interpretation": "content-addressed archive reconstruction; tar overlay cannot express deletions",
        },
        "resident_tree": resident_result,
        "artifacts": {
            name: {
                "sha256": hashlib.sha256(text.encode("ascii")).hexdigest(),
                "bytes": len(text.encode("ascii")),
            }
            for name, text in sorted(artifacts.items())
        },
        "safety": {
            "device_contact": False,
            "compiler_invocation": False,
            "image_packaging": False,
            "flash": False,
            "partition_write": False,
        },
    }
    artifacts["manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    return artifacts


def write_artifacts(out_dir: Path, artifacts: dict[str, str]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    stale = sorted(path.name for path in out_dir.iterdir() if path.is_file() and path.name not in artifacts)
    if stale:
        raise AuditError(f"refusing to leave stale output files: {stale}")
    for name, text in artifacts.items():
        (out_dir / name).write_text(text, encoding="ascii")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--delta", type=Path, default=DEFAULT_DELTA)
    parser.add_argument("--resident-tree", type=Path)
    parser.add_argument("--check-resident", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = repo_root()
    resident_arg = args.resident_tree
    if args.check_resident and resident_arg is None:
        resident_arg = DEFAULT_RESIDENT
    artifacts = build_artifacts(
        root,
        resolve(root, args.base),
        resolve(root, args.delta),
        resolve(root, resident_arg) if resident_arg is not None else None,
    )
    out_dir = resolve(root, args.out)
    write_artifacts(out_dir, artifacts)
    manifest = json.loads(artifacts["manifest.json"])
    resident_result = manifest["resident_tree"]
    if resident_result.get("checked") and not resident_result.get("match"):
        raise AuditError(
            "resident tree differs from reconstructed source: "
            f"missing={resident_result['missing_count']} "
            f"mismatched={resident_result['mismatch_count']}"
        )
    print(json.dumps({"result": "pass", "out": display_path(root, out_dir), **manifest["summary"], "resident_tree": manifest["resident_tree"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditError, OSError, tarfile.TarError) as exc:
        raise SystemExit(str(exc)) from exc
