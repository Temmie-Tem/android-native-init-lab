#!/usr/bin/env python3
"""Model CNSS daemon dry-run feasibility without executing vendor services."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import (
    DEFAULT_EXPECT_VERSION,
    REPO_ROOT,
    capture_to_manifest,
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
    strip_cmdv1_text,
)
from a90harness.evidence import EvidenceStore


DEFAULT_V210_MANIFEST = Path("tmp/wifi/v210-vendor-asset-classifier/manifest.json")
DEFAULT_V216_MANIFEST = Path("tmp/wifi/v216-service-replay-model/manifest.json")
DEFAULT_V217_MANIFEST = Path("tmp/wifi/v217-icnss-debug-recovery-inventory/manifest.json")
DEFAULT_V217_NATIVE_MANIFEST = Path("tmp/wifi/v217-icnss-debug-recovery-inventory-native/manifest.json")

TARGET_SERVICES = ("cnss-daemon", "cnss_diag")
SERVICE_EXECUTABLES = {
    "cnss-daemon": "/system/vendor/bin/cnss-daemon",
    "cnss_diag": "/system/vendor/bin/cnss_diag",
}

ACTIVE_PATTERNS = (
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bctl\.(?:start|restart)\b", re.IGNORECASE),
    re.compile(r"\bclass_start\b", re.IGNORECASE),
    re.compile(r">\s*/sys/", re.IGNORECASE),
    re.compile(r"\b(?:tee|printf|echo)\b.*\s/sys/", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(
        r"(?:^|[;&]\s*)(?:/[^ ]*/)?(?:cnss-daemon|cnss_diag|wificond|wpa_supplicant|hostapd)\b",
        re.IGNORECASE,
    ),
)

NATIVE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 15.0),
    ("status", ["status"], 25.0),
    ("bootstatus", ["bootstatus"], 25.0),
    ("proc-mounts", ["cat", "/proc/mounts"], 20.0),
    ("firmware-class-path", ["cat", "/sys/module/firmware_class/parameters/path"], 20.0),
    ("stat-vendor-cnss-daemon", ["stat", "/vendor/bin/cnss-daemon"], 20.0),
    ("stat-system-vendor-cnss-daemon", ["stat", "/system/vendor/bin/cnss-daemon"], 20.0),
    ("stat-mnt-system-vendor-cnss-daemon", ["stat", "/mnt/system/vendor/bin/cnss-daemon"], 20.0),
    ("stat-vendor-cnss-diag", ["stat", "/vendor/bin/cnss_diag"], 20.0),
    ("stat-system-vendor-cnss-diag", ["stat", "/system/vendor/bin/cnss_diag"], 20.0),
    ("stat-mnt-system-vendor-cnss-diag", ["stat", "/mnt/system/vendor/bin/cnss_diag"], 20.0),
)


@dataclass
class DaemonModel:
    name: str
    executable: str
    vendor_relative_path: str
    native_visible: bool
    native_visibility_source: str
    path_alias_required: bool
    init_source: str
    args: list[str]
    user: str
    groups: list[str]
    capabilities: list[str]
    classes: list[str]
    flags: list[str]
    android_state: str
    process_seen: bool
    elf_interpreter: str
    needed_libraries: list[str]
    elf_inspection: str
    android_runtime_assumptions: list[str]
    blockers: list[str]
    risk: str


def default_out_dir() -> Path:
    return REPO_ROOT / "tmp" / "wifi" / "v218-cnss-daemon-dryrun"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", "--bridge-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v210-manifest", type=Path, default=DEFAULT_V210_MANIFEST)
    parser.add_argument("--v216-manifest", type=Path, default=DEFAULT_V216_MANIFEST)
    parser.add_argument("--v217-manifest", type=Path, default=DEFAULT_V217_MANIFEST)
    parser.add_argument("--v217-native-manifest", type=Path, default=DEFAULT_V217_NATIVE_MANIFEST)
    parser.add_argument("--vendor-root", type=Path, default=None, help="optional host-visible vendor root for readelf only")
    parser.add_argument("--native-bridge", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", name).strip("-") or "capture"


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    return re.sub(r"(?i)(serialno)=([^\s]+)", r"\1=<redacted>", text)


def validate_no_active_commands() -> None:
    command_text = "\n".join(" ".join(argv) for _, argv, _ in NATIVE_COMMANDS)
    for pattern in ACTIVE_PATTERNS:
        if pattern.search(command_text):
            raise AssertionError(f"active command pattern present: {pattern.pattern}")


def collect_native(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    captures: list[dict[str, Any]] = []
    for name, argv, timeout in NATIVE_COMMANDS:
        capture = run_capture(args, name, argv, timeout=timeout)
        text = capture.text if capture.text else capture.error
        store.write_text(f"native/commands/{safe_name(name)}.txt", redact_text(text).rstrip() + "\n")
        data = capture_to_manifest(capture)
        data["file"] = f"native/commands/{safe_name(name)}.txt"
        data["mode"] = "native"
        captures.append(data)
    return captures


def vendor_relative(executable: str) -> str:
    if executable.startswith("/system/vendor/"):
        return executable.removeprefix("/system/vendor/")
    if executable.startswith("/vendor/"):
        return executable.removeprefix("/vendor/")
    return executable.lstrip("/")


def service_from_graph(v216: dict[str, Any], name: str) -> dict[str, Any]:
    for service in v216.get("graph", {}).get("services", []):
        if isinstance(service, dict) and service.get("name") == name:
            return service
    return {"name": name, "executable": SERVICE_EXECUTABLES.get(name, "")}


def service_from_v210(v210: dict[str, Any], name: str) -> dict[str, Any]:
    classification = v210.get("classification")
    if not isinstance(classification, dict):
        return {}
    for service in classification.get("service_blocks", []):
        if isinstance(service, dict) and service.get("name") == name:
            return service
    return {}


def visible_paths(v210: dict[str, Any]) -> set[str]:
    classification = v210.get("classification")
    if not isinstance(classification, dict):
        return set()
    values = classification.get("visible_paths")
    if not isinstance(values, list):
        return set()
    return {str(value).lstrip("/") for value in values}


def run_readelf(binary: Path) -> tuple[str, str, list[str]]:
    if not binary.exists():
        return "missing-local-binary", "", []
    try:
        result = subprocess.run(
            ["readelf", "-d", "-l", str(binary)],
            cwd=REPO_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
    except FileNotFoundError:
        return "readelf-unavailable", "", []
    except subprocess.TimeoutExpired:
        return "readelf-timeout", "", []
    if result.returncode != 0:
        return f"readelf-rc-{result.returncode}", "", []
    interpreter = ""
    needed: list[str] = []
    for line in result.stdout.splitlines():
        interp_match = re.search(r"Requesting program interpreter:\s*([^\]]+)", line)
        if interp_match:
            interpreter = interp_match.group(1).strip()
        needed_match = re.search(r"Shared library:\s*\[([^\]]+)\]", line)
        if needed_match:
            needed.append(needed_match.group(1))
    return "ok", interpreter, sorted(set(needed))


def host_binary_path(args: argparse.Namespace, relative_path: str) -> Path | None:
    if args.vendor_root is None:
        return None
    root = args.vendor_root if args.vendor_root.is_absolute() else REPO_ROOT / args.vendor_root
    return root / relative_path


def build_daemon_model(args: argparse.Namespace,
                       v210: dict[str, Any],
                       v216: dict[str, Any],
                       v217: dict[str, Any],
                       v217_native: dict[str, Any],
                       name: str) -> DaemonModel:
    graph_service = service_from_graph(v216, name)
    v210_service = service_from_v210(v210, name)
    executable = str(graph_service.get("executable") or v210_service.get("executable") or SERVICE_EXECUTABLES[name])
    rel = vendor_relative(executable)
    visible = rel in visible_paths(v210)
    binary_path = host_binary_path(args, rel)
    if binary_path is not None:
        elf_state, interpreter, libraries = run_readelf(binary_path)
    else:
        elf_state, interpreter, libraries = "no-host-vendor-root", "", []

    blockers = list(graph_service.get("blockers") or [])
    assumptions: list[str] = []
    if executable.startswith("/system/vendor/"):
        assumptions.append("requires /system/vendor -> /vendor path compatibility")
    if v217.get("decision") == "state-only-inventory" or v217_native.get("decision") == "state-only-inventory":
        blockers.append("reboot-only-icnss-recovery-known")
    if not visible:
        blockers.append("native-vendor-binary-not-visible-in-v210")
    if elf_state != "ok":
        blockers.append(f"elf-inspection-{elf_state}")
    if name == "cnss-daemon":
        assumptions.extend([
            "requires NET_ADMIN capability",
            "requires Android wifi/system/net_admin group policy",
            "may depend on ICNSS QMI/PDR service ordering",
        ])
    else:
        assumptions.extend([
            "diagnostic service is oneshot in Android service model",
            "may require diag group/device availability",
        ])

    return DaemonModel(
        name=name,
        executable=executable,
        vendor_relative_path=rel,
        native_visible=visible,
        native_visibility_source="v210-visible_paths" if visible else "missing",
        path_alias_required=executable.startswith("/system/vendor/"),
        init_source=str(graph_service.get("source") or v210_service.get("source") or ""),
        args=list(graph_service.get("args") or str(v210_service.get("args") or "").split()),
        user=str(graph_service.get("user") or v210_service.get("user") or ""),
        groups=list(graph_service.get("groups") or v210_service.get("group") or []),
        capabilities=list(graph_service.get("capabilities") or v210_service.get("capabilities") or []),
        classes=list(graph_service.get("classes") or v210_service.get("class") or []),
        flags=list(graph_service.get("flags") or v210_service.get("flags") or []),
        android_state=str(graph_service.get("android_state") or ""),
        process_seen=bool(graph_service.get("process_seen")),
        elf_interpreter=interpreter,
        needed_libraries=libraries,
        elf_inspection=elf_state,
        android_runtime_assumptions=assumptions,
        blockers=sorted(set(blockers)),
        risk="kernel-lifecycle-high",
    )


def decide(v210: dict[str, Any],
           v216: dict[str, Any],
           v217: dict[str, Any],
           models: list[DaemonModel]) -> tuple[str, str, bool]:
    if v210.get("decision") not in {"asset-map-ready", "firmware-path-policy-needed"}:
        return "insufficient-evidence", "v210 vendor asset map is not available", False
    if v216.get("decision") != "replay-model-ready":
        return "insufficient-evidence", "v216 service replay model is not ready", False
    if v217.get("decision") not in {"state-only-inventory", "safe-control-candidate"}:
        return "insufficient-evidence", "v217 ICNSS recovery inventory is not usable", False
    if any(not model.native_visible for model in models):
        return "daemon-native-blocked", "one or more CNSS daemon binaries are not visible in vendor asset evidence", False
    if any(model.elf_inspection != "ok" for model in models):
        return "daemon-dryrun-partial", "service and binary visibility are mapped, but host ELF/library inspection is incomplete", True
    broad_blockers = [
        blocker
        for model in models
        for blocker in model.blockers
        if blocker.startswith("requires-") or blocker.startswith("reboot-only")
    ]
    if broad_blockers:
        return "daemon-dryrun-partial", "dependencies are mapped but runtime/recovery blockers remain", True
    return "daemon-dryrun-ready", "CNSS daemon dependency surface is mapped for v219 shim planning", True


def build_summary(manifest: dict[str, Any]) -> str:
    rows = []
    for daemon in manifest["daemons"]:
        rows.append([
            daemon["name"],
            daemon["executable"],
            "yes" if daemon["native_visible"] else "no",
            daemon["elf_inspection"],
            ", ".join(daemon["capabilities"]) or "none",
            ", ".join(daemon["blockers"][:4]) or "none",
        ])
    lines = [
        "# v218 CNSS Daemon Dry-Run Feasibility",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        "",
        "## Daemons",
        "",
        markdown_table(["name", "executable", "native visible", "ELF", "capabilities", "blockers"], rows),
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
        "- `cnss-daemon` and `cnss_diag` remain blocked until v219+ explicitly approves a shim experiment.",
        "- Wi-Fi HAL, supplicant, hostapd, scan, and connect remain blocked.",
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
    v217 = load_json(args.v217_manifest)
    v217_native = load_json(args.v217_native_manifest)

    captures: list[dict[str, Any]] = []
    if args.native_bridge:
        captures = collect_native(args, store)

    daemon_models = [
        build_daemon_model(args, v210, v216, v217, v217_native, name)
        for name in TARGET_SERVICES
    ]
    decision, reason, pass_ok = decide(v210, v216, v217, daemon_models)

    dependencies = {
        "daemons": [asdict(model) for model in daemon_models],
        "source_decisions": {
            "v210": v210.get("decision"),
            "v216": v216.get("decision"),
            "v217": v217.get("decision"),
            "v217_native": v217_native.get("decision"),
        },
    }
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "mode": "native" if args.native_bridge else "manifest-only",
        "inputs": {
            "v210_manifest": str(repo_path(args.v210_manifest)),
            "v216_manifest": str(repo_path(args.v216_manifest)),
            "v217_manifest": str(repo_path(args.v217_manifest)),
            "v217_native_manifest": str(repo_path(args.v217_native_manifest)),
            "vendor_root": str(args.vendor_root) if args.vendor_root else None,
        },
        "captures": captures,
        "daemons": dependencies["daemons"],
        "dependencies": dependencies,
        "guardrails": [
            "no daemon execution",
            "no service start",
            "no ICNSS sysfs/debugfs writes",
            "no firmware path mutation",
            "no vendor/system mount mutation in default mode",
            "no Wi-Fi enablement",
            "no rfkill write",
            "no link-up",
            "no scan/connect",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_json("daemon-dependencies.json", dependencies)
    store.write_text("summary.md", build_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
