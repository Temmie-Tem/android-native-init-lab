#!/usr/bin/env python3
"""V697 host-only cnss-daemon Binder runtime target classifier.

This classifier consumes existing V684/V695/V696 evidence only. It does not
contact the device, start daemons, mount filesystems, scan/connect, use
credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v697-cnss-binder-runtime-target-classifier")
DEFAULT_V684_MANIFEST = Path("tmp/wifi/v684-cnss-daemon-vndbinder-target/manifest.json")
DEFAULT_V695_MANIFEST = Path("tmp/wifi/v695-provider-confirmed-cnss-retry-orchestrated-live/manifest.json")
DEFAULT_V696_MANIFEST = Path("tmp/wifi/v696-post-provider-retry-blocker-classifier-rerun/manifest.json")
DEFAULT_V695_HELPER = Path(
    "tmp/wifi/v695-provider-confirmed-cnss-retry-orchestrated-live/"
    "arm-v695-v118-provider-confirmed-cnss-retry/live/native/companion-start-only-with-holder.txt"
)
DEFAULT_V695_DMESG = Path(
    "tmp/wifi/v695-provider-confirmed-cnss-retry-orchestrated-live/"
    "arm-v695-v118-provider-confirmed-cnss-retry/live/native/dmesg-delta.txt"
)

FORBIDDEN_ACTIONS = (
    "device command",
    "mount or bind mount",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "supplicant or hostapd start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "sysfs or debugfs write",
    "boot image or partition write",
)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
KEY_VALUE_RE = re.compile(r"^(?P<key>[^=\s][^=]*?)=(?P<value>.*)$")
CNSS_BINDER_FAIL_RE = re.compile(r"cnss-daemon.*binder:.*transaction failed\s+29189/-22", re.I)
GENERIC_BINDER_IOCTL_RE = re.compile(r"binder: .* ioctl .* returned -22", re.I)
PM_QOS_RE = re.compile(r"pm_qos_add_request\(\) called for already added request", re.I)
WLFW_RE = re.compile(r"cnss-daemon wlfw_start: Starting", re.I)
VNDBINDER_RE = re.compile(r"/dev/vndbinder(?:\b|$)")
DEV_BINDER_RE = re.compile(r"/dev/binder(?:\b|$)")
DEV_HWBINDER_RE = re.compile(r"/dev/hwbinder(?:\b|$)")
PERIPHERAL_MANAGER_RE = re.compile(r"\bvendor\.qcom\.PeripheralManager\b")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v684-manifest", type=Path, default=DEFAULT_V684_MANIFEST)
    parser.add_argument("--v695-manifest", type=Path, default=DEFAULT_V695_MANIFEST)
    parser.add_argument("--v696-manifest", type=Path, default=DEFAULT_V696_MANIFEST)
    parser.add_argument("--v695-helper", type=Path, default=DEFAULT_V695_HELPER)
    parser.add_argument("--v695-dmesg", type=Path, default=DEFAULT_V695_DMESG)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ready"}


def intish(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def nested(mapping: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def strip_line(line: str) -> str:
    return ANSI_RE.sub("", line).strip()


def bounded_lines(text: str, pattern: re.Pattern[str], limit: int = 8) -> list[str]:
    rows: list[str] = []
    for raw_line in text.splitlines():
        line = strip_line(raw_line)
        if pattern.search(line):
            rows.append(line[:260])
            if len(rows) >= limit:
                break
    return rows


def parse_key_values(text: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for raw_line in text.splitlines():
        line = strip_line(raw_line)
        match = KEY_VALUE_RE.match(line)
        if not match:
            continue
        values.setdefault(match.group("key"), []).append(match.group("value"))
    return values


def values_for_prefix(key_values: dict[str, list[str]], prefix: str, suffix: str = "") -> list[str]:
    rows: list[str] = []
    for key, values in key_values.items():
        if key.startswith(prefix) and (not suffix or key.endswith(suffix)):
            rows.extend(values)
    return rows


def first_value(key_values: dict[str, list[str]], key: str) -> str:
    values = key_values.get(key) or []
    return values[0] if values else ""


def fd_surface(key_values: dict[str, list[str]], child: str) -> dict[str, Any]:
    targets = values_for_prefix(
        key_values,
        f"capture.wifi_hal_composite_{child}.fd_links.entry_",
        ".target",
    )
    return {
        "child": child,
        "target_count": len(targets),
        "vndbinder_count": sum(1 for target in targets if VNDBINDER_RE.search(target)),
        "binder_count": sum(1 for target in targets if DEV_BINDER_RE.search(target)),
        "hwbinder_count": sum(1 for target in targets if DEV_HWBINDER_RE.search(target)),
        "targets": targets[:12],
    }


def child_exec_surface(key_values: dict[str, list[str]], child: str) -> dict[str, Any]:
    prefix = f"wifi_hal_composite_child.{child}."
    return {
        "child": child,
        "observable": first_value(key_values, prefix + "observable"),
        "exit_code": first_value(key_values, prefix + "exit_code"),
        "signal": first_value(key_values, prefix + "signal"),
        "postflight_safe": first_value(key_values, prefix + "postflight_safe"),
        "selinux_exec_ok": first_value(key_values, prefix + "selinux_exec.ok"),
        "selinux_exec_errno": first_value(key_values, prefix + "selinux_exec.errno"),
        "selinux_exec_target_context": first_value(key_values, prefix + "selinux_exec.target_context"),
        "uid": first_value(key_values, prefix + "uid"),
        "gid": first_value(key_values, prefix + "gid"),
        "groups": first_value(key_values, prefix + "groups"),
        "caps_effective": first_value(key_values, prefix + "caps.effective"),
    }


def dmesg_surface(text: str) -> dict[str, Any]:
    return {
        "cnss_binder_29189_minus_22": len(CNSS_BINDER_FAIL_RE.findall(text)),
        "generic_context_manager_ioctl_minus_22": len(GENERIC_BINDER_IOCTL_RE.findall(text)),
        "pm_qos_duplicate": len(PM_QOS_RE.findall(text)),
        "wlfw_start": len(WLFW_RE.findall(text)),
        "cnss_binder_lines": bounded_lines(text, CNSS_BINDER_FAIL_RE),
        "generic_ioctl_lines": bounded_lines(text, GENERIC_BINDER_IOCTL_RE),
        "pm_qos_lines": bounded_lines(text, PM_QOS_RE),
    }


def build_surface(
    v684_manifest: dict[str, Any],
    v695_manifest: dict[str, Any],
    v696_manifest: dict[str, Any],
    helper_text: str,
    dmesg_text: str,
) -> dict[str, Any]:
    key_values = parse_key_values(helper_text)
    arm_v695 = nested(v695_manifest, ("arm_v695",), {}) or {}
    counts = nested(v695_manifest, ("arm_v695", "counts"), {}) or {}
    cnss_retry = nested(v695_manifest, ("arm_v695", "peripheral", "cnss_retry"), {}) or {}
    children = (
        "cnss_daemon",
        "cnss_daemon_retry",
        "vndservicemanager",
        "servicemanager",
        "hwservicemanager",
        "per_mgr",
        "per_proxy",
    )
    return {
        "v684": {
            "decision": v684_manifest.get("decision", ""),
            "pass": boolish(v684_manifest.get("pass")),
            "static_peripheral_candidate": v684_manifest.get("decision", "") == "v684-cnss-daemon-peripheral-manager-target-candidate",
        },
        "v695": {
            "decision": v695_manifest.get("decision", ""),
            "pass": boolish(v695_manifest.get("pass")),
            "query_exact_match": boolish(arm_v695.get("query_exact_match")),
            "cnss_retry_started": boolish(arm_v695.get("cnss_retry_started")) or bool(first_value(key_values, "wifi_companion_start.cnss_retry.enabled")),
            "retry_start_order": cnss_retry.get("retry_start_order", ""),
            "counts": counts,
        },
        "v696": {
            "decision": v696_manifest.get("decision", ""),
            "pass": boolish(v696_manifest.get("pass")),
        },
        "provider": {
            "literal_count": len(PERIPHERAL_MANAGER_RE.findall(helper_text)),
            "lines": bounded_lines(helper_text, PERIPHERAL_MANAGER_RE),
        },
        "fds": {child: fd_surface(key_values, child) for child in children},
        "children": {child: child_exec_surface(key_values, child) for child in children},
        "dmesg": dmesg_surface(dmesg_text),
    }


def build_checks(surface: dict[str, Any]) -> list[dict[str, Any]]:
    v684 = surface["v684"]
    v695 = surface["v695"]
    v696 = surface["v696"]
    fds = surface["fds"]
    children = surface["children"]
    dmesg = surface["dmesg"]
    cnss_domain = "u:r:vendor_wcnss_service:s0"
    return [
        {
            "name": "input-evidence-ready",
            "status": "pass" if v684["pass"] and v695["pass"] and v696["pass"] else "blocked",
            "detail": {
                "v684_decision": v684["decision"],
                "v695_decision": v695["decision"],
                "v696_decision": v696["decision"],
            },
            "next_step": "refresh V684/V695/V696 evidence before classifying V697",
        },
        {
            "name": "provider-registration-proven",
            "status": "pass" if v695["query_exact_match"] and surface["provider"]["literal_count"] >= 1 else "blocked",
            "detail": {
                "query_exact_match": v695["query_exact_match"],
                "provider_literal_count": surface["provider"]["literal_count"],
                "provider_lines": surface["provider"]["lines"],
            },
            "next_step": "do not target cnss-daemon transaction until provider registration is proven",
        },
        {
            "name": "static-cnss-target-is-peripheral-manager-vndbinder",
            "status": "finding" if v684["static_peripheral_candidate"] else "review",
            "detail": {"v684_decision": v684["decision"]},
            "next_step": "keep the repair target on libperipheral_client/vendor Binder unless new static evidence appears",
        },
        {
            "name": "cnss-daemon-uses-vndbinder",
            "status": "finding" if fds["cnss_daemon"]["vndbinder_count"] > 0 and fds["cnss_daemon_retry"]["vndbinder_count"] > 0 else "review",
            "detail": {
                "initial": fds["cnss_daemon"],
                "retry": fds["cnss_daemon_retry"],
            },
            "next_step": "if absent, repair private /dev/vndbinder mapping before another CNSS retry",
        },
        {
            "name": "vndservicemanager-ready-on-vndbinder",
            "status": "finding" if fds["vndservicemanager"]["vndbinder_count"] > 0 else "review",
            "detail": fds["vndservicemanager"],
            "next_step": "if absent, repair vndservicemanager argv/devnode before CNSS retry",
        },
        {
            "name": "cnss-domain-and-preexec-ok",
            "status": "finding" if (
                children["cnss_daemon"]["selinux_exec_ok"] == "1"
                and children["cnss_daemon_retry"]["selinux_exec_ok"] == "1"
                and children["cnss_daemon"]["selinux_exec_target_context"] == cnss_domain
                and children["cnss_daemon_retry"]["selinux_exec_target_context"] == cnss_domain
            ) else "review",
            "detail": {
                "initial": children["cnss_daemon"],
                "retry": children["cnss_daemon_retry"],
            },
            "next_step": "if context is wrong, repair service-default SELinux exec before Binder framing work",
        },
        {
            "name": "cnss-binder-transaction-failure-stable",
            "status": "finding" if dmesg["cnss_binder_29189_minus_22"] > 0 and dmesg["wlfw_start"] == 0 else "review",
            "detail": {
                "cnss_binder_29189_minus_22": dmesg["cnss_binder_29189_minus_22"],
                "wlfw_start": dmesg["wlfw_start"],
                "lines": dmesg["cnss_binder_lines"],
            },
            "next_step": "target the native cnss-daemon vendor Binder transaction path before WLFW",
        },
        {
            "name": "generic-context-manager-ioctl-demoted",
            "status": "finding" if (
                dmesg["generic_context_manager_ioctl_minus_22"] > 0
                and fds["servicemanager"]["binder_count"] > 0
                and fds["hwservicemanager"]["hwbinder_count"] > 0
                and fds["vndservicemanager"]["vndbinder_count"] > 0
                and v695["query_exact_match"]
            ) else "review",
            "detail": {
                "generic_ioctl_count": dmesg["generic_context_manager_ioctl_minus_22"],
                "servicemanager": fds["servicemanager"],
                "hwservicemanager": fds["hwservicemanager"],
                "vndservicemanager": fds["vndservicemanager"],
                "lines": dmesg["generic_ioctl_lines"],
            },
            "next_step": "treat generic binder/hwbinder ioctl -22 as noise unless provider visibility regresses",
        },
        {
            "name": "pm-qos-remains-secondary",
            "status": "finding" if (
                dmesg["pm_qos_duplicate"] > 0
                and v696["decision"] == "v696-cnss-binder-continuation-remains-primary"
            ) else "review",
            "detail": {
                "pm_qos_duplicate": dmesg["pm_qos_duplicate"],
                "lines": dmesg["pm_qos_lines"],
            },
            "next_step": "track the kernel warning, but do not make it the first repair target",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v697-cnss-binder-runtime-target-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run the host-only V697 classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v697-cnss-binder-runtime-target-classifier-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh missing evidence before planning another live unit",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    required = {
        "static-cnss-target-is-peripheral-manager-vndbinder",
        "cnss-daemon-uses-vndbinder",
        "vndservicemanager-ready-on-vndbinder",
        "cnss-domain-and-preexec-ok",
        "cnss-binder-transaction-failure-stable",
        "generic-context-manager-ioctl-demoted",
    }
    if required <= findings:
        return (
            "v697-cnss-vndbinder-transaction-framing-targeted",
            True,
            "provider registration, vndservicemanager readiness, cnss-daemon /dev/vndbinder fd usage, and SELinux preexec are proven; the remaining primary target is the cnss-daemon vendor Binder transaction framing/runtime path that returns 29189/-22 before WLFW.",
            "plan a narrow capture or repair for cnss-daemon/libperipheral_client vendor Binder transaction framing; keep Wi-Fi HAL, scan/connect, DHCP, routes, credentials, and external ping blocked",
        )
    if "cnss-binder-transaction-failure-stable" in findings:
        return (
            "v697-cnss-binder-target-needs-manual-review",
            True,
            "CNSS Binder -22 remains, but one or more target-isolation checks did not reach finding status",
            "inspect fd/SELinux/provider surfaces before live repair",
        )
    return (
        "v697-cnss-binder-runtime-target-inconclusive",
        False,
        "evidence did not match the expected post-provider CNSS Binder target pattern",
        "refresh V695/V696 evidence and rerun classifier",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v684_manifest = load_json(args.v684_manifest)
    v695_manifest = load_json(args.v695_manifest)
    v696_manifest = load_json(args.v696_manifest)
    helper_text = read_text(args.v695_helper)
    dmesg_text = read_text(args.v695_dmesg)
    surface = build_surface(v684_manifest, v695_manifest, v696_manifest, helper_text, dmesg_text)
    checks = [] if args.command == "plan" else build_checks(surface)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v697",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v684_manifest": str(repo_path(args.v684_manifest)),
            "v695_manifest": str(repo_path(args.v695_manifest)),
            "v696_manifest": str(repo_path(args.v696_manifest)),
            "v695_helper": str(repo_path(args.v695_helper)),
            "v695_dmesg": str(repo_path(args.v695_dmesg)),
        },
        "surface": surface,
        "checks": checks,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "mount_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    fd_rows = [
        [
            child,
            str(surface["vndbinder_count"]),
            str(surface["binder_count"]),
            str(surface["hwbinder_count"]),
            "; ".join(surface["targets"][:4]),
        ]
        for child, surface in manifest["surface"]["fds"].items()
    ]
    child_rows = [
        [
            child,
            surface["observable"],
            surface["exit_code"],
            surface["selinux_exec_ok"],
            surface["selinux_exec_target_context"],
            surface["caps_effective"],
        ]
        for child, surface in manifest["surface"]["children"].items()
    ]
    dmesg = manifest["surface"]["dmesg"]
    return "\n".join([
        "# V697 cnss-daemon Binder Runtime Target Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows) if check_rows else "- plan only",
        "",
        "## Binder FD Surface",
        "",
        markdown_table(["child", "vndbinder", "binder", "hwbinder", "sample targets"], fd_rows),
        "",
        "## Child Runtime Surface",
        "",
        markdown_table(["child", "observable", "exit", "selinux ok", "target context", "caps effective"], child_rows),
        "",
        "## Dmesg Surface",
        "",
        markdown_table(
            ["signal", "count"],
            [
                ["cnss binder 29189/-22", str(dmesg["cnss_binder_29189_minus_22"])],
                ["generic context-manager ioctl -22", str(dmesg["generic_context_manager_ioctl_minus_22"])],
                ["duplicate pm_qos", str(dmesg["pm_qos_duplicate"])],
                ["wlfw_start", str(dmesg["wlfw_start"])],
            ],
        ),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
