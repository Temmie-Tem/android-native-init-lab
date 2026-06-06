#!/usr/bin/env python3
"""V2001 host-only classifier for the post-WLFW-cap native gap."""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path


CYCLE = "V2001"
SOURCE_DIR = repo_path("tmp/wifi/v2000-downstream-cascade-handoff")
SOURCE_MANIFEST = SOURCE_DIR / "manifest.json"
SOURCE_HELPER = SOURCE_DIR / "v1999-handoff/test-v1393-helper-result.stdout.txt"
SOURCE_DMESG = SOURCE_DIR / "v1999-handoff/test-v1393-dmesg.stdout.txt"
CNSS_DAEMON = repo_path("tmp/wifi/v222-vendor-root-evidence-export/vendor-root/bin/cnss-daemon")
OUT_DIR = repo_path("tmp/wifi/v2001-post-wlfw-cap-gap-classifier")
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V2001_POST_WLFW_CAP_GAP_CLASSIFIER_2026-06-04.md")

WLFW_EVENTS = (
    "wlfw_start",
    "wlfw_service_request",
    "wlfw_worker_pthread_create_success",
    "wlfw_client_init_instance_call",
    "wlfw_client_init_instance_retcheck",
    "wlfw_send_ind_register_entry",
    "wlfw_ind_register_qmi",
    "wlfw_fw_mem_cond_wait",
    "wlfw_cap_qmi",
)

LIBQMI_EVENTS = (
    "libqmi_get_service_list_lookup_call",
    "libqmi_get_service_list_lookup_ret",
    "libqmi_wait_return",
    "libqmi_loop_get_service_instance_ret",
    "libqmi_loop_client_init_ret",
    "libqmi_init_return",
    "libqmi_xport_new_server_service",
    "libqmi_xport_new_server_signal",
)

NEXT_PROBES = (
    {
        "name": "wlfw_fw_mem_wait_return",
        "offset": "0xdc1c",
        "fetch": "none",
        "meaning": "pthread_cond_wait returned before the capability-send call path",
    },
    {
        "name": "wlfw_cap_send_ret",
        "offset": "0xf464",
        "fetch": "send_rc=%x0",
        "meaning": "qmi_client_send_msg_sync returned from the WLFW capability request",
    },
    {
        "name": "wlfw_cap_send_or_result_error_branch",
        "offset": "0xf470",
        "fetch": "send_rc=%x0",
        "meaning": "send rc or QMI result was nonzero after the capability request",
    },
    {
        "name": "wlfw_cap_invalid_0x77_branch",
        "offset": "0xf49c",
        "fetch": "reason_reg=%x8",
        "meaning": "capability response hit the 0x77 special failure branch",
    },
    {
        "name": "wlfw_cap_success_branch",
        "offset": "0xf4b4",
        "fetch": "none",
        "meaning": "send rc and QMI result were both zero",
    },
    {
        "name": "wlfw_cap_rsp_result_error_branch",
        "offset": "0xf564",
        "fetch": "qmi_result=%x8",
        "meaning": "capability response QMI result error branch",
    },
    {
        "name": "wlfw_cap_return",
        "offset": "0xf580",
        "fetch": "rc=%x19",
        "meaning": "final return from the capability-request helper",
    },
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing source manifest: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"source manifest is not an object: {path}")
    return data


def read_strings(path: Path) -> str:
    if not path.exists():
        return ""
    return subprocess.check_output(["strings", "-a", str(path)], text=True, errors="replace")


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line or line.startswith("A90_"):
            continue
        key, value = line.split("=", 1)
        if key:
            fields[key.strip()] = value.strip()
    return fields


def event(fields: dict[str, str], group: str, name: str) -> dict[str, str]:
    prefix = f"wlan_pd_cnss_nonlog_control_flow.{group}.{name}."
    return {
        "name": name,
        "registered": fields.get(prefix + "registered", ""),
        "enabled": fields.get(prefix + "enabled", ""),
        "hit_count": fields.get(prefix + "hit_count", ""),
        "first_hit_line": fields.get(prefix + "first_hit_line", ""),
        "sample_line_0": fields.get(prefix + "sample_line_0", ""),
        "sample_line_1": fields.get(prefix + "sample_line_1", ""),
        "sample_line_2": fields.get(prefix + "sample_line_2", ""),
        "sample_line_3": fields.get(prefix + "sample_line_3", ""),
    }


def hit(data: dict[str, str]) -> int:
    return intish(data.get("hit_count"))


def line_time(line: str) -> float | None:
    match = re.search(r"\s([0-9]+\.[0-9]+):\s+[A-Za-z0-9_]", line)
    if not match:
        match = re.search(r"\[\s*([0-9]+\.[0-9]+)\]", line)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def first_time(event_data: dict[str, str]) -> float | None:
    return line_time(event_data.get("first_hit_line", ""))


def thread_token(line: str) -> str:
    match = re.search(r"\bcnss-daemon-([0-9]+)\b", line)
    return match.group(1) if match else ""


def time_for_thread(event_data: dict[str, str], thread: str) -> float | None:
    if not thread:
        return first_time(event_data)
    for key in ("first_hit_line", "sample_line_0", "sample_line_1", "sample_line_2", "sample_line_3"):
        line = event_data.get(key, "")
        if f"cnss-daemon-{thread}" in line:
            return line_time(line)
    return first_time(event_data)


def time_for_thread_matching(event_data: dict[str, str], thread: str, needle: str) -> float | None:
    for key in ("first_hit_line", "sample_line_0", "sample_line_1", "sample_line_2", "sample_line_3"):
        line = event_data.get(key, "")
        if (not thread or f"cnss-daemon-{thread}" in line) and needle in line:
            return line_time(line)
    return time_for_thread(event_data, thread)


def dmesg_count(pattern: str) -> int:
    if not SOURCE_DMESG.exists():
        return 0
    regex = re.compile(pattern, re.IGNORECASE)
    return sum(1 for line in SOURCE_DMESG.read_text(encoding="utf-8", errors="replace").splitlines() if regex.search(line))


def objdump_window(start: str, stop: str) -> list[str]:
    if not CNSS_DAEMON.exists():
        return []
    proc = subprocess.run(
        [
            "aarch64-linux-gnu-objdump",
            "-d",
            f"--start-address={start}",
            f"--stop-address={stop}",
            str(CNSS_DAEMON),
        ],
        cwd=repo_path("."),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return proc.stdout.splitlines()


def collect(source: dict[str, Any], fields: dict[str, str]) -> dict[str, Any]:
    cascade = ((source.get("details") or {}).get("cascade") or {})
    wlfw = {name: event(fields, "uprobe", name) for name in WLFW_EVENTS}
    libqmi = {name: event(fields, "libqmi_uprobe", name) for name in LIBQMI_EVENTS}
    wlfw_thread = thread_token(wlfw["wlfw_service_request"].get("first_hit_line", ""))
    ipc_after_post = {
        "wlfw_server_arrive": fields.get(
            "wlan_pd_icnss_ipc_snapshot.after_post_listener_window.debugfs_ipc_logging.wlfw_server_arrive", ""
        ),
        "service69_text": fields.get(
            "wlan_pd_icnss_ipc_snapshot.after_post_listener_window.debugfs_ipc_logging.service69_text", ""
        ),
        "first_focus_line": fields.get(
            "wlan_pd_icnss_ipc_snapshot.after_post_listener_window.debugfs_ipc_logging.first_focus_line", ""
        ),
    }
    return {
        "source_decision": source.get("decision", ""),
        "source_pass": bool(source.get("pass")),
        "source_report": "docs/reports/NATIVE_INIT_V2000_DOWNSTREAM_CASCADE_HANDOFF_2026-06-04.md",
        "helper_result": rel(SOURCE_HELPER),
        "cnss_daemon": rel(CNSS_DAEMON),
        "cnss_daemon_sha256": subprocess.check_output(["sha256sum", str(CNSS_DAEMON)], text=True).split()[0]
        if CNSS_DAEMON.exists()
        else "",
        "cascade": {
            "wlan_pd_up": intish(cascade.get("wlan_pd_up")),
            "icnss_qmi_connected": intish(cascade.get("icnss_qmi_connected")),
            "wlfw69": intish(cascade.get("wlfw69")),
            "bdf": intish(cascade.get("bdf")),
            "fw_ready": intish(cascade.get("fw_ready")),
            "wlan0": intish(cascade.get("wlan0")),
            "wlanmdsp_tftp": intish(cascade.get("wlanmdsp_tftp")),
            "pd_load": intish(cascade.get("pd_load")),
            "requested_any": intish(cascade.get("requested_any")),
            "post_up_hold_sec": cascade.get("post_up_hold_sec"),
        },
        "labels": {
            "nonlog": fields.get("wlan_pd_cnss_nonlog_control_flow.label", ""),
            "libqmi": fields.get("wlan_pd_cnss_nonlog_control_flow.libqmi_uprobe.label", ""),
            "service_window": fields.get("wlan_pd_service_window_trigger.label", ""),
            "firmware_serve": fields.get("wlan_pd_firmware_serve_gate.label", ""),
        },
        "ipc_after_post": ipc_after_post,
        "wlfw_events": wlfw,
        "libqmi_events": libqmi,
        "timing": {
            "wlan_pd_up": cascade.get("wlan_pd_up_ts"),
            "wlfw_thread": wlfw_thread,
            "libqmi_wlfw_wait_return": time_for_thread(libqmi["libqmi_wait_return"], wlfw_thread),
            "libqmi_wlfw_loop_instance_ret": time_for_thread_matching(
                libqmi["libqmi_loop_get_service_instance_ret"], wlfw_thread, "rc=0x0"
            ),
            "libqmi_wlfw_client_init_ret": time_for_thread_matching(
                libqmi["libqmi_loop_client_init_ret"], wlfw_thread, "rc=0x0"
            ),
            "wlfw_client_init_ret": first_time(wlfw["wlfw_client_init_instance_retcheck"]),
            "wlfw_ind_register": first_time(wlfw["wlfw_ind_register_qmi"]),
            "wlfw_fw_mem_wait": first_time(wlfw["wlfw_fw_mem_cond_wait"]),
            "wlfw_cap": first_time(wlfw["wlfw_cap_qmi"]),
        },
        "dmesg": {
            "bdf": dmesg_count(r"\bBDF\b|bdwlan|regdb|board data"),
            "fw_ready": dmesg_count(r"fw[_ -]?ready|firmware ready|FW ready"),
            "wlan0": dmesg_count(r"\bwlan0\b"),
            "wlanmdsp": dmesg_count(r"wlanmdsp"),
        },
        "static_next_probes": list(NEXT_PROBES),
        "static_disasm": {
            "fw_mem_window": objdump_window("0xdbf0", "0xdc30"),
            "cap_window": objdump_window("0xf450", "0xf590"),
        },
    }


def classify(details: dict[str, Any]) -> dict[str, Any]:
    cascade = details["cascade"]
    wlfw = details["wlfw_events"]
    libqmi = details["libqmi_events"]
    source_ok = details["source_pass"]
    route_ok = (
        source_ok
        and cascade["wlan_pd_up"] > 0
        and cascade["icnss_qmi_connected"] > 0
        and hit(wlfw["wlfw_service_request"]) > 0
        and hit(wlfw["wlfw_client_init_instance_retcheck"]) > 0
        and hit(libqmi["libqmi_loop_client_init_ret"]) > 0
    )
    cap_reached = hit(wlfw["wlfw_ind_register_qmi"]) > 0 and hit(wlfw["wlfw_cap_qmi"]) > 0
    downstream = cascade["bdf"] > 0 or cascade["fw_ready"] > 0 or cascade["wlan0"] > 0
    request_or_load = cascade["requested_any"] > 0 or cascade["wlanmdsp_tftp"] > 0 or cascade["pd_load"] > 0
    if not route_ok:
        label = "post-wlfw-cap-route-regression"
        reason = "V2000 did not preserve WLAN-PD UP plus CNSS/libqmi prerequisites"
        passed = False
    elif downstream:
        label = "post-wlfw-cap-downstream-progress"
        reason = "V2000 crossed the post-cap boundary into BDF/FW-ready/wlan0 progress"
        passed = True
    elif request_or_load:
        label = "post-wlfw-cap-firmware-request-or-load-progress"
        reason = "V2000 reached a firmware request/load marker but did not reach wlan0"
        passed = True
    elif cap_reached:
        label = "post-wlfw-cap-no-bdf-no-firmware-request"
        reason = "V2000 reached WLFW ind-register, firmware-memory wait, and capability QMI send, but no BDF/FW-ready/wlan0 or wlanmdsp request/load followed"
        passed = True
    else:
        label = "wlfw-cap-not-reached"
        reason = "V2000 reached WLFW client init but not the WLFW capability-send boundary"
        passed = False
    return {
        "label": label,
        "decision": f"v2001-{label}-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "route_ok": route_ok,
        "cap_reached": cap_reached,
        "downstream_progress": downstream,
        "firmware_request_or_load": request_or_load,
    }


def event_rows(events: dict[str, dict[str, str]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for name, data in events.items():
        rows.append([name, data.get("hit_count", ""), data.get("first_hit_line", "")])
    return rows


def probe_rows(details: dict[str, Any]) -> list[list[str]]:
    return [[item["name"], item["offset"], item["fetch"], item["meaning"]] for item in details["static_next_probes"]]


def render_disasm(lines: list[str], limit: int = 60) -> list[str]:
    selected = [line.rstrip() for line in lines if line.strip()]
    return [f"    {line}" for line in selected[:limit]]


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    cascade = details["cascade"]
    timing = details["timing"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["source", details["source_pass"], details["source_decision"]],
        ["cascade", "", f"wlan_pd={cascade['wlan_pd_up']} icnss_qmi={cascade['icnss_qmi_connected']} bdf={cascade['bdf']} fw_ready={cascade['fw_ready']} wlan0={cascade['wlan0']}"],
        ["firmware", classification["firmware_request_or_load"], f"requested_any={cascade['requested_any']} wlanmdsp_tftp={cascade['wlanmdsp_tftp']} pd_load={cascade['pd_load']}"],
        ["ipc", details["ipc_after_post"]["wlfw_server_arrive"], f"service69_text={details['ipc_after_post']['service69_text']} first={details['ipc_after_post']['first_focus_line']}"],
        ["labels", "", f"nonlog={details['labels']['nonlog']} libqmi={details['labels']['libqmi']} service_window={details['labels']['service_window']}"],
        ["timing", "", f"thread={timing['wlfw_thread']} up={timing['wlan_pd_up']} wait_ret={timing['libqmi_wlfw_wait_return']} instance_ret={timing['libqmi_wlfw_loop_instance_ret']} client_ret={timing['libqmi_wlfw_client_init_ret']} init_ret={timing['wlfw_client_init_ret']} ind={timing['wlfw_ind_register']} fw_mem_wait={timing['wlfw_fw_mem_wait']} cap={timing['wlfw_cap']}"],
    ]
    return "\n".join([
        "# Native Init V2001 Post-WLFW-Cap Gap Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V2001`",
        "- Type: host-only classifier over V2000 rollback-verified evidence plus `cnss-daemon` disassembly",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Result: `{'PASS' if manifest['pass'] else 'BLOCKED'}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Source: `{details['source_report']}`",
        "",
        "## Matrix",
        "",
        markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in matrix_rows]),
        "",
        "## WLFW Events",
        "",
        markdown_table(["event", "hits", "first"], event_rows(details["wlfw_events"])),
        "",
        "## Libqmi Events",
        "",
        markdown_table(["event", "hits", "first"], event_rows(details["libqmi_events"])),
        "",
        "## Next Live Probe Contract",
        "",
        markdown_table(["probe", "offset", "fetch", "meaning"], probe_rows(details)),
        "",
        "## Static Evidence",
        "",
        f"- `cnss-daemon`: `{details['cnss_daemon']}`",
        f"- SHA256: `{details['cnss_daemon_sha256']}`",
        "- The next unit should add only the branch probes above to the existing light V1999/V2000 route; no tftp ptrace, QRTR matrix, strace, HAL, scan/connect, or eSoC/PCIe/GDSC path is needed.",
        "",
        "### Firmware-Memory Wait Window",
        "",
        "```",
        *render_disasm(details["static_disasm"]["fw_mem_window"], 40),
        "```",
        "",
        "### Capability Send Window",
        "",
        "```",
        *render_disasm(details["static_disasm"]["cap_window"], 80),
        "```",
        "",
        "## Safety Scope",
        "",
        "- Host-only: no live device command, flash, reboot, service start, or filesystem mutation was performed.",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No `/dev/subsys_esoc0`, eSoC notify/BOOT_DONE, PCI rescan/bind, platform unbind, PMIC/GPIO/GDSC/regulator write, forced RC1/case, or fake ONLINE action was used.",
        "",
    ])


def main() -> int:
    source = read_json(SOURCE_MANIFEST)
    fields = parse_fields(read_strings(SOURCE_HELPER))
    details = collect(source, fields)
    classification = classify(details)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(OUT_DIR),
        "source_manifest": rel(SOURCE_MANIFEST),
        "decision": classification["decision"],
        "label": classification["label"],
        "pass": bool(classification["pass"]),
        "reason": classification["reason"],
        "classification": classification,
        "details": details,
        "host_metadata": collect_host_metadata(),
    }
    report = render_report(manifest)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(report, encoding="utf-8")
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ("decision", "label", "pass", "reason")}, indent=2))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
