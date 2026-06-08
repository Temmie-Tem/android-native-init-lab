#!/usr/bin/env python3
"""Validate V2178 current-baseline Wi-Fi autoconnect once with shared phase timers.

This runner does not flash, enable boot autoconnect, scan separately, install
unbounded routes, or run external ping. It uses the already-staged private
default profile, runs one bounded `wifi autoconnect once`, captures status, then
cleans up Wi-Fi runtime state.
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
from a90harness.evidence import EvidenceStore, safe_artifact_label, wifi_artifact_dir


CYCLE = "V2180"
RUN_LABEL = "v2180-v2178-wifi-autoconnect-phase-validation"
EXPECTED_VERSION = "A90 Linux init 0.9.253 (v2178-wifi-profile-autoconnect)"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def run_step(store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             *,
             bridge_timeout: float = 60.0) -> dict[str, Any]:
    return transport.run_serial_step(
        store,
        steps,
        name,
        command,
        bridge_timeout=bridge_timeout,
    )


def step_text(store: EvidenceStore, step: dict[str, Any] | None) -> str:
    if not step:
        return ""
    text = ""
    for key in ("stdout_file", "stderr_file"):
        value = step.get(key)
        if not value:
            continue
        path = store.run_dir / str(value)
        try:
            text += path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    return text


def find_step(steps: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for step in reversed(steps):
        if step.get("name") == name:
            return step
    return None


def classify(manifest: dict[str, Any]) -> dict[str, Any]:
    version = manifest.get("version") or {}
    connect = manifest.get("connect") or {}
    cleanup = manifest.get("cleanup") or {}
    disable_restore = manifest.get("autoconnect_disable_restore") or {}
    final_selftest = manifest.get("final_selftest") or {}
    if not version.get("expected"):
        return {
            "decision": "v2180-wifi-phase-wrong-baseline",
            "pass": False,
            "reason": "device is not on the V2178 Wi-Fi autoconnect baseline",
        }
    if connect.get("decision") != "wifi-autoconnect-pass":
        return {
            "decision": "v2180-wifi-phase-connect-failed",
            "pass": False,
            "reason": "wifi autoconnect once did not pass",
        }
    if cleanup.get("decision") != "wifi-cleanup-done":
        return {
            "decision": "v2180-wifi-phase-cleanup-failed",
            "pass": False,
            "reason": "wifi cleanup did not report done",
        }
    if disable_restore.get("decision") != "wifi-autoconnect-disabled":
        return {
            "decision": "v2180-wifi-phase-disable-restore-failed",
            "pass": False,
            "reason": "autoconnect disable restore did not report disabled",
        }
    if not final_selftest.get("fail0"):
        return {
            "decision": "v2180-wifi-phase-selftest-failed",
            "pass": False,
            "reason": "final selftest did not report fail=0",
        }
    return {
        "decision": "v2180-wifi-phase-validation-pass",
        "pass": True,
        "reason": "V2178 wifi autoconnect once passed, cleanup completed, and selftest fail=0",
    }


def run(label: str, profile: str | None = None) -> dict[str, Any]:
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
            "flash": 0,
            "boot_autoconnect_enable": 0,
            "external_ping": 0,
            "credentials_logged": 0,
        },
        "profile_source": "explicit" if profile else "autoconnect-default-profile",
    }
    selected_profile = profile

    with transport.phase(manifest, "preflight"):
        selection = transport.select_transport(store, steps, ensure=True, prefer_fast=True)
        version_step = run_step(store, steps, "pre-version", ["version"], bridge_timeout=30)
        status_step = run_step(store, steps, "pre-wifi-status", ["wifi", "status"], bridge_timeout=60)
        autoconnect_status_step = run_step(
            store,
            steps,
            "pre-wifi-autoconnect-status",
            ["wifi", "autoconnect", "status"],
            bridge_timeout=60,
        )
        version_text = step_text(store, find_step(steps, "pre-version"))
        autoconnect_status_text = step_text(store, find_step(steps, "pre-wifi-autoconnect-status"))
        autoconnect_status_fields = transport.parse_key_values(autoconnect_status_text)
        if not selected_profile:
            selected_profile = autoconnect_status_fields.get("default_profile", "")
        manifest["transport_selection"] = selection
        manifest["version"] = {
            "expected": EXPECTED_VERSION in version_text,
            "command_ok": bool(version_step.get("ok")),
        }
        manifest["pre_status_ok"] = bool(status_step.get("ok"))
        manifest["pre_autoconnect_status_ok"] = bool(autoconnect_status_step.get("ok"))
        manifest["selected_profile_present"] = 1 if selected_profile else 0
        manifest["autoconnect_status"] = {
            "config_valid": autoconnect_status_fields.get("config_valid", ""),
            "autoconnect": autoconnect_status_fields.get("autoconnect", ""),
            "profile_valid": autoconnect_status_fields.get("profile_valid", ""),
            "external_ping": autoconnect_status_fields.get("external_ping", ""),
            "secret_values_logged": autoconnect_status_fields.get("secret_values_logged", ""),
            "decision": autoconnect_status_fields.get("decision", ""),
        }

    with transport.phase(manifest, "connect_window"):
        connect_command = ["wifi", "autoconnect", "once"] + ([selected_profile] if selected_profile else [])
        connect_step = run_step(
            store,
            steps,
            "wifi-autoconnect-once",
            connect_command,
            bridge_timeout=260,
        )
        connect_text = step_text(store, find_step(steps, "wifi-autoconnect-once"))
        connect_fields = transport.parse_key_values(connect_text)
        manifest["connect"] = {
            "command_ok": bool(connect_step.get("ok")),
            "decision": connect_fields.get("decision", ""),
            "final_rc": connect_fields.get("autoconnect.final_rc", connect_fields.get("final_rc", "")),
            "carrier_up": connect_fields.get("autoconnect.carrier_up", connect_fields.get("carrier_up", "")),
            "secret_values_logged": connect_fields.get("secret_values_logged", ""),
            "credentials_logged": connect_fields.get("credentials_logged", ""),
        }

    with transport.phase(manifest, "selftest"):
        status_after = run_step(store, steps, "post-connect-wifi-status", ["wifi", "status"], bridge_timeout=60)
        manifest["post_connect_status_ok"] = bool(status_after.get("ok"))

    with transport.phase(manifest, "cleanup"):
        cleanup_step = run_step(store, steps, "wifi-cleanup", ["wifi", "cleanup"], bridge_timeout=90)
        disable_step = run_step(
            store,
            steps,
            "wifi-autoconnect-disable-restore",
            ["wifi", "autoconnect", "disable"],
            bridge_timeout=60,
        )
        cleanup_text = step_text(store, find_step(steps, "wifi-cleanup"))
        disable_text = step_text(store, find_step(steps, "wifi-autoconnect-disable-restore"))
        cleanup_fields = transport.parse_key_values(cleanup_text)
        disable_fields = transport.parse_key_values(disable_text)
        manifest["cleanup"] = {
            "command_ok": bool(cleanup_step.get("ok")),
            "decision": cleanup_fields.get("decision", ""),
        }
        manifest["autoconnect_disable_restore"] = {
            "command_ok": bool(disable_step.get("ok")),
            "decision": disable_fields.get("decision", ""),
        }

    with transport.phase(manifest, "selftest_final"):
        final_status = run_step(store, steps, "final-wifi-status", ["wifi", "status"], bridge_timeout=60)
        final_selftest = run_step(store, steps, "final-selftest", ["selftest"], bridge_timeout=60)
        final_selftest_text = step_text(store, find_step(steps, "final-selftest"))
        manifest["final_status_ok"] = bool(final_status.get("ok"))
        manifest["final_selftest"] = {
            "command_ok": bool(final_selftest.get("ok")),
            "fail0": "fail=0" in final_selftest_text,
        }

    manifest["steps"] = steps
    classification = classify(manifest)
    manifest["classification"] = classification
    manifest["decision"] = classification["decision"]
    manifest["pass"] = classification["pass"]
    manifest["reason"] = classification["reason"]
    with transport.phase(manifest, "artifact_upload"):
        pass
    store.write_json("manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default=RUN_LABEL)
    parser.add_argument("--profile", help="private profile name; omitted uses default_profile from device autoconnect config")
    args = parser.parse_args()
    manifest = run(args.label, profile=args.profile)
    print(json.dumps({
        "decision": manifest["decision"],
        "pass": manifest["pass"],
        "reason": manifest["reason"],
        "out_dir": manifest["out_dir"],
        "phase_timer_contract": manifest.get("phase_timer_contract"),
        "phases": [item.get("name") for item in manifest.get("phase_timers", [])],
        "transport_selected": (manifest.get("transport_selection") or {}).get("selected"),
        "connect_decision": (manifest.get("connect") or {}).get("decision"),
        "cleanup_decision": (manifest.get("cleanup") or {}).get("decision"),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
