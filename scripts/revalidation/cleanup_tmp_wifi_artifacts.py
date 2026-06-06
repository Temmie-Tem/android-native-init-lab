#!/usr/bin/env python3
"""Plan or remove local tmp/wifi artifacts under the structured layout."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import stat
import time
from pathlib import Path
from typing import Any

from a90harness.evidence import (
    DOC_ARTIFACT_ROOT,
    TMP_LOG_KINDS,
    TMP_LOG_ROOT,
    WIFI_ARTIFACT_KINDS,
    WIFI_TMP_ROOT,
    ensure_private_dir,
    ensure_public_dir,
    write_private_json,
)


DEFAULT_KEEP_PREFIXES = (
    "v2167-connect-dhcp-google-ping-handoff-v726",
    "v725-fasttransport-baseline-validation",
    "v726-wifi-lifecycle-test-boot",
)
STRUCTURED_KINDS = ("runs", "builds", "cache", "bench", "scratch", "archive")
BUILD_PRODUCT_PATTERNS = (
    ("boot-image", re.compile(r"^boot_linux.*\.img$")),
    ("ramdisk", re.compile(r"^ramdisk.*\.cpio$")),
    ("init-binary", re.compile(r"^init_v[0-9][A-Za-z0-9_-]*$")),
    ("helper-binary", re.compile(r"^a90_[A-Za-z0-9_-]*_v[0-9][A-Za-z0-9_-]*$")),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="delete selected artifacts")
    parser.add_argument("--init-layout", action="store_true", help="create tmp/docs artifact roots")
    parser.add_argument("--json", action="store_true", help="emit machine-readable plan")
    parser.add_argument("--scratch-days", type=float, default=0.0)
    parser.add_argument("--builds-days", type=float, default=14.0)
    parser.add_argument("--bench-days", type=float, default=14.0)
    parser.add_argument("--cache-days", type=float, help="prune cache entries older than this many days")
    parser.add_argument("--archive-days", type=float, help="prune archive entries older than this many days")
    parser.add_argument("--include-legacy-flat", action="store_true", help="allow pruning old tmp/wifi flat entries")
    parser.add_argument("--legacy-days", type=float, help="required with --include-legacy-flat")
    parser.add_argument(
        "--legacy-build-products-only",
        action="store_true",
        help="select generated build-product files inside legacy flat directories without removing logs/evidence dirs",
    )
    parser.add_argument(
        "--legacy-build-product-days",
        type=float,
        default=0.0,
        help="age threshold for --legacy-build-products-only file candidates",
    )
    parser.add_argument("--keep-prefix", action="append", default=list(DEFAULT_KEEP_PREFIXES))
    parser.add_argument("--top", type=int, default=30, help="number of protected legacy entries to show")
    parser.add_argument("--write-plan", type=Path, help="write the computed JSON plan to this path")
    parser.add_argument("--delete-manifest", type=Path, help="manifest path written before --execute deletion")
    return parser.parse_args()


def path_size(path: Path) -> int:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return 0
    if stat.S_ISLNK(info.st_mode) or stat.S_ISREG(info.st_mode):
        return info.st_size
    total = 0
    for child in path.rglob("*"):
        try:
            total += child.lstat().st_size
        except FileNotFoundError:
            pass
    return total


def age_days(path: Path, now: float) -> float:
    try:
        return max(0.0, (now - path.lstat().st_mtime) / 86400.0)
    except FileNotFoundError:
        return 0.0


def is_kept(path: Path, keep_prefixes: list[str]) -> bool:
    return any(path.name.startswith(prefix) for prefix in keep_prefixes)


def direct_children(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.iterdir(), key=lambda item: str(item))


def removal_item(path: Path, kind: str, reason: str, now: float) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(WIFI_TMP_ROOT.parent.parent)),
        "kind": kind,
        "reason": reason,
        "age_days": round(age_days(path, now), 3),
        "bytes": path_size(path),
    }


def threshold_plan(kind: str,
                   threshold_days: float | None,
                   keep_prefixes: list[str],
                   now: float) -> list[dict[str, Any]]:
    if threshold_days is None:
        return []
    root = WIFI_TMP_ROOT / kind
    items: list[dict[str, Any]] = []
    for path in direct_children(root):
        if path.name.startswith(".") or is_kept(path, keep_prefixes):
            continue
        item_age = age_days(path, now)
        if item_age >= threshold_days:
            items.append(removal_item(path, kind, f"{kind}-older-than-{threshold_days:g}d", now))
    return items


def legacy_entries() -> list[Path]:
    roots = set(STRUCTURED_KINDS)
    entries: list[Path] = []
    for path in direct_children(WIFI_TMP_ROOT):
        if path.name in roots or path.name.startswith("."):
            continue
        entries.append(path)
    return entries


def legacy_class(path: Path) -> str:
    name = path.name
    if name.startswith("a90-ncm-transport-smoke"):
        return "legacy-bench"
    if "build" in name or "source" in name or "extract" in name or "cache" in name:
        return "legacy-build-cache"
    if name.startswith("v") and "-test-boot" in name:
        return "legacy-test-boot"
    if name.startswith("v"):
        return "legacy-run"
    return "legacy-other"


def build_product_kind(path: Path) -> str | None:
    if not path.is_file() and not path.is_symlink():
        return None
    name = path.name
    for kind, pattern in BUILD_PRODUCT_PATTERNS:
        if pattern.match(name):
            return f"legacy-build-product-{kind}"
    return None


def legacy_build_product_plan(args: argparse.Namespace, now: float) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for root in legacy_entries():
        if is_kept(root, args.keep_prefix):
            continue
        candidates = [root] if root.is_file() or root.is_symlink() else sorted(root.rglob("*"))
        for path in candidates:
            kind = build_product_kind(path)
            if kind is None:
                continue
            if age_days(path, now) < args.legacy_build_product_days:
                continue
            items.append(
                removal_item(
                    path,
                    kind,
                    f"legacy-build-product-file-older-than-{args.legacy_build_product_days:g}d",
                    now,
                )
            )
    return items


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    if args.include_legacy_flat and args.legacy_days is None:
        raise SystemExit("--legacy-days is required with --include-legacy-flat")
    now = time.time()
    removals: list[dict[str, Any]] = []
    removals.extend(threshold_plan("scratch", args.scratch_days, args.keep_prefix, now))
    removals.extend(threshold_plan("builds", args.builds_days, args.keep_prefix, now))
    removals.extend(threshold_plan("bench", args.bench_days, args.keep_prefix, now))
    removals.extend(threshold_plan("cache", args.cache_days, args.keep_prefix, now))
    removals.extend(threshold_plan("archive", args.archive_days, args.keep_prefix, now))
    if args.legacy_build_products_only:
        removals.extend(legacy_build_product_plan(args, now))

    protected_legacy: list[dict[str, Any]] = []
    legacy_removals: list[dict[str, Any]] = []
    for path in legacy_entries():
        entry = removal_item(path, legacy_class(path), "legacy-flat-protected", now)
        if is_kept(path, args.keep_prefix):
            protected_legacy.append(entry)
            continue
        if args.include_legacy_flat and args.legacy_days is not None and age_days(path, now) >= args.legacy_days:
            entry["reason"] = f"legacy-flat-older-than-{args.legacy_days:g}d"
            legacy_removals.append(entry)
        else:
            protected_legacy.append(entry)
    removals.extend(legacy_removals)

    return {
        "mode": "execute" if args.execute else "dry-run",
        "root": str(WIFI_TMP_ROOT),
        "structured_kinds": list(STRUCTURED_KINDS),
        "keep_prefixes": args.keep_prefix,
        "remove_count": len(removals),
        "remove_bytes": sum(int(item["bytes"]) for item in removals),
        "removals": removals,
        "legacy_build_products_only": bool(args.legacy_build_products_only),
        "legacy_build_product_days": args.legacy_build_product_days,
        "build_product_patterns": [pattern.pattern for _kind, pattern in BUILD_PRODUCT_PATTERNS],
        "protected_legacy_count": len(protected_legacy),
        "protected_legacy_bytes": sum(int(item["bytes"]) for item in protected_legacy),
        "protected_legacy_top": sorted(protected_legacy, key=lambda item: int(item["bytes"]), reverse=True)[:args.top],
    }


def delete_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def execute_plan(plan: dict[str, Any]) -> None:
    for item in plan["removals"]:
        path = WIFI_TMP_ROOT.parent.parent / item["path"]
        if not path.exists() and not path.is_symlink():
            continue
        if WIFI_TMP_ROOT not in path.resolve().parents and path.resolve() != WIFI_TMP_ROOT:
            raise RuntimeError(f"refusing path outside tmp/wifi: {path}")
        delete_path(path)


def default_delete_manifest_path() -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return WIFI_TMP_ROOT / "archive" / f"cleanup-tmp-wifi-delete-manifest-{stamp}.json"


def init_layout() -> None:
    ensure_private_dir(WIFI_TMP_ROOT)
    for kind in WIFI_ARTIFACT_KINDS:
        ensure_private_dir(WIFI_TMP_ROOT / kind)
    ensure_private_dir(TMP_LOG_ROOT)
    for kind in TMP_LOG_KINDS:
        ensure_private_dir(TMP_LOG_ROOT / kind)
    ensure_public_dir(DOC_ARTIFACT_ROOT)


def render_text(plan: dict[str, Any]) -> str:
    lines = [
        f"mode: {plan['mode']}",
        f"root: {plan['root']}",
        f"remove: {plan['remove_count']} entries, {plan['remove_bytes']} bytes",
        f"protected_legacy: {plan['protected_legacy_count']} entries, {plan['protected_legacy_bytes']} bytes",
    ]
    for item in plan["removals"]:
        lines.append(f"remove {item['bytes']}B age={item['age_days']}d {item['path']} ({item['reason']})")
    if plan["protected_legacy_top"]:
        lines.append("protected_legacy_top:")
        for item in plan["protected_legacy_top"]:
            lines.append(f"keep {item['bytes']}B age={item['age_days']}d {item['path']} ({item['kind']})")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    if args.init_layout:
        init_layout()
    plan = build_plan(args)
    if args.write_plan is not None:
        write_private_json(args.write_plan, plan)
    if args.execute:
        manifest_path = args.delete_manifest or default_delete_manifest_path()
        plan = dict(plan)
        plan["delete_manifest"] = str(manifest_path)
        write_private_json(manifest_path, plan)
        execute_plan(plan)
    if args.json:
        print(json.dumps(plan, indent=2, sort_keys=True))
    else:
        print(render_text(plan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
