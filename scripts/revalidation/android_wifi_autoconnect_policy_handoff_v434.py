#!/usr/bin/env python3
"""V434 Android Wi-Fi auto-connect policy handoff.

This wrapper reruns the V433 read-only containment handoff and then selects the
V434 policy from the fresh V433 evidence.  It does not add any Wi-Fi enable,
scan, connect, credential, route mutation, external packet probe, or server
exposure step.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from android_hwservice_handoff_v424 import (
    DEFAULT_BOOT_BLOCK,
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_NATIVE_EXPECT_VERSION,
    DEFAULT_NATIVE_IMAGE,
    DEFAULT_REMOTE_ANDROID_IMAGE,
)


DEFAULT_OUT_DIR = Path("tmp/wifi/v434-android-wifi-autoconnect-policy-handoff")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--native-image", type=Path, default=DEFAULT_NATIVE_IMAGE)
    parser.add_argument("--native-expect-version", default=DEFAULT_NATIVE_EXPECT_VERSION)
    parser.add_argument("--android-boot-image", action="append", type=Path, default=[])
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--boot-block", default=DEFAULT_BOOT_BLOCK)
    parser.add_argument("--remote-android-image", default=DEFAULT_REMOTE_ANDROID_IMAGE)
    parser.add_argument("--bridge-host", default=DEFAULT_BRIDGE_HOST)
    parser.add_argument("--bridge-port", type=int, default=DEFAULT_BRIDGE_PORT)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--recovery-timeout", type=int, default=180)
    parser.add_argument("--android-timeout", type=int, default=300)
    parser.add_argument("--boot-complete-timeout", type=int, default=300)
    parser.add_argument("--settle-sleep", type=int, default=20)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--sample-interval", type=float, default=10.0)
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("dry-run")
    subparsers.add_parser("run")
    return parser.parse_args()


def display_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run_process(command: list[str], timeout: int) -> tuple[int | None, str, str, float]:
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
        return result.returncode, result.stdout, "", time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, output, f"timeout after {timeout}s", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - evidence wrapper preserves failure detail
        return None, "", str(exc), time.monotonic() - started


def write_command(store: EvidenceStore, name: str, command: list[str], rc: int | None, text: str, error: str, duration: float) -> dict[str, Any]:
    body = "\n".join(
        [
            f"$ {display_command(command)}",
            (text or error).rstrip(),
            f"rc={rc}",
            "",
        ]
    )
    path = store.write_text(f"commands/{name}.txt", body)
    return {
        "name": name,
        "command": display_command(command),
        "rc": rc,
        "ok": rc == 0,
        "duration_sec": duration,
        "file": str(path.relative_to(store.run_dir)),
        "error": error,
    }


def v433_out_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "v433-containment-handoff"


def v434_policy_out_dir(store: EvidenceStore) -> Path:
    return store.run_dir / "v434-policy"


def build_v433_command(args: argparse.Namespace, store: EvidenceStore, command: str) -> list[str]:
    result = [
        "python3",
        "scripts/revalidation/android_wifi_autoconnect_containment_handoff_v433.py",
        "--out-dir",
        str(v433_out_dir(store)),
        "--native-image",
        str(args.native_image),
        "--native-expect-version",
        args.native_expect_version,
        "--adb",
        args.adb,
        "--boot-block",
        args.boot_block,
        "--remote-android-image",
        args.remote_android_image,
        "--bridge-host",
        args.bridge_host,
        "--bridge-port",
        str(args.bridge_port),
        "--timeout",
        str(args.timeout),
        "--recovery-timeout",
        str(args.recovery_timeout),
        "--android-timeout",
        str(args.android_timeout),
        "--boot-complete-timeout",
        str(args.boot_complete_timeout),
        "--settle-sleep",
        str(args.settle_sleep),
        "--samples",
        str(max(1, args.samples)),
        "--sample-interval",
        str(max(0.0, args.sample_interval)),
    ]
    for image in args.android_boot_image:
        result.extend(["--android-boot-image", str(image)])
    if args.serial:
        result.extend(["--serial", args.serial])
    if args.allow_android_boot_flash:
        result.append("--allow-android-boot-flash")
    if args.assume_yes:
        result.append("--assume-yes")
    if args.i_understand_native_rollback:
        result.append("--i-understand-native-rollback")
    result.append(command)
    return result


def build_policy_command(args: argparse.Namespace, store: EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_android_autoconnect_policy_v434.py",
        "--out-dir",
        str(v434_policy_out_dir(store)),
        "--v433-manifest",
        str(v433_out_dir(store) / "manifest.json"),
        "run",
    ]


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"decision": "missing", "pass": False, "path": str(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    data["path"] = str(path)
    return data


def run_mode(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any], str, bool]:
    records: list[dict[str, Any]] = []
    if args.command == "plan":
        v433_command = build_v433_command(args, store, "plan")
        policy_plan = [
            "python3",
            "scripts/revalidation/wifi_android_autoconnect_policy_v434.py",
            "--out-dir",
            str(v434_policy_out_dir(store)),
            "plan",
        ]
        records.append(write_command(store, "v433-plan", v433_command, 0, "[plan] not executed\n", "", 0.0))
        records.append(write_command(store, "v434-policy-plan", policy_plan, 0, "[plan] not executed\n", "", 0.0))
        context = {"v433_out_dir": str(v433_out_dir(store)), "v434_policy_out_dir": str(v434_policy_out_dir(store))}
        return records, context, "v434-handoff-plan-ready", True

    v433_subcommand = "run" if args.command == "run" else "dry-run"
    v433_command = build_v433_command(args, store, v433_subcommand)
    rc, text, error, duration = run_process(v433_command, timeout=max(900, args.android_timeout + args.recovery_timeout + 360))
    records.append(write_command(store, "v433-containment-handoff", v433_command, rc, text, error, duration))
    v433_manifest = load_manifest(v433_out_dir(store) / "manifest.json")
    context: dict[str, Any] = {
        "v433_out_dir": str(v433_out_dir(store)),
        "v434_policy_out_dir": str(v434_policy_out_dir(store)),
        "v433": {
            "path": v433_manifest.get("path"),
            "decision": v433_manifest.get("decision"),
            "pass": v433_manifest.get("pass"),
            "reason": v433_manifest.get("reason"),
        },
    }
    if rc != 0:
        return records, context, "v434-handoff-v433-failed", False
    if args.command == "dry-run":
        return records, context, "v434-handoff-dryrun-ready", True

    policy_command = build_policy_command(args, store)
    rc, text, error, duration = run_process(policy_command, timeout=120)
    records.append(write_command(store, "v434-policy", policy_command, rc, text, error, duration))
    policy_manifest = load_manifest(v434_policy_out_dir(store) / "manifest.json")
    context["policy"] = {
        "path": policy_manifest.get("path"),
        "decision": policy_manifest.get("decision"),
        "pass": policy_manifest.get("pass"),
        "reason": policy_manifest.get("reason"),
        "policy": (policy_manifest.get("policy") or {}).get("policy"),
        "next_gate": (policy_manifest.get("policy") or {}).get("next_gate"),
        "evidence_state": (policy_manifest.get("policy") or {}).get("evidence_state"),
    }
    if rc != 0:
        return records, context, "v434-handoff-policy-failed", False
    return records, context, str(policy_manifest.get("decision") or "v434-handoff-policy-missing"), bool(policy_manifest.get("pass"))


def reason_for(decision: str, context: dict[str, Any]) -> str:
    policy = context.get("policy") or {}
    if policy.get("decision") == decision:
        return str(policy.get("reason") or decision)
    return {
        "v434-handoff-plan-ready": "execution plan generated without device mutation",
        "v434-handoff-dryrun-ready": "dry-run recorded V433 handoff without device mutation",
        "v434-handoff-v433-failed": "fresh V433 containment handoff failed",
        "v434-handoff-policy-failed": "V434 host-side policy selection failed",
    }.get(decision, decision)


def render_summary(manifest: dict[str, Any]) -> str:
    command_rows = [
        [item["name"], "ok" if item["ok"] else "fail", str(item["rc"]), f"{item['duration_sec']:.3f}s", item["file"]]
        for item in manifest["commands"]
    ]
    policy = manifest["context"].get("policy") or {}
    evidence_state = policy.get("evidence_state") or {}
    state_rows = [[key, str(value)] for key, value in evidence_state.items()]
    return "\n".join(
        [
            "# V434 Android Wi-Fi Auto-connect Policy Handoff",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- policy: `{policy.get('policy', '-')}`",
            f"- next_gate: `{policy.get('next_gate', '-')}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Evidence State",
            "",
            markdown_table(["item", "value"], state_rows if state_rows else [["-", "-"]]),
            "",
            "## Commands",
            "",
            markdown_table(["name", "status", "rc", "duration", "file"], command_rows if command_rows else [["-", "-", "-", "-", "-"]]),
            "",
            "## Guardrails",
            "",
            "- V434 only wraps V433 read-only containment and host-side policy selection.",
            "- No Wi-Fi enable/disable, scan/connect, credential, DHCP/routing mutation, external probe, or server exposure is added.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    records, context, decision, pass_ok = run_mode(args, store)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason_for(decision, context),
        "host": collect_host_metadata(),
        "context": context,
        "commands": records,
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run",
        "wifi_bringup_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {manifest['reason']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
