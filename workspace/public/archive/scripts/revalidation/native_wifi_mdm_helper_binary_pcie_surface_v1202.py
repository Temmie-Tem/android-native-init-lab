#!/usr/bin/env python3
"""V1202: mdm_helper/ks binary strings + PCIe/MHI idle surface classifier.

Host-only analysis + read-only live device surface. No trigger, no new helper
deploy, no subsys_esoc0 open, no actors, no Wi-Fi HAL, scan/connect,
credentials, DHCP/routes, external ping, flash, or partition write.

V1201 result: mdm_helper holds esoc-0, receives ESOC_REQ_IMG at t=0, then
enters SyS_nanosleep loop (10s interval) for 100s. ks_count=0, mhi_dev=0
throughout. mhi_dev_count checks /dev/mhi_0305_01.01.00_pipe_10 (DATA pipe,
appears AFTER MHI link-up, not BHI boot pipe).

Root cause hypothesis: PCIe link training fails after sdx50m_toggle_soft_reset.
V1196 data: PCIe RC1 LTSSM reaches POLL_COMPLIANCE (MDM endpoint does not
respond to link training). MHI never enumerates → pipe_10/BHI absent → ks
never spawns → firmware never loaded → GPIO 142 never fires.

This script:
  1. Binary grep on device: find /dev/mhi* and /dev/block* paths embedded in
     mdm_helper and ks binaries to confirm internal wait logic.
  2. PCIe/MHI idle surface: ls /sys/bus/mhi/devices/, /sys/bus/pci/devices/,
     /sys/devices/platform/soc/1c08000.qcom,pcie/ at idle (no trigger).
  3. MHI device listing: check /dev/ for any mhi* nodes at idle.
  4. GPIO 135 (AP2MDM) surface: /proc/interrupts, /sys/class/gpio/ at idle.
  5. Decision: select V1203 gate (helper v242 with PCIe link state monitoring).

Blocked: subsys_esoc0 open, actors, Wi-Fi HAL, scan/connect, DHCP/routes,
credentials, external ping, boot image write, partition write, flash.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

import native_wifi_pm_service_property_contract_start_only_v857 as v857
from a90_kernel_tools import (
    collect_host_metadata,
    markdown_table,
    repo_path,
    run_capture,
)
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1202-mdm-helper-binary-pcie-surface")
LATEST_POINTER = Path("tmp/wifi/latest-v1202-mdm-helper-binary-pcie-surface.txt")
PCIE_RC1_PATH = "/sys/devices/platform/soc/1c08000.qcom,pcie"
MHI_BUS_PATH = "/sys/bus/mhi/devices"
PCI_BUS_PATH = "/sys/bus/pci/devices"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=v857.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=v857.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("command", choices=("plan", "preflight", "run"), nargs="?", default="run")
    return parser.parse_args()


def run_device_cmd(
    args: argparse.Namespace,
    name: str,
    shell_cmd: str,
    timeout: float = 30.0,
) -> tuple[bool, str]:
    """Run a shell command on device via exec, return (ok, output)."""
    cap = run_capture(args, name, ["exec", shell_cmd], timeout=timeout)
    text = ""
    if cap.text:
        # Strip cmdv1 framing (lines starting with A90P1, etc.)
        lines = []
        for line in cap.text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
            if line.startswith("A90P1 ") or line.startswith("a90:/#"):
                continue
            lines.append(line)
        text = "\n".join(lines).strip()
    return cap.ok, text


def run_version_check(args: argparse.Namespace) -> dict[str, Any]:
    ok, text = run_device_cmd(args, "version", "version", timeout=15.0)
    return {"ok": ok, "text": text[:400]}


def run_binary_grep(
    args: argparse.Namespace,
    binary_path: str,
    pattern: str,
    label: str,
    timeout: float = 25.0,
) -> dict[str, Any]:
    """Extract printable strings matching pattern from a binary via grep."""
    # grep -ao 'pattern' binary: prints only matching parts, ignoring nulls
    cmd = f"grep -ao '{pattern}' {binary_path} 2>/dev/null | head -80"
    ok, text = run_device_cmd(args, label, cmd, timeout=timeout)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return {"ok": ok, "lines": lines, "count": len(lines)}


def run_sysfs_ls(
    args: argparse.Namespace,
    path: str,
    label: str,
    timeout: float = 12.0,
) -> dict[str, Any]:
    """List a sysfs directory; return entries or ABSENT."""
    cmd = f"ls {path}/ 2>/dev/null || echo ABSENT"
    ok, text = run_device_cmd(args, label, cmd, timeout=timeout)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    absent = "ABSENT" in lines or (not lines)
    entries = [l for l in lines if l != "ABSENT"]
    return {"ok": ok, "absent": absent, "entries": entries, "raw": text[:512]}


def run_sysfs_read(
    args: argparse.Namespace,
    path: str,
    label: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Read a sysfs file; return value or ABSENT."""
    cmd = f"cat {path} 2>/dev/null || echo ABSENT"
    ok, text = run_device_cmd(args, label, cmd, timeout=timeout)
    text = text.strip()
    return {"ok": ok, "value": text[:256], "absent": text == "ABSENT" or not text}


def decide(
    args: argparse.Namespace,
    binary_results: dict[str, Any],
    surface_results: dict[str, Any],
) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v1202-plan-ready",
            True,
            "plan-only; no device trigger",
            (
                "binary grep confirms mdm_helper internal MHI wait logic; "
                "PCIe/MHI surface confirms link training state"
            ),
        )

    # ---- binary analysis ----
    mdm_mhi_paths = binary_results.get("mdm_helper_mhi_paths", {}).get("lines", [])
    mdm_block_paths = binary_results.get("mdm_helper_block_paths", {}).get("lines", [])
    ks_mhi_paths = binary_results.get("ks_mhi_paths", {}).get("lines", [])

    has_pipe10 = any("pipe_10" in p or "mhi_0305" in p for p in mdm_mhi_paths)
    has_mhi_bhi = any("BHI" in p or "bhi" in p or "mhi_BHI" in p for p in mdm_mhi_paths)
    has_block_by_name = any("by-name" in p or "bootdevice" in p for p in mdm_block_paths)

    # ---- surface analysis ----
    mhi_idle = surface_results.get("mhi_bus_idle", {})
    pci_idle = surface_results.get("pci_bus_idle", {})
    pcie_rc1 = surface_results.get("pcie_rc1_ls", {})
    dev_mhi = surface_results.get("dev_mhi_ls", {})

    mhi_idle_empty = mhi_idle.get("absent", True) or not mhi_idle.get("entries")
    pci_idle_count = len(pci_idle.get("entries", []))
    dev_mhi_entries = [
        e for e in dev_mhi.get("entries", []) if e.startswith("mhi")
    ]
    pcie_rc1_absent = pcie_rc1.get("absent", True)

    binary_ok = binary_results.get("version_ok", False)

    if not binary_ok:
        return (
            "v1202-device-not-reachable",
            False,
            "device version check failed; serial bridge may be down",
            "start serial_tcp_bridge.py and retry",
        )

    binary_summary = (
        f"mdm_helper mhi_paths={mdm_mhi_paths[:5]}; "
        f"block_paths={mdm_block_paths[:3]}; "
        f"ks_mhi_paths={ks_mhi_paths[:3]}"
    )
    surface_summary = (
        f"mhi_bus_idle={mhi_idle.get('entries', [])}; "
        f"pci_bus_count={pci_idle_count}; "
        f"dev_mhi={dev_mhi_entries[:5]}; "
        f"pcie_rc1_absent={pcie_rc1_absent}"
    )

    # MHI devices present at idle = unexpected path
    if dev_mhi_entries or not mhi_idle_empty:
        return (
            "v1202-mhi-devices-present-at-idle",
            True,
            (
                f"MHI devices present at idle (unexpected): "
                f"dev_mhi={dev_mhi_entries}; mhi_bus={mhi_idle.get('entries', [])}; "
                f"{binary_summary}"
            ),
            "Investigate why MHI enumerated at idle; this changes the model",
        )

    # Confirm PCIe RC1 exists
    if pcie_rc1_absent:
        return (
            "v1202-pcie-rc1-sysfs-absent",
            False,
            f"PCIe RC1 sysfs {PCIE_RC1_PATH!r} absent; unexpected; {binary_summary}",
            "Verify PCIe RC1 device tree path for SM8250 A90",
        )

    # MHI absent, PCIe RC1 exists: confirm link training issue
    reason_parts = [
        f"mhi_bus_idle=absent (confirmed no MHI devices at idle); "
        f"pcie_rc1=present ({len(pcie_rc1.get('entries', []))} entries); "
        f"pci_bus_count={pci_idle_count}; "
    ]
    if has_pipe10:
        reason_parts.append(
            f"mdm_helper_binary: pipe_10 wait confirmed {mdm_mhi_paths[:3]}; "
        )
    elif has_mhi_bhi:
        reason_parts.append(
            f"mdm_helper_binary: mhi_BHI wait path {mdm_mhi_paths[:3]}; "
        )
    else:
        reason_parts.append(
            f"mdm_helper_binary: mhi_paths={mdm_mhi_paths[:3]} (grep may be limited); "
        )

    if has_block_by_name:
        reason_parts.append(
            f"block_by-name path confirmed in mdm_helper: {mdm_block_paths[:2]}; "
        )

    reason = "".join(reason_parts)
    next_step = (
        "PCIe link training is the blocker: MHI never enumerates after "
        "sdx50m_toggle_soft_reset. Next: helper v242 adds PCIe LTSSM state "
        "and /sys/bus/pci/devices/ count to status loop; "
        "also investigate PM dependency flag (per_proxy timing) to enable "
        "pm-service PCIe resource management before subsys_esoc0 open."
    )

    return (
        "v1202-pcie-link-training-blocker-classified",
        True,
        reason,
        next_step,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    binary_results = manifest.get("binary_results", {})
    surface_results = manifest.get("surface_results", {})

    mdm_mhi = binary_results.get("mdm_helper_mhi_paths", {}).get("lines", [])
    mdm_block = binary_results.get("mdm_helper_block_paths", {}).get("lines", [])
    ks_mhi = binary_results.get("ks_mhi_paths", {}).get("lines", [])

    mhi_idle = surface_results.get("mhi_bus_idle", {})
    pci_idle = surface_results.get("pci_bus_idle", {})
    pcie_rc1 = surface_results.get("pcie_rc1_ls", {})
    dev_mhi = surface_results.get("dev_mhi_ls", {})
    gpio135 = surface_results.get("gpio135_interrupts", {})

    rows = [
        ["decision", manifest.get("decision", "")],
        ["pass", str(manifest.get("pass", ""))],
        ["mdm_helper_mhi_paths", str(mdm_mhi[:8])],
        ["mdm_helper_block_paths", str(mdm_block[:4])],
        ["ks_mhi_paths", str(ks_mhi[:4])],
        ["mhi_bus_idle_entries", str(mhi_idle.get("entries", []))],
        ["pci_bus_entries", str(pci_idle.get("entries", []))],
        ["pcie_rc1_entries", str(pcie_rc1.get("entries", [])[:10])],
        ["dev_mhi_nodes", str([e for e in dev_mhi.get("entries", []) if "mhi" in e])],
        ["gpio135_interrupts_raw", gpio135.get("value", "")[:120]],
    ]

    lines = [
        "# V1202 mdm_helper Binary + PCIe/MHI Surface Classifier",
        "",
        f"**Decision**: `{manifest.get('decision', '')}`",
        f"**Pass**: `{manifest.get('pass', '')}`",
        f"**Reason**: {manifest.get('reason', '')[:500]}",
        f"**Next**: {manifest.get('next_step', '')}",
        "",
        "## Surface",
        "",
        markdown_table(["key", "value"], rows),
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(DEFAULT_OUT_DIR))

    manifest: dict[str, Any] = {
        "cycle": "v1202",
        "generated_at": now_iso(),
        "host_metadata": collect_host_metadata(),
    }

    binary_results: dict[str, Any] = {}
    surface_results: dict[str, Any] = {}

    if args.command == "plan":
        manifest["plan"] = {
            "binary_targets": [
                "/vendor/bin/mdm_helper: grep /dev/mhi paths",
                "/vendor/bin/mdm_helper: grep /dev/block/by-name paths",
                "/vendor/bin/ks: grep /dev/mhi paths",
            ],
            "surface_targets": [
                f"{MHI_BUS_PATH}/: MHI devices at idle",
                f"{PCI_BUS_PATH}/: PCIe devices at idle",
                f"{PCIE_RC1_PATH}/: PCIe RC1 structure",
                "/dev/ mhi* nodes at idle",
                "/proc/interrupts GPIO 135 / AP2MDM",
            ],
            "safety": [
                "no subsys_esoc0 open",
                "no actors (mdm_helper, ks, pm-service)",
                "no Wi-Fi HAL / scan / connect / credentials / DHCP / ping",
                "no flash or partition write",
            ],
        }
        decision, passed, reason, next_step = decide(args, binary_results, surface_results)
        manifest.update({"decision": decision, "pass": passed,
                         "reason": reason, "next_step": next_step,
                         "binary_results": binary_results,
                         "surface_results": surface_results})
        summary = render_summary(manifest)
        store.write_json("manifest.json", manifest)
        write_private_text(repo_path(LATEST_POINTER), summary + "\n")
        print(summary)
        return 0

    # preflight + run: same live queries
    print("[V1202] checking device version...")
    ver = run_version_check(args)
    binary_results["version_ok"] = ver["ok"]
    binary_results["version_text"] = ver["text"]
    if not ver["ok"]:
        print(f"  WARN: version check failed: {ver['text'][:80]}")
    else:
        print(f"  OK: {ver['text'][:80]}")

    if args.command == "preflight":
        decision, passed, reason, next_step = decide(args, binary_results, surface_results)
        manifest.update({"decision": "v1202-preflight-done",
                         "pass": ver["ok"],
                         "reason": f"version_ok={ver['ok']} text={ver['text'][:80]}",
                         "next_step": "run V1202 run subcommand",
                         "binary_results": binary_results,
                         "surface_results": surface_results})
        store.write_json("manifest.json", manifest)
        print(f"preflight: version_ok={ver['ok']}")
        return 0 if ver["ok"] else 1

    # run: full analysis
    print("[V1202] binary grep: mdm_helper /dev/mhi paths...")
    binary_results["mdm_helper_mhi_paths"] = run_binary_grep(
        args,
        "/vendor/bin/mdm_helper",
        "/dev/mhi[^[:space:]]*",
        "mdm_helper_mhi_paths",
        timeout=25.0,
    )
    print(f"  found {binary_results['mdm_helper_mhi_paths']['count']} mhi path(s)")

    print("[V1202] binary grep: mdm_helper /dev/block paths...")
    binary_results["mdm_helper_block_paths"] = run_binary_grep(
        args,
        "/vendor/bin/mdm_helper",
        "/dev/block[^[:space:]]*",
        "mdm_helper_block_paths",
        timeout=25.0,
    )
    print(f"  found {binary_results['mdm_helper_block_paths']['count']} block path(s)")

    print("[V1202] binary grep: ks /dev/mhi paths...")
    binary_results["ks_mhi_paths"] = run_binary_grep(
        args,
        "/vendor/bin/ks",
        "/dev/mhi[^[:space:]]*",
        "ks_mhi_paths",
        timeout=20.0,
    )
    print(f"  found {binary_results['ks_mhi_paths']['count']} ks mhi path(s)")

    # Also try a broader printable-strings approach for interesting sections
    print("[V1202] binary grep: mdm_helper broader printable strings (mhi/ks/esoc)...")
    binary_results["mdm_helper_broad_strings"] = run_binary_grep(
        args,
        "/vendor/bin/mdm_helper",
        "[[:print:]]\\{8,\\}",
        "mdm_helper_broad_strings_raw",
        timeout=30.0,
    )
    # filter on host
    broad_lines = binary_results["mdm_helper_broad_strings"].get("lines", [])
    keywords = re.compile(
        r"(mhi|MHI|BHI|bhi|ks |/bin/ks|by.name|bootdevice|ESOC|esoc|"
        r"pcie|PCIe|pipe|firmware|modem\.mbn|boot|BOOT_DONE|IMG_XFER)",
        re.IGNORECASE,
    )
    binary_results["mdm_helper_filtered_strings"] = [
        line for line in broad_lines if keywords.search(line)
    ][:60]
    print(
        f"  broad={binary_results['mdm_helper_broad_strings']['count']} strings, "
        f"filtered={len(binary_results['mdm_helper_filtered_strings'])}"
    )

    # Surface reads
    print("[V1202] reading MHI bus idle surface...")
    surface_results["mhi_bus_idle"] = run_sysfs_ls(args, MHI_BUS_PATH, "mhi_bus_idle")
    print(f"  mhi_bus: entries={surface_results['mhi_bus_idle']['entries']}")

    print("[V1202] reading PCIe bus idle surface...")
    surface_results["pci_bus_idle"] = run_sysfs_ls(args, PCI_BUS_PATH, "pci_bus_idle")
    print(f"  pci_bus: entries={surface_results['pci_bus_idle']['entries']}")

    print("[V1202] reading PCIe RC1 structure...")
    surface_results["pcie_rc1_ls"] = run_sysfs_ls(args, PCIE_RC1_PATH, "pcie_rc1_ls")
    print(f"  pcie_rc1: absent={surface_results['pcie_rc1_ls']['absent']} entries={surface_results['pcie_rc1_ls']['entries'][:8]}")

    # PCIe RC1 interesting files
    for fname in ("current_link_state", "link_state", "rc_id"):
        surface_results[f"pcie_rc1_{fname}"] = run_sysfs_read(
            args, f"{PCIE_RC1_PATH}/{fname}", f"pcie_rc1_{fname}",
        )
        print(f"  pcie_rc1/{fname}: {surface_results[f'pcie_rc1_{fname}']['value'][:60]!r}")

    print("[V1202] reading /dev/ for mhi nodes...")
    ok, text = run_device_cmd(args, "dev_mhi_ls", "ls /dev/ 2>/dev/null", timeout=12.0)
    all_dev = [l.strip() for l in text.splitlines() if l.strip()]
    mhi_devs = [e for e in all_dev if e.startswith("mhi") or "mhi_" in e]
    surface_results["dev_mhi_ls"] = {"ok": ok, "entries": mhi_devs, "all_dev_count": len(all_dev)}
    print(f"  /dev/ mhi nodes: {mhi_devs}")

    print("[V1202] reading GPIO 135 AP2MDM interrupts...")
    ok, text = run_device_cmd(
        args, "gpio135_interrupts",
        "cat /proc/interrupts 2>/dev/null | grep -i '135\\|AP2MDM\\|ap2mdm\\|mdm'",
        timeout=12.0,
    )
    surface_results["gpio135_interrupts"] = {"ok": ok, "value": text[:512]}
    print(f"  gpio135/AP2MDM: {text[:120]!r}")

    print("[V1202] reading GPIO class surface...")
    ok, text = run_device_cmd(
        args, "gpio_class",
        "ls /sys/class/gpio/ 2>/dev/null | head -20",
        timeout=10.0,
    )
    surface_results["gpio_class"] = {"ok": ok, "value": text[:512]}

    # MHI drivers
    print("[V1202] reading MHI drivers...")
    surface_results["mhi_drivers"] = run_sysfs_ls(args, "/sys/bus/mhi/drivers", "mhi_drivers")
    print(f"  mhi_drivers: {surface_results['mhi_drivers']['entries'][:8]}")

    # MHI module
    ok, text = run_device_cmd(args, "mhi_module", "ls /sys/module/mhi/ 2>/dev/null || echo ABSENT", timeout=10.0)
    surface_results["mhi_module"] = {"ok": ok, "value": text[:256]}
    print(f"  /sys/module/mhi: {text[:60]!r}")

    decision, passed, reason, next_step = decide(args, binary_results, surface_results)
    manifest.update({
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "binary_results": binary_results,
        "surface_results": {
            k: {kk: vv for kk, vv in v.items() if kk != "raw"}
            if isinstance(v, dict) else v
            for k, v in surface_results.items()
        },
    })

    summary = render_summary(manifest)
    store.write_json("manifest.json", manifest)
    write_private_text(repo_path(LATEST_POINTER), summary + "\n")

    print()
    print(summary)
    print(f"\nEvidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
