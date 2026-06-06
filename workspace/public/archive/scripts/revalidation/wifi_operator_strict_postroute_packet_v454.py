#!/usr/bin/env python3
"""V454 strict post-route operator packet for Wi-Fi handoff.

V454 is host-side only.  It generates private V447 operator scripts like V453,
but treats post-route/proof command failures as blocking when the underlying
V447 flow succeeds.  This prevents a clean preflight/live result from being
reported without route/proof evidence.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import shlex
import textwrap
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from wifi_operator_postroute_packet_v453 import (
    common_v447_args,
    env_state,
    prompt_block,
    run_step,
    syntax_check,
    prompt_probe,
    script_header,
    v446_command,
    v447_plan_command,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v454-operator-strict-postroute-packet")


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


def strict_postroute_block(kind: str) -> str:
    suffix = "after-live" if kind == "live" else "after-preflight"
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
        if [[ "${{FLOW_RC}}" -eq 0 && "${{ROUTE_RC}}" -ne 0 ]]; then
          exit "${{ROUTE_RC}}"
        fi
        exit "${{FLOW_RC}}"
        """
    )


def preflight_script(args: argparse.Namespace) -> str:
    return (
        script_header()
        + prompt_block(args.security)
        + textwrap.dedent(
            f"""\
            TS=$(date +%Y%m%d-%H%M%S)
            set +e
            python3 scripts/revalidation/wifi_explicit_connect_flow_v447.py \\
              --out-dir "tmp/wifi/v447-explicit-connect-flow-private-preflight-${{TS}}" \\
              {common_v447_args(args)} \\
              --allow-read-wifi-env --i-understand-wifi-secret-env \\
              run
            FLOW_RC=$?
            set -e
            """
        )
        + strict_postroute_block("preflight")
    )


def live_script(args: argparse.Namespace) -> str:
    return (
        script_header()
        + textwrap.dedent(
            """\
            read -r -p "Type V447-LIVE to boot/flash Android and run bounded Wi-Fi connect: " CONFIRM
            if [[ "${CONFIRM}" != "V447-LIVE" ]]; then
              echo "live handoff cancelled" >&2
              exit 3
            fi
            """
        )
        + prompt_block(args.security)
        + textwrap.dedent(
            f"""\
            TS=$(date +%Y%m%d-%H%M%S)
            set +e
            python3 scripts/revalidation/wifi_explicit_connect_flow_v447.py \\
              --out-dir "tmp/wifi/v447-explicit-connect-flow-live-${{TS}}" \\
              {common_v447_args(args)} \\
              --allow-read-wifi-env --i-understand-wifi-secret-env \\
              --allow-live-v445 \\
              --allow-android-boot-flash --assume-yes --i-understand-native-rollback \\
              --allow-explicit-scan-connect --i-understand-explicit-wifi-connect \\
              run
            FLOW_RC=$?
            set -e
            """
        )
        + strict_postroute_block("live")
    )


def write_packet(store: EvidenceStore, args: argparse.Namespace) -> dict[str, str]:
    preflight = store.write_text("run-v454-host-preflight-strict-route.sh", preflight_script(args))
    live = store.write_text("run-v454-live-strict-proof.sh", live_script(args))
    return {
        "preflight_script": str(preflight),
        "live_script": str(live),
        "preflight_command": f"bash {preflight}",
        "live_command": f"bash {live}",
    }


def validate_packet(store: EvidenceStore, packet: dict[str, str], timeout: int) -> list[dict[str, Any]]:
    return [
        syntax_check(store, "preflight-bash-n", packet["preflight_script"], timeout),
        prompt_probe(store, "preflight-empty-input", packet["preflight_script"], "\n\n", 2, timeout),
        syntax_check(store, "live-bash-n", packet["live_script"], timeout),
        prompt_probe(store, "live-cancel-input", packet["live_script"], "NO\n", 3, timeout),
    ]


def classify(command: str, steps: list[dict[str, Any]], packet: dict[str, str], checks: list[dict[str, Any]]) -> dict[str, Any]:
    if command == "plan":
        return {
            "decision": "v454-operator-strict-postroute-packet-plan-ready",
            "pass": True,
            "reason": "strict post-route operator packet plan generated",
            "next_gate": "run V454 to generate strict post-route handoff scripts",
        }
    if steps and not steps[0]["ok"]:
        return {
            "decision": "v454-operator-strict-postroute-secret-guard-blocked",
            "pass": False,
            "reason": "V446 repository secret guard failed before packet generation",
            "next_gate": "remove repository-visible private Wi-Fi material",
        }
    if len(steps) > 1 and not steps[1]["ok"]:
        return {
            "decision": "v454-operator-strict-postroute-v447-plan-blocked",
            "pass": False,
            "reason": "V447 plan failed before packet generation",
            "next_gate": "repair V447 before live handoff",
        }
    if not packet:
        return {
            "decision": "v454-operator-strict-postroute-packet-missing",
            "pass": False,
            "reason": "strict post-route handoff scripts were not generated",
            "next_gate": "inspect V454 evidence",
        }
    failed = [item for item in checks if not item.get("ok")]
    if failed:
        return {
            "decision": "v454-operator-strict-postroute-validation-failed",
            "pass": False,
            "reason": "generated strict post-route scripts failed syntax or fail-closed prompt validation",
            "next_gate": "repair V454 packet generation",
        }
    return {
        "decision": "v454-operator-strict-postroute-packet-ready",
        "pass": True,
        "reason": "strict post-route handoff scripts generated and fail-closed validated without storing Wi-Fi secret values",
        "next_gate": "run strict post-route host preflight script, then live script if routed",
    }


def guardrails() -> list[str]:
    return [
        "host-side packet generation and script validation only",
        "prompts for Wi-Fi values at execution time",
        "does not write Wi-Fi values to tracked files or V454 evidence",
        "post-route failures block a successful V447 flow",
        "live script requires exact V447-LIVE confirmation",
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
            "# V454 Operator Strict Post-route Packet",
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
    if args.command == "run":
        steps.append(run_step(store, "v446-secret-guard", v446_command(args, store), args.timeout * 8))
        if steps[-1]["ok"]:
            steps.append(run_step(store, "v447-plan", v447_plan_command(args, store), args.timeout * 4))
        if len(steps) > 1 and steps[-1]["ok"]:
            packet = write_packet(store, args)
            checks = validate_packet(store, packet, args.probe_timeout)
    classification = classify(args.command, steps, packet, checks)
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
        print(f"preflight_command: {packet['preflight_command']}")
        print(f"live_command: {packet['live_command']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
