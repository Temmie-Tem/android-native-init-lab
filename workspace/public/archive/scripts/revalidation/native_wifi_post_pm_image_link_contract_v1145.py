#!/usr/bin/env python3
"""V1145 host-only classifier for the post-PM mdm_helper/ks image-link gap.

This script reconciles the current V1143/V1144 post-PM eSoC wait evidence with
older Android-positive and native-negative mdm_helper/ks/MHI evidence. It does
not contact the device, start actors, open eSoC/subsys nodes, run Wi-Fi HAL,
scan/connect, use credentials, run DHCP/routes, external ping, or write
boot/partitions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1145-post-pm-image-link-contract")
LATEST_POINTER = Path("tmp/wifi/latest-v1145-post-pm-image-link-contract.txt")

DEFAULT_V1144 = Path("tmp/wifi/v1144-esoc-wait-ioctl-contract/manifest.json")
DEFAULT_V1143 = Path("tmp/wifi/v1143-post-pm-lower-trace-live/manifest.json")
DEFAULT_V900 = Path("tmp/wifi/v900-mdm-helper-ks-contract-live/manifest.json")
DEFAULT_V938 = Path("tmp/wifi/v938-mdm-helper-lower-contract-capture-live/manifest.json")
DEFAULT_V939 = Path("tmp/wifi/v939-v938-lower-contract-classifier/manifest.json")
DEFAULT_V1024 = Path("tmp/wifi/v1024-fast-fd-contract-classifier/manifest.json")
DEFAULT_V968 = Path("tmp/wifi/v968-android-dmesg-esoc-gpio-timing/manifest.json")
DEFAULT_V896_REPORT = Path("docs/reports/NATIVE_INIT_V896_ANDROID_MDM_HELPER_IMAGE_CONTRACT_2026-05-26.md")
DEFAULT_V904_REPORT = Path("docs/reports/NATIVE_INIT_V904_MDM_HELPER_RUNTIME_INPUT_PARITY_2026-05-26.md")
DEFAULT_V1024_REPORT = Path("docs/reports/NATIVE_INIT_V1024_FAST_FD_CONTRACT_CLASSIFIER_2026-05-26.md")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1144", type=Path, default=DEFAULT_V1144)
    parser.add_argument("--v1143", type=Path, default=DEFAULT_V1143)
    parser.add_argument("--v900", type=Path, default=DEFAULT_V900)
    parser.add_argument("--v938", type=Path, default=DEFAULT_V938)
    parser.add_argument("--v939", type=Path, default=DEFAULT_V939)
    parser.add_argument("--v1024", type=Path, default=DEFAULT_V1024)
    parser.add_argument("--v968", type=Path, default=DEFAULT_V968)
    parser.add_argument("--v896-report", type=Path, default=DEFAULT_V896_REPORT)
    parser.add_argument("--v904-report", type=Path, default=DEFAULT_V904_REPORT)
    parser.add_argument("--v1024-report", type=Path, default=DEFAULT_V1024_REPORT)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    return parser.parse_args()


def read_text(path: Path, limit: int = 4_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ok"}


def intish(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return 0
    try:
        return int(text, 0)
    except ValueError:
        return 0


def nested_get(data: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = data
    for item in path:
        if not isinstance(current, dict):
            return default
        current = current.get(item)
    return default if current is None else current


def dictish(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def summarize_current(v1144: dict[str, Any], v1143: dict[str, Any]) -> dict[str, Any]:
    v1144_flags = dictish(nested_get(v1144, ("analysis", "classification", "flags"), {}))
    lower = dictish(nested_get(v1143, ("analysis", "tracefs_uprobe", "post_pm_mdm_helper_lower_trace"), {}))
    sample_count = len({key.split(".", 1)[0] for key in lower if key.startswith("sample_") and key.endswith(".alive")})
    return {
        "v1144_decision": v1144.get("decision", ""),
        "v1144_pass": bool(v1144.get("pass")),
        "v1143_decision": v1143.get("decision", ""),
        "v1143_pass": bool(v1143.get("pass")),
        "esoc_wait_classified": boolish(v1144_flags.get("ioctl_decoded_as_esoc_wait_for_req")),
        "samples_stable": boolish(v1144_flags.get("all_samples_stable_esoc_wait")),
        "sample_count": sample_count,
        "mdm3_after_observer": nested_get(v1143, ("analysis", "global_firmware", "mdm3_after_observer"), ""),
        "mss_after_observer": nested_get(v1143, ("analysis", "global_firmware", "mss_after_observer"), ""),
        "subsys_open_attempted": boolish(v1143.get("subsys_esoc0_open_attempted", False))
        or any(str(value) == "1" for key, value in lower.items() if key.endswith("subsys_esoc0_open_attempted")),
        "wifi_hal_start_executed": bool(v1143.get("wifi_hal_start_executed")),
        "scan_connect_executed": bool(v1143.get("scan_connect_executed")),
        "credential_use_executed": bool(v1143.get("credential_use_executed")),
        "dhcp_route_executed": bool(v1143.get("dhcp_route_executed")),
        "external_ping_executed": bool(v1143.get("external_ping_executed")),
    }


def summarize_v900(manifest: dict[str, Any]) -> dict[str, Any]:
    contract = dictish(nested_get(manifest, ("analysis", "helper", "contract"), {}))
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "mode": manifest.get("mode", ""),
        "mdm_helper_observable": boolish(contract.get("mdm_helper_observable")),
        "subsys_trigger_started": boolish(contract.get("subsys_trigger.started")),
        "subsys_open_attempted": bool(manifest.get("subsys_esoc0_open_attempted"))
        or boolish(contract.get("subsys_esoc0_open_attempted")),
        "trigger_reaped": boolish(contract.get("subsys_trigger.reaped")),
        "ks_count_window": intish(contract.get("ks_count.window")),
        "mhi_pipe_cmdline_count_window": intish(contract.get("mhi_pipe_cmdline_count.window")),
        "result": contract.get("result", ""),
        "reason": contract.get("reason", ""),
        "cleanup_reboot_executed": bool(manifest.get("cleanup_reboot_executed")),
    }


def summarize_v938(manifest: dict[str, Any]) -> dict[str, Any]:
    contract = dictish(nested_get(manifest, ("analysis", "helper", "contract"), {}))
    lower = dictish(nested_get(manifest, ("analysis", "helper", "lower_contract"), {}))
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "mdm_helper_start_executed": bool(manifest.get("mdm_helper_start_executed")),
        "per_mgr_light_start_executed": bool(manifest.get("per_mgr_light_start_executed")),
        "result": contract.get("result", ""),
        "fd_esoc0_count_final": intish(contract.get("fd_esoc0_count.final")),
        "fd_subsys_esoc0_count_final": intish(contract.get("fd_subsys_esoc0_count.final")),
        "fd_mhi_pipe_count_final": intish(contract.get("fd_mhi_pipe_count.final")),
        "ks_count_window": intish(contract.get("ks_count.window")),
        "unable_to_queue_sdx50m_count": sum(
            1 for value in lower.values()
            if "unable to queue event for SDX50M" in str(value)
        ),
        "subsys_open_attempted": bool(manifest.get("subsys_esoc0_open_attempted")),
    }


def summarize_v939(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "next_step": manifest.get("next_step", ""),
    }


def summarize_android(v1024: dict[str, Any], v968: dict[str, Any], report_texts: dict[str, str]) -> dict[str, Any]:
    early_fd = dictish(nested_get(v1024, ("classification", "early", "fd"), {}))
    late_chain = dictish(nested_get(v1024, ("classification", "late", "chain"), {}))
    v968_events = dictish(nested_get(v968, ("classification", "events"), {}))
    return {
        "v1024_decision": v1024.get("decision", ""),
        "v1024_pass": bool(v1024.get("pass")),
        "pm_proxy_helper_subsys_modem_fd": boolish(early_fd.get("pm_proxy_helper_subsys_modem_fd")),
        "pm_service_subsys_modem_fd": boolish(early_fd.get("pm_service_subsys_modem_fd")),
        "mdm_helper_esoc0_fd": boolish(early_fd.get("mdm_helper_esoc0_fd")),
        "wlfw_chain": boolish(late_chain.get("wlfw_chain")),
        "wlfw_start": late_chain.get("wlfw_start"),
        "subsys_esoc0_get": late_chain.get("subsys_esoc0_get"),
        "fw_ready": late_chain.get("fw_ready"),
        "wlan0": late_chain.get("wlan0"),
        "v968_decision": nested_get(v968, ("classification", "decision"), ""),
        "v968_pass": boolish(nested_get(v968, ("classification", "pass"), False)),
        "v968_wlfw_to_subsys_ms": nested_get(v968, ("classification", "answers", "wlfw_start_to_esoc0_get_ms"), None),
        "v968_has_wlfw_start_event": bool(v968_events.get("wlfw_start")),
        "v968_has_subsys_get_event": bool(v968_events.get("esoc0_subsystem_get")),
        "v968_has_wlan0_event": bool(v968_events.get("wlan0_event")),
        "v896_report_positive": all(
            needle in report_texts["v896"]
            for needle in (
                "mdm3=ONLINE",
                "`mdm_helper` holds `/dev/esoc-0",
                "`ks` uses `/dev/mhi_0305_01.01.00_pipe_10",
                "WLFW, BDF, WLAN-PD, and `wlan0`",
            )
        ),
        "v904_runtime_delta_recorded": all(
            needle in report_texts["v904"]
            for needle in (
                "SELinux context mismatch",
                "peripheral-manager mismatch",
                "Android `pm-service` owns subsystem nodes",
            )
        ),
        "v1024_report_positive": (
            "The same handoff's late sampler captured the WLFW/FW-ready/`wlan0` chain" in report_texts["v1024"]
            and "pm_proxy_helper` | `/dev/subsys_modem`" in report_texts["v1024"]
        ),
    }


def helper_features(text: str) -> dict[str, Any]:
    return {
        "post_pm_mode_present": "wifi-companion-post-pm-mdm-helper-esoc-observer" in text,
        "post_pm_lower_trace_flag_present": "--allow-post-pm-mdm-helper-lower-trace" in text,
        "ks_image_contract_mode_present": "wifi-companion-mdm-helper-ks-image-contract-preflight" in text,
        "ks_expected_cmdline_literal": "/vendor/bin/ks /dev/mhi_0305_01.01.00_pipe_10 -w /dev/block/bootdevice/by-name/ -t -1 -l -g mdm1" in text,
        "subsys_trigger_in_ks_mode": "mdm_helper_ks_image_contract.subsys_esoc0_open_attempted=1" in text,
        "post_pm_req_img_verifier_mode_present": "wifi-companion-post-pm-mdm-helper-esoc-req-img-verifier" in text,
        "post_pm_subsys_trigger_flag_present": "--allow-post-pm-esoc-req-img-verifier" in text,
    }


def classify(analysis: dict[str, Any]) -> dict[str, Any]:
    current = analysis["current"]
    android = analysis["android"]
    v900 = analysis["v900"]
    v938 = analysis["v938"]
    v939 = analysis["v939"]
    helper = analysis["helper_features"]
    guardrails_clean = not any(
        current[key]
        for key in (
            "wifi_hal_start_executed",
            "scan_connect_executed",
            "credential_use_executed",
            "dhcp_route_executed",
            "external_ping_executed",
        )
    )
    flags = {
        "current_post_pm_esoc_wait_classified": (
            current["v1144_pass"]
            and current["v1144_decision"] == "v1144-post-pm-esoc-wait-ioctl-contract-classified"
            and current["esoc_wait_classified"]
            and current["samples_stable"]
            and current["subsys_open_attempted"] is False
        ),
        "android_pm_fd_and_wlfw_chain_positive": (
            android["v1024_pass"]
            and android["v1024_decision"] == "v1024-android-pm-esoc-fd-contract-captured"
            and android["pm_proxy_helper_subsys_modem_fd"]
            and android["pm_service_subsys_modem_fd"]
            and android["mdm_helper_esoc0_fd"]
            and android["wlfw_chain"]
            and android["v1024_report_positive"]
        ),
        "android_dmesg_order_positive": (
            android["v968_pass"]
            and android["v968_has_wlfw_start_event"]
            and android["v968_has_subsys_get_event"]
            and android["v968_has_wlan0_event"]
        ),
        "android_image_link_contract_positive": android["v896_report_positive"],
        "old_mdm_helper_before_subsys_insufficient": (
            v900["pass"]
            and v900["decision"] == "v900-reboot-required-cleaned"
            and v900["mdm_helper_observable"]
            and v900["subsys_open_attempted"]
            and v900["ks_count_window"] == 0
            and v900["mhi_pipe_cmdline_count_window"] == 0
            and v900["cleanup_reboot_executed"]
        ),
        "runtime_surface_reaches_esoc0_but_no_ks": (
            v938["pass"]
            and v938["decision"] == "v938-mdm-helper-lower-contract-captured"
            and v938["fd_esoc0_count_final"] > 0
            and v938["fd_mhi_pipe_count_final"] == 0
            and v938["ks_count_window"] == 0
        ),
        "property_context_not_next_blocker": (
            v939["pass"]
            and v939["decision"] == "v939-exact-property-context-gap-not-sufficient"
        ),
        "helper_has_split_modes_only": (
            helper["post_pm_mode_present"]
            and helper["post_pm_lower_trace_flag_present"]
            and helper["ks_image_contract_mode_present"]
            and helper["ks_expected_cmdline_literal"]
            and not helper["post_pm_req_img_verifier_mode_present"]
        ),
        "guardrails_clean": guardrails_clean,
    }
    required = list(flags)
    missing = [name for name in required if not flags[name]]
    if not missing:
        return {
            "decision": "v1145-select-post-pm-esoc-req-img-verifier-build",
            "pass": True,
            "reason": (
                "current post-PM path reaches mdm_helper ESOC_WAIT_FOR_REQ, while Android-positive evidence "
                "requires the PM fd plus mdm_helper/ks/MHI image-link chain; existing helper modes are split "
                "between post-PM observation and older mdm_helper-before-subsys trigger"
            ),
            "next_step": (
                "V1146 should be source/build-only: add a fail-closed post-PM eSoC request verifier mode "
                "that confirms mdm_helper ESOC_WAIT_FOR_REQ before any bounded /dev/subsys_esoc0 trigger and "
                "captures ks/MHI/mdm3/WLFW without HAL, scan/connect, credentials, DHCP, routes, or external ping"
            ),
            "flags": flags,
            "missing": [],
        }
    return {
        "decision": "v1145-post-pm-image-link-input-incomplete",
        "pass": False,
        "reason": "missing=" + ",".join(missing),
        "next_step": "refresh missing Android/native image-link evidence before implementing a new live gate",
        "flags": flags,
        "missing": missing,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rows = [
        ["current V1144", analysis["current"]["v1144_decision"], str(analysis["current"]["esoc_wait_classified"])],
        ["current subsys trigger", str(analysis["current"]["subsys_open_attempted"]), "must stay false in V1145"],
        ["Android PM fd", analysis["android"]["v1024_decision"], str(analysis["android"]["pm_proxy_helper_subsys_modem_fd"])],
        ["Android WLFW chain", str(analysis["android"]["wlfw_chain"]), f"wlan0={analysis['android']['wlan0']}"],
        ["old ks contract live", analysis["v900"]["decision"], f"ks={analysis['v900']['ks_count_window']} mhi={analysis['v900']['mhi_pipe_cmdline_count_window']}"],
        ["V938 lower capture", analysis["v938"]["decision"], f"esoc0={analysis['v938']['fd_esoc0_count_final']} ks={analysis['v938']['ks_count_window']}"],
        ["V939 property classifier", analysis["v939"]["decision"], "property override not selected"],
        ["helper current modes", "split", str(analysis["classification"]["flags"]["helper_has_split_modes_only"])],
    ]
    helper_rows = [[key, str(value)] for key, value in analysis["helper_features"].items()]
    flag_rows = [[key, str(value)] for key, value in analysis["classification"]["flags"].items()]
    return "\n".join(
        [
            "# V1145 Post-PM Image-Link Contract Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            "",
            "## Evidence Matrix",
            "",
            markdown_table(["item", "state", "detail"], rows),
            "",
            "## Helper Feature Surface",
            "",
            markdown_table(["feature", "value"], helper_rows),
            "",
            "## Classification Flags",
            "",
            markdown_table(["flag", "value"], flag_rows),
            "",
            "## Safety",
            "",
            "- device commands executed: `false`",
            "- actor start / eSoC ioctl / `/dev/subsys_esoc0` open: `false`",
            "- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping: `false`",
            "- boot image/partition writes/flash: `false`",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    report_texts = {
        "v896": read_text(args.v896_report),
        "v904": read_text(args.v904_report),
        "v1024": read_text(args.v1024_report),
    }
    helper_text = read_text(args.helper_source)
    analysis = {
        "current": summarize_current(load_json(args.v1144), load_json(args.v1143)),
        "v900": summarize_v900(load_json(args.v900)),
        "v938": summarize_v938(load_json(args.v938)),
        "v939": summarize_v939(load_json(args.v939)),
        "android": summarize_android(load_json(args.v1024), load_json(args.v968), report_texts),
        "helper_features": helper_features(helper_text),
    }
    classification = classify(analysis)
    analysis["classification"] = classification
    manifest = {
        "cycle": "v1145",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1144": str(repo_path(args.v1144)),
            "v1143": str(repo_path(args.v1143)),
            "v900": str(repo_path(args.v900)),
            "v938": str(repo_path(args.v938)),
            "v939": str(repo_path(args.v939)),
            "v1024": str(repo_path(args.v1024)),
            "v968": str(repo_path(args.v968)),
            "v896_report": str(repo_path(args.v896_report)),
            "v904_report": str(repo_path(args.v904_report)),
            "v1024_report": str(repo_path(args.v1024_report)),
            "helper_source": str(repo_path(args.helper_source)),
        },
        "analysis": analysis,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "device_commands_executed": False,
        "device_mutations": False,
        "actor_start_executed": False,
        "live_esoc_ioctl_executed": False,
        "subsys_esoc0_open_attempted": False,
        "tracefs_write_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
