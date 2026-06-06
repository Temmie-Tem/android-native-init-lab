#!/usr/bin/env python3
"""V860 pm-service property superset incremental deploy.

Uploads only the V860 files needed to update the existing versioned V535
private property root with the V858/V859/V677 property superset.  It verifies
device-side hashes after upload.  It does not replace global
`/dev/__properties__`, start daemons, scan/connect, or bring Wi-Fi up.
"""

from __future__ import annotations

import json
from pathlib import Path

import native_property_runtime_incremental_v536 as v536
from a90_kernel_tools import repo_path


DEFAULT_LAYOUT = Path("tmp/wifi/v860-pm-service-property-superset-runtime/manifest.json")
DEFAULT_OUT_DIR = Path("tmp/wifi/v860-pm-service-property-superset-incremental-live")
HELPER_V132_SHA256 = "a167500bd43f56a99da7e3644a8b240360de571aea5edc76b8afaa5215b1f5c7"
APPROVAL_PHRASE = (
    "approve v860 pm-service property superset delta deploy only; "
    "no daemon start and no Wi-Fi bring-up"
)


def load_json(path: Path) -> dict:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    return json.loads(resolved.read_text(encoding="utf-8"))


def rewrite(text: str) -> str:
    return (
        text.replace("V536", "V860")
        .replace("v536", "v860")
        .replace("rmt-storage", "pm-service-superset")
        .replace("rmt_storage", "pm-service-superset")
        .replace("rmt", "pm-service-superset")
    )


base_build_manifest = v536.build_manifest
base_render_summary = v536.render_summary
base_preflight = v536.preflight


def decide(args, layout, files, records, lookups, live_error):
    failed_commands = [record.name for record in records if not record.ok]
    bad_files = [item.relative_path for item in files if item.status != "pass"]
    if args.command == "plan":
        return "v860-pm-service-property-superset-incremental-plan-ready", True, "plan generated without device commands", "run preflight"
    if layout.get("decision") != "v860-pm-service-property-superset-runtime-ready" or not layout.get("pass"):
        return "v860-pm-service-property-superset-incremental-blocked", False, "V860 layout is not ready", "regenerate V860 layout"
    if bad_files:
        return "v860-pm-service-property-superset-incremental-blocked", False, "bad files: " + ", ".join(bad_files), "fix V860 selected files"
    if failed_commands or live_error:
        return "v860-pm-service-property-superset-incremental-failed", False, live_error or "failed commands: " + ", ".join(failed_commands), "inspect live evidence"
    if args.command == "preflight":
        return "v860-pm-service-property-superset-incremental-preflight-ready", True, "preflight passed; delta upload still needs approval", "run approved V860 delta deploy"
    if not v536.approved(args):
        return "v860-pm-service-property-superset-incremental-approval-required", False, "exact approval phrase required", "provide exact approval phrase"
    return (
        "v860-pm-service-property-superset-incremental-deploy-pass",
        True,
        "V860 property superset deployed and device-side hashes verified",
        "rerun bounded pm-service/pm-proxy start-only against the updated private root",
    )


def build_manifest(args, store):
    manifest = base_build_manifest(args, store)
    layout = load_json(args.v535_manifest)
    manifest["cycle"] = "v860"
    manifest["decision"] = rewrite(str(manifest.get("decision", "")))
    manifest["reason"] = rewrite(str(manifest.get("reason", "")))
    manifest["next_step"] = rewrite(str(manifest.get("next_step", "")))
    manifest["inputs"]["v860_layout"] = {
        "path": layout.get("path"),
        "decision": layout.get("decision"),
        "pass": layout.get("pass"),
        "superset_key_count": len(layout.get("v860_superset_keys", [])),
        "v859_new_key_count": len(layout.get("v859_new_keys", [])),
    }
    manifest["residual_lookup_keys"] = list(layout.get("v860_superset_keys", []))
    manifest["required_approval_phrase"] = APPROVAL_PHRASE
    manifest["approval_phrase_matched"] = args.approval_phrase == APPROVAL_PHRASE
    manifest["lookup_skipped_reason"] = (
        "helper property-lookup allowlist intentionally does not include all service-specific V860 keys; "
        "host-side V860 layout roundtrip plus device-side sha verification are the proof for this deploy"
    )
    return manifest


def preflight(args, store, records):
    base_preflight(args, store, records)
    v536.v535.live.device_cmd(args, store, records, "mountsystem-ro", ["mountsystem", "ro"], 20.0)


def render_summary(manifest):
    text = base_render_summary(manifest).replace(
        "# V536 rmt_storage Property Incremental Deploy",
        "# V860 pm-service Property Superset Incremental Deploy",
        1,
    )
    return "\n".join([
        text,
        "",
        "## V860 Notes",
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
