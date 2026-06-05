#!/usr/bin/env python3
"""V800 provider-first ICNSS edge proof with already-deployed helper v124.

This keeps the proven V712 provider-first/ICNSS-edge capture contract but
rebases it to the current stock native image and helper already present on the
device. It remains below Wi-Fi HAL, scan/connect, credentials, DHCP, routes,
and external ping.
"""

from __future__ import annotations

from typing import Any

import native_wifi_provider_first_icnss_edge_v712 as v712


base = v712.base
v700 = v712.v700

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v800-provider-first-icnss-edge-v124")
base.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"
base.DEFAULT_HELPER_SHA256 = "d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v124"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v800-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v800 provider-first ICNSS edge v124 replay proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping"
)

v700.V700_USAGE_TOKENS = (
    v700.V700_MODE,
    "a90_android_execns_probe v124",
    "--property-root",
    "--allow-service-manager-start-only",
    "--allow-qrtr-ns-readback",
)

_v712_decide = base.decide
_v712_render_summary = base.render_summary
_v712_build_manifest = base.build_manifest


def _rewrite_text(text: str) -> str:
    return (
        text.replace("v712", "v800")
        .replace("V712", "V800")
        .replace("v121", "v124")
        .replace("helper v121", "helper v124")
        .replace("a90_android_execns_probe v121", "a90_android_execns_probe v124")
    )


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _v712_decide(args, checks, live)
    if isinstance(live, dict):
        edge = live.get("v712_icnss_edge_surface") or {}
        live["v800_icnss_edge_surface"] = edge
        live["v800_icnss_edge_captured"] = bool(live.get("v712_icnss_edge_captured"))
    return (
        _rewrite_text(decision),
        pass_ok,
        _rewrite_text(reason),
        _rewrite_text(next_step),
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _rewrite_text(_v712_render_summary(manifest))
    live = manifest.get("live") or {}
    edge = live.get("v800_icnss_edge_surface") or live.get("v712_icnss_edge_surface") or {}
    rows = [[key, value] for key, value in sorted(edge.items())]
    return "\n".join([
        text,
        "",
        "## V800 v124 Replay",
        "",
        f"- helper_marker: `{base.DEFAULT_HELPER_MARKER}`",
        f"- expect_version: `{base.DEFAULT_EXPECT_VERSION}`",
        f"- icnss_edge_captured: `{live.get('v800_icnss_edge_captured', live.get('v712_icnss_edge_captured', ''))}`",
        "",
        base.markdown_table(["key", "value"], rows) if rows else "- not captured",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v712_build_manifest(args, store)
    manifest["cycle"] = "v800"
    manifest["helper_version"] = "v124"
    manifest["decision"] = _rewrite_text(str(manifest.get("decision", "")))
    manifest["reason"] = _rewrite_text(str(manifest.get("reason", "")))
    manifest["next_step"] = _rewrite_text(str(manifest.get("next_step", "")))
    live = manifest.get("live") or {}
    if isinstance(live, dict):
        edge = live.get("v712_icnss_edge_surface") or {}
        live["v800_icnss_edge_surface"] = edge
        live["v800_icnss_edge_captured"] = bool(live.get("v712_icnss_edge_captured"))
        manifest["icnss_edge_captured"] = bool(live.get("v800_icnss_edge_captured"))
        manifest["icnss_edge_surface"] = edge
    manifest["explicitly_approved"] = [
        _rewrite_text(str(item)) for item in manifest.get("explicitly_approved", [])
    ]
    manifest["explicitly_not_approved"] = [
        _rewrite_text(str(item)) for item in manifest.get("explicitly_not_approved", [])
    ]
    return manifest


base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
