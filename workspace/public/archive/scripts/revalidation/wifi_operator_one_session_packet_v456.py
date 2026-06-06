#!/usr/bin/env python3
"""V456 one-session operator packet for Wi-Fi handoff.

V456 is host-side only.  It generates a private one-session script that prompts
for Wi-Fi values once, runs V447 host preflight, routes/proves the result, then
optionally runs V447 live with the same in-memory env values.
"""

from __future__ import annotations

import argparse
import datetime as dt
import textwrap
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from wifi_operator_postroute_packet_v453 import (
    common_v447_args,
    env_state,
    run_step,
    syntax_check,
    prompt_probe,
    script_header,
    v446_command,
    v447_plan_command,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v456-operator-one-session-packet")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--tracked-only-secret-scan", action="store_true")
    parser.add_argument("--target-id", default="lab-primary")
    parser.add_argument("--security", choices=("open", "owe", "wpa2", "wpa3"), default="wpa2")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--serial", default="")
    parser.add_argument("--probe-timeout", type=int, default=8)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def strict_route_block(suffix: str, flow_var: str) -> str:
    return textwrap.dedent(
        f"""\
        ROUTE_RC=0
        python3 scripts/revalidation/wifi_handoff_result_router_v449.py \\
          --out-dir "tmp/wifi/v449-wifi-handoff-result-router-{suffix}-${{TS}}" \\
          run || ROUTE_RC=$?
        python3 scripts/revalidation/wifi_operator_preflight_readiness_v450.py \\
          --out-dir "tmp/wifi/v450-operator-preflight-readiness-{suffix}-${{TS}}" \\
          run || ROUTE_RC=$?
        python3 scripts/revalidation/wifi_live_cleanup_proof_v452.py \\
          --out-dir "tmp/wifi/v452-wifi-live-cleanup-proof-{suffix}-${{TS}}" \\
          run || ROUTE_RC=$?
        if [[ "${{{flow_var}}}" -eq 0 && "${{ROUTE_RC}}" -ne 0 ]]; then
          exit "${{ROUTE_RC}}"
        fi
        """
    )


def prompt_block_no_export(security: str) -> str:
    if security in {"wpa2", "wpa3"}:
        return textwrap.dedent(
            """\
            read -r -p "A90 Wi-Fi SSID: " A90_WIFI_SSID
            read -r -s -p "A90 Wi-Fi PSK: " A90_WIFI_PSK
            printf '\\n'
            if [[ -z "${A90_WIFI_SSID}" || -z "${A90_WIFI_PSK}" ]]; then
              echo "SSID and PSK are required for this flow" >&2
              exit 2
            fi
            """
        )
    return textwrap.dedent(
        """\
        read -r -p "A90 Wi-Fi SSID: " A90_WIFI_SSID
        if [[ -z "${A90_WIFI_SSID}" ]]; then
          echo "SSID is required for this flow" >&2
          exit 2
        fi
        unset A90_WIFI_PSK || true
        """
    )


def v447_env_prefix(security: str) -> str:
    if security in {"wpa2", "wpa3"}:
        return 'env "A90_WIFI_SSID=$A90_WIFI_SSID" "A90_WIFI_PSK=$A90_WIFI_PSK"'
    return 'env "A90_WIFI_SSID=$A90_WIFI_SSID"'


def one_session_script(args: argparse.Namespace) -> str:
    v447_args = common_v447_args(args)
    env_prefix = v447_env_prefix(args.security)
    return (
        script_header()
        + textwrap.dedent(
            """\
            TS=$(date +%Y%m%d-%H%M%S)
            python3 scripts/revalidation/wifi_private_secret_guard_v446.py \
              --out-dir "tmp/wifi/v446-wifi-private-secret-guard-v456-start-${TS}" \
              --include-untracked \
              run
            """
        )
        + prompt_block_no_export(args.security)
        + textwrap.dedent(
            f"""\
            set +e
            {env_prefix} \\
            python3 scripts/revalidation/wifi_explicit_connect_flow_v447.py \\
              --out-dir "tmp/wifi/v447-explicit-connect-flow-private-preflight-${{TS}}" \\
              {v447_args} \\
              --allow-read-wifi-env --i-understand-wifi-secret-env \\
              run
            PREFLIGHT_RC=$?
            set -e
            """
        )
        + strict_route_block("after-preflight", "PREFLIGHT_RC")
        + textwrap.dedent(
            """\
            if [[ "${PREFLIGHT_RC}" -ne 0 ]]; then
              exit "${PREFLIGHT_RC}"
            fi
            read -r -p "Type V447-LIVE to boot/flash Android and run bounded Wi-Fi connect: " CONFIRM
            if [[ "${CONFIRM}" != "V447-LIVE" ]]; then
              echo "live handoff cancelled" >&2
              exit 3
            fi
            set +e
            """
        )
        + textwrap.dedent(
            f"""\
            {env_prefix} \\
            python3 scripts/revalidation/wifi_explicit_connect_flow_v447.py \\
              --out-dir "tmp/wifi/v447-explicit-connect-flow-live-${{TS}}" \\
              {v447_args} \\
              --allow-read-wifi-env --i-understand-wifi-secret-env \\
              --allow-live-v445 \\
              --allow-android-boot-flash --assume-yes --i-understand-native-rollback \\
              --allow-explicit-scan-connect --i-understand-explicit-wifi-connect \\
              run
            LIVE_RC=$?
            set -e
            """
        )
        + strict_route_block("after-live", "LIVE_RC")
        + 'exit "${LIVE_RC}"\n'
    )


def write_packet(store: EvidenceStore, args: argparse.Namespace) -> dict[str, str]:
    script = store.write_text("run-v456-one-session-wifi-flow.sh", one_session_script(args))
    return {
        "preflight_script": str(script),
        "live_script": str(script),
        "one_session_script": str(script),
        "preflight_command": f"bash {script}",
        "live_command": f"bash {script}",
        "one_session_command": f"bash {script}",
    }


def validate_packet(store: EvidenceStore, packet: dict[str, str], timeout: int) -> list[dict[str, Any]]:
    script = packet["one_session_script"]
    return [
        syntax_check(store, "one-session-bash-n", script, timeout),
        prompt_probe(store, "one-session-empty-input", script, "\n\n", 2, timeout),
    ]


def marker_audit(packet: dict[str, str]) -> dict[str, Any]:
    path = Path(packet.get("one_session_script") or "")
    result = {"present": path.is_file(), "markers": {}, "issues": []}
    markers = [
        "wifi_private_secret_guard_v446.py",
        "wifi_explicit_connect_flow_v447.py",
        "PREFLIGHT_RC=$?",
        "LIVE_RC=$?",
        "wifi_handoff_result_router_v449.py",
        "wifi_operator_preflight_readiness_v450.py",
        "wifi_live_cleanup_proof_v452.py",
        "Type V447-LIVE",
        'exit "${LIVE_RC}"',
    ]
    if not path.is_file():
        result["issues"].append("script missing")
        return result
    text = path.read_text(encoding="utf-8", errors="replace")
    for marker in markers:
        present = marker in text
        result["markers"][marker] = present
        if not present:
            result["issues"].append(f"missing marker: {marker}")
    return result


def classify(command: str, steps: list[dict[str, Any]], packet: dict[str, str], checks: list[dict[str, Any]], audit: dict[str, Any]) -> dict[str, Any]:
    if command == "plan":
        return {
            "decision": "v456-operator-one-session-packet-plan-ready",
            "pass": True,
            "reason": "one-session operator packet plan generated",
            "next_gate": "run V456 to generate one-session Wi-Fi handoff script",
        }
    if steps and not steps[0]["ok"]:
        return {
            "decision": "v456-operator-one-session-secret-guard-blocked",
            "pass": False,
            "reason": "V446 repository secret guard failed before packet generation",
            "next_gate": "remove repository-visible private Wi-Fi material",
        }
    if len(steps) > 1 and not steps[1]["ok"]:
        return {
            "decision": "v456-operator-one-session-v447-plan-blocked",
            "pass": False,
            "reason": "V447 plan failed before packet generation",
            "next_gate": "repair V447 before live handoff",
        }
    if not packet:
        return {
            "decision": "v456-operator-one-session-packet-missing",
            "pass": False,
            "reason": "one-session handoff script was not generated",
            "next_gate": "inspect V456 evidence",
        }
    if audit.get("issues"):
        return {
            "decision": "v456-operator-one-session-marker-failed",
            "pass": False,
            "reason": "generated one-session script is missing required markers",
            "next_gate": "repair V456 packet generation",
        }
    failed = [item for item in checks if not item.get("ok")]
    if failed:
        return {
            "decision": "v456-operator-one-session-validation-failed",
            "pass": False,
            "reason": "generated one-session script failed syntax or fail-closed prompt validation",
            "next_gate": "repair V456 packet generation",
        }
    return {
        "decision": "v456-operator-one-session-packet-ready",
        "pass": True,
        "reason": "one-session Wi-Fi handoff script generated and fail-closed validated without storing Wi-Fi secret values",
        "next_gate": "run one-session script and enter Wi-Fi values locally",
    }


def guardrails() -> list[str]:
    return [
        "host-side packet generation and script validation only",
        "prompts for Wi-Fi values once at execution time",
        "does not write Wi-Fi values to tracked files or V456 evidence",
        "passes Wi-Fi values only to V447 child processes, not route/proof commands",
        "runs preflight, route/proof, optional live, and final proof in one shell session",
        "live step still requires exact V447-LIVE confirmation",
        "server exposure remains blocked",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    step_rows = [
        [item["name"], "ok" if item["ok"] else "fail", str(item["rc"]), f"{item['duration_sec']:.3f}s", item["file"]]
        for item in manifest["steps"]
    ]
    check_rows = [
        [item["name"], item["kind"], "ok" if item["ok"] else "fail", str(item["rc"]), str(item.get("expected_rc", "-")), item["file"]]
        for item in manifest["checks"]
    ]
    packet_rows = [[key, value] for key, value in (manifest.get("packet") or {}).items()]
    return "\n".join(
        [
            "# V456 Operator One-session Packet",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_gate: `{manifest['classification']['next_gate']}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Packet",
            "",
            markdown_table(["item", "value"], packet_rows if packet_rows else [["-", "-"]]),
            "",
            "## Steps",
            "",
            markdown_table(["step", "status", "rc", "duration", "file"], step_rows if step_rows else [["none", "-", "-", "-", "-"]]),
            "",
            "## Checks",
            "",
            markdown_table(["name", "kind", "status", "rc", "expected", "file"], check_rows if check_rows else [["-", "-", "-", "-", "-", "-"]]),
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
    steps: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    packet: dict[str, str] = {}
    audit: dict[str, Any] = {}
    if args.command == "run":
        steps.append(run_step(store, "v446-secret-guard", v446_command(args, store), args.timeout * 8))
        if steps[-1]["ok"]:
            steps.append(run_step(store, "v447-plan", v447_plan_command(args, store), args.timeout * 4))
        if len(steps) > 1 and steps[-1]["ok"]:
            packet = write_packet(store, args)
            audit = marker_audit(packet)
            checks = validate_packet(store, packet, args.probe_timeout)
    classification = classify(args.command, steps, packet, checks, audit)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "host": collect_host_metadata(),
        "env_state": env_state(),
        "classification": classification,
        "steps": steps,
        "checks": checks,
        "audit": audit,
        "packet": packet,
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
    if packet:
        print(f"one_session_command: {packet['one_session_command']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
