#!/usr/bin/env python3
"""V1211: cnss-daemon peripheral name classifier (read-only live).

V1210 proved cnss-daemon calls pm_client_register with peripheral='modem' not
'SDX50M'.  This script classifies WHY, by:
  1. strings /vendor/bin/cnss-daemon | grep -iE "SDX50M|peripheral|ro[.][a-z]|subsys|esoc"
  2. ls /vendor/etc/ | grep -iE "cnss|peripheral"
  3. cat any /vendor/etc/cnss*.cfg / cnss*.json found
  4. ls /sys/module/icnss/parameters/ + read all params
  5. cat /sys/devices/platform/18800000.qcom,icnss/uevent (ICNSS sysfs)

Decision matrix:
  v1211-config-file-controls       -- /vendor/etc/cnss*.cfg exists with peripheral key
  v1211-property-reference-found   -- ro.* property name found in cnss-daemon binary
  v1211-sdx50m-string-present      -- 'SDX50M' found in binary (runtime-selected)
  v1211-modem-only-hardcoded       -- only 'modem', no SDX50M, no property refs
  v1211-icnss-ext-modem-param      -- ICNSS module has ext_modem param readable
  v1211-insufficient-data          -- mount/strings failed

Safety: sda29 read-only, no binary execution, no Wi-Fi HAL/scan/connect, no
  DHCP/routes, no credentials, no external ping, no partition write.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a90_kernel_tools import (  # noqa: E402
    CommandCapture,
    capture_to_manifest,
    collect_host_metadata,
    repo_path,
    run_capture,
)
from a90harness.evidence import EvidenceStore, write_private_text  # noqa: E402

DEFAULT_OUT_DIR = Path("tmp/wifi/v1211-cnss-daemon-peripheral-name")
LATEST_POINTER = Path("tmp/wifi/latest-v1211-cnss-daemon-peripheral-name.txt")
WORK_DIR = "/cache/a90-runtime/v1211"
SDA29_MNT = "/tmp/a90-v1211-sda29"

# Shell script run on device
_PROBE_SCRIPT = r"""#!/bin/sh
set -u
BB=/cache/bin/busybox
TOY=/cache/bin/toybox

# --- setup ---
$TOY mkdir -p {mnt}
echo "v1211_probe_begin"

# --- materialize sda29 block device node (major=259 minor=13) ---
$TOY mknod /dev/block/sda29 b 259 13 2>/dev/null || true

# --- mount sda29 read-only ---
$TOY mount -o ro,noexec /dev/block/sda29 {mnt} 2>&1
if [ $? -ne 0 ]; then
    echo "v1211_mount_failed"
    exit 1
fi
echo "v1211_mount_ok"

# --- strings on cnss-daemon (filtered) ---
echo "v1211_strings_begin"
$BB strings {mnt}/vendor/bin/cnss-daemon 2>/dev/null \
  | $BB grep -iE "SDX50M|peripheral|subsystem|esoc|mdm.type|ro[.][a-z]|cnss.cfg|cnss2.cfg|cnss.conf|chip.type|wcnss|wlan.type|peri.name" \
  | $BB sort -u \
  | $BB head -200
echo "v1211_strings_end"

# --- /vendor/etc/ config file listing ---
echo "v1211_vendor_etc_begin"
$TOY ls {mnt}/vendor/etc/ 2>/dev/null \
  | $BB grep -iE "cnss|peripheral|wlan|wcnss|mdm" \
  | $BB head -30
echo "v1211_vendor_etc_end"

# --- read any cnss config file found ---
for cfg in {mnt}/vendor/etc/cnss2.cfg {mnt}/vendor/etc/cnss.cfg \
           {mnt}/vendor/etc/cnss2.json {mnt}/vendor/etc/cnss_cfg.json \
           {mnt}/vendor/etc/cnss2.conf {mnt}/vendor/etc/wifi/cnss2.cfg \
           {mnt}/vendor/etc/wifi/cnss.cfg; do
    if [ -f "$cfg" ]; then
        echo "v1211_config_file_begin $cfg"
        $TOY cat "$cfg" 2>/dev/null | $BB head -100
        echo "v1211_config_file_end $cfg"
    fi
done

# --- ICNSS module parameters ---
echo "v1211_icnss_params_begin"
$TOY ls /sys/module/icnss/parameters/ 2>/dev/null && \
  for p in /sys/module/icnss/parameters/*; do
    echo "$p=$($TOY cat $p 2>/dev/null)"
  done
echo "v1211_icnss_params_end"

# --- ICNSS sysfs platform device ---
echo "v1211_icnss_sysfs_begin"
$TOY ls /sys/devices/platform/18800000.qcom,icnss/ 2>/dev/null | $BB head -30
echo "v1211_icnss_sysfs_end"

# --- ICNSS power/wakeup sysfs ---
echo "v1211_icnss_uevent_begin"
$TOY cat /sys/devices/platform/18800000.qcom,icnss/uevent 2>/dev/null
echo "v1211_icnss_uevent_end"

# --- cnss-daemon DT node check (does DT expose ext_mdm flag?) ---
echo "v1211_dt_wlan_begin"
$TOY find /sys/firmware/devicetree -name "ext-sdx50m" -o -name "external-modem" \
     -o -name "mdm-link-status-gpio" 2>/dev/null | $BB head -10
echo "v1211_dt_wlan_end"

# --- unmount ---
$TOY umount {mnt} 2>/dev/null || true
$TOY rm -rf {mnt} 2>/dev/null || true
echo "v1211_probe_end"
""".format(mnt=SDA29_MNT)


def _parse_probe_output(text: str) -> dict[str, Any]:
    """Extract structured findings from probe script output."""
    strings_lines: list[str] = []
    config_files: dict[str, list[str]] = {}
    vendor_etc_files: list[str] = []
    icnss_params: dict[str, str] = {}

    section = None
    cfg_name = ""

    for line in text.splitlines():
        line_stripped = line.strip()
        if line_stripped == "v1211_strings_begin":
            section = "strings"
        elif line_stripped == "v1211_strings_end":
            section = None
        elif line_stripped == "v1211_vendor_etc_begin":
            section = "vendor_etc"
        elif line_stripped == "v1211_vendor_etc_end":
            section = None
        elif line_stripped.startswith("v1211_config_file_begin"):
            cfg_name = line_stripped.split(" ", 1)[1] if " " in line_stripped else "unknown"
            config_files[cfg_name] = []
            section = "config"
        elif line_stripped.startswith("v1211_config_file_end"):
            section = None
        elif line_stripped == "v1211_icnss_params_begin":
            section = "icnss_params"
        elif line_stripped == "v1211_icnss_params_end":
            section = None
        elif section == "strings" and line_stripped:
            strings_lines.append(line_stripped)
        elif section == "vendor_etc" and line_stripped:
            vendor_etc_files.append(line_stripped)
        elif section == "config" and line_stripped:
            config_files[cfg_name].append(line_stripped)
        elif section == "icnss_params" and "=" in line_stripped:
            k, _, v = line_stripped.partition("=")
            icnss_params[k.split("/")[-1]] = v

    # Classify findings
    has_sdx50m = any("sdx50m" in s.lower() or "SDX50M" in s for s in strings_lines)
    has_modem_string = any(s.lower() in ("modem", "\"modem\"") or
                            re.match(r"^modem\s*$", s, re.I) for s in strings_lines)
    property_refs = [s for s in strings_lines if re.match(r"ro[.][a-z]", s)]
    peripheral_refs = [s for s in strings_lines if "peripheral" in s.lower() or
                        "subsys" in s.lower()]
    config_file_found = bool(config_files)

    return {
        "strings_count": len(strings_lines),
        "strings_sample": strings_lines[:80],
        "has_sdx50m_string": has_sdx50m,
        "has_modem_string": has_modem_string,
        "property_refs": property_refs,
        "peripheral_refs": peripheral_refs,
        "config_file_found": config_file_found,
        "config_files": {k: v for k, v in config_files.items()},
        "vendor_etc_cnss_files": vendor_etc_files,
        "icnss_params": icnss_params,
        "mount_ok": "v1211_mount_ok" in text,
    }


def decide_v1211(analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if not analysis.get("mount_ok"):
        return ("v1211-mount-failed", False,
                "sda29 mount failed; cannot analyse cnss-daemon binary",
                "check sda29 availability and retry")

    has_sdx50m = analysis.get("has_sdx50m_string", False)
    property_refs = analysis.get("property_refs", [])
    config_found = analysis.get("config_file_found", False)
    config_files = analysis.get("config_files", {})
    icnss_params = analysis.get("icnss_params", {})

    # Config file with peripheral key → highest priority
    if config_found:
        cfg_text = "\n".join(
            "\n".join(lines) for lines in config_files.values()
        )
        has_peripheral_key = re.search(r"peripheral|sdx50m|subsystem", cfg_text, re.I)
        if has_peripheral_key:
            return ("v1211-config-file-controls", True,
                    f"config files found: {list(config_files.keys())}; "
                    "contains peripheral/subsystem key",
                    "V1212: set peripheral=SDX50M in config file and re-run")
        return ("v1211-config-file-present-no-peripheral-key", False,
                f"config files found: {list(config_files.keys())}; "
                "no peripheral/subsystem key detected",
                "V1212: inspect config file content more carefully")

    # SDX50M string in binary → runtime-selected, must be property or env
    if has_sdx50m:
        if property_refs:
            return ("v1211-property-reference-found", True,
                    f"'SDX50M' string present in binary; "
                    f"property refs: {property_refs[:10]}",
                    "V1212: identify which ro.* property selects SDX50M and set it")
        return ("v1211-sdx50m-string-present", True,
                "'SDX50M' string present in binary; no clear ro.* property ref found; "
                "selection may depend on /dev/esoc-0 presence or ioctl",
                "V1212: test peripheral name with /dev/esoc-0 materialized before cnss-daemon")

    # No SDX50M, only property refs → property might select peripheral dynamically
    if property_refs:
        return ("v1211-property-refs-no-sdx50m", False,
                f"no 'SDX50M' in binary; property refs: {property_refs[:10]}; "
                "'modem' may be hardcoded for this chip variant",
                "V1212: check if property override can inject SDX50M peripheral name")

    # ICNSS external_modem param
    if any("ext" in k.lower() or "modem" in k.lower() for k in icnss_params):
        return ("v1211-icnss-ext-modem-param", True,
                f"ICNSS has external_modem param: {icnss_params}",
                "V1212: check if ICNSS ext_modem param controls cnss-daemon peripheral")

    # Fallback: modem only, hardcoded
    return ("v1211-modem-only-hardcoded", False,
            "no 'SDX50M' string in binary, no cnss config files, no clear property refs; "
            "'modem' appears hardcoded for this chip/platform variant in cnss-daemon",
            "V1212: inspect cnss-daemon binary with hex disassembly or test "
            "/dev/esoc-0 presence before cnss-daemon start")


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def add_standard_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--out-dir", type=Path, default=DEFAULT_OUT_DIR,
    )
    parser.add_argument("--assume-yes", action="store_true")


def cmd_plan(args: argparse.Namespace) -> int:
    print("V1211 plan: cnss-daemon peripheral name classifier")
    print()
    print("Actions (read-only):")
    print("  1. Mount sda29 at", SDA29_MNT, "(ro,noexec)")
    print("  2. strings /vendor/bin/cnss-daemon | grep -iE 'SDX50M|peripheral|ro\\.|subsys|esoc'")
    print("  3. ls /vendor/etc/ | grep -iE 'cnss|peripheral'")
    print("  4. cat /vendor/etc/cnss*.cfg or cnss*.json if found")
    print("  5. read /sys/module/icnss/parameters/*")
    print("  6. Unmount sda29")
    print()
    print("Decision matrix:")
    print("  v1211-config-file-controls     -- cnss*.cfg exists with peripheral key")
    print("  v1211-property-reference-found -- ro.* property ref found in binary")
    print("  v1211-sdx50m-string-present    -- 'SDX50M' in binary (runtime selection)")
    print("  v1211-modem-only-hardcoded     -- only 'modem', no SDX50M/property refs")
    print("  v1211-icnss-ext-modem-param    -- ICNSS module has ext_modem param")
    print()
    print("Safety: no binary execution, no Wi-Fi HAL/scan/connect, no DHCP/routes,")
    print("        no credentials, no external ping, no partition write.")
    return 0


def _push_script(args: argparse.Namespace, store: EvidenceStore,
                  script_text: str, remote_path: str, label: str) -> bool:
    """Push script to device via appendfile (1200-char chunks)."""
    CHUNK = 1200
    # Remove existing file
    rm_cap = run_capture(args, f"{label}-rm",
                         ["run", "/cache/bin/busybox", "rm", "-f", remote_path],
                         timeout=10.0)
    # Append chunks
    for idx in range(0, len(script_text), CHUNK):
        chunk = script_text[idx:idx + CHUNK]
        chunk_cap = run_capture(args, f"{label}-append-{idx // CHUNK:03d}",
                                ["appendfile", remote_path, chunk], timeout=15.0)
        write_private_text(
            store.run_dir / f"{label}-append-{idx // CHUNK:03d}.txt",
            chunk_cap.text,
        )
        if not chunk_cap.ok:
            print(f"  FAIL: appendfile chunk {idx // CHUNK} failed: "
                  f"rc={chunk_cap.rc} status={chunk_cap.status!r} "
                  f"error={chunk_cap.error!r} text={chunk_cap.text[:200]!r}")
            return False
    chmod_cap = run_capture(args, f"{label}-chmod",
                            ["run", "/cache/bin/busybox", "chmod", "755", remote_path],
                            timeout=10.0)
    write_private_text(store.run_dir / f"{label}-chmod.txt", chmod_cap.text)
    return chmod_cap.ok


def cmd_run(args: argparse.Namespace) -> int:
    store = EvidenceStore(repo_path(args.out_dir))
    manifest: dict[str, Any] = {
        "cycle": "v1211",
        "generated_at": _now_iso(),
        "host": collect_host_metadata(),
        "out_dir": str(store.run_dir),
    }

    # --- preflight: version + status ---
    print("[V1211] preflight: version")
    ver_cap = run_capture(args, "version", ["version"])
    manifest["preflight_version"] = capture_to_manifest(ver_cap)
    if not ver_cap.ok:
        print(f"  FAIL: version failed: {ver_cap.error}")
        manifest.update({"decision": "v1211-preflight-failed", "pass": False,
                         "reason": "version command failed", "next_step": "check bridge"})
        store.write_json("manifest.json", manifest)
        return 1
    print(f"  version: {ver_cap.text.strip()}")

    print("[V1211] preflight: status")
    stat_cap = run_capture(args, "status", ["status"])
    manifest["preflight_status"] = capture_to_manifest(stat_cap)
    if not stat_cap.ok:
        print(f"  FAIL: status failed")
        manifest.update({"decision": "v1211-preflight-failed", "pass": False,
                         "reason": "status command failed", "next_step": "check device"})
        store.write_json("manifest.json", manifest)
        return 1
    print(f"  status: {stat_cap.text.strip()[:120]}")

    # --- push probe script via appendfile ---
    print("[V1211] pushing probe script to device")
    SCRIPT_PATH = WORK_DIR + "/probe.sh"
    write_private_text(store.run_dir / "probe-script.sh", _PROBE_SCRIPT)
    # Setup workdir on device (cache/a90-runtime/v1211/ for appendfile access)
    mkdir_cap = run_capture(args, "v1211-mkdir",
                             ["run", "/cache/bin/toybox", "mkdir", "-p", WORK_DIR],
                             timeout=10.0)
    write_private_text(store.run_dir / "mkdir.txt", mkdir_cap.text)

    ok = _push_script(args, store, _PROBE_SCRIPT, SCRIPT_PATH, "probe-script")
    if not ok:
        manifest.update({"decision": "v1211-script-push-failed", "pass": False,
                         "reason": "failed to push probe script to device",
                         "next_step": "check bridge and device storage"})
        store.write_json("manifest.json", manifest)
        return 1
    print("  probe script pushed OK")

    # --- run probe ---
    print("[V1211] running probe (mount sda29 + strings + config + ICNSS sysfs)")
    probe_cap = run_capture(
        args, "v1211-probe",
        ["run", "/cache/bin/busybox", "sh", SCRIPT_PATH],
        timeout=90.0,
    )
    manifest["probe"] = capture_to_manifest(probe_cap)
    write_private_text(store.run_dir / "probe-output.txt", probe_cap.text)
    print(f"  probe ok={probe_cap.ok} rc={probe_cap.rc} duration={probe_cap.duration_sec:.1f}s")

    if not probe_cap.ok and "v1211_probe_end" not in probe_cap.text:
        print("  WARNING: probe may not have completed cleanly")
        manifest["probe_incomplete"] = True

    # --- cleanup script ---
    run_capture(args, "v1211-script-rm",
                ["run", "/cache/bin/busybox", "rm", "-f", SCRIPT_PATH], timeout=10.0)

    # --- parse and decide ---
    analysis = _parse_probe_output(probe_cap.text)
    manifest["analysis"] = analysis

    decision, passed, reason, next_step = decide_v1211(analysis)
    manifest.update({
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
    })

    store.write_json("manifest.json", manifest)
    if LATEST_POINTER:
        try:
            LATEST_POINTER.parent.mkdir(parents=True, exist_ok=True)
            LATEST_POINTER.write_text(str(store.run_dir))
        except Exception:
            pass

    # --- print results ---
    print()
    print(f"decision: {decision}")
    print(f"pass:     {passed}")
    print(f"reason:   {reason}")
    print(f"next:     {next_step}")
    print()
    print(f"mount_ok:               {analysis.get('mount_ok')}")
    print(f"has_sdx50m_string:      {analysis.get('has_sdx50m_string')}")
    print(f"has_modem_string:       {analysis.get('has_modem_string')}")
    print(f"property_refs_count:    {len(analysis.get('property_refs', []))}")
    print(f"property_refs:          {analysis.get('property_refs', [])[:5]}")
    print(f"peripheral_refs_count:  {len(analysis.get('peripheral_refs', []))}")
    print(f"config_file_found:      {analysis.get('config_file_found')}")
    print(f"vendor_etc_cnss_files:  {analysis.get('vendor_etc_cnss_files')}")
    print(f"icnss_params:           {analysis.get('icnss_params')}")
    print(f"strings_count:          {analysis.get('strings_count')}")
    print()
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="V1211 cnss-daemon peripheral classifier")
    add_standard_args(parser)
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("plan")
    sub.add_parser("run")
    args = parser.parse_args()
    if args.cmd == "plan":
        return cmd_plan(args)
    if args.cmd == "run":
        return cmd_run(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
