#!/usr/bin/env python3
"""V791 host-only classifier for the current lower-only warning route.

V790 reproduced the ASoC/pm_qos warning without cnss_diag/cnss-daemon.  Older
Android evidence later showed the same warning class can occur on stock Android
while Wi-Fi still continues to WLFW/BDF/wlan0.  This classifier reconciles the
current V790 result with the existing warning/continuation evidence and routes
the next gate toward the real Wi-Fi blocker without touching the device.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v791-current-warning-route-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v791-current-warning-route-classifier.txt")
DEFAULT_V790_MANIFEST = Path("tmp/wifi/v790-clean-dsp-lower-only/manifest.json")
DEFAULT_V790_DMESG = Path("tmp/wifi/v790-clean-dsp-lower-only/native/dmesg-delta.txt")
DEFAULT_V788_MANIFEST = Path("tmp/wifi/v788-clean-dsp-lower-readback/manifest.json")
DEFAULT_V788_DMESG = Path("tmp/wifi/v788-clean-dsp-lower-readback/native/dmesg-delta.txt")
DEFAULT_V787_MANIFEST = Path("tmp/wifi/v787-clean-dsp-arm-only/manifest.json")
DEFAULT_V733_MANIFEST = Path("tmp/wifi/v733-holder-lower-companion/manifest.json")
DEFAULT_V735_MANIFEST = Path("tmp/wifi/v735-current-cnss-only-observer/manifest.json")
DEFAULT_V642_REPORT = Path("docs/reports/NATIVE_INIT_V642_CLEAN_DSP_LOWER_COMPANION_LIVE_2026-05-23.md")
DEFAULT_V645_REPORT = Path("docs/reports/NATIVE_INIT_V645_V644_WARNING_ATTRIBUTION_2026-05-23.md")
DEFAULT_V647_REPORT = Path("docs/reports/NATIVE_INIT_V647_WARNING_SOURCE_CLASSIFIER_2026-05-23.md")
DEFAULT_V649_REPORT = Path("docs/reports/NATIVE_INIT_V649_ANDROID_FULL_AUDIO_WIFI_RECAPTURE_LIVE_2026-05-23.md")
DEFAULT_V650_REPORT = Path("docs/reports/NATIVE_INIT_V650_POST_WARNING_CONTINUATION_2026-05-23.md")
DEFAULT_V651_REPORT = Path("docs/reports/NATIVE_INIT_V651_CNSS_WLFW_CONTINUATION_2026-05-23.md")
READ_LIMIT_BYTES = 8 * 1024 * 1024

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
DMESG_TIME_RE = re.compile(r"\[\s*(?P<time>[0-9]+\.[0-9]+)\]")
DECISION_RE = re.compile(r"decision:\s*`?(?P<decision>[a-z0-9_.-]+)`?", re.IGNORECASE)
REASON_RE = re.compile(r"reason:\s*(?P<reason>.+)", re.IGNORECASE)
NEXT_RE = re.compile(r"next:\s*(?P<next>.+)", re.IGNORECASE)

EVENT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("qrtr_rx", re.compile(r"qrtr: Modem QMI Readiness RX", re.IGNORECASE)),
    ("qrtr_tx", re.compile(r"qrtr: Modem QMI Readiness TX", re.IGNORECASE)),
    ("sysmon_modem", re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.IGNORECASE)),
    ("sysmon_adsp", re.compile(r"sysmon-qmi:.*adsp's SSCTL service", re.IGNORECASE)),
    ("sysmon_cdsp", re.compile(r"sysmon-qmi:.*cdsp's SSCTL service", re.IGNORECASE)),
    ("sysmon_slpi", re.compile(r"sysmon-qmi:.*slpi's SSCTL service", re.IGNORECASE)),
    ("service180", re.compile(r"service-notifier:.*180 service", re.IGNORECASE)),
    ("service74", re.compile(r"service-notifier:.*74 service", re.IGNORECASE)),
    ("apr_adsp_up", re.compile(r"apr_adsp_up: Q6 is Up", re.IGNORECASE)),
    ("asoc_probe", re.compile(r"msm_asoc_machine_probe: Enter", re.IGNORECASE)),
    ("pm_qos_duplicate", re.compile(r"pm_qos_add_request\(\) called for already added request", re.IGNORECASE)),
    ("qos_warning", re.compile(r"WARNING: CPU:.*pm_qos_add_request", re.IGNORECASE)),
    ("sound_card", re.compile(r"Sound card .*registered", re.IGNORECASE)),
    ("wlfw", re.compile(r"wlfw|WLFW|WLAN FW", re.IGNORECASE)),
    ("bdf", re.compile(r"\bBDF\b|bdwlan|regdb", re.IGNORECASE)),
    ("wlan0", re.compile(r"\bwlan0\b", re.IGNORECASE)),
)


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
    parser.add_argument("--v790-manifest", type=Path, default=DEFAULT_V790_MANIFEST)
    parser.add_argument("--v790-dmesg", type=Path, default=DEFAULT_V790_DMESG)
    parser.add_argument("--v788-manifest", type=Path, default=DEFAULT_V788_MANIFEST)
    parser.add_argument("--v788-dmesg", type=Path, default=DEFAULT_V788_DMESG)
    parser.add_argument("--v787-manifest", type=Path, default=DEFAULT_V787_MANIFEST)
    parser.add_argument("--v733-manifest", type=Path, default=DEFAULT_V733_MANIFEST)
    parser.add_argument("--v735-manifest", type=Path, default=DEFAULT_V735_MANIFEST)
    parser.add_argument("--v642-report", type=Path, default=DEFAULT_V642_REPORT)
    parser.add_argument("--v645-report", type=Path, default=DEFAULT_V645_REPORT)
    parser.add_argument("--v647-report", type=Path, default=DEFAULT_V647_REPORT)
    parser.add_argument("--v649-report", type=Path, default=DEFAULT_V649_REPORT)
    parser.add_argument("--v650-report", type=Path, default=DEFAULT_V650_REPORT)
    parser.add_argument("--v651-report", type=Path, default=DEFAULT_V651_REPORT)
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


def clean_line(line: str) -> str:
    return ANSI_RE.sub("", line.rstrip("\n"))


def marker_counts(manifest: dict[str, Any]) -> dict[str, int]:
    for branch_name in ("lower_only", "lower_readback"):
        branch = manifest.get(branch_name) or {}
        live = branch.get("live") or {}
        markers = live.get("markers") or {}
        if markers:
            return {key: int(value or 0) for key, value in markers.items() if isinstance(value, int)}
    live = manifest.get("live") or {}
    markers = live.get("markers") or {}
    if isinstance(markers.get("counts"), dict):
        return {key: int(value or 0) for key, value in markers["counts"].items() if isinstance(value, int)}
    return {key: int(value or 0) for key, value in markers.items() if isinstance(value, int)}


def branch_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    for branch_name in ("lower_only", "lower_readback"):
        branch = manifest.get(branch_name)
        if isinstance(branch, dict) and branch:
            return branch
    return manifest


def safety_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    top_safety = manifest.get("safety") or {}
    branch_safety = (branch_payload(manifest).get("safety") or {}) if isinstance(branch_payload(manifest), dict) else {}
    merged = dict(branch_safety)
    merged.update(top_safety)
    return merged


def run_row(name: str, manifest: dict[str, Any]) -> dict[str, Any]:
    counts = marker_counts(manifest)
    safety = safety_payload(manifest)
    branch = branch_payload(manifest)
    helper = ((branch.get("live") or {}).get("helper") or (branch.get("live") or {}).get("helper_result") or {}) if isinstance(branch, dict) else {}
    return {
        "name": name,
        "path": manifest.get("path", ""),
        "decision": manifest.get("decision") or branch.get("decision", ""),
        "pass": manifest.get("pass") if manifest.get("pass") is not None else branch.get("pass"),
        "kernel_warning": counts.get("kernel_warning", counts.get("pm_qos_warning", 0)),
        "service_notifier": counts.get("service_notifier", 0),
        "sysmon_qmi": counts.get("sysmon_qmi", counts.get("sibling_sysmon", 0)),
        "service69_or_wlfw": counts.get("wlfw", 0),
        "bdf": counts.get("bdf", 0),
        "wlan0": counts.get("wlan0", 0),
        "cnss": bool(safety.get("cnss_diag_start_executed") or safety.get("cnss_daemon_start_executed") or helper.get("cnss_daemon") or helper.get("cnss_diag")),
        "lower": bool(safety.get("lower_companion_start_executed")),
        "wifi_hal": bool(safety.get("wifi_hal_start_executed")),
        "connect": bool(safety.get("scan_connect_executed") or safety.get("credential_use_executed") or safety.get("external_ping_executed")),
    }


def parse_dmesg_events(path: Path) -> dict[str, Any]:
    text, info = safe_read(path)
    events: dict[str, dict[str, Any]] = {
        name: {"count": 0, "first_time": None, "first_line": ""}
        for name, _pattern in EVENT_PATTERNS
    }
    selected_lines: list[str] = []
    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        if not line:
            continue
        matched = False
        time_match = DMESG_TIME_RE.search(line)
        timestamp = float(time_match.group("time")) if time_match else None
        for name, pattern in EVENT_PATTERNS:
            if pattern.search(line):
                matched = True
                event = events[name]
                event["count"] += 1
                if event["first_time"] is None:
                    event["first_time"] = timestamp
                    event["first_line"] = line
        if matched and len(selected_lines) < 160:
            selected_lines.append(line)
    return {
        "file": info,
        "events": events,
        "gaps_ms": compute_gaps_ms(events),
        "selected_lines": selected_lines,
    }


def compute_gaps_ms(events: dict[str, dict[str, Any]]) -> dict[str, float | None]:
    def gap_ms(start: str, end: str) -> float | None:
        start_time = events.get(start, {}).get("first_time")
        end_time = events.get(end, {}).get("first_time")
        if start_time is None or end_time is None:
            return None
        return round((float(end_time) - float(start_time)) * 1000.0, 3)

    return {
        "service180_to_service74": gap_ms("service180", "service74"),
        "service74_to_asoc_probe": gap_ms("service74", "asoc_probe"),
        "asoc_probe_to_pm_qos_duplicate": gap_ms("asoc_probe", "pm_qos_duplicate"),
        "service74_to_pm_qos_duplicate": gap_ms("service74", "pm_qos_duplicate"),
        "pm_qos_duplicate_to_sound_card": gap_ms("pm_qos_duplicate", "sound_card"),
        "pm_qos_duplicate_to_wlfw": gap_ms("pm_qos_duplicate", "wlfw"),
    }


def report_facts(path: Path) -> dict[str, Any]:
    text, info = safe_read(path)
    decisions = [match.group("decision") for match in DECISION_RE.finditer(text)]
    reasons = [match.group("reason").strip(" `") for match in REASON_RE.finditer(text)]
    next_steps = [match.group("next").strip(" `") for match in NEXT_RE.finditer(text)]
    return {
        "file": info,
        "decisions": decisions[:5],
        "reason": reasons[0] if reasons else "",
        "next": next_steps[0] if next_steps else "",
        "has_android_warning_continues": "Android also emits the same warning" in text and "wlan0" in text,
        "has_post_warning_wlfw_gap": "first meaningful native-only gap is WLFW continuation" in text,
        "has_cnss_binder_wlfw_gap": (
            "cnss-daemon" in text
            and ("binder -22" in text or "binder ioctl `-22`" in text or "native binder errors present" in text)
            and "WLFW" in text
        ),
        "has_service74_warning_risk": "service74" in text.replace(" `", "").replace("`", "") and "warning" in text.lower(),
        "has_audio_asoc_source": "msm_asoc_machine_probe" in text and "pm_qos" in text,
    }


def build_checks(args: argparse.Namespace,
                 rows: dict[str, dict[str, Any]],
                 dmesg: dict[str, dict[str, Any]],
                 reports: dict[str, dict[str, Any]]) -> list[Check]:
    checks: list[Check] = []
    v790 = rows["v790"]
    v788 = rows["v788"]
    v787 = rows["v787"]
    v733 = rows["v733"]
    v735 = rows["v735"]
    v790_events = dmesg["v790"]["events"]
    v788_events = dmesg["v788"]["events"]
    checks.append(Check(
        "v790-current-input",
        "pass" if v790["decision"] == "v790-clean-dsp-lower-only-blocked" and v790["kernel_warning"] > 0 else "blocked",
        "blocker",
        f"decision={v790['decision']} warning={v790['kernel_warning']} cnss={v790['cnss']} wlfw={v790['service69_or_wlfw']} wlan0={v790['wlan0']}",
        [str(resolve(args.v790_manifest)), str(resolve(args.v790_dmesg))],
        "complete V790 before routing the current warning boundary",
    ))
    checks.append(Check(
        "lower-only-cnss-absent",
        "pass" if v790["lower"] and not v790["cnss"] and not v790["wifi_hal"] and not v790["connect"] else "blocked",
        "blocker",
        f"lower={v790['lower']} cnss={v790['cnss']} wifi_hal={v790['wifi_hal']} connect={v790['connect']}",
        [str(resolve(args.v790_manifest))],
        "do not use V790 if it crossed CNSS/HAL/connect boundaries",
    ))
    checks.append(Check(
        "service74-warning-signature",
        "pass" if v790_events["service74"]["count"] and v790_events["pm_qos_duplicate"]["count"] and v790_events["asoc_probe"]["count"] else "blocked",
        "blocker",
        f"service74={v790_events['service74']['count']} asoc={v790_events['asoc_probe']['count']} pm_qos={v790_events['pm_qos_duplicate']['count']} gap_ms={dmesg['v790']['gaps_ms'].get('service74_to_pm_qos_duplicate')}",
        [str(resolve(args.v790_dmesg))],
        "recapture V790 dmesg if exact ASoC warning signature is missing",
    ))
    checks.append(Check(
        "v788-corroborates-current-warning",
        "pass" if v788["kernel_warning"] > 0 and v788_events["service74"]["count"] and v788_events["pm_qos_duplicate"]["count"] else "review",
        "warn",
        f"warning={v788['kernel_warning']} cnss={v788['cnss']} service74={v788_events['service74']['count']} pm_qos={v788_events['pm_qos_duplicate']['count']}",
        [str(resolve(args.v788_manifest)), str(resolve(args.v788_dmesg))],
        "treat V790 as primary if V788 corroboration is absent",
    ))
    checks.append(Check(
        "clean-alone-warning-free",
        "pass" if v787["kernel_warning"] == 0 and not v787["service_notifier"] else "blocked",
        "blocker",
        f"v787_warning={v787['kernel_warning']} v787_service_notifier={v787['service_notifier']}",
        [str(resolve(args.v787_manifest))],
        "do not widen if clean-DSP alone is dirty",
    ))
    checks.append(Check(
        "historical-lower-warning-free",
        "pass" if v733["kernel_warning"] == 0 and v735["kernel_warning"] == 0 else "review",
        "warn",
        f"v733_warning={v733['kernel_warning']} v735_warning={v735['kernel_warning']}",
        [str(resolve(args.v733_manifest)), str(resolve(args.v735_manifest))],
        "use current V790 as primary if historical lower references are stale",
    ))
    checks.append(Check(
        "android-warning-continuation-reference",
        "pass" if reports["v649"].get("has_android_warning_continues") and reports["v650"].get("has_post_warning_wlfw_gap") else "blocked",
        "blocker",
        f"v649_android_continues={reports['v649'].get('has_android_warning_continues')} v650_post_warning_gap={reports['v650'].get('has_post_warning_wlfw_gap')}",
        [str(resolve(args.v649_report)), str(resolve(args.v650_report))],
        "keep warning as stop condition if Android continuation evidence is missing",
    ))
    checks.append(Check(
        "known-cnss-wlfw-continuation-gap",
        "pass" if reports["v651"].get("has_cnss_binder_wlfw_gap") else "review",
        "warn",
        f"v651_cnss_binder_wlfw_gap={reports['v651'].get('has_cnss_binder_wlfw_gap')}",
        [str(resolve(args.v651_report))],
        "if missing, route only to post-warning WLFW observer before binder/runtime work",
    ))
    checks.append(Check(
        "host-only-safety",
        "pass",
        "blocker",
        "V791 reads bounded local evidence only",
        [],
        "preserve host-only behavior",
    ))
    return checks


def decide(args: argparse.Namespace, checks: list[Check], rows: dict[str, dict[str, Any]], dmesg: dict[str, dict[str, Any]]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v791-current-warning-route-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only V791 classifier before any lower/CNSS live retry",
        )
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return (
            "v791-current-warning-route-classifier-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "repair missing evidence before choosing the next live gate",
        )
    v790 = rows["v790"]
    v790_events = dmesg["v790"]["events"]
    if v790["kernel_warning"] and v790_events["service74"]["count"] and not v790["service69_or_wlfw"]:
        return (
            "v791-known-asoc-warning-wlfw-route-classified",
            True,
            "V790 reproduced the known ASoC pm_qos warning below CNSS/HAL/connect; Android V649/V650 proves this warning class can continue to WLFW, so the current route should stop treating the exact signature as the first Wi-Fi blocker",
            "plan V792 as a known-ASoC-warning-tolerant CNSS/WLFW readback gate: exact warning allowlist only, no HAL/scan/connect/credentials/DHCP/external ping, success only on WLFW/service69/BDF/wlan0 or a sharper CNSS continuation blocker",
        )
    return (
        "v791-current-warning-route-classified",
        True,
        "current warning route classified, but no WLFW-positive branch exists yet",
        "route next live work to a bounded post-warning WLFW observer below HAL/connect",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [
            row["name"], row["decision"], row["pass"], row["kernel_warning"], row["service_notifier"], row["sysmon_qmi"],
            row["service69_or_wlfw"], row["bdf"], row["wlan0"], row["cnss"], row["wifi_hal"], row["connect"],
        ]
        for row in manifest["runs"].values()
    ]
    event_rows = []
    for name, parsed in manifest["dmesg"].items():
        events = parsed["events"]
        gaps = parsed["gaps_ms"]
        event_rows.append([
            name,
            events["service180"]["count"],
            events["service74"]["count"],
            events["asoc_probe"]["count"],
            events["pm_qos_duplicate"]["count"],
            events["sound_card"]["count"],
            events["wlfw"]["count"],
            gaps.get("service74_to_pm_qos_duplicate"),
            gaps.get("pm_qos_duplicate_to_sound_card"),
        ])
    report_rows = [
        [name, facts["decisions"][0] if facts["decisions"] else "", facts.get("has_android_warning_continues"), facts.get("has_post_warning_wlfw_gap"), facts.get("has_cnss_binder_wlfw_gap")]
        for name, facts in manifest["reports"].items()
    ]
    return "\n".join([
        "# V791 Current Warning Route Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Run Matrix",
        "",
        markdown_table(["run", "decision", "pass", "warning", "service_notifier", "sysmon", "WLFW", "BDF", "wlan0", "CNSS", "HAL", "connect"], rows),
        "",
        "## Dmesg Timing",
        "",
        markdown_table(["run", "svc180", "svc74", "ASoC", "pm_qos", "sound_card", "WLFW", "svc74->pm_qos ms", "pm_qos->sound_card ms"], event_rows),
        "",
        "## Prior Classifiers",
        "",
        markdown_table(["report", "decision", "android_warning_continues", "post_warning_wlfw_gap", "cnss_binder_wlfw_gap"], report_rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Selected V790 Lines",
        "",
        "```text",
        "\n".join(manifest["dmesg"]["v790"]["selected_lines"][:80]),
        "```",
        "",
        "## Safety",
        "",
        "- Host-only classifier.",
        "- No device command, reboot, mount, daemon start, Wi-Fi action, credential use, network change, boot image write, partition write, or custom kernel flash.",
        "- Reads are bounded to avoid broad evidence scans.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    manifests = {
        "v790": load_json(args.v790_manifest),
        "v788": load_json(args.v788_manifest),
        "v787": load_json(args.v787_manifest),
        "v733": load_json(args.v733_manifest),
        "v735": load_json(args.v735_manifest),
    }
    rows = {name: run_row(name, manifest) for name, manifest in manifests.items()}
    dmesg = {
        "v790": parse_dmesg_events(args.v790_dmesg),
        "v788": parse_dmesg_events(args.v788_dmesg),
    }
    reports = {
        "v642": report_facts(args.v642_report),
        "v645": report_facts(args.v645_report),
        "v647": report_facts(args.v647_report),
        "v649": report_facts(args.v649_report),
        "v650": report_facts(args.v650_report),
        "v651": report_facts(args.v651_report),
    }
    checks = build_checks(args, rows, dmesg, reports)
    decision, passed, reason, next_step = decide(args, checks, rows, dmesg)
    manifest = {
        "cycle": "v791",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "runs": rows,
        "dmesg": dmesg,
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
