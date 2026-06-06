#!/usr/bin/env python3
"""V893 host-only classifier for post-ESOC_IMG_XFER_DONE not-ready state."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v893-esoc-post-img-xfer-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v893-esoc-post-img-xfer-classifier.txt")
DEFAULT_V891_MANIFEST = Path("tmp/wifi/v891-esoc-conditional-response-live-v142/manifest.json")
SOURCE_ROOT = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source")
UAPI = SOURCE_ROOT / "include/uapi/linux/esoc_ctrl.h"
ESOC_DEV = SOURCE_ROOT / "drivers/esoc/esoc_dev.c"
MDM_PON = SOURCE_ROOT / "drivers/esoc/esoc-mdm-pon.c"
MDM_4X = SOURCE_ROOT / "drivers/esoc/esoc-mdm-4x.c"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v891-manifest", type=Path, default=DEFAULT_V891_MANIFEST)
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


def line_hits(path: Path, patterns: dict[str, str]) -> dict[str, dict[str, Any]]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {name: {"present": False, "path": str(path), "line": 0, "text": ""} for name in patterns}
    lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
    hits: dict[str, dict[str, Any]] = {}
    for name, pattern in patterns.items():
        regex = re.compile(pattern)
        found = {"present": False, "path": str(path), "line": 0, "text": ""}
        for index, line in enumerate(lines, start=1):
            if regex.search(line):
                found = {"present": True, "path": str(path), "line": index, "text": line.strip()}
                break
        hits[name] = found
    return hits


def extract_v891(manifest: dict[str, Any]) -> dict[str, Any]:
    analysis = manifest.get("analysis") or {}
    helper = analysis.get("helper") or {}
    conditional = helper.get("conditional") or {}
    outer = helper.get("outer") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": manifest.get("pass", False),
        "img_xfer_sent": conditional.get("img_xfer_sent", ""),
        "status_ready": conditional.get("status_ready", ""),
        "status_last_value": conditional.get("status_last_value", ""),
        "status_poll_count": conditional.get("status_poll_count", ""),
        "boot_done_sent": conditional.get("boot_done_sent", ""),
        "request_observed": conditional.get("request_observed", ""),
        "wait_request_name": conditional.get("wait_request_name", ""),
        "outer_result": outer.get("result", ""),
        "cleanup_healthy": (analysis.get("reboot_cleanup") or {}).get("healthy", False),
    }


def collect_sources() -> dict[str, Any]:
    return {
        "uapi": line_hits(UAPI, {
            "img_xfer_done": r"\bESOC_IMG_XFER_DONE\s*=\s*1\b",
            "boot_done": r"\bESOC_BOOT_DONE\b",
            "req_img": r"\bESOC_REQ_IMG\s*=\s*1\b",
            "get_status": r"#define\s+ESOC_GET_STATUS\b",
        }),
        "esoc_dev": line_hits(ESOC_DEV, {
            "wait_for_req_fifo": r"kfifo_out_spinlocked.*req_fifo",
            "notify_calls_clink": r"clink_ops->notify",
            "get_status_calls_clink": r"clink_ops->get_status",
        }),
        "mdm_pon": line_hits(MDM_PON, {
            "queue_req_img": r"Queueing the request: ESOC_REQ_IMG",
            "let_userspace_confirm": r"Let userspace confirm establishment",
            "ap2mdm_status_high": r"Setting AP2MDM_STATUS = 1",
        }),
        "mdm_4x": line_hits(MDM_4X, {
            "img_xfer_done_case": r"case\s+ESOC_IMG_XFER_DONE",
            "schedules_status_check": r"schedule_delayed_work.*mdm2ap_status_check_work",
            "boot_done_sends_run_state": r"ESOC_BOOT_DONE: Sending the notification: ESOC_RUN_STATE",
            "status_irq": r"MDM2AP_STATUS IRQ received",
            "status_value_one": r"value\s*==\s*1",
            "mdm_ready_true": r"mdm->ready\s*=\s*true",
        }),
    }


def decide(v891: dict[str, Any], sources: dict[str, Any]) -> tuple[str, bool, str, str, dict[str, Any]]:
    source_ok = all(
        hit.get("present")
        for group in sources.values()
        for hit in group.values()
    )
    v891_ok = (
        v891.get("img_xfer_sent") == "1"
        and v891.get("status_ready") == "0"
        and v891.get("status_last_value") == "0"
        and v891.get("boot_done_sent") == "0"
        and bool(v891.get("cleanup_healthy"))
    )
    classification = {
        "img_xfer_done_effect": "schedules MDM2AP_STATUS readiness wait/check; it does not directly set ready",
        "get_status_zero_meaning": "MDM2AP_STATUS/ready did not transition to ready in the bounded window",
        "boot_done_policy": "remain blocked until readiness is proven; blind BOOT_DONE would only synthesize RUN_STATE",
        "next_gate": "observe MDM2AP_STATUS/ready transition source after IMG_XFER_DONE; do not start actors or HAL yet",
    }
    if not v891_ok:
        return "v893-v891-evidence-incomplete", False, f"v891={v891}", "restore or rerun V891 evidence before classifier", classification
    if not source_ok:
        return "v893-source-evidence-incomplete", False, "required ESOC source markers missing", "restore staged ESOC source before classifier", classification
    return (
        "v893-post-img-xfer-status-line-classified",
        True,
        "IMG_XFER_DONE succeeded but source shows readiness still depends on MDM2AP_STATUS/ready transition",
        "plan a bounded read-only/live observer for MDM2AP_STATUS readiness after image-done",
        classification,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    source_rows: list[list[Any]] = []
    for group, hits in (manifest.get("sources") or {}).items():
        for name, hit in hits.items():
            source_rows.append([group, name, hit.get("present"), hit.get("path"), hit.get("line")])
    class_rows = [[key, value] for key, value in (manifest.get("classification") or {}).items()]
    return "\n".join([
        "# V893 eSoC Post Image-done Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- live_device_action: `{manifest['live_device_action']}`",
        "",
        "## V891 Evidence",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in manifest.get("v891", {}).items()]),
        "",
        "## Classification",
        "",
        markdown_table(["field", "value"], class_rows),
        "",
        "## Source Markers",
        "",
        markdown_table(["group", "marker", "present", "path", "line"], source_rows),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v891 = extract_v891(load_json(args.v891_manifest))
    sources = collect_sources()
    decision, pass_ok, reason, next_step, classification = decide(v891, sources)
    manifest = {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v891_manifest": str(args.v891_manifest),
        "v891": v891,
        "sources": sources,
        "classification": classification,
        "live_device_action": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"next: {next_step}")
    print(f"live_device_action: {manifest['live_device_action']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
