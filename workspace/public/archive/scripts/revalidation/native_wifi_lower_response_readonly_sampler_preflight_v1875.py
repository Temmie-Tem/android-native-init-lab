#!/usr/bin/env python3
"""V1875 host-only preflight for the V1874 lower-response sampler artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1875-lower-response-readonly-sampler-preflight"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1875_LOWER_RESPONSE_READONLY_SAMPLER_PREFLIGHT_2026-06-03.md"
)
DEFAULT_V1874_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1874-lower-response-readonly-sampler-test-boot"
    / "manifest.json"
)
DEFAULT_V1874_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1874_LOWER_RESPONSE_READONLY_SAMPLER_SOURCE_BUILD_2026-06-03.md"
)


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


def strings_contains(path: Path, marker: str) -> bool:
    if not path.exists():
        return False
    proc = subprocess.run(
        ["strings", str(path)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return marker in proc.stdout


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    manifest = read_json(args.v1874_manifest)
    report_text = read_text(args.v1874_report)
    boot_image = REPO_ROOT / str(manifest.get("boot_image", ""))
    helper_binary = args.v1874_manifest.parent / "a90_android_execns_probe_v357"
    wifi_test = manifest.get("wifi_test", {})
    helper_sha = sha256(helper_binary) if helper_binary.exists() else ""
    boot_sha = sha256(boot_image) if boot_image.exists() else ""
    checks = {
        "v1874_manifest_present": bool(manifest),
        "v1874_decision_pass": manifest.get("decision") == "v1874-lower-response-readonly-sampler-source-build-pass",
        "v1874_report_present": "v1874-lower-response-readonly-sampler-source-build-pass" in report_text,
        "helper_exists": helper_binary.exists(),
        "boot_image_exists": boot_image.exists(),
        "helper_sha_matches_manifest": helper_sha == manifest.get("helper_sha256"),
        "boot_sha_matches_manifest": boot_sha == manifest.get("boot_sha256"),
        "helper_marker_v357_present": strings_contains(helper_binary, "a90_android_execns_probe v357"),
        "helper_contract_strings_present": strings_contains(helper_binary, "wlan_pd_lower_response_input_contract"),
        "boot_init_build_present": strings_contains(boot_image, "v1874-lower-response-readonly-sampler"),
        "boot_property_root_present": strings_contains(boot_image, "/mnt/sdext/a90/private-property-v317/v1874/dev/__properties__"),
        "boot_helper_result_present": strings_contains(boot_image, "/cache/native-init-wifi-test-boot-v1874-helper.result"),
        "private_sdx50m_route_enabled": wifi_test.get("private_cnss_daemon_sdx50m") is True,
        "lower_observer_mode_enabled": wifi_test.get("helper_runtime_mode") == "wifi-companion-wlan-pd-post-pm-lower-state-observer-start-only",
        "firmware_mounts_enabled": wifi_test.get("firmware_mounts") is True,
        "debugfs_mount_enabled_for_readonly_snapshots": wifi_test.get("mount_debugfs") is True,
        "scan_connect_credentials_blocked": wifi_test.get("scan_connect_credentials") is False,
        "rc1_writes_blocked": not any(
            bool(wifi_test.get(key))
            for key in [
                "rc1_sysfs_client_enumerate",
                "rc1_window_sampler",
                "rc1_endpoint_sampler",
                "rc1_immediate_endpoint_sampler",
                "pid1_rc1_watcher",
                "pcie1_clock_vote_proof",
                "pcie1_clock_vote_async",
            ]
        ),
    }
    pass_ok = all(checks.values())
    return {
        "cycle": "V1875",
        "type": "host-only V1874 lower-response sampler artifact preflight",
        "decision": (
            "v1875-lower-response-readonly-sampler-preflight-pass"
            if pass_ok
            else "v1875-lower-response-readonly-sampler-preflight-review"
        ),
        "label": "lower-response-readonly-sampler-live-ready" if pass_ok else "review",
        "pass": pass_ok,
        "reason": (
            "V1874 boot/helper artifacts are present, hash-matched, v357-marked, and configured for a read-only lower-response sampler with scan/connect and RC1 write paths blocked."
        ),
        "checks": checks,
        "artifacts": {
            "manifest": rel(args.v1874_manifest),
            "report": rel(args.v1874_report),
            "helper_binary": rel(helper_binary),
            "boot_image": rel(boot_image),
            "helper_sha256": helper_sha,
            "boot_sha256": boot_sha,
        },
        "next_gate": {
            "cycle": "V1876",
            "type": "one-run rollbackable live handoff",
            "boot_image": rel(boot_image),
            "required_stop": "do not attempt Wi-Fi connect or ping unless WLFW service 69 and wlan0 are both present",
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    artifacts = result["artifacts"]
    next_gate = result["next_gate"]
    return "\n".join([
        "# Native Init V1875 Lower Response Read-only Sampler Preflight",
        "",
        "## Summary",
        "",
        "- Cycle: `V1875`",
        "- Type: host-only V1874 lower-response sampler artifact preflight",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Reason: {result['reason']}",
        "- Evidence: `tmp/wifi/v1875-lower-response-readonly-sampler-preflight`",
        "",
        "## Checks",
        "",
        "| check | value |",
        "|---|---:|",
        *(f"| `{key}` | `{value}` |" for key, value in checks.items()),
        "",
        "## Artifacts",
        "",
        f"- Manifest: `{artifacts['manifest']}`",
        f"- Report: `{artifacts['report']}`",
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
        "V1875 is host-only. It does not contact the device, flash, reboot, start services, open `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1874-manifest", type=Path, default=DEFAULT_V1874_MANIFEST)
    parser.add_argument("--v1874-report", type=Path, default=DEFAULT_V1874_REPORT)
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
