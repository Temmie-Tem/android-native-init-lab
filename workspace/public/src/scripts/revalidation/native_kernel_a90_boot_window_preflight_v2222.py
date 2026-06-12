#!/usr/bin/env python3
"""Prepare the approved a90 boot-window trace run contract.

This runner is intentionally preflight-only. It validates the current bridge,
native-init, helper/event readiness, and the V2221 collector->parser contract
without rebooting, flashing, scanning Wi-Fi, or writing tracefs controls.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import a90_transport as transport


REPO_ROOT = Path(__file__).resolve().parents[5]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
PRIVATE_RUNS = REPO_ROOT / "workspace/private/runs/kernel"
REMOTE_TOYBOX = "/cache/bin/busybox"


@dataclass
class StepResult:
    name: str
    command: list[str]
    returncode: int
    elapsed_sec: float
    stdout_path: str
    stderr_path: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def now_label() -> str:
    return time.strftime("%Y%m%d-%H%M%S")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def run_step(
    out_dir: Path,
    steps: list[StepResult],
    name: str,
    command: list[str],
    *,
    timeout: float = 120.0,
    allow_error: bool = False,
) -> str:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )
    elapsed = time.monotonic() - started
    stdout_path = out_dir / f"{name}.stdout.txt"
    stderr_path = out_dir / f"{name}.stderr.txt"
    stdout_path.write_text(completed.stdout)
    stderr_path.write_text(completed.stderr)
    step = StepResult(
        name=name,
        command=command,
        returncode=completed.returncode,
        elapsed_sec=round(elapsed, 3),
        stdout_path=rel(stdout_path),
        stderr_path=rel(stderr_path),
    )
    steps.append(step)
    if completed.returncode != 0 and not allow_error:
        raise RuntimeError(f"{name} failed rc={completed.returncode}: {stderr_path}")
    return completed.stdout


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if not stripped:
        return {}
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            return json.loads(stripped[start : end + 1])
        raise


def a90ctl_command(args: argparse.Namespace, argv: list[str], *, allow_error: bool = False) -> list[str]:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "a90ctl.py"),
        "--host",
        args.bridge_host,
        "--port",
        str(args.bridge_port),
        "--timeout",
        str(args.timeout),
    ]
    if allow_error:
        command.append("--allow-error")
    command.extend(argv)
    return command


def parse_protocol_rc(text: str) -> int | None:
    match = re.search(r"A90P1 END .* rc=(?P<rc>-?\d+)", text)
    if not match:
        return None
    return int(match.group("rc"), 10)


def grep_value(pattern: str, text: str, default: str = "") -> str:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1) if match else default


def parse_helper_inventory(text: str) -> dict[str, dict[str, str]]:
    inventory: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if (
            not line
            or line.startswith("a90:/#")
            or line.startswith("A90P1 ")
            or line.startswith("[done]")
            or line.startswith("cmdv1")
            or line.startswith("linker: ")
            or line.startswith("WARNING: linker:")
        ):
            continue
        if line.startswith("HELPER "):
            current = line.split(" ", 1)[1]
            inventory[current] = {}
            continue
        if current is None or "=" not in line:
            continue
        key, value = line.split("=", 1)
        inventory[current][key] = value
    return inventory


def build_contract(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_version": 1,
        "purpose": "approved boot-window a90 trace_uprobe capture with V2221 collector-parser postprocess",
        "preflight_summary_path": summary.get("summary_path"),
        "requires_explicit_user_approval": True,
        "preflight_only_runner": True,
        "current_preflight_pass": summary.get("pass"),
        "allowed_when_approved": [
            "rollbackable test-boot or already-active helper-owned boot window",
            "helper-owned a90 trace_uprobe registration/collection route",
            "V2220 parser postprocess",
            "stock BPF only for static kernel tracepoints if separately required",
        ],
        "forbidden_without_new_approval": [
            "BPF attach to dynamic a90 trace_uprobe events",
            "probe_write_user execution",
            "cgroup-BPF attach",
            "Wi-Fi scan/connect/credentials/DHCP/routes/external ping",
            "PMIC/GPIO/GDSC/eSoC/PCI rescan/platform bind/unbind",
            "partition writes or sda29 writes",
        ],
        "expected_event_sequence": [
            "a90cnss:wlfw_start",
            "a90cnss:wlfw_service_request",
            "a90cnss:wlfw_cap_qmi",
            "a90cnss:wlfw_bdf_entry",
        ],
        "postprocess_command_template": [
            "python3",
            "workspace/public/src/scripts/revalidation/a90_kernel_v2220_helper_summary_trace_parser.py",
            "--input",
            "<boot_window_helper_summary_or_collector_summary.json>",
        ],
        "current_wrapper_command_template": [
            "python3",
            "workspace/public/src/scripts/revalidation/native_kernel_a90_uprobe_trace_postprocess_v2221.py",
        ],
        "preflight_evidence": {
            "bridge_ready": summary.get("bridge_ready"),
            "selftest_fail0": summary.get("selftest_fail0"),
            "native_version": summary.get("native_version"),
            "event_exists_count": summary.get("event_exists_count"),
            "event_enabled_count": summary.get("event_enabled_count"),
            "helper_inventory": summary.get("helper_inventory"),
            "v2221_contract_pass": summary.get("v2221_contract_pass"),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="v2222-boot-window-preflight")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--toybox", default=REMOTE_TOYBOX)
    return parser.parse_args()


def residual_state(summary: dict[str, Any]) -> dict[str, Any]:
    device_touched = bool(summary.get("steps"))
    selftest_ok = bool(summary.get("selftest_fail0"))
    cleanup_required = bool(device_touched and not selftest_ok)
    return {
        "device_touched": device_touched,
        "flash_reboot": False,
        "test_flash_ok": False,
        "rollback_ok": True,
        "rollback_attempt": "not-needed-no-flash",
        "selftest_ok": selftest_ok,
        "cleanup_required": cleanup_required,
        "residual_risk": "post-selftest-incomplete" if cleanup_required else "none",
        "wifi_scan_connect": False,
        "credentials_used": False,
        "dhcp_routes_ping": False,
        "tracefs_control_write": False,
        "bpf_attach": False,
        "probe_write_user_executed": False,
        "partition_write": False,
    }


def main() -> int:
    args = parse_args()
    out_dir = PRIVATE_RUNS / f"{args.label}-{now_label()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    steps: list[StepResult] = []
    summary: dict[str, Any] = {
        "label": args.label,
        "out_dir": rel(out_dir),
        "summary_path": rel(out_dir / "summary.json"),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "mode": "preflight-only",
        "phase_timer_contract": transport.PHASE_TIMER_CONTRACT,
        "phase_timers": [],
        "safety": {
            "tracefs_control_write": False,
            "bpf_attach": False,
            "probe_write_user_executed": False,
            "cgroup_bpf_attach": False,
            "wifi_scan_connect": False,
            "network_route_change": False,
            "flash_reboot": False,
            "partition_write": False,
        },
    }

    try:
        with transport.phase(summary, "bridge_status"):
            bridge_stdout = run_step(
                out_dir,
                steps,
                "bridge-status",
                [sys.executable, str(SCRIPT_DIR / "a90_bridge.py"), "status", "--json"],
                timeout=30,
                allow_error=True,
            )
        bridge_status = parse_json_object(bridge_stdout)
        bridge_ready = (
            bridge_status.get("bridge_process") == "running"
            and bridge_status.get("port_listening") is True
            and bridge_status.get("bridge_probe") == "connected-no-immediate-error"
        )

        with transport.phase(summary, "native_state_snapshot"):
            status_text = run_step(
                out_dir,
                steps,
                "native-status",
                a90ctl_command(args, ["status"], allow_error=True),
                timeout=args.timeout + 20,
                allow_error=True,
            )
            version_text = run_step(
                out_dir,
                steps,
                "native-version",
                a90ctl_command(args, ["version"], allow_error=True),
                timeout=args.timeout + 20,
                allow_error=True,
            )
            helpers_text = run_step(
                out_dir,
                steps,
                "native-helpers",
                a90ctl_command(args, ["helpers"], allow_error=True),
                timeout=args.timeout + 20,
                allow_error=True,
            )

        helper_script = (
            "for h in /bin/a90_android_execns_probe /cache/bin/a90_android_execns_probe; do "
            "echo HELPER $h; "
            "test -e $h && echo exists=1 || { echo exists=0; continue; }; "
            "test -x $h && echo executable=1 || echo executable=0; "
            "ls -l $h 2>/dev/null | sed 's/^/ls=/'; "
            "sha256sum $h 2>/dev/null | awk '{print \"sha256=\"$1}'; "
            "grep -ao -m1 'a90_android_execns_probe v[0-9][0-9]*' $h 2>/dev/null | sed 's/^/version_string=/'; "
            "done"
        )
        with transport.phase(summary, "helper_inventory"):
            helper_inventory_text = run_step(
                out_dir,
                steps,
                "helper-inventory",
                a90ctl_command(args, ["run", args.toybox, "sh", "-c", helper_script], allow_error=True),
                timeout=args.timeout + 20,
                allow_error=True,
            )
        helper_inventory = parse_helper_inventory(helper_inventory_text)

        with transport.phase(summary, "v2221_current_window_contract"):
            v2221_stdout = run_step(
                out_dir,
                steps,
                "v2221-current-window-contract",
                [
                    sys.executable,
                    str(SCRIPT_DIR / "native_kernel_a90_uprobe_trace_postprocess_v2221.py"),
                    "--bridge-host",
                    args.bridge_host,
                    "--bridge-port",
                    str(args.bridge_port),
                    "--timeout",
                    str(args.timeout),
                    "--wait-sec",
                    "0",
                ],
                timeout=max(180.0, args.timeout * 6),
            )
            v2221_brief = parse_json_object(v2221_stdout)
            v2221_summary_path = REPO_ROOT / str(v2221_brief["out_dir"]) / "summary.json"
            v2221_summary = json.loads(v2221_summary_path.read_text())

        with transport.phase(summary, "post_selftest"):
            selftest_text = run_step(
                out_dir,
                steps,
                "post-selftest",
                a90ctl_command(args, ["selftest"], allow_error=True),
                timeout=args.timeout + 30,
                allow_error=True,
            )

        summary.update(
            {
                "decision": "v2222-boot-window-preflight-ready-approval-required",
                "bridge_ready": bridge_ready,
                "bridge_status": bridge_status,
                "native_status_rc": parse_protocol_rc(status_text),
                "native_version_rc": parse_protocol_rc(version_text),
                "native_helpers_rc": parse_protocol_rc(helpers_text),
                "native_version": grep_value(r"version: ([^\n]+)", version_text),
                "native_init_line": grep_value(r"init: ([^\n]+)", status_text),
                "selftest_fail0": "fail=0" in selftest_text,
                "helper_inventory": helper_inventory,
                "v2221_contract_path": rel(v2221_summary_path),
                "v2221_contract_pass": v2221_summary.get("pass") is True,
                "v2221_contract_decision": v2221_summary.get("decision"),
                "event_exists_count": v2221_summary.get("collector_event_exists_count"),
                "event_enabled_count": v2221_summary.get("collector_event_enabled_count"),
                "current_window_hits": v2221_summary.get("collector_total_hits"),
            }
        )
        summary["pass"] = all(
            [
                summary["bridge_ready"],
                summary["native_status_rc"] == 0,
                summary["native_version_rc"] == 0,
                summary["native_helpers_rc"] == 0,
                summary["selftest_fail0"],
                summary["v2221_contract_pass"],
                summary["event_exists_count"] == 21,
                summary["event_enabled_count"] == 21,
            ]
        )
        if not summary["pass"]:
            summary["decision"] = "v2222-boot-window-preflight-not-ready"
    except Exception as exc:  # noqa: BLE001
        summary["decision"] = "v2222-boot-window-preflight-failed"
        summary["pass"] = False
        summary["error"] = str(exc)
    finally:
        summary["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        summary["steps"] = [
            {
                "name": step.name,
                "command": step.command,
                "returncode": step.returncode,
                "ok": step.ok,
                "elapsed_sec": step.elapsed_sec,
                "stdout_path": step.stdout_path,
                "stderr_path": step.stderr_path,
            }
            for step in steps
        ]
        with transport.phase(summary, "contract_write"):
            contract = build_contract(summary)
            contract_path = out_dir / "boot_window_contract.json"
            contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n")
        summary["contract_path"] = rel(contract_path)
        transport.set_residual_state(summary, residual_state(summary))
        transport.add_total_phase(summary, "artifact_write", time.monotonic(), ok=True)
        (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
        print(
            json.dumps(
                {
                    "decision": summary.get("decision"),
                    "pass": summary.get("pass"),
                    "out_dir": summary.get("out_dir"),
                    "contract_path": summary.get("contract_path"),
                    "bridge_ready": summary.get("bridge_ready"),
                    "native_version": summary.get("native_version"),
                    "event_exists_count": summary.get("event_exists_count"),
                    "event_enabled_count": summary.get("event_enabled_count"),
                    "v2221_contract_pass": summary.get("v2221_contract_pass"),
                    "selftest_fail0": summary.get("selftest_fail0"),
                    "error": summary.get("error"),
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0 if summary.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
