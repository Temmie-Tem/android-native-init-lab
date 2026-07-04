#!/usr/bin/env python3
"""WSTA89 host-only D-harden readiness audit.

WSTA80/WSTA88 make the public publish workflow usable and default-off.  WSTA89
starts the next security phase without touching the device: consume existing
redacted D0/Debian-eye inventory summaries and classify which D-harden controls
are ready, partial, blocked, or still need a live/source implementation unit.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_wsta88_persistent_operator_workflow as wsta88  # noqa: E402


REPO_ROOT = wsta88.REPO_ROOT
PRIVATE_ROOT = wsta88.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta88.DEFAULT_RUN_BASE
DEFAULT_D0_SUMMARY = REPO_ROOT / "workspace/private/runs/server-distro/d0-device-live-20260702T200338Z/inventory_public_summary.json"
DEFAULT_DEBIAN_EYE_SUMMARY = REPO_ROOT / "workspace/private/runs/server-distro/debian-eye-hw-inventory-20260704T082032Z/debian_eye_public_summary.json"
DESIGN_DOC = REPO_ROOT / "docs/plans/NATIVE_INIT_SERVER_DISTRO_ENDGAME_DESIGN_2026-06-30.md"
PASS_DECISION = "wsta89-hardening-readiness-audit-pass"


def rel(path: Path) -> str:
    return wsta88.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta88.is_under(path, root)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object JSON: {path}")
    return payload


def safety_flags() -> dict[str, Any]:
    return {
        "device_action": False,
        "boot_flash": False,
        "native_reboot": False,
        "wifi_connect": False,
        "dhcp": False,
        "public_tunnel": False,
        "public_smoke": False,
        "userdata_touch": False,
        "switch_root": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def template() -> dict[str, Any]:
    return {
        "scope": "WSTA89 host-only D-harden readiness audit",
        "default_mode": "host-only-existing-redacted-inventory",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--audit-hardening-readiness",
            "--d0-public-summary-json",
            rel(DEFAULT_D0_SUMMARY),
            "--debian-eye-public-summary-json",
            rel(DEFAULT_DEBIAN_EYE_SUMMARY),
        ],
        "device_action": False,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def public_summary(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": result.get("decision"),
        "run_dir": result.get("run_dir"),
        "gate_decision": result.get("gate_decision"),
        "audit": result.get("audit", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta88.redaction_findings(payload)


def config_value(d0: dict[str, Any], key: str) -> str:
    return str((d0.get("kernel_config") or {}).get(key, "missing"))


def bool_value(payload: dict[str, Any], *path: str) -> bool | None:
    current: Any = payload
    for item in path:
        if not isinstance(current, dict) or item not in current:
            return None
        current = current[item]
    if isinstance(current, bool):
        return current
    return None


def control(name: str, status: str, evidence: list[str], next_action: str, *, blocks_always_on: bool) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "evidence": evidence,
        "next_action": next_action,
        "blocks_persistent_always_on": blocks_always_on,
    }


def classify_controls(d0: dict[str, Any], debian_eye: dict[str, Any] | None) -> list[dict[str, Any]]:
    seccomp_ready = config_value(d0, "CONFIG_SECCOMP") == "y" and config_value(d0, "CONFIG_SECCOMP_FILTER") == "y"
    netns = config_value(d0, "CONFIG_NET_NS") == "y"
    veth = config_value(d0, "CONFIG_VETH") == "y"
    tun_cfg = config_value(d0, "CONFIG_TUN") == "y"
    tun_node = bool_value(d0, "tun_device_present")
    overlay = bool_value(d0, "filesystems", "overlay")
    ext4 = bool_value(d0, "filesystems", "ext4")
    root_locked = bool_value(d0, "host_staging", "root_shadow_locked")
    apparmor_cfg = config_value(d0, "CONFIG_SECURITY_APPARMOR")
    nf_tables = config_value(d0, "CONFIG_NF_TABLES")
    iptables = config_value(d0, "CONFIG_NETFILTER")
    vendor_absent = debian_eye.get("vendor_userspace_absent", {}) if isinstance(debian_eye, dict) else {}
    network_redacted = bool_value(debian_eye or {}, "network", "ip_addr_values_redacted")

    controls = [
        control(
            "seccomp-bpf-per-service",
            "ready-for-profile-source" if seccomp_ready else "blocked-kernel-config",
            [
                f"CONFIG_SECCOMP={config_value(d0, 'CONFIG_SECCOMP')}",
                f"CONFIG_SECCOMP_FILTER={config_value(d0, 'CONFIG_SECCOMP_FILTER')}",
            ],
            "add per-service seccomp profile templates and a runner-level enforcement proof",
            blocks_always_on=not seccomp_ready,
        ),
        control(
            "capability-drop-nonroot-services",
            "needs-service-manifest",
            [
                f"root_shadow_locked={root_locked}",
                f"ext4={ext4}",
            ],
            "define service users, ambient/bounding capability sets, and no-new-privs policy",
            blocks_always_on=True,
        ),
        control(
            "network-namespace-containment",
            "partial-no-veth" if netns and not veth else ("ready-for-prototype" if netns else "blocked-kernel-config"),
            [
                f"CONFIG_NET_NS={config_value(d0, 'CONFIG_NET_NS')}",
                f"CONFIG_VETH={config_value(d0, 'CONFIG_VETH')}",
                f"network_values_redacted={network_redacted}",
            ],
            "prototype namespace isolation that does not require veth, or choose host-network plus seccomp/caps",
            blocks_always_on=not netns,
        ),
        control(
            "tun-node-tunnel-support",
            "partial-node-missing" if tun_cfg and not tun_node else ("ready" if tun_cfg and tun_node else "blocked-kernel-config"),
            [
                f"CONFIG_TUN={config_value(d0, 'CONFIG_TUN')}",
                f"tun_device_present={tun_node}",
            ],
            "materialize /dev/net/tun only if the selected tunnel mode requires it; quick HTTP tunnel may not",
            blocks_always_on=False,
        ),
        control(
            "apparmor-mac",
            "needs-proof" if apparmor_cfg == "missing" else ("ready-for-profile-source" if apparmor_cfg == "y" else "blocked-kernel-config"),
            [f"CONFIG_SECURITY_APPARMOR={apparmor_cfg}"],
            "inventory LSM/AppArmor config and userspace before treating AppArmor as available",
            blocks_always_on=False,
        ),
        control(
            "packet-filter-default-drop",
            "needs-netfilter-inventory" if nf_tables == "missing" and iptables == "missing" else "ready-for-filter-prototype",
            [
                f"CONFIG_NF_TABLES={nf_tables}",
                f"CONFIG_NETFILTER={iptables}",
            ],
            "run a read-only netfilter/iptables/nftables inventory, then pick the viable default-drop mechanism",
            blocks_always_on=True,
        ),
        control(
            "overlay-free-persistence",
            "blocked-overlay-missing-use-plain-ext4" if overlay is False else "ready",
            [f"overlay={overlay}", f"ext4={ext4}"],
            "keep persistence on plain ext4/userdata or SD image; do not design around overlayfs",
            blocks_always_on=False,
        ),
        control(
            "minimal-vendor-userspace",
            "ready-observed-absent" if vendor_absent else "needs-debian-eye-inventory",
            [f"vendor_userspace_absent_keys={','.join(sorted(vendor_absent)) if vendor_absent else 'missing'}"],
            "keep Debian service set minimal and continue native-owned vendor Wi-Fi boundary",
            blocks_always_on=False,
        ),
        control(
            "tier2-text-hard-disable",
            "needs-target-selection",
            ["REPL hardening-posture bundle exists", "no server-distro hard-disable target list selected"],
            "select unused built-in attack-surface targets after service profile requirements are fixed",
            blocks_always_on=False,
        ),
    ]
    return controls


def build_audit(d0_path: Path, d0: dict[str, Any], debian_path: Path | None, debian_eye: dict[str, Any] | None) -> dict[str, Any]:
    controls = classify_controls(d0, debian_eye)
    blocking = [item["name"] for item in controls if item["blocks_persistent_always_on"] and item["status"] not in {"ready", "ready-for-profile-source", "ready-for-prototype", "ready-observed-absent"}]
    return {
        "state": "HARDENING_READINESS_AUDITED",
        "design_doc": rel(DESIGN_DOC),
        "d0_public_summary": rel(d0_path),
        "debian_eye_public_summary": rel(debian_path) if debian_path else None,
        "controls": controls,
        "blocking_before_persistent_always_on": blocking,
        "recommended_next_units": [
            "WSTA90 source: per-service seccomp/capability manifest skeleton",
            "WSTA91 read-only live: netfilter/iptables/nftables inventory",
            "WSTA92 source/live: enforce no-new-privs plus capability drop for one smoke service",
            "WSTA93 design: Tier-2 hard-disable candidate selection after service needs are fixed",
        ],
        "default_public_off": True,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# WSTA D-Harden Readiness Audit",
        "",
        f"- State: `{audit.get('state')}`",
        f"- D0 summary: `{audit.get('d0_public_summary')}`",
        f"- Debian-eye summary: `{audit.get('debian_eye_public_summary')}`",
        f"- Design: `{audit.get('design_doc')}`",
        "- Device action: `false`",
        "- Default public state: `PUBLIC_OFF`",
        "",
        "## Controls",
        "",
        "| Control | Status | Blocks always-on | Next action |",
        "| --- | --- | --- | --- |",
    ]
    for item in audit.get("controls", []):
        lines.append(
            "| `{name}` | `{status}` | `{blocks}` | {next_action} |".format(
                name=item.get("name"),
                status=item.get("status"),
                blocks=str(bool(item.get("blocks_persistent_always_on"))).lower(),
                next_action=item.get("next_action"),
            )
        )
    lines.extend([
        "",
        "## Blocking Before Persistent Always-On",
        "",
    ])
    for name in audit.get("blocking_before_persistent_always_on", []):
        lines.append(f"- `{name}`")
    lines.extend(["", "## Recommended Next Units", ""])
    for item in audit.get("recommended_next_units", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta89-hardening-readiness-audit-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    result: dict[str, Any] = {
        "scope": "WSTA89 host-only D-harden readiness audit",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta89-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta89-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / "wsta89_hardening_readiness.json"
    out_md = run_dir / "wsta89_hardening_readiness.md"

    if not args.audit_hardening_readiness:
        result["decision"] = "wsta89-blocked-audit-hardening-readiness-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    d0_path = resolve_path(args.d0_public_summary_json)
    if not d0_path.is_file():
        result["decision"] = "wsta89-blocked-d0-summary-missing"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    d0 = load_json(d0_path)
    if d0.get("decision") != "server-distro-d0-device-live-read-only-inventory-pass":
        result["decision"] = "wsta89-blocked-d0-summary-not-pass"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    debian_path = resolve_path(args.debian_eye_public_summary_json) if args.debian_eye_public_summary_json else None
    debian_eye = load_json(debian_path) if debian_path and debian_path.is_file() else None
    if debian_path and debian_eye and debian_eye.get("decision") != "debian-eye-hardware-inventory-live-pass":
        result["decision"] = "wsta89-blocked-debian-eye-summary-not-pass"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    audit = build_audit(d0_path, d0, debian_path, debian_eye)
    result["audit"] = audit
    result["checks"] = {
        "d0_summary_pass": True,
        "debian_eye_summary_pass": debian_eye is not None,
        "seccomp_filter_available": any(
            item["name"] == "seccomp-bpf-per-service" and item["status"] == "ready-for-profile-source"
            for item in audit["controls"]
        ),
        "default_public_off": True,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    result["decision"] = PASS_DECISION
    result["gate_decision"] = "ok"

    md_text = markdown(audit)
    findings = redaction_findings(public_summary(result)) + redaction_findings({"markdown": md_text})
    if findings:
        result["decision"] = "wsta89-blocked-redaction-finding"
        result["gate_decision"] = result["decision"]
        result["gate_detail"] = {"findings": sorted(set(findings))}
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    result["ended_utc"] = utc_stamp()
    write_json(out_json, result)
    write_text(out_md, md_text)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--audit-hardening-readiness", action="store_true")
    parser.add_argument("--d0-public-summary-json", type=Path, default=DEFAULT_D0_SUMMARY)
    parser.add_argument("--debian-eye-public-summary-json", type=Path, default=DEFAULT_DEBIAN_EYE_SUMMARY)
    parser.add_argument("--print-template", action="store_true")
    parser.add_argument("--print-full-json", action="store_true")
    return parser


def main_with_args(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.print_template:
        print(json.dumps(template(), indent=2, sort_keys=True))
        return 0
    try:
        result = run(args)
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "wsta89-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
