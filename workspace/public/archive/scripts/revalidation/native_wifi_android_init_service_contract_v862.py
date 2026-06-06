#!/usr/bin/env python3
"""V862 Android init service-contract classifier for PeripheralManager.

This is a host-only classifier. It does not contact the device, start daemons,
start Wi-Fi HAL, scan/connect, use credentials, run DHCP, change routes, ping
externally, write sysfs/debugfs/GPIO/subsystem nodes, or write boot/partitions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_OUT_DIR = Path("tmp/wifi/v862-android-init-service-contract")
DEFAULT_TARGET_RC = Path("tmp/wifi/v210-vendor-asset-classifier/native/commands/cat-etc-init-hw-init.target.rc.txt")
DEFAULT_V210_MANIFEST = Path("tmp/wifi/v210-vendor-asset-classifier/manifest.json")
DEFAULT_V853_MANIFEST = Path("tmp/wifi/v853-android-esoc-actor-handoff/v853-android-esoc-actor-run/manifest.json")
DEFAULT_V861_MANIFEST = Path("tmp/wifi/v861-pm-service-domain-parity-live-r2/manifest.json")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")

TARGET_SERVICES = ("vendor.per_mgr", "vendor.per_proxy", "vendor.per_proxy_helper")


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return Path(result.stdout.strip())


def repo_path(path: Path) -> Path:
    return path if path.is_absolute() else repo_root() / path


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def cmdv1_payload(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if line.startswith("a90:/#") or line.startswith("A90P1 ") or line.startswith("[done]"):
            continue
        lines.append(line)
    return "\n".join(lines)


def parse_init_services(text: str) -> dict[str, dict[str, Any]]:
    services: dict[str, dict[str, Any]] = {}
    current: dict[str, Any] | None = None
    for raw_line in cmdv1_payload(text).splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        service_match = re.match(r"^service\s+(\S+)\s+(\S+)(?:\s+(.*))?$", stripped)
        if service_match and not raw_line[:1].isspace():
            name, path, args = service_match.groups()
            current = {
                "name": name,
                "path": path,
                "args": args or "",
                "options": [],
                "class": [],
                "user": "",
                "group": [],
                "disabled": False,
                "oneshot": False,
                "shutdown": [],
                "ioprio": "",
                "capabilities": [],
                "socket": [],
                "file": [],
            }
            services[name] = current
            continue
        if current is None:
            continue
        if not raw_line[:1].isspace() and re.match(r"^(on|import|service)\b", stripped):
            current = None
            continue
        if current is None:
            continue
        current["options"].append(stripped)
        parts = stripped.split()
        if not parts:
            continue
        key = parts[0]
        if key == "class":
            current["class"].extend(parts[1:])
        elif key == "user" and len(parts) > 1:
            current["user"] = parts[1]
        elif key == "group":
            current["group"].extend(parts[1:])
        elif key == "disabled":
            current["disabled"] = True
        elif key == "oneshot":
            current["oneshot"] = True
        elif key == "shutdown":
            current["shutdown"].extend(parts[1:])
        elif key == "ioprio":
            current["ioprio"] = " ".join(parts[1:])
        elif key == "capabilities":
            current["capabilities"].extend(parts[1:])
        elif key == "socket":
            current["socket"].append(" ".join(parts[1:]))
        elif key == "file":
            current["file"].append(" ".join(parts[1:]))
    return services


def parse_init_actions(text: str) -> dict[str, list[str]]:
    actions: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in cmdv1_payload(text).splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        action_match = re.match(r"^on\s+(.+)$", stripped)
        if action_match and not raw_line[:1].isspace():
            current = action_match.group(1)
            actions[current] = []
            continue
        if current is None:
            continue
        if not raw_line[:1].isspace() and re.match(r"^(service|import|on)\b", stripped):
            current = None
            continue
        if current is not None:
            actions[current].append(stripped)
    return actions


def manifest_text(data: dict[str, Any]) -> str:
    parts: list[str] = []
    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
        elif isinstance(value, str):
            parts.append(value)
    walk(data)
    return "\n".join(parts)


def v861_children(v861: dict[str, Any]) -> dict[str, dict[str, str]]:
    children = ((v861.get("analysis") or {}).get("helper") or {}).get("children") or {}
    return {str(name): dict(value) for name, value in children.items() if isinstance(value, dict)}


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    target_rc = read_text(args.target_rc)
    v210 = load_json(args.v210_manifest)
    v853 = load_json(args.v853_manifest)
    v861 = load_json(args.v861_manifest)
    helper = read_text(args.helper_source)
    services = parse_init_services(target_rc)
    actions = parse_init_actions(target_rc)
    v210_text = manifest_text(v210)
    v853_text = manifest_text(v853)
    children = v861_children(v861)
    per_mgr = services.get("vendor.per_mgr", {})
    per_proxy = services.get("vendor.per_proxy", {})

    per_mgr_running_action = actions.get("property:init.svc.vendor.per_mgr=running", [])
    sys_shutdown_action = actions.get("property:sys.shutdown.requested=*", [])
    gaps = {
        "per_mgr_ioprio_rt4_missing_in_helper": per_mgr.get("ioprio") == "rt 4" and "ioprio" not in helper,
        "per_proxy_property_lifecycle_not_modelled": "start vendor.per_proxy" in per_mgr_running_action,
        "per_proxy_shutdown_stop_not_modelled": "stop vendor.per_proxy" in sys_shutdown_action,
        "per_proxy_helper_started_by_android_but_not_modelled": (
            "starting service 'vendor.per_proxy_helper'" in v853_text and "per_proxy_helper" not in helper
        ),
        "per_proxy_helper_rc_content_missing": (
            "pm_proxy_helper.rc" in v210_text and "service vendor.per_proxy_helper" not in target_rc
        ),
        "runtime_domain_still_kernel": any(
            child.get("actual_attr_current") == "kernel"
            for name, child in children.items()
            if name in {"per_mgr", "per_proxy"}
        ),
        "subsys_fd_hold_absent": not (
            ((v861.get("analysis") or {}).get("helper") or {}).get("per_mgr_holds_subsys_esoc0")
            and ((v861.get("analysis") or {}).get("helper") or {}).get("per_mgr_holds_subsys_modem")
        ),
    }
    if gaps["per_proxy_helper_rc_content_missing"]:
        decision = "v862-init-contract-classified-pm-proxy-helper-content-needed"
        next_step = "capture /vendor/etc/init/pm_proxy_helper.rc read-only before modelling vendor.per_proxy_helper"
    elif gaps["per_mgr_ioprio_rt4_missing_in_helper"] or gaps["per_proxy_property_lifecycle_not_modelled"]:
        decision = "v862-init-contract-classified-init-wrapper-needed"
        next_step = "implement bounded init-equivalent wrapper for ioprio and init.svc vendor.per_mgr lifecycle"
    elif gaps["runtime_domain_still_kernel"]:
        decision = "v862-init-contract-classified-selinux-transition-gap"
        next_step = "classify init-domain transition semantics before mdm_helper"
    else:
        decision = "v862-init-contract-no-new-gap"
        next_step = "review evidence manually before actor escalation"

    return {
        "generated_at": now_iso(),
        "command": args.command,
        "pass": True,
        "decision": decision,
        "reason": "Android init contract exposes lifecycle inputs not reproduced by V861 direct exec",
        "next_step": next_step,
        "inputs": {
            "target_rc": str(args.target_rc),
            "v210_manifest": str(args.v210_manifest),
            "v853_manifest": str(args.v853_manifest),
            "v861_manifest": str(args.v861_manifest),
            "helper_source": str(args.helper_source),
        },
        "android_init_contract": {
            "services": {name: services.get(name, {}) for name in TARGET_SERVICES},
            "per_mgr_running_action": per_mgr_running_action,
            "sys_shutdown_action": sys_shutdown_action,
            "pm_proxy_helper_rc_listed": "pm_proxy_helper.rc" in v210_text,
            "pm_proxy_helper_android_started": "starting service 'vendor.per_proxy_helper'" in v853_text,
        },
        "v861_native_result": {
            "decision": v861.get("decision", ""),
            "children": {name: children.get(name, {}) for name in ("per_mgr", "per_proxy", "vndservicemanager")},
            "property_denials_total": (((v861.get("analysis") or {}).get("helper") or {}).get("property_denials") or {}).get("total"),
        },
        "helper_contract": {
            "has_per_mgr_identity_contract": "apply_peripheral_manager_identity_contract" in helper,
            "has_per_mgr_selinux_mapping": "u:r:vendor_per_mgr:s0" in helper,
            "has_ioprio_support": "ioprio" in helper,
            "has_per_proxy_helper_model": "per_proxy_helper" in helper,
            "has_init_svc_lifecycle_model": "init.svc.vendor.per_mgr" in helper,
        },
        "gaps": gaps,
        "hard_gates": {
            "device_contact_executed": False,
            "daemon_start_executed": False,
            "mdm_helper_start_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "raw_esoc_ioctl_executed": False,
            "gpio_write_executed": False,
            "sysfs_write_executed": False,
            "boot_or_partition_write_executed": False,
        },
    }


def write_outputs(out_dir: Path, manifest: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    services = manifest["android_init_contract"]["services"]
    lines = [
        "# V862 Android Init Service Contract Classifier",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- next: {manifest['next_step']}",
        "",
        "## Service Contract",
        "",
        "| Service | Path | Class | User | Group | Disabled | I/O priority |",
        "|---|---|---|---|---|---|---|",
    ]
    for name in TARGET_SERVICES:
        service = services.get(name) or {}
        lines.append(
            "| {name} | `{path}` | `{classes}` | `{user}` | `{groups}` | `{disabled}` | `{ioprio}` |".format(
                name=name,
                path=service.get("path", ""),
                classes=",".join(service.get("class", [])),
                user=service.get("user", ""),
                groups=",".join(service.get("group", [])),
                disabled=service.get("disabled", ""),
                ioprio=service.get("ioprio", ""),
            )
        )
    lines.extend([
        "",
        "## Gaps",
        "",
    ])
    for name, value in manifest["gaps"].items():
        lines.append(f"- `{name}`: `{value}`")
    lines.extend([
        "",
        "## Guardrails",
        "",
    ])
    for name, value in manifest["hard_gates"].items():
        lines.append(f"- `{name}`: `{value}`")
    (out_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--target-rc", type=Path, default=DEFAULT_TARGET_RC)
    parser.add_argument("--v210-manifest", type=Path, default=DEFAULT_V210_MANIFEST)
    parser.add_argument("--v853-manifest", type=Path, default=DEFAULT_V853_MANIFEST)
    parser.add_argument("--v861-manifest", type=Path, default=DEFAULT_V861_MANIFEST)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    write_outputs(repo_path(args.out_dir), manifest)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"summary: {repo_path(args.out_dir / 'summary.md')}")
    print(f"manifest: {repo_path(args.out_dir / 'manifest.json')}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
