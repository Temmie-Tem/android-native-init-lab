#!/usr/bin/env python3
"""V639 host-only sibling SSCTL warning attribution classifier.

This classifier compares V638 all-sibling firmware-backed writes with V619,
V635, and V636 evidence. It does not contact the device, write sysfs, start
daemons, start service-manager, start Wi-Fi HAL, scan/connect/link-up, use
credentials, run DHCP, change routes, reboot, flash, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v639-sibling-warning-attribution-classifier")
DEFAULT_V619_MANIFEST = Path("tmp/wifi/v619-android-order-post-sysmon-observer-run/manifest.json")
DEFAULT_V635_MANIFEST = Path("tmp/wifi/v635-cdsp-proof-20260523-052940/manifest.json")
DEFAULT_V636_MANIFEST = Path("tmp/wifi/v636-cdsp-v598-live-20260523-054728/manifest.json")
DEFAULT_V638_MANIFEST = Path("tmp/wifi/v638-firmware-sibling-live-20260523-060104/manifest.json")
DEFAULT_V638_DMESG = Path("tmp/wifi/v638-firmware-sibling-live-20260523-060104/native/dmesg-after-sibling.txt")
DEFAULT_V638_STATE_DIR = Path("tmp/wifi/v638-firmware-sibling-live-20260523-060104/native")

NODES = ("adsp", "cdsp", "slpi")
LOWER_MARKERS = (
    "sysmon_slpi",
    "sysmon_cdsp",
    "sysmon_adsp",
    "service_notifier_180",
    "service_notifier_74",
    "wlan_pd",
    "qmi_server_connected",
    "wlfw_start",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wlan0",
)
FORBIDDEN_ACTIONS = [
    "device command",
    "sysfs write",
    "DSP boot-node write",
    "boot image build/flash/reboot",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
]

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TS_RE = re.compile(r"^\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
NODE_PATTERNS = {
    "adsp": re.compile(r"subsys-pil.*lpass: adsp:|apr_adsp_up|for adsp\b", re.I),
    "cdsp": re.compile(r"subsys-pil.*turing: cdsp:|for cdsp\b|cdsp request manager|fastcvpd", re.I),
    "slpi": re.compile(r"subsys-pil.*ssc: slpi:|for slpi\b", re.I),
}
NODE_START_PATTERNS = {
    "adsp": re.compile(r"subsys-pil.*lpass: adsp: loading", re.I),
    "cdsp": re.compile(r"subsys-pil.*turing: cdsp: loading", re.I),
    "slpi": re.compile(r"subsys-pil.*ssc: slpi: loading", re.I),
}
NODE_READY_PATTERNS = {
    "adsp": re.compile(r"lpass: adsp: Power/Clock ready", re.I),
    "cdsp": re.compile(r"turing: cdsp: Power/Clock ready", re.I),
    "slpi": re.compile(r"ssc: slpi: Power/Clock ready", re.I),
}
PM_QOS_RE = re.compile(r"pm_qos_add_request\(\) called for already added request", re.I)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v619-manifest", type=Path, default=DEFAULT_V619_MANIFEST)
    parser.add_argument("--v635-manifest", type=Path, default=DEFAULT_V635_MANIFEST)
    parser.add_argument("--v636-manifest", type=Path, default=DEFAULT_V636_MANIFEST)
    parser.add_argument("--v638-manifest", type=Path, default=DEFAULT_V638_MANIFEST)
    parser.add_argument("--v638-dmesg", type=Path, default=DEFAULT_V638_DMESG)
    parser.add_argument("--v638-state-dir", type=Path, default=DEFAULT_V638_STATE_DIR)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def clean_line(raw_line: str) -> str:
    return ANSI_RE.sub("", raw_line).strip()


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


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def bool_text(value: bool) -> str:
    return "yes" if value else "no"


def line_time(line: str) -> float | None:
    match = TS_RE.match(clean_line(line))
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def marker_delta(manifest: dict[str, Any]) -> dict[str, Any]:
    return nested(manifest, ("proof", "marker_delta"), {}) or nested(manifest, ("live", "cdsp_marker_delta"), {}) or {}


def v636_post_markers(manifest: dict[str, Any]) -> dict[str, Any]:
    return nested(manifest, ("live", "post_cdsp_markers"), {}) or {}


def parse_states(state_dir: Path) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for label in ("initial-sibling-state", "mounted-initial-sibling-state", "state-after-adsp", "state-after-cdsp", "state-after-slpi"):
        lines = [line.strip() for line in read_text(repo_path(state_dir) / f"{label}.txt").splitlines() if line.strip()]
        states: dict[str, str] = {}
        index = 0
        while index + 2 < len(lines):
            if lines[index].startswith("/sys/"):
                name = lines[index + 1]
                state = lines[index + 2]
                states[name] = state
                index += 4
            else:
                index += 1
        result[label] = states
    return result


def parse_v638_warning_timeline(text: str) -> dict[str, Any]:
    node_counts = {node: 0 for node in NODES}
    node_start: dict[str, float | None] = {node: None for node in NODES}
    node_ready: dict[str, float | None] = {node: None for node in NODES}
    warning_rows: list[list[str]] = []
    last_node = "unknown"
    last_node_time: float | None = None

    for raw_line in text.splitlines():
        line = clean_line(raw_line)
        timestamp = line_time(line)
        for node in NODES:
            if NODE_START_PATTERNS[node].search(line):
                last_node = node
                last_node_time = timestamp
                node_start[node] = node_start[node] if node_start[node] is not None else timestamp
            elif NODE_READY_PATTERNS[node].search(line):
                last_node = node
                last_node_time = timestamp
                node_ready[node] = node_ready[node] if node_ready[node] is not None else timestamp
            elif NODE_PATTERNS[node].search(line):
                last_node = node
                last_node_time = timestamp
        if PM_QOS_RE.search(line):
            node = last_node
            node_counts[node] = node_counts.get(node, 0) + 1
            if len(warning_rows) < 20:
                delta = ""
                if timestamp is not None and last_node_time is not None:
                    delta = f"{(timestamp - last_node_time) * 1000.0:.3f}"
                warning_rows.append([
                    "" if timestamp is None else f"{timestamp:.6f}",
                    node,
                    delta,
                    line,
                ])

    node_rows = []
    for node in NODES:
        start = node_start.get(node)
        ready = node_ready.get(node)
        node_rows.append([
            node,
            "" if start is None else f"{start:.6f}",
            "" if ready is None else f"{ready:.6f}",
            str(node_counts.get(node, 0)),
        ])
    return {
        "node_warning_counts": node_counts,
        "node_rows": node_rows,
        "warning_rows": warning_rows,
        "total_pm_qos_warnings": sum(node_counts.values()),
    }


def node_results_summary(v638: dict[str, Any]) -> dict[str, dict[str, bool]]:
    results = nested(v638, ("proof", "node_results"), {}) or {}
    return {
        node: {
            "returned": bool((results.get(node) or {}).get("returned")),
            "timed_out": bool((results.get(node) or {}).get("timed_out")),
            "child_write_rc0": bool((results.get(node) or {}).get("child_write_rc0")),
        }
        for node in NODES
    }


def build_case_rows(manifest: dict[str, Any]) -> list[list[str]]:
    v619 = manifest["v619"]
    v635 = manifest["v635"]
    v636 = manifest["v636"]
    v638 = manifest["v638"]
    return [
        [
            "V619 all-sibling replay",
            str(v619.get("decision")),
            f"kernel_warning={nested(v619, ('live', 'markers', 'counts'), {}).get('kernel_warning', 0)}; "
            f"sibling_sysmon={nested(v619, ('live', 'dsp_counts'), {})}",
            "warning-positive all-sibling precedent",
        ],
        [
            "V635 CDSP-only firmware proof",
            str(v635.get("decision")),
            f"cdsp_returned={nested(v635, ('proof', 'cdsp_returned'), False)}; "
            f"pm_qos={marker_delta(v635).get('pm_qos_warning', 0)}",
            "warning-free single-node contrast",
        ],
        [
            "V636 CDSP+V598 composite",
            str(v636.get("decision")),
            f"service180={v636_post_markers(v636).get('service_notifier_180', 0)}; "
            f"service74={v636_post_markers(v636).get('service_notifier_74', 0)}; "
            f"kernel_warning={v636_post_markers(v636).get('kernel_warning', 0)}",
            "warning-free lower-path contrast",
        ],
        [
            "V638 firmware all-sibling",
            str(v638.get("decision")),
            f"pm_qos={marker_delta(v638).get('pm_qos_warning', 0)}; "
            f"kernel_warning={marker_delta(v638).get('kernel_warning', 0)}; "
            f"lower_advanced={manifest['checks']['v638_lower_markers_advanced']}",
            "warning-positive no-progress result",
        ],
    ]


def build_checks(v619: dict[str, Any], v635: dict[str, Any], v636: dict[str, Any], v638: dict[str, Any], timeline: dict[str, Any]) -> dict[str, Any]:
    v638_delta = marker_delta(v638)
    v635_delta = marker_delta(v635)
    v636_post = v636_post_markers(v636)
    v619_counts = nested(v619, ("live", "markers", "counts"), {}) or {}
    node_results = node_results_summary(v638)
    return {
        "v638_all_nodes_returned": all(row["returned"] and row["child_write_rc0"] and not row["timed_out"] for row in node_results.values()),
        "v638_pm_qos_warning": int_value(v638_delta.get("pm_qos_warning")) > 0,
        "v638_kernel_warning": int_value(v638_delta.get("kernel_warning")) > 0,
        "v638_lower_markers_advanced": any(int_value(v638_delta.get(marker)) > 0 for marker in LOWER_MARKERS),
        "v638_warning_tied_to_multiple_nodes": sum(1 for node in NODES if int_value(timeline["node_warning_counts"].get(node)) > 0) >= 2,
        "v619_all_sibling_warning_precedent": int_value(v619_counts.get("kernel_warning")) > 0,
        "v635_cdsp_only_warning_free": int_value(v635_delta.get("pm_qos_warning")) == 0,
        "v636_cdsp_v598_warning_free": int_value(v636_post.get("kernel_warning")) == 0,
        "v636_service180_only": int_value(v636_post.get("service_notifier_180")) > 0 and int_value(v636_post.get("service_notifier_74")) == 0,
        "single_node_culprit_proven": False,
    }


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    checks = manifest["checks"]
    if (
        checks["v638_all_nodes_returned"]
        and checks["v638_pm_qos_warning"]
        and checks["v638_kernel_warning"]
        and not checks["v638_lower_markers_advanced"]
        and checks["v638_warning_tied_to_multiple_nodes"]
        and checks["v619_all_sibling_warning_precedent"]
        and checks["v635_cdsp_only_warning_free"]
        and checks["v636_cdsp_v598_warning_free"]
    ):
        return (
            "v639-all-sibling-warning-attributed-single-node-unresolved",
            True,
            (
                "V638 warnings are temporally tied to the late all-sibling ADSP/CDSP/SLPI boot sequence, "
                "while CDSP-only and CDSP+V598 stayed warning-free. A single culprit is not proven."
            ),
            "avoid direct all-sibling write retries; next classify a non-write or Android-sequenced lower publisher path",
        )
    if checks["v635_cdsp_only_warning_free"] and checks["v636_cdsp_v598_warning_free"]:
        return (
            "v639-cdsp-only-warning-free-contrast-classified",
            True,
            "CDSP-only paths are warning-free; all-sibling attribution is incomplete",
            "collect or compare per-node dmesg checkpoints before another live node write",
        )
    return (
        "v639-warning-evidence-gap",
        False,
        f"insufficient evidence: {checks}",
        "refresh host-only evidence references before choosing a live gate",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v619 = load_json(args.v619_manifest)
    v635 = load_json(args.v635_manifest)
    v636 = load_json(args.v636_manifest)
    v638 = load_json(args.v638_manifest)
    timeline = parse_v638_warning_timeline(read_text(args.v638_dmesg))
    states = parse_states(args.v638_state_dir)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "v619_manifest": str(repo_path(args.v619_manifest)),
            "v635_manifest": str(repo_path(args.v635_manifest)),
            "v636_manifest": str(repo_path(args.v636_manifest)),
            "v638_manifest": str(repo_path(args.v638_manifest)),
            "v638_dmesg": str(repo_path(args.v638_dmesg)),
            "v638_state_dir": str(repo_path(args.v638_state_dir)),
        },
        "v619": v619,
        "v635": v635,
        "v636": v636,
        "v638": v638,
        "v638_node_results": node_results_summary(v638),
        "v638_warning_timeline": timeline,
        "v638_states": states,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "sysfs_writes_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }
    manifest["checks"] = build_checks(v619, v635, v636, v638, timeline)
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v639-sibling-warning-attribution-plan-ready",
            True,
            "plan-only; run will classify existing V619/V635/V636/V638 evidence without device contact",
            "run V639 host-only classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(manifest)
    manifest.update({
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
    })
    manifest["case_rows"] = build_case_rows(manifest)
    manifest["inferences"] = {
        "late_all_sibling_direct_write_retry_blocked": True,
        "cdsp_only_path_not_the_warning_root_by_itself": manifest["checks"]["v635_cdsp_only_warning_free"],
        "service180_warning_free_path_remains_useful": manifest["checks"]["v636_service180_only"],
        "single_node_culprit_unproven": not manifest["checks"]["single_node_culprit_proven"],
        "wifi_bringup_still_blocked": True,
    }
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V639 Sibling Warning Attribution Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- sysfs_writes_executed: `{manifest['sysfs_writes_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Evidence Cases",
        "",
        markdown_table(["case", "decision", "evidence", "classification"], manifest["case_rows"]),
        "",
        "## V638 Warning Attribution",
        "",
        markdown_table(["node", "first_start_ts", "first_ready_ts", "pm_qos_warning_count"], manifest["v638_warning_timeline"]["node_rows"]),
        "",
        "## V638 Warning Samples",
        "",
        markdown_table(["timestamp", "nearest_node", "delta_ms", "line"], manifest["v638_warning_timeline"]["warning_rows"]),
        "",
        "## V638 State Snapshots",
        "",
        markdown_table(
            ["snapshot", "adsp", "cdsp", "slpi"],
            [
                [label, states.get("adsp", ""), states.get("cdsp", ""), states.get("slpi", "")]
                for label, states in manifest["v638_states"].items()
            ],
        ),
        "",
        "## Checks",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in manifest["checks"].items()]),
        "",
        "## Inferences",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in manifest["inferences"].items()]),
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
    print(f"sysfs_writes_executed: {manifest['sysfs_writes_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
