#!/usr/bin/env python3
"""V994 host-only route classifier for the V993 SELinux service-window gap."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v994-selinux-route-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v994-selinux-route-classifier.txt")

DEFAULT_V490 = Path("tmp/wifi/v490-run-v52-20260521-082835/manifest.json")
DEFAULT_V491 = Path("tmp/wifi/v491-run-v52-20260521-082856/manifest.json")
DEFAULT_V990 = Path("tmp/wifi/v990-wificond-service-registration-gap/manifest.json")
DEFAULT_V993 = Path("tmp/wifi/v993-android-service-window-live-v168/manifest.json")
DEFAULT_V993_REPORT = Path("docs/reports/NATIVE_INIT_V993_ANDROID_SERVICE_WINDOW_LIVE_V168_2026-05-26.md")
DEFAULT_V993_TRANSCRIPT = Path("tmp/wifi/v993-android-service-window-live-v168/native/mdm-helper-cnss-before-esoc.txt")

SOURCE_REFS = [
    {
        "name": "AOSP servicemanager ServiceManager.cpp",
        "url": "https://android.googlesource.com/platform/frameworks/native/+/refs/heads/main/cmds/servicemanager/ServiceManager.cpp",
        "finding": "addService reaches canAddService before accepting a service.",
    },
    {
        "name": "AOSP servicemanager Access.cpp",
        "url": "https://android.googlesource.com/platform/frameworks/native/+/4257ea6038/cmds/servicemanager/Access.cpp",
        "finding": "canAdd resolves service_contexts and checks service_manager:add with the caller SELinux SID.",
    },
    {
        "name": "AOSP init SELinux",
        "url": "https://android.googlesource.com/platform/system/core/+/refs/heads/main/init/selinux.cpp",
        "finding": "Android init loads policy, restores init context, then execs into the proper SELinux domain.",
    },
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v490", type=Path, default=DEFAULT_V490)
    parser.add_argument("--v491", type=Path, default=DEFAULT_V491)
    parser.add_argument("--v990", type=Path, default=DEFAULT_V990)
    parser.add_argument("--v993", type=Path, default=DEFAULT_V993)
    parser.add_argument("--v993-report", type=Path, default=DEFAULT_V993_REPORT)
    parser.add_argument("--v993-transcript", type=Path, default=DEFAULT_V993_TRANSCRIPT)
    return parser.parse_args()


def read_text(path: Path, limit: int = 2_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    return json.loads(resolved.read_text())


def flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            flat.update(flatten(child, child_prefix))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            flat.update(flatten(child, f"{prefix}[{index}]"))
    else:
        flat[prefix] = value
    return flat


def contains_any(flat: dict[str, Any], needles: list[str]) -> bool:
    haystack = "\n".join(f"{key}={value}" for key, value in flat.items())
    return all(needle in haystack for needle in needles)


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v490 = load_json(args.v490)
    v491 = load_json(args.v491)
    v990 = load_json(args.v990)
    v993 = load_json(args.v993)
    v993_flat = flatten(v993)
    v993_report = read_text(args.v993_report)
    v993_transcript = read_text(args.v993_transcript)

    historical_policy_load_pass = (
        v490.get("decision") == "v490-selinux-policy-load-proof-pass"
        and v490.get("pass") is True
        and v490.get("policy_load_executed") is True
    )
    historical_domain_proof_pass = (
        v491.get("decision") == "v491-post-load-domain-handoff-present"
        and v491.get("pass") is True
    )
    wificond_service_context_present = (
        v990.get("checks", {}).get("service_context_maps_wifinl80211") is True
    )
    wificond_setexec_accepted = (
        v990.get("checks", {}).get("wificond_setexeccon_accepted") is True
        and "wifi_hal_composite_child.wificond.selinux_exec.ok=1" in v993_transcript
    )
    wificond_post_exec_still_kernel = all(
        marker in v993_transcript
        for marker in (
            "capture.exec.attr/current.value=kernel\\x00",
            "capture.crash.attr/current.value=kernel\\x00",
            "wifi_hal_composite_child.wificond.selinux.current=kernel",
        )
    )
    v993_policy_load_absent = not any("policy_load_executed" in key for key in v993_flat)
    service_window_guards_held = all(
        f"android_wifi_service_window.{name}=0" in v993_transcript
        for name in (
            "qcwlanstate_write",
            "iwifi_start",
            "subsys_esoc0_open_attempted",
            "esoc_ioctl_attempted",
            "scan_connect_linkup",
            "credentials",
            "dhcp_routing",
            "external_ping",
        )
    )
    aosp_servicemanager_requires_selinux_add = True
    aosp_init_reexec_model = True

    checks = {
        "historical_policy_load_pass": historical_policy_load_pass,
        "historical_domain_proof_pass": historical_domain_proof_pass,
        "wificond_service_context_present": wificond_service_context_present,
        "wificond_setexec_accepted": wificond_setexec_accepted,
        "wificond_post_exec_still_kernel": wificond_post_exec_still_kernel,
        "v993_policy_load_absent": v993_policy_load_absent,
        "service_window_guards_held": service_window_guards_held,
        "aosp_servicemanager_requires_selinux_add": aosp_servicemanager_requires_selinux_add,
        "aosp_init_reexec_model": aosp_init_reexec_model,
        "v993_report_confirms_runtime_gap": "transition mechanism is changed" in v993_report,
    }

    if not all(checks.values()):
        decision = "v994-selinux-route-evidence-incomplete"
        passed = False
        reason = "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        route = "review-evidence-before-live"
        next_step = "repair or refresh missing V990/V993/V490/V491 evidence before selecting a live route"
    else:
        decision = "v994-current-boot-selinux-refresh-selected"
        passed = True
        reason = (
            "wificond has a valid service context and accepted setexeccon, but V993 did not run a "
            "current-boot policy-load/domain proof and the traced child stayed kernel after exec"
        )
        route = "fresh-current-boot-policy-load-and-domain-proof-before-service-window"
        next_step = (
            "V995 should refresh V401/V490 on the current boot, then prove wificond/servicemanager "
            "post-exec domains without service-manager, HAL, scan/connect, credentials, DHCP, or external ping"
        )

    return {
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "route": route,
        "next_step": next_step,
        "checks": checks,
        "inputs": {
            "v490": str(repo_path(args.v490)),
            "v491": str(repo_path(args.v491)),
            "v990": str(repo_path(args.v990)),
            "v993": str(repo_path(args.v993)),
            "v993_report": str(repo_path(args.v993_report)),
            "v993_transcript": str(repo_path(args.v993_transcript)),
        },
        "source_refs": SOURCE_REFS,
        "device_commands_executed": False,
        "device_mutations": False,
        "policy_load_executed": False,
        "actor_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_linkup": False,
        "credentials_used": False,
        "dhcp_routing": False,
        "external_ping": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[name, "PASS" if ok else "FAIL"] for name, ok in manifest["checks"].items()]
    source_rows = [[item["name"], item["url"], item["finding"]] for item in manifest["source_refs"]]
    input_rows = [[name, path] for name, path in manifest["inputs"].items()]
    return "\n".join(
        [
            "# V994 SELinux Route Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- route: `{manifest['route']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            "## Checks",
            "",
            markdown_table(["check", "result"], check_rows),
            "",
            "## Inputs",
            "",
            markdown_table(["name", "path"], input_rows),
            "",
            "## Source References",
            "",
            markdown_table(["source", "url", "finding"], source_rows),
            "",
            "## Guardrails",
            "",
            "- Host-only classifier.",
            "- No device command, policy load, actor start, service-manager start, Wi-Fi HAL start, scan/connect, credentials, DHCP, route, external ping, boot image write, partition write, firmware mutation, GPIO write, sysfs write, or debugfs write.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    classification = classify(args)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        **classification,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"route: {manifest['route']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
