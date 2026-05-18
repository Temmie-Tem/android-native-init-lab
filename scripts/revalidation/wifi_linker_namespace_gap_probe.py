#!/usr/bin/env python3
"""Classify the post-devnull cnss-daemon linker namespace gap.

This tool does not start cnss-daemon.  It combines:

* v239 real-linkerconfig linker-list evidence
* a minimal-vendor linkerconfig smoke run
* the captured Android linkerconfig
* read-only live stat probes for VNDK/system/vendor library paths

The goal is to explain why ``linker64 --list /vendor/bin/cnss-daemon`` cannot
resolve ``libcutils.so`` under the real Android namespace while the same target
resolves under the intentionally permissive minimal-vendor config.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v240-linker-namespace-gap")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.59 (v159)"
DEFAULT_REAL_MANIFEST = Path("tmp/wifi/v239-devnull-linker-capture-live/manifest.json")
DEFAULT_MINIMAL_MANIFEST = Path("tmp/wifi/v240-minimal-vendor-cnss-smoke/manifest.json")
DEFAULT_LINKERCONFIG = Path("tmp/wifi/v233-android-linkerconfig-source-live/files/linkerconfig__ld.config.txt")
DEFAULT_VENDOR_ROOT = Path("tmp/wifi/v226-vendor-root-live-export/vendor-source")
DEFAULT_SYSTEM_ROOT = Path("tmp/wifi/v227-android-core-system-library-evidence/system-root/system")
TARGET = "/vendor/bin/cnss-daemon"
MISSING_RE = re.compile(r'library "([^"]+)" not found')


LIVE_PATHS = [
    "/mnt/system/system/apex/com.android.vndk.v30/lib64/libcutils.so",
    "/mnt/system/system/apex/com.android.vndk.v30/lib64",
    "/mnt/system/system/apex/com.android.vndk.v30",
    "/mnt/system/system/apex/com.android.vndk.current/lib64/libcutils.so",
    "/mnt/system/system/apex/com.android.vndk.current/lib64",
    "/mnt/system/system/apex/com.android.vndk.current",
    "/mnt/system/system/lib64/libcutils.so",
    "/mnt/system/vendor/lib64/libcutils.so",
    "/vendor/lib64/libcutils.so",
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._+-" else "-" for ch in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def split_list(value: str | None) -> list[str]:
    if not value:
        return []
    items: list[str] = []
    for part in re.split(r"[:,]", value):
        item = part.strip()
        if item:
            items.append(item)
    return items


def parse_linkerconfig(path: Path) -> dict[str, Any]:
    sections: dict[str, dict[str, str]] = {}
    dirs: dict[str, list[str]] = {}
    current: str | None = None

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1]
            sections.setdefault(current, {})
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        append = key.endswith("+")
        if append:
            key = key[:-1].strip()
        if key.startswith("dir."):
            label = key.split(".", 1)[1]
            dirs.setdefault(label, []).append(value)
            continue
        if current is None:
            continue
        section = sections.setdefault(current, {})
        if append and key in section:
            section[key] = f"{section[key]}:{value}"
        else:
            section[key] = value
    return {"sections": sections, "dirs": dirs}


def classify_section_for_target(config: dict[str, Any], target: str) -> dict[str, Any]:
    matches: list[dict[str, str]] = []
    for label, prefixes in config["dirs"].items():
        for prefix in prefixes:
            if target.startswith(prefix):
                matches.append({"section": label, "prefix": prefix})
    if not matches:
        return {"section": None, "matches": []}
    matches.sort(key=lambda item: len(item["prefix"]), reverse=True)
    return {"section": matches[0]["section"], "matches": matches}


def get_section(config: dict[str, Any], section: str) -> dict[str, str]:
    return dict(config["sections"].get(section, {}))


def expand_lib_path(path: str) -> str:
    return path.replace("${LIB}", "lib64")


def section_namespace_values(section: dict[str, str], namespace: str, suffix: str) -> list[str]:
    return [expand_lib_path(item) for item in split_list(section.get(f"namespace.{namespace}.{suffix}"))]


def link_shared_libs(section: dict[str, str], from_namespace: str, to_namespace: str) -> list[str]:
    return split_list(section.get(f"namespace.{from_namespace}.link.{to_namespace}.shared_libs"))


def extract_missing_libs_from_text(text: str) -> list[str]:
    libs: list[str] = []
    for match in MISSING_RE.finditer(text):
        lib = match.group(1)
        if lib not in libs:
            libs.append(lib)
    return libs


def matrix_text_for_item(manifest_path: Path, item: dict[str, Any]) -> str:
    rel = item.get("output_file")
    if not rel:
        return ""
    path = manifest_path.parent / str(rel)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def summarize_manifest_rows(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    rows = []
    missing_libs: list[str] = []
    for item in manifest.get("matrix", []):
        text = matrix_text_for_item(manifest_path, item)
        libs = extract_missing_libs_from_text(text)
        for lib in libs:
            if lib not in missing_libs:
                missing_libs.append(lib)
        rows.append(
            {
                "linker_profile": item.get("linker_profile"),
                "profile": item.get("profile"),
                "decision": item.get("decision"),
                "child_exit_code": item.get("child_exit_code"),
                "child_signal": item.get("child_signal"),
                "fault_addr": item.get("fault_addr"),
                "missing_libs": libs,
                "output_file": item.get("output_file"),
            }
        )
    return {
        "path": str(manifest_path),
        "decision": manifest.get("decision"),
        "reason": manifest.get("reason"),
        "pass": manifest.get("pass"),
        "rows": rows,
        "missing_libs": missing_libs,
    }


def run_readelf_needed(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "ok": False, "error": "missing", "needed": []}
    try:
        result = subprocess.run(
            ["readelf", "-W", "-d", str(path)],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
        )
    except FileNotFoundError:
        return {"path": str(path), "ok": False, "error": "readelf missing", "needed": []}
    except subprocess.TimeoutExpired:
        return {"path": str(path), "ok": False, "error": "readelf timeout", "needed": []}
    needed = re.findall(r"Shared library: \[([^\]]+)\]", result.stdout)
    return {
        "path": str(path),
        "ok": result.returncode == 0,
        "rc": result.returncode,
        "needed": needed,
        "text": result.stdout[:4096],
    }


def local_candidate_path(virtual_path: str, vendor_root: Path, system_root: Path) -> Path | None:
    if virtual_path.startswith("/vendor/"):
        return vendor_root / virtual_path[len("/vendor/") :]
    if virtual_path.startswith("/system/"):
        return system_root / virtual_path[len("/system/") :]
    return None


def local_candidates(lib: str, paths: list[str], vendor_root: Path, system_root: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for virtual_dir in paths:
        virtual = f"{virtual_dir.rstrip('/')}/{lib}"
        local = local_candidate_path(virtual, vendor_root, system_root)
        items.append(
            {
                "virtual": virtual,
                "local": str(local) if local is not None else None,
                "exists": bool(local is not None and local.exists()),
            }
        )
    return items


def capture_device_path(store: EvidenceStore, args: argparse.Namespace, path: str) -> dict[str, Any]:
    name = f"stat-{safe_name(path)}"
    capture = run_capture(args, name, ["stat", path], timeout=args.timeout)
    text = capture.text if capture.text else f"{capture.error}\n"
    output = store.write_text(f"commands/{safe_name(name)}.txt", text)
    stripped = strip_cmdv1_text(text) if text else ""
    return {
        **asdict(capture),
        "file": str(output.relative_to(store.run_dir)),
        "path": path,
        "exists": capture.ok,
        "stripped": stripped[:1024],
    }


def collect_live_stats(store: EvidenceStore, args: argparse.Namespace) -> list[dict[str, Any]]:
    captures = []
    for path in LIVE_PATHS:
        captures.append(capture_device_path(store, args, path))
    apex_capture = run_capture(args, "ls-apex", ["ls", "/mnt/system/system/apex"], timeout=args.timeout)
    captures.append(
        {
            **asdict(apex_capture),
            "path": "/mnt/system/system/apex",
            "exists": None,
            "file": str(store.write_text("commands/ls-apex.txt", apex_capture.text).relative_to(store.run_dir)),
        }
    )
    return captures


def bool_by_path(captures: list[dict[str, Any]], path: str) -> bool:
    for capture in captures:
        if capture.get("path") == path:
            return bool(capture.get("exists"))
    return False


def classify(analysis: dict[str, Any]) -> tuple[str, str, bool]:
    missing = set(analysis["real_manifest"]["missing_libs"])
    minimal_cnss_ok = analysis["minimal_cnss_ok"]
    section = analysis["target_section"].get("section")
    default_links = analysis["vendor_section"].get("default_links", [])
    vndk_shared = set(analysis["vendor_section"].get("link_shared_libs", {}).get("vndk", []))
    live = analysis["live_paths"]
    vndk_v30 = bool_by_path(live, "/mnt/system/system/apex/com.android.vndk.v30/lib64/libcutils.so")
    vndk_current = bool_by_path(live, "/mnt/system/system/apex/com.android.vndk.current/lib64/libcutils.so")

    if (
        "libcutils.so" in missing
        and minimal_cnss_ok
        and section == "vendor"
        and "vndk" in default_links
        and "libcutils.so" in vndk_shared
        and not vndk_v30
        and vndk_current
    ):
        return (
            "android-linker-vndk-apex-version-alias-gap",
            "real vendor namespace links libcutils.so through vndk, but linkerconfig points to com.android.vndk.v30 while the mounted system image exposes com.android.vndk.current",
            True,
        )
    if "libcutils.so" in missing and minimal_cnss_ok:
        return (
            "android-linker-real-namespace-policy-gap",
            "cnss-daemon resolves under permissive minimal-vendor config but fails under real vendor namespace",
            True,
        )
    if "libcutils.so" in missing:
        return (
            "android-linker-libcutils-unresolved",
            "real linkerconfig still reports libcutils.so unresolved; minimal comparison did not prove a namespace-policy gap",
            False,
        )
    return (
        "android-linker-namespace-gap-manual-review",
        "expected libcutils.so unresolved signature was not present in the supplied real manifest",
        False,
    )


def build_analysis(args: argparse.Namespace, store: EvidenceStore, live_paths: list[dict[str, Any]]) -> dict[str, Any]:
    linkerconfig = parse_linkerconfig(args.linkerconfig)
    target_section = classify_section_for_target(linkerconfig, TARGET)
    vendor_section = get_section(linkerconfig, "vendor")
    default_links = split_list(vendor_section.get("namespace.default.links"))
    link_shared: dict[str, list[str]] = {
        name: link_shared_libs(vendor_section, "default", name) for name in default_links
    }
    namespace_paths: dict[str, dict[str, list[str]]] = {}
    for namespace in ["default", *default_links]:
        namespace_paths[namespace] = {
            "search": section_namespace_values(vendor_section, namespace, "search.paths"),
            "permitted": section_namespace_values(vendor_section, namespace, "permitted.paths"),
        }

    real = summarize_manifest_rows(args.real_manifest)
    minimal = summarize_manifest_rows(args.minimal_manifest) if args.minimal_manifest.exists() else {
        "path": str(args.minimal_manifest),
        "missing": True,
        "rows": [],
        "missing_libs": [],
    }
    minimal_cnss_ok = any(
        row.get("profile") == "cnss-daemon"
        and row.get("child_exit_code") == 0
        and row.get("child_signal") == 0
        for row in minimal.get("rows", [])
    )
    missing_libs = real.get("missing_libs", [])
    library_model: dict[str, Any] = {}
    for lib in missing_libs:
        linked_namespaces = [name for name, libs in link_shared.items() if lib in libs]
        library_model[lib] = {
            "linked_namespaces": linked_namespaces,
            "default_candidates": local_candidates(lib, namespace_paths["default"]["search"], args.vendor_root, args.system_root),
            "linked_candidates": {
                name: local_candidates(lib, namespace_paths.get(name, {}).get("search", []), args.vendor_root, args.system_root)
                for name in linked_namespaces
            },
        }

    cnss_readelf = run_readelf_needed(args.vendor_root / "bin/cnss-daemon")
    analysis = {
        "target": TARGET,
        "target_section": target_section,
        "real_manifest": real,
        "minimal_manifest": minimal,
        "minimal_cnss_ok": minimal_cnss_ok,
        "linkerconfig": {
            "path": str(args.linkerconfig),
            "section_count": len(linkerconfig["sections"]),
            "dir_labels": sorted(linkerconfig["dirs"]),
        },
        "vendor_section": {
            "default_search_paths": namespace_paths["default"]["search"],
            "default_permitted_paths": namespace_paths["default"]["permitted"],
            "default_links": default_links,
            "link_shared_libs": link_shared,
            "namespace_paths": namespace_paths,
        },
        "library_model": library_model,
        "cnss_readelf": cnss_readelf,
        "live_paths": live_paths,
        "inputs": {
            "real_manifest": str(args.real_manifest),
            "minimal_manifest": str(args.minimal_manifest),
            "vendor_root": str(args.vendor_root),
            "system_root": str(args.system_root),
        },
        "host_metadata": collect_host_metadata(),
        "out_dir": str(store.run_dir),
    }
    decision, reason, pass_ok = classify(analysis)
    analysis["decision"] = decision
    analysis["reason"] = reason
    analysis["pass"] = pass_ok
    return analysis


def build_summary(manifest: dict[str, Any]) -> str:
    rows = []
    for path in LIVE_PATHS:
        rows.append([path, "yes" if bool_by_path(manifest["live_paths"], path) else "no"])
    lib_rows = []
    for lib, model in manifest["library_model"].items():
        lib_rows.append(
            [
                lib,
                ",".join(model["linked_namespaces"]) or "none",
                " / ".join(item["virtual"] for item in model["default_candidates"] if item["exists"]) or "none",
                " / ".join(
                    item["virtual"]
                    for candidates in model["linked_candidates"].values()
                    for item in candidates
                    if item["exists"]
                )
                or "none",
            ]
        )
    return "\n".join(
        [
            "# v240 Linker Namespace Gap Probe",
            "",
            f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
            f"- decision: `{manifest['decision']}`",
            f"- reason: `{manifest['reason']}`",
            f"- target: `{manifest['target']}`",
            f"- target section: `{manifest['target_section'].get('section')}`",
            f"- minimal cnss ok: `{manifest['minimal_cnss_ok']}`",
            "",
            "## Missing Library Model",
            "",
            markdown_table(["lib", "linked namespaces", "default exists", "linked exists"], lib_rows or [["none", "none", "none", "none"]]),
            "",
            "## Live Path Checks",
            "",
            markdown_table(["path", "exists"], rows),
            "",
            "## Guardrails",
            "",
            "- no `cnss-daemon` entrypoint execution",
            "- no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "- only read-only `stat`/`ls` captures plus existing `linker64 --list` evidence",
            "- minimal-vendor comparison is diagnostic only and not a proposed production namespace",
            "",
        ]
    )


def run(args: argparse.Namespace) -> int:
    store = EvidenceStore(repo_path(args.out_dir))
    if args.subcommand == "probe":
        live_paths = collect_live_stats(store, args)
    else:
        live_paths = []
    manifest = build_analysis(args, store, live_paths)
    manifest["created"] = now_iso()
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    print(f"decision={manifest['decision']} pass={manifest['pass']} out_dir={store.run_dir}")
    print(f"reason={manifest['reason']}")
    return 0 if manifest["pass"] else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / DEFAULT_OUT_DIR)
    parser.add_argument("--real-manifest", type=Path, default=REPO_ROOT / DEFAULT_REAL_MANIFEST)
    parser.add_argument("--minimal-manifest", type=Path, default=REPO_ROOT / DEFAULT_MINIMAL_MANIFEST)
    parser.add_argument("--linkerconfig", type=Path, default=REPO_ROOT / DEFAULT_LINKERCONFIG)
    parser.add_argument("--vendor-root", type=Path, default=REPO_ROOT / DEFAULT_VENDOR_ROOT)
    parser.add_argument("--system-root", type=Path, default=REPO_ROOT / DEFAULT_SYSTEM_ROOT)
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    subparsers.add_parser("analyze", help="analyze existing host evidence only")
    subparsers.add_parser("probe", help="also collect read-only live device path stats")
    args = parser.parse_args()
    args.real_manifest = repo_path(args.real_manifest)
    args.minimal_manifest = repo_path(args.minimal_manifest)
    args.linkerconfig = repo_path(args.linkerconfig)
    args.vendor_root = repo_path(args.vendor_root)
    args.system_root = repo_path(args.system_root)
    for label in ("real_manifest", "linkerconfig", "vendor_root", "system_root"):
        path = getattr(args, label)
        if not path.exists():
            parser.error(f"{label.replace('_', '-')} does not exist: {path}")
    return args


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
