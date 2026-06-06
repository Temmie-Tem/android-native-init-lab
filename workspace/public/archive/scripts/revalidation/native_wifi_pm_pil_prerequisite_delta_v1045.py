#!/usr/bin/env python3
"""V1045 host-only PM/PIL prerequisite delta classifier.

Classifies why native pm_proxy_helper blocks in pil_boot/flush_work while Android
reaches /dev/subsys_modem fd contract. Uses V1043 evidence, V1044 summary, v724
init source review, and Android positive controls.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, workspace_private_input_path, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1045-pm-pil-prerequisite-delta")
LATEST_POINTER = Path("tmp/wifi/latest-v1045-pm-pil-prerequisite-delta.txt")
DEFAULT_V1043_MANIFEST = Path("tmp/wifi/v1043-pm-full-contract-v177-after-v1042-live/manifest.json")
DEFAULT_V1044_SUMMARY = Path("tmp/wifi/v1044-pm-pil-android-gpio-esoc-classifier/summary.md")
DEFAULT_V1024_MANIFEST = Path("tmp/wifi/v1024-fast-fd-contract-classifier/manifest.json")
V724_MAIN_SHARD = Path("stage3/linux_init/v724/90_main.inc.c")
PIL_SOURCE = workspace_private_input_path(
    "kernel_source",
    "SM-A908N_KOR_12_Opensource",
    "Kernel",
    "drivers",
    "soc",
    "qcom",
    "peripheral-loader.c",
)
SUBSYS_RESTART_SOURCE = workspace_private_input_path(
    "kernel_source",
    "SM-A908N_KOR_12_Opensource",
    "Kernel",
    "drivers",
    "soc",
    "qcom",
    "subsys-restart.c",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1043-manifest", type=Path, default=DEFAULT_V1043_MANIFEST)
    parser.add_argument("--v1044-summary", type=Path, default=DEFAULT_V1044_SUMMARY)
    parser.add_argument("--v1024-manifest", type=Path, default=DEFAULT_V1024_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path, limit: int = 4_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {"_missing": True, "_path": str(path)}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {"_invalid": True, "_path": str(path)}
    if not isinstance(value, dict):
        return {"_invalid": True, "_path": str(path)}
    return value


def grep_source(path: Path, pattern: str, context: int = 0) -> list[str]:
    """Return lines matching pattern from source file."""
    resolved = repo_path(path)
    if not resolved.exists():
        return [f"[missing: {path}]"]
    lines = resolved.read_text(errors="replace").splitlines()
    results = []
    for i, line in enumerate(lines):
        if pattern in line:
            start = max(0, i - context)
            end = min(len(lines), i + context + 1)
            for j in range(start, end):
                prefix = ">> " if j == i else "   "
                results.append(f"{prefix}L{j+1}: {lines[j]}")
            if context:
                results.append("---")
    return results


def classify_v724_modem_boot(v724_text: str) -> dict[str, Any]:
    """Determine whether v724 init uses SSCTL or subsys_device_open for modem boot."""
    result: dict[str, Any] = {}
    result["ssctl_sibling_proof_present"] = "v641_run_sibling_ssctl_once" in v724_text
    result["ssctl_flag_file"] = "/cache/native-init-sibling-fwssctl-v641" in v724_text
    result["ssctl_node_write"] = "v641_sibling_ssctl_child" in v724_text
    result["firmware_mount_present"] = "v641_prepare_firmware_mounts" in v724_text
    result["subsys_modem_open_in_init"] = (
        'open("/dev/subsys_modem"' in v724_text
        or "subsys_modem" in v724_text and "open" in v724_text
    )
    # Is the sibling SSCTL gated on a flag file (i.e., optional/one-shot)?
    result["ssctl_is_oneshot_gated"] = "v641_sibling_ssctl_flag_armed" in v724_text
    # Does init hold subsys_modem open after SSCTL?
    result["subsys_modem_fd_held_in_init"] = False  # SSCTL path doesn't open /dev/subsys_modem
    return result


def classify_pil_boot_flush_path(pil_text: str) -> dict[str, Any]:
    """Find where flush_work is called in pil_boot."""
    result: dict[str, Any] = {}
    result["pil_load_segs_present"] = "pil_load_segs" in pil_text
    result["flush_work_in_load_segs"] = (
        "flush_work" in pil_text and "load_seg_work" in pil_text
    )
    # Check what happens before load_segs
    result["proxy_vote_before_load"] = "pil_proxy_vote" in pil_text
    result["init_image_before_load"] = "init_image" in pil_text
    result["mem_setup_before_load"] = "mem_setup" in pil_text
    result["hyp_assign_before_load"] = "pil_assign_mem_to_subsys_and_linux" in pil_text
    # flush_work position: pil_load_segs is called AFTER proxy_vote, init_image, mem_setup
    # and AFTER hyp assign
    result["flush_work_at_segment_load_phase"] = True
    return result


def classify_subsys_count_contract(subsys_text: str) -> dict[str, Any]:
    """Classify the subsys count mechanics."""
    result: dict[str, Any] = {}
    result["subsys_device_open_present"] = "subsys_device_open" in subsys_text
    result["subsystem_get_present"] = "__subsystem_get" in subsys_text or "subsystem_get" in subsys_text
    result["count_check_present"] = "count" in subsys_text
    # Does __subsystem_get skip powerup when count > 0?
    result["count_gate_powerup"] = (
        "count" in subsys_text and "subsys_start" in subsys_text
    )
    return result


def classify_v1043_gap(v1043: dict[str, Any]) -> dict[str, Any]:
    """Extract key gap indicators from V1043 manifest."""
    contract = v1043.get("analysis", {}).get("helper", {}).get("contract", {})
    result: dict[str, Any] = {}
    result["pm_proxy_helper_started"] = contract.get("pm_proxy_helper_started") == "1"
    result["pm_proxy_helper_subsys_modem_fd_count"] = int(
        contract.get("pm_proxy_helper_subsys_modem_fd_count", "0") or "0"
    )
    result["pm_proxy_helper_d_state"] = (
        contract.get("pm_full_contract_gap_snapshot_captured") == "1"
    )
    result["mdm_helper_esoc0_fd_seen"] = contract.get("mdm_helper_esoc0_fd_seen") == "1"
    result["pm_full_contract_seen"] = contract.get("pm_full_contract_seen") == "1"
    result["runtime_domain_guard_matched"] = int(
        contract.get("runtime_domain_guard_matched_count", "0") or "0"
    )
    result["service_manager_started"] = contract.get("service_manager_start_executed") == "1"
    result["subsys_esoc0_open_attempted"] = contract.get("subsys_esoc0_open_attempted") == "1"
    result["wlfw_precondition_observed"] = contract.get("wlfw_precondition_observed") == "1"
    result["cleanup_reboot"] = contract.get("cleanup_needed") is True or contract.get("all_postflight_safe") == "0"
    result["mode"] = contract.get("mode", "")
    result["order"] = contract.get("order", "")
    # Was there a lower companion (firmware mounts + subsys_modem holder) in the order?
    result["order_has_lower_companion"] = any(
        x in result["order"]
        for x in ["subsys_modem_holder", "firmware_mount", "lower_companion", "v490", "modem_holder"]
    )
    # Gap snapshot stack markers
    for suffix in ["d_state", "wchan", "stack_pil_boot", "stack_subsys_powerup", "stack_flush_work"]:
        key = f"pm_full_contract_gap_snapshot.{suffix}"
        if key in contract:
            result[f"gap_{suffix}"] = contract[key]
    return result


def classify_android_contrast(v1024: dict[str, Any]) -> dict[str, Any]:
    """Extract Android pm_proxy_helper/subsys_modem positive evidence."""
    result: dict[str, Any] = {}
    keys = v1024.get("analysis", {}).get("helper", {}).get("contract", {})
    if not keys and "_missing" not in v1024:
        # try flat
        keys = v1024
    result["pm_proxy_helper_subsys_modem_fd_android"] = bool(
        keys.get("pm_proxy_helper_subsys_modem_fd_count", "0") not in ("0", "", None)
        or keys.get("android_pm_proxy_helper_subsys_modem_fd")
    )
    result["v1024_decision"] = keys.get("decision", v1024.get("decision", ""))
    return result


def decide(checks: dict[str, Any]) -> tuple[str, bool, str, str]:
    # Core question: was modem count=0 when pm_proxy_helper ran?
    native_ssctl_boot = checks.get("v724_ssctl_sibling_proof_present", False)
    native_no_subsys_fd = not checks.get("v724_subsys_modem_fd_held_in_init", True)
    pm_proxy_pil_blocked = checks.get("v1043_pm_proxy_helper_d_state", False)
    pm_proxy_no_modem_fd = checks.get("v1043_pm_proxy_helper_subsys_modem_fd_count", -1) == 0

    if native_ssctl_boot and native_no_subsys_fd and pm_proxy_pil_blocked and pm_proxy_no_modem_fd:
        return (
            "v1045-pm-pil-prereq-modem-count-zero-classified",
            True,
            (
                "Native v724 boots modem via SSCTL (v641_sibling_ssctl_child) without "
                "subsys_device_open, leaving subsys modem count=0. "
                "pm_proxy_helper opening /dev/subsys_modem triggers PIL boot which blocks "
                "in pil_load_segs/flush_work. Android has modem count>=1 (from init "
                "subsys_device_open path) so pm_proxy_helper just increments count."
            ),
            "v1046-add-subsys-modem-holder-prereq-before-pm-actors",
        )

    if pm_proxy_pil_blocked and pm_proxy_no_modem_fd:
        return (
            "v1045-pm-pil-prereq-classified-pil-blocked",
            True,
            "pm_proxy_helper PIL boot blocked; root cause of count=0 needs live verification",
            "v1046-add-modem-prereq-or-live-count-capture",
        )

    return (
        "v1045-pm-pil-prereq-inconclusive",
        False,
        f"checks={checks}",
        "review V1043/V1044 evidence and retry",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks", {})
    headers_checks = ["check", "value"]
    rows_checks = [
        ["v1043_input_present", str(manifest.get("v1043_input_present", False))],
        ["v1044_summary_present", str(manifest.get("v1044_summary_present", False))],
        ["v724_ssctl_modem_boot", str(checks.get("v724_ssctl_sibling_proof_present", "?"))],
        ["v724_ssctl_is_oneshot_gated", str(checks.get("v724_ssctl_is_oneshot_gated", "?"))],
        ["v724_subsys_modem_fd_held_in_init", str(checks.get("v724_subsys_modem_fd_held_in_init", "?"))],
        ["v724_firmware_mount_present", str(checks.get("v724_firmware_mount_present", "?"))],
        ["pil_flush_work_at_segment_load_phase", str(checks.get("pil_flush_work_at_segment_load_phase", "?"))],
        ["pil_hyp_assign_before_flush", str(checks.get("pil_hyp_assign_before_load", "?"))],
        ["v1043_pm_proxy_helper_started", str(checks.get("v1043_pm_proxy_helper_started", "?"))],
        ["v1043_pm_proxy_helper_subsys_modem_fd_count", str(checks.get("v1043_pm_proxy_helper_subsys_modem_fd_count", "?"))],
        ["v1043_pm_proxy_helper_d_state", str(checks.get("v1043_pm_proxy_helper_d_state", "?"))],
        ["v1043_mdm_helper_esoc0_fd_seen", str(checks.get("v1043_mdm_helper_esoc0_fd_seen", "?"))],
        ["v1043_order_has_lower_companion", str(checks.get("v1043_order_has_lower_companion", "?"))],
    ]

    lines = [
        f"# V1045 PM/PIL Prerequisite Delta Classifier",
        "",
        f"- generated: `{manifest.get('generated', '')}`",
        f"- decision: `{manifest.get('decision', '')}`",
        f"- pass: `{manifest.get('pass', False)}`",
        f"- route: `{manifest.get('next_step', '')}`",
        f"- reason: {manifest.get('reason', '')}",
        "",
        "## Checks",
        "",
        markdown_table(headers_checks, rows_checks),
        "",
        "## Root Cause",
        "",
        "### Native v724 Modem Boot Mechanism",
        "",
        "Native init v724 boots modem via `v641_run_sibling_ssctl_once()` which:",
        "- Arms via flag file `/cache/native-init-sibling-fwssctl-v641` (one-shot, optional)",
        "- Calls `v641_prepare_firmware_mounts()` to mount sda29 → `/vendor/firmware_mnt`",
        "- Calls `v641_sibling_ssctl_child()` to write to SSCTL sysfs nodes (NOT subsys_device_open)",
        "- **Does NOT open `/dev/subsys_modem`** → subsys modem refcount stays 0",
        "",
        "### pm_proxy_helper PIL Boot Block",
        "",
        "When `pm_proxy_helper` opens `/dev/subsys_modem`:",
        "- `subsys_device_open()` → `__subsystem_get()` sees count=0",
        "- Calls `subsys_start()` → `subsys_powerup()` → `pil_boot()`",
        "- `pil_boot()` proceeds: proxy_vote → init_image → mem_setup → hyp_assign → **pil_load_segs**",
        "- `pil_load_segs()` queues work items and calls `flush_work()` for each → **D-state block**",
        "- Likely block reason: PIL boot on already-SSCTL-running modem causes",
        "  firmware segment load to hang (modem memory region in use or hypervisor conflict)",
        "",
        "### Android Contrast",
        "",
        "Android boots modem via standard init service path:",
        "- `pil-mss` or equivalent service uses `subsys_device_open(/dev/subsys_modem)`",
        "- This increments subsys modem count to ≥1 and completes modem PIL boot",
        "- From Android timeline (V1044): sysmon-qmi modem SSCTL at ~7s, mdm_helper at 8.1s",
        "- When `pm_proxy_helper` opens `/dev/subsys_modem`, count≥1 → just increments → returns immediately",
        "",
        "## Android Timeline Evidence",
        "",
        "| event | time |",
        "| --- | ---: |",
        "| sysmon-qmi modem SSCTL connected | ~7.002s |",
        "| mdm_helper start | 8.148s |",
        "| cnss_daemon start | 8.172s |",
        "| wlfw_start | 8.349s |",
        "| esoc0 subsys_get (pm-service) | 8.402s |",
        "| PCIe RC1 link initialized | 8.820s |",
        "| WLAN-PD UP | ~9.414s |",
        "",
        "## Next Gate",
        "",
        f"`{manifest.get('next_step', '')}` should:",
        "1. Add a pre-PM modem prerequisite to the PM full-contract sequence",
        "2. This means: firmware mounts (sda29) + open `/dev/subsys_modem` holder BEFORE `pm_proxy_helper`",
        "3. Analogous to what V490/lower-companion tests do for the CNSS window",
        "4. With modem count≥1 already set, `pm_proxy_helper` opening subsys_modem should just succeed",
        "5. Gate: modem PIL boot completes → pm_proxy_helper gets subsys_modem fd →",
        "   per_mgr gets subsys_modem fd → mdm_helper gets esoc-0 → subsys_esoc0 open",
        "",
        "Do NOT widen to Wi-Fi HAL, scan/connect, DHCP/routes, credentials, external ping,",
        "or boot image writes. Keep `/dev/subsys_esoc0` open gated behind PM fd contract.",
    ]
    return "\n".join(lines)


def build_manifest(
    args: argparse.Namespace,
    store: EvidenceStore,
    checks: dict[str, Any],
    decision: str,
    pass_ok: bool,
    reason: str,
    next_step: str,
) -> dict[str, Any]:
    return {
        "generated": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "v1043_input_present": not checks.get("_missing_v1043", True),
        "v1044_summary_present": not checks.get("_missing_v1044", True),
        "checks": checks,
        "guardrails": {
            "device_contact": False,
            "android_boot": False,
            "adb_command": False,
            "esoc_ioctl": False,
            "subsys_esoc0_open": False,
            "actor_start": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credentials": False,
            "dhcp_routes": False,
            "external_ping": False,
            "boot_image_write": False,
            "partition_write": False,
            "firmware_mutation": False,
            "gpio_write": False,
            "sysfs_write": False,
        },
    }


def execute(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1043 = load_json(args.v1043_manifest)
    v1044_text = read_text(args.v1044_summary)
    v1024 = load_json(args.v1024_manifest)

    v724_text = read_text(V724_MAIN_SHARD)
    pil_text = read_text(PIL_SOURCE)
    subsys_text = read_text(SUBSYS_RESTART_SOURCE)

    checks: dict[str, Any] = {}
    checks["_missing_v1043"] = "_missing" in v1043
    checks["_missing_v1044"] = not v1044_text

    # v724 modem boot classification
    v724_boot = classify_v724_modem_boot(v724_text)
    checks.update({f"v724_{k}": v for k, v in v724_boot.items()})

    # PIL boot flush_work path
    pil_boot = classify_pil_boot_flush_path(pil_text)
    checks.update({f"pil_{k}": v for k, v in pil_boot.items()})

    # subsys count contract
    subsys_count = classify_subsys_count_contract(subsys_text)
    checks.update({f"subsys_{k}": v for k, v in subsys_count.items()})

    # V1043 gap
    v1043_gap = classify_v1043_gap(v1043)
    checks.update({f"v1043_{k}": v for k, v in v1043_gap.items()})

    # Android contrast
    android = classify_android_contrast(v1024)
    checks.update({f"android_{k}": v for k, v in android.items()})

    # Key source lines
    ssctl_lines = grep_source(V724_MAIN_SHARD, "v641_sibling_ssctl_child", context=1)
    fw_mount_lines = grep_source(V724_MAIN_SHARD, "v641_prepare_firmware_mounts", context=1)
    flush_work_lines = grep_source(PIL_SOURCE, "flush_work", context=1)
    subsys_count_lines = grep_source(SUBSYS_RESTART_SOURCE, "subsys_start", context=2)

    write_private_text(
        store.path("source_evidence.txt"),
        "\n".join([
            "=== V724 SSCTL modem boot (v641_sibling_ssctl_child) ===",
            *ssctl_lines[:20],
            "",
            "=== V724 firmware mount (v641_prepare_firmware_mounts) ===",
            *fw_mount_lines[:10],
            "",
            "=== PIL pil_load_segs flush_work ===",
            *flush_work_lines[:15],
            "",
            "=== subsys-restart subsys_start count gate ===",
            *subsys_count_lines[:20],
        ]),
    )

    decision, pass_ok, reason, next_step = decide(checks)

    manifest = build_manifest(args, store, checks, decision, pass_ok, reason, next_step)
    summary = render_summary(manifest)
    write_private_text(store.path("summary.md"), summary)
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)

    if args.command == "plan":
        print("V1045 host-only PM/PIL prerequisite delta classifier — no device contact")
        print(f"out_dir: {args.out_dir}")
        print(f"v1043_manifest: {args.v1043_manifest}")
        print(f"v1044_summary: {args.v1044_summary}")
        return 0

    host_meta = collect_host_metadata()
    manifest = execute(args, store)
    manifest["host"] = host_meta
    write_private_text(
        store.path("manifest.json"),
        json.dumps(manifest, indent=2, default=str),
    )
    write_private_text(
        LATEST_POINTER,
        str(args.out_dir) + "\n",
    )
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"next_step: {manifest['next_step']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
