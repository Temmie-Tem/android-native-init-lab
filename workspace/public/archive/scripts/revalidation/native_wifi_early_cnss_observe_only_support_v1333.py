#!/usr/bin/env python3
"""V1333 source/build-only gate for early-CNSS observe-only support."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1333-early-cnss-observe-only-support")
DEFAULT_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_STAGE3_BINARY = Path("stage3/linux_init/helpers/a90_android_execns_probe_v277")
DEFAULT_BUILD_SCRIPT = Path("scripts/revalidation/build_android_execns_probe_helper.sh")
LATEST_POINTER = Path("tmp/wifi/latest-v1333-early-cnss-observe-only-support.txt")
HELPER_MARKER = "a90_android_execns_probe v277"
REQUIRED_SOURCE_STRINGS = (
    'EXECNS_VERSION "a90_android_execns_probe v277"',
    "observe-only|wlfw-precondition",
    'streq(gate, "observe-only")',
    "const bool observe_only_gate =",
    "const bool wlfw_trigger_ready =",
    "cnss_before_esoc.observe_only_gate=%d",
    "cnss_before_esoc.wlfw_trigger_ready=%d",
    "cnss_before_esoc.result=wlfw-precondition-observed-observe-only-no-open",
    "observe-only-gate-kept-subsys-esoc0-closed",
)
REQUIRED_BINARY_STRINGS = (
    HELPER_MARKER,
    "observe-only|wlfw-precondition",
    "cnss_before_esoc.observe_only_gate=%d",
    "cnss_before_esoc.wlfw_trigger_ready=%d",
    "cnss_before_esoc.result=wlfw-precondition-observed-observe-only-no-open",
    "observe-only-gate-kept-subsys-esoc0-closed",
    "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--stage3-binary", type=Path, default=DEFAULT_STAGE3_BINARY)
    parser.add_argument("--build-script", type=Path, default=DEFAULT_BUILD_SCRIPT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_host(command: list[str], output_file: Path, timeout: float = 240.0) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [str(item) for item in command],
            cwd=repo_path("."),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        write_private_text(output_file, result.stdout)
        return {"command": [str(item) for item in command], "rc": result.returncode, "timeout": False, "file": str(output_file)}
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        write_private_text(output_file, output + "\n[TIMEOUT]\n")
        return {"command": [str(item) for item in command], "rc": None, "timeout": True, "file": str(output_file)}


def inspect_binary(path: Path, store: EvidenceStore) -> dict[str, Any]:
    logs = store.mkdir("logs")
    full = repo_path(path)
    if not full.exists():
        return {"path": str(full), "exists": False}
    readelf = run_host(["aarch64-linux-gnu-readelf", "-l", str(full)], logs / "readelf-program.txt")
    dynamic = run_host(["aarch64-linux-gnu-readelf", "-d", str(full)], logs / "readelf-dynamic.txt")
    strings_result = run_host(["strings", str(full)], logs / "strings.txt")
    file_result = run_host(["file", str(full)], logs / "file.txt")
    strings_text = Path(strings_result["file"]).read_text(encoding="utf-8", errors="replace")
    readelf_text = Path(readelf["file"]).read_text(encoding="utf-8", errors="replace")
    dynamic_text = Path(dynamic["file"]).read_text(encoding="utf-8", errors="replace")
    return {
        "path": str(full),
        "exists": True,
        "size": full.stat().st_size,
        "sha256": sha256(full),
        "file": file_result,
        "readelf": readelf,
        "dynamic": dynamic,
        "strings": strings_result,
        "static_no_interp": "INTERP" not in readelf_text,
        "static_no_dynamic_section": "There is no dynamic section" in dynamic_text,
        "required_binary_strings": {item: item in strings_text for item in REQUIRED_BINARY_STRINGS},
    }


def analyze(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    source = repo_path(args.source)
    source_text = source.read_text(encoding="utf-8", errors="replace") if source.exists() else ""
    build: dict[str, Any] = {}
    if args.command == "run":
        logs = store.mkdir("logs")
        build_result = run_host([str(repo_path(args.build_script)), str(repo_path(args.stage3_binary))], logs / "build.txt")
        build = {"build": build_result, "stage3": inspect_binary(args.stage3_binary, store)}
    return {
        "source": {
            "path": str(source),
            "exists": source.exists(),
            "required_strings": {item: item in source_text for item in REQUIRED_SOURCE_STRINGS},
        },
        "build": build,
    }


def checks(command: str, analysis: dict[str, Any]) -> list[dict[str, str]]:
    rows = [
        {
            "name": "source-strings",
            "status": "pass" if all(analysis["source"]["required_strings"].values()) else "blocked",
            "detail": json.dumps(analysis["source"]["required_strings"], sort_keys=True),
            "next_step": "repair observe-only helper source support",
        },
        {
            "name": "plan-live-exclusion",
            "status": "pass",
            "detail": "source/build-only; no device command or deploy is performed",
            "next_step": "run build-only gate",
        },
    ]
    if command == "plan":
        return rows
    build = analysis["build"]
    stage3 = build.get("stage3") or {}
    rows.extend([
        {
            "name": "build",
            "status": "pass" if (build.get("build") or {}).get("rc") == 0 and stage3.get("exists") else "blocked",
            "detail": f"rc={(build.get('build') or {}).get('rc')} output={stage3.get('path')}",
            "next_step": "fix compile/link errors",
        },
        {
            "name": "static-stage3-helper",
            "status": "pass" if stage3.get("static_no_interp") and stage3.get("static_no_dynamic_section") else "blocked",
            "detail": f"no_interp={stage3.get('static_no_interp')} no_dynamic={stage3.get('static_no_dynamic_section')}",
            "next_step": "ensure helper is static aarch64",
        },
        {
            "name": "binary-strings",
            "status": "pass" if all((stage3.get("required_binary_strings") or {}).values()) else "blocked",
            "detail": json.dumps(stage3.get("required_binary_strings") or {}, sort_keys=True),
            "next_step": "repair built helper marker strings",
        },
    ])
    return rows


def decide(command: str, rows: list[dict[str, str]], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v1333-early-cnss-observe-only-build-plan-ready",
            True,
            "plan-only",
            "run V1333 source/build-only gate",
        )
    blockers = [row["name"] for row in rows if row["status"] != "pass"]
    if blockers:
        return (
            "v1333-early-cnss-observe-only-build-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "fix blockers before deploy",
        )
    stage3 = analysis["build"]["stage3"]
    return (
        "v1333-early-cnss-observe-only-build-pass",
        True,
        f"helper v277 built sha256={stage3['sha256']}",
        "V1334 should deploy helper v277 only; V1335 should run observe-only early-CNSS WLFW parity live",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[row["name"], row["status"], row["detail"], row["next_step"]] for row in manifest["checks"]]
    stage3 = (manifest["analysis"].get("build") or {}).get("stage3") or {}
    return "\n".join([
        "# V1333 Early-CNSS Observe-only Build",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{HELPER_MARKER}`",
        f"- stage3_sha256: `{stage3.get('sha256', '')}`",
        f"- output_size: `{stage3.get('size', 0)}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], rows),
        "",
        "## Added Helper Surface",
        "",
        "- helper marker: `a90_android_execns_probe v277`",
        "- new `--subsys-trigger-gate observe-only` value for `wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture`",
        "- output contract: `cnss_before_esoc.observe_only_gate`, `cnss_before_esoc.wlfw_trigger_ready`, and `wlfw-precondition-observed-observe-only-no-open`",
        "- safety intent: observe early CNSS/WLFW state without opening `/dev/subsys_esoc0`, even if a WLFW precondition appears",
        "",
        "## Safety",
        "",
        "- source/build-only; no deploy or device command",
        "- no PM/CNSS actor start, eSoC open/ioctl, PMIC write, GPIO request/hold, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = analyze(args, store)
    rows = checks(args.command, analysis)
    decision, passed, reason, next_step = decide(args.command, rows, analysis)
    manifest = {
        "cycle": "v1333",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "analysis": analysis,
        "checks": rows,
        "device_commands_executed": False,
        "deploy_executed": False,
        "gpio_line_request_executed": False,
        "pmic_write_executed": False,
        "esoc_ioctl_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
