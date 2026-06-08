#!/usr/bin/env python3
"""V2177 rollbackable Wi-Fi hold/idle and reconnect validation.

This runner reuses the V2176 test boot image. It validates the remaining
stability gate after basic V2176 N=3: hold an associated/DHCP link for a bounded
window, cleanly disconnect through `wifi cleanup`, reconnect, reacquire DHCP,
run one bounded ping, clean up again, and roll back to V2174.
"""

from __future__ import annotations

import argparse
import json
import shlex
import time
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import a90_transport as transport
import native_wifi_connect_carrier_handoff_v2174 as v2174
import native_wifi_dhcp_ping_handoff_v2176 as v2176
from a90harness.evidence import EvidenceStore, WORKSPACE_PRIVATE_ROOT


CYCLE = "V2177"
RUN_LABEL = "v2177-wifi-hold-reconnect"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2177_WIFI_HOLD_RECONNECT_LIVE_VALIDATION_2026-06-09.md"
)
DEFAULT_HOLD_SEC = 180
DEFAULT_HOLD_INTERVAL_SEC = 30
DEFAULT_PING_TARGET = "google.com"


def phase_timer(manifest: dict[str, Any], name: str):
    return v2176.phase_timer(manifest, name)


def rel(path: Path) -> str:
    return v2174.rel(path)


def step_fields(store: EvidenceStore, steps: list[dict[str, Any]], name: str) -> dict[str, str]:
    return v2174.parse_key_values(v2174.step_stdout(store, v2174.find_step(steps, name)))


def serial_step(store: EvidenceStore,
                steps: list[dict[str, Any]],
                name: str,
                command: list[str],
                *,
                timeout: float = 90.0,
                bridge_timeout: float = 60.0) -> dict[str, Any]:
    return v2174.a90ctl_step(
        store,
        steps,
        name,
        command,
        timeout=timeout,
        bridge_timeout=bridge_timeout,
    )


def run_connect_phase(store: EvidenceStore,
                      steps: list[dict[str, Any]],
                      *,
                      prefix: str,
                      profile_name: str | None) -> dict[str, Any]:
    substore = EvidenceStore(store.run_dir / prefix)
    substeps: list[dict[str, Any]] = []
    result = v2174.run_connect_window(substore, substeps, profile_name)
    substore.write_json("connect-result.json", {
        "result": result,
        "steps": substeps,
    })
    result["evidence_dir"] = prefix
    v2174.write_step(
        store,
        steps,
        f"{prefix}-connect-result",
        v2174.synthetic_step_result(
            ["wifi-connect-phase", prefix],
            ok=bool(result.get("ok")),
            stdout=json.dumps({
                "decision": result.get("decision", ""),
                "carrier_up": result.get("carrier_up", ""),
                "wpa_state": result.get("wpa_state", ""),
                "secret_values_logged": result.get("secret_values_logged", ""),
                "credentials_logged": result.get("credentials_logged", ""),
                "evidence_dir": prefix,
            }, ensure_ascii=False, sort_keys=True) + "\n",
        ),
    )
    return result


def run_ping_step(store: EvidenceStore,
                  steps: list[dict[str, Any]],
                  *,
                  name: str,
                  target: str) -> dict[str, str]:
    target_q = shlex.quote(target)
    script = (
        "LOG=/cache/a90-wifi/ping-test.log; "
        "rm -f \"$LOG\"; "
        f"/cache/bin/busybox ping -c 1 -W 5 {target_q} >\"$LOG\" 2>&1; "
        "rc=$?; "
        "echo external_ping_executed=1; "
        f"echo external_ping_target={target_q}; "
        "echo external_ping_rc=$rc; "
        "echo external_ping_output.present=$([ -s \"$LOG\" ] && echo 1 || echo 0); "
        "echo external_ping_output.bytes_from=$(grep -Eci 'bytes from|bytes from' \"$LOG\" 2>/dev/null || true); "
        "echo external_ping_output.bad_address=$(grep -Eci 'bad address|unknown host' \"$LOG\" 2>/dev/null || true); "
        "echo external_ping_output.network_unreachable=$(grep -Eci 'network is unreachable|unreachable' \"$LOG\" 2>/dev/null || true); "
        "echo external_ping_output.packet_loss_100=$(grep -Eci '100% packet loss' \"$LOG\" 2>/dev/null || true); "
        "exit $rc"
    )
    result = serial_step(
        store,
        steps,
        name,
        ["run", "/cache/bin/busybox", "sh", "-c", script],
        timeout=60,
        bridge_timeout=45,
    )
    text = v2174.step_stdout(store, v2174.find_step(steps, name))
    fields = v2174.parse_key_values(v2174.redact_wifi_evidence(text))
    fields["command_ok"] = "1" if result.get("ok") else "0"
    return fields


def run_dhcp_ping_no_cleanup(store: EvidenceStore,
                             steps: list[dict[str, Any]],
                             *,
                             prefix: str,
                             profile_name: str | None,
                             ping_target: str) -> dict[str, Any]:
    dhcp_name = f"{prefix}-wifi-dhcp"
    dhcp_command = ["wifi", "dhcp"] + ([profile_name] if profile_name else [])
    dhcp_result = serial_step(store, steps, dhcp_name, dhcp_command, timeout=120, bridge_timeout=90)
    dhcp_fields = step_fields(store, steps, dhcp_name)
    ping_fields: dict[str, str] = {}
    ping_ok = False
    if dhcp_fields.get("decision") == "wifi-dhcp-pass":
        ping_fields = run_ping_step(
            store,
            steps,
            name=f"{prefix}-external-ping",
            target=ping_target,
        )
        ping_ok = ping_fields.get("external_ping_rc") == "0"

    serial_step(store, steps, f"{prefix}-wifi-status-after-dhcp", ["wifi", "status"], timeout=90, bridge_timeout=60)
    serial_step(
        store,
        steps,
        f"{prefix}-residual-before-cleanup",
        [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            (
                "echo residual.before=1; "
                "echo supplicant_count=$(ps | grep -c '[w]pa_supplicant' 2>/dev/null || true); "
                "echo udhcpc_pidfile=$([ -s /cache/a90-wifi/udhcpc-wlan0.pid ] && echo 1 || echo 0); "
                "echo resolv_conf=$([ -s /cache/a90-wifi/resolv.conf ] && echo 1 || echo 0); "
                "echo carrier=$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo unreadable); "
                "echo route_default_present=$(awk '$1==\"wlan0\" && $2==\"00000000\" {f=1} END {print f+0}' /proc/net/route 2>/dev/null)"
            ),
        ],
        timeout=45,
        bridge_timeout=35,
    )
    return {
        "ok": dhcp_fields.get("decision") == "wifi-dhcp-pass" and ping_ok,
        "dhcp_command_ok": bool(dhcp_result.get("ok")),
        "dhcp_decision": dhcp_fields.get("decision", ""),
        "dhcp_rc": dhcp_fields.get("dhcp_rc", ""),
        "ipv4_assigned": dhcp_fields.get("ipv4_assigned", ""),
        "route_default_present": dhcp_fields.get("route_default_present", ""),
        "resolv_conf_present": dhcp_fields.get("resolv_conf.present", ""),
        "resolv_conf_nameserver_count": dhcp_fields.get("resolv_conf.nameserver_count", ""),
        "secret_values_logged": dhcp_fields.get("secret_values_logged", ""),
        "credentials_logged": dhcp_fields.get("credentials_logged", ""),
        "external_ping_rc": ping_fields.get("external_ping_rc", ""),
        "external_ping_bytes_from": ping_fields.get("external_ping_output.bytes_from", ""),
        "external_ping_bad_address": ping_fields.get("external_ping_output.bad_address", ""),
    }


def run_cleanup_check(store: EvidenceStore,
                      steps: list[dict[str, Any]],
                      *,
                      prefix: str) -> dict[str, Any]:
    cleanup_name = f"{prefix}-wifi-cleanup"
    cleanup_result = serial_step(store, steps, cleanup_name, ["wifi", "cleanup"], timeout=90, bridge_timeout=60)
    cleanup_fields = step_fields(store, steps, cleanup_name)
    residual_name = f"{prefix}-residual-after-cleanup"
    serial_step(
        store,
        steps,
        residual_name,
        [
            "run",
            "/cache/bin/busybox",
            "sh",
            "-c",
            (
                "echo residual.after=1; "
                "echo supplicant_count=$(ps | grep -c '[w]pa_supplicant' 2>/dev/null || true); "
                "echo udhcpc_pidfile=$([ -s /cache/a90-wifi/udhcpc-wlan0.pid ] && echo 1 || echo 0); "
                "echo resolv_conf=$([ -s /cache/a90-wifi/resolv.conf ] && echo 1 || echo 0); "
                "echo carrier=$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo unreadable); "
                "echo route_default_present=$(awk '$1==\"wlan0\" && $2==\"00000000\" {f=1} END {print f+0}' /proc/net/route 2>/dev/null)"
            ),
        ],
        timeout=45,
        bridge_timeout=35,
    )
    residual_fields = step_fields(store, steps, residual_name)
    residue_clean = (
        residual_fields.get("supplicant_count") == "0"
        and residual_fields.get("udhcpc_pidfile") == "0"
        and residual_fields.get("resolv_conf") == "0"
    )
    return {
        "ok": bool(cleanup_result.get("ok")) and cleanup_fields.get("decision") == "wifi-cleanup-done" and residue_clean,
        "cleanup_command_ok": bool(cleanup_result.get("ok")),
        "cleanup_decision": cleanup_fields.get("decision", ""),
        "residue_clean": residue_clean,
        "supplicant_count": residual_fields.get("supplicant_count", ""),
        "udhcpc_pidfile": residual_fields.get("udhcpc_pidfile", ""),
        "resolv_conf": residual_fields.get("resolv_conf", ""),
        "carrier": residual_fields.get("carrier", ""),
        "route_default_present": residual_fields.get("route_default_present", ""),
    }


def hold_sample_command() -> list[str]:
    return [
        "run",
        "/cache/bin/busybox",
        "sh",
        "-c",
        (
            "echo hold.sample=1; "
            "echo carrier=$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo unreadable); "
            "echo operstate=$(cat /sys/class/net/wlan0/operstate 2>/dev/null || echo unreadable); "
            "echo supplicant_count=$(ps | grep -c '[w]pa_supplicant' 2>/dev/null || true); "
            "echo udhcpc_pidfile=$([ -s /cache/a90-wifi/udhcpc-wlan0.pid ] && echo 1 || echo 0); "
            "echo resolv_conf=$([ -s /cache/a90-wifi/resolv.conf ] && echo 1 || echo 0); "
            "echo route_default_present=$(awk '$1==\"wlan0\" && $2==\"00000000\" {f=1} END {print f+0}' /proc/net/route 2>/dev/null)"
        ),
    ]


def run_hold_idle(store: EvidenceStore,
                  steps: list[dict[str, Any]],
                  *,
                  hold_sec: int,
                  interval_sec: int,
                  ping_target: str) -> dict[str, Any]:
    samples: list[dict[str, str]] = []
    started = time.monotonic()
    sample_index = 0
    while True:
        elapsed = time.monotonic() - started
        if elapsed >= hold_sec:
            break
        time.sleep(min(interval_sec, max(0.0, hold_sec - elapsed)))
        sample_index += 1
        sample_name = f"hold-idle-sample-{sample_index}"
        serial_step(store, steps, sample_name, hold_sample_command(), timeout=45, bridge_timeout=35)
        fields = step_fields(store, steps, sample_name)
        samples.append(fields)

    ping_fields = run_ping_step(store, steps, name="hold-final-external-ping", target=ping_target)
    sample_ok = bool(samples) and all(
        item.get("carrier") == "1"
        and item.get("route_default_present") == "1"
        and item.get("resolv_conf") == "1"
        for item in samples
    )
    ping_ok = ping_fields.get("external_ping_rc") == "0"
    return {
        "ok": sample_ok and ping_ok,
        "hold_sec": hold_sec,
        "interval_sec": interval_sec,
        "samples": len(samples),
        "sample_ok": sample_ok,
        "final_ping_rc": ping_fields.get("external_ping_rc", ""),
        "final_ping_bytes_from": ping_fields.get("external_ping_output.bytes_from", ""),
        "carrier_values": [item.get("carrier", "") for item in samples],
        "operstate_values": [item.get("operstate", "") for item in samples],
        "route_values": [item.get("route_default_present", "") for item in samples],
        "resolv_conf_values": [item.get("resolv_conf", "") for item in samples],
        "supplicant_count_values": [item.get("supplicant_count", "") for item in samples],
        "udhcpc_pidfile_values": [item.get("udhcpc_pidfile", "") for item in samples],
    }


def classify(manifest: dict[str, Any]) -> dict[str, Any]:
    if not manifest["preflight"]["test_image_exists"] or not manifest["preflight"]["rollback_image_exists"]:
        return {"decision": "v2177-hold-reconnect-preflight-image-missing", "pass": False, "reason": "test or rollback image missing"}
    if not (manifest.get("wifi_secret_status") or {}).get("valid"):
        return {"decision": "v2177-hold-reconnect-wifi-env-missing-no-flash", "pass": False, "reason": "Wi-Fi env missing or invalid"}
    if not (manifest.get("transport_selection") or {}).get("status_ok"):
        return {"decision": "v2177-hold-reconnect-native-unavailable-no-flash", "pass": False, "reason": "native status preflight failed"}
    if not manifest.get("test_flash_ok"):
        return {"decision": "v2177-hold-reconnect-test-flash-failed", "pass": False, "reason": "test boot flash failed"}
    rollback_result = manifest.get("rollback") or {}
    if not rollback_result.get("ok") or rollback_result.get("selftest_ok") is not True:
        return {"decision": "v2177-hold-reconnect-rollback-selftest-failed", "pass": False, "reason": "rollback did not end with selftest fail=0"}
    initial = manifest.get("initial") or {}
    reconnect = manifest.get("reconnect") or {}
    safety_ok = all(
        item.get("secret_values_logged") == "0" and item.get("credentials_logged") == "0"
        for item in (initial.get("connect", {}), initial.get("dhcp_ping", {}), reconnect.get("connect", {}), reconnect.get("dhcp_ping", {}))
    )
    if (
        initial.get("connect", {}).get("ok")
        and initial.get("dhcp_ping", {}).get("ok")
        and manifest.get("hold", {}).get("ok")
        and manifest.get("disconnect", {}).get("ok")
        and reconnect.get("connect", {}).get("ok")
        and reconnect.get("dhcp_ping", {}).get("ok")
        and reconnect.get("cleanup", {}).get("ok")
        and safety_ok
    ):
        return {
            "decision": "v2177-hold-reconnect-rollback-pass",
            "pass": True,
            "reason": "V2176 Wi-Fi held through the bounded idle window, reconnected after cleanup, and rolled back cleanly",
        }
    return {
        "decision": "v2177-hold-reconnect-failed-rollback-pass",
        "pass": False,
        "reason": "hold, reconnect, cleanup, or safety field failed",
    }


def render_report(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    initial = manifest.get("initial") or {}
    reconnect = manifest.get("reconnect") or {}
    hold = manifest.get("hold") or {}
    disconnect = manifest.get("disconnect") or {}
    rollback = manifest.get("rollback") or {}
    phase_lines = [
        f"- `{item['name']}`: `{item['elapsed_sec']}` sec"
        for item in manifest.get("phase_timers", [])
    ]
    return "\n".join([
        "# Native Init V2177 Wi-Fi Hold Reconnect Live Validation",
        "",
        "## Summary",
        "",
        f"- Decision: `{classification['decision']}`",
        f"- Pass: `{classification['pass']}`",
        f"- Reason: {classification['reason']}",
        f"- Run dir: `{manifest['out_dir']}`",
        f"- Test image: `{manifest['preflight']['test_image']}`",
        f"- Test SHA256: `{manifest['preflight']['test_image_sha256']}`",
        f"- Rollback image: `{manifest['preflight']['rollback_image']}`",
        f"- Rollback SHA256: `{manifest['preflight']['rollback_image_sha256']}`",
        "",
        "## Scope",
        "",
        "- Commands: `wifi connect`, `wifi dhcp`, bounded hold/idle sampling, one bounded ping, `wifi cleanup`, reconnect, DHCP, one bounded ping, final cleanup.",
        "- Raw SSID, PSK, BSSID, MAC, assigned IP, route, DNS, DHCP lease, and ping transcript are not written to this public report.",
        f"- Hold window: `{hold.get('hold_sec', '')}` sec; samples `{hold.get('samples', '')}`; sample OK `{hold.get('sample_ok', False)}`; final ping rc `{hold.get('final_ping_rc', '')}`.",
        f"- Hold gating values: carrier `{hold.get('carrier_values', [])}` route `{hold.get('route_values', [])}` resolv `{hold.get('resolv_conf_values', [])}`.",
        f"- Hold observed non-gating values: operstate `{hold.get('operstate_values', [])}` supplicant_count `{hold.get('supplicant_count_values', [])}` udhcpc_pidfile `{hold.get('udhcpc_pidfile_values', [])}`.",
        f"- Initial connect: `{(initial.get('connect') or {}).get('decision', '')}` carrier `{(initial.get('connect') or {}).get('carrier_up', '')}` WPA `{(initial.get('connect') or {}).get('wpa_state', '')}`.",
        f"- Initial DHCP: `{(initial.get('dhcp_ping') or {}).get('dhcp_decision', '')}` ping rc `{(initial.get('dhcp_ping') or {}).get('external_ping_rc', '')}`.",
        f"- Disconnect cleanup: `{disconnect.get('cleanup_decision', '')}` residue clean `{disconnect.get('residue_clean', False)}`.",
        f"- Reconnect: `{(reconnect.get('connect') or {}).get('decision', '')}` carrier `{(reconnect.get('connect') or {}).get('carrier_up', '')}` WPA `{(reconnect.get('connect') or {}).get('wpa_state', '')}`.",
        f"- Reconnect DHCP: `{(reconnect.get('dhcp_ping') or {}).get('dhcp_decision', '')}` ping rc `{(reconnect.get('dhcp_ping') or {}).get('external_ping_rc', '')}`.",
        f"- Final cleanup: `{(reconnect.get('cleanup') or {}).get('cleanup_decision', '')}` residue clean `{(reconnect.get('cleanup') or {}).get('residue_clean', False)}`.",
        f"- Secret values logged: initial connect `{(initial.get('connect') or {}).get('secret_values_logged', '')}` initial DHCP `{(initial.get('dhcp_ping') or {}).get('secret_values_logged', '')}` reconnect connect `{(reconnect.get('connect') or {}).get('secret_values_logged', '')}` reconnect DHCP `{(reconnect.get('dhcp_ping') or {}).get('secret_values_logged', '')}`.",
        "",
        "## Phase Timers",
        "",
        *(phase_lines if phase_lines else ["- `none`: `0` sec"]),
        "",
        "## Rollback",
        "",
        f"- Rollback OK: `{rollback.get('ok', False)}`",
        f"- Rollback attempt: `{rollback.get('attempt', '')}`",
        f"- Rollback selftest fail=0: `{rollback.get('selftest_ok', False)}`",
        "",
    ])


def run(profile_name: str | None = None,
        ping_target: str = DEFAULT_PING_TARGET,
        hold_sec: int = DEFAULT_HOLD_SEC,
        hold_interval_sec: int = DEFAULT_HOLD_INTERVAL_SEC) -> dict[str, Any]:
    out_dir = WORKSPACE_PRIVATE_ROOT / "runs" / "wifi" / f"{RUN_LABEL}-{v2174.timestamp_label()}"
    store = EvidenceStore(out_dir)
    steps: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {
        "cycle": CYCLE,
        "run_label": RUN_LABEL,
        "out_dir": rel(out_dir),
        "phase_timers": [],
    }
    env_load = v2174.load_wifi_env()
    secret_status = v2174.wifi_secret_status(profile_name)
    preflight = {
        "cycle": CYCLE,
        "run_label": RUN_LABEL,
        "test_image": rel(v2176.TEST_IMAGE),
        "test_image_exists": v2176.TEST_IMAGE.exists(),
        "test_image_sha256": v2176.sha256(v2176.TEST_IMAGE) if v2176.TEST_IMAGE.exists() else "",
        "rollback_image": rel(v2176.ROLLBACK_IMAGE),
        "rollback_image_exists": v2176.ROLLBACK_IMAGE.exists(),
        "rollback_image_sha256": v2176.sha256(v2176.ROLLBACK_IMAGE) if v2176.ROLLBACK_IMAGE.exists() else "",
        "profile_source": "explicit" if profile_name else "default",
        "credential_values_logged": False,
        "env_load": env_load,
        "ping_target": ping_target,
        "hold_sec": hold_sec,
        "hold_interval_sec": hold_interval_sec,
    }
    store.write_json("preflight.json", preflight)
    manifest["preflight"] = preflight
    manifest["wifi_secret_status"] = secret_status

    with phase_timer(manifest, "preflight_transport"):
        transport_selection = transport.select_transport(store, steps, ensure=True, prefer_fast=True)
    manifest["transport_selection"] = {
        "selector_contract": transport_selection.get("selector_contract"),
        "transport_contract": transport_selection.get("transport_contract"),
        "selected": transport_selection.get("selected"),
        "fallback_reason": transport_selection.get("fallback_reason"),
        "status_ok": transport_selection.get("status_ok"),
        "ncm_host": transport_selection.get("ncm_host"),
        "tcpctl": transport_selection.get("tcpctl"),
    }

    test_flash_ok = False
    initial_connect: dict[str, Any] = {}
    initial_dhcp: dict[str, Any] = {}
    hold_result: dict[str, Any] = {}
    disconnect: dict[str, Any] = {}
    reconnect_connect: dict[str, Any] = {}
    reconnect_dhcp: dict[str, Any] = {}
    reconnect_cleanup: dict[str, Any] = {}
    rollback_result: dict[str, Any] = {"ok": True, "attempt": "not-needed", "selftest_ok": "not-tested"}

    if preflight["test_image_exists"] and preflight["rollback_image_exists"] and secret_status.get("valid") and transport_selection.get("status_ok"):
        with phase_timer(manifest, "flash_boot_wait"):
            test_flash = v2174.run_command(v2176.flash_command(v2176.TEST_IMAGE, v2176.TEST_EXPECT_VERSION, from_native=True), timeout=720)
            v2174.write_step(store, steps, "test-flash-v2176-from-native", test_flash)
            test_flash_ok = bool(test_flash.get("ok"))
        if test_flash_ok:
            with phase_timer(manifest, "initial_connect_window"):
                initial_connect = run_connect_phase(
                    store,
                    steps,
                    prefix="initial-connect",
                    profile_name=profile_name,
                )
            if initial_connect.get("ok"):
                with phase_timer(manifest, "initial_dhcp_ping_window"):
                    initial_dhcp = run_dhcp_ping_no_cleanup(
                        store,
                        steps,
                        prefix="initial",
                        profile_name=profile_name,
                        ping_target=ping_target,
                    )
            if initial_dhcp.get("ok"):
                with phase_timer(manifest, "hold_idle_window"):
                    hold_result = run_hold_idle(
                        store,
                        steps,
                        hold_sec=hold_sec,
                        interval_sec=hold_interval_sec,
                        ping_target=ping_target,
                    )
            with phase_timer(manifest, "disconnect_cleanup_window"):
                disconnect = run_cleanup_check(store, steps, prefix="disconnect")
            if disconnect.get("ok"):
                with phase_timer(manifest, "reconnect_window"):
                    reconnect_connect = run_connect_phase(
                        store,
                        steps,
                        prefix="reconnect-connect",
                        profile_name=profile_name,
                    )
                if reconnect_connect.get("ok"):
                    with phase_timer(manifest, "reconnect_dhcp_ping_window"):
                        reconnect_dhcp = run_dhcp_ping_no_cleanup(
                            store,
                            steps,
                            prefix="reconnect",
                            profile_name=profile_name,
                            ping_target=ping_target,
                        )
                with phase_timer(manifest, "final_cleanup_window"):
                    reconnect_cleanup = run_cleanup_check(store, steps, prefix="final")
        with phase_timer(manifest, "rollback"):
            rollback_result = v2176.rollback(store, steps)
        with phase_timer(manifest, "selftest"):
            final_selftest = serial_step(store, steps, "post-rollback-selftest", ["selftest"], timeout=90, bridge_timeout=60)
            rollback_result["post_selftest_ok"] = bool(final_selftest.get("ok")) and "fail=0" in str(final_selftest.get("stdout") or "")

    with phase_timer(manifest, "artifact_upload"):
        pass

    manifest["test_flash_ok"] = test_flash_ok
    manifest["initial"] = {"connect": initial_connect, "dhcp_ping": initial_dhcp}
    manifest["hold"] = hold_result
    manifest["disconnect"] = disconnect
    manifest["reconnect"] = {
        "connect": reconnect_connect,
        "dhcp_ping": reconnect_dhcp,
        "cleanup": reconnect_cleanup,
    }
    manifest["rollback"] = rollback_result
    manifest["steps"] = steps
    classification = classify(manifest)
    manifest["classification"] = classification
    manifest["decision"] = classification["decision"]
    manifest["pass"] = classification["pass"]
    manifest["reason"] = classification["reason"]
    store.write_json("manifest.json", manifest)
    summary = render_report(manifest)
    store.write_text("summary.md", summary)
    REPORT_PATH.write_text(summary, encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile")
    parser.add_argument("--ping-target", default=DEFAULT_PING_TARGET)
    parser.add_argument("--hold-sec", type=int, default=DEFAULT_HOLD_SEC)
    parser.add_argument("--hold-interval-sec", type=int, default=DEFAULT_HOLD_INTERVAL_SEC)
    args = parser.parse_args()
    manifest = run(
        profile_name=args.profile,
        ping_target=args.ping_target,
        hold_sec=max(30, args.hold_sec),
        hold_interval_sec=max(10, args.hold_interval_sec),
    )
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "reason": manifest["reason"],
        "out_dir": manifest["out_dir"],
        "transport_selected": (manifest.get("transport_selection") or {}).get("selected", ""),
        "wifi_env_valid": (manifest.get("wifi_secret_status") or {}).get("valid", False),
        "hold_sec": (manifest.get("hold") or {}).get("hold_sec", ""),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
