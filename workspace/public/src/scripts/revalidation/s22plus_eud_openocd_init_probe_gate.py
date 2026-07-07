#!/usr/bin/env python3
"""Guarded S22+ EUD/OpenOCD init-probe gate.

Default mode is host-only preflight:

- re-run the SM8450 target-cfg audit;
- re-run the EUD OpenOCD host audit with the private EUD OpenOCD build and the
  public SM8450 script directory;
- do not touch the device, do not write sysfs, do not flash, and do not run
  OpenOCD init.

Live mode is intentionally inert until a future AGENTS.md exception is promoted.
When active, it still refuses to run OpenOCD unless the host audit reports a
current host EUD USB hint and all cfg/tool gates are present.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import s22plus_eud_openocd_host_audit as host_audit
import s22plus_sm8450_openocd_target_cfg_audit as cfg_audit


DEFAULT_RUN_ROOT = Path("workspace/private/runs")
DEFAULT_OPENOCD = Path("workspace/private/tools/linux-msm-openocd-eud/install/bin/openocd")
DEFAULT_PRIVATE_SCRIPT_DIR = Path("workspace/private/tools/linux-msm-openocd-eud/install/share/openocd/scripts")
DEFAULT_PUBLIC_SCRIPT_DIR = Path("workspace/public/src/openocd")
DEFAULT_TARGET_CFG = "target/qualcomm/sm8450_s22plus_romtable.cfg"
DEFAULT_INTERFACE_CFG = "interface/eud.cfg"
POLICY_DRAFT = Path("docs/operations/S22PLUS_EUD_OPENOCD_INIT_PROBE_AGENTS_EXCEPTION_DRAFT_2026-07-08.md")
LIVE_ACK_TOKEN = "S22PLUS-EUD-OPENOCD-INIT-PROBE-LIVE-GATE"
EXPECTED_TARGET = "SM-S906N/g0q/S906NKSS7FYG8"


def repo_root() -> Path:
    return host_audit.repo_root()


def resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def resolve_run_dir(root: Path, requested: Path | None) -> Path:
    if requested is not None:
        run_dir = resolve(root, requested)
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir
    stamp = host_audit.utc_now().replace("-", "").replace(":", "").replace("Z", "Z")
    base = resolve(root, DEFAULT_RUN_ROOT / f"s22plus_eud_openocd_init_probe_{stamp}")
    for suffix in range(100):
        run_dir = base if suffix == 0 else Path(f"{base}_{suffix:02d}")
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            continue
        return run_dir
    raise SystemExit(f"could not allocate unique run directory under {base.parent}")


def policy_markers() -> list[str]:
    return [
        "S22+ EUD OpenOCD Init Probe",
        LIVE_ACK_TOKEN,
        "workspace/public/src/scripts/revalidation/s22plus_eud_openocd_init_probe_gate.py",
        str(DEFAULT_OPENOCD),
        str(DEFAULT_PRIVATE_SCRIPT_DIR),
        str(DEFAULT_PUBLIC_SCRIPT_DIR),
        DEFAULT_INTERFACE_CFG,
        DEFAULT_TARGET_CFG,
        "host_openocd_eud_ready_to_probe",
        "bounded OpenOCD init",
        "debug attach/halt side effect",
        "no flash",
        "no reboot",
        "no partition write",
        "no EUD sysfs write",
        "no memory write commands",
    ]


def missing_policy_markers(text: str) -> list[str]:
    normalized = " ".join(text.split())
    return [marker for marker in policy_markers() if marker not in normalized]


def verify_policy_file(path: Path, *, active: bool) -> list[str]:
    if not path.is_file():
        return [f"missing-policy-file:{path}"]
    missing = missing_policy_markers(path.read_text(encoding="utf-8"))
    return missing


def openocd_base_args(openocd: Path, private_script_dir: Path, public_script_dir: Path) -> list[str]:
    return [
        str(openocd),
        "-s",
        str(private_script_dir),
        "-s",
        str(public_script_dir),
        "-f",
        DEFAULT_INTERFACE_CFG,
        "-f",
        DEFAULT_TARGET_CFG,
    ]


def openocd_probe_args(openocd: Path, private_script_dir: Path, public_script_dir: Path) -> list[str]:
    return openocd_base_args(openocd, private_script_dir, public_script_dir) + [
        "-c",
        "init",
        "-c",
        "targets",
        "-c",
        "shutdown",
    ]


def cfg_namespace(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(run_dir=None, dtb=args.dtb, dtc=args.dtc, cfg=args.target_cfg, require_pass=False)


def host_namespace(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        run_dir=None,
        openocd=args.openocd,
        script_dir=[args.private_script_dir, args.public_script_dir],
        phase_b_summary=args.phase_b_summary,
        require_ready=False,
    )


def run_cfg_audit(root: Path, args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    return cfg_audit.build_report(root, cfg_namespace(args))


def run_host_audit(root: Path, args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    return host_audit.build_report(root, host_namespace(args))


def summarize_preflight(cfg_summary: dict[str, Any], host_summary: dict[str, Any]) -> dict[str, Any]:
    cfg_result = cfg_summary["classification"]["result"]
    host_result = host_summary["classification"]["result"]
    ready = cfg_result in ("sm8450_cfg_draft_ready_romtable_dbgbase", "sm8450_cfg_source_has_dbgbase_hints") and (
        host_result == "host_openocd_eud_ready_to_probe"
    )
    if ready:
        result = "ready_for_bounded_openocd_init_probe"
    elif host_result == "waiting_for_eud_enumeration_or_hardware":
        result = "waiting_for_eud_enumeration_or_hardware"
    else:
        result = "blocked_preflight"
    return {
        "result": result,
        "ready": ready,
        "cfg_result": cfg_result,
        "host_result": host_result,
        "host_eud_usb_hint": bool(host_summary["host"]["host_eud_usb_hint"]),
    }


def build_preflight_report(root: Path, args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    run_dir = resolve_run_dir(root, args.run_dir)
    cfg_run_dir, cfg_summary = run_cfg_audit(root, args)
    host_run_dir, host_summary = run_host_audit(root, args)
    draft_missing = verify_policy_file(resolve(root, POLICY_DRAFT), active=False)
    active_missing = verify_policy_file(root / "AGENTS.md", active=True)
    summary = {
        "generated_at_utc": host_audit.utc_now(),
        "target": EXPECTED_TARGET,
        "device_action": False,
        "writes_performed": False,
        "reboots_performed": False,
        "flashes_performed": False,
        "sysfs_writes_performed": False,
        "openocd_init_performed": False,
        "cfg_audit_summary": str(cfg_run_dir / "summary.json"),
        "host_audit_summary": str(host_run_dir / "summary.json"),
        "policy_draft_missing": draft_missing,
        "active_agents_missing": active_missing,
        "openocd_probe_argv": openocd_probe_args(args.openocd, args.private_script_dir, args.public_script_dir),
        "classification": summarize_preflight(cfg_summary, host_summary),
    }
    write_text(run_dir / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return run_dir, summary


def run_openocd_probe(run_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    argv = openocd_probe_args(args.openocd, args.private_script_dir, args.public_script_dir)
    try:
        completed = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=args.openocd_timeout_sec,
            check=False,
        )
        result = {
            "argv": argv,
            "returncode": completed.returncode,
            "stdout": host_audit.redact(completed.stdout),
            "stderr": host_audit.redact(completed.stderr),
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        result = {
            "argv": argv,
            "returncode": 124,
            "stdout": host_audit.redact(exc.stdout or ""),
            "stderr": host_audit.redact(exc.stderr or ""),
            "timeout": True,
        }
    write_text(run_dir / "openocd_probe_stdout.txt", result["stdout"])
    write_text(run_dir / "openocd_probe_stderr.txt", result["stderr"])
    return result


def run_live(root: Path, args: argparse.Namespace) -> int:
    run_dir, preflight = build_preflight_report(root, args)
    if args.ack != LIVE_ACK_TOKEN:
        raise SystemExit("live OpenOCD probe requires exact ack token")
    active_missing = preflight["active_agents_missing"]
    if active_missing:
        raise SystemExit(f"AGENTS.md missing S22+ EUD OpenOCD live authorization markers: {active_missing}")
    if not preflight["classification"]["ready"]:
        raise SystemExit(f"OpenOCD live probe refused before init: {preflight['classification']}")

    probe = run_openocd_probe(run_dir, args)
    summary = dict(preflight)
    summary["device_action"] = True
    summary["openocd_init_performed"] = True
    summary["openocd_probe"] = {
        "returncode": probe["returncode"],
        "timeout": probe["timeout"],
        "stdout_path": str(run_dir / "openocd_probe_stdout.txt"),
        "stderr_path": str(run_dir / "openocd_probe_stderr.txt"),
    }
    summary["classification"] = {
        "result": "openocd_init_probe_completed" if probe["returncode"] == 0 else "openocd_init_probe_failed",
        "ready": False,
        "returncode": probe["returncode"],
        "timeout": probe["timeout"],
    }
    write_text(run_dir / "summary.json", json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(
        "S22+ EUD OpenOCD init probe gate: "
        f"{summary['classification']['result']}; rc={probe['returncode']} "
        f"timeout={int(probe['timeout'])}; log={display_path(run_dir / 'summary.json')}"
    )
    return 0 if probe["returncode"] == 0 else 20


def print_plan(args: argparse.Namespace) -> None:
    print("S22+ EUD OpenOCD init probe plan")
    print()
    print("1. Host-only preflight:")
    print("   PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \\")
    print("     workspace/public/src/scripts/revalidation/s22plus_eud_openocd_init_probe_gate.py --offline-check")
    print()
    print("2. Live probe only after AGENTS.md promotes the inert draft and host audit is ready:")
    print("   PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \\")
    print("     workspace/public/src/scripts/revalidation/s22plus_eud_openocd_init_probe_gate.py \\")
    print(f"     --live --ack {LIVE_ACK_TOKEN}")
    print()
    print("OpenOCD command:")
    print("   " + " ".join(openocd_probe_args(args.openocd, args.private_script_dir, args.public_script_dir)))
    print()
    print("Safety boundary: no flash, no reboot, no partition write, no EUD sysfs write, no memory write commands.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--openocd", type=Path, default=DEFAULT_OPENOCD)
    parser.add_argument("--private-script-dir", type=Path, default=DEFAULT_PRIVATE_SCRIPT_DIR)
    parser.add_argument("--public-script-dir", type=Path, default=DEFAULT_PUBLIC_SCRIPT_DIR)
    parser.add_argument("--target-cfg", type=Path, default=cfg_audit.DEFAULT_CFG)
    parser.add_argument("--dtb", type=Path, default=cfg_audit.DEFAULT_DTB)
    parser.add_argument("--dtc", type=Path)
    parser.add_argument("--phase-b-summary", type=Path)
    parser.add_argument("--openocd-timeout-sec", type=float, default=20.0)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--ack", default="")
    args = parser.parse_args(argv)

    root = repo_root()
    args.openocd = resolve(root, args.openocd)
    args.private_script_dir = resolve(root, args.private_script_dir)
    args.public_script_dir = resolve(root, args.public_script_dir)
    args.target_cfg = resolve(root, args.target_cfg)
    args.dtb = resolve(root, args.dtb)
    if args.dtc is not None:
        args.dtc = resolve(root, args.dtc)

    if args.print_plan:
        print_plan(args)
        return 0
    if args.live:
        return run_live(root, args)

    run_dir, summary = build_preflight_report(root, args)
    result = summary["classification"]["result"]
    print(
        "S22+ EUD OpenOCD init probe gate: "
        f"{result}; cfg={summary['classification']['cfg_result']} "
        f"host={summary['classification']['host_result']} "
        f"host_eud_usb={int(summary['classification']['host_eud_usb_hint'])}; "
        f"draft_missing={len(summary['policy_draft_missing'])} "
        f"active_missing={len(summary['active_agents_missing'])}; "
        f"log={display_path(run_dir / 'summary.json')}"
    )
    if args.offline_check and summary["policy_draft_missing"]:
        return 2
    if args.require_ready and not summary["classification"]["ready"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
