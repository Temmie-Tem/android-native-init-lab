#!/usr/bin/env python3
"""V465 IWifi.start contract mapper.

This host-side gate fixes the native-init control contract before any
credential, scan, connect, DHCP, route, or external packet step is allowed.
It performs only host inspection plus read-only native captures.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore
from wifi_service_manager_start_only_approval_packet import DEFAULT_EXPECT_VERSION


DEFAULT_OUT_DIR = Path("tmp/wifi/v465-iwifi-start-contract")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "96179d75ee81586cf8f46edb7354eeb8c57569e56a047a2c55e678c794a514e9"
DEFAULT_V464_GLOB = "tmp/wifi/v464-native-wlan-surface-live*/manifest.json"
TOYBOX = "/cache/bin/toybox"

IHW_SERVICE_MANAGER_DESCRIPTOR = "android.hidl.manager@1.0::IServiceManager"
IHW_SERVICE_MANAGER_INSTANCE = "manager"
IHW_SERVICE_MANAGER_GET_CODE = 1
IWIFI_DESCRIPTOR = "android.hardware.wifi@1.0::IWifi"
IWIFI_INSTANCE = "default"
IWIFI_START_CODE = 3
IWIFI_START_EXPECTS_ARGS = 0


@dataclass
class Step:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


READ_ONLY_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("selftest", ["selftest"], 10.0),
    ("stat-helper", ["stat", DEFAULT_HELPER], 10.0),
    ("sha-helper", ["run", TOYBOX, "sha256sum", DEFAULT_HELPER], 10.0),
    ("helper-usage", ["run", DEFAULT_HELPER], 10.0),
    ("stat-hwservicemanager", ["stat", "/mnt/system/system/bin/hwservicemanager"], 10.0),
    ("stat-lshal", ["stat", "/mnt/system/system/bin/lshal"], 10.0),
    ("stat-service", ["stat", "/mnt/system/system/bin/service"], 10.0),
    ("stat-cmd", ["stat", "/mnt/system/system/bin/cmd"], 10.0),
    ("stat-app-process64", ["stat", "/mnt/system/system/bin/app_process64"], 10.0),
    ("stat-framework-wifi", ["stat", "/mnt/system/system/apex/com.android.wifi/javalib/framework-wifi.jar"], 10.0),
    ("stat-service-wifi", ["stat", "/mnt/system/system/apex/com.android.wifi/javalib/service-wifi.jar"], 10.0),
    ("stat-wifi-hidl-1-0", ["stat", "/mnt/system/system/system_ext/apex/com.android.vndk.v30/lib64/android.hardware.wifi@1.0.so"], 10.0),
    ("stat-vendor-wifi-hal", ["stat", "/mnt/system/vendor/bin/hw/vendor.samsung.hardware.wifi@2.0-service"], 10.0),
    ("stat-aosp-wifi-hal", ["stat", "/mnt/system/vendor/bin/hw/android.hardware.wifi@1.0-service"], 10.0),
    ("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
    ("sys-class-ieee80211", ["run", TOYBOX, "ls", "/sys/class/ieee80211"], 10.0),
    ("proc-net-wireless", ["run", TOYBOX, "cat", "/proc/net/wireless"], 10.0),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--v464-manifest", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._+-" else "-" for ch in value).strip("-") or "capture"


def command_with_overrides(args: argparse.Namespace, command: list[str]) -> list[str]:
    return [
        args.helper if item == DEFAULT_HELPER else item
        for item in command
    ]


def capture_command(args: argparse.Namespace, store: EvidenceStore, name: str, command: list[str], timeout: float) -> Step:
    real_command = command_with_overrides(args, command)
    record = run_capture(args, name, real_command, timeout=timeout)
    text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text)
    return Step(name, record.command, record.ok, record.rc, record.status, record.duration_sec, rel, record.error)


def run_preflight(args: argparse.Namespace, store: EvidenceStore) -> list[Step]:
    store.mkdir("native")
    return [capture_command(args, store, name, command, timeout) for name, command, timeout in READ_ONLY_COMMANDS]


def step_text(store: EvidenceStore, steps: list[Step], name: str) -> str:
    for step in steps:
        if step.name == name:
            path = store.path(step.file)
            return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return ""


def step_ok(steps: list[Step], name: str) -> bool:
    return any(step.name == name and step.ok for step in steps)


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def latest_manifest(pattern: str) -> dict[str, Any]:
    manifests = sorted(repo_path(".").glob(pattern), key=lambda path: path.stat().st_mtime if path.exists() else 0)
    if not manifests:
        return {"present": False, "path": "", "decision": "missing", "pass": False}
    path = manifests[-1]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - evidence parser preserves failure detail
        return {"present": True, "path": str(path), "decision": "invalid", "pass": False, "error": str(exc)}
    payload["present"] = True
    payload["path"] = str(path)
    return payload


def load_v464(args: argparse.Namespace) -> dict[str, Any]:
    if args.v464_manifest:
        path = repo_path(args.v464_manifest)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            return {"present": path.exists(), "path": str(path), "decision": "invalid", "pass": False, "error": str(exc)}
        payload["present"] = True
        payload["path"] = str(path)
        return payload
    return latest_manifest(DEFAULT_V464_GLOB)


def build_contract(args: argparse.Namespace) -> dict[str, Any]:
    del args
    return {
        "service_manager": {
            "descriptor": IHW_SERVICE_MANAGER_DESCRIPTOR,
            "instance": IHW_SERVICE_MANAGER_INSTANCE,
            "lookup_transaction": {
                "method": "get(string fqName, string name)",
                "code": IHW_SERVICE_MANAGER_GET_CODE,
                "request_args": [
                    IWIFI_DESCRIPTOR,
                    IWIFI_INSTANCE,
                ],
                "expected_reply": "nullable strong hwbinder handle for android.hardware.wifi@1.0::IWifi/default",
            },
        },
        "iwifi_start": {
            "descriptor": IWIFI_DESCRIPTOR,
            "instance": IWIFI_INSTANCE,
            "transaction": {
                "method": "start() generates (WifiStatus status)",
                "code": IWIFI_START_CODE,
                "request_args": IWIFI_START_EXPECTS_ARGS,
                "expected_reply": "HIDL transport status then android.hardware.wifi@1.0::WifiStatus",
            },
        },
        "call_order": [
            "start V464 private runtime: servicemanager, hwservicemanager, vendor Wi-Fi HAL, cnss-daemon",
            "open private /dev/hwbinder from the helper namespace",
            "call IServiceManager.get(android.hardware.wifi@1.0::IWifi, default)",
            "call IWifi.start() exactly once if and only if a non-null service handle is returned",
            "snapshot wlan/wiphy/rfkill surfaces before, after call, and after cleanup",
        ],
        "blocked_actions": [
            "SSID/password read",
            "scan/connect/link-up",
            "DHCP/DNS/route/external ping",
            "rfkill/sysfs write",
            "module load/unload or driver bind/unbind",
            "persistent Android partition write or boot autostart",
        ],
    }


def host_contract_inputs() -> dict[str, Any]:
    return {
        "hidl_gen": shutil.which("hidl-gen"),
        "aarch64_gcc": shutil.which("aarch64-linux-gnu-gcc"),
        "aarch64_readelf": shutil.which("aarch64-linux-gnu-readelf"),
        "existing_generated_iwifi_headers": [
            str(path.relative_to(repo_path(".")))
            for path in repo_path(".").glob("**/IWifi.h")
            if ".git" not in path.parts and "__pycache__" not in path.parts
        ][:20],
    }


def build_strategy(args: argparse.Namespace, store: EvidenceStore, steps: list[Step]) -> dict[str, Any]:
    host_inputs = host_contract_inputs()
    helper_usage = step_text(store, steps, "helper-usage")
    return {
        "generated_hidl_client": {
            "usable_now": bool(host_inputs["hidl_gen"] and host_inputs["existing_generated_iwifi_headers"]),
            "reason": "requires hidl-gen and generated IWifi C++ headers/libraries in the repo or an Android-target build tree",
            "hidl_gen": host_inputs["hidl_gen"],
            "existing_generated_iwifi_headers": host_inputs["existing_generated_iwifi_headers"],
        },
        "existing_android_tool": {
            "usable_now": False,
            "reason": "lshal can enumerate/wait/status HIDL services but is not an IWifi.start invoker; cmd/svc require Android framework services and are not native-init HAL-only control",
            "lshal_present": step_ok(steps, "stat-lshal"),
            "cmd_present": step_ok(steps, "stat-cmd"),
            "service_present": step_ok(steps, "stat-service"),
            "app_process64_present": step_ok(steps, "stat-app-process64"),
        },
        "raw_hwbinder_client": {
            "usable_now": False,
            "reason": "helper v31 has V464 runtime/surface snapshots but does not yet implement the raw hwbinder IServiceManager.get + IWifi.start primitive",
            "next_helper_label": "v32",
            "remote_helper_has_v31_surface_mode": "a90_android_execns_probe v31" in helper_usage and "wifi-surface-composite-start-only" in helper_usage,
            "planned_mode": "wifi-iwifi-start-surface",
            "planned_allow_flag": "--allow-iwifi-start-only",
        },
        "selected_next_strategy": "raw-hwbinder-client",
        "selected_next_reason": "it is the only strategy that can stay inside native init and call exactly IWifi.start without framework scan/connect paths",
        "host_inputs": host_inputs,
        "helper": args.helper,
    }


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "contract": build_contract(args),
        "guardrails": {
            "device_commands_in_plan": False,
            "preflight_read_only": True,
            "live_start_in_this_script": False,
            "credentials_allowed": False,
            "packets_allowed": False,
        },
        "next_artifact": {
            "helper": "a90_android_execns_probe v32",
            "mode": "wifi-iwifi-start-surface",
            "runner": "native_iwifi_start_surface_v466.py",
        },
    }


def build_checks(args: argparse.Namespace, store: EvidenceStore, steps: list[Step], v464: dict[str, Any],
                 strategy: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight to confirm current native inputs")
        return checks

    version = step_text(store, steps, "version")
    status = step_text(store, steps, "status")
    selftest = step_text(store, steps, "selftest")
    helper_sha = step_text(store, steps, "sha-helper")
    helper_usage = step_text(store, steps, "helper-usage")
    netdev = step_text(store, steps, "proc-net-dev")
    wifi_links = [line.strip() for line in netdev.splitlines() if "wlan" in line.lower() or "p2p" in line.lower()]

    add_check(checks, "native-version", "pass" if args.expect_version in version else "warn", "warning", f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:2], "refresh baseline if native version intentionally changed")
    add_check(checks, "native-clean", "pass" if step_ok(steps, "status") and step_ok(steps, "selftest") and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker", "status/selftest rc=0 fail=0 expected", [], "fix native health before Wi-Fi control work")
    add_check(checks, "helper-v31-context", "pass" if args.helper_sha256 in helper_sha and "a90_android_execns_probe v31" in helper_usage else "blocked", "blocker", "remote helper v31 context should be deployed before deriving v32", [line for line in helper_sha.splitlines() if args.helper in line][:2], "deploy latest helper context before extending it")
    add_check(checks, "v464-surface-input", "pass" if v464.get("decision") == "v464-native-wlan-surface-not-observed" and v464.get("pass") else "warn", "warning", f"decision={v464.get('decision')} pass={v464.get('pass')}", [str(v464.get("path", ""))], "refresh V464 if missing or stale")
    add_check(checks, "wifi-surface-still-absent", "pass" if not wifi_links else "blocked", "blocker", f"wifi_link_count={len(wifi_links)}", wifi_links[:8], "do not run start-gate while an unmanaged Wi-Fi link already exists")
    add_check(checks, "iwifi-contract-explicit", "pass", "info", f"{IWIFI_DESCRIPTOR}/{IWIFI_INSTANCE} start_code={IWIFI_START_CODE}", [], "keep code/descriptor pinned in v32 implementation")
    add_check(checks, "generated-client-strategy", "available" if strategy["generated_hidl_client"]["usable_now"] else "not-available", "info", strategy["generated_hidl_client"]["reason"], strategy["generated_hidl_client"]["existing_generated_iwifi_headers"], "use only if an Android-target HIDL client build tree is added")
    add_check(checks, "android-tool-strategy", "not-usable", "info", strategy["existing_android_tool"]["reason"], [], "do not substitute lshal/cmd/svc for IWifi.start")
    add_check(checks, "raw-hwbinder-strategy", "next", "next", strategy["raw_hwbinder_client"]["reason"], [], "implement helper v32 raw hwbinder primitive")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(args: argparse.Namespace, checks: list[Check], strategy: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return "v465-iwifi-start-contract-plan-ready", True, "plan-only; no device command executed", "run V465 preflight"
    blocked = blockers(checks)
    if blocked:
        return "v465-iwifi-start-contract-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before helper v32 design"
    if strategy["generated_hidl_client"]["usable_now"]:
        return "v465-iwifi-start-contract-generated-client-available", True, "generated HIDL client path is available", "build generated-client runner before live start gate"
    return "v465-iwifi-start-contract-ready-raw-hwbinder-next", True, "IWifi.start contract is explicit; next implementation is helper v32 raw hwbinder client", "implement v32 wifi-iwifi-start-surface and V466 runner"


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v464 = load_v464(args)
    steps: list[Step] = []
    if args.command != "plan":
        steps = run_preflight(args, store)
    strategy = build_strategy(args, store, steps)
    checks = build_checks(args, store, steps, v464, strategy)
    decision, pass_ok, reason, next_step = decide(args, checks, strategy)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v464": {"path": v464.get("path"), "decision": v464.get("decision"), "pass": v464.get("pass")},
        "plan": build_plan(args),
        "strategy": strategy,
        "steps": [asdict(step) for step in steps],
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": args.command != "plan",
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "iwifi_start_executed": False,
        "wifi_bringup_executed": False,
        "credentials_read": False,
        "external_packets_sent": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], "<br>".join(c["evidence"]), c["next_step"]] for c in manifest["checks"]]
    step_rows = [[s["name"], "PASS" if s["ok"] else "FAIL", s["rc"], s["status"], s["file"]] for s in manifest["steps"]]
    contract = manifest["plan"]["contract"]
    return "\n".join([
        "# V465 IWifi.start Contract Mapper",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- iwifi_start_executed: `{manifest['iwifi_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Contract",
        "",
        f"- service_manager_descriptor: `{contract['service_manager']['descriptor']}`",
        f"- service_manager_get_code: `{contract['service_manager']['lookup_transaction']['code']}`",
        f"- iwifi_descriptor: `{contract['iwifi_start']['descriptor']}`",
        f"- iwifi_start_code: `{contract['iwifi_start']['transaction']['code']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence", "next"], check_rows),
        "",
        "## Native Steps",
        "",
        markdown_table(["step", "ok", "rc", "status", "file"], step_rows) if step_rows else "- none",
        "",
    ]) + "\n"


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"iwifi_start_executed: {manifest['iwifi_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
