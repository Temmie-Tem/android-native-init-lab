#!/usr/bin/env python3
"""V662 service-74 gated registry/context snapshot proof.

This proof reuses the V659 service-74 gate and vndservicemanager readiness
sequence, then captures read-only Binder debug/property context snapshots before
any fresh cnss-daemon retry. It does not write DSP boot nodes, open esoc0,
write qcwlanstate, start Wi-Fi HAL, scan/connect, use credentials, run DHCP,
change routes, or ping externally.
"""

from __future__ import annotations

from typing import Any

import native_wifi_vndservicemanager_cnss_retry_v655 as v655


base = v655.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v662-registry-context-snapshot")
base.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
base.DEFAULT_HELPER_SHA256 = "103c6f5c9d423599c7dd7c551281e540e4586f451b4808d971a254420d3ed481"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v108"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v662-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v662 registry context snapshot proof only; "
    "no CNSS retry, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

V662_MODE = "wifi-companion-service74-gated-vnd-service-manager-registry-snapshot-start-only"
EXPECTED_ORDER = (
    "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,"
    "service74_gate,servicemanager,hwservicemanager,vndservicemanager,"
    "vndservicemanager_ready,registry_snapshot"
)
V662_KEY_RE = base.re.compile(r"^((?:wifi_registry_snapshot|wifi_companion_start)\.[A-Za-z0-9_.-]+)=(.*)$")

v655.V655_MODE = V662_MODE
v655.EXPECTED_ORDER = EXPECTED_ORDER

_v655_build_checks = v655.build_checks
_v655_run_live = v655.run_live
_v655_render_summary = v655.render_summary
_v655_build_manifest = v655.build_manifest


def _rewrite_text(text: str) -> str:
    return (
        text.replace("V655", "V662")
        .replace("v655", "v662")
        .replace("helper v106", "helper v108")
        .replace("helper-v106", "helper-v108")
        .replace("a90_android_execns_probe v106", "a90_android_execns_probe v108")
        .replace("vndservicemanager-readiness plus fresh cnss-daemon retry", "registry/context snapshot")
        .replace("CNSS retry", "registry snapshot")
        .replace("cnss retry", "registry snapshot")
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


def _v662_keys_from_text(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = V662_KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = [_rename_check(check) for check in _v655_build_checks(args, steps, mount_preflight, v490, v525)]
    if args.command != "plan":
        usage = base.step_payload(steps, "helper-usage")
        sha_text = base.step_payload(steps, "sha-helper")
        base.add_check(
            checks,
            "helper-v108-registry-snapshot-contract",
            "pass"
            if (
                args.helper_sha256 in sha_text
                and args.helper_marker in usage
                and V662_MODE in usage
            )
            else "blocked",
            "blocker",
            "remote helper SHA, marker, and usage mode must match V662 registry snapshot helper",
            [
                line
                for line in (sha_text + "\n" + usage).splitlines()
                if args.helper_sha256 in line
                or args.helper_marker in line
                or V662_MODE in line
            ][:12],
            "build and deploy helper v108 before V662",
        )
    return checks


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    result = _v655_run_live(args, store, steps, mount_preflight)
    helper_text = base.step_payload(steps, "companion-start-only-with-holder")
    keys = {**(result.get("companion_keys") or {}), **_v662_keys_from_text(helper_text)}
    surface = result.get("v655_surface") or {}
    registry = {
        "enabled": keys.get("wifi_companion_start.registry_snapshot.enabled", ""),
        "before_enabled": keys.get("wifi_companion_start.registry_snapshot.before_initial_cnss_cleanup", ""),
        "before_files_captured": keys.get("wifi_registry_snapshot.before_initial_cnss_cleanup.files_captured", ""),
        "before_dirs_captured": keys.get("wifi_registry_snapshot.before_initial_cnss_cleanup.dirs_captured", ""),
        "before_child_proc_captured": keys.get("wifi_registry_snapshot.before_initial_cnss_cleanup.child_proc_captured", ""),
        "before_end": keys.get("wifi_registry_snapshot.before_initial_cnss_cleanup.end", ""),
        "after_files_captured": keys.get("wifi_registry_snapshot.after_initial_cnss_cleanup.files_captured", ""),
        "after_dirs_captured": keys.get("wifi_registry_snapshot.after_initial_cnss_cleanup.dirs_captured", ""),
        "after_child_proc_captured": keys.get("wifi_registry_snapshot.after_initial_cnss_cleanup.child_proc_captured", ""),
        "after_end": keys.get("wifi_registry_snapshot.after_initial_cnss_cleanup.end", ""),
    }
    surface["registry_snapshot"] = registry
    surface["initial_cnss_daemon"] = {
        "index": keys.get("wifi_companion_start.initial_cnss_daemon.index", ""),
        "observable": keys.get("wifi_companion_start.initial_cnss_daemon.observable", ""),
        "cleanup_safe": keys.get("wifi_companion_start.initial_cnss_daemon.cleanup_safe", ""),
    }
    result["v662_surface"] = surface
    result["v662_counts"] = result.get("v655_counts") or {}
    result["v662_helper_stdout_stderr"] = helper_text
    return result


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v662-registry-context-snapshot-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v108, refresh V641/V490 prerequisites, then run V662 preflight",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v662-registry-context-snapshot-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V662", False
    if args.command == "preflight":
        return (
            "v662-registry-context-snapshot-preflight-ready",
            True,
            "preflight ready; live run needs exact approval and uses reboot cleanup",
            "run V662 live proof",
            False,
        )
    if not base.approved(args):
        return "v662-registry-context-snapshot-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V662 approval", False
    if not live:
        return "v662-registry-context-snapshot-review-required", False, "missing live result", "inspect runner failure", True

    reboot = live.get("reboot_cleanup") or {}
    if not reboot.get("version_seen") or not reboot.get("status_healthy"):
        return "v662-cleanup-review", False, f"reboot_cleanup={reboot}", "verify device manually before continuing", True
    if not live.get("holder_started") or not (live.get("qrtr_rx_wait") or {}).get("seen"):
        return "v662-lower-modem-blocked", False, "subsys_modem holder did not reproduce QRTR RX", "restore lower modem readiness before V662", True
    if not live.get("companion_executed") or not live.get("all_postflight_safe"):
        return "v662-cleanup-review", False, f"helper_result={live.get('helper_result')} all_postflight_safe={live.get('all_postflight_safe')}", "inspect companion transcript before retry", True

    surface = live.get("v662_surface") or {}
    service74_gate = surface.get("service74_gate") or {}
    vnd_ready = surface.get("vndservicemanager_readiness") or {}
    initial_cnss = surface.get("initial_cnss_daemon") or {}
    cnss_retry = surface.get("cnss_retry") or {}
    registry = surface.get("registry_snapshot") or {}
    service_manager_executed = (
        surface.get("with_service_manager") == "1"
        and surface.get("with_vnd_service_manager") == "1"
        and surface.get("order") == EXPECTED_ORDER
        and surface.get("service_manager_started") == "1"
    )
    if service74_gate.get("seen") != "1" or service74_gate.get("open") != "1":
        return (
            "v662-service74-gate-timeout",
            True,
            (
                f"gate_status={service74_gate.get('status')} "
                f"final_74={service74_gate.get('final_count_74')} "
                f"wait_ms={service74_gate.get('wait_ms')}"
            ),
            "registry snapshot was correctly withheld; classify lower service74 regression before retry",
            True,
        )
    if not service_manager_executed:
        return "v662-service-manager-not-executed", False, f"surface={surface}", "inspect helper mode and approval propagation", True
    if cnss_retry.get("enabled") != "0" or cnss_retry.get("retry_start_order"):
        return (
            "v662-cnss-retry-guard-failed",
            False,
            f"cnss_retry={cnss_retry}",
            "stop; V662 must not run the fresh cnss-daemon retry tail",
            True,
        )
    if vnd_ready.get("ready") != "1" or initial_cnss.get("cleanup_safe") != "1":
        return (
            "v662-readiness-blocked",
            True,
            f"vndservicemanager_readiness={vnd_ready} initial_cnss={initial_cnss}",
            "inspect readiness before registry snapshot",
            True,
        )
    if registry.get("enabled") != "1" or registry.get("before_end") != "1" or registry.get("after_end") != "1":
        return (
            "v662-registry-snapshot-incomplete",
            False,
            f"registry_snapshot={registry}",
            "inspect helper v108 snapshot capture before retry",
            True,
        )
    return (
        "v662-registry-context-snapshot-pass",
        True,
        f"registry_snapshot={registry}",
        "classify snapshot evidence, then decide whether property namespace or service registration needs repair before CNSS retry",
        True,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _rewrite_text(_v655_render_summary(manifest)).replace(
        "# V662 vndservicemanager Readiness + registry snapshot Proof",
        "# V662 Registry/Context Snapshot Proof",
        1,
    )
    live = manifest.get("live") or {}
    surface = live.get("v662_surface") or {}
    registry = surface.get("registry_snapshot") or {}
    return "\n".join([
        text,
        "",
        "## V662 Registry Snapshot Contract",
        "",
        f"- expected_order: `{EXPECTED_ORDER}`",
        f"- observed_order: `{surface.get('order', '')}`",
        f"- cnss_retry_enabled: `{(surface.get('cnss_retry') or {}).get('enabled', '')}`",
        f"- registry_snapshot_enabled: `{registry.get('enabled', '')}`",
        "",
        "## V662 Registry Snapshot",
        "",
        base.markdown_table(
            ["key", "value"],
            [[key, str(value)] for key, value in sorted(registry.items())],
        ) if registry else "- none",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v655_build_manifest(args, store)
    manifest["cycle"] = "v662"
    manifest["registry_snapshot_mode"] = V662_MODE
    manifest["expected_order"] = EXPECTED_ORDER
    return manifest


base.build_checks = build_checks
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
