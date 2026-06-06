#!/usr/bin/env python3
"""V1161 source/build-only gate for late pm-proxy eSoC trigger probing."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1161-execns-helper-v216-build")
DEFAULT_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")
DEFAULT_OUTPUT_NAME = "a90_android_execns_probe"
DEFAULT_BUILD_SCRIPT = Path("scripts/revalidation/build_android_execns_probe_helper.sh")
DEFAULT_V1160_MANIFEST = Path("tmp/wifi/v1160-pm-esoc-trigger-reconcile/manifest.json")
LATEST_POINTER = Path("tmp/wifi/latest-v1161-execns-helper-v216-build.txt")
HELPER_MARKER = "a90_android_execns_probe v216"
EXPECTED_V1160_DECISION = "v1160-late-per-proxy-esoc-trigger-route-classified"
REQUIRED_SOURCE_STRINGS = (
    'EXECNS_VERSION "a90_android_execns_probe v216"',
    "pm_observer_start_per_proxy_after_mdm_helper_esoc_fd",
    "--pm-observer-start-per-proxy-after-mdm-helper-esoc-fd",
    "late_per_proxy_after_mdm_helper_esoc_fd_requested",
    "late_per_proxy_poll_%02d",
    "per_mgr_subsys_esoc0_count",
    "late-per-proxy-observed-no-lower-publication",
)
REQUIRED_BINARY_STRINGS = (
    HELPER_MARKER,
    "--pm-observer-start-per-proxy-after-mdm-helper-esoc-fd",
    "late_per_proxy_after_mdm_helper_esoc_fd_requested",
    "late_per_proxy_poll_%02d",
    "per_mgr_subsys_esoc0_count",
    "late-per-proxy-observed-no-lower-publication",
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


def build(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    logs = store.mkdir("logs")
    output = store.path(DEFAULT_OUTPUT_NAME)
    result = run_host([str(repo_path(args.build_script)), str(output)], logs / "build.txt")
    if output.exists():
        output.chmod(0o600)
    readelf = run_host(["aarch64-linux-gnu-readelf", "-l", str(output)], logs / "readelf-program.txt") if output.exists() else {}
    dynamic = run_host(["aarch64-linux-gnu-readelf", "-d", str(output)], logs / "readelf-dynamic.txt") if output.exists() else {}
    strings_result = run_host(["strings", str(output)], logs / "strings.txt") if output.exists() else {}
    file_result = run_host(["file", str(output)], logs / "file.txt") if output.exists() else {}
    strings_text = Path(strings_result.get("file", "")).read_text(encoding="utf-8", errors="replace") if strings_result.get("file") else ""
    readelf_text = Path(readelf.get("file", "")).read_text(encoding="utf-8", errors="replace") if readelf.get("file") else ""
    dynamic_text = Path(dynamic.get("file", "")).read_text(encoding="utf-8", errors="replace") if dynamic.get("file") else ""
    return {
        "build": result,
        "readelf": readelf,
        "dynamic": dynamic,
        "strings": strings_result,
        "file": file_result,
        "output": str(output),
        "output_exists": output.exists(),
        "output_size": output.stat().st_size if output.exists() else 0,
        "output_sha256": sha256(output) if output.exists() else "",
        "static_no_interp": output.exists() and "INTERP" not in readelf_text,
        "static_no_dynamic_section": output.exists() and "There is no dynamic section" in dynamic_text,
        "required_binary_strings": {item: item in strings_text for item in REQUIRED_BINARY_STRINGS},
    }


def analyze(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    source = repo_path(args.source)
    source_text = source.read_text(encoding="utf-8", errors="replace") if source.exists() else ""
    v1160 = load_json(args.v1160_manifest)
    analysis: dict[str, Any] = {
        "v1160": {
            "decision": v1160.get("decision", ""),
            "pass": bool(v1160.get("pass")),
            "path": str(repo_path(args.v1160_manifest)),
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
            "name": "v1160-input",
            "status": "pass" if analysis["v1160"]["decision"] == EXPECTED_V1160_DECISION and analysis["v1160"]["pass"] else "blocked",
            "detail": f"decision={analysis['v1160']['decision']} pass={analysis['v1160']['pass']}",
            "next_step": "refresh V1160 before building helper v216",
        },
        {
            "name": "source-strings",
            "status": "pass" if all(analysis["source"]["required_strings"].values()) else "blocked",
            "detail": json.dumps(analysis["source"]["required_strings"], sort_keys=True),
            "next_step": "repair helper source late pm-proxy support",
        },
    ]
    if args.command == "plan":
        rows.append({"name": "plan-only", "status": "pass", "detail": "no build or device command executed", "next_step": "run V1161 build-only gate"})
        return rows
    build_info = analysis["build"]
    rows.extend([
        {
            "name": "build",
            "status": "pass" if (build_info.get("build") or {}).get("rc") == 0 and build_info.get("output_exists") else "blocked",
            "detail": f"rc={(build_info.get('build') or {}).get('rc')} output={build_info.get('output')}",
            "next_step": "fix compile/link errors",
        },
        {
            "name": "static-helper",
            "status": "pass" if build_info.get("static_no_interp") and build_info.get("static_no_dynamic_section") else "blocked",
            "detail": f"no_interp={build_info.get('static_no_interp')} no_dynamic={build_info.get('static_no_dynamic_section')}",
            "next_step": "ensure helper is static before deploy",
        },
        {
            "name": "binary-strings",
            "status": "pass" if all((build_info.get("required_binary_strings") or {}).values()) else "blocked",
            "detail": json.dumps(build_info.get("required_binary_strings") or {}, sort_keys=True),
            "next_step": "repair build artifact or strings validation",
        },
    ])
    return rows


def decide(args: argparse.Namespace, rows: list[dict[str, Any]], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1161-late-per-proxy-helper-build-plan-ready",
            True,
            "plan-only; no build, deploy, device command, PM actor, mdm_helper, CNSS actor, or Wi-Fi action executed",
            "run V1161 build-only gate",
        )
    blockers = [row["name"] for row in rows if row["status"] != "pass"]
    if blockers:
        return ("v1161-late-per-proxy-helper-build-blocked", False, "blocked by " + ", ".join(blockers), "fix blockers before deploy")
    return (
        "v1161-late-per-proxy-helper-build-pass",
        True,
        f"helper v216 built sha256={analysis['build']['output_sha256']}",
        "V1162 should deploy helper v216; V1163 should run bounded late pm-proxy live without Wi-Fi HAL or bring-up",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [[row["name"], row["status"], row["detail"], row["next_step"]] for row in manifest["checks"]]
    build_info = manifest["analysis"].get("build") or {}
    return "\n".join([
        "# V1161 Late pm-proxy Helper Build",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{HELPER_MARKER}`",
        f"- output_sha256: `{build_info.get('output_sha256', '')}`",
        f"- output_size: `{build_info.get('output_size', 0)}`",
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
    parser.add_argument("--build-script", type=Path, default=DEFAULT_BUILD_SCRIPT)
    parser.add_argument("--v1160-manifest", type=Path, default=DEFAULT_V1160_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = analyze(args, store)
    row_data = checks(args, analysis)
    decision, passed, reason, next_step = decide(args, row_data, analysis)
    manifest = {
        "cycle": "v1161",
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
