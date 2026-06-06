#!/usr/bin/env python3
"""V664 private property/runtime materialization proof.

This proof reuses the V662 service-74 gated registry/context snapshot mode and
adds the already-exported V317 private property root. The intended live check is
to prove that the private namespace now has `/dev/__properties__` and a private
`/dev/socket/property_service` shim before deciding whether to re-enable a fresh
CNSS retry. It does not write DSP boot nodes, open esoc0, write qcwlanstate,
start Wi-Fi HAL, scan/connect, use credentials, run DHCP, change routes, or ping
externally.
"""

from __future__ import annotations

from typing import Any

import native_wifi_registry_context_snapshot_v662 as v662


base = v662.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v664-private-runtime-materialization")
base.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
base.DEFAULT_HELPER_SHA256 = "103c6f5c9d423599c7dd7c551281e540e4586f451b4808d971a254420d3ed481"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v108"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v664-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v664 private property runtime materialization proof only; "
    "no CNSS retry, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
MAX_CMDV1_COMMAND_ARGS = 30

_v662_capture_preflight = base.capture_preflight
_v662_build_checks = base.build_checks
_v662_companion_command = base.companion_command
_v662_run_live = base.run_live
_v662_decide = base.decide
_v662_render_summary = base.render_summary
_v662_build_manifest = base.build_manifest

KEY_RE = base.re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")


def _rewrite_text(text: str) -> str:
    return (
        text.replace("V662", "V664")
        .replace("v662", "v664")
        .replace("registry/context snapshot", "private property/runtime materialization")
        .replace("registry snapshot", "private runtime snapshot")
    )


def capture_preflight(args: base.argparse.Namespace,
                      store: base.EvidenceStore,
                      steps: list[dict[str, Any]]) -> dict[str, Any]:
    mount_preflight = _v662_capture_preflight(args, store, steps)
    if args.command != "plan":
        base.run_step(args, store, steps, "stat-property-root", ["run", args.toybox, "stat", PROPERTY_ROOT], 10.0)
        base.run_step(args, store, steps, "ls-property-root", ["run", args.toybox, "ls", "-l", PROPERTY_ROOT], 10.0)
    return mount_preflight


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = _v662_build_checks(args, steps, mount_preflight, v490, v525)
    if args.command == "plan":
        return checks
    stat_text = base.step_payload(steps, "stat-property-root")
    ls_text = base.step_payload(steps, "ls-property-root")
    base.add_check(
        checks,
        "v317-private-property-root-present",
        "pass" if PROPERTY_ROOT in stat_text and "No such file" not in stat_text else "blocked",
        "blocker",
        f"property_root={PROPERTY_ROOT}",
        [line for line in (stat_text + "\n" + ls_text).splitlines() if PROPERTY_ROOT in line or "property" in line][:8],
        "rerun or repair V317 private property namespace export before V664",
    )
    return checks


def companion_command(args: base.argparse.Namespace) -> list[str]:
    command = _v662_companion_command(args)
    if "--property-root" not in command:
        command.extend(["--property-root", PROPERTY_ROOT])
    if len(command) > MAX_CMDV1_COMMAND_ARGS:
        raise RuntimeError(f"V664 helper command has {len(command)} args; max safe args={MAX_CMDV1_COMMAND_ARGS}")
    return command


def _intish(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _keys_from_helper_text(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.replace("\0", "\n").splitlines():
        match = KEY_RE.match(raw_line.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def _merged_companion_keys(live: dict[str, Any]) -> dict[str, str]:
    helper_text = str(live.get("v662_helper_stdout_stderr") or live.get("helper_stdout_stderr") or "")
    return {**(live.get("companion_keys") or {}), **_keys_from_helper_text(helper_text)}


def _materialization_surface(live: dict[str, Any]) -> dict[str, Any]:
    keys = _merged_companion_keys(live)
    surface = live.get("v662_surface") or {}
    registry = surface.get("registry_snapshot") or {}
    return {
        "property_root": PROPERTY_ROOT,
        "context_dev_properties_exists": keys.get("context.dev_properties.exists", ""),
        "context_dev_properties_access_r": keys.get("context.dev_properties.access_r", ""),
        "context_dev_properties_access_x": keys.get("context.dev_properties.access_x", ""),
        "context_dev_properties_host_path": keys.get("context.dev_properties.host_path", ""),
        "context_dev_socket_exists": keys.get("context.dev_socket.exists", ""),
        "property_service_shim_mode": keys.get("wifi_hal_composite_start.property_service_shim.mode", ""),
        "property_service_shim_started": keys.get("wifi_hal_composite_start.property_service_shim.started", ""),
        "property_service_socket": keys.get("wifi_hal_composite_start.property_service_shim.socket", ""),
        "property_service_shim_child_started": keys.get("wifi_hal_composite_start.property_service_shim.child_started", ""),
        "property_service_shim_request_count": keys.get("wifi_hal_composite_start.property_service_shim.request_count", ""),
        "property_service_shim_postflight_safe": keys.get("wifi_hal_composite_start.property_service_shim.postflight_safe", ""),
        "before_dev_properties_capture_path": registry.get("before_dev_properties_capture_path", keys.get("wifi_registry_snapshot.before_initial_cnss_cleanup.dev_properties_capture_path", "")),
        "after_dev_properties_capture_path": registry.get("after_dev_properties_capture_path", keys.get("wifi_registry_snapshot.after_initial_cnss_cleanup.dev_properties_capture_path", "")),
        "before_dev_socket_capture_path": registry.get("before_dev_socket_capture_path", keys.get("wifi_registry_snapshot.before_initial_cnss_cleanup.dev_socket_capture_path", "")),
        "after_dev_socket_capture_path": registry.get("after_dev_socket_capture_path", keys.get("wifi_registry_snapshot.after_initial_cnss_cleanup.dev_socket_capture_path", "")),
        "before_dirs_captured": registry.get("before_dirs_captured", ""),
        "after_dirs_captured": registry.get("after_dirs_captured", ""),
        "before_end": registry.get("before_end", ""),
        "after_end": registry.get("after_end", ""),
    }


def run_live(args: base.argparse.Namespace,
             store: base.EvidenceStore,
             steps: list[dict[str, Any]],
             mount_preflight: dict[str, Any]) -> dict[str, Any]:
    live = _v662_run_live(args, store, steps, mount_preflight)
    live["v664_materialization_surface"] = _materialization_surface(live)
    return live


def _materialization_passed(surface: dict[str, Any]) -> bool:
    return (
        surface.get("context_dev_properties_exists") == "1"
        and surface.get("context_dev_properties_access_r") == "1"
        and surface.get("context_dev_properties_access_x") == "1"
        and surface.get("property_service_shim_started") == "1"
        and surface.get("property_service_socket") == "/dev/socket/property_service"
        and surface.get("property_service_shim_postflight_safe") == "1"
        and _intish(surface.get("before_dirs_captured")) >= 2
        and _intish(surface.get("after_dirs_captured")) >= 2
        and surface.get("before_end") == "1"
        and surface.get("after_end") == "1"
    )


def _runtime_visible(surface: dict[str, Any]) -> bool:
    return (
        surface.get("context_dev_properties_exists") == "1"
        and surface.get("context_dev_properties_access_r") == "1"
        and surface.get("context_dev_properties_access_x") == "1"
        and surface.get("property_service_shim_started") == "1"
        and surface.get("property_service_socket") == "/dev/socket/property_service"
    )


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return (
            "v664-private-runtime-materialization-plan-ready",
            True,
            "plan-only; no device command executed",
            "refresh current-boot V490, confirm V317 property root, then run V664 preflight",
            False,
        )
    blocked = base.blockers(checks)
    if blocked:
        return "v664-private-runtime-materialization-blocked", False, "blocked by " + ", ".join(blocked), "resolve blockers before V664", False
    if args.command == "preflight":
        return (
            "v664-private-runtime-materialization-preflight-ready",
            True,
            "preflight ready; live run needs exact approval and uses reboot cleanup",
            "run V664 live proof",
            False,
        )
    decision, pass_ok, reason, next_step, live_executed = _v662_decide(args, checks, live)
    if args.command != "run" or not live or not live_executed:
        return _rewrite_text(decision), pass_ok, _rewrite_text(reason), _rewrite_text(next_step), live_executed
    materialization = live.get("v664_materialization_surface") or {}
    if not pass_ok:
        return _rewrite_text(decision), pass_ok, _rewrite_text(reason), _rewrite_text(next_step), live_executed
    if decision != "v662-registry-context-snapshot-pass":
        return _rewrite_text(decision), pass_ok, _rewrite_text(reason), _rewrite_text(next_step), live_executed
    if _materialization_passed(materialization):
        return (
            "v664-private-runtime-materialization-pass",
            True,
            f"materialization={materialization}",
            "plan V665 fresh CNSS retry with private property/runtime surface; keep Wi-Fi HAL, scan/connect, credentials, DHCP, routes, and external ping blocked",
            live_executed,
        )
    if (
        _runtime_visible(materialization)
        and materialization.get("before_end") == "1"
        and materialization.get("after_end") == "1"
        and _intish(materialization.get("before_dirs_captured")) == 0
        and _intish(materialization.get("after_dirs_captured")) == 0
    ):
        return (
            "v664-private-runtime-visible-snapshot-path-gap",
            True,
            f"materialization={materialization}",
            "build V665 helper snapshot repair so registry capture reads the private temp-root paths before enabling CNSS retry",
            live_executed,
        )
    return (
        "v664-private-runtime-materialization-incomplete",
        True,
        f"materialization={materialization}",
        "classify why property root or private property_service socket did not appear before enabling CNSS retry",
        live_executed,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    text = _rewrite_text(_v662_render_summary(manifest)).replace(
        "# V664 Registry/Context Snapshot Proof",
        "# V664 Private Property/Runtime Materialization Proof",
        1,
    )
    live = manifest.get("live") or {}
    materialization = live.get("v664_materialization_surface") or {}
    return "\n".join([
        text,
        "",
        "## V664 Private Runtime Surface",
        "",
        f"- property_root: `{PROPERTY_ROOT}`",
        base.markdown_table(
            ["key", "value"],
            [[key, str(value)] for key, value in sorted(materialization.items())],
        ) if materialization else "- not captured",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v662_build_manifest(args, store)
    manifest["cycle"] = "v664"
    manifest["property_root"] = PROPERTY_ROOT
    manifest["private_runtime_materialization"] = {
        "adds_property_root": True,
        "expects_property_service_shim": True,
        "cnss_retry_enabled": False,
        "wifi_bringup_enabled": False,
    }
    return manifest


base.capture_preflight = capture_preflight
base.build_checks = build_checks
base.companion_command = companion_command
base.run_live = run_live
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
