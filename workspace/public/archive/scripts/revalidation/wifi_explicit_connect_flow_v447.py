#!/usr/bin/env python3
"""V447 gated explicit Wi-Fi connect flow.

V447 ties the private credential path into one operator-safe command:
V446 repository secret guard, V443 private policy materialization, V444
preflight, then optional V445 live explicit scan/connect.
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
from android_hwservice_handoff_v424 import (
    DEFAULT_BOOT_BLOCK,
    DEFAULT_BRIDGE_HOST,
    DEFAULT_BRIDGE_PORT,
    DEFAULT_NATIVE_EXPECT_VERSION,
    DEFAULT_NATIVE_IMAGE,
    DEFAULT_REMOTE_ANDROID_IMAGE,
)
from android_hwservice_settled_handoff_v425 import (
    DEFAULT_BOOT_COMPLETE_TIMEOUT,
    DEFAULT_SETTLE_SLEEP,
)
from wifi_android_explicit_connect_live_v445 import DEFAULT_OUT_DIR as V445_DEFAULT_OUT_DIR


DEFAULT_OUT_DIR = Path("tmp/wifi/v447-explicit-connect-flow")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--policy", type=Path, default=None)
    parser.add_argument("--include-untracked-secret-scan", dest="include_untracked_secret_scan", action="store_true", default=True)
    parser.add_argument("--tracked-only-secret-scan", dest="include_untracked_secret_scan", action="store_false")
    parser.add_argument("--target-id", default="lab-primary")
    parser.add_argument("--security", choices=("open", "owe", "wpa2", "wpa3"), default="wpa2")
    parser.add_argument("--allow-read-wifi-env", action="store_true")
    parser.add_argument("--i-understand-wifi-secret-env", action="store_true")
    parser.add_argument("--allow-live-v445", action="store_true")
    parser.add_argument("--allow-android-boot-flash", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--i-understand-native-rollback", action="store_true")
    parser.add_argument("--allow-explicit-scan-connect", action="store_true")
    parser.add_argument("--i-understand-explicit-wifi-connect", action="store_true")
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
    parser.add_argument("--boot-complete-timeout", type=int, default=DEFAULT_BOOT_COMPLETE_TIMEOUT)
    parser.add_argument("--settle-sleep", type=int, default=DEFAULT_SETTLE_SLEEP)
    parser.add_argument("--enable-settle-sleep", type=float, default=20.0)
    parser.add_argument("--scan-settle-sleep", type=float, default=12.0)
    parser.add_argument("--connect-settle-sleep", type=float, default=35.0)
    parser.add_argument("--cleanup-settle-sleep", type=float, default=25.0)
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


def secret_values_allowed(args: argparse.Namespace) -> bool:
    return bool(args.allow_read_wifi_env and args.i_understand_wifi_secret_env)


def live_allowed(args: argparse.Namespace) -> bool:
    return bool(
        args.allow_live_v445
        and args.allow_android_boot_flash
        and args.assume_yes
        and args.i_understand_native_rollback
        and args.allow_explicit_scan_connect
        and args.i_understand_explicit_wifi_connect
        and secret_values_allowed(args)
    )


def live_missing_flags(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    if not args.allow_live_v445:
        missing.append("--allow-live-v445")
    if not args.allow_android_boot_flash:
        missing.append("--allow-android-boot-flash")
    if not args.assume_yes:
        missing.append("--assume-yes")
    if not args.i_understand_native_rollback:
        missing.append("--i-understand-native-rollback")
    if not args.allow_explicit_scan_connect:
        missing.append("--allow-explicit-scan-connect")
    if not args.i_understand_explicit_wifi_connect:
        missing.append("--i-understand-explicit-wifi-connect")
    if not args.allow_read_wifi_env:
        missing.append("--allow-read-wifi-env")
    if not args.i_understand_wifi_secret_env:
        missing.append("--i-understand-wifi-secret-env")
    return missing


def redact_output(text: str) -> str:
    redacted = text
    for name in ("A90_WIFI_SSID", "A90_WIFI_PSK"):
        value = os.environ.get(name, "")
        if value:
            redacted = redacted.replace(value, f"${name}")
    return redacted


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
    visible_command = " ".join(str(part) for part in command)
    body = "\n".join(
        [
            f"$ {visible_command}",
            redact_output(output).rstrip(),
            redact_output(error).rstrip(),
            f"rc={rc}",
            "",
        ]
    )
    path = store.write_text(f"steps/{name}.txt", body)
    return {
        "name": name,
        "command": visible_command,
        "ok": rc == 0,
        "rc": rc,
        "duration_sec": duration,
        "file": str(path.relative_to(store.run_dir)),
        "error": redact_output(error),
    }


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"decision": "missing", "pass": False, "_path": str(path)}
    except Exception as exc:  # noqa: BLE001
        return {"decision": "invalid", "pass": False, "error": str(exc), "_path": str(path)}


def nested_dir(store: EvidenceStore, name: str) -> Path:
    return store.run_dir / name


def policy_path(args: argparse.Namespace, store: EvidenceStore) -> Path:
    return repo_path(args.policy) if args.policy else nested_dir(store, "v443-private-policy") / "wifi-target-policy.private.json"


def guard_command(args: argparse.Namespace, store: EvidenceStore) -> list[str]:
    command = [
        "python3",
        "scripts/revalidation/wifi_private_secret_guard_v446.py",
        "--out-dir",
        str(nested_dir(store, "v446-secret-guard")),
    ]
    if args.include_untracked_secret_scan:
        command.append("--include-untracked")
    command.append("run")
    return command


def v443_command(args: argparse.Namespace, store: EvidenceStore) -> list[str]:
    command = [
        "python3",
        "scripts/revalidation/wifi_android_private_policy_materialize_v443.py",
        "--out-dir",
        str(nested_dir(store, "v443-private-policy")),
        "--target-id",
        args.target_id,
        "--security",
        args.security,
    ]
    if args.allow_read_wifi_env:
        command.append("--allow-read-wifi-env")
    if args.i_understand_wifi_secret_env:
        command.append("--i-understand-wifi-secret-env")
    command.append("run")
    return command


def v444_command(args: argparse.Namespace, store: EvidenceStore, policy: Path) -> list[str]:
    command = [
        "python3",
        "scripts/revalidation/wifi_android_explicit_connect_preflight_v444.py",
        "--out-dir",
        str(nested_dir(store, "v444-preflight")),
        "--policy",
        str(policy),
    ]
    if args.allow_read_wifi_env:
        command.append("--allow-read-wifi-env")
    if args.i_understand_wifi_secret_env:
        command.append("--i-understand-wifi-secret-env")
    command.append("run")
    return command


def v445_command(args: argparse.Namespace, store: EvidenceStore, policy: Path) -> list[str]:
    command = [
        "python3",
        "scripts/revalidation/wifi_android_explicit_connect_live_v445.py",
        "--out-dir",
        str(nested_dir(store, V445_DEFAULT_OUT_DIR.name)),
        "--policy",
        str(policy),
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
        "--enable-settle-sleep",
        str(args.enable_settle_sleep),
        "--scan-settle-sleep",
        str(args.scan_settle_sleep),
        "--connect-settle-sleep",
        str(args.connect_settle_sleep),
        "--cleanup-settle-sleep",
        str(args.cleanup_settle_sleep),
    ]
    for image in args.android_boot_image:
        command.extend(["--android-boot-image", str(image)])
    if args.serial:
        command.extend(["--serial", args.serial])
    if args.allow_android_boot_flash:
        command.append("--allow-android-boot-flash")
    if args.assume_yes:
        command.append("--assume-yes")
    if args.i_understand_native_rollback:
        command.append("--i-understand-native-rollback")
    if args.allow_read_wifi_env:
        command.append("--allow-read-wifi-env")
    if args.i_understand_wifi_secret_env:
        command.append("--i-understand-wifi-secret-env")
    if args.allow_explicit_scan_connect:
        command.append("--allow-explicit-scan-connect")
    if args.i_understand_explicit_wifi_connect:
        command.append("--i-understand-explicit-wifi-connect")
    command.append("run")
    return command


def planned_steps(args: argparse.Namespace) -> list[dict[str, Any]]:
    return [
        {"step": "v446-secret-guard", "mutates_device": False},
        {"step": "v443-private-policy", "mutates_device": False},
        {"step": "v444-preflight", "mutates_device": False},
        {"step": "v445-live", "mutates_device": True, "requires": live_missing_flags(args)},
    ]


def execute_flow(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any], str, bool]:
    steps: list[dict[str, Any]] = []
    context: dict[str, Any] = {
        "env_state": env_state(),
        "secret_values_allowed": secret_values_allowed(args),
        "live_allowed": live_allowed(args),
        "live_missing_flags": live_missing_flags(args),
        "policy_path": str(policy_path(args, store)),
    }
    if args.command == "plan":
        context["planned_steps"] = planned_steps(args)
        return [], context, "v447-explicit-connect-flow-plan-ready", True

    guard = run_step(store, "v446-secret-guard", guard_command(args, store), args.timeout * 8)
    steps.append(guard)
    context["v446"] = load_manifest(nested_dir(store, "v446-secret-guard") / "manifest.json")
    if not guard["ok"]:
        return steps, context, "v447-explicit-connect-flow-secret-guard-blocked", False

    if args.policy:
        policy = policy_path(args, store)
        context["v443_skipped"] = "policy provided"
    else:
        materialize = run_step(store, "v443-private-policy", v443_command(args, store), args.timeout * 4)
        steps.append(materialize)
        context["v443"] = load_manifest(nested_dir(store, "v443-private-policy") / "manifest.json")
        if not materialize["ok"]:
            return steps, context, "v447-explicit-connect-flow-v443-blocked", False
        policy = policy_path(args, store)

    preflight = run_step(store, "v444-preflight", v444_command(args, store, policy), args.timeout * 6)
    steps.append(preflight)
    context["v444"] = load_manifest(nested_dir(store, "v444-preflight") / "manifest.json")
    if not preflight["ok"]:
        return steps, context, "v447-explicit-connect-flow-preflight-blocked", False

    if not args.allow_live_v445:
        return steps, context, "v447-explicit-connect-flow-preflight-ready", True
    if not live_allowed(args):
        return steps, context, "v447-explicit-connect-flow-live-approval-required", False

    live = run_step(store, "v445-live", v445_command(args, store, policy), args.boot_complete_timeout + 900)
    steps.append(live)
    context["v445"] = load_manifest(nested_dir(store, V445_DEFAULT_OUT_DIR.name) / "manifest.json")
    return steps, context, ("v447-explicit-connect-flow-live-pass" if live["ok"] else "v447-explicit-connect-flow-live-failed"), bool(live["ok"])


def guardrails() -> list[str]:
    return [
        "V446 repository secret guard runs before private policy materialization",
        "V443 and V444 run before any optional V445 live boot/scan/connect",
        "V445 live requires explicit live and rollback approval flags",
        "secret values are redacted from nested step transcripts",
        "server exposure remains blocked",
    ]


def reason_for(decision: str, context: dict[str, Any]) -> str:
    if decision == "v447-explicit-connect-flow-plan-ready":
        return "explicit connect flow plan generated without mutation"
    if decision == "v447-explicit-connect-flow-secret-guard-blocked":
        return "V446 repository secret guard failed before credential materialization"
    if decision == "v447-explicit-connect-flow-v443-blocked":
        v443 = context.get("v443") or {}
        return str(v443.get("reason") or "V443 private policy materialization failed")
    if decision == "v447-explicit-connect-flow-preflight-blocked":
        v444 = context.get("v444") or {}
        return str(v444.get("reason") or "V444 explicit connect preflight failed")
    if decision == "v447-explicit-connect-flow-preflight-ready":
        return "V446/V443/V444 passed; V445 live was not requested"
    if decision == "v447-explicit-connect-flow-live-approval-required":
        return "V445 live was requested but required live approval flags are missing"
    if decision == "v447-explicit-connect-flow-live-pass":
        v445 = context.get("v445") or {}
        return str(v445.get("reason") or "V445 live explicit connect passed")
    if decision == "v447-explicit-connect-flow-live-failed":
        v445 = context.get("v445") or {}
        return str(v445.get("reason") or "V445 live explicit connect failed")
    return decision


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
        for name, data in (manifest["context"].get("env_state") or {}).items()
    ]
    return "\n".join(
        [
            "# V447 Explicit Wi-Fi Connect Flow",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
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
            "## Guardrails",
            "",
            *[f"- {item}" for item in manifest["guardrails"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    steps, context, decision, pass_ok = execute_flow(args, store)
    v445 = context.get("v445") or {}
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason_for(decision, context),
        "host": collect_host_metadata(),
        "context": context,
        "steps": steps,
        "guardrails": guardrails(),
        "device_commands_executed": bool(v445.get("device_commands_executed")),
        "device_mutations": bool(v445.get("device_mutations")),
        "wifi_bringup_executed": bool(v445.get("wifi_bringup_executed")),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
