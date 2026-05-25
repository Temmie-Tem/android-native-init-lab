#!/usr/bin/env python3
"""V888 host-only eSoC response gate classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v888-esoc-response-gate-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v888-esoc-response-gate-classifier.txt")
V884_MANIFEST = Path("tmp/wifi/v884-esoc-req-registered-subsys-hold-live/manifest.json")
V887_MANIFEST = Path("tmp/wifi/v887-execns-helper-v140-deploy-preflight-retry1850/manifest.json")
UAPI = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/uapi/linux/esoc_ctrl.h")
ESOC_DEV = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc_dev.c")
ESOC_PON = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc-mdm-pon.c")
ESOC_MDM4X = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc-mdm-4x.c")
ESOC_MDM_DRV = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc-mdm-drv.c")
ESOC_BUS = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc_bus.c")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v884-manifest", type=Path, default=V884_MANIFEST)
    parser.add_argument("--v887-manifest", type=Path, default=V887_MANIFEST)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def line_of(text: str, pattern: str) -> int | None:
    regex = re.compile(pattern)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return None


def line_after(text: str, anchor_pattern: str, target_pattern: str) -> int | None:
    anchor = line_of(text, anchor_pattern)
    if not anchor:
        return None
    regex = re.compile(target_pattern)
    for index, line in enumerate(text.splitlines(), start=1):
        if index > anchor and regex.search(line):
            return index
    return None


def extract_v884(manifest: dict[str, Any]) -> dict[str, Any]:
    helper = ((manifest.get("analysis") or {}).get("helper") or {})
    keys = helper.get("keys") or {}
    observer = helper.get("observer") or {}
    return {
        "decision": manifest.get("decision", ""),
        "reg_req_eng_rc": keys.get("reg_req_eng_rc", ""),
        "subsys_open_attempted": keys.get("subsys_esoc0_open_attempted", ""),
        "postflight_safe": keys.get("all_postflight_safe", ""),
        "observer_rc": observer.get("ioctl_rc", ""),
        "observer_errno": observer.get("ioctl_errno", ""),
        "observer_value": observer.get("ioctl_value", ""),
        "forbidden_true": helper.get("forbidden_true") or {},
    }


def extract_v887(manifest: dict[str, Any]) -> dict[str, Any]:
    deploy = manifest.get("deploy_result") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": manifest.get("pass", False),
        "helper_sha": manifest.get("helper_expected_sha256", ""),
        "device_mutations": manifest.get("device_mutations", ""),
        "daemon_start_executed": manifest.get("daemon_start_executed", ""),
        "wifi_bringup_executed": manifest.get("wifi_bringup_executed", ""),
        "deploy_method": deploy.get("method", ""),
        "deploy_chunks": deploy.get("chunks", ""),
        "deploy_max_line": deploy.get("max_cmdv1_line_bytes", ""),
        "deploy_line_check_ok": deploy.get("line_check_ok", ""),
    }


def classify_sources() -> dict[str, Any]:
    uapi = read_text(UAPI)
    esoc_dev = read_text(ESOC_DEV)
    esoc_pon = read_text(ESOC_PON)
    esoc_mdm4x = read_text(ESOC_MDM4X)
    esoc_mdm_drv = read_text(ESOC_MDM_DRV)
    esoc_bus = read_text(ESOC_BUS)
    return {
        "uapi": {
            "path": str(UAPI),
            "notify_ioctl": line_of(uapi, r"#define\s+ESOC_NOTIFY\b"),
            "get_status_ioctl": line_of(uapi, r"#define\s+ESOC_GET_STATUS\b"),
            "img_xfer_done": line_of(uapi, r"\bESOC_IMG_XFER_DONE\s*=\s*1\b"),
            "boot_done": line_of(uapi, r"\bESOC_BOOT_DONE\b"),
            "req_img": line_of(uapi, r"\bESOC_REQ_IMG\s*=\s*1\b"),
        },
        "esoc_dev": {
            "path": str(ESOC_DEV),
            "wait_for_req_case": line_of(esoc_dev, r"case\s+ESOC_WAIT_FOR_REQ"),
            "notify_case": line_of(esoc_dev, r"case\s+ESOC_NOTIFY"),
            "get_status_case": line_of(esoc_dev, r"case\s+ESOC_GET_STATUS"),
        },
        "esoc_pon": {
            "path": str(ESOC_PON),
            "queue_req_img": line_of(esoc_pon, r"esoc_clink_queue_request\(ESOC_REQ_IMG"),
            "let_userspace_confirm_link": line_of(esoc_pon, r"Let userspace confirm establishment"),
        },
        "esoc_mdm4x": {
            "path": str(ESOC_MDM4X),
            "notify_fn": line_of(esoc_mdm4x, r"static void mdm_notify"),
            "img_xfer_done_case": line_of(esoc_mdm4x, r"case\s+ESOC_IMG_XFER_DONE"),
            "img_xfer_schedules_status_check": line_after(
                esoc_mdm4x,
                r"case\s+ESOC_IMG_XFER_DONE",
                r"mdm2ap_status_check_work",
            ),
            "boot_done_case": line_of(esoc_mdm4x, r"case\s+ESOC_BOOT_DONE"),
            "boot_done_run_state": line_of(esoc_mdm4x, r"esoc_clink_evt_notify\(ESOC_RUN_STATE"),
            "status_irq_ready": line_of(esoc_mdm4x, r"mdm is now ready"),
            "autoboot_boot_done": line_of(esoc_mdm4x, r"notify\(ESOC_BOOT_DONE"),
        },
        "esoc_mdm_drv": {
            "path": str(ESOC_MDM_DRV),
            "req_eng_wait": line_of(esoc_mdm_drv, r"wait_for_completion\(&mdm_drv->req_eng_wait"),
            "pwr_on_cmd": line_of(esoc_mdm_drv, r"cmd_exe\(ESOC_PWR_ON"),
            "wait_pon_done": line_of(esoc_mdm_drv, r"wait_for_completion_timeout\(&mdm_drv->pon_done"),
            "run_state_success": line_of(esoc_mdm_drv, r"ESOC_RUN_STATE: Calling complete with state: PON_SUCCESS"),
        },
        "esoc_bus": {
            "path": str(ESOC_BUS),
            "queue_request_calls_req_eng": line_of(esoc_bus, r"handle_clink_req\(req"),
            "evt_notify_req_eng": line_of(esoc_bus, r"handle_clink_evt\(evt"),
        },
    }


def decide(v884: dict[str, Any], v887: dict[str, Any], sources: dict[str, Any]) -> tuple[str, bool, str, str, dict[str, Any]]:
    req_img_observed = (
        v884.get("reg_req_eng_rc") == "0"
        and v884.get("observer_errno") == "0"
        and v884.get("observer_rc") == "4"
        and v884.get("observer_value") == "1"
        and not v884.get("forbidden_true")
    )
    helper_ready = (
        v887.get("decision") == "execns-helper-v140-deploy-pass"
        and bool(v887.get("pass"))
        and v887.get("wifi_bringup_executed") is False
    )
    source_ready = all(
        sources.get(section, {}).get(key)
        for section, key in (
            ("uapi", "img_xfer_done"),
            ("uapi", "boot_done"),
            ("esoc_dev", "notify_case"),
            ("esoc_dev", "get_status_case"),
            ("esoc_pon", "queue_req_img"),
            ("esoc_mdm4x", "img_xfer_done_case"),
            ("esoc_mdm4x", "boot_done_case"),
            ("esoc_mdm4x", "boot_done_run_state"),
            ("esoc_mdm_drv", "wait_pon_done"),
            ("esoc_mdm_drv", "run_state_success"),
        )
    )
    response_gate = {
        "first_notify": "ESOC_IMG_XFER_DONE",
        "first_notify_value": 1,
        "poll_after_first_notify": "ESOC_GET_STATUS",
        "conditional_second_notify": "ESOC_BOOT_DONE",
        "conditional_second_notify_value": 2,
        "second_notify_condition": "GET_STATUS returns 1 or equivalent mdm2ap-status readiness is observed",
        "forbidden": [
            "blind ESOC_BOOT_DONE before status readiness",
            "direct userspace ESOC_PWR_ON",
            "REG_CMD_ENG/CMD_EXE ownership retry",
            "actor/HAL/scan/connect/DHCP/external ping",
        ],
    }
    if req_img_observed and helper_ready and source_ready:
        return (
            "v888-esoc-response-gate-classified",
            True,
            "source supports IMG_XFER_DONE first, status-gated BOOT_DONE second; blind BOOT_DONE is too wide",
            "build V889 helper v141 source-only conditional response mode",
            response_gate,
        )
    return (
        "v888-esoc-response-gate-incomplete",
        False,
        f"req_img_observed={req_img_observed} helper_ready={helper_ready} source_ready={source_ready}",
        "repair missing evidence before response helper work",
        response_gate,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    source_rows: list[list[Any]] = []
    for section, payload in (manifest.get("sources") or {}).items():
        for key, value in payload.items():
            if key != "path":
                source_rows.append([section, key, value, payload.get("path", "")])
    gate_rows = [[key, value] for key, value in (manifest.get("response_gate") or {}).items()]
    return "\n".join([
        "# V888 eSoC Response Gate Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_contact: `{manifest['device_contact']}`",
        f"- live_ioctl_executed: `{manifest['live_ioctl_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Response Gate",
        "",
        markdown_table(["field", "value"], gate_rows),
        "",
        "## Source Anchors",
        "",
        markdown_table(["section", "anchor", "line", "path"], source_rows),
        "",
        "## Interpretation",
        "",
        "- `ESOC_IMG_XFER_DONE` is the first bounded response to `ESOC_REQ_IMG`.",
        "- `ESOC_BOOT_DONE` emits `ESOC_RUN_STATE`, which completes the powerup wait, so it must be gated by readiness evidence.",
        "- The next helper mode should be source/build-only and fail closed before any live `ESOC_NOTIFY` run.",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v884 = extract_v884(load_json(args.v884_manifest))
    v887 = extract_v887(load_json(args.v887_manifest))
    sources = classify_sources()
    decision, pass_ok, reason, next_step, response_gate = decide(v884, v887, sources)
    manifest = {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v884_manifest": str(args.v884_manifest),
        "v884": v884,
        "v887_manifest": str(args.v887_manifest),
        "v887": v887,
        "sources": sources,
        "response_gate": response_gate,
        "device_contact": False,
        "live_ioctl_executed": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"next: {next_step}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
