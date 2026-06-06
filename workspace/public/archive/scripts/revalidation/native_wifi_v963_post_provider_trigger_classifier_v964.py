#!/usr/bin/env python3
"""V964 host-only classifier for V963 post-provider trigger evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v964-v963-post-provider-trigger-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v964-v963-post-provider-trigger-classifier.txt")
DEFAULT_V963_MANIFEST = Path("tmp/wifi/v963-post-provider-trigger-live/manifest.json")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v963-manifest", type=Path, default=DEFAULT_V963_MANIFEST)
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    return json.loads(text)


def step_file(manifest: dict[str, Any], name: str) -> Path | None:
    for step in manifest.get("steps", []):
        if step.get("name") == name and step.get("file"):
            manifest_path = Path(manifest.get("_manifest_path", ""))
            base = manifest_path.parent if manifest_path else repo_path(".")
            return base / step["file"]
    return None


def extract_block(text: str, begin: str, end: str) -> str:
    pattern = re.compile(re.escape(begin) + r"\n(.*?)\n" + re.escape(end), re.DOTALL)
    match = pattern.search(text)
    return match.group(1) if match else ""


def classify(manifest: dict[str, Any], helper_text: str, dmesg_text: str) -> dict[str, Any]:
    analysis = manifest.get("analysis") or {}
    helper = analysis.get("helper") or {}
    contract = helper.get("contract") or {}
    cleanup = analysis.get("reboot_cleanup") or {}
    stack = extract_block(
        helper_text,
        "A90_EXECNS_CNSS_PROC_cnss_before_esoc_subsys_trigger_child_stack_BEGIN path=/proc/1712/stack name=stack limit=8192",
        "A90_EXECNS_CNSS_PROC_cnss_before_esoc_subsys_trigger_child_stack_END bytes=749 truncated=0",
    )
    if not stack:
        stack = "\n".join(line for line in helper_text.splitlines() if any(
            token in line
            for token in (
                "sdx50m_toggle_soft_reset",
                "mdm4x_do_first_power_on",
                "mdm_subsys_powerup",
                "__subsystem_get",
                "subsys_device_open",
            )
        ))
    wchan = "sdx50m_toggle_soft_reset" if "sdx50m_toggle_soft_reset" in helper_text else ""
    checks = {
        "v963_manifest_present": bool(manifest),
        "v963_helper_v160": manifest.get("helper_marker") == "a90_android_execns_probe v160",
        "post_provider_gate_selected": contract.get("subsys_trigger_gate") == "post-provider-no-wlfw",
        "pm_proxy_matrix_order": contract.get("service_manager_order") == "after-mdm-helper-esoc-fd-with-pm-proxy",
        "provider_stack_started": all(
            contract.get(key) == "1"
            for key in (
                "pm_proxy_start_attempted",
                "mdm_helper_start_attempted",
                "service_manager_started",
                "cnss_diag_start_attempted",
                "cnss_daemon_start_attempted",
            )
        ),
        "gate_ready_observed_once": "cnss_before_esoc.post_provider_no_wlfw_gate_ready=1" in helper_text,
        "wlfw_absent_at_trigger": contract.get("wlfw_precondition_observed") == "0",
        "subsys_open_attempted": contract.get("subsys_esoc0_open_attempted") == "1",
        "trigger_child_stalled": contract.get("subsys_trigger.blocker_capture_attempted") == "1",
        "wchan_sdx50m_soft_reset": wchan == "sdx50m_toggle_soft_reset",
        "stack_shows_mdm_powerup_path": all(
            token in stack
            for token in (
                "sdx50m_toggle_soft_reset",
                "mdm4x_do_first_power_on",
                "mdm_subsys_powerup",
                "__subsystem_get",
                "subsys_device_open",
            )
        ),
        "kernel_logged_subsystem_get": "subsys-restart: __subsystem_get(): __subsystem_get: esoc0 count:0" in dmesg_text,
        "cleanup_reboot_healthy": bool(cleanup.get("healthy")),
        "no_forbidden_actions": not bool(helper.get("forbidden_true")),
        "no_wifi_bringup": all(
            not bool(manifest.get(key))
            for key in (
                "wifi_hal_start_executed",
                "scan_connect_executed",
                "credential_use_executed",
                "dhcp_route_executed",
                "external_ping_executed",
                "wifi_bringup_executed",
            )
        ),
    }
    passed = all(checks.values())
    decision = (
        "v964-post-provider-trigger-stalls-in-sdx50m-reset"
        if passed
        else "v964-post-provider-trigger-classifier-incomplete"
    )
    reason = (
        "V963 proved the post-provider trigger reaches /dev/subsys_esoc0, then stalls in sdx50m_toggle_soft_reset during mdm_subsys_powerup; cleanup reboot recovered native health"
        if passed
        else "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
    )
    return {
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": (
            "compare Android GPIO/IRQ/PMIC timing for the SDX50M soft-reset path before attempting another subsystem trigger"
            if passed
            else "inspect V963 evidence gaps before retrying live trigger work"
        ),
        "checks": checks,
        "summary": {
            "wchan": wchan,
            "stack_contains": [line.strip() for line in stack.splitlines() if line.strip()][:16],
            "cleanup_reboot_healthy": bool(cleanup.get("healthy")),
            "v963_decision": manifest.get("decision"),
            "subsys_open_attempted": contract.get("subsys_esoc0_open_attempted") == "1",
            "wifi_bringup_executed": bool(manifest.get("wifi_bringup_executed")),
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [(name, "PASS" if ok else "FAIL") for name, ok in manifest["checks"].items()]
    stack_lines = manifest["summary"].get("stack_contains") or []
    return "\n".join(
        [
            "# V964 V963 Post-Provider Trigger Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- v963 manifest: `{manifest['v963_manifest']}`",
            f"- next: {manifest['next_step']}",
            "",
            markdown_table(["check", "result"], rows),
            "",
            "## Key Evidence",
            "",
            f"- wchan: `{manifest['summary'].get('wchan') or '<missing>'}`",
            f"- cleanup_reboot_healthy: `{manifest['summary'].get('cleanup_reboot_healthy')}`",
            f"- subsys_open_attempted: `{manifest['summary'].get('subsys_open_attempted')}`",
            f"- wifi_bringup_executed: `{manifest['summary'].get('wifi_bringup_executed')}`",
            "",
            "```text",
            "\n".join(stack_lines),
            "```",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    v963_manifest_path = repo_path(args.v963_manifest)
    manifest = load_json(args.v963_manifest)
    manifest["_manifest_path"] = str(v963_manifest_path)
    helper_path = step_file(manifest, "mdm-helper-cnss-before-esoc")
    dmesg_path = step_file(manifest, "post-dmesg-wifi-esoc-tail")
    helper_text = read_text(helper_path) if helper_path else ""
    dmesg_text = read_text(dmesg_path) if dmesg_path else ""
    classification = classify(manifest, helper_text, dmesg_text)
    store = EvidenceStore(repo_path(args.out_dir))
    output: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "v963_manifest": str(v963_manifest_path),
        "helper_evidence": str(helper_path) if helper_path else "",
        "dmesg_evidence": str(dmesg_path) if dmesg_path else "",
        "device_commands_executed": False,
        "device_mutations": False,
        **classification,
    }
    store.write_json("manifest.json", output)
    store.write_text("summary.md", render_summary(output))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {output['decision']}")
    print(f"pass: {output['pass']}")
    print(f"reason: {output['reason']}")
    print(f"next: {output['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if output["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
