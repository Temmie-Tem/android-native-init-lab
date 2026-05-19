#!/usr/bin/env python3
"""v269 QRTR nameservice runner.

This runner keeps the plan and read-only preflight paths non-transmitting. The
run path remains fail-closed unless the explicit QRTR nameservice transmit
approval flags are present; with approval it builds/deploys the reviewed static
helper and executes one bounded QRTR nameservice lookup cleanup pair.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import http.server
import json
import re
import subprocess
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90ctl import run_cmdv1_command  # noqa: E402
from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text  # noqa: E402
from a90harness.evidence import EvidenceStore  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = Path("tmp/wifi/v269-qrtr-nameservice-live-retry")
DEFAULT_V264_MANIFEST = Path("tmp/wifi/v264-qrtr-qmi-nameservice-model/manifest.json")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.60 (v261)"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_HELPER_LOCAL_BINARY = Path("tmp/wifi/v269-qrtr-nameservice-live-retry/build/a90_qrtr_ns_probe")
DEFAULT_HELPER_DEVICE_BINARY = "/cache/bin/a90_qrtr_ns_probe"
BUILD_HELPER = Path("scripts/revalidation/build_qrtr_ns_probe_helper.sh")

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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_host_process(command: list[str], timeout: float, cwd: Path = REPO_ROOT) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return {
            "command": command,
            "started": started.isoformat(),
            "rc": result.returncode,
            "ok": result.returncode == 0,
            "text": result.stdout,
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001 - evidence preserves failure details
        return {
            "command": command,
            "started": started.isoformat(),
            "rc": None,
            "ok": False,
            "text": "",
            "error": str(exc),
        }


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


class SingleFileHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "A90QRTRHelperHTTP/1"

    def do_GET(self) -> None:  # noqa: N802 - http.server API
        expected_path = "/" + self.server.file_path.name  # type: ignore[attr-defined]
        if self.path.split("?", 1)[0] != expected_path:
            self.send_error(404, "not found")
            return
        data = self.server.file_path.read_bytes()  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(data)
            self.wfile.flush()
            self.server.served_count += 1  # type: ignore[attr-defined]
        except (BrokenPipeError, ConnectionResetError) as exc:
            self.server.request_log.append(f"client-closed-during-body: {exc}")  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        self.server.request_log.append(fmt % args)  # type: ignore[attr-defined]


class HelperHttpServer:
    def __init__(self, bind_addr: str, url_host: str, port: int, file_path: Path) -> None:
        self.bind_addr = bind_addr
        self.url_host = url_host
        self.port = port
        self.file_path = file_path
        self.server: http.server.ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None

    def __enter__(self) -> "HelperHttpServer":
        server = http.server.ThreadingHTTPServer((self.bind_addr, self.port), SingleFileHandler)
        server.daemon_threads = True
        server.file_path = self.file_path  # type: ignore[attr-defined]
        server.request_log = []  # type: ignore[attr-defined]
        server.served_count = 0  # type: ignore[attr-defined]
        self.server = server
        self.thread = threading.Thread(target=server.serve_forever, name="a90-qrtr-helper-http", daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2.0)

    @property
    def url(self) -> str:
        if self.server is None:
            raise RuntimeError("HTTP server not started")
        port = self.server.server_address[1]
        return f"http://{self.url_host}:{port}/{self.file_path.name}"

    def manifest(self) -> dict[str, Any]:
        if self.server is None:
            return {}
        return {
            "bind_addr": self.server.server_address[0],
            "url_host": self.url_host,
            "port": self.server.server_address[1],
            "url": self.url,
            "served_count": getattr(self.server, "served_count", 0),
            "request_log": list(getattr(self.server, "request_log", [])),
        }


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
            "transmit_implemented": True,
            "helper_local_binary": str(repo_path(args.helper_local_binary)),
            "helper_device_binary": args.helper_device_binary,
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
            "name": "qmi-payload-disallowed",
            "pass": contract["packet_scope"]["qmi_payload_allowed"] is False,
            "severity": "critical",
            "detail": "runner only permits QRTR nameservice control packet, never QMI payload",
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
    return True, "qrtr-ns-runner-plan-ready", "runner plan is ready; transmission remains approval-gated"


def classify_preflight(checks: list[dict[str, Any]]) -> tuple[bool, str, str]:
    failed = [item["name"] for item in checks if item["severity"] == "critical" and not item["pass"]]
    if failed:
        return False, "qrtr-ns-runner-preflight-blocked", "preflight failed: " + ", ".join(failed)
    return True, "qrtr-ns-runner-preflight-ready", "read-only preflight passed without QRTR/QMI transmission"


def classify_run_pre_execute(checks: list[dict[str, Any]], contract: dict[str, Any]) -> tuple[bool, str, str]:
    failed = [item["name"] for item in checks if item["severity"] == "critical" and not item["pass"]]
    if failed:
        return False, "qrtr-ns-runner-run-blocked", "run prerequisite failed: " + ", ".join(failed)
    approval = contract["approval"]
    if not approval["all_present"]:
        return True, "qrtr-ns-runner-fail-closed", "missing explicit transmit approval flags; no QRTR packet sent"
    return True, "qrtr-ns-runner-approved", "approval flags present and pre-execute checks passed"


def classify_executed_run(checks: list[dict[str, Any]], helper_keys: dict[str, str]) -> tuple[bool, str, str]:
    failed = [item["name"] for item in checks if item["severity"] == "critical" and not item["pass"]]
    if failed:
        return False, "qrtr-ns-runner-live-failed", "live run failed: " + ", ".join(failed)
    return True, "qrtr-ns-runner-lookup-sent", (
        "single QRTR nameservice lookup/delete packet pair executed; "
        f"helper_status={helper_keys.get('status', 'missing')}"
    )


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
        "# v269 QRTR Nameservice Runner\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- command: `{manifest['command']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        f"- out_dir: `{manifest['out_dir']}`\n",
        f"- QRTR/QMI packet transmission: `{manifest.get('qrtr_transmission', 'not executed')}`\n",
        "- Wi-Fi scan/connect/link-up: `not executed`\n\n",
        "## Checks\n\n",
        markdown_table(["check", "result", "severity", "detail"], checks),
        "\n\n## Contract\n\n",
        markdown_table(["section", "key", "value"], contract_rows),
        "\n\n## Guardrails\n\n",
        "- `plan` and `preflight` never open QRTR sockets or send QRTR/QMI packets.\n",
        "- `run` without explicit approval flags succeeds only as a fail-closed proof.\n",
        "- Approved `run` executes only `/cache/bin/a90_qrtr_ns_probe` with the reviewed nameservice helper.\n",
        "- The helper sends QRTR nameservice control packets only; QMI payloads remain disallowed.\n",
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
        "mode": "qrtr-nameservice-runner",
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
        "mode": "qrtr-nameservice-runner",
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


def build_helper(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    local_binary = repo_path(args.helper_local_binary)
    build_script = repo_path(BUILD_HELPER)
    local_binary.parent.mkdir(parents=True, exist_ok=True)
    result = run_host_process(
        [str(build_script), str(local_binary)],
        timeout=max(30.0, float(args.build_timeout)),
    )
    store.write_text("build-helper.txt", result["text"] if result["text"] else result["error"] + "\n")
    result["local_binary"] = str(local_binary)
    if local_binary.exists():
        result["sha256"] = sha256_file(local_binary)
        result["size"] = local_binary.stat().st_size
    else:
        result["sha256"] = None
        result["size"] = None
    return result


def host_ping_device(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    result = run_host_process(
        ["ping", "-c", "1", "-W", "1", args.device_ip],
        timeout=5.0,
    )
    store.write_text("host-ping-device.txt", result["text"] if result["text"] else result["error"] + "\n")
    return result


def deploy_helper(args: argparse.Namespace, store: EvidenceStore, local_binary: Path) -> dict[str, Any]:
    local_hash = sha256_file(local_binary)
    target = args.helper_device_binary
    target_dir = str(Path(target).parent)
    tmp_target = f"{target_dir}/.{Path(target).name}.tmp.{int(time.time())}"
    captures: list[dict[str, Any]] = []
    errors: list[str] = []

    def run_step(name: str, command: list[str], timeout: float) -> bool:
        started = time.monotonic()
        try:
            result = run_cmdv1_command(args.host, args.port, timeout, command, retry_unsafe=False)
            ok = result.rc == 0 and result.status == "ok"
            captures.append({
                "name": name,
                "command": command,
                "ok": ok,
                "rc": result.rc,
                "status": result.status,
                "duration_sec": time.monotonic() - started,
                "text": result.text,
                "error": "",
            })
            if not ok:
                errors.append(f"{name}: rc={result.rc} status={result.status}")
            return ok
        except Exception as exc:  # noqa: BLE001 - preserve deploy evidence
            captures.append({
                "name": name,
                "command": command,
                "ok": False,
                "rc": None,
                "status": "missing",
                "duration_sec": time.monotonic() - started,
                "text": "",
                "error": str(exc),
            })
            errors.append(f"{name}: {exc}")
            return False

    http_info: dict[str, Any] = {}
    with HelperHttpServer(args.host_http_bind, args.host_http_url_host, args.transfer_port, local_binary) as httpd:
        http_info = httpd.manifest()
        url = httpd.url
        run_step("mkdir-target-dir", ["mkdir", target_dir], 10.0)
        run_step("remove-temp", ["run", args.toybox, "rm", "-f", tmp_target], 15.0)
        if run_step("wget-helper", ["run", args.toybox, "wget", "-O", tmp_target, url], args.deploy_timeout):
            run_step("chmod-helper", ["run", args.toybox, "chmod", "755", tmp_target], 10.0)
            sha_ok = run_step("sha256-helper", ["run", args.toybox, "sha256sum", tmp_target], 15.0)
            if sha_ok and local_hash not in captures[-1]["text"]:
                errors.append("sha256-helper: local hash not found in device output")
                captures[-1]["ok"] = False
            if not errors:
                run_step("move-helper", ["run", args.toybox, "mv", "-f", tmp_target, target], 15.0)
                run_step("sync", ["sync"], 10.0)
        http_info = httpd.manifest()

    if errors:
        run_step("cleanup-temp", ["run", args.toybox, "rm", "-f", tmp_target], 15.0)

    text_parts: list[str] = [
        f"http: {json.dumps(http_info, sort_keys=True)}\n",
        f"local_sha256: {local_hash}\n",
        f"target: {target}\n",
        f"tmp_target: {tmp_target}\n",
        "\n",
    ]
    for item in captures:
        text_parts.append(f"--- {item['name']} ok={item['ok']} rc={item['rc']} status={item['status']} ---\n")
        if item["text"]:
            text_parts.append(str(item["text"]))
            if not str(item["text"]).endswith("\n"):
                text_parts.append("\n")
        if item["error"]:
            text_parts.append(str(item["error"]) + "\n")
    store.write_text("deploy-helper.txt", "".join(text_parts))
    return {
        "command": "http-wget-deploy",
        "ok": not errors,
        "rc": 0 if not errors else 1,
        "started": now_iso(),
        "device_binary": target,
        "tmp_target": tmp_target,
        "local_binary": str(local_binary),
        "sha256": local_hash,
        "http": http_info,
        "captures": captures,
        "errors": errors,
        "text": "".join(text_parts),
    }


def run_helper(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    command = [
        "run",
        args.helper_device_binary,
        "--service",
        str(int(args.service, 0)),
        "--instance",
        str(int(args.instance, 0)),
        "--allow-qrtr-ns-transmit",
    ]
    if args.allow_wildcard_lookup:
        command.append("--allow-wildcard-lookup")
    if args.no_del_lookup:
        command.append("--no-del-lookup")
    started = dt.datetime.now(dt.timezone.utc)
    try:
        result = run_cmdv1_command(
            args.host,
            args.port,
            max(3.0, float(args.max_runtime_sec)),
            command,
            retry_unsafe=False,
        )
        text = result.text
        stripped = strip_cmdv1_text(text)
        helper_keys = parse_key_values(stripped, "qrtr_ns")
        payload = {
            "command": command,
            "started": started.isoformat(),
            "ok": result.rc == 0 and result.status == "ok",
            "rc": result.rc,
            "status": result.status,
            "text": text,
            "stripped_text": stripped,
            "helper_keys": helper_keys,
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001 - live evidence preserves failure
        payload = {
            "command": command,
            "started": started.isoformat(),
            "ok": False,
            "rc": None,
            "status": "missing",
            "text": "",
            "stripped_text": "",
            "helper_keys": {},
            "error": str(exc),
        }
    store.write_text("run-helper.txt", payload["text"] if payload["text"] else payload["error"] + "\n")
    return payload


def command_run(args: argparse.Namespace) -> int:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    v264 = load_json(repo_path(args.v264_manifest))
    contract = build_contract(args, v264)
    captures_list = capture_preflight(args, store)
    captures = by_name(captures_list)
    checks = preflight_checks(args, v264, contract, captures)
    checks.append({
        "name": "approval-flag-check",
        "pass": True,
        "severity": "info",
        "detail": json.dumps(contract["approval"], sort_keys=True),
    })
    pre_ok, decision, reason = classify_run_pre_execute(checks, contract)
    build_result: dict[str, Any] | None = None
    deploy_result: dict[str, Any] | None = None
    helper_result: dict[str, Any] | None = None
    host_ping_result: dict[str, Any] | None = None
    live_checks: list[dict[str, Any]] = []
    pass_ok = pre_ok

    if pre_ok and contract["approval"]["all_present"]:
        host_ping_result = host_ping_device(args, store)
        live_checks.append({
            "name": "host-ncm-ping-device",
            "pass": bool(host_ping_result.get("ok")),
            "severity": "critical",
            "detail": json.dumps({
                "rc": host_ping_result.get("rc"),
                "device_ip": args.device_ip,
            }, sort_keys=True),
        })

    if pre_ok and contract["approval"]["all_present"] and all(item["pass"] for item in live_checks if item["severity"] == "critical"):
        build_result = build_helper(args, store)
        live_checks.append({
            "name": "helper-build",
            "pass": bool(build_result.get("ok")) and bool(build_result.get("sha256")),
            "severity": "critical",
            "detail": json.dumps({
                "rc": build_result.get("rc"),
                "sha256": build_result.get("sha256"),
                "size": build_result.get("size"),
            }, sort_keys=True),
        })
        local_binary = repo_path(args.helper_local_binary)
        if live_checks[-1]["pass"] and not args.skip_deploy:
            deploy_result = deploy_helper(args, store, local_binary)
            live_checks.append({
                "name": "helper-deploy",
                "pass": bool(deploy_result.get("ok")),
                "severity": "critical",
                "detail": json.dumps({
                    "rc": deploy_result.get("rc"),
                    "device_binary": deploy_result.get("device_binary"),
                }, sort_keys=True),
            })
        elif args.skip_deploy:
            live_checks.append({
                "name": "helper-deploy",
                "pass": True,
                "severity": "critical",
                "detail": "skipped by --skip-deploy; assuming device helper already matches reviewed binary",
            })

        if all(item["pass"] for item in live_checks if item["severity"] == "critical"):
            helper_result = run_helper(args, store)
            helper_keys = helper_result.get("helper_keys", {})
            live_checks.extend([
                {
                    "name": "helper-command-rc",
                    "pass": bool(helper_result.get("ok")),
                    "severity": "critical",
                    "detail": json.dumps({
                        "rc": helper_result.get("rc"),
                        "status": helper_result.get("status"),
                        "error": helper_result.get("error"),
                    }, sort_keys=True),
                },
                {
                    "name": "qrtr-lookup-sent",
                    "pass": helper_keys.get("status") == "lookup-sent",
                    "severity": "critical",
                    "detail": json.dumps(helper_keys, sort_keys=True),
                },
                {
                    "name": "qrtr-send-attempted",
                    "pass": helper_keys.get("send_attempted") == "1",
                    "severity": "critical",
                    "detail": json.dumps(helper_keys, sort_keys=True),
                },
                {
                    "name": "qmi-not-attempted",
                    "pass": helper_keys.get("qmi_attempted") == "0",
                    "severity": "critical",
                    "detail": json.dumps(helper_keys, sort_keys=True),
                },
            ])
    if pre_ok and contract["approval"]["all_present"] and live_checks:
        checks.extend(live_checks)
        pass_ok, decision, reason = classify_executed_run(checks, helper_result.get("helper_keys", {}) if helper_result else {})

    manifest = {
        "created": now_iso(),
        "mode": "qrtr-nameservice-runner",
        "command": "run",
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(out_dir),
        "inputs": {"v264_manifest": str(repo_path(args.v264_manifest))},
        "host_metadata": collect_host_metadata(),
        "contract": contract,
        "checks": checks,
        "captures": captures_list,
        "host_ping": host_ping_result,
        "build": build_result,
        "deploy": deploy_result,
        "helper_run": helper_result,
        "qrtr_transmission": "executed" if helper_result else "not executed",
        "guardrails": [
            "read-only preflight always runs before approved helper execution",
            "fail closed unless approval flags are present",
            "approved helper sends only QRTR nameservice NEW_LOOKUP and cleanup DEL_LOOKUP",
            "no QMI request payload",
            "no Wi-Fi scan/connect/link-up",
        ],
    }
    store.write_json("captures.json", {"captures": captures_list})
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
    parser.add_argument("--build-timeout", type=float, default=60.0)
    parser.add_argument("--deploy-timeout", type=float, default=120.0)
    parser.add_argument("--transfer-port", type=int, default=18084)
    parser.add_argument("--device-ip", default="192.168.7.2")
    parser.add_argument("--host-http-bind", default="0.0.0.0")
    parser.add_argument("--host-http-url-host", default="192.168.7.1")
    parser.add_argument("--helper-local-binary", type=Path, default=DEFAULT_HELPER_LOCAL_BINARY)
    parser.add_argument("--helper-device-binary", default=DEFAULT_HELPER_DEVICE_BINARY)
    parser.add_argument("--skip-deploy", action="store_true")
    parser.add_argument("--no-del-lookup", action="store_true")
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
