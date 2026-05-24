#!/usr/bin/env python3
"""V784 read-only native memshare/CMA surface classifier.

V783 identified a concrete native lead: memshare/CMA allocation failures appear
at the modem sysmon window while Android proceeds to service-notifier 74/180,
WLAN-PD, ICNSS-QMI, BDF, and wlan0.  V784 does not trigger Wi-Fi.  It only reads
the current native memshare/CMA/reserved-memory surface and compares it with the
previous V782 failure evidence.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v784-memshare-cma-surface")
LATEST_POINTER = Path("tmp/wifi/latest-v784-memshare-cma-surface.txt")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_V782_DMESG = Path("tmp/wifi/v782-bpf-counter-boot-wlan/native/dmesg-delta.txt")
DEFAULT_V783_MANIFEST = Path("tmp/wifi/v783-android-native-pil-gap/manifest.json")

FORBIDDEN_TERMS = (
    " mount ",
    " umount ",
    " echo ",
    " tee ",
    " dd ",
    " mknod ",
    " mkdir ",
    " rm ",
    " rmdir ",
    " chmod ",
    " chown ",
    " cp ",
    " mv ",
    "boot_wlan",
    "qcwlanstate on",
    "/bind",
    "/unbind",
    "driver_override",
    "drivers_probe",
    "insmod",
    "rmmod",
    "modprobe",
    "servicemanager",
    "android.hardware.wifi",
    "wificond",
    "wpa_supplicant",
    "hostapd",
    "svc wifi",
    "cmd wifi",
    " iw ",
    "dhcp",
    " ip route",
    " ip addr",
    " ping ",
)

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
MEMINFO_RE = re.compile(r"^(?P<key>[A-Za-z_()]+):\s+(?P<value>\d+)\s+kB$", re.MULTILINE)
REQUEST_RE = re.compile(r"request size:\s*(?P<size>\d+)")
UNABLE_RE = re.compile(r"unable to allocate memory of size:\s*(?P<size>\d+)")
CMA_FAIL_RE = re.compile(r"cma_alloc: alloc failed, req-size:\s*(?P<pages>\d+)\s+pages,\s+ret:\s*(?P<ret>-?\d+)")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v782-dmesg", type=Path, default=DEFAULT_V782_DMESG)
    parser.add_argument("--v783-manifest", type=Path, default=DEFAULT_V783_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text).replace("\r\n", "\n")


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def load_text(path: Path) -> str:
    resolved = resolve(path)
    if not resolved.exists():
        return ""
    return strip_ansi(resolved.read_text(encoding="utf-8", errors="replace"))


def load_json(path: Path) -> dict[str, Any]:
    resolved = resolve(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def validate_device_command(command: list[str]) -> None:
    joined = " " + " ".join(command).lower() + " "
    for term in FORBIDDEN_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden V784 command term {term!r}: {' '.join(command)}")


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    validate_device_command(command)
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
    item = capture_to_manifest(capture)
    payload = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    payload = strip_ansi(payload)
    item["payload"] = payload
    item["file"] = f"native/{safe_name(name)}.txt"
    store.write_text(item["file"], payload.rstrip() + "\n")
    steps.append(item)
    return item


def shell_command(args: argparse.Namespace, script: str) -> list[str]:
    return ["run", args.busybox, "sh", "-c", script]


def readonly_surface_script(args: argparse.Namespace) -> str:
    bb = args.busybox
    return (
        f"BB={bb}; "
        "printf '== cmdline ==\\n'; $BB cat /proc/cmdline 2>&1; "
        "printf '\\n== meminfo_focus ==\\n'; "
        "$BB grep -E '^(MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree|CmaTotal|CmaFree):' /proc/meminfo 2>&1; "
        "printf '\\n== buddyinfo ==\\n'; $BB cat /proc/buddyinfo 2>&1; "
        "printf '\\n== iomem_focus ==\\n'; "
        "$BB grep -Ei 'cma|reserved|modem|wlan|mhi|smem|System RAM' /proc/iomem 2>&1 | $BB head -n 180; "
        "printf '\\n== memshare_sysfs_tree ==\\n'; "
        "BASE=/sys/devices/platform/soc/soc:qcom,memshare; "
        "if [ -d \"$BASE\" ]; then $BB find \"$BASE\" -maxdepth 3 -print 2>&1 | $BB head -n 180; "
        "else printf 'missing %s\\n' \"$BASE\"; fi; "
        "printf '\\n== memshare_safe_attrs ==\\n'; "
        "for f in \"$BASE\"/uevent \"$BASE\"/modalias \"$BASE\"/power/runtime_status \"$BASE\"/power/control "
        "\"$BASE\"/soc:qcom,memshare:qcom,client_1/uevent "
        "\"$BASE\"/soc:qcom,memshare:qcom,client_2/uevent "
        "\"$BASE\"/soc:qcom,memshare:qcom,client_3/uevent "
        "\"$BASE\"/soc:qcom,memshare:qcom,client_4/uevent "
        "\"$BASE\"/soc:qcom,memshare:qcom,client_4/power/runtime_status "
        "\"$BASE\"/soc:qcom,memshare:qcom,client_4/power/control; do "
        "printf 'FILE %s\\n' \"$f\"; if [ -r \"$f\" ]; then $BB cat \"$f\" 2>&1 | $BB head -c 600; printf '\\n'; else printf 'unreadable\\n'; fi; "
        "done; "
        "printf '\\n== cma_paths ==\\n'; $BB ls -ld /sys/kernel/mm/cma /sys/kernel/debug/cma 2>&1; "
        "printf '\\n== reserved_memory_focus ==\\n'; "
        "$BB find /sys/firmware/devicetree/base/reserved-memory -maxdepth 3 -print 2>&1 "
        "| $BB grep -Ei 'linux,cma|modem_shared|modem_region|pil_wlan|mhi_region|smem|wlan|cma|memshare' "
        "| $BB head -n 180; "
        "printf '\\n== devicetree_memshare_focus ==\\n'; "
        "$BB find /sys/firmware/devicetree/base/soc/qcom,memshare -maxdepth 3 -print 2>&1 | $BB head -n 180; "
        "printf '\\n== dmesg_focus ==\\n'; "
        "$BB dmesg 2>&1 | $BB grep -Ei 'memshare|cma_alloc|service-notifier|servloc|qrtr: Modem QMI Readiness|sysmon-qmi|wlan_pd|icnss_qmi|BDF file|WLAN FW|wlan0|icnss: Modules not initialized|wlan: Loading driver|wlan_hdd_state|subsys-restart|subsys-pil|modem:' | $BB tail -n 240"
    )


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def parse_meminfo(text: str) -> dict[str, int]:
    return {match.group("key"): int(match.group("value")) for match in MEMINFO_RE.finditer(text)}


def parse_v782_failure(text: str) -> dict[str, Any]:
    clean = strip_ansi(text)
    requests = [int(match.group("size")) for match in REQUEST_RE.finditer(clean)]
    unable = [int(match.group("size")) for match in UNABLE_RE.finditer(clean)]
    cma = [
        {"pages": int(match.group("pages")), "ret": int(match.group("ret")), "bytes": int(match.group("pages")) * 4096}
        for match in CMA_FAIL_RE.finditer(clean)
    ]
    focus_lines = [
        line for line in clean.splitlines()
        if re.search(r"memshare|cma_alloc|sysmon-qmi|servloc|service-notifier|qrtr: Modem QMI", line, re.IGNORECASE)
    ]
    return {
        "request_sizes": requests,
        "unable_sizes": unable,
        "cma_failures": cma,
        "max_request_bytes": max(requests) if requests else 0,
        "sum_request_bytes": sum(requests),
        "failure_count": len(unable) + len(cma),
        "focus_tail": focus_lines[-24:],
    }


def analyze_surface(surface: str) -> dict[str, Any]:
    meminfo = parse_meminfo(surface)
    cmdline = surface.split("== meminfo_focus ==", 1)[0]
    cma_free_bytes = meminfo.get("CmaFree", 0) * 1024
    cma_total_bytes = meminfo.get("CmaTotal", 0) * 1024
    return {
        "meminfo": meminfo,
        "cma_total_bytes": cma_total_bytes,
        "cma_free_bytes": cma_free_bytes,
        "cmdline": {
            "firmware_class_path": key_from_cmdline(cmdline, "firmware_class.path"),
            "service_locator_enable": key_from_cmdline(cmdline, "service_locator.enable"),
            "cp_reserved_mem": key_from_cmdline(cmdline, "androidboot.cp_reserved_mem"),
        },
        "memshare_sysfs_present": "/sys/devices/platform/soc/soc:qcom,memshare" in surface and "missing /sys/devices/platform/soc/soc:qcom,memshare" not in surface,
        "client4_present": "qcom,client_4" in surface,
        "client4_size_zero_marker": "client_id 3 / size 0" in surface,
        "client4_no_clients_marker": "no memshare clients registered" in surface,
        "linux_cma_reserved_node": "linux,cma" in surface,
        "modem_shared_mem_region_seen": "modem_shared_mem_region" in surface,
        "pil_wlan_fw_region_seen": "pil_wlan_fw_region" in surface,
        "mhi_region_seen": "mhi_region" in surface,
        "debugfs_cma_absent": "/sys/kernel/debug/cma: No such file or directory" in surface,
        "current_memshare_failure_count": len(UNABLE_RE.findall(surface)) + len(CMA_FAIL_RE.findall(surface)),
        "current_service_notifier_count": len(re.findall(r"service-notifier", surface, re.IGNORECASE)),
    }


def key_from_cmdline(text: str, key: str) -> str:
    match = re.search(rf"(?:^|\s){re.escape(key)}=([^\s]+)", text)
    return match.group(1) if match else ""


def collect_live(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    run_step(args, store, steps, "hide-menu", ["hide"], 10.0)
    run_step(args, store, steps, "version", ["version"], 10.0)
    run_step(args, store, steps, "status", ["status"], 25.0)
    run_step(args, store, steps, "memshare-cma-surface", shell_command(args, readonly_surface_script(args)), 35.0)
    return steps


def build_analysis(args: argparse.Namespace, steps: list[dict[str, Any]]) -> dict[str, Any]:
    surface = step_payload(steps, "memshare-cma-surface")
    version = step_payload(steps, "version")
    v782_text = load_text(args.v782_dmesg)
    v783 = load_json(args.v783_manifest)
    surface_analysis = analyze_surface(surface)
    v782_failure = parse_v782_failure(v782_text)
    cma_free = surface_analysis["cma_free_bytes"]
    return {
        "version_ok": args.expect_version in version,
        "expect_version": args.expect_version,
        "surface": surface_analysis,
        "v782_failure": v782_failure,
        "comparison": {
            "current_cma_free_bytes": cma_free,
            "v782_max_request_bytes": v782_failure["max_request_bytes"],
            "v782_sum_request_bytes": v782_failure["sum_request_bytes"],
            "current_cma_free_ge_max_v782_request": bool(cma_free and cma_free >= v782_failure["max_request_bytes"]),
            "current_cma_free_ge_sum_v782_requests": bool(cma_free and cma_free >= v782_failure["sum_request_bytes"]),
            "v783_decision": v783.get("decision", ""),
            "v783_next_step": v783.get("next_step", ""),
        },
        "device_commands_executed": bool(steps),
        "device_mutating_commands_executed": False,
        "wifi_trigger_executed": False,
        "boot_wlan_executed": False,
        "qcwlanstate_on_executed": False,
        "reboot_executed": False,
        "flash_executed": False,
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(args: argparse.Namespace, command: str, analysis: dict[str, Any], steps: list[dict[str, Any]]) -> list[Check]:
    surface = analysis["surface"]
    failure = analysis["v782_failure"]
    comparison = analysis["comparison"]
    checks: list[Check] = []
    add_check(
        checks,
        "runtime-version",
        "pass" if command == "plan" or analysis["version_ok"] else "blocked",
        "blocker",
        f"expect={args.expect_version} ok={analysis['version_ok']}",
        "restore stock v724 before interpreting native memshare/CMA state",
    )
    add_check(
        checks,
        "read-only-boundary",
        "pass",
        "blocker",
        "no Wi-Fi trigger, reboot, flash, partition write, mount, bind, or route command",
        "keep V784 as a read-only classifier",
    )
    add_check(
        checks,
        "command-success",
        "pass" if command == "plan" or all(step.get("ok") for step in steps) else "blocked",
        "blocker",
        " ".join(f"{step.get('name')}={step.get('ok')}" for step in steps),
        "rerun with a healthy serial bridge before using the analysis",
    )
    add_check(
        checks,
        "memshare-sysfs",
        "pass" if surface["memshare_sysfs_present"] and surface["client4_present"] else "review",
        "warn",
        f"present={surface['memshare_sysfs_present']} client4={surface['client4_present']}",
        "if absent, classify native DT/platform-driver registration before modem triggers",
    )
    add_check(
        checks,
        "reserved-memory",
        "pass" if surface["linux_cma_reserved_node"] and surface["pil_wlan_fw_region_seen"] else "review",
        "warn",
        f"linux_cma={surface['linux_cma_reserved_node']} pil_wlan={surface['pil_wlan_fw_region_seen']} mhi={surface['mhi_region_seen']}",
        "map exact reserved-memory consumers before changing any trigger sequence",
    )
    add_check(
        checks,
        "v782-failure-evidence",
        "pass" if failure["failure_count"] > 0 and failure["max_request_bytes"] > 0 else "blocked",
        "blocker",
        f"failure_count={failure['failure_count']} max_request={failure['max_request_bytes']} sum_request={failure['sum_request_bytes']}",
        "restore V782 dmesg evidence before using V784 as a classifier",
    )
    add_check(
        checks,
        "cma-headroom-at-idle",
        "pass" if comparison["current_cma_free_ge_sum_v782_requests"] else "review",
        "warn",
        (
            f"cma_free={comparison['current_cma_free_bytes']} "
            f"v782_sum={comparison['v782_sum_request_bytes']} "
            f"ge_sum={comparison['current_cma_free_ge_sum_v782_requests']}"
        ),
        "treat V782 failure as timing/client-registration/reserved-pool specific until matched recapture proves otherwise",
    )
    add_check(
        checks,
        "client4-registration-marker",
        "pass" if surface["client4_size_zero_marker"] or surface["client4_no_clients_marker"] else "review",
        "warn",
        f"size_zero={surface['client4_size_zero_marker']} no_clients={surface['client4_no_clients_marker']}",
        "compare Android boot dmesg with explicit memshare filters before any new WLAN trigger",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v784-memshare-cma-surface-plan-ready",
            True,
            "plan-only; live run will remain read-only and avoid Wi-Fi triggers",
            "run V784 read-only native memshare/CMA surface classifier",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v784-memshare-cma-surface-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "restore runtime/evidence prerequisites and rerun V784",
        )
    return (
        "v784-native-memshare-cma-surface-classified",
        True,
        (
            "native exposes memshare sysfs and reserved-memory nodes, V782 failure requests are confirmed, "
            "and idle CMA headroom is not obviously too small; next gap is client-registration/timing or "
            "Android/native memshare behavior, not another blind WLAN trigger"
        ),
        (
            "V785 should recapture Android and native dmesg with explicit memshare/CMA filters and map "
            "client_4/id3 registration before boot_wlan, qcwlanstate, daemon ordering, HAL, scan/connect, or flash"
        ),
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    surface = analysis["surface"]
    failure = analysis["v782_failure"]
    comparison = analysis["comparison"]
    return "\n".join([
        "# V784 Native Memshare/CMA Surface",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutating_commands_executed: `{manifest['device_mutating_commands_executed']}`",
        f"- wifi_trigger_executed: `{manifest['wifi_trigger_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Native Surface",
        "",
        markdown_table(["signal", "value"], [
            ["CmaTotal bytes", surface["cma_total_bytes"]],
            ["CmaFree bytes", surface["cma_free_bytes"]],
            ["MemAvailable kB", surface["meminfo"].get("MemAvailable")],
            ["firmware_class.path", surface["cmdline"].get("firmware_class_path")],
            ["service_locator.enable", surface["cmdline"].get("service_locator_enable")],
            ["androidboot.cp_reserved_mem", surface["cmdline"].get("cp_reserved_mem")],
            ["memshare sysfs present", surface["memshare_sysfs_present"]],
            ["client_4 present", surface["client4_present"]],
            ["client_4 size-zero marker", surface["client4_size_zero_marker"]],
            ["client_4 no-clients marker", surface["client4_no_clients_marker"]],
            ["linux,cma node", surface["linux_cma_reserved_node"]],
            ["pil_wlan_fw_region", surface["pil_wlan_fw_region_seen"]],
            ["mhi_region", surface["mhi_region_seen"]],
            ["debugfs cma absent", surface["debugfs_cma_absent"]],
        ]),
        "",
        "## V782 Failure",
        "",
        markdown_table(["signal", "value"], [
            ["request_sizes", failure["request_sizes"]],
            ["unable_sizes", failure["unable_sizes"]],
            ["cma_failures", failure["cma_failures"]],
            ["max_request_bytes", failure["max_request_bytes"]],
            ["sum_request_bytes", failure["sum_request_bytes"]],
            ["current_cma_free_ge_sum", comparison["current_cma_free_ge_sum_v782_requests"]],
        ]),
        "",
        "## Interpretation",
        "",
        "- V784 did not trigger Wi-Fi or change kernel/runtime state; it only read existing native surfaces.",
        "- Current idle native has non-zero CMA headroom and visible memshare/client_4 platform nodes.",
        "- V782 still has the critical failure evidence: client id 3 requested 96 MiB and 32 MiB near modem sysmon and failed, including `cma_alloc` `-12`.",
        "- Because idle CMA headroom is larger than the V782 request sum, the next hypothesis should be client registration, reserved-pool ownership, or timing under modem/sysmon transition rather than a simple always-too-small CMA pool.",
        "- Android comparison still needs a matching memshare/CMA dmesg filter; previous Android references were filtered for Wi-Fi/QMI and cannot prove memshare absence.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    if args.command == "run":
        steps = collect_live(args, store)
    analysis = build_analysis(args, steps)
    checks = build_checks(args, args.command, analysis, steps)
    decision, ok, reason, next_step = decide(args.command, checks, analysis)
    manifest: dict[str, Any] = {
        "cycle": "v784",
        "generated_at": now_iso(),
        "command": args.command,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "steps": steps,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": analysis["device_commands_executed"],
        "device_mutating_commands_executed": analysis["device_mutating_commands_executed"],
        "wifi_trigger_executed": analysis["wifi_trigger_executed"],
        "boot_wlan_executed": analysis["boot_wlan_executed"],
        "qcwlanstate_on_executed": analysis["qcwlanstate_on_executed"],
        "reboot_executed": analysis["reboot_executed"],
        "flash_executed": analysis["flash_executed"],
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_mutating_commands_executed: {manifest['device_mutating_commands_executed']}")
    print(f"wifi_trigger_executed: {manifest['wifi_trigger_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
