#!/usr/bin/env python3
"""V1994 passive pd-mapper/tftp producer-child handoff."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import native_wifi_rfs_bridge_wlanmdsp_handoff_v1992 as prev1992


CYCLE = "V1994"
OUT_DIR = prev1992.prev.repo_path("tmp/wifi/v1994-producer-child-passive-handoff")
HANDOFF_DIR = OUT_DIR / "v1993-handoff"
HANDOFF_REPORT = OUT_DIR / "v1993-handoff-report.md"
REPORT_PATH = prev1992.prev.repo_path(
    "docs/reports/NATIVE_INIT_V1994_PRODUCER_CHILD_PASSIVE_HANDOFF_2026-06-04.md"
)
V1993_OUT = prev1992.prev.repo_path("tmp/wifi/v1993-producer-child-passive-test-boot")
V1993_INIT = V1993_OUT / "init_v1993_producer_child_passive"
V1993_BOOT = V1993_OUT / "boot_linux_v1993_producer_child_passive.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1993/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.179 (v1993-producer-child-passive)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1993.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1993.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1993-helper.result"

ORIGINAL_PATCH_PREV_MODULE = prev1992.patch_prev_module
ORIGINAL_CLASSIFY = prev1992.classify
ORIGINAL_RENDER_REPORT = prev1992.render_report
ORIGINAL_COLLECT_DETAILS = prev1992.prev.collect_details


def rel(path: Path) -> str:
    return prev1992.prev.rel(path)


def read_helper_text() -> str:
    parts: list[str] = []
    for path in (
        HANDOFF_DIR / "test-v1393-helper-result.stdout.txt",
        HANDOFF_DIR / "test-v1393-helper-result.stderr.txt",
        HANDOFF_DIR / "test-v1393-log.stdout.txt",
        HANDOFF_DIR / "test-v1393-summary.stdout.txt",
    ):
        if path.exists():
            parts.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(parts)


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line or line.startswith("A90_EXECNS_PATH_"):
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            fields[key] = value.strip()
    return fields


def syscall_blocks(text: str, label: str, limit: int = 10) -> list[str]:
    escaped = re.escape(label)
    pattern = re.compile(
        rf"A90_EXECNS_PATH_({escaped}(?:_stall_task_[0-9]+)?_syscall)_BEGIN[^\n]*\n"
        rf"(.*?)\nA90_EXECNS_PATH_\1_END",
        re.S,
    )
    blocks: list[str] = []
    for match in pattern.finditer(text):
        body = " ".join(line.strip() for line in match.group(2).splitlines() if line.strip())
        if body:
            blocks.append(body[:240])
        if len(blocks) >= limit:
            break
    return blocks


def collect_producer_child_snapshot() -> dict[str, Any]:
    text = read_helper_text()
    fields = parse_fields(text)
    phases = ("after_holder_start", "after_post_listener_window")
    children = ("pd_mapper", "tftp_server")
    result: dict[str, Any] = {
        "text_present": bool(text),
        "phases": {},
        "raw_marker_count": text.count("wlan_pd_producer_child_snapshot."),
        "passive_contract": {
            "no_qmi_send": True,
            "no_qrtr_readback": True,
            "no_ptrace": True,
        },
    }
    for phase in phases:
        phase_info: dict[str, Any] = {
            "target_count": int(prev1992.prev.intish(fields.get(f"wlan_pd_producer_child_snapshot.{phase}.target_count"))),
            "alive_count": int(prev1992.prev.intish(fields.get(f"wlan_pd_producer_child_snapshot.{phase}.alive_count"))),
            "snapshot_count": int(prev1992.prev.intish(fields.get(f"wlan_pd_producer_child_snapshot.{phase}.snapshot_count"))),
            "children": {},
        }
        for child in children:
            label = f"wlan_pd_producer_{phase}_{child}"
            child_info = {
                "pid": fields.get(f"wlan_pd_producer_child_snapshot.{phase}.{child}.pid", ""),
                "alive": int(prev1992.prev.intish(fields.get(f"wlan_pd_producer_child_snapshot.{phase}.{child}.alive"))),
                "state": fields.get(f"wlan_pd_producer_child_snapshot.{phase}.{child}.state", ""),
                "fd_socket_count": int(prev1992.prev.intish(fields.get(f"capture.{label}.fd_links.socket_count"))),
                "fd_count": int(prev1992.prev.intish(fields.get(f"capture.{label}.fd_links.count"))),
                "stall_snapshot": int(prev1992.prev.intish(fields.get(f"capture.{label}.stall_snapshot.task_captured"))),
                "syscall_captured": int(prev1992.prev.intish(fields.get(f"capture.{label}.stall_snapshot.syscall_captured"))),
                "task_count": int(prev1992.prev.intish(fields.get(f"capture.{label}.stall_tasks.count"))),
                "syscall_blocks": syscall_blocks(text, label, limit=6),
            }
            phase_info["children"][child] = child_info
        result["phases"][phase] = phase_info
    result["ok"] = all(
        (result["phases"][phase]["target_count"] >= 2 and result["phases"][phase]["snapshot_count"] >= 2)
        for phase in phases
    )
    result["both_alive_after_holder"] = (
        result["phases"]["after_holder_start"]["children"]["pd_mapper"]["alive"] > 0
        and result["phases"]["after_holder_start"]["children"]["tftp_server"]["alive"] > 0
    )
    result["both_alive_after_window"] = (
        result["phases"]["after_post_listener_window"]["children"]["pd_mapper"]["alive"] > 0
        and result["phases"]["after_post_listener_window"]["children"]["tftp_server"]["alive"] > 0
    )
    return result


def collect_helper_completion(handoff: dict[str, Any]) -> dict[str, Any]:
    text = read_helper_text()
    fields = parse_fields(text)
    rollback = handoff.get("post_rollback_verification") if isinstance(handoff.get("post_rollback_verification"), dict) else {}
    result = {
        "text_present": bool(text),
        "result_file_version": fields.get("result_file_version", ""),
        "version_ok": fields.get("result_file_version") == "a90_android_execns_probe v366",
        "probe_run_rc": fields.get("probe_run_rc", ""),
        "probe_run_rc_ok": int(prev1992.prev.intish(fields.get("probe_run_rc"))) == 0,
        "child_exit_code": fields.get("child_exit_code", ""),
        "child_exit_code_ok": int(prev1992.prev.intish(fields.get("child_exit_code"))) == 0,
        "child_signal": fields.get("child_signal", ""),
        "child_signal_ok": int(prev1992.prev.intish(fields.get("child_signal"))) == 0,
        "timed_out": int(prev1992.prev.intish(fields.get("timed_out"))),
        "test_flash_ok": bool(handoff.get("test_flash_ok")),
        "rollback_version_ok": bool(rollback.get("version_ok")),
        "rollback_selftest_fail_zero": bool(rollback.get("selftest_fail_zero")),
    }
    result["ok"] = (
        result["text_present"]
        and result["version_ok"]
        and result["probe_run_rc_ok"]
        and result["child_exit_code_ok"]
        and result["child_signal_ok"]
        and result["test_flash_ok"]
        and result["rollback_version_ok"]
        and result["rollback_selftest_fail_zero"]
    )
    return result


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
        "A90v1993",
        "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
    )
    init_forbidden = (
        "--allow-servloc-domain-list-probe",
        "--allow-service-notifier-listener-probe",
        "--qrtr-readback-matrix",
        "wlfw:69:0,1",
    )
    boot_required = (
        *init_required,
        "a90_android_execns_probe v366",
        "wlan_pd_firmware_serve_gate.rfs_bridge",
        "wlan_pd_producer_child_snapshot.%s.mode=passive-proc-only",
        "wlan_pd_producer_child_snapshot.%s.no_qmi_send=1",
        "wlan_pd_producer_child_snapshot.%s.no_qrtr_readback=1",
        "wlan_pd_producer_child_snapshot.%s.no_ptrace=1",
        "wlan_pd_firmware_serve_gate.requested_wlanmdsp=%d",
        "tftp_server",
        "pd-mapper",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V1993_INIT, init_required), (V1993_BOOT, boot_required)):
        if not path.exists():
            checks[rel(path)] = {"exists": False, "ok": False, "missing": list(required), "forbidden": []}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        forbidden = [token for token in init_forbidden if path == V1993_INIT and token.encode() in data]
        checks[rel(path)] = {"exists": True, "ok": not missing and not forbidden, "missing": missing, "forbidden": forbidden}
    return checks


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    details = ORIGINAL_COLLECT_DETAILS(handoff)
    details["helper_completion"] = collect_helper_completion(handoff)
    details["producer_child_snapshot"] = collect_producer_child_snapshot()
    return details


def classify(handoff: dict[str, Any],
             hook: dict[str, Any],
             steps: list[dict[str, Any]],
             details: dict[str, Any]) -> dict[str, Any]:
    base = ORIGINAL_CLASSIFY(handoff, hook, steps, details)
    trace = details.get("wlanmdsp_trace") if isinstance(details.get("wlanmdsp_trace"), dict) else {}
    producer = details.get("producer_child_snapshot") if isinstance(details.get("producer_child_snapshot"), dict) else {}
    helper = details.get("helper_completion") if isinstance(details.get("helper_completion"), dict) else {}
    route_ok = (
        bool(base.get("hook_ok"))
        and bool(base.get("prearm_ok"))
        and bool(base.get("rollback_ok"))
        and bool(base.get("light_ok"))
        and bool(base.get("combined"))
        and bool(base.get("rfs_bridge_ok"))
        and bool(helper.get("ok"))
    )
    if not route_ok:
        return {
            **base,
            "decision": f"v1994-{base.get('label', 'handoff-failed')}-rollback-blocked",
            "helper_completion_ok": bool(helper.get("ok")),
            "inner_handoff_pass": bool(base.get("handoff_ok")),
            "producer_child_snapshot_ok": bool(producer.get("ok")),
        }
    if not producer.get("ok"):
        label = "native-producer-child-passive-snapshot-missing"
        return {
            **base,
            "label": label,
            "decision": f"v1994-{label}-rollback-blocked",
            "pass": False,
            "reason": "V1993 did not capture passive pd-mapper/tftp_server child snapshots",
            "helper_completion_ok": True,
            "inner_handoff_pass": bool(base.get("handoff_ok")),
            "producer_child_snapshot_ok": False,
        }
    if not trace.get("requested") and producer.get("both_alive_after_window"):
        label = "native-producer-children-alive-no-wlanmdsp-request"
        return {
            **base,
            "label": label,
            "decision": f"v1994-{label}-rollback-pass",
            "pass": True,
            "reason": "V1993 helper, RFS bridge, light observer, and rollback passed; pd-mapper and tftp_server stayed alive, but the modem still never requested wlanmdsp.mbn",
            "helper_completion_ok": True,
            "inner_handoff_pass": bool(base.get("handoff_ok")),
            "producer_child_snapshot_ok": True,
        }
    label = str(base.get("label") or "native-producer-child-passive-review")
    return {
        **base,
        "label": label,
        "decision": f"v1994-{label}-rollback-pass",
        "pass": True,
        "helper_completion_ok": True,
        "inner_handoff_pass": bool(base.get("handoff_ok")),
        "producer_child_snapshot_ok": True,
    }


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    trace = details["wlanmdsp_trace"]
    bridge = trace["rfs_bridge"]
    light = trace["light_observer"]
    helper = details["helper_completion"]
    producer = details["producer_child_snapshot"]
    android = details["android_v1982"]
    rows = [
        ["label", classification["label"], classification["reason"]],
        ["helper_completion", classification.get("helper_completion_ok"), f"version={helper['result_file_version']} probe_rc={helper['probe_run_rc']} child_exit={helper['child_exit_code']} timed_out={helper['timed_out']} inner_pass={classification.get('inner_handoff_pass')}"],
        ["rfs_bridge", classification.get("rfs_bridge_ok"), f"exact_exists={bridge['exact_exists']} nonzero={bridge['exact_nonzero']} open_rc={bridge['exact_open_rc']} source_nonzero={bridge['source_asset_nonzero']} sda29_write={bridge['sda29_write']}"],
        ["light_observer", classification["light_ok"], f"servloc={light['servloc_domain_list_probe']} servnotif={light['service_notifier_listener_probe']} qrtr_send={light['qrtr_readback_send_attempted']} result={light['qrtr_readback_result']}"],
        ["producer_snapshots", producer.get("ok"), f"markers={producer.get('raw_marker_count')} after_holder={producer['phases']['after_holder_start']['snapshot_count']} after_window={producer['phases']['after_post_listener_window']['snapshot_count']}"],
        ["producer_alive", producer.get("both_alive_after_window"), f"holder={producer.get('both_alive_after_holder')} window={producer.get('both_alive_after_window')}"],
        ["combined_prereq", classification["combined"], f"service74={details['service74']} service180={details['service180']} pm_open={details['pm_open_subsys_modem']} holder={details['holder_opened']}"],
        ["wlanmdsp_request", trace["requested"], f"field={trace['requested_field']} tftp_lines={trace['tftp_wlanmdsp_lines']} failures={trace['wlanmdsp_failure_lines']}"],
        ["wlanmdsp_serve_load", bool(trace["requested"] and trace["served"]), f"available_nonzero={trace['served_nonzero']} pil_load={trace['pil_load_lines']} wlan_pd_up={trace['wlan_pd_up_lines']} wlfw69={trace['wlfw69_lines']} wlan0={trace['wlan0_lines']}"],
        ["android_v1982", android.get("requested_wlanmdsp", ""), f"wlan_pd={android.get('wlan_pd_up')} BDF={android.get('bdf')} wlan0={android.get('wlan0')} lines={android.get('wlanmdsp_line_count')}"],
    ]
    phase_lines: list[str] = []
    for phase, phase_info in producer["phases"].items():
        for child, child_info in phase_info["children"].items():
            phase_lines.append(
                f"- `{phase}/{child}` alive `{child_info['alive']}` state `{child_info['state']}` fd_socket_count `{child_info['fd_socket_count']}` task_count `{child_info['task_count']}`"
            )
            for block in child_info["syscall_blocks"][:2]:
                phase_lines.append(f"- `{phase}/{child}` syscall `{block}`")
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V1994 Producer Child Passive Handoff",
        "",
        "## Summary",
        "",
        "- Cycle: `V1994`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        prev1992.prev.markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in rows]),
        "",
        "## Producer Child Snapshot",
        "",
        *phase_lines,
        "",
        "## First Native Wlanmdsp Lines",
        "",
        *(f"- `{line}`" for line in trace["first_wlanmdsp_lines"]),
        *([] if trace["first_wlanmdsp_lines"] else ["- `none`"]),
        "",
        "## Branch",
        "",
        "- `native-producer-children-alive-no-wlanmdsp-request`: producer-side AP services are present/waiting, so the remaining gate is still before the modem chooses to request WLAN-PD code.",
        "- `native-wlanmdsp-requested-served-publication-progress`: stop before HAL/scan/connect and move downstream to WLFW/BDF/wlan0 validation.",
        "- `native-wlanmdsp-requested-served-pd-still-down`: escalate to modem-side DIAG; AP serve path is no longer the blocker.",
        "",
        "## Android Comparator",
        "",
        f"- Report: `{android.get('report', rel(prev1992.prev.ANDROID_V1982_REPORT))}`",
        f"- Timeline: WLAN-PD UP `{android.get('wlan_pd_up')}`, BDF `{android.get('bdf')}`, wlan0 `{android.get('wlan0')}`.",
        f"- Request evidence: requested_wlanmdsp `{android.get('requested_wlanmdsp')}`, wlanmdsp line count `{android.get('wlanmdsp_line_count')}`.",
        "",
        "## Steps",
        "",
        *step_lines,
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No rild/cnss/pm-service strace, boot-time QRTR matrix, service-locator probe, or service-notifier listener was run.",
        "- Passive producer snapshots used only `/proc` fd/wchan/syscall/status reads for `pd-mapper` and `tftp_server`; no ptrace, no QRTR readback, and no QMI send was used.",
        "- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V1993 test-boot flash-handoff, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def patch_prev_module() -> None:
    prev1992.CYCLE = CYCLE
    prev1992.OUT_DIR = OUT_DIR
    prev1992.HANDOFF_DIR = HANDOFF_DIR
    prev1992.HANDOFF_REPORT = HANDOFF_REPORT
    prev1992.REPORT_PATH = REPORT_PATH
    prev1992.V1991_OUT = V1993_OUT
    prev1992.V1991_INIT = V1993_INIT
    prev1992.V1991_BOOT = V1993_BOOT
    prev1992.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    prev1992.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    prev1992.TEST_LOG_PATH = TEST_LOG_PATH
    prev1992.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    prev1992.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    prev1992.artifact_hook_check = artifact_hook_check
    prev1992.classify = classify
    prev1992.render_report = render_report
    ORIGINAL_PATCH_PREV_MODULE()
    prev1992.prev.collect_details = collect_details


def main(argv: list[str] | None = None) -> int:
    prev1992.patch_prev_module = patch_prev_module
    return prev1992.main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
