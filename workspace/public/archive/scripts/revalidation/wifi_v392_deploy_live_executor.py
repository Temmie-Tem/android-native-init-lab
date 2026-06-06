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
ORIGINAL_CLASSIFY_IF_NEEDED = executor.classify_if_needed
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


def framechain_dir(store: executor.EvidenceStore) -> Path:
    return store.run_dir / "framechain"


def framechain_command(store: executor.EvidenceStore) -> list[str]:
    return [
        "python3",
        "scripts/revalidation/wifi_service_manager_framechain_analyze.py",
        "--out-dir",
        str(framechain_dir(store)),
        "--run-log",
        str(executor.live_dir(store) / "native/run-system-servicemanager.txt"),
        "analyze",
    ]


def framechain_manifest(store: executor.EvidenceStore) -> dict[str, Any]:
    return executor.load_json(framechain_dir(store) / "manifest.json")


def base_result(*args: Any, **kwargs: Any) -> dict[str, Any]:
    manifest = replace_version_text(ORIGINAL_BASE_RESULT(*args, **kwargs))
    if len(args) >= 2:
        manifest["planned_framechain_command"] = executor.command_string(framechain_command(args[1]))
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    summary = replace_version_text(ORIGINAL_RENDER_SUMMARY(manifest))
    planned = manifest.get("planned_framechain_command")
    if not planned:
        return summary
    return "\n".join([
        summary.rstrip(),
        "### Framechain Analyze",
        "",
        "```bash",
        str(planned),
        "```",
        "",
    ])


def list_blockers(manifest: dict[str, Any]) -> list[str]:
    blockers = manifest.get("remaining_blockers")
    if not isinstance(blockers, list):
        return []
    return [str(item) for item in blockers]


def classify_if_needed(
    args: executor.argparse.Namespace,
    store: executor.EvidenceStore,
    steps: list[executor.StepResult],
) -> tuple[str, bool, str, str, list[str]]:
    live = executor.live_manifest(store)
    if live.get("decision") != "service-manager-start-only-live-runtime-gap":
        return ORIGINAL_CLASSIFY_IF_NEEDED(args, store, steps)

    steps.append(executor.execute_step(store, "runtime-gap-classifier", executor.classify_command(store), args.timeout, execute=True))
    steps.append(executor.execute_step(store, "framechain-analyzer", framechain_command(store), args.timeout, execute=True))
    classified = executor.classify_manifest(store)
    framechain = framechain_manifest(store)
    frame_decision = str(framechain.get("decision") or "")

    if frame_decision == "service-manager-framechain-symbolization-pass":
        return (
            "service-manager-framechain-symbolization-pass",
            bool(framechain.get("pass")),
            f"classifier decision={classified.get('decision')} framechain decision={frame_decision}",
            str(framechain.get("next_step") or "inspect symbolized caller and plan targeted runtime repair"),
            list_blockers(framechain),
        )
    if frame_decision in {
        "service-manager-framechain-maprow-ready",
        "service-manager-framechain-no-maprow",
        "service-manager-framechain-needs-v392-live",
    }:
        return (
            frame_decision,
            bool(framechain.get("pass")),
            f"classifier decision={classified.get('decision')} framechain decision={frame_decision}",
            str(framechain.get("next_step") or "inspect framechain evidence"),
            list_blockers(framechain),
        )
    return (
        str(classified.get("decision") or "v392-classify-missing"),
        bool(classified.get("pass")),
        f"classifier decision={classified.get('decision')} framechain decision={frame_decision or 'missing'}",
        str(classified.get("next_step") or "inspect classifier evidence"),
        list_blockers(classified),
    )


executor.deploy_command = deploy_command
executor.live_preflight_command = live_preflight_command
executor.live_command = live_command
executor.deploy_ok = deploy_ok
executor.base_result = base_result
executor.render_summary = render_summary
executor.classify_if_needed = classify_if_needed


if __name__ == "__main__":
    raise SystemExit(executor.main())
