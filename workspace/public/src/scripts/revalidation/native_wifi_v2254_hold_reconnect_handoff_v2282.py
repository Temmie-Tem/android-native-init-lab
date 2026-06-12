#!/usr/bin/env python3
"""V2282 V2254 Wi-Fi hold/reconnect validation runner.

Default mode is source/dry-run only. Live mode flashes the current promoted
V2254 Wi-Fi detail surface image, performs an explicitly scoped connect -> DHCP
-> bounded ping -> hold/idle -> cleanup -> reconnect -> DHCP -> bounded ping
cycle, then rolls back to V2237 and verifies selftest fail=0.

The runner is intentionally credential-gated: if Wi-Fi secrets are absent or
invalid, live mode exits before flashing.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import a90_transport as transport  # noqa: E402
import native_wifi_connect_carrier_handoff_v2174 as v2174  # noqa: E402
import native_wifi_hold_reconnect_handoff_v2177 as v2177  # noqa: E402
from a90harness.evidence import EvidenceStore, WORKSPACE_PRIVATE_ROOT, workspace_private_input_path  # noqa: E402


CYCLE = "V2282"
RUN_LABEL = "v2282-v2254-wifi-hold-reconnect"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2282_V2254_WIFI_HOLD_RECONNECT_RUNNER_2026-06-12.md"
)
TEST_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v2254_wifi_detail_surface.img", legacy_fallback=False)
ROLLBACK_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2237_supplicant_terminate_poll.img", legacy_fallback=False
)
FALLBACK_IMAGE = workspace_private_input_path("boot_images", "boot_linux_v48.img", legacy_fallback=False)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.272 (v2254-wifi-detail-surface)"
ROLLBACK_EXPECT_VERSION = "A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)"
TEST_EXPECT_SHA256 = "c668e9cd9a3621c955fa369c5d106271a96a949dcaec3774a5719d24b8ba19e9"
ROLLBACK_EXPECT_SHA256 = "b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f"
FALLBACK_EXPECT_SHA256 = "1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042"
REQUIRED_CONFIRM = "I_UNDERSTAND_V2282_FLASHES_V2254_RUNS_WIFI_AND_ROLLS_BACK_TO_V2237"
DEFAULT_HOLD_SEC = 180
DEFAULT_HOLD_INTERVAL_SEC = 30
DEFAULT_PING_TARGET = "1.1.1.1"


def rel(path: Path) -> str:
    return v2174.rel(path)


def sha256(path: Path) -> str:
    return v2174.sha256(path)


def now_iso() -> str:
    return v2174.now_iso()


def preflight(profile_name: str | None, ping_target: str, hold_sec: int, hold_interval_sec: int) -> dict[str, Any]:
    env_load = v2174.load_wifi_env()
    secret_status = v2174.wifi_secret_status(profile_name)
    test_sha = sha256(TEST_IMAGE) if TEST_IMAGE.exists() else ""
    rollback_sha = sha256(ROLLBACK_IMAGE) if ROLLBACK_IMAGE.exists() else ""
    fallback_sha = sha256(FALLBACK_IMAGE) if FALLBACK_IMAGE.exists() else ""
    return {
        "cycle": CYCLE,
        "run_label": RUN_LABEL,
        "test_image": rel(TEST_IMAGE),
        "test_image_exists": TEST_IMAGE.exists(),
        "test_image_sha256": test_sha,
        "test_image_expected_sha256": TEST_EXPECT_SHA256,
        "test_image_sha_matches_expected": test_sha == TEST_EXPECT_SHA256,
        "test_expect_version": TEST_EXPECT_VERSION,
        "rollback_image": rel(ROLLBACK_IMAGE),
        "rollback_image_exists": ROLLBACK_IMAGE.exists(),
        "rollback_image_sha256": rollback_sha,
        "rollback_image_expected_sha256": ROLLBACK_EXPECT_SHA256,
        "rollback_image_sha_matches_expected": rollback_sha == ROLLBACK_EXPECT_SHA256,
        "rollback_expect_version": ROLLBACK_EXPECT_VERSION,
        "fallback_image": rel(FALLBACK_IMAGE),
        "fallback_image_exists": FALLBACK_IMAGE.exists(),
        "fallback_image_sha256": fallback_sha,
        "fallback_image_expected_sha256": FALLBACK_EXPECT_SHA256,
        "fallback_image_sha_matches_expected": fallback_sha == FALLBACK_EXPECT_SHA256,
        "profile": secret_status.get("profile"),
        "profile_source": "explicit" if profile_name else "default-or-env",
        "wifi_secret_status": secret_status,
        "env_load": env_load,
        "ping_target": ping_target,
        "hold_sec": hold_sec,
        "hold_interval_sec": hold_interval_sec,
        "credential_values_logged": False,
        "recovery_twrp_available_source": "docs/operations/NATIVE_INIT_FLASH_AND_BRIDGE_GUIDE.md",
        "flash_helper": "workspace/public/src/scripts/revalidation/native_init_flash.py",
    }


def dry_run_commands() -> dict[str, Any]:
    commands = {
        "flash_v2254": v2174.flash_command(
            TEST_IMAGE,
            TEST_EXPECT_VERSION,
            from_native=True,
            expect_sha256=TEST_EXPECT_SHA256,
        ),
        "connect": ["a90ctl", "wifi", "connect", "<profile>"],
        "dhcp": ["a90ctl", "wifi", "dhcp", "<profile>"],
        "hold_samples": ["a90ctl", "run", "/cache/bin/busybox", "sh", "-c", "<read-only carrier/route/resolv sampling>"],
        "cleanup": ["a90ctl", "wifi", "cleanup"],
        "rollback_v2237": v2174.flash_command(
            ROLLBACK_IMAGE,
            ROLLBACK_EXPECT_VERSION,
            from_native=True,
            expect_sha256=ROLLBACK_EXPECT_SHA256,
        ),
    }
    return json.loads(json.dumps(commands, default=str))


def serial_step(
    store: EvidenceStore,
    steps: list[dict[str, Any]],
    name: str,
    command: list[str],
    *,
    timeout: float = 90.0,
    bridge_timeout: float = 60.0,
) -> dict[str, Any]:
    return v2177.serial_step(store, steps, name, command, timeout=timeout, bridge_timeout=bridge_timeout)


def rollback(store: EvidenceStore, steps: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    first = v2174.run_command(
        v2174.flash_command(
            ROLLBACK_IMAGE,
            ROLLBACK_EXPECT_VERSION,
            from_native=True,
            expect_sha256=ROLLBACK_EXPECT_SHA256,
        ),
        timeout=args.flash_timeout,
    )
    v2174.write_step(store, steps, "rollback-v2237-from-native", first)
    ok = bool(first.get("ok"))
    attempt = "from-native"
    if not ok:
        second = v2174.run_command(
            v2174.flash_command(
                ROLLBACK_IMAGE,
                ROLLBACK_EXPECT_VERSION,
                from_native=False,
                expect_sha256=ROLLBACK_EXPECT_SHA256,
            ),
            timeout=args.flash_timeout,
        )
        v2174.write_step(store, steps, "rollback-v2237-from-recovery", second)
        ok = bool(second.get("ok"))
        attempt = "from-recovery"
    version = serial_step(store, steps, "post-rollback-version", ["version"], timeout=90, bridge_timeout=60)
    status = serial_step(store, steps, "post-rollback-status", ["status"], timeout=90, bridge_timeout=60)
    selftest = serial_step(store, steps, "post-rollback-selftest", ["selftest"], timeout=90, bridge_timeout=60)
    return {
        "ok": ok,
        "attempt": attempt,
        "version_ok": bool(version.get("ok")) and ROLLBACK_EXPECT_VERSION in str(version.get("stdout") or ""),
        "status_ok": bool(status.get("ok")),
        "selftest_ok": bool(selftest.get("ok")) and "fail=0" in str(selftest.get("stdout") or ""),
    }


def classify(manifest: dict[str, Any]) -> dict[str, Any]:
    pre = manifest.get("preflight") or {}
    if not manifest.get("execute"):
        ready = all([
            pre.get("test_image_exists"),
            pre.get("test_image_sha_matches_expected"),
            pre.get("rollback_image_exists"),
            pre.get("rollback_image_sha_matches_expected"),
            pre.get("fallback_image_exists"),
            pre.get("fallback_image_sha_matches_expected"),
        ])
        return {
            "decision": "v2282-v2254-hold-reconnect-dry-run-ready" if ready else "v2282-v2254-hold-reconnect-dry-run-blocked",
            "pass": bool(ready),
            "reason": (
                "runner, image hashes, rollback image, and emergency fallback are ready; live mode remains credential-gated"
                if ready
                else "required V2254, V2237, or emergency fallback image is missing/mismatched"
            ),
        }
    if manifest.get("confirm_missing"):
        return {"decision": "v2282-v2254-hold-reconnect-confirmation-missing", "pass": False, "reason": "live mode requires the exact confirmation token"}
    if not (pre.get("wifi_secret_status") or {}).get("valid"):
        return {"decision": "v2282-v2254-hold-reconnect-wifi-env-missing-no-flash", "pass": False, "reason": "Wi-Fi credential presence check failed before flash"}
    if not (manifest.get("transport_selection") or {}).get("status_ok"):
        return {"decision": "v2282-v2254-hold-reconnect-native-unavailable-no-flash", "pass": False, "reason": "native transport/status preflight failed before flash"}
    if not (manifest.get("current_preflight") or {}).get("selftest_ok"):
        return {"decision": "v2282-v2254-hold-reconnect-current-selftest-failed-no-flash", "pass": False, "reason": "current native selftest failed before flash"}
    if not manifest.get("test_flash_ok"):
        rollback_result = manifest.get("rollback") or {}
        suffix = "rollback-pass" if rollback_result.get("selftest_ok") else "rollback-failed"
        return {"decision": f"v2282-v2254-hold-reconnect-test-flash-failed-{suffix}", "pass": False, "reason": "V2254 flash or boot health failed"}
    rollback_result = manifest.get("rollback") or {}
    if not rollback_result.get("ok") or rollback_result.get("selftest_ok") is not True:
        return {"decision": "v2282-v2254-hold-reconnect-rollback-selftest-failed", "pass": False, "reason": "rollback did not end with selftest fail=0"}
    initial = manifest.get("initial") or {}
    reconnect = manifest.get("reconnect") or {}
    safety_ok = all(
        item.get("secret_values_logged") == "0" and item.get("credentials_logged") == "0"
        for item in (
            initial.get("connect", {}),
            initial.get("dhcp_ping", {}),
            reconnect.get("connect", {}),
            reconnect.get("dhcp_ping", {}),
        )
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
            "decision": "v2282-v2254-hold-reconnect-rollback-pass",
            "pass": True,
            "reason": "V2254 Wi-Fi held through the bounded idle window, reconnected after cleanup, and rolled back cleanly",
        }
    return {
        "decision": "v2282-v2254-hold-reconnect-failed-rollback-pass",
        "pass": False,
        "reason": "connect, DHCP, bounded ping, hold, reconnect, cleanup, or secret hygiene failed",
    }


def redacted_secret_status(status: dict[str, Any]) -> dict[str, Any]:
    return {
        "profile": status.get("profile"),
        "ssid_present": bool(status.get("ssid_present")),
        "psk_present": bool(status.get("psk_present")),
        "valid": bool(status.get("valid")),
        "secret_values_logged": status.get("secret_values_logged", 0),
    }


def redacted_env_load(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    redacted: list[dict[str, Any]] = []
    for entry in entries:
        path = Path(str(entry.get("path") or ""))
        redacted.append({
            "path": rel(path),
            "present": bool(entry.get("present")),
            "loaded_keys": list(entry.get("loaded_keys") or []),
        })
    return redacted


def render_report(manifest: dict[str, Any]) -> str:
    result = manifest["classification"]
    pre = manifest.get("preflight") or {}
    secret_status = redacted_secret_status(pre.get("wifi_secret_status") or {})
    initial = manifest.get("initial") or {}
    reconnect = manifest.get("reconnect") or {}
    hold = manifest.get("hold") or {}
    disconnect = manifest.get("disconnect") or {}
    rollback_result = manifest.get("rollback") or {}
    phase_lines = [
        f"- `{item['name']}`: `{item['elapsed_sec']}` sec"
        for item in manifest.get("phase_timers", [])
    ]
    lines = [
        "# Native Init V2282 V2254 Wi-Fi Hold Reconnect Runner",
        "",
        "## Summary",
        "",
        "- Cycle: `V2282`",
        "- Type: T2 WLAN native-init current-baseline hold/reconnect runner.",
        f"- Decision: `{result['decision']}`",
        f"- Result: `{'PASS' if result['pass'] else 'FAIL'}`",
        f"- Reason: {result['reason']}",
        f"- Execute mode: `{manifest.get('execute')}`",
        f"- Evidence: `{manifest.get('out_dir')}`",
        "- T1 drop trigger: V2280 exhausted the workqueue execute-start oracle for the firmware_class/qcacld-HDD target and no new independent T1 oracle is encoded.",
        "",
        "## Images",
        "",
        f"- Test image: `{pre.get('test_image')}`",
        f"- Test SHA256: `{pre.get('test_image_sha256')}`",
        f"- Test version: `{pre.get('test_expect_version')}`",
        f"- Rollback image: `{pre.get('rollback_image')}`",
        f"- Rollback SHA256: `{pre.get('rollback_image_sha256')}`",
        f"- Rollback version: `{pre.get('rollback_expect_version')}`",
        f"- Emergency fallback image present: `{pre.get('fallback_image_exists')}` SHA match `{pre.get('fallback_image_sha_matches_expected')}`",
        "",
        "## Credential Gate",
        "",
        f"- Presence only: `{secret_status}`",
        f"- Env sources: `{redacted_env_load(pre.get('env_load') or [])}`",
        "- Raw SSID, PSK, BSSID, MAC, assigned IP, route, DNS, DHCP lease, and ping transcript are not written to this public report.",
        "",
    ]
    if not manifest.get("execute"):
        lines.extend([
            "## Dry-Run Plan",
            "",
            "```json",
            json.dumps(manifest.get("dry_run_commands") or {}, indent=2, ensure_ascii=False, default=str),
            "```",
            "",
        ])
    else:
        lines.extend([
            "## Live Evidence",
            "",
            f"- Current preflight selftest fail=0: `{(manifest.get('current_preflight') or {}).get('selftest_ok')}`",
            f"- V2254 flash OK: `{manifest.get('test_flash_ok')}`",
            f"- V2254 health: `{manifest.get('test_health')}`",
            f"- Initial connect: `{(initial.get('connect') or {}).get('decision', '')}` carrier `{(initial.get('connect') or {}).get('carrier_up', '')}` WPA `{(initial.get('connect') or {}).get('wpa_state', '')}`.",
            f"- Initial DHCP: `{(initial.get('dhcp_ping') or {}).get('dhcp_decision', '')}` ping rc `{(initial.get('dhcp_ping') or {}).get('external_ping_rc', '')}`.",
            f"- Hold window: `{hold.get('hold_sec', '')}` sec; samples `{hold.get('samples', '')}`; sample OK `{hold.get('sample_ok', False)}`; final ping rc `{hold.get('final_ping_rc', '')}`.",
            f"- Hold gating values: carrier `{hold.get('carrier_values', [])}` route `{hold.get('route_values', [])}` resolv `{hold.get('resolv_conf_values', [])}`.",
            f"- Disconnect cleanup: `{disconnect.get('cleanup_decision', '')}` residue clean `{disconnect.get('residue_clean', False)}`.",
            f"- Reconnect: `{(reconnect.get('connect') or {}).get('decision', '')}` carrier `{(reconnect.get('connect') or {}).get('carrier_up', '')}` WPA `{(reconnect.get('connect') or {}).get('wpa_state', '')}`.",
            f"- Reconnect DHCP: `{(reconnect.get('dhcp_ping') or {}).get('dhcp_decision', '')}` ping rc `{(reconnect.get('dhcp_ping') or {}).get('external_ping_rc', '')}`.",
            f"- Final cleanup: `{(reconnect.get('cleanup') or {}).get('cleanup_decision', '')}` residue clean `{(reconnect.get('cleanup') or {}).get('residue_clean', False)}`.",
            f"- Rollback OK: `{rollback_result.get('ok')}` via `{rollback_result.get('attempt')}` selftest fail=0 `{rollback_result.get('selftest_ok')}`.",
            "",
        ])
    lines.extend([
        "## Phase Timers",
        "",
        *(phase_lines if phase_lines else ["- `none`: `0` sec"]),
        "",
        "## Safety Scope",
        "",
        "- Live mode is disabled unless `--execute` and the exact confirmation token are supplied.",
        "- Live mode exits before flash if Wi-Fi credentials are absent or invalid.",
        "- Flash path is limited to boot partition via `native_init_flash.py`.",
        "- Wi-Fi actions are explicitly scoped to connect, DHCP, bounded ping, hold/idle sampling, cleanup, reconnect, DHCP, bounded ping, and final cleanup.",
        "- No Wi-Fi scan is run by this runner.",
        "- No credentials, SSID, BSSID, MAC, IP, route, DHCP lease, DNS server, or ping transcript is committed.",
        "- No BPF attach, tracefs write, `probe_write_user`, eSoC/PCIe/GDSC/PMIC/GPIO, platform bind/unbind, or `sda29` write.",
        "",
    ])
    return "\n".join(lines)


def write_outputs(store: EvidenceStore, manifest: dict[str, Any]) -> None:
    store.write_json("manifest.json", manifest)
    report = render_report(manifest)
    store.write_text("summary.md", report)
    REPORT_PATH.write_text(report, encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    label = v2174.safe_artifact_label(args.label) if hasattr(v2174, "safe_artifact_label") else args.label.replace("/", "-")
    out_dir = WORKSPACE_PRIVATE_ROOT / "runs" / "wifi" / f"{label}-{v2174.timestamp_label()}"
    store = EvidenceStore(out_dir)
    steps: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {
        "cycle": CYCLE,
        "run_label": RUN_LABEL,
        "out_dir": rel(out_dir),
        "execute": bool(args.execute),
        "phase_timer_contract": transport.PHASE_TIMER_CONTRACT,
        "phase_timers": [],
        "steps": steps,
    }
    with transport.phase(manifest, "host_preflight"):
        manifest["preflight"] = preflight(args.profile, args.ping_target, args.hold_sec, args.hold_interval_sec)
    if not args.execute:
        with transport.phase(manifest, "dry_run_plan"):
            manifest["dry_run_commands"] = dry_run_commands()
        manifest["rollback"] = {"ok": True, "attempt": "not-needed-no-flash", "selftest_ok": True}
        manifest["classification"] = classify(manifest)
        transport.set_residual_state(manifest, {
            "device_touched": False,
            "flash_reboot": False,
            "rollback_ok": True,
            "cleanup_required": False,
            "wifi_connect": False,
            "dhcp_routes_ping": False,
            "credentials_used": False,
        })
        write_outputs(store, manifest)
        return manifest
    if args.confirm != REQUIRED_CONFIRM:
        manifest["confirm_missing"] = True
        manifest["rollback"] = {"ok": True, "attempt": "not-needed-no-flash", "selftest_ok": True}
        manifest["classification"] = classify(manifest)
        transport.set_residual_state(manifest, {"device_touched": False, "flash_reboot": False, "cleanup_required": False})
        write_outputs(store, manifest)
        return manifest

    with transport.phase(manifest, "transport_preflight"):
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
    if not (manifest["preflight"].get("wifi_secret_status") or {}).get("valid") or not transport_selection.get("status_ok"):
        manifest["rollback"] = {"ok": True, "attempt": "not-needed-no-flash", "selftest_ok": True}
        manifest["classification"] = classify(manifest)
        transport.set_residual_state(manifest, {"device_touched": bool(steps), "flash_reboot": False, "cleanup_required": False})
        write_outputs(store, manifest)
        return manifest

    with transport.phase(manifest, "current_selftest_preflight"):
        current_selftest = serial_step(store, steps, "preflight-current-selftest", ["selftest"], timeout=90, bridge_timeout=60)
    manifest["current_preflight"] = {
        "selftest_ok": bool(current_selftest.get("ok")) and "fail=0" in str(current_selftest.get("stdout") or ""),
    }
    if not manifest["current_preflight"]["selftest_ok"]:
        manifest["rollback"] = {"ok": True, "attempt": "not-needed-no-flash", "selftest_ok": True}
        manifest["classification"] = classify(manifest)
        transport.set_residual_state(manifest, {"device_touched": True, "flash_reboot": False, "cleanup_required": False})
        write_outputs(store, manifest)
        return manifest

    test_flash_ok = False
    rollback_result: dict[str, Any] = {"ok": True, "attempt": "not-needed", "selftest_ok": True}
    try:
        with transport.phase(manifest, "flash_v2254"):
            test_flash = v2174.run_command(
                v2174.flash_command(
                    TEST_IMAGE,
                    TEST_EXPECT_VERSION,
                    from_native=True,
                    expect_sha256=TEST_EXPECT_SHA256,
                ),
                timeout=args.flash_timeout,
            )
            v2174.write_step(store, steps, "flash-v2254-from-native", test_flash)
            test_flash_ok = bool(test_flash.get("ok"))
        manifest["test_flash_ok"] = test_flash_ok
        if test_flash_ok:
            with transport.phase(manifest, "test_boot_health"):
                version = serial_step(store, steps, "test-boot-version", ["version"], timeout=120, bridge_timeout=80)
                status = serial_step(store, steps, "test-boot-status", ["status"], timeout=120, bridge_timeout=80)
                selftest = serial_step(store, steps, "test-boot-selftest", ["selftest"], timeout=120, bridge_timeout=80)
            manifest["test_health"] = {
                "version_ok": bool(version.get("ok")) and TEST_EXPECT_VERSION in str(version.get("stdout") or ""),
                "status_ok": bool(status.get("ok")),
                "selftest_ok": bool(selftest.get("ok")) and "fail=0" in str(selftest.get("stdout") or ""),
            }
            with transport.phase(manifest, "initial_connect_window"):
                initial_connect = v2177.run_connect_phase(store, steps, prefix="initial-connect", profile_name=args.profile)
            initial_dhcp: dict[str, Any] = {}
            hold_result: dict[str, Any] = {}
            disconnect: dict[str, Any] = {}
            reconnect_connect: dict[str, Any] = {}
            reconnect_dhcp: dict[str, Any] = {}
            reconnect_cleanup: dict[str, Any] = {}
            if initial_connect.get("ok"):
                with transport.phase(manifest, "initial_dhcp_ping_window"):
                    initial_dhcp = v2177.run_dhcp_ping_no_cleanup(
                        store,
                        steps,
                        prefix="initial",
                        profile_name=args.profile,
                        ping_target=args.ping_target,
                    )
            if initial_dhcp.get("ok"):
                with transport.phase(manifest, "hold_idle_window"):
                    hold_result = v2177.run_hold_idle(
                        store,
                        steps,
                        hold_sec=args.hold_sec,
                        interval_sec=args.hold_interval_sec,
                        ping_target=args.ping_target,
                    )
            with transport.phase(manifest, "disconnect_cleanup_window"):
                disconnect = v2177.run_cleanup_check(store, steps, prefix="disconnect")
            if disconnect.get("ok"):
                with transport.phase(manifest, "reconnect_window"):
                    reconnect_connect = v2177.run_connect_phase(store, steps, prefix="reconnect-connect", profile_name=args.profile)
                if reconnect_connect.get("ok"):
                    with transport.phase(manifest, "reconnect_dhcp_ping_window"):
                        reconnect_dhcp = v2177.run_dhcp_ping_no_cleanup(
                            store,
                            steps,
                            prefix="reconnect",
                            profile_name=args.profile,
                            ping_target=args.ping_target,
                        )
                with transport.phase(manifest, "final_cleanup_window"):
                    reconnect_cleanup = v2177.run_cleanup_check(store, steps, prefix="final")
            manifest["initial"] = {"connect": initial_connect, "dhcp_ping": initial_dhcp}
            manifest["hold"] = hold_result
            manifest["disconnect"] = disconnect
            manifest["reconnect"] = {"connect": reconnect_connect, "dhcp_ping": reconnect_dhcp, "cleanup": reconnect_cleanup}
    finally:
        if test_flash_ok:
            with transport.phase(manifest, "rollback"):
                rollback_result = rollback(store, steps, args)
    manifest["rollback"] = rollback_result
    manifest["classification"] = classify(manifest)
    transport.set_residual_state(manifest, {
        "device_touched": True,
        "flash_reboot": bool(test_flash_ok),
        "test_flash_ok": bool(test_flash_ok),
        "rollback_ok": bool(rollback_result.get("ok")) and bool(rollback_result.get("selftest_ok")),
        "rollback_attempt": rollback_result.get("attempt"),
        "selftest_ok": bool(rollback_result.get("selftest_ok")),
        "cleanup_required": not (
            bool((manifest.get("reconnect") or {}).get("cleanup", {}).get("ok"))
            and bool((manifest.get("reconnect") or {}).get("cleanup", {}).get("residue_clean"))
            and bool(rollback_result.get("selftest_ok"))
        ),
        "wifi_connect": True,
        "dhcp_routes_ping": True,
        "credentials_used": True,
    })
    write_outputs(store, manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default=RUN_LABEL)
    parser.add_argument("--profile")
    parser.add_argument("--ping-target", default=DEFAULT_PING_TARGET)
    parser.add_argument("--hold-sec", type=int, default=DEFAULT_HOLD_SEC)
    parser.add_argument("--hold-interval-sec", type=int, default=DEFAULT_HOLD_INTERVAL_SEC)
    parser.add_argument("--flash-timeout", type=float, default=900.0)
    parser.add_argument("--execute", action="store_true", help="perform the live flash/connect/hold/reconnect/rollback sequence")
    parser.add_argument("--confirm", default="", help=f"required for --execute: {REQUIRED_CONFIRM}")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.hold_sec = max(30, args.hold_sec)
    args.hold_interval_sec = max(10, args.hold_interval_sec)
    manifest = run(args)
    result = manifest["classification"]
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "reason": result["reason"],
        "out_dir": manifest["out_dir"],
        "execute": manifest["execute"],
        "credential_valid": bool((manifest.get("preflight") or {}).get("wifi_secret_status", {}).get("valid")),
        "hold_sec": args.hold_sec,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
