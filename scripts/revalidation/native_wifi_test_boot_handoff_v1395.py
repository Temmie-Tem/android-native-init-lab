#!/usr/bin/env python3
"""V1395 bounded live handoff for the V1393 Wi-Fi test boot artifact.

This runner flashes the V1393 test boot image, collects below-connect boot
evidence, and rolls back to the known v724 native boot image. It does not run
Wi-Fi scan/connect, use credentials, run DHCP/routes, or external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1395-wifi-test-boot-handoff"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1395_WIFI_TEST_BOOT_HANDOFF_2026-06-01.md"
DEFAULT_V1394_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1394-wifi-test-boot-artifact-sanity" / "manifest.json"
DEFAULT_TEST_IMAGE = REPO_ROOT / "tmp" / "wifi" / "v1393-wifi-test-boot" / "boot_linux_v1393_wifi_test.img"
DEFAULT_ROLLBACK_IMAGE = REPO_ROOT / "stage3" / "boot_linux_v724.img"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.69 (v1393-wifitest)"
ROLLBACK_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1393.log"
DEFAULT_TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1393.summary"
DEFAULT_DMESG_PATTERN = "A90v1393|A90v1397|subsystem_get|PCIe RC1|LTSSM|GPIO142|wlfw|FW ready|BDF|wlan0|mhi|ks"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def run_command(command: list[object],
                *,
                timeout: float,
                check: bool = False) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
    try:
        completed = subprocess.run(
            [str(item) for item in command],
            cwd=str(REPO_ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        ok = completed.returncode == 0
        if check and not ok:
            raise subprocess.CalledProcessError(
                completed.returncode,
                [str(item) for item in command],
                output=completed.stdout,
                stderr=completed.stderr,
            )
        return {
            "command": [str(item) for item in command],
            "started": started.isoformat(),
            "ended": now_iso(),
            "timeout": False,
            "rc": completed.returncode,
            "ok": ok,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": [str(item) for item in command],
            "started": started.isoformat(),
            "ended": now_iso(),
            "timeout": True,
            "rc": None,
            "ok": False,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def write_step(store: EvidenceStore, steps: list[dict[str, Any]], name: str, result: dict[str, Any]) -> None:
    clean = {
        "command": result["command"],
        "started": result["started"],
        "ended": result["ended"],
        "timeout": result["timeout"],
        "rc": result["rc"],
        "ok": result["ok"],
        "stdout_file": f"{name}.stdout.txt",
        "stderr_file": f"{name}.stderr.txt",
    }
    store.write_text(clean["stdout_file"], str(result.get("stdout") or ""))
    store.write_text(clean["stderr_file"], str(result.get("stderr") or ""))
    steps.append(clean)


def run_a90ctl_step(store: EvidenceStore,
                    steps: list[dict[str, Any]],
                    name: str,
                    command: list[object],
                    timeout: float) -> dict[str, Any]:
    result = run_command(command, timeout=timeout)
    if "[busy]" not in str(result.get("stdout") or ""):
        write_step(store, steps, name, result)
        return result

    hide = run_command(a90ctl_command(["hide"]), timeout=min(timeout, 20.0))
    write_step(store, steps, f"{name}-hide-on-busy", hide)
    retry = run_command(command, timeout=timeout)
    write_step(store, steps, name, retry)
    return retry


def a90ctl_command(command: list[str]) -> list[object]:
    return ["python3", "scripts/revalidation/a90ctl.py", *command]


def flash_command(image: Path, expect_version: str, *, from_native: bool) -> list[object]:
    command: list[object] = [
        "python3",
        "scripts/revalidation/native_init_flash.py",
        image,
        "--expect-version",
        expect_version,
        "--bridge-timeout",
        "240",
        "--recovery-timeout",
        "240",
    ]
    if from_native:
        command.append("--from-native")
    return command


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def preflight(args: argparse.Namespace) -> dict[str, Any]:
    v1394 = load_json(args.v1394_manifest)
    return {
        "v1394_manifest": display_path(args.v1394_manifest),
        "v1394_decision": v1394.get("decision", ""),
        "v1394_pass": bool(v1394.get("pass")),
        "test_image": display_path(args.test_image),
        "test_image_exists": args.test_image.exists(),
        "rollback_image": display_path(args.rollback_image),
        "rollback_image_exists": args.rollback_image.exists(),
    }


def collect_test_boot_evidence(args: argparse.Namespace,
                               store: EvidenceStore,
                               steps: list[dict[str, Any]]) -> dict[str, Any]:
    commands = {
        "test-version": a90ctl_command(["version"]),
        "test-status": a90ctl_command(["status"]),
        "test-selftest": a90ctl_command(["selftest"]),
        "test-bootstatus": a90ctl_command(["bootstatus"]),
        "test-v1393-log": a90ctl_command([
            "run",
            "/cache/bin/toybox",
            "cat",
            args.test_log_path,
        ]),
        "test-v1393-summary": a90ctl_command([
            "run",
            "/cache/bin/toybox",
            "cat",
            args.test_summary_path,
        ]),
        "test-v1393-dmesg": a90ctl_command([
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            f"dmesg | grep -Ei {args.dmesg_grep_pattern!r} | tail -240",
        ]),
        "test-wlan0": a90ctl_command([
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            "test -e /sys/class/net/wlan0 && echo wlan0=present || echo wlan0=absent",
        ]),
    }
    evidence: dict[str, Any] = {}
    for name, command in commands.items():
        result = run_a90ctl_step(store, steps, name, command, args.collect_timeout_sec)
        evidence[name] = {
            "ok": result["ok"],
            "rc": result["rc"],
            "timeout": result["timeout"],
            "stdout_file": f"{name}.stdout.txt",
            "stderr_file": f"{name}.stderr.txt",
        }
    return evidence


def rollback(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]]) -> dict[str, Any]:
    first = run_command(
        flash_command(args.rollback_image, args.expect_rollback_version, from_native=True),
        timeout=args.flash_timeout_sec,
    )
    write_step(store, steps, "rollback-from-native", first)
    if first["ok"]:
        return {"attempt": "from-native", "ok": True}

    second = run_command(
        flash_command(args.rollback_image, args.expect_rollback_version, from_native=False),
        timeout=args.flash_timeout_sec,
    )
    write_step(store, steps, "rollback-from-recovery", second)
    return {"attempt": "from-recovery", "ok": bool(second["ok"])}


def cycle_slug(cycle: str) -> str:
    return cycle.strip().lower()


def decision_label(cycle: str, suffix: str) -> str:
    return f"{cycle_slug(cycle)}-{suffix}"


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def classify(test_flash: dict[str, Any],
             evidence: dict[str, Any],
             rollback_result: dict[str, Any],
             store: EvidenceStore,
             cycle: str,
             expect_test_version: str) -> tuple[str, bool, str]:
    if not test_flash["ok"]:
        return (
            decision_label(cycle, "test-boot-flash-or-verify-failed"),
            False,
            "test boot flash/verify did not complete; inspect rollback evidence before retry",
        )
    test_version = store.path("test-version.stdout.txt").read_text(encoding="utf-8", errors="replace")
    dmesg = store.path("test-v1393-dmesg.stdout.txt").read_text(encoding="utf-8", errors="replace")
    wlan0 = store.path("test-wlan0.stdout.txt").read_text(encoding="utf-8", errors="replace")
    rc1_progress = any(
        marker in dmesg
        for marker in ("PCIe RC1 PHY is ready", "LTSSM_STATE", "PCIe RC1 Current")
    )
    firmware_progress = any(marker in dmesg for marker in ("FW ready", "BDF", "wlfw"))
    wlan0_present = "wlan0=present" in wlan0
    provider_trigger = "__subsystem_get: esoc0" in dmesg
    if expect_test_version not in test_version:
        return (
            decision_label(cycle, "test-boot-version-missing"),
            False,
            "test boot returned through bridge but expected version marker was missing",
        )
    if not rollback_result.get("ok"):
        return (
            decision_label(cycle, "test-boot-rollback-failed"),
            False,
            "test boot evidence collected but rollback did not verify",
        )
    if rc1_progress or firmware_progress or wlan0_present:
        return (
            decision_label(cycle, "test-boot-downstream-progress-rollback-pass"),
            True,
            "test boot produced downstream Wi-Fi/PCIe evidence and rollback verified",
        )
    if provider_trigger:
        return (
            decision_label(cycle, "test-boot-provider-trigger-no-downstream-rollback-pass"),
            True,
            "test boot reached the esoc0 provider trigger and rollback verified, but no RC1/MHI/WLFW/wlan0 progress marker appeared",
        )
    return (
        decision_label(cycle, "test-boot-no-downstream-progress-rollback-pass"),
        True,
        "test boot ran and rollback verified, but no MDM2AP/PCIe/MHI/WLFW/wlan0 progress marker appeared",
    )


def render_report(result: dict[str, Any]) -> str:
    cycle = str(result["cycle"])
    return "\n".join([
        f"# Native Init {cycle} Wi-Fi Test Boot Handoff",
        "",
        "## Summary",
        "",
        f"- Cycle: `{cycle}`",
        "- Type: bounded live test-boot handoff with rollback",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Safety Scope",
        "",
        "No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,",
        "PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was",
        "performed by this runner. Device mutation was limited to flashing the",
        "test boot image and rolling back to `stage3/boot_linux_v724.img`.",
        "",
        "## Images",
        "",
        f"- Test image: `{result['preflight']['test_image']}`",
        f"- Rollback image: `{result['preflight']['rollback_image']}`",
        "",
        "## Next",
        "",
        "Inspect the collected V1393 boot log and dmesg evidence before deciding",
        "whether to keep refining PID1 timing or proceed toward a later explicit",
        "Wi-Fi scan/connect gate.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1394-manifest", type=Path, default=DEFAULT_V1394_MANIFEST)
    parser.add_argument("--test-image", type=Path, default=DEFAULT_TEST_IMAGE)
    parser.add_argument("--rollback-image", type=Path, default=DEFAULT_ROLLBACK_IMAGE)
    parser.add_argument("--cycle", default="V1395")
    parser.add_argument("--post-boot-hold-sec", type=float, default=0.0)
    parser.add_argument("--expect-test-version", default=TEST_EXPECT_VERSION)
    parser.add_argument("--expect-rollback-version", default=ROLLBACK_EXPECT_VERSION)
    parser.add_argument("--test-log-path", default=DEFAULT_TEST_LOG_PATH)
    parser.add_argument("--test-summary-path", default=DEFAULT_TEST_SUMMARY_PATH)
    parser.add_argument("--dmesg-grep-pattern", default=DEFAULT_DMESG_PATTERN)
    parser.add_argument("--flash-timeout-sec", type=float, default=720.0)
    parser.add_argument("--collect-timeout-sec", type=float, default=120.0)
    parser.add_argument("--classify-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    steps: list[dict[str, Any]] = []
    pre = preflight(args)
    store.write_json("preflight.json", pre)
    if not pre["v1394_pass"] or not pre["test_image_exists"] or not pre["rollback_image_exists"]:
        result = {
            "cycle": args.cycle,
            "decision": decision_label(args.cycle, "preflight-blocked"),
            "pass": False,
            "reason": "V1394 pass, test image, or rollback image missing",
            "preflight": pre,
            "steps": steps,
            "out_dir": display_path(args.out_dir),
        }
        store.write_json("manifest.json", result)
        args.report_path.write_text(render_report(result), encoding="utf-8")
        print(json.dumps({"decision": result["decision"], "pass": False}, indent=2))
        return 1

    if args.classify_only:
        evidence = {
            name: {"stdout_file": f"{name}.stdout.txt"}
            for name in (
                "test-version",
                "test-status",
                "test-selftest",
                "test-bootstatus",
                "test-v1393-log",
                "test-v1393-summary",
                "test-v1393-dmesg",
                "test-wlan0",
            )
        }
        test_version_path = store.path("test-version.stdout.txt")
        rollback_path = store.path("rollback-from-native.stdout.txt")
        test_flash = {
            "ok": test_version_path.exists() and args.expect_test_version in test_version_path.read_text(encoding="utf-8", errors="replace"),
        }
        rollback_result = {
            "attempt": "existing",
            "ok": rollback_path.exists() and args.expect_rollback_version in rollback_path.read_text(encoding="utf-8", errors="replace"),
        }
        label, pass_ok, reason = classify(test_flash,
                                          evidence,
                                          rollback_result,
                                          store,
                                          args.cycle,
                                          args.expect_test_version)
        result = {
            "cycle": args.cycle,
            "decision": label,
            "pass": pass_ok,
            "reason": reason,
            "preflight": pre,
            "test_flash_ok": bool(test_flash["ok"]),
            "evidence": evidence,
            "rollback": rollback_result,
            "steps": [],
            "out_dir": display_path(args.out_dir),
            "classify_only": True,
        }
        store.write_json("manifest.json", result)
        store.write_text("summary.md", render_report(result))
        args.report_path.write_text(render_report(result), encoding="utf-8")
        print(json.dumps({"decision": label, "pass": pass_ok, "rollback": rollback_result}, indent=2))
        return 0 if pass_ok else 1

    test_flash = run_command(
        flash_command(args.test_image, args.expect_test_version, from_native=True),
        timeout=args.flash_timeout_sec,
    )
    write_step(store, steps, "test-flash-from-native", test_flash)

    evidence: dict[str, Any] = {}
    if test_flash["ok"]:
        if args.post_boot_hold_sec > 0:
            hold = run_command(
                [
                    "python3",
                    "-c",
                    f"import time; time.sleep({args.post_boot_hold_sec!r})",
                ],
                timeout=args.post_boot_hold_sec + 10.0,
            )
            write_step(store, steps, "post-boot-hold", hold)
        evidence = collect_test_boot_evidence(args, store, steps)

    rollback_result = rollback(args, store, steps)
    label, pass_ok, reason = classify(test_flash,
                                      evidence,
                                      rollback_result,
                                      store,
                                      args.cycle,
                                      args.expect_test_version)
    result = {
        "cycle": args.cycle,
        "decision": label,
        "pass": pass_ok,
        "reason": reason,
        "preflight": pre,
        "test_flash_ok": bool(test_flash["ok"]),
        "evidence": evidence,
        "rollback": rollback_result,
        "steps": steps,
        "out_dir": display_path(args.out_dir),
    }
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_report(result))
    args.report_path.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({"decision": label, "pass": pass_ok, "rollback": rollback_result}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
