#!/usr/bin/env python3
"""V431 read-only Android Wi-Fi runtime gap mapper.

V431 collects the Android boot-complete Wi-Fi runtime surfaces that are missing
from the native private namespace experiments: init service definitions,
properties, running daemon metadata, sockets, device nodes, netdev/rfkill state,
and data/vendor/wifi layout.  It is read-only and does not enable Wi-Fi, scan,
connect, link up interfaces, mutate properties, write rfkill/sysfs, start
daemons, reboot, flash, or touch credentials.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shlex
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v431-android-runtime-gap-map")
RUNTIME_TARGETS = (
    "android.hardware.wifi@1.0-service",
    "vendor.samsung.hardware.wifi@2.0-service",
    "wificond",
    "wpa_supplicant",
)
ACTIVE_WIFI_PATTERNS = (
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bwpa_cli\b", re.IGNORECASE),
    re.compile(r"(?:^|[;&]\s*)(?:/[^ ]*/)?(?:wpa_supplicant|hostapd|cnss-daemon|wificond|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/class/rfkill", re.IGNORECASE),
    re.compile(r">\s*/sys/module/firmware_class/parameters/path", re.IGNORECASE),
    re.compile(r"\bsetprop\b", re.IGNORECASE),
)
WIFI_LINE_RE = re.compile(
    r"wifi|wlan|wificond|supplicant|hostapd|cnss|qcom|qcacld|IWifi|ISehWifi|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi",
    re.IGNORECASE,
)

ANDROID_SHELL_CAPTURES: tuple[tuple[str, str, int], ...] = (
    (
        "identity-props",
        "for p in sys.boot_completed ro.build.version.release ro.build.version.sdk ro.product.name ro.hardware "
        "init.svc.servicemanager init.svc.hwservicemanager init.svc.vendor.wifi_hal_ext init.svc.vendor.wifi_hal "
        "init.svc.wificond init.svc.wpa_supplicant wlan.driver.status wifi.interface; do echo \"$p=$(getprop $p 2>/dev/null)\"; done",
        20,
    ),
    (
        "wifi-props-filtered",
        "getprop 2>/dev/null | grep -Ei '(^|\\[)(init\\.svc\\.|ro\\.|persist\\.|vendor\\.|wifi|wlan|cnss|qcom|qcacld|supplicant|hostapd|wificond)' || true",
        30,
    ),
    (
        "wifi-processes",
        "ps -AZ 2>/dev/null | grep -Ei 'servicemanager|hwservicemanager|vndservicemanager|android\\.hardware\\.wifi|vendor\\.samsung\\.hardware\\.wifi|wificond|supplicant|hostapd|cnss|wlan|wifi' || "
        "ps -A 2>/dev/null | grep -Ei 'servicemanager|hwservicemanager|vndservicemanager|android\\.hardware\\.wifi|vendor\\.samsung\\.hardware\\.wifi|wificond|supplicant|hostapd|cnss|wlan|wifi' || true",
        25,
    ),
    (
        "init-rc-wifi-context",
        "grep -RniE -C 8 'vendor\\.samsung\\.hardware\\.wifi|android\\.hardware\\.wifi|wificond|wpa_supplicant|hostapd|cnss|wlan' "
        "/vendor/etc/init /odm/etc/init /system/etc/init /system_ext/etc/init /product/etc/init 2>/dev/null || true",
        45,
    ),
    (
        "service-list-wifi",
        "service list 2>/dev/null | grep -Ei 'wifi|wlan|wificond|supplicant|hostapd|netd|connectivity' || true",
        25,
    ),
    (
        "dumpsys-service-names-wifi",
        "dumpsys -l 2>/dev/null | grep -Ei 'wifi|wlan|wificond|supplicant|hostapd|netd|connectivity' || true",
        25,
    ),
    (
        "target-proc-summary",
        "for n in android.hardware.wifi@1.0-service vendor.samsung.hardware.wifi@2.0-service wificond wpa_supplicant; do "
        "echo \"=== $n ===\"; for p in $(pidof $n 2>/dev/null); do echo \"pid=$p\"; "
        "tr '\\0' ' ' < /proc/$p/cmdline 2>/dev/null; echo; "
        "cat /proc/$p/status 2>/dev/null | grep -E '^(Name|State|Pid|PPid|Uid|Gid|Groups|Threads|Cap(Inh|Prm|Eff|Bnd|Amb)|Seccomp):' || true; "
        "cat /proc/$p/cgroup 2>/dev/null; "
        "for ns in /proc/$p/ns/*; do [ -e \"$ns\" ] && echo \"ns:${ns##*/}=$(readlink $ns 2>/dev/null)\"; done; "
        "done; done; true",
        35,
    ),
    (
        "target-proc-fd-sockets",
        "for n in android.hardware.wifi@1.0-service vendor.samsung.hardware.wifi@2.0-service wificond wpa_supplicant; do "
        "echo \"=== $n ===\"; for p in $(pidof $n 2>/dev/null); do echo \"pid=$p\"; "
        "ls -lZ /proc/$p/fd 2>/dev/null | grep -Ei 'socket|binder|hwbinder|vndbinder|wlan|wifi|supplicant|hostapd|netlink|eventpoll' || true; "
        "done; done",
        35,
    ),
    (
        "target-proc-maps-wifi",
        "for n in android.hardware.wifi@1.0-service vendor.samsung.hardware.wifi@2.0-service wificond wpa_supplicant; do "
        "echo \"=== $n ===\"; for p in $(pidof $n 2>/dev/null); do echo \"pid=$p\"; "
        "grep -Ei 'wifi|wlan|wpa|supplicant|hostapd|cnss|qca|qcacld|hidl|binder|vndk' /proc/$p/maps 2>/dev/null || true; "
        "done; done",
        35,
    ),
    (
        "socket-surface-wifi",
        "echo '--- /dev/socket ---'; ls -laZ /dev/socket 2>/dev/null | grep -Ei 'wifi|wpa|supplicant|hostapd|wificond|netd|hal|vendor' || true; "
        "echo '--- /proc/net/unix ---'; cat /proc/net/unix 2>/dev/null | grep -Ei 'wifi|wpa|supplicant|hostapd|wificond|netd|hal|vendor' || true",
        30,
    ),
    (
        "devnode-surface-wifi",
        "for p in /dev/binder /dev/hwbinder /dev/vndbinder /dev/rfkill /dev/wlan* /dev/cnss* /dev/qce* /dev/qseecom /dev/diag /dev/socket/wpa_* /dev/socket/wpa*; do "
        "[ -e \"$p\" ] && ls -lZ \"$p\" 2>/dev/null; done; true",
        25,
    ),
    (
        "netdev-rfkill-readonly",
        "ip link show 2>/dev/null; echo '--- sysfs net ---'; "
        "for d in /sys/class/net/*; do [ -e \"$d\" ] || continue; echo \"node=$d\"; "
        "for f in ifindex type operstate carrier mtu address; do [ -e \"$d/$f\" ] && echo \"$f=$(cat \"$d/$f\" 2>/dev/null)\"; done; "
        "[ -e \"$d/device/driver\" ] && echo \"driver=$(readlink \"$d/device/driver\" 2>/dev/null)\"; done; "
        "echo '--- rfkill ---'; for r in /sys/class/rfkill/rfkill*; do [ -e \"$r\" ] || continue; echo \"node=$r\"; "
        "for f in name type state soft hard persistent; do [ -e \"$r/$f\" ] && echo \"$f=$(cat \"$r/$f\" 2>/dev/null)\"; done; done",
        35,
    ),
    (
        "data-vendor-wifi-layout",
        "for d in /data/vendor/wifi /data/vendor/wifi/wpa /data/vendor/wifi/hostapd /data/misc/wifi; do "
        "[ -e \"$d\" ] || continue; echo \"=== $d ===\"; ls -laZ \"$d\" 2>/dev/null | head -120; done; "
        "find /data/vendor/wifi -maxdepth 3 2>/dev/null | sed -n '1,220p'",
        35,
    ),
)


@dataclass
class CaptureRecord:
    name: str
    command: str
    ok: bool
    rc: int | None
    duration_sec: float
    file: str
    text: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default="")
    parser.add_argument("--timeout", type=int, default=25)
    parser.add_argument("--su", action="store_true", help="run adb shell commands through su -c")
    parser.add_argument("--v430-manifest", type=Path, default=None)
    parser.add_argument("--v429-manifest", type=Path, default=None)
    parser.add_argument("--v407-manifest", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.+-]+", "-", value).strip("-") or "capture"


def adb_base(args: argparse.Namespace) -> list[str]:
    command = [args.adb]
    if args.serial:
        command.extend(["-s", args.serial])
    return command


def adb_shell_command(args: argparse.Namespace, shell_command: str) -> list[str]:
    if args.su:
        return [*adb_base(args), "shell", f"su -c {shlex.quote(shell_command)}"]
    return [*adb_base(args), "shell", shell_command]


def display_command(command: list[str]) -> str:
    redacted = ["<adb-serial>" if index > 0 and command[index - 1] == "-s" else part for index, part in enumerate(command)]
    return " ".join(shlex.quote(part) for part in redacted)


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?im)^([A-Za-z0-9_.:-]+)(\s+(?:device|recovery|sideload|offline|unauthorized)\b)", r"<adb-serial>\2", text)
    text = re.sub(r"(?i)(\b(?:psk|password|passphrase|ssid|bssid|passpoint|identity|anonymous_identity|private_key|client_cert|ca_cert)\b)[:=]\s*([^\s\]]+)", r"\1=<redacted>", text)
    text = re.sub(
        r"(?i)(\b(?:androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|ro\.boot\.serialno|serialno)\b)[:=]\s*([^\s\]]+)",
        r"\1=<redacted>",
        text,
    )
    text = re.sub(r"(?i)(\[(?:ro\.serialno|ro\.boot\.serialno)\]:\s*\[)([^\]]+)(\])", r"\1<redacted>\3", text)
    return text


def truncate_text(text: str, limit: int = 16000) -> str:
    redacted = redact_text(text)
    if len(redacted) > limit:
        return redacted[:limit] + "\n[truncated in manifest]\n"
    return redacted


def validate_no_active_wifi_commands() -> None:
    joined = "\n".join(command for _, command, _ in ANDROID_SHELL_CAPTURES)
    for pattern in ACTIVE_WIFI_PATTERNS:
        if pattern.search(joined):
            raise RuntimeError(f"active or sensitive Wi-Fi command pattern found: {pattern.pattern}")


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
    except FileNotFoundError as exc:
        return None, "", str(exc), time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        text = exc.stdout if isinstance(exc.stdout, str) else ""
        return None, text, f"timeout after {timeout}s", time.monotonic() - started
    except Exception as exc:  # noqa: BLE001 - evidence collector preserves failure detail
        return None, "", str(exc), time.monotonic() - started


def write_capture(store: EvidenceStore, name: str, command: list[str], text: str, error: str, rc: int | None) -> str:
    body = "\n".join(
        [
            f"$ {display_command(command)}",
            redact_text(text if text else error).rstrip(),
            f"rc={rc}",
            "",
        ]
    )
    path = store.write_text(f"commands/{safe_name(name)}.txt", body)
    return str(path.relative_to(store.run_dir))


def capture_command(store: EvidenceStore, name: str, command: list[str], timeout: int) -> CaptureRecord:
    rc, text, error, duration = run_process(command, timeout)
    relative = write_capture(store, name, command, text, error, rc)
    return CaptureRecord(
        name=name,
        command=display_command(command),
        ok=rc == 0,
        rc=rc,
        duration_sec=duration,
        file=relative,
        text=truncate_text(text),
        error=error,
    )


def read_capture_text(captures: list[CaptureRecord], name: str) -> str:
    for capture in captures:
        if capture.name == name:
            return capture.text
    return ""


def read_capture_file_text(store: EvidenceStore, captures: list[CaptureRecord], name: str) -> str:
    for capture in captures:
        if capture.name != name:
            continue
        path = store.run_dir / capture.file
        if not path.exists():
            return capture.text
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def adb_state(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[CaptureRecord], str]:
    captures = [
        capture_command(store, "adb-devices", [*adb_base(args), "devices", "-l"], args.timeout),
        capture_command(store, "adb-get-state", [*adb_base(args), "get-state"], args.timeout),
    ]
    state_text = read_capture_text(captures, "adb-get-state").strip()
    state = state_text.splitlines()[-1].strip() if state_text else ""
    if captures[1].rc is None and ("No such file" in captures[1].error or "No such file" in state_text):
        state = "adb-missing"
    return captures, state


def latest_manifest(pattern: str) -> Path | None:
    candidates = sorted(repo_path("tmp/wifi").glob(pattern), key=lambda path: path.stat().st_mtime)
    for candidate in reversed(candidates):
        manifest = candidate / "manifest.json"
        if manifest.exists():
            return manifest
    return None


def load_manifest(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"present": False, "path": "", "decision": "missing", "pass": False}
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved), "decision": "missing", "pass": False}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    return {
        "present": True,
        "path": str(resolved),
        "decision": payload.get("decision"),
        "pass": payload.get("pass"),
        "reason": payload.get("reason"),
        "live_result": payload.get("live_result"),
        "context": payload.get("context"),
        "classification": payload.get("classification"),
    }


def load_references(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "v430": load_manifest(args.v430_manifest or latest_manifest("v430-android-lshal-explicit-handoff-live-fix-*")),
        "v429": load_manifest(args.v429_manifest or latest_manifest("v429-lshal-minimal-split-live-*")),
        "v407": load_manifest(args.v407_manifest or latest_manifest("v407-composite-hal-start-only-retry-live-*")),
    }


def unique_matching_lines(text: str, limit: int = 260) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("$") or "grep -" in line:
            continue
        if not WIFI_LINE_RE.search(line):
            continue
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def evidence_text(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.startswith("$"))


def collect_android(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[CaptureRecord], str]:
    captures, state = adb_state(args, store)
    if state != "device":
        return captures, state
    for name, shell_command, timeout in ANDROID_SHELL_CAPTURES:
        captures.append(capture_command(store, name, adb_shell_command(args, shell_command), max(timeout, args.timeout)))
    return captures, state


def has_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def classify(args: argparse.Namespace, store: EvidenceStore, captures: list[CaptureRecord], state: str, refs: dict[str, Any]) -> dict[str, Any]:
    identity_text = read_capture_file_text(store, captures, "identity-props")
    props_text = read_capture_file_text(store, captures, "wifi-props-filtered")
    processes_text = read_capture_file_text(store, captures, "wifi-processes")
    init_text = read_capture_file_text(store, captures, "init-rc-wifi-context")
    service_text = read_capture_file_text(store, captures, "service-list-wifi") + "\n" + read_capture_file_text(store, captures, "dumpsys-service-names-wifi")
    proc_summary_text = read_capture_file_text(store, captures, "target-proc-summary")
    proc_fd_text = read_capture_file_text(store, captures, "target-proc-fd-sockets")
    maps_text = read_capture_file_text(store, captures, "target-proc-maps-wifi")
    socket_text = read_capture_file_text(store, captures, "socket-surface-wifi")
    devnode_text = read_capture_file_text(store, captures, "devnode-surface-wifi")
    netdev_text = read_capture_file_text(store, captures, "netdev-rfkill-readonly")
    data_text = read_capture_file_text(store, captures, "data-vendor-wifi-layout")
    service_evidence = evidence_text(service_text)
    socket_evidence = evidence_text(socket_text)
    devnode_evidence = evidence_text(devnode_text)
    netdev_evidence = evidence_text(netdev_text)
    data_evidence = evidence_text(data_text)

    boot_complete = "sys.boot_completed=1" in identity_text
    process_presence = {target: target in processes_text for target in RUNTIME_TARGETS}
    service_def_presence = {target: target in init_text for target in RUNTIME_TARGETS}
    runtime_service_count = sum(1 for present in process_presence.values() if present)
    service_def_count = sum(1 for present in service_def_presence.values() if present)
    socket_surface_present = has_any(socket_evidence, ("wpa", "wificond", "wifi", "hostapd"))
    devnode_surface_present = has_any(devnode_evidence, ("/dev/binder", "/dev/hwbinder", "/dev/vndbinder", "rfkill", "/dev/wlan"))
    netdev_surface_present = has_any(netdev_evidence, ("wlan", "p2p", "wifi", "rfkill"))
    data_surface_present = any(
        line.startswith("=== /data/vendor/wifi") or line.startswith("/data/vendor/wifi")
        for line in data_evidence.splitlines()
    )
    framework_service_present = has_any(service_evidence, ("wifi", "sem_wifi", "wifiscanner"))
    native_v429_timeout = (refs.get("v429", {}).get("live_result") or {}).get("service_query_reason") == "lshal-timeout"
    v430_targets = (((refs.get("v430", {}).get("context") or {}).get("comparison") or {}).get("matched_targets") or [])

    if state == "adb-missing":
        decision = "v431-android-runtime-gap-adb-missing"
        pass_ok = False
        reason = "adb executable is unavailable on host"
    elif state != "device":
        decision = "v431-android-runtime-gap-waiting-for-android"
        pass_ok = False
        reason = f"Android ADB is not online (state={state or 'missing'})"
    elif not boot_complete:
        decision = "v431-android-runtime-gap-bootcomplete-missing"
        pass_ok = False
        reason = "Android ADB is online, but sys.boot_completed=1 was not observed"
    elif runtime_service_count >= 3 and service_def_count >= 3 and framework_service_present:
        decision = "v431-android-runtime-gap-map-pass"
        pass_ok = True
        reason = "Android boot-complete Wi-Fi runtime map captured running services, init definitions, and framework/service surfaces"
    elif runtime_service_count >= 3:
        decision = "v431-android-runtime-gap-runtime-present-definitions-partial"
        pass_ok = True
        reason = "Android boot-complete Wi-Fi runtime daemons are present, but init definition capture is partial"
    else:
        decision = "v431-android-runtime-gap-map-incomplete"
        pass_ok = False
        reason = "Android Wi-Fi runtime surface capture did not prove the expected daemon set"

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "adb_state": state,
        "boot_complete": boot_complete,
        "runtime_targets": list(RUNTIME_TARGETS),
        "process_presence": process_presence,
        "service_def_presence": service_def_presence,
        "runtime_service_count": runtime_service_count,
        "service_def_count": service_def_count,
        "socket_surface_present": socket_surface_present,
        "devnode_surface_present": devnode_surface_present,
        "netdev_surface_present": netdev_surface_present,
        "data_surface_present": data_surface_present,
        "framework_service_present": framework_service_present,
        "native_v429_timeout": native_v429_timeout,
        "v430_matched_targets": v430_targets,
        "refs": refs,
        "wifi_prop_lines": unique_matching_lines(props_text),
        "wifi_process_lines": unique_matching_lines(processes_text),
        "wifi_init_lines": unique_matching_lines(init_text),
        "wifi_service_lines": unique_matching_lines(service_text),
        "wifi_proc_summary_lines": unique_matching_lines(proc_summary_text),
        "wifi_fd_lines": unique_matching_lines(proc_fd_text),
        "wifi_maps_lines": unique_matching_lines(maps_text),
        "wifi_socket_lines": unique_matching_lines(socket_text),
        "wifi_devnode_lines": unique_matching_lines(devnode_text),
        "wifi_netdev_lines": unique_matching_lines(netdev_text),
        "wifi_data_lines": unique_matching_lines(data_text),
    }


def guardrails() -> list[str]:
    return [
        "read-only ADB shell commands only",
        "no svc wifi, cmd wifi, scan, connect, link-up, credential, DHCP, or routing command",
        "no rfkill/sysfs write, module load/unload, firmware path write, setprop, reboot, flash, or partition write",
        "no direct Wi-Fi daemon start command",
        "no file contents from /data/vendor/wifi; list layout only",
        "captured text redacts serials, MACs, SSID/passphrase-like fields",
    ]


def run_plan(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "command": "plan",
        "decision": "v431-android-runtime-gap-map-plan-ready",
        "pass": True,
        "reason": "read-only Android Wi-Fi runtime gap map plan generated",
        "host": collect_host_metadata(),
        "references": load_references(args),
        "runtime_targets": list(RUNTIME_TARGETS),
        "host_commands": [
            display_command([*adb_base(args), "devices", "-l"]),
            display_command([*adb_base(args), "get-state"]),
        ],
        "android_shell_captures": [{"name": name, "command": command, "timeout": timeout} for name, command, timeout in ANDROID_SHELL_CAPTURES],
        "guardrails": guardrails(),
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }


def run_preflight(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    captures, state = adb_state(args, store)
    if state == "device":
        decision = "v431-android-runtime-gap-adb-online"
        pass_ok = True
        reason = "Android ADB is online; run mode can collect read-only runtime gap map"
    elif state == "adb-missing":
        decision = "v431-android-runtime-gap-adb-missing"
        pass_ok = False
        reason = "adb executable is unavailable on host"
    else:
        decision = "v431-android-runtime-gap-waiting-for-android"
        pass_ok = True
        reason = f"Android ADB is not online yet (state={state or 'missing'})"
    return {
        "generated_at": now_iso(),
        "command": "preflight",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "references": load_references(args),
        "adb_state": state,
        "captures": [asdict(capture) for capture in captures],
        "guardrails": guardrails(),
        "device_commands_executed": True,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }


def run_capture_mode(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    refs = load_references(args)
    captures, state = collect_android(args, store)
    classification = classify(args, store, captures, state, refs)
    return {
        "generated_at": now_iso(),
        "command": "run",
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "host": collect_host_metadata(),
        "classification": classification,
        "captures": [asdict(capture) for capture in captures],
        "guardrails": guardrails(),
        "device_commands_executed": True,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest.get("classification", {})
    captures = manifest.get("captures", [])
    capture_rows = [
        [item["name"], "ok" if item["ok"] else "fail", str(item["rc"]), f"{item['duration_sec']:.3f}s", item["file"]]
        for item in captures
    ]
    target_rows = [
        [
            target,
            "yes" if classification.get("process_presence", {}).get(target) else "no",
            "yes" if classification.get("service_def_presence", {}).get(target) else "no",
        ]
        for target in RUNTIME_TARGETS
    ]
    surface_rows = [
        ["framework_service", classification.get("framework_service_present", "-")],
        ["socket_surface", classification.get("socket_surface_present", "-")],
        ["devnode_surface", classification.get("devnode_surface_present", "-")],
        ["netdev_surface", classification.get("netdev_surface_present", "-")],
        ["data_vendor_wifi", classification.get("data_surface_present", "-")],
        ["native_v429_timeout", classification.get("native_v429_timeout", "-")],
    ]
    evidence_rows: list[list[str]] = []
    for key in (
        "wifi_process_lines",
        "wifi_init_lines",
        "wifi_service_lines",
        "wifi_socket_lines",
        "wifi_devnode_lines",
        "wifi_netdev_lines",
        "wifi_data_lines",
    ):
        for value in classification.get(key, [])[:20]:
            evidence_rows.append([key, value])
    return "\n".join(
        [
            "# V431 Android Wi-Fi Runtime Gap Map",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- adb_state: `{manifest.get('adb_state', classification.get('adb_state', '-'))}`",
            f"- boot_complete: `{classification.get('boot_complete', '-')}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Target Runtime Services",
            "",
            markdown_table(["target", "process", "init rc definition"], target_rows),
            "",
            "## Surface Summary",
            "",
            markdown_table(["surface", "present"], [[str(a), str(b)] for a, b in surface_rows]),
            "",
            "## Evidence Lines",
            "",
            markdown_table(["source", "line"], evidence_rows if evidence_rows else [["-", "-"]]),
            "",
            "## Captures",
            "",
            markdown_table(["name", "status", "rc", "duration", "file"], capture_rows if capture_rows else [["-", "-", "-", "-", "-"]]),
            "",
            "## Guardrails",
            "",
            *[f"- {item}" for item in manifest["guardrails"]],
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    validate_no_active_wifi_commands()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        manifest = run_plan(args, store)
    elif args.command == "preflight":
        manifest = run_preflight(args, store)
    else:
        manifest = run_capture_mode(args, store)
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
