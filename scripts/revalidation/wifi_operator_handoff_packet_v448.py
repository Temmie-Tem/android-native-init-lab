#!/usr/bin/env python3
"""V448 operator handoff packet for private Wi-Fi live flow.

V448 is host-side only.  It generates private, ignored handoff scripts that
prompt for Wi-Fi values at execution time and run the V447 gated flow without
writing those values to tracked files, chat, or evidence.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import subprocess
import textwrap
import time
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v448-operator-handoff-packet")


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
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def env_state() -> dict[str, Any]:
    state: dict[str, Any] = {}
    for name in ("A90_WIFI_SSID", "A90_WIFI_PSK"):
        value = os.environ.get(name, "")
        state[name] = {"present": name in os.environ, "length": len(value)}
    return state


def run_step(store: EvidenceStore, name: str, command: list[str], timeout: int) -> dict[str, Any]:
    started = time.monotonic()
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
        rc = result.returncode
        output = result.stdout
        error = ""
    except subprocess.TimeoutExpired as exc:
        rc = None
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        error = f"timeout after {timeout}s"
    except Exception as exc:  # noqa: BLE001
        rc = None
        output = ""
        error = str(exc)
    duration = time.monotonic() - started
    body = "\n".join(
        [
            "$ " + " ".join(shlex.quote(str(part)) for part in command),
            output.rstrip(),
            error.rstrip(),
            f"rc={rc}",
            "",
        ]
    )
    path = store.write_text(f"steps/{name}.txt", body)
    return {
        "name": name,
        "command": " ".join(shlex.quote(str(part)) for part in command),
        "ok": rc == 0,
        "rc": rc,
        "duration_sec": duration,
        "file": str(path.relative_to(store.run_dir)),
        "error": error,
    }


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"decision": "missing", "pass": False, "_path": str(path)}
    except Exception as exc:  # noqa: BLE001
        return {"decision": "invalid", "pass": False, "error": str(exc), "_path": str(path)}


def v446_command(args: argparse.Namespace, store: EvidenceStore) -> list[str]:
    command = [
        "python3",
        "scripts/revalidation/wifi_private_secret_guard_v446.py",
        "--out-dir",
        str(store.run_dir / "v446-secret-guard"),
    ]
    if not args.tracked_only_secret_scan:
        command.append("--include-untracked")
    command.append("run")
    return command


def v447_plan_command(args: argparse.Namespace, store: EvidenceStore) -> list[str]:
    command = [
        "python3",
        "scripts/revalidation/wifi_explicit_connect_flow_v447.py",
        "--out-dir",
        str(store.run_dir / "v447-plan"),
        "--target-id",
        args.target_id,
        "--security",
        args.security,
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--timeout",
        str(args.timeout),
    ]
    if args.serial:
        command.extend(["--serial", args.serial])
    command.append("plan")
    return command


def common_v447_args(args: argparse.Namespace) -> list[str]:
    command = [
        "--target-id",
        shlex.quote(args.target_id),
        "--security",
        args.security,
        "--bridge-host",
        shlex.quote(args.bridge_host),
        "--bridge-port",
        str(args.bridge_port),
        "--timeout",
        str(args.timeout),
    ]
    if args.serial:
        command.extend(["--serial", shlex.quote(args.serial)])
    return command


def shell_array(items: list[str]) -> str:
    return " ".join(items)


def prompt_block(security: str) -> str:
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
            export A90_WIFI_SSID A90_WIFI_PSK
            """
        )
    return textwrap.dedent(
        """\
        read -r -p "A90 Wi-Fi SSID: " A90_WIFI_SSID
        if [[ -z "${A90_WIFI_SSID}" ]]; then
          echo "SSID is required for this flow" >&2
          exit 2
        fi
        unset A90_WIFI_PSK
        export A90_WIFI_SSID
        """
    )


def script_header() -> str:
    return textwrap.dedent(
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        cd {shlex.quote(str(repo_path(".")))}
        cleanup() {{
          unset A90_WIFI_SSID || true
          unset A90_WIFI_PSK || true
        }}
        trap cleanup EXIT
        umask 077
        """
    )


def preflight_script(args: argparse.Namespace) -> str:
    v447_args = shell_array(common_v447_args(args))
    return (
        script_header()
        + prompt_block(args.security)
        + textwrap.dedent(
            f"""\
            TS=$(date +%Y%m%d-%H%M%S)
            python3 scripts/revalidation/wifi_explicit_connect_flow_v447.py \\
              --out-dir "tmp/wifi/v447-explicit-connect-flow-private-preflight-${{TS}}" \\
              {v447_args} \\
              --allow-read-wifi-env --i-understand-wifi-secret-env \\
              run
            """
        )
    )


def live_script(args: argparse.Namespace) -> str:
    v447_args = shell_array(common_v447_args(args))
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
            python3 scripts/revalidation/wifi_explicit_connect_flow_v447.py \\
              --out-dir "tmp/wifi/v447-explicit-connect-flow-live-${{TS}}" \\
              {v447_args} \\
              --allow-read-wifi-env --i-understand-wifi-secret-env \\
              --allow-live-v445 \\
              --allow-android-boot-flash --assume-yes --i-understand-native-rollback \\
              --allow-explicit-scan-connect --i-understand-explicit-wifi-connect \\
              run
            """
        )
    )


def write_packet(store: EvidenceStore, args: argparse.Namespace) -> dict[str, str]:
    preflight = store.write_text("run-v447-host-preflight.sh", preflight_script(args))
    live = store.write_text("run-v447-live.sh", live_script(args))
    return {
        "preflight_script": str(preflight),
        "live_script": str(live),
        "preflight_command": f"bash {preflight}",
        "live_command": f"bash {live}",
    }


def classify(command: str, steps: list[dict[str, Any]], packet: dict[str, str]) -> dict[str, Any]:
    if command == "plan":
        return {
            "decision": "v448-operator-handoff-packet-plan-ready",
            "pass": True,
            "reason": "operator handoff packet plan generated",
            "next_gate": "run V448 to generate private handoff scripts",
        }
    if steps and not steps[0]["ok"]:
        return {
            "decision": "v448-operator-handoff-secret-guard-blocked",
            "pass": False,
            "reason": "V446 repository secret guard failed before packet generation",
            "next_gate": "remove repository-visible private Wi-Fi material",
        }
    if len(steps) > 1 and not steps[1]["ok"]:
        return {
            "decision": "v448-operator-handoff-v447-plan-blocked",
            "pass": False,
            "reason": "V447 plan failed before packet generation",
            "next_gate": "repair V447 before live handoff",
        }
    if not packet:
        return {
            "decision": "v448-operator-handoff-packet-missing",
            "pass": False,
            "reason": "handoff scripts were not generated",
            "next_gate": "inspect V448 evidence",
        }
    return {
        "decision": "v448-operator-handoff-packet-ready",
        "pass": True,
        "reason": "private handoff scripts generated without storing Wi-Fi secret values",
        "next_gate": "run host preflight script, then live script if preflight passes",
    }


def guardrails() -> list[str]:
    return [
        "host-side packet generation only",
        "prompts for Wi-Fi values at execution time",
        "does not write Wi-Fi values to tracked files or V448 evidence",
        "runs V446 and V447 plan before writing handoff scripts",
        "live script requires exact V447-LIVE confirmation",
        "server exposure remains blocked",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [
            item["name"],
            "ok" if item["ok"] else "fail",
            str(item["rc"]),
            f"{item['duration_sec']:.3f}s",
            item["file"],
        ]
        for item in manifest["steps"]
    ]
    env_rows = [
        [name, str(data.get("present")), str(data.get("length"))]
        for name, data in (manifest["env_state"] or {}).items()
    ]
    packet = manifest.get("packet") or {}
    packet_rows = [[key, value] for key, value in packet.items()]
    return "\n".join(
        [
            "# V448 Operator Handoff Packet",
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
            "## Env State",
            "",
            markdown_table(["name", "present", "length"], env_rows if env_rows else [["-", "-", "-"]]),
            "",
            "## Steps",
            "",
            markdown_table(["step", "status", "rc", "duration", "file"], rows if rows else [["none", "-", "-", "-", "-"]]),
            "",
            "## Packet",
            "",
            markdown_table(["item", "value"], packet_rows if packet_rows else [["-", "-"]]),
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
    packet: dict[str, str] = {}
    if args.command == "run":
        steps.append(run_step(store, "v446-secret-guard", v446_command(args, store), args.timeout * 8))
        if steps[-1]["ok"]:
            steps.append(run_step(store, "v447-plan", v447_plan_command(args, store), args.timeout * 4))
        if len(steps) > 1 and steps[-1]["ok"]:
            packet = write_packet(store, args)
    classification = classify(args.command, steps, packet)
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
    for key in ("preflight_command", "live_command"):
        if key in packet:
            print(f"{key}: {packet[key]}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
