#!/usr/bin/env python3
"""v273 bounded QRTR nameservice readback matrix.

The run mode sends only QRTR nameservice NEW_LOOKUP/DEL_LOOKUP control packet
pairs through the reviewed /cache/bin/a90_qrtr_ns_probe helper. It never sends
QMI payloads and never starts Wi-Fi daemons.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text  # noqa: E402
from a90ctl import run_cmdv1_command  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402


DEFAULT_OUT_DIR = Path("tmp/wifi/v273-qrtr-readback-matrix")
DEFAULT_V272_MANIFEST = Path("tmp/wifi/v272-qmi-service-object-extractor/manifest.json")
DEFAULT_HELPER_DEVICE_BINARY = "/cache/bin/a90_qrtr_ns_probe"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_MATRIX = "wds:1:0,1;dms:2:0,1"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)
    return payload if isinstance(payload, dict) else {}


def parse_key_values(text: str, prefix: str) -> dict[str, str]:
    values: dict[str, str] = {}
    dotted = prefix + "."
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith(dotted) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key[len(dotted):]] = value
    return values


def helper_int(values: dict[str, str], key: str, default: int = 0) -> int:
    try:
        return int(values.get(key, str(default)), 0)
    except ValueError:
        return default


def parse_u32(text: str) -> int:
    value = int(text, 0)
    if value < 0 or value > 0xFFFFFFFF:
        raise ValueError(f"u32 out of range: {text}")
    return value


def parse_matrix(text: str) -> list[dict[str, int | str]]:
    matrix: list[dict[str, int | str]] = []
    seen: set[tuple[int, int]] = set()
    for group in text.split(";"):
        group = group.strip()
        if not group:
            continue
        parts = group.split(":")
        if len(parts) != 3:
            raise ValueError(f"invalid matrix group: {group}")
        name = parts[0].strip()
        service = parse_u32(parts[1].strip())
        instances = [parse_u32(item.strip()) for item in parts[2].split(",") if item.strip()]
        if service == 0:
            raise ValueError("service 0 is global wildcard and is not allowed")
        for instance in instances:
            key = (service, instance)
            if key in seen:
                continue
            seen.add(key)
            matrix.append({"name": name, "service": service, "instance": instance})
    if not matrix:
        raise ValueError("empty matrix")
    return matrix


def capture_preflight(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    commands: tuple[tuple[str, list[str], float, bool], ...] = (
        ("version", ["version"], 10.0, True),
        ("status", ["status"], 15.0, True),
        ("netservice-status", ["netservice", "status"], 10.0, True),
        ("helper-sha256", ["run", "/cache/bin/toybox", "sha256sum", args.helper_device_binary], 10.0, True),
        ("pidof-cnss-daemon", ["run", "/cache/bin/toybox", "pidof", "cnss-daemon"], 10.0, False),
        ("cat-proc-net-dev", ["cat", "/proc/net/dev"], 10.0, True),
    )
    records: list[dict[str, Any]] = []
    store.mkdir("captures")
    for name, command, timeout, required in commands:
        capture = run_capture(args, name, command, timeout=timeout)
        store.write_text(f"captures/{safe_name(name)}.txt", capture.text if capture.text else capture.error + "\n")
        item = capture_to_manifest(capture)
        item["required"] = required
        records.append(item)
    return records


def by_name(captures: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["name"]): item for item in captures}


def capture_ok(captures: dict[str, dict[str, Any]], name: str) -> bool:
    item = captures.get(name, {})
    return item.get("rc") == 0 and item.get("status") == "ok"


def add_check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str, *, severity: str = "critical") -> None:
    checks.append({"name": name, "pass": passed, "severity": severity, "detail": detail})


def build_contract(args: argparse.Namespace, v272: dict[str, Any], matrix: list[dict[str, int | str]]) -> dict[str, Any]:
    approval = {
        "allow_qrtr_ns_transmit": args.allow_qrtr_ns_transmit,
        "assume_yes": args.assume_yes,
        "understand_qrtr_packet_transmission": args.i_understand_qrtr_packet_transmission,
    }
    approval["all_present"] = all(bool(value) for value in approval.values())
    return {
        "v272_decision": v272.get("decision"),
        "approval": approval,
        "matrix": matrix,
        "packet_scope": "QRTR nameservice NEW_LOOKUP plus cleanup DEL_LOOKUP only",
        "qmi_payload_allowed": False,
        "global_wildcard_allowed": False,
    }


def run_matrix_case(args: argparse.Namespace, store: EvidenceStore, item: dict[str, int | str]) -> dict[str, Any]:
    service = int(item["service"])
    instance = int(item["instance"])
    command = [
        "run",
        args.helper_device_binary,
        "--service",
        str(service),
        "--instance",
        str(instance),
        "--allow-qrtr-ns-transmit",
        "--readback-ms",
        str(args.readback_ms),
        "--max-events",
        str(args.max_events),
    ]
    started = now_iso()
    try:
        result = run_cmdv1_command(args.host, args.port, max(3.0, float(args.max_runtime_sec)), command, retry_unsafe=False)
        text = result.text
        stripped = strip_cmdv1_text(text)
        helper_keys = parse_key_values(stripped, "qrtr_ns")
        payload = {
            "name": item["name"],
            "service": service,
            "instance": instance,
            "command": command,
            "started": started,
            "ok": result.rc == 0 and result.status == "ok",
            "rc": result.rc,
            "status": result.status,
            "text": text,
            "stripped_text": stripped,
            "helper_keys": helper_keys,
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001 - live matrix evidence preserves failures
        payload = {
            "name": item["name"],
            "service": service,
            "instance": instance,
            "command": command,
            "started": started,
            "ok": False,
            "rc": None,
            "status": "missing",
            "text": "",
            "stripped_text": "",
            "helper_keys": {},
            "error": str(exc),
        }
    filename = f"matrix/{safe_name(str(item['name']))}-svc{service}-inst{instance}.txt"
    store.write_text(filename, payload["text"] if payload["text"] else payload["error"] + "\n")
    payload["file"] = filename
    return payload


def classify_case(case: dict[str, Any]) -> str:
    keys = case.get("helper_keys", {})
    if not case.get("ok"):
        return "failed"
    if keys.get("qmi_attempted") != "0":
        return "qmi-attempted"
    if keys.get("send_attempted") != "1":
        return "not-sent"
    if keys.get("del_lookup_send.rc") != "0":
        return "cleanup-failed"
    if helper_int(keys, "readback.service_events") > 0:
        return "services"
    if keys.get("readback.end_of_list") == "1":
        return "empty"
    if keys.get("readback.timeout") == "1":
        return "timeout"
    return "complete"


def matrix_rows(cases: list[dict[str, Any]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for case in cases:
        keys = case.get("helper_keys", {})
        rows.append(
            [
                str(case["name"]),
                str(case["service"]),
                str(case["instance"]),
                str(case.get("classification")),
                str(keys.get("readback.events")),
                str(keys.get("readback.service_events")),
                str(keys.get("readback.end_of_list")),
                str(keys.get("readback.timeout")),
                str(keys.get("qmi_attempted")),
            ]
        )
    return rows


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# QRTR Readback Matrix\n\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- reason: {manifest['reason']}\n\n",
        "## Checks\n\n",
    ]
    for item in manifest["checks"]:
        lines.append(f"- {'PASS' if item['pass'] else 'FAIL'} `{item['name']}` ({item['severity']}): {item['detail']}\n")
    lines.extend(
        [
            "\n## Matrix Results\n\n",
            markdown_table(
                ["name", "service", "instance", "classification", "events", "service_events", "end_of_list", "timeout", "qmi_attempted"],
                matrix_rows(manifest["matrix_results"]),
            ),
            "\n\n## Guardrails\n\n",
        ]
    )
    for item in manifest["guardrails"]:
        lines.append(f"- {item}\n")
    return "".join(lines)


def command_plan(args: argparse.Namespace) -> int:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    v272 = load_json(repo_path(args.v272_manifest))
    matrix = parse_matrix(args.matrix)
    manifest = {
        "created": now_iso(),
        "mode": "qrtr-readback-matrix",
        "command": "plan",
        "decision": "qrtr-readback-matrix-plan-ready",
        "pass": True,
        "reason": "bounded matrix plan generated without packet transmission",
        "out_dir": str(out_dir),
        "host_metadata": collect_host_metadata(),
        "contract": build_contract(args, v272, matrix),
        "guardrails": [
            "plan mode sends no packets",
            "run mode requires explicit approval flags",
            "matrix uses only nonzero service ids",
            "instance 0 is service-specific wildcard, not global service 0 wildcard",
            "no QMI request payload",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary({**manifest, "checks": [], "matrix_results": []}))
    print_result(manifest)
    return 0


def command_preflight(args: argparse.Namespace) -> int:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    v272 = load_json(repo_path(args.v272_manifest))
    matrix = parse_matrix(args.matrix)
    captures = capture_preflight(args, store)
    captures_by_name = by_name(captures)
    checks: list[dict[str, Any]] = []
    add_check(checks, "v272-ready", v272.get("decision") == "qmi-service-object-ids-extracted" and v272.get("pass") is True, f"decision={v272.get('decision')} pass={v272.get('pass')}")
    add_check(checks, "expected-version", capture_ok(captures_by_name, "version") and args.expect_version in str(captures_by_name["version"].get("text", "")), args.expect_version)
    add_check(checks, "helper-present", capture_ok(captures_by_name, "helper-sha256"), str(captures_by_name.get("helper-sha256", {}).get("text", ""))[:200])
    add_check(checks, "matrix-bounded", 0 < len(matrix) <= args.max_cases, f"cases={len(matrix)} max={args.max_cases}")
    add_check(checks, "global-wildcard-blocked", all(int(item["service"]) != 0 for item in matrix), json.dumps(matrix, sort_keys=True))
    pass_ok = all(item["pass"] for item in checks if item["severity"] == "critical")
    manifest = {
        "created": now_iso(),
        "mode": "qrtr-readback-matrix",
        "command": "preflight",
        "decision": "qrtr-readback-matrix-preflight-ready" if pass_ok else "qrtr-readback-matrix-preflight-blocked",
        "pass": pass_ok,
        "reason": "preflight ready; run still requires approval flags" if pass_ok else "preflight prerequisite failed",
        "out_dir": str(out_dir),
        "host_metadata": collect_host_metadata(),
        "contract": build_contract(args, v272, matrix),
        "checks": checks,
        "captures": captures,
        "guardrails": [
            "preflight mode sends no packets",
            "run mode requires explicit approval flags",
            "no QMI request payload",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary({**manifest, "matrix_results": []}))
    print_result(manifest)
    return 0 if pass_ok else 1


def command_run(args: argparse.Namespace) -> int:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    store.mkdir("matrix")
    v272 = load_json(repo_path(args.v272_manifest))
    matrix = parse_matrix(args.matrix)
    captures = capture_preflight(args, store)
    captures_by_name = by_name(captures)
    contract = build_contract(args, v272, matrix)

    checks: list[dict[str, Any]] = []
    add_check(checks, "v272-ready", v272.get("decision") == "qmi-service-object-ids-extracted" and v272.get("pass") is True, f"decision={v272.get('decision')} pass={v272.get('pass')}")
    add_check(checks, "expected-version", capture_ok(captures_by_name, "version") and args.expect_version in str(captures_by_name["version"].get("text", "")), args.expect_version)
    add_check(checks, "helper-present", capture_ok(captures_by_name, "helper-sha256"), str(captures_by_name.get("helper-sha256", {}).get("text", ""))[:200])
    add_check(checks, "approval-flags", bool(contract["approval"]["all_present"]), json.dumps(contract["approval"], sort_keys=True))
    add_check(checks, "matrix-bounded", 0 < len(matrix) <= args.max_cases, f"cases={len(matrix)} max={args.max_cases}")
    add_check(checks, "global-wildcard-blocked", all(int(item["service"]) != 0 for item in matrix), json.dumps(matrix, sort_keys=True))

    cases: list[dict[str, Any]] = []
    if all(item["pass"] for item in checks if item["severity"] == "critical"):
        for item in matrix:
            case = run_matrix_case(args, store, item)
            case["classification"] = classify_case(case)
            cases.append(case)
            keys = case.get("helper_keys", {})
            add_check(
                checks,
                f"case-{item['name']}-svc{item['service']}-inst{item['instance']}",
                case["classification"] in {"services", "empty", "timeout", "complete"},
                json.dumps({
                    "classification": case["classification"],
                    "rc": case.get("rc"),
                    "status": case.get("status"),
                    "events": keys.get("readback.events"),
                    "service_events": keys.get("readback.service_events"),
                    "end_of_list": keys.get("readback.end_of_list"),
                    "timeout": keys.get("readback.timeout"),
                    "qmi_attempted": keys.get("qmi_attempted"),
                    "error": case.get("error"),
                }, sort_keys=True),
            )
    pass_ok = all(item["pass"] for item in checks if item["severity"] == "critical")
    classifications = {str(case.get("classification")) for case in cases}
    if not pass_ok:
        decision = "qrtr-readback-matrix-failed"
        reason = "one or more matrix prerequisites or cases failed"
    elif "services" in classifications:
        decision = "qrtr-readback-matrix-services"
        reason = "one or more matrix cases observed service events"
    elif classifications == {"timeout"}:
        decision = "qrtr-readback-matrix-timeout"
        reason = "all matrix cases completed with bounded readback timeouts"
    elif "empty" in classifications:
        decision = "qrtr-readback-matrix-empty"
        reason = "one or more matrix cases reached nameservice end-of-list without services"
    else:
        decision = "qrtr-readback-matrix-complete"
        reason = "matrix completed without QMI payloads"

    manifest = {
        "created": now_iso(),
        "mode": "qrtr-readback-matrix",
        "command": "run",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "out_dir": str(out_dir),
        "host_metadata": collect_host_metadata(),
        "contract": contract,
        "checks": checks,
        "captures": captures,
        "matrix_results": cases,
        "guardrails": [
            "approved run sends only QRTR nameservice NEW_LOOKUP and cleanup DEL_LOOKUP",
            "readback is bounded by --readback-ms and --max-events",
            "service id 0 global wildcard is blocked",
            "no QMI request payload",
            "no Wi-Fi scan/connect/link-up",
            "no daemon start",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print_result(manifest)
    return 0 if pass_ok else 1


def print_result(manifest: dict[str, Any]) -> None:
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"out_dir: {manifest['out_dir']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v272-manifest", type=Path, default=DEFAULT_V272_MANIFEST)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper-device-binary", default=DEFAULT_HELPER_DEVICE_BINARY)
    parser.add_argument("--matrix", default=DEFAULT_MATRIX)
    parser.add_argument("--readback-ms", type=int, default=1500)
    parser.add_argument("--max-events", type=int, default=16)
    parser.add_argument("--max-runtime-sec", type=int, default=8)
    parser.add_argument("--max-cases", type=int, default=8)
    parser.add_argument("--allow-qrtr-ns-transmit", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-qrtr-packet-transmission", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "preflight", "run"):
        subparsers.add_parser(name)
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
