#!/usr/bin/env python3
"""Clean classified tmp artifacts while preserving evidence records."""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import stat
import time
from pathlib import Path
from typing import Any

from a90harness.evidence import (
    REPO_ROOT,
    WIFI_TMP_ROOT,
    write_private_json,
)


TMP_ROOT = REPO_ROOT / "tmp"
ARCHIVE_ROOT = WIFI_TMP_ROOT / "archive"
V766_KERNEL_OUT = WIFI_TMP_ROOT / "v766-icnss-qcacld-patch-apply-build" / "source" / "out"
ELF_MAGIC = b"\x7fELF"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="apply cleanup actions")
    parser.add_argument("--json", action="store_true", help="emit machine-readable plan")
    parser.add_argument("--ncm-benchmark-payloads", action="store_true", help="remove NCM benchmark *.bin payloads")
    parser.add_argument("--kernel-build-out", action="store_true", help="remove known generated kernel build output")
    parser.add_argument("--root-build-products", action="store_true", help="remove root tmp ELF helper build products")
    parser.add_argument("--compress-bridge-logs", action="store_true", help="gzip large root bridge logs and remove originals")
    parser.add_argument("--bridge-min-mib", type=float, default=16.0, help="minimum bridge log size to compress")
    parser.add_argument("--all-safe", action="store_true", help="enable all conservative classified cleanup groups")
    parser.add_argument("--manifest", type=Path, help="manifest path written before execution")
    return parser.parse_args()


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def path_size(path: Path) -> int:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return 0
    if stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
        return info.st_size
    total = 0
    for child in path.rglob("*"):
        try:
            total += child.lstat().st_size
        except FileNotFoundError:
            pass
    return total


def regular_file(path: Path) -> bool:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISREG(info.st_mode) and not stat.S_ISLNK(info.st_mode)


def elf_file(path: Path) -> bool:
    if not regular_file(path):
        return False
    try:
        with path.open("rb") as file_obj:
            return file_obj.read(4) == ELF_MAGIC
    except OSError:
        return False


def removal(path: Path, category: str, reason: str) -> dict[str, Any]:
    return {
        "action": "remove",
        "path": rel(path),
        "category": category,
        "reason": reason,
        "bytes": path_size(path),
    }


def compression(path: Path, category: str, reason: str) -> dict[str, Any]:
    return {
        "action": "compress-gzip-remove-original",
        "path": rel(path),
        "gzip_path": rel(path.with_suffix(path.suffix + ".gz")),
        "category": category,
        "reason": reason,
        "bytes": path_size(path),
    }


def plan_ncm_payloads() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for root in sorted(WIFI_TMP_ROOT.glob("a90-ncm-transport-smoke*")):
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.bin")):
            if regular_file(path):
                items.append(removal(path, "wifi-benchmark-payload", "generated NCM dummy payload"))
    return items


def plan_kernel_build_out() -> list[dict[str, Any]]:
    if V766_KERNEL_OUT.exists():
        return [removal(V766_KERNEL_OUT, "wifi-kernel-build-output", "generated kernel build out directory")]
    return []


def plan_root_build_products() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for path in sorted(TMP_ROOT.iterdir() if TMP_ROOT.exists() else []):
        if not path.name.startswith("a90_") or "_v" not in path.name:
            continue
        if elf_file(path):
            items.append(removal(path, "root-helper-build-product", "root tmp ELF helper build product"))
    return items


def plan_bridge_logs(min_mib: float) -> list[dict[str, Any]]:
    min_bytes = int(min_mib * 1024 * 1024)
    items: list[dict[str, Any]] = []
    for path in sorted(TMP_ROOT.glob("bridge-*.log")):
        if not regular_file(path) or path_size(path) < min_bytes:
            continue
        if path.with_suffix(path.suffix + ".gz").exists():
            continue
        items.append(compression(path, "root-bridge-log", f"bridge log >= {min_mib:g} MiB"))
    return items


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    use_all = bool(args.all_safe)
    actions: list[dict[str, Any]] = []
    if use_all or args.ncm_benchmark_payloads:
        actions.extend(plan_ncm_payloads())
    if use_all or args.kernel_build_out:
        actions.extend(plan_kernel_build_out())
    if use_all or args.root_build_products:
        actions.extend(plan_root_build_products())
    if use_all or args.compress_bridge_logs:
        actions.extend(plan_bridge_logs(args.bridge_min_mib))
    return {
        "mode": "execute" if args.execute else "dry-run",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %z"),
        "actions": actions,
        "action_count": len(actions),
        "planned_remove_bytes": sum(int(item["bytes"]) for item in actions if item["action"] == "remove"),
        "planned_compress_input_bytes": sum(
            int(item["bytes"]) for item in actions if item["action"].startswith("compress")
        ),
    }


def assert_under_tmp(path: Path) -> None:
    resolved = path.resolve()
    tmp_resolved = TMP_ROOT.resolve()
    if resolved != tmp_resolved and tmp_resolved not in resolved.parents:
        raise RuntimeError(f"refusing path outside tmp: {path}")


def remove_path(path: Path) -> None:
    assert_under_tmp(path)
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def gzip_and_remove(path: Path) -> None:
    assert_under_tmp(path)
    output = path.with_suffix(path.suffix + ".gz")
    assert_under_tmp(output)
    tmp_output = output.with_suffix(output.suffix + ".tmp")
    with path.open("rb") as src, tmp_output.open("wb") as raw_dst:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_dst, compresslevel=1, mtime=0) as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
    tmp_output.replace(output)
    path.unlink()


def default_manifest_path() -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return ARCHIVE_ROOT / f"cleanup-tmp-classified-manifest-{stamp}.json"


def execute_plan(plan: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for item in plan["actions"]:
        path = REPO_ROOT / item["path"]
        before = path_size(path)
        if item["action"] == "remove":
            remove_path(path)
            result = dict(item)
            result["before_bytes"] = before
            result["after_bytes"] = 0
            results.append(result)
        elif item["action"] == "compress-gzip-remove-original":
            gzip_path = REPO_ROOT / item["gzip_path"]
            gzip_and_remove(path)
            result = dict(item)
            result["before_bytes"] = before
            result["gzip_bytes"] = path_size(gzip_path)
            result["freed_bytes_estimate"] = before - result["gzip_bytes"]
            results.append(result)
        else:
            raise RuntimeError(f"unknown action: {item['action']}")
    executed = dict(plan)
    executed["results"] = results
    executed["executed_count"] = len(results)
    executed["executed_freed_bytes_estimate"] = sum(
        int(item.get("freed_bytes_estimate", item.get("before_bytes", 0))) for item in results
    )
    return executed


def main() -> int:
    args = parse_args()
    plan = build_plan(args)
    if args.execute:
        manifest = args.manifest or default_manifest_path()
        plan["manifest"] = rel(manifest)
        write_private_json(manifest, plan)
        plan = execute_plan(plan)
        plan["manifest"] = rel(manifest)
        write_private_json(manifest, plan)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"mode: {plan['mode']}")
        print(f"actions: {plan['action_count']}")
        print(f"planned_remove_bytes: {plan['planned_remove_bytes']}")
        print(f"planned_compress_input_bytes: {plan['planned_compress_input_bytes']}")
        for item in plan["actions"][:100]:
            print(f"{item['action']} {item['bytes']}B {item['path']} ({item['category']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
