#!/usr/bin/env python3
"""V896 host-only Android mdm_helper image/link contract classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Iterable

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v896-android-mdm-helper-image-contract")
LATEST_POINTER = Path("tmp/wifi/latest-v896-android-mdm-helper-image-contract.txt")
DEFAULT_V895_MANIFEST = Path("tmp/wifi/v895-mdm2ap-irq-snapshot-live/manifest.json")
DEFAULT_V852_MANIFEST = Path(
    "tmp/wifi/v852-android-ext-mdm-provider-surface-handoff/"
    "v852-android-ext-mdm-provider-surface-run/manifest.json"
)
DEFAULT_V853_MANIFEST = Path(
    "tmp/wifi/v853-android-esoc-actor-handoff/"
    "v853-android-esoc-actor-run/manifest.json"
)
SOURCE_ROOT = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source")
UAPI = SOURCE_ROOT / "include/uapi/linux/esoc_ctrl.h"
ESOC_DEV = SOURCE_ROOT / "drivers/esoc/esoc_dev.c"
MDM_PON = SOURCE_ROOT / "drivers/esoc/esoc-mdm-pon.c"
MDM_4X = SOURCE_ROOT / "drivers/esoc/esoc-mdm-4x.c"

IRQ_RE = re.compile(
    r"^\s*(?P<irq>\d+):(?P<counts>(?:\s+\d+)+)\s+(?P<controller>\S+)\s+"
    r"(?P<gpio>\d+)\s+(?P<trigger>\S+)\s+(?P<name>.+?)\s*$"
)
TIME_RE = re.compile(r"^\[\s*(?P<time>\d+\.\d+)\]")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v895-manifest", type=Path, default=DEFAULT_V895_MANIFEST)
    parser.add_argument("--v852-manifest", type=Path, default=DEFAULT_V852_MANIFEST)
    parser.add_argument("--v853-manifest", type=Path, default=DEFAULT_V853_MANIFEST)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def line_hits(path: Path, patterns: dict[str, str]) -> dict[str, dict[str, Any]]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {name: {"present": False, "path": str(path), "line": 0, "text": ""} for name in patterns}
    lines = resolved.read_text(encoding="utf-8", errors="replace").splitlines()
    hits: dict[str, dict[str, Any]] = {}
    for name, pattern in patterns.items():
        regex = re.compile(pattern)
        found = {"present": False, "path": str(path), "line": 0, "text": ""}
        for index, line in enumerate(lines, start=1):
            if regex.search(line):
                found = {"present": True, "path": str(path), "line": index, "text": line.strip()}
                break
        hits[name] = found
    return hits


def flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value.replace("\x00", "")
    elif isinstance(value, dict):
        for item in value.values():
            yield from flatten_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from flatten_strings(item)


def filtered_lines(strings: Iterable[str], pattern: str, limit: int = 80) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    lines: list[str] = []
    seen: set[str] = set()
    for text in strings:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line in seen:
                continue
            if regex.search(line):
                seen.add(line)
                lines.append(line)
                if len(lines) >= limit:
                    return lines
    return lines


def dmesg_time(line: str) -> float | None:
    match = TIME_RE.search(line)
    return float(match.group("time")) if match else None


def first_timed_line(lines: list[str], pattern: str) -> dict[str, Any]:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in lines:
        if regex.search(line):
            return {"present": True, "time": dmesg_time(line), "line": line}
    return {"present": False, "time": None, "line": ""}


def parse_irq_line(lines: list[str]) -> dict[str, Any]:
    for line in lines:
        if "mdm status" not in line.lower():
            continue
        match = IRQ_RE.search(line)
        if not match:
            continue
        counts = [int(value) for value in match.group("counts").split()]
        return {
            "present": True,
            "line": line,
            "irq": int(match.group("irq")),
            "controller": match.group("controller"),
            "gpio": int(match.group("gpio")),
            "trigger": match.group("trigger"),
            "name": match.group("name").strip(),
            "count_total": sum(counts),
        }
    return {"present": False, "line": "", "count_total": 0}


def extract_v895(manifest: dict[str, Any]) -> dict[str, Any]:
    helper = (manifest.get("analysis") or {}).get("helper") or {}
    conditional = helper.get("conditional") or {}
    irq = manifest.get("v895_irq_snapshot") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "img_xfer_sent": conditional.get("img_xfer_sent", ""),
        "status_last_value": conditional.get("status_last_value", ""),
        "status_poll_count": conditional.get("status_poll_count", ""),
        "boot_done_sent": conditional.get("boot_done_sent", ""),
        "irq_fired": bool(irq.get("irq_fired")),
        "irq_delta_total": irq.get("delta_total"),
        "irq_before_img_xfer": irq.get("before_img_xfer_count"),
        "irq_after_img_xfer": irq.get("after_img_xfer_count"),
        "irq_max_count": irq.get("max_count"),
        "irq_phase_count": irq.get("phase_count"),
        "all_parsed_gpio142": bool(irq.get("all_parsed_gpio142")),
        "cleanup_reboot_executed": bool(manifest.get("cleanup_reboot_executed")),
        "wifi_bringup_executed": bool(manifest.get("wifi_bringup_executed")),
    }


def command_text(manifest_path: Path, relative: str) -> str:
    return read_text(manifest_path.parent / relative)


def extract_v852(manifest_path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    summary = manifest.get("android_summary") or {}
    focused = summary.get("focused_lines") or {}
    dmesg_focus = command_text(manifest_path, "android/commands/dmesg-focus.txt")
    irq_focus = command_text(manifest_path, "android/commands/interrupts-focus.txt")
    gpio_focus = command_text(manifest_path, "android/commands/gpio-pinctrl-surface.txt")
    dmesg_lines = filtered_lines(
        list(focused.get("dmesg") or []) + [dmesg_focus],
        r"cnss-daemon|__subsystem_get.*esoc0|msm_pcie_enable|wlan_pd|wlfw|BDF file|sysmon-qmi|wlan0",
        limit=40,
    )
    irq_lines = list(summary.get("irq_focus_lines") or []) + filtered_lines([irq_focus], r"mdm status|mhi|wlanfw", 40)
    gpio_lines = filtered_lines(
        list((focused.get("gpio_pinctrl") or [])) + [gpio_focus],
        r"gpio135|gpio142|pin 135|pin 142|GPIO_DEBUG readable|pin 7 \(gpio9\)|pm8150l",
        limit=40,
    )
    timeline = {
        "cnss_daemon_start": first_timed_line(dmesg_lines, r"cnss-daemon wlfw_start"),
        "esoc0_subsystem_get": first_timed_line(dmesg_lines, r"__subsystem_get.*esoc0"),
        "pcie_link_l0": first_timed_line(dmesg_lines, r"LTSSM_L0|link initialized"),
        "wlan_pd_indication": first_timed_line(dmesg_lines, r"msm/modem/wlan_pd"),
        "bdf_regdb": first_timed_line(dmesg_lines, r"regdb\.bin"),
        "bdf_bdwlan": first_timed_line(dmesg_lines, r"bdwlan\.bin"),
        "sysmon_esoc0": first_timed_line(dmesg_lines, r"esoc0's SSCTL"),
        "wlan0": first_timed_line(dmesg_lines, r"\bwlan0\b"),
    }
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "boot_completed": bool(summary.get("boot_completed")),
        "mdm3_state": summary.get("mdm3_state", ""),
        "mss_state": summary.get("mss_state", ""),
        "counts": summary.get("counts") or {},
        "dmesg_hints": summary.get("dmesg_hints") or {},
        "surface": summary.get("surface") or {},
        "symbols": summary.get("symbols") or {},
        "irq_mdm_status": parse_irq_line(irq_lines),
        "gpio_focus_lines": gpio_lines,
        "timeline": timeline,
        "selected_dmesg_lines": dmesg_lines,
    }


def extract_v853(manifest: dict[str, Any]) -> dict[str, Any]:
    summary = manifest.get("android_summary") or {}
    holder_lines = filtered_lines(
        summary.get("holder_lines") or [],
        r"mdm_helper|ks .*mhi_0305|/dev/esoc-0|pm-service|/dev/subsys_esoc0|/dev/subsys_modem",
        limit=40,
    )
    process_lines = filtered_lines(
        summary.get("process_lines") or [],
        r"mdm_helper|ks .*mhi_0305|cnss-daemon|pm-service|qrtr-ns|rmt_storage|tftp_server|irq/290-mdm",
        limit=50,
    )
    ueventd_lines = filtered_lines(
        summary.get("ueventd_lines") or [],
        r"/dev/esoc-0|/dev/subsys_\*|service vendor\.mdm_helper|service vendor\.per_mgr|service cnss-daemon|service vendor\.rmt_storage|service vendor\.tftp_server",
        limit=60,
    )
    selinux_lines = filtered_lines(
        summary.get("selinux_lines") or [],
        r"mdm_helper|/bin/ks|/dev/esoc|/dev/subsys_|pm-service|rmt_storage|tftp_server|cnss-daemon",
        limit=60,
    )
    service_lines = filtered_lines(flatten_strings(manifest.get("captures") or []), r"init\.svc\.(vendor\.mdm_helper|vendor\.per_mgr|cnss-daemon|rmt_storage|tftp_server|vendor\.qrtr-ns)=", limit=20)
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "boot_completed": bool(summary.get("boot_completed")),
        "holder_lines": holder_lines,
        "process_lines": process_lines,
        "ueventd_lines": ueventd_lines,
        "selinux_lines": selinux_lines,
        "service_lines": service_lines,
        "has_mdm_helper_esoc_fd": any("mdm_helper" in line and "/dev/esoc-0" in line for line in holder_lines),
        "has_ks_esoc_fd": any("comm=ks" in line or "cmd=/vendor/bin/ks" in line for line in holder_lines)
        and any("/dev/esoc-0" in line for line in holder_lines),
        "has_ks_mhi_pipe": any("/dev/mhi_0305_01.01.00_pipe_10" in line for line in process_lines + holder_lines),
        "has_per_mgr_subsys_esoc0_fd": any("/dev/subsys_esoc0" in line for line in holder_lines),
        "has_per_mgr_subsys_modem_fd": any("/dev/subsys_modem" in line for line in holder_lines),
        "has_mdm_helper_init_service": any("service vendor.mdm_helper" in line for line in ueventd_lines),
        "has_esoc0_ueventd_rule": any("/dev/esoc-0" in line for line in ueventd_lines),
        "has_mdm_helper_selinux": any("vendor_mdm_helper_exec" in line for line in selinux_lines),
        "has_esoc_device_selinux": any("vendor_esoc_device" in line for line in selinux_lines),
    }


def collect_sources() -> dict[str, Any]:
    return {
        "uapi": line_hits(UAPI, {
            "wait_for_req_ioctl": r"#define\s+ESOC_WAIT_FOR_REQ\b",
            "notify_ioctl": r"#define\s+ESOC_NOTIFY\b",
            "get_status_ioctl": r"#define\s+ESOC_GET_STATUS\b",
            "img_xfer_done": r"\bESOC_IMG_XFER_DONE\s*=\s*1\b",
            "boot_done": r"\bESOC_BOOT_DONE\b",
            "req_img": r"\bESOC_REQ_IMG\s*=\s*1\b",
        }),
        "esoc_dev": line_hits(ESOC_DEV, {
            "wait_for_req_case": r"case\s+ESOC_WAIT_FOR_REQ",
            "notify_case": r"case\s+ESOC_NOTIFY",
            "get_status_case": r"case\s+ESOC_GET_STATUS",
        }),
        "mdm_pon": line_hits(MDM_PON, {
            "ap2mdm_status_high": r"Setting AP2MDM_STATUS = 1",
            "queue_req_img": r"Queueing the request: ESOC_REQ_IMG",
            "userspace_confirms_link": r"Let userspace confirm establishment",
        }),
        "mdm_4x": line_hits(MDM_4X, {
            "img_xfer_done_case": r"case\s+ESOC_IMG_XFER_DONE",
            "img_xfer_timeout": r"ESOC_IMG_XFER_DONE: Begin timeout",
            "mdm2ap_irq": r"MDM2AP_STATUS IRQ received",
            "ready_set": r"mdm->ready\s*=\s*true",
            "boot_done_case": r"case\s+ESOC_BOOT_DONE",
            "boot_done_run_state": r"ESOC_BOOT_DONE: Sending the notification: ESOC_RUN_STATE",
        }),
    }


def decide(v895: dict[str, Any], v852: dict[str, Any], v853: dict[str, Any], sources: dict[str, Any]) -> tuple[str, bool, str, str, dict[str, Any]]:
    native_negative = (
        v895.get("pass")
        and v895.get("img_xfer_sent") == "1"
        and v895.get("status_last_value") == "0"
        and v895.get("boot_done_sent") == "0"
        and v895.get("irq_fired") is False
        and v895.get("irq_delta_total") == 0
        and v895.get("all_parsed_gpio142") is True
    )
    hints = v852.get("dmesg_hints") or {}
    irq = v852.get("irq_mdm_status") or {}
    android_positive = (
        v852.get("pass")
        and v852.get("boot_completed")
        and v852.get("mdm3_state") == "ONLINE"
        and bool(hints.get("has_wlfw"))
        and bool(hints.get("has_bdf"))
        and bool(hints.get("has_wlan0"))
        and irq.get("gpio") == 142
        and int(irq.get("count_total") or 0) > 0
    )
    actor_contract = all(
        bool(v853.get(key))
        for key in (
            "has_mdm_helper_esoc_fd",
            "has_ks_esoc_fd",
            "has_ks_mhi_pipe",
            "has_per_mgr_subsys_esoc0_fd",
            "has_per_mgr_subsys_modem_fd",
            "has_mdm_helper_init_service",
            "has_esoc0_ueventd_rule",
            "has_mdm_helper_selinux",
            "has_esoc_device_selinux",
        )
    )
    source_contract = all(
        hit.get("present")
        for group in sources.values()
        for hit in group.values()
    )
    classification = {
        "android_positive_control": "Android reaches mdm3 ONLINE, WLFW/BDF/wlan0, and GPIO142 mdm status IRQ count > 0",
        "native_negative_control": "V895 sends ESOC_IMG_XFER_DONE but GPIO142 IRQ delta remains 0 and GET_STATUS stays 0",
        "source_contract": "ESOC_REQ_IMG asks userspace to confirm link establishment before IMG_XFER_DONE",
        "missing_native_contract": "native immediate IMG_XFER_DONE did not reproduce Android mdm_helper -> ks MHI link/image path",
        "next_gate": "V897 should be host-only native mdm_helper/ks contract design or focused Android timing recapture, not a blind image-done retry",
    }
    if native_negative and android_positive and actor_contract and source_contract:
        return (
            "v896-android-mdm-helper-image-contract-classified",
            True,
            "Android positive path includes mdm_helper/ks MHI contract and MDM2AP IRQ; native V895 immediate image-done lacks that contract",
            "plan V897 fail-closed native mdm_helper/ks contract preflight before any live actor start",
            classification,
        )
    return (
        "v896-android-mdm-helper-image-contract-incomplete",
        False,
        f"native_negative={native_negative} android_positive={android_positive} actor_contract={actor_contract} source_contract={source_contract}",
        "repair missing V852/V853/V895/source evidence or recapture focused Android dmesg before live work",
        classification,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    source_rows: list[list[Any]] = []
    for group, hits in (manifest.get("sources") or {}).items():
        for name, hit in hits.items():
            source_rows.append([group, name, hit.get("present"), hit.get("path"), hit.get("line")])
    actor_rows = [[key, value] for key, value in (manifest.get("v853_actor_flags") or {}).items()]
    timeline_rows: list[list[Any]] = []
    for name, item in (manifest.get("v852") or {}).get("timeline", {}).items():
        timeline_rows.append([name, item.get("present"), item.get("time"), item.get("line")])
    return "\n".join([
        "# V896 Android mdm_helper Image Contract Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_contact: `{manifest['device_contact']}`",
        f"- live_esoc_ioctl_executed: `{manifest['live_esoc_ioctl_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## V895 Native Negative Control",
        "",
        markdown_table(["field", "value"], [[key, value] for key, value in manifest.get("v895", {}).items()]),
        "",
        "## Android Positive Control",
        "",
        markdown_table([
            "field",
            "value",
        ], [
            ["mdm3_state", manifest["v852"].get("mdm3_state")],
            ["mss_state", manifest["v852"].get("mss_state")],
            ["dmesg_hints", json.dumps(manifest["v852"].get("dmesg_hints"), sort_keys=True)],
            ["irq_mdm_status", json.dumps(manifest["v852"].get("irq_mdm_status"), sort_keys=True)],
        ]),
        "",
        "## Android Timeline Anchors",
        "",
        markdown_table(["anchor", "present", "time", "line"], timeline_rows),
        "",
        "## Android Actor Contract",
        "",
        markdown_table(["flag", "value"], actor_rows),
        "",
        "## Source Markers",
        "",
        markdown_table(["group", "marker", "present", "path", "line"], source_rows),
        "",
        "## Interpretation",
        "",
        "- Existing Android evidence is sufficient for the focused comparison; a Magisk module is not required for V896.",
        "- Android proves the same GPIO142 readiness line fires after the mdm helper path is active.",
        "- V895 proves native immediate image-done does not make that line fire.",
        "- The next safe step is a fail-closed native design for the mdm_helper/ks MHI contract, not a wider live retry.",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v895_manifest = load_json(args.v895_manifest)
    v852_manifest = load_json(args.v852_manifest)
    v853_manifest = load_json(args.v853_manifest)
    v895 = extract_v895(v895_manifest)
    v852 = extract_v852(args.v852_manifest, v852_manifest)
    v853 = extract_v853(v853_manifest)
    sources = collect_sources()
    decision, pass_ok, reason, next_step, classification = decide(v895, v852, v853, sources)
    manifest = {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v895_manifest": str(args.v895_manifest),
        "v852_manifest": str(args.v852_manifest),
        "v853_manifest": str(args.v853_manifest),
        "v895": v895,
        "v852": v852,
        "v853_actor_flags": {
            key: v853.get(key)
            for key in (
                "has_mdm_helper_esoc_fd",
                "has_ks_esoc_fd",
                "has_ks_mhi_pipe",
                "has_per_mgr_subsys_esoc0_fd",
                "has_per_mgr_subsys_modem_fd",
                "has_mdm_helper_init_service",
                "has_esoc0_ueventd_rule",
                "has_mdm_helper_selinux",
                "has_esoc_device_selinux",
            )
        },
        "v853_selected_lines": {
            "holder_lines": v853.get("holder_lines"),
            "process_lines": v853.get("process_lines"),
            "ueventd_lines": v853.get("ueventd_lines"),
            "selinux_lines": v853.get("selinux_lines"),
            "service_lines": v853.get("service_lines"),
        },
        "sources": sources,
        "classification": classification,
        "device_contact": False,
        "android_boot_executed": False,
        "adb_command_executed": False,
        "live_esoc_ioctl_executed": False,
        "actor_start_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "boot_image_write_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"next: {next_step}")
    print(f"device_contact: {manifest['device_contact']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
