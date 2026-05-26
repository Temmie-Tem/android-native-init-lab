#!/usr/bin/env python3
"""V1076 build-only PM-service uprobe/BPF counter helper gate."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1076-pm-service-uprobe-helper-build")
DEFAULT_SOURCE = Path("stage3/linux_init/helpers/a90_pm_service_uprobe_counter.c")
DEFAULT_OUTPUT_NAME = "a90_pm_service_uprobe_counter-aarch64-static"
DEFAULT_V1075_MANIFEST = Path("tmp/wifi/v1075-pm-service-uprobe-host-classifier/manifest.json")
HELPER_MARKER = "a90_pm_service_uprobe_counter v1076"
SAFETY_STRINGS = (
    "--check-only",
    "--allow-tracefs-write",
    "--allow-attach",
    "--allow-child-command",
    "result=check-only",
    "result=uprobe-count-pass",
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def repo_path(path: Path | str) -> Path:
    path = Path(path)
    return path if path.is_absolute() else Path.cwd() / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--v1075-manifest", type=Path, default=DEFAULT_V1075_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_host(command: list[str], output_file: Path, timeout: float = 120.0) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [str(item) for item in command],
            cwd=repo_path(Path(".")),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        write_private_text(output_file, result.stdout)
        return {
            "command": [str(item) for item in command],
            "rc": result.returncode,
            "timeout": False,
            "output_file": str(output_file),
        }
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        write_private_text(output_file, output + "\n[TIMEOUT]\n")
        return {
            "command": [str(item) for item in command],
            "rc": None,
            "timeout": True,
            "output_file": str(output_file),
        }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(lines)


def candidate_event_specs(v1075: dict[str, Any]) -> list[str]:
    specs: list[str] = []
    for candidate in v1075.get("candidate_uprobes", []):
        offset = candidate.get("offset")
        label = candidate.get("label")
        aligned = candidate.get("aligned4")
        if isinstance(offset, str) and isinstance(label, str) and aligned:
            safe_label = label.replace("-", "_")
            specs.append(f"{safe_label}:{offset}")
    return specs


def build(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    logs = store.mkdir("logs")
    source = repo_path(args.source)
    output = store.path(DEFAULT_OUTPUT_NAME)
    compile_cmd = [
        "aarch64-linux-gnu-gcc",
        "-static",
        "-O2",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-o",
        str(output),
        str(source),
    ]
    compile_result = run_host(compile_cmd, logs / "compile.txt")
    if output.exists():
        output.chmod(0o600)
    strip_result = {"command": [], "rc": None, "timeout": False, "output_file": ""}
    if compile_result["rc"] == 0 and output.exists():
        strip_result = run_host(["aarch64-linux-gnu-strip", str(output)], logs / "strip.txt")
    readelf_header = run_host(["aarch64-linux-gnu-readelf", "-h", str(output)], logs / "readelf-header.txt") if output.exists() else {}
    readelf_program = run_host(["aarch64-linux-gnu-readelf", "-l", str(output)], logs / "readelf-program.txt") if output.exists() else {}
    strings = run_host(["strings", str(output)], logs / "strings.txt") if output.exists() else {}
    program_text = Path(readelf_program.get("output_file", "")).read_text(encoding="utf-8", errors="replace") if readelf_program.get("output_file") else ""
    strings_text = Path(strings.get("output_file", "")).read_text(encoding="utf-8", errors="replace") if strings.get("output_file") else ""
    return {
        "source": str(source),
        "source_exists": source.exists(),
        "output": str(output),
        "output_exists": output.exists(),
        "output_size": output.stat().st_size if output.exists() else 0,
        "output_sha256": sha256(output) if output.exists() else "",
        "compile": compile_result,
        "strip": strip_result,
        "readelf_header": readelf_header,
        "readelf_program": readelf_program,
        "strings": strings,
        "static_no_interp": output.exists() and "INTERP" not in program_text,
        "marker_present": HELPER_MARKER in strings_text,
        "safety_strings": {text: text in strings_text for text in SAFETY_STRINGS},
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(manifest: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    analysis = manifest["analysis"]
    v1075 = analysis["v1075"]
    add_check(
        checks,
        "v1075-input",
        "pass" if v1075["decision"] == "v1075-pm-service-uprobe-host-classified" and v1075["pass"] else "blocked",
        "blocker",
        f"decision={v1075['decision']} pass={v1075['pass']}",
        "complete V1075 before building the uprobe helper",
    )
    add_check(
        checks,
        "event-specs",
        "pass" if len(analysis["candidate_event_specs"]) >= 4 else "blocked",
        "blocker",
        f"count={len(analysis['candidate_event_specs'])}",
        "repair V1075 candidate extraction",
    )
    if manifest["command"] == "plan":
        add_check(checks, "plan-only", "pass", "info", "no build or device command executed", "run V1076 build-only gate")
        return checks
    build_info = analysis["build"]
    add_check(checks, "compile", "pass" if build_info.get("compile", {}).get("rc") == 0 else "blocked", "blocker", f"rc={build_info.get('compile', {}).get('rc')}", "fix helper compile errors")
    add_check(checks, "static-no-interp", "pass" if build_info.get("static_no_interp") else "blocked", "blocker", f"static_no_interp={build_info.get('static_no_interp')}", "ensure helper is static before deploy")
    add_check(checks, "marker", "pass" if build_info.get("marker_present") else "blocked", "blocker", f"marker_present={build_info.get('marker_present')}", "preserve V1076 marker")
    safety = build_info.get("safety_strings") or {}
    missing = [key for key, present in safety.items() if not present]
    add_check(checks, "safety-strings", "pass" if not missing else "blocked", "blocker", f"missing={missing}", "preserve check-only and explicit allow gates")
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v1076-pm-service-uprobe-helper-build-plan-ready",
            True,
            "plan-only; no build, device command, tracefs write, BPF attach, or Wi-Fi action executed",
            "run V1076 build-only gate",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v1076-pm-service-uprobe-helper-build-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "fix build blocker before deploy/check-only",
        )
    return (
        "v1076-pm-service-uprobe-helper-build-pass",
        True,
        "static aarch64 PM-service uprobe/BPF counter helper built with explicit tracefs/attach/child gates",
        "V1077 should deploy helper and run check-only; live attach remains a separate bounded gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = manifest.get("checks") or []
    build_info = manifest.get("analysis", {}).get("build", {})
    return "\n".join([
        "# V1076 PM Service Uprobe Helper Build",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- tracefs_write_executed: `{manifest['tracefs_write_executed']}`",
        f"- bpf_attach_executed: `{manifest['bpf_attach_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in checks
        ]),
        "",
        "## Artifact",
        "",
        markdown_table(["signal", "value"], [
            ["output", build_info.get("output", "")],
            ["size", build_info.get("output_size", "")],
            ["sha256", build_info.get("output_sha256", "")],
            ["static_no_interp", build_info.get("static_no_interp", "")],
            ["marker_present", build_info.get("marker_present", "")],
        ]),
        "",
        "## Event Specs",
        "",
        "```text",
        "\n".join(manifest.get("analysis", {}).get("candidate_event_specs", [])),
        "```",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1075 = load_json(args.v1075_manifest)
    analysis: dict[str, Any] = {
        "v1075": {
            "manifest": str(repo_path(args.v1075_manifest)),
            "decision": v1075.get("decision", ""),
            "pass": bool(v1075.get("pass")),
        },
        "candidate_event_specs": candidate_event_specs(v1075),
        "build": {},
    }
    if args.command == "run":
        analysis["build"] = build(args, store)
    manifest: dict[str, Any] = {
        "cycle": "v1076",
        "generated_at": now_iso(),
        "command": args.command,
        "analysis": analysis,
        "device_commands_executed": False,
        "tracefs_write_executed": False,
        "bpf_attach_executed": False,
        "child_command_executed": False,
        "wifi_action_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
    }
    checks = build_checks(manifest)
    decision, passed, reason, next_step = decide(args.command, checks)
    manifest.update({
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "checks": [asdict(check) for check in checks],
        "host_metadata": {
            "cwd": str(Path.cwd()),
        },
    })
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
    build_info = manifest.get("analysis", {}).get("build", {})
    if build_info.get("output"):
        print(f"output: {build_info['output']}")
        print(f"sha256: {build_info.get('output_sha256', '')}")
    print(f"manifest: {store.path('manifest.json')}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
