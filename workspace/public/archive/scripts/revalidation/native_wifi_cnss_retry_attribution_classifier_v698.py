#!/usr/bin/env python3
"""V698 host-only CNSS retry attribution classifier.

This classifier consumes existing V695/V697 evidence only. It separates the
initial pre-provider cnss-daemon Binder failure from the post-provider retry
path. It does not contact the device, start daemons, mount filesystems,
scan/connect, use credentials, run DHCP, change routes, or ping externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v698-cnss-retry-attribution-classifier")
DEFAULT_V695_MANIFEST = Path("tmp/wifi/v695-provider-confirmed-cnss-retry-orchestrated-live/manifest.json")
DEFAULT_V697_MANIFEST = Path("tmp/wifi/v697-cnss-binder-runtime-target-classifier-rerun/manifest.json")
DEFAULT_V695_HELPER = Path(
    "tmp/wifi/v695-provider-confirmed-cnss-retry-orchestrated-live/"
    "arm-v695-v118-provider-confirmed-cnss-retry/live/native/companion-start-only-with-holder.txt"
)
DEFAULT_V695_DMESG = Path(
    "tmp/wifi/v695-provider-confirmed-cnss-retry-orchestrated-live/"
    "arm-v695-v118-provider-confirmed-cnss-retry/live/native/dmesg-delta.txt"
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
TS_RE = re.compile(r"\[\s*(?P<ts>\d+\.\d+)\]")
CNSS_NETLINK_RE = re.compile(r"netlink_create\(694\).*?pid:(?P<pid>\d+)\s+comm:\s*cnss-daemon", re.I)
BINDER_FAIL_RE = re.compile(
    r"binder:\s+(?P<pid>\d+):(?P<tid>\d+)\s+transaction failed\s+"
    r"(?P<return_error>\d+)/(?P<return_param>-?\d+),\s+size\s+"
    r"(?P<data_size>\d+)-(?P<offsets_size>\d+)\s+line\s+(?P<line>\d+)",
    re.I,
)
WLFW_RE = re.compile(r"cnss-daemon wlfw_start: Starting", re.I)
PROVIDER_RE = re.compile(r"\bvendor\.qcom\.PeripheralManager\b")

BR_RETURN_NAMES = {
    0x7205: "BR_DEAD_REPLY",
    0x7211: "BR_FAILED_REPLY",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v695-manifest", type=Path, default=DEFAULT_V695_MANIFEST)
    parser.add_argument("--v697-manifest", type=Path, default=DEFAULT_V697_MANIFEST)
    parser.add_argument("--v695-helper", type=Path, default=DEFAULT_V695_HELPER)
    parser.add_argument("--v695-dmesg", type=Path, default=DEFAULT_V695_DMESG)
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


def nested(mapping: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
    return current


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


def first_value(key_values: dict[str, list[str]], key: str) -> str:
    values = key_values.get(key) or []
    return values[0] if values else ""


def ts_for(line: str) -> float | None:
    match = TS_RE.search(line)
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def bounded_provider_lines(text: str, limit: int = 4) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = strip_line(raw_line)
        if PROVIDER_RE.search(line):
            lines.append(line[:240])
            if len(lines) >= limit:
                break
    return lines


def parse_dmesg(text: str) -> dict[str, Any]:
    netlink_by_pid: dict[str, list[dict[str, Any]]] = {}
    failures: list[dict[str, Any]] = []
    wlfw_lines: list[str] = []
    for raw_line in text.splitlines():
        line = strip_line(raw_line)
        timestamp = ts_for(line)
        netlink_match = CNSS_NETLINK_RE.search(line)
        if netlink_match:
            pid = netlink_match.group("pid")
            netlink_by_pid.setdefault(pid, []).append({"ts": timestamp, "line": line[:260]})
        failure_match = BINDER_FAIL_RE.search(line)
        if failure_match and "cnss-daemon" in line:
            return_error = int(failure_match.group("return_error"))
            return_param = int(failure_match.group("return_param"))
            failures.append({
                "ts": timestamp,
                "pid": failure_match.group("pid"),
                "tid": failure_match.group("tid"),
                "return_error": return_error,
                "return_error_hex": hex(return_error),
                "return_error_name": BR_RETURN_NAMES.get(return_error, "unknown"),
                "return_param": return_param,
                "data_size": int(failure_match.group("data_size")),
                "offsets_size": int(failure_match.group("offsets_size")),
                "line": int(failure_match.group("line")),
                "raw": line[:260],
            })
        if WLFW_RE.search(line):
            wlfw_lines.append(line[:260])
    return {
        "netlink_by_pid": netlink_by_pid,
        "failures": failures,
        "wlfw_count": len(wlfw_lines),
        "wlfw_lines": wlfw_lines[:4],
    }


def build_surface(v695: dict[str, Any], v697: dict[str, Any], helper_text: str, dmesg_text: str) -> dict[str, Any]:
    key_values = parse_key_values(helper_text)
    dmesg = parse_dmesg(dmesg_text)
    initial_pid = first_value(key_values, "wifi_hal_composite_start.child.cnss_daemon.pid")
    retry_pid = first_value(key_values, "wifi_hal_composite_start.child.cnss_daemon_retry.pid")
    order = first_value(key_values, "wifi_companion_start.order")
    provider_lines = bounded_provider_lines(helper_text)
    counts = nested(v695, ("arm_v695", "counts"), {}) or {}
    failures = dmesg["failures"]
    return {
        "v695": {
            "decision": v695.get("decision", ""),
            "pass": boolish(v695.get("pass")),
            "query_exact_match": boolish(nested(v695, ("arm_v695", "query_exact_match"), False)),
            "cnss_retry_started": boolish(nested(v695, ("arm_v695", "cnss_retry_started"), False)),
            "counts": counts,
        },
        "v697": {
            "decision": v697.get("decision", ""),
            "pass": boolish(v697.get("pass")),
        },
        "helper": {
            "order": order,
            "initial_pid": initial_pid,
            "retry_pid": retry_pid,
            "initial_start_order": first_value(key_values, "wifi_companion_start.child.cnss_daemon.start_order"),
            "vndservicemanager_start_order": first_value(key_values, "wifi_companion_start.child.vndservicemanager.start_order"),
            "per_mgr_start_order": first_value(key_values, "wifi_companion_start.child.per_mgr.start_order"),
            "per_proxy_start_order": first_value(key_values, "wifi_companion_start.child.per_proxy.start_order"),
            "retry_start_order": first_value(key_values, "wifi_companion_start.child.cnss_daemon_retry.start_order"),
            "provider_literal_count": len(PROVIDER_RE.findall(helper_text)),
            "provider_lines": provider_lines,
            "query_before_retry_in_order": 0 <= order.find("vndservice_query") < order.find("cnss_daemon_retry") if "vndservice_query" in order and "cnss_daemon_retry" in order else False,
        },
        "dmesg": {
            "failures": failures,
            "failure_count": len(failures),
            "initial_failure_count": sum(1 for item in failures if item["pid"] == initial_pid),
            "retry_failure_count": sum(1 for item in failures if item["pid"] == retry_pid),
            "initial_netlink_count": len(dmesg["netlink_by_pid"].get(initial_pid, [])),
            "retry_netlink_count": len(dmesg["netlink_by_pid"].get(retry_pid, [])),
            "initial_netlink_first": (dmesg["netlink_by_pid"].get(initial_pid, [{}])[0] if dmesg["netlink_by_pid"].get(initial_pid) else {}),
            "retry_netlink_first": (dmesg["netlink_by_pid"].get(retry_pid, [{}])[0] if dmesg["netlink_by_pid"].get(retry_pid) else {}),
            "wlfw_count": dmesg["wlfw_count"],
            "wlfw_lines": dmesg["wlfw_lines"],
        },
    }


def build_checks(surface: dict[str, Any]) -> list[dict[str, Any]]:
    v695 = surface["v695"]
    v697 = surface["v697"]
    helper = surface["helper"]
    dmesg = surface["dmesg"]
    first_failure = dmesg["failures"][0] if dmesg["failures"] else {}
    return [
        {
            "name": "input-evidence-ready",
            "status": "pass" if v695["pass"] and v697["pass"] and helper["initial_pid"] and helper["retry_pid"] else "blocked",
            "detail": {
                "v695_decision": v695["decision"],
                "v697_decision": v697["decision"],
                "initial_pid": helper["initial_pid"],
                "retry_pid": helper["retry_pid"],
            },
            "next_step": "refresh V695/V697 evidence before classifying retry attribution",
        },
        {
            "name": "binder-return-code-decoded",
            "status": "finding" if first_failure.get("return_error_name") == "BR_DEAD_REPLY" and first_failure.get("return_param") == -22 else "review",
            "detail": first_failure,
            "next_step": "treat 29189/-22 as BR_DEAD_REPLY/-EINVAL, not as a service method transaction code",
        },
        {
            "name": "binder-failure-attributed-to-initial-cnss",
            "status": "finding" if dmesg["initial_failure_count"] > 0 and dmesg["retry_failure_count"] == 0 else "review",
            "detail": {
                "initial_pid": helper["initial_pid"],
                "retry_pid": helper["retry_pid"],
                "initial_failure_count": dmesg["initial_failure_count"],
                "retry_failure_count": dmesg["retry_failure_count"],
                "failures": dmesg["failures"],
            },
            "next_step": "avoid treating the pre-provider initial failure as proof that the post-provider retry transaction failed",
        },
        {
            "name": "provider-query-precedes-retry",
            "status": "finding" if v695["query_exact_match"] and helper["provider_literal_count"] >= 1 and helper["query_before_retry_in_order"] else "review",
            "detail": {
                "query_exact_match": v695["query_exact_match"],
                "provider_literal_count": helper["provider_literal_count"],
                "query_before_retry_in_order": helper["query_before_retry_in_order"],
                "provider_lines": helper["provider_lines"],
                "order": helper["order"],
            },
            "next_step": "keep provider-first ordering for the next live gate",
        },
        {
            "name": "post-provider-retry-reaches-netlink-without-binder-fail",
            "status": "finding" if dmesg["retry_netlink_count"] > 0 and dmesg["retry_failure_count"] == 0 and dmesg["wlfw_count"] == 0 else "review",
            "detail": {
                "retry_pid": helper["retry_pid"],
                "retry_netlink_count": dmesg["retry_netlink_count"],
                "retry_netlink_first": dmesg["retry_netlink_first"],
                "retry_failure_count": dmesg["retry_failure_count"],
                "wlfw_count": dmesg["wlfw_count"],
            },
            "next_step": "capture retry stdout/stderr/proc state or run provider-first without initial cnss-daemon",
        },
        {
            "name": "v697-target-refined",
            "status": "finding" if v697["decision"] == "v697-cnss-vndbinder-transaction-framing-targeted" and dmesg["retry_failure_count"] == 0 else "review",
            "detail": {
                "v697_decision": v697["decision"],
                "initial_failure_count": dmesg["initial_failure_count"],
                "retry_failure_count": dmesg["retry_failure_count"],
            },
            "next_step": "split the next gate into initial-suppressed provider-first retry and retry-tail observability",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v698-cnss-retry-attribution-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V698 host-only classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v698-cnss-retry-attribution-classifier-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh missing evidence before live work",
        )
    findings = {check["name"] for check in checks if check["status"] == "finding"}
    required = {
        "binder-return-code-decoded",
        "binder-failure-attributed-to-initial-cnss",
        "provider-query-precedes-retry",
        "post-provider-retry-reaches-netlink-without-binder-fail",
        "v697-target-refined",
    }
    if required <= findings:
        return (
            "v698-post-provider-cnss-retry-silent-after-netlink-classified",
            True,
            "the observed 29189/-22 decodes to BR_DEAD_REPLY/-EINVAL and belongs to the initial pre-provider cnss-daemon pid, while the post-provider retry reaches netlink without a matching Binder failure or WLFW progression",
            "plan V699 as provider-first initial-suppressed cnss-daemon start-only with retry stdout/stderr/proc capture; keep Wi-Fi HAL, scan/connect, DHCP, credentials, routes, and external ping blocked",
        )
    return (
        "v698-cnss-retry-attribution-inconclusive",
        False,
        "evidence did not cleanly separate initial and retry CNSS paths",
        "inspect V695 helper/dmesg manually before another live unit",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v695_manifest = load_json(args.v695_manifest)
    v697_manifest = load_json(args.v697_manifest)
    helper_text = read_text(args.v695_helper)
    dmesg_text = read_text(args.v695_dmesg)
    surface = build_surface(v695_manifest, v697_manifest, helper_text, dmesg_text)
    checks = [] if args.command == "plan" else build_checks(surface)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v698",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v695_manifest": str(repo_path(args.v695_manifest)),
            "v697_manifest": str(repo_path(args.v697_manifest)),
            "v695_helper": str(repo_path(args.v695_helper)),
            "v695_dmesg": str(repo_path(args.v695_dmesg)),
            "binder_uapi_reference": "/usr/include/linux/android/binder.h and Android kernel UAPI",
        },
        "surface": surface,
        "checks": checks,
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
    surface = manifest["surface"]
    helper = surface["helper"]
    dmesg = surface["dmesg"]
    failure_rows = [
        [
            item["pid"],
            item["return_error_name"],
            str(item["return_error"]),
            str(item["return_param"]),
            str(item["data_size"]),
            str(item["offsets_size"]),
            str(item["line"]),
        ]
        for item in dmesg["failures"]
    ]
    return "\n".join([
        "# V698 CNSS Retry Attribution Classifier",
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
        "## Pids And Order",
        "",
        markdown_table(
            ["item", "value"],
            [
                ["initial cnss pid", helper["initial_pid"]],
                ["retry cnss pid", helper["retry_pid"]],
                ["initial start order", helper["initial_start_order"]],
                ["vndservicemanager start order", helper["vndservicemanager_start_order"]],
                ["per_mgr start order", helper["per_mgr_start_order"]],
                ["per_proxy start order", helper["per_proxy_start_order"]],
                ["retry start order", helper["retry_start_order"]],
                ["query before retry", str(helper["query_before_retry_in_order"])],
            ],
        ),
        "",
        "## Binder Failures",
        "",
        markdown_table(["pid", "return", "raw", "param", "data", "offsets", "line"], failure_rows),
        "",
        "## Retry Tail",
        "",
        markdown_table(
            ["signal", "count"],
            [
                ["initial netlink", str(dmesg["initial_netlink_count"])],
                ["retry netlink", str(dmesg["retry_netlink_count"])],
                ["initial binder failures", str(dmesg["initial_failure_count"])],
                ["retry binder failures", str(dmesg["retry_failure_count"])],
                ["wlfw_start", str(dmesg["wlfw_count"])],
            ],
        ),
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
