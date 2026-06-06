#!/usr/bin/env python3
"""V1373 host-only classifier for Android/native provider-path parity."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1373-provider-path-parity-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1373-provider-path-parity-classifier.txt")
REPORT_PATH = Path("docs/reports/NATIVE_INIT_V1373_PROVIDER_PATH_PARITY_CLASSIFIER_2026-06-01.md")

V852_REPORT = Path("docs/reports/NATIVE_INIT_V852_ANDROID_EXT_MDM_PROVIDER_SURFACE_HANDOFF_2026-05-25.md")
V1158_REPORT = Path("docs/reports/NATIVE_INIT_V1158_ANDROID_MDM_HELPER_EXTENDED_STRACE_CAPTURE_2026-05-27.md")
V1228_MANIFEST = Path("tmp/wifi/v1228-mdm-helper-early-compact-trace-live/manifest.json")
V1239_MANIFEST = Path("tmp/wifi/v1239-post-esoc0-powerup-gap-classifier/manifest.json")
V1246_MANIFEST = Path("tmp/wifi/v1246-same-run-power-stack-classifier/manifest.json")
V1370_MANIFEST = Path("tmp/wifi/v1370-pci-msm-corrected-rc1-enumerate-live/manifest.json")
V1371_MANIFEST = Path("tmp/wifi/v1371-rc1-ltssm-failure-classifier/manifest.json")
V1372_MANIFEST = Path("tmp/wifi/v1372-provider-held-pcie1-enumerate-live/manifest.json")
V1372_PROVIDER_TRANSCRIPT = Path(
    "tmp/wifi/v1372-provider-held-pcie1-enumerate-live/native/provider-held-case11.txt"
)

INPUTS = {
    "v852_report": V852_REPORT,
    "v1158_report": V1158_REPORT,
    "v1228_manifest": V1228_MANIFEST,
    "v1239_manifest": V1239_MANIFEST,
    "v1246_manifest": V1246_MANIFEST,
    "v1370_manifest": V1370_MANIFEST,
    "v1371_manifest": V1371_MANIFEST,
    "v1372_manifest": V1372_MANIFEST,
    "v1372_provider_transcript": V1372_PROVIDER_TRANSCRIPT,
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path, limit: int = 4 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def get(mapping: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def all_checks_pass(checks: list[dict[str, str]]) -> bool:
    return all(item.get("status") == "pass" for item in checks)


def row_dict(mapping: dict[str, Any]) -> list[list[Any]]:
    return [[key, value] for key, value in mapping.items()]


def classify() -> dict[str, Any]:
    missing = [str(path) for path in INPUTS.values() if not repo_path(path).exists()]
    if missing:
        return {
            "cycle": "V1373",
            "type": "host-only provider-path parity classifier",
            "generated_at": now_iso(),
            "decision": "v1373-inputs-missing",
            "pass": False,
            "reason": "required prior Android/native parity evidence is missing",
            "next_step": "restore V1373 inputs before selecting another live mutation",
            "missing": missing,
            "safety": safety(),
        }

    v852_report = read_text(V852_REPORT)
    v1158_report = read_text(V1158_REPORT)
    v1228 = load_json(V1228_MANIFEST)
    v1239 = load_json(V1239_MANIFEST)
    v1246 = load_json(V1246_MANIFEST)
    v1370 = load_json(V1370_MANIFEST)
    v1371 = load_json(V1371_MANIFEST)
    v1372 = load_json(V1372_MANIFEST)
    v1372_transcript = read_text(V1372_PROVIDER_TRANSCRIPT)

    v1228_trace = v1228.get("mdm_helper_early_compact_trace") or {}
    v1228_boundary = v1228.get("post_esoc_boundary") or {}
    v1239_android = v1239.get("android") or {}
    v1239_native = v1239.get("native") or {}
    v1246_observer = v1246.get("observer") or {}
    v1370_analysis = v1370.get("analysis") or {}
    v1371_deltas = v1371.get("deltas") or {}
    v1372_analysis = v1372.get("analysis") or {}

    android_reference = {
        "v852_positive": "| mdm3 state | `ONLINE`" in v852_report
        and "| `wlan0` | present" in v852_report,
        "v1158_fw_ready": "wifi_ready=1" in v1158_report
        and "icnss: WLAN FW is ready" in v1158_report,
        "v1158_mdm_helper_cmd_engine": "strace_has_cmd_engine_register = true" in v1158_report
        and "strace_has_wait_for_req        = true" in v1158_report,
        "v1158_pm_service_esoc0": "__subsystem_get: esoc0 count:0" in v1158_report,
        "v1371_android_esoc0_to_rc1_sec": v1371_deltas.get("android_esoc0_to_assert_sec"),
        "v1371_android_release_to_l0_sec": v1371_deltas.get("android_release_to_l0_sec"),
        "v1239_android_gpio142_irq": v1239_android.get("gpio142_irq_count"),
        "v1239_android_pcie_l0_lines": v1239_android.get("pcie_l0_lines"),
        "v1239_android_wlan0": v1239_android.get("wlan0_present"),
    }

    native_paths = {
        "v1228_mdm_helper_wait_req": v1228.get("decision") == "v1228-early-wait-for-req-observed-no-ks-mhi"
        and int_value(v1228_trace.get("max_fd_esoc0_count")) > 0
        and int_value(v1228_trace.get("max_fd_mhi_pipe_count")) == 0
        and int_value(v1228_trace.get("wait_for_req_thread_count")) > 0,
        "v1228_pm_service_attempt_no_downstream": bool(v1228_boundary.get("esoc_open_seen"))
        and int_value(v1228_boundary.get("max_dmesg_wlfw_count")) == 0
        and not bool(v1228_boundary.get("wlan0_seen")),
        "v1239_pm_service_gap_after_esoc0": v1239.get("decision")
        == "v1239-gap-is-after-pm-service-esoc0-before-gpio142-pcie-wlfw",
        "v1246_same_run_gdsc_silent": bool(v1246.get("same_gdsc_zero"))
        and bool(v1246.get("same_no_downstream")),
        "v1370_case11_no_l0": v1370.get("decision") == "v1370-corrected-rc1-link-training-no-l0-clean"
        and bool(v1370_analysis.get("pcie_phy_ready_seen"))
        and not bool(v1370_analysis.get("pcie_link_seen")),
        "v1372_raw_provider_case11_no_l0": v1372.get("decision") == "v1372-provider-held-still-no-l0-clean"
        and bool(v1372_analysis.get("holder_block_seen"))
        and not bool(v1372_analysis.get("pcie_l0_seen")),
        "v1372_no_gpio142_pci_mhi_wlan": not bool(v1372_analysis.get("gpio142_seen"))
        and int_value(v1372_analysis.get("pci_device_count")) == 0
        and not bool(v1372_analysis.get("mhi_present"))
        and not bool(v1372_analysis.get("wlan0_seen")),
    }

    coverage = [
        {
            "path": "Android V852/V1158 reference",
            "mdm_helper_cmd_engine": True,
            "pm_service_esoc0": True,
            "provider_holder": True,
            "corrected_case11": False,
            "rc1_l0": True,
            "wlan0": True,
            "meaning": "known-good lower Wi-Fi path; no native credentials/connect involved",
        },
        {
            "path": "Native V1228/V1239/V1246 PM path",
            "mdm_helper_cmd_engine": True,
            "pm_service_esoc0": True,
            "provider_holder": True,
            "corrected_case11": False,
            "rc1_l0": False,
            "wlan0": False,
            "meaning": "Android-like PM actors reach mdm_subsys_powerup, but RC1 remains off/silent",
        },
        {
            "path": "Native V1370 corrected RC1 enumerate",
            "mdm_helper_cmd_engine": False,
            "pm_service_esoc0": False,
            "provider_holder": False,
            "corrected_case11": True,
            "rc1_l0": False,
            "wlan0": False,
            "meaning": "AP-side RC1 enumerate reaches PHY/LTSSM but no endpoint response",
        },
        {
            "path": "Native V1372 raw provider + corrected RC1 enumerate",
            "mdm_helper_cmd_engine": False,
            "pm_service_esoc0": False,
            "provider_holder": True,
            "corrected_case11": True,
            "rc1_l0": False,
            "wlan0": False,
            "meaning": "direct provider holder plus RC1 enumerate still lacks endpoint readiness",
        },
    ]

    checks = [
        {
            "name": "android-positive-reference-still-valid",
            "status": "pass"
            if all(
                [
                    android_reference["v852_positive"],
                    android_reference["v1158_fw_ready"],
                    android_reference["v1239_android_gpio142_irq"] == 1,
                    android_reference["v1239_android_pcie_l0_lines"],
                    android_reference["v1239_android_wlan0"] is True,
                ]
            )
            else "blocked",
            "detail": "Android reaches GPIO142, RC1 L0, FW-ready, and wlan0",
        },
        {
            "name": "android-command-engine-before-lower-success",
            "status": "pass"
            if android_reference["v1158_mdm_helper_cmd_engine"]
            and android_reference["v1158_pm_service_esoc0"]
            else "blocked",
            "detail": "Android has mdm_helper CMD_ENG/WAIT_FOR_REQ plus pm-service esoc0 path",
        },
        {
            "name": "native-pm-actor-path-does-not-enumerate-rc1",
            "status": "pass"
            if native_paths["v1228_mdm_helper_wait_req"]
            and native_paths["v1239_pm_service_gap_after_esoc0"]
            and native_paths["v1246_same_run_gdsc_silent"]
            else "blocked",
            "detail": "native PM path reaches mdm_helper/pm-service but keeps pcie1/GPIO142/WLFW silent",
        },
        {
            "name": "native-manual-rc1-path-lacks-android-participants",
            "status": "pass" if native_paths["v1370_case11_no_l0"] else "blocked",
            "detail": "V1370 exercises corrected RC1 enumerate without provider/PM participants and stops before L0",
        },
        {
            "name": "native-raw-provider-plus-rc1-still-lacks-command-engine",
            "status": "pass"
            if native_paths["v1372_raw_provider_case11_no_l0"]
            and native_paths["v1372_no_gpio142_pci_mhi_wlan"]
            and "mdm_helper" not in v1372_transcript
            and "pm-service" not in v1372_transcript
            else "blocked",
            "detail": "V1372 combines raw provider holder with RC1 enumerate, but not Android mdm_helper/pm-service context",
        },
    ]

    pass_condition = all_checks_pass(checks)
    decision = (
        "v1373-gap-is-android-participant-plus-rc1-combination"
        if pass_condition
        else "v1373-provider-path-parity-incomplete"
    )
    reason = (
        "existing evidence has tested PM actors without corrected RC1 enumerate, corrected RC1 enumerate without PM actors, and raw provider-hold plus corrected RC1 enumerate without Android mdm_helper/pm-service context; the untested narrow combination is Android participant parity plus corrected RC1 enumerate"
        if pass_condition
        else "one or more Android/native parity inputs are missing or contradictory"
    )
    next_step = (
        "V1374 should be a source/build-only design for a bounded live gate that starts mdm_helper/PM actor parity, confirms /dev/esoc-0 and /dev/subsys_esoc0 readiness, then runs corrected rc_sel=2 + case=11 with reboot cleanup; still no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping"
        if pass_condition
        else "repair V1373 inputs before selecting another live mutation"
    )

    return {
        "cycle": "V1373",
        "type": "host-only provider-path parity classifier",
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_condition,
        "reason": reason,
        "next_step": next_step,
        "inputs": {name: str(path) for name, path in INPUTS.items()},
        "checks": checks,
        "android_reference": android_reference,
        "native_paths": native_paths,
        "coverage_matrix": coverage,
        "v1246_first_same_phase": v1246_observer.get("first_same_phase_sample") or {},
        "v1374_candidate": v1374_candidate(pass_condition),
        "safety": safety(),
    }


def safety() -> dict[str, bool]:
    return {
        "host_only": True,
        "device_command_executed": False,
        "device_mutation_executed": False,
        "debugfs_write_executed": False,
        "pm_actor_start_executed": False,
        "subsys_esoc0_open_executed": False,
        "wifi_hal_scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_external_ping_executed": False,
        "flash_boot_partition_write_executed": False,
    }


def v1374_candidate(enabled: bool) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "name": "android-participant-parity-plus-corrected-rc1-enumerate",
        "scope": "source/build-only design first; live gate only after explicit script preflight",
        "rationale": (
            "V1372 proved a raw provider holder is not equivalent to Android's "
            "mdm_helper plus pm-service/per_proxy path. The next narrow test must "
            "combine the Android participant set with the already-proven corrected "
            "RC1 enumerate path, rather than retrying upper Wi-Fi HAL or direct GPIO."
        ),
        "candidate_order": [
            "preflight native selftest fail=0 and debugfs mount state",
            "start only lower Android participant parity needed for mdm_helper CMD_ENG and pm-service esoc0 path",
            "confirm /dev/esoc-0 fd, ESOC_WAIT_FOR_REQ/CMD_ENG evidence, and pm-service /dev/subsys_esoc0 wchan",
            "write only rc_sel=2 then case=11 after the provider window is confirmed",
            "capture GPIO142, LTSSM/L0, PCI/MHI, WLFW/BDF/wlan0 markers, cleanup, and post-selftest",
        ],
        "hard_stops": [
            "no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping",
            "no direct PMIC/GPIO/GDSC writes",
            "no PERST assert/deassert debug cases beyond pci-msm case11's normal enumerate path",
            "no eSoC notify or BOOT_DONE spoof",
            "no flash, boot image write, or partition write",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V1373 Provider-path Parity Classifier",
            "",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            "",
            markdown_table(["check", "status", "detail"], check_rows(manifest.get("checks") or [])),
            "",
        ]
    )


def render_report(manifest: dict[str, Any]) -> str:
    if manifest.get("missing"):
        return "\n".join(
            [
                "# Native Init V1373 Provider-path Parity Classifier",
                "",
                "## Summary",
                "",
                f"- Decision: `{manifest['decision']}`",
                f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
                "",
                "## Missing Inputs",
                "",
                "\n".join(f"- `{item}`" for item in manifest["missing"]),
                "",
            ]
        )
    candidate = manifest["v1374_candidate"]
    return "\n".join(
        [
            "# Native Init V1373 Provider-path Parity Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1373`",
            "- Type: host-only provider-path parity classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Result: {'PASS' if manifest['pass'] else 'FAIL'}",
            "- Script: `scripts/revalidation/native_wifi_provider_path_parity_classifier_v1373.py`",
            "- Evidence:",
            "  - `tmp/wifi/v1373-provider-path-parity-classifier/manifest.json`",
            "  - `tmp/wifi/v1373-provider-path-parity-classifier/summary.md`",
            "",
            "## Decision",
            "",
            manifest["reason"],
            "",
            "## Checks",
            "",
            markdown_table(["check", "status", "detail"], check_rows(manifest["checks"])),
            "",
            "## Coverage Matrix",
            "",
            markdown_table(
                [
                    "path",
                    "mdm_helper CMD",
                    "pm-service esoc0",
                    "provider",
                    "case11",
                    "RC1 L0",
                    "wlan0",
                    "meaning",
                ],
                coverage_rows(manifest["coverage_matrix"]),
            ),
            "",
            "## Android Reference",
            "",
            markdown_table(["field", "value"], row_dict(manifest["android_reference"])),
            "",
            "## Native Paths",
            "",
            markdown_table(["field", "value"], row_dict(manifest["native_paths"])),
            "",
            "## V1246 Same-run Power Snapshot",
            "",
            markdown_table(["field", "value"], row_dict(manifest.get("v1246_first_same_phase") or {})),
            "",
            "## V1374 Candidate",
            "",
            f"- Name: `{candidate['name']}`",
            f"- Scope: {candidate['scope']}",
            f"- Rationale: {candidate['rationale']}",
            "",
            "### Candidate Order",
            "",
            "\n".join(f"- {item}" for item in candidate["candidate_order"]),
            "",
            "### Hard Stops",
            "",
            "\n".join(f"- {item}" for item in candidate["hard_stops"]),
            "",
            "## Safety",
            "",
            "- V1373 is host-only and executes no device command.",
            "- No PM actor start, `/dev/subsys_esoc0` open, debugfs write,",
            "  PMIC/GPIO/GDSC write, eSoC notify/`BOOT_DONE`, Wi-Fi HAL,",
            "  scan/connect, credential handling, DHCP/routes, external ping, flash,",
            "  boot image write, or partition write occurred.",
            "",
            "## Next",
            "",
            manifest["next_step"],
            "",
        ]
    )


def check_rows(checks: list[dict[str, str]]) -> list[list[str]]:
    return [[item["name"], item["status"], item["detail"]] for item in checks]


def coverage_rows(rows: list[dict[str, Any]]) -> list[list[Any]]:
    return [
        [
            item["path"],
            item["mdm_helper_cmd_engine"],
            item["pm_service_esoc0"],
            item["provider_holder"],
            item["corrected_case11"],
            item["rc1_l0"],
            item["wlan0"],
            item["meaning"],
        ]
        for item in rows
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("command", choices=("run",), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = repo_path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = classify()
    manifest["command"] = args.command
    manifest["host"] = collect_host_metadata()
    write_private_text(out_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    write_private_text(out_dir / "summary.md", render_summary(manifest))
    write_private_text(repo_path(REPORT_PATH), render_report(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(out_dir) + "\n")
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"], "out_dir": str(out_dir)}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
