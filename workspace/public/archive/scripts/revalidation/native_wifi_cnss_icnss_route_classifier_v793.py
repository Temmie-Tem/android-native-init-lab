#!/usr/bin/env python3
"""V793 host-only CNSS/ICNSS route classifier.

V792 proved current clean-DSP + lower companion + cnss_diag/cnss-daemon reaches
service 180/74 and the known ASoC warning, but not WLFW/service69/BDF/wlan0.
This classifier reconciles that live evidence with prior binder, service-manager,
ICNSS, boot_wlan, mdm3, and memshare classifiers to select the next bounded gate.
It does not contact the device.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v793-cnss-icnss-route-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v793-cnss-icnss-route-classifier.txt")
DEFAULT_V792_MANIFEST = Path("tmp/wifi/v792-known-asoc-warning-cnss-wlfw/manifest.json")
DEFAULT_V792_DMESG = Path("tmp/wifi/v792-known-asoc-warning-cnss-wlfw/native/dmesg-delta.txt")
REPORT_DEFAULTS = {
    "v660": Path("docs/reports/NATIVE_INIT_V660_READY_CNSS_RETRY_LIVE_2026-05-23.md"),
    "v661": Path("docs/reports/NATIVE_INIT_V661_BINDER_REGISTRATION_CONTEXT_CLASSIFIER_2026-05-23.md"),
    "v666": Path("docs/reports/NATIVE_INIT_V666_REPAIRED_PRIVATE_CNSS_RETRY_LIVE_2026-05-24.md"),
    "v750": Path("docs/reports/NATIVE_INIT_V750_LOWER_WINDOW_BOOT_WLAN_2026-05-24.md"),
    "v752": Path("docs/reports/NATIVE_INIT_V752_CNSS_THEN_BOOT_WLAN_2026-05-24.md"),
    "v763": Path("docs/reports/NATIVE_INIT_V763_ICNSS_ARCH_REBASE_2026-05-24.md"),
    "v783": Path("docs/reports/NATIVE_INIT_V783_ANDROID_NATIVE_PIL_GAP_2026-05-25.md"),
    "v785": Path("docs/reports/NATIVE_INIT_V785_ANDROID_NATIVE_MEMSHARE_DELTA_2026-05-25.md"),
}
READ_LIMIT_BYTES = 8 * 1024 * 1024
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
DECISION_RE = re.compile(r"decision:\s*`?(?P<decision>[a-z0-9_.-]+)`?", re.IGNORECASE)
REASON_RE = re.compile(r"reason:\s*(?P<reason>.+)", re.IGNORECASE)
NEXT_RE = re.compile(r"next:\s*(?P<next>.+)", re.IGNORECASE)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v792-manifest", type=Path, default=DEFAULT_V792_MANIFEST)
    parser.add_argument("--v792-dmesg", type=Path, default=DEFAULT_V792_DMESG)
    for name, path in REPORT_DEFAULTS.items():
        parser.add_argument(f"--{name}-report", type=Path, default=path)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def file_info(path: Path) -> dict[str, Any]:
    resolved = resolve(path)
    if not resolved.exists():
        return {"path": str(resolved), "exists": False}
    return {
        "path": str(resolved),
        "exists": True,
        "is_file": resolved.is_file(),
        "size": resolved.stat().st_size if resolved.is_file() else None,
    }


def safe_read(path: Path) -> tuple[str, dict[str, Any]]:
    resolved = resolve(path)
    info = file_info(path)
    if not resolved.exists() or not resolved.is_file():
        return "", info
    payload = resolved.read_bytes()[:READ_LIMIT_BYTES]
    info["bytes_read"] = len(payload)
    info["truncated"] = resolved.stat().st_size > len(payload)
    return payload.decode("utf-8", errors="replace"), info


def load_json(path: Path) -> dict[str, Any]:
    text, info = safe_read(path)
    if not text:
        return {"exists": False, "path": info.get("path", str(resolve(path)))}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolve(path)), "invalid": str(exc)}
    if not isinstance(payload, dict):
        return {"exists": True, "path": str(resolve(path)), "invalid": "not-object"}
    payload.setdefault("exists", True)
    payload.setdefault("path", str(resolve(path)))
    return payload


def clean_text(text: str) -> str:
    return ANSI_RE.sub("", text)


def count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def report_path(args: argparse.Namespace, name: str) -> Path:
    return getattr(args, f"{name}_report")


def report_facts(name: str, path: Path) -> dict[str, Any]:
    text, info = safe_read(path)
    text = clean_text(text)
    decisions = [match.group("decision") for match in DECISION_RE.finditer(text)]
    reasons = [match.group("reason").strip(" `") for match in REASON_RE.finditer(text)]
    next_steps = [match.group("next").strip(" `") for match in NEXT_RE.finditer(text)]
    return {
        "name": name,
        "file": info,
        "decision": decisions[0] if decisions else "",
        "reason": reasons[0] if reasons else "",
        "next": next_steps[0] if next_steps else "",
        "service_manager_ready": any(marker in text for marker in ("vndservicemanager_readiness.ready` | `1`", "vndservicemanager` observable | `1`", "vndservicemanager readiness")),
        "cnss_retry_executed": "fresh cnss retry executed" in text.lower() or "retry `cnss-daemon` observable" in text or "cnss_retry.enabled` | `1`" in text,
        "binder_minus22": (
            "binder transaction failure persisted" in text.lower()
            or "binder transaction failed" in text.lower()
            or "binder transaction `-22`" in text
            or "CNSS binder transaction failure" in text
            or "`cnss-daemon` binder transaction failure" in text
        ),
        "wlfw_absent": any(marker in text for marker in ("WLFW start | `0`", "wlfw_start` | `0`", "WLFW/service69/BDF/wlan0 -> absent", "no WLFW")),
        "boot_wlan_no_advance": "boot_wlan" in text and ("WLFW/service69/BDF/wiphy/wlan0 -> absent" in text or "qcwlanstate` after observe | `OFF`" in text or "hdd-init-still-stalls" in text),
        "icnss_arch_rebased": "live SM-A908N path is ICNSS/QCACLD" in text or "v763-icnss-architecture-rebased" in text,
        "mdm3_android_online_native_offlining": "mdm3` final state | `ONLINE` | `OFFLINING`" in text or "`mdm3=OFFLINING` while Android has `mdm3=ONLINE`" in text,
        "memshare_demoted": "demotes memshare/CMA failure as the sole blocker" in text or "memshare-common-nonfatal" in text,
    }


def v792_facts(manifest: dict[str, Any], dmesg_path: Path) -> dict[str, Any]:
    dmesg, dmesg_info = safe_read(dmesg_path)
    dmesg = clean_text(dmesg)
    lower = manifest.get("lower_readback") or {}
    live = lower.get("live") or {}
    markers = live.get("markers") or {}
    helper = live.get("helper") or {}
    safety = manifest.get("safety") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": manifest.get("pass"),
        "manifest_path": manifest.get("path", ""),
        "dmesg_file": dmesg_info,
        "mss": live.get("mss", []),
        "mdm3": live.get("mdm3", []),
        "markers": markers,
        "helper": helper,
        "safety": safety,
        "binder_ioctl_minus22": count(dmesg, r"binder: .* ioctl .* returned -22"),
        "binder_transaction_minus22": count(dmesg, r"binder: .* transaction failed .*-/??22|binder: .* transaction failed .* -22"),
        "cnss_netlink": count(dmesg, r"comm:\s*cnss-daemon|cnss-daemon:.*netlink|cnss-daemon.*ctrl_getfamily"),
        "cnss_diag_netlink": count(dmesg, r"comm:\s*cnss_diag|cnss_diag.*ctrl_getfamily"),
        "icnss_qmi": count(dmesg, r"icnss.*qmi|ICNSS-QMI|qmi_server_connected"),
        "wlan_hdd_state": count(dmesg, r"wlan_hdd_state|wlan major|qcwlanstate"),
        "boot_wlan": count(dmesg, r"boot_wlan|Modules not initialized"),
        "wlfw": count(dmesg, r"wlfw|WLFW|WLAN FW"),
        "bdf": count(dmesg, r"\bBDF\b|bdwlan|regdb"),
        "wlan0": count(dmesg, r"\bwlan0\b"),
        "service_notifier": int(markers.get("service_notifier", 0) or 0),
        "sysmon_qmi": int(markers.get("sysmon_qmi", 0) or 0),
        "known_warning": bool((manifest.get("known_asoc_warning_guard") or {}).get("exact_known_asoc_warning")),
        "service_manager_executed": bool(safety.get("service_manager_start_executed")),
        "wifi_hal_executed": bool(safety.get("wifi_hal_start_executed")),
        "connect_executed": bool(safety.get("scan_connect_executed") or safety.get("credential_use_executed") or safety.get("external_ping_executed")),
    }


def build_checks(args: argparse.Namespace, v792: dict[str, Any], reports: dict[str, dict[str, Any]]) -> list[Check]:
    checks: list[Check] = []
    checks.append(Check(
        "v792-input",
        "pass" if v792.get("decision") == "v792-known-warning-cnss-no-wlfw-classified" and v792.get("pass") is True else "blocked",
        "blocker",
        f"decision={v792.get('decision')} pass={v792.get('pass')}",
        [str(resolve(args.v792_manifest)), str(resolve(args.v792_dmesg))],
        "complete V792 before V793 route classification",
    ))
    checks.append(Check(
        "v792-safety",
        "pass" if not v792.get("wifi_hal_executed") and not v792.get("connect_executed") else "blocked",
        "blocker",
        f"service_manager={v792.get('service_manager_executed')} wifi_hal={v792.get('wifi_hal_executed')} connect={v792.get('connect_executed')}",
        [str(resolve(args.v792_manifest))],
        "do not route from evidence that crossed HAL/connect boundaries",
    ))
    checks.append(Check(
        "v792-cnss-no-wlfw",
        "pass" if v792.get("cnss_netlink", 0) and v792.get("service_notifier", 0) and not v792.get("wlfw") and not v792.get("bdf") and not v792.get("wlan0") else "blocked",
        "blocker",
        f"cnss_netlink={v792.get('cnss_netlink')} service_notifier={v792.get('service_notifier')} wlfw/bdf/wlan0={v792.get('wlfw')}/{v792.get('bdf')}/{v792.get('wlan0')}",
        [str(resolve(args.v792_dmesg))],
        "recapture V792 if CNSS or WLFW state is ambiguous",
    ))
    checks.append(Check(
        "service-manager-demoted",
        "pass" if reports["v660"].get("service_manager_ready") and reports["v660"].get("cnss_retry_executed") and reports["v666"].get("service_manager_ready") and reports["v666"].get("wlfw_absent") else "blocked",
        "blocker",
        f"v660_ready={reports['v660'].get('service_manager_ready')} v660_retry={reports['v660'].get('cnss_retry_executed')} v666_ready={reports['v666'].get('service_manager_ready')} v666_wlfw_absent={reports['v666'].get('wlfw_absent')}",
        [str(report_path(args, "v660")), str(report_path(args, "v666"))],
        "do not repeat service-manager readiness as the next primary gate",
    ))
    checks.append(Check(
        "binder-secondary-not-primary",
        "pass" if reports["v661"].get("binder_minus22") and reports["v666"].get("binder_minus22") and v792.get("binder_transaction_minus22", 0) else "review",
        "warn",
        f"v792_binder_tx={v792.get('binder_transaction_minus22')} v661_binder={reports['v661'].get('binder_minus22')} v666_binder={reports['v666'].get('binder_minus22')}",
        [str(report_path(args, "v661")), str(report_path(args, "v666")), str(resolve(args.v792_dmesg))],
        "capture binder context only as part of ICNSS/WLFW route, not as an unchanged retry",
    ))
    checks.append(Check(
        "boot-wlan-demoted",
        "pass" if reports["v750"].get("boot_wlan_no_advance") and reports["v752"].get("boot_wlan_no_advance") else "blocked",
        "blocker",
        f"v750={reports['v750'].get('boot_wlan_no_advance')} v752={reports['v752'].get('boot_wlan_no_advance')}",
        [str(report_path(args, "v750")), str(report_path(args, "v752"))],
        "do not repeat blind boot_wlan/qcwlanstate without new observability",
    ))
    checks.append(Check(
        "icnss-architecture",
        "pass" if reports["v763"].get("icnss_arch_rebased") else "blocked",
        "blocker",
        f"v763_icnss_arch={reports['v763'].get('icnss_arch_rebased')}",
        [str(report_path(args, "v763"))],
        "route next work through ICNSS/QCACLD, not CNSS2/MHI assumptions",
    ))
    checks.append(Check(
        "mdm3-primary-gap",
        "pass" if reports["v783"].get("mdm3_android_online_native_offlining") and reports["v785"].get("mdm3_android_online_native_offlining") and "OFFLINING" in v792.get("mdm3", []) else "blocked",
        "blocker",
        f"v792_mdm3={v792.get('mdm3')} v783={reports['v783'].get('mdm3_android_online_native_offlining')} v785={reports['v785'].get('mdm3_android_online_native_offlining')}",
        [str(report_path(args, "v783")), str(report_path(args, "v785")), str(resolve(args.v792_manifest))],
        "make mdm3/ICNSS-WLFW continuation the next primary route",
    ))
    checks.append(Check(
        "memshare-demoted",
        "pass" if reports["v785"].get("memshare_demoted") else "review",
        "warn",
        f"v785_memshare_demoted={reports['v785'].get('memshare_demoted')}",
        [str(report_path(args, "v785"))],
        "avoid memshare-only reruns unless mdm3/ICNSS evidence points there",
    ))
    checks.append(Check(
        "host-only-safety",
        "pass",
        "blocker",
        "bounded local evidence reads only",
        [],
        "preserve host-only behavior",
    ))
    return checks


def decide(args: argparse.Namespace, checks: list[Check], v792: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v793-cnss-icnss-route-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only V793 route classifier",
        )
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return (
            "v793-cnss-icnss-route-classifier-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "repair evidence inputs before selecting next live gate",
        )
    return (
        "v793-route-mdm3-icnss-wlfw-continuation",
        True,
        "V792 plus prior V660/V666/V750/V752/V763/V783/V785 evidence demotes unchanged service-manager, binder-only, boot_wlan, and memshare-only retries; the closest current blocker is mdm3 staying OFFLINING before ICNSS/WLFW service69/BDF/wlan0 continuation",
        "plan V794 as a bounded read-only/current-live mdm3 + ICNSS/WLFW surface observer: no service-manager start, no Wi-Fi HAL, no boot_wlan/qcwlanstate write, no scan/connect/DHCP/external ping",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    v792 = manifest["v792"]
    report_rows = [
        [
            name,
            facts.get("decision"),
            facts.get("service_manager_ready"),
            facts.get("cnss_retry_executed"),
            facts.get("binder_minus22"),
            facts.get("boot_wlan_no_advance"),
            facts.get("icnss_arch_rebased"),
            facts.get("mdm3_android_online_native_offlining"),
            facts.get("memshare_demoted"),
        ]
        for name, facts in manifest["reports"].items()
    ]
    return "\n".join([
        "# V793 CNSS/ICNSS Route Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## V792 Current Live Facts",
        "",
        markdown_table(["signal", "value"], [
            ["decision", v792.get("decision")],
            ["mss", " -> ".join(v792.get("mss") or [])],
            ["mdm3", " -> ".join(v792.get("mdm3") or [])],
            ["service_notifier/sysmon", f"{v792.get('service_notifier')} / {v792.get('sysmon_qmi')}"],
            ["cnss netlink / diag", f"{v792.get('cnss_netlink')} / {v792.get('cnss_diag_netlink')}"],
            ["binder ioctl/tx -22", f"{v792.get('binder_ioctl_minus22')} / {v792.get('binder_transaction_minus22')}"],
            ["ICNSS-QMI / WLFW / BDF / wlan0", f"{v792.get('icnss_qmi')} / {v792.get('wlfw')} / {v792.get('bdf')} / {v792.get('wlan0')}"],
            ["known ASoC warning", v792.get("known_warning")],
            ["HAL/connect executed", f"{v792.get('wifi_hal_executed')} / {v792.get('connect_executed')}"]
        ]),
        "",
        "## Prior Evidence Matrix",
        "",
        markdown_table(["report", "decision", "svc_mgr_ready", "cnss_retry", "binder_-22", "boot_wlan_no_advance", "ICNSS_arch", "mdm3_delta", "memshare_demoted"], report_rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Safety",
        "",
        "- Host-only classifier.",
        "- No device command, reboot, mount, daemon start, Wi-Fi action, credential use, network change, boot image write, partition write, or custom kernel flash.",
        "- Reads are bounded to avoid broad evidence scans.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v792_manifest = load_json(args.v792_manifest)
    v792 = v792_facts(v792_manifest, args.v792_dmesg)
    reports = {name: report_facts(name, report_path(args, name)) for name in REPORT_DEFAULTS}
    checks = build_checks(args, v792, reports)
    decision, passed, reason, next_step = decide(args, checks, v792)
    manifest = {
        "cycle": "v793",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "v792": v792,
        "reports": reports,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    print("device_commands_executed: False")
    print("wifi_hal_start_executed: False")
    print("scan_connect_executed: False")
    print("external_ping_executed: False")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
