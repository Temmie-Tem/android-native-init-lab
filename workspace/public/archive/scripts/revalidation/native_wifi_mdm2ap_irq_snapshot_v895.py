#!/usr/bin/env python3
"""V895 bounded MDM2AP IRQ snapshot proof around guarded image-done."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import native_wifi_esoc_conditional_response_v891 as base


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v895-mdm2ap-irq-snapshot-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v895-mdm2ap-irq-snapshot-live.txt")
base.DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v895-execns-helper-v143-build/a90_android_execns_probe")
base.DEFAULT_HELPER_SHA256 = "994959b2f70339c25f37d836803c12e9fda10f577cdd3b7452a883efa42f6bc4"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v143"
base.DEFAULT_MARKER = "/tmp/a90-v895-mdm2ap-irq-snapshot.created"


IRQ_PREFIX = f"{base.COND_PREFIX}.irq_snapshot"


def _to_int(value: str | None, default: int = -1) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


def _load_helper_payload(store: base.EvidenceStore, manifest: dict[str, Any]) -> str:
    for step in manifest.get("steps", []):
        if step.get("name") != "esoc-conditional-response":
            continue
        rel = str(step.get("file") or "")
        path = store.run_dir / rel
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def _irq_snapshot_analysis(keys: dict[str, str]) -> dict[str, Any]:
    phases: dict[str, dict[str, str]] = {}
    prefix = IRQ_PREFIX + "."
    for key, value in keys.items():
        if not key.startswith(prefix):
            continue
        remainder = key[len(prefix):]
        if "." not in remainder:
            continue
        phase, field = remainder.split(".", 1)
        phases.setdefault(phase, {})[field] = value
    count_by_phase = {
        phase: _to_int(values.get("mdm_status_count_total"))
        for phase, values in phases.items()
        if values.get("mdm_status_count_total") is not None
    }
    parsed_phases = [
        phase for phase, values in phases.items()
        if values.get("mdm_status_irq_present") == "1"
        and values.get("mdm_status_irq_parsed") == "1"
        and values.get("mdm_status_gpio") == "142"
    ]
    before = count_by_phase.get("before_img_xfer", -1)
    after = count_by_phase.get("after_img_xfer", before)
    max_count = max(count_by_phase.values()) if count_by_phase else -1
    delta_total = max_count - before if before >= 0 and max_count >= 0 else -1
    poll_phases = sorted(
        phase for phase in phases
        if re.fullmatch(r"poll_\d+", phase)
    )
    return {
        "phase_count": len(phases),
        "parsed_phase_count": len(parsed_phases),
        "parsed_phases": parsed_phases[:16],
        "poll_phase_count": len(poll_phases),
        "before_img_xfer_count": before,
        "after_img_xfer_count": after,
        "max_count": max_count,
        "delta_total": delta_total,
        "irq_fired": delta_total > 0,
        "all_parsed_gpio142": bool(phases) and len(parsed_phases) == len(phases),
        "counts_by_phase_sample": {phase: count_by_phase[phase] for phase in sorted(count_by_phase)[:12]},
    }


def _decide_v895(manifest: dict[str, Any], irq: dict[str, Any]) -> tuple[str, bool, str, str]:
    base_decision = str(manifest.get("decision") or "")
    base_pass = bool(manifest.get("pass"))
    if manifest.get("command") == "plan":
        return "v895-mdm2ap-irq-snapshot-plan-ready", base_pass, f"base_decision={base_decision}", "build/deploy helper v143, then run bounded V895 live proof"
    if not base_pass:
        return "v895-base-proof-blocked", False, f"base_decision={base_decision}", "resolve base conditional response blocker before V895"
    if irq.get("phase_count", 0) < 3 or not irq.get("all_parsed_gpio142"):
        return "v895-irq-snapshot-incomplete", False, f"irq={irq}", "repair helper IRQ snapshot parser before retry"
    conditional = ((manifest.get("analysis") or {}).get("helper") or {}).get("conditional") or {}
    if conditional.get("img_xfer_sent") != "1":
        return "v895-img-xfer-not-sent", False, f"conditional={conditional}", "inspect ESOC_NOTIFY path before IRQ classification"
    if conditional.get("boot_done_sent") == "1":
        return "v895-mdm-status-ready-boot-done-sent", True, f"irq={irq}", "inspect WLFW/service69/wlan0 deltas before actor/HAL work"
    if irq.get("irq_fired"):
        return "v895-mdm-status-irq-fired-status-not-ready-reboot-cleaned", True, f"irq={irq}", "classify kernel ready-state handling after mdm status IRQ"
    return "v895-mdm-status-irq-not-fired-reboot-cleaned", True, f"irq={irq}", "classify why SDX50M does not drive MDM2AP status high"


def render_summary(manifest: dict[str, Any]) -> str:
    base_summary = base.render_summary(manifest)
    irq = manifest.get("v895_irq_snapshot") or {}
    rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in irq.items()]
    return "\n".join([
        base_summary.rstrip(),
        "",
        "## V895 IRQ Snapshot",
        "",
        base.markdown_table(["field", "value"], rows),
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = base.build_manifest(args, store)
    helper_payload = _load_helper_payload(store, manifest)
    keys = base.parse_keys(helper_payload)
    irq = _irq_snapshot_analysis(keys)
    decision, pass_ok, reason, next_step = _decide_v895(manifest, irq)
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "v895_irq_snapshot": irq,
        "helper_marker": base.DEFAULT_HELPER_MARKER,
        "helper_sha256": base.DEFAULT_HELPER_SHA256,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    })
    return manifest


def main() -> int:
    args = base.parse_args()
    store = base.EvidenceStore(base.repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    base.write_private_text(base.repo_path(base.LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"conditional_response_executed: {manifest['conditional_response_executed']}")
    print(f"reg_req_eng_ioctl_executed: {manifest['reg_req_eng_ioctl_executed']}")
    print(f"subsys_esoc0_open_attempted: {manifest['subsys_esoc0_open_attempted']}")
    print(f"esoc_notify_executed: {manifest['esoc_notify_executed']}")
    print(f"cleanup_reboot_executed: {manifest['cleanup_reboot_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
