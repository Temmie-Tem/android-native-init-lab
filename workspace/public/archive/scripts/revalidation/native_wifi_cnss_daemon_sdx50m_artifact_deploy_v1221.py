#!/usr/bin/env python3
"""V1221 deploy-only gate for the private patched cnss-daemon SDX50M artifact.

The deploy path writes only ``/cache/bin/cnss-daemon.sdx50m``.  It does not
execute the artifact, start daemons, touch Wi-Fi credentials, scan/connect,
configure routes, or perform external network tests.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore
from a90ctl import encode_cmdv1_line, run_cmdv1_command
import wifi_execns_helper_v12_deploy_preflight as deploy_base


DEFAULT_OUT_DIR = Path("tmp/wifi/v1221-cnss-daemon-sdx50m-artifact-deploy")
DEFAULT_LOCAL_ARTIFACT = Path(
    "tmp/wifi/v1220-cnss-daemon-sdx50m-patch/artifacts/cnss-daemon.sdx50m"
)
DEFAULT_REMOTE_ARTIFACT = "/cache/bin/cnss-daemon.sdx50m"
DEFAULT_ARTIFACT_SHA256 = (
    "784fd7bd9b602d8e1f94c9ceef977845909f452611025c40fda589d0e57de5fd"
)
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
DEFAULT_DEVICE_IP = "192.168.7.2"
DEFAULT_TRANSFER_PORT = 18086
DEFAULT_SERIAL_CHUNK_SIZE = 1800
DEPLOY_LABEL = "v1221-cnss-daemon-sdx50m"
APPROVAL_PHRASE = (
    "approve v1221 deploy private cnss-daemon sdx50m artifact only; "
    "no daemon start and no Wi-Fi bring-up"
)


@dataclass
class StepResult:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_host(command: list[str], *, timeout: float = 30.0) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--local-artifact", type=Path, default=DEFAULT_LOCAL_ARTIFACT)
    parser.add_argument("--remote-artifact", default=DEFAULT_REMOTE_ARTIFACT)
    parser.add_argument("--artifact-sha256", default=DEFAULT_ARTIFACT_SHA256)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--device-ip", default=DEFAULT_DEVICE_IP)
    parser.add_argument("--transfer-port", type=int, default=DEFAULT_TRANSFER_PORT)
    parser.add_argument(
        "--transfer-method",
        choices=("auto", "ncm", "serial"),
        default="auto",
    )
    parser.add_argument("--serial-staging-dir", default="/cache/a90-runtime/bin")
    parser.add_argument("--serial-chunk-size", type=int, default=DEFAULT_SERIAL_CHUNK_SIZE)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._+-" else "-" for ch in value).strip("-") or "capture"


def capture_native(args: argparse.Namespace,
                   store: EvidenceStore,
                   name: str,
                   command: list[str],
                   *,
                   timeout: float | None = None,
                   allow_error: bool = True) -> StepResult:
    record = run_capture(args, name, command, timeout=timeout or args.timeout)
    text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text)
    ok = record.ok if not allow_error else True
    return StepResult(name, record.command, ok, record.rc, record.status, record.duration_sec, rel, record.error)


def local_artifact_info(args: argparse.Namespace) -> dict[str, Any]:
    path = repo_path(args.local_artifact)
    info: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "sha256": "",
        "size": 0,
        "file_output": "",
    }
    if not path.exists():
        return info
    info["sha256"] = sha256_file(path)
    info["size"] = path.stat().st_size
    rc, output = run_host(["file", str(path)], timeout=10)
    info["file_output"] = output.strip() if rc == 0 else output.strip()
    return info


def run_read_only(args: argparse.Namespace, store: EvidenceStore) -> list[StepResult]:
    return [
        capture_native(args, store, "version", ["version"], timeout=10.0),
        capture_native(args, store, "status", ["status"], timeout=10.0),
        capture_native(args, store, "selftest", ["selftest"], timeout=10.0),
        capture_native(args, store, "netservice-status", ["netservice", "status"], timeout=10.0),
        capture_native(args, store, "stat-artifact", ["stat", args.remote_artifact], timeout=10.0),
        capture_native(
            args,
            store,
            "sha-artifact",
            ["run", args.toybox, "sha256sum", args.remote_artifact],
            timeout=15.0,
        ),
        capture_native(
            args,
            store,
            "ps",
            ["run", args.toybox, "ps", "-A", "-o", "pid,stat,comm,args"],
            timeout=20.0,
        ),
        capture_native(args, store, "proc-net-dev", ["cat", "/proc/net/dev"], timeout=10.0),
    ]


def step_text(store: EvidenceStore, steps: list[StepResult], name: str) -> str:
    for step in steps:
        if step.name == name:
            return store.path(step.file).read_text(encoding="utf-8", errors="replace")
    return ""


def run_device(args: argparse.Namespace, argv: list[str], timeout: float = 30.0) -> tuple[bool, str, int | None, str]:
    try:
        result = run_cmdv1_command(args.host, args.port, timeout, argv, retry_unsafe=False)
    except Exception as exc:  # noqa: BLE001 - deploy evidence keeps failure text
        return False, str(exc) + "\n", None, "missing"
    return result.rc == 0 and result.status == "ok", result.text, result.rc, result.status


def run_serial_install(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    local_path = repo_path(args.local_artifact)
    target = args.remote_artifact
    target_dir = str(Path(target).parent)
    target_name = Path(target).name
    stamp = f"{int(time.time())}.{os.getpid()}"
    staging_dir = args.serial_staging_dir.rstrip("/")
    staging = f"{staging_dir}/.{target_name}.{DEPLOY_LABEL}.{stamp}.uu"
    tmp_target = f"{target_dir}/.{target_name}.tmp.{stamp}"
    transcript: list[str] = []
    chunks_written = 0

    data = local_path.read_bytes()
    encoded = deploy_base.uuencode_bytes(data, name=Path(tmp_target).name, mode=0o700)
    chunk_size = max(256, min(args.serial_chunk_size, deploy_base.SERIAL_MAX_REQUESTED_CHUNK_SIZE))
    line_check = deploy_base.serial_append_line_check(staging, encoded, chunk_size)

    def step(name: str, argv: list[str], timeout: float = 30.0, allow_error: bool = False) -> str:
        ok, text, rc, status = run_device(args, argv, timeout)
        transcript.append(f"## {name}\nargv={argv!r}\nok={ok} rc={rc} status={status}\n{text}\n")
        if not ok and not allow_error:
            raise RuntimeError(f"serial artifact deploy step failed: {name} rc={rc} status={status}\n{text}")
        return text

    if not line_check["ok"]:
        message = (
            f"serial chunk size unsafe: chunk_size={chunk_size} "
            f"max_cmdv1_line_bytes={line_check['max_cmdv1_line_bytes']}"
        )
        store.write_text("host/serial-install-artifact.txt", message + "\n")
        return {**line_check, "method": "serial", "ok": False, "rc": 1, "file": "host/serial-install-artifact.txt", "error": message}

    try:
        step("mkdir-target-dir", ["mkdir", target_dir], allow_error=True)
        step("mkdir-staging-dir", ["mkdir", staging_dir], allow_error=True)
        step("rm-staging", ["run", args.toybox, "rm", "-f", staging], allow_error=True)
        step("rm-tmp", ["run", args.toybox, "rm", "-f", tmp_target], allow_error=True)
        for offset in range(0, len(encoded), chunk_size):
            chunk = encoded[offset:offset + chunk_size]
            step(f"append-{chunks_written:04d}", ["appendfile", staging, chunk], timeout=20.0)
            chunks_written += 1
        step("uudecode", ["run", args.toybox, "uudecode", "-o", tmp_target, staging], timeout=60.0)
        step("chmod", ["run", args.toybox, "chmod", "700", tmp_target])
        sha_text = step("sha-tmp", ["run", args.toybox, "sha256sum", tmp_target])
        if args.artifact_sha256 not in sha_text:
            raise RuntimeError(f"tmp artifact sha256 mismatch, expected {args.artifact_sha256}\n{sha_text}")
        step("mv-target", ["run", args.toybox, "mv", "-f", tmp_target, target])
        target_sha = step("sha-target", ["run", args.toybox, "sha256sum", target])
        if args.artifact_sha256 not in target_sha:
            raise RuntimeError(f"target artifact sha256 mismatch, expected {args.artifact_sha256}\n{target_sha}")
        step("rm-staging-post", ["run", args.toybox, "rm", "-f", staging], allow_error=True)
    except Exception as exc:
        run_device(args, ["run", args.toybox, "rm", "-f", tmp_target], timeout=20.0)
        store.write_text("host/serial-install-artifact.txt", "\n".join(transcript))
        return {
            **line_check,
            "method": "serial",
            "ok": False,
            "rc": 1,
            "file": "host/serial-install-artifact.txt",
            "error": str(exc),
            "chunks_written": chunks_written,
        }

    store.write_text("host/serial-install-artifact.txt", "\n".join(transcript))
    return {
        **line_check,
        "method": "serial",
        "ok": True,
        "rc": 0,
        "file": "host/serial-install-artifact.txt",
        "chunks_written": chunks_written,
    }


def run_ncm_install(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    command = [
        sys.executable,
        str(repo_path(deploy_base.TCPCTL_SCRIPT)),
        "--bridge-host",
        args.host,
        "--bridge-port",
        str(args.port),
        "--device-ip",
        args.device_ip,
        "--device-binary",
        args.remote_artifact,
        "--toybox",
        args.toybox,
        "install",
        "--local-binary",
        str(repo_path(args.local_artifact)),
        "--transfer-port",
        str(args.transfer_port),
    ]
    rc, output = run_host(command, timeout=150)
    store.write_text("host/ncm-install-artifact.txt", output)
    return {"method": "ncm", "command": " ".join(command), "rc": rc, "ok": rc == 0, "file": "host/ncm-install-artifact.txt"}


def run_install(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    if args.transfer_method == "serial":
        return run_serial_install(args, store)
    if args.transfer_method == "auto":
        rc, _output = run_host(["ping", "-c", "1", "-W", "1", args.device_ip], timeout=3)
        if rc != 0:
            return run_serial_install(args, store)
    return run_ncm_install(args, store)


def decide(args: argparse.Namespace,
           local: dict[str, Any],
           steps: list[StepResult],
           deploy_result: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    version = step_text(args._store, steps, "version") if hasattr(args, "_store") else ""
    status = step_text(args._store, steps, "status") if hasattr(args, "_store") else ""
    selftest = step_text(args._store, steps, "selftest") if hasattr(args, "_store") else ""
    sha_text = step_text(args._store, steps, "sha-artifact") if hasattr(args, "_store") else ""
    ps_text = step_text(args._store, steps, "ps") if hasattr(args, "_store") else ""
    netdev_text = step_text(args._store, steps, "proc-net-dev") if hasattr(args, "_store") else ""
    managers = [line for line in ps_text.splitlines() if any(name in line for name in ("servicemanager", "hwservicemanager", "vndservicemanager"))]
    wifi_links = [line for line in netdev_text.splitlines() if "wlan" in line.lower() or "p2p" in line.lower()]

    if not local["exists"] or local["sha256"] != args.artifact_sha256:
        return ("v1221-artifact-deploy-local-blocked", False, f"local artifact sha={local['sha256'] or 'missing'}", "regenerate V1220 patched artifact")
    if args.command == "plan":
        return ("v1221-artifact-deploy-plan-ready", True, "plan-only; no device command executed", "run preflight")
    if args.expect_version not in version:
        return ("v1221-artifact-deploy-version-warn", False, "native version did not match expected v724", "verify device boot baseline before writing /cache")
    if "fail=0" not in status or "fail=0" not in selftest:
        return ("v1221-artifact-deploy-native-blocked", False, "status/selftest did not both report fail=0", "fix native health before deploy")
    if managers:
        return ("v1221-artifact-deploy-process-blocked", False, f"service-manager processes active: {len(managers)}", "cleanup active Android-service experiment first")
    if wifi_links:
        return ("v1221-artifact-deploy-wifi-active-blocked", False, f"Wi-Fi link surface active: {len(wifi_links)}", "do not deploy during active Wi-Fi bring-up")
    if args.command == "preflight":
        remote_current = args.artifact_sha256 in sha_text
        return (
            "v1221-artifact-deploy-preflight-ready",
            True,
            f"preflight passed; remote_current={remote_current}",
            "run approved deploy if remote artifact is absent or stale",
        )
    if not approved(args):
        return ("v1221-artifact-deploy-approval-required", True, "exact deploy approval required; no write executed", "rerun with exact approval phrase")
    if deploy_result and deploy_result.get("ok"):
        return ("v1221-artifact-deploy-pass", True, "private cnss-daemon SDX50M artifact deployed and sha verified", "run V1221 bounded private-cnss-daemon live observer")
    return ("v1221-artifact-deploy-failed", False, f"deploy failed: {(deploy_result or {}).get('error', '')}", "inspect deploy transcript")


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [[s["name"], s["ok"], s["rc"], s["status"], s["file"]] for s in manifest["steps"]]
    lines = [
        "# V1221 Private CNSS Daemon SDX50M Artifact Deploy",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Steps",
        "",
        markdown_table(["step", "ok", "rc", "status", "file"], step_rows) if step_rows else "- none",
        "",
    ]
    if manifest.get("deploy_result"):
        lines.extend([
            "## Deploy Result",
            "",
            f"- method: `{manifest['deploy_result'].get('method')}`",
            f"- ok: `{manifest['deploy_result'].get('ok')}`",
            f"- rc: `{manifest['deploy_result'].get('rc')}`",
            f"- file: `{manifest['deploy_result'].get('file')}`",
            "",
        ])
    return "\n".join(lines)


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    setattr(args, "_store", store)
    local = local_artifact_info(args)
    steps: list[StepResult] = []
    deploy_result: dict[str, Any] | None = None
    device_mutations = False
    if args.command != "plan":
        steps = run_read_only(args, store)
        sha_text = step_text(store, steps, "sha-artifact")
        remote_current = args.artifact_sha256 in sha_text
        if args.command == "run" and approved(args) and not remote_current:
            deploy_result = run_install(args, store)
            device_mutations = True
        elif args.command == "run" and approved(args):
            deploy_result = {"method": "skip", "ok": True, "rc": 0, "file": "", "skipped": True}
    decision, passed, reason, next_step = decide(args, local, steps, deploy_result)
    manifest = {
        "cycle": "v1221-artifact-deploy",
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "local_artifact": local,
        "remote_artifact": args.remote_artifact,
        "artifact_expected_sha256": args.artifact_sha256,
        "steps": [asdict(step) for step in steps],
        "deploy_result": deploy_result,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "device_mutations": device_mutations,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "explicitly_not_approved": [
            "execute patched cnss-daemon artifact",
            "start service-manager/CNSS/Wi-Fi HAL/wificond/supplicant",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
            "partition write, firmware mutation, boot image write",
        ],
    }
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
