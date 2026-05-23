#!/usr/bin/env python3
"""V676 V535 property-seeded Android userspace-order proof.

This proof replays the V671 service74-gated Android userspace-order path with
the V535 private property root that already covers the V675 property targets.
It does not start supplicant, scan, connect, use credentials, run DHCP, change
routes, or ping externally.
"""

from __future__ import annotations

import collections
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_service74_android_order_v671 as v671


base = v671.base
v666 = v671.v668.v666

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v676-v535-property-android-order")
base.APPROVAL_PHRASE = (
    "approve v676 V535 property-seeded Android userspace-order start-only proof only; "
    "no supplicant, no scan/connect/link-up, no DHCP and no external ping"
)

V535_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v535/dev/__properties__"
DEFAULT_V675 = base.Path("tmp/wifi/v675-property-binder-targets/manifest.json")
DEFAULT_V535 = base.Path("tmp/wifi/v535-rmt-storage-private-property-runtime/manifest.json")
PROPERTY_DENIAL_RE = re.compile(
    r'(?:Could not find context for property|Access denied finding property) "([^"]+)"',
    re.I,
)
BINDER_FAILURE_RE = re.compile(r"binder:.*(?:transaction failed|ioctl).*?-22", re.I)

v666.PROPERTY_ROOT = V535_PROPERTY_ROOT

_v671_build_checks = base.build_checks
_v671_companion_command = base.companion_command
_v671_run_live = base.run_live
_v671_decide = base.decide
_v671_render_summary = base.render_summary
_v671_build_manifest = base.build_manifest


def _load_json(path: Path) -> dict[str, Any]:
    resolved = base.repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def _coverage() -> dict[str, Any]:
    v675 = _load_json(DEFAULT_V675)
    v535 = _load_json(DEFAULT_V535)
    targets = [
        item for item in v675.get("property_targets", [])
        if isinstance(item, dict) and item.get("key")
    ]
    seed_by_key = {
        str(item.get("key")): item
        for item in v535.get("seeds", [])
        if isinstance(item, dict) and item.get("key")
    }
    mapping_by_key = {
        str(item.get("key")): item
        for item in v535.get("mappings", [])
        if isinstance(item, dict) and item.get("key")
    }
    missing_seed = [str(item["key"]) for item in targets if str(item["key"]) not in seed_by_key]
    missing_mapping = [
        str(item["key"]) for item in targets
        if str(item["key"]) not in mapping_by_key or mapping_by_key[str(item["key"])].get("status") != "pass"
    ]
    runtime_keys = [str(item["key"]) for item in targets if item.get("category") == "runtime_required"]
    runtime_seeded = [
        key for key in runtime_keys
        if key in seed_by_key and str(seed_by_key[key].get("value", "")) != ""
    ]
    return {
        "v675_decision": v675.get("decision"),
        "v675_pass": bool(v675.get("pass")),
        "v675_path": v675.get("path"),
        "v535_decision": v535.get("decision"),
        "v535_pass": bool(v535.get("pass")),
        "v535_path": v535.get("path"),
        "target_count": len(targets),
        "missing_seed": missing_seed,
        "missing_mapping": missing_mapping,
        "runtime_keys": runtime_keys,
        "runtime_seeded": runtime_seeded,
        "covered": bool(targets) and not missing_seed and not missing_mapping and set(runtime_seeded) == set(runtime_keys),
    }


def _runtime_surface(live: dict[str, Any]) -> dict[str, Any]:
    helper_text = str(live.get("helper_stdout_stderr") or "")
    dmesg_text = str(live.get("dmesg_delta") or "")
    denials = collections.Counter(match.group(1) for match in PROPERTY_DENIAL_RE.finditer(helper_text))
    binder_failures = BINDER_FAILURE_RE.findall(dmesg_text)
    return {
        "property_denial_total": sum(denials.values()),
        "property_denial_unique": len(denials),
        "property_denial_top": [[key, count] for key, count in denials.most_common(16)],
        "binder_failure_count": len(binder_failures),
    }


def _rewrite(text: str) -> str:
    return (
        text.replace("V671", "V676")
        .replace("v671", "v676")
        .replace("Android userspace-order", "V535 property-seeded Android userspace-order")
        .replace("V317 private property root", "V535 private property root")
        .replace("/mnt/sdext/a90/private-property-v317/dev/__properties__", V535_PROPERTY_ROOT)
    )


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = [
        base.Check(
            _rewrite(check.name),
            check.status,
            check.severity,
            _rewrite(check.detail),
            [_rewrite(item) for item in check.evidence],
            _rewrite(check.next_step),
        )
        for check in _v671_build_checks(args, steps, mount_preflight, v490, v525)
    ]
    coverage = _coverage()
    base.add_check(
        checks,
        "v675-property-target-input",
        "pass" if coverage["v675_decision"] == "v675-property-binder-targets-classified" and coverage["v675_pass"] else "blocked",
        "blocker",
        f"decision={coverage['v675_decision']} pass={coverage['v675_pass']} targets={coverage['target_count']}",
        [str(coverage["v675_path"])],
        "run V675 before V676",
    )
    base.add_check(
        checks,
        "v535-property-layout-covers-v675-targets",
        "pass" if coverage["covered"] else "blocked",
        "blocker",
        (
            f"v535_decision={coverage['v535_decision']} pass={coverage['v535_pass']} "
            f"missing_seed={coverage['missing_seed']} missing_mapping={coverage['missing_mapping']} "
            f"runtime_seeded={coverage['runtime_seeded']}"
        ),
        [str(coverage["v535_path"])],
        "regenerate V535/V676 property layout before live replay",
    )
    if args.command != "plan":
        stat_text = base.step_payload(steps, "stat-property-root")
        base.add_check(
            checks,
            "v535-remote-property-root-present",
            "pass" if V535_PROPERTY_ROOT in stat_text and "No such file" not in stat_text else "blocked",
            "blocker",
            f"property_root={V535_PROPERTY_ROOT}",
            [line for line in stat_text.splitlines() if V535_PROPERTY_ROOT in line or "No such file" in line][:8],
            "deploy V535 property root before V676 live replay",
        )
    return checks


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = _v671_companion_command(args)
    for index, item in enumerate(command):
        if item == "--property-root" and index + 1 < len(command):
            command[index + 1] = V535_PROPERTY_ROOT
            break
    else:
        command.extend(["--property-root", V535_PROPERTY_ROOT])
    return command


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    live = _v671_run_live(args, store, steps, mount_preflight)
    live["v676_property_runtime_surface"] = _runtime_surface(live)
    live["v676_property_target_coverage"] = _coverage()
    return live


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _v671_decide(args, checks, live)
    decision = _rewrite(decision)
    reason = _rewrite(reason)
    next_step = _rewrite(next_step)
    if args.command != "run" or not live or not live_executed:
        return decision, pass_ok, reason, next_step, live_executed

    surface = live.get("v676_property_runtime_surface") or {}
    counts = live.get("v655_counts") or {}
    wifi_advanced = any(int(counts.get(name) or 0) > 0 for name in (
        "qmi_server_connected",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    ))
    if wifi_advanced:
        return (
            "v676-v535-property-wifi-surface-advanced",
            True,
            f"V535 property-seeded replay advanced lower Wi-Fi markers; counts={counts}; property_surface={surface}",
            "classify WLFW/BDF/wlan0 state before supplicant or scan/connect",
            live_executed,
        )
    if surface.get("property_denial_total", 0) == 0:
        return (
            "v676-v535-property-clean-binder-gap-classified",
            True,
            f"V535 property root removed V675 property denials; binder_failures={surface.get('binder_failure_count')} counts={counts}",
            "plan a narrow Binder registration/transaction repair or capture before supplicant/scan/connect",
            live_executed,
        )
    return (
        "v676-v535-property-gap-persists",
        True,
        f"V535 property root used but property denials remain; property_surface={surface}; counts={counts}",
        "compare remaining denials against V675 and extend property layout before another Binder repair",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _rewrite(_v671_render_summary(manifest)).replace(
        "# V676 Service74 V535 property-seeded Android Userspace-order Proof",
        "# V676 V535 Property-seeded Android Userspace-order Proof",
        1,
    )
    live = manifest.get("live") or {}
    property_surface = live.get("v676_property_runtime_surface") or {}
    coverage = live.get("v676_property_target_coverage") or manifest.get("v676_property_target_coverage") or {}
    return "\n".join([
        text,
        "",
        "## V676 Property Target Coverage",
        "",
        f"- property_root: `{V535_PROPERTY_ROOT}`",
        f"- v675_target_count: `{coverage.get('target_count', '')}`",
        f"- v535_covers_v675_targets: `{coverage.get('covered', '')}`",
        f"- missing_seed: `{coverage.get('missing_seed', [])}`",
        f"- missing_mapping: `{coverage.get('missing_mapping', [])}`",
        f"- runtime_seeded: `{coverage.get('runtime_seeded', [])}`",
        "",
        "## V676 Runtime Property Surface",
        "",
        f"- property_denial_total: `{property_surface.get('property_denial_total', '')}`",
        f"- property_denial_unique: `{property_surface.get('property_denial_unique', '')}`",
        f"- binder_failure_count: `{property_surface.get('binder_failure_count', '')}`",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v671_build_manifest(args, store)
    live = manifest.get("live") or {}
    coverage = _coverage()
    manifest["cycle"] = "v676"
    manifest["property_root"] = V535_PROPERTY_ROOT
    manifest["v676_property_target_coverage"] = coverage
    manifest["v676_property_runtime_surface"] = live.get("v676_property_runtime_surface") if live else {}
    manifest["required_approval_phrase"] = base.APPROVAL_PHRASE
    manifest["explicitly_approved"] = [
        "helper v111 service74-gated Android userspace-order start-only mode",
        "servicemanager, hwservicemanager, and vndservicemanager start-only inside bounded private namespace",
        "Wi-Fi HAL legacy/ext and wificond start-only inside bounded private namespace",
        "QRTR companion services, cnss_diag, initial cnss-daemon, and one retry cnss-daemon start-only inside bounded private namespace",
        "V535 private property root bind and property service shim inside helper namespace",
        "WLFW QRTR nameservice readback without QMI payload",
        "reboot cleanup boundary after live proof",
    ] if args.command == "run" and base.approved(args) else []
    manifest["explicitly_not_approved"] = [
        "sysfs writes or subsystem state writes",
        "direct ADSP/CDSP/SLPI boot-node writes",
        "esoc0 open/hold",
        "supplicant or hostapd start",
        "IWifi.start transaction, qcwlanstate, or sysfs driver-state writes",
        "Wi-Fi scan/connect/link-up/credential/DHCP/routing/external ping",
        "boot image changes or partition writes",
    ]
    return manifest


base.build_checks = build_checks
base.companion_command = companion_command
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
