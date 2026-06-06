#!/usr/bin/env python3
"""V665 private registry snapshot path repair proof.

This proof reruns the V664 private runtime materialization gate with helper
v109, which captures registry snapshot directories from the helper's private
temp-root paths instead of the host/global `/dev` paths. It does not write DSP
boot nodes, open esoc0, write qcwlanstate, run a fresh CNSS retry, start Wi-Fi
HAL, scan/connect, use credentials, run DHCP, change routes, or ping
externally.
"""

from __future__ import annotations

from typing import Any

import native_wifi_private_runtime_materialization_v664 as v664


base = v664.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v665-private-registry-snapshot-path-repair")
base.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
base.DEFAULT_HELPER_SHA256 = "eda3e88405d15cfa2b12ef3252cef3ff25ba23aae69aeb5075700fa147150030"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v109"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v665-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v665 private registry snapshot path repair proof only; "
    "no CNSS retry, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

_v664_build_checks = base.build_checks
_v664_run_live = base.run_live
_v664_decide = base.decide
_v664_render_summary = base.render_summary
_v664_build_manifest = base.build_manifest


def _rewrite_text(text: str) -> str:
    return (
        text.replace("V664", "V665")
        .replace("v664", "v665")
        .replace("helper v108", "helper v109")
        .replace("helper-v108", "helper-v109")
        .replace("a90_android_execns_probe v108", "a90_android_execns_probe v109")
        .replace("private property/runtime materialization", "private registry snapshot path repair")
        .replace("private runtime materialization", "private registry snapshot path repair")
        .replace("private-runtime-materialization", "private-registry-snapshot-path-repair")
        .replace("private-runtime-visible-snapshot-path-gap", "private-registry-snapshot-path-gap")
    )


def _rename_check(check: base.Check) -> base.Check:
    return base.Check(
        _rewrite_text(check.name),
        check.status,
        check.severity,
        _rewrite_text(check.detail),
        [_rewrite_text(item) for item in check.evidence],
        _rewrite_text(check.next_step),
    )


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    return [_rename_check(check) for check in _v664_build_checks(args, steps, mount_preflight, v490, v525)]


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    live = _v664_run_live(args, store, steps, mount_preflight)
    live["v665_materialization_surface"] = live.get("v664_materialization_surface") or {}
    return live


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _v664_decide(args, checks, live)
    decision = _rewrite_text(decision)
    reason = _rewrite_text(reason)
    next_step = _rewrite_text(next_step)
    if decision == "v665-private-registry-snapshot-path-repair-pass":
        next_step = (
            "plan V666 fresh CNSS retry with repaired private property/runtime snapshot; "
            "keep Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external ping blocked"
        )
    if decision == "v665-private-registry-snapshot-path-gap":
        next_step = "inspect helper v109 path repair; V665 should capture private temp-root paths"
    return decision, pass_ok, reason, next_step, live_executed


def render_summary(manifest: dict[str, Any]) -> str:
    text = _rewrite_text(_v664_render_summary(manifest)).replace(
        "# V665 Private Property/Runtime Materialization Proof",
        "# V665 Private Registry Snapshot Path Repair Proof",
        1,
    )
    live = manifest.get("live") or {}
    surface = live.get("v665_materialization_surface") or live.get("v664_materialization_surface") or {}
    return "\n".join([
        text,
        "",
        "## V665 Path Repair Contract",
        "",
        f"- helper_marker: `{base.DEFAULT_HELPER_MARKER}`",
        f"- property_root: `{v664.PROPERTY_ROOT}`",
        "- expected: registry snapshot captures private temp-root `dev/__properties__` and `dev/socket` paths",
        base.markdown_table(
            ["key", "value"],
            [[key, str(value)] for key, value in sorted(surface.items()) if "capture_path" in key or key.endswith("_captured")],
        ) if surface else "- not captured",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v664_build_manifest(args, store)
    manifest["cycle"] = "v665"
    manifest["helper_marker"] = base.DEFAULT_HELPER_MARKER
    manifest["private_registry_snapshot_path_repair"] = {
        "captures_private_dev_properties_path": True,
        "captures_private_dev_socket_path": True,
        "cnss_retry_enabled": False,
        "wifi_bringup_enabled": False,
    }
    return manifest


base.build_checks = build_checks
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
