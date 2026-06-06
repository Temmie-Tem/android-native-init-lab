#!/usr/bin/env python3
"""V1013 host-only classifier for the V1012 CNSS/WLFW precondition gap."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1013-v1012-wlfw-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1013-v1012-wlfw-gap-classifier.txt")
DEFAULT_V1012_MANIFEST = Path("tmp/wifi/v1012-after-fd-cnss-service-manager-matrix-live/manifest.json")
DEFAULT_V1008_MANIFEST = Path("tmp/wifi/v1008-android-service-window-fd-poll-live/manifest.json")
DEFAULT_V1000_DMESG = Path(
    "tmp/wifi/v1000-android-esoc-gpio-recapture-handoff-live/"
    "v913-android-esoc-gpio-timeline-run/android/commands/dmesg-full.txt"
)
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")

TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")
EVENT_PATTERNS: dict[str, str] = {
    "wifi_hal_legacy_start": r"init: starting service 'vendor\.wifi_hal_legacy'",
    "wifi_hal_ext_start": r"init: starting service 'vendor\.wifi_hal_ext'",
    "per_mgr_start": r"init: starting service 'vendor\.per_mgr'",
    "wificond_start": r"init: starting service 'wificond'",
    "mdm_helper_start": r"init: starting service 'vendor\.mdm_helper'",
    "cnss_daemon_start": r"init: starting service 'cnss-daemon'",
    "subsys_esoc0_get": r"__subsystem_get\(\):\s+__subsystem_get:\s+esoc0 count:0",
    "wlfw_start": r"cnss-daemon wlfw_start:\s+Starting",
    "wlan_pd": r"msm/modem/wlan_pd, state:",
    "icnss_qmi_connected": r"icnss_qmi:\s+QMI Server Connected",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1012-manifest", type=Path, default=DEFAULT_V1012_MANIFEST)
    parser.add_argument("--v1008-manifest", type=Path, default=DEFAULT_V1008_MANIFEST)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_V1000_DMESG)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    return parser.parse_args()


def read_text(path: Path, limit: int = 8_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def sha256(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    digest = hashlib.sha256()
    with resolved.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_contract(manifest: dict[str, Any]) -> dict[str, str]:
    helper = ((manifest.get("analysis") or {}).get("helper") or {})
    contract = helper.get("contract") or {}
    return {str(key): str(value) for key, value in contract.items()}


def dmesg_time(line: str) -> float | None:
    match = TIME_RE.search(line.strip())
    return float(match.group("time")) if match else None


def first_event(text: str, pattern: str) -> dict[str, Any]:
    regex = re.compile(pattern, re.IGNORECASE)
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("$ "):
            continue
        if regex.search(line):
            return {
                "present": True,
                "line_number": line_number,
                "time": dmesg_time(line),
                "line": line,
            }
    return {"present": False, "line_number": None, "time": None, "line": ""}


def parse_events(text: str) -> dict[str, dict[str, Any]]:
    return {name: first_event(text, pattern) for name, pattern in EVENT_PATTERNS.items()}


def event_time(events: dict[str, dict[str, Any]], name: str) -> float | None:
    value = events.get(name, {}).get("time")
    return float(value) if isinstance(value, int | float) else None


def before(events: dict[str, dict[str, Any]], left: str, right: str) -> bool:
    left_time = event_time(events, left)
    right_time = event_time(events, right)
    return left_time is not None and right_time is not None and left_time < right_time


def delta_ms(events: dict[str, dict[str, Any]], later: str, earlier: str) -> float | None:
    later_time = event_time(events, later)
    earlier_time = event_time(events, earlier)
    if later_time is None or earlier_time is None:
        return None
    return round((later_time - earlier_time) * 1000.0, 3)


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1012_manifest = load_json(args.v1012_manifest)
    v1008_manifest = load_json(args.v1008_manifest)
    v1012 = manifest_contract(v1012_manifest)
    v1008 = manifest_contract(v1008_manifest)
    android_dmesg = read_text(args.android_dmesg)
    source = read_text(args.helper_source)
    events = parse_events(android_dmesg)

    v1012_after_fd_matrix_ok = (
        v1012_manifest.get("decision") == "v1012-reboot-required-cleaned"
        and v1012.get("service_manager_order") == "after-mdm-helper-esoc-fd"
        and v1012.get("mdm_helper_esoc0_fd_seen") == "1"
        and v1012.get("service_manager_started") == "1"
        and v1012.get("cnss_daemon_started") == "1"
    )
    v1012_wlfw_gap = (
        v1012.get("wlfw_precondition_observed") == "0"
        and v1012.get("subsys_esoc0_open_attempted") == "0"
        and v1012.get("post_provider_no_wlfw_trigger_started") == "0"
    )
    v1012_guardrails = all(
        v1012_manifest.get(key) is False
        for key in (
            "wifi_hal_start_executed",
            "scan_connect_executed",
            "credential_use_executed",
            "dhcp_route_executed",
            "external_ping_executed",
            "subsys_esoc0_open_attempted",
        )
    )
    v1008_upper_surface_present_but_fd_missing = (
        v1008_manifest.get("decision") == "v1008-mdm-helper-esoc-fd-missing-no-trigger"
        and v1008.get("wifi_hal_start_executed") == "1"
        and v1008.get("wificond_start_executed") == "1"
        and v1008.get("cnss_daemon_start_executed") == "1"
        and v1008.get("mdm_helper_esoc0_fd_poll_seen") == "0"
    )
    android_positive_surface_order = all(
        events[name]["present"]
        for name in (
            "wifi_hal_legacy_start",
            "wifi_hal_ext_start",
            "wificond_start",
            "mdm_helper_start",
            "cnss_daemon_start",
            "subsys_esoc0_get",
            "wlfw_start",
            "wlan_pd",
            "icnss_qmi_connected",
        )
    )
    android_upper_before_wlfw = all(
        before(events, actor, "wlfw_start")
        for actor in ("wifi_hal_legacy_start", "wifi_hal_ext_start", "wificond_start", "mdm_helper_start", "cnss_daemon_start")
    )
    source_has_upper_actor_contracts = all(
        token in source
        for token in (
            "COMPOSITE_ID_WIFI_HAL",
            "COMPOSITE_ID_WIFICOND",
            "/vendor/bin/hw/android.hardware.wifi@1.0-service",
            "/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service",
            "/system/bin/wificond",
        )
    )
    source_lacks_after_fd_wifi_surface_matrix = "after-mdm-helper-esoc-fd-with-wifi-surface" not in source
    existing_matrix_has_after_fd_lower_order = all(
        token in source
        for token in (
            "wifi-companion-mdm-helper-cnss-service-manager-matrix",
            "after-mdm-helper-esoc-fd",
            "esoc0-fd-gate,servicemanager,hwservicemanager,vndservicemanager,cnss_diag,cnss_daemon",
        )
    )
    cleanup_verified = v1012_manifest.get("cleanup_reboot_executed") is True

    checks = {
        "v1012_input_present": bool(v1012_manifest),
        "v1008_input_present": bool(v1008_manifest),
        "android_dmesg_present": bool(android_dmesg),
        "v1012_after_fd_matrix_ok": v1012_after_fd_matrix_ok,
        "v1012_wlfw_gap_confirmed": v1012_wlfw_gap,
        "v1012_guardrails_clean": v1012_guardrails,
        "v1012_cleanup_verified": cleanup_verified,
        "v1008_upper_surface_present_but_fd_missing": v1008_upper_surface_present_but_fd_missing,
        "android_positive_surface_order": android_positive_surface_order,
        "android_upper_surface_before_wlfw": android_upper_before_wlfw,
        "source_has_upper_actor_contracts": source_has_upper_actor_contracts,
        "source_has_after_fd_lower_matrix": existing_matrix_has_after_fd_lower_order,
        "source_lacks_after_fd_wifi_surface_matrix": source_lacks_after_fd_wifi_surface_matrix,
    }

    if all(checks.values()):
        decision = "v1013-select-after-fd-wifi-surface-matrix-support"
        passed = True
        route = "v1014-source-build-helper-v172-after-fd-dual-hal-wificond-matrix"
        reason = (
            "V1012 proves fd+service-manager+CNSS is insufficient, while Android positive evidence has "
            "dual Wi-Fi HAL and wificond before WLFW; V1008 proves those upper actors without the fd predicate are also insufficient"
        )
        next_step = (
            "Add helper v172 support for an after-mdm-helper-esoc-fd Wi-Fi surface matrix that preserves the fd predicate, "
            "then starts service-manager, Wi-Fi HAL legacy/ext, wificond, CNSS, and only observes WLFW without scan/connect"
        )
    elif v1012_after_fd_matrix_ok and v1012_wlfw_gap:
        decision = "v1013-wlfw-gap-confirmed-route-inputs-incomplete"
        passed = True
        route = "refresh-android-upper-surface-evidence"
        reason = "V1012 gap is proven, but Android/source evidence is not strong enough to choose the next upper actor"
        next_step = "Refresh Android dmesg/source evidence before adding Wi-Fi HAL or wificond to the after-fd matrix"
    else:
        missing = ", ".join(name for name, ok in checks.items() if not ok)
        decision = "v1013-wlfw-gap-evidence-incomplete"
        passed = False
        route = "repair-evidence-before-helper-change"
        reason = f"required evidence missing or contradictory: {missing}"
        next_step = "Recreate V1012 or Android timing evidence before changing helper behavior"

    return {
        "decision": decision,
        "pass": passed,
        "route": route,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "android_timing": {
            "events": {name: {"present": event["present"], "time": event["time"], "line_number": event["line_number"]} for name, event in events.items()},
            "deltas_ms": {
                "wifi_hal_legacy_to_mdm_helper": delta_ms(events, "mdm_helper_start", "wifi_hal_legacy_start"),
                "wifi_hal_ext_to_mdm_helper": delta_ms(events, "mdm_helper_start", "wifi_hal_ext_start"),
                "wificond_to_mdm_helper": delta_ms(events, "mdm_helper_start", "wificond_start"),
                "mdm_helper_to_cnss_daemon": delta_ms(events, "cnss_daemon_start", "mdm_helper_start"),
                "cnss_daemon_to_wlfw": delta_ms(events, "wlfw_start", "cnss_daemon_start"),
                "subsys_esoc0_get_to_wlfw": delta_ms(events, "wlfw_start", "subsys_esoc0_get"),
            },
        },
        "v1012": {
            "decision": v1012_manifest.get("decision"),
            "result": v1012.get("result"),
            "mdm_helper_esoc0_fd_seen": v1012.get("mdm_helper_esoc0_fd_seen"),
            "service_manager_started": v1012.get("service_manager_started"),
            "cnss_daemon_started": v1012.get("cnss_daemon_started"),
            "wlfw_precondition_observed": v1012.get("wlfw_precondition_observed"),
            "subsys_esoc0_open_attempted": v1012.get("subsys_esoc0_open_attempted"),
            "cleanup_reboot_executed": v1012_manifest.get("cleanup_reboot_executed"),
        },
        "v1008": {
            "decision": v1008_manifest.get("decision"),
            "result": v1008.get("result"),
            "wifi_hal_start_executed": v1008.get("wifi_hal_start_executed"),
            "wificond_start_executed": v1008.get("wificond_start_executed"),
            "cnss_daemon_start_executed": v1008.get("cnss_daemon_start_executed"),
            "mdm_helper_esoc0_fd_poll_seen": v1008.get("mdm_helper_esoc0_fd_poll_seen"),
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    checks = classification["checks"]
    timing = classification["android_timing"]
    return "\n".join(
        [
            "# V1013 V1012 WLFW Gap Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{classification['decision']}`",
            f"- pass: `{classification['pass']}`",
            f"- route: `{classification['route']}`",
            f"- reason: {classification['reason']}",
            f"- next: {classification['next_step']}",
            "",
            "## Inputs",
            "",
            markdown_table(
                ["input", "path", "exists", "sha256"],
                [
                    (name, payload["path"], str(payload["exists"]), payload["sha256"])
                    for name, payload in manifest["inputs"].items()
                ],
            ),
            "",
            "## Checks",
            "",
            markdown_table(["check", "pass"], [(name, str(value)) for name, value in checks.items()]),
            "",
            "## Android Timing",
            "",
            markdown_table(
                ["event", "present", "time_s", "line"],
                [
                    (name, str(event["present"]), "" if event["time"] is None else f"{event['time']:.6f}", str(event["line_number"] or ""))
                    for name, event in timing["events"].items()
                ],
            ),
            "",
            "## Derived Deltas",
            "",
            markdown_table(
                ["delta", "ms"],
                [(name, "" if value is None else str(value)) for name, value in timing["deltas_ms"].items()],
            ),
            "",
            "## V1012 / V1008 Split",
            "",
            "```json",
            json.dumps({"v1012": classification["v1012"], "v1008": classification["v1008"]}, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    inputs = {
        "v1012_manifest": args.v1012_manifest,
        "v1008_manifest": args.v1008_manifest,
        "android_dmesg": args.android_dmesg,
        "helper_source": args.helper_source,
    }
    classification = classify(args)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "host_only": True,
        "device_commands_executed": False,
        "device_mutations": False,
        "native_live_executed": False,
        "android_live_executed": False,
        "classification": classification,
        "inputs": {
            name: {
                "path": str(repo_path(path)),
                "exists": repo_path(path).exists(),
                "sha256": sha256(path),
                "bytes": repo_path(path).stat().st_size if repo_path(path).exists() else 0,
            }
            for name, path in inputs.items()
        },
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {classification['decision']}")
    print(f"pass: {classification['pass']}")
    print(f"route: {classification['route']}")
    print(f"reason: {classification['reason']}")
    print(f"next: {classification['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if classification["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
