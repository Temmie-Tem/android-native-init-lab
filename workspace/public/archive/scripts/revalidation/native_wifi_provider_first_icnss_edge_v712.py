#!/usr/bin/env python3
"""V712 provider-first CNSS retry proof with helper v121 ICNSS edge capture."""

from __future__ import annotations

from typing import Any

import native_wifi_provider_first_cnss_v708 as v708


base = v708.base
v700 = v708.v700

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v712-provider-first-icnss-edge-v121")
base.DEFAULT_HELPER_SHA256 = "547232ddb352740bb7a7f1d0f9116162584e34a536b9d9b77869ed8d838e7c89"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v121"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v712-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v712 provider-first ICNSS edge v121 capture proof only; "
    "no Wi-Fi HAL start, no scan/connect/link-up, no DHCP and no external ping"
)

v700.V700_USAGE_TOKENS = (
    v700.V700_MODE,
    "a90_android_execns_probe v121",
    "--property-root",
    "--allow-service-manager-start-only",
    "--allow-qrtr-ns-readback",
)


def _icnss_edge_surface(keys: dict[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in keys.items():
        if key.startswith("wifi_companion_start.icnss_edge_"):
            result[key] = value
        elif key.startswith("wifi_icnss_edge."):
            result[key] = value
        elif "wifi_icnss_edge_" in key:
            result[key] = value
        elif key.endswith(".icnss_edge_captured"):
            result[key] = value
    return result


def _icnss_edge_captured(surface: dict[str, str]) -> bool:
    return (
        surface.get("wifi_companion_start.cnss2_focus_service74_open.icnss_edge_captured") == "1"
        or surface.get("wifi_companion_start.cnss2_focus_window.icnss_edge_captured") == "1"
        or surface.get("wifi_companion_start.icnss_edge_service74_open.begin") == "1"
        or surface.get("wifi_companion_start.icnss_edge_window.begin") == "1"
    )


_base_build_checks = v708._v700_build_checks
_base_decide = v708._v700_decide
_base_render_summary = v708._v700_render_summary
_base_build_manifest = v708._v700_build_manifest


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = _base_build_checks(args, steps, mount_preflight, v490, v525)
    if args.command == "plan":
        return checks
    usage = base.step_payload(steps, "helper-usage")
    sha_text = base.step_payload(steps, "sha-helper")
    helper_ready = args.helper_sha256 in sha_text and args.helper_marker in usage
    base.add_check(
        checks,
        "helper-v121-icnss-edge-contract",
        "pass" if helper_ready else "blocked",
        "blocker",
        "remote helper must match the helper v121 build statically verified for ICNSS edge capture",
        [
            line
            for line in (sha_text + "\n" + usage).splitlines()
            if args.helper_marker in line or args.helper_sha256 in line or "provider-first-cnss" in line
        ][:20],
        "deploy helper v121 before V712 live proof",
    )
    return checks


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _base_decide(args, checks, live)
    decision = decision.replace("v700", "v712")
    reason = reason.replace("v119", "v121").replace("V700", "V712")
    next_step = next_step.replace("v119", "v121").replace("V700", "V712")
    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed
    keys = v700._keys(live)
    edge = _icnss_edge_surface(keys)
    live["v712_icnss_edge_surface"] = edge
    live["v712_icnss_edge_captured"] = _icnss_edge_captured(edge)
    if not live["v712_icnss_edge_captured"]:
        return (
            "v712-provider-first-icnss-edge-capture-missing",
            False,
            f"provider-first path ran but v121 ICNSS edge capture was missing; prior={decision}",
            "inspect helper v121 capture placement before another live retry",
            live_executed,
        )
    if decision == "v712-provider-first-cnss-gap-persists":
        return (
            "v712-provider-first-icnss-edge-captured-gap-persists",
            True,
            reason + "; ICNSS edge surface captured",
            "classify ICNSS-QMI/WLFW edge surface before Wi-Fi HAL or scan/connect",
            live_executed,
        )
    return decision, pass_ok, reason + "; ICNSS edge surface captured", next_step, live_executed


def render_summary(manifest: dict[str, Any]) -> str:
    text = _base_render_summary(manifest).replace("V700", "V712").replace("v119", "v121")
    live = manifest.get("live") or {}
    edge = live.get("v712_icnss_edge_surface") or {}
    rows = [[key, value] for key, value in sorted(edge.items())]
    return "\n".join([
        text,
        "",
        "## V712 ICNSS Edge Snapshot",
        "",
        f"- helper_marker: `{base.DEFAULT_HELPER_MARKER}`",
        f"- icnss_edge_captured: `{live.get('v712_icnss_edge_captured', '')}`",
        "",
        base.markdown_table(["key", "value"], rows) if rows else "- not captured",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _base_build_manifest(args, store)
    live = manifest.get("live") or {}
    if isinstance(live, dict):
        keys = v700._keys(live)
        edge = _icnss_edge_surface(keys)
        live["v712_icnss_edge_surface"] = edge
        live["v712_icnss_edge_captured"] = _icnss_edge_captured(edge)
    manifest["cycle"] = "v712"
    manifest["helper_version"] = "v121"
    manifest["decision"] = str(manifest.get("decision", "")).replace("v700", "v712")
    manifest["reason"] = str(manifest.get("reason", "")).replace("v119", "v121").replace("V700", "V712")
    manifest["next_step"] = str(manifest.get("next_step", "")).replace("v119", "v121").replace("V700", "V712")
    manifest["icnss_edge_captured"] = bool(live.get("v712_icnss_edge_captured")) if isinstance(live, dict) else False
    if (
        manifest["decision"] == "v712-provider-first-cnss-gap-persists"
        and manifest["icnss_edge_captured"]
    ):
        manifest["decision"] = "v712-provider-first-icnss-edge-captured-gap-persists"
        manifest["reason"] = str(manifest.get("reason", "")) + "; ICNSS edge surface captured"
        manifest["next_step"] = "classify ICNSS-QMI/WLFW edge surface before Wi-Fi HAL or scan/connect"
    manifest["explicitly_approved"] = [
        str(item).replace("v119", "v121")
        for item in manifest.get("explicitly_approved", [])
    ]
    return manifest


base.build_checks = build_checks
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
