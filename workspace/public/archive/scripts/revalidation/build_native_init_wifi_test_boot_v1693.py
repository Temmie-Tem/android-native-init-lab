#!/usr/bin/env python3
"""Build V1693 WLAN-PD cnss-daemon non-log control-flow test boot."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_bytes, write_private_text
from wifi_property_serializer_proof import PropAreaBuilder, find_property_in_area, find_property_info

import build_native_init_wifi_test_boot_v1393 as base


OUT_DIR = base.REPO_ROOT / "tmp" / "wifi" / "v1693-wlan-pd-cnss-nonlog-control-flow-test-boot"
PROPERTY_RUNTIME_DIR = OUT_DIR / "property-runtime"
PROPERTY_ROOT = PROPERTY_RUNTIME_DIR / "layout" / "dev" / "__properties__"
REMOTE_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v1693/dev/__properties__"
V535_MANIFEST = base.REPO_ROOT / "tmp" / "wifi" / "v535-rmt-storage-private-property-runtime" / "manifest.json"
REPORT_PATH = (
    base.REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1693_WLAN_PD_CNSS_NONLOG_CONTROL_FLOW_SOURCE_BUILD_2026-06-02.md"
)
CNSS_PROPERTY_OVERRIDES = {
    "persist.vendor.cnss-daemon.kmsg_logging": "1",
    "persist.vendor.cnss-daemon.debug_level": "4",
}
DEFAULT_ARGS = [
    "--cycle",
    "V1693",
    "--decision",
    "v1693-wlan-pd-cnss-nonlog-control-flow-source-build-pass",
    "--cycle-label",
    "v1693",
    "--init-version",
    "0.9.125",
    "--init-build",
    "v1693-wlan-pd-cnss-nonlog-control-flow",
    "--out-dir",
    str(OUT_DIR),
    "--init-binary",
    str(OUT_DIR / "init_v1693_wlan_pd_cnss_nonlog_control_flow"),
    "--helper-binary",
    str(OUT_DIR / "a90_android_execns_probe_v311"),
    "--ramdisk-cpio",
    str(OUT_DIR / "ramdisk_v1693_wlan_pd_cnss_nonlog_control_flow.cpio"),
    "--boot-image",
    str(OUT_DIR / "boot_linux_v1693_wlan_pd_cnss_nonlog_control_flow.img"),
    "--wifi-test-klog-prefix",
    "A90v1693",
    "--wifi-test-disable",
    "/cache/native-init-wifi-test-boot-v1693.disable",
    "--wifi-test-log",
    "/cache/native-init-wifi-test-boot-v1693.log",
    "--wifi-test-summary",
    "/cache/native-init-wifi-test-boot-v1693.summary",
    "--wifi-test-helper-result",
    "/cache/native-init-wifi-test-boot-v1693-helper.result",
    "--wifi-test-pid",
    "/cache/native-init-wifi-test-boot-v1693.pid",
    "--wifi-test-watcher-pid",
    "/cache/native-init-wifi-test-boot-v1693-supervisor.pid",
    "--wifi-test-watch-sec",
    "55",
    "--wifi-test-supervise-helper",
    "--wifi-test-supervisor-timeout-sec",
    "80",
    "--wifi-test-firmware-mounts",
    "--wifi-test-property-root",
    REMOTE_PROPERTY_ROOT,
    "--wifi-test-helper-mode",
    "wlan-pd-cnss-output-visibility",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.REPO_ROOT))
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    return base.sha256(path)


def write_binary(path: Path, payload: bytes) -> dict[str, Any]:
    write_private_bytes(path, payload)
    path.chmod(0o600)
    return {
        "relative_path": rel(path),
        "bytes": len(payload),
        "sha256": sha256_file(path),
    }


def load_v535_manifest() -> dict[str, Any]:
    if not V535_MANIFEST.exists():
        raise RuntimeError(f"missing V535 manifest: {V535_MANIFEST}")
    manifest = json.loads(V535_MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("decision") != "v535-rmt-storage-private-property-runtime-ready" or not manifest.get("pass"):
        raise RuntimeError(f"V535 manifest is not ready: decision={manifest.get('decision')} pass={manifest.get('pass')}")
    return manifest


def build_cnss_property_runtime() -> dict[str, Any]:
    manifest = load_v535_manifest()
    source_root = V535_MANIFEST.parent / "layout" / "dev" / "__properties__"
    source_property_info = source_root / "property_info"
    if not source_property_info.exists():
        raise RuntimeError(f"missing V535 property_info: {source_property_info}")

    if PROPERTY_RUNTIME_DIR.exists():
        shutil.rmtree(PROPERTY_RUNTIME_DIR)
    PROPERTY_ROOT.mkdir(parents=True, mode=0o700)

    property_info = source_property_info.read_bytes()
    seed_values = {str(item["key"]): str(item["value"]) for item in manifest.get("seeds", [])}
    seed_values.update(CNSS_PROPERTY_OVERRIDES)

    properties_by_context: dict[str, list[tuple[str, str]]] = {}
    for mapping in manifest.get("mappings", []):
        if mapping.get("status") != "pass" or not mapping.get("context"):
            continue
        key = str(mapping.get("key"))
        if key not in seed_values:
            continue
        properties_by_context.setdefault(str(mapping["context"]), []).append((key, seed_values[key]))

    files: list[dict[str, Any]] = []
    files.append({"role": "property_info", **write_binary(PROPERTY_ROOT / "property_info", property_info)})
    files.append({"role": "properties_serial", **write_binary(PROPERTY_ROOT / "properties_serial", PropAreaBuilder().bytes())})
    for context, properties in sorted(properties_by_context.items()):
        builder = PropAreaBuilder()
        for key, value in sorted(properties):
            builder.add(key, value)
        files.append({"role": "context_prop_area", "context": context, **write_binary(PROPERTY_ROOT / context, builder.bytes())})

    checks: list[dict[str, Any]] = []
    for key, expected_value in CNSS_PROPERTY_OVERRIDES.items():
        context, prop_type = find_property_info(property_info, key)
        area_path = PROPERTY_ROOT / str(context)
        actual_value = find_property_in_area(area_path.read_bytes(), key) if context and area_path.exists() else None
        checks.append({
            "name": key,
            "status": "pass" if context and prop_type == "string" and actual_value == expected_value else "blocked",
            "context": context,
            "type": prop_type,
            "expected": expected_value,
            "actual": actual_value,
        })
    pass_ok = all(check["status"] == "pass" for check in checks)
    return {
        "decision": "v1693-cnss-nonlog-property-runtime-ready" if pass_ok else "v1693-cnss-nonlog-property-runtime-blocked",
        "pass": pass_ok,
        "source_manifest": rel(V535_MANIFEST),
        "local_property_root": rel(PROPERTY_ROOT),
        "remote_property_root": REMOTE_PROPERTY_ROOT,
        "overrides": CNSS_PROPERTY_OVERRIDES,
        "files": files,
        "checks": checks,
    }


def render_report(manifest: dict[str, Any]) -> str:
    wifi = manifest["wifi_test"]
    property_runtime = manifest["cnss_nonlog_property_runtime"]
    check_lines = [
        f"- `{item['name']}`: `{item['actual']}` in `{item['context']}`"
        for item in property_runtime["checks"]
    ]
    return "\n".join([
        "# Native Init V1693 WLAN-PD cnss-daemon Non-log Control-flow Source Build",
        "",
        "## Summary",
        "",
        "- Cycle: `V1693`",
        "- Type: source/build-only rollbackable WLAN-PD cnss-daemon non-log control-flow test boot artifact",
        f"- Decision: `{manifest['decision']}`",
        "- Result: PASS",
        "- Reason: preserves the V1680/V1691 internal-modem route and adds read-only `/proc` non-log cnss-daemon control-flow fallback fields",
        f"- Manifest: `{rel(OUT_DIR / 'manifest.json')}`",
        f"- Boot image: `{manifest['boot_image']}`",
        f"- Boot SHA256: `{manifest['boot_sha256']}`",
        f"- Init: `A90 Linux init {manifest['init_version']} ({manifest['init_build']})`",
        f"- Helper marker: `{manifest['helper_marker']}`",
        f"- Helper SHA256: `{manifest['helper_sha256']}`",
        "",
        "## Route",
        "",
        f"- Helper runtime mode: `{wifi['helper_runtime_mode']}`",
        f"- Property root: `{wifi['property_root']}`",
        "- Actors: `qrtr-ns`, `pd-mapper`, `rmt_storage`, `tftp_server`, `/dev/subsys_modem` holder, `cnss_diag`, stock `cnss-daemon`",
        "- New evidence prefix: `wlan_pd_cnss_nonlog_control_flow.*`.",
        "- The new fallback does not write tracefs and does not arm uprobes; it records PID, maps load-bias, computed `wlfw_start` runtime PC, fd/socket counts, task state, and MHI/ks absence.",
        "- No service-manager, PM trio, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
        "",
        "## Property Runtime",
        "",
        *check_lines,
        "",
        "## Live Labels",
        "",
        "- `cnss-process-exited-before-wlfw`",
        "- `cnss-uprobe-unavailable-fallback-needed`",
        "- Existing output labels remain captured through `wlan_pd_cnss_output_visibility.label`.",
        "",
        "## Safety Scope",
        "",
        "This build script performed host-side source/build work only. It did not issue device commands, flash, reboot, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE` spoof, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def main() -> int:
    property_runtime = build_cnss_property_runtime()
    if not property_runtime["pass"]:
        raise RuntimeError("blocked property runtime checks: " + json.dumps(property_runtime["checks"], indent=2))
    run_args = [*DEFAULT_ARGS, *sys.argv[1:]]
    rc = base.main(run_args)
    if rc != 0:
        return rc
    manifest_path = OUT_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["pass"] = True
    manifest["source_build_only"] = True
    manifest["device_command"] = False
    manifest["cnss_nonlog_property_runtime"] = property_runtime
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_private_text(REPORT_PATH, render_report(manifest))
    print(f"report={rel(REPORT_PATH)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
