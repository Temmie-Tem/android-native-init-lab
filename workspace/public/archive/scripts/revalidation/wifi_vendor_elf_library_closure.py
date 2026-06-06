#!/usr/bin/env python3
"""Close CNSS daemon ELF/library evidence gaps without executing services."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import stat
import subprocess
from collections import deque
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_V210_MANIFEST = Path("tmp/wifi/v210-vendor-asset-classifier/manifest.json")
DEFAULT_V216_MANIFEST = Path("tmp/wifi/v216-service-replay-model/manifest.json")
DEFAULT_V218_MANIFEST = Path("tmp/wifi/v218-cnss-daemon-dryrun/manifest.json")
DEFAULT_V218_NATIVE_MANIFEST = Path("tmp/wifi/v218-cnss-daemon-dryrun-native/manifest.json")
DEFAULT_V219_MANIFEST = Path("tmp/wifi/v219-native-android-env-shim/manifest.json")
DEFAULT_V220_MANIFEST = Path("tmp/wifi/v220-bringup-gate-v2/manifest.json")

TARGET_SERVICES = ("cnss-daemon", "cnss_diag")
MAX_RECURSIVE_ELF_OBJECTS = 200

ANDROID_CORE_LIBS = {
    "ld-android.so",
    "libbase.so",
    "libbinder.so",
    "libc++.so",
    "libc.so",
    "libcrypto.so",
    "libdl.so",
    "libhardware.so",
    "libhidlbase.so",
    "libhidltransport.so",
    "liblog.so",
    "libm.so",
    "libprotobuf-cpp-lite.so",
    "libselinux.so",
    "libssl.so",
    "libstdc++.so",
    "libutils.so",
    "libz.so",
}

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
    return REPO_ROOT / "tmp" / "wifi" / "v221-host-vendor-elf-library-evidence"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--vendor-root", type=Path, default=None)
    parser.add_argument("--system-root", type=Path, default=None)
    parser.add_argument("--v210-manifest", type=Path, default=DEFAULT_V210_MANIFEST)
    parser.add_argument("--v216-manifest", type=Path, default=DEFAULT_V216_MANIFEST)
    parser.add_argument("--v218-manifest", type=Path, default=DEFAULT_V218_MANIFEST)
    parser.add_argument("--v218-native-manifest", type=Path, default=DEFAULT_V218_NATIVE_MANIFEST)
    parser.add_argument("--v219-manifest", type=Path, default=DEFAULT_V219_MANIFEST)
    parser.add_argument("--v220-manifest", type=Path, default=DEFAULT_V220_MANIFEST)
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


def service_from_v218(v218: dict[str, Any], name: str) -> dict[str, Any]:
    for daemon in v218.get("daemons", []):
        if isinstance(daemon, dict) and daemon.get("name") == name:
            return daemon
    return {"name": name}


def service_from_v216(v216: dict[str, Any], name: str) -> dict[str, Any]:
    for service in v216.get("graph", {}).get("services", []):
        if isinstance(service, dict) and service.get("name") == name:
            return service
    return {"name": name}


def visible_paths(v210: dict[str, Any]) -> set[str]:
    classification = v210.get("classification")
    if not isinstance(classification, dict):
        return set()
    values = classification.get("visible_paths")
    if not isinstance(values, list):
        return set()
    return {str(value).lstrip("/") for value in values}


def vendor_relative(executable: str) -> str:
    if executable.startswith("/system/vendor/"):
        return executable.removeprefix("/system/vendor/")
    if executable.startswith("/vendor/"):
        return executable.removeprefix("/vendor/")
    return executable.lstrip("/")


def normalize_vendor_root(path: Path | None) -> tuple[Path | None, str]:
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


def normalize_system_root(path: Path | None) -> tuple[Path | None, str]:
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_metadata(path: Path) -> dict[str, Any]:
    info = path.stat()
    return {
        "path": str(path),
        "mode": oct(info.st_mode & 0o7777),
        "size": info.st_size,
        "sha256": sha256_file(path),
    }


def run_readelf(path: Path) -> tuple[str, str]:
    try:
        result = subprocess.run(
            ["readelf", "-W", "-h", "-l", "-d", str(path)],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=15,
        )
    except FileNotFoundError:
        return "readelf-unavailable", ""
    except subprocess.TimeoutExpired:
        return "readelf-timeout", ""
    if result.returncode != 0:
        return f"readelf-rc-{result.returncode}", result.stdout
    return "ok", result.stdout


def parse_readelf(text: str) -> dict[str, Any]:
    needed: list[str] = []
    rpath: list[str] = []
    runpath: list[str] = []
    interpreter = ""
    machine = ""
    elf_class = ""
    elf_type = ""
    for line in text.splitlines():
        class_match = re.search(r"^\s*Class:\s*(.+)$", line)
        if class_match:
            elf_class = class_match.group(1).strip()
        machine_match = re.search(r"^\s*Machine:\s*(.+)$", line)
        if machine_match:
            machine = machine_match.group(1).strip()
        type_match = re.search(r"^\s*Type:\s*(.+)$", line)
        if type_match:
            elf_type = type_match.group(1).strip()
        interp_match = re.search(r"Requesting program interpreter:\s*([^\]]+)", line)
        if interp_match:
            interpreter = interp_match.group(1).strip()
        needed_match = re.search(r"Shared library:\s*\[([^\]]+)\]", line)
        if needed_match:
            needed.append(needed_match.group(1).strip())
        rpath_match = re.search(r"Library rpath:\s*\[([^\]]+)\]", line)
        if rpath_match:
            rpath.extend(split_search_path(rpath_match.group(1)))
        runpath_match = re.search(r"Library runpath:\s*\[([^\]]+)\]", line)
        if runpath_match:
            runpath.extend(split_search_path(runpath_match.group(1)))
    return {
        "class": elf_class,
        "machine": machine,
        "type": elf_type,
        "interpreter": interpreter,
        "needed": sorted(set(needed)),
        "rpath": unique(rpath),
        "runpath": unique(runpath),
    }


def split_search_path(value: str) -> list[str]:
    return [part for part in value.split(":") if part]


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            result.append(value)
            seen.add(value)
    return result


def map_android_path(vendor_root: Path, android_path: str, origin_dir: Path) -> list[Path]:
    expanded = android_path.replace("${ORIGIN}", "$ORIGIN")
    expanded = expanded.replace("$ORIGIN", str(origin_dir))
    candidates: list[Path] = []
    lib_variants = ["lib64", "lib"]
    if "$LIB" in expanded or "${LIB}" in expanded:
        for lib_dir in lib_variants:
            candidates.extend(map_android_path(vendor_root, expanded.replace("${LIB}", lib_dir).replace("$LIB", lib_dir), origin_dir))
        return candidates
    if expanded.startswith("/system/vendor/"):
        candidates.append(vendor_root / expanded.removeprefix("/system/vendor/"))
    elif expanded.startswith("/vendor/"):
        candidates.append(vendor_root / expanded.removeprefix("/vendor/"))
    elif expanded.startswith("/"):
        candidates.append(Path(expanded))
    else:
        candidates.append(Path(expanded))
    return candidates


def common_library_dirs(vendor_root: Path) -> list[Path]:
    return [
        vendor_root / "lib64",
        vendor_root / "lib",
        vendor_root / "lib64" / "hw",
        vendor_root / "lib" / "hw",
        vendor_root / "lib64" / "vndk-sp",
        vendor_root / "lib" / "vndk-sp",
        vendor_root / "lib64" / "egl",
        vendor_root / "lib" / "egl",
    ]


def common_system_library_dirs(system_root: Path | None) -> list[Path]:
    if system_root is None:
        return []
    return [
        system_root / "system" / "lib64",
        system_root / "system" / "lib",
        system_root / "system" / "lib64" / "vndk-sp",
        system_root / "system" / "lib" / "vndk-sp",
        system_root / "system" / "lib64" / "hw",
        system_root / "system" / "lib" / "hw",
        system_root / "lib64",
        system_root / "lib",
    ]


def resolve_existing_path(path: Path, vendor_root: Path) -> tuple[Path | None, str]:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None, "missing"
    if stat.S_ISLNK(info.st_mode):
        target = os.readlink(path)
        if target.startswith("/vendor/"):
            mapped = vendor_root / target.removeprefix("/vendor/")
        elif target.startswith("/system/vendor/"):
            mapped = vendor_root / target.removeprefix("/system/vendor/")
        elif target.startswith("/"):
            return None, f"external-symlink:{target}"
        else:
            mapped = path.parent / target
        try:
            resolved = mapped.resolve()
            resolved.relative_to(vendor_root)
        except (FileNotFoundError, ValueError):
            return None, f"unsafe-symlink:{target}"
        if not resolved.exists():
            return None, f"broken-symlink:{target}"
        return resolved, "symlink"
    if not stat.S_ISREG(info.st_mode):
        return None, "not-regular"
    return path, "regular"


def resolve_existing_system_path(path: Path, system_root: Path) -> tuple[Path | None, str]:
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None, "missing"
    if stat.S_ISLNK(info.st_mode):
        target = os.readlink(path)
        if target.startswith("/system/"):
            mapped = system_root / target.removeprefix("/")
        elif target.startswith("/"):
            return None, f"external-symlink:{target}"
        else:
            mapped = path.parent / target
        try:
            resolved = mapped.resolve()
            resolved.relative_to(system_root)
        except (FileNotFoundError, ValueError):
            return None, f"unsafe-symlink:{target}"
        if not resolved.exists():
            return None, f"broken-symlink:{target}"
        return resolved, "symlink"
    if not stat.S_ISREG(info.st_mode):
        return None, "not-regular"
    return path, "regular"


def resolve_library(vendor_root: Path,
                    system_root: Path | None,
                    origin_dir: Path,
                    needed: str,
                    rpath: list[str],
                    runpath: list[str]) -> dict[str, Any]:
    searched: list[str] = []
    directories: list[Path] = []
    for path in rpath + runpath:
        directories.extend(map_android_path(vendor_root, path, origin_dir))
    directories.extend(common_library_dirs(vendor_root))
    for directory in unique([str(path) for path in directories]):
        candidate = Path(directory) / needed
        searched.append(str(candidate))
        resolved, source = resolve_existing_path(candidate, vendor_root)
        if resolved is not None:
            return {
                "name": needed,
                "resolved": True,
                "path": str(resolved),
                "root": str(vendor_root),
                "source": source,
                "searched": searched,
                "classification": "vendor-resolved",
            }
    if system_root is not None:
        for directory in unique([str(path) for path in common_system_library_dirs(system_root)]):
            candidate = Path(directory) / needed
            searched.append(str(candidate))
            resolved, source = resolve_existing_system_path(candidate, system_root)
            if resolved is not None:
                return {
                    "name": needed,
                    "resolved": True,
                    "path": str(resolved),
                    "root": str(system_root),
                    "source": source,
                    "searched": searched,
                    "classification": "android-system-resolved",
                }
    classification = "android-core-runtime-required" if needed in ANDROID_CORE_LIBS else "unresolved"
    return {
        "name": needed,
        "resolved": False,
        "path": "",
        "source": "missing",
        "searched": searched,
        "classification": classification,
    }


def inspect_elf(path: Path, root: Path, root_kind: str) -> dict[str, Any]:
    if root_kind == "system":
        resolved, source = resolve_existing_system_path(path, root)
    else:
        resolved, source = resolve_existing_path(path, root)
    if resolved is None:
        return {
            "path": str(path),
            "exists": False,
            "source": source,
            "readelf_status": "missing",
            "metadata": {},
            "elf": {},
        }
    readelf_status, readelf_text = run_readelf(resolved)
    parsed = parse_readelf(readelf_text) if readelf_status == "ok" else {}
    return {
        "path": str(path),
        "resolved_path": str(resolved),
        "exists": True,
        "source": source,
        "readelf_status": readelf_status,
        "metadata": file_metadata(resolved),
        "elf": parsed,
    }


def dependency_graph(vendor_root: Path, system_root: Path | None, binary_path: Path) -> dict[str, Any]:
    objects: list[dict[str, Any]] = []
    resolutions: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    queue: deque[tuple[Path, Path, str]] = deque([(binary_path, vendor_root, "vendor")])
    visited: set[str] = set()
    while queue and len(visited) < MAX_RECURSIVE_ELF_OBJECTS:
        current, current_root, current_root_kind = queue.popleft()
        inspected = inspect_elf(current, current_root, current_root_kind)
        objects.append(inspected)
        if not inspected.get("exists") or inspected.get("readelf_status") != "ok":
            continue
        resolved_path = str(inspected["resolved_path"])
        if resolved_path in visited:
            continue
        visited.add(resolved_path)
        elf = inspected.get("elf", {})
        origin_dir = Path(resolved_path).parent
        for needed in elf.get("needed", []):
            resolution = resolve_library(
                vendor_root,
                system_root,
                origin_dir,
                needed,
                list(elf.get("rpath", [])),
                list(elf.get("runpath", [])),
            )
            resolution["required_by"] = resolved_path
            resolutions.append(resolution)
            if resolution["resolved"]:
                path = Path(str(resolution["path"]))
                if str(path) not in visited:
                    root_kind = "system" if resolution.get("classification") == "android-system-resolved" else "vendor"
                    queue.append((path, Path(str(resolution.get("root") or vendor_root)), root_kind))
            elif resolution["classification"] != "android-core-runtime-required":
                unresolved.append(resolution)
    truncated = bool(queue)
    return {
        "objects": objects,
        "library_resolutions": resolutions,
        "unresolved_libraries": unresolved,
        "truncated": truncated,
        "object_count": len(objects),
    }


def build_required_checklist(v218: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for service in TARGET_SERVICES:
        daemon = service_from_v218(v218, service)
        executable = str(daemon.get("executable") or "")
        rel = str(daemon.get("vendor_relative_path") or vendor_relative(executable))
        rows.append({
            "service": service,
            "executable": executable,
            "vendor_relative_path": rel,
            "expected_host_path": f"<vendor-root>/{rel}",
            "args": daemon.get("args", []),
            "user": daemon.get("user", ""),
            "groups": daemon.get("groups", []),
            "capabilities": daemon.get("capabilities", []),
        })
    return rows


def inspect_daemon(vendor_root: Path | None,
                   system_root: Path | None,
                   v216: dict[str, Any],
                   v218: dict[str, Any],
                   service: str) -> dict[str, Any]:
    v218_daemon = service_from_v218(v218, service)
    v216_service = service_from_v216(v216, service)
    executable = str(v218_daemon.get("executable") or v216_service.get("executable") or "")
    rel = str(v218_daemon.get("vendor_relative_path") or vendor_relative(executable))
    base = {
        "name": service,
        "executable": executable,
        "vendor_relative_path": rel,
        "args": v218_daemon.get("args", v216_service.get("args", [])),
        "user": v218_daemon.get("user", v216_service.get("user", "")),
        "groups": v218_daemon.get("groups", v216_service.get("groups", [])),
        "capabilities": v218_daemon.get("capabilities", v216_service.get("capabilities", [])),
        "classes": v218_daemon.get("classes", v216_service.get("classes", [])),
        "flags": v218_daemon.get("flags", v216_service.get("flags", [])),
        "v218_blockers": v218_daemon.get("blockers", []),
    }
    if vendor_root is None:
        base.update({
            "inspection": "vendor-root-required",
            "binary": {},
            "dependency_graph": {},
            "unresolved_libraries": [],
        })
        return base
    binary_path = vendor_root / rel
    graph = dependency_graph(vendor_root, system_root, binary_path)
    unresolved = graph.get("unresolved_libraries", [])
    first_object = graph["objects"][0] if graph.get("objects") else {}
    if first_object.get("readelf_status") == "ok":
        inspection = "ok" if not unresolved else "unresolved-libraries"
    else:
        inspection = str(first_object.get("readelf_status", "missing"))
    base.update({
        "inspection": inspection,
        "binary": first_object,
        "dependency_graph": graph,
        "unresolved_libraries": unresolved,
    })
    return base


def decide(v210: dict[str, Any],
           v216: dict[str, Any],
           v218: dict[str, Any],
           v220: dict[str, Any],
           vendor_root_status: str,
           system_root_status: str,
           daemons: list[dict[str, Any]]) -> tuple[str, str, bool]:
    if v210.get("decision") not in {"asset-map-ready", "firmware-path-policy-needed"}:
        return "manual-review-required", "v210 vendor asset evidence is not usable", False
    if v216.get("decision") != "replay-model-ready":
        return "manual-review-required", "v216 service replay model is not ready", False
    if v218.get("decision") not in {"daemon-dryrun-ready", "daemon-dryrun-partial"}:
        return "manual-review-required", "v218 daemon dry-run evidence is not usable", False
    if v220.get("decision") != "no-go":
        return "manual-review-required", "v220 decision is not the expected no-go prerequisite closure state", False
    if vendor_root_status == "not-provided":
        return "vendor-root-required", "host-visible vendor root is required for ELF/library inspection", True
    if vendor_root_status != "ok":
        return "daemon-native-blocked", f"vendor root is not usable: {vendor_root_status}", False
    if system_root_status not in {"not-provided", "ok"}:
        return "daemon-native-blocked", f"system root is not usable: {system_root_status}", False
    missing_or_bad = [
        daemon["name"]
        for daemon in daemons
        if daemon.get("inspection") not in {"ok"}
    ]
    if missing_or_bad:
        return "daemon-native-blocked", f"ELF/library inspection has unresolved blockers: {', '.join(missing_or_bad)}", False
    return "elf-evidence-ready", "CNSS daemon ELF and direct library evidence captured", True


def build_summary(manifest: dict[str, Any]) -> str:
    rows = []
    for daemon in manifest["daemons"]:
        if daemon["inspection"] == "vendor-root-required":
            needed = "n/a"
            unresolved = "n/a"
        else:
            binary = daemon.get("binary", {})
            needed = ", ".join(binary.get("elf", {}).get("needed", [])) or "none"
            unresolved = ", ".join(item["name"] for item in daemon.get("unresolved_libraries", [])) or "none"
        rows.append([
            daemon["name"],
            daemon["vendor_relative_path"],
            daemon["inspection"],
            needed,
            unresolved,
        ])
    checklist_rows = [
        [item["service"], item["expected_host_path"], ", ".join(item["capabilities"]) or "none"]
        for item in manifest["required_vendor_paths"]
    ]
    lines = [
        "# v221 Host Vendor ELF / Library Evidence Closure",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        f"- vendor_root_status: `{manifest['vendor_root_status']}`",
        f"- system_root_status: `{manifest['system_root_status']}`",
        "",
        "## Daemon ELF Summary",
        "",
        markdown_table(["name", "vendor path", "inspection", "DT_NEEDED", "unresolved"], rows),
        "",
        "## Required Vendor Paths",
        "",
        markdown_table(["service", "expected host path", "capabilities"], checklist_rows),
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
        "- This is not an execution plan.",
        "- `vendor-root-required` is a successful planning result when no host vendor root is available.",
        "- `cnss-daemon` and `cnss_diag` remain blocked.",
        "- Active Wi-Fi scan/connect remains blocked by v220.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    validate_no_active_commands()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)

    v210 = load_json(args.v210_manifest)
    v216 = load_json(args.v216_manifest)
    v218 = load_json(args.v218_manifest)
    v218_native = load_json(args.v218_native_manifest)
    v219 = load_json(args.v219_manifest)
    v220 = load_json(args.v220_manifest)

    vendor_root, vendor_root_status = normalize_vendor_root(args.vendor_root)
    system_root, system_root_status = normalize_system_root(args.system_root)
    daemons = [inspect_daemon(vendor_root, system_root, v216, v218, service) for service in TARGET_SERVICES]
    required_paths = build_required_checklist(v218)
    decision, reason, pass_ok = decide(v210, v216, v218, v220, vendor_root_status, system_root_status, daemons)

    dependencies = {
        "daemons": daemons,
        "required_vendor_paths": required_paths,
        "system_root": str(system_root) if system_root else None,
        "system_root_status": system_root_status,
        "source_decisions": {
            "v210": v210.get("decision"),
            "v216": v216.get("decision"),
            "v218": v218.get("decision"),
            "v218_native": v218_native.get("decision"),
            "v219": v219.get("decision"),
            "v220": v220.get("decision"),
        },
    }
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "mode": "host-vendor-elf-library-evidence",
        "vendor_root": str(vendor_root) if vendor_root else None,
        "vendor_root_status": vendor_root_status,
        "system_root": str(system_root) if system_root else None,
        "system_root_status": system_root_status,
        "inputs": {
            "v210_manifest": str(repo_path(args.v210_manifest)),
            "v216_manifest": str(repo_path(args.v216_manifest)),
            "v218_manifest": str(repo_path(args.v218_manifest)),
            "v218_native_manifest": str(repo_path(args.v218_native_manifest)),
            "v219_manifest": str(repo_path(args.v219_manifest)),
            "v220_manifest": str(repo_path(args.v220_manifest)),
            "system_root": str(repo_path(args.system_root)) if args.system_root else None,
        },
        "visible_vendor_paths_count": len(visible_paths(v210)),
        "required_vendor_paths": required_paths,
        "daemons": daemons,
        "dependencies": dependencies,
        "guardrails": [
            "no live device commands",
            "no daemon execution",
            "no Android service start",
            "no ICNSS sysfs/debugfs writes",
            "no firmware path mutation",
            "no rfkill write",
            "no link-up",
            "no scan/connect",
            "no credential collection",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_json("elf-dependencies.json", dependencies)
    store.write_text("summary.md", build_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
