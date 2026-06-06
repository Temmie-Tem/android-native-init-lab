#!/usr/bin/env python3
"""V1881 host-only preflight for the V1880 delayed lower-response sampler."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1881-delayed-lower-readonly-sampler-preflight"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1881_DELAYED_LOWER_READONLY_SAMPLER_PREFLIGHT_2026-06-03.md"
)
DEFAULT_V1879_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1879_ANDROID_DELAYED_LOWER_TIMING_RECONCILE_2026-06-03.md"
)
DEFAULT_V1880_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1880-delayed-lower-readonly-sampler-test-boot"
    / "manifest.json"
)
DEFAULT_V1880_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1880_DELAYED_LOWER_READONLY_SAMPLER_SOURCE_BUILD_2026-06-03.md"
)


HELPER_MARKERS = [
    "a90_android_execns_probe v358",
    "wlan_pd_lower_response_input_contract.%s.offsets_seconds",
    "post_powerup_delayed",
    "offsets_seconds=0,1,2,5,10,20,30,60,90,120,150,180,210,240,250,260,300",
    "source=android-good-delayed-private-sdx50m-readonly-window",
    "no_esoc0_open=1",
    "no_rc_sel_case_write=1",
    "no_pci_rescan_or_bind=1",
    "no_wifi_hal_scan_connect=1",
]


RC1_WRITE_KEYS = [
    "rc1_sysfs_client_enumerate",
    "rc1_window_sampler",
    "rc1_endpoint_sampler",
    "rc1_focused_endpoint_sampler",
    "rc1_immediate_endpoint_sampler",
    "rc1_micro_endpoint_sampler",
    "rc1_micro_focused_endpoint_sampler",
    "rc1_micro_batched_focused_endpoint_sampler",
    "rc1_micro_critical_fast_endpoint_sampler",
    "rc1_micro_source_timestamped_sampler",
    "rc1_case_aligned_micro_endpoint_sampler",
    "pid1_rc1_watcher",
    "pcie1_clock_vote_proof",
    "pcie1_clock_vote_async",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def strings_output(path: Path) -> str:
    if not path.exists():
        return ""
    proc = subprocess.run(
        ["strings", str(path)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return proc.stdout


def all_strings_present(output: str, markers: list[str]) -> bool:
    return all(marker in output for marker in markers)


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    manifest = read_json(args.v1880_manifest)
    v1879_report_text = read_text(args.v1879_report)
    v1880_report_text = read_text(args.v1880_report)
    boot_image = REPO_ROOT / str(manifest.get("boot_image", ""))
    helper_binary = args.v1880_manifest.parent / "a90_android_execns_probe_v358"
    wifi_test = manifest.get("wifi_test", {})
    helper_sha = sha256(helper_binary) if helper_binary.exists() else ""
    boot_sha = sha256(boot_image) if boot_image.exists() else ""
    helper_strings = strings_output(helper_binary)
    boot_strings = strings_output(boot_image)
    checks = {
        "v1879_report_selected_delayed_sampler": (
            "v1879-android-delayed-lower-timing-selects-readonly-long-sampler-host-pass"
            in v1879_report_text
            and "private-sdx50m-delayed-lower-readonly-sampler-source-build"
            in v1879_report_text
        ),
        "v1880_manifest_present": bool(manifest),
        "v1880_decision_pass": manifest.get("decision") == "v1880-delayed-lower-readonly-sampler-source-build-pass",
        "v1880_report_present": "v1880-delayed-lower-readonly-sampler-source-build-pass" in v1880_report_text,
        "helper_exists": helper_binary.exists(),
        "boot_image_exists": boot_image.exists(),
        "helper_sha_matches_manifest": helper_sha == manifest.get("helper_sha256"),
        "boot_sha_matches_manifest": boot_sha == manifest.get("boot_sha256"),
        "helper_delayed_contract_strings_present": all_strings_present(helper_strings, HELPER_MARKERS),
        "boot_init_build_present": "v1880-delayed-lower-readonly-sampler" in boot_strings,
        "boot_property_root_present": "/mnt/sdext/a90/private-property-v317/v1880/dev/__properties__" in boot_strings,
        "boot_helper_result_present": "/cache/native-init-wifi-test-boot-v1880-helper.result" in boot_strings,
        "private_sdx50m_route_enabled": wifi_test.get("private_cnss_daemon_sdx50m") is True,
        "lower_observer_mode_enabled": (
            wifi_test.get("helper_runtime_mode")
            == "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only"
        ),
        "firmware_mounts_enabled": wifi_test.get("firmware_mounts") is True,
        "debugfs_mount_enabled_for_readonly_snapshots": wifi_test.get("mount_debugfs") is True,
        "supervisor_long_enough_for_delayed_window": (
            wifi_test.get("watch_sec") == 330
            and wifi_test.get("supervisor_timeout_sec") == 360
        ),
        "scan_connect_credentials_blocked": wifi_test.get("scan_connect_credentials") is False,
        "rc1_writes_blocked": not any(bool(wifi_test.get(key)) for key in RC1_WRITE_KEYS),
    }
    pass_ok = all(checks.values())
    return {
        "cycle": "V1881",
        "type": "host-only V1880 delayed lower-response sampler artifact preflight",
        "decision": (
            "v1881-delayed-lower-readonly-sampler-preflight-pass"
            if pass_ok
            else "v1881-delayed-lower-readonly-sampler-preflight-review"
        ),
        "label": "delayed-lower-readonly-sampler-live-ready" if pass_ok else "review",
        "pass": pass_ok,
        "reason": (
            "V1880 boot/helper artifacts are present, hash-matched, v358-marked, and configured for the Android-good delayed read-only lower-response window with scan/connect and RC1 write paths blocked."
        ),
        "checks": checks,
        "artifacts": {
            "v1879_report": rel(args.v1879_report),
            "v1880_manifest": rel(args.v1880_manifest),
            "v1880_report": rel(args.v1880_report),
            "helper_binary": rel(helper_binary),
            "boot_image": rel(boot_image),
            "helper_sha256": helper_sha,
            "boot_sha256": boot_sha,
        },
        "delayed_window": {
            "source": "android-good-delayed-private-sdx50m-readonly-window",
            "offsets_seconds": [0, 1, 2, 5, 10, 20, 30, 60, 90, 120, 150, 180, 210, 240, 250, 260, 300],
            "watch_sec": wifi_test.get("watch_sec"),
            "supervisor_timeout_sec": wifi_test.get("supervisor_timeout_sec"),
        },
        "next_gate": {
            "cycle": "V1882",
            "type": "one-run rollbackable live delayed lower-response read-only handoff",
            "boot_image": rel(boot_image),
            "required_stop": "do not attempt Wi-Fi connect or ping unless WLFW service 69 and wlan0 are both present",
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    artifacts = result["artifacts"]
    delayed_window = result["delayed_window"]
    next_gate = result["next_gate"]
    offsets = ",".join(str(offset) for offset in delayed_window["offsets_seconds"])
    return "\n".join([
        "# Native Init V1881 Delayed Lower Read-only Sampler Preflight",
        "",
        "## Summary",
        "",
        "- Cycle: `V1881`",
        "- Type: host-only V1880 delayed lower-response sampler artifact preflight",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Reason: {result['reason']}",
        "- Evidence: `tmp/wifi/v1881-delayed-lower-readonly-sampler-preflight`",
        "",
        "## Checks",
        "",
        "| check | value |",
        "|---|---:|",
        *(f"| `{key}` | `{value}` |" for key, value in checks.items()),
        "",
        "## Delayed Window",
        "",
        f"- Source: `{delayed_window['source']}`",
        f"- Offsets seconds: `{offsets}`",
        f"- PID1 watch/supervisor seconds: `{delayed_window['watch_sec']}` / `{delayed_window['supervisor_timeout_sec']}`",
        "",
        "## Artifacts",
        "",
        f"- V1879 report: `{artifacts['v1879_report']}`",
        f"- V1880 manifest: `{artifacts['v1880_manifest']}`",
        f"- V1880 report: `{artifacts['v1880_report']}`",
        f"- Helper binary: `{artifacts['helper_binary']}`",
        f"- Helper SHA256: `{artifacts['helper_sha256']}`",
        f"- Boot image: `{artifacts['boot_image']}`",
        f"- Boot SHA256: `{artifacts['boot_sha256']}`",
        "",
        "## Next",
        "",
        f"- Cycle: `{next_gate['cycle']}`",
        f"- Type: `{next_gate['type']}`",
        f"- Boot image: `{next_gate['boot_image']}`",
        f"- Required stop: {next_gate['required_stop']}",
        "",
        "## Safety Scope",
        "",
        "V1881 is host-only. It does not contact the device, flash, reboot, start services, open `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1879-report", type=Path, default=DEFAULT_V1879_REPORT)
    parser.add_argument("--v1880-manifest", type=Path, default=DEFAULT_V1880_MANIFEST)
    parser.add_argument("--v1880-report", type=Path, default=DEFAULT_V1880_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_result(args)
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    report = render_report(result)
    store.write_text("summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "label": result["label"],
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
