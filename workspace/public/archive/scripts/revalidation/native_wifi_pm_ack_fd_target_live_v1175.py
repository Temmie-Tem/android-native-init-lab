#!/usr/bin/env python3
"""V1175 bounded PM-service ack fd-target live gate.

This V1174 derivative samples `/proc/<pm-service>/fd` while the PM-service
state-2 ack body opens its device fd.  It classifies whether the observed fd is
`/dev/subsys_modem`, `/dev/subsys_esoc0`, or another target.  It does not start
Wi-Fi HAL, scan/connect/link-up, use credentials, run DHCP/routes, external
ping, write boot/partitions, or flash.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_pm_ack_body_live_v1174 as v1174
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1175-pm-ack-fd-target-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1175-pm-ack-fd-target-live.txt")
DEFAULT_WORK_DIR = "/cache/a90-runtime/v1175"
DEFAULT_CHILD_SCRIPT = "/cache/a90-runtime/v1175/pm-ack-fd-target-child.sh"
DEFAULT_COLLECTOR_SCRIPT = "/cache/a90-runtime/v1175/pm-ack-fd-target-collector.sh"
DEFAULT_CHILD_OUTPUT = "/cache/a90-runtime/v1175/pm-ack-fd-target-output.txt"
PROOF_PREFIX = "/tmp/a90-v1175-"
DEFAULT_V1174_MANIFEST = Path("tmp/wifi/v1174-rerun-pm-ack-body-live-after-v490/manifest.json")
FD_SAMPLE_RE = re.compile(
    r"^pm_service_fd_sample index=(?P<index>[^ ]+) fd=(?P<fd>[0-9]+) target=(?P<target>.*)$"
)
FD_SAMPLE_PID_RE = re.compile(r"^pm_service_fd_sample_pid index=(?P<index>[^ ]+) pid=(?P<pid>[0-9]*)$")
_base_tracefs_collector_script_v1174 = v1174.tracefs_collector_script_v1174
_base_parse_tracefs_output_v1174 = v1174.parse_tracefs_output_v1174


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def tracefs_collector_script_v1175(args: Any) -> str:
    script = _base_tracefs_collector_script_v1174(args)
    function_anchor = 'echo "thread_sample_end index=$idx"\n}\n\n'
    fd_function = '''echo "thread_sample_end index=$idx"
}

sample_pm_service_fds() {
  idx="$1"
  echo "pm_service_fd_sample_begin index=$idx"
  pm_pid=$(find_pm_service_pid || true)
  echo "pm_service_fd_sample_pid index=$idx pid=$pm_pid"
  if $BB test -n "$pm_pid" && $BB test -d "/proc/$pm_pid/fd"; then
    for fd_path in /proc/$pm_pid/fd/[0-9]*; do
      if ! $BB test -e "$fd_path"; then
        continue
      fi
      fd_num="${fd_path##*/}"
      fd_target=$($BB readlink "$fd_path" 2>/dev/null || true)
      echo "pm_service_fd_sample index=$idx fd=$fd_num target=$fd_target"
    done
  else
    echo "pm_service_fd_sample_unavailable index=$idx"
  fi
  echo "pm_service_fd_sample_end index=$idx"
}

'''
    if function_anchor not in script:
        raise RuntimeError("V1106 collector sample function insertion point changed")
    script = script.replace(function_anchor, fd_function, 1)

    loop_anchor = '  sample_pm_service_threads "$sample_index"\n'
    loop_replacement = (
        '  sample_pm_service_threads "$sample_index"\n'
        '  sample_pm_service_fds "$sample_index"\n'
    )
    if loop_anchor not in script:
        raise RuntimeError("V1106 collector sample loop insertion point changed")
    script = script.replace(loop_anchor, loop_replacement, 1)

    final_anchor = "sample_pm_service_threads final\n"
    final_replacement = "sample_pm_service_threads final\nsample_pm_service_fds final\n"
    if final_anchor not in script:
        raise RuntimeError("V1106 collector final sample insertion point changed")
    return script.replace(final_anchor, final_replacement, 1)


def parse_fd_samples(text: str) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    pids: list[dict[str, str]] = []
    samples_seen: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("pm_service_fd_sample_begin "):
            index = stripped.split("index=", 1)[-1]
            samples_seen.add(index)
            continue
        pid_match = FD_SAMPLE_PID_RE.match(stripped)
        if pid_match:
            pids.append({"index": pid_match.group("index"), "pid": pid_match.group("pid")})
            continue
        sample_match = FD_SAMPLE_RE.match(stripped)
        if not sample_match:
            continue
        index = sample_match.group("index")
        samples_seen.add(index)
        fd = int(sample_match.group("fd"), 10)
        target = sample_match.group("target")
        records.append({"index": index, "fd": fd, "target": target})

    targets_by_fd: dict[str, list[str]] = {}
    for record in records:
        key = str(record["fd"])
        target = str(record.get("target", ""))
        if target not in targets_by_fd.setdefault(key, []):
            targets_by_fd[key].append(target)

    fd8_targets = targets_by_fd.get("8", [])
    return {
        "sample_count": len(samples_seen),
        "samples_with_pid": sum(1 for item in pids if item.get("pid")),
        "pid_samples": pids,
        "record_count": len(records),
        "records": records[:240],
        "targets_by_fd": targets_by_fd,
        "fd8_targets": fd8_targets,
        "has_subsys_modem": any("/dev/subsys_modem" in record.get("target", "") for record in records),
        "has_subsys_esoc0": any("/dev/subsys_esoc0" in record.get("target", "") for record in records),
        "has_fd8_subsys_modem": any("/dev/subsys_modem" in target for target in fd8_targets),
        "has_fd8_subsys_esoc0": any("/dev/subsys_esoc0" in target for target in fd8_targets),
    }


def parse_tracefs_output_v1175(text: str) -> dict[str, Any]:
    parsed = _base_parse_tracefs_output_v1174(text)
    parsed["pm_ack_fd_targets"] = parse_fd_samples(text)
    return parsed


def patch_defaults() -> None:
    v1174.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1174.LATEST_POINTER = LATEST_POINTER
    v1174.DEFAULT_WORK_DIR = DEFAULT_WORK_DIR
    v1174.DEFAULT_CHILD_SCRIPT = DEFAULT_CHILD_SCRIPT
    v1174.DEFAULT_COLLECTOR_SCRIPT = DEFAULT_COLLECTOR_SCRIPT
    v1174.DEFAULT_CHILD_OUTPUT = DEFAULT_CHILD_OUTPUT
    v1174.PROOF_PREFIX = PROOF_PREFIX
    v1174.patch_defaults()
    v1174.tracefs_collector_script_v1174 = tracefs_collector_script_v1175
    v1174.parse_tracefs_output_v1174 = parse_tracefs_output_v1175
    v1174.v1173.v1172.v1171.v1170.v1169.tracefs_collector_script_v1169 = tracefs_collector_script_v1175
    v1174.v1173.v1172.v1171.v1170.parse_tracefs_output_v1170 = parse_tracefs_output_v1175
    v1174.v1173.v1172.v1171.v1170.v1169.v1168.tracefs_collector_script_v1168 = tracefs_collector_script_v1175
    v1174.v1173.v1172.v1171.v1170.v1169.parse_tracefs_output_v1169 = parse_tracefs_output_v1175
    v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.tracefs_collector_script_v1165 = (
        tracefs_collector_script_v1175
    )
    v1174.v1173.v1172.v1171.v1170.v1169.v1168.parse_tracefs_output_v1168 = parse_tracefs_output_v1175
    v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.parse_tracefs_output_v1167 = parse_tracefs_output_v1175
    v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.tracefs_collector_script = (
        tracefs_collector_script_v1175
    )
    v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.parse_tracefs_output = (
        parse_tracefs_output_v1175
    )


def tracefs(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1174.tracefs(manifest)


def pm_ack_body(manifest: dict[str, Any]) -> dict[str, Any]:
    return v1174.pm_ack_body(manifest)


def pm_ack_fd_targets(manifest: dict[str, Any]) -> dict[str, Any]:
    value = tracefs(manifest).get("pm_ack_fd_targets") or {}
    return value if isinstance(value, dict) else {}


def _open_result_fds(body: dict[str, Any]) -> list[int]:
    values = body.get("open_ret_signed")
    return values if isinstance(values, list) else []


def decide_v1175(args: Any, manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1175-pm-ack-fd-target-plan-ready",
            True,
            "plan-only; no device mutation, PM actor, mdm_helper, CNSS daemon, reboot, or Wi-Fi action executed",
            "run bounded PM ack fd-target live with helper v217 and explicit allow flags",
        )

    base_decision, base_pass, base_reason, base_next = v1174.decide_v1174(args, manifest)
    body = pm_ack_body(manifest)
    fd_targets = pm_ack_fd_targets(manifest)
    open_result_fds = _open_result_fds(body)
    if not base_pass:
        return (
            base_decision.replace("v1174", "v1175", 1),
            False,
            base_reason,
            base_next,
        )
    if not body.get("state2_open_success_seen"):
        return (
            "v1175-state2-open-not-reproduced",
            False,
            f"body={body}",
            "restore V1174 state-2 open reproduction before fd-target classification",
        )
    if not fd_targets.get("record_count"):
        return (
            "v1175-pm-service-fd-sample-missing",
            True,
            f"open_result_fds={open_result_fds} fd_targets={fd_targets}",
            "increase fd sampling window or fetch device_path string directly from tracefs",
        )
    if 8 in open_result_fds and fd_targets.get("has_fd8_subsys_esoc0"):
        return (
            "v1175-state2-opened-subsys-esoc0",
            True,
            f"open_result_fds={open_result_fds} fd_targets={fd_targets}",
            "move to bounded MHI/WLFW/BDF publication gate",
        )
    if 8 in open_result_fds and fd_targets.get("has_fd8_subsys_modem"):
        return (
            "v1175-state2-opened-subsys-modem-not-esoc0",
            True,
            f"open_result_fds={open_result_fds} fd_targets={fd_targets}",
            "compare Android state-3 post-open actor that opens or requests mdm3/esoc0",
        )
    if 8 in open_result_fds and fd_targets.get("fd8_targets"):
        return (
            "v1175-state2-opened-other-fd-target",
            True,
            f"open_result_fds={open_result_fds} fd_targets={fd_targets}",
            "inspect fd 8 target and compare Android PM-service state-3 follow-up",
        )
    if fd_targets.get("has_subsys_esoc0"):
        return (
            "v1175-subsys-esoc0-fd-seen-fd8-missed",
            True,
            f"open_result_fds={open_result_fds} fd_targets={fd_targets}",
            "move to bounded MHI/WLFW/BDF publication gate after aligning fd sampling with open result",
        )
    if fd_targets.get("has_subsys_modem"):
        return (
            "v1175-subsys-modem-fd-seen-fd8-missed",
            True,
            f"open_result_fds={open_result_fds} fd_targets={fd_targets}",
            "align fd sampling with the state-2 open result or compare Android state-3 actor",
        )
    return (
        "v1175-pm-ack-fd-target-unclassified",
        True,
        f"open_result_fds={open_result_fds} fd_targets={fd_targets}",
        "inspect sampled fd targets before choosing the next gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    base = v1174.render_summary(manifest).replace(
        "# V1174 PM Ack Body Live",
        "# V1175 PM Ack FD Target Live",
        1,
    )
    fd_targets = pm_ack_fd_targets(manifest)
    body = pm_ack_body(manifest)
    rows = [
        ["open_ret_signed", json.dumps(body.get("open_ret_signed", []))],
        ["sample_count", fd_targets.get("sample_count", "")],
        ["samples_with_pid", fd_targets.get("samples_with_pid", "")],
        ["record_count", fd_targets.get("record_count", "")],
        ["fd8_targets", json.dumps(fd_targets.get("fd8_targets", []), sort_keys=True)],
        ["has_fd8_subsys_modem", fd_targets.get("has_fd8_subsys_modem", "")],
        ["has_fd8_subsys_esoc0", fd_targets.get("has_fd8_subsys_esoc0", "")],
        ["has_subsys_modem", fd_targets.get("has_subsys_modem", "")],
        ["has_subsys_esoc0", fd_targets.get("has_subsys_esoc0", "")],
    ]
    target_rows = [
        [fd, json.dumps(targets, sort_keys=True)]
        for fd, targets in sorted(fd_targets.get("targets_by_fd", {}).items(), key=lambda item: int(item[0]))
    ]
    return base + "\n".join([
        "",
        "## V1175 PM-Service FD Targets",
        "",
        markdown_table(["key", "value"], rows),
        "",
        "## V1175 Targets By FD",
        "",
        markdown_table(["fd", "targets"], target_rows),
        "",
    ])


def main() -> int:
    patch_defaults()
    args = v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.parse_args()
    v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.set_global_defaults(args)
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.v1113.v1106.build_manifest(args, store)
    manifest["base_v1174_decision"] = manifest.get("decision", "")
    manifest["cycle"] = "v1175"
    manifest["generated_at"] = now_iso()
    manifest["v1174_manifest"] = str(DEFAULT_V1174_MANIFEST)
    decision, passed, reason, next_step = decide_v1175(args, manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    fw = v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.global_firmware(manifest)
    values = v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.contract(manifest)
    post = v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.v1139.post_pm(manifest)
    lower = v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.v1143.lower_trace(manifest)
    late = v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165.late_per_proxy(manifest)
    manifest["firmware_mounts_executed"] = bool(fw.get("mount_results"))
    manifest["global_modem_holder_opened"] = bool(fw.get("holder_opened"))
    manifest["reboot_executed"] = bool(fw.get("reboot_cleanup"))
    manifest["post_pm_mdm_helper_executed"] = post.get("exec_attempted") == "1"
    manifest["post_pm_mdm_helper_lower_trace_emitted"] = lower.get("begin") == "1"
    manifest["late_per_proxy_started"] = late.get("started") == "1"
    manifest["cnss_daemon_start_executed"] = values.get("cnss_daemon_start_executed") == "1"
    manifest["wifi_hal_start_executed"] = (
        values.get("wifi_hal_start_executed") == "1"
        or post.get("wifi_hal_start_executed") == "1"
        or lower.get("wifi_hal_start_executed") == "1"
    )
    manifest["scan_connect_executed"] = (
        values.get("scan_connect_linkup") == "1"
        or post.get("scan_connect_linkup") == "1"
        or lower.get("scan_connect_linkup") == "1"
    )
    manifest["credential_use_executed"] = lower.get("credentials") == "1"
    manifest["dhcp_route_executed"] = lower.get("dhcp_routing") == "1"
    manifest["external_ping_executed"] = (
        values.get("external_ping") == "1"
        or post.get("external_ping") == "1"
        or lower.get("external_ping") == "1"
    )
    manifest["wifi_bringup_executed"] = False

    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"firmware_mounts_executed: {manifest['firmware_mounts_executed']}")
    print(f"global_modem_holder_opened: {manifest['global_modem_holder_opened']}")
    print(f"post_pm_mdm_helper_executed: {manifest['post_pm_mdm_helper_executed']}")
    print(f"post_pm_mdm_helper_lower_trace_emitted: {manifest['post_pm_mdm_helper_lower_trace_emitted']}")
    print(f"late_per_proxy_started: {manifest['late_per_proxy_started']}")
    print(f"tracefs_write_executed: {manifest['tracefs_write_executed']}")
    print(f"cnss_daemon_start_executed: {manifest['cnss_daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
