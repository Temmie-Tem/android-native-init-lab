#!/usr/bin/env python3
"""V1925 clean-DSP plus V1924 WLFW client-wait observer handoff."""

from __future__ import annotations

import datetime as dt
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import native_wifi_pm_service_open_context_handoff_v1847 as v1847
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1925"
OUT_DIR = repo_path("tmp/wifi/v1925-wlfw-client-wait-integration")
HANDOFF_DIR = OUT_DIR / "v1924-handoff"
HANDOFF_REPORT = OUT_DIR / "v1924-handoff-report.md"
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1925_WLFW_CLIENT_WAIT_INTEGRATION_2026-06-04.md")
V1924_OUT = repo_path("tmp/wifi/v1924-wlfw-client-wait-observer-test-boot")
V1924_INIT = V1924_OUT / "init_v1924_wlfw_client_wait_observer"
V1924_BOOT = V1924_OUT / "boot_linux_v1924_wlfw_client_wait_observer.img"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1924/dev/__properties__"
TEST_EXPECT_VERSION = "A90 Linux init 0.9.173 (v1924-wlfw-client-wait-observer)"
TEST_LOG_PATH = "/cache/native-init-wifi-test-boot-v1924.log"
TEST_SUMMARY_PATH = "/cache/native-init-wifi-test-boot-v1924.summary"
TEST_HELPER_RESULT_PATH = "/cache/native-init-wifi-test-boot-v1924-helper.result"
V641_FLAG = "/cache/native-init-sibling-fwssctl-v641"
V724_QRTR_FLAG = "/cache/native-init-qrtr-servloc-boot-v724"

SECRET_RE = re.compile(r"t[e]mmie[0-9A-Za-z_@.-]*")
REDACT_PATTERNS = (
    (SECRET_RE, "[REDACTED]"),
    (re.compile(r"made by [^\r\n]+"), "made by [redacted]"),
    (re.compile(r"creator: made by [^\r\n]+"), "creator: made by [redacted]"),
)
WLFW_CLIENT_EVENTS = (
    "wlfw_start",
    "dms_service_request",
    "wlfw_service_request",
    "wlfw_worker_pthread_create_success",
    "wlfw_client_init_instance_call",
    "wlfw_client_init_instance_retcheck",
    "wlfw_client_init_instance_fail_log",
    "wlfw_register_error_cb_call",
    "wlfw_register_error_cb_retcheck",
    "wlfw_get_service_instance_call",
    "wlfw_get_service_instance_retcheck",
    "wlfw_get_instance_id_call",
    "wlfw_get_instance_id_retcheck",
    "wlfw_send_ind_register_entry",
    "wlfw_fw_mem_cond_wait",
    "wlfw_ind_register_qmi",
    "wlfw_cap_qmi",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reparse-existing", action="store_true", help="reclassify existing V1925 handoff evidence without live device actions")
    return parser.parse_args(argv)


def redact(text: str) -> str:
    result = text
    for pattern, replacement in REDACT_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


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


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "present"}


def positive_count_list(value: object) -> bool:
    return any(intish(part.strip()) > 0 for part in str(value or "").split(",") if part.strip())


def run_host(store: EvidenceStore, name: str, command: list[str], timeout: float = 60.0) -> dict[str, Any]:
    started = dt.datetime.now(dt.timezone.utc)
    try:
        proc = subprocess.run(
            command,
            cwd=repo_path("."),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        output = redact(proc.stdout)
        rc = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        output = redact((exc.stdout or "") + (exc.stderr or "") + f"\n[timeout after {timeout}s]\n")
        rc = 124
        timed_out = True
    path = f"host/{name}.txt"
    store.write_text(path, "$ " + " ".join(command) + "\n" + output.rstrip() + "\n")
    return {
        "name": name,
        "command": command,
        "rc": rc,
        "ok": rc == 0,
        "timed_out": timed_out,
        "started": started.isoformat(),
        "file": path,
        "output_tail": output.splitlines()[-20:],
    }


def a90ctl(command: list[str]) -> list[str]:
    return [sys.executable, "scripts/revalidation/a90ctl.py", "--timeout", "45", *command]


def shell_a90(script: str) -> list[str]:
    return a90ctl(["run", "/cache/bin/busybox", "sh", "-c", script])


def flag_probe_script() -> str:
    return (
        f"for f in {V641_FLAG} {V724_QRTR_FLAG} /cache/native-init-sibling-fwssctl-v641.log; do "
        'if [ -e "$f" ]; then echo "exists $f"; /cache/bin/busybox ls -l "$f"; '
        '/cache/bin/busybox tail -n 20 "$f" 2>/dev/null || true; '
        'else echo "missing $f"; fi; done'
    )


def arm_clean_dsp_flag_script() -> str:
    return (
        f"if [ -e {V724_QRTR_FLAG} ]; then echo v1925.blocked=qrtr_flag_present; exit 42; fi; "
        f"umask 077; printf run > {V641_FLAG}; sync; "
        f"echo v1925.clean_dsp_flag_armed=1; /cache/bin/busybox ls -l {V641_FLAG}; "
        f"/cache/bin/busybox cat {V641_FLAG}"
    )


def cleanup_flag_script() -> str:
    return (
        f"if [ -e {V641_FLAG} ]; then /cache/bin/busybox rm -f {V641_FLAG}; "
        "echo v1925.cleaned_leftover_clean_dsp_flag=1; "
        "else echo v1925.cleaned_leftover_clean_dsp_flag=0; fi"
    )


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": rel(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": rel(path), "invalid": str(exc)}
    return data if isinstance(data, dict) else {"exists": True, "path": rel(path), "invalid": "not-object"}


def text_contains(path: Path, pattern: str) -> bool:
    if not path.exists():
        return False
    regex = re.compile(pattern, re.IGNORECASE)
    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if regex.search(text):
            return True
    return False


def artifact_hook_check() -> dict[str, Any]:
    init_required = (
        "native-init-sibling-fwssctl-v641",
        "A90v641: sibling fwssctl proof armed",
        "wifi-v641-fwssctl",
    )
    boot_required = (
        *init_required,
        "a90_android_execns_probe v360",
        "wlfw_client_init_instance_call",
        "wlfw_get_service_instance_call",
        "wlfw_send_ind_register_entry",
    )
    checks: dict[str, Any] = {}
    for path, required in ((V1924_INIT, init_required), (V1924_BOOT, boot_required)):
        if not path.exists():
            checks[rel(path)] = {"exists": False, "ok": False, "missing": list(required)}
            continue
        data = path.read_bytes()
        missing = [token for token in required if token.encode() not in data]
        checks[rel(path)] = {"exists": True, "ok": not missing, "missing": missing}
    return checks


def configure_handoff_globals() -> None:
    v1847.V1846_OUT = V1924_OUT
    v1847.REMOTE_PROPERTY_ROOT = REMOTE_PROPERTY_ROOT
    v1847.DEFAULT_OUT_DIR = HANDOFF_DIR
    v1847.DEFAULT_REPORT_PATH = HANDOFF_REPORT
    v1847.TEST_EXPECT_VERSION = TEST_EXPECT_VERSION
    v1847.TEST_LOG_PATH = TEST_LOG_PATH
    v1847.TEST_SUMMARY_PATH = TEST_SUMMARY_PATH
    v1847.TEST_HELPER_RESULT_PATH = TEST_HELPER_RESULT_PATH
    v1847.DMESG_PATTERN = (
        "A90v1924|A90v641|sibling fwssctl|wifi-v641-fwssctl|"
        "wlfw_client_init_instance|wlfw_get_service_instance|wlfw_get_instance_id|"
        "wlfw_send_ind_register_entry|wlfw_fw_mem_cond_wait|"
        + v1847.DMESG_PATTERN
    )


def run_handoff() -> int:
    configure_handoff_globals()
    original_configure_runner = v1847.configure_runner

    def patched_configure_runner() -> None:
        original_configure_runner()
        v1847.runner().DEFAULT_TEST_IMAGE = V1924_BOOT

    v1847.configure_runner = patched_configure_runner
    try:
        return v1847.main([])
    finally:
        v1847.configure_runner = original_configure_runner


def event(fields: dict[str, str], name: str) -> dict[str, str]:
    prefix = f"wlan_pd_cnss_nonlog_control_flow.uprobe.{name}."
    return {
        "name": name,
        "registered": fields.get(prefix + "registered", ""),
        "enabled": fields.get(prefix + "enabled", ""),
        "hit_count": fields.get(prefix + "hit_count", ""),
        "first_hit_line": fields.get(prefix + "first_hit_line", ""),
        "sample_count": fields.get(prefix + "sample_count", ""),
        "sample_line_0": fields.get(prefix + "sample_line_0", ""),
    }


def hit(fields: dict[str, str], name: str) -> int:
    return intish(event(fields, name).get("hit_count"))


def collect_details(handoff: dict[str, Any]) -> dict[str, Any]:
    gate = handoff.get("gate") if isinstance(handoff.get("gate"), dict) else {}
    fields = v1847.runner().fwbase.parse_helper_fields(HANDOFF_DIR)
    client_events = {name: event(fields, name) for name in WLFW_CLIENT_EVENTS}
    service74 = bool(gate.get("klog_service74_positive")) or bool(gate.get("raw_service74_text_positive")) or positive_count_list(gate.get("raw_service74_text_counts"))
    service180 = bool(gate.get("klog_service180_positive")) or bool(gate.get("raw_service180_text_positive")) or positive_count_list(gate.get("raw_service180_text_counts"))
    pm_open = gate.get("open_context_path") == "/dev/subsys_modem" and intish(gate.get("open_context_fd")) >= 0
    holder_opened = boolish(fields.get("wlan_pd_modem_holder.opened"))
    return {
        "service74": service74,
        "service180": service180,
        "pm_open_subsys_modem": pm_open,
        "open_context_path": gate.get("open_context_path", ""),
        "open_context_fd": gate.get("open_context_fd", ""),
        "holder_opened": holder_opened,
        "holder_fd": fields.get("wlan_pd_modem_holder.fd", ""),
        "nonlog_label": fields.get("wlan_pd_cnss_nonlog_control_flow.label", ""),
        "service_window_label": fields.get("wlan_pd_service_window_trigger.label", ""),
        "service_object_label": fields.get("wlan_pd_service_object_visible_trigger.label", ""),
        "servnotif_late_state": fields.get("wifi_companion_service_notifier_late_listener.response_curr_state_name", ""),
        "servnotif_late_indication": fields.get("wifi_companion_service_notifier_late_listener.indication_seen", ""),
        "servloc_result": fields.get("wifi_companion_servloc_domain_list.result", ""),
        "servloc_domain": fields.get("wifi_companion_servloc_domain_list.domain.0.name", ""),
        "servloc_instance": fields.get("wifi_companion_servloc_domain_list.domain.0.instance_id", ""),
        "qrtr69_case0_events": fields.get("wifi_companion_qrtr_readback.case_0.readback.service_events", ""),
        "qrtr69_case1_events": fields.get("wifi_companion_qrtr_readback.case_1.readback.service_events", ""),
        "wlfw69": intish(fields.get("wlan_pd_service_window_trigger.wlfw_service69_seen")) > 0 or bool(gate.get("lower_service69_progress")),
        "wlan_pd": positive_count_list(gate.get("raw_wlan_pd_text_counts")),
        "wlanmdsp": intish(fields.get("wlan_pd_service_window_trigger.requested_wlanmdsp")) > 0,
        "wlan0": bool(gate.get("lower_wlan0_present")),
        "events": client_events,
    }


def classify(handoff: dict[str, Any], hook: dict[str, Any], steps: list[dict[str, Any]], details: dict[str, Any]) -> dict[str, Any]:
    rollback = handoff.get("post_rollback_verification") or {}
    hook_ok = all(item.get("ok") for item in hook.values())
    prearm_ok = any(step["name"] == "arm-clean-dsp-flag" and step["ok"] for step in steps)
    handoff_ok = bool(handoff.get("pass"))
    rollback_ok = bool(rollback.get("version_ok")) and bool(rollback.get("selftest_fail_zero"))
    combined = details["service74"] and details["pm_open_subsys_modem"] and details["holder_opened"] and hit_from_details(details, "wlfw_service_request") > 0
    publication_progress = details["wlfw69"] or details["wlan_pd"] or details["wlanmdsp"] or details["wlan0"]
    if not hook_ok or not prearm_ok or not handoff_ok or not rollback_ok:
        label = "wlfw-client-wait-handoff-failed"
        reason = "artifact hook, clean-DSP prearm, V1924 handoff, or rollback verification failed"
        passed = False
    elif publication_progress or hit_from_details(details, "wlfw_ind_register_qmi") > 0 or hit_from_details(details, "wlfw_cap_qmi") > 0:
        label = "wlfw-client-wait-progress-stop"
        reason = "WLFW/QMI or lower WLAN-PD publication progressed; stop before HAL/scan/connect"
        passed = True
    elif not combined:
        label = "wlfw-client-wait-prereq-regression"
        reason = "combined service74 + PM-open + holder + WLFW worker prerequisites did not reproduce"
        passed = False
    elif hit_from_details(details, "wlfw_client_init_instance_call") > 0 and hit_from_details(details, "wlfw_client_init_instance_retcheck") == 0:
        label = "wlfw-worker-blocked-in-qmi-client-init-instance"
        reason = "WLFW worker entered qmi_client_init_instance and did not return while WLFW69/WLAN-PD stayed absent"
        passed = True
    elif hit_from_details(details, "wlfw_get_service_instance_call") > 0 and hit_from_details(details, "wlfw_get_service_instance_retcheck") == 0:
        label = "wlfw-worker-blocked-in-get-service-instance"
        reason = "WLFW client init returned, but qmi_client_get_service_instance did not return while WLFW69/WLAN-PD stayed absent"
        passed = True
    elif hit_from_details(details, "wlfw_get_service_instance_retcheck") > 0 and hit_from_details(details, "wlfw_get_instance_id_call") == 0:
        label = "wlfw-worker-service-instance-returned-before-instance-id"
        reason = "WLFW service-instance lookup returned but instance-id lookup did not start"
        passed = True
    elif hit_from_details(details, "wlfw_send_ind_register_entry") > 0 and hit_from_details(details, "wlfw_ind_register_qmi") == 0:
        label = "wlfw-worker-entered-ind-register-before-qmi-send"
        reason = "WLFW ind-register function entry fired but the first QMI sync send did not"
        passed = True
    else:
        label = "wlfw-client-wait-incomplete"
        reason = "WLFW worker reproduced but the new client-wait discriminator was incomplete"
        passed = False
    return {
        "label": label,
        "decision": f"v1925-{label}-rollback-{'pass' if passed else 'blocked'}",
        "pass": passed,
        "reason": reason,
        "hook_ok": hook_ok,
        "prearm_ok": prearm_ok,
        "handoff_ok": handoff_ok,
        "rollback_ok": rollback_ok,
        "combined": combined,
        "publication_progress": publication_progress,
    }


def hit_from_details(details: dict[str, Any], name: str) -> int:
    return intish(details["events"].get(name, {}).get("hit_count"))


def render_event_rows(details: dict[str, Any]) -> list[list[str]]:
    rows: list[list[str]] = []
    for name in WLFW_CLIENT_EVENTS:
        data = details["events"].get(name, {})
        rows.append([
            name,
            f"{data.get('registered')}/{data.get('enabled')}/{data.get('hit_count')}",
            data.get("first_hit_line", ""),
        ])
    return rows


def render_report(manifest: dict[str, Any]) -> str:
    details = manifest["details"]
    classification = manifest["classification"]
    matrix_rows = [
        ["label", classification["label"], classification["reason"]],
        ["combined", classification["combined"], f"service74={details['service74']} pm_open={details['pm_open_subsys_modem']} holder={details['holder_opened']}"],
        ["publication", classification["publication_progress"], f"wlfw69={details['wlfw69']} wlan_pd={details['wlan_pd']} wlanmdsp={details['wlanmdsp']} wlan0={details['wlan0']}"],
        ["servnotif", details["servnotif_late_state"], f"indication={details['servnotif_late_indication']} qrtr69={details['qrtr69_case0_events']},{details['qrtr69_case1_events']}"],
    ]
    step_lines = [
        f"- `{step['name']}` rc `{step['rc']}` ok `{step['ok']}` evidence `{step['file']}`"
        for step in manifest["steps"]
    ]
    return "\n".join([
        "# Native Init V1925 WLFW Client-wait Integration",
        "",
        "## Summary",
        "",
        "- Cycle: `V1925`",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Pass: `{manifest['pass']}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        f"- Inner handoff: `{manifest['handoff_manifest']}`",
        "",
        "## Matrix",
        "",
        markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in matrix_rows]),
        "",
        "## WLFW Client Events",
        "",
        markdown_table(["event", "registered/enabled/hits", "first hit"], render_event_rows(details)),
        "",
        "## Route State",
        "",
        f"- PM open: `{details['open_context_path']}` fd `{details['open_context_fd']}`",
        f"- Holder fd: `{details['holder_fd']}`",
        f"- Labels: `{details['nonlog_label']}` / `{details['service_window_label']}` / `{details['service_object_label']}`",
        f"- Servloc: `{details['servloc_result']}` domain `{details['servloc_domain']}` instance `{details['servloc_instance']}`",
        "",
        "## Steps",
        "",
        *step_lines,
        "",
        "## Safety",
        "",
        "- No Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was used.",
        "- No direct `/dev/subsys_esoc0` open/control, forced RC1/case, PMIC/GPIO/GDSC/regulator, PCI rescan, platform bind/unbind, fake ONLINE, or eSoC notify/BOOT_DONE action was used.",
        "- Mutation scope: `/cache` one-shot clean-DSP flag, V1924 test-boot flash-handoff, and rollback to `stage3/boot_linux_v724.img` with selftest fail=0.",
        "",
    ])


def write_result(store: EvidenceStore,
                 handoff: dict[str, Any],
                 hook: dict[str, Any],
                 steps: list[dict[str, Any]],
                 handoff_rc: int,
                 created: str | None = None) -> dict[str, Any]:
    details = collect_details(handoff)
    classification = classify(handoff, hook, steps, details)
    host_metadata = collect_host_metadata()
    host_metadata["repo"] = "."
    manifest = {
        "created": created or dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(OUT_DIR),
        "decision": classification["decision"],
        "label": classification["label"],
        "pass": bool(classification["pass"]),
        "reason": classification["reason"],
        "handoff_rc": handoff_rc,
        "handoff_manifest": rel(HANDOFF_DIR / "manifest.json"),
        "artifact_hook": hook,
        "classification": classification,
        "details": details,
        "steps": steps,
        "host_metadata": host_metadata,
    }
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    REPORT_PATH.write_text(report, encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    store = EvidenceStore(OUT_DIR)
    store.mkdir("host")
    if args.reparse_existing:
        existing = load_json(OUT_DIR / "manifest.json")
        handoff = load_json(HANDOFF_DIR / "manifest.json")
        hook = artifact_hook_check()
        steps = existing.get("steps") if isinstance(existing.get("steps"), list) else []
        manifest = write_result(
            store,
            handoff,
            hook,
            steps,
            intish(existing.get("handoff_rc")),
            created=str(existing.get("created") or dt.datetime.now(dt.timezone.utc).isoformat()),
        )
        print(f"{'PASS' if manifest['pass'] else 'BLOCKED'} label={manifest['label']} out_dir={manifest['out_dir']}")
        return 0 if manifest["pass"] else 1
    steps: list[dict[str, Any]] = []
    steps.append(run_host(store, "pre-version", a90ctl(["version"]), timeout=45.0))
    steps.append(run_host(store, "pre-selftest", a90ctl(["selftest"]), timeout=45.0))
    steps.append(run_host(store, "pre-flags", shell_a90(flag_probe_script()), timeout=45.0))
    hook = artifact_hook_check()
    steps.append(run_host(store, "arm-clean-dsp-flag", shell_a90(arm_clean_dsp_flag_script()), timeout=45.0))
    handoff_rc = run_handoff()
    handoff = load_json(HANDOFF_DIR / "manifest.json")
    steps.append(run_host(store, "cleanup-leftover-clean-dsp-flag", shell_a90(cleanup_flag_script()), timeout=45.0))
    steps.append(run_host(store, "post-selftest", a90ctl(["selftest"]), timeout=45.0))
    steps.append(run_host(store, "post-status", a90ctl(["status"]), timeout=45.0))
    steps.append(run_host(store, "post-flags", [sys.executable, "scripts/revalidation/a90ctl.py", "--timeout", "45", "--hide-on-busy", "run", "/cache/bin/busybox", "sh", "-c", flag_probe_script()], timeout=60.0))
    manifest = write_result(store, handoff, hook, steps, handoff_rc)
    print(f"{'PASS' if manifest['pass'] else 'BLOCKED'} label={manifest['label']} out_dir={manifest['out_dir']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
