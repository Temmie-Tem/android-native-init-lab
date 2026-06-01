#!/usr/bin/env python3
"""V1394 local-only sanity verifier for the V1393 Wi-Fi test boot artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_V1393_MANIFEST = REPO_ROOT / "tmp" / "wifi" / "v1393-wifi-test-boot" / "manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1394-wifi-test-boot-artifact-sanity"
DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1394_WIFI_TEST_BOOT_ARTIFACT_SANITY_2026-06-01.md"
EXPECTED_DECISION = "v1393-wifi-test-boot-source-build-pass"
EXPECTED_BOOT_MARKERS = (
    "A90 Linux init 0.9.69 (v1393-wifitest)",
    "a90_android_execns_probe v286",
    "A90v1393: wifi test boot armed",
    "native-init-wifi-test-boot-v1393",
    "wifi-v1393-test-boot",
    "/bin/a90_android_execns_probe",
)
EXPECTED_RAMDISK_ENTRIES = (
    "init",
    "bin/a90_android_execns_probe",
    "bin/a90_tcpctl",
    "bin/a90_rshell",
)
FORBIDDEN_BYTES = (
    bytes([116, 101, 109, 109, 105, 101, 48, 50, 49, 52]),
    bytes([116, 101, 109, 109, 105, 101, 53, 71]),
)


def run(command: list[object], *, capture: bool = True, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(item) for item in command],
        cwd=str(cwd) if cwd else None,
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


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def mode_octal(path: Path) -> str:
    return oct(stat.S_IMODE(path.lstat().st_mode))


def check_file_sha(manifest: dict[str, Any], key: str, sha_key: str) -> dict[str, Any]:
    path = repo_path(str(manifest[key]))
    exists = path.exists()
    actual = sha256(path) if exists else ""
    expected = str(manifest[sha_key])
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "exists": exists,
        "expected_sha256": expected,
        "actual_sha256": actual,
        "sha256_ok": exists and actual == expected,
        "mode": mode_octal(path) if exists else "",
    }


def check_static(path: Path) -> dict[str, Any]:
    dynamic = run(["aarch64-linux-gnu-readelf", "-d", path]).stdout
    headers = run(["aarch64-linux-gnu-readelf", "-l", path]).stdout
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "no_dynamic_section": "There is no dynamic section" in dynamic,
        "no_interp": "INTERP" not in headers,
    }


def check_ramdisk(path: Path) -> dict[str, Any]:
    listing = run(["bash", "-lc", f"cpio -it < {shlex.quote(str(path))}"]).stdout.splitlines()
    missing = [entry for entry in EXPECTED_RAMDISK_ENTRIES if entry not in listing]
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "entry_count": len(listing),
        "missing": missing,
        "entries_ok": not missing,
    }


def check_boot_markers(path: Path) -> dict[str, Any]:
    strings = run(["strings", path]).stdout
    missing = [marker for marker in EXPECTED_BOOT_MARKERS if marker not in strings]
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "missing": missing,
        "markers_ok": not missing,
    }


def check_no_forbidden(paths: list[Path]) -> dict[str, Any]:
    hits: list[str] = []
    for path in paths:
        data = path.read_bytes()
        if any(needle in data for needle in FORBIDDEN_BYTES):
            hits.append(str(path.relative_to(REPO_ROOT)))
    return {
        "hits": hits,
        "ok": not hits,
    }


def unpack_boot(path: Path, out_dir: Path) -> tuple[list[str], Path]:
    text = run([
        "python3",
        REPO_ROOT / "mkbootimg" / "unpack_bootimg.py",
        "--boot_img",
        path,
        "--out",
        out_dir,
        "--format=mkbootimg",
    ]).stdout
    return shlex.split(text), out_dir / "kernel"


def mkboot_arg_map(args: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    index = 0
    while index < len(args):
        key = args[index]
        if key.startswith("--") and index + 1 < len(args):
            result[key] = args[index + 1]
            index += 2
        else:
            index += 1
    return result


def check_header_parity(base_boot: Path, test_boot: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="a90-v1394-base-") as base_name, \
            tempfile.TemporaryDirectory(prefix="a90-v1394-test-") as test_name:
        base_args, base_kernel = unpack_boot(base_boot, Path(base_name))
        test_args, test_kernel = unpack_boot(test_boot, Path(test_name))
        base_map = mkboot_arg_map(base_args)
        test_map = mkboot_arg_map(test_args)
        ignored = {"--kernel", "--ramdisk"}
        compared = sorted((set(base_map) | set(test_map)) - ignored)
        mismatches = [
            {
                "key": key,
                "base": base_map.get(key, ""),
                "test": test_map.get(key, ""),
            }
            for key in compared
            if key not in ignored and base_map.get(key, "") != test_map.get(key, "")
        ]
        base_kernel_sha = sha256(base_kernel)
        test_kernel_sha = sha256(test_kernel)
    return {
        "mismatches": mismatches,
        "header_args_ok": not mismatches,
        "base_kernel_sha256": base_kernel_sha,
        "test_kernel_sha256": test_kernel_sha,
        "kernel_sha256_ok": base_kernel_sha == test_kernel_sha,
    }


def decision(checks: dict[str, Any]) -> tuple[str, bool, str]:
    required = [
        checks["manifest"].get("decision_ok"),
        checks["base_boot"].get("exists"),
        checks["files"]["init_binary"].get("sha256_ok"),
        checks["files"]["helper"].get("sha256_ok"),
        checks["files"]["ramdisk"].get("sha256_ok"),
        checks["files"]["boot"].get("sha256_ok"),
        checks["static"]["init_binary"].get("no_dynamic_section"),
        checks["static"]["init_binary"].get("no_interp"),
        checks["static"]["helper"].get("no_dynamic_section"),
        checks["static"]["helper"].get("no_interp"),
        checks["ramdisk"].get("entries_ok"),
        checks["boot_markers"].get("markers_ok"),
        checks["header_parity"].get("header_args_ok"),
        checks["header_parity"].get("kernel_sha256_ok"),
        checks["forbidden_bytes"].get("ok"),
        checks["private_modes"].get("ok"),
    ]
    pass_ok = all(bool(item) for item in required)
    if pass_ok:
        return (
            "v1394-wifi-test-boot-artifact-sanity-pass",
            True,
            "V1393 staged test boot artifact passed local sanity checks; V1395 may be planned as a separate rollbackable live handoff",
        )
    return (
        "v1394-wifi-test-boot-artifact-sanity-blocked",
        False,
        "artifact sanity checks failed; fix local artifact before any flash handoff",
    )


def render_summary(manifest: dict[str, Any], result: dict[str, Any]) -> str:
    lines = [
        "# V1394 Wi-Fi Test Boot Artifact Sanity",
        "",
        f"- decision: `{result['decision']}`",
        f"- pass: `{result['pass']}`",
        f"- reason: {result['reason']}",
        f"- v1393 manifest: `{manifest['_path']}`",
        f"- boot image: `{manifest['boot_image']}`",
        f"- boot sha256: `{manifest['boot_sha256']}`",
        "",
        "## Safety",
        "",
        "- local-only artifact verification",
        "- no device command",
        "- no flash/reboot/partition write",
        "- no Wi-Fi HAL, scan/connect, DHCP/routes, or external ping",
        "",
    ]
    return "\n".join(lines)


def render_report(manifest: dict[str, Any], result: dict[str, Any]) -> str:
    checks = result["checks"]
    return "\n".join([
        "# Native Init V1394 Wi-Fi Test Boot Artifact Sanity",
        "",
        "## Summary",
        "",
        "- Cycle: `V1394`",
        "- Type: local-only artifact sanity verifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- V1393 manifest: `{manifest['_path']}`",
        f"- V1393 boot image: `{manifest['boot_image']}`",
        "",
        "## Checks",
        "",
        f"- manifest decision: `{checks['manifest']['decision_ok']}`",
        f"- base boot exists: `{checks['base_boot']['exists']}`",
        f"- init static: `{checks['static']['init_binary']['no_dynamic_section'] and checks['static']['init_binary']['no_interp']}`",
        f"- helper static: `{checks['static']['helper']['no_dynamic_section'] and checks['static']['helper']['no_interp']}`",
        f"- ramdisk entries: `{checks['ramdisk']['entries_ok']}`",
        f"- boot markers: `{checks['boot_markers']['markers_ok']}`",
        f"- header parity: `{checks['header_parity']['header_args_ok']}`",
        f"- kernel parity: `{checks['header_parity']['kernel_sha256_ok']}`",
        f"- forbidden credential-like bytes absent: `{checks['forbidden_bytes']['ok']}`",
        f"- private modes: `{checks['private_modes']['ok']}`",
        "",
        "## Artifact",
        "",
        f"- boot image: `{manifest['boot_image']}`",
        f"- boot sha256: `{manifest['boot_sha256']}`",
        f"- ramdisk sha256: `{manifest['ramdisk_sha256']}`",
        f"- helper sha256: `{manifest['helper_sha256']}`",
        "",
        "## Safety Scope",
        "",
        "No device command, flash, reboot, boot partition write, partition write,",
        "Wi-Fi HAL, scan/connect, credential handling, DHCP/routes, external ping,",
        "PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was",
        "performed.",
        "",
        "## Next",
        "",
        "V1395 may be a separate bounded live handoff only if it explicitly names",
        "the test image and rollback to `stage3/boot_linux_v724.img`.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1393-manifest", type=Path, default=DEFAULT_V1393_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--write-report", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    manifest = load_manifest(args.v1393_manifest)
    manifest["_path"] = str(args.v1393_manifest.relative_to(REPO_ROOT))

    base_boot = repo_path(str(manifest["base_boot"]))
    init_binary = repo_path(str(manifest["init_binary"]))
    helper = args.v1393_manifest.parent / "a90_android_execns_probe_v286"
    ramdisk = repo_path(str(manifest["ramdisk_cpio"]))
    boot = repo_path(str(manifest["boot_image"]))

    checks: dict[str, Any] = {
        "manifest": {
            "decision": manifest.get("decision", ""),
            "decision_ok": manifest.get("decision") == EXPECTED_DECISION,
        },
        "base_boot": {
            "path": str(base_boot.relative_to(REPO_ROOT)),
            "exists": base_boot.exists(),
            "sha256": sha256(base_boot) if base_boot.exists() else "",
        },
        "files": {
            "init_binary": check_file_sha(manifest, "init_binary", "init_sha256"),
            "helper": {
                "path": str(helper.relative_to(REPO_ROOT)),
                "exists": helper.exists(),
                "expected_sha256": manifest["helper_sha256"],
                "actual_sha256": sha256(helper) if helper.exists() else "",
                "sha256_ok": helper.exists() and sha256(helper) == manifest["helper_sha256"],
                "mode": mode_octal(helper) if helper.exists() else "",
            },
            "ramdisk": check_file_sha(manifest, "ramdisk_cpio", "ramdisk_sha256"),
            "boot": check_file_sha(manifest, "boot_image", "boot_sha256"),
        },
        "static": {
            "init_binary": check_static(init_binary),
            "helper": check_static(helper),
        },
        "ramdisk": check_ramdisk(ramdisk),
        "boot_markers": check_boot_markers(boot),
        "header_parity": check_header_parity(base_boot, boot),
        "forbidden_bytes": check_no_forbidden([init_binary, helper, ramdisk, boot]),
        "private_modes": {
            "ramdisk_mode": mode_octal(ramdisk),
            "boot_mode": mode_octal(boot),
            "manifest_mode": mode_octal(args.v1393_manifest),
            "ok": mode_octal(ramdisk) == "0o600" and mode_octal(boot) == "0o600",
        },
    }
    label, pass_ok, reason = decision(checks)
    result = {
        "cycle": "V1394",
        "decision": label,
        "pass": pass_ok,
        "reason": reason,
        "checks": checks,
    }
    store.write_json("manifest.json", result)
    store.write_text("summary.md", render_summary(manifest, result))
    if args.write_report:
        args.report_path.write_text(render_report(manifest, result), encoding="utf-8")
    print(json.dumps({"decision": label, "pass": pass_ok, "out_dir": str(args.out_dir)}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
