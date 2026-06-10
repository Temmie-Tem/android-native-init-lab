#!/usr/bin/env python3
"""V2176 rollbackable Wi-Fi DHCP/route/ping validation.

This runner is explicit Wi-Fi connectivity scope. It may run DHCP, install
temporary wlan0 route/DNS through native-init `wifi dhcp`, and run one bounded
external ping. It rolls back to the promoted V2174 baseline afterward.
"""

from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import a90_transport as transport
import native_wifi_connect_carrier_handoff_v2174 as v2174
from a90harness.evidence import EvidenceStore, WORKSPACE_PRIVATE_ROOT, workspace_private_input_path


CYCLE = "V2176"
RUN_LABEL = "v2176-wifi-dhcp-ping"
TEST_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v2176_wifi_dhcp.img", legacy_fallback=False)
ROLLBACK_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2174_wifi_urandom_connect.img", legacy_fallback=False
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.252 (v2176-wifi-dhcp)"
ROLLBACK_EXPECT_VERSION = "A90 Linux init 0.9.251 (v2174-wifi-urandom-connect)"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2176_WIFI_DHCP_PING_LIVE_VALIDATION_2026-06-08.md"
)
DEFAULT_PING_TARGET = "google.com"


def rel(path: Path) -> str:
    return v2174.rel(path)


def sha256(path: Path) -> str:
    return v2174.sha256(path)


def run_ping_step(store: EvidenceStore,
                  steps: list[dict[str, Any]],
                  target: str) -> dict[str, Any]:
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
    return v2174.a90ctl_step(
        store,
        steps,
        "test-wifi-external-ping",
        ["run", "/cache/bin/busybox", "sh", "-c", script],
        timeout=60,
        bridge_timeout=45,
    )


def run_dhcp_window(store: EvidenceStore,
                    steps: list[dict[str, Any]],
                    profile_name: str | None,
                    ping_target: str) -> dict[str, Any]:
    dhcp_command = ["wifi", "dhcp"] + ([profile_name] if profile_name else [])
    dhcp = v2174.a90ctl_step(
        store,
        steps,
        "test-wifi-dhcp",
        dhcp_command,
        timeout=120,
        bridge_timeout=90,
    )
    dhcp_text = v2174.step_stdout(store, v2174.find_step(steps, "test-wifi-dhcp"))
    dhcp_fields = v2174.parse_key_values(dhcp_text)
    ping_fields: dict[str, str] = {}
    ping_ok = False
    ping = {}
    if dhcp_fields.get("decision") == "wifi-dhcp-pass":
        ping = run_ping_step(store, steps, ping_target)
        ping_text = v2174.step_stdout(store, v2174.find_step(steps, "test-wifi-external-ping"))
        ping_fields = v2174.parse_key_values(v2174.redact_wifi_evidence(ping_text))
        ping_ok = bool(ping.get("ok")) and ping_fields.get("external_ping_rc") == "0"

    v2174.a90ctl_step(store, steps, "test-wifi-status-after-dhcp", ["wifi", "status"], timeout=90, bridge_timeout=60)
    v2174.a90ctl_step(
        store,
        steps,
        "test-wifi-residual-before-cleanup",
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
                "echo carrier=$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo unreadable)"
            ),
        ],
        timeout=45,
        bridge_timeout=35,
    )
    cleanup = v2174.a90ctl_step(store, steps, "test-wifi-cleanup", ["wifi", "cleanup"], timeout=90, bridge_timeout=60)
    v2174.a90ctl_step(
        store,
        steps,
        "test-wifi-residual-after-cleanup",
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
                "echo carrier=$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo unreadable)"
            ),
        ],
        timeout=45,
        bridge_timeout=35,
    )
    cleanup_text = v2174.step_stdout(store, v2174.find_step(steps, "test-wifi-cleanup"))
    cleanup_fields = v2174.parse_key_values(cleanup_text)
    return {
        "ok": dhcp_fields.get("decision") == "wifi-dhcp-pass" and ping_ok,
        "dhcp_command_ok": bool(dhcp.get("ok")),
        "dhcp_decision": dhcp_fields.get("decision", ""),
        "dhcp_rc": dhcp_fields.get("dhcp_rc", ""),
        "ipv4_assigned": dhcp_fields.get("ipv4_assigned", ""),
        "route_default_present": dhcp_fields.get("route_default_present", ""),
        "resolv_conf_present": dhcp_fields.get("resolv_conf.present", ""),
        "resolv_conf_nameserver_count": dhcp_fields.get("resolv_conf.nameserver_count", ""),
        "secret_values_logged": dhcp_fields.get("secret_values_logged", ""),
        "credentials_logged": dhcp_fields.get("credentials_logged", ""),
        "external_ping_executed": ping_fields.get("external_ping_executed", "0"),
        "external_ping_target": ping_target,
        "external_ping_rc": ping_fields.get("external_ping_rc", ""),
        "external_ping_bytes_from": ping_fields.get("external_ping_output.bytes_from", ""),
        "external_ping_bad_address": ping_fields.get("external_ping_output.bad_address", ""),
        "external_ping_network_unreachable": ping_fields.get("external_ping_output.network_unreachable", ""),
        "external_ping_packet_loss_100": ping_fields.get("external_ping_output.packet_loss_100", ""),
        "cleanup_ok": bool(cleanup.get("ok")) and cleanup_fields.get("decision") == "wifi-cleanup-done",
        "cleanup_decision": cleanup_fields.get("decision", ""),
    }


def flash_command(image: Path, expect_version: str, *, from_native: bool) -> list[object]:
    return v2174.flash_command(image, expect_version, from_native=from_native)


def rollback(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    first = v2174.run_command(flash_command(ROLLBACK_IMAGE, ROLLBACK_EXPECT_VERSION, from_native=True), timeout=720)
    v2174.write_step(store, steps, "rollback-v2174-from-native", first)
    ok = bool(first.get("ok"))
    attempt = "from-native"
    if not ok:
        second = v2174.run_command(flash_command(ROLLBACK_IMAGE, ROLLBACK_EXPECT_VERSION, from_native=False), timeout=720)
        v2174.write_step(store, steps, "rollback-v2174-from-recovery", second)
        ok = bool(second.get("ok"))
        attempt = "from-recovery"
    final_status = v2174.a90ctl_step(store, steps, "rollback-v2174-status", ["status"], timeout=90, bridge_timeout=60)
    final_selftest = v2174.a90ctl_step(store, steps, "rollback-v2174-selftest", ["selftest"], timeout=90, bridge_timeout=60)
    return {
        "ok": ok,
        "attempt": attempt,
        "status_ok": bool(final_status.get("ok")),
        "selftest_ok": bool(final_selftest.get("ok")) and "fail=0" in str(final_selftest.get("stdout") or ""),
    }


def classify(manifest: dict[str, Any]) -> dict[str, Any]:
    if not manifest["preflight"]["test_image_exists"] or not manifest["preflight"]["rollback_image_exists"]:
        return {"decision": "v2176-dhcp-preflight-image-missing", "pass": False, "reason": "test or rollback image missing"}
    if not (manifest.get("wifi_secret_status") or {}).get("valid"):
        return {"decision": "v2176-dhcp-preflight-wifi-env-missing-no-flash", "pass": False, "reason": "Wi-Fi env missing or invalid"}
    if not (manifest.get("transport_selection") or {}).get("status_ok"):
        return {"decision": "v2176-dhcp-preflight-native-unavailable-no-flash", "pass": False, "reason": "native status preflight failed"}
    if not manifest.get("test_flash_ok"):
        return {"decision": "v2176-dhcp-test-flash-failed", "pass": False, "reason": "test boot flash failed"}
    rollback_result = manifest.get("rollback") or {}
    if not rollback_result.get("ok") or rollback_result.get("selftest_ok") is not True:
        return {"decision": "v2176-dhcp-rollback-selftest-failed", "pass": False, "reason": "rollback did not end with selftest fail=0"}
    connect = manifest.get("connect") or {}
    dhcp = manifest.get("dhcp_ping") or {}
    safety_ok = (
        connect.get("secret_values_logged") == "0"
        and connect.get("credentials_logged") == "0"
        and dhcp.get("secret_values_logged") == "0"
        and dhcp.get("credentials_logged") == "0"
    )
    if connect.get("ok") and dhcp.get("ok") and dhcp.get("cleanup_ok") and safety_ok:
        return {"decision": "v2176-dhcp-ping-rollback-pass", "pass": True, "reason": "carrier, DHCP, bounded ping, cleanup, and rollback selftest passed"}
    return {"decision": "v2176-dhcp-ping-failed-rollback-pass", "pass": False, "reason": "connect, DHCP, ping, cleanup, or safety field failed"}


def render_report(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    connect = manifest.get("connect") or {}
    dhcp = manifest.get("dhcp_ping") or {}
    rollback_result = manifest.get("rollback") or {}
    phase_lines = [
        f"- `{item['name']}`: `{item['elapsed_sec']}` sec"
        for item in manifest.get("phase_timers", [])
    ]
    return "\n".join([
        "# Native Init V2176 Wi-Fi DHCP Ping Live Validation",
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
        "## Connectivity Scope",
        "",
        "- Commands: `wifi connect [profile]`, `wifi dhcp [profile]`, one bounded ping, `wifi cleanup`.",
        "- DHCP may install temporary wlan0 route/DNS. External ping is runner/test scope.",
        "- Raw SSID, PSK, BSSID, MAC, assigned IP, route, DNS, DHCP lease, and ping transcript are not written to this public report.",
        f"- Connect decision: `{connect.get('decision', '')}` carrier `{connect.get('carrier_up', '')}` WPA `{connect.get('wpa_state', '')}`.",
        f"- DHCP decision: `{dhcp.get('dhcp_decision', '')}` rc `{dhcp.get('dhcp_rc', '')}` IPv4 assigned `{dhcp.get('ipv4_assigned', '')}` default route `{dhcp.get('route_default_present', '')}` nameservers `{dhcp.get('resolv_conf_nameserver_count', '')}`.",
        f"- Ping target: `{dhcp.get('external_ping_target', '')}` rc `{dhcp.get('external_ping_rc', '')}` bytes_from `{dhcp.get('external_ping_bytes_from', '')}`.",
        f"- Cleanup: `{dhcp.get('cleanup_decision', '')}` ok `{dhcp.get('cleanup_ok', False)}`.",
        f"- Secret values logged: connect `{connect.get('secret_values_logged', '')}` dhcp `{dhcp.get('secret_values_logged', '')}`.",
        "",
        "## Phase Timers",
        "",
        *(phase_lines if phase_lines else ["- `none`: `0` sec"]),
        "",
        "## Rollback",
        "",
        f"- Rollback OK: `{rollback_result.get('ok', False)}`",
        f"- Rollback attempt: `{rollback_result.get('attempt', '')}`",
        f"- Rollback selftest fail=0: `{rollback_result.get('selftest_ok', False)}`",
        "",
    ])


def run(profile_name: str | None = None, ping_target: str = DEFAULT_PING_TARGET) -> dict[str, Any]:
    out_dir = WORKSPACE_PRIVATE_ROOT / "runs" / "wifi" / f"{RUN_LABEL}-{v2174.timestamp_label()}"
    store = EvidenceStore(out_dir)
    steps: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {
        "cycle": CYCLE,
        "run_label": RUN_LABEL,
        "out_dir": rel(out_dir),
        "phase_timer_contract": transport.PHASE_TIMER_CONTRACT,
        "phase_timers": [],
    }
    env_load = v2174.load_wifi_env()
    secret_status = v2174.wifi_secret_status(profile_name)
    preflight = {
        "cycle": CYCLE,
        "run_label": RUN_LABEL,
        "test_image": rel(TEST_IMAGE),
        "test_image_exists": TEST_IMAGE.exists(),
        "test_image_sha256": sha256(TEST_IMAGE) if TEST_IMAGE.exists() else "",
        "rollback_image": rel(ROLLBACK_IMAGE),
        "rollback_image_exists": ROLLBACK_IMAGE.exists(),
        "rollback_image_sha256": sha256(ROLLBACK_IMAGE) if ROLLBACK_IMAGE.exists() else "",
        "profile_source": "explicit" if profile_name else "default",
        "credential_values_logged": False,
        "env_load": env_load,
        "ping_target": ping_target,
    }
    store.write_json("preflight.json", preflight)
    manifest["preflight"] = preflight
    manifest["wifi_secret_status"] = secret_status

    with transport.phase(manifest, "preflight"):
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
    connect_result: dict[str, Any] = {}
    dhcp_result: dict[str, Any] = {}
    rollback_result: dict[str, Any] = {"ok": True, "attempt": "not-needed", "selftest_ok": "not-tested"}
    if preflight["test_image_exists"] and preflight["rollback_image_exists"] and secret_status.get("valid") and transport_selection.get("status_ok"):
        with transport.phase(manifest, "flash"):
            test_flash = v2174.run_command(flash_command(TEST_IMAGE, TEST_EXPECT_VERSION, from_native=True), timeout=720)
            v2174.write_step(store, steps, "test-flash-v2176-from-native", test_flash)
            test_flash_ok = bool(test_flash.get("ok"))
        if test_flash_ok:
            with transport.phase(manifest, "connect_window"):
                connect_result = v2174.run_connect_window(store, steps, profile_name)
            if connect_result.get("ok"):
                with transport.phase(manifest, "dhcp_ping_window"):
                    dhcp_result = run_dhcp_window(store, steps, profile_name, ping_target)
        with transport.phase(manifest, "rollback"):
            rollback_result = rollback(store, steps)
        with transport.phase(manifest, "selftest"):
            final_selftest = v2174.a90ctl_step(store, steps, "post-rollback-selftest", ["selftest"], timeout=90, bridge_timeout=60)
            rollback_result["post_selftest_ok"] = bool(final_selftest.get("ok")) and "fail=0" in str(final_selftest.get("stdout") or "")

    with transport.phase(manifest, "artifact_upload"):
        pass

    manifest["test_flash_ok"] = test_flash_ok
    manifest["connect"] = connect_result
    manifest["dhcp_ping"] = dhcp_result
    manifest["rollback"] = rollback_result
    manifest["steps"] = steps
    classification = classify(manifest)
    manifest["classification"] = classification
    manifest["decision"] = classification["decision"]
    manifest["pass"] = classification["pass"]
    manifest["reason"] = classification["reason"]
    transport.set_residual_state(manifest, {
        "connect_ok": bool(connect_result.get("ok")),
        "dhcp_ping_ok": bool(dhcp_result.get("ok")),
        "cleanup_ok": bool(dhcp_result.get("cleanup_ok")),
        "cleanup_decision": dhcp_result.get("cleanup_decision", ""),
        "rollback_ok": bool(rollback_result.get("ok")),
        "rollback_attempt": rollback_result.get("attempt", ""),
        "rollback_selftest_ok": bool(rollback_result.get("selftest_ok")),
        "cleanup_required": not (
            bool(dhcp_result.get("cleanup_ok")) and bool(rollback_result.get("selftest_ok"))
        ),
    })
    store.write_json("manifest.json", manifest)
    summary = render_report(manifest)
    store.write_text("summary.md", summary)
    REPORT_PATH.write_text(summary, encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile")
    parser.add_argument("--ping-target", default=DEFAULT_PING_TARGET)
    args = parser.parse_args()
    manifest = run(profile_name=args.profile, ping_target=args.ping_target)
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "reason": manifest["reason"],
        "out_dir": manifest["out_dir"],
        "transport_selected": (manifest.get("transport_selection") or {}).get("selected", ""),
        "wifi_env_valid": (manifest.get("wifi_secret_status") or {}).get("valid", False),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
