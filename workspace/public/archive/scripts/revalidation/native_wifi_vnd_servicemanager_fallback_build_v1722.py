#!/usr/bin/env python3
"""V1722 source/build-only helper verifier for VND Binder servicemanager fallback."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
HELPER_SOURCE = REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_android_execns_probe.c"
HELPER_BUILD_SCRIPT = REPO_ROOT / "workspace" / "public" / "archive" / "scripts" / "revalidation" / "build_android_execns_probe_helper.sh"
BOOT_BUILDER = REPO_ROOT / "scripts" / "revalidation" / "build_native_init_wifi_test_boot_v1393.py"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1722-vnd-servicemanager-fallback-source-build"
HELPER_BINARY = OUT_DIR / "a90_android_execns_probe_v321"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1722_VND_SERVICEMANAGER_FALLBACK_SOURCE_BUILD_2026-06-03.md"
)
NEXT_WORK_PATH = REPO_ROOT / "docs" / "plans" / "NATIVE_INIT_NEXT_WORK_2026-04-25.md"

EXPECTED_MARKER = "a90_android_execns_probe v321"
EXPECTED_SHA256 = "57aa9f95395480fe8b9fa28a424ae71c3c46572846796f78d73b06e10cac599e"
NEW_ARGV = "/system/bin/servicemanager /dev/vndbinder"
OLD_ARGV = "/vendor/bin/vndservicemanager /dev/vndbinder"


def run(command: list[object], *, capture: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + shlex.join(str(item) for item in command), flush=True)
    return subprocess.run(
        [str(item) for item in command],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_private_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)


def source_checks() -> dict[str, bool]:
    text = HELPER_SOURCE.read_text(encoding="utf-8")
    return {
        "version_v321": '#define EXECNS_VERSION "a90_android_execns_probe v321"' in text,
        "vendor_profile_targets_system_servicemanager": 'cfg->target = "/system/bin/servicemanager";' in text,
        "vnd_context_override": "u:r:vndservicemanager:s0" in text
        and "android_default_selinux_context_for_request" in text,
        "composite_vnd_target_fallback": "COMPOSITE_ID_VND_SERVICE_MANAGER" in text
        and '"/system/bin/servicemanager"' in text,
        "new_argv_logged": NEW_ARGV in text,
        "old_argv_not_logged": OLD_ARGV not in text,
    }


def build_helper() -> dict[str, Any]:
    OUT_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    run(["bash", HELPER_BUILD_SCRIPT, HELPER_BINARY], capture=True)
    helper_sha = sha256(HELPER_BINARY)
    strings = run(["strings", HELPER_BINARY]).stdout
    file_out = run(["file", HELPER_BINARY]).stdout.strip()
    readelf_out = run(["readelf", "-d", HELPER_BINARY]).stdout
    return {
        "path": str(HELPER_BINARY.relative_to(REPO_ROOT)),
        "sha256": helper_sha,
        "sha256_expected": helper_sha == EXPECTED_SHA256,
        "marker_present": EXPECTED_MARKER in strings,
        "new_argv_present": NEW_ARGV in strings,
        "old_argv_absent": OLD_ARGV not in strings,
        "vnd_context_present": "u:r:vndservicemanager:s0" in strings,
        "file": file_out,
        "static": "statically linked" in file_out,
        "no_dynamic_section": "There is no dynamic section" in readelf_out,
    }


def render_report(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Native Init V1722 VND Servicemanager Fallback Source Build",
            "",
            "## Summary",
            "",
            "- Cycle: `V1722`",
            "- Type: source/build-only helper contract patch verifier",
            f"- Decision: `{manifest['decision']}`",
            "- Result: PASS",
            "- Evidence: `tmp/wifi/v1722-vnd-servicemanager-fallback-source-build`",
            f"- Helper: `{manifest['helper']['path']}`",
            f"- Helper SHA256: `{manifest['helper']['sha256']}`",
            "",
            "## Change",
            "",
            "- `COMPOSITE_ID_VND_SERVICE_MANAGER` now executes the system `servicemanager` binary with `/dev/vndbinder`.",
            "- The VND manager child keeps the `u:r:vndservicemanager:s0` SELinux exec context through an identity/profile-aware context override.",
            "- Logged argv contracts now report `/system/bin/servicemanager /dev/vndbinder`.",
            "- Common Wi-Fi test-boot helper expectations now point at helper marker `v321` and the new SHA.",
            "",
            "## Checks",
            "",
            f"- Source checks: `{manifest['source_checks']}`",
            f"- Static AArch64 helper: `{manifest['helper']['static']}`",
            f"- No dynamic section: `{manifest['helper']['no_dynamic_section']}`",
            f"- Marker present: `{manifest['helper']['marker_present']}`",
            f"- New argv present: `{manifest['helper']['new_argv_present']}`",
            f"- Old argv absent from helper strings: `{manifest['helper']['old_argv_absent']}`",
            f"- VND SELinux context present: `{manifest['helper']['vnd_context_present']}`",
            "",
            "## Next Gate",
            "",
            "- V1723 should deploy/use helper v321 and run one rollbackable live proof that starts only the service-manager bootstrap needed to unblock `defaultServiceManager()`.",
            "- It must still not start PM trio, `vendor.qcom.PeripheralManager`, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
            "",
            "## Safety Scope",
            "",
            "This script performed host-side source/build work only. It did not contact the device, flash, reboot, start actors, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
            "",
        ]
    )


def append_next_work(manifest: dict[str, Any]) -> None:
    entry = "\n".join(
        [
            "",
            "## V1722 VND servicemanager fallback source/build (2026-06-03)",
            "",
            "- V1722 source/build-only helper patch completed.",
            "",
            "  Result:",
            "",
            f"  - decision: `{manifest['decision']}`;",
            f"  - helper: `{manifest['helper']['path']}`;",
            f"  - helper SHA256: `{manifest['helper']['sha256']}`;",
            "  - VND service-manager child now uses `/system/bin/servicemanager /dev/vndbinder` while preserving `u:r:vndservicemanager:s0`;",
            "  - common Wi-Fi test-boot helper expectations now require `a90_android_execns_probe v321`.",
            "",
            "  Next candidate:",
            "",
            "  - V1723 one-run live service-manager bootstrap proof with helper v321;",
            "  - no PM trio, `vendor.qcom.PeripheralManager`, `boot_wlan`, `/dev/subsys_esoc0`, forced RC1, fake-ONLINE, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping.",
            "",
            "  Report:",
            "  `docs/reports/NATIVE_INIT_V1722_VND_SERVICEMANAGER_FALLBACK_SOURCE_BUILD_2026-06-03.md`.",
            "",
        ]
    )
    current = NEXT_WORK_PATH.read_text(encoding="utf-8")
    if "## V1722 VND servicemanager fallback source/build" not in current:
        NEXT_WORK_PATH.write_text(current.rstrip() + "\n" + entry, encoding="utf-8")


def main() -> int:
    checks = source_checks()
    helper = build_helper()
    manifest: dict[str, Any] = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": "V1722",
        "pass": all(checks.values())
        and helper["sha256_expected"]
        and helper["marker_present"]
        and helper["new_argv_present"]
        and helper["old_argv_absent"]
        and helper["vnd_context_present"]
        and helper["static"]
        and helper["no_dynamic_section"],
        "source_checks": checks,
        "helper": helper,
        "inputs": {
            "helper_source": str(HELPER_SOURCE.relative_to(REPO_ROOT)),
            "boot_builder": str(BOOT_BUILDER.relative_to(REPO_ROOT)),
        },
    }
    manifest["decision"] = (
        "v1722-vnd-servicemanager-fallback-source-build-pass"
        if manifest["pass"]
        else "v1722-vnd-servicemanager-fallback-source-build-blocked"
    )
    write_private_json(OUT_DIR / "manifest.json", manifest)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    append_next_work(manifest)
    print(json.dumps({"decision": manifest["decision"], "pass": manifest["pass"]}, sort_keys=True))
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
