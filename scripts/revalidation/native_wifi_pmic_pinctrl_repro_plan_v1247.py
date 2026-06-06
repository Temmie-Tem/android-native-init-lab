#!/usr/bin/env python3
"""V1247 host-only PMIC pinctrl reproduction plan classifier.

V1246 proved the current live path reaches ``mdm_subsys_powerup`` while the
same run still shows PM8150L soft-reset GPIO9 unclaimed, PCIe GDSC rails at
0mV, GPIO142 IRQ count 0, and no PCI/MHI/wlan0 response. V1247 chooses the
first defensible reproduction path before any live write.

No device command is executed here.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v1247-pmic-pinctrl-repro-plan")
LATEST_POINTER = Path("tmp/wifi/latest-v1247-pmic-pinctrl-repro-plan.txt")
DEFAULT_V1246_MANIFEST = Path("tmp/wifi/v1246-same-run-power-stack-classifier/manifest.json")
DEFAULT_V1244_MANIFEST = Path("tmp/wifi/v1244-android-power-surface-classifier/manifest.json")
DEFAULT_ANDROID_GPIO = Path(
    "tmp/wifi/v1024-fast-fd-android-timing-handoff-live-20260526-181232/"
    "v1022-late-android-pm-esoc-timing/android/commands/gpio.txt"
)
DEFAULT_V919_REPORT = Path("docs/reports/NATIVE_INIT_V919_SDX50M_SOFT_RESET_BLOCKER_CLASSIFIER_2026-05-26.md")
DEFAULT_V1024_REPORT = Path("docs/reports/NATIVE_INIT_V1024_FAST_FD_CONTRACT_CLASSIFIER_2026-05-26.md")
DEFAULT_DTS = workspace_private_input_path(
    "kernel_source",
    "SM-A908N_KOR_12_Opensource",
    "Kernel",
    "arch",
    "arm64",
    "boot",
    "dts",
    "samsung",
    "renovation",
    "sm8150-sec-r3q-kor-overlay-r00.dts",
)
DEFAULT_OSRC_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel')


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1246-manifest", type=Path, default=DEFAULT_V1246_MANIFEST)
    parser.add_argument("--v1244-manifest", type=Path, default=DEFAULT_V1244_MANIFEST)
    parser.add_argument("--android-gpio", type=Path, default=DEFAULT_ANDROID_GPIO)
    parser.add_argument("--v919-report", type=Path, default=DEFAULT_V919_REPORT)
    parser.add_argument("--v1024-report", type=Path, default=DEFAULT_V1024_REPORT)
    parser.add_argument("--dts", type=Path, default=DEFAULT_DTS)
    parser.add_argument("--osrc-root", type=Path, default=DEFAULT_OSRC_ROOT)
    parser.add_argument("command", nargs="?", choices=("run",), default="run")
    return parser.parse_args()


def read_text(path: Path, limit: int = 8 * 1024 * 1024) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def first_line(text: str, *needles: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if all(needle in line for needle in needles):
            return line
    return ""


def has_line(text: str, *needles: str) -> bool:
    return bool(first_line(text, *needles))


def parse_gpio_class_absence(android_gpio: str) -> dict[str, Any]:
    return {
        "gpio9_absent": has_line(android_gpio, "ls: /sys/class/gpio/gpio9:", "No such file or directory"),
        "gpio135_absent": has_line(android_gpio, "ls: /sys/class/gpio/gpio135:", "No such file or directory"),
        "gpio142_absent": has_line(android_gpio, "ls: /sys/class/gpio/gpio142:", "No such file or directory"),
        "debug_gpio_readable": "GPIO_DEBUG readable=1" in android_gpio,
        "gpiochip2_range": first_line(android_gpio, "gpiochip2:", "GPIOs 1263-1273"),
        "pm8150l_gpio9_line": first_line(android_gpio, "gpio9 : out", "vin-1", "push-pull"),
    }


def scan_osrc_for_soft_reset(osrc_root: Path) -> dict[str, Any]:
    root = repo_path(osrc_root)
    search_dirs = [
        root / "drivers" / "soc" / "qcom",
        root / "drivers" / "platform" / "msm",
        root / "drivers" / "pci",
        root / "drivers" / "power",
    ]
    searched_files = 0
    hits: list[str] = []
    for directory in search_dirs:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.suffix not in {".c", ".h"}:
                continue
            searched_files += 1
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if "sdx50m_toggle_soft_reset" in text or "mdm4x_do_first_power_on" in text:
                hits.append(str(path.relative_to(repo_path(Path(".")))))
    return {
        "root_present": root.exists(),
        "searched_files": searched_files,
        "soft_reset_symbol_hits": hits,
        "soft_reset_source_absent_in_scanned_osrc": root.exists() and not hits,
    }


def parse_dts_contract(dts: str) -> dict[str, str]:
    return {
        "compatible": first_line(dts, 'compatible = "qcom,ext-sdx50m"'),
        "ap2mdm_soft_reset_gpio": first_line(dts, "qcom,ap2mdm-soft-reset-gpio"),
        "ap2mdm_status_gpio": first_line(dts, "qcom,ap2mdm-status-gpio"),
        "mdm2ap_status_gpio": first_line(dts, "qcom,mdm2ap-status-gpio"),
    }


def classify_candidates(context: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "candidate": "direct-sysfs-gpio-export-write",
            "status": "reject",
            "reason": (
                "Android reference does not expose /sys/class/gpio/gpio9/gpio135/gpio142; "
                "PM8150L GPIO9 belongs to the PMIC pinctrl domain, not a confirmed safe userspace gpio export contract"
            ),
        },
        {
            "candidate": "debugfs-pinctrl-or-regulator-write",
            "status": "reject",
            "reason": (
                "debugfs is observation-only in current evidence; mutating pinctrl/regulator debugfs would bypass the "
                "vendor eSoC contract and risks broad side effects"
            ),
        },
        {
            "candidate": "direct-pcie-gdsc-enable",
            "status": "reject",
            "reason": (
                "PCIe GDSC at 0mV is downstream evidence, but direct GDSC enable does not reproduce the Android "
                "PM8150L soft-reset GPIO claim or the proprietary SDX50M sequencing"
            ),
        },
        {
            "candidate": "retry-dev-subsys-esoc0-trigger",
            "status": "reject",
            "reason": (
                "V1246 already proves same-run /dev/subsys_esoc0 reaches mdm_subsys_powerup while PMIC/GDSC/GPIO142 "
                "remain silent; blind retries do not add information"
            ),
        },
        {
            "candidate": "fail-closed-pmic-preflight-helper",
            "status": "select",
            "reason": (
                "Build a source-only helper gate that first verifies DTS PMIC phandle, Android GPIO-class absence, "
                "PM8150L gpiochip range, native MUX UNCLAIMED state, and explicit operator write flag before any "
                "bounded reproduction attempt"
            ),
        },
    ]


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    v1246 = load_json(args.v1246_manifest)
    v1244 = load_json(args.v1244_manifest)
    android_gpio = read_text(args.android_gpio)
    v919_report = read_text(args.v919_report)
    v1024_report = read_text(args.v1024_report)
    dts = read_text(args.dts)

    v1246_same_run = {
        "pass": bool(v1246.get("pass")),
        "decision": v1246.get("decision", ""),
        "same_phase_count": (v1246.get("observer") or {}).get("same_phase_count"),
        "same_pmic_unclaimed": bool(v1246.get("same_pmic_unclaimed")),
        "same_gdsc_zero": bool(v1246.get("same_gdsc_zero")),
        "same_no_downstream": bool(v1246.get("same_no_downstream")),
        "first_pmic_line": ((v1246.get("observer") or {}).get("first_same_phase_sample") or {}).get("pmic_soft_reset_line", ""),
        "first_pcie1_gdsc_line": ((v1246.get("observer") or {}).get("first_same_phase_sample") or {}).get("pcie1_gdsc_line", ""),
        "first_pcie0_gdsc_line": ((v1246.get("observer") or {}).get("first_same_phase_sample") or {}).get("pcie0_gdsc_line", ""),
    }
    v1244_android = {
        "pass": bool(v1244.get("pass")),
        "decision": v1244.get("decision", ""),
        "pmic_soft_reset": ((v1244.get("android") or {}).get("pm8150l_gpio9_line") or ""),
        "pcie_rc1": ((v1244.get("android") or {}).get("pcie_rc1_report_line") or ""),
        "android_chain_present": bool((v1244.get("v1244") or {}).get("android_chain_present"))
        if "v1244" in v1244 else bool((v1244.get("android") or {}).get("timeline")),
    }
    gpio_contract = parse_gpio_class_absence(android_gpio)
    dts_contract = parse_dts_contract(dts)
    osrc_scan = scan_osrc_for_soft_reset(args.osrc_root)
    source_contract = {
        "v919_mentions_soft_reset": "sdx50m_toggle_soft_reset" in v919_report,
        "v919_mentions_powerup_stack": all(
            needle in v919_report
            for needle in ("mdm4x_do_first_power_on", "mdm_cmd_exe", "mdm_subsys_powerup")
        ),
        "v1024_mentions_android_pm_fd_contract": all(
            needle in v1024_report
            for needle in ("pm_proxy_helper", "/dev/subsys_modem", "mdm_helper", "/dev/esoc-0")
        ),
    }
    context = {
        "v1246_same_run": v1246_same_run,
        "v1244_android": v1244_android,
        "gpio_contract": gpio_contract,
        "dts_contract": dts_contract,
        "osrc_scan": osrc_scan,
        "source_contract": source_contract,
    }
    candidates = classify_candidates(context)
    selected = next((candidate for candidate in candidates if candidate["status"] == "select"), {})
    checks = [
        {
            "name": "same-run-native-gap-proven",
            "status": "pass" if (
                v1246_same_run["pass"]
                and v1246_same_run["same_phase_count"]
                and v1246_same_run["same_pmic_unclaimed"]
                and v1246_same_run["same_gdsc_zero"]
                and v1246_same_run["same_no_downstream"]
            ) else "blocked",
            "detail": f"decision={v1246_same_run['decision']} same_phase_count={v1246_same_run['same_phase_count']}",
        },
        {
            "name": "android-pmic-reference-positive",
            "status": "pass" if (
                v1244_android["pass"]
                and "out" in v1244_android["pmic_soft_reset"]
                and "PCIe RC1" in v1244_android["pcie_rc1"]
            ) else "blocked",
            "detail": f"pmic={v1244_android['pmic_soft_reset']} pcie={v1244_android['pcie_rc1']}",
        },
        {
            "name": "android-gpio-class-is-not-contract",
            "status": "pass" if (
                gpio_contract["gpio9_absent"]
                and gpio_contract["gpio135_absent"]
                and gpio_contract["gpio142_absent"]
            ) else "blocked",
            "detail": "gpio9/gpio135/gpio142 are absent from Android /sys/class/gpio",
        },
        {
            "name": "pmic-gpiochip-reference-present",
            "status": "pass" if (
                gpio_contract["debug_gpio_readable"]
                and bool(gpio_contract["gpiochip2_range"])
                and "gpio9 : out" in gpio_contract["pm8150l_gpio9_line"]
            ) else "blocked",
            "detail": f"{gpio_contract['gpiochip2_range']} / {gpio_contract['pm8150l_gpio9_line']}",
        },
        {
            "name": "dts-soft-reset-contract-present",
            "status": "pass" if all(dts_contract.values()) else "blocked",
            "detail": dts_contract["ap2mdm_soft_reset_gpio"],
        },
        {
            "name": "proprietary-soft-reset-source-gap-acknowledged",
            "status": "pass" if (
                source_contract["v919_mentions_soft_reset"]
                and osrc_scan["soft_reset_source_absent_in_scanned_osrc"]
            ) else "blocked",
            "detail": f"searched_files={osrc_scan['searched_files']} hits={osrc_scan['soft_reset_symbol_hits']}",
        },
    ]
    pass_ok = all(check["status"] == "pass" for check in checks) and bool(selected)
    decision = (
        "v1247-select-fail-closed-pmic-preflight-before-write"
        if pass_ok else
        "v1247-pmic-pinctrl-plan-input-incomplete"
    )
    reason = (
        "direct GPIO/debugfs/GDSC writes are not defensible from the Android contract; the next safe step is a source/build-only fail-closed helper preflight before any bounded PMIC reproduction write"
        if pass_ok else
        "one or more PMIC pinctrl planning inputs are missing or contradictory"
    )
    next_step = (
        "V1248 source/build-only: add a fail-closed PMIC soft-reset preflight/write-gate skeleton with no live write, no Wi-Fi HAL, no scan/connect, no credentials, no DHCP/routes, and no external ping"
        if pass_ok else
        "refresh V1244/V1246/Android GPIO/DTS evidence before designing a write gate"
    )
    return {
        "cycle": "v1247",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1246_manifest": str(repo_path(args.v1246_manifest)),
            "v1244_manifest": str(repo_path(args.v1244_manifest)),
            "android_gpio": str(repo_path(args.android_gpio)),
            "v919_report": str(repo_path(args.v919_report)),
            "v1024_report": str(repo_path(args.v1024_report)),
            "dts": str(repo_path(args.dts)),
            "osrc_root": str(repo_path(args.osrc_root)),
        },
        "v1246_same_run": v1246_same_run,
        "v1244_android": v1244_android,
        "gpio_contract": gpio_contract,
        "dts_contract": dts_contract,
        "source_contract": source_contract,
        "osrc_scan": osrc_scan,
        "checks": checks,
        "candidates": candidates,
        "selected_candidate": selected,
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
    return "\n".join([
        "# V1247 PMIC Pinctrl Reproduction Plan",
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
        "## Candidate Classification",
        "",
        markdown_table(
            ["candidate", "status", "reason"],
            [[c["candidate"], c["status"], c["reason"]] for c in manifest["candidates"]],
        ),
        "",
        "## Evidence Anchors",
        "",
        markdown_table(["field", "value"], [
            ["v1246_decision", manifest["v1246_same_run"]["decision"]],
            ["v1246_same_phase_count", manifest["v1246_same_run"]["same_phase_count"]],
            ["native_pmic_line", manifest["v1246_same_run"]["first_pmic_line"]],
            ["native_pcie1_gdsc_line", manifest["v1246_same_run"]["first_pcie1_gdsc_line"]],
            ["native_pcie0_gdsc_line", manifest["v1246_same_run"]["first_pcie0_gdsc_line"]],
            ["android_pmic_line", manifest["v1244_android"]["pmic_soft_reset"]],
            ["android_pcie_rc1", manifest["v1244_android"]["pcie_rc1"]],
            ["android_gpiochip2", manifest["gpio_contract"]["gpiochip2_range"]],
            ["android_gpio_class_absent", {
                "gpio9": manifest["gpio_contract"]["gpio9_absent"],
                "gpio135": manifest["gpio_contract"]["gpio135_absent"],
                "gpio142": manifest["gpio_contract"]["gpio142_absent"],
            }],
            ["dts_soft_reset_gpio", manifest["dts_contract"]["ap2mdm_soft_reset_gpio"]],
            ["osrc_soft_reset_symbol_hits", manifest["osrc_scan"]["soft_reset_symbol_hits"]],
        ]),
        "",
        "## Safety",
        "",
        "- host-only classifier; no device command or mutation executed",
        "- rejects direct sysfs GPIO, debugfs pinctrl/regulator, direct GDSC, and blind esoc0 retry paths",
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
