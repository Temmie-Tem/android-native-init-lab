#!/usr/bin/env python3
"""Host-only V1748 classifier for the WLAN-PD CNSS tracefs delta."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1748-wlan-pd-tracefs-delta-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1748_WLAN_PD_TRACEFS_DELTA_CLASSIFIER_2026-06-03.md"
)

V1701_SOURCE_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1701-wlan-pd-cnss-tracefs-target-path-test-boot" / "manifest.json"
)
V1702_LIVE_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1702-wlan-pd-cnss-tracefs-target-path-handoff" / "manifest.json"
)
V1702_HELPER = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1702-wlan-pd-cnss-tracefs-target-path-handoff"
    / "test-v1393-helper-result.stdout.txt"
)
V1745_SOURCE_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1745-wlan-pd-private-tracefs-repair-test-boot" / "manifest.json"
)
V1747_LIVE_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1747-wlan-pd-private-tracefs-repair-handoff" / "manifest.json"
)
V1747_HELPER = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1747-wlan-pd-private-tracefs-repair-handoff"
    / "test-v1393-helper-result.stdout.txt"
)
HELPER_SOURCE = REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_android_execns_probe.c"
V1701_BUILD = REPO_ROOT / "scripts" / "revalidation" / "build_native_init_wifi_test_boot_v1701.py"
V1745_BUILD = REPO_ROOT / "scripts" / "revalidation" / "build_native_init_wifi_test_boot_v1745.py"
NEXT_WORK_PATH = REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_NEXT_WORK_2026-04-25.md"


def display(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_text(encoding="utf-8", errors="replace")


def read_text_binary_safe(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path)
    return path.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def parse_kv(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line or line.startswith("$"):
            continue
        key, value = line.split("=", 1)
        if re.fullmatch(r"[A-Za-z0-9_.:-]+", key):
            values[key] = value
    return values


def intish(value: object) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return 0


def boolish(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass"}


def line_number(path: Path, pattern: str) -> int | None:
    regex = re.compile(pattern)
    for number, line in enumerate(read_text(path).splitlines(), 1):
        if regex.search(line):
            return number
    return None


def write_json_private(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    path.chmod(0o600)


def collect_evidence() -> dict[str, Any]:
    v1701_source = load_json(V1701_SOURCE_MANIFEST)
    v1702_live = load_json(V1702_LIVE_MANIFEST)
    v1702_kv = parse_kv(read_text_binary_safe(V1702_HELPER))
    v1745_source = load_json(V1745_SOURCE_MANIFEST)
    v1747_live = load_json(V1747_LIVE_MANIFEST)
    v1747_kv = parse_kv(read_text_binary_safe(V1747_HELPER))
    helper_source = read_text(HELPER_SOURCE)
    v1701_build = read_text(V1701_BUILD)
    v1745_build = read_text(V1745_BUILD)

    return {
        "v1701_source_artifact": {
            "manifest": display(V1701_SOURCE_MANIFEST),
            "decision": v1701_source.get("decision"),
            "pass": boolish(v1701_source.get("pass")),
            "helper_marker": v1701_source.get("helper_marker"),
            "mount_debugfs": boolish(v1701_source.get("wifi_test", {}).get("mount_debugfs")),
            "firmware_mounts": boolish(v1701_source.get("wifi_test", {}).get("firmware_mounts")),
            "runtime_mode": v1701_source.get("wifi_test", {}).get("helper_runtime_mode"),
            "build_script_has_mount_debugfs_flag": "--wifi-test-mount-debugfs" in v1701_build,
        },
        "v1702_live": {
            "manifest": display(V1702_LIVE_MANIFEST),
            "decision": v1702_live.get("decision"),
            "pass": boolish(v1702_live.get("pass")),
            "rollback_ok": boolish(v1702_live.get("rollback", {}).get("ok")),
            "tracefs_available": intish(v1702_kv.get("wlan_pd_cnss_nonlog_control_flow.tracefs.available")),
            "tracefs_path": v1702_kv.get("wlan_pd_cnss_nonlog_control_flow.tracefs.path"),
            "tracefs_errno": intish(v1702_kv.get("wlan_pd_cnss_nonlog_control_flow.tracefs.errno")),
            "uprobe_attempted": intish(v1702_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe_attempted")),
            "uprobe_register_rc": intish(v1702_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.register_rc")),
            "uprobe_enabled": intish(v1702_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.enabled")),
            "uprobe_hit_count": intish(v1702_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.hit_count")),
            "target_selected_path": v1702_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.target.selected_path"),
            "target0_path": v1702_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.target.0.path"),
            "target0_access_rc": intish(v1702_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.target.0.access_rc")),
            "label": v1702_kv.get("wlan_pd_cnss_nonlog_control_flow.label"),
            "wlfw_first_hit": v1702_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.first_hit_line"),
        },
        "v1745_source_artifact": {
            "manifest": display(V1745_SOURCE_MANIFEST),
            "decision": v1745_source.get("decision"),
            "pass": boolish(v1745_source.get("pass")),
            "helper_marker": v1745_source.get("helper_marker"),
            "mount_debugfs": boolish(v1745_source.get("wifi_test", {}).get("mount_debugfs")),
            "firmware_mounts": boolish(v1745_source.get("wifi_test", {}).get("firmware_mounts")),
            "runtime_mode": v1745_source.get("wifi_test", {}).get("helper_runtime_mode"),
            "build_script_has_mount_debugfs_flag": "--wifi-test-mount-debugfs" in v1745_build,
        },
        "v1747_live": {
            "manifest": display(V1747_LIVE_MANIFEST),
            "decision": v1747_live.get("decision"),
            "pass": boolish(v1747_live.get("pass")),
            "rollback_ok": boolish(v1747_live.get("rollback", {}).get("ok")),
            "corrected_label": v1747_live.get("gate", {}).get("v1747_label"),
            "tracefs_available": intish(v1747_kv.get("wlan_pd_cnss_nonlog_control_flow.tracefs.available")),
            "tracefs_path": v1747_kv.get("wlan_pd_cnss_nonlog_control_flow.tracefs.path"),
            "tracefs_errno": intish(v1747_kv.get("wlan_pd_cnss_nonlog_control_flow.tracefs.errno")),
            "uprobe_attempted": intish(v1747_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe_attempted")),
            "uprobe_register_attempted": intish(v1747_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.register_attempted")),
            "uprobe_enabled": intish(v1747_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.enabled")),
            "uprobe_hit_count": intish(v1747_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.hit_count")),
            "target_selected_path": v1747_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.target.selected_path"),
            "target0_path": v1747_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.target.0.path"),
            "target0_access_rc": intish(v1747_kv.get("wlan_pd_cnss_nonlog_control_flow.uprobe.target.0.access_rc")),
            "label": v1747_kv.get("wlan_pd_cnss_nonlog_control_flow.label"),
        },
        "source_contract": {
            "helper_source": display(HELPER_SOURCE),
            "materialize_tracefs_line": line_number(HELPER_SOURCE, r"materialize_wlan_pd_cnss_tracefs_surface"),
            "source_debug_tracing_line": line_number(HELPER_SOURCE, r'const char \*source = "/sys/kernel/debug/tracing"'),
            "source_kernel_tracing_fallback_line": line_number(HELPER_SOURCE, r'source = "/sys/kernel/tracing"'),
            "bind_rw_source_target_line": line_number(HELPER_SOURCE, r"bind_rw\(source, target\)"),
            "find_tracefs_line": line_number(HELPER_SOURCE, r"cnss_wlfw_uprobe_find_tracefs"),
            "private_roots_first_line": line_number(HELPER_SOURCE, r"roots\[root_count\+\+\] = paths->sys_kernel_debug_tracing"),
            "arm_before_children_line": line_number(HELPER_SOURCE, r"cnss_wlfw_uprobe_arm_global\(paths\)"),
            "helper_mounts_tracefs_itself": "mount(\"tracefs\"" in helper_source or "mount(\"debugfs\"" in helper_source,
        },
    }


def classify(evidence: dict[str, Any]) -> tuple[str, bool, str, dict[str, bool]]:
    v1701 = evidence["v1701_source_artifact"]
    v1702 = evidence["v1702_live"]
    v1745 = evidence["v1745_source_artifact"]
    v1747 = evidence["v1747_live"]
    source = evidence["source_contract"]
    checks = {
        "v1701_source_passed_with_debugfs_mount": (
            v1701["pass"]
            and v1701["mount_debugfs"]
            and v1701["build_script_has_mount_debugfs_flag"]
            and v1701["runtime_mode"] == "wifi-companion-wlan-pd-cnss-output-visibility-start-only"
        ),
        "v1702_live_tracefs_and_uprobe_worked": (
            v1702["pass"]
            and v1702["rollback_ok"]
            and v1702["tracefs_available"] == 1
            and v1702["tracefs_path"] == "/sys/kernel/debug/tracing"
            and v1702["uprobe_attempted"] == 1
            and v1702["uprobe_register_rc"] == 0
            and v1702["uprobe_enabled"] == 1
            and v1702["uprobe_hit_count"] > 0
        ),
        "v1745_source_omitted_debugfs_mount": (
            v1745["pass"]
            and not v1745["mount_debugfs"]
            and not v1745["build_script_has_mount_debugfs_flag"]
            and v1745["runtime_mode"] == "wifi-companion-wlan-pd-cnss-output-visibility-start-only"
        ),
        "v1747_live_tracefs_failed_before_target_probe": (
            v1747["pass"]
            and v1747["rollback_ok"]
            and v1747["tracefs_available"] == 0
            and v1747["tracefs_errno"] == 2
            and v1747["uprobe_attempted"] == 0
            and v1747["uprobe_register_attempted"] == 0
            and str(v1747["target_selected_path"]) == "none"
        ),
        "helper_only_binds_existing_tracefs_source": (
            bool(source["materialize_tracefs_line"])
            and bool(source["source_debug_tracing_line"])
            and bool(source["source_kernel_tracing_fallback_line"])
            and bool(source["bind_rw_source_target_line"])
            and not source["helper_mounts_tracefs_itself"]
        ),
        "v1745_path_repair_did_not_explain_missing_source_mount": (
            bool(source["private_roots_first_line"])
            and bool(source["arm_before_children_line"])
            and v1747["corrected_label"] == "cnss-output-still-invisible"
        ),
    }
    if all(checks.values()):
        return (
            "v1748-tracefs-delta-debugfs-mount-flag-missing",
            True,
            "V1702 worked with debugfs mounted, V1745 omitted that mount, and V1747 failed before target probing because no tracefs source was available",
            checks,
        )
    return (
        "v1748-tracefs-delta-incomplete-evidence",
        False,
        "the host-only evidence does not fully prove the debugfs mount flag delta",
        checks,
    )


def render_report(result: dict[str, Any]) -> str:
    evidence = result["evidence"]
    checks = result["checks"]
    v1701 = evidence["v1701_source_artifact"]
    v1702 = evidence["v1702_live"]
    v1745 = evidence["v1745_source_artifact"]
    v1747 = evidence["v1747_live"]
    source = evidence["source_contract"]
    return "\n".join([
        "# Native Init V1748 WLAN-PD Tracefs Delta Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1748`",
        "- Type: host/source-only tracefs target-path delta classifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Delta",
        "",
        f"- V1701 source `mount_debugfs`: `{v1701['mount_debugfs']}`; build flag present: `{v1701['build_script_has_mount_debugfs_flag']}`",
        f"- V1702 live tracefs path/available/uprobe hits: `{v1702['tracefs_path']}` / `{v1702['tracefs_available']}` / `{v1702['uprobe_hit_count']}`",
        f"- V1745 source `mount_debugfs`: `{v1745['mount_debugfs']}`; build flag present: `{v1745['build_script_has_mount_debugfs_flag']}`",
        f"- V1747 live tracefs path/available/errno/uprobe attempted: `{v1747['tracefs_path']}` / `{v1747['tracefs_available']}` / `{v1747['tracefs_errno']}` / `{v1747['uprobe_attempted']}`",
        f"- V1747 selected target path: `{v1747['target_selected_path']}`",
        "",
        "## Source Contract",
        "",
        f"- `materialize_wlan_pd_cnss_tracefs_surface`: `{source['materialize_tracefs_line']}`",
        f"- source `/sys/kernel/debug/tracing`: `{source['source_debug_tracing_line']}`",
        f"- fallback `/sys/kernel/tracing`: `{source['source_kernel_tracing_fallback_line']}`",
        f"- bind existing tracefs source: `{source['bind_rw_source_target_line']}`",
        f"- helper mounts tracefs/debugfs itself: `{source['helper_mounts_tracefs_itself']}`",
        f"- private roots searched first: `{source['private_roots_first_line']}`",
        "",
        "## Checks",
        "",
        *[f"- `{name}`: `{value}`" for name, value in checks.items()],
        "",
        "## Interpretation",
        "",
        "- V1745 fixed tracefs path selection but did not restore the source tracefs mount that made V1702 work.",
        "- Because V1747 failed before target probing, the remaining immediate bug is not the cnss-daemon uprobe target path.",
        "- The next source/build unit should restore the V1701 `--wifi-test-mount-debugfs` contract on the pure internal-modem route, then run artifact sanity before any live retry.",
        "- This does not justify adding PM/service-window actors, `boot_wlan`, eSoC/RC1, Wi-Fi HAL, scan/connect, DHCP/routes, or external ping.",
        "",
        "## Safety Scope",
        "",
        "This classifier performed host-side reads only. It did not issue live device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def update_next_work(result: dict[str, Any]) -> None:
    section = render_next_work_section(result)
    existing = read_text(NEXT_WORK_PATH)
    marker = "## V1748 WLAN-PD tracefs delta classifier (2026-06-03)"
    if marker in existing:
        existing = existing[: existing.index(marker)].rstrip() + "\n\n"
    NEXT_WORK_PATH.write_text(existing.rstrip() + "\n\n" + section, encoding="utf-8")


def render_next_work_section(result: dict[str, Any]) -> str:
    evidence = result["evidence"]
    v1702 = evidence["v1702_live"]
    v1747 = evidence["v1747_live"]
    return "\n".join([
        "## V1748 WLAN-PD tracefs delta classifier (2026-06-03)",
        "",
        "- V1748 host/source-only classifier completed.",
        "",
        "  Result:",
        "",
        f"  - decision: `{result['decision']}`;",
        f"  - evidence: `{result['out_dir']}`;",
        f"  - V1702 tracefs available/path/hits: `{v1702['tracefs_available']}` / `{v1702['tracefs_path']}` / `{v1702['uprobe_hit_count']}`;",
        f"  - V1747 tracefs available/path/errno: `{v1747['tracefs_available']}` / `{v1747['tracefs_path']}` / `{v1747['tracefs_errno']}`.",
        "",
        "  Interpretation:",
        "",
        "  - V1701/V1702 worked because the test boot mounted debugfs/tracefs before",
        "    CNSS uprobe arming;",
        "  - V1745/V1747 omitted `--wifi-test-mount-debugfs`, so the private tracefs",
        "    path repair had no source tracefs to bind and failed before target probing;",
        "  - no PM/service-window actors, `boot_wlan`, eSoC/RC1, Wi-Fi HAL,",
        "    scan/connect, DHCP/routes, or external ping are justified by this delta.",
        "",
        "  Next candidate:",
        "",
        "  - V1749 source/build-only: rebuild the pure internal-modem V1745-style",
        "    artifact with the V1701 `--wifi-test-mount-debugfs` contract restored;",
        "  - then run local artifact sanity before any rollbackable live handoff.",
        "",
        "  Report:",
        "  `docs/reports/NATIVE_INIT_V1748_WLAN_PD_TRACEFS_DELTA_CLASSIFIER_2026-06-03.md`.",
    ])


def main() -> int:
    evidence = collect_evidence()
    decision, pass_ok, reason, checks = classify(evidence)
    result = {
        "cycle": "V1748",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "checks": checks,
        "evidence": evidence,
        "out_dir": display(OUT_DIR),
    }
    write_json_private(OUT_DIR / "manifest.json", result)
    write_json_private(OUT_DIR / "evidence.json", evidence)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    update_next_work(result)
    print(json.dumps({"decision": decision, "pass": pass_ok, "checks": checks}, indent=2, sort_keys=True))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
