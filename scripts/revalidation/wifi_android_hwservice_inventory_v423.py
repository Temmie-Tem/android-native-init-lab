#!/usr/bin/env python3
"""V423 read-only Android hwservice/lshal Wi-Fi inventory.

V423 answers the post-V422 question from the full Android runtime: which Wi-Fi
HIDL/hwservice names are visible when Android owns the real service managers?

The collector is read-only.  It does not enable Wi-Fi, scan, connect, link up an
interface, write rfkill/sysfs, start daemons, change properties, reboot, flash,
or touch credentials.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v423-android-hwservice-inventory")
TARGETED_WAIT_TARGETS = (
    "vendor.samsung.hardware.wifi@2.0::ISehWifi/default",
    "vendor.samsung.hardware.wifi@2.1::ISehWifi/default",
    "vendor.samsung.hardware.wifi@2.2::ISehWifi/default",
)
WIFI_LINE_RE = re.compile(
    r"wifi|wlan|wificond|supplicant|hostapd|IWifi|ISehWifi|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi",
    re.IGNORECASE,
)
ACTIVE_WIFI_PATTERNS = (
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\b(?:insmod|rmmod|modprobe)\b", re.IGNORECASE),
    re.compile(r"\bsvc\s+wifi\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\s+set-wifi-enabled\b", re.IGNORECASE),
    re.compile(r"\bcmd\s+wifi\s+(connect-network|start-scan|force-country-code|set-scan-always-available)\b", re.IGNORECASE),
    re.compile(r"\bwpa_cli\b", re.IGNORECASE),
    re.compile(r"(?:^|[;&]\s*)(?:/[^ ]*/)?(?:wpa_supplicant|hostapd|cnss-daemon|wificond)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/class/rfkill", re.IGNORECASE),
    re.compile(r">\s*/sys/module/firmware_class/parameters/path", re.IGNORECASE),
    re.compile(r"\bsetprop\b", re.IGNORECASE),
)

ANDROID_SHELL_CAPTURES: tuple[tuple[str, str, int], ...] = (
    (
        "identity-props",
        "for p in sys.boot_completed ro.build.version.release ro.build.version.sdk ro.product.name ro.hardware "
        "init.svc.servicemanager init.svc.hwservicemanager init.svc.wificond init.svc.wpa_supplicant "
        "init.svc.vendor.wifi_hal_ext init.svc.vendor.wifi_hal; do echo \"$p=$(getprop $p 2>/dev/null)\"; done",
        20,
    ),
    (
        "service-processes",
        "ps -AZ 2>/dev/null | grep -Ei 'servicemanager|hwservicemanager|vndservicemanager|android\\.hardware\\.wifi|vendor\\.samsung\\.hardware\\.wifi|wificond|supplicant|hostapd|cnss|wlan|wifi' || "
        "ps -A 2>/dev/null | grep -Ei 'servicemanager|hwservicemanager|vndservicemanager|android\\.hardware\\.wifi|vendor\\.samsung\\.hardware\\.wifi|wificond|supplicant|hostapd|cnss|wlan|wifi' || true",
        25,
    ),
    (
        "lshal-binderized-neat",
        "lshal list --types=binderized --neat 2>&1",
        45,
    ),
    (
        "lshal-wifi-filter",
        "lshal list --types=binderized --neat 2>&1 | grep -Ei 'wifi|wlan|IWifi|ISehWifi|supplicant|hostapd|wificond|vendor\\.samsung\\.hardware\\.wifi|android\\.hardware\\.wifi' || true",
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
        "vintf-wifi-hal",
        "grep -RHiE 'android\\.hardware\\.wifi|vendor.*wifi|IWifi|ISehWifi|supplicant|hostapd|wificond' "
        "/vendor/etc/vintf /odm/etc/vintf /system/etc/vintf /system_ext/etc/vintf /product/etc/vintf 2>/dev/null || true",
        30,
    ),
    (
        "netdev-rfkill-readonly",
        "ip link show 2>/dev/null; echo '--- rfkill ---'; "
        "for r in /sys/class/rfkill/rfkill*; do [ -e \"$r\" ] || continue; echo \"node=$r\"; "
        "for f in name type state soft hard persistent; do [ -e \"$r/$f\" ] && echo \"$f=$(cat \"$r/$f\" 2>/dev/null)\"; done; done",
        30,
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
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--su", action="store_true", help="run adb shell commands through su -c")
    parser.add_argument("--v422-manifest", type=Path, default=None)
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
        return [*adb_base(args), "shell", "su", "-c", shell_command]
    return [*adb_base(args), "shell", shell_command]


def display_command(command: list[str]) -> str:
    redacted = ["<adb-serial>" if index > 0 and command[index - 1] == "-s" else part for index, part in enumerate(command)]
    return " ".join(shlex.quote(part) for part in redacted)


def redact_text(text: str) -> str:
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", "<mac>", text)
    text = re.sub(r"(?im)^([A-Za-z0-9_.:-]+)(\s+(?:device|recovery|sideload|offline|unauthorized)\b)", r"<adb-serial>\2", text)
    text = re.sub(r"(?i)(\b(?:psk|password|passphrase|ssid|bssid)\b)[:=]\s*([^\s\]]+)", r"\1=<redacted>", text)
    text = re.sub(
        r"(?i)(\b(?:androidboot\.serialno|androidboot\.ap_serial|ro\.serialno|ro\.boot\.serialno|serialno)\b)[:=]\s*([^\s\]]+)",
        r"\1=<redacted>",
        text,
    )
    text = re.sub(r"(?i)(\[(?:ro\.serialno|ro\.boot\.serialno)\]:\s*\[)([^\]]+)(\])", r"\1<redacted>\3", text)
    return text


def truncate_text(text: str, limit: int = 12000) -> str:
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


def load_v422(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = args.v422_manifest or latest_manifest("v422-micro-lshal-wait-live-*")
    if manifest_path is None:
        return {"present": False, "path": "", "decision": "missing", "pass": False}
    resolved = repo_path(manifest_path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved), "decision": "missing", "pass": False}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    return {
        "present": True,
        "path": str(resolved),
        "decision": payload.get("decision"),
        "pass": payload.get("pass"),
        "reason": payload.get("reason"),
        "micro_query_result": (payload.get("live_result") or {}).get("micro_query_result"),
        "micro_query_reason": (payload.get("live_result") or {}).get("micro_query_reason"),
    }


def unique_matching_lines(text: str, limit: int = 200) -> list[str]:
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


def collect_android(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[CaptureRecord], str]:
    captures, state = adb_state(args, store)
    if state != "device":
        return captures, state
    for name, shell_command, timeout in ANDROID_SHELL_CAPTURES:
        captures.append(capture_command(store, name, adb_shell_command(args, shell_command), max(timeout, args.timeout)))
    return captures, state


def classify(args: argparse.Namespace, store: EvidenceStore, captures: list[CaptureRecord], state: str, v422: dict[str, Any]) -> dict[str, Any]:
    lshal_text = read_capture_file_text(store, captures, "lshal-binderized-neat") + "\n" + read_capture_file_text(store, captures, "lshal-wifi-filter")
    service_text = read_capture_file_text(store, captures, "service-list-wifi") + "\n" + read_capture_file_text(store, captures, "dumpsys-service-names-wifi")
    process_text = read_capture_file_text(store, captures, "service-processes")
    vintf_text = read_capture_file_text(store, captures, "vintf-wifi-hal")
    netdev_text = read_capture_file_text(store, captures, "netdev-rfkill-readonly")
    wifi_lshal_lines = unique_matching_lines(lshal_text)
    wifi_service_lines = unique_matching_lines(service_text)
    wifi_process_lines = unique_matching_lines(process_text)
    wifi_vintf_lines = unique_matching_lines(vintf_text)
    wifi_netdev_lines = unique_matching_lines(netdev_text)
    matched_targets = [target for target in TARGETED_WAIT_TARGETS if target in lshal_text]
    lshal_ok = any(capture.name == "lshal-binderized-neat" and capture.ok for capture in captures)
    android_online = state == "device"

    if state == "adb-missing":
        decision = "v423-android-hwservice-adb-missing"
        pass_ok = False
        reason = "adb executable is unavailable on host"
    elif not android_online:
        decision = "v423-android-hwservice-waiting-for-android"
        pass_ok = False
        reason = f"Android ADB is not online (state={state or 'missing'})"
    elif matched_targets:
        decision = "v423-android-hwservice-targets-present"
        pass_ok = True
        reason = "Android runtime lshal contains V414/V422 target fqinstances"
    elif wifi_lshal_lines:
        decision = "v423-android-hwservice-wifi-present-target-mismatch"
        pass_ok = True
        reason = "Android runtime lshal contains Wi-Fi HAL evidence but not the V422 target fqinstances"
    elif lshal_ok:
        decision = "v423-android-hwservice-no-wifi-targets"
        pass_ok = True
        reason = "Android runtime lshal completed but no Wi-Fi HAL target line was found"
    else:
        decision = "v423-android-hwservice-lshal-incomplete"
        pass_ok = False
        reason = "Android runtime capture ran but lshal did not complete"

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "adb_state": state,
        "v422": v422,
        "targeted_wait_targets": list(TARGETED_WAIT_TARGETS),
        "matched_targets": matched_targets,
        "lshal_ok": lshal_ok,
        "wifi_lshal_lines": wifi_lshal_lines,
        "wifi_service_lines": wifi_service_lines,
        "wifi_process_lines": wifi_process_lines,
        "wifi_vintf_lines": wifi_vintf_lines,
        "wifi_netdev_lines": wifi_netdev_lines,
    }


def run_plan(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "command": "plan",
        "decision": "v423-android-hwservice-inventory-plan-ready",
        "pass": True,
        "reason": "read-only Android hwservice/lshal inventory plan generated",
        "host": collect_host_metadata(),
        "v422": load_v422(args),
        "targeted_wait_targets": list(TARGETED_WAIT_TARGETS),
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
        decision = "v423-android-hwservice-adb-online"
        pass_ok = True
        reason = "Android ADB is online; run mode can collect read-only hwservice inventory"
    elif state == "adb-missing":
        decision = "v423-android-hwservice-adb-missing"
        pass_ok = False
        reason = "adb executable is unavailable on host"
    else:
        decision = "v423-android-hwservice-waiting-for-android"
        pass_ok = True
        reason = f"Android ADB is not online yet (state={state or 'missing'})"
    return {
        "generated_at": now_iso(),
        "command": "preflight",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "v422": load_v422(args),
        "adb_state": state,
        "captures": [asdict(capture) for capture in captures],
        "guardrails": guardrails(),
        "device_commands_executed": True,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }


def run_capture_mode(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v422 = load_v422(args)
    captures, state = collect_android(args, store)
    classification = classify(args, store, captures, state, v422)
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


def guardrails() -> list[str]:
    return [
        "read-only ADB shell commands only",
        "no svc wifi, cmd wifi set-wifi-enabled, scan, connect, link-up, credential, DHCP, or routing command",
        "no rfkill/sysfs write, module load/unload, firmware path write, setprop, reboot, flash, or partition write",
        "no wificond, supplicant, hostapd, CNSS, or Wi-Fi HAL daemon start command",
        "captured text redacts serials, MACs, SSID/passphrase-like fields",
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest.get("classification", {})
    captures = manifest.get("captures", [])
    capture_rows = [
        [item["name"], "ok" if item["ok"] else "fail", str(item["rc"]), f"{item['duration_sec']:.3f}s", item["file"]]
        for item in captures
    ]
    target_rows = [[target, "present" if target in classification.get("matched_targets", []) else "not-seen"] for target in TARGETED_WAIT_TARGETS]
    evidence_rows = []
    for key in ("wifi_lshal_lines", "wifi_service_lines", "wifi_process_lines", "wifi_vintf_lines", "wifi_netdev_lines"):
        for value in classification.get(key, [])[:30]:
            evidence_rows.append([key, value])
    return "\n".join(
        [
            "# V423 Android hwservice/lshal Wi-Fi Inventory",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- adb_state: `{manifest.get('adb_state', classification.get('adb_state', '-'))}`",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Target Match",
            "",
            markdown_table(["fqinstance", "state"], target_rows),
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
