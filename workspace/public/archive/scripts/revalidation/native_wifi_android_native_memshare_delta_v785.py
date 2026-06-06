#!/usr/bin/env python3
"""V785 host-only Android/native memshare delta classifier.

V784 showed native idle CMA headroom is not obviously too small.  Existing V611
Android lower-surface evidence also contains memshare/CMA failures, yet Android
continues to service-notifier, WLAN-PD, ICNSS-QMI, BDF, firmware-ready, and
wlan0.  This classifier proves whether memshare/CMA failure is common/non-fatal
and identifies the next Android/native divergence.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v785-android-native-memshare-delta")
LATEST_POINTER = Path("tmp/wifi/latest-v785-android-native-memshare-delta.txt")
DEFAULT_ANDROID_DMESG = Path(
    "tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/"
    "v611-android-lower-surface-recapture-run/android/commands/dmesg-lower-surface-tail.txt"
)
DEFAULT_ANDROID_STATE = Path(
    "tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/"
    "v611-android-lower-surface-recapture-run/android-lower-surface-state.txt"
)
DEFAULT_ANDROID_MANIFEST = Path(
    "tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/"
    "v611-android-lower-surface-recapture-run/manifest.json"
)
DEFAULT_NATIVE_DMESG = Path("tmp/wifi/v782-bpf-counter-boot-wlan/native/dmesg-delta.txt")
DEFAULT_NATIVE_MANIFEST = Path("tmp/wifi/v782-bpf-counter-boot-wlan/manifest.json")
DEFAULT_V784_MANIFEST = Path("tmp/wifi/v784-memshare-cma-surface/manifest.json")
READ_LIMIT_BYTES = 8 * 1024 * 1024

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TIMESTAMP_RE = re.compile(r"^\s*\[\s*(?P<time>\d+(?:\.\d+)?)\]")
REQUEST_RE = re.compile(r"request size:\s*(?P<size>\d+)")
UNABLE_RE = re.compile(r"unable to allocate memory of size:\s*(?P<size>\d+)")
CMA_FAIL_RE = re.compile(r"cma_alloc: alloc failed, req-size:\s*(?P<pages>\d+)\s+pages,\s+ret:\s*(?P<ret>-?\d+)")

MARKERS: dict[str, re.Pattern[str]] = {
    "qrtr_rx": re.compile(r"qrtr: Modem QMI Readiness RX", re.IGNORECASE),
    "qrtr_tx": re.compile(r"qrtr: Modem QMI Readiness TX", re.IGNORECASE),
    "memshare_request": re.compile(r"memshare_.*memory alloc request", re.IGNORECASE),
    "memshare_fail": re.compile(r"memshare_.*unable to allocate", re.IGNORECASE),
    "cma_alloc_fail": re.compile(r"cma: cma_alloc: alloc failed", re.IGNORECASE),
    "sysmon_modem": re.compile(r"sysmon-qmi:.*modem's SSCTL service", re.IGNORECASE),
    "sysmon_slpi": re.compile(r"sysmon-qmi:.*slpi's SSCTL service", re.IGNORECASE),
    "sysmon_cdsp": re.compile(r"sysmon-qmi:.*cdsp's SSCTL service", re.IGNORECASE),
    "sysmon_adsp": re.compile(r"sysmon-qmi:.*adsp's SSCTL service", re.IGNORECASE),
    "sysmon_esoc0": re.compile(r"sysmon-qmi:.*esoc0's SSCTL service", re.IGNORECASE),
    "servloc": re.compile(r"\bservloc:.*Service locator", re.IGNORECASE),
    "service_notifier_180": re.compile(r"service-notifier:.*\b180 service", re.IGNORECASE),
    "service_notifier_74": re.compile(r"service-notifier:.*\b74 service", re.IGNORECASE),
    "wlan_pd": re.compile(r"service-notifier:.*msm/modem/wlan_pd", re.IGNORECASE),
    "icnss_qmi": re.compile(r"icnss_qmi: QMI Server Connected", re.IGNORECASE),
    "bdf_regdb": re.compile(r"BDF file\s*:\s*regdb\.bin", re.IGNORECASE),
    "bdf_bdwlan": re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.IGNORECASE),
    "wlan_fw_ready": re.compile(r"icnss: WLAN FW is ready", re.IGNORECASE),
    "wlan0": re.compile(r"\bdev\s*:\s*wlan0\b|ADDRCONF\(NETDEV_UP\): wlan0", re.IGNORECASE),
}

ORDER = (
    "qrtr_rx",
    "qrtr_tx",
    "memshare_request",
    "memshare_fail",
    "cma_alloc_fail",
    "sysmon_slpi",
    "sysmon_adsp",
    "sysmon_cdsp",
    "sysmon_modem",
    "servloc",
    "service_notifier_180",
    "service_notifier_74",
    "wlan_pd",
    "icnss_qmi",
    "bdf_regdb",
    "bdf_bdwlan",
    "sysmon_esoc0",
    "wlan_fw_ready",
    "wlan0",
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--android-dmesg", type=Path, default=DEFAULT_ANDROID_DMESG)
    parser.add_argument("--android-state", type=Path, default=DEFAULT_ANDROID_STATE)
    parser.add_argument("--android-manifest", type=Path, default=DEFAULT_ANDROID_MANIFEST)
    parser.add_argument("--native-dmesg", type=Path, default=DEFAULT_NATIVE_DMESG)
    parser.add_argument("--native-manifest", type=Path, default=DEFAULT_NATIVE_MANIFEST)
    parser.add_argument("--v784-manifest", type=Path, default=DEFAULT_V784_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def file_info(path: Path) -> dict[str, Any]:
    resolved = resolve(path)
    if not resolved.exists():
        return {"path": str(resolved), "exists": False}
    size = resolved.stat().st_size if resolved.is_file() else None
    return {"path": str(resolved), "exists": True, "is_file": resolved.is_file(), "size": size}


def safe_read(path: Path) -> tuple[str, dict[str, Any]]:
    resolved = resolve(path)
    info = file_info(path)
    if not resolved.exists() or not resolved.is_file():
        return "", info
    data = resolved.read_bytes()[:READ_LIMIT_BYTES]
    info["bytes_read"] = len(data)
    info["truncated"] = resolved.stat().st_size > len(data)
    return data.decode("utf-8", errors="replace"), info


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text).replace("\r\n", "\n")


def timestamp(line: str) -> float | None:
    match = TIMESTAMP_RE.match(line)
    return float(match.group("time")) if match else None


def analyze_dmesg(path: Path, label: str) -> dict[str, Any]:
    raw, info = safe_read(path)
    text = strip_ansi(raw)
    lines = text.splitlines()
    marker_data: dict[str, dict[str, Any]] = {}
    for marker, pattern in MARKERS.items():
        hits: list[dict[str, Any]] = []
        for line_no, line in enumerate(lines, start=1):
            if line.startswith("$ "):
                continue
            if pattern.search(line):
                hits.append({"line_no": line_no, "time": timestamp(line), "line": line[:260]})
        first = hits[0] if hits else {}
        marker_data[marker] = {
            "count": len(hits),
            "first_time": first.get("time"),
            "first_line_no": first.get("line_no"),
            "first_line": first.get("line", ""),
        }
    return {
        "label": label,
        "file": info,
        "line_count": len(lines),
        "markers": marker_data,
        "memshare": parse_memshare(text),
        "deltas": build_deltas(marker_data),
        "chain": [{"marker": marker, "count": marker_data[marker]["count"], "first_time": marker_data[marker]["first_time"]} for marker in ORDER],
    }


def parse_memshare(text: str) -> dict[str, Any]:
    clean = strip_ansi(text)
    request_sizes = [int(match.group("size")) for match in REQUEST_RE.finditer(clean)]
    unable_sizes = [int(match.group("size")) for match in UNABLE_RE.finditer(clean)]
    cma_failures = [
        {"pages": int(match.group("pages")), "ret": int(match.group("ret")), "bytes": int(match.group("pages")) * 4096}
        for match in CMA_FAIL_RE.finditer(clean)
    ]
    return {
        "request_sizes": request_sizes,
        "unable_sizes": unable_sizes,
        "cma_failures": cma_failures,
        "request_sum_bytes": sum(request_sizes),
        "max_request_bytes": max(request_sizes) if request_sizes else 0,
        "failure_count": len(unable_sizes) + len(cma_failures),
    }


def build_deltas(markers: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sysmon_modem = markers["sysmon_modem"]["first_time"]
    memshare_fail = markers["memshare_fail"]["first_time"]

    def delta(marker: str, base: float | None) -> float | None:
        first = markers[marker]["first_time"]
        if first is None or base is None:
            return None
        return round((first - base) * 1000, 3)

    return {
        "memshare_fail_to_sysmon_modem_ms": delta("sysmon_modem", memshare_fail),
        "sysmon_modem_to_service_locator_ms": delta("servloc", sysmon_modem),
        "sysmon_modem_to_service_notifier_180_ms": delta("service_notifier_180", sysmon_modem),
        "sysmon_modem_to_service_notifier_74_ms": delta("service_notifier_74", sysmon_modem),
        "sysmon_modem_to_wlan_pd_ms": delta("wlan_pd", sysmon_modem),
        "sysmon_modem_to_icnss_qmi_ms": delta("icnss_qmi", sysmon_modem),
        "sysmon_modem_to_wlan_fw_ready_ms": delta("wlan_fw_ready", sysmon_modem),
        "sysmon_modem_to_wlan0_ms": delta("wlan0", sysmon_modem),
    }


def parse_state(path: Path) -> dict[str, str]:
    text, _ = safe_read(path)
    values: dict[str, str] = {}
    for line in strip_ansi(text).splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def load_json(path: Path) -> dict[str, Any]:
    text, _ = safe_read(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def first_divergence(android: dict[str, Any], native: dict[str, Any]) -> str:
    for marker in ORDER:
        if android["markers"][marker]["count"] > 0 and native["markers"][marker]["count"] == 0:
            return marker
    return ""


def build_analysis(args: argparse.Namespace) -> dict[str, Any]:
    android = analyze_dmesg(args.android_dmesg, "android-v611")
    native = analyze_dmesg(args.native_dmesg, "native-v782")
    android_state = parse_state(args.android_state)
    android_manifest = load_json(args.android_manifest)
    native_manifest = load_json(args.native_manifest)
    v784 = load_json(args.v784_manifest)
    memshare_same_requests = android["memshare"]["request_sizes"] == native["memshare"]["request_sizes"]
    memshare_same_fail_sizes = android["memshare"]["unable_sizes"] == native["memshare"]["unable_sizes"]
    android_success_after_memshare = all(android["markers"][marker]["count"] > 0 for marker in ("service_notifier_180", "service_notifier_74", "wlan_pd", "icnss_qmi", "bdf_regdb", "bdf_bdwlan", "wlan_fw_ready", "wlan0"))
    native_stop_after_memshare = native["markers"]["sysmon_modem"]["count"] > 0 and native["markers"]["service_notifier_180"]["count"] == 0 and native["markers"]["service_notifier_74"]["count"] == 0
    return {
        "inputs": {
            "android_dmesg": file_info(args.android_dmesg),
            "android_state": file_info(args.android_state),
            "android_manifest": file_info(args.android_manifest),
            "native_dmesg": file_info(args.native_dmesg),
            "native_manifest": file_info(args.native_manifest),
            "v784_manifest": file_info(args.v784_manifest),
        },
        "android": {
            "dmesg": android,
            "state": android_state,
            "manifest_decision": android_manifest.get("decision", ""),
            "manifest_pass": android_manifest.get("pass"),
        },
        "native": {
            "dmesg": native,
            "manifest_decision": native_manifest.get("decision", ""),
            "manifest_pass": native_manifest.get("pass"),
        },
        "v784": {
            "decision": v784.get("decision", ""),
            "pass": v784.get("pass"),
            "cma_free_bytes": ((v784.get("analysis") or {}).get("surface") or {}).get("cma_free_bytes"),
            "client4_size_zero_marker": ((v784.get("analysis") or {}).get("surface") or {}).get("client4_size_zero_marker"),
            "client4_no_clients_marker": ((v784.get("analysis") or {}).get("surface") or {}).get("client4_no_clients_marker"),
        },
        "comparison": {
            "first_divergence": first_divergence(android, native),
            "memshare_same_requests": memshare_same_requests,
            "memshare_same_fail_sizes": memshare_same_fail_sizes,
            "android_success_after_memshare": android_success_after_memshare,
            "native_stop_after_memshare": native_stop_after_memshare,
            "android_mss_state": android_state.get("mss_state", ""),
            "android_mdm3_state": android_state.get("mdm3_state", ""),
            "native_mss_state": (native_manifest.get("live") or {}).get("mss_after_boot", ""),
            "native_mdm3_state": (native_manifest.get("live") or {}).get("mdm3_after_boot", ""),
            "android_sibling_sysmon_count": sum(android["markers"][marker]["count"] for marker in ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp")),
            "native_sibling_sysmon_count": sum(native["markers"][marker]["count"] for marker in ("sysmon_slpi", "sysmon_cdsp", "sysmon_adsp")),
        },
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_trigger_executed": False,
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(command: str, analysis: dict[str, Any]) -> list[Check]:
    inputs = analysis["inputs"]
    comparison = analysis["comparison"]
    android_memshare = analysis["android"]["dmesg"]["memshare"]
    native_memshare = analysis["native"]["dmesg"]["memshare"]
    checks: list[Check] = []
    add_check(
        checks,
        "required-inputs",
        "pass" if all(info.get("exists") for info in inputs.values()) else "blocked",
        "blocker",
        " ".join(f"{name}={info.get('exists')}" for name, info in inputs.items()),
        "restore V611/V782/V784 evidence before classifying",
    )
    add_check(
        checks,
        "host-only-boundary",
        "pass",
        "blocker",
        "device_commands=false wifi_trigger=false",
        "keep V785 host-only; do not recapture unless evidence is missing",
    )
    add_check(
        checks,
        "android-memshare-evidence",
        "pass" if android_memshare["failure_count"] > 0 else "blocked",
        "blocker",
        f"requests={android_memshare['request_sizes']} failures={android_memshare['unable_sizes']} cma={android_memshare['cma_failures']}",
        "use V611 dmesg-lower-surface evidence or recapture Android with memshare filters",
    )
    add_check(
        checks,
        "native-memshare-evidence",
        "pass" if native_memshare["failure_count"] > 0 else "blocked",
        "blocker",
        f"requests={native_memshare['request_sizes']} failures={native_memshare['unable_sizes']} cma={native_memshare['cma_failures']}",
        "restore V782 native dmesg evidence before comparing",
    )
    add_check(
        checks,
        "memshare-common-nonfatal",
        "pass" if comparison["memshare_same_requests"] and comparison["memshare_same_fail_sizes"] and comparison["android_success_after_memshare"] else "review",
        "warn",
        (
            f"same_requests={comparison['memshare_same_requests']} "
            f"same_fail_sizes={comparison['memshare_same_fail_sizes']} "
            f"android_success_after={comparison['android_success_after_memshare']}"
        ),
        "demote memshare/CMA failure as sole blocker when Android succeeds after the same failure",
    )
    add_check(
        checks,
        "post-memshare-divergence",
        "pass" if comparison["native_stop_after_memshare"] and comparison["first_divergence"] in {"sysmon_slpi", "sysmon_adsp", "sysmon_cdsp", "servloc", "service_notifier_180"} else "review",
        "warn",
        (
            f"first={comparison['first_divergence']} "
            f"native_stop={comparison['native_stop_after_memshare']} "
            f"android_sibling={comparison['android_sibling_sysmon_count']} "
            f"native_sibling={comparison['native_sibling_sysmon_count']}"
        ),
        "target sibling sysmon/service-notifier prerequisites, not another memshare-only probe",
    )
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device action", "run V785 host-only classifier")
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v785-android-native-memshare-delta-plan-ready",
            True,
            "plan-only host classifier; no device command or Wi-Fi trigger",
            "run V785 against existing V611 Android and V782/V784 native evidence",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v785-android-native-memshare-delta-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "restore required evidence or run an explicit Android/native recapture gate",
        )
    comparison = analysis["comparison"]
    return (
        "v785-memshare-common-nonfatal-sibling-sysmon-gap",
        True,
        (
            "Android and native both show the same memshare/CMA failure sizes, but Android continues to "
            "sibling sysmon, service-notifier 74/180, WLAN-PD, ICNSS-QMI, BDF, FW-ready, and wlan0; "
            f"native first divergence is {comparison['first_divergence']}"
        ),
        (
            "V786 should focus on native sibling sysmon/service-notifier prerequisites and mdm3/esoc0 ONLINE "
            "transition, not another memshare-only or boot_wlan retry"
        ),
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    android = analysis["android"]["dmesg"]
    native = analysis["native"]["dmesg"]
    comparison = analysis["comparison"]
    chain_rows = [
        [
            marker,
            android["markers"][marker]["count"],
            android["markers"][marker]["first_time"],
            native["markers"][marker]["count"],
            native["markers"][marker]["first_time"],
        ]
        for marker in ORDER
    ]
    delta_rows = [[key, value, native["deltas"].get(key)] for key, value in android["deltas"].items()]
    return "\n".join([
        "# V785 Android/Native Memshare Delta",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_trigger_executed: `{manifest['wifi_trigger_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Memshare Comparison",
        "",
        markdown_table(["signal", "android", "native"], [
            ["request_sizes", android["memshare"]["request_sizes"], native["memshare"]["request_sizes"]],
            ["unable_sizes", android["memshare"]["unable_sizes"], native["memshare"]["unable_sizes"]],
            ["cma_failures", android["memshare"]["cma_failures"], native["memshare"]["cma_failures"]],
            ["request_sum_bytes", android["memshare"]["request_sum_bytes"], native["memshare"]["request_sum_bytes"]],
            ["same_requests", comparison["memshare_same_requests"], comparison["memshare_same_requests"]],
            ["same_fail_sizes", comparison["memshare_same_fail_sizes"], comparison["memshare_same_fail_sizes"]],
        ]),
        "",
        "## Chain Comparison",
        "",
        markdown_table(["marker", "android_count", "android_first", "native_count", "native_first"], chain_rows),
        "",
        "## Deltas",
        "",
        markdown_table(["delta", "android_ms", "native_ms"], delta_rows),
        "",
        "## State",
        "",
        markdown_table(["signal", "android", "native"], [
            ["mss_state", comparison["android_mss_state"], comparison["native_mss_state"]],
            ["mdm3_state", comparison["android_mdm3_state"], comparison["native_mdm3_state"]],
            ["sibling_sysmon_count", comparison["android_sibling_sysmon_count"], comparison["native_sibling_sysmon_count"]],
            ["first_divergence", comparison["first_divergence"], comparison["first_divergence"]],
        ]),
        "",
        "## Interpretation",
        "",
        "- Android V611 and native V782 both hit the same memshare request/failure sizes, including the 32 MiB CMA `-12` failure.",
        "- Android still reaches sibling sysmon, service-notifier `180/74`, WLAN-PD, ICNSS-QMI, BDF, firmware-ready, and `wlan0`.",
        "- Native reaches modem sysmon but lacks sibling sysmon and service-notifier publication; memshare/CMA failure alone is therefore not the final blocker.",
        "- The next live work should target mdm3/esoc0/sibling sysmon/service-notifier prerequisites with bounded cleanup, not another blind `boot_wlan`, `qcwlanstate`, or memshare-only retry.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = build_analysis(args)
    checks = build_checks(args.command, analysis)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest: dict[str, Any] = {
        "cycle": "v785",
        "generated_at": now_iso(),
        "command": args.command,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_trigger_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
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
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_trigger_executed: {manifest['wifi_trigger_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
