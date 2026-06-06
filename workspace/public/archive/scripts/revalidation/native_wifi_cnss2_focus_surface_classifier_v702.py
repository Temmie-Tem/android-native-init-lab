#!/usr/bin/env python3
"""V702 host-only cnss2/icnss/QCA focus-surface classifier.

This classifier consumes the read-only focus capture already emitted by V700
helper v119 during the provider-first CNSS retry window. It does not contact
the device, start daemons, mount filesystems, scan/connect, use credentials,
run DHCP, change routes, or ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v702-cnss2-focus-surface-classifier")
DEFAULT_V700_MANIFEST = Path("tmp/wifi/v700-provider-first-cnss-orchestrated-run/manifest.json")
DEFAULT_V701_MANIFEST = Path("tmp/wifi/v701-pre-wlfw-trigger-classifier/manifest.json")
DEFAULT_V700_HELPER = Path(
    "tmp/wifi/v700-provider-first-cnss-orchestrated-run/"
    "arm-v700-v119-provider-first-cnss/live/native/companion-start-only-with-holder.txt"
)
DEFAULT_V700_DMESG = Path(
    "tmp/wifi/v700-provider-first-cnss-orchestrated-run/"
    "arm-v700-v119-provider-first-cnss/live/native/dmesg-delta.txt"
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

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
KEY_VALUE_RE = re.compile(r"^(?P<key>[^=\s][^=]*?)=(?P<value>.*)$")
DIR_BEGIN_RE = re.compile(r"^A90_EXECNS_DIR_(?P<label>\S+)_BEGIN path=(?P<path>\S+) ")
DIR_END_RE = re.compile(r"^A90_EXECNS_DIR_(?P<label>\S+)_END count=(?P<count>\d+) shown=(?P<shown>\d+) truncated=(?P<truncated>\d+)")
PATH_BEGIN_RE = re.compile(r"^A90_EXECNS_PATH_(?P<label>\S+)_BEGIN path=(?P<path>\S+) ")
PATH_END_RE = re.compile(r"^A90_EXECNS_PATH_(?P<label>\S+)_END bytes=(?P<bytes>\d+) truncated=(?P<truncated>\d+)")

FOCUS_PHASES = ("service74_open", "window")
FOCUS_PREFIX = "wifi_companion_start.cnss2_focus_"

FOCUS_DIR_LABELS = (
    "wifi_cnss2_focus_icnss_driver",
    "wifi_cnss2_focus_icnss_device",
    "wifi_cnss2_focus_qca6390_device",
    "wifi_cnss2_focus_net_class",
    "wifi_cnss2_focus_wlan0",
    "wifi_cnss2_focus_debug_icnss",
)
FOCUS_PATH_LABELS = (
    "wifi_cnss2_focus_icnss_uevent",
    "wifi_cnss2_focus_icnss_modalias",
    "wifi_cnss2_focus_icnss_power_control",
    "wifi_cnss2_focus_icnss_power_runtime_status",
    "wifi_cnss2_focus_qca6390_uevent",
    "wifi_cnss2_focus_qca6390_modalias",
    "wifi_cnss2_focus_qca6390_power_control",
    "wifi_cnss2_focus_qca6390_power_runtime_status",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v700-manifest", type=Path, default=DEFAULT_V700_MANIFEST)
    parser.add_argument("--v701-manifest", type=Path, default=DEFAULT_V701_MANIFEST)
    parser.add_argument("--v700-helper", type=Path, default=DEFAULT_V700_HELPER)
    parser.add_argument("--v700-dmesg", type=Path, default=DEFAULT_V700_DMESG)
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


def strip_line(line: str) -> str:
    return ANSI_RE.sub("", line).strip()


def parse_key_values(text: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for raw_line in text.splitlines():
        line = strip_line(raw_line)
        match = KEY_VALUE_RE.match(line)
        if match:
            values.setdefault(match.group("key"), []).append(match.group("value"))
    return values


def latest_value(values: dict[str, list[str]], key: str) -> str:
    rows = values.get(key) or []
    return rows[-1] if rows else ""


def parse_blocks(text: str) -> dict[str, Any]:
    dirs: dict[str, list[dict[str, Any]]] = {}
    paths: dict[str, list[dict[str, Any]]] = {}
    current_dir: dict[str, Any] | None = None
    current_path: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        line = strip_line(raw_line)
        dir_begin = DIR_BEGIN_RE.match(line)
        if dir_begin:
            current_dir = {
                "label": dir_begin.group("label"),
                "path": dir_begin.group("path"),
                "entries": [],
                "open_error": "",
            }
            continue
        if current_dir is not None:
            dir_end = DIR_END_RE.match(line)
            if line.startswith("entry."):
                _, _, value = line.partition("=")
                current_dir["entries"].append(value)
                continue
            if line.startswith("open-error="):
                current_dir["open_error"] = line.split("=", 1)[1]
                continue
            if dir_end and dir_end.group("label") == current_dir["label"]:
                current_dir["count"] = int(dir_end.group("count"))
                current_dir["shown"] = int(dir_end.group("shown"))
                current_dir["truncated"] = int(dir_end.group("truncated"))
                dirs.setdefault(current_dir["label"], []).append(current_dir)
                current_dir = None
                continue

        path_begin = PATH_BEGIN_RE.match(line)
        if path_begin:
            current_path = {
                "label": path_begin.group("label"),
                "path": path_begin.group("path"),
                "content": [],
                "open_error": "",
            }
            continue
        if current_path is not None:
            path_end = PATH_END_RE.match(line)
            if line.startswith("open-error="):
                current_path["open_error"] = line.split("=", 1)[1]
                continue
            if path_end and path_end.group("label") == current_path["label"]:
                current_path["bytes"] = int(path_end.group("bytes"))
                current_path["truncated"] = int(path_end.group("truncated"))
                paths.setdefault(current_path["label"], []).append(current_path)
                current_path = None
                continue
            current_path["content"].append(line)
    return {"dirs": dirs, "paths": paths}


def phase_surface(values: dict[str, list[str]], phase: str) -> dict[str, Any]:
    prefix = f"{FOCUS_PREFIX}{phase}."
    return {
        "begin": latest_value(values, f"{prefix}begin"),
        "end": latest_value(values, f"{prefix}end"),
        "icnss_driver_captured": latest_value(values, f"{prefix}icnss_driver_captured"),
        "icnss_device_captured": latest_value(values, f"{prefix}icnss_device_captured"),
        "qca6390_device_captured": latest_value(values, f"{prefix}qca6390_device_captured"),
        "net_class_captured": latest_value(values, f"{prefix}net_class_captured"),
        "wlan0_captured": latest_value(values, f"{prefix}wlan0_captured"),
        "debug_icnss_captured": latest_value(values, f"{prefix}debug_icnss_captured"),
        "value_captures": intish(latest_value(values, f"{prefix}value_captures")),
    }


def last_dir(blocks: dict[str, Any], label: str) -> dict[str, Any]:
    rows = ((blocks.get("dirs") or {}).get(label) or [])
    return rows[-1] if rows else {"entries": [], "count": 0, "shown": 0, "truncated": 0, "open_error": "missing"}


def path_values(blocks: dict[str, Any], label: str) -> list[str]:
    values = []
    for row in ((blocks.get("paths") or {}).get(label) or []):
        if row.get("open_error"):
            values.append("open-error=" + str(row.get("open_error")))
        else:
            values.append("\n".join(row.get("content") or []).strip())
    return values


def latest_path_value(blocks: dict[str, Any], label: str) -> str:
    values = path_values(blocks, label)
    return values[-1] if values else ""


def arm_v700(manifest: dict[str, Any]) -> dict[str, Any]:
    arm = manifest.get("arm_v700")
    return arm if isinstance(arm, dict) else {}


def build_surface(args: argparse.Namespace) -> dict[str, Any]:
    v700_manifest = load_json(args.v700_manifest)
    v701_manifest = load_json(args.v701_manifest)
    helper_text = read_text(args.v700_helper)
    dmesg_text = read_text(args.v700_dmesg)
    values = parse_key_values(helper_text)
    blocks = parse_blocks(helper_text)
    arm = arm_v700(v700_manifest)
    counts = arm.get("counts") or {}
    markers = arm.get("markers") or {}

    dirs = {label: last_dir(blocks, label) for label in FOCUS_DIR_LABELS}
    paths = {label: latest_path_value(blocks, label) for label in FOCUS_PATH_LABELS}
    qca_entries = dirs["wifi_cnss2_focus_qca6390_device"].get("entries") or []
    icnss_device_entries = dirs["wifi_cnss2_focus_icnss_device"].get("entries") or []
    icnss_driver_entries = dirs["wifi_cnss2_focus_icnss_driver"].get("entries") or []
    net_entries = dirs["wifi_cnss2_focus_net_class"].get("entries") or []
    return {
        "v700": {
            "decision": v700_manifest.get("decision", ""),
            "pass": boolish(v700_manifest.get("pass")),
            "counts": counts,
            "markers": markers,
            "query_exact_match": boolish(arm.get("query_exact_match")),
            "cnss_retry_started": boolish(arm.get("cnss_retry_started")),
            "initial_cnss_suppressed": boolish(arm.get("initial_cnss_suppressed")),
        },
        "v701": {
            "decision": v701_manifest.get("decision", ""),
            "pass": boolish(v701_manifest.get("pass")),
        },
        "focus": {
            phase: phase_surface(values, phase)
            for phase in FOCUS_PHASES
        },
        "dirs": {
            label: {
                "path": dirs[label].get("path", ""),
                "count": dirs[label].get("count", 0),
                "shown": dirs[label].get("shown", 0),
                "truncated": dirs[label].get("truncated", 0),
                "open_error": dirs[label].get("open_error", ""),
                "entries": dirs[label].get("entries", []),
            }
            for label in FOCUS_DIR_LABELS
        },
        "paths": paths,
        "classification": {
            "icnss_driver_bound": "18800000.qcom,icnss" in icnss_driver_entries and "driver" in icnss_device_entries,
            "qca6390_device_visible": intish(dirs["wifi_cnss2_focus_qca6390_device"].get("count")) > 0,
            "qca6390_driver_symlink_visible": "driver" in qca_entries,
            "net_class_has_wlan0": "wlan0" in net_entries,
            "wlan0_open_error": dirs["wifi_cnss2_focus_wlan0"].get("open_error", ""),
            "debug_icnss_open_error": dirs["wifi_cnss2_focus_debug_icnss"].get("open_error", ""),
            "icnss_power_runtime_status": paths["wifi_cnss2_focus_icnss_power_runtime_status"],
            "qca6390_power_runtime_status": paths["wifi_cnss2_focus_qca6390_power_runtime_status"],
            "icnss_power_control": paths["wifi_cnss2_focus_icnss_power_control"],
            "qca6390_power_control": paths["wifi_cnss2_focus_qca6390_power_control"],
            "wlfw_marker": intish(markers.get("wlfw")),
            "bdf_marker": intish(markers.get("bdf")),
            "wlan0_marker": intish(markers.get("wlan0")),
            "dmesg_has_icnss_qmi": "icnss_qmi: QMI Server Connected" in dmesg_text,
            "dmesg_has_wlfw": "wlfw" in dmesg_text.lower() or "WLFW" in dmesg_text,
        },
    }


def int_count(surface: dict[str, Any], key: str) -> int:
    return intish((surface.get("v700") or {}).get("counts", {}).get(key))


def focus_ready(surface: dict[str, Any]) -> bool:
    for phase in FOCUS_PHASES:
        item = (surface.get("focus") or {}).get(phase) or {}
        if (
            item.get("begin") != "1"
            or item.get("end") != "1"
            or item.get("icnss_driver_captured") != "1"
            or item.get("icnss_device_captured") != "1"
            or item.get("qca6390_device_captured") != "1"
            or item.get("net_class_captured") != "1"
        ):
            return False
    return True


def build_checks(surface: dict[str, Any]) -> list[dict[str, Any]]:
    classification = surface["classification"]
    return [
        {
            "name": "v700-v701-input-ready",
            "status": "pass" if (
                surface["v700"]["pass"]
                and surface["v700"]["query_exact_match"]
                and surface["v700"]["cnss_retry_started"]
                and surface["v701"]["decision"] == "v701-pre-wlfw-kernel-progression-gap-classified"
            ) else "blocked",
            "detail": {
                "v700_decision": surface["v700"]["decision"],
                "v701_decision": surface["v701"]["decision"],
                "query_exact_match": surface["v700"]["query_exact_match"],
                "cnss_retry_started": surface["v700"]["cnss_retry_started"],
            },
            "next_step": "refresh V700/V701 evidence before classifying focus surface",
        },
        {
            "name": "focus-capture-ready",
            "status": "pass" if focus_ready(surface) else "blocked",
            "detail": surface["focus"],
            "next_step": "rerun provider-first helper only if focus capture is missing",
        },
        {
            "name": "icnss-platform-driver-bound",
            "status": "finding" if classification["icnss_driver_bound"] else "review",
            "detail": {
                "icnss_driver_entries": surface["dirs"]["wifi_cnss2_focus_icnss_driver"]["entries"],
                "icnss_device_entries": surface["dirs"]["wifi_cnss2_focus_icnss_device"]["entries"],
                "icnss_power_runtime_status": classification["icnss_power_runtime_status"],
            },
            "next_step": "do not target icnss bind unless later evidence shows it detached",
        },
        {
            "name": "qca6390-platform-node-visible-without-driver-link",
            "status": "finding" if (
                classification["qca6390_device_visible"]
                and not classification["qca6390_driver_symlink_visible"]
            ) else "review",
            "detail": {
                "qca_entries": surface["dirs"]["wifi_cnss2_focus_qca6390_device"]["entries"],
                "qca_power_runtime_status": classification["qca6390_power_runtime_status"],
                "qca_power_control": classification["qca6390_power_control"],
            },
            "next_step": "compare Android/native qca6390 binding surface before any bind/unbind write is considered",
        },
        {
            "name": "wlan0-and-debug-icnss-absent",
            "status": "finding" if (
                not classification["net_class_has_wlan0"]
                and classification["wlan0_open_error"] == "No such file or directory"
                and classification["debug_icnss_open_error"] == "No such file or directory"
            ) else "review",
            "detail": {
                "net_class_entries": surface["dirs"]["wifi_cnss2_focus_net_class"]["entries"],
                "wlan0_open_error": classification["wlan0_open_error"],
                "debug_icnss_open_error": classification["debug_icnss_open_error"],
            },
            "next_step": "keep scan/connect blocked; debugfs absence means rely on sysfs/dmesg observability",
        },
        {
            "name": "wlfw-bdf-progression-still-zero",
            "status": "finding" if (
                int_count(surface, "wlfw_start") == 0
                and int_count(surface, "bdf_bdwlan") == 0
                and int_count(surface, "wlan0") == 0
                and not classification["dmesg_has_icnss_qmi"]
                and not classification["dmesg_has_wlfw"]
            ) else "review",
            "detail": {
                "wlfw_start": int_count(surface, "wlfw_start"),
                "bdf_bdwlan": int_count(surface, "bdf_bdwlan"),
                "wlan0": int_count(surface, "wlan0"),
                "dmesg_has_icnss_qmi": classification["dmesg_has_icnss_qmi"],
                "dmesg_has_wlfw": classification["dmesg_has_wlfw"],
            },
            "next_step": "classify qca6390 platform binding against Android reference before Wi-Fi HAL or scan/connect",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v702-cnss2-focus-surface-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V702 host-only classifier over V700 focus capture",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v702-cnss2-focus-surface-classifier-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh missing focus evidence before another live unit",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    required = {
        "icnss-platform-driver-bound",
        "qca6390-platform-node-visible-without-driver-link",
        "wlan0-and-debug-icnss-absent",
        "wlfw-bdf-progression-still-zero",
    }
    if required <= findings:
        return (
            "v702-qca6390-platform-binding-gap-classified",
            True,
            "V700 focus capture proves icnss is bound and qca6390 platform node is visible, but qca6390 has no driver link, runtime status is unsupported, debug icnss and wlan0 are absent, and WLFW/BDF markers stay zero.",
            "plan V703 as Android-vs-native qca6390/icnss binding reference comparison; do not write bind/unbind, start Wi-Fi HAL, scan/connect, DHCP, credentials, or external ping yet",
        )
    return (
        "v702-cnss2-focus-surface-manual-review",
        False,
        "focus surface did not match a known cnss2/icnss/QCA gap pattern",
        "inspect V700 helper transcript manually",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    surface = build_surface(args)
    checks = [] if args.command == "plan" else build_checks(surface)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v702",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v700_manifest": str(repo_path(args.v700_manifest)),
            "v701_manifest": str(repo_path(args.v701_manifest)),
            "v700_helper": str(repo_path(args.v700_helper)),
            "v700_dmesg": str(repo_path(args.v700_dmesg)),
        },
        "surface": surface,
        "checks": checks,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    surface = manifest["surface"]
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    focus_rows: list[list[str]] = []
    for phase, values in surface["focus"].items():
        for key, value in sorted(values.items()):
            focus_rows.append([phase, key, str(value)])
    dir_rows = [
        [label, str(values["count"]), ",".join(values["entries"]), values["open_error"]]
        for label, values in surface["dirs"].items()
    ]
    path_rows = [
        [label, value.replace("\n", "\\n")[:240]]
        for label, value in surface["paths"].items()
    ]
    class_rows = [[key, str(value)] for key, value in sorted(surface["classification"].items())]
    return "\n".join([
        "# V702 cnss2 Focus Surface Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows) if check_rows else "- plan only",
        "",
        "## Focus Phases",
        "",
        markdown_table(["phase", "key", "value"], focus_rows),
        "",
        "## Directory Blocks",
        "",
        markdown_table(["label", "count", "entries", "open_error"], dir_rows),
        "",
        "## Path Blocks",
        "",
        markdown_table(["label", "value"], path_rows),
        "",
        "## Classification",
        "",
        markdown_table(["key", "value"], class_rows),
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
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
