#!/usr/bin/env python3
"""Shared bridge and transport selection helpers for A90 revalidation scripts."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

sys.dont_write_bytecode = True

from _workspace_bootstrap import repo_root

import a90ctl
import a90_ncm_transport as ncm


DEFAULT_HOST = a90ctl.DEFAULT_HOST
DEFAULT_PORT = a90ctl.DEFAULT_PORT
DEFAULT_BRIDGE_DEVICE = os.environ.get("A90_BRIDGE_DEVICE", "auto")
DEFAULT_BRIDGE_DEVICE_GLOB = "/dev/serial/by-id/usb-SAMSUNG_SAMSUNG_Android_*"
BRIDGE_SCRIPT_REL = "workspace/public/src/scripts/revalidation/a90_bridge.py"
TRANSPORT_SELECTOR_CONTRACT = 1
PHASE_TIMER_CONTRACT = 1
SERIAL_RECOVERY_CONTRACT = 1
NCM_AUTO_REPAIR_ENV = "A90_TRANSPORT_AUTO_REPAIR_NCM"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def elapsed_sec(started_monotonic: float) -> float:
    return round(time.monotonic() - started_monotonic, 3)


@contextmanager
def phase(manifest: dict[str, Any], name: str) -> Iterator[None]:
    started = now_iso()
    started_monotonic = time.monotonic()
    ok = False
    error_type = ""
    manifest["phase_timer_contract"] = PHASE_TIMER_CONTRACT
    try:
        yield
        ok = True
    except BaseException as exc:
        error_type = exc.__class__.__name__
        raise
    finally:
        item = {
            "name": name,
            "started": started,
            "ended": now_iso(),
            "elapsed_sec": elapsed_sec(started_monotonic),
            "ok": ok,
        }
        if error_type:
            item["error_type"] = error_type
        manifest.setdefault("phase_timers", []).append(item)


def run_host_command(command: list[object], *, timeout: float = 30.0) -> dict[str, Any]:
    started = now_iso()
    started_monotonic = time.monotonic()
    try:
        completed = subprocess.run(
            [str(item) for item in command],
            cwd=str(repo_root()),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return {
            "command": [str(item) for item in command],
            "started": started,
            "ended": now_iso(),
            "elapsed_sec": elapsed_sec(started_monotonic),
            "timeout": False,
            "rc": completed.returncode,
            "ok": completed.returncode == 0,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": [str(item) for item in command],
            "started": started,
            "ended": now_iso(),
            "elapsed_sec": elapsed_sec(started_monotonic),
            "timeout": True,
            "rc": None,
            "ok": False,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }


def write_step(store: Any,
               steps: list[dict[str, Any]],
               name: str,
               result: dict[str, Any]) -> None:
    stdout_file = f"{name}.stdout.txt"
    stderr_file = f"{name}.stderr.txt"
    if hasattr(store, "write_log"):
        stdout_path = store.write_log("host", stdout_file, str(result.get("stdout") or ""))
        stderr_path = store.write_log("host", stderr_file, str(result.get("stderr") or ""))
        stdout_file = str(stdout_path.relative_to(store.run_dir))
        stderr_file = str(stderr_path.relative_to(store.run_dir))
    else:
        store.write_text(f"logs/host/{stdout_file}", str(result.get("stdout") or ""))
        store.write_text(f"logs/host/{stderr_file}", str(result.get("stderr") or ""))
        stdout_file = f"logs/host/{stdout_file}"
        stderr_file = f"logs/host/{stderr_file}"
    step = {
        "name": name,
        "command": [str(item) for item in result.get("command", [])],
        "started": result.get("started", now_iso()),
        "ended": result.get("ended", now_iso()),
        "timeout": bool(result.get("timeout")),
        "rc": result.get("rc"),
        "ok": bool(result.get("ok")),
        "stdout_file": stdout_file,
        "stderr_file": stderr_file,
    }
    if "elapsed_sec" in result:
        step["elapsed_sec"] = result.get("elapsed_sec")
    recovery = result.get("serial_recovery")
    if isinstance(recovery, dict):
        step["serial_recovery_contract"] = result.get(
            "serial_recovery_contract",
            SERIAL_RECOVERY_CONTRACT,
        )
        step["serial_recovery"] = recovery
        step["recovery"] = {
            "reason": recovery.get("reason", ""),
            "recovered": bool(recovery.get("recovered")),
        }
    steps.append(step)


def parse_json_stdout(result: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = json.loads(str(result.get("stdout") or "{}"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def bridge_command(subcommand: str,
                   *,
                   host: str = DEFAULT_HOST,
                   port: int = DEFAULT_PORT,
                   device: str = DEFAULT_BRIDGE_DEVICE,
                   device_glob: str = DEFAULT_BRIDGE_DEVICE_GLOB,
                   no_client_probe: bool = True,
                   extra: list[object] | None = None) -> list[object]:
    command: list[object] = [
        "python3",
        BRIDGE_SCRIPT_REL,
        subcommand,
        "--host",
        host,
        "--port",
        port,
        "--device",
        device,
        "--device-glob",
        device_glob,
        "--json",
    ]
    if no_client_probe:
        command.append("--no-client-probe")
    if extra:
        command.extend(extra)
    return command


def ensure_bridge(*,
                  host: str = DEFAULT_HOST,
                  port: int = DEFAULT_PORT,
                  device: str = DEFAULT_BRIDGE_DEVICE,
                  device_glob: str = DEFAULT_BRIDGE_DEVICE_GLOB,
                  no_client_probe: bool = True,
                  timeout: float = 10.0) -> dict[str, Any]:
    result = run_host_command(
        bridge_command(
            "ensure",
            host=host,
            port=port,
            device=device,
            device_glob=device_glob,
            no_client_probe=no_client_probe,
        ),
        timeout=timeout,
    )
    result["json"] = parse_json_stdout(result)
    return result


def bridge_status(*,
                  host: str = DEFAULT_HOST,
                  port: int = DEFAULT_PORT,
                  device: str = DEFAULT_BRIDGE_DEVICE,
                  device_glob: str = DEFAULT_BRIDGE_DEVICE_GLOB,
                  no_client_probe: bool = True,
                  timeout: float = 10.0) -> dict[str, Any]:
    result = run_host_command(
        bridge_command(
            "status",
            host=host,
            port=port,
            device=device,
            device_glob=device_glob,
            no_client_probe=no_client_probe,
        ),
        timeout=timeout,
    )
    result["json"] = parse_json_stdout(result)
    return result


def restart_bridge(*,
                   host: str = DEFAULT_HOST,
                   port: int = DEFAULT_PORT,
                   device: str = DEFAULT_BRIDGE_DEVICE,
                   device_glob: str = DEFAULT_BRIDGE_DEVICE_GLOB,
                   no_client_probe: bool = True,
                   timeout: float = 20.0) -> dict[str, Any]:
    result = run_host_command(
        bridge_command(
            "restart",
            host=host,
            port=port,
            device=device,
            device_glob=device_glob,
            no_client_probe=no_client_probe,
        ),
        timeout=timeout,
    )
    result["json"] = parse_json_stdout(result)
    return result


def protocol_result_to_command_result(command: list[str],
                                      started: str,
                                      elapsed: float,
                                      result: a90ctl.ProtocolResult) -> dict[str, Any]:
    return {
        "command": ["cmdv1", *command],
        "started": started,
        "ended": now_iso(),
        "elapsed_sec": elapsed,
        "timeout": False,
        "rc": result.rc,
        "ok": result.rc == 0,
        "stdout": result.text,
        "stderr": "",
        "protocol": {
            "begin": result.begin,
            "end": result.end,
            "status": result.status,
        },
    }


def run_serial_command(command: list[str],
                       *,
                       host: str = DEFAULT_HOST,
                       port: int = DEFAULT_PORT,
                       timeout: float = 20.0,
                       retry_unsafe: bool = False) -> dict[str, Any]:
    started = now_iso()
    started_monotonic = time.monotonic()
    try:
        result = a90ctl.run_cmdv1_command(
            host,
            port,
            timeout,
            command,
            retry_unsafe=retry_unsafe,
        )
        return protocol_result_to_command_result(
            command,
            started,
            elapsed_sec(started_monotonic),
            result,
        )
    except Exception as exc:  # noqa: BLE001 - transport evidence must preserve exact failure
        return {
            "command": ["cmdv1", *command],
            "started": started,
            "ended": now_iso(),
            "elapsed_sec": elapsed_sec(started_monotonic),
            "timeout": False,
            "rc": None,
            "ok": False,
            "stdout": "",
            "stderr": repr(exc),
        }


def serial_output(result: dict[str, Any]) -> str:
    return "\n".join([str(result.get("stdout") or ""), str(result.get("stderr") or "")])


def serial_needs_hide_on_busy(result: dict[str, Any]) -> bool:
    return "[busy]" in serial_output(result)


def serial_needs_hide_on_protocol_noise(result: dict[str, Any]) -> bool:
    output = serial_output(result)
    return (
        "A90P1 END marker not found" in output
        or "A90P1 command mismatch" in output
        or "cmdvATATAT" in output
    )


def serial_needs_bridge_ensure_on_missing(result: dict[str, Any]) -> bool:
    return a90ctl.BRIDGE_SERIAL_MISSING_TEXT in serial_output(result)


def serial_command_can_recover(command: list[str], retry_unsafe: bool) -> bool:
    return retry_unsafe or a90ctl.command_allows_retry(command)


def attach_serial_recovery(result: dict[str, Any],
                           recovery: dict[str, Any]) -> dict[str, Any]:
    result["serial_recovery_contract"] = SERIAL_RECOVERY_CONTRACT
    result["serial_recovery"] = recovery
    return result


def run_serial_command_recovered(command: list[str],
                                 *,
                                 host: str = DEFAULT_HOST,
                                 port: int = DEFAULT_PORT,
                                 timeout: float = 20.0,
                                 retry_unsafe: bool = False,
                                 store: Any | None = None,
                                 steps: list[dict[str, Any]] | None = None,
                                 recovery_step_prefix: str = "serial") -> dict[str, Any]:
    result = run_serial_command(
        command,
        host=host,
        port=port,
        timeout=timeout,
        retry_unsafe=retry_unsafe,
    )
    recovery = {
        "attempts": 1,
        "recovered": False,
        "reason": "",
        "actions": [],
        "unsafe_retry": bool(retry_unsafe),
        "retry_allowed": serial_command_can_recover(command, retry_unsafe),
    }
    recovery_label = ""
    if serial_needs_hide_on_busy(result):
        recovery_label = "busy"
    elif serial_needs_hide_on_protocol_noise(result):
        recovery_label = "protocol-noise"
    elif serial_needs_bridge_ensure_on_missing(result):
        recovery_label = "serial-missing"

    if not recovery_label:
        return attach_serial_recovery(result, recovery)

    recovery["reason"] = recovery_label
    if recovery_label == "busy":
        hide = run_serial_command(["hide"], host=host, port=port, timeout=20.0)
        if store is not None and steps is not None:
            write_step(store, steps, f"{recovery_step_prefix}-hide-on-{recovery_label}", hide)
        recovery["actions"] = ["hide"]
        if not recovery["retry_allowed"]:
            recovery["skip_reason"] = "unsafe-retry-not-allowed"
            return attach_serial_recovery(result, recovery)
        recovery["actions"].append("retry-command")
        recovery["attempts"] = 2
        result = run_serial_command(
            command,
            host=host,
            port=port,
            timeout=timeout,
            retry_unsafe=retry_unsafe,
        )
        recovery["recovered"] = bool(result.get("ok"))
        return attach_serial_recovery(result, recovery)

    if not recovery["retry_allowed"]:
        recovery["skip_reason"] = "unsafe-retry-not-allowed"
        return attach_serial_recovery(result, recovery)

    if recovery_label == "protocol-noise":
        restart = restart_bridge(host=host, port=port)
        if store is not None and steps is not None:
            write_step(store, steps, f"{recovery_step_prefix}-bridge-restart-on-{recovery_label}", restart)
        recovery["actions"] = ["bridge-restart", "retry-command"]
    else:
        ensure = ensure_bridge(host=host, port=port)
        if store is not None and steps is not None:
            write_step(store, steps, f"{recovery_step_prefix}-bridge-ensure-on-{recovery_label}", ensure)
        recovery["actions"] = ["bridge-ensure", "retry-command"]

    recovery["attempts"] = 2
    result = run_serial_command(
        command,
        host=host,
        port=port,
        timeout=timeout,
        retry_unsafe=retry_unsafe,
    )
    recovery["recovered"] = bool(result.get("ok"))
    return attach_serial_recovery(result, recovery)


def run_serial_step(store: Any,
                    steps: list[dict[str, Any]],
                    name: str,
                    command: list[str],
                    *,
                    timeout: float = 60.0,
                    bridge_timeout: float = 45.0,
                    host: str = DEFAULT_HOST,
                    port: int = DEFAULT_PORT,
                    hide_on_busy: bool = True,
                    retry_unsafe: bool = False) -> dict[str, Any]:
    del timeout
    if hide_on_busy:
        result = run_serial_command_recovered(
            command,
            host=host,
            port=port,
            timeout=bridge_timeout,
            retry_unsafe=retry_unsafe,
            store=store,
            steps=steps,
            recovery_step_prefix=name,
        )
    else:
        result = run_serial_command(
            command,
            host=host,
            port=port,
            timeout=bridge_timeout,
            retry_unsafe=retry_unsafe,
        )
    write_step(store, steps, name, result)
    return result


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("[") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def summarize_host_ncm() -> dict[str, Any]:
    snapshot = ncm.host_netdev_snapshot()
    ready = ncm.host_ncm_candidates(snapshot, require_link_local=True)
    present = ncm.host_ncm_candidates(snapshot, require_link_local=False)
    if ready:
        state = "ready"
    elif present:
        state = "present-no-link-local"
    else:
        state = "not-ready"
    return {
        "state": state,
        "ready_candidates": ready,
        "present_candidates": present,
        "snapshot": snapshot,
    }


def auto_repair_enabled(default: bool = True) -> bool:
    raw = os.environ.get(NCM_AUTO_REPAIR_ENV)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def maybe_repair_host_ncm(store: Any | None,
                          steps: list[dict[str, Any]] | None,
                          host_ncm: dict[str, Any],
                          *,
                          enabled: bool) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if not enabled or host_ncm.get("state") != "present-no-link-local":
        return host_ncm, None

    repair = ncm.host_linklocal_repair_nmcli(
        reason="transport-selector-present-no-link-local",
        before=host_ncm.get("snapshot") if isinstance(host_ncm.get("snapshot"), list) else None,
    )
    if store is not None and steps is not None:
        write_step(
            store,
            steps,
            "transport-host-ncm-linklocal-repair",
            {
                "command": ["host", "nmcli", "a90-linklocal-repair"],
                "started": now_iso(),
                "ended": now_iso(),
                "timeout": False,
                "rc": 0 if repair.get("ok") else 1,
                "ok": bool(repair.get("ok")),
                "stdout": json.dumps(repair, ensure_ascii=False, sort_keys=True) + "\n",
                "stderr": "",
            },
        )

    repaired_ncm = summarize_host_ncm()
    if store is not None and steps is not None:
        write_step(
            store,
            steps,
            "transport-host-ncm-after-repair",
            {
                "command": ["host", "detect-a90-ncm-after-repair"],
                "started": now_iso(),
                "ended": now_iso(),
                "timeout": False,
                "rc": 0 if repaired_ncm.get("state") == "ready" else 1,
                "ok": repaired_ncm.get("state") == "ready",
                "stdout": json.dumps(repaired_ncm, ensure_ascii=False, sort_keys=True) + "\n",
                "stderr": "",
            },
        )
    return repaired_ncm, repair


def compact_ncm_repair(repair: dict[str, Any] | None) -> dict[str, Any] | None:
    if repair is None:
        return None
    commands = repair.get("commands") if isinstance(repair.get("commands"), list) else []
    return {
        "ok": bool(repair.get("ok")),
        "reason": repair.get("reason", ""),
        "trigger_reason": repair.get("trigger_reason", ""),
        "profile": repair.get("profile", ""),
        "ifname": repair.get("ifname", ""),
        "host_link_local": repair.get("host_link_local", ""),
        "commands": [
            {
                "command": item.get("command", []),
                "rc": item.get("rc"),
                "ok": bool(item.get("ok")),
            }
            for item in commands
            if isinstance(item, dict)
        ],
    }


def select_transport(store: Any | None = None,
                     steps: list[dict[str, Any]] | None = None,
                     *,
                     host: str = DEFAULT_HOST,
                     port: int = DEFAULT_PORT,
                     bridge_device: str = DEFAULT_BRIDGE_DEVICE,
                     ensure: bool = True,
                     no_client_probe: bool = True,
                     prefer_fast: bool = True,
                     auto_repair_ncm: bool | None = None) -> dict[str, Any]:
    bridge_result = ensure_bridge(
        host=host,
        port=port,
        device=bridge_device,
        no_client_probe=no_client_probe,
    ) if ensure else bridge_status(
        host=host,
        port=port,
        device=bridge_device,
        no_client_probe=no_client_probe,
    )
    if store is not None and steps is not None:
        write_step(store, steps, "transport-bridge-ensure" if ensure else "transport-bridge-status", bridge_result)

    version_result = run_serial_command_recovered(
        ["version"],
        host=host,
        port=port,
        timeout=10.0,
        store=store,
        steps=steps,
        recovery_step_prefix="transport-version",
    )
    if store is not None and steps is not None:
        write_step(store, steps, "transport-version", version_result)

    status_result = run_serial_command_recovered(
        ["status"],
        host=host,
        port=port,
        timeout=20.0,
        store=store,
        steps=steps,
        recovery_step_prefix="transport-status",
    )
    if store is not None and steps is not None:
        write_step(store, steps, "transport-status", status_result)

    host_ncm = summarize_host_ncm()
    if store is not None and steps is not None:
        write_step(
            store,
            steps,
            "transport-host-ncm-snapshot",
            {
                "command": ["host", "detect-a90-ncm"],
                "started": now_iso(),
                "ended": now_iso(),
                "timeout": False,
                "rc": 0,
                "ok": True,
                "stdout": json.dumps(host_ncm, ensure_ascii=False, sort_keys=True) + "\n",
                "stderr": "",
            },
        )
    host_ncm_repair: dict[str, Any] | None
    host_ncm, host_ncm_repair = maybe_repair_host_ncm(
        store,
        steps,
        host_ncm,
        enabled=auto_repair_enabled() if auto_repair_ncm is None else auto_repair_ncm,
    )

    status_fields = parse_key_values(str(status_result.get("stdout") or ""))
    contract_raw = status_fields.get("transport.contract", "0")
    try:
        contract = int(contract_raw, 0)
    except ValueError:
        contract = 0

    bridge_json = bridge_result.get("json") if isinstance(bridge_result.get("json"), dict) else {}
    serial_bridge = "ready" if bridge_result.get("ok") and bridge_json.get("bridge_process") == "running" else "not-ready"
    device_status = "ready" if status_result.get("ok") else "not-ready"
    tcpctl = status_fields.get("transport.tcpctl", "not-tested")
    if not status_result.get("ok"):
        selected = "serial"
        fallback_reason = "device-status-not-ready"
    elif contract and tcpctl == "ready" and prefer_fast:
        selected = "tcpctl"
        fallback_reason = None
    elif prefer_fast and host_ncm["state"] == "ready":
        selected = "ncm"
        fallback_reason = None
    else:
        selected = "serial"
        fallback_reason = None if serial_bridge == "ready" else "bridge-not-ready"
        if prefer_fast and host_ncm["state"] != "ready":
            fallback_reason = f"host-ncm-{host_ncm['state']}"

    selection = {
        "selector_contract": TRANSPORT_SELECTOR_CONTRACT,
        "transport_contract": contract,
        "bridge_wrapper_contract": bridge_json.get("wrapper_contract", 0),
        "bridge_device": bridge_device,
        "serial_bridge": serial_bridge,
        "device_status": device_status,
        "ncm_host": host_ncm["state"],
        "tcpctl": tcpctl,
        "selected": selected,
        "fallback_reason": fallback_reason,
        "bridge": bridge_json,
        "status_fields": status_fields,
        "version_ok": bool(version_result.get("ok")),
        "status_ok": bool(status_result.get("ok")),
        "host_ncm": {
            "ready_candidates": host_ncm["ready_candidates"],
            "present_candidates": host_ncm["present_candidates"],
        },
        "host_ncm_repair": compact_ncm_repair(host_ncm_repair),
        "host_ncm_auto_repair": auto_repair_enabled() if auto_repair_ncm is None else auto_repair_ncm,
    }
    if store is not None and steps is not None:
        write_step(
            store,
            steps,
            "transport-selection",
            {
                "command": ["host", "select-transport"],
                "started": now_iso(),
                "ended": now_iso(),
                "timeout": False,
                "rc": 0 if serial_bridge == "ready" else 1,
                "ok": serial_bridge == "ready",
                "stdout": json.dumps(selection, ensure_ascii=False, sort_keys=True) + "\n",
                "stderr": "",
            },
        )
    return selection
