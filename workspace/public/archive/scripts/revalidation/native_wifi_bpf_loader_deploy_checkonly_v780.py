#!/usr/bin/env python3
"""V780 deploy/check-only proof for the minimal BPF tracepoint helper.

V779 built a static aarch64 helper but did not deploy or execute it.  V780 is
the first live gate: deploy only that reviewed artifact, verify the remote hash,
and run check-only/default-no-attach modes.  It never passes --allow-attach.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90ctl import bridge_exchange, encode_cmdv1_line, run_cmdv1_command
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v780-bpf-loader-deploy-checkonly")
LATEST_POINTER = Path("tmp/wifi/latest-v780-bpf-loader-deploy-checkonly.txt")
DEFAULT_LOCAL_HELPER = Path("tmp/wifi/v779-bpf-loader-build/a90_bpf_trace_probe-aarch64-static")
DEFAULT_V779_MANIFEST = Path("tmp/wifi/v779-bpf-loader-build/manifest.json")
DEFAULT_REMOTE_HELPER = "/cache/bin/a90_bpf_trace_probe"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_SHA256 = "9d8fdfeaa9281ba814db62ddc588b37959021d68fbd08164ae366dde3f08b1c3"
HELPER_MARKER = "a90_bpf_trace_probe v779"
SERIAL_CONSOLE_LINE_LIMIT = 4096
SERIAL_CONSOLE_LINE_MARGIN = 128
SERIAL_SAFE_LINE_LIMIT = SERIAL_CONSOLE_LINE_LIMIT - SERIAL_CONSOLE_LINE_MARGIN
SERIAL_MAX_REQUESTED_CHUNK_SIZE = 1800

FORBIDDEN_DEVICE_TERMS = (
    "--allow-attach",
    " boot_wlan",
    " qcwlanstate",
    " servicemanager",
    " android.hardware.wifi",
    " wpa_supplicant",
    " wificond",
    " hostapd",
    " svc wifi",
    " cmd wifi",
    " iw ",
    " dhcp",
    " ip route",
    " ip addr",
    " ping ",
    " reboot",
    " dd ",
    " flash",
    " set_ftrace_filter",
    " trace_marker",
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
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--local-helper", type=Path, default=DEFAULT_LOCAL_HELPER)
    parser.add_argument("--v779-manifest", type=Path, default=DEFAULT_V779_MANIFEST)
    parser.add_argument("--remote-helper", default=DEFAULT_REMOTE_HELPER)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--expect-sha256", default=DEFAULT_EXPECT_SHA256)
    parser.add_argument("--serial-staging-dir", default="/cache/a90-runtime/bin")
    parser.add_argument("--serial-chunk-size", type=int, default=SERIAL_MAX_REQUESTED_CHUNK_SIZE)
    parser.add_argument("--allow-serial-deploy", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def uu_char(value: int) -> str:
    value &= 0x3f
    return chr(value + 0x20) if value else "`"


def uuencode_bytes(data: bytes, *, name: str, mode: int = 0o755) -> str:
    lines = [f"begin {mode:o} {name}\n"]
    for offset in range(0, len(data), 45):
        chunk = data[offset:offset + 45]
        padded = chunk + b"\0" * ((3 - len(chunk) % 3) % 3)
        encoded: list[str] = []
        for index in range(0, len(padded), 3):
            first, second, third = padded[index], padded[index + 1], padded[index + 2]
            encoded.extend(
                uu_char(value)
                for value in (
                    first >> 2,
                    ((first << 4) & 0x30) | (second >> 4),
                    ((second << 2) & 0x3c) | (third >> 6),
                    third & 0x3f,
                )
            )
        lines.append(uu_char(len(chunk)) + "".join(encoded) + "\n")
    lines.append("`\nend\n")
    return "".join(lines)


def serial_append_line_check(staging: str, encoded: str, chunk_size: int) -> dict[str, Any]:
    max_line_bytes = 0
    max_line_offset = 0
    chunks = 0
    uses_cmdv1x = False
    for offset in range(0, len(encoded), chunk_size):
        chunk = encoded[offset:offset + chunk_size]
        line = encode_cmdv1_line(["appendfile", staging, chunk])
        line_bytes = len(line.encode("utf-8"))
        if line_bytes > max_line_bytes:
            max_line_bytes = line_bytes
            max_line_offset = offset
        uses_cmdv1x = uses_cmdv1x or line.startswith("cmdv1x ")
        chunks += 1
    return {
        "ok": max_line_bytes <= SERIAL_SAFE_LINE_LIMIT,
        "chunk_size": chunk_size,
        "chunks": chunks,
        "max_cmdv1_line_bytes": max_line_bytes,
        "max_cmdv1_line_offset": max_line_offset,
        "safe_line_limit": SERIAL_SAFE_LINE_LIMIT,
        "console_line_limit": SERIAL_CONSOLE_LINE_LIMIT,
        "uses_cmdv1x": uses_cmdv1x,
    }


def validate_device_command(command: list[str]) -> None:
    joined = " " + " ".join(command).lower() + " "
    for term in FORBIDDEN_DEVICE_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden V780 command term {term!r}: {' '.join(command)}")


def run_device(args: argparse.Namespace, argv: list[str], timeout: float = 30.0) -> tuple[bool, str, int | None, str]:
    validate_device_command(argv)
    try:
        result = run_cmdv1_command(args.host, args.port, timeout, argv, retry_unsafe=False)
    except Exception as exc:  # noqa: BLE001 - live evidence preserves failure text
        return False, str(exc) + "\n", None, "missing"
    if result.status == "busy":
        hide_text = ""
        try:
            hide_text = bridge_exchange(
                args.host,
                args.port,
                "hide",
                min(timeout, 8.0),
                markers=(b"[busy]", b"[done]", b"[err]"),
            )
            result = run_cmdv1_command(args.host, args.port, timeout, argv, retry_unsafe=False)
        except Exception as exc:  # noqa: BLE001
            return False, result.text + "\n## auto-hide retry failed\n" + hide_text + str(exc) + "\n", result.rc, result.status
    return result.rc == 0 and result.status == "ok", result.text, result.rc, result.status


def capture_device(args: argparse.Namespace,
                   store: EvidenceStore,
                   steps: list[dict[str, Any]],
                   name: str,
                   command: list[str],
                   timeout: float | None = None) -> dict[str, Any]:
    validate_device_command(command)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    item = capture_to_manifest(capture)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item["payload"] = payload
    item["file"] = f"native/{safe_name(name)}.txt"
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def run_serial_install(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    local_path = repo_path(args.local_helper)
    target = args.remote_helper
    target_dir = str(Path(target).parent)
    target_name = Path(target).name
    stamp = f"{int(time.time())}.{os.getpid()}"
    staging_dir = args.serial_staging_dir.rstrip("/")
    staging = f"{staging_dir}/.{target_name}.v780.{stamp}.uu"
    tmp_target = f"{target_dir}/.{target_name}.tmp.{stamp}"
    transcript: list[str] = []
    chunks_written = 0

    data = local_path.read_bytes()
    encoded = uuencode_bytes(data, name=Path(tmp_target).name, mode=0o755)
    chunk_size = max(256, min(args.serial_chunk_size, SERIAL_MAX_REQUESTED_CHUNK_SIZE))
    line_check = serial_append_line_check(staging, encoded, chunk_size)
    if not line_check["ok"]:
        message = (
            "serial chunk size is unsafe for the native console line limit: "
            f"chunk_size={chunk_size} max_cmdv1_line_bytes={line_check['max_cmdv1_line_bytes']} "
            f"safe_line_limit={SERIAL_SAFE_LINE_LIMIT}"
        )
        store.write_text("host/serial-install-helper.txt", message + "\n")
        return {
            **line_check,
            "method": "serial",
            "rc": 1,
            "ok": False,
            "file": "host/serial-install-helper.txt",
            "error": message,
            "chunks_written": 0,
            "encoded_bytes": len(encoded.encode("utf-8")),
        }

    def step(name: str, argv: list[str], timeout: float = 30.0, allow_error: bool = False) -> str:
        ok, text, rc, status = run_device(args, argv, timeout)
        transcript.append(f"## {name}\nargv={argv!r}\nok={ok} rc={rc} status={status}\n{text}\n")
        if not ok and not allow_error:
            raise RuntimeError(f"serial deploy step failed: {name} rc={rc} status={status}\n{text}")
        return text

    try:
        step("mkdir-staging-dir", ["mkdir", staging_dir], allow_error=True)
        step("rm-staging", ["run", args.toybox, "rm", "-f", staging], allow_error=True)
        step("rm-tmp", ["run", args.toybox, "rm", "-f", tmp_target], allow_error=True)
        for offset in range(0, len(encoded), chunk_size):
            chunk = encoded[offset:offset + chunk_size]
            step(f"append-{chunks_written:04d}", ["appendfile", staging, chunk], timeout=20.0)
            chunks_written += 1
            if chunks_written % 100 == 0:
                print(f"[v780] serial append chunks={chunks_written}/{line_check['chunks']}", flush=True)
        step("uudecode", ["run", args.toybox, "uudecode", "-o", tmp_target, staging], timeout=90.0)
        step("chmod", ["run", args.toybox, "chmod", "755", tmp_target])
        sha_text = step("sha-tmp", ["run", args.toybox, "sha256sum", tmp_target])
        if args.expect_sha256 not in sha_text:
            raise RuntimeError(f"tmp helper sha256 mismatch, expected {args.expect_sha256}\n{sha_text}")
        step("mv-target", ["run", args.toybox, "mv", "-f", tmp_target, target])
        target_sha = step("sha-target", ["run", args.toybox, "sha256sum", target])
        if args.expect_sha256 not in target_sha:
            raise RuntimeError(f"target helper sha256 mismatch, expected {args.expect_sha256}\n{target_sha}")
        step("rm-staging-post", ["run", args.toybox, "rm", "-f", staging], allow_error=True)
    except Exception as exc:
        try:
            run_device(args, ["run", args.toybox, "rm", "-f", tmp_target], timeout=20.0)
        finally:
            store.write_text("host/serial-install-helper.txt", "\n".join(transcript))
        return {
            **line_check,
            "method": "serial",
            "rc": 1,
            "ok": False,
            "file": "host/serial-install-helper.txt",
            "error": str(exc),
            "chunks_written": chunks_written,
            "encoded_bytes": len(encoded.encode("utf-8")),
        }

    store.write_text("host/serial-install-helper.txt", "\n".join(transcript))
    return {
        **line_check,
        "method": "serial",
        "rc": 0,
        "ok": True,
        "file": "host/serial-install-helper.txt",
        "chunks_written": chunks_written,
        "encoded_bytes": len(encoded.encode("utf-8")),
    }


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def local_helper_info(args: argparse.Namespace) -> dict[str, Any]:
    path = repo_path(args.local_helper)
    return {
        "path": str(path),
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }


def analyze(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v779 = load_json(args.v779_manifest)
    steps: list[dict[str, Any]] = []
    install: dict[str, Any] = {}
    analysis: dict[str, Any] = {
        "v779": {
            "manifest": str(repo_path(args.v779_manifest)),
            "decision": v779.get("decision", ""),
            "pass": bool(v779.get("pass")),
        },
        "local_helper": local_helper_info(args),
        "serial_install": install,
        "native_steps": steps,
    }
    if args.command != "run":
        return analysis
    if not args.allow_serial_deploy or not args.assume_yes:
        analysis["serial_install"] = {"ok": False, "error": "run requires --allow-serial-deploy --assume-yes"}
        return analysis
    capture_device(args, store, steps, "version", ["version"], 10.0)
    capture_device(args, store, steps, "status", ["status"], 25.0)
    install = run_serial_install(args, store)
    analysis["serial_install"] = install
    if install.get("ok"):
        capture_device(args, store, steps, "sha-helper", ["run", args.toybox, "sha256sum", args.remote_helper], 20.0)
        capture_device(args, store, steps, "helper-check-only", ["run", args.remote_helper, "--check-only"], 20.0)
        capture_device(args, store, steps, "helper-default", ["run", args.remote_helper], 20.0)
    return analysis


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(manifest: dict[str, Any]) -> list[Check]:
    analysis = manifest["analysis"]
    checks: list[Check] = []
    local = analysis["local_helper"]
    add_check(
        checks,
        "v779-input",
        "pass" if analysis["v779"]["decision"] == "v779-bpf-loader-build-pass" else "blocked",
        "blocker",
        f"decision={analysis['v779']['decision']} pass={analysis['v779']['pass']}",
        [analysis["v779"]["manifest"]],
        "complete V779 before live deploy",
    )
    add_check(
        checks,
        "local-helper-sha",
        "pass" if local["exists"] and local["sha256"] == manifest["expect_sha256"] else "blocked",
        "blocker",
        f"exists={local['exists']} size={local['size']} sha256={local['sha256']}",
        [local["path"]],
        "rebuild V779 helper or update expected hash only after review",
    )
    if manifest["command"] == "plan":
        add_check(checks, "plan-only", "pass", "info", "no live deploy or device command executed", [], "run V780 with explicit serial deploy flags")
        return checks
    install = analysis["serial_install"]
    add_check(
        checks,
        "serial-deploy",
        "pass" if install.get("ok") else "blocked",
        "blocker",
        f"method={install.get('method')} chunks={install.get('chunks_written')}/{install.get('chunks')} error={install.get('error', '')}",
        [install.get("file", "")],
        "fix deploy path before check-only proof",
    )
    sha_text = step_payload(analysis["native_steps"], "sha-helper")
    check_text = step_payload(analysis["native_steps"], "helper-check-only")
    default_text = step_payload(analysis["native_steps"], "helper-default")
    add_check(
        checks,
        "remote-helper-sha",
        "pass" if manifest["expect_sha256"] in sha_text else "blocked",
        "blocker",
        f"expected_sha_present={manifest['expect_sha256'] in sha_text}",
        ["native/sha-helper.txt"],
        "redeploy helper before execution",
    )
    check_ok = HELPER_MARKER in check_text and "result=check-only" in check_text and "attach_attempted=0" in check_text
    add_check(
        checks,
        "check-only-no-attach",
        "pass" if check_ok else "blocked",
        "blocker",
        f"marker={HELPER_MARKER in check_text} result_check_only={'result=check-only' in check_text} attach0={'attach_attempted=0' in check_text}",
        ["native/helper-check-only.txt"],
        "stop before BPF attach gate",
    )
    default_ok = HELPER_MARKER in default_text and "result=check-only" in default_text and "attach_attempted=0" in default_text
    add_check(
        checks,
        "default-no-attach",
        "pass" if default_ok else "blocked",
        "blocker",
        f"marker={HELPER_MARKER in default_text} result_check_only={'result=check-only' in default_text} attach0={'attach_attempted=0' in default_text}",
        ["native/helper-default.txt"],
        "preserve default no-attach behavior",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return ("v780-bpf-loader-deploy-checkonly-plan-ready", True, "plan-only; no live deploy, BPF attach, or Wi-Fi action executed", "run V780 deploy/check-only gate")
    blockers = blocking(checks)
    if blockers:
        return ("v780-bpf-loader-deploy-checkonly-blocked", False, "blocked by " + ", ".join(blockers), "fix blockers before any attach proof")
    return (
        "v780-bpf-loader-deploy-checkonly-pass",
        True,
        "helper deployed, hash matched, and both check-only/default modes reported attach_attempted=0",
        "V781 may attempt bounded idle tracepoint attach only after separate review gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    local = manifest.get("analysis", {}).get("local_helper", {})
    install = manifest.get("analysis", {}).get("serial_install", {})
    return "\n".join([
        "# V780 BPF Loader Deploy Check-Only",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- serial_deploy_executed: `{manifest['serial_deploy_executed']}`",
        f"- bpf_attach_executed: `{manifest['bpf_attach_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence", "next"], [
            [
                check["name"],
                check["status"],
                check["severity"],
                check["detail"],
                ", ".join(check.get("evidence") or []),
                check["next_step"],
            ]
            for check in checks
        ]),
        "",
        "## Artifact",
        "",
        markdown_table(["signal", "value"], [
            ["local", local.get("path", "")],
            ["size", local.get("size", "")],
            ["sha256", local.get("sha256", "")],
            ["remote", manifest.get("remote_helper", "")],
            ["serial_chunks", f"{install.get('chunks_written', 0)}/{install.get('chunks', 0)}"],
            ["serial_encoded_bytes", install.get("encoded_bytes", "")],
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = analyze(args, store)
    manifest: dict[str, Any] = {
        "cycle": "v780",
        "generated_at": now_iso(),
        "command": args.command,
        "analysis": analysis,
        "expect_sha256": args.expect_sha256,
        "remote_helper": args.remote_helper,
        "device_commands_executed": args.command == "run",
        "serial_deploy_executed": args.command == "run" and bool(analysis.get("serial_install", {}).get("ok")),
        "bpf_attach_executed": False,
        "ftrace_control_write_executed": False,
        "wifi_action_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
        "host": collect_host_metadata(),
    }
    checks = build_checks(manifest)
    decision, ok, reason, next_step = decide(args.command, checks)
    manifest.update({"checks": [asdict(check) for check in checks], "decision": decision, "pass": ok, "reason": reason, "next_step": next_step})
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(LATEST_POINTER, str(store.run_dir.relative_to(repo_path(Path(".")))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"serial_deploy_executed: {manifest['serial_deploy_executed']}")
    print(f"bpf_attach_executed: {manifest['bpf_attach_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
