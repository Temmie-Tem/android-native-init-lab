#!/usr/bin/env python3
"""v266 QRTR nameservice runner skeleton.

This runner intentionally cannot transmit QRTR/QMI packets in v266. It provides
the plan, read-only preflight, and no-approval fail-closed command surface that
will be needed before a later transmit-capable helper can be reviewed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v266-qrtr-nameservice-runner-skeleton")
DEFAULT_V264_MANIFEST = Path("tmp/wifi/v264-qrtr-qmi-nameservice-model/manifest.json")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_TOYBOX = "/cache/bin/toybox"

QRTR_PORT_CTRL = 0xFFFFFFFE
QRTR_TYPE_NEW_LOOKUP = 10
QRTR_TYPE_DEL_LOOKUP = 11

READ_ONLY_PREFLIGHT_COMMANDS: tuple[tuple[str, tuple[str, ...], float, bool], ...] = (
    ("version", ("version",), 10.0, True),
    ("status", ("status",), 15.0, True),
    ("netservice-status", ("netservice", "status"), 10.0, True),
    ("pidof-cnss-daemon", ("run", DEFAULT_TOYBOX, "pidof", "cnss-daemon"), 10.0, False),
    ("cat-proc-net-dev", ("cat", "/proc/net/dev"), 10.0, True),
    ("wifiinv-full", ("wifiinv", "full"), 30.0, True),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)
    if not isinstance(payload, dict):
        raise ValueError(f"expected object manifest: {path}")
    return payload


def replace_defaults(command: tuple[str, ...], args: argparse.Namespace) -> list[str]:
    return [args.toybox if item == DEFAULT_TOYBOX else item for item in command]


def strip_text(item: dict[str, Any] | None) -> str:
    if not item or not item.get("text"):
        return ""
    return strip_cmdv1_text(str(item["text"]))


def capture_preflight(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    store.mkdir("captures")
    for name, command, timeout, required in READ_ONLY_PREFLIGHT_COMMANDS:
        actual = replace_defaults(command, args)
        capture = run_capture(args, name, actual, timeout=timeout)
        store.write_text(f"captures/{safe_name(name)}.txt", capture.text if capture.text else capture.error + "\n")
        item = capture_to_manifest(capture)
        item["required"] = required
        records.append(item)
    return records


def by_name(captures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in captures}


def capture_ok(captures: dict[str, dict[str, Any]], name: str) -> bool:
    item = captures.get(name, {})
    return bool(item.get("ok")) and item.get("rc") == 0 and item.get("status") == "ok"


def capture_rc(captures: dict[str, dict[str, Any]], name: str) -> int | None:
    value = captures.get(name, {}).get("rc")
    return value if isinstance(value, int) else None


def has_wlan_link(text: str) -> bool:
    return re.search(r"^\s*wlan\S*:", text, re.MULTILINE | re.IGNORECASE) is not None


def parse_u32_token(name: str, value: str) -> tuple[bool, int | None, str]:
    try:
        parsed = int(value, 0)
    except ValueError:
        return False, None, f"{name} is not an integer: {value!r}"
    if parsed < 0 or parsed > 0xFFFFFFFF:
        return False, parsed, f"{name} outside uint32 range: {parsed}"
    return True, parsed, "ok"


def approval_flags_present(args: argparse.Namespace) -> bool:
    return bool(args.allow_qrtr_ns_transmit and args.assume_yes and args.i_understand_qrtr_packet_transmission)


def build_contract(args: argparse.Namespace, v264: dict[str, Any]) -> dict[str, Any]:
    service_ok, service_value, service_detail = parse_u32_token("service", args.service)
    instance_ok, instance_value, instance_detail = parse_u32_token("instance", args.instance)
    wildcard = service_value == 0 and instance_value == 0 if service_value is not None and instance_value is not None else False
    return {
        "packet_scope": {
            "port": f"0x{QRTR_PORT_CTRL:08x}",
            "packet_type": "QRTR_TYPE_NEW_LOOKUP",
            "packet_type_value": QRTR_TYPE_NEW_LOOKUP,
            "cleanup_packet_type": "QRTR_TYPE_DEL_LOOKUP",
            "cleanup_packet_type_value": QRTR_TYPE_DEL_LOOKUP,
            "qmi_payload_allowed": False,
            "transmit_implemented": False,
        },
        "target": {
            "service_raw": args.service,
            "instance_raw": args.instance,
            "service_ok": service_ok,
            "instance_ok": instance_ok,
            "service_value": service_value,
            "instance_value": instance_value,
            "service_detail": service_detail,
            "instance_detail": instance_detail,
            "wildcard": wildcard,
            "wildcard_allowed": args.allow_wildcard_lookup,
        },
        "approval": {
            "allow_qrtr_ns_transmit": args.allow_qrtr_ns_transmit,
            "assume_yes": args.assume_yes,
            "i_understand_qrtr_packet_transmission": args.i_understand_qrtr_packet_transmission,
            "all_present": approval_flags_present(args),
        },
        "v264": {
            "decision": v264.get("decision"),
            "pass": v264.get("pass"),
        },
    }


def common_checks(v264: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    target = contract["target"]
    return [
        {
            "name": "v264-model-ready",
            "pass": bool(v264.get("pass")) and v264.get("decision") == "qrtr-qmi-userspace-model-ready",
            "severity": "critical",
            "detail": f"decision={v264.get('decision')} pass={v264.get('pass')}",
        },
        {
            "name": "service-instance-valid",
            "pass": bool(target["service_ok"]) and bool(target["instance_ok"]),
            "severity": "critical",
            "detail": json.dumps({
                "service": target["service_raw"],
                "service_detail": target["service_detail"],
                "instance": target["instance_raw"],
                "instance_detail": target["instance_detail"],
            }, sort_keys=True),
        },
        {
            "name": "wildcard-blocked",
            "pass": not bool(target["wildcard"]) or bool(target["wildcard_allowed"]),
            "severity": "critical",
            "detail": json.dumps({
                "wildcard": target["wildcard"],
                "wildcard_allowed": target["wildcard_allowed"],
            }, sort_keys=True),
        },
        {
            "name": "transmit-not-implemented",
            "pass": contract["packet_scope"]["transmit_implemented"] is False,
            "severity": "critical",
            "detail": "v266 runner skeleton cannot send QRTR packets",
        },
    ]


def preflight_checks(args: argparse.Namespace,
                     v264: dict[str, Any],
                     contract: dict[str, Any],
                     captures: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    version_text = strip_text(captures.get("version"))
    netdev_text = strip_text(captures.get("cat-proc-net-dev"))
    required_failed = [name for name, _, _, required in READ_ONLY_PREFLIGHT_COMMANDS if required and not capture_ok(captures, name)]
    checks = common_checks(v264, contract)
    checks.extend([
        {
            "name": "expected-version",
            "pass": args.expect_version in version_text,
            "severity": "critical",
            "detail": args.expect_version,
        },
        {
            "name": "required-readonly-captures",
            "pass": not required_failed,
            "severity": "critical",
            "detail": json.dumps(required_failed),
        },
        {
            "name": "cnss-daemon-absent",
            "pass": capture_rc(captures, "pidof-cnss-daemon") == 1,
            "severity": "critical",
            "detail": "pidof cnss-daemon should return rc=1",
        },
        {
            "name": "no-wlan-link-surface",
            "pass": not has_wlan_link(netdev_text),
            "severity": "critical",
            "detail": "no wlan-like interface in /proc/net/dev",
        },
    ])
    return checks


def classify_plan(checks: list[dict[str, Any]]) -> tuple[bool, str, str]:
    failed = [item["name"] for item in checks if item["severity"] == "critical" and not item["pass"]]
    if failed:
        return False, "qrtr-ns-runner-plan-blocked", "plan prerequisite failed: " + ", ".join(failed)
    return True, "qrtr-ns-runner-plan-ready", "runner skeleton plan is ready and transmission remains unimplemented"


def classify_preflight(checks: list[dict[str, Any]]) -> tuple[bool, str, str]:
    failed = [item["name"] for item in checks if item["severity"] == "critical" and not item["pass"]]
    if failed:
        return False, "qrtr-ns-runner-preflight-blocked", "preflight failed: " + ", ".join(failed)
    return True, "qrtr-ns-runner-preflight-ready", "read-only preflight passed without QRTR/QMI transmission"


def classify_run(checks: list[dict[str, Any]], contract: dict[str, Any]) -> tuple[bool, str, str]:
    failed = [item["name"] for item in checks if item["severity"] == "critical" and not item["pass"]]
    if failed:
        return False, "qrtr-ns-runner-run-blocked", "run prerequisite failed: " + ", ".join(failed)
    approval = contract["approval"]
    if not approval["all_present"]:
        return True, "qrtr-ns-runner-fail-closed", "missing explicit transmit approval flags; no QRTR packet sent"
    return False, "qrtr-ns-runner-transmit-not-implemented", "approval flags are present but v266 has no transmit-capable helper"


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[item["name"], "PASS" if item["pass"] else "FAIL", item["severity"], item["detail"]] for item in manifest["checks"]]
    contract_rows: list[list[str]] = []
    for section, values in manifest["contract"].items():
        if isinstance(values, dict):
            for key, value in values.items():
                contract_rows.append([section, key, json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)])
        else:
            contract_rows.append([section, "-", str(values)])
    return "".join([
        "# v266 QRTR Nameservice Runner Skeleton\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- command: `{manifest['command']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        f"- out_dir: `{manifest['out_dir']}`\n",
        "- QRTR/QMI packet transmission: `not implemented/not executed`\n",
        "- Wi-Fi scan/connect/link-up: `not executed`\n\n",
        "## Checks\n\n",
        markdown_table(["check", "result", "severity", "detail"], checks),
        "\n\n## Contract\n\n",
        markdown_table(["section", "key", "value"], contract_rows),
        "\n\n## Guardrails\n\n",
        "- No QRTR socket is opened by this runner in v266.\n",
        "- No QRTR nameservice packet or QMI request is sent by this runner in v266.\n",
        "- `run` without explicit approval flags succeeds only as a fail-closed proof.\n",
        "- `run` with approval flags still fails because no transmit helper exists in v266.\n",
    ])


def write_manifest(store: EvidenceStore, manifest: dict[str, Any]) -> None:
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))


def command_plan(args: argparse.Namespace) -> int:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    v264 = load_json(repo_path(args.v264_manifest))
    contract = build_contract(args, v264)
    checks = common_checks(v264, contract)
    pass_ok, decision, reason = classify_plan(checks)
    manifest = {
        "created": now_iso(),
        "mode": "qrtr-nameservice-runner-skeleton",
        "command": "plan",
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(out_dir),
        "inputs": {"v264_manifest": str(repo_path(args.v264_manifest))},
        "host_metadata": collect_host_metadata(),
        "contract": contract,
        "checks": checks,
        "captures": [],
        "guardrails": [
            "host-only plan",
            "no bridge command",
            "no QRTR socket open",
            "no QRTR/QMI packet transmission",
        ],
    }
    write_manifest(store, manifest)
    print_result(manifest)
    return 0 if pass_ok else 1


def command_preflight(args: argparse.Namespace) -> int:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    v264 = load_json(repo_path(args.v264_manifest))
    contract = build_contract(args, v264)
    captures_list = capture_preflight(args, store)
    captures = by_name(captures_list)
    checks = preflight_checks(args, v264, contract, captures)
    pass_ok, decision, reason = classify_preflight(checks)
    manifest = {
        "created": now_iso(),
        "mode": "qrtr-nameservice-runner-skeleton",
        "command": "preflight",
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(out_dir),
        "inputs": {"v264_manifest": str(repo_path(args.v264_manifest))},
        "host_metadata": collect_host_metadata(),
        "contract": contract,
        "checks": checks,
        "captures": captures_list,
        "guardrails": [
            "read-only bridge captures only",
            "no QRTR socket open",
            "no QRTR/QMI packet transmission",
            "no Wi-Fi scan/connect/link-up",
        ],
    }
    store.write_json("captures.json", {"captures": captures_list})
    write_manifest(store, manifest)
    print_result(manifest)
    return 0 if pass_ok else 1


def command_run(args: argparse.Namespace) -> int:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    v264 = load_json(repo_path(args.v264_manifest))
    contract = build_contract(args, v264)
    checks = common_checks(v264, contract)
    checks.append({
        "name": "approval-flag-check",
        "pass": True,
        "severity": "info",
        "detail": json.dumps(contract["approval"], sort_keys=True),
    })
    pass_ok, decision, reason = classify_run(checks, contract)
    manifest = {
        "created": now_iso(),
        "mode": "qrtr-nameservice-runner-skeleton",
        "command": "run",
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(out_dir),
        "inputs": {"v264_manifest": str(repo_path(args.v264_manifest))},
        "host_metadata": collect_host_metadata(),
        "contract": contract,
        "checks": checks,
        "captures": [],
        "guardrails": [
            "no QRTR socket open",
            "no QRTR/QMI packet transmission",
            "fail closed unless approval flags are present",
            "approval flags still cannot transmit in v266 because helper is not implemented",
        ],
    }
    write_manifest(store, manifest)
    print_result(manifest)
    return 0 if pass_ok else 1


def print_result(manifest: dict[str, Any]) -> None:
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"out_dir: {manifest['out_dir']}")


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v264-manifest", type=Path, default=DEFAULT_V264_MANIFEST)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--service", default="1")
    parser.add_argument("--instance", default="1")
    parser.add_argument("--max-runtime-sec", type=int, default=5)
    parser.add_argument("--allow-wildcard-lookup", action="store_true")
    parser.add_argument("--allow-qrtr-ns-transmit", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-qrtr-packet-transmission", action="store_true")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_args(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "preflight", "run"):
        sub = subparsers.add_parser(name)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "plan":
        return command_plan(args)
    if args.command == "preflight":
        return command_preflight(args)
    if args.command == "run":
        return command_run(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
