#!/usr/bin/env python3
"""V1246 host-only same-run stack + PMIC/GDSC classifier.

V1245 proved reachability by combining V918, V1243, and V1244. V1246 tightens
that claim by proving the current V1243 live run itself contains both sides:

* pm-service Binder thread samples in mdm_subsys_powerup during late per_proxy.
* response samples from the same phase window show PM8150L soft-reset unclaimed,
  PCIe GDSC rails at 0mV, GPIO142 count 0, and no PCI/MHI/wlan0 response.

No device command is executed here.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1246-same-run-power-stack-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1246-same-run-power-stack-classifier.txt")
DEFAULT_V1243_MANIFEST = Path("tmp/wifi/v1243-sdx50m-power-prereq-response-live/manifest.json")
DEFAULT_V1243_OBSERVER = Path(
    "tmp/wifi/v1243-sdx50m-power-prereq-response-live/host/pm-server-wchan-tracefs-observer.txt"
)
DEFAULT_V1244_MANIFEST = Path("tmp/wifi/v1244-android-power-surface-classifier/manifest.json")

KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")
SYSCALL_PREFIX = "pm_service_trigger_observer.syscall_probe."
SAMPLE_PREFIX = "pm_service_trigger_observer.response_sample."


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1243-manifest", type=Path, default=DEFAULT_V1243_MANIFEST)
    parser.add_argument("--v1243-observer", type=Path, default=DEFAULT_V1243_OBSERVER)
    parser.add_argument("--v1244-manifest", type=Path, default=DEFAULT_V1244_MANIFEST)
    parser.add_argument("command", nargs="?", choices=("run",), default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def parse_observer(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    keys: dict[str, str] = {}
    if resolved.exists():
        with resolved.open("rb") as handle:
            for raw in handle:
                line = raw.decode("utf-8", errors="replace").replace("\0", "").strip()
                match = KEY_RE.match(line)
                if match:
                    keys[match.group(1)] = match.group(2).strip()

    syscall_phases: dict[str, dict[str, dict[str, str]]] = {}
    sample_phases: dict[str, dict[str, str]] = {}

    for key, value in keys.items():
        if key.startswith(SYSCALL_PREFIX):
            rest = key[len(SYSCALL_PREFIX):]
            parts = rest.split(".")
            if len(parts) != 3:
                continue
            phase, entry, field = parts
            syscall_phases.setdefault(phase, {}).setdefault(entry, {})[field] = value
        elif key.startswith(SAMPLE_PREFIX):
            rest = key[len(SAMPLE_PREFIX):]
            if "." not in rest:
                continue
            phase, field = rest.split(".", 1)
            sample_phases.setdefault(phase, {})[field] = value

    mdm_powerup_phases: dict[str, list[dict[str, str]]] = {}
    for phase, entries in syscall_phases.items():
        for entry_name, entry in entries.items():
            if entry.get("wchan") == "mdm_subsys_powerup":
                row = dict(entry)
                row["entry"] = entry_name
                mdm_powerup_phases.setdefault(phase, []).append(row)

    response_rows: list[dict[str, Any]] = []
    for phase, sample in sorted(sample_phases.items()):
        response_rows.append({
            "phase": phase,
            "monotonic_ms": int_value(sample.get("monotonic_ms"), -1),
            "pmic_soft_reset_line": sample.get("pmic_soft_reset_line", ""),
            "pcie1_gdsc_line": sample.get("pcie1_gdsc_line", ""),
            "pcie0_gdsc_line": sample.get("pcie0_gdsc_line", ""),
            "mdm_status_count_total": int_value(sample.get("mdm_status_count_total"), -1),
            "pci_dev_count": int_value(sample.get("pci_dev_count"), -1),
            "mhi_bus_count": int_value(sample.get("mhi_bus_count"), -1),
            "mhi_pipe_exists": int_value(sample.get("mhi_pipe_exists"), -1),
            "wlan0_exists": int_value(sample.get("wlan0_exists"), -1),
        })

    sample_phase_set = set(sample_phases)
    powerup_phase_set = set(mdm_powerup_phases)
    same_phases = sorted(sample_phase_set & powerup_phase_set)
    same_phase_rows = [
        row for row in response_rows
        if row["phase"] in same_phases
    ]
    return {
        "observer_present": resolved.exists(),
        "key_count": len(keys),
        "syscall_phase_count": len(syscall_phases),
        "response_phase_count": len(sample_phases),
        "mdm_powerup_phase_count": len(mdm_powerup_phases),
        "same_phase_count": len(same_phases),
        "same_phases": same_phases,
        "first_mdm_powerup_phase": same_phases[0] if same_phases else next(iter(sorted(powerup_phase_set)), ""),
        "first_same_phase_sample": same_phase_rows[0] if same_phase_rows else {},
        "mdm_powerup_entries": mdm_powerup_phases,
        "response_rows": response_rows,
        "same_phase_rows": same_phase_rows,
    }


def parse_v1243_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    pm = manifest.get("pm_service_trigger_observer") or {}
    sampler = manifest.get("response_sampler") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "pm_service_actor_esoc0_attempt": bool(pm.get("pm_service_actor_esoc0_attempt")),
        "late_per_proxy_started": bool(pm.get("late_per_proxy_started")),
        "all_postflight_safe": int_value(pm.get("all_postflight_safe"), -1),
        "sample_count": int_value(sampler.get("sample_count"), 0),
        "sample_phases": sampler.get("phases") or [],
    }


def parse_v1244_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    android = manifest.get("android") or {}
    timeline = android.get("timeline") or {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "android_pmic_soft_reset": android.get("pm8150l_gpio9_line", ""),
        "android_pcie_rc1": android.get("pcie_rc1_report_line", ""),
        "android_chain_present": all((timeline.get(name) or {}).get("present") for name in (
            "subsys_esoc0_get",
            "wlfw_start",
            "wlan_pd",
            "icnss_qmi",
            "fw_ready",
            "wlan0",
        )),
    }


def all_same_rows_match(rows: list[dict[str, Any]], predicate) -> bool:
    return bool(rows) and all(predicate(row) for row in rows)


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    v1243 = parse_v1243_manifest(load_json(args.v1243_manifest))
    v1244 = parse_v1244_manifest(load_json(args.v1244_manifest))
    observer = parse_observer(args.v1243_observer)
    same_rows = observer["same_phase_rows"]

    same_pmic_unclaimed = all_same_rows_match(
        same_rows,
        lambda row: "MUX UNCLAIMED" in str(row.get("pmic_soft_reset_line", "")),
    )
    same_gdsc_zero = all_same_rows_match(
        same_rows,
        lambda row: "0mV" in str(row.get("pcie1_gdsc_line", "")) and "0mV" in str(row.get("pcie0_gdsc_line", "")),
    )
    same_no_downstream = all_same_rows_match(
        same_rows,
        lambda row: row.get("mdm_status_count_total") == 0
        and row.get("pci_dev_count") == 0
        and row.get("mhi_bus_count") == 0
        and row.get("mhi_pipe_exists") == 0
        and row.get("wlan0_exists") == 0,
    )
    android_positive = (
        v1244["pass"]
        and "out" in v1244["android_pmic_soft_reset"]
        and "PCIe RC1" in v1244["android_pcie_rc1"]
        and v1244["android_chain_present"]
    )
    checks = [
        {
            "name": "v1243-live-path-valid",
            "status": "pass" if v1243["pass"] and v1243["pm_service_actor_esoc0_attempt"] and v1243["late_per_proxy_started"] else "blocked",
            "detail": f"decision={v1243['decision']} samples={v1243['sample_count']}",
        },
        {
            "name": "observer-has-mdm-subsys-powerup",
            "status": "pass" if observer["mdm_powerup_phase_count"] > 0 else "blocked",
            "detail": f"mdm_powerup_phases={observer['mdm_powerup_phase_count']} first={observer['first_mdm_powerup_phase']}",
        },
        {
            "name": "same-phase-stack-and-power-samples",
            "status": "pass" if observer["same_phase_count"] > 0 else "blocked",
            "detail": ", ".join(observer["same_phases"][:8]),
        },
        {
            "name": "same-phase-pmic-soft-reset-unclaimed",
            "status": "pass" if same_pmic_unclaimed else "blocked",
            "detail": str((observer["first_same_phase_sample"] or {}).get("pmic_soft_reset_line", "")),
        },
        {
            "name": "same-phase-pcie-gdsc-zero",
            "status": "pass" if same_gdsc_zero else "blocked",
            "detail": f"pcie1={(observer['first_same_phase_sample'] or {}).get('pcie1_gdsc_line', '')}; pcie0={(observer['first_same_phase_sample'] or {}).get('pcie0_gdsc_line', '')}",
        },
        {
            "name": "same-phase-no-downstream-response",
            "status": "pass" if same_no_downstream else "blocked",
            "detail": f"first_same_phase={observer['first_same_phase_sample']}",
        },
        {
            "name": "android-positive-contrast",
            "status": "pass" if android_positive else "blocked",
            "detail": f"pmic={v1244['android_pmic_soft_reset']} pcie={v1244['android_pcie_rc1']}",
        },
    ]
    pass_ok = all(check["status"] == "pass" for check in checks)
    decision = "v1246-same-run-mdm-powerup-pmic-gdsc-silent" if pass_ok else "v1246-same-run-input-incomplete"
    reason = (
        "V1243 same-run evidence shows pm-service Binder threads blocked in mdm_subsys_powerup while the same response window keeps PM8150L soft-reset unclaimed, PCIe GDSC at 0mV, and GPIO142/PCI/MHI/wlan0 silent"
        if pass_ok else
        "same-run mdm_subsys_powerup and PMIC/GDSC response evidence is missing or contradictory"
    )
    next_step = (
        "V1247 should choose the first bounded PMIC pinctrl reproduction gate, preferably host-only source/Android-contract planning before any write; Wi-Fi HAL/connect remains blocked"
        if pass_ok else
        "add helper-side same-run stack sampling before another PMIC/GDSC decision"
    )

    return {
        "cycle": "v1246",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1243_manifest": str(repo_path(args.v1243_manifest)),
            "v1243_observer": str(repo_path(args.v1243_observer)),
            "v1244_manifest": str(repo_path(args.v1244_manifest)),
        },
        "v1243": v1243,
        "v1244": v1244,
        "observer": observer,
        "same_pmic_unclaimed": same_pmic_unclaimed,
        "same_gdsc_zero": same_gdsc_zero,
        "same_no_downstream": same_no_downstream,
        "checks": checks,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "flash_executed": False,
        "partition_write_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    observer = manifest["observer"]
    first = observer["first_same_phase_sample"] or {}
    return "\n".join([
        "# V1246 Same-run Stack + PMIC/GDSC Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail"], [[c["name"], c["status"], c["detail"]] for c in manifest["checks"]]),
        "",
        "## Same-run Evidence",
        "",
        markdown_table(["field", "value"], [
            ["observer_key_count", observer["key_count"]],
            ["syscall_phase_count", observer["syscall_phase_count"]],
            ["response_phase_count", observer["response_phase_count"]],
            ["mdm_powerup_phase_count", observer["mdm_powerup_phase_count"]],
            ["same_phase_count", observer["same_phase_count"]],
            ["same_phases", ", ".join(observer["same_phases"])],
            ["first_same_phase", first.get("phase", "")],
            ["first_same_phase_pmic", first.get("pmic_soft_reset_line", "")],
            ["first_same_phase_pcie1", first.get("pcie1_gdsc_line", "")],
            ["first_same_phase_pcie0", first.get("pcie0_gdsc_line", "")],
            ["first_same_phase_gpio142", first.get("mdm_status_count_total", "")],
            ["first_same_phase_pci_mhi_wlan0", f"pci={first.get('pci_dev_count', '')} mhi={first.get('mhi_bus_count', '')} pipe={first.get('mhi_pipe_exists', '')} wlan0={first.get('wlan0_exists', '')}"],
        ]),
        "",
        "## Safety",
        "",
        "- host-only classifier; no device command or mutation executed",
        "- no Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, flash, boot image write, or partition write",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = analyze(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
