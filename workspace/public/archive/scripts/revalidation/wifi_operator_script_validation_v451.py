#!/usr/bin/env python3
"""V451 operator handoff script validation.

V451 is host-side only.  It validates the generated V448 operator scripts with
shell syntax checks and bounded fail-closed prompt probes, without Wi-Fi secrets
or device access.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v451-operator-script-validation")
DEFAULT_WIFI_ROOT = Path("tmp/wifi")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--wifi-root", type=Path, default=DEFAULT_WIFI_ROOT)
    parser.add_argument("--timeout", type=int, default=8)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        payload = {"decision": "invalid", "pass": False, "error": str(exc)}
    payload["_path"] = str(path)
    payload["_run_dir"] = str(path.parent)
    try:
        payload["_mtime"] = path.stat().st_mtime
    except OSError:
        payload["_mtime"] = 0.0
    return payload


def latest_packet(root: Path) -> dict[str, Any] | None:
    rows: list[dict[str, Any]] = []
    for path in repo_path(root).glob("v448-operator-handoff-packet-run*/manifest.json"):
        rows.append(load_json(path))
    rows.sort(key=lambda item: float(item.get("_mtime") or 0.0))
    return rows[-1] if rows else None


def command_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("A90_WIFI_SSID", None)
    env.pop("A90_WIFI_PSK", None)
    return env


def run_process(command: list[str], timeout: int, stdin: str = "") -> tuple[int | None, str, str, float]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            env=command_env(),
            input=stdin,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return result.returncode, result.stdout, "", time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, text, f"timeout after {timeout}s", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001
        return None, "", str(exc), time.monotonic() - started


def write_capture(store: EvidenceStore, name: str, command: list[str], rc: int | None, text: str, error: str, duration: float) -> str:
    body = "\n".join(
        [
            "$ " + " ".join(command),
            text.rstrip(),
            error.rstrip(),
            f"rc={rc}",
            f"duration_sec={duration:.3f}",
            "",
        ]
    )
    path = store.write_text(f"captures/{name}.txt", body)
    return str(path.relative_to(store.run_dir))


def syntax_check(store: EvidenceStore, name: str, script: str, timeout: int) -> dict[str, Any]:
    command = ["bash", "-n", script]
    rc, text, error, duration = run_process(command, timeout)
    return {
        "name": name,
        "kind": "syntax",
        "command": " ".join(command),
        "ok": rc == 0,
        "rc": rc,
        "duration_sec": duration,
        "file": write_capture(store, name, command, rc, text, error, duration),
        "error": error,
    }


def prompt_probe(store: EvidenceStore, name: str, script: str, stdin: str, expected_rc: int, timeout: int) -> dict[str, Any]:
    command = ["bash", script]
    rc, text, error, duration = run_process(command, timeout, stdin=stdin)
    output = (text or "") + (error or "")
    return {
        "name": name,
        "kind": "prompt-probe",
        "command": " ".join(command),
        "ok": rc == expected_rc,
        "rc": rc,
        "expected_rc": expected_rc,
        "duration_sec": duration,
        "file": write_capture(store, name, command, rc, text, error, duration),
        "error": error,
        "cancel_observed": "cancelled" in output.lower(),
        "empty_guard_observed": "required for this flow" in output,
    }


def packet_scripts(packet: dict[str, Any] | None) -> dict[str, str]:
    payload = (packet or {}).get("packet") or {}
    return {
        "preflight": str(payload.get("preflight_script") or ""),
        "live": str(payload.get("live_script") or ""),
        "preflight_command": str(payload.get("preflight_command") or ""),
        "live_command": str(payload.get("live_command") or ""),
    }


def execute_checks(args: argparse.Namespace, store: EvidenceStore, packet: dict[str, Any] | None) -> tuple[list[dict[str, Any]], dict[str, str]]:
    scripts = packet_scripts(packet)
    checks: list[dict[str, Any]] = []
    if scripts["preflight"]:
        checks.append(syntax_check(store, "preflight-bash-n", scripts["preflight"], args.timeout))
        checks.append(prompt_probe(store, "preflight-empty-input", scripts["preflight"], "\n\n", 2, args.timeout))
    if scripts["live"]:
        checks.append(syntax_check(store, "live-bash-n", scripts["live"], args.timeout))
        checks.append(prompt_probe(store, "live-cancel-input", scripts["live"], "NO\n", 3, args.timeout))
    return checks, scripts


def classify(command: str, packet: dict[str, Any] | None, checks: list[dict[str, Any]], scripts: dict[str, str]) -> dict[str, Any]:
    if command == "plan":
        return {
            "decision": "v451-operator-script-validation-plan-ready",
            "pass": True,
            "reason": "operator script validation plan generated",
            "next_gate": "run V451 before operator host preflight",
            "recommended_command": "",
        }
    if not packet:
        return {
            "decision": "v451-operator-script-validation-needs-v448-packet",
            "pass": False,
            "reason": "no V448 packet evidence found",
            "next_gate": "run V448 packet generation",
            "recommended_command": "python3 scripts/revalidation/wifi_operator_handoff_packet_v448.py run",
        }
    if packet.get("decision") != "v448-operator-handoff-packet-ready" or packet.get("pass") is not True:
        return {
            "decision": "v451-operator-script-validation-v448-not-ready",
            "pass": False,
            "reason": str(packet.get("reason") or "latest V448 packet did not pass"),
            "next_gate": "repair or rerun V448",
            "recommended_command": "",
        }
    if not scripts.get("preflight") or not scripts.get("live"):
        return {
            "decision": "v451-operator-script-validation-missing-scripts",
            "pass": False,
            "reason": "V448 packet does not include both preflight and live scripts",
            "next_gate": "regenerate V448 packet",
            "recommended_command": "",
        }
    failed = [item for item in checks if not item.get("ok")]
    if failed:
        return {
            "decision": "v451-operator-script-validation-failed",
            "pass": False,
            "reason": "generated V448 scripts failed syntax or fail-closed prompt validation",
            "next_gate": "regenerate V448 packet before operator input",
            "recommended_command": "",
        }
    return {
        "decision": "v451-operator-script-validation-pass",
        "pass": True,
        "reason": "generated V448 scripts pass shell syntax and fail-closed prompt probes",
        "next_gate": "run generated host preflight script and enter Wi-Fi values locally",
        "recommended_command": scripts.get("preflight_command") or "",
    }


def check_rows(checks: list[dict[str, Any]]) -> list[list[str]]:
    return [
        [
            item["name"],
            item["kind"],
            "ok" if item["ok"] else "fail",
            str(item.get("rc")),
            str(item.get("expected_rc", "-")),
            f"{item['duration_sec']:.3f}s",
            item["file"],
        ]
        for item in checks
    ]


def guardrails() -> list[str]:
    return [
        "host-side script validation only",
        "clears A90_WIFI_SSID and A90_WIFI_PSK from child process environment",
        "uses empty or cancellation input only",
        "does not run successful V447 preflight/live paths",
        "does not run device commands or Wi-Fi bring-up",
        "server exposure remains blocked",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V451 Operator Script Validation",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{manifest['classification']['next_gate']}`",
            f"- recommended_command: `{manifest['classification'].get('recommended_command') or '-'}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Checks",
            "",
            markdown_table(["name", "kind", "status", "rc", "expected", "duration", "file"], check_rows(manifest["checks"]) if manifest["checks"] else [["-", "-", "-", "-", "-", "-", "-"]]),
            "",
            "## Guardrails",
            "",
            *[f"- {item}" for item in manifest["guardrails"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    packet = latest_packet(args.wifi_root) if args.command == "run" else None
    checks: list[dict[str, Any]] = []
    scripts: dict[str, str] = {}
    if args.command == "run" and packet:
        checks, scripts = execute_checks(args, store, packet)
    classification = classify(args.command, packet, checks, scripts)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "host": collect_host_metadata(),
        "classification": classification,
        "packet": packet,
        "scripts": scripts,
        "checks": checks,
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next_gate: {classification['next_gate']}")
    if classification.get("recommended_command"):
        print(f"recommended_command: {classification['recommended_command']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
