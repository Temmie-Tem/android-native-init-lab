#!/usr/bin/env python3
"""Build a no-start approval packet for the first CNSS live start-only run."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, repo_path, run_capture
from a90harness.evidence import EvidenceStore
import wifi_cnss_start_only_runner as runner

DEFAULT_OUT_DIR = Path("tmp/wifi/v255-cnss-live-approval-packet")
DEFAULT_LIVE_OUT_DIR = Path("tmp/wifi/v255-cnss-live-start-only-run")
DEFAULT_EXPECT_VERSION = runner.DEFAULT_EXPECT_VERSION
DEFAULT_HELPER = runner.DEFAULT_HELPER
DEFAULT_HELPER_SHA256 = runner.DEFAULT_HELPER_SHA256
DEFAULT_RUNTIME_SEC = runner.DEFAULT_HELPER_TIMEOUT_SEC

REQUIRED_PROFILE = {
    "null_device_mode": "dev-null-selinux",
    "data_wifi_mode": "private-empty",
    "private_namespace_only": True,
}

READ_ONLY_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("version",),
    ("status",),
    ("bootstatus",),
    ("selftest", "verbose"),
    ("wifiinv", "full"),
    ("kernelinv", "summary"),
    ("netservice", "status"),
    ("cat", "/proc/net/dev"),
    ("stat", "/data/vendor/wifi"),
    ("run", "/cache/bin/toybox", "pidof", "cnss-daemon"),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(command: tuple[str, ...]) -> str:
    text = "-".join(command)
    text = re.sub(r"[^A-Za-z0-9_.+-]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-") or "command"


def runner_args(args: argparse.Namespace, command: str, *, approved: bool) -> argparse.Namespace:
    return argparse.Namespace(
        out_dir=args.out_dir,
        host=args.host,
        port=args.port,
        timeout=args.timeout,
        expect_version=args.expect_version,
        helper=args.helper,
        helper_sha256=args.helper_sha256,
        max_runtime_sec=args.max_runtime_sec,
        command=command,
        allow_daemon_start=approved,
        assume_yes=approved,
        i_understand_reboot_only_recovery=approved,
    )


def capture_commands(store: EvidenceStore, args: argparse.Namespace) -> dict[str, Any]:
    captures: list[dict[str, Any]] = []
    by_name: dict[str, dict[str, Any]] = {}
    for command in READ_ONLY_COMMANDS:
        name = safe_name(command)
        capture = run_capture(args, name, list(command), timeout=args.timeout)
        store.write_text(f"commands/{name}.txt", capture.text if capture.text else capture.error + "\n")
        data = capture_to_manifest(capture)
        captures.append(data)
        by_name[name] = data
    return {"captures": captures, "by_name": by_name}


def pidof_absent(capture: dict[str, Any] | None) -> bool:
    if not capture:
        return False
    return capture.get("rc") == 1 and capture.get("status") == "error"


def same_rc_status(left: dict[str, Any] | None, right: dict[str, Any] | None) -> bool:
    if not left or not right:
        return False
    return left.get("rc") == right.get("rc") and left.get("status") == right.get("status")


def no_wlan_interface(capture: dict[str, Any] | None) -> bool:
    if not capture:
        return False
    text = str(capture.get("text", ""))
    return re.search(r"^\s*wlan\S*:", text, re.MULTILINE) is None


def profile_matches(plan: dict[str, Any]) -> bool:
    materialization = plan.get("runtime_materialization", {})
    return all(materialization.get(key) == expected for key, expected in REQUIRED_PROFILE.items())


def argv_contains_required_profile(argv: list[str]) -> bool:
    joined = " ".join(argv)
    required_tokens = (
        "--null-device-mode dev-null-selinux",
        "--data-wifi-mode private-empty",
        "--allow-cnss-start-only",
    )
    return all(token in joined for token in required_tokens)


def render_approval_command(args: argparse.Namespace) -> str:
    parts = [
        "python3",
        "scripts/revalidation/wifi_cnss_start_only_runner.py",
        "--out-dir",
        str(args.live_out_dir),
        "--max-runtime-sec",
        str(args.max_runtime_sec),
        "run",
        "--allow-daemon-start",
        "--assume-yes",
        "--i-understand-reboot-only-recovery",
    ]
    return " ".join(shlex.quote(item) for item in parts) + "\n"


def render_rollback_checklist() -> str:
    return """# CNSS Start-Only Rollback Checklist

## Before Manual Live Run

- Confirm bridge/NCM control is working.
- Confirm `pidof cnss-daemon` is absent.
- Confirm no `wlan*` interface is unexpectedly active.
- Confirm battery/power and thermal state are acceptable.
- Keep TWRP/recovery access available.

## During Manual Live Run

- Do not start Wi-Fi scan/connect/link-up.
- Do not run `cnss_diag`.
- Do not run rfkill unblock.
- Do not bind/unbind ICNSS.
- Do not mutate firmware path or Android partitions.

## If Result Is start-only-pass

- Preserve the evidence directory.
- Confirm `pidof cnss-daemon` is absent after cleanup.
- Confirm postflight Wi-Fi inventory has no unexpected link-up.

## If Result Is start-only-runtime-gap

- Preserve stdout/stderr and postflight evidence.
- Treat the reported missing primitive as the next no-start planning input.
- Do not improvise property service, diag, rfkill, or ICNSS writes in the same run.

## If Result Is start-only-reboot-required Or Control Is Lost

- Stop automation.
- Do not use generic ICNSS bind/unbind as recovery.
- Reboot is the accepted recovery primitive.
- After recovery, re-run version/status/selftest/wifiinv/kernelinv before continuing.
"""


def render_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# CNSS Live Start Approval Packet\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: `{manifest['reason']}`\n",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`\n",
        f"- output: `{manifest['out_dir']}`\n\n",
        "## Proposed Manual Command\n\n",
        "```bash\n",
        manifest["approval_command"],
        "```\n\n",
        "## Gate Summary\n\n",
    ]
    for item in manifest["checks"]:
        lines.append(f"- {'PASS' if item['pass'] else 'FAIL'} `{item['name']}`: {item['detail']}\n")
    lines.extend(
        [
            "\n## Guardrails\n\n",
            "- This packet does not execute `cnss-daemon`.\n",
            "- Live execution still requires an explicit operator instruction.\n",
            "- Wi-Fi scan/connect/link-up/credential/DHCP/routing remain blocked.\n",
            "- `cnss_diag`, rfkill unblock, ICNSS bind/unbind, firmware mutation, Android partition writes, and automatic reboot remain blocked.\n",
        ]
    )
    return "".join(lines)


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    plan_args = runner_args(args, "plan", approved=False)
    approved_args = runner_args(args, "run", approved=True)
    noallow_args = runner_args(args, "run", approved=False)

    prereq_manifests, prereq_checks = runner.build_prerequisite_checks()
    dry_run_plan = runner.build_dry_run_plan(plan_args)
    approved_helper_argv = runner.helper_start_argv(approved_args)
    noallow_helper_argv = runner.helper_start_argv(noallow_args)
    approved_runner_command = render_approval_command(args)
    denied_matches = [pattern.pattern for pattern in runner.DENIED_TEXT_PATTERNS if pattern.search(" ".join(approved_helper_argv))]

    store.write_json("prerequisite-checks.json", {"checks": prereq_checks, "manifests": prereq_manifests})
    store.write_json("dry-run-plan.json", dry_run_plan)
    store.write_text("approval-command.sh", "#!/usr/bin/env bash\nset -euo pipefail\n" + approved_runner_command)
    store.write_text("rollback-checklist.md", render_rollback_checklist())

    command_evidence = capture_commands(store, args)
    before_pidof = command_evidence["by_name"].get("run-cache-bin-toybox-pidof-cnss-daemon")
    proc_net_dev = command_evidence["by_name"].get("cat-proc-net-dev")
    before_data_wifi = command_evidence["by_name"].get("stat-data-vendor-wifi")

    noallow_capture = run_capture(args, "helper-noallow", ["run", *noallow_helper_argv], timeout=args.timeout + args.max_runtime_sec + 20.0)
    store.write_text("commands/helper-noallow.txt", noallow_capture.text if noallow_capture.text else noallow_capture.error + "\n")
    noallow_observation = runner.build_start_observation(noallow_capture)
    store.write_json("helper-noallow-observation.json", noallow_observation)

    after_pidof_capture = run_capture(args, "pidof-cnss-daemon-after-noallow", ["run", "/cache/bin/toybox", "pidof", "cnss-daemon"], timeout=args.timeout)
    store.write_text("commands/pidof-cnss-daemon-after-noallow.txt", after_pidof_capture.text if after_pidof_capture.text else after_pidof_capture.error + "\n")
    after_pidof = capture_to_manifest(after_pidof_capture)
    after_data_wifi_capture = run_capture(args, "stat-data-vendor-wifi-after-noallow", ["stat", "/data/vendor/wifi"], timeout=args.timeout)
    store.write_text("commands/stat-data-vendor-wifi-after-noallow.txt", after_data_wifi_capture.text if after_data_wifi_capture.text else after_data_wifi_capture.error + "\n")
    after_data_wifi = capture_to_manifest(after_data_wifi_capture)

    checks = [
        {
            "name": "prerequisites-match",
            "pass": all(item.get("pass") for item in prereq_checks),
            "detail": f"{sum(1 for item in prereq_checks if item.get('pass'))}/{len(prereq_checks)} prerequisite manifests matched",
        },
        {
            "name": "runtime-materialization-profile",
            "pass": profile_matches(dry_run_plan),
            "detail": json.dumps(dry_run_plan.get("runtime_materialization", {}), ensure_ascii=False, sort_keys=True),
        },
        {
            "name": "approved-helper-argv-has-required-profile",
            "pass": argv_contains_required_profile(approved_helper_argv),
            "detail": " ".join(approved_helper_argv),
        },
        {
            "name": "approved-helper-argv-denied-patterns",
            "pass": not denied_matches,
            "detail": json.dumps(denied_matches, ensure_ascii=False),
        },
        {
            "name": "pidof-cnss-daemon-before",
            "pass": pidof_absent(before_pidof),
            "detail": json.dumps({"rc": before_pidof.get("rc") if before_pidof else None, "status": before_pidof.get("status") if before_pidof else None}, sort_keys=True),
        },
        {
            "name": "no-wlan-interface-before",
            "pass": no_wlan_interface(proc_net_dev),
            "detail": "no wlan* line in /proc/net/dev" if no_wlan_interface(proc_net_dev) else "wlan* interface present",
        },
        {
            "name": "helper-noallow-fail-closed",
            "pass": noallow_observation.get("helper_result") == "start-only-blocked"
            and noallow_observation.get("exec_attempted") is False
            and noallow_observation.get("postflight_safe") is True,
            "detail": json.dumps({
                "helper_result": noallow_observation.get("helper_result"),
                "exec_attempted": noallow_observation.get("exec_attempted"),
                "postflight_safe": noallow_observation.get("postflight_safe"),
                "helper_reason": noallow_observation.get("helper_reason"),
            }, ensure_ascii=False, sort_keys=True),
        },
        {
            "name": "pidof-cnss-daemon-after-noallow",
            "pass": pidof_absent(after_pidof),
            "detail": json.dumps({"rc": after_pidof.get("rc"), "status": after_pidof.get("status")}, sort_keys=True),
        },
        {
            "name": "real-data-wifi-state-unchanged",
            "pass": same_rc_status(before_data_wifi, after_data_wifi),
            "detail": json.dumps({
                "before_rc": before_data_wifi.get("rc") if before_data_wifi else None,
                "before_status": before_data_wifi.get("status") if before_data_wifi else None,
                "after_rc": after_data_wifi.get("rc"),
                "after_status": after_data_wifi.get("status"),
            }, sort_keys=True),
        },
    ]
    pass_ok = all(item["pass"] for item in checks)
    manifest = {
        "created": now_iso(),
        "mode": "no-start-live-approval-packet",
        "pass": pass_ok,
        "decision": "live-approval-packet-ready" if pass_ok else "live-approval-packet-blocked",
        "reason": "all no-start approval gates passed" if pass_ok else "one or more approval gates failed",
        "out_dir": str(out_dir),
        "daemon_start_executed": False,
        "host_metadata": collect_host_metadata(),
        "approval_command": approved_runner_command,
        "approved_helper_argv": approved_helper_argv,
        "noallow_helper_argv": noallow_helper_argv,
        "dry_run_plan": dry_run_plan,
        "prerequisite_checks": prereq_checks,
        "device_captures": command_evidence["captures"],
        "noallow_observation": noallow_observation,
        "pidof_after_noallow": after_pidof,
        "data_wifi_after_noallow": after_data_wifi,
        "checks": checks,
        "guardrails": [
            "no daemon execution by this packet",
            "manual live command is generated but not executed",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no cnss_diag",
            "no rfkill unblock",
            "no ICNSS bind/unbind",
            "no firmware mutation or persistent Android partition write",
            "no automatic reboot",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--live-out-dir", type=Path, default=DEFAULT_LIVE_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--max-runtime-sec", type=int, default=DEFAULT_RUNTIME_SEC)
    args = parser.parse_args()
    if args.max_runtime_sec < 1 or args.max_runtime_sec > 30:
        raise SystemExit("--max-runtime-sec must be 1..30")
    return args


def main() -> int:
    manifest = build_manifest(parse_args())
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {manifest['out_dir']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
