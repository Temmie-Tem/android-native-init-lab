#!/usr/bin/env python3
"""V999 host-only route classifier after the post-SELinux service-window retry."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v999-post-selinux-wlfw-route-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v999-post-selinux-wlfw-route-classifier.txt")

DEFAULT_V998_MANIFEST = Path("tmp/wifi/v998-android-service-window-live-v169-post-selinux/manifest.json")
DEFAULT_V998_REPORT = Path("docs/reports/NATIVE_INIT_V998_ANDROID_SERVICE_WINDOW_POST_SELINUX_2026-05-26.md")
DEFAULT_V998_TRANSCRIPT = Path(
    "tmp/wifi/v998-android-service-window-live-v169-post-selinux/native/mdm-helper-cnss-before-esoc.txt"
)
DEFAULT_V966_REPORT = Path("docs/reports/NATIVE_INIT_V966_ANDROID_WLFW_START_ATTRIBUTION_2026-05-26.md")
DEFAULT_V968_REPORT = Path("docs/reports/NATIVE_INIT_V968_ANDROID_DMESG_ESOC_GPIO_TIMING_2026-05-26.md")
DEFAULT_V918_REPORT = Path("docs/reports/NATIVE_INIT_V918_MDM_HELPER_SUBSYS_TRIGGER_WAIT_LIVE_2026-05-26.md")
DEFAULT_V923_REPORT = Path("docs/reports/NATIVE_INIT_V923_CNSS_BEFORE_ESOC_LIVE_2026-05-26.md")
DEFAULT_V924_REPORT = Path("docs/reports/NATIVE_INIT_V924_CNSS_WLFW_PRECONDITION_GAP_2026-05-26.md")
DEFAULT_V965_REPORT = Path("docs/reports/NATIVE_INIT_V965_V964_ROUTE_CLASSIFIER_2026-05-26.md")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v998-manifest", type=Path, default=DEFAULT_V998_MANIFEST)
    parser.add_argument("--v998-report", type=Path, default=DEFAULT_V998_REPORT)
    parser.add_argument("--v998-transcript", type=Path, default=DEFAULT_V998_TRANSCRIPT)
    parser.add_argument("--v966-report", type=Path, default=DEFAULT_V966_REPORT)
    parser.add_argument("--v968-report", type=Path, default=DEFAULT_V968_REPORT)
    parser.add_argument("--v918-report", type=Path, default=DEFAULT_V918_REPORT)
    parser.add_argument("--v923-report", type=Path, default=DEFAULT_V923_REPORT)
    parser.add_argument("--v924-report", type=Path, default=DEFAULT_V924_REPORT)
    parser.add_argument("--v965-report", type=Path, default=DEFAULT_V965_REPORT)
    return parser.parse_args()


def read_text(path: Path, limit: int = 2_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    return json.loads(resolved.read_text(encoding="utf-8"))


def bool_from_manifest(manifest: dict[str, Any], key: str) -> bool | None:
    value = manifest.get(key)
    return value if isinstance(value, bool) else None


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v998_manifest = load_json(args.v998_manifest)
    v998_report = read_text(args.v998_report)
    v998_transcript = read_text(args.v998_transcript)
    v966_report = read_text(args.v966_report)
    v968_report = read_text(args.v968_report)
    v918_report = read_text(args.v918_report)
    v923_report = read_text(args.v923_report)
    v924_report = read_text(args.v924_report)
    v965_report = read_text(args.v965_report)

    v998_service_window_clean = all(
        marker in v998_report
        for marker in (
            "child_started=14",
            "all_observable_at_timeout=1",
            "all_postflight_safe=1",
            "wificond` post-exec context",
        )
    ) or all(
        marker in v998_transcript
        for marker in (
            "android_wifi_service_window.child_started=14",
            "android_wifi_service_window.all_observable_at_timeout=1",
            "android_wifi_service_window.all_postflight_safe=1",
            "wifi_hal_composite_child.wificond.selinux.exec=u:r:wificond:s0",
        )
    )
    v998_wlfw_missing = (
        "WLFW precondition | MISSING" in v998_report
        or "wlfw_precondition_observed=0" in v998_transcript
        or bool_from_manifest(v998_manifest, "wlfw_precondition_observed") is False
    )
    v998_no_lower_trigger = all(
        marker in v998_report
        for marker in (
            "no `qcwlanstate`",
            "no `IWifi.start`",
            "no `/dev/subsys_esoc0` open",
            "no eSoC ioctl",
        )
    ) or all(
        marker in v998_transcript
        for marker in (
            "android_wifi_service_window.qcwlanstate_write=0",
            "android_wifi_service_window.iwifi_start=0",
            "android_wifi_service_window.subsys_esoc0_open_attempted=0",
            "android_wifi_service_window.esoc_ioctl_attempted=0",
        )
    )
    v966_wlfw_precedes_esoc_get = all(
        marker in v966_report
        for marker in (
            "`cnss-daemon wlfw_start` | `8.349631`",
            "`/dev/subsys_esoc0` `__subsystem_get` | `8.402277`",
            "`wlfw_start` is not caused by the direct `/dev/subsys_esoc0` open",
        )
    )
    v968_gpio_transition_unresolved = all(
        marker in v968_report
        for marker in (
            "GPIO level-transition timing is not directly visible",
            "not prove when GPIO135 asserts high",
            "Magisk or adb early sampler is justified only if the next native gate requires exact AP2MDM/MDM2AP level-transition timing",
        )
    )
    v968_fallback_condition_now_met = v998_service_window_clean and v998_wlfw_missing
    v918_blind_subsys_stalls = all(
        marker in v918_report
        for marker in (
            "`sdx50m_toggle_soft_reset`",
            "does not return under the current native runtime conditions",
        )
    )
    v923_fail_closed_gate = all(
        marker in v923_report
        for marker in (
            "`subsys_esoc0_open_attempted` | `false`",
            "WLFW precondition",
        )
    )
    v924_rejects_repeat_subsys = "Repeating `/dev/subsys_esoc0` open is not the right next move" in v924_report
    v965_rejects_stale_iwifi_qcwlan = all(
        marker in v965_report
        for marker in (
            "`qcwlanstate ON` retry",
            "`IWifi.start` retry",
            "Wi-Fi HAL scan/connect",
        )
    )

    checks = {
        "v998_service_window_clean": v998_service_window_clean,
        "v998_wlfw_missing": v998_wlfw_missing,
        "v998_no_lower_trigger": v998_no_lower_trigger,
        "v966_wlfw_precedes_esoc_get": v966_wlfw_precedes_esoc_get,
        "v968_gpio_transition_unresolved": v968_gpio_transition_unresolved,
        "v968_fallback_condition_now_met": v968_fallback_condition_now_met,
        "v918_blind_subsys_stalls": v918_blind_subsys_stalls,
        "v923_fail_closed_gate": v923_fail_closed_gate,
        "v924_rejects_repeat_subsys": v924_rejects_repeat_subsys,
        "v965_rejects_stale_iwifi_qcwlan": v965_rejects_stale_iwifi_qcwlan,
    }

    if all(checks.values()):
        decision = "v999-select-android-dmesg-gpio-recapture-before-lower-trigger"
        passed = True
        route = "android-positive-control-gpio-esoc-recapture-first"
        reason = (
            "V998 proves the post-SELinux service-window actors are clean but still no WLFW; "
            "V968's fallback condition is now met, while prior blind eSoC and stale IWifi/qcwlanstate retries remain demoted"
        )
        next_step = (
            "V1000 should boot Android temporarily and run a read-only ADB dmesg/eSoC/GPIO recapture first; "
            "Magisk early sampling remains a fallback only if immediate ADB evidence still lacks GPIO135/PMIC9/GPIO142 transition timing"
        )
    else:
        decision = "v999-route-evidence-incomplete"
        passed = False
        route = "repair-host-evidence-before-live"
        missing = ", ".join(name for name, ok in checks.items() if not ok)
        reason = f"required route evidence missing: {missing}"
        next_step = "refresh or reclassify the missing V918/V923/V924/V965/V966/V968/V998 evidence before selecting a live action"

    return {
        "decision": decision,
        "pass": passed,
        "route": route,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "inputs": {
            "v998_manifest": str(repo_path(args.v998_manifest)),
            "v998_report": str(repo_path(args.v998_report)),
            "v998_transcript": str(repo_path(args.v998_transcript)),
            "v966_report": str(repo_path(args.v966_report)),
            "v968_report": str(repo_path(args.v968_report)),
            "v918_report": str(repo_path(args.v918_report)),
            "v923_report": str(repo_path(args.v923_report)),
            "v924_report": str(repo_path(args.v924_report)),
            "v965_report": str(repo_path(args.v965_report)),
        },
        "device_commands_executed": False,
        "device_mutations": False,
        "android_boot_executed": False,
        "adb_command_executed": False,
        "magisk_module_created": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_linkup": False,
        "credentials_used": False,
        "dhcp_routing": False,
        "external_ping": False,
        "subsys_esoc0_open_executed": False,
        "esoc_ioctl_executed": False,
        "gpio_write_executed": False,
        "sysfs_write_executed": False,
        "debugfs_write_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[name, "PASS" if ok else "FAIL"] for name, ok in manifest["checks"].items()]
    input_rows = [[name, path] for name, path in manifest["inputs"].items()]
    return "\n".join(
        [
            "# V999 Post-SELinux WLFW Route Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- route: `{manifest['route']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            "## Checks",
            "",
            markdown_table(["check", "result"], check_rows),
            "",
            "## Inputs",
            "",
            markdown_table(["name", "path"], input_rows),
            "",
            "## Guardrails",
            "",
            "- Host-only classifier.",
            "- No Android boot, ADB command, Magisk module, serial command, actor start, service-manager start, Wi-Fi HAL start, scan/connect, credentials, DHCP, route, external ping, eSoC ioctl, `/dev/subsys_esoc0` open, GPIO/sysfs/debugfs write, boot image write, or partition write.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    classification = classify(args)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        **classification,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"route: {manifest['route']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
