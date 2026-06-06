#!/usr/bin/env python3
"""V455 strict post-route semantics proof.

V455 is host-side only.  It proves the V454 strict post-route shell semantics:
when the V447 flow succeeds, any V449/V450/V452 post-route failure must make the
operator script fail; when V447 itself fails, the V447 return code is preserved.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v455-strict-postroute-semantics")
DEFAULT_WIFI_ROOT = Path("tmp/wifi")
STRICT_MARKERS = (
    "ROUTE_RC=0",
    'if [[ "${FLOW_RC}" -eq 0 && "${ROUTE_RC}" -ne 0 ]]; then',
    'exit "${ROUTE_RC}"',
    'exit "${FLOW_RC}"',
    "wifi_handoff_result_router_v449.py",
    "wifi_operator_preflight_readiness_v450.py",
    "wifi_live_cleanup_proof_v452.py",
)


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


def latest_v454_packet(root: Path) -> dict[str, Any] | None:
    rows: list[dict[str, Any]] = []
    for path in repo_path(root).glob("v454-operator-strict-postroute-packet-run*/manifest.json"):
        if path.name == "manifest.json":
            rows.append(load_json(path))
    rows.sort(key=lambda item: float(item.get("_mtime") or 0.0))
    return rows[-1] if rows else None


def packet_scripts(packet: dict[str, Any] | None) -> dict[str, str]:
    payload = (packet or {}).get("packet") or {}
    return {
        "preflight": str(payload.get("preflight_script") or ""),
        "live": str(payload.get("live_script") or ""),
        "preflight_command": str(payload.get("preflight_command") or ""),
        "live_command": str(payload.get("live_command") or ""),
    }


def marker_audit(path_text: str) -> dict[str, Any]:
    path = Path(path_text)
    result = {"path": path_text, "present": path.is_file(), "markers": {}, "issues": []}
    if not path.is_file():
        result["issues"].append("script missing")
        return result
    text = path.read_text(encoding="utf-8", errors="replace")
    for marker in STRICT_MARKERS:
        present = marker in text
        result["markers"][marker] = present
        if not present:
            result["issues"].append(f"missing marker: {marker}")
    return result


def matrix_script(flow_rc: int, route_codes: tuple[int, int, int]) -> str:
    route_assignments = "\n".join(
        f"RC={code}; if [[ \"${{RC}}\" -ne 0 ]]; then ROUTE_RC=\"${{RC}}\"; fi"
        for code in route_codes
    )
    return "\n".join(
        [
            "set -euo pipefail",
            f"FLOW_RC={flow_rc}",
            "ROUTE_RC=0",
            route_assignments,
            'if [[ "${FLOW_RC}" -eq 0 && "${ROUTE_RC}" -ne 0 ]]; then',
            '  exit "${ROUTE_RC}"',
            "fi",
            'exit "${FLOW_RC}"',
        ]
    )


def run_matrix_case(store: EvidenceStore, name: str, flow_rc: int, route_codes: tuple[int, int, int], expected_rc: int, timeout: int) -> dict[str, Any]:
    script = matrix_script(flow_rc, route_codes)
    command = ["bash", "-c", script]
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        rc: int | None = result.returncode
        output = result.stdout
        error = ""
    except subprocess.TimeoutExpired as exc:
        rc = None
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        error = f"timeout after {timeout}s"
    path = store.write_text(
        f"matrix/{name}.txt",
        "\n".join(
            [
                f"flow_rc={flow_rc}",
                f"route_codes={route_codes}",
                f"expected_rc={expected_rc}",
                "--- script ---",
                script,
                "--- output ---",
                output.rstrip(),
                error.rstrip(),
                f"rc={rc}",
                "",
            ]
        ),
    )
    return {
        "name": name,
        "flow_rc": flow_rc,
        "route_codes": list(route_codes),
        "expected_rc": expected_rc,
        "rc": rc,
        "ok": rc == expected_rc,
        "file": str(path.relative_to(store.run_dir)),
        "error": error,
    }


def run_matrix(store: EvidenceStore, timeout: int) -> list[dict[str, Any]]:
    cases = [
        ("flow-pass-routes-pass", 0, (0, 0, 0), 0),
        ("flow-pass-router-fails", 0, (7, 0, 0), 7),
        ("flow-pass-later-route-fails", 0, (0, 0, 9), 9),
        ("flow-fails-route-passes", 2, (0, 0, 0), 2),
        ("flow-fails-route-fails", 2, (0, 7, 0), 2),
        ("live-cancel-preserved", 3, (0, 0, 0), 3),
    ]
    return [run_matrix_case(store, *case, timeout=timeout) for case in cases]


def classify(command: str, packet: dict[str, Any] | None, audits: dict[str, Any], matrix: list[dict[str, Any]]) -> dict[str, Any]:
    if command == "plan":
        return {
            "decision": "v455-strict-postroute-semantics-plan-ready",
            "pass": True,
            "reason": "strict post-route semantics proof plan generated",
            "next_gate": "run V455 after V454 packet generation",
            "recommended_command": "",
        }
    if not packet:
        return {
            "decision": "v455-strict-postroute-semantics-needs-v454",
            "pass": False,
            "reason": "no V454 packet evidence found",
            "next_gate": "run V454 strict post-route packet generation",
            "recommended_command": "python3 scripts/revalidation/wifi_operator_strict_postroute_packet_v454.py run",
        }
    if packet.get("decision") != "v454-operator-strict-postroute-packet-ready" or packet.get("pass") is not True:
        return {
            "decision": "v455-strict-postroute-semantics-v454-not-ready",
            "pass": False,
            "reason": str(packet.get("reason") or "latest V454 packet did not pass"),
            "next_gate": "repair or rerun V454",
            "recommended_command": "",
        }
    audit_failures = [name for name, audit in audits.items() if audit.get("issues")]
    if audit_failures:
        return {
            "decision": "v455-strict-postroute-semantics-marker-failed",
            "pass": False,
            "reason": "generated V454 scripts are missing strict post-route markers: " + ", ".join(audit_failures),
            "next_gate": "repair V454 packet generation",
            "recommended_command": "",
        }
    failed = [item["name"] for item in matrix if not item.get("ok")]
    if failed:
        return {
            "decision": "v455-strict-postroute-semantics-matrix-failed",
            "pass": False,
            "reason": "strict post-route return-code matrix failed: " + ", ".join(failed),
            "next_gate": "repair V454 strict post-route logic",
            "recommended_command": "",
        }
    scripts = packet_scripts(packet)
    return {
        "decision": "v455-strict-postroute-semantics-pass",
        "pass": True,
        "reason": "V454 scripts contain strict markers and the return-code matrix proves post-route failure propagation",
        "next_gate": "run V454 host preflight strict-route script and enter Wi-Fi values locally",
        "recommended_command": scripts.get("preflight_command", ""),
    }


def matrix_rows(matrix: list[dict[str, Any]]) -> list[list[str]]:
    return [
        [
            item["name"],
            str(item["flow_rc"]),
            str(item["route_codes"]),
            str(item["expected_rc"]),
            str(item["rc"]),
            "ok" if item["ok"] else "fail",
            item["file"],
        ]
        for item in matrix
    ]


def audit_rows(audits: dict[str, Any]) -> list[list[str]]:
    rows = []
    for name, audit in audits.items():
        rows.append([name, str(audit.get("present")), "; ".join(audit.get("issues") or []) or "-"])
    return rows


def guardrails() -> list[str]:
    return [
        "host-side strict semantics proof only",
        "does not read Wi-Fi secret env values",
        "does not execute generated operator scripts",
        "does not run device commands or Wi-Fi bring-up",
        "server exposure remains blocked",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# V455 Strict Post-route Semantics Proof",
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
            "## Script Marker Audit",
            "",
            markdown_table(["script", "present", "issues"], audit_rows(manifest["audits"]) if manifest["audits"] else [["-", "-", "-"]]),
            "",
            "## Return-code Matrix",
            "",
            markdown_table(["case", "flow_rc", "route_codes", "expected", "actual", "status", "file"], matrix_rows(manifest["matrix"]) if manifest["matrix"] else [["-", "-", "-", "-", "-", "-", "-"]]),
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
    packet = latest_v454_packet(args.wifi_root) if args.command == "run" else None
    scripts = packet_scripts(packet)
    audits: dict[str, Any] = {}
    matrix: list[dict[str, Any]] = []
    if args.command == "run":
        audits = {
            "preflight": marker_audit(scripts.get("preflight", "")),
            "live": marker_audit(scripts.get("live", "")),
        }
        matrix = run_matrix(store, args.timeout)
    classification = classify(args.command, packet, audits, matrix)
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
        "audits": audits,
        "matrix": matrix,
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
