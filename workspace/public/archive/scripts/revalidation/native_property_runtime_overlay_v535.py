#!/usr/bin/env python3
"""V535 rmt_storage private property runtime overlay dry-run.

This extends the V471 private `/dev/__properties__` model with the
`rmt_storage` property keys observed in V530 stderr.  It is host-only: it does
not install files on the device, bind over global `/dev/__properties__`, create
property-service sockets, start daemons, or bring Wi-Fi up.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import native_property_runtime_overlay_v471 as base
from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v535-rmt-storage-private-property-runtime")
DEFAULT_V295 = base.DEFAULT_V295
DEFAULT_V470 = base.DEFAULT_V470
DEFAULT_ANDROID_GETPROP = base.DEFAULT_ANDROID_GETPROP

RMT_STORAGE_OBSERVED_KEYS = (
    "debug.ld.app.rmt_storage",
    "arm64.memtag.process.rmt_storage",
    "persist.log.tag.vendor.rmt_storage",
    "log.tag.vendor.rmt_storage",
    "persist.log.semlevel",
    "ro.baseband",
    "init.svc.vendor.rmt_storage",
)

COMPANION_OBSERVED_KEYS = (
    "debug.ld.app.qrtr-ns",
    "arm64.memtag.process.qrtr-ns",
    "debug.ld.app.tftp_server",
    "arm64.memtag.process.tftp_server",
    "persist.log.tag.tftp_server",
    "log.tag.tftp_server",
    "debug.ld.app.pd-mapper",
    "arm64.memtag.process.pd-mapper",
    "persist.log.tag.pd-mapper-svc",
    "log.tag.pd-mapper-svc",
    "persist.vendor.pd_locater_debug",
    "debug.ld.app.cnss_diag",
    "arm64.memtag.process.cnss_diag",
    "persist.log.tag.CNSS",
    "log.tag.CNSS",
    "debug.ld.app.cnss-daemon",
    "arm64.memtag.process.cnss-daemon",
    "persist.log.tag.cnss-daemon",
    "log.tag.cnss-daemon",
    "persist.vendor.cnss-daemon.debug_level",
    "persist.vendor.cnss-daemon.hw_trc_disable_override",
    "persist.vendor.cnss-daemon.kmsg_logging",
)

WIFI_COMPANION_OBSERVED_KEYS = tuple(dict.fromkeys(RMT_STORAGE_OBSERVED_KEYS + COMPANION_OBSERVED_KEYS))

RMT_STORAGE_FALLBACK_VALUES = {
    "debug.ld.app.rmt_storage": "",
    "arm64.memtag.process.rmt_storage": "",
    "persist.log.tag.vendor.rmt_storage": "",
    "log.tag.vendor.rmt_storage": "",
    "persist.log.semlevel": "0xFFFFFF00",
    "ro.baseband": "mdm",
    "init.svc.vendor.rmt_storage": "running",
}
RMT_STORAGE_FALLBACK_VALUES.update({key: "" for key in COMPANION_OBSERVED_KEYS})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v295-manifest", type=Path, default=DEFAULT_V295)
    parser.add_argument("--v470-analysis", type=Path, default=DEFAULT_V470)
    parser.add_argument("--android-getprop", type=Path, default=DEFAULT_ANDROID_GETPROP)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    return parser.parse_args()


def _with_rmt_keys(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    original_runtime_keys = base.RUNTIME_OBSERVED_KEYS
    original_fallback_values = dict(base.FALLBACK_VALUES)
    try:
        base.RUNTIME_OBSERVED_KEYS = tuple(dict.fromkeys(original_runtime_keys + WIFI_COMPANION_OBSERVED_KEYS))
        base.FALLBACK_VALUES.update(RMT_STORAGE_FALLBACK_VALUES)
        manifest = base.build_manifest(args, store)
    finally:
        base.RUNTIME_OBSERVED_KEYS = original_runtime_keys
        base.FALLBACK_VALUES.clear()
        base.FALLBACK_VALUES.update(original_fallback_values)

    pass_ok = bool(manifest.get("pass"))
    manifest["decision"] = (
        "v535-rmt-storage-private-property-runtime-ready"
        if pass_ok
        else "v535-rmt-storage-private-property-runtime-blocked"
    )
    manifest["reason"] = (
        "rmt_storage private property layout generated and roundtripped"
        if pass_ok
        else str(manifest.get("reason") or "blocked")
    )
    manifest["next_step"] = (
        "deploy under /mnt/sdext/a90/private-property-v317/v535 and rerun rmt_storage proof"
        if pass_ok
        else "fix private property layout before live deploy"
    )
    model = manifest.setdefault("model", {})
    model["scope"] = "host-only rmt_storage private /dev/__properties__ layout"
    model["rmt_storage_observed_keys"] = list(WIFI_COMPANION_OBSERVED_KEYS)
    manifest["rmt_storage_observed_keys"] = list(WIFI_COMPANION_OBSERVED_KEYS)
    return manifest


def _render_summary(manifest: dict[str, Any]) -> str:
    seed_rows = [[item["key"], item["value"], item["source"]] for item in manifest["seeds"]]
    mapping_rows = [
        [item["key"], item["context"], item["prop_type"], item["match_kind"], f"{item['source']}:{item['line_number']}"]
        for item in manifest["mappings"]
        if item["key"] in manifest["rmt_storage_observed_keys"]
    ]
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"]] for item in manifest["checks"]]
    return "\n".join([
        "# V535 rmt_storage Private Property Runtime Overlay Dry-run",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- property_count: `{manifest['model']['property_count']}`",
        f"- context_count: `{manifest['model']['context_count']}`",
        "",
        "## rmt_storage Observed Mappings",
        "",
        markdown_table(["key", "context", "type", "match", "source"], mapping_rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail"], check_rows),
        "",
        "## Seeds",
        "",
        markdown_table(["key", "value", "source"], seed_rows),
        "",
        "## Blocked Actions",
        "",
        "\n".join(f"- `{item}`" for item in manifest["blocked_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = _with_rmt_keys(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", _render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
