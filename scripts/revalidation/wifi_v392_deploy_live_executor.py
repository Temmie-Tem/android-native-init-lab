#!/usr/bin/env python3
"""Fail-closed executor for V392 helper v21 deploy and backchain capture.

This keeps the V389 executor mechanics but swaps the version-specific helper,
runner, expected hash, output directory, and exact approval phrases. Without
the exact V392 approval phrases and explicit flags, this wrapper executes no
bridge/device command. It never starts Wi-Fi HAL or performs Wi-Fi bring-up.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wifi_v389_deploy_live_executor as executor


ORIGINAL_BASE_RESULT = executor.base_result
ORIGINAL_RENDER_SUMMARY = executor.render_summary

executor.__doc__ = __doc__
executor.DEFAULT_OUT_DIR = Path("tmp/wifi/v392-deploy-live-executor")
executor.DEPLOY_APPROVAL_PHRASE = "approve v392 deploy execns helper v21 only; no daemon start and no Wi-Fi bring-up"
executor.LIVE_APPROVAL_PHRASE = "approve v392 service-manager backchain capture only; no Wi-Fi HAL start and no Wi-Fi bring-up"
executor.DEPLOY_APPROVAL_BLOCKER = "exact-v392-deploy-approval-phrase"
executor.LIVE_APPROVAL_BLOCKER = "exact-v392-backchain-capture-live-approval-phrase"


def replace_version_text(value: Any) -> Any:
    if isinstance(value, str):
        return (
            value.replace("V389", "V392")
            .replace("v389", "v392")
            .replace("helper v19", "helper v21")
            .replace("Helper v19", "Helper v21")
            .replace("execns-helper-v19", "execns-helper-v21")
            .replace("enhanced crash capture", "backchain capture")
            .replace("Enhanced Crash Capture", "Backchain Capture")
        )
    if isinstance(value, list):
        return [replace_version_text(item) for item in value]
    if isinstance(value, dict):
        return {key: replace_version_text(item) for key, item in value.items()}
    return value


def deploy_command(args: executor.argparse.Namespace, store: executor.EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_execns_helper_v21_deploy_preflight.py",
        "--out-dir",
        str(executor.deploy_dir(store)),
        "--approval-phrase",
        args.deploy_approval_phrase,
        "--apply",
        "--assume-yes",
        "run",
    ]


def live_preflight_command(store: executor.EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_service_manager_start_only_v392_live_runner.py",
        "--out-dir",
        str(executor.live_preflight_dir(store)),
        "preflight",
    ]


def live_command(args: executor.argparse.Namespace, store: executor.EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_service_manager_start_only_v392_live_runner.py",
        "--out-dir",
        str(executor.live_dir(store)),
        "--approval-phrase",
        args.live_approval_phrase,
        "--apply",
        "--assume-yes",
        "run",
    ]


def deploy_ok(store: executor.EvidenceStore) -> bool:
    manifest = executor.load_json(executor.deploy_dir(store) / "manifest.json")
    return manifest.get("decision") == "execns-helper-v21-deploy-pass" and bool(manifest.get("pass"))


def base_result(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return replace_version_text(ORIGINAL_BASE_RESULT(*args, **kwargs))


def render_summary(manifest: dict[str, Any]) -> str:
    return replace_version_text(ORIGINAL_RENDER_SUMMARY(manifest))


executor.deploy_command = deploy_command
executor.live_preflight_command = live_preflight_command
executor.live_command = live_command
executor.deploy_ok = deploy_ok
executor.base_result = base_result
executor.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(executor.main())
