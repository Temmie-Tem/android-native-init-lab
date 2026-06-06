#!/usr/bin/env python3
"""V624 host-only safe positive regression classifier.

V623 classified `qmiproxy` and `mdm_helper` as blind live targets. V624 focuses
on the only native safe positive lower-publication evidence: V598 reached
service-notifier instance 180 without direct DSP boot-node writes or kernel
warnings. It compares that positive with later negative replays to decide the
next safe gate.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v624-safe-positive-regression-classifier")
DEFAULT_V598 = Path("tmp/wifi/v598-modem-holder-wlfw-readback/manifest.json")
DEFAULT_V606 = Path("tmp/wifi/v606-v102-baseline-wlfw-readback-live/manifest.json")
DEFAULT_V608 = Path("tmp/wifi/v608-helper-v100-20260523-002902/v608-helper-v100-wlfw-live/manifest.json")
DEFAULT_V609 = Path("tmp/wifi/v609-post-sysmon-20260523-004918/v609-observer-live/manifest.json")
DEFAULT_V619 = Path("tmp/wifi/v619-android-order-post-sysmon-observer-run/manifest.json")
DEFAULT_V622 = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_V623 = Path("tmp/wifi/v623-lower-publication-gap-classifier/manifest.json")

FORBIDDEN_ACTIONS = [
    "device command",
    "boot image or partition write",
    "sysfs write",
    "DSP boot-node write",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "QRTR/QMI payload",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v598", type=Path, default=DEFAULT_V598)
    parser.add_argument("--v606", type=Path, default=DEFAULT_V606)
    parser.add_argument("--v608", type=Path, default=DEFAULT_V608)
    parser.add_argument("--v609", type=Path, default=DEFAULT_V609)
    parser.add_argument("--v619", type=Path, default=DEFAULT_V619)
    parser.add_argument("--v622", type=Path, default=DEFAULT_V622)
    parser.add_argument("--v623", type=Path, default=DEFAULT_V623)
    parser.add_argument("command", choices=("run",), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def marker_count(manifest: dict[str, Any], key: str) -> int:
    live = manifest.get("live") or {}
    markers = ((live.get("markers") or {}).get("counts") or {})
    if key in markers:
        return int(markers.get(key) or 0)
    dsp = live.get("dsp_counts") or {}
    return int(dsp.get(key) or 0)


def companion_key(manifest: dict[str, Any], key: str) -> str:
    return str(((manifest.get("live") or {}).get("companion_keys") or {}).get(key, ""))


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def case_summary(name: str, path: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    live = manifest.get("live") or {}
    boot_nodes = live.get("boot_nodes_written")
    boot_node_written = any(bool(value) for value in boot_nodes.values()) if isinstance(boot_nodes, dict) else False
    markers = ((live.get("markers") or {}).get("counts") or {})
    service_notifier = int(markers.get("service_notifier") or 0)
    if service_notifier == 0:
        service_notifier = marker_count(manifest, "service_notifier_180") + marker_count(manifest, "service_notifier_74")
    return {
        "name": name,
        "path": str(repo_path(path)),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "order": companion_key(manifest, "wifi_companion_start.order"),
        "child_started": companion_key(manifest, "wifi_companion_start.child_started"),
        "with_service_manager": companion_key(manifest, "wifi_companion_start.with_service_manager"),
        "with_vnd_service_manager": companion_key(manifest, "wifi_companion_start.with_vnd_service_manager"),
        "qrtr_rx": int(markers.get("qrtr_rx") or 0),
        "qrtr_tx": int(markers.get("qrtr_tx") or 0),
        "sysmon_qmi": int(markers.get("sysmon_qmi") or 0),
        "service_notifier": service_notifier,
        "service_notifier_180": marker_count(manifest, "service_notifier_180"),
        "service_notifier_74": marker_count(manifest, "service_notifier_74"),
        "wlan_pd": int(markers.get("wlan_pd") or 0),
        "qmi_server_connected": int(markers.get("qmi_server_connected") or 0),
        "wlfw": int(markers.get("wlfw") or 0),
        "bdf": int(markers.get("bdf") or 0),
        "wlan_fw_ready": int(markers.get("wlan_fw_ready") or 0),
        "wlan0": int(markers.get("wlan0") or 0),
        "kernel_warning": int(markers.get("kernel_warning") or 0),
        "boot_node_written": boot_node_written,
        "mss_after_companion": live.get("mss_after_companion"),
        "mdm3_after_companion": live.get("mdm3_after_companion"),
        "mounted_hits": live.get("mounted_hits") or {},
        "helper_result": live.get("helper_result"),
    }


def android_summary(v622: dict[str, Any]) -> dict[str, Any]:
    summary = v622.get("android_summary") or {}
    timing = summary.get("timing") or {}
    counts = summary.get("counts") or {}
    return {
        "decision": v622.get("decision"),
        "pass": bool(v622.get("pass")),
        "service_notifier_180_ms": timing.get("service_notifier_180_ms"),
        "service_notifier_74_ms": timing.get("service_notifier_74_ms"),
        "wlan_pd_ms": timing.get("wlan_pd_ms"),
        "mdm_helper_boottime_ms": timing.get("mdm_helper_boottime_ms"),
        "counts": {
            "service_notifier_180": counts.get("service_notifier_180", 0),
            "service_notifier_74": counts.get("service_notifier_74", 0),
            "wlan_pd": counts.get("wlan_pd", 0),
            "qmi_server_connected": counts.get("qmi_server_connected", 0),
            "wlan_fw_ready": counts.get("wlan_fw_ready", 0),
            "wlan0": counts.get("wlan0", 0),
        },
    }


def case_rows(cases: list[dict[str, Any]]) -> list[list[str]]:
    return [
        [
            case["name"],
            str(case["decision"]),
            case["order"],
            str(case["service_notifier"]),
            str(case["wlan_pd"]),
            str(case["kernel_warning"]),
            bool_text(case["boot_node_written"]),
            str(case["mdm3_after_companion"]),
        ]
        for case in cases
    ]


def evidence_rows(manifest: dict[str, Any]) -> list[list[str]]:
    cases = {case["name"]: case for case in manifest["native_cases"]}
    android = manifest["android_v622"]
    return [
        [
            "V598 positive",
            "safe partial native positive",
            (
                f"service_notifier={cases['v598']['service_notifier']}; "
                f"kernel_warning={cases['v598']['kernel_warning']}; "
                f"boot_node_written={bool_text(cases['v598']['boot_node_written'])}; "
                f"order={cases['v598']['order']}"
            ),
            "can seed next safe replay, but not enough for Wi-Fi bring-up",
        ],
        [
            "V606/V608",
            "same baseline no longer reproduces",
            (
                f"v606_notifier={cases['v606']['service_notifier']}; "
                f"v608_notifier={cases['v608']['service_notifier']}; "
                f"warnings={cases['v606']['kernel_warning']}/{cases['v608']['kernel_warning']}"
            ),
            "classify as current-boot/precondition or timing instability",
        ],
        [
            "V609",
            "no-CNSS lower observer insufficient",
            (
                f"order={cases['v609']['order']}; "
                f"service_notifier={cases['v609']['service_notifier']}; "
                f"kernel_warning={cases['v609']['kernel_warning']}"
            ),
            "CNSS timing is not proven causal, but no-CNSS window is weaker",
        ],
        [
            "V619",
            "unsafe DSP boot-node path",
            (
                f"service_notifier={cases['v619']['service_notifier']}; "
                f"kernel_warning={cases['v619']['kernel_warning']}; "
                f"boot_node_written={bool_text(cases['v619']['boot_node_written'])}"
            ),
            "do not repeat ADSP/CDSP/SLPI boot-node writes",
        ],
        [
            "Android V622",
            "full lower target",
            (
                f"service180={android['service_notifier_180_ms']}ms; "
                f"service74={android['service_notifier_74_ms']}ms; "
                f"wlan_pd={android['wlan_pd_ms']}ms"
            ),
            "native must advance from partial 180 to stable 180/74 + WLAN-PD",
        ],
    ]


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    cases = {case["name"]: case for case in manifest["native_cases"]}
    v623_ok = manifest["prior"]["v623"]["decision"] == "v623-lower-qmi-publication-gap-classified"
    v598_safe_positive = (
        cases["v598"]["service_notifier"] > 0
        and cases["v598"]["kernel_warning"] == 0
        and not cases["v598"]["boot_node_written"]
        and cases["v598"]["wlan_pd"] == 0
    )
    replays_regressed = cases["v606"]["service_notifier"] == 0 and cases["v608"]["service_notifier"] == 0
    no_cnss_weaker = cases["v609"]["service_notifier"] == 0 and "cnss" not in cases["v609"]["order"]
    direct_dsp_unsafe = cases["v619"]["kernel_warning"] > 0 and cases["v619"]["boot_node_written"]
    android_full = manifest["android_v622"]["counts"]["service_notifier_180"] > 0 and manifest["android_v622"]["counts"]["service_notifier_74"] > 0

    if v623_ok and v598_safe_positive and replays_regressed and no_cnss_weaker and direct_dsp_unsafe and android_full:
        return (
            "v624-safe-positive-nondeterministic-precondition-gap",
            True,
            (
                "V598 is the only warning-free native partial service-notifier positive, "
                "but exact helper-version replays lost it; V619's broader DSP path is unsafe. "
                "The next safe gate should replay/observe the V598-class path from a fresh "
                "native boot with stronger pre/post state capture, not add new blind daemons."
            ),
            "V625 should implement a bounded fresh-boot V598-class replay/observer with no DSP boot-node writes, no service-manager, no HAL, no scan/connect, and expanded precondition capture",
        )

    return (
        "v624-safe-positive-evidence-gap",
        False,
        (
            f"v623_ok={v623_ok} v598_safe_positive={v598_safe_positive} "
            f"replays_regressed={replays_regressed} no_cnss_weaker={no_cnss_weaker} "
            f"direct_dsp_unsafe={direct_dsp_unsafe} android_full={android_full}"
        ),
        "refresh existing evidence before selecting a live gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    paths = {
        "v598": args.v598,
        "v606": args.v606,
        "v608": args.v608,
        "v609": args.v609,
        "v619": args.v619,
    }
    loaded = {name: load_json(path) for name, path in paths.items()}
    v622 = load_json(args.v622)
    v623 = load_json(args.v623)
    cases = [case_summary(name, paths[name], loaded[name]) for name in ("v598", "v606", "v608", "v609", "v619")]
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {name: str(repo_path(path)) for name, path in {**paths, "v622": args.v622, "v623": args.v623}.items()},
        "prior": {"v623": {"decision": v623.get("decision"), "pass": v623.get("pass")}},
        "native_cases": cases,
        "android_v622": android_summary(v622),
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    decision, pass_ok, reason, next_step = classify(manifest)
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "evidence_rows": evidence_rows(manifest),
    })
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    android_counts = manifest["android_v622"]["counts"]
    return "\n".join([
        "# V624 Safe Positive Regression Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Evidence Matrix",
        "",
        markdown_table(["subject", "classification", "evidence", "next"], manifest["evidence_rows"]),
        "",
        "## Native Cases",
        "",
        markdown_table(
            ["case", "decision", "order", "service_notifier", "wlan_pd", "kernel_warning", "boot_node_written", "mdm3"],
            case_rows(manifest["native_cases"]),
        ),
        "",
        "## Android V622 Counts",
        "",
        markdown_table(["marker", "count"], [[key, str(value)] for key, value in android_counts.items()]),
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
