#!/usr/bin/env python3
"""V885 host-only ESOC_REQ_IMG response contract classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v885-esoc-req-img-response-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v885-esoc-req-img-response-classifier.txt")
DEFAULT_V884_MANIFEST = Path("tmp/wifi/v884-esoc-req-registered-subsys-hold-live/manifest.json")
UAPI = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel/include/uapi/linux/esoc_ctrl.h")
ESOC_DEV = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc_dev.c")
ESOC_PON = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc-mdm-pon.c")
ESOC_MDM4X = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc-mdm-4x.c")
ESOC_DBG = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc/esoc-mdm-dbg-eng.c")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v884-manifest", type=Path, default=DEFAULT_V884_MANIFEST)
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
        "result": keys.get("result", ""),
        "observer_rc": observer.get("ioctl_rc", ""),
        "observer_errno": observer.get("ioctl_errno", ""),
        "observer_value": observer.get("ioctl_value", ""),
        "observer_elapsed_ms": observer.get("elapsed_ms", ""),
        "forbidden_true": helper.get("forbidden_true") or {},
    }


def classify_sources() -> dict[str, Any]:
    uapi = read_text(UAPI)
    esoc_dev = read_text(ESOC_DEV)
    esoc_pon = read_text(ESOC_PON)
    esoc_mdm4x = read_text(ESOC_MDM4X)
    esoc_dbg = read_text(ESOC_DBG)
    return {
        "uapi": {
            "path": str(UAPI),
            "wait_for_req": line_of(uapi, r"#define\s+ESOC_WAIT_FOR_REQ\b"),
            "notify": line_of(uapi, r"#define\s+ESOC_NOTIFY\b"),
            "reg_req_eng": line_of(uapi, r"#define\s+ESOC_REG_REQ_ENG\b"),
            "img_xfer_done": line_of(uapi, r"\bESOC_IMG_XFER_DONE\b"),
            "boot_done": line_of(uapi, r"\bESOC_BOOT_DONE\b"),
            "req_img": line_of(uapi, r"\bESOC_REQ_IMG\s*=\s*1\b"),
        },
        "esoc_dev": {
            "path": str(ESOC_DEV),
            "reg_req_case": line_of(esoc_dev, r"case\s+ESOC_REG_REQ_ENG"),
            "wait_for_req_case": line_of(esoc_dev, r"case\s+ESOC_WAIT_FOR_REQ"),
            "kfifo_out": line_of(esoc_dev, r"kfifo_out_spinlocked"),
            "put_user_req": line_of(esoc_dev, r"put_user\(req"),
            "wait_for_req_return_err": line_after(
                esoc_dev,
                r"case\s+ESOC_WAIT_FOR_REQ",
                r"return\s+err;",
            ),
            "notify_case": line_of(esoc_dev, r"case\s+ESOC_NOTIFY"),
        },
        "esoc_pon": {
            "path": str(ESOC_PON),
            "sdx50m_req_img": line_of(esoc_pon, r"Queueing the request: ESOC_REQ_IMG"),
            "queue_req_img": line_of(esoc_pon, r"esoc_clink_queue_request\(ESOC_REQ_IMG"),
        },
        "esoc_mdm4x": {
            "path": str(ESOC_MDM4X),
            "notify_fn": line_of(esoc_mdm4x, r"static void mdm_notify"),
            "img_xfer_done_case": line_of(esoc_mdm4x, r"case\s+ESOC_IMG_XFER_DONE"),
            "boot_done_case": line_of(esoc_mdm4x, r"case\s+ESOC_BOOT_DONE"),
            "run_state_notify": line_of(esoc_mdm4x, r"esoc_clink_evt_notify\(ESOC_RUN_STATE"),
            "pblrdy_queue_req_img": line_of(esoc_mdm4x, r"esoc_clink_queue_request\(ESOC_REQ_IMG"),
        },
        "esoc_dbg": {
            "path": str(ESOC_DBG),
            "xfer_done_mapping": line_of(esoc_dbg, r"\.str\s*=\s*\"XFER_DONE\""),
            "boot_done_mapping": line_of(esoc_dbg, r"\.str\s*=\s*\"BOOT_DONE\""),
            "req_img_mapping": line_of(esoc_dbg, r"\.str\s*=\s*\"REQ_IMG\""),
        },
    }


def decide(v884: dict[str, Any], sources: dict[str, Any]) -> tuple[str, bool, str, str]:
    if not v884:
        return "v885-v884-evidence-missing", False, "V884 manifest missing", "restore or rerun V884 evidence before classifier"
    if v884.get("forbidden_true"):
        return "v885-v884-forbidden-action-review", False, f"forbidden={v884.get('forbidden_true')}", "audit V884 before response planning"
    req_observed = (
        v884.get("reg_req_eng_rc") == "0"
        and v884.get("observer_errno") == "0"
        and v884.get("observer_rc") == "4"
        and v884.get("observer_value") == "1"
    )
    required_source = all(
        sources.get(section, {}).get(key)
        for section, key in (
            ("uapi", "req_img"),
            ("esoc_dev", "wait_for_req_case"),
            ("esoc_dev", "kfifo_out"),
            ("esoc_dev", "put_user_req"),
            ("esoc_mdm4x", "img_xfer_done_case"),
            ("esoc_mdm4x", "boot_done_case"),
            ("esoc_dbg", "xfer_done_mapping"),
            ("esoc_dbg", "boot_done_mapping"),
        )
    )
    if req_observed and required_source:
        return (
            "v885-esoc-req-img-response-contract-classified",
            True,
            "V884 observed ESOC_REQ_IMG and local OSRC exposes IMG_XFER_DONE/BOOT_DONE response hooks",
            "build V886 helper v140 source-only semantic repair plus guarded response-mode scaffold",
        )
    return "v885-esoc-req-img-response-contract-incomplete", False, f"v884={v884} sources={sources}", "fill missing source/evidence before live response work"


def render_summary(manifest: dict[str, Any]) -> str:
    source_rows: list[list[Any]] = []
    for section, payload in (manifest.get("sources") or {}).items():
        for key, value in payload.items():
            if key != "path":
                source_rows.append([section, key, value, payload.get("path", "")])
    v884_rows = [[key, value] for key, value in (manifest.get("v884") or {}).items()]
    return "\n".join([
        "# V885 ESOC_REQ_IMG Response Contract Classifier",
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
        "## V884 Evidence",
        "",
        markdown_table(["field", "value"], v884_rows),
        "",
        "## Source Anchors",
        "",
        markdown_table(["section", "anchor", "line", "path"], source_rows),
        "",
        "## Interpretation",
        "",
        "- `ESOC_WAIT_FOR_REQ rc=4 errno=0 value=1` is `ESOC_REQ_IMG`, not an ioctl failure.",
        "- The missing piece is Android-equivalent response handling, not another blind subsystem-open retry.",
        "- Do not issue `ESOC_NOTIFY` live until helper semantics and cleanup gates are repaired in a source/build-only cycle.",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v884 = extract_v884(load_json(args.v884_manifest))
    sources = classify_sources()
    decision, pass_ok, reason, next_step = decide(v884, sources)
    manifest = {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v884_manifest": str(args.v884_manifest),
        "v884": v884,
        "sources": sources,
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
