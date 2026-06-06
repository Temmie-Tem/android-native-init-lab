#!/usr/bin/env python3
"""V760 host-only Samsung source staging verifier.

V759 identified the exact Samsung OSRC source package, but the download is
manual-gated. V760 checks whether the operator has staged the official archive
or extracted source tree, and verifies target QCACLD/ICNSS source visibility
without extracting large archives or loading them into memory.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import tarfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, workspace_private_input_path, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v760-source-staging")
DEFAULT_V759_MANIFEST = Path("tmp/wifi/v759-source-acquisition/manifest.json")
EXPECTED_FILENAME = "SM-A908N_KOR_12_Opensource.zip"
KERNEL_SOURCE_INPUT = workspace_private_input_path("kernel_source", legacy_fallback=False)

ARCHIVE_CANDIDATES = (
    KERNEL_SOURCE_INPUT / EXPECTED_FILENAME,
    KERNEL_SOURCE_INPUT / "source" / EXPECTED_FILENAME,
    KERNEL_SOURCE_INPUT / "downloads" / EXPECTED_FILENAME,
    Path("kernel_build") / EXPECTED_FILENAME,
    Path("kernel_build/source") / EXPECTED_FILENAME,
    Path("kernel_build/downloads") / EXPECTED_FILENAME,
    Path(EXPECTED_FILENAME),
    Path("../") / EXPECTED_FILENAME,
    Path.home() / "Downloads" / EXPECTED_FILENAME,
)

SOURCE_ROOT_CANDIDATES = (
    KERNEL_SOURCE_INPUT / "source" / "SM-A908N_KOR_12_Opensource",
    KERNEL_SOURCE_INPUT / "SM-A908N_KOR_12_Opensource",
    KERNEL_SOURCE_INPUT / "source",
    Path("kernel_build/source/SM-A908N_KOR_12_Opensource"),
    Path("kernel_build/SM-A908N_KOR_12_Opensource"),
    Path("kernel_build/source"),
    Path("SM-A908N_KOR_12_Opensource"),
)

TARGET_SOURCE_GROUPS = {
    "qcacld_hdd_main": (
        "drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c",
        "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.c",
    ),
    "qcacld_hdd_driver_ops": (
        "drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c",
        "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c",
    ),
    "qcacld_pld_snoc": (
        "drivers/staging/qcacld-3.0/core/pld/src/pld_snoc.c",
        "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/src/pld_snoc.c",
    ),
    "icnss_core": (
        "drivers/soc/qcom/icnss.c",
    ),
    "icnss_qmi": (
        "drivers/soc/qcom/icnss_qmi.c",
    ),
}

TARGET_SOURCE_SUFFIXES = tuple(
    suffix
    for suffixes in TARGET_SOURCE_GROUPS.values()
    for suffix in suffixes
)

NESTED_ARCHIVE_SUFFIXES = (
    ".zip",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".tar.xz",
    ".txz",
    ".tar.bz2",
    ".tbz2",
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v759-manifest", type=Path, default=DEFAULT_V759_MANIFEST)
    parser.add_argument(
        "--extra-source",
        action="append",
        type=Path,
        default=[],
        help="Additional archive or extracted source path to inspect.",
    )
    parser.add_argument(
        "--hash-full",
        action="store_true",
        help="Compute full SHA-256 for staged archive files. Default records a 1 MiB prefix hash only.",
    )
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    return path.expanduser() if path.is_absolute() else repo_path(path)


def load_json(path: Path) -> dict[str, Any]:
    resolved = resolve_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def hash_file(path: Path, full: bool) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        if full:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        else:
            hasher.update(handle.read(1024 * 1024))
    return hasher.hexdigest()


def file_info(path: Path, hash_full: bool = False) -> dict[str, Any]:
    resolved = resolve_path(path)
    info: dict[str, Any] = {
        "path": str(resolved),
        "exists": resolved.exists(),
        "is_file": False,
        "is_dir": False,
        "size": None,
        "sha256": None,
        "sha256_mode": "full" if hash_full else "prefix-1m",
    }
    if not resolved.exists():
        return info
    info["is_file"] = resolved.is_file()
    info["is_dir"] = resolved.is_dir()
    info["size"] = resolved.stat().st_size if resolved.is_file() else None
    if resolved.is_file():
        info["sha256"] = hash_file(resolved, hash_full)
    return info


def empty_hits() -> dict[str, list[str]]:
    return {group: [] for group in TARGET_SOURCE_GROUPS}


def member_hits(members: list[str]) -> dict[str, list[str]]:
    hits = empty_hits()
    for member in members:
        normalized = member.strip("/")
        for group, suffixes in TARGET_SOURCE_GROUPS.items():
            if any(normalized.endswith(suffix) for suffix in suffixes):
                hits[group].append(normalized)
    return hits


def nested_archives(members: list[str]) -> list[str]:
    nested: list[str] = []
    for member in members:
        lower = member.lower()
        if any(lower.endswith(suffix) for suffix in NESTED_ARCHIVE_SUFFIXES):
            nested.append(member)
    return sorted(set(nested))[:200]


def inspect_zip(path: Path, hash_full: bool) -> dict[str, Any]:
    resolved = resolve_path(path)
    result: dict[str, Any] = {
        "file": file_info(path, hash_full),
        "kind": "zip",
        "readable": False,
        "member_count": 0,
        "target_hits": empty_hits(),
        "nested_archives": [],
        "error": "",
    }
    if not result["file"]["exists"] or not result["file"]["is_file"]:
        return result
    try:
        with zipfile.ZipFile(resolved) as archive:
            members = archive.namelist()
            result["readable"] = True
            result["member_count"] = len(members)
            result["target_hits"] = member_hits(members)
            result["nested_archives"] = nested_archives(members)
    except (OSError, zipfile.BadZipFile) as exc:
        result["error"] = str(exc)
    return result


def inspect_tar(path: Path, hash_full: bool) -> dict[str, Any]:
    resolved = resolve_path(path)
    result: dict[str, Any] = {
        "file": file_info(path, hash_full),
        "kind": "tar",
        "readable": False,
        "member_count": 0,
        "target_hits": empty_hits(),
        "nested_archives": [],
        "error": "",
    }
    if not result["file"]["exists"] or not result["file"]["is_file"]:
        return result
    try:
        members: list[str] = []
        with tarfile.open(resolved, "r:*") as archive:
            for member in archive:
                members.append(member.name)
        result["readable"] = True
        result["member_count"] = len(members)
        result["target_hits"] = member_hits(members)
        result["nested_archives"] = nested_archives(members)
    except (OSError, tarfile.TarError) as exc:
        result["error"] = str(exc)
    return result


def archive_kind(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".zip"):
        return "zip"
    if name.endswith((".tar", ".tar.gz", ".tgz", ".tar.xz", ".txz", ".tar.bz2", ".tbz2")):
        return "tar"
    return "unknown"


def inspect_archive(path: Path, hash_full: bool) -> dict[str, Any]:
    kind = archive_kind(path)
    if kind == "zip":
        return inspect_zip(path, hash_full)
    if kind == "tar":
        return inspect_tar(path, hash_full)
    return {
        "file": file_info(path, hash_full),
        "kind": kind,
        "readable": False,
        "member_count": 0,
        "target_hits": empty_hits(),
        "nested_archives": [],
        "error": "unsupported archive suffix" if file_info(path)["exists"] else "",
    }


def inspect_source_root(path: Path) -> dict[str, Any]:
    resolved = resolve_path(path)
    root = file_info(path)
    hits = empty_hits()
    if not root["exists"] or not root["is_dir"]:
        return {"root": root, "target_hits": hits, "searched": False}
    for group, suffixes in TARGET_SOURCE_GROUPS.items():
        for suffix in suffixes:
            exact = resolved / suffix
            if exact.exists():
                hits[group].append(str(exact))
                break
        if hits[group]:
            continue
        basename = Path(suffixes[0]).name
        for candidate in resolved.rglob(basename):
            normalized = str(candidate).replace("\\", "/")
            if any(normalized.endswith(suffix) for suffix in suffixes):
                hits[group].append(str(candidate))
                if len(hits[group]) >= 20:
                    break
    return {"root": root, "target_hits": hits, "searched": True}


def count_hits(items: list[dict[str, Any]], key: str) -> int:
    count = 0
    for item in items:
        hits = item.get(key)
        if isinstance(hits, dict):
            count += sum(1 for values in hits.values() if isinstance(values, list) and values)
    return count


def verified_groups(*items: list[dict[str, Any]]) -> list[str]:
    groups: set[str] = set()
    for collection in items:
        for item in collection:
            hits = item.get("target_hits")
            if isinstance(hits, dict):
                groups.update(group for group, values in hits.items() if isinstance(values, list) and values)
    return sorted(groups)


def missing_groups(groups: list[str]) -> list[str]:
    present = set(groups)
    return [group for group in TARGET_SOURCE_GROUPS if group not in present]


def staged_paths(extra_sources: list[Path]) -> tuple[list[Path], list[Path]]:
    archive_candidates = list(ARCHIVE_CANDIDATES)
    root_candidates = list(SOURCE_ROOT_CANDIDATES)
    for source in extra_sources:
        resolved = resolve_path(source)
        if resolved.is_dir():
            root_candidates.append(source)
        else:
            archive_candidates.append(source)
    for root in root_candidates:
        resolved = resolve_path(root)
        if not resolved.is_dir():
            continue
        for child in resolved.iterdir():
            if child.is_file() and archive_kind(child) in {"zip", "tar"}:
                archive_candidates.append(child)
    return archive_candidates, root_candidates


def build_analysis(args: argparse.Namespace) -> dict[str, Any]:
    v759 = load_json(args.v759_manifest)
    archive_candidates, root_candidates = staged_paths(args.extra_source)
    archives = [inspect_archive(path, args.hash_full) for path in archive_candidates]
    roots = [inspect_source_root(path) for path in root_candidates]
    archive_present = any(item["file"]["exists"] for item in archives)
    archive_readable = any(item["readable"] for item in archives)
    archive_target_hits = count_hits(archives, "target_hits")
    root_target_hits = count_hits(roots, "target_hits")
    target_groups_verified = verified_groups(archives, roots)
    target_groups_missing = missing_groups(target_groups_verified)
    nested_archive_count = sum(len(item.get("nested_archives") or []) for item in archives)
    target_sources_verified = not target_groups_missing
    return {
        "v759": {
            "manifest": str(resolve_path(args.v759_manifest)),
            "decision": v759.get("decision", ""),
            "pass": bool(v759.get("pass")),
            "device_mutations": bool(v759.get("device_mutations")),
            "boot_image_write_executed": bool(v759.get("boot_image_write_executed")),
        },
        "stage": {
            "archive_candidates": archives,
            "source_root_candidates": roots,
            "archive_present": archive_present,
            "archive_readable": archive_readable,
            "archive_target_hits": archive_target_hits,
            "root_target_hits": root_target_hits,
            "target_groups_verified": target_groups_verified,
            "target_groups_missing": target_groups_missing,
            "nested_archive_count": nested_archive_count,
            "target_sources_verified": target_sources_verified,
            "hash_mode": "full" if args.hash_full else "prefix-1m",
        },
        "route": {
            "source_stage_missing": not archive_present and root_target_hits == 0,
            "extract_required": archive_present and archive_readable and not target_sources_verified and nested_archive_count > 0,
            "target_sources_verified": target_sources_verified,
            "can_plan_kernel_instrumentation": target_sources_verified,
            "next_cycle": "v764-kernel-log-instrumentation-plan" if target_sources_verified else "v760-stage-official-source-and-rerun",
        },
    }


def add_check(
    checks: list[Check],
    name: str,
    status: str,
    severity: str,
    detail: str,
    evidence: list[str] | None = None,
    next_step: str = "",
) -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(analysis: dict[str, Any] | None) -> list[Check]:
    if not analysis:
        return []
    v759 = analysis["v759"]
    stage = analysis["stage"]
    route = analysis["route"]
    checks: list[Check] = []
    add_check(
        checks,
        "v759-input",
        "pass" if v759["decision"] == "v759-official-source-identified-manual-download-gated" and v759["pass"] else "blocked",
        "blocker",
        f"decision={v759['decision']} pass={v759['pass']} mutations={v759['device_mutations']} boot_write={v759['boot_image_write_executed']}",
        [v759["manifest"]],
        "complete V759 before V760",
    )
    add_check(
        checks,
        "source-stage-present",
        "review" if route["source_stage_missing"] else "pass",
        "finding",
        f"archive_present={stage['archive_present']} root_hits={stage['root_target_hits']}",
        [],
        "stage the official OSRC archive or extracted tree under kernel_build",
    )
    add_check(
        checks,
        "archive-readable",
        "pass" if stage["archive_readable"] or not stage["archive_present"] else "blocked",
        "blocker",
        f"archive_present={stage['archive_present']} archive_readable={stage['archive_readable']} hash_mode={stage['hash_mode']}",
        [],
        "replace unreadable staged archive before source verification",
    )
    add_check(
        checks,
        "target-source-files",
        "pass" if stage["target_sources_verified"] else "blocked",
        "blocker",
        f"archive_hits={stage['archive_target_hits']} root_hits={stage['root_target_hits']} nested_archives={stage['nested_archive_count']}",
        [],
        "extract nested source if needed, then verify QCACLD/ICNSS target files",
    )
    add_check(
        checks,
        "kernel-instrumentation-readiness",
        "pass" if route["can_plan_kernel_instrumentation"] else "blocked",
        "blocker",
        f"can_plan_kernel_instrumentation={route['can_plan_kernel_instrumentation']}",
        [],
        "do not patch or flash until target source files are verified",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v760-source-staging-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only source staging verifier after official source is staged",
        )
    if not analysis:
        return (
            "v760-source-staging-missing-analysis",
            False,
            "analysis missing",
            "rerun V760",
        )
    route = analysis["route"]
    blockers = blocking(checks)
    if route["can_plan_kernel_instrumentation"]:
        return (
            "v760-source-targets-verified",
            True,
            "staged source exposes required QCACLD/ICNSS target files",
            "V764 can plan minimal kernel log instrumentation without live flash",
        )
    if route["extract_required"]:
        return (
            "v760-source-archive-present-extract-required",
            True,
            "official archive is readable, but target files are inside nested archives or extracted source is not visible",
            "extract the official source under kernel_build/source and rerun V760",
        )
    if route["source_stage_missing"]:
        return (
            "v760-source-stage-missing",
            True,
            "official source archive/tree is not staged locally",
            "manually download the official source package, stage it under kernel_build, and rerun V760",
        )
    if blockers:
        return (
            "v760-source-staging-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear staging blockers before kernel instrumentation",
        )
    return (
        "v760-source-staging-review",
        True,
        "source staging classified but needs manual review",
        "inspect manifest before V761",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis") or {}
    stage = (analysis.get("stage") or {}) if isinstance(analysis, dict) else {}
    route = (analysis.get("route") or {}) if isinstance(analysis, dict) else {}
    return "\n".join([
        "# V760 Source Staging Verifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- boot_image_write_executed: `{manifest['boot_image_write_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]) if checks else "- plan only",
        "",
        "## Stage",
        "",
        markdown_table(["signal", "value"], [
            [key, value] for key, value in stage.items()
            if key not in ("archive_candidates", "source_root_candidates")
        ]) if stage else "- plan only",
        "",
        "## Route",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in route.items()]) if route else "- plan only",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis: dict[str, Any] | None = None
    if args.command != "plan":
        analysis = build_analysis(args)
    checks = build_checks(analysis)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest: dict[str, Any] = {
        "cycle": "v760",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "analysis": analysis or {},
        "checks": [asdict(check) for check in checks],
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    latest = repo_path("tmp/wifi/latest-v760-source-staging.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"boot_image_write_executed: {manifest['boot_image_write_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
