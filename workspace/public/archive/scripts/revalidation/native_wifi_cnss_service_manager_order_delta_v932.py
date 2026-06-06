#!/usr/bin/env python3
"""V932 host-only CNSS/service-manager order delta classifier.

Compares existing V927, V603/V601, and V931 evidence to choose the next bounded
CNSS/service-manager matrix order. This script is host-only: it reads existing
private evidence and does not contact the device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v932-cnss-service-manager-order-delta")
LATEST_POINTER = Path("tmp/wifi/latest-v932-cnss-service-manager-order-delta.txt")
DEFAULT_V927_MANIFEST = Path("tmp/wifi/v927-mdm-helper-cnss-before-esoc-compact-live/manifest.json")
DEFAULT_V927_DMESG = Path("tmp/wifi/v927-mdm-helper-cnss-before-esoc-compact-live/native/post-dmesg-wifi-esoc-tail.txt")
DEFAULT_V601_MANIFEST = Path("tmp/wifi/v601-modem-holder-service-manager/manifest.json")
DEFAULT_V603_MANIFEST = Path("tmp/wifi/v603-qrtr-first-service-manager-live/manifest.json")
DEFAULT_V931_MANIFEST = Path("tmp/wifi/v931-cnss-service-manager-matrix-live/manifest.json")
DEFAULT_V931_DMESG = Path("tmp/wifi/v931-cnss-service-manager-matrix-live/native/post-dmesg-wifi-esoc-tail.txt")
DEFAULT_V914_MANIFEST = Path("tmp/wifi/v914-v913-android-timeline-reclassifier/manifest.json")


DMESG_PATTERNS = {
    "binder_transaction_failed": r"cnss-daemon.*(?:transaction failed|returned -22|ioctl .*40046210)",
    "cnss_cld80211": r"cnss.*cld80211",
    "service_notifier_180": r"service-notifier.*180|service 180|msm/modem/wlan_pd",
    "service_notifier_74": r"service-notifier.*74|service 74",
    "wlfw_start": r"cnss-daemon.*wlfw_start|wlfw_start:\s*Starting",
    "bdf": r"BDF file|bdwlan\.bin|regdb\.bin",
    "wlan0": r"\bwlan0\b",
}


@dataclass(frozen=True)
class OrderCase:
    label: str
    source: str
    decision: str
    pass_ok: bool
    order: str
    service_manager: bool
    service_manager_phase: str
    mdm_helper_esoc0_fd: bool
    binder_failures: int
    cnss_cld80211: int
    service_notifier_180: int
    service_notifier_74: int
    wlfw_start: int
    bdf: int
    wlan0: int
    wlfw_precondition_observed: bool
    subsys_esoc0_open_attempted: bool
    cleanup_reboot: bool
    guardrail_clean: bool


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v927-manifest", type=Path, default=DEFAULT_V927_MANIFEST)
    parser.add_argument("--v927-dmesg", type=Path, default=DEFAULT_V927_DMESG)
    parser.add_argument("--v601-manifest", type=Path, default=DEFAULT_V601_MANIFEST)
    parser.add_argument("--v603-manifest", type=Path, default=DEFAULT_V603_MANIFEST)
    parser.add_argument("--v931-manifest", type=Path, default=DEFAULT_V931_MANIFEST)
    parser.add_argument("--v931-dmesg", type=Path, default=DEFAULT_V931_DMESG)
    parser.add_argument("--v914-manifest", type=Path, default=DEFAULT_V914_MANIFEST)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8", errors="replace")


def count_lines(text: str, pattern: str) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    return sum(1 for line in text.splitlines() if regex.search(line))


def dmesg_counts(text: str) -> dict[str, int]:
    return {key: count_lines(text, pattern) for key, pattern in DMESG_PATTERNS.items()}


def contract(manifest: dict[str, Any]) -> dict[str, Any]:
    return (((manifest.get("analysis") or {}).get("helper") or {}).get("contract") or {})


def bool_manifest(manifest: dict[str, Any], key: str) -> bool:
    return bool(manifest.get(key))


def bool_contract(data: dict[str, Any], key: str) -> bool:
    return str(data.get(key) or "0") == "1"


def guardrail_clean(manifest: dict[str, Any]) -> bool:
    forbidden = (
        "wifi_hal_start_executed",
        "scan_connect_executed",
        "credential_use_executed",
        "dhcp_route_executed",
        "external_ping_executed",
        "wifi_bringup_executed",
        "notify_attempted",
        "boot_done_attempted",
    )
    return not any(bool_manifest(manifest, key) for key in forbidden)


def case_from_matrix_manifest(
    label: str,
    manifest_path: Path,
    dmesg_path: Path,
    default_order: str,
    default_phase: str,
) -> OrderCase:
    manifest = load_json(manifest_path)
    data = contract(manifest)
    counts = dmesg_counts(read_text(dmesg_path))
    return OrderCase(
        label=label,
        source=str(manifest_path),
        decision=str(manifest.get("decision")),
        pass_ok=bool(manifest.get("pass")),
        order=str(data.get("service_manager_order") or default_order),
        service_manager=bool_manifest(manifest, "service_manager_start_executed")
        or bool_contract(data, "service_manager_start_executed"),
        service_manager_phase=str(data.get("service_manager_start_phase") or default_phase),
        mdm_helper_esoc0_fd=bool_contract(data, "mdm_helper_esoc0_fd_seen"),
        binder_failures=counts["binder_transaction_failed"],
        cnss_cld80211=counts["cnss_cld80211"],
        service_notifier_180=counts["service_notifier_180"],
        service_notifier_74=counts["service_notifier_74"],
        wlfw_start=counts["wlfw_start"],
        bdf=counts["bdf"],
        wlan0=counts["wlan0"],
        wlfw_precondition_observed=bool_manifest(manifest, "wlfw_precondition_observed")
        or bool_contract(data, "wlfw_precondition_observed"),
        subsys_esoc0_open_attempted=bool_manifest(manifest, "subsys_esoc0_open_attempted")
        or bool_contract(data, "subsys_esoc0_open_attempted"),
        cleanup_reboot=bool_manifest(manifest, "cleanup_reboot_executed"),
        guardrail_clean=guardrail_clean(manifest),
    )


def case_from_service_manager_manifest(label: str, manifest_path: Path) -> OrderCase:
    manifest = load_json(manifest_path)
    live = manifest.get("live") or {}
    counts = live.get("v603_counts") or live.get("v601_counts") or {}
    service_manager = live.get("service_manager") or {}
    return OrderCase(
        label=label,
        source=str(manifest_path),
        decision=str(manifest.get("decision")),
        pass_ok=bool(manifest.get("pass")),
        order=str(service_manager.get("order") or "service-manager-before-cnss"),
        service_manager=bool(manifest.get("service_manager_start_executed")),
        service_manager_phase="before-cnss",
        mdm_helper_esoc0_fd=False,
        binder_failures=int(counts.get("binder_transaction_failed") or 0),
        cnss_cld80211=0,
        service_notifier_180=int(counts.get("service_notifier_180") or 0),
        service_notifier_74=int(counts.get("service_notifier_74") or 0),
        wlfw_start=int(counts.get("wlfw_start") or 0),
        bdf=int(counts.get("bdf") or 0),
        wlan0=int(counts.get("wlan0") or 0),
        wlfw_precondition_observed=False,
        subsys_esoc0_open_attempted=False,
        cleanup_reboot=bool((live.get("reboot_cleanup") or {}).get("status_healthy")),
        guardrail_clean=not any(
            bool(manifest.get(key))
            for key in (
                "wifi_hal_start_executed",
                "scan_connect_executed",
                "external_ping_executed",
                "wifi_bringup_executed",
                "wlan_driver_state_write_executed",
            )
        ),
    )


def score_cases(cases: list[OrderCase]) -> dict[str, Any]:
    by_label = {case.label: case for case in cases}
    v927 = by_label["v927-no-service-manager"]
    v603 = by_label["v603-qrtr-first-service-manager"]
    v931 = by_label["v931-after-mdm-helper-esoc-fd"]
    binder_reduction = v927.binder_failures - v931.binder_failures
    return {
        "v927_has_lower_fd_but_binder_fails": v927.mdm_helper_esoc0_fd
        and not v927.service_manager
        and v927.binder_failures > 0
        and v927.wlfw_start == 0,
        "v603_service_manager_clears_binder_but_loses_lower_publication": v603.service_manager
        and v603.binder_failures == 0
        and v603.service_notifier_180 == 0
        and v603.wlfw_start == 0,
        "v931_preserves_lower_fd_but_binder_still_fails": v931.service_manager
        and v931.mdm_helper_esoc0_fd
        and v931.binder_failures > 0
        and v931.wlfw_start == 0,
        "v931_binder_failure_reduction_vs_v927": binder_reduction,
        "v931_binder_failure_reduction_ratio": round(binder_reduction / v927.binder_failures, 3)
        if v927.binder_failures
        else None,
        "all_guardrails_clean": all(case.guardrail_clean for case in cases),
    }


def decide(cases: list[OrderCase], scores: dict[str, Any]) -> tuple[str, bool, str, str]:
    if not scores["all_guardrails_clean"]:
        return (
            "v932-order-delta-guardrail-review",
            False,
            "one or more inputs report forbidden Wi-Fi/HAL/network mutation",
            "audit input manifests before any further live matrix",
        )
    if (
        scores["v927_has_lower_fd_but_binder_fails"]
        and scores["v603_service_manager_clears_binder_but_loses_lower_publication"]
        and scores["v931_preserves_lower_fd_but_binder_still_fails"]
    ):
        return (
            "v932-select-before-cnss-matrix-live",
            True,
            (
                "V931 proved after-mdm-helper-esoc-fd preserves the mdm_helper /dev/esoc-0 window, "
                "but Binder failures remain. V603/V601 show service managers can clear Binder when "
                "started before CNSS. The remaining untested intersection is the v154 before-cnss "
                "matrix order: service managers first, then pm-service/mdm_helper, then CNSS."
            ),
            (
                "run V933 with helper v154 --service-manager-order before-cnss; keep WLFW-precondition "
                "gate and continue blocking Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping"
            ),
        )
    return (
        "v932-order-delta-review",
        False,
        f"scores={scores}",
        "inspect order matrix inputs before choosing another live order",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    cases = [
        case_from_matrix_manifest(
            "v927-no-service-manager",
            args.v927_manifest,
            args.v927_dmesg,
            "none",
            "none",
        ),
        case_from_service_manager_manifest(
            "v601-service-manager-before-cnss",
            args.v601_manifest,
        ),
        case_from_service_manager_manifest(
            "v603-qrtr-first-service-manager",
            args.v603_manifest,
        ),
        case_from_matrix_manifest(
            "v931-after-mdm-helper-esoc-fd",
            args.v931_manifest,
            args.v931_dmesg,
            "after-mdm-helper-esoc-fd",
            "after-mdm-helper-esoc-fd",
        ),
    ]
    scores = score_cases(cases)
    decision, pass_ok, reason, next_step = decide(cases, scores)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v927_manifest": str(repo_path(args.v927_manifest)),
            "v927_dmesg": str(repo_path(args.v927_dmesg)),
            "v601_manifest": str(repo_path(args.v601_manifest)),
            "v603_manifest": str(repo_path(args.v603_manifest)),
            "v931_manifest": str(repo_path(args.v931_manifest)),
            "v931_dmesg": str(repo_path(args.v931_dmesg)),
            "v914_manifest": str(repo_path(args.v914_manifest)),
        },
        "android_positive_reference": {
            "manifest": str(repo_path(args.v914_manifest)),
            "decision": load_json(args.v914_manifest).get("decision"),
            "role": "confirms WLFW/BDF/wlan0 positivity without making post-boot lower GPIO/MHI markers mandatory",
        },
        "cases": [asdict(case) for case in cases],
        "scores": scores,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [
            case["label"],
            case["order"],
            case["service_manager_phase"],
            case["mdm_helper_esoc0_fd"],
            case["binder_failures"],
            case["service_notifier_180"],
            case["wlfw_start"],
            case["bdf"],
            case["wlan0"],
            case["subsys_esoc0_open_attempted"],
        ]
        for case in manifest["cases"]
    ]
    score_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in manifest["scores"].items()]
    return "\n".join(
        [
            "# V932 CNSS Service-Manager Order Delta Summary",
            "",
            f"decision: `{manifest['decision']}`",
            f"pass: `{manifest['pass']}`",
            f"reason: {manifest['reason']}",
            f"next: {manifest['next_step']}",
            "",
            "## Case Matrix",
            "",
            markdown_table(
                [
                    "case",
                    "order",
                    "phase",
                    "mdm_helper_esoc0_fd",
                    "binder_failures",
                    "service180",
                    "wlfw_start",
                    "bdf",
                    "wlan0",
                    "subsys_open",
                ],
                rows,
            ),
            "",
            "## Scores",
            "",
            markdown_table(["score", "value"], score_rows),
            "",
            "## Guardrails",
            "",
            "- host-only classifier",
            "- no device command",
            "- no daemon start",
            "- no service-manager start",
            "- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping",
            "- no eSoC ioctl, subsystem open, GPIO/sysfs/debugfs write, boot image write, or partition write",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
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
