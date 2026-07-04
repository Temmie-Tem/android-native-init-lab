#!/usr/bin/env python3
"""WSTA90 host-only D-public service hardening manifest skeleton.

Consumes the WSTA89 readiness audit and emits the first structured service
hardening contract: target user, capabilities, no-new-privs, network intent,
seccomp profile class, and proof gaps for the D-public services.  This is a
source/planning artifact only; it does not enforce seccomp/caps yet.
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

import run_wsta89_hardening_readiness_audit as wsta89  # noqa: E402


REPO_ROOT = wsta89.REPO_ROOT
PRIVATE_ROOT = wsta89.PRIVATE_ROOT
DEFAULT_RUN_BASE = wsta89.DEFAULT_RUN_BASE
DEFAULT_WSTA89_AUDIT = REPO_ROOT / "workspace/private/runs/server-distro/wsta89-hardening-readiness-audit-20260704T130000Z/wsta89_hardening_readiness.json"
PASS_DECISION = "wsta90-service-hardening-manifest-source-pass"


def rel(path: Path) -> str:
    return wsta89.rel(path)


def utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def is_under(path: Path, root: Path) -> bool:
    return wsta89.is_under(path, root)


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
        "scope": "WSTA90 host-only service hardening manifest skeleton",
        "default_mode": "host-only-source-manifest",
        "command": [
            "python3",
            rel(Path(__file__).resolve()),
            "--emit-service-hardening-manifest",
            "--wsta89-hardening-readiness-json",
            rel(DEFAULT_WSTA89_AUDIT),
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
        "manifest": result.get("manifest", {}),
        "checks": result.get("checks", {}),
        "safety": result.get("safety", {}),
    }


def redaction_findings(payload: Any) -> list[str]:
    return wsta89.redaction_findings(payload)


def readiness_controls(audit_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    audit = audit_result.get("audit") or {}
    controls = audit.get("controls") or []
    return {
        str(item.get("name")): item
        for item in controls
        if isinstance(item, dict) and item.get("name")
    }


def service(name: str,
            binary: str,
            user: str,
            network: str,
            seccomp_profile: str,
            allowed_caps: list[str],
            proof_gaps: list[str],
            *,
            status: str = "manifest-skeleton") -> dict[str, Any]:
    return {
        "name": name,
        "binary": binary,
        "target_user": user,
        "target_group": user,
        "no_new_privs": True,
        "ambient_capabilities": allowed_caps,
        "bounding_capabilities": allowed_caps,
        "network_intent": network,
        "seccomp_profile": seccomp_profile,
        "status": status,
        "proof_gaps": proof_gaps,
    }


def build_manifest(readiness_path: Path, readiness: dict[str, Any]) -> dict[str, Any]:
    controls = readiness_controls(readiness)
    seccomp = controls.get("seccomp-bpf-per-service", {})
    cap_drop = controls.get("capability-drop-nonroot-services", {})
    packet_filter = controls.get("packet-filter-default-drop", {})
    services = [
        service(
            "dpublic-smoke-httpd",
            "/usr/local/bin/a90-dpublic-smoke-httpd",
            "a90www",
            "bind-loopback-127.0.0.1:8080-only",
            "smoke-httpd-loopback-minimal",
            [],
            [
                "trace exact libc/kernel syscall set before enforcement",
                "create non-root a90www user/group in appliance rootfs",
                "prove loopback bind still works with no ambient capabilities",
            ],
        ),
        service(
            "cloudflared-quick-tunnel",
            "/usr/local/bin/cloudflared",
            "a90tunnel",
            "outbound-only-plus-loopback-origin",
            "cloudflared-network-client",
            [],
            [
                "trace DNS/TLS/connect syscall set before enforcement",
                "confirm no inbound listen except loopback metrics",
                "choose packet-filter backend before always-on mode",
            ],
        ),
        service(
            "dropbear-admin-usb",
            "/usr/sbin/dropbear",
            "a90admin",
            "usb-ncm-admin-only-192.168.7.2:2222",
            "dropbear-admin-keyonly",
            [],
            [
                "replace root authorized_keys model with admin user policy",
                "prove key-only login under non-root/cap-dropped setup or explicitly justify root",
                "keep service bound to USB/NCM admin path, not public tunnel",
            ],
            status="needs-user-model",
        ),
        service(
            "dpublic-hud",
            "/usr/local/bin/a90-dpublic-hud",
            "a90hud",
            "no-network-drm-output-only",
            "hud-drm-minimal",
            [],
            [
                "define /dev/dri/card0 ownership/group policy",
                "trace DRM ioctl set before seccomp enforcement",
                "prove HUD can run without broader root privileges",
            ],
            status="needs-device-node-policy",
        ),
        service(
            "wsta-native-uplink-helper",
            "/usr/local/bin/a90-dpublic-native-uplink-profile",
            "root-native-boundary",
            "native-owned-wifi-control-only",
            "native-uplink-boundary",
            [],
            [
                "keep credential handling in native-owned service boundary",
                "do not expose raw SSID/PSK in manifest or public logs",
                "decide whether this stays root-only helper or moves behind a narrower IPC",
            ],
            status="boundary-preserve",
        ),
    ]
    return {
        "state": "SERVICE_HARDENING_MANIFEST_SKELETON",
        "wsta89_hardening_readiness": rel(readiness_path),
        "services": services,
        "global_policy": {
            "default_public_off": True,
            "no_new_privs_default": True,
            "ambient_capabilities_default": [],
            "capability_drop_required": cap_drop.get("status") == "needs-service-manifest",
            "seccomp_ready_for_profile_source": seccomp.get("status") == "ready-for-profile-source",
            "packet_filter_backend_required": packet_filter.get("status") == "needs-netfilter-inventory",
            "root_login_policy": "replace-root-authorized-keys-before-always-on",
        },
        "blocking_before_enforcement": [
            "non-root users/groups not staged",
            "syscall traces not captured",
            "packet-filter backend not inventoried",
            "dropbear admin user model not finalized",
        ],
        "recommended_next_units": [
            "WSTA91 read-only live: netfilter/iptables/nftables inventory",
            "WSTA92 source: rootfs user/group and no-new-privs launcher plan",
            "WSTA93 live/source: trace smoke-httpd syscall set under loopback-only load",
        ],
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }


def markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# WSTA Service Hardening Manifest",
        "",
        f"- State: `{manifest.get('state')}`",
        f"- WSTA89 readiness: `{manifest.get('wsta89_hardening_readiness')}`",
        "- Device action: `false`",
        "- Default public state: `PUBLIC_OFF`",
        "",
        "## Services",
        "",
        "| Service | User | Network | Seccomp profile | Status | Caps |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in manifest.get("services", []):
        lines.append(
            "| `{name}` | `{user}` | `{network}` | `{profile}` | `{status}` | `{caps}` |".format(
                name=item.get("name"),
                user=item.get("target_user"),
                network=item.get("network_intent"),
                profile=item.get("seccomp_profile"),
                status=item.get("status"),
                caps=",".join(item.get("ambient_capabilities") or []) or "none",
            )
        )
    lines.extend(["", "## Blocking Before Enforcement", ""])
    for item in manifest.get("blocking_before_enforcement", []):
        lines.append(f"- {item}")
    lines.extend(["", "## Recommended Next Units", ""])
    for item in manifest.get("recommended_next_units", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def run(args: argparse.Namespace) -> dict[str, Any]:
    ts = utc_stamp()
    run_id = args.run_id or f"wsta90-service-hardening-manifest-{ts}"
    run_dir = resolve_path(args.run_dir or (DEFAULT_RUN_BASE / run_id))
    result: dict[str, Any] = {
        "scope": "WSTA90 host-only service hardening manifest skeleton",
        "started_utc": ts,
        "run_dir": rel(run_dir),
        "decision": "wsta90-blocked",
        "gate_decision": "not-run",
        "safety": safety_flags(),
    }
    if not is_under(run_dir, PRIVATE_ROOT):
        result["decision"] = "wsta90-blocked-nonprivate-run-dir"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        return result
    run_dir.mkdir(parents=True, exist_ok=True)
    out_json = run_dir / "wsta90_service_hardening_manifest.json"
    out_md = run_dir / "wsta90_service_hardening_manifest.md"

    if not args.emit_service_hardening_manifest:
        result["decision"] = "wsta90-blocked-emit-service-hardening-manifest-required"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    readiness_path = resolve_path(args.wsta89_hardening_readiness_json)
    if not readiness_path.is_file():
        result["decision"] = "wsta90-blocked-wsta89-readiness-missing"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    readiness = load_json(readiness_path)
    if readiness.get("decision") != wsta89.PASS_DECISION:
        result["decision"] = "wsta90-blocked-wsta89-readiness-not-pass"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result
    controls = readiness_controls(readiness)
    if controls.get("seccomp-bpf-per-service", {}).get("status") != "ready-for-profile-source":
        result["decision"] = "wsta90-blocked-seccomp-not-ready"
        result["gate_decision"] = result["decision"]
        result["ended_utc"] = utc_stamp()
        write_json(out_json, result)
        return result

    manifest = build_manifest(readiness_path, readiness)
    result["manifest"] = manifest
    result["checks"] = {
        "wsta89_readiness_pass": True,
        "seccomp_ready_for_profile_source": manifest["global_policy"]["seccomp_ready_for_profile_source"],
        "service_count": len(manifest["services"]),
        "all_services_no_new_privs": all(bool(item.get("no_new_privs")) for item in manifest["services"]),
        "all_services_drop_ambient_caps": all(item.get("ambient_capabilities") == [] for item in manifest["services"]),
        "default_public_off": True,
        "public_url_value_logged": False,
        "secret_values_logged": 0,
    }
    result["decision"] = PASS_DECISION
    result["gate_decision"] = "ok"

    md_text = markdown(manifest)
    findings = redaction_findings(public_summary(result)) + redaction_findings({"markdown": md_text})
    if findings:
        result["decision"] = "wsta90-blocked-redaction-finding"
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
    parser.add_argument("--emit-service-hardening-manifest", action="store_true")
    parser.add_argument("--wsta89-hardening-readiness-json", type=Path, default=DEFAULT_WSTA89_AUDIT)
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
        payload = {"decision": "wsta90-runner-error", "error": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    payload = result if args.print_full_json else public_summary(result)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.get("decision") == PASS_DECISION else 2


def main() -> int:
    return main_with_args()


if __name__ == "__main__":
    raise SystemExit(main())
