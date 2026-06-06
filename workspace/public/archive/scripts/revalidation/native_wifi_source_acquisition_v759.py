#!/usr/bin/env python3
"""V759 host-only Samsung OSRC source acquisition/staging gate.

V758 proved that rollback-safe kernel log instrumentation is only sensible
after exact kernel/QCACLD/CNSS source exists locally. V759 identifies the
official Samsung OSRC package, records the download gate, and checks whether the
source archive or extracted source is already staged. It performs no device
action.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, workspace_private_input_path, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v759-source-acquisition")
DEFAULT_V758_MANIFEST = Path("tmp/wifi/v758-kernel-instrumentation-feasibility/manifest.json")
DEFAULT_OSRC_HTML = Path("tmp/source/v759-osrc-probe/A908NKSU5EWA3.html")
DEFAULT_OSRC_PAGE_JSON = Path("tmp/source/v759-osrc-browser/page-meta2.json")
DEFAULT_OSRC_MODAL_JSON = Path("tmp/source/v759-osrc-browser/modal-result2.json")

EXPECTED_MODEL = "SM-A908N"
EXPECTED_VERSION = "A908NKSU5EWA3"
EXPECTED_FILENAME = "SM-A908N_KOR_12_Opensource.zip"
EXPECTED_UPLOAD_ID = "13272"
EXPECTED_ANNOUNCEMENT_ATTACH_ID = "39494"
KERNEL_SOURCE_INPUT = workspace_private_input_path("kernel_source", legacy_fallback=False)

ARCHIVE_CANDIDATES = (
    KERNEL_SOURCE_INPUT / EXPECTED_FILENAME,
    KERNEL_SOURCE_INPUT / "source" / EXPECTED_FILENAME,
    KERNEL_SOURCE_INPUT / "downloads" / EXPECTED_FILENAME,
    Path(EXPECTED_FILENAME),
    Path("kernel_build") / EXPECTED_FILENAME,
    Path("kernel_build/source") / EXPECTED_FILENAME,
    Path("kernel_build/downloads") / EXPECTED_FILENAME,
    Path("../") / EXPECTED_FILENAME,
    Path.home() / "Downloads" / EXPECTED_FILENAME,
)

SOURCE_ROOT_CANDIDATES = (
    KERNEL_SOURCE_INPUT / "source" / "SM-A908N_KOR_12_Opensource",
    KERNEL_SOURCE_INPUT / "SM-A908N_KOR_12_Opensource",
    KERNEL_SOURCE_INPUT / "source",
    Path("SM-A908N_KOR_12_Opensource"),
    Path("kernel_build/SM-A908N_KOR_12_Opensource"),
    Path("kernel_build/source/SM-A908N_KOR_12_Opensource"),
    Path("kernel_build/source"),
)

TARGET_SOURCE_SUFFIXES = (
    "drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_main.c",
    "drivers/staging/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c",
    "drivers/net/wireless/cnss2/main.c",
    "drivers/net/wireless/cnss2/qmi.c",
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
    parser.add_argument("--v758-manifest", type=Path, default=DEFAULT_V758_MANIFEST)
    parser.add_argument("--osrc-html", type=Path, default=DEFAULT_OSRC_HTML)
    parser.add_argument("--osrc-page-json", type=Path, default=DEFAULT_OSRC_PAGE_JSON)
    parser.add_argument("--osrc-modal-json", type=Path, default=DEFAULT_OSRC_MODAL_JSON)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path) if not path.is_absolute() else path
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def file_info(path: Path) -> dict[str, Any]:
    resolved = repo_path(path) if not path.is_absolute() else path.expanduser()
    exists = resolved.exists()
    info: dict[str, Any] = {
        "path": str(resolved),
        "exists": exists,
        "is_file": False,
        "is_dir": False,
        "size": None,
        "sha256_1m": None,
    }
    if not exists:
        return info
    stat = resolved.stat()
    info["is_file"] = resolved.is_file()
    info["is_dir"] = resolved.is_dir()
    info["size"] = stat.st_size if resolved.is_file() else None
    if resolved.is_file():
        hasher = hashlib.sha256()
        with resolved.open("rb") as handle:
            hasher.update(handle.read(1024 * 1024))
        info["sha256_1m"] = hasher.hexdigest()
    return info


def extract_json_text(data: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("bodyText", "html", "innerHTML", "text", "content", "url", "title"):
        value = data.get(key)
        if isinstance(value, str):
            parts.append(value)
    links = data.get("links")
    if isinstance(links, list):
        for link in links:
            if isinstance(link, dict):
                for key in ("text", "href", "attr"):
                    value = link.get(key)
                    if isinstance(value, str):
                        parts.append(value)
    return "\n".join(parts)


def parse_osrc(args: argparse.Namespace) -> dict[str, Any]:
    html_text = html.unescape(read_text(args.osrc_html))
    page_json = load_json(args.osrc_page_json)
    modal_json = load_json(args.osrc_modal_json)
    page_text = html.unescape(extract_json_text(page_json))
    modal_text = html.unescape(extract_json_text(modal_json))
    combined = "\n".join([html_text, page_text])
    upload_ids = sorted(set(re.findall(r"showSrcDownPop\('(\d+)'\)", combined)))
    ann_matches = re.findall(r"showAnnDownPop\('(\d+)'\s*,\s*'(\d+)'\)", combined)
    modal_upload_ids = sorted(set(re.findall(r'name=["\']uploadId["\'][^>]*value=["\'](\d+)["\']', modal_text)))
    result_count_match = re.search(r"(\d+)\s+of results found", combined)
    result_count = int(result_count_match.group(1)) if result_count_match else None
    hcaptcha_gate = "hcaptcha" in modal_text.lower() or "are you a real person" in modal_text.lower()
    model_present = EXPECTED_MODEL in combined
    version_present = EXPECTED_VERSION in combined
    filename_present = EXPECTED_FILENAME in combined
    upload_id_present = EXPECTED_UPLOAD_ID in upload_ids or EXPECTED_UPLOAD_ID in modal_upload_ids
    announcement_attach_present = any(
        upload_id == EXPECTED_UPLOAD_ID and attach_id == EXPECTED_ANNOUNCEMENT_ATTACH_ID
        for upload_id, attach_id in ann_matches
    )
    return {
        "search_url": f"https://opensource.samsung.com/uploadSearch?searchValue={EXPECTED_VERSION}",
        "model": EXPECTED_MODEL if model_present else "",
        "version": EXPECTED_VERSION if version_present else "",
        "filename": EXPECTED_FILENAME if filename_present else "",
        "result_count": result_count,
        "source_upload_ids": upload_ids,
        "modal_upload_ids": modal_upload_ids,
        "announcement_pairs": [{"upload_id": upload_id, "attach_id": attach_id} for upload_id, attach_id in ann_matches],
        "expected_upload_id": EXPECTED_UPLOAD_ID,
        "expected_announcement_attach_id": EXPECTED_ANNOUNCEMENT_ATTACH_ID,
        "hcaptcha_gate": hcaptcha_gate,
        "exact_source_identified": all((
            result_count == 1,
            model_present,
            version_present,
            filename_present,
            upload_id_present,
            announcement_attach_present,
        )),
        "evidence_files": [
            str(repo_path(args.osrc_html)),
            str(repo_path(args.osrc_page_json)),
            str(repo_path(args.osrc_modal_json)),
        ],
    }


def inspect_zip(path: Path) -> dict[str, Any]:
    resolved = repo_path(path) if not path.is_absolute() else path.expanduser()
    info = file_info(path)
    result: dict[str, Any] = {
        "file": info,
        "is_zip": False,
        "readable": False,
        "target_hits": {},
        "error": "",
    }
    if not info["exists"] or not info["is_file"]:
        return result
    try:
        with zipfile.ZipFile(resolved) as archive:
            result["is_zip"] = True
            result["readable"] = True
            hits = {suffix: [] for suffix in TARGET_SOURCE_SUFFIXES}
            for member in archive.infolist():
                normalized = member.filename.strip("/")
                for suffix in TARGET_SOURCE_SUFFIXES:
                    if normalized.endswith(suffix):
                        hits[suffix].append(normalized)
            result["target_hits"] = hits
    except (OSError, zipfile.BadZipFile) as exc:
        result["error"] = str(exc)
    return result


def inspect_source_root(path: Path) -> dict[str, Any]:
    resolved = repo_path(path) if not path.is_absolute() else path.expanduser()
    info = file_info(path)
    hits: dict[str, list[str]] = {suffix: [] for suffix in TARGET_SOURCE_SUFFIXES}
    if info["exists"] and info["is_dir"]:
        for suffix in TARGET_SOURCE_SUFFIXES:
            exact = resolved / suffix
            if exact.exists():
                hits[suffix].append(str(exact))
    return {"root": info, "target_hits": hits}


def target_hit_count(items: list[dict[str, Any]], key: str) -> int:
    count = 0
    for item in items:
        hits = item.get("target_hits")
        if isinstance(hits, dict):
            count += sum(1 for values in hits.values() if isinstance(values, list) and values)
    return count


def build_analysis(args: argparse.Namespace) -> dict[str, Any]:
    v758 = load_json(args.v758_manifest)
    osrc = parse_osrc(args)
    archives = [inspect_zip(path) for path in ARCHIVE_CANDIDATES]
    roots = [inspect_source_root(path) for path in SOURCE_ROOT_CANDIDATES]
    local_archive_present = any(item["file"]["exists"] for item in archives)
    local_archive_readable = any(item["readable"] for item in archives)
    archive_target_hits = target_hit_count(archives, "target_hits")
    root_target_hits = target_hit_count(roots, "target_hits")
    source_targets_present = archive_target_hits > 0 or root_target_hits > 0
    return {
        "v758": {
            "manifest": str(repo_path(args.v758_manifest)),
            "decision": v758.get("decision", ""),
            "pass": bool(v758.get("pass")),
            "device_mutations": bool(v758.get("device_mutations")),
            "boot_image_write_executed": bool(v758.get("boot_image_write_executed")),
        },
        "osrc": osrc,
        "local_stage": {
            "archive_candidates": archives,
            "source_root_candidates": roots,
            "local_archive_present": local_archive_present,
            "local_archive_readable": local_archive_readable,
            "archive_target_hits": archive_target_hits,
            "root_target_hits": root_target_hits,
            "source_targets_present": source_targets_present,
        },
        "route": {
            "official_source_identified": osrc["exact_source_identified"],
            "manual_download_required": osrc["exact_source_identified"] and osrc["hcaptcha_gate"] and not local_archive_present,
            "local_source_staged": local_archive_present or root_target_hits > 0,
            "target_sources_verified": source_targets_present,
            "can_plan_kernel_patch": source_targets_present,
            "next_cycle": "v760-source-content-verification" if source_targets_present else "v760-manual-source-download-and-stage",
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
    v758 = analysis["v758"]
    osrc = analysis["osrc"]
    local = analysis["local_stage"]
    route = analysis["route"]
    checks: list[Check] = []
    add_check(
        checks,
        "v758-input",
        "pass" if v758["decision"] == "v758-source-acquisition-required-before-kernel-instrumentation" and v758["pass"] else "blocked",
        "blocker",
        f"decision={v758['decision']} pass={v758['pass']} mutations={v758['device_mutations']} boot_write={v758['boot_image_write_executed']}",
        [v758["manifest"]],
        "complete V758 before V759",
    )
    add_check(
        checks,
        "official-osrc-source",
        "pass" if osrc["exact_source_identified"] else "blocked",
        "blocker",
        f"model={osrc['model']} version={osrc['version']} filename={osrc['filename']} upload_ids={osrc['source_upload_ids']} result_count={osrc['result_count']}",
        osrc["evidence_files"],
        "identify exact Samsung OSRC source package",
    )
    add_check(
        checks,
        "download-gate",
        "review" if osrc["hcaptcha_gate"] else "pass",
        "finding",
        f"hcaptcha_gate={osrc['hcaptcha_gate']} modal_upload_ids={osrc['modal_upload_ids']}",
        [osrc["evidence_files"][-1]],
        "manual browser download is required when hCaptcha is present",
    )
    add_check(
        checks,
        "local-source-stage",
        "pass" if local["source_targets_present"] else "review",
        "finding",
        f"archive_present={local['local_archive_present']} archive_readable={local['local_archive_readable']} archive_hits={local['archive_target_hits']} root_hits={local['root_target_hits']}",
        [],
        "stage official archive or extracted source under ignored kernel_build paths",
    )
    add_check(
        checks,
        "kernel-patch-readiness",
        "pass" if route["can_plan_kernel_patch"] else "blocked",
        "blocker",
        f"target_sources_verified={route['target_sources_verified']} can_plan_kernel_patch={route['can_plan_kernel_patch']}",
        [],
        "verify source contents before any kernel instrumentation patch",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v759-source-acquisition-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only OSRC source acquisition classifier",
        )
    if not analysis:
        return (
            "v759-source-acquisition-missing-analysis",
            False,
            "analysis missing",
            "rerun V759",
        )
    route = analysis["route"]
    blockers = blocking(checks)
    if route["can_plan_kernel_patch"]:
        return (
            "v759-source-staged-targets-present",
            True,
            "official source is staged and target source files are visible",
            "V760 should verify source version/build prerequisites before patching",
        )
    if route["official_source_identified"] and route["manual_download_required"]:
        return (
            "v759-official-source-identified-manual-download-gated",
            True,
            "official exact source package is identified, but download is hCaptcha/manual-gated and not staged locally",
            "download the official source package manually and stage it under kernel_build before V760",
        )
    if blockers:
        return (
            "v759-source-acquisition-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear source acquisition blockers before kernel instrumentation",
        )
    return (
        "v759-source-acquisition-review",
        True,
        "source route classified but needs manual review",
        "inspect manifest before V760",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    analysis = manifest.get("analysis") or {}
    osrc = (analysis.get("osrc") or {}) if isinstance(analysis, dict) else {}
    route = (analysis.get("route") or {}) if isinstance(analysis, dict) else {}
    return "\n".join([
        "# V759 Source Acquisition Gate",
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
        "## OSRC",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in osrc.items() if key != "evidence_files"]) if osrc else "- plan only",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]) if checks else "- plan only",
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
        "cycle": "v759",
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
    latest = repo_path("tmp/wifi/latest-v759-source-acquisition.txt")
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
