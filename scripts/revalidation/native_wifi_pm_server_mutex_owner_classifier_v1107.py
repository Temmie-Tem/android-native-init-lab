#!/usr/bin/env python3
"""V1107 host-only PM server modem mutex owner classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1107-pm-server-mutex-owner-classifier")
DEFAULT_V1106_MANIFEST = Path("tmp/wifi/v1106-pm-server-wchan-tracefs-live/manifest.json")
DEFAULT_PM_SERVICE = Path("tmp/wifi/v1073-host-only/vendor-extract/files/pm-service")
LATEST_POINTER = Path("tmp/wifi/latest-v1107-pm-server-mutex-owner-classifier.txt")
ALLOWED_V1106_DECISIONS = {
    "v1106-cnss-raw-lock-pending-in-futex-wait",
}

TIME_RE = re.compile(r"\s(?P<time>\d+\.\d+):\s+")
PC_RE = re.compile(r"\((?P<pc>0x[0-9A-Fa-f]+)(?:\s+<-|\))")
RET_PC_RE = re.compile(r"\((?P<ret>0x[0-9A-Fa-f]+)\s+<-")
MUTEX_RE = re.compile(r"\bmutex=(?P<mutex>0x[0-9A-Fa-f]+)")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def repo_path(path: Path | str) -> Path:
    path = Path(path)
    return path if path.is_absolute() else Path.cwd() / path


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(repo_path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def parse_time(line: str) -> float:
    match = TIME_RE.search(line)
    return float(match.group("time")) if match else -1.0


def parse_pc(line: str) -> int | None:
    match = PC_RE.search(line)
    return int(match.group("pc"), 16) if match else None


def parse_return_pc(line: str) -> int | None:
    match = RET_PC_RE.search(line)
    return int(match.group("ret"), 16) if match else None


def target_cnss_pending(tracefs: dict[str, Any]) -> dict[str, str]:
    cnss_comms = set(tracefs.get("cnss_server_register_comms") or [])
    pending = tracefs.get("pending_raw_locks_by_comm") or {}
    for comm in sorted(cnss_comms):
        for event in pending.get(comm, []):
            if event.get("mutex") and event.get("pid"):
                return {
                    "comm": comm,
                    "tid": str(event.get("pid", "")),
                    "mutex": str(event.get("mutex", "")),
                    "line": str(event.get("line", "")),
                    "time": str(parse_time(str(event.get("line", "")))),
                }
    for comm, events in sorted(pending.items()):
        if "Binder" not in comm:
            continue
        for event in events:
            if event.get("mutex") and event.get("pid"):
                return {
                    "comm": comm,
                    "tid": str(event.get("pid", "")),
                    "mutex": str(event.get("mutex", "")),
                    "line": str(event.get("line", "")),
                    "time": str(parse_time(str(event.get("line", "")))),
                }
    return {}


def runtime_base(events: list[dict[str, str]], target_mutex: str) -> int | None:
    for event in events:
        label = event.get("label", "")
        line = event.get("line", "")
        mutex = event.get("mutex", "")
        if mutex != target_mutex:
            continue
        pc = parse_pc(line)
        if pc is None:
            continue
        if label == "pm_raw_pthread_mutex_lock_call":
            return pc - 0xA250
        if label == "pm_raw_pthread_mutex_unlock_call":
            return pc - 0xA270
    return None


def classify_owner(tracefs: dict[str, Any], target: dict[str, str]) -> dict[str, Any]:
    events = tracefs.get("raw_mutex_events") or []
    target_mutex = target.get("mutex", "")
    target_time = float(target.get("time") or -1.0)
    base = runtime_base(events, target_mutex)
    lock_calls: dict[str, list[dict[str, Any]]] = {}
    unlock_calls: dict[str, list[dict[str, Any]]] = {}
    held: list[dict[str, Any]] = []
    sequence: list[dict[str, Any]] = []

    for event in events:
        label = str(event.get("label", ""))
        comm = str(event.get("comm", ""))
        tid = str(event.get("pid", ""))
        line = str(event.get("line", ""))
        event_time = parse_time(line)
        if target_time >= 0 and event_time > target_time:
            break
        if label == "pm_raw_pthread_mutex_lock_call":
            call = {
                "comm": comm,
                "tid": tid,
                "mutex": str(event.get("mutex", "")),
                "line": line,
                "time": event_time,
            }
            lock_calls.setdefault(f"{comm}:{tid}", []).append(call)
            if call["mutex"] == target_mutex:
                sequence.append({**call, "kind": "lock_call"})
        elif label == "pm_raw_pthread_mutex_lock_ret":
            stack = lock_calls.get(f"{comm}:{tid}") or []
            call = stack.pop() if stack else {}
            mutex = call.get("mutex", "")
            return_pc = parse_return_pc(line)
            return_offset = return_pc - base if return_pc is not None and base is not None else None
            acquisition = {
                "comm": comm,
                "tid": tid,
                "mutex": mutex,
                "call_line": call.get("line", ""),
                "return_line": line,
                "call_time": call.get("time", -1.0),
                "return_time": event_time,
                "return_pc": f"0x{return_pc:x}" if return_pc is not None else "",
                "return_offset": f"0x{return_offset:x}" if return_offset is not None else "",
                "ret": str(event.get("ret", "")),
            }
            if mutex == target_mutex and acquisition["ret"] in ("0", "0x0"):
                held.append(acquisition)
                sequence.append({**acquisition, "kind": "lock_ret"})
        elif label == "pm_raw_pthread_mutex_unlock_call":
            call = {
                "comm": comm,
                "tid": tid,
                "mutex": str(event.get("mutex", "")),
                "line": line,
                "time": event_time,
            }
            unlock_calls.setdefault(f"{comm}:{tid}", []).append(call)
            if call["mutex"] == target_mutex:
                sequence.append({**call, "kind": "unlock_call"})
        elif label == "pm_raw_pthread_mutex_unlock_ret":
            stack = unlock_calls.get(f"{comm}:{tid}") or []
            call = stack.pop() if stack else {}
            mutex = call.get("mutex", "")
            if mutex == target_mutex and str(event.get("ret", "")) in ("0", "0x0"):
                for index in range(len(held) - 1, -1, -1):
                    if held[index].get("comm") == comm and held[index].get("tid") == tid:
                        held.pop(index)
                        break
                sequence.append({
                    "kind": "unlock_ret",
                    "comm": comm,
                    "tid": tid,
                    "mutex": mutex,
                    "line": line,
                    "time": event_time,
                    "ret": str(event.get("ret", "")),
                })

    owner = max(held, key=lambda item: float(item.get("return_time", -1.0)), default={})
    return {
        "target_mutex": target_mutex,
        "target_time": target_time,
        "runtime_base": f"0x{base:x}" if base is not None else "",
        "sequence_before_waiter": sequence,
        "unmatched_holders_before_waiter": held,
        "owner": owner,
    }


def thread_state(tracefs: dict[str, Any], tid: str) -> dict[str, Any]:
    samples = (tracefs.get("thread_samples_by_tid") or {}).get(tid, [])
    return {
        "tid": tid,
        "sample_count": len(samples),
        "comm": samples[-1].get("comm", "") if samples else "",
        "states": sorted({sample.get("state", "") for sample in samples if sample.get("state", "")}),
        "wchans": sorted({sample.get("wchan", "") for sample in samples if sample.get("wchan", "")}),
        "syscalls": sorted({str(sample.get("syscall", "")).split()[0] for sample in samples if sample.get("syscall", "")}),
        "last_samples": samples[-8:],
    }


def disassemble(pm_service: Path, offset: str, store: EvidenceStore) -> dict[str, Any]:
    resolved = repo_path(pm_service)
    if not resolved.exists() or not offset:
        return {"ok": False, "reason": "pm-service missing or owner offset unavailable"}
    start = max(int(offset, 16) - 0xC0, 0)
    stop = int(offset, 16) + 0x580
    commands = [
        ["aarch64-linux-gnu-objdump", "-d", f"--start-address=0x{start:x}", f"--stop-address=0x{stop:x}", str(resolved)],
        ["objdump", "-d", f"--start-address=0x{start:x}", f"--stop-address=0x{stop:x}", str(resolved)],
    ]
    last_error = ""
    for command in commands:
        try:
            result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=False)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            last_error = str(exc)
            continue
        if result.returncode == 0 and result.stdout:
            output_path = store.path("host/pm-service-owner-disassembly.txt")
            write_private_text(output_path, result.stdout)
            return {
                "ok": True,
                "command": " ".join(command),
                "file": str(output_path.relative_to(store.run_dir)),
                "start": f"0x{start:x}",
                "stop": f"0x{stop:x}",
            }
        last_error = result.stderr.strip()
    return {"ok": False, "reason": last_error}


def decide(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest["command"] == "plan":
        return (
            "v1107-pm-server-mutex-owner-classifier-plan-ready",
            True,
            "host-only plan; no device command, tracefs write, PM actor, or Wi-Fi action executed",
            "run V1107 host-only classifier against V1106 evidence",
        )
    if manifest.get("v1106", {}).get("decision") not in ALLOWED_V1106_DECISIONS:
        return (
            "v1107-v1106-predecessor-missing",
            False,
            f"unexpected V1106 decision={manifest.get('v1106', {}).get('decision')!r}",
            "rerun or inspect V1106 before owner classification",
        )
    owner = manifest.get("analysis", {}).get("mutex_owner", {}).get("owner") or {}
    owner_state = manifest.get("analysis", {}).get("owner_thread_state") or {}
    waiter_state = manifest.get("analysis", {}).get("waiter_thread_state") or {}
    owner_wchans = set(owner_state.get("wchans") or [])
    waiter_wchans = set(waiter_state.get("wchans") or [])
    if not owner:
        return (
            "v1107-modem-mutex-owner-not-found",
            False,
            "no unmatched modem mutex holder was reconstructed before CNSS futex wait",
            "extend raw event window or trace owner stack directly",
        )
    if {"__subsystem_get", "_request_firmware"} & owner_wchans and "futex_wait_queue_me" in waiter_wchans:
        return (
            "v1107-modem-mutex-owner-blocked-in-subsystem-get",
            True,
            (
                f"owner={owner} owner_wchans={sorted(owner_wchans)} "
                f"waiter_wchans={sorted(waiter_wchans)}"
            ),
            "test PM ordering without pre-CNSS per_proxy connect or repair firmware/subsystem path before PM connect",
        )
    return (
        "v1107-modem-mutex-owner-classified",
        True,
        f"owner={owner} owner_wchans={sorted(owner_wchans)} waiter_wchans={sorted(waiter_wchans)}",
        "interpret owner wait state and choose minimal PM ordering repair",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v1106_manifest = load_json(args.v1106_manifest)
    tracefs = (v1106_manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    target = target_cnss_pending(tracefs)
    owner = classify_owner(tracefs, target) if args.command == "run" and target else {}
    owner_tid = str((owner.get("owner") or {}).get("tid", ""))
    waiter_tid = str(target.get("tid", ""))
    manifest: dict[str, Any] = {
        "cycle": "v1107",
        "generated_at": now_iso(),
        "command": args.command,
        "v1106": {
            "manifest": str(repo_path(args.v1106_manifest)),
            "decision": v1106_manifest.get("decision", ""),
            "pass": bool(v1106_manifest.get("pass")),
        },
        "analysis": {},
        "device_command_executed": False,
        "tracefs_write_executed": False,
        "bpf_attach_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
    }
    if args.command == "run":
        manifest["analysis"] = {
            "target_cnss_pending": target,
            "mutex_owner": owner,
            "owner_thread_state": thread_state(tracefs, owner_tid) if owner_tid else {},
            "waiter_thread_state": thread_state(tracefs, waiter_tid) if waiter_tid else {},
            "disassembly": disassemble(args.pm_service, str((owner.get("owner") or {}).get("return_offset", "")), store),
        }
    decision, passed, reason, next_step = decide(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest.get("analysis") or {}
    return "\n".join([
        "# V1107 PM Server Mutex Owner Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_command_executed: `{manifest['device_command_executed']}`",
        f"- tracefs_write_executed: `{manifest['tracefs_write_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Analysis",
        "",
        "```json",
        json.dumps(analysis, indent=2, sort_keys=True),
        "```",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1106-manifest", type=Path, default=DEFAULT_V1106_MANIFEST)
    parser.add_argument("--pm-service", type=Path, default=DEFAULT_PM_SERVICE)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    LATEST_POINTER.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(LATEST_POINTER, str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_command_executed: {manifest['device_command_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
