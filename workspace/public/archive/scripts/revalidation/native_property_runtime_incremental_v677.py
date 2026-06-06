#!/usr/bin/env python3
"""V677 V676-residual private property delta deploy.

Uploads only the V677 files needed to update the versioned V535 private
property root with V676 residual property coverage. It then runs read-only
property lookup proof against that private root. It does not replace global
`/dev/__properties__`, start daemons, scan/connect, or bring Wi-Fi up.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_property_runtime_incremental_v536 as v536
from a90_kernel_tools import repo_path


DEFAULT_LAYOUT = Path("tmp/wifi/v677-v676-residual-private-property-runtime/manifest.json")
DEFAULT_OUT_DIR = Path("tmp/wifi/v677-v676-residual-property-incremental-live")
HELPER_V111_SHA256 = "1c65e1b766b85fda7629d9d7067047d8e0322d412447cf731ccab65a70655d88"
APPROVAL_PHRASE = (
    "approve v677 V676 residual private property delta deploy only; "
    "no daemon start and no Wi-Fi bring-up"
)


def _load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    return json.loads(resolved.read_text(encoding="utf-8"))


def _residual_lookup_keys() -> tuple[str, ...]:
    layout = _load_json(DEFAULT_LAYOUT)
    residual = [str(key) for key in layout.get("v676_residual_keys", [])]
    return tuple(dict.fromkeys(tuple(v536.v535.live.LOOKUP_KEYS) + tuple(residual)))


_base_render_summary = v536.render_summary
_base_build_manifest = v536.build_manifest
_base_preflight = v536.preflight


def _rewrite(text: str) -> str:
    return (
        text.replace("V536", "V677")
        .replace("v536", "v677")
        .replace("rmt-storage", "v676-residual")
        .replace("rmt_storage", "V676 residual")
        .replace("rmt", "V676 residual")
    )


def decide(args, layout, files, records, lookups, live_error):
    failed_commands = [record.name for record in records if not record.ok]
    bad_files = [item.relative_path for item in files if item.status != "pass"]
    lookup_failures = [item.key for item in lookups if not item.ok]
    if args.command == "plan":
        return "v677-v676-residual-property-incremental-plan-ready", True, "plan generated without device commands", "run preflight"
    if layout.get("decision") != "v677-v676-residual-private-property-runtime-ready" or not layout.get("pass"):
        return "v677-v676-residual-property-incremental-blocked", False, "V677 layout is not ready", "regenerate V677 layout"
    if bad_files:
        return "v677-v676-residual-property-incremental-blocked", False, "bad files: " + ", ".join(bad_files), "fix V677 selected files"
    if failed_commands or live_error:
        return "v677-v676-residual-property-incremental-failed", False, live_error or "failed commands: " + ", ".join(failed_commands), "inspect live evidence"
    if args.command == "preflight":
        return "v677-v676-residual-property-incremental-preflight-ready", True, "preflight passed; delta upload still needs approval", "run approved V677 delta deploy"
    if not v536.approved(args):
        return "v677-v676-residual-property-incremental-approval-required", False, "exact approval phrase required", "provide exact approval phrase"
    if lookup_failures:
        return "v677-v676-residual-property-incremental-lookup-blocked", False, "lookup failures: " + ", ".join(lookup_failures), "fix property layout or helper allowlist"
    return "v677-v676-residual-property-incremental-lookup-pass", True, "property delta deployed and selected V676 residual lookups passed", "rerun V676 property-seeded Android userspace-order proof"


def build_manifest(args, store):
    manifest = _base_build_manifest(args, store)
    layout = _load_json(args.v535_manifest)
    manifest["cycle"] = "v677"
    manifest["decision"] = _rewrite(str(manifest.get("decision", "")))
    manifest["reason"] = _rewrite(str(manifest.get("reason", "")))
    manifest["next_step"] = _rewrite(str(manifest.get("next_step", "")))
    manifest["inputs"]["v677_layout"] = {
        "path": layout.get("path"),
        "decision": layout.get("decision"),
        "pass": layout.get("pass"),
        "residual_key_count": len(layout.get("v676_residual_keys", [])),
    }
    manifest["residual_lookup_keys"] = list(_residual_lookup_keys())
    manifest["required_approval_phrase"] = APPROVAL_PHRASE
    manifest["approval_phrase_matched"] = args.approval_phrase == APPROVAL_PHRASE
    return manifest


def preflight(args, store, records):
    _base_preflight(args, store, records)
    v536.v535.live.device_cmd(args, store, records, "mountsystem-ro", ["mountsystem", "ro"], 20.0)


def render_summary(manifest):
    return _base_render_summary(manifest).replace(
        "# V536 rmt_storage Property Incremental Deploy",
        "# V677 V676-residual Property Incremental Deploy",
        1,
    )


v536.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
v536.DEFAULT_V535 = DEFAULT_LAYOUT
v536.APPROVAL_PHRASE = APPROVAL_PHRASE
v536.v535.live.DEFAULT_HELPER_SHA256 = HELPER_V111_SHA256
v536.v535.live.LOOKUP_KEYS = _residual_lookup_keys()
v536.decide = decide
v536.build_manifest = build_manifest
v536.render_summary = render_summary
v536.preflight = preflight


if __name__ == "__main__":
    raise SystemExit(v536.main())
