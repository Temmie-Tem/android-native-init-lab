#!/usr/bin/env python3
"""V745 service180-gated mdm_helper start-only proof.

This is the V744-derived retry of V741: start the same lower/CNSS-only stack,
but open the `mdm_helper` gate on the observed service-notifier `180` marker
instead of waiting for service `74`. It remains below service-manager, Wi-Fi
HAL, scan/connect, credentials, DHCP/routes, and external ping.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_mdm_helper_gated_live_v741 as v741
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v745-mdm-helper-service180-live")
DEFAULT_HELPER_SHA256 = "1456974a114240380dce30a855d3571985ae4587ab61366fb3426862ccd59240"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v123"
MODE = "wifi-companion-service180-gated-mdm-helper-start-only"
EXPECTED_ORDER = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service180_gate,mdm_helper"
PROOF_PREFIX = "/tmp/a90-v745-"
LATEST_POINTER = Path("tmp/wifi/latest-v745-mdm-helper-service180-live.txt")


def configure_v741_adapter() -> None:
    v741.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v741.DEFAULT_HELPER_SHA256 = DEFAULT_HELPER_SHA256
    v741.DEFAULT_HELPER_MARKER = DEFAULT_HELPER_MARKER
    v741.MODE = MODE
    v741.EXPECTED_ORDER = EXPECTED_ORDER
    v741.PROOF_PREFIX = PROOF_PREFIX
    v741.LATEST_POINTER = LATEST_POINTER
    v741.configure_observer()


def retag_manifest(manifest: dict[str, object]) -> None:
    manifest["cycle"] = "v745"
    manifest["adapter"] = "native_wifi_mdm_helper_service180_live_v745.py"
    manifest["mode"] = MODE
    manifest["expected_order"] = EXPECTED_ORDER
    decision = str(manifest.get("decision", ""))
    reason = str(manifest.get("reason", ""))
    next_step = str(manifest.get("next_step", ""))
    manifest["decision"] = decision.replace("v741", "v745").replace("service74", "service180")
    manifest["reason"] = reason.replace("service74", "service180")
    manifest["next_step"] = (
        next_step.replace("service74", "service180")
        .replace("V741", "V745")
        .replace("v122", "v123")
        .replace("helper v122", "helper v123")
    )
    for check in manifest.get("checks", []):
        if isinstance(check, dict):
            if check.get("name") == "service74-gate":
                check["name"] = "service180-gate"
            if isinstance(check.get("next_step"), str):
                check["next_step"] = check["next_step"].replace("service74", "service180")


def render_summary(manifest: dict[str, object]) -> str:
    text = v741.render_summary(manifest)
    return (
        text.replace("# V741 Gated MDM Helper Live Proof", "# V745 Service180-gated MDM Helper Live Proof")
        .replace("service74_gate_open", "service180_gate_open")
        .replace("V741", "V745")
        .replace("service74", "service180")
    )


def main() -> int:
    configure_v741_adapter()
    args = v741.parse_args()
    store = EvidenceStore(v741.observer.base.repo_path(args.out_dir))
    store.mkdir("native")
    manifest = v741.build_manifest(args, store)
    retag_manifest(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(v741.observer.base.repo_path(LATEST_POINTER), str(store.run_dir.relative_to(v741.observer.base.repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"mdm_helper_start_executed: {manifest['mdm_helper_start_executed']}")
    print(f"service_manager_start_executed: {manifest['service_manager_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
