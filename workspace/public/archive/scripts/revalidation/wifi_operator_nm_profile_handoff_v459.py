#!/usr/bin/env python3
"""V459 NetworkManager saved-profile Wi-Fi handoff packet.

V459 is host-side only.  It generates a private one-session operator script
that asks the operator to select a saved NetworkManager Wi-Fi profile by number,
reads SSID/PSK values locally through nmcli, and then runs the same strict V447
preflight/live handoff flow without printing Wi-Fi secret values.
"""

from __future__ import annotations

import argparse
import datetime as dt
import textwrap
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from wifi_operator_one_session_packet_v456 import strict_route_block, v447_env_prefix
from wifi_operator_postroute_packet_v453 import (
    common_v447_args,
    env_state,
    prompt_probe,
    run_step,
    script_header,
    syntax_check,
    v446_command,
    v447_plan_command,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v459-nm-profile-handoff-packet")


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


def nm_profile_prompt_block(security: str) -> str:
    psk_required = "true" if security in {"wpa2", "wpa3"} else "false"
    return textwrap.dedent(
        f"""\
        if ! command -v nmcli >/dev/null 2>&1; then
          echo "nmcli is required for V459 saved-profile handoff" >&2
          exit 4
        fi
        declare -a A90_NM_PROFILES=()
        while IFS= read -r A90_NM_NAME; do
          A90_NM_TYPE=$(nmcli -s -g connection.type connection show "${{A90_NM_NAME}}" 2>/dev/null || true)
          if [[ "${{A90_NM_TYPE}}" == "802-11-wireless" ]]; then
            A90_NM_PROFILES+=("${{A90_NM_NAME}}")
          fi
        done < <(nmcli -g NAME connection show)
        if [[ "${{#A90_NM_PROFILES[@]}}" -eq 0 ]]; then
          echo "no saved NetworkManager Wi-Fi profiles found" >&2
          exit 4
        fi
        echo "Saved NetworkManager Wi-Fi profiles (names and secrets are not printed):"
        for A90_NM_INDEX in "${{!A90_NM_PROFILES[@]}}"; do
          A90_NM_NAME="${{A90_NM_PROFILES[${{A90_NM_INDEX}}]}}"
          A90_NM_SSID=$(nmcli -s -g 802-11-wireless.ssid connection show "${{A90_NM_NAME}}" 2>/dev/null || true)
          A90_NM_PSK=$(nmcli -s --show-secrets -g 802-11-wireless-security.psk connection show "${{A90_NM_NAME}}" 2>/dev/null || true)
          if [[ -n "${{A90_NM_PSK}}" ]]; then
            A90_NM_PSK_PRESENT=true
          else
            A90_NM_PSK_PRESENT=false
          fi
          printf '%d) name_len=%d ssid_len=%d psk_present=%s psk_len=%d\\n' \\
            "$((A90_NM_INDEX + 1))" "${{#A90_NM_NAME}}" "${{#A90_NM_SSID}}" "${{A90_NM_PSK_PRESENT}}" "${{#A90_NM_PSK}}"
        done
        read -r -p "Select saved NetworkManager Wi-Fi profile number: " A90_NM_CHOICE
        if ! [[ "${{A90_NM_CHOICE}}" =~ ^[0-9]+$ ]]; then
          echo "invalid NetworkManager profile selection" >&2
          exit 2
        fi
        if (( A90_NM_CHOICE < 1 || A90_NM_CHOICE > ${{#A90_NM_PROFILES[@]}} )); then
          echo "NetworkManager profile selection out of range" >&2
          exit 2
        fi
        A90_NM_PROFILE="${{A90_NM_PROFILES[$((A90_NM_CHOICE - 1))]}}"
        read -r A90_WIFI_SSID < <(nmcli -s -g 802-11-wireless.ssid connection show "${{A90_NM_PROFILE}}" 2>/dev/null || true)
        read -r A90_WIFI_PSK < <(nmcli -s --show-secrets -g 802-11-wireless-security.psk connection show "${{A90_NM_PROFILE}}" 2>/dev/null || true)
        if [[ -z "${{A90_WIFI_SSID}}" ]]; then
          echo "selected NetworkManager profile has empty SSID" >&2
          exit 2
        fi
        if [[ "{psk_required}" == "true" && -z "${{A90_WIFI_PSK}}" ]]; then
          echo "selected NetworkManager profile has no PSK for this security mode" >&2
          exit 2
        fi
        """
    )


def nm_profile_script(args: argparse.Namespace) -> str:
    v447_args = common_v447_args(args)
    env_prefix = v447_env_prefix(args.security)
    return (
        script_header()
        + textwrap.dedent(
            """\
            cleanup() {
              unset A90_WIFI_SSID || true
              unset A90_WIFI_PSK || true
              unset A90_NM_NAME || true
              unset A90_NM_TYPE || true
              unset A90_NM_SSID || true
              unset A90_NM_PSK || true
              unset A90_NM_PSK_PRESENT || true
              unset A90_NM_PROFILE || true
              unset A90_NM_CHOICE || true
            }
            trap cleanup EXIT
            """
        )
        + textwrap.dedent(
            """\
            TS=$(date +%Y%m%d-%H%M%S)
            python3 scripts/revalidation/wifi_private_secret_guard_v446.py \
              --out-dir "tmp/wifi/v446-wifi-private-secret-guard-v459-start-${TS}" \
              --include-untracked \
              run
            """
        )
        + nm_profile_prompt_block(args.security)
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
    script = store.write_text("run-v459-nm-profile-wifi-flow.sh", nm_profile_script(args))
    return {
        "preflight_script": str(script),
        "live_script": str(script),
        "nm_profile_script": str(script),
        "preflight_command": f"bash {script}",
        "live_command": f"bash {script}",
        "nm_profile_command": f"bash {script}",
    }


def validate_packet(store: EvidenceStore, packet: dict[str, str], timeout: int) -> list[dict[str, Any]]:
    script = packet["nm_profile_script"]
    return [
        syntax_check(store, "nm-profile-bash-n", script, timeout),
        prompt_probe(store, "nm-profile-empty-input", script, "\n", 2, timeout),
    ]


def marker_audit(packet: dict[str, str]) -> dict[str, Any]:
    path = Path(packet.get("nm_profile_script") or "")
    result = {"present": path.is_file(), "markers": {}, "issues": []}
    markers = [
        "nmcli",
        "Select saved NetworkManager Wi-Fi profile number",
        "names and secrets are not printed",
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
        result["markers"][marker] = marker in text
        if marker not in text:
            result["issues"].append(f"missing marker: {marker}")
    return result


def classify(command: str, steps: list[dict[str, Any]], packet: dict[str, str], checks: list[dict[str, Any]], audit: dict[str, Any]) -> dict[str, Any]:
    if command == "plan":
        return {
            "decision": "v459-nm-profile-handoff-packet-plan-ready",
            "pass": True,
            "reason": "NetworkManager saved-profile handoff packet plan generated",
            "next_gate": "run V459 to generate a local saved-profile Wi-Fi handoff script",
        }
    if steps and not steps[0]["ok"]:
        return {
            "decision": "v459-nm-profile-handoff-secret-guard-blocked",
            "pass": False,
            "reason": "V446 repository secret guard failed before packet generation",
            "next_gate": "remove repository-visible private Wi-Fi material",
        }
    if len(steps) > 1 and not steps[1]["ok"]:
        return {
            "decision": "v459-nm-profile-handoff-v447-plan-blocked",
            "pass": False,
            "reason": "V447 plan failed before packet generation",
            "next_gate": "repair V447 before live handoff",
        }
    if not packet:
        return {
            "decision": "v459-nm-profile-handoff-packet-missing",
            "pass": False,
            "reason": "NetworkManager saved-profile handoff script was not generated",
            "next_gate": "inspect V459 evidence",
        }
    if audit.get("issues"):
        return {
            "decision": "v459-nm-profile-handoff-marker-failed",
            "pass": False,
            "reason": "generated saved-profile script is missing required markers",
            "next_gate": "repair V459 packet generation",
        }
    failed = [item for item in checks if not item.get("ok")]
    if failed:
        return {
            "decision": "v459-nm-profile-handoff-validation-failed",
            "pass": False,
            "reason": "generated saved-profile script failed syntax or fail-closed prompt validation",
            "next_gate": "repair V459 packet generation",
        }
    return {
        "decision": "v459-nm-profile-handoff-packet-ready",
        "pass": True,
        "reason": "saved NetworkManager profile handoff script generated and fail-closed validated without printing Wi-Fi secret values",
        "next_gate": "run saved-profile script locally and select the intended Wi-Fi profile by number",
    }


def guardrails() -> list[str]:
    return [
        "host-side packet generation and script validation only",
        "generated script prints profile lengths only, not names or secrets",
        "generated script reads SSID/PSK locally through nmcli at execution time",
        "passes Wi-Fi values only to V447 child processes, not route/proof commands",
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
            "# V459 NetworkManager Profile Handoff Packet",
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
        print(f"nm_profile_command: {packet['nm_profile_command']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
