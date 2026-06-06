#!/usr/bin/env python3
"""V1893 host-only classifier for the pm-service msg22 pending-client gate."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1893-pm-msg22-pending-client-gate"
DEFAULT_REPORT_PATH = (
    REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1893_PM_MSG22_PENDING_CLIENT_GATE_2026-06-03.md"
)
DEFAULT_PM_SERVICE = REPO_ROOT / "tmp" / "wifi" / "v1073-host-only" / "vendor-extract" / "files" / "pm-service"
DEFAULT_V1885_MANIFEST = (
    REPO_ROOT / "tmp" / "wifi" / "v1885-internal-pm-qmi-servreg-trigger-source-diff" / "manifest.json"
)
DEFAULT_V1891_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1891-android-capture-parser-handoff" / "manifest.json"
DEFAULT_V1892_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1892-pm-ack-open-trigger-boundary" / "manifest.json"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def run_text(command: list[str]) -> str:
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0:
        return proc.stdout
    return proc.stdout


def disassemble(binary: Path, start: str, stop: str) -> str:
    objdump = shutil.which("aarch64-linux-gnu-objdump")
    if not objdump:
        return ""
    return run_text([objdump, "-d", f"--start-address={start}", f"--stop-address={stop}", str(binary)])


def strings_text(binary: Path) -> str:
    strings = shutil.which("strings")
    if not strings:
        return ""
    return run_text([strings, "-tx", str(binary)])


def native_summary(v1885: dict[str, Any], v1892: dict[str, Any]) -> dict[str, Any]:
    native = v1885.get("native_post_open") or {}
    boundary = v1892.get("native_post_open") or {}
    checks = v1892.get("checks") or {}
    return {
        "v1885_label": v1885.get("label", ""),
        "v1885_pass": boolish(v1885.get("pass")),
        "v1892_label": v1892.get("label", ""),
        "v1892_pass": boolish(v1892.get("pass")),
        "modem_open_present": boolish(checks.get("modem_open_present")),
        "modem_open_not_trigger": boolish(checks.get("modem_open_not_trigger")),
        "open_context_path": native.get("open_context_path") or boundary.get("open_context_path", ""),
        "open_context_fd": native.get("open_context_fd") or boundary.get("open_context_fd", ""),
        "pm_client_register_rc": str(native.get("pm_client_register_rc") or boundary.get("pm_client_register_rc", "")),
        "pm_client_connect_rc": str(native.get("pm_client_connect_rc") or boundary.get("pm_client_connect_rc", "")),
        "post_ack_open_call_hits": intish(native.get("post_ack_open_call_hits") or boundary.get("post_ack_open_call_hits")),
        "post_ack_open_ret_hits": intish(native.get("post_ack_open_ret_hits")),
        "post_ack_msg22_ind_hits": intish(native.get("post_ack_qmi_restart_ind_hits") or boundary.get("post_ack_msg22_ind_hits")),
        "requested_wlanmdsp": str(native.get("requested_wlanmdsp") or boundary.get("requested_wlanmdsp", "")),
        "wlfw_service69_seen": str(native.get("wlfw_service69_seen") or boundary.get("wlfw_service69_seen", "")),
        "wlan0_present": str(native.get("wlan0_present") or boundary.get("wlan0_present", "")),
        "early_servnotif_state": native.get("early_servnotif_state") or boundary.get("early_servnotif_state", ""),
        "late_servnotif_state": native.get("late_servnotif_state") or boundary.get("late_servnotif_state", ""),
    }


def handoff_summary(v1891: dict[str, Any]) -> dict[str, Any]:
    checks = v1891.get("checks") or {}
    return {
        "label": v1891.get("label", ""),
        "pass": boolish(v1891.get("pass")),
        "required_parser_inputs_declared": boolish(checks.get("required_parser_inputs_declared")),
        "forbidden_command_surface_absent": boolish(checks.get("forbidden_command_surface_absent")),
        "future_commands": v1891.get("future_commands") or [],
    }


def source_checks(post_ack: str, msg22_handler: str, pending_helper: str, strings: str) -> dict[str, Any]:
    return {
        "post_ack_loads_pending_qmi_client": "ldr\tx8, [x20, #200]" in post_ack
        or "ldr\tx8, [x20,#200]" in post_ack,
        "post_ack_skips_msg22_when_pending_client_null": "cbz\tx8, 8a74" in post_ack,
        "post_ack_sends_msg22_indication": (
            "mov\tw1, #0x22" in post_ack and "qmi_csi_send_ind@plt" in post_ack
        ),
        "post_ack_msg22_uses_pending_client": (
            "ldr\tx21, [x20, #200]" in post_ack
            and "mov\tx0, x21" in post_ack
            and "qmi_csi_send_ind@plt" in post_ack
        ),
        "post_ack_failed_restart_ind_log_string": "failed to send a restart indication to QMI client" in strings,
        "msg22_handler_request_string": "QMI service peripheral restart request from %s" in strings,
        "msg22_handler_calls_pending_helper": "bl\t956c" in msg22_handler,
        "msg22_handler_error_response_path": (
            "mov\tw8, #0x2e" in msg22_handler and "qmi_csi_send_resp@plt" in msg22_handler
        ),
        "pending_helper_stores_qmi_client": "str\tx20, [x19, #200]" in pending_helper,
        "pending_helper_rejects_existing_pending_client": "ldr\tx8, [x19, #200]" in pending_helper
        and "cbz\tx8" in pending_helper,
        "pending_helper_invokes_state_transition": "bl\t92dc" in pending_helper,
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    v1885 = read_json(args.v1885_manifest)
    v1891 = read_json(args.v1891_manifest)
    v1892 = read_json(args.v1892_manifest)
    post_ack = disassemble(args.pm_service, "0x8950", "0x8d30")
    msg22_handler = disassemble(args.pm_service, "0x716c", "0x72e0")
    pending_helper = disassemble(args.pm_service, "0x956c", "0x95f4")
    strings = strings_text(args.pm_service)
    source = source_checks(post_ack, msg22_handler, pending_helper, strings)
    native = native_summary(v1885, v1892)
    handoff = handoff_summary(v1891)
    checks = {
        "pm_service_binary_present": args.pm_service.exists(),
        "source_pending_client_gate": (
            source["post_ack_loads_pending_qmi_client"]
            and source["post_ack_skips_msg22_when_pending_client_null"]
            and source["post_ack_sends_msg22_indication"]
            and source["post_ack_msg22_uses_pending_client"]
            and source["pending_helper_stores_qmi_client"]
            and source["pending_helper_invokes_state_transition"]
        ),
        "source_msg22_request_handler": (
            source["msg22_handler_request_string"]
            and source["msg22_handler_calls_pending_helper"]
            and source["msg22_handler_error_response_path"]
        ),
        "native_open_without_pending_msg22": (
            native["v1885_pass"]
            and native["v1892_pass"]
            and native["modem_open_present"]
            and native["modem_open_not_trigger"]
            and native["open_context_path"] == "/dev/subsys_modem"
            and native["pm_client_register_rc"] == "0"
            and native["pm_client_connect_rc"] == "0"
            and native["post_ack_open_call_hits"] > 0
            and native["post_ack_msg22_ind_hits"] == 0
            and native["requested_wlanmdsp"] == "0"
            and native["wlfw_service69_seen"] == "0"
            and native["wlan0_present"] == "0"
            and native["early_servnotif_state"] == "uninit"
            and native["late_servnotif_state"] == "uninit"
        ),
        "android_capture_handoff_ready": (
            handoff["pass"]
            and handoff["label"] == "android-capture-parser-handoff-ready"
            and handoff["required_parser_inputs_declared"]
            and handoff["forbidden_command_surface_absent"]
        ),
    }
    if all(checks.values()):
        decision = "v1893-pm-msg22-pending-client-gate-source-pass"
        label = "pm-msg22-pending-client-gate"
        reason = (
            "pm-service source shows post-ack msg22 indication is gated by a pending QMI client slot; "
            "native reaches PM ack/open but the pending-client msg22 edge never fires, so the next proof must "
            "come from a normal Android PM msg22/servreg/SSCTL capture"
        )
        passed = True
    else:
        decision = "v1893-pm-msg22-pending-client-gate-incomplete"
        label = "pm-msg22-pending-client-gate-incomplete"
        reason = "source disassembly or prior native/Android handoff prerequisites are incomplete"
        passed = False
    return {
        "cycle": "V1893",
        "decision": decision,
        "pass": passed,
        "label": label,
        "reason": reason,
        "out_dir": rel(args.out_dir),
        "report": rel(args.report),
        "inputs": {
            "pm_service": rel(args.pm_service),
            "v1885_manifest": rel(args.v1885_manifest),
            "v1891_manifest": rel(args.v1891_manifest),
            "v1892_manifest": rel(args.v1892_manifest),
        },
        "checks": checks,
        "source": source,
        "native_post_open": native,
        "handoff": handoff,
        "artifacts": {
            "post_ack_disasm": "host/pm-service-post-ack-0x8950-0x8d30.S",
            "msg22_handler_disasm": "host/pm-service-msg22-handler-0x716c-0x72e0.S",
            "pending_helper_disasm": "host/pm-service-pending-client-helper-0x956c-0x95f4.S",
            "strings": "host/pm-service-strings-0x3d00-0x4d00.txt",
        },
        "raw_artifacts": {
            "post_ack": post_ack,
            "msg22_handler": msg22_handler,
            "pending_helper": pending_helper,
            "strings": "\n".join(
                line
                for line in strings.splitlines()
                if line.strip() and "3d00" <= line.split(maxsplit=1)[0] <= "4d00"
            )
            + "\n",
        },
        "safety": {
            "host_only": True,
            "device_contact": False,
            "flash": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credential_use": False,
            "dhcp_routes": False,
            "external_ping": False,
            "pmic_gpio_gdsc_write": False,
            "forced_rc1_case": False,
            "subsys_esoc0_open": False,
            "esoc_notify_boot_done": False,
            "pci_rescan": False,
            "platform_bind_unbind": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    source = result["source"]
    native = result["native_post_open"]
    safety = result["safety"]
    future_commands = result["handoff"]["future_commands"]
    capture_command = future_commands[0] if len(future_commands) > 0 else ""
    parser_command = future_commands[1] if len(future_commands) > 1 else ""
    return "\n".join(
        [
            "# Native Init V1893 PM Msg22 Pending Client Gate",
            "",
            "## Summary",
            "",
            "- Cycle: `V1893`",
            "- Type: host-only pm-service source classifier for msg22 pending-client gate",
            f"- Decision: `{result['decision']}`",
            f"- Label: `{result['label']}`",
            f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
            f"- Reason: {result['reason']}",
            f"- Evidence: `{result['out_dir']}`",
            "",
            "## Source Gate",
            "",
            f"- post-ack pending-client load/null-skip: `{source['post_ack_loads_pending_qmi_client']}` / `{source['post_ack_skips_msg22_when_pending_client_null']}`",
            f"- post-ack msg22 indication/uses-pending-client: `{source['post_ack_sends_msg22_indication']}` / `{source['post_ack_msg22_uses_pending_client']}`",
            f"- msg22 request handler string/helper/error-response: `{source['msg22_handler_request_string']}` / `{source['msg22_handler_calls_pending_helper']}` / `{source['msg22_handler_error_response_path']}`",
            f"- pending helper stores/rejects-existing/transitions: `{source['pending_helper_stores_qmi_client']}` / `{source['pending_helper_rejects_existing_pending_client']}` / `{source['pending_helper_invokes_state_transition']}`",
            f"- restart-indication log strings: `{source['post_ack_failed_restart_ind_log_string']}`",
            "",
            "## Native Boundary",
            "",
            f"- PM register/connect/open: `{native['pm_client_register_rc']}` / `{native['pm_client_connect_rc']}` / `{native['open_context_path']}` fd `{native['open_context_fd']}`",
            f"- post-ack open/msg22 hits: `{native['post_ack_open_call_hits']}` / `{native['post_ack_msg22_ind_hits']}`",
            f"- native wlanmdsp/WLFW69/wlan0: `{native['requested_wlanmdsp']}` / `{native['wlfw_service69_seen']}` / `{native['wlan0_present']}`",
            f"- native service-notifier state: `{native['early_servnotif_state']}` -> `{native['late_servnotif_state']}`",
            "",
            "## Classifier Checks",
            "",
            f"- pm-service binary present: `{checks['pm_service_binary_present']}`",
            f"- source pending-client gate: `{checks['source_pending_client_gate']}`",
            f"- source msg22 request handler: `{checks['source_msg22_request_handler']}`",
            f"- native open without pending msg22: `{checks['native_open_without_pending_msg22']}`",
            f"- Android capture handoff ready: `{checks['android_capture_handoff_ready']}`",
            "",
            "## Selected Diff",
            "",
            f"- Label: `{result['label']}`.",
            "- `/dev/subsys_modem` open is below the PM ack path but above the missing guest-PD load; it does not populate the pm-service pending QMI client slot by itself.",
            "- The source candidate is now narrower: prove whether normal Android creates the msg22 pending-client edge before `wlanmdsp.mbn`, or whether a different servreg/SSCTL request causes the modem-side WLAN-PD load.",
            "- Native still lacks the post-ack msg22 indication, WLFW service 69, `wlanmdsp.mbn`, and `wlan0`.",
            "",
            "## Handoff Commands",
            "",
            f"- Capture command: `{capture_command}`",
            f"- Parser command: `{parser_command}`",
            "",
            "## Safety Scope",
            "",
            f"- host-only/device-contact: `{safety['host_only']}` / `{safety['device_contact']}`",
            f"- Wi-Fi HAL/scan-connect/credential/DHCP/routes/ping: `{safety['wifi_hal']}` / `{safety['scan_connect']}` / `{safety['credential_use']}` / `{safety['dhcp_routes']}` / `{safety['external_ping']}`",
            f"- PMIC-GPIO-GDSC/forced-RC1/subsys-esoc0/eSoC notify/PCI rescan/platform bind: `{safety['pmic_gpio_gdsc_write']}` / `{safety['forced_rc1_case']}` / `{safety['subsys_esoc0_open']}` / `{safety['esoc_notify_boot_done']}` / `{safety['pci_rescan']}` / `{safety['platform_bind_unbind']}`",
            "",
            "## Next",
            "",
            "- Run the normal Android capture only when ADB/root is available; reject degraded 257s captures or any pre-wlan0 PCIe/MHI path.",
            "- Diff for pm-service msg22 pending-client creation, servreg state-up, SSCTL, and first `wlanmdsp.mbn` request.",
            "- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0` are both present.",
        ]
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--pm-service", type=Path, default=DEFAULT_PM_SERVICE)
    parser.add_argument("--v1885-manifest", type=Path, default=DEFAULT_V1885_MANIFEST)
    parser.add_argument("--v1891-manifest", type=Path, default=DEFAULT_V1891_MANIFEST)
    parser.add_argument("--v1892-manifest", type=Path, default=DEFAULT_V1892_MANIFEST)
    args = parser.parse_args()

    result = analyze(args)
    store = EvidenceStore(args.out_dir)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    raw = result.pop("raw_artifacts")
    store.write_text(result["artifacts"]["post_ack_disasm"], raw["post_ack"])
    store.write_text(result["artifacts"]["msg22_handler_disasm"], raw["msg22_handler"])
    store.write_text(result["artifacts"]["pending_helper_disasm"], raw["pending_helper"])
    store.write_text(result["artifacts"]["strings"], raw["strings"])
    store.write_text("host/source-checks.json", json.dumps(result["source"], indent=2, sort_keys=True) + "\n")
    store.write_text("host/native-post-open.json", json.dumps(result["native_post_open"], indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "manifest.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_private_text(args.out_dir / "summary.md", render_report(result))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    write_private_text(args.report, render_report(result))
    print(json.dumps({key: result[key] for key in ("decision", "pass", "label", "out_dir", "report")}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
