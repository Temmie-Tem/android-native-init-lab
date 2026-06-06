#!/usr/bin/env python3
"""V691 host-only classifier for V690 post-property provider exits."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v691-peripheral-post-property-exit-classifier")
DEFAULT_V690_MANIFEST = Path("tmp/wifi/v690-peripheral-manager-cnss-retry-orchestrated-live/manifest.json")
EXPECTED_ACKS = {
    ("vendor.peripheral.SDX50M.state", "OFFLINE"),
    ("vendor.peripheral.modem.state", "OFFLINE"),
}
PROPERTY_DENIAL_RE = re.compile(
    r'(?:Could not find context for property|Access denied finding property) "([^"]+)"',
    re.I,
)
FORBIDDEN_ACTIONS = (
    "device command",
    "helper deploy",
    "daemon or service start",
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "scan/connect/link-up",
    "credential, DHCP, route change, or external ping",
    "boot image or partition write",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v690-manifest", type=Path, default=DEFAULT_V690_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {"present": False, "path": str(repo_path(path))}
    data = json.loads(text)
    data["present"] = True
    data["path"] = str(repo_path(path))
    return data


def arm_manifest_from_v690(v690: dict[str, Any]) -> dict[str, Any]:
    arm_path = ((v690.get("arm_v690") or {}).get("manifest") or "")
    if not arm_path:
        return {}
    return load_json(Path(str(arm_path)))


def evidence_dir(manifest: dict[str, Any], fallback: Path) -> Path:
    evidence = manifest.get("evidence") or manifest.get("out_dir")
    if evidence:
        return repo_path(Path(str(evidence)))
    return repo_path(fallback).parent


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)=(.*)$", line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def companion_text(v690_path: Path, v690: dict[str, Any], arm: dict[str, Any]) -> str:
    arm_path = Path(str((v690.get("arm_v690") or {}).get("manifest") or v690_path))
    return read_text(evidence_dir(arm, arm_path) / "native" / "companion-start-only-with-holder.txt")


def ps_text(v690_path: Path, v690: dict[str, Any], arm: dict[str, Any]) -> str:
    arm_path = Path(str((v690.get("arm_v690") or {}).get("manifest") or v690_path))
    return read_text(evidence_dir(arm, arm_path) / "native" / "ps-before-reboot.txt")


def child_status(keys: dict[str, str], name: str) -> dict[str, str]:
    child_prefix = f"wifi_companion_start.child.{name}."
    start_prefix = f"wifi_hal_composite_start.child.{name}."
    fd_prefix = f"capture.wifi_hal_composite_{name}.fd_links."
    fd_targets = [
        value
        for key, value in keys.items()
        if key.startswith(fd_prefix) and key.endswith(".target")
    ]
    return {
        "pid": keys.get(start_prefix + "pid", ""),
        "pgid": keys.get(start_prefix + "pgid", ""),
        "target": keys.get(start_prefix + "target", ""),
        "start_order": keys.get(child_prefix + "start_order", ""),
        "observable": keys.get(child_prefix + "observable", ""),
        "exited": keys.get(child_prefix + "exited", ""),
        "exit_code": keys.get(child_prefix + "exit_code", ""),
        "signal": keys.get(child_prefix + "signal", ""),
        "postflight_safe": keys.get(child_prefix + "postflight_safe", ""),
        "fd_count": keys.get(fd_prefix + "count", ""),
        "socket_count": keys.get(fd_prefix + "socket_count", ""),
        "has_vndbinder_fd": "1" if any(target.endswith("/dev/vndbinder") for target in fd_targets) else "0",
        "has_binder_fd": "1" if any(target.endswith("/dev/binder") for target in fd_targets) else "0",
        "has_hwbinder_fd": "1" if any(target.endswith("/dev/hwbinder") for target in fd_targets) else "0",
    }


def property_ack_surface(arm: dict[str, Any]) -> dict[str, Any]:
    surface = arm.get("property_shim_surface") or {}
    requests = surface.get("requests") or []
    ack_pairs = {
        (str(request.get("name") or ""), str(request.get("value") or "")): {
            "allowed": str(request.get("allowed") or ""),
            "result": str(request.get("result") or ""),
        }
        for request in requests
    }
    expected = {
        f"{name}={value}": ack_pairs.get((name, value), {})
        for name, value in sorted(EXPECTED_ACKS)
    }
    return {
        "regressed": bool(arm.get("property_ack_regressed")),
        "requests": requests,
        "expected": expected,
    }


def property_denials(text: str) -> dict[str, Any]:
    names = [match.group(1) for match in PROPERTY_DENIAL_RE.finditer(text)]
    counts = collections.Counter(names)
    return {
        "total": len(names),
        "unique": len(counts),
        "top": [[name, count] for name, count in counts.most_common(20)],
        "has_unable_set_property": "Unable to set property" in text,
    }


def residual_processes(ps: str) -> dict[str, Any]:
    targets = ("pm-service", "pm-proxy", "vndservicemanager", "cnss-daemon", "cnss_diag", "qrtr-ns", "pd-mapper")
    found = {
        target: [line for line in ps.splitlines() if target in line]
        for target in targets
    }
    return {
        "counts": {target: len(lines) for target, lines in found.items()},
        "lines": {target: lines[:8] for target, lines in found.items() if lines},
    }


def marker_counts(arm: dict[str, Any]) -> dict[str, int]:
    live = arm.get("live") or {}
    counts = live.get("v655_counts") or {}
    keys = (
        "service_notifier_180",
        "service_notifier_74",
        "cnss_daemon_netlink",
        "cnss_daemon_cld80211",
        "cnss_binder_transaction_failed",
        "binder_transaction_failed",
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    )
    result: dict[str, int] = {}
    for key in keys:
        try:
            result[key] = int(counts.get(key) or 0)
        except (TypeError, ValueError):
            result[key] = 0
    return result


def decide(command: str,
           v690: dict[str, Any],
           arm: dict[str, Any],
           children: dict[str, dict[str, str]],
           ack: dict[str, Any],
           denials: dict[str, Any],
           residual: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v691-peripheral-post-property-exit-classifier-plan-ready",
            True,
            "plan-only; no evidence parsed",
            "run host-only V691 classifier against V690 evidence",
        )
    if not v690.get("present") or not arm.get("present"):
        return "v691-missing-v690-evidence", False, "V690 manifest or arm manifest missing", "restore V690 evidence before V691"
    if v690.get("decision") != "v690-provider-post-property-start-gap-classified":
        return "v691-v690-state-mismatch", False, f"v690_decision={v690.get('decision')}", "refresh V690 before V691 classification"
    if ack.get("regressed") or denials.get("has_unable_set_property"):
        return "v691-property-ack-not-clean", False, f"ack={ack} denials={denials}", "repair V690 exact property ack before exit classification"
    residual_counts = residual.get("counts") or {}
    provider_residual = int(residual_counts.get("pm-service") or 0) + int(residual_counts.get("pm-proxy") or 0)
    per_mgr = children.get("per_mgr") or {}
    per_proxy = children.get("per_proxy") or {}
    if (
        per_mgr.get("observable") == "1"
        and per_mgr.get("exited") == "1"
        and per_mgr.get("exit_code") == "0"
        and per_mgr.get("has_vndbinder_fd") == "1"
        and per_proxy.get("observable") == "1"
        and per_proxy.get("exited") == "1"
        and per_proxy.get("exit_code") == "1"
        and provider_residual == 0
    ):
        return (
            "v691-provider-post-property-exit-classified",
            True,
            "property ack is clean; pm-service exits 0 after vndbinder open, pm-proxy exits 1, and no provider residual process remains",
            "V692 should add targeted provider exit/registration capture before more property-area changes or Wi-Fi HAL start",
        )
    return (
        "v691-provider-post-property-manual-review",
        True,
        f"children={children} residual={residual_counts} ack={ack}",
        "inspect V690 evidence manually before changing helper behavior",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v690 = load_json(args.v690_manifest)
    arm = {} if args.command == "plan" else arm_manifest_from_v690(v690)
    text = "" if args.command == "plan" else companion_text(args.v690_manifest, v690, arm)
    ps = "" if args.command == "plan" else ps_text(args.v690_manifest, v690, arm)
    keys = parse_keys(text)
    children = {name: child_status(keys, name) for name in ("per_mgr", "per_proxy", "cnss_daemon_retry")}
    ack = property_ack_surface(arm)
    denials = property_denials(text)
    residual = residual_processes(ps)
    decision, pass_ok, reason, next_step = decide(args.command, v690, arm, children, ack, denials, residual)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v691",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v690": {"path": v690.get("path"), "present": bool(v690.get("present")), "decision": v690.get("decision"), "pass": v690.get("pass")},
            "v690_arm": {"path": arm.get("path"), "present": bool(arm.get("present")), "decision": arm.get("decision"), "pass": arm.get("pass")},
        },
        "property_ack": ack,
        "remaining_property_denials": denials,
        "provider_children": children,
        "residual_processes": residual,
        "marker_counts": marker_counts(arm),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    input_rows = [[name, str(data["present"]), str(data.get("decision")), str(data.get("path"))] for name, data in manifest["inputs"].items()]
    ack_rows = [
        [item["name"], item["value"], item["allowed"], item["result"]]
        for item in manifest["property_ack"].get("requests", [])
    ]
    child_rows = [
        [name, data["observable"], data["exited"], data["exit_code"], data["signal"], data["fd_count"], data["has_vndbinder_fd"]]
        for name, data in manifest["provider_children"].items()
    ]
    residual_rows = [[name, str(count)] for name, count in sorted((manifest["residual_processes"].get("counts") or {}).items())]
    denial_rows = [[name, str(count)] for name, count in manifest["remaining_property_denials"].get("top", [])]
    marker_rows = [[name, str(count)] for name, count in sorted(manifest["marker_counts"].items())]
    return "\n".join([
        "# V691 Peripheral Post-Property Exit Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "present", "decision", "path"], input_rows),
        "",
        "## Property Ack",
        "",
        markdown_table(["name", "value", "allowed", "result"], ack_rows) if ack_rows else "- not captured",
        "",
        "## Provider Children",
        "",
        markdown_table(["child", "observable", "exited", "exit_code", "signal", "fd_count", "vndbinder_fd"], child_rows),
        "",
        "## Residual Processes",
        "",
        markdown_table(["process", "count"], residual_rows),
        "",
        "## Remaining Property Denials",
        "",
        markdown_table(["property", "count"], denial_rows) if denial_rows else "- none",
        "",
        "## Marker Counts",
        "",
        markdown_table(["marker", "count"], marker_rows),
        "",
        "## Guardrails",
        "",
        *[f"- {item}" for item in manifest["forbidden_actions"]],
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
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
