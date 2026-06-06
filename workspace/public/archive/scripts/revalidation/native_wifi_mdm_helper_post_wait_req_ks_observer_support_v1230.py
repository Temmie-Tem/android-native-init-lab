#!/usr/bin/env python3
"""V1230 source/build-only gate for mdm_helper post-WAIT_FOR_REQ ks observer."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1230-execns-helper-v256-build")
DEFAULT_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_OUTPUT_NAME = "a90_android_execns_probe"
DEFAULT_STAGE3_BINARY = Path("stage3/linux_init/helpers/a90_android_execns_probe_v256")
DEFAULT_BUILD_SCRIPT = Path("scripts/revalidation/build_android_execns_probe_helper.sh")
DEFAULT_V1229_MANIFEST = Path("tmp/wifi/v1229-esoc-wait-req-ks-mhi-contract/manifest.json")
LATEST_POINTER = Path("tmp/wifi/latest-v1230-execns-helper-v256-build.txt")
HELPER_MARKER = "a90_android_execns_probe v256"
EXPECTED_V1229_DECISION = "v1229-esoc-wait-req-ks-mhi-contract-classified"
REQUIRED_SOURCE_STRINGS = (
    'EXECNS_VERSION "a90_android_execns_probe v256"',
    "pm_observer_mdm_helper_post_wait_req_ks_observer",
    "--pm-observer-mdm-helper-post-wait-req-ks-observer",
    "run_mdm_helper_post_wait_req_ks_observer",
    "post_wait_req.begin=1",
    "post_wait_req.transition_detected=%d",
    "post_wait_req.ks_process_count=%d",
    "post_wait_req.mhi_pipe_fd_count=%d",
    "post_wait_req.esoc_notify_attempted=0",
    "post_wait_req.boot_done_attempted=0",
)
REQUIRED_BINARY_STRINGS = (
    HELPER_MARKER,
    "--pm-observer-mdm-helper-post-wait-req-ks-observer",
    "post_wait_req.begin=1",
    "post_wait_req.transition_detected=%d",
    "post_wait_req.ks_process_count=%d",
    "post_wait_req.mhi_pipe_fd_count=%d",
    "post_wait_req.esoc_notify_attempted=0",
    "post_wait_req.boot_done_attempted=0",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def run_host(command: list[str], output_file: Path, timeout: float = 180.0) -> dict[str, Any]:
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


def inspect_binary(path: Path, store: EvidenceStore, label: str) -> dict[str, Any]:
    logs = store.mkdir("logs")
    resolved = repo_path(path)
    if not resolved.exists():
        return {"path": str(resolved), "exists": False}
    readelf = run_host(["aarch64-linux-gnu-readelf", "-l", str(resolved)], logs / f"{label}-readelf-program.txt")
    dynamic = run_host(["aarch64-linux-gnu-readelf", "-d", str(resolved)], logs / f"{label}-readelf-dynamic.txt")
    strings_result = run_host(["strings", str(resolved)], logs / f"{label}-strings.txt")
    file_result = run_host(["file", str(resolved)], logs / f"{label}-file.txt")
    strings_text = Path(strings_result["file"]).read_text(encoding="utf-8", errors="replace")
    readelf_text = Path(readelf["file"]).read_text(encoding="utf-8", errors="replace")
    dynamic_text = Path(dynamic["file"]).read_text(encoding="utf-8", errors="replace")
    return {
        "path": str(resolved),
        "exists": True,
        "size": resolved.stat().st_size,
        "sha256": sha256(resolved),
        "readelf": readelf,
        "dynamic": dynamic,
        "strings": strings_result,
        "file": file_result,
        "static_no_interp": "INTERP" not in readelf_text,
        "static_no_dynamic_section": "There is no dynamic section" in dynamic_text,
        "required_binary_strings": {item: item in strings_text for item in REQUIRED_BINARY_STRINGS},
    }


def build(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    logs = store.mkdir("logs")
    output = store.path(DEFAULT_OUTPUT_NAME)
    result = run_host([str(repo_path(args.build_script)), str(output)], logs / "build.txt")
    if output.exists():
        output.chmod(0o600)
    return {
        "build": result,
        "output": inspect_binary(output, store, "built-helper"),
        "stage3": inspect_binary(args.stage3_binary, store, "stage3-helper"),
    }


def analyze(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    source = repo_path(args.source)
    source_text = source.read_text(encoding="utf-8", errors="replace") if source.exists() else ""
    v1229 = load_json(args.v1229_manifest)
    analysis: dict[str, Any] = {
        "v1229": {
            "decision": v1229.get("decision", ""),
            "pass": bool(v1229.get("pass")),
            "path": str(repo_path(args.v1229_manifest)),
        },
        "source": {
            "path": str(source),
            "exists": source.exists(),
            "required_strings": {item: item in source_text for item in REQUIRED_SOURCE_STRINGS},
        },
        "build": {},
    }
    if args.command == "run":
        analysis["build"] = build(args, store)
    return analysis


def checks(args: argparse.Namespace, analysis: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {
            "name": "v1229-input",
            "status": "pass" if analysis["v1229"]["decision"] == EXPECTED_V1229_DECISION and analysis["v1229"]["pass"] else "blocked",
            "detail": f"decision={analysis['v1229']['decision']} pass={analysis['v1229']['pass']}",
            "next_step": "refresh V1229 before building helper v256",
        },
        {
            "name": "source-strings",
            "status": "pass" if all(analysis["source"]["required_strings"].values()) else "blocked",
            "detail": json.dumps(analysis["source"]["required_strings"], sort_keys=True),
            "next_step": "repair helper source post-WAIT_FOR_REQ observer support",
        },
    ]
    if args.command == "plan":
        rows.append({"name": "plan-only", "status": "pass", "detail": "no build or device command executed", "next_step": "run V1230 build-only gate"})
        return rows
    build_info = analysis["build"]
    built = build_info.get("output") or {}
    stage3 = build_info.get("stage3") or {}
    rows.extend([
        {
            "name": "build",
            "status": "pass" if (build_info.get("build") or {}).get("rc") == 0 and built.get("exists") else "blocked",
            "detail": f"rc={(build_info.get('build') or {}).get('rc')} output={built.get('path')}",
            "next_step": "fix compile/link errors",
        },
        {
            "name": "static-built-helper",
            "status": "pass" if built.get("static_no_interp") and built.get("static_no_dynamic_section") else "blocked",
            "detail": f"no_interp={built.get('static_no_interp')} no_dynamic={built.get('static_no_dynamic_section')}",
            "next_step": "ensure built helper is static before deploy",
        },
        {
            "name": "built-binary-strings",
            "status": "pass" if all((built.get("required_binary_strings") or {}).values()) else "blocked",
            "detail": json.dumps(built.get("required_binary_strings") or {}, sort_keys=True),
            "next_step": "repair built helper strings",
        },
        {
            "name": "stage3-binary",
            "status": "pass" if stage3.get("exists") and stage3.get("sha256") == built.get("sha256") else "blocked",
            "detail": f"exists={stage3.get('exists')} sha={stage3.get('sha256')} built_sha={built.get('sha256')}",
            "next_step": "copy built helper to stage3/linux_init/helpers/a90_android_execns_probe_v256",
        },
        {
            "name": "static-stage3-helper",
            "status": "pass" if stage3.get("static_no_interp") and stage3.get("static_no_dynamic_section") else "blocked",
            "detail": f"no_interp={stage3.get('static_no_interp')} no_dynamic={stage3.get('static_no_dynamic_section')}",
            "next_step": "replace stage3 helper with static aarch64 artifact",
        },
    ])
    return rows


def decide(args: argparse.Namespace, rows: list[dict[str, Any]], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1230-post-wait-req-ks-observer-build-plan-ready",
            True,
            "plan-only; no build, deploy, device command, eSoC ioctl, PM actor, mdm_helper, CNSS actor, or Wi-Fi action executed",
            "run V1230 build-only gate",
        )
    blockers = [row["name"] for row in rows if row["status"] != "pass"]
    if blockers:
        return ("v1230-post-wait-req-ks-observer-build-blocked", False, "blocked by " + ", ".join(blockers), "fix blockers before deploy")
    return (
        "v1230-post-wait-req-ks-observer-build-pass",
        True,
        f"helper v256 built sha256={analysis['build']['output']['sha256']}",
        "V1231 should deploy helper v256 only; V1232 should run the bounded post-WAIT_FOR_REQ observer without Wi-Fi HAL or bring-up",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[row["name"], row["status"], row["detail"], row["next_step"]] for row in manifest["checks"]]
    build_info = manifest["analysis"].get("build") or {}
    built = build_info.get("output") or {}
    stage3 = build_info.get("stage3") or {}
    return "\n".join([
        "# V1230 mdm_helper Post-WAIT_FOR_REQ ks Observer Build",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{HELPER_MARKER}`",
        f"- built_sha256: `{built.get('sha256', '')}`",
        f"- stage3_sha256: `{stage3.get('sha256', '')}`",
        f"- output_size: `{built.get('size', 0)}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], rows),
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--stage3-binary", type=Path, default=DEFAULT_STAGE3_BINARY)
    parser.add_argument("--build-script", type=Path, default=DEFAULT_BUILD_SCRIPT)
    parser.add_argument("--v1229-manifest", type=Path, default=DEFAULT_V1229_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = analyze(args, store)
    row_data = checks(args, analysis)
    decision, passed, reason, next_step = decide(args, row_data, analysis)
    manifest = {
        "cycle": "v1230",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "analysis": analysis,
        "checks": row_data,
        "device_commands_executed": False,
        "deploy_executed": False,
        "tracefs_write_executed": False,
        "esoc_ioctl_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "mdm_helper_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "reboot_executed": False,
        "partition_write_executed": False,
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
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
