#!/usr/bin/env python3
"""V928 host-only CNSS binder/lower-publication intersection classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v928-cnss-binder-lower-intersection")
LATEST_POINTER = Path("tmp/wifi/latest-v928-cnss-binder-lower-intersection.txt")
DEFAULT_V927_MANIFEST = Path("tmp/wifi/v927-mdm-helper-cnss-before-esoc-compact-live/manifest.json")
DEFAULT_V927_TRANSCRIPT = Path("tmp/wifi/v927-mdm-helper-cnss-before-esoc-compact-live/native/mdm-helper-cnss-before-esoc.txt")
DEFAULT_V927_DMESG = Path("tmp/wifi/v927-mdm-helper-cnss-before-esoc-compact-live/native/post-dmesg-wifi-esoc-tail.txt")
DEFAULT_V924_MANIFEST = Path("tmp/wifi/v924-cnss-wlfw-precondition-gap/manifest.json")
DEFAULT_V914_MANIFEST = Path("tmp/wifi/v914-v913-android-timeline-reclassifier/manifest.json")
DEFAULT_V600_MANIFEST = Path("tmp/wifi/v600-registry-cnss-matrix/manifest.json")
DEFAULT_V603_MANIFEST = Path("tmp/wifi/v603-qrtr-first-service-manager-live/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v927-manifest", type=Path, default=DEFAULT_V927_MANIFEST)
    parser.add_argument("--v927-transcript", type=Path, default=DEFAULT_V927_TRANSCRIPT)
    parser.add_argument("--v927-dmesg", type=Path, default=DEFAULT_V927_DMESG)
    parser.add_argument("--v924-manifest", type=Path, default=DEFAULT_V924_MANIFEST)
    parser.add_argument("--v914-manifest", type=Path, default=DEFAULT_V914_MANIFEST)
    parser.add_argument("--v600-manifest", type=Path, default=DEFAULT_V600_MANIFEST)
    parser.add_argument("--v603-manifest", type=Path, default=DEFAULT_V603_MANIFEST)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return repo_path(path).read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def count_lines(text: str, pattern: str) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    return sum(1 for line in text.splitlines() if regex.search(line))


def selected_lines(text: str, pattern: str, limit: int = 60) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    rows: list[str] = []
    for line in text.splitlines():
        if regex.search(line):
            rows.append(line.strip()[:220])
            if len(rows) >= limit:
                break
    return rows


def v927_analysis(manifest: dict[str, Any], transcript: str, dmesg: str) -> dict[str, Any]:
    contract = (((manifest.get("analysis") or {}).get("helper") or {}).get("contract") or {})
    helper_execns = (((manifest.get("analysis") or {}).get("helper") or {}).get("execns") or {})
    dmesg_counts = {
        "cnss_daemon_binder_failure": count_lines(dmesg, r"cnss-daemon.*(?:transaction failed|returned -22|ioctl .*40046210)"),
        "cnss_daemon_cld80211": count_lines(dmesg, r"cnss-daemon.*cld80211"),
        "cnss_diag_cld80211": count_lines(dmesg, r"cnss_diag.*cld80211"),
        "wlfw_start": count_lines(dmesg, r"cnss-daemon.*wlfw_start|wlfw_start:\s*Starting"),
        "bdf": count_lines(dmesg, r"BDF file|bdwlan\.bin|regdb\.bin"),
        "wlan0": count_lines(dmesg, r"\bwlan0\b"),
    }
    transcript_counts = {
        "linkerconfig_warning": count_lines(transcript, r"linkerconfig.*(?:missing|not found|warning)"),
        "property_denied": count_lines(transcript, r"Access denied finding property"),
        "dev_kmsg_denied": count_lines(transcript, r"can't create /dev/kmsg"),
        "wlfw_precondition_poll": count_lines(transcript, r"cnss_before_esoc\.wlfw_precondition_poll="),
    }
    namespace = {
        "surface_mode": contract.get("surface_mode"),
        "stdout_truncated": bool(helper_execns.get("stdout_truncated")),
        "linkerconfig_mode": contract.get("runtime_namespace.linkerconfig_mode"),
        "vndk_apex_alias_mode": contract.get("runtime_namespace.vndk_apex_alias_mode"),
        "android_selinux_context_mode": contract.get("runtime_namespace.android_selinux_context_mode"),
        "property_root_present": contract.get("runtime_namespace.property_root_present") == "1",
    }
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "contract_result": contract.get("result"),
        "contract_reason": contract.get("reason"),
        "namespace": namespace,
        "dmesg_counts": dmesg_counts,
        "transcript_counts": transcript_counts,
        "service_manager_start_executed": manifest.get("service_manager_start_executed", False),
        "cnss_daemon_start_executed": manifest.get("cnss_daemon_start_executed", False),
        "mdm_helper_esoc0_fd_seen": contract.get("mdm_helper_esoc0_fd_seen") == "1",
        "wlfw_precondition_observed": manifest.get("wlfw_precondition_observed", False),
        "subsys_esoc0_open_attempted": manifest.get("subsys_esoc0_open_attempted", False),
        "forbidden_clean": not any(
            manifest.get(key)
            for key in (
                "wifi_hal_start_executed",
                "scan_connect_executed",
                "credential_use_executed",
                "dhcp_route_executed",
                "external_ping_executed",
                "wifi_bringup_executed",
            )
        ),
        "selected_binder_lines": selected_lines(dmesg, r"cnss-daemon.*(?:transaction failed|returned -22|ioctl .*40046210)", 20),
    }


def v603_analysis(manifest: dict[str, Any]) -> dict[str, Any]:
    live = manifest.get("live") or {}
    counts = live.get("v603_counts") or {}
    markers = (live.get("markers") or {}).get("counts") or {}
    service_manager = live.get("service_manager") or {}
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "service_manager_start_executed": manifest.get("service_manager_start_executed"),
        "binder_transaction_failed": counts.get("binder_transaction_failed"),
        "service_notifier_180": counts.get("service_notifier_180"),
        "service_notifier_74": counts.get("service_notifier_74"),
        "wlfw_start": counts.get("wlfw_start"),
        "wlan0": counts.get("wlan0"),
        "qrtr_rx": markers.get("qrtr_rx"),
        "qrtr_tx": markers.get("qrtr_tx"),
        "sysmon_qmi": markers.get("sysmon_qmi"),
        "order": service_manager.get("order"),
    }


def decide(v927: dict[str, Any], v603: dict[str, Any]) -> tuple[str, bool, str, str]:
    namespace_repaired = (
        v927["namespace"]["surface_mode"] == "compact"
        and not v927["namespace"]["stdout_truncated"]
        and v927["namespace"]["linkerconfig_mode"] == "copy-real"
        and v927["namespace"]["vndk_apex_alias_mode"] == "v30-to-system-ext-v30"
        and v927["namespace"]["property_root_present"]
    )
    v927_binder_gap = (
        v927["cnss_daemon_start_executed"]
        and v927["dmesg_counts"]["cnss_daemon_cld80211"] > 0
        and v927["dmesg_counts"]["cnss_daemon_binder_failure"] > 0
        and v927["dmesg_counts"]["wlfw_start"] == 0
        and not v927["service_manager_start_executed"]
    )
    v603_ordering_gap = (
        v603["service_manager_start_executed"] is True
        and v603["binder_transaction_failed"] == 0
        and v603["service_notifier_180"] == 0
        and v603["wlfw_start"] == 0
    )
    if namespace_repaired and v927_binder_gap and v603_ordering_gap and v927["forbidden_clean"]:
        return (
            "v928-cnss-binder-lower-publication-intersection-gap",
            True,
            (
                "V927 repairs namespace/truncation and reaches CNSS cld80211, but cnss-daemon repeats binder failure before WLFW; "
                "V603 proves service-manager can clear binder failure but regresses service-notifier 180, so the next blocker is same-window ordering"
            ),
            "plan V929 source/build-only delayed service-manager/CNSS intersection gate using helper v153 compact output; still no HAL, scan/connect, credentials, DHCP, routes, or external ping",
        )
    return (
        "v928-cnss-binder-lower-intersection-review",
        False,
        f"namespace_repaired={namespace_repaired} v927_binder_gap={v927_binder_gap} v603_ordering_gap={v603_ordering_gap}",
        "inspect V927/V603 evidence before planning another live gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v927_manifest = load_json(args.v927_manifest)
    v924_manifest = load_json(args.v924_manifest)
    v914_manifest = load_json(args.v914_manifest)
    v600_manifest = load_json(args.v600_manifest)
    v603_manifest = load_json(args.v603_manifest)
    v927 = v927_analysis(v927_manifest, read_text(args.v927_transcript), read_text(args.v927_dmesg))
    v603 = v603_analysis(v603_manifest)
    decision, pass_ok, reason, next_step = decide(v927, v603)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v927_manifest": str(repo_path(args.v927_manifest)),
            "v927_transcript": str(repo_path(args.v927_transcript)),
            "v927_dmesg": str(repo_path(args.v927_dmesg)),
            "v924_manifest": str(repo_path(args.v924_manifest)),
            "v914_manifest": str(repo_path(args.v914_manifest)),
            "v600_manifest": str(repo_path(args.v600_manifest)),
            "v603_manifest": str(repo_path(args.v603_manifest)),
        },
        "v927": v927,
        "v603": v603,
        "v924_decision": v924_manifest.get("decision"),
        "v914_decision": v914_manifest.get("decision"),
        "v600_decision": v600_manifest.get("decision"),
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    v927 = manifest["v927"]
    v603 = manifest["v603"]
    rows = [
        ["V927 namespace repaired", json.dumps(v927["namespace"], sort_keys=True)],
        ["V927 dmesg counts", json.dumps(v927["dmesg_counts"], sort_keys=True)],
        ["V927 transcript counts", json.dumps(v927["transcript_counts"], sort_keys=True)],
        ["V603 ordering counts", json.dumps(v603, sort_keys=True)],
    ]
    return "\n".join([
        "# V928 CNSS Binder / Lower Publication Intersection Summary",
        "",
        f"decision: `{manifest['decision']}`",
        f"pass: `{manifest['pass']}`",
        f"reason: {manifest['reason']}",
        f"next: {manifest['next_step']}",
        "",
        "## Evidence Matrix",
        "",
        markdown_table(["item", "value"], rows),
        "",
        "## Guardrails",
        "",
        "- host-only classifier",
        "- no device command",
        "- no daemon start",
        "- no service-manager start",
        "- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
