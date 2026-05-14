#!/usr/bin/env python3
"""Inventory Android execution namespace prerequisites for Wi-Fi bring-up.

v230 intentionally does not start Android daemons and does not perform global
bind mounts.  The probe answers whether the native init environment has enough
read-only evidence to later build a *temporary/private* Android exec namespace.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from a90_kernel_tools import (
    REPO_ROOT,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v230-android-exec-namespace-probe")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.59 (v159)"
DEFAULT_V229_OUT_DIR = Path("tmp/wifi/v229-controlled-cnss-start-experiment-preflight-before-v230")
DEFAULT_V221_MANIFEST = Path("tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json")
DEFAULT_V222_MANIFEST = Path("tmp/wifi/v222-vendor-root-evidence-export/manifest.json")
DEFAULT_V226_MANIFEST = Path("tmp/wifi/v226-vendor-root-live-export/manifest.json")
DEFAULT_V227_MANIFEST = Path("tmp/wifi/v227-android-core-system-library-evidence/manifest.json")
DEFAULT_V228_MANIFEST = Path("tmp/wifi/v228-controlled-cnss-start-plan/manifest.json")
DEFAULT_V229_MANIFEST = Path("tmp/wifi/v229-controlled-cnss-start-experiment/manifest.json")

EXPECTED_DECISIONS = {
    "v221": {"elf-evidence-ready"},
    "v222": {"vendor-root-ready"},
    "v226": {"vendor-source-exported"},
    "v227": {"system-root-ready"},
    "v228": {"cnss-start-plan-ready"},
    "v229": {"dry-run-ready", "start-only-runtime-gap"},
}

LIVE_CAPTURE_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("version",),
    ("status",),
    ("bootstatus",),
    ("selftest", "verbose"),
    ("mountsystem", "ro"),
    ("mounts",),
    ("cat", "/proc/mounts"),
    ("cat", "/proc/net/dev"),
    ("cat", "/sys/module/firmware_class/parameters/path"),
    ("cat", "/sys/devices/platform/soc/18800000.qcom,icnss/uevent"),
    ("cat", "/sys/class/block/sda29/dev"),
    ("ls", "/sys/class/net"),
    ("ls", "/sys/class/rfkill"),
    ("ls", "/sys/class/ieee80211"),
    ("ls", "/mnt/system"),
    ("ls", "/mnt/system/system"),
    ("ls", "/mnt/system/system/etc"),
    ("ls", "/mnt/system/system/apex"),
    ("ls", "/mnt/system/linkerconfig"),
    ("ls", "/apex"),
    ("ls", "/vendor"),
    ("ls", "/system"),
    ("ls", "/mnt/vendor"),
    ("stat", "/mnt/system/system/vendor"),
    ("stat", "/mnt/system/vendor"),
    ("stat", "/system/vendor"),
    ("stat", "/vendor"),
    ("stat", "/mnt/vendor/bin/cnss-daemon"),
    ("stat", "/vendor/bin/cnss-daemon"),
    ("stat", "/system/vendor/bin/cnss-daemon"),
    ("stat", "/mnt/system/vendor/bin/cnss-daemon"),
    ("stat", "/mnt/system/system/bin/linker64"),
    ("stat", "/mnt/system/system/bin/toybox"),
    ("stat", "/mnt/system/system/lib64/libc.so"),
    ("stat", "/mnt/system/linkerconfig"),
    ("stat", "/mnt/system/linkerconfig/ld.config.txt"),
    ("stat", "/mnt/system/system/etc/ld.config.txt"),
    ("stat", "/mnt/system/system/apex"),
    ("stat", "/mnt/system/system/apex/com.android.runtime"),
    ("stat", "/apex"),
    ("stat", "/apex/com.android.runtime"),
    ("stat", "/cache/bin/a90_android_execns_probe"),
    ("stat", "/cache/bin/toybox"),
    ("stat", "/sys/devices/platform/soc/18800000.qcom,icnss"),
    ("stat", "/sys/bus/platform/drivers/icnss"),
    ("run", "/cache/bin/toybox", "ls", "-ld", "/mnt/system/system/vendor"),
    ("run", "/cache/bin/toybox", "ls", "-ld", "/system/vendor"),
    ("run", "/cache/bin/toybox", "ls", "-ld", "/vendor"),
    ("run", "/cache/bin/toybox", "ls", "-ld", "/mnt/system/vendor"),
    ("run", "/cache/bin/toybox", "ls", "-ld", "/mnt/system/linkerconfig"),
    ("run", "/cache/bin/toybox", "ls", "-ld", "/mnt/system/system/apex"),
    ("run", "/cache/bin/toybox", "ls", "-ld", "/apex"),
    ("run", "/cache/bin/toybox", "readlink", "/mnt/system/system/vendor"),
    ("run", "/cache/bin/toybox", "readlink", "/system/vendor"),
    ("run", "/cache/bin/toybox", "readlink", "/vendor"),
    ("run", "/cache/bin/toybox", "find", "/mnt/system", "-maxdepth", "4", "-name", "ld.config*.txt"),
)

SAFE_CAT_PATHS = {
    "/proc/mounts",
    "/proc/net/dev",
    "/sys/module/firmware_class/parameters/path",
    "/sys/devices/platform/soc/18800000.qcom,icnss/uevent",
    "/sys/class/block/sda29/dev",
}
SAFE_LS_PATHS = {
    "/sys/class/net",
    "/sys/class/rfkill",
    "/sys/class/ieee80211",
    "/mnt/system",
    "/mnt/system/system",
    "/mnt/system/system/etc",
    "/mnt/system/system/apex",
    "/mnt/system/linkerconfig",
    "/apex",
    "/vendor",
    "/system",
    "/mnt/vendor",
}
SAFE_STAT_PATHS = {
    "/mnt/system/system/vendor",
    "/mnt/system/vendor",
    "/system/vendor",
    "/vendor",
    "/mnt/vendor/bin/cnss-daemon",
    "/vendor/bin/cnss-daemon",
    "/system/vendor/bin/cnss-daemon",
    "/mnt/system/vendor/bin/cnss-daemon",
    "/mnt/system/system/bin/linker64",
    "/mnt/system/system/bin/toybox",
    "/mnt/system/system/lib64/libc.so",
    "/mnt/system/linkerconfig",
    "/mnt/system/linkerconfig/ld.config.txt",
    "/mnt/system/system/etc/ld.config.txt",
    "/mnt/system/system/apex",
    "/mnt/system/system/apex/com.android.runtime",
    "/apex",
    "/apex/com.android.runtime",
    "/cache/bin/a90_android_execns_probe",
    "/cache/bin/toybox",
    "/sys/devices/platform/soc/18800000.qcom,icnss",
    "/sys/bus/platform/drivers/icnss",
}
SAFE_TOYBOX_LS_PATHS = {
    "/mnt/system/system/vendor",
    "/system/vendor",
    "/vendor",
    "/mnt/system/vendor",
    "/mnt/system/linkerconfig",
    "/mnt/system/system/apex",
    "/apex",
}
SAFE_TOYBOX_READLINK_PATHS = {
    "/mnt/system/system/vendor",
    "/system/vendor",
    "/vendor",
}


@dataclass
class CommandRecord:
    name: str
    command: list[str]
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._+-" else "-" for ch in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def manifest_decision(manifest: dict[str, Any]) -> str:
    if manifest.get("missing"):
        return "missing"
    return str(manifest.get("decision", "unknown"))


def manifest_pass(manifest: dict[str, Any]) -> bool:
    return bool(manifest.get("pass")) and not manifest.get("missing")


def load_prior_manifests(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    return {
        "v221": load_json(args.v221_manifest),
        "v222": load_json(args.v222_manifest),
        "v226": load_json(args.v226_manifest),
        "v227": load_json(args.v227_manifest),
        "v228": load_json(args.v228_manifest),
        "v229": load_json(args.v229_manifest),
    }


def validate_prior_manifests(manifests: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for name, expected in EXPECTED_DECISIONS.items():
        manifest = manifests.get(name, {"missing": True})
        actual = manifest_decision(manifest)
        checks.append(
            {
                "name": name,
                "expected_any": sorted(expected),
                "actual": actual,
                "pass": manifest_pass(manifest) and actual in expected,
                "manifest": manifest.get("_manifest_path", manifest.get("path", "")),
            }
        )
    return checks


def validate_live_command(command: Iterable[str]) -> list[str]:
    argv = list(command)
    if not argv:
        return ["empty command"]
    name = argv[0]
    problems: list[str] = []
    if name in {"version", "status", "bootstatus", "mounts"}:
        if len(argv) != 1:
            problems.append("unexpected arity")
    elif name == "selftest":
        if argv != ["selftest", "verbose"]:
            problems.append("only selftest verbose allowed")
    elif name == "mountsystem":
        if argv != ["mountsystem", "ro"]:
            problems.append("only mountsystem ro allowed")
    elif name == "cat":
        if len(argv) != 2 or argv[1] not in SAFE_CAT_PATHS:
            problems.append("cat path not allowlisted")
    elif name == "ls":
        if len(argv) != 2 or argv[1] not in SAFE_LS_PATHS:
            problems.append("ls path not allowlisted")
    elif name == "stat":
        if len(argv) != 2 or argv[1] not in SAFE_STAT_PATHS:
            problems.append("stat path not allowlisted")
    elif name == "run":
        if len(argv) >= 2 and argv[1] != "/cache/bin/toybox":
            problems.append("only /cache/bin/toybox run helper allowed")
        elif len(argv) == 5 and argv[2:4] == ["ls", "-ld"] and argv[4] in SAFE_TOYBOX_LS_PATHS:
            pass
        elif len(argv) == 4 and argv[2] == "readlink" and argv[3] in SAFE_TOYBOX_READLINK_PATHS:
            pass
        elif argv == ["run", "/cache/bin/toybox", "find", "/mnt/system", "-maxdepth", "4", "-name", "ld.config*.txt"]:
            pass
        else:
            problems.append("toybox subcommand not allowlisted")
    else:
        problems.append(f"command not allowlisted: {name}")
    return problems


def record_blocked(store: EvidenceStore, name: str, command: list[str], problems: list[str]) -> CommandRecord:
    path = store.write_text(
        f"commands/{safe_name(name)}.txt",
        "command blocked by v230 guard:\n" + "\n".join(problems) + "\n",
    )
    return CommandRecord(name, command, False, None, "blocked", 0.0, str(path.relative_to(store.run_dir)), "; ".join(problems))


def capture_device(store: EvidenceStore, args: argparse.Namespace, name: str, command: list[str]) -> CommandRecord:
    problems = validate_live_command(command)
    if problems:
        return record_blocked(store, name, command, problems)
    started = time.monotonic()
    capture = run_capture(args, name, command, timeout=args.timeout)
    duration = time.monotonic() - started
    text = capture.text if capture.text else f"{capture.error}\n"
    path = store.write_text(f"commands/{safe_name(name)}.txt", text.rstrip() + "\n")
    return CommandRecord(
        name=name,
        command=command,
        ok=capture.ok,
        rc=capture.rc,
        status=capture.status,
        duration_sec=duration,
        file=str(path.relative_to(store.run_dir)),
        error=capture.error,
    )


def command_label(command: Iterable[str]) -> str:
    return safe_name("-".join(command))


def read_record_text(store: EvidenceStore, record: CommandRecord | None) -> str:
    if record is None:
        return ""
    path = store.run_dir / record.file
    if not path.exists():
        return ""
    return strip_cmdv1_text(path.read_text(encoding="utf-8", errors="replace"))


def find_record(records: dict[str, CommandRecord], command: Iterable[str]) -> CommandRecord | None:
    return records.get(command_label(command))


def run_fresh_v229_preflight(store: EvidenceStore, args: argparse.Namespace) -> dict[str, Any]:
    out_dir = repo_path(args.fresh_v229_out_dir)
    command = [
        "python3",
        "scripts/revalidation/wifi_cnss_start_experiment.py",
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--timeout",
        str(args.timeout),
        "--out-dir",
        str(out_dir),
        "preflight",
    ]
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=args.fresh_v229_timeout,
    )
    duration = time.monotonic() - started
    store.write_text("fresh-v229-preflight.txt", result.stdout)
    manifest_path = out_dir / "manifest.json"
    manifest = load_json(manifest_path)
    return {
        "command": command,
        "rc": result.returncode,
        "duration_sec": duration,
        "out_dir": str(out_dir),
        "manifest": manifest,
        "decision": manifest_decision(manifest),
        "pass": manifest_pass(manifest),
        "accepted": result.returncode == 0 and manifest_decision(manifest) == "start-only-runtime-gap",
    }


def check_bridge_ready(store: EvidenceStore, args: argparse.Namespace) -> dict[str, Any]:
    started = time.monotonic()
    capture = run_capture(args, "bridge-check-version", ["version"], timeout=args.bridge_check_timeout)
    duration = time.monotonic() - started
    text = capture.text if capture.text else f"{capture.error}\n"
    path = store.write_text("bridge-check-version.txt", text.rstrip() + "\n")
    return {
        "ok": capture.ok,
        "rc": capture.rc,
        "status": capture.status,
        "duration_sec": duration,
        "file": str(path.relative_to(store.run_dir)),
        "error": capture.error,
    }


def host_manifest_summary(manifests: dict[str, dict[str, Any]]) -> dict[str, Any]:
    v221 = manifests.get("v221", {})
    v222 = manifests.get("v222", {})
    v226 = manifests.get("v226", {})
    v227 = manifests.get("v227", {})
    cnss: dict[str, Any] = {}
    daemons = v221.get("daemons")
    if isinstance(daemons, list):
        for item in daemons:
            if not isinstance(item, dict):
                continue
            executable = str(item.get("executable", ""))
            binary_path = str(item.get("binary", {}).get("path", "")) if isinstance(item.get("binary"), dict) else ""
            if executable.endswith("/cnss-daemon") or binary_path.endswith("/cnss-daemon"):
                cnss = item
                break
    if not cnss:
        services = v221.get("services", {}) if isinstance(v221.get("services"), dict) else {}
        service = services.get("cnss-daemon", {})
        cnss = service if isinstance(service, dict) else {}
    binary = cnss.get("binary", {}) if isinstance(cnss.get("binary"), dict) else {}
    return {
        "cnss_daemon": {
            "executable": cnss.get("executable"),
            "argv": cnss.get("argv"),
            "interpreter": binary.get("elf", {}).get("interpreter") if isinstance(binary.get("elf"), dict) else None,
            "needed": binary.get("elf", {}).get("needed") if isinstance(binary.get("elf"), dict) else None,
            "unresolved": binary.get("unresolved_libraries"),
        },
        "vendor_root": {
            "path": v222.get("output_vendor_root"),
            "source_root": v222.get("source_root"),
        },
        "vendor_source": {
            "path": v226.get("output_vendor_source") or v226.get("output_root"),
            "source_root": v226.get("source_root"),
        },
        "system_root": {
            "path": v227.get("output_system_root"),
            "source_root": v227.get("source_root"),
        },
    }


def path_exists(record: CommandRecord | None) -> bool:
    return bool(record and record.ok)


def classify_system_vendor(store: EvidenceStore, records: dict[str, CommandRecord]) -> dict[str, Any]:
    readlink_mnt = find_record(records, ["run", "/cache/bin/toybox", "readlink", "/mnt/system/system/vendor"])
    ls_mnt = find_record(records, ["run", "/cache/bin/toybox", "ls", "-ld", "/mnt/system/system/vendor"])
    stat_mnt = find_record(records, ["stat", "/mnt/system/system/vendor"])
    readlink_live = find_record(records, ["run", "/cache/bin/toybox", "readlink", "/system/vendor"])
    ls_live = find_record(records, ["run", "/cache/bin/toybox", "ls", "-ld", "/system/vendor"])
    stat_live = find_record(records, ["stat", "/system/vendor"])

    evidence: list[str] = []
    for record in (readlink_mnt, ls_mnt, stat_mnt, readlink_live, ls_live, stat_live):
        if record:
            text = read_record_text(store, record).strip()
            evidence.append(f"{record.name}: ok={record.ok} text={text[:120]}")

    relation = "unknown"
    mapping = "blocked"
    detail = "unable to prove /system/vendor relation"
    readlink_text = read_record_text(store, readlink_mnt).strip()
    ls_text = read_record_text(store, ls_mnt).strip()
    live_readlink_text = read_record_text(store, readlink_live).strip()
    live_ls_text = read_record_text(store, ls_live).strip()
    if readlink_text in {"vendor", "/vendor", "../vendor"} or "->" in ls_text:
        relation = "symlink-to-vendor"
        mapping = "system-vendor-symlink"
        detail = "/mnt/system/system/vendor is a symlink path"
    elif live_readlink_text in {"vendor", "/vendor", "../vendor"} or "->" in live_ls_text:
        relation = "live-symlink-to-vendor"
        mapping = "system-vendor-symlink"
        detail = "/system/vendor is a live symlink path"
    elif path_exists(stat_mnt) or path_exists(stat_live):
        relation = "directory-or-existing-path"
        mapping = "system-vendor-direct"
        detail = "path exists but symlink direction is not proven"
    elif stat_mnt and not stat_mnt.ok and stat_live and not stat_live.ok:
        relation = "absent"
        mapping = "blocked"
        detail = "neither /mnt/system/system/vendor nor /system/vendor exists in current namespace"
    return {
        "relation": relation,
        "namespace_mapping": mapping,
        "detail": detail,
        "evidence": evidence,
    }


def classify_linker_apex(store: EvidenceStore, records: dict[str, CommandRecord], host_summary: dict[str, Any]) -> dict[str, Any]:
    find_ld = find_record(records, ["run", "/cache/bin/toybox", "find", "/mnt/system", "-maxdepth", "4", "-name", "ld.config*.txt"])
    ld_paths = [
        line.strip()
        for line in read_record_text(store, find_ld).splitlines()
        if line.strip().endswith(".txt")
    ]
    linker_ok = path_exists(find_record(records, ["stat", "/mnt/system/system/bin/linker64"]))
    libc_ok = path_exists(find_record(records, ["stat", "/mnt/system/system/lib64/libc.so"]))
    apex_ok = path_exists(find_record(records, ["stat", "/mnt/system/system/apex/com.android.runtime"])) or path_exists(
        find_record(records, ["stat", "/apex/com.android.runtime"])
    )
    linkerconfig_ok = path_exists(find_record(records, ["stat", "/mnt/system/linkerconfig/ld.config.txt"])) or path_exists(
        find_record(records, ["stat", "/mnt/system/system/etc/ld.config.txt"])
    ) or bool(ld_paths)
    cnss = host_summary.get("cnss_daemon", {})
    needed = cnss.get("needed") or []
    bionic_libs = {"libc.so", "libdl.so", "libm.so", "libc++.so"}
    needs_bionic = any(lib in bionic_libs for lib in needed)
    if linkerconfig_ok:
        linkerconfig_required = "available"
    elif needs_bionic:
        linkerconfig_required = "unknown"
    else:
        linkerconfig_required = "not-observed"
    if apex_ok:
        apex_runtime_required = "available"
    elif needs_bionic:
        apex_runtime_required = "unknown"
    else:
        apex_runtime_required = "not-observed"
    return {
        "linker_interpreter": cnss.get("interpreter"),
        "linker64_available": linker_ok,
        "libc_available": libc_ok,
        "ld_config_paths": ld_paths,
        "linkerconfig_required": linkerconfig_required,
        "apex_runtime_required": apex_runtime_required,
        "apex_runtime_available": apex_ok,
        "needed_bionic_libs": sorted(set(needed).intersection(bionic_libs)),
    }


def classify_vendor_source(store: EvidenceStore, records: dict[str, CommandRecord], host_summary: dict[str, Any]) -> dict[str, Any]:
    record_mounts = records.get(command_label(["cat", "/proc/mounts"]))
    proc_mounts = read_record_text(store, record_mounts)
    vendor_live = path_exists(records.get(command_label(["stat", "/mnt/vendor/bin/cnss-daemon"]))) or path_exists(
        records.get(command_label(["stat", "/vendor/bin/cnss-daemon"]))
    )
    vendor_under_mnt_system = path_exists(records.get(command_label(["stat", "/mnt/system/vendor/bin/cnss-daemon"])))
    sda29_present = path_exists(records.get(command_label(["cat", "/sys/class/block/sda29/dev"])))
    host_vendor_root = host_summary.get("vendor_root", {}).get("path")
    host_vendor_source = host_summary.get("vendor_source", {}).get("path")
    if vendor_live:
        source = "live-mounted"
        detail = "cnss-daemon is visible under live /vendor or /mnt/vendor"
    elif vendor_under_mnt_system:
        source = "live-mounted"
        detail = "cnss-daemon is visible under /mnt/system/vendor"
    elif sda29_present:
        source = "needs-remount"
        detail = "vendor block device is visible but vendor root is not mounted into Android runtime paths"
    elif host_vendor_root or host_vendor_source:
        source = "host-only-evidence"
        detail = "vendor evidence exists on host but live device source is not proven"
    else:
        source = "blocked"
        detail = "no live or host vendor source evidence"
    return {
        "source": source,
        "detail": detail,
        "host_vendor_root": host_vendor_root,
        "host_vendor_source": host_vendor_source,
        "proc_mounts_contains_vendor": "/vendor" in proc_mounts,
    }


def classify_requirements(
    store: EvidenceStore,
    records: dict[str, CommandRecord],
    manifests: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    host_summary = host_manifest_summary(manifests)
    system_vendor = classify_system_vendor(store, records)
    linker_apex = classify_linker_apex(store, records, host_summary)
    vendor_source = classify_vendor_source(store, records, host_summary)
    blockers: list[str] = []
    warnings: list[str] = []
    if system_vendor["namespace_mapping"] == "blocked":
        blockers.append("system-vendor-mapping-unproven")
    if vendor_source["source"] == "blocked":
        blockers.append("vendor-source-unavailable")
    if vendor_source["source"] == "host-only-evidence":
        warnings.append("vendor-source-host-only")
    if linker_apex["linkerconfig_required"] == "unknown":
        blockers.append("linkerconfig-need-unproven")
    if linker_apex["apex_runtime_required"] == "unknown":
        blockers.append("apex-runtime-need-unproven")
    if not linker_apex["linker64_available"]:
        blockers.append("linker64-not-visible")
    if not linker_apex["libc_available"]:
        warnings.append("system-libc-not-visible")
    ready = not blockers and vendor_source["source"] in {"live-mounted", "needs-remount"}
    return {
        "ready": ready,
        "blockers": blockers,
        "warnings": warnings,
        "host_summary": host_summary,
        "system_vendor": system_vendor,
        "linker_apex": linker_apex,
        "vendor_source": vendor_source,
    }


def build_namespace_plan(requirements: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "mode": "inventory-first-private-namespace",
        "daemon_execution": False,
        "global_mounts_allowed": False,
        "requires_probe_flags": ["--allow-temp-namespace", "--assume-yes"],
        "namespace_steps_candidate": [
            "fresh-v229-preflight-must-return-start-only-runtime-gap",
            "prove-/system/vendor-relation",
            "prove-linkerconfig-and-apex-runtime-requirements",
            "classify-live-vendor-source",
            "if-all-ready-only-then-use-private-namespace-helper-in-future-version",
        ],
        "requirements": requirements,
        "forbidden_in_v230": [
            "cnss-daemon execution",
            "cnss_diag execution",
            "global bind mounts",
            "USB rebind",
            "NCM start/stop",
            "Wi-Fi scan/connect/link-up",
            "persistent Android partition writes",
        ],
    }


def decide(
    mode: str,
    prior_checks: list[dict[str, Any]],
    fresh_v229: dict[str, Any] | None,
    requirements: dict[str, Any] | None,
    args: argparse.Namespace,
) -> tuple[str, str, bool]:
    if any(not check["pass"] for check in prior_checks):
        return "android-exec-namespace-blocked", "required v221-v229 evidence is missing or has changed", False
    if mode == "plan":
        return "android-exec-plan-ready", "host-side plan and prior evidence are ready; no live inventory performed", True
    if not fresh_v229 or not fresh_v229.get("accepted"):
        actual = fresh_v229.get("decision") if fresh_v229 else "missing"
        return "android-exec-manual-review-required", f"fresh v229 preflight did not return start-only-runtime-gap: {actual}", False
    if requirements is None:
        return "android-exec-namespace-blocked", "live requirements inventory was not collected", False
    if requirements.get("ready"):
        if mode == "probe":
            if not args.allow_temp_namespace or not args.assume_yes:
                return "android-exec-namespace-blocked", "probe requires --allow-temp-namespace --assume-yes", False
            return (
                "android-exec-namespace-blocked",
                "requirements look ready, but v230 has no private namespace helper and refuses global mounts",
                True,
            )
        return "android-exec-requirements-ready", "read-only inventory indicates a future private namespace probe can be implemented", True
    blockers = requirements.get("blockers", [])
    if blockers:
        return "android-exec-namespace-runtime-gap", "read-only inventory still has blockers: " + ", ".join(blockers), True
    return "android-exec-namespace-blocked", "requirements inventory did not produce a ready or runtime-gap state", False


def write_plan_outputs(store: EvidenceStore, manifests: dict[str, dict[str, Any]], prior_checks: list[dict[str, Any]]) -> None:
    store.write_json("prior-evidence.json", {"checks": prior_checks, "manifests": manifests})
    store.write_json("namespace-plan.json", build_namespace_plan(None))


def collect_live_inventory(store: EvidenceStore, args: argparse.Namespace) -> tuple[list[CommandRecord], dict[str, CommandRecord]]:
    records: list[CommandRecord] = []
    for command_tuple in LIVE_CAPTURE_COMMANDS:
        command = list(command_tuple)
        records.append(capture_device(store, args, command_label(command), command))
    by_name = {record.name: record for record in records}
    store.write_json("live-inventory-commands.json", {"commands": [asdict(record) for record in records]})
    return records, by_name


def build_summary(manifest: dict[str, Any]) -> str:
    prior_rows = [
        [item["name"], ",".join(item["expected_any"]), item["actual"], "PASS" if item["pass"] else "FAIL"]
        for item in manifest["prior_checks"]
    ]
    lines = [
        "# v230 Android Exec Namespace Probe",
        "",
        f"- generated: `{manifest['created']}`",
        f"- mode: `{manifest['mode']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        f"- out_dir: `{manifest['out_dir']}`",
        "",
        "## Prior Evidence",
        "",
        markdown_table(["version", "expected", "actual", "status"], prior_rows),
        "",
    ]
    fresh = manifest.get("fresh_v229")
    if fresh:
        lines.extend(
            [
                "## Fresh v229 Gate",
                "",
                f"- decision: `{fresh.get('decision')}`",
                f"- pass: `{fresh.get('pass')}`",
                f"- accepted: `{fresh.get('accepted')}`",
                f"- out_dir: `{fresh.get('out_dir')}`",
                "",
            ]
        )
    req = manifest.get("requirements")
    if req:
        lines.extend(
            [
                "## Requirements",
                "",
                f"- ready: `{req.get('ready')}`",
                f"- blockers: `{req.get('blockers')}`",
                f"- warnings: `{req.get('warnings')}`",
                f"- /system/vendor relation: `{req['system_vendor']['relation']}`",
                f"- namespace mapping: `{req['system_vendor']['namespace_mapping']}`",
                f"- vendor source: `{req['vendor_source']['source']}`",
                f"- linkerconfig: `{req['linker_apex']['linkerconfig_required']}`",
                f"- apex runtime: `{req['linker_apex']['apex_runtime_required']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Guardrails",
            "",
            "- v230 does not execute `cnss-daemon`.",
            "- v230 does not create global bind mounts.",
            "- `probe` only records why a private namespace helper is required.",
            "",
        ]
    )
    return "\n".join(lines)


def run_mode(args: argparse.Namespace) -> int:
    store = EvidenceStore(repo_path(args.out_dir))
    manifests = load_prior_manifests(args)
    prior_checks = validate_prior_manifests(manifests)
    write_plan_outputs(store, manifests, prior_checks)

    fresh_v229: dict[str, Any] | None = None
    requirements: dict[str, Any] | None = None
    records: list[CommandRecord] = []

    if args.subcommand in {"inventory", "preflight", "probe"}:
        bridge_check = check_bridge_ready(store, args)
        store.write_json("bridge-check.json", bridge_check)
        if bridge_check["ok"]:
            fresh_v229 = run_fresh_v229_preflight(store, args)
            records, by_name = collect_live_inventory(store, args)
            requirements = classify_requirements(store, by_name, manifests)
            store.write_json("requirements-inventory.json", requirements)
            store.write_json("namespace-plan.json", build_namespace_plan(requirements))
        else:
            fresh_v229 = {
                "command": ["version"],
                "rc": bridge_check["rc"],
                "duration_sec": bridge_check["duration_sec"],
                "out_dir": str(store.run_dir),
                "manifest": {},
                "decision": "bridge-unavailable",
                "pass": False,
                "accepted": False,
                "error": bridge_check["error"],
            }

    if args.subcommand == "probe":
        store.write_text(
            "probe-result.txt",
            "v230 does not ship a private Android exec namespace helper.\n"
            "Global bind mounts are refused by design.\n"
            "Use requirements-inventory.json to decide the v231 implementation.\n",
        )

    decision, reason, pass_ok = decide(args.subcommand, prior_checks, fresh_v229, requirements, args)
    manifest = {
        "created": now_iso(),
        "mode": args.subcommand,
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(store.run_dir),
        "expect_version": args.expect_version,
        "prior_checks": prior_checks,
        "fresh_v229": fresh_v229,
        "requirements": requirements,
        "command_count": len(records),
        "host_metadata": collect_host_metadata(),
        "guardrails": [
            "no cnss-daemon execution",
            "no cnss_diag execution",
            "no global bind mounts",
            "no USB/NCM rebind",
            "no Wi-Fi scan/connect/link-up",
            "no persistent Android partition writes",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    print(f"decision={decision} pass={pass_ok} out_dir={store.run_dir}")
    print(f"reason={reason}")
    return 0 if pass_ok else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)

    def add_common(target: argparse.ArgumentParser, *, suppress: bool) -> None:
        default = argparse.SUPPRESS if suppress else None
        target.add_argument("--host", default=default or "127.0.0.1")
        target.add_argument("--port", type=int, default=default or 54321)
        target.add_argument("--timeout", type=float, default=default or 10.0)
        target.add_argument("--expect-version", default=default or DEFAULT_EXPECT_VERSION)
        target.add_argument("--out-dir", type=Path, default=default or (REPO_ROOT / DEFAULT_OUT_DIR))
        target.add_argument("--fresh-v229-out-dir", type=Path, default=default or (REPO_ROOT / DEFAULT_V229_OUT_DIR))
        target.add_argument("--fresh-v229-timeout", type=int, default=default or 180)
        target.add_argument("--bridge-check-timeout", type=float, default=default or 3.0)
        target.add_argument("--v221-manifest", type=Path, default=default or (REPO_ROOT / DEFAULT_V221_MANIFEST))
        target.add_argument("--v222-manifest", type=Path, default=default or (REPO_ROOT / DEFAULT_V222_MANIFEST))
        target.add_argument("--v226-manifest", type=Path, default=default or (REPO_ROOT / DEFAULT_V226_MANIFEST))
        target.add_argument("--v227-manifest", type=Path, default=default or (REPO_ROOT / DEFAULT_V227_MANIFEST))
        target.add_argument("--v228-manifest", type=Path, default=default or (REPO_ROOT / DEFAULT_V228_MANIFEST))
        target.add_argument("--v229-manifest", type=Path, default=default or (REPO_ROOT / DEFAULT_V229_MANIFEST))

    add_common(parser, suppress=False)
    common = argparse.ArgumentParser(add_help=False)
    add_common(common, suppress=True)
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    subparsers.add_parser("plan", parents=[common])
    subparsers.add_parser("inventory", parents=[common])
    subparsers.add_parser("preflight", parents=[common])
    probe_parser = subparsers.add_parser("probe", parents=[common])
    probe_parser.add_argument("--allow-temp-namespace", action="store_true")
    probe_parser.add_argument("--assume-yes", action="store_true")
    subparsers.add_parser("cleanup", parents=[common])
    args = parser.parse_args()
    if args.subcommand != "probe":
        args.allow_temp_namespace = False
        args.assume_yes = False
    if args.subcommand == "cleanup":
        # Cleanup is intentionally a no-op until v231 ships a private helper.
        args.subcommand = "plan"
    return args


if __name__ == "__main__":
    raise SystemExit(run_mode(parse_args()))
