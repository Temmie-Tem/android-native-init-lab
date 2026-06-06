#!/usr/bin/env python3
"""V684 host-only cnss-daemon vndbinder target classifier.

This classifier consumes V683/V682 evidence plus local exported vendor ELF
files to identify the most likely native-only vendor Binder target before WLFW.
It does not contact the device, start daemons, mount filesystems, scan/connect,
use credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v684-cnss-daemon-vndbinder-target")
DEFAULT_V683_MANIFEST = Path("tmp/wifi/v683-cnss2-qmi-trigger-isolation/manifest.json")
DEFAULT_V682_MANIFEST = Path("tmp/wifi/v682-cnss2-wlfw-progression-observer-live/manifest.json")
DEFAULT_V682_LIVE_MANIFEST = Path(
    "tmp/wifi/v682-cnss2-wlfw-progression-observer-live/arm-v679-v112-observer/live/manifest.json"
)
DEFAULT_VENDOR_ROOT = Path("tmp/wifi/v226-vendor-root-live-export/vendor-source")
DEFAULT_CNSS_DAEMON = DEFAULT_VENDOR_ROOT / "bin/cnss-daemon"
DEFAULT_LIBPERIPHERAL_CLIENT = DEFAULT_VENDOR_ROOT / "lib64/libperipheral_client.so"
DEFAULT_LIBQMISERVICES = DEFAULT_VENDOR_ROOT / "lib64/libqmiservices.so"

STATIC_TERMS = {
    "cnss_daemon": (
        "libperipheral_client.so",
        "pm_client_register",
        "pm_client_connect",
        "wlfw_start",
        "Failed to start wlfw service",
        "/data/vendor/wifi/sockets/cnss_user_server",
    ),
    "libperipheral_client": (
        "libbinder.so",
        "/dev/vndbinder",
        "defaultServiceManager",
        "IPeripheralManager",
        "vendor.qcom.PeripheralManager",
        "pm_client_register",
        "pm_client_connect",
    ),
    "libqmiservices": (
        "libbinder.so",
        "vendor.qcom.PeripheralManager",
        "wlfw",
    ),
}

LIVE_TERMS = (
    "cnss-daemon",
    "libperipheral_client.so",
    "transaction failed",
    "29189/-22",
    "vendor.qcom.PeripheralManager",
    "wlfw_start",
    "QMI Server Connected",
    "BDF file",
)

FORBIDDEN_ACTIONS = (
    "device command",
    "mount or bind mount",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "supplicant or hostapd start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "sysfs or debugfs write",
    "boot image or partition write",
)

ASCII_RE = re.compile(rb"[\x20-\x7e]{4,}")
CNSS_BINDER_FAIL_RE = re.compile(r"cnss-daemon.*binder:.*transaction failed .*?-22", re.I)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v683-manifest", type=Path, default=DEFAULT_V683_MANIFEST)
    parser.add_argument("--v682-manifest", type=Path, default=DEFAULT_V682_MANIFEST)
    parser.add_argument("--v682-live-manifest", type=Path, default=DEFAULT_V682_LIVE_MANIFEST)
    parser.add_argument("--cnss-daemon", type=Path, default=DEFAULT_CNSS_DAEMON)
    parser.add_argument("--libperipheral-client", type=Path, default=DEFAULT_LIBPERIPHERAL_CLIENT)
    parser.add_argument("--libqmiservices", type=Path, default=DEFAULT_LIBQMISERVICES)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def nested(mapping: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "pass", "ready"}


def intish(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def sha256_file(path: Path) -> str:
    resolved = repo_path(path)
    digest = hashlib.sha256()
    with resolved.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_ascii_strings(path: Path) -> list[str]:
    resolved = repo_path(path)
    if not resolved.exists():
        return []
    return [match.group(0).decode("utf-8", errors="replace") for match in ASCII_RE.finditer(resolved.read_bytes())]


def binary_surface(path: Path, terms: tuple[str, ...]) -> dict[str, Any]:
    resolved = repo_path(path)
    exists = resolved.exists()
    strings = extract_ascii_strings(path) if exists else []
    matches = {
        term: sorted({item for item in strings if term in item})[:8]
        for term in terms
    }
    return {
        "path": str(resolved),
        "exists": exists,
        "size": resolved.stat().st_size if exists else 0,
        "sha256": sha256_file(path) if exists else "",
        "terms": {term: bool(matches[term]) for term in terms},
        "matched_strings": matches,
    }


def bounded_matching_lines(text: str, needle: str, limit: int = 12) -> list[str]:
    rows: list[str] = []
    for line in text.splitlines():
        if needle in line:
            rows.append(line.strip()[:240])
            if len(rows) >= limit:
                break
    return rows


def build_static_surface(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "cnss_daemon": binary_surface(args.cnss_daemon, STATIC_TERMS["cnss_daemon"]),
        "libperipheral_client": binary_surface(args.libperipheral_client, STATIC_TERMS["libperipheral_client"]),
        "libqmiservices": binary_surface(args.libqmiservices, STATIC_TERMS["libqmiservices"]),
    }


def build_live_surface(v682: dict[str, Any], v682_live: dict[str, Any]) -> dict[str, Any]:
    helper_text = str(nested(v682_live, ("live", "helper_stdout_stderr"), ""))
    dmesg_text = str(nested(v682_live, ("live", "dmesg_delta"), ""))
    combined = helper_text + "\n" + dmesg_text
    counts = nested(v682, ("arm_v682", "counts"), {}) or {}
    markers = nested(v682, ("arm_v682", "markers"), {}) or {}
    return {
        "v682_decision": v682.get("decision", ""),
        "v682_pass": boolish(v682.get("pass")),
        "term_counts": {term: combined.count(term) for term in LIVE_TERMS},
        "cnss_binder_failures": len(CNSS_BINDER_FAIL_RE.findall(dmesg_text)),
        "libperipheral_client_lines": bounded_matching_lines(helper_text, "libperipheral_client.so"),
        "cnss_binder_failure_lines": bounded_matching_lines(dmesg_text, "cnss-daemon"),
        "counts": {
            "service_notifier_180": intish(counts.get("service_notifier_180")),
            "service_notifier_74": intish(counts.get("service_notifier_74")),
            "cnss_daemon_netlink": intish(counts.get("cnss_daemon_netlink")),
            "cnss_daemon_cld80211": intish(counts.get("cnss_daemon_cld80211")),
            "cnss_binder_transaction_failed": intish(counts.get("cnss_binder_transaction_failed")),
            "qmi_server_connected": intish(counts.get("qmi_server_connected")),
            "wlfw_start": intish(counts.get("wlfw_start")),
            "wlfw_service_request": intish(counts.get("wlfw_service_request")),
            "bdf_regdb": intish(counts.get("bdf_regdb")),
            "bdf_bdwlan": intish(counts.get("bdf_bdwlan")),
            "wlan_fw_ready": intish(counts.get("wlan_fw_ready")),
            "wlan0": intish(counts.get("wlan0")),
        },
        "markers": {
            "qrtr_rx": intish(markers.get("qrtr_rx")),
            "qrtr_tx": intish(markers.get("qrtr_tx")),
            "sysmon_qmi": intish(markers.get("sysmon_qmi")),
        },
    }


def build_surface(args: argparse.Namespace) -> dict[str, Any]:
    v683 = load_json(args.v683_manifest)
    v682 = load_json(args.v682_manifest)
    v682_live = load_json(args.v682_live_manifest)
    return {
        "v683": {
            "decision": v683.get("decision", ""),
            "pass": boolish(v683.get("pass")),
            "reason": v683.get("reason", ""),
            "next_step": v683.get("next_step", ""),
        },
        "static": build_static_surface(args),
        "live": build_live_surface(v682, v682_live),
    }


def term_present(surface: dict[str, Any], group: str, term: str) -> bool:
    return bool(nested(surface, ("static", group, "terms", term), False))


def build_checks(surface: dict[str, Any]) -> list[dict[str, Any]]:
    live_counts = nested(surface, ("live", "counts"), {}) or {}
    live_terms = nested(surface, ("live", "term_counts"), {}) or {}
    cnss_daemon = nested(surface, ("static", "cnss_daemon"), {}) or {}
    libperipheral = nested(surface, ("static", "libperipheral_client"), {}) or {}
    libqmiservices = nested(surface, ("static", "libqmiservices"), {}) or {}
    return [
        {
            "name": "input-v683-ready",
            "status": "pass" if surface["v683"]["pass"] else "blocked",
            "detail": surface["v683"],
            "next_step": "refresh V683 if pre-WLFW trigger routing is stale",
        },
        {
            "name": "cnss-daemon-imports-peripheral-client",
            "status": "finding" if (
                cnss_daemon.get("exists")
                and term_present(surface, "cnss_daemon", "libperipheral_client.so")
                and term_present(surface, "cnss_daemon", "pm_client_register")
                and term_present(surface, "cnss_daemon", "wlfw_start")
            ) else "review",
            "detail": {
                "path": cnss_daemon.get("path"),
                "sha256": cnss_daemon.get("sha256"),
                "terms": cnss_daemon.get("terms"),
            },
            "next_step": "treat peripheral client as the static Binder bridge candidate for CNSS",
        },
        {
            "name": "peripheral-client-uses-vndbinder-service-manager",
            "status": "finding" if (
                libperipheral.get("exists")
                and term_present(surface, "libperipheral_client", "libbinder.so")
                and term_present(surface, "libperipheral_client", "/dev/vndbinder")
                and term_present(surface, "libperipheral_client", "defaultServiceManager")
                and term_present(surface, "libperipheral_client", "vendor.qcom.PeripheralManager")
            ) else "review",
            "detail": {
                "path": libperipheral.get("path"),
                "sha256": libperipheral.get("sha256"),
                "terms": libperipheral.get("terms"),
            },
            "next_step": "check vendor.qcom.PeripheralManager availability before another CNSS retry",
        },
        {
            "name": "qmiservices-not-the-static-binder-target",
            "status": "finding" if (
                libqmiservices.get("exists")
                and not term_present(surface, "libqmiservices", "vendor.qcom.PeripheralManager")
                and not term_present(surface, "libqmiservices", "libbinder.so")
            ) else "review",
            "detail": {
                "path": libqmiservices.get("path"),
                "sha256": libqmiservices.get("sha256"),
                "terms": libqmiservices.get("terms"),
            },
            "next_step": "keep WLFW/QMI payload probing behind Binder target availability",
        },
        {
            "name": "live-cnss-daemon-mapped-peripheral-client",
            "status": "finding" if (
                live_terms.get("cnss-daemon", 0) > 0
                and live_terms.get("libperipheral_client.so", 0) > 0
            ) else "review",
            "detail": {
                "term_counts": live_terms,
                "sample_lines": nested(surface, ("live", "libperipheral_client_lines"), []),
            },
            "next_step": "capture service availability rather than only ELF strings",
        },
        {
            "name": "live-binder-failure-precedes-missing-wlfw",
            "status": "finding" if (
                live_counts.get("service_notifier_74", 0) > 0
                and live_counts.get("cnss_daemon_netlink", 0) > 0
                and live_counts.get("cnss_binder_transaction_failed", 0) > 0
                and live_counts.get("wlfw_start", 0) == 0
                and live_counts.get("qmi_server_connected", 0) == 0
                and live_counts.get("wlan0", 0) == 0
            ) else "review",
            "detail": {
                "counts": live_counts,
                "cnss_binder_failures": nested(surface, ("live", "cnss_binder_failures"), 0),
                "sample_lines": nested(surface, ("live", "cnss_binder_failure_lines"), []),
            },
            "next_step": "repair or prove PeripheralManager surface before scan/connect",
        },
        {
            "name": "live-peripheral-manager-literal-not-confirmed",
            "status": "finding" if live_terms.get("vendor.qcom.PeripheralManager", 0) == 0 else "review",
            "detail": {"term_counts": live_terms},
            "next_step": "V685 should prove service registration/lookup target live, not infer it solely from static strings",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v684-cnss-daemon-vndbinder-target-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V684 host-only classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v684-cnss-daemon-vndbinder-target-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh missing input evidence before planning live repair",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    required = {
        "cnss-daemon-imports-peripheral-client",
        "peripheral-client-uses-vndbinder-service-manager",
        "qmiservices-not-the-static-binder-target",
        "live-cnss-daemon-mapped-peripheral-client",
        "live-binder-failure-precedes-missing-wlfw",
        "live-peripheral-manager-literal-not-confirmed",
    }
    if required <= findings:
        return (
            "v684-cnss-daemon-peripheral-manager-target-candidate",
            True,
            "static ELF evidence points cnss-daemon through libperipheral_client to vendor.qcom.PeripheralManager over vndbinder, and V682 live maps that client before the CNSS binder -22 / no-WLFW gap; the exact live service availability still needs proof.",
            "plan V685 as a narrow vendor.qcom.PeripheralManager availability/start-order proof before another CNSS retry; keep Wi-Fi HAL, scan/connect, DHCP, and external ping blocked",
        )
    return (
        "v684-cnss-daemon-vndbinder-target-review",
        False,
        "static and live evidence did not isolate a single vndbinder target candidate",
        "inspect cnss-daemon/libperipheral_client strings and V682 helper capture manually",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    surface = build_surface(args)
    checks = build_checks(surface)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v684",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v683_manifest": str(repo_path(args.v683_manifest)),
            "v682_manifest": str(repo_path(args.v682_manifest)),
            "v682_live_manifest": str(repo_path(args.v682_live_manifest)),
            "cnss_daemon": str(repo_path(args.cnss_daemon)),
            "libperipheral_client": str(repo_path(args.libperipheral_client)),
            "libqmiservices": str(repo_path(args.libqmiservices)),
        },
        "surface": surface,
        "checks": checks,
        "routing": {
            "primary_next": "vendor.qcom.PeripheralManager live availability/start-order proof",
            "why_not_qmi_payload": "WLFW service 69 is still absent, so WLFW payload probing is premature",
            "why_not_scan_connect": "wlan0 and firmware-ready markers are absent",
            "why_not_direct_qca_write": "current evidence points to missing native Binder continuation before WLFW",
        },
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "mount_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    static_rows: list[list[str]] = []
    for name, values in manifest["surface"]["static"].items():
        static_rows.append([
            name,
            str(values["exists"]),
            str(values["size"]),
            values["sha256"],
            json.dumps(values["terms"], sort_keys=True),
        ])
    live_counts = manifest["surface"]["live"]["counts"]
    live_term_rows = [[key, str(value)] for key, value in manifest["surface"]["live"]["term_counts"].items()]
    return "\n".join([
        "# V684 cnss-daemon vndbinder Target Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Static ELF Surface",
        "",
        markdown_table(["binary", "exists", "size", "sha256", "terms"], static_rows),
        "",
        "## Live Evidence Counts",
        "",
        markdown_table(["marker", "count"], [[key, str(value)] for key, value in live_counts.items()]),
        "",
        "## Live Term Counts",
        "",
        markdown_table(["term", "count"], live_term_rows),
        "",
        "## Routing",
        "",
        markdown_table(["item", "value"], [[key, value] for key, value in manifest["routing"].items()]),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
