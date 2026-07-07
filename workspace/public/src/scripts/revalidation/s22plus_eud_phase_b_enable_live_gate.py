#!/usr/bin/env python3
"""Guarded S22+ EUD Phase-B reversible enable gate.

Host/read-only modes:

  --offline-check     verify the inert policy draft markers;
  --print-plan        print the attended operator plan;
  --read-only-check   verify current Android/root, Magisk boot hash, and EUD
                      state without requiring AGENTS.md policy.

Live mode, once separately authorized:

  --live              write 1 to /sys/module/eud/parameters/enable, collect
                      host USB/dmesg evidence, then write 0 back.

No flash, no reboot, no partition write, no module insertion, and no native-init
boot candidate is performed by this helper.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from s22plus_m3_observable_live_gate import (
    DEFAULT_ODIN,
    DEFAULT_RUN_ROOT,
    adb_exec_out,
    adb_shell,
    append_log,
    repo_root,
    require_current_android,
    resolve,
    run,
    utc_now,
)
from s22plus_m5_usb_acm_live_gate import verify_android_stability
from s22plus_sec_debug_mid_sysrq_gate import verify_current_boot_hash


EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"
LIVE_ACK_TOKEN = "S22PLUS-EUD-PHASE-B-ENABLE-LIVE-GATE"
EUD_ENABLE_PARAM = "/sys/module/eud/parameters/enable"
EUD_TTY = "/dev/ttyEUD0"
EUD_PLATFORM = "/sys/devices/platform/soc/88e0000.qcom,msm-eud"
POLICY_DRAFT = Path("docs/operations/S22PLUS_EUD_PHASE_B_ENABLE_AGENTS_EXCEPTION_DRAFT_2026-07-08.md")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_eud_phase_b_enable_{stamp}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def redact(text: str) -> str:
    text = re.sub(r"RFCT[0-9A-Z]+", "<REDACTED_SERIAL>", text)
    text = re.sub(r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", "<REDACTED_MAC>", text)
    return text


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def host_command(run_dir: Path, log_path: Path, label: str, argv: list[str | Path], timeout: float) -> dict[str, Any]:
    completed = run(argv, timeout=timeout)
    text = redact(completed.stdout + completed.stderr)
    write_text(run_dir / "host" / f"{label}.txt", text)
    eud_hint = bool(re.search(r"\bEUD\b|Embedded USB Debug|Qualcomm.*debug|05c6:", text, re.IGNORECASE))
    summary = {
        "label": label,
        "rc": completed.returncode,
        "bytes": len(text.encode("utf-8", errors="replace")),
        "eud_usb_hint": eud_hint,
    }
    append_log(log_path, f"host_{label}={json.dumps(summary, sort_keys=True)}")
    return summary


def collect_host_state(run_dir: Path, log_path: Path, label: str, odin: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "label": label,
        "timestamp_utc": utc_now(),
        "lsusb": host_command(run_dir, log_path, f"{label}_lsusb", ["lsusb"], 10.0),
        "dmesg_tail": host_command(
            run_dir,
            log_path,
            f"{label}_dmesg_tail",
            ["bash", "-lc", "dmesg -T 2>/dev/null | tail -n 260 || true"],
            10.0,
        ),
        "ip_link": host_command(run_dir, log_path, f"{label}_ip_link", ["ip", "-j", "link"], 10.0),
        "adb_devices": host_command(run_dir, log_path, f"{label}_adb_devices", ["adb", "devices", "-l"], 10.0),
    }
    if odin.is_file():
        summary["odin_l"] = host_command(run_dir, log_path, f"{label}_odin_l", [odin, "-l"], 10.0)
    summary["host_eud_usb_hint"] = any(
        isinstance(item, dict) and item.get("eud_usb_hint") for item in summary.values()
    )
    append_log(log_path, f"host_state_{label}={json.dumps(summary, sort_keys=True)}")
    return summary


def adb_su_text(serial: str, command: str, *, timeout: float = 30.0) -> tuple[int, str]:
    result = adb_exec_out(command, serial=serial, timeout=timeout)
    text = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    return result.returncode, redact(text)


def collect_eud_state(run_dir: Path, log_path: Path, serial: str, label: str) -> dict[str, Any]:
    command = "\n".join(
        [
            "set -u",
            f"echo EUD_ENABLE_PARAM={EUD_ENABLE_PARAM}",
            f"ls -l {EUD_ENABLE_PARAM} 2>&1 || true",
            f"printf 'enable_value='; cat {EUD_ENABLE_PARAM} 2>/dev/null || echo __MISSING__",
            f"printf 'tty='; ls -l {EUD_TTY} 2>&1 || true",
            f"printf 'tty_console='; cat {EUD_PLATFORM}/tty/ttyEUD0/console 2>/dev/null || echo __MISSING__",
            f"printf 'runtime_status='; cat {EUD_PLATFORM}/power/runtime_status 2>/dev/null || echo __MISSING__",
            "printf 'proc_modules='; cat /proc/modules 2>/dev/null | grep -i '^eud ' || true",
            "printf 'platform_uevent='; cat /sys/bus/platform/devices/88e0000.qcom,msm-eud/uevent 2>/dev/null || true",
            "printf 'extcon='; find /sys/devices/platform/soc/88e0000.qcom,msm-eud -maxdepth 4 -path '*/extcon*' -print 2>/dev/null | sort | head -40",
            "printf 'dmesg_eud='; dmesg | grep -Ei '(^|[^A-Za-z])eud([^A-Za-z]|$)|Embedded USB|ttyEUD|msm-eud|qcom_scm_io' | tail -120 || true",
        ]
    )
    rc, text = adb_su_text(serial, command, timeout=45.0)
    write_text(run_dir / "android" / f"{label}_eud_state.txt", text)
    enable_matches = re.findall(r"enable_value=([0-9]+)", text)
    enable_value = int(enable_matches[-1]) if enable_matches else None
    summary = {
        "label": label,
        "timestamp_utc": utc_now(),
        "rc": rc,
        "bytes": len(text.encode("utf-8", errors="replace")),
        "enable_param_present": EUD_ENABLE_PARAM in text and "__MISSING__" not in text.split("enable_value=", 1)[-1].splitlines()[0],
        "enable_value": enable_value,
        "tty_eud_present": "ttyEUD0" in text,
        "tty_console_yes": "tty_console=Y" in text,
        "module_loaded": "proc_modules=eud " in text,
        "platform_bound": "DRIVER=msm-eud" in text,
        "secure_path_hint": "qcom_scm_io" in text or "secure" in text.lower(),
    }
    append_log(log_path, f"eud_state_{label}={json.dumps(summary, sort_keys=True)}")
    return summary


def write_eud_enable(serial: str, value: int, log_path: Path, label: str) -> dict[str, Any]:
    if value not in (0, 1):
        raise ValueError(value)
    command = f"printf '{value}\\n' > {EUD_ENABLE_PARAM} && printf 'after=' && cat {EUD_ENABLE_PARAM}"
    rc, text = adb_su_text(serial, command, timeout=20.0)
    append_log(log_path, f"{label}_write_eud_enable_value={value} rc={rc}")
    append_log(log_path, text)
    after_matches = re.findall(r"after=([0-9]+)", text)
    after_value = int(after_matches[-1]) if after_matches else None
    return {
        "label": label,
        "requested": value,
        "rc": rc,
        "after_value": after_value,
        "text": text,
    }


def required_policy_markers() -> list[str]:
    return [
        "S22+ EUD Phase-B reversible enable only",
        "workspace/public/src/scripts/revalidation/s22plus_eud_phase_b_enable_live_gate.py",
        EXPECTED_TARGET,
        LIVE_ACK_TOKEN,
        EUD_ENABLE_PARAM,
        "/dev/ttyEUD0",
        "write 1",
        "write 0",
        "restore enable=0",
        "no flash",
        "no reboot",
        "no partition write",
        "no native-init boot candidate",
        "no module insertion",
        "host lsusb",
    ]


def verify_text_markers(text: str, source: str, log_path: Path) -> None:
    normalized = " ".join(text.split())
    missing = [item for item in required_policy_markers() if item not in normalized]
    append_log(log_path, f"{source}_missing={missing}")
    if missing:
        raise SystemExit(f"{source} missing EUD Phase-B markers: {missing}")


def verify_policy_draft(root: Path, log_path: Path) -> None:
    draft = root / POLICY_DRAFT
    if not draft.is_file():
        raise SystemExit(f"inert policy draft missing: {draft}")
    verify_text_markers(draft.read_text(encoding="utf-8"), "policy_draft", log_path)


def verify_agents_exception(root: Path, log_path: Path) -> None:
    verify_text_markers((root / "AGENTS.md").read_text(encoding="utf-8"), "agents_exception", log_path)


def print_plan() -> None:
    script = "workspace/public/src/scripts/revalidation/s22plus_eud_phase_b_enable_live_gate.py"
    print("S22+ EUD Phase-B reversible enable plan:")
    print(f"1. Run read-only check to verify Android/root, Magisk boot hash, {EUD_ENABLE_PARAM}, and {EUD_TTY}.")
    print(f"   PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 {script} --read-only-check")
    print("2. Promote the narrow AGENTS.md exception only after operator approval.")
    print("3. Run live reversible enable:")
    print(f"   PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 {script} --live --ack {LIVE_ACK_TOKEN}")
    print(f"4. Helper will write 1 to {EUD_ENABLE_PARAM}, collect host lsusb/dmesg, then write 0 back.")
    print("Scope: no flash, no reboot, no partition write, no module insertion, no native-init candidate.")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--odin", type=Path, default=DEFAULT_ODIN)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--serial")
    parser.add_argument("--android-stability-samples", type=int, default=4)
    parser.add_argument("--android-stability-interval-sec", type=float, default=3.0)
    parser.add_argument("--post-enable-wait-sec", type=float, default=5.0)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--read-only-check", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--ack")
    args = parser.parse_args(argv)

    modes = sum(1 for enabled in (args.offline_check, args.print_plan, args.read_only_check, args.live) if enabled)
    if modes > 1:
        raise SystemExit("--offline-check, --print-plan, --read-only-check, and --live are mutually exclusive")

    root = repo_root()
    run_dir = resolve_run_dir(root, args.run_dir)
    log_path = run_dir / "s22plus_eud_phase_b_enable_live_gate.txt"
    append_log(log_path, f"=== {utc_now()} s22plus EUD Phase-B enable live gate ===")
    append_log(log_path, f"target={EXPECTED_TARGET}")
    odin = resolve(root, args.odin)

    if args.offline_check:
        verify_policy_draft(root, log_path)
        append_log(log_path, "offline_check=ok device_action=0")
        print(f"offline-check ok: inert policy draft verified; log={display_path(log_path)}")
        return 0

    if args.print_plan:
        verify_policy_draft(root, log_path)
        print_plan()
        append_log(log_path, "print_plan=ok device_action=0")
        return 0

    if not args.read_only_check:
        verify_agents_exception(root, log_path)

    serial = require_current_android(log_path, args.serial)
    verify_android_stability(log_path, serial, args.android_stability_samples, args.android_stability_interval_sec)
    verify_current_boot_hash(log_path, serial)
    before = collect_eud_state(run_dir, log_path, serial, "before")
    host_before = collect_host_state(run_dir, log_path, "before", odin)

    if args.read_only_check:
        ok = before["enable_param_present"] and before["enable_value"] in (0, 1) and before["tty_eud_present"]
        summary = {"before": before, "host_before": host_before, "ok": bool(ok), "writes_performed": False}
        write_text(run_dir / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(
            f"read-only check {'ok' if ok else 'failed'}: "
            f"enable={before.get('enable_value')} ttyEUD0={int(before.get('tty_eud_present'))}; "
            f"log={display_path(log_path)}"
        )
        return 0 if ok else 2

    if not args.live:
        print(
            "dry-run ok: AGENTS exception, Android/root, boot hash, EUD state, and host baseline verified; "
            f"log={display_path(log_path)}"
        )
        return 0

    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit(f"--live requires --ack {LIVE_ACK_TOKEN}")
    if not before["enable_param_present"] or before["enable_value"] not in (0, 1):
        raise SystemExit(f"EUD enable param not in a writable known state: {before}")

    enabled = False
    enable_result: dict[str, Any] | None = None
    disable_result: dict[str, Any] | None = None
    try:
        enable_result = write_eud_enable(serial, 1, log_path, "enable")
        enabled = enable_result["rc"] == 0 and enable_result.get("after_value") == 1
        time.sleep(args.post_enable_wait_sec)
        after_enable = collect_eud_state(run_dir, log_path, serial, "after_enable")
        host_after_enable = collect_host_state(run_dir, log_path, "after_enable", odin)
    finally:
        if enabled or enable_result is not None:
            disable_result = write_eud_enable(serial, 0, log_path, "disable")
            time.sleep(1.0)
    after_disable = collect_eud_state(run_dir, log_path, serial, "after_disable")
    host_after_disable = collect_host_state(run_dir, log_path, "after_disable", odin)

    restored = disable_result is not None and disable_result["rc"] == 0 and after_disable.get("enable_value") == 0
    host_eud_hint = bool(host_after_enable.get("host_eud_usb_hint")) if "host_after_enable" in locals() else False
    summary = {
        "before": before,
        "host_before": host_before,
        "enable_result": {k: v for k, v in (enable_result or {}).items() if k != "text"},
        "after_enable": locals().get("after_enable"),
        "host_after_enable": locals().get("host_after_enable"),
        "disable_result": {k: v for k, v in (disable_result or {}).items() if k != "text"},
        "after_disable": after_disable,
        "host_after_disable": host_after_disable,
        "restored_enable_0": restored,
        "host_eud_usb_hint": host_eud_hint,
    }
    write_text(run_dir / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(
        "EUD Phase-B live completed; "
        f"enabled={int(enabled)} restored_enable_0={int(restored)} host_eud_usb_hint={int(host_eud_hint)}; "
        f"log={display_path(log_path)}"
    )
    if not restored:
        return 6
    return 0 if host_eud_hint else 10


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
