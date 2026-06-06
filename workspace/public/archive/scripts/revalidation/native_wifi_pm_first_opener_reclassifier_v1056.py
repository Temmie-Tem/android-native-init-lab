#!/usr/bin/env python3
"""V1056 host-only PM first-opener reclassifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1056-pm-first-opener-reclassifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1056-pm-first-opener-reclassifier.txt")
DEFAULT_V1043_MANIFEST = Path("tmp/wifi/v1043-pm-full-contract-v177-after-v1042-live/manifest.json")
DEFAULT_V1043_REPORT = Path("docs/reports/NATIVE_INIT_V1043_PM_FULL_CONTRACT_AFTER_V1042_2026-05-26.md")
DEFAULT_V1045_REPORT = Path("docs/reports/NATIVE_INIT_V1045_PM_PIL_PREREQUISITE_DELTA_2026-05-26.md")
DEFAULT_V1052_MANIFEST = Path("tmp/wifi/v1052-pm-full-contract-with-modem-holder-live/manifest.json")
DEFAULT_V1055_MANIFEST = Path("tmp/wifi/v1055-pm-full-contract-with-modem-holder-live/manifest.json")
DEFAULT_V1055_TRANSCRIPT = Path(
    "tmp/wifi/v1055-pm-full-contract-with-modem-holder-live/native/"
    "mdm-helper-cnss-before-esoc.txt"
)
DEFAULT_ANDROID_LATE_MANIFEST = Path(
    "tmp/wifi/v1024-fast-fd-android-timing-handoff-live-20260526-181232/"
    "v1022-late-android-pm-esoc-timing/manifest.json"
)
DEFAULT_ANDROID_EARLY_SAMPLE = Path(
    "tmp/wifi/v1024-fast-fd-android-timing-handoff-live-20260526-181232/"
    "v1022-early-android-pm-esoc-timing/android/commands/sample-loop.txt"
)
HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
V724_INIT_SOURCE = Path("stage3/linux_init/v724/90_main.inc.c")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1043-manifest", type=Path, default=DEFAULT_V1043_MANIFEST)
    parser.add_argument("--v1043-report", type=Path, default=DEFAULT_V1043_REPORT)
    parser.add_argument("--v1045-report", type=Path, default=DEFAULT_V1045_REPORT)
    parser.add_argument("--v1052-manifest", type=Path, default=DEFAULT_V1052_MANIFEST)
    parser.add_argument("--v1055-manifest", type=Path, default=DEFAULT_V1055_MANIFEST)
    parser.add_argument("--v1055-transcript", type=Path, default=DEFAULT_V1055_TRANSCRIPT)
    parser.add_argument("--android-late-manifest", type=Path, default=DEFAULT_ANDROID_LATE_MANIFEST)
    parser.add_argument("--android-early-sample", type=Path, default=DEFAULT_ANDROID_EARLY_SAMPLE)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path, limit: int = 2_000_000) -> str:
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
    value["_path"] = str(path)
    return value


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "pass"}
    return False


def intish(value: Any, default: int = -1) -> int:
    try:
        text = str(value).strip()
        if not text:
            return default
        return int(text)
    except (TypeError, ValueError):
        return default


def floatish(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def contract_from_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    helper = (manifest.get("analysis") or {}).get("helper") or {}
    contract = helper.get("contract") or {}
    return contract if isinstance(contract, dict) else {}


def timeline_time(manifest: dict[str, Any], key: str) -> float | None:
    timeline = ((manifest.get("classification") or {}).get("timeline") or {})
    if not isinstance(timeline, dict):
        return None
    entry = timeline.get(key) or {}
    if not isinstance(entry, dict) or not boolish(entry.get("present")):
        return None
    return floatish(entry.get("time"))


def first_line(text: str, pattern: str) -> str:
    regex = re.compile(pattern, re.IGNORECASE)
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line and regex.search(line):
            return line
    return ""


def selected_lines(text: str, patterns: list[str], limit: int = 24) -> list[str]:
    regexes = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line in seen:
            continue
        if any(regex.search(line) for regex in regexes):
            seen.add(line)
            lines.append(line)
            if len(lines) >= limit:
                break
    return lines


def line_present(text: str, pattern: str) -> bool:
    return bool(first_line(text, pattern))


def block_present(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.IGNORECASE | re.DOTALL) is not None


def v1055_checks(manifest: dict[str, Any], transcript: str) -> dict[str, Any]:
    contract = contract_from_manifest(manifest)
    return {
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "private_node_subsys_modem_exists": line_present(
            transcript,
            r"private_node\.subsys_modem\.exists=1",
        ),
        "private_node_subsys_modem_path": first_line(
            transcript,
            r"private_node\.subsys_modem\.path=",
        ).split("=", 1)[-1],
        "child_chroot": boolish(manifest.get("modem_pre_holder_child_chroot")),
        "path": manifest.get("modem_pre_holder_path", ""),
        "nonblock_opened": boolish(manifest.get("modem_pre_holder_nonblock_opened")),
        "nonblock_errno": str(manifest.get("modem_pre_holder_nonblock_errno", "")),
        "plain_retry": boolish(manifest.get("modem_pre_holder_plain_retry")),
        "open_reported": boolish(manifest.get("modem_pre_holder_open_reported")),
        "result_reported": boolish(manifest.get("modem_pre_holder_result_reported")),
        "confirmed": boolish(manifest.get("modem_pre_holder_confirmed")),
        "pm_full_contract_seen": boolish(manifest.get("pm_full_contract_seen")),
        "pm_proxy_helper_subsys_modem_fd_count": intish(
            manifest.get("pm_proxy_helper_subsys_modem_fd_count")
        ),
        "per_mgr_subsys_modem_fd_count": intish(manifest.get("per_mgr_subsys_modem_fd_count")),
        "poll_count": intish(contract.get("pm_full_contract_poll_count")),
        "result": contract.get("result", ""),
        "all_postflight_safe": contract.get("all_postflight_safe", ""),
    }


def v1052_checks(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": manifest.get("decision", ""),
        "child_chroot": boolish(manifest.get("modem_pre_holder_child_chroot")),
        "path": manifest.get("modem_pre_holder_path", ""),
        "errno": str(manifest.get("modem_pre_holder_errno", "")),
        "confirmed": boolish(manifest.get("modem_pre_holder_confirmed")),
        "pm_full_contract_seen": boolish(manifest.get("pm_full_contract_seen")),
    }


def v1043_checks(manifest: dict[str, Any], report: str) -> dict[str, Any]:
    contract = contract_from_manifest(manifest)
    order = str(contract.get("order", ""))
    return {
        "decision": manifest.get("decision", ""),
        "runtime_domain_guard_matched_count": intish(
            manifest.get("runtime_domain_guard_matched_count")
            or contract.get("runtime_domain_guard_matched_count")
        ),
        "pm_proxy_helper_started": boolish(contract.get("pm_proxy_helper_started")),
        "pm_proxy_helper_subsys_modem_fd_count": intish(
            contract.get("pm_proxy_helper_subsys_modem_fd_count")
        ),
        "per_mgr_subsys_modem_fd_count": intish(contract.get("per_mgr_subsys_modem_fd_count")),
        "pm_full_contract_seen": boolish(contract.get("pm_full_contract_seen")),
        "gap_snapshot_captured": boolish(contract.get("pm_full_contract_gap_snapshot_captured")),
        "order_pm_proxy_helper_before_per_mgr": "pm_proxy_helper,per_mgr_light" in order,
        "report_flush_work": "flush_work" in report,
        "report_pil_boot": "pil_boot" in report,
        "report_d_state": "D (disk sleep)" in report,
    }


def android_checks(manifest: dict[str, Any], early_sample: str) -> dict[str, Any]:
    captures = manifest.get("captures") if isinstance(manifest.get("captures"), dict) else {}
    dmesg_focus = captures.get("dmesg-focus") if isinstance(captures.get("dmesg-focus"), dict) else {}
    dmesg_text = str(dmesg_focus.get("text") or "")
    per_proxy_helper_start = timeline_time(manifest, "per_proxy_helper_start")
    per_mgr_start = timeline_time(manifest, "per_mgr_start")
    per_proxy_start = timeline_time(manifest, "per_proxy_start")
    mdm_helper_start = timeline_time(manifest, "mdm_helper_start")
    wlfw_start = timeline_time(manifest, "wlfw_start")
    wlan_pd = timeline_time(manifest, "wlan_pd")
    fw_ready = timeline_time(manifest, "fw_ready")
    modem_count0_line = first_line(
        dmesg_text,
        r"__subsystem_get\(\): __subsystem_get: modem count:0",
    )
    modem_count1_line = first_line(
        dmesg_text,
        r"__subsystem_get\(\): __subsystem_get: modem count:1",
    )
    return {
        "decision": manifest.get("decision", ""),
        "pass": boolish(manifest.get("pass")),
        "per_proxy_helper_start": per_proxy_helper_start,
        "per_mgr_start": per_mgr_start,
        "per_proxy_start": per_proxy_start,
        "mdm_helper_start": mdm_helper_start,
        "wlfw_start": wlfw_start,
        "wlan_pd": wlan_pd,
        "fw_ready": fw_ready,
        "per_proxy_helper_before_per_mgr": (
            per_proxy_helper_start is not None
            and per_mgr_start is not None
            and per_proxy_helper_start < per_mgr_start
        ),
        "modem_count0_seen": bool(modem_count0_line),
        "modem_count1_seen": bool(modem_count1_line),
        "modem_count0_line": modem_count0_line,
        "modem_count1_line": modem_count1_line,
        "early_sample_all_pm_running": line_present(
            early_sample,
            r"props .*vendor\.per_proxy_helper=running .*vendor\.per_mgr=running .*vendor\.per_proxy=running .*vendor\.mdm_helper=running",
        ),
        "early_sample_per_proxy_helper_subsys_modem_fd": line_present(
            early_sample,
            r"-> /dev/subsys_modem",
        )
        and block_present(
            early_sample,
            r"TARGET_PROC tag=pm_proxy_helper[^\n]*\n[^\n]*-> /dev/subsys_modem",
        ),
        "early_sample_pm_service_subsys_modem_fd": line_present(
            early_sample,
            r"-> /dev/subsys_modem",
        )
        and block_present(
            early_sample,
            r"TARGET_PROC tag=pm-service[^\n]*\n[^\n]*-> /dev/subsys_modem",
        ),
        "early_sample_mdm_helper_esoc0_fd": line_present(
            early_sample,
            r"-> /dev/esoc-0",
        )
        and block_present(
            early_sample,
            r"TARGET_PROC tag=mdm_helper[^\n]*\n[^\n]*-> /dev/esoc-0",
        ),
    }


def source_checks(helper_source: str, v724_source: str) -> dict[str, Any]:
    helper_order = (
        "property-shim,modem-pre-holder,pm_proxy_helper,per_mgr_light,pm_proxy,mdm_helper"
        in helper_source
    )
    return {
        "helper_v180_modem_pre_holder_before_pm_proxy_helper": helper_order,
        "helper_v180_plain_retry": "modem_pre_holder_plain_retry=1" in helper_source,
        "v724_sibling_ssctl_flag": "/cache/native-init-sibling-fwssctl-v641" in v724_source,
        "v724_sibling_ssctl_nodes_adsp_cdsp_slpi": all(
            node in v724_source for node in ("/sys/kernel/boot_adsp/boot", "/sys/kernel/boot_cdsp/boot", "/sys/kernel/boot_slpi/boot")
        ),
        "v724_no_subsys_modem_open_in_init": 'open("/dev/subsys_modem"' not in v724_source,
    }


def decide(checks: dict[str, Any]) -> tuple[str, bool, str, str]:
    android_count0_to_count1 = (
        checks["android"]["per_proxy_helper_before_per_mgr"]
        and checks["android"]["modem_count0_seen"]
        and checks["android"]["modem_count1_seen"]
    )
    native_first_open_blocked = (
        checks["v1055"]["private_node_subsys_modem_exists"]
        and checks["v1055"]["child_chroot"]
        and checks["v1055"]["path"] == "/dev/subsys_modem"
        and checks["v1055"]["nonblock_errno"] == "14"
        and checks["v1055"]["plain_retry"]
        and not checks["v1055"]["confirmed"]
        and not checks["v1055"]["pm_full_contract_seen"]
    )
    v1043_actual_pm_helper_blocked = (
        checks["v1043"]["runtime_domain_guard_matched_count"] >= 4
        and checks["v1043"]["order_pm_proxy_helper_before_per_mgr"]
        and checks["v1043"]["report_flush_work"]
        and checks["v1043"]["report_pil_boot"]
        and not checks["v1043"]["pm_full_contract_seen"]
    )
    pre_holder_not_android_order = (
        checks["source"]["helper_v180_modem_pre_holder_before_pm_proxy_helper"]
        and checks["android"]["per_proxy_helper_before_per_mgr"]
    )

    if android_count0_to_count1 and native_first_open_blocked and v1043_actual_pm_helper_blocked:
        return (
            "v1056-android-count-zero-first-open-parity-gap-classified",
            True,
            (
                "Android starts vendor.per_proxy_helper first, observes modem count=0, "
                "and later reaches modem count=1 before vendor.per_mgr can be a "
                "pre-holder. Native V1043/V1055 also attempts a first /dev/subsys_modem "
                "open, but it blocks and never forms the PM fd contract. The V1047 "
                "synthetic pre-holder model is therefore not an Android-faithful fix; "
                "the remaining gap is lower first-open runtime prerequisite parity."
            ),
            "v1057-readonly-first-open-runtime-prereq-classifier",
        )

    if native_first_open_blocked and pre_holder_not_android_order:
        return (
            "v1056-native-first-open-blocker-classified",
            True,
            "Native first-open still blocks, and helper v180 pre-holder ordering is not Android-faithful.",
            "v1057-review-android-count0-to-count1-and-runtime-prereqs",
        )

    return (
        "v1056-first-opener-reclassifier-inconclusive",
        False,
        "Required V1024/V1043/V1055 evidence was missing or did not match expected blocker shape.",
        "refresh targeted evidence before another live PM retry",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest["checks"]
    android = checks["android"]
    v1055 = checks["v1055"]
    v1043 = checks["v1043"]
    source = checks["source"]
    rows = [
        ["Android per_proxy_helper start", android["per_proxy_helper_start"]],
        ["Android per_mgr start", android["per_mgr_start"]],
        ["Android per_proxy_helper before per_mgr", android["per_proxy_helper_before_per_mgr"]],
        ["Android modem count=0 seen", android["modem_count0_seen"]],
        ["Android modem count=1 seen", android["modem_count1_seen"]],
        ["Android early sample PM fds", android["early_sample_per_proxy_helper_subsys_modem_fd"]],
        ["Native V1043 PM domains matched", v1043["runtime_domain_guard_matched_count"]],
        ["Native V1043 PM contract seen", v1043["pm_full_contract_seen"]],
        ["Native V1055 private node exists", v1055["private_node_subsys_modem_exists"]],
        ["Native V1055 nonblock errno", v1055["nonblock_errno"]],
        ["Native V1055 plain retry", v1055["plain_retry"]],
        ["Native V1055 holder confirmed", v1055["confirmed"]],
        ["Helper pre-holder before pm_proxy_helper", source["helper_v180_modem_pre_holder_before_pm_proxy_helper"]],
    ]
    lines = [
        "# V1056 PM First-Opener Reclassifier",
        "",
        f"- generated: `{manifest['generated']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- next: `{manifest['next_step']}`",
        f"- reason: {manifest['reason']}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "value"], rows),
        "",
        "## Key Reclassification",
        "",
        "Android does not prove that `pm-service` pre-holds `/dev/subsys_modem`",
        "before `pm_proxy_helper`. The Android dmesg positive control shows",
        "`vendor.per_proxy_helper` starts first, enters `__subsystem_get()` with",
        "`modem count:0`, and the later PM path observes `modem count:1`.",
        "",
        "Native V1043 already started actual `pm_proxy_helper` before `pm-service`",
        "with PM SELinux domains matched, but it blocked in the PIL/subsystem path.",
        "V1055 then proved that a synthetic pre-holder reaches the correct private",
        "node but blocks as another first-opener. So the blocker is no longer",
        "classified as a missing holder; it is Android first-open runtime parity.",
        "",
        "## Evidence Lines",
        "",
        f"- Android count0: `{android['modem_count0_line']}`",
        f"- Android count1: `{android['modem_count1_line']}`",
        f"- V1055 private node path: `{v1055['private_node_subsys_modem_path']}`",
        "",
        "## Next Gate",
        "",
        "`v1057-readonly-first-open-runtime-prereq-classifier` should inspect the",
        "lower prerequisites for a successful modem count-zero first open:",
        "",
        "1. `firmware_class.path`;",
        "2. global and private firmware mount visibility;",
        "3. `modem.b00`/`modem.mdt` visibility at the exact PIL path;",
        "4. whether native has already changed modem state before the PM first-open window.",
        "",
        "Do not rerun the same synthetic modem pre-holder gate.",
    ]
    return "\n".join(str(line) for line in lines)


def execute(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1043_manifest = load_json(args.v1043_manifest)
    v1043_report = read_text(args.v1043_report)
    v1045_report = read_text(args.v1045_report)
    v1052_manifest = load_json(args.v1052_manifest)
    v1055_manifest = load_json(args.v1055_manifest)
    v1055_transcript = read_text(args.v1055_transcript)
    android_late_manifest = load_json(args.android_late_manifest)
    android_early_sample = read_text(args.android_early_sample)
    helper_source = read_text(HELPER_SOURCE)
    v724_source = read_text(V724_INIT_SOURCE)
    captures = android_late_manifest.get("captures") if isinstance(android_late_manifest.get("captures"), dict) else {}
    dmesg_focus = captures.get("dmesg-focus") if isinstance(captures.get("dmesg-focus"), dict) else {}
    android_dmesg_text = str(dmesg_focus.get("text") or "")

    checks = {
        "inputs": {
            "v1043_present": "_missing" not in v1043_manifest,
            "v1045_report_present": bool(v1045_report),
            "v1052_present": "_missing" not in v1052_manifest,
            "v1055_present": "_missing" not in v1055_manifest,
            "android_late_present": "_missing" not in android_late_manifest,
            "android_early_sample_present": bool(android_early_sample),
            "helper_source_present": bool(helper_source),
            "v724_source_present": bool(v724_source),
        },
        "v1043": v1043_checks(v1043_manifest, v1043_report),
        "v1052": v1052_checks(v1052_manifest),
        "v1055": v1055_checks(v1055_manifest, v1055_transcript),
        "android": android_checks(android_late_manifest, android_early_sample),
        "source": source_checks(helper_source, v724_source),
    }
    decision, pass_ok, reason, next_step = decide(checks)
    manifest = {
        "generated": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "guardrails": {
            "host_only": True,
            "device_contact": False,
            "android_boot": False,
            "adb_command": False,
            "bridge_command": False,
            "subsys_modem_open": False,
            "subsys_esoc0_open": False,
            "esoc0_open": False,
            "esoc_ioctl": False,
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
            "debugfs_write": False,
        },
    }
    write_private_text(
        store.path("evidence_lines.txt"),
        "\n".join(
            selected_lines(
                android_dmesg_text,
                [
                    r"per_proxy_helper",
                    r"modem count:0",
                    r"modem count:1",
                    r"vendor\.per_mgr",
                    r"wlfw_start",
                    r"WLAN FW is ready",
                ],
                limit=40,
            )
            + [""]
            + selected_lines(
                v1055_transcript,
                [
                    r"private_node\.subsys_modem",
                    r"modem_pre_holder",
                    r"pm_full_contract_seen",
                    r"result=reboot-required",
                ],
                limit=60,
            )
        ),
    )
    write_private_text(store.path("summary.md"), render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    if args.command == "plan":
        print("V1056 host-only PM first-opener reclassifier")
        print(f"out_dir: {args.out_dir}")
        print(f"v1055_manifest: {args.v1055_manifest}")
        print(f"android_late_manifest: {args.android_late_manifest}")
        return 0

    manifest = execute(args, store)
    manifest["host"] = collect_host_metadata()
    write_private_text(store.path("manifest.json"), json.dumps(manifest, indent=2, default=str))
    write_private_text(LATEST_POINTER, str(args.out_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"next_step: {manifest['next_step']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
