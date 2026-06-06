#!/usr/bin/env python3
"""V858 pm-service private property delta deploy.

Uploads only the V858 files needed to update the existing versioned V535
private property root with V857 pm-service/pm-proxy residual property coverage.
It verifies device-side hashes after upload.  It does not replace global
`/dev/__properties__`, start daemons, scan/connect, or bring Wi-Fi up.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_property_runtime_incremental_v536 as v536
from a90_kernel_tools import repo_path


DEFAULT_LAYOUT = Path("tmp/wifi/v858-pm-service-private-property-runtime/manifest.json")
DEFAULT_OUT_DIR = Path("tmp/wifi/v858-pm-service-property-incremental-live")
HELPER_V132_SHA256 = "a167500bd43f56a99da7e3644a8b240360de571aea5edc76b8afaa5215b1f5c7"
APPROVAL_PHRASE = (
    "approve v858 pm-service private property delta deploy only; "
    "no daemon start and no Wi-Fi bring-up"
)


def _load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    return json.loads(resolved.read_text(encoding="utf-8"))


def _rewrite(text: str) -> str:
    return (
        text.replace("V536", "V858")
        .replace("v536", "v858")
        .replace("rmt-storage", "pm-service")
        .replace("rmt_storage", "pm-service")
        .replace("rmt", "pm-service")
    )


_base_build_manifest = v536.build_manifest
_base_render_summary = v536.render_summary
_base_preflight = v536.preflight


def decide(args, layout, files, records, lookups, live_error):
    failed_commands = [record.name for record in records if not record.ok]
    bad_files = [item.relative_path for item in files if item.status != "pass"]
    if args.command == "plan":
        return "v858-pm-service-property-incremental-plan-ready", True, "plan generated without device commands", "run preflight"
    if layout.get("decision") != "v858-pm-service-private-property-runtime-ready" or not layout.get("pass"):
        return "v858-pm-service-property-incremental-blocked", False, "V858 layout is not ready", "regenerate V858 layout"
    if bad_files:
        return "v858-pm-service-property-incremental-blocked", False, "bad files: " + ", ".join(bad_files), "fix V858 selected files"
    if failed_commands or live_error:
        return "v858-pm-service-property-incremental-failed", False, live_error or "failed commands: " + ", ".join(failed_commands), "inspect live evidence"
    if args.command == "preflight":
        return "v858-pm-service-property-incremental-preflight-ready", True, "preflight passed; delta upload still needs approval", "run approved V858 delta deploy"
    if not v536.approved(args):
        return "v858-pm-service-property-incremental-approval-required", False, "exact approval phrase required", "provide exact approval phrase"
    return (
        "v858-pm-service-property-incremental-deploy-pass",
        True,
        "V858 property delta deployed and device-side hashes verified",
        "rerun pm-service property-contract start-only against the updated private root",
    )


def build_manifest(args, store):
    manifest = _base_build_manifest(args, store)
    layout = _load_json(args.v535_manifest)
    manifest["cycle"] = "v858"
    manifest["decision"] = _rewrite(str(manifest.get("decision", "")))
    manifest["reason"] = _rewrite(str(manifest.get("reason", "")))
    manifest["next_step"] = _rewrite(str(manifest.get("next_step", "")))
    manifest["inputs"]["v858_layout"] = {
        "path": layout.get("path"),
        "decision": layout.get("decision"),
        "pass": layout.get("pass"),
        "residual_key_count": len(layout.get("v857_residual_keys", [])),
    }
    manifest["residual_lookup_keys"] = list(layout.get("v857_residual_keys", []))
    manifest["required_approval_phrase"] = APPROVAL_PHRASE
    manifest["approval_phrase_matched"] = args.approval_phrase == APPROVAL_PHRASE
    manifest["lookup_skipped_reason"] = (
        "helper property-lookup allowlist intentionally does not include the new pm-service/pm-proxy keys; "
        "host-side V858 layout roundtrip plus device-side sha verification are the proof for this deploy"
    )
    return manifest


def preflight(args, store, records):
    _base_preflight(args, store, records)
    v536.v535.live.device_cmd(args, store, records, "mountsystem-ro", ["mountsystem", "ro"], 20.0)


def render_summary(manifest):
    text = _base_render_summary(manifest).replace(
        "# V536 rmt_storage Property Incremental Deploy",
        "# V858 pm-service Property Incremental Deploy",
        1,
    )
    return "\n".join([
        text,
        "",
        "## V858 Notes",
        "",
        f"- residual_lookup_keys: `{manifest.get('residual_lookup_keys', [])}`",
        f"- lookup_skipped_reason: {manifest.get('lookup_skipped_reason', '')}",
        "",
    ])


v536.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
v536.DEFAULT_V535 = DEFAULT_LAYOUT
v536.APPROVAL_PHRASE = APPROVAL_PHRASE
v536.v535.live.DEFAULT_HELPER_SHA256 = HELPER_V132_SHA256
v536.v535.live.LOOKUP_KEYS = ()
v536.decide = decide
v536.build_manifest = build_manifest
v536.render_summary = render_summary
v536.preflight = preflight


if __name__ == "__main__":
    raise SystemExit(v536.main())
