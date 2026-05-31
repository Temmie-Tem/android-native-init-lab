#!/usr/bin/env python3
"""V1320 host-only mdm_helper/ks/MHI response-contract classifier.

V1319 proved native reaches AP2MDM GPIO135 high but still lacks the response
Android gets: GPIO142, PCIe, MHI, WLFW, and wlan0.  V1320 ties that post-GPIO135
gap to the existing Android mdm_helper/ks/MHI image-link evidence and rejects
another lower GPIO/PMIC/eSoC mutation before that contract is handled.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1320-mdm-helper-ks-mhi-contract-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1320-mdm-helper-ks-mhi-contract-classifier.txt")
DEFAULT_V1319_MANIFEST = Path("tmp/wifi/v1319-gpio135-response-gap-classifier/manifest.json")
DEFAULT_V1318_MANIFEST = Path("tmp/wifi/v1318-critical-lower-trace-collector-live/manifest.json")
DEFAULT_V1229_MANIFEST = Path("tmp/wifi/v1229-esoc-wait-req-ks-mhi-contract/manifest.json")
DEFAULT_V896_MANIFEST = Path("tmp/wifi/v896-android-mdm-helper-image-contract-validate/manifest.json")
DEFAULT_ESOC_RESEARCH = Path("docs/overview/ESOC_PERIPHERAL_MANAGER_BRINGUP_RESEARCH_2026-05-25.md")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1320_MDM_HELPER_KS_MHI_CONTRACT_CLASSIFIER_2026-05-31.md")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1319-manifest", type=Path, default=DEFAULT_V1319_MANIFEST)
    parser.add_argument("--v1318-manifest", type=Path, default=DEFAULT_V1318_MANIFEST)
    parser.add_argument("--v1229-manifest", type=Path, default=DEFAULT_V1229_MANIFEST)
    parser.add_argument("--v896-manifest", type=Path, default=DEFAULT_V896_MANIFEST)
    parser.add_argument("--esoc-research", type=Path, default=DEFAULT_ESOC_RESEARCH)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return False


def int_value(value: Any, fallback: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return fallback


def summarize_v1319(v1319: dict[str, Any]) -> dict[str, Any]:
    native = v1319.get("native_v1318") or {}
    android = v1319.get("android_reference") or {}
    return {
        "decision": v1319.get("decision", ""),
        "pass": bool_value(v1319.get("pass")),
        "gpio135_high_count": int_value(native.get("gpio135_high_count")),
        "gpio142_line_count": int_value(native.get("gpio142_line_count")),
        "post_gpio135_sample_span_sec": float(native.get("post_gpio135_sample_span_sec") or 0.0),
        "native_ks_count_window": int_value(native.get("ks_count_window")),
        "native_mhi_pipe_seen": bool_value(native.get("mhi_pipe_seen")),
        "native_mdm3_states": native.get("mdm3_states") or [],
        "native_service69_seen": bool_value(native.get("service69_seen")),
        "native_wlan0_seen": bool_value(native.get("wlan0_seen")),
        "android_gpio142_irq_count": int_value(android.get("v1239_gpio142_irq_count")),
        "android_pcie_rc1_lines": int_value(android.get("v1239_pcie_rc1_lines")),
        "android_ks_mhi_pipe": bool_value(android.get("v896_ks_mhi_pipe")),
        "android_wlfw_present": bool_value(android.get("v1239_wlfw_present")),
        "android_wlan0_present": bool_value(android.get("v1239_wlan0_present")),
    }


def summarize_v1318(v1318: dict[str, Any]) -> dict[str, Any]:
    parity = v1318.get("mdm_helper_ks_mhi_parity") or {}
    response = v1318.get("response_sampler") or {}
    boundary = v1318.get("post_esoc_boundary") or {}
    return {
        "decision": v1318.get("decision", ""),
        "pass": bool_value(v1318.get("pass")),
        "mdm_helper_esoc_present": bool_value(parity.get("mdm_helper_esoc_present")),
        "mdm_helper_esoc0_count_window": int_value(parity.get("mdm_helper_esoc0_count_window")),
        "ks_count_window": int_value(parity.get("ks_count_window")),
        "mhi_pipe_seen": bool_value(response.get("mhi_pipe_seen")) or int_value(parity.get("mdm_helper_mhi_pipe_count_window")) > 0,
        "pm_service_subsys_esoc0_attempt": bool_value(parity.get("pm_service_subsys_esoc0_attempt")),
        "max_mhi_bus_count": int_value(response.get("max_mhi_bus_count")),
        "max_pci_dev_count": int_value(response.get("max_pci_dev_count")),
        "service69_seen": bool_value(boundary.get("service69_seen")),
        "wlan0_seen": bool_value(boundary.get("wlan0_seen")) or bool_value(response.get("wlan0_seen")),
    }


def summarize_v1229(v1229: dict[str, Any]) -> dict[str, Any]:
    analysis = v1229.get("analysis") or {}
    v1228 = analysis.get("v1228") or {}
    v891 = analysis.get("v891") or {}
    v1199 = analysis.get("v1199") or {}
    v896 = analysis.get("v896") or {}
    classification = analysis.get("classification") or {}
    flags = classification.get("flags") or {}
    return {
        "decision": v1229.get("decision", ""),
        "pass": bool_value(v1229.get("pass")),
        "v1228_natural_wait_req_seen": bool_value(flags.get("v1228_natural_wait_req_seen")) or "ESOC_WAIT_FOR_REQ" in str(v1228),
        "v1228_no_ks_mhi_wlfw_wlan0": bool_value(flags.get("v1228_no_ks_mhi_wlfw_wlan0")) or not bool_value(v1228.get("ks_or_mhi_present")),
        "v891_request_observed": bool_value(v891.get("request_observed")),
        "v891_img_xfer_sent": bool_value(v891.get("img_xfer_sent")),
        "v891_status_last_value": int_value(v891.get("status_last_value")),
        "v1199_img_xfer_alone_no_mhi": bool_value(flags.get("v1199_img_xfer_alone_no_mhi")) or bool_value(v1199.get("mhi_not_appeared")),
        "v896_android_ks_mhi_contract": bool_value(v896.get("android_ks_mhi_contract")),
        "v896_android_wlan0_positive": bool_value(v896.get("android_wlan0_positive")),
        "reference_reports_consistent": bool_value(flags.get("reference_reports_consistent")),
    }


def summarize_v896(v896: dict[str, Any]) -> dict[str, Any]:
    v852 = v896.get("v852") or {}
    flags = v896.get("v853_actor_flags") or {}
    v895 = v896.get("v895") or {}
    classification = v896.get("classification") or {}
    return {
        "decision": v896.get("decision", ""),
        "pass": bool_value(v896.get("pass")),
        "android_mdm3_online": v852.get("mdm3_state") == "ONLINE",
        "android_gpio142_irq_count": int_value((v852.get("irq_mdm_status") or {}).get("count_total")),
        "android_wlan0": bool_value((v852.get("dmesg_hints") or {}).get("has_wlan0")) or bool_value(((v852.get("timeline") or {}).get("wlan0") or {}).get("present")),
        "android_wlfw": bool_value((v852.get("dmesg_hints") or {}).get("has_wlfw")),
        "android_bdf": bool_value((v852.get("dmesg_hints") or {}).get("has_bdf")),
        "has_mdm_helper_esoc_fd": bool_value(flags.get("has_mdm_helper_esoc_fd")),
        "has_ks_esoc_fd": bool_value(flags.get("has_ks_esoc_fd")),
        "has_ks_mhi_pipe": bool_value(flags.get("has_ks_mhi_pipe")),
        "has_per_mgr_subsys_esoc0_fd": bool_value(flags.get("has_per_mgr_subsys_esoc0_fd")),
        "native_v895_img_xfer_sent": bool_value(v895.get("img_xfer_sent")),
        "native_v895_status_last_value": int_value(v895.get("status_last_value")),
        "native_v895_irq_delta_total": int_value(v895.get("irq_delta_total")),
        "source_contract_text": str(classification.get("source_contract", "")),
        "missing_native_contract_text": str(classification.get("missing_native_contract", "")),
    }


def summarize_research(text: str) -> dict[str, Any]:
    return {
        "records_esoc_req_img": "ESOC_REQ_IMG" in text,
        "records_img_xfer_done": "ESOC_IMG_XFER_DONE" in text,
        "records_boot_done_guard": "BOOT_DONE" in text and "blind" in text,
        "records_android_ks_mhi_contract": "ks" in text and "/dev/mhi_0305_01.01.00_pipe_10" in text,
        "records_v896_remaining_gap": "Android `mdm_helper`/`ks` MHI image/link contract" in text,
        "records_v1229_contract": "request/image-link handoff" in text or "ESOC_WAIT_FOR_REQ" in text,
    }


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1319 = summarize_v1319(load_json(args.v1319_manifest))
    v1318 = summarize_v1318(load_json(args.v1318_manifest))
    v1229 = summarize_v1229(load_json(args.v1229_manifest))
    v896 = summarize_v896(load_json(args.v896_manifest))
    research = summarize_research(read_text(args.esoc_research))

    post_gpio135_gap_proven = (
        v1319["pass"]
        and v1319["decision"] == "v1319-gpio135-asserted-mdm2ap-pcie-response-absent"
        and v1319["gpio135_high_count"] >= 1
        and v1319["gpio142_line_count"] == 0
        and v1319["post_gpio135_sample_span_sec"] >= 10.0
        and not v1319["native_mhi_pipe_seen"]
        and not v1319["native_wlan0_seen"]
    )
    android_contract_positive = (
        v896["pass"]
        and v896["android_mdm3_online"]
        and v896["android_gpio142_irq_count"] > 0
        and v896["android_wlan0"]
        and v896["has_mdm_helper_esoc_fd"]
        and v896["has_ks_esoc_fd"]
        and v896["has_ks_mhi_pipe"]
    )
    native_current_missing_contract = (
        v1318["pass"]
        and v1318["mdm_helper_esoc_present"]
        and v1318["pm_service_subsys_esoc0_attempt"]
        and v1318["ks_count_window"] == 0
        and not v1318["mhi_pipe_seen"]
        and v1318["max_mhi_bus_count"] == 0
        and not v1318["wlan0_seen"]
    )
    request_boundary_real = (
        v1229["pass"]
        and v1229["v1228_natural_wait_req_seen"]
        and v1229["v891_request_observed"]
        and v1229["v891_img_xfer_sent"]
    )
    img_xfer_alone_insufficient = (
        v1229["v1199_img_xfer_alone_no_mhi"]
        and v896["native_v895_img_xfer_sent"]
        and v896["native_v895_irq_delta_total"] == 0
        and v896["native_v895_status_last_value"] == 0
    )
    source_contract_consistent = (
        research["records_esoc_req_img"]
        and research["records_img_xfer_done"]
        and research["records_android_ks_mhi_contract"]
        and v1229["reference_reports_consistent"]
    )

    checks = [
        check(
            "post-gpio135-gap-proven",
            post_gpio135_gap_proven,
            f"gpio135={v1319['gpio135_high_count']} gpio142={v1319['gpio142_line_count']} span={v1319['post_gpio135_sample_span_sec']} native_mhi={v1319['native_mhi_pipe_seen']}",
        ),
        check(
            "android-mdm-helper-ks-mhi-positive",
            android_contract_positive,
            f"mdm_helper_fd={v896['has_mdm_helper_esoc_fd']} ks_fd={v896['has_ks_esoc_fd']} ks_mhi={v896['has_ks_mhi_pipe']} gpio142={v896['android_gpio142_irq_count']}",
        ),
        check(
            "native-current-missing-contract",
            native_current_missing_contract,
            f"mdm_helper={v1318['mdm_helper_esoc_present']} pm_esoc0={v1318['pm_service_subsys_esoc0_attempt']} ks={v1318['ks_count_window']} mhi={v1318['mhi_pipe_seen']}",
        ),
        check(
            "esoc-request-boundary-real",
            request_boundary_real,
            f"wait_req={v1229['v1228_natural_wait_req_seen']} req={v1229['v891_request_observed']} img_xfer={v1229['v891_img_xfer_sent']}",
        ),
        check(
            "img-xfer-alone-insufficient",
            img_xfer_alone_insufficient,
            f"v1199_no_mhi={v1229['v1199_img_xfer_alone_no_mhi']} v895_irq_delta={v896['native_v895_irq_delta_total']} status={v896['native_v895_status_last_value']}",
        ),
        check(
            "source-research-contract-consistent",
            source_contract_consistent,
            json.dumps(research, sort_keys=True),
        ),
    ]

    passed = all(item["pass"] for item in checks)
    if passed:
        decision = "v1320-mdm-helper-ks-mhi-contract-selected"
        reason = (
            "post-GPIO135 response is absent in native while Android-positive readiness correlates with "
            "mdm_helper plus ks MHI image-link; ESOC_IMG_XFER_DONE alone is insufficient"
        )
        next_step = (
            "design V1321 as a fail-closed source/build gate for observing or reproducing the Android "
            "mdm_helper/ks/MHI image-link contract before any direct GPIO/PMIC/GDSC/eSoC mutation"
        )
    else:
        decision = "v1320-contract-evidence-incomplete"
        reason = "required post-GPIO135, Android contract, or native negative-control evidence is missing"
        next_step = "refresh the failed evidence source before another live gate"

    return {
        "cycle": "v1320",
        "command": args.command,
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1319_manifest": str(repo_path(args.v1319_manifest)),
            "v1318_manifest": str(repo_path(args.v1318_manifest)),
            "v1229_manifest": str(repo_path(args.v1229_manifest)),
            "v896_manifest": str(repo_path(args.v896_manifest)),
            "esoc_research": str(repo_path(args.esoc_research)),
        },
        "v1319": v1319,
        "v1318": v1318,
        "v1229": v1229,
        "v896": v896,
        "research": research,
        "checks": checks,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "tracefs_write_executed": False,
        "pm_actor_executed": False,
        "live_esoc_ioctl_executed": False,
        "live_esoc_notify_executed": False,
        "pmic_write_executed": False,
        "gpio_line_request_executed": False,
        "direct_esoc_ioctl_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
        "partition_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    v1319 = manifest["v1319"]
    v1318 = manifest["v1318"]
    v1229 = manifest["v1229"]
    v896 = manifest["v896"]
    safety_rows = [[key, manifest.get(key)] for key in (
        "device_commands_executed",
        "tracefs_write_executed",
        "pm_actor_executed",
        "live_esoc_ioctl_executed",
        "live_esoc_notify_executed",
        "pmic_write_executed",
        "gpio_line_request_executed",
        "direct_esoc_ioctl_executed",
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
        "wifi_bringup_executed",
        "flash_executed",
        "partition_write_executed",
    )]
    return "\n".join([
        "# V1320 mdm_helper/ks/MHI Contract Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "pass", "detail"], [[item["name"], item["pass"], item["detail"]] for item in manifest["checks"]]),
        "",
        "## Evidence Matrix",
        "",
        markdown_table(["surface", "native", "Android / reference"], [
            ["post-GPIO135 response", f"GPIO142={v1319['gpio142_line_count']} MHI={v1319['native_mhi_pipe_seen']} wlan0={v1319['native_wlan0_seen']}", f"GPIO142={v1319['android_gpio142_irq_count']} PCIe={v1319['android_pcie_rc1_lines']} wlan0={v1319['android_wlan0_present']}"],
            ["current actor surface", f"mdm_helper={v1318['mdm_helper_esoc_present']} pm_esoc0={v1318['pm_service_subsys_esoc0_attempt']} ks={v1318['ks_count_window']} MHI={v1318['mhi_pipe_seen']}", f"mdm_helper_fd={v896['has_mdm_helper_esoc_fd']} ks_fd={v896['has_ks_esoc_fd']} ks_mhi={v896['has_ks_mhi_pipe']}"],
            ["request boundary", f"wait_req={v1229['v1228_natural_wait_req_seen']} img_xfer_sent={v1229['v891_img_xfer_sent']}", f"Android contract={v1229['v896_android_ks_mhi_contract']}"],
            ["negative control", f"img_xfer_alone_no_mhi={v1229['v1199_img_xfer_alone_no_mhi']}", f"v895_irq_delta={v896['native_v895_irq_delta_total']} status={v896['native_v895_status_last_value']}"],
        ]),
        "",
        "## Safety",
        "",
        markdown_table(["field", "value"], safety_rows),
        "",
    ])


def render_report(manifest: dict[str, Any]) -> str:
    v1319 = manifest["v1319"]
    v1318 = manifest["v1318"]
    v1229 = manifest["v1229"]
    v896 = manifest["v896"]
    return "\n".join([
        "# Native Init V1320 mdm_helper/ks/MHI Contract Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1320`",
        "- Type: host-only classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
        "- Evidence:",
        "  - `tmp/wifi/v1320-mdm-helper-ks-mhi-contract-classifier/manifest.json`",
        "  - `tmp/wifi/v1320-mdm-helper-ks-mhi-contract-classifier/summary.md`",
        "- Script: `scripts/revalidation/native_wifi_mdm_helper_ks_mhi_contract_classifier_v1320.py`",
        "",
        "V1320 links the V1319 post-GPIO135 response gap to the Android",
        "`mdm_helper`/`ks`/MHI image-link contract. Native has `mdm_helper` and",
        "PM-service eSoC trigger visibility, but no `ks`, MHI pipe, GPIO142, WLFW,",
        "or `wlan0`. Android-positive evidence has `mdm_helper`, `ks`,",
        "`/dev/mhi_0305_01.01.00_pipe_10`, GPIO142 IRQ, PCIe RC1, WLFW, and",
        "`wlan0`.",
        "",
        "## Result",
        "",
        markdown_table(["surface", "native", "Android / reference"], [
            ["GPIO135 response", f"GPIO142={v1319['gpio142_line_count']}, MHI={v1319['native_mhi_pipe_seen']}, wlan0={v1319['native_wlan0_seen']}", f"GPIO142={v1319['android_gpio142_irq_count']}, PCIe={v1319['android_pcie_rc1_lines']}, wlan0={v1319['android_wlan0_present']}"],
            ["Actor contract", f"mdm_helper={v1318['mdm_helper_esoc_present']}, ks={v1318['ks_count_window']}, MHI={v1318['mhi_pipe_seen']}", f"mdm_helper_fd={v896['has_mdm_helper_esoc_fd']}, ks_fd={v896['has_ks_esoc_fd']}, ks_mhi={v896['has_ks_mhi_pipe']}"],
            ["REQ/IMG evidence", f"wait_req={v1229['v1228_natural_wait_req_seen']}, img_xfer={v1229['v891_img_xfer_sent']}", f"android_contract={v1229['v896_android_ks_mhi_contract']}"],
            ["Negative control", f"img_xfer_alone_no_mhi={v1229['v1199_img_xfer_alone_no_mhi']}", f"v895_irq_delta={v896['native_v895_irq_delta_total']}, status={v896['native_v895_status_last_value']}"],
        ]),
        "",
        "## Decision",
        "",
        "The next unit should not mutate GPIO/PMIC/GDSC or send blind eSoC",
        "notifications. It should first build a fail-closed V1321 gate that either",
        "observes or reproduces the Android `mdm_helper`/`ks`/MHI image-link",
        "contract with explicit timeout and cleanup.",
        "",
        "## Safety",
        "",
        "Host-only classifier. No device command, tracefs write, PM actor start,",
        "live eSoC ioctl/notify, PMIC write, userspace GPIO line request/hold,",
        "direct eSoC ioctl, Wi-Fi HAL start, scan/connect, credential use,",
        "DHCP/routes, external ping, flash, boot image write, or partition write",
        "occurred.",
        "",
    ])


def print_result(manifest: dict[str, Any]) -> None:
    print(f"decision: {manifest.get('decision')}")
    print(f"pass:     {manifest.get('pass')}")
    print(f"reason:   {manifest.get('reason')}")
    print(f"next:     {manifest.get('next_step')}")
    print(f"native_ks_count:  {manifest['v1318']['ks_count_window']}")
    print(f"native_mhi_pipe:  {manifest['v1318']['mhi_pipe_seen']}")
    print(f"android_ks_mhi:   {manifest['v896']['has_ks_mhi_pipe']}")
    print(f"evidence: {manifest.get('_run_dir')}")


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    manifest["_run_dir"] = str(store.run_dir)
    if args.command == "plan":
        manifest["decision"] = "v1320-mdm-helper-ks-mhi-contract-plan-ready"
        manifest["pass"] = True
        manifest["reason"] = "plan-only; no device command or live action executed"
        manifest["next_step"] = "run V1320 host-only classifier against existing Android/native contract evidence"
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    if args.command == "run":
        write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    print_result(manifest)
    return 0 if manifest.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
