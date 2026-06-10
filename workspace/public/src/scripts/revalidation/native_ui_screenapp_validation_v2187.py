#!/usr/bin/env python3
"""Rollbackable V2187 screenapp UI validation.

This runner flashes the V2187 test image, validates direct rendering of the
same Wi-Fi network screens used by the on-device menu, then rolls back to the
promoted V2186 baseline.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

REPO_ROOT = repo_root()
add_legacy_revalidation_path(REPO_ROOT)

import a90_transport as transport
import native_wifi_connect_carrier_handoff_v2174 as v2174
from a90harness.evidence import EvidenceStore, safe_artifact_label, wifi_artifact_dir, workspace_private_input_path


CYCLE = "V2187"
RUN_LABEL = "v2187-screenapp-ui-validation"
TEST_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2187_screenapp_ui_validation.img", legacy_fallback=False
)
ROLLBACK_IMAGE = workspace_private_input_path(
    "boot_images", "boot_linux_v2186_wifi_ui_polish.img", legacy_fallback=False
)
TEST_EXPECT_VERSION = "A90 Linux init 0.9.259 (v2187-screenapp-ui-validation)"
ROLLBACK_EXPECT_VERSION = "A90 Linux init 0.9.258 (v2186-wifi-ui-polish)"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V2187_SCREENAPP_UI_VALIDATION_LIVE_2026-06-10.md"
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def step_text(store: EvidenceStore, step: dict[str, Any] | None) -> str:
    return v2174.step_stdout(store, step)


def find_step(steps: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    return v2174.find_step(steps, name)


def fields_for(store: EvidenceStore, steps: list[dict[str, Any]], name: str) -> dict[str, str]:
    return transport.parse_key_values(step_text(store, find_step(steps, name)))


def run_serial(store: EvidenceStore,
               steps: list[dict[str, Any]],
               name: str,
               command: list[str],
               *,
               timeout: float = 60.0,
               bridge_timeout: float | None = None) -> dict[str, Any]:
    return transport.run_serial_step(
        store,
        steps,
        name,
        command,
        timeout=timeout,
        bridge_timeout=bridge_timeout if bridge_timeout is not None else timeout,
    )


def flash_command(image: Path, expect_version: str, *, from_native: bool) -> list[object]:
    return v2174.flash_command(image, expect_version, from_native=from_native)


def flash_step(store: EvidenceStore,
               steps: list[dict[str, Any]],
               name: str,
               image: Path,
               expect_version: str,
               *,
               from_native: bool) -> dict[str, Any]:
    result = v2174.run_command(flash_command(image, expect_version, from_native=from_native), timeout=720)
    v2174.write_step(store, steps, name, result)
    return result


def rollback(store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    first = flash_step(
        store,
        steps,
        "rollback-v2186-from-native",
        ROLLBACK_IMAGE,
        ROLLBACK_EXPECT_VERSION,
        from_native=True,
    )
    ok = bool(first.get("ok"))
    attempt = "from-native"
    if not ok:
        second = flash_step(
            store,
            steps,
            "rollback-v2186-from-recovery",
            ROLLBACK_IMAGE,
            ROLLBACK_EXPECT_VERSION,
            from_native=False,
        )
        ok = bool(second.get("ok"))
        attempt = "from-recovery"

    status = run_serial(store, steps, "post-rollback-status", ["status"], timeout=90, bridge_timeout=60)
    selftest = run_serial(store, steps, "post-rollback-selftest", ["selftest"], timeout=90, bridge_timeout=60)
    return {
        "ok": ok,
        "attempt": attempt,
        "status_ok": bool(status.get("ok")),
        "selftest_ok": bool(selftest.get("ok")) and "fail=0" in str(selftest.get("stdout") or ""),
    }


def screenapp_pass(fields: dict[str, str], title: str) -> bool:
    return (
        fields.get("screenapp.valid") == "1"
        and fields.get("screenapp.presented") == "1"
        and fields.get("screenapp.rc") == "0"
        and fields.get("screenapp.title") == title
    )


def classify(manifest: dict[str, Any]) -> dict[str, Any]:
    if not manifest.get("flash_v2187", {}).get("ok"):
        return {
            "decision": "v2187-screenapp-flash-failed",
            "pass": False,
            "reason": "V2187 test image did not flash or boot cleanly",
        }
    if not manifest.get("screenapp_status", {}).get("pass"):
        return {
            "decision": "v2187-screenapp-wifi-status-failed",
            "pass": False,
            "reason": "screenapp wifi-status did not present the WIFI STATUS screen",
        }
    if not manifest.get("screenapp_ping", {}).get("pass"):
        return {
            "decision": "v2187-screenapp-wifi-ping-failed",
            "pass": False,
            "reason": "screenapp wifi-ping did not present the WIFI PING RESULTS screen",
        }
    if not manifest.get("rollback", {}).get("selftest_ok"):
        return {
            "decision": "v2187-screenapp-rollback-selftest-failed",
            "pass": False,
            "reason": "rollback to V2186 did not end with selftest fail=0",
        }
    return {
        "decision": "v2187-screenapp-ui-validation-pass",
        "pass": True,
        "reason": "V2187 rendered WIFI STATUS and WIFI PING RESULTS through screenapp, then rolled back to V2186 with selftest fail=0",
    }


def render_report(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    status = manifest.get("screenapp_status", {})
    ping = manifest.get("screenapp_ping", {})
    rollback_info = manifest.get("rollback", {})
    return "\n".join([
        "# Native Init V2187 Screenapp UI Validation Live",
        "",
        "## Summary",
        "",
        "- Candidate tag: `v2187-screenapp-ui-validation`.",
        "- Parent/promoted rollback baseline: `v2186-wifi-ui-polish`.",
        "- Type: rollbackable live test-boot UI validation.",
        f"- Decision: `{classification['decision']}`.",
        f"- Result: {'PASS' if classification['pass'] else 'FAIL'}.",
        f"- Reason: {classification['reason']}.",
        f"- Evidence directory: `{manifest['out_dir']}`.",
        f"- Test boot image: `{rel(TEST_IMAGE)}`.",
        f"- Rollback image: `{rel(ROLLBACK_IMAGE)}`.",
        "",
        "## Screen Evidence",
        "",
        f"- `screenapp wifi-status`: pass `{status.get('pass')}`, title `{status.get('title', '')}`, presented `{status.get('presented', '')}`.",
        f"- `screenapp wifi-ping`: pass `{ping.get('pass')}`, title `{ping.get('title', '')}`, presented `{ping.get('presented', '')}`.",
        "- Both commands use the same native draw functions as the `NETWORK` menu apps.",
        "- This is command-level framebuffer presentation evidence; physical button navigation/OCR remains optional follow-up evidence.",
        "- `autohud` is not restored inside the test boot because rollback to V2186 immediately reboots and restores the baseline HUD service.",
        "",
        "## Rollback",
        "",
        f"- Rollback attempt: `{rollback_info.get('attempt', '')}`.",
        f"- Rollback command ok: `{rollback_info.get('ok')}`.",
        f"- Post-rollback status ok: `{rollback_info.get('status_ok')}`.",
        f"- Post-rollback selftest ok: `{rollback_info.get('selftest_ok')}`.",
        "",
        "## Safety Scope",
        "",
        "- `screenapp wifi-status` is read-only.",
        "- `screenapp wifi-ping` is explicit and bounded, using the existing `NETWORK > PING TEST` collector.",
        "- No credentials, raw SSID, BSSID, private IP, gateway, or peer MAC details are included in this public report.",
        "- No PMIC/GPIO/GDSC/regulator writes, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, or `/dev/subsys_esoc0` path was used.",
        "",
    ])


def run(label: str) -> dict[str, Any]:
    safe_label = safe_artifact_label(label, default=RUN_LABEL)
    out_dir = wifi_artifact_dir("runs", f"{RUN_LABEL}-{safe_label}", timestamp=True)
    store = EvidenceStore(out_dir)
    steps: list[dict[str, Any]] = []
    manifest: dict[str, Any] = {
        "cycle": CYCLE,
        "run_label": RUN_LABEL,
        "label": safe_label,
        "out_dir": rel(out_dir),
        "phase_timer_contract": transport.PHASE_TIMER_CONTRACT,
        "phase_timers": [],
        "scope": {
            "test_boot_flash": 1,
            "rollback_to_v2186": 1,
            "screenapp_status": 1,
            "screenapp_ping": 1,
            "credentials_logged": 0,
        },
    }
    rollback_info: dict[str, Any] = {"ok": False, "attempt": "not-started", "selftest_ok": False}

    try:
        with transport.phase(manifest, "preflight"):
            manifest["transport_selection"] = transport.select_transport(store, steps, ensure=True, prefer_fast=True)
            pre_version = run_serial(store, steps, "pre-version", ["version"], timeout=30, bridge_timeout=30)
            manifest["pre_version_ok"] = bool(pre_version.get("ok"))

        with transport.phase(manifest, "flash_v2187"):
            flashed = flash_step(
                store,
                steps,
                "flash-v2187-from-native",
                TEST_IMAGE,
                TEST_EXPECT_VERSION,
                from_native=True,
            )
            manifest["flash_v2187"] = {"ok": bool(flashed.get("ok"))}

        with transport.phase(manifest, "screenapp_window"):
            run_serial(store, steps, "stophud-before-screenapp", ["stophud"], timeout=30, bridge_timeout=30)
            run_serial(store, steps, "wifi-status-before-screenapp", ["wifi", "status"], timeout=90, bridge_timeout=60)
            status_step = run_serial(
                store,
                steps,
                "screenapp-wifi-status",
                ["screenapp", "wifi-status"],
                timeout=45,
                bridge_timeout=45,
            )
            ping_step = run_serial(
                store,
                steps,
                "screenapp-wifi-ping",
                ["screenapp", "wifi-ping"],
                timeout=60,
                bridge_timeout=60,
            )

            status_fields = fields_for(store, steps, "screenapp-wifi-status")
            ping_fields = fields_for(store, steps, "screenapp-wifi-ping")
            manifest["screenapp_status"] = {
                "command_ok": bool(status_step.get("ok")),
                "pass": bool(status_step.get("ok")) and screenapp_pass(status_fields, "WIFI STATUS"),
                "title": status_fields.get("screenapp.title", ""),
                "presented": status_fields.get("screenapp.presented", ""),
                "rc": status_fields.get("screenapp.rc", ""),
            }
            manifest["screenapp_ping"] = {
                "command_ok": bool(ping_step.get("ok")),
                "pass": bool(ping_step.get("ok")) and screenapp_pass(ping_fields, "WIFI PING RESULTS"),
                "title": ping_fields.get("screenapp.title", ""),
                "presented": ping_fields.get("screenapp.presented", ""),
                "rc": ping_fields.get("screenapp.rc", ""),
            }
    finally:
        with transport.phase(manifest, "rollback"):
            rollback_info = rollback(store, steps)
            manifest["rollback"] = rollback_info

    manifest["steps"] = steps
    manifest["classification"] = classify(manifest)
    manifest["decision"] = manifest["classification"]["decision"]
    manifest["pass"] = manifest["classification"]["pass"]
    manifest["reason"] = manifest["classification"]["reason"]
    transport.set_residual_state(manifest, {
        "rollback_ok": bool(rollback_info.get("ok")),
        "rollback_attempt": rollback_info.get("attempt", ""),
        "rollback_selftest_ok": bool(rollback_info.get("selftest_ok")),
        "screenapp_status_presented": (manifest.get("screenapp_status") or {}).get("presented", ""),
        "screenapp_ping_presented": (manifest.get("screenapp_ping") or {}).get("presented", ""),
        "cleanup_required": not bool(rollback_info.get("selftest_ok")),
    })
    store.write_json("manifest.json", manifest)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default=RUN_LABEL)
    args = parser.parse_args()
    manifest = run(args.label)
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "reason": manifest["reason"],
        "out_dir": manifest["out_dir"],
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
