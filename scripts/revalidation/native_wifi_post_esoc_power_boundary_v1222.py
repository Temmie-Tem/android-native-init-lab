#!/usr/bin/env python3
"""V1222: observe the post-subsys_esoc0 eSoC power-up boundary.

V1221 proved the private patched CNSS path can register ``SDX50M`` and make
``pm-service`` enter the ``/dev/subsys_esoc0`` open path.  V1222 keeps the same
bounded setup but holds the child script alive after the helper returns so the
tracefs sampler can observe what happens after that eSoC open:

* ``mdm3`` state transitions;
* ``pm-service`` wchan/syscall while the eSoC open is active;
* ICNSS/modem-down/WLFW/BDF/``wlan0`` dmesg markers;
* QRTR service-69 visibility and network-interface surface.

Safety is unchanged from V1221: no Wi-Fi HAL, scan/connect, credentials,
DHCP/routes, external ping, boot image write, or vendor partition write.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import shlex
from pathlib import Path
from typing import Any

from a90_kernel_tools import repo_path
from a90harness.evidence import EvidenceStore, write_private_text

import native_wifi_private_cnss_daemon_sdx50m_live_v1221 as v1221
import native_wifi_pm_dep_early_per_proxy_zero_delay_per_mgr_v1180 as v1180
import native_wifi_pm_dep_post_cnss_per_mgr_wchan_v1210 as v1210_mod
import native_wifi_pm_server_wchan_tracefs_live_v1106 as v1106_mod


DEFAULT_OUT_DIR = Path("tmp/wifi/v1222-post-esoc-power-boundary-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1222-post-esoc-power-boundary-live.txt")
POST_HOLD_SEC = 45
POST_HOLD_INTERVAL_SEC = 1

POST_RE = re.compile(r"^v1222\.post_hold\.(?P<idx>\d+)\.(?P<key>[^=]+)=(?P<value>.*)$")


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _patch_collector_script(original_collector):
    def tracefs_collector_script(args: Any) -> str:
        script = original_collector(args)
        return script.replace(
            r"wifi_companion_qrtr_readback\.|v1106\.)",
            r"wifi_companion_qrtr_readback\.|v1106\.|v1222\.)",
        )

    return tracefs_collector_script


def _write_child_script_v1222(args: Any, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    command = v1106_mod.pm_cnss_child_command(args)
    grep_pattern = (
        r"^(A90_EXECNS_(BEGIN|END|STDOUT_END)|"
        r"private_cnss_daemon\.|"
        r"pm_service_trigger_observer\.|"
        r"wifi_vndservice_query\.|"
        r"wifi_companion_qrtr_readback\.|"
        r"v1222\.)"
    )
    post_hold_script = f"""
post_snapshot() {{
  idx="$1"
  echo "v1222.post_hold.$idx.begin=1"
  state=$($BB cat /sys/bus/msm_subsys/devices/subsys9/state 2>/dev/null || echo error)
  echo "v1222.post_hold.$idx.mdm3_state=$state"
  if $BB test -e /sys/class/net/wlan0; then
    echo "v1222.post_hold.$idx.wlan0_exists=1"
    op=$($BB cat /sys/class/net/wlan0/operstate 2>/dev/null || echo error)
    echo "v1222.post_hold.$idx.wlan0_operstate=$op"
  else
    echo "v1222.post_hold.$idx.wlan0_exists=0"
  fi
  if $BB test -r /proc/net/qrtr; then
    svc69=$($BB grep -Ec '(^|[[:space:]])69([[:space:]]|$)' /proc/net/qrtr 2>/dev/null || true)
    echo "v1222.post_hold.$idx.qrtr_service69_lines=$svc69"
  else
    echo "v1222.post_hold.$idx.qrtr_service69_lines=-1"
  fi
  down=$($BB dmesg | $BB grep -Eic 'Modem went down|crashed: 1|Collecting msa0' 2>/dev/null || true)
  wlfw=$($BB dmesg | $BB grep -Eic 'wlfw|FW ready|BDF|wlan0|qcwlan' 2>/dev/null || true)
  esoc=$($BB dmesg | $BB grep -Eic 'subsystem_get.*esoc0|subsys fw_name to esoc0|mdm_subsys_powerup' 2>/dev/null || true)
  echo "v1222.post_hold.$idx.dmesg_modem_down_count=$down"
  echo "v1222.post_hold.$idx.dmesg_wlfw_count=$wlfw"
  echo "v1222.post_hold.$idx.dmesg_esoc_open_count=$esoc"
  echo "v1222.post_hold.$idx.end=1"
}}
idx=0
while $BB test "$idx" -le {POST_HOLD_SEC}; do
  post_snapshot "$idx"
  idx=$((idx + {POST_HOLD_INTERVAL_SEC}))
  $BB sleep {POST_HOLD_INTERVAL_SEC}
done
"""
    script = "\n".join([
        f"#!{args.busybox} sh",
        f"OUT={shlex.quote(args.child_output)}",
        f"{args.busybox} mkdir -p {shlex.quote(args.work_dir)}",
        " ".join(shlex.quote(part) for part in command) + ' > "$OUT" 2>&1',
        "rc=$?",
        f"{args.busybox} grep -E {shlex.quote(grep_pattern)} \"$OUT\" || true",
        f"echo v1106.child_full_output={shlex.quote(args.child_output)}",
        "echo v1106.child_rc=$rc",
        "BB=" + shlex.quote(args.busybox),
        post_hold_script,
        "exit $rc",
        "",
    ])
    store.write_text("host/pm-cnss-voter-child-script.txt", script)
    v1106_mod.base.run_a90ctl(args, store, steps, "workdir-mkdir", ["run", args.busybox, "mkdir", "-p", args.work_dir], timeout=12.0)
    v1106_mod.append_device_file(args, store, steps, args.child_script, script, "child-script")


def patch_defaults() -> None:
    v1221.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v1221.LATEST_POINTER = LATEST_POINTER
    v1221.patch_defaults()
    v1106_mod.write_child_script = _write_child_script_v1222
    v1106_mod.tracefs_collector_script = _patch_collector_script(
        v1106_mod.tracefs_collector_script
    )


def _read_child_output(manifest: dict[str, Any]) -> str:
    return v1221._read_child_output(manifest)


def _extract_post_hold(text: str) -> list[dict[str, str]]:
    by_index: dict[int, dict[str, str]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = POST_RE.match(line)
        if not match:
            continue
        index = int(match.group("idx"))
        by_index.setdefault(index, {})[match.group("key")] = match.group("value")
    return [by_index[index] | {"index": str(index)} for index in sorted(by_index)]


def _int_value(value: str | None, fallback: int = 0) -> int:
    try:
        return int(value or "")
    except ValueError:
        return fallback


def _analyze_boundary(manifest: dict[str, Any], child_text: str) -> dict[str, Any]:
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    contract = tracefs.get("pm_contract") or {}
    post_hold = _extract_post_hold(child_text)
    states = [entry.get("mdm3_state", "") for entry in post_hold if entry.get("mdm3_state")]
    wlan0_seen = any(entry.get("wlan0_exists") == "1" for entry in post_hold)
    service69_seen = any(_int_value(entry.get("qrtr_service69_lines"), 0) > 0 for entry in post_hold)
    max_wlfw = max((_int_value(entry.get("dmesg_wlfw_count"), 0) for entry in post_hold), default=0)
    max_modem_down = max((_int_value(entry.get("dmesg_modem_down_count"), 0) for entry in post_hold), default=0)
    max_esoc_open = max((_int_value(entry.get("dmesg_esoc_open_count"), 0) for entry in post_hold), default=0)
    syscall_paths = [
        value
        for key, value in contract.items()
        if key.startswith("syscall_probe.after_cnss_daemon.")
        and key.endswith(".path.value")
    ]
    esoc_syscall_seen = "/dev/subsys_esoc0" in syscall_paths
    dmesg_esoc_seen = (
        "__subsystem_get: esoc0" in child_text
        or "Changing subsys fw_name to esoc0" in child_text
    )
    return {
        "post_hold": post_hold,
        "post_hold_count": len(post_hold),
        "mdm3_state_transitions": list(dict.fromkeys(states)),
        "wlan0_seen": wlan0_seen,
        "service69_seen": service69_seen,
        "max_dmesg_wlfw_count": max_wlfw,
        "max_dmesg_modem_down_count": max_modem_down,
        "max_dmesg_esoc_open_count": max_esoc_open,
        "syscall_paths": syscall_paths,
        "esoc_syscall_seen": esoc_syscall_seen,
        "dmesg_esoc_seen": dmesg_esoc_seen,
        "esoc_open_seen": esoc_syscall_seen or dmesg_esoc_seen or max_esoc_open > 0,
    }


def decide_v1222(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if manifest.get("command") == "plan":
        return (
            "v1222-post-esoc-boundary-plan-ready",
            True,
            "plan-only; no tracefs write, daemon start, or Wi-Fi action executed",
            "run V1222 bounded observer after helper/artifact deploy",
        )
    boundary = manifest.get("post_esoc_boundary") or {}
    thread_analysis = manifest.get("thread_analysis") or {}
    if not boundary.get("esoc_open_seen"):
        return (
            "v1222-esoc-open-regression",
            False,
            f"subsys_esoc0 open not observed; syscall_paths={boundary.get('syscall_paths')}",
            "return to V1221 SDX50M registration gate",
        )
    if boundary.get("wlan0_seen"):
        return (
            "v1222-wlan0-up",
            True,
            "wlan0 appeared during post-eSoC boundary hold",
            "V1223: bounded link/DHCP gate; still keep credential handling private",
        )
    if boundary.get("service69_seen") or _int_value(str(boundary.get("max_dmesg_wlfw_count")), 0) > 0:
        return (
            "v1222-wlfw-progress-without-wlan0",
            True,
            f"WLFW/BDF markers or service69 appeared; boundary={boundary}",
            "V1223: extend WLFW-to-wlan0 observer before HAL/connect",
        )
    if _int_value(str(boundary.get("max_dmesg_modem_down_count")), 0) > 0:
        return (
            "v1222-esoc-powerup-crash-before-wlfw",
            True,
            f"eSoC open reached mdm_subsys_powerup but modem-down/crash markers appeared; states={boundary.get('mdm3_state_transitions')}",
            "V1223: classify SDX50M crash source around PM/CNSS lifetime, MHI, and firmware handoff",
        )
    if thread_analysis.get("mdm_subsys_powerup_any"):
        return (
            "v1222-esoc-powerup-stalled-no-crash",
            True,
            f"pm-service stayed in mdm_subsys_powerup; states={boundary.get('mdm3_state_transitions')}",
            "V1223: inspect wait condition and Android parity for mdm2ap status/IRQ/MHI",
        )
    return (
        "v1222-post-esoc-boundary-inconclusive",
        False,
        f"boundary={boundary}",
        "inspect observer output and add a narrower marker",
    )


def main() -> int:
    patch_defaults()
    v1179 = v1180.v1179
    v1177_chain = v1179.v1177
    v1165 = v1177_chain.v1175.v1174.v1173.v1172.v1171.v1170.v1169.v1168.v1167.v1165
    v1106 = v1165.v1143.v1139.v1113.v1106

    args = v1106.parse_args()
    if args.helper_timeout_sec == 4:
        args.helper_timeout_sec = 30
    if args.toybox_timeout_sec == 18:
        args.toybox_timeout_sec = 70
    if args.tracefs_duration_sec == 18:
        args.tracefs_duration_sec = 95
    if args.thread_sample_count == 80:
        args.thread_sample_count = 260
    v1165.v1143.v1139.v1113.set_global_defaults(args)

    store = EvidenceStore(repo_path(DEFAULT_OUT_DIR))
    manifest = v1106.build_manifest(args, store)
    manifest["cycle"] = "v1222"
    manifest["generated_at"] = _now_iso()
    manifest["helper_version"] = v1221.HELPER_MARKER_V253
    manifest["helper_sha256"] = v1221.HELPER_SHA256_V253
    manifest["post_hold_sec"] = POST_HOLD_SEC
    manifest["_run_dir"] = str(store.run_dir)

    child_output_text = _read_child_output(manifest)
    manifest["private_cnss_daemon"] = v1221._parse_prefixed_lines(child_output_text, "private_cnss_daemon.")
    tracefs = (manifest.get("analysis") or {}).get("tracefs_uprobe") or {}
    manifest["thread_analysis"] = v1210_mod._parse_thread_samples(tracefs)
    manifest["post_esoc_boundary"] = _analyze_boundary(manifest, child_output_text)

    decision, passed, reason, next_step = decide_v1222(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "next_step": next_step})

    store.write_json("manifest.json", manifest)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")

    boundary = manifest["post_esoc_boundary"]
    print(f"decision: {decision}")
    print(f"pass:     {passed}")
    print(f"reason:   {reason}")
    print(f"next:     {next_step}")
    print()
    print(f"esoc_open_seen:            {boundary.get('esoc_open_seen')}")
    print(f"mdm3_state_transitions:    {boundary.get('mdm3_state_transitions')}")
    print(f"service69_seen:            {boundary.get('service69_seen')}")
    print(f"wlan0_seen:                {boundary.get('wlan0_seen')}")
    print(f"max_dmesg_modem_down_count:{boundary.get('max_dmesg_modem_down_count')}")
    print(f"max_dmesg_wlfw_count:      {boundary.get('max_dmesg_wlfw_count')}")
    print(f"post_hold_count:           {boundary.get('post_hold_count')}")
    print(f"thread_analysis:           {manifest.get('thread_analysis')}")
    print()
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
