#!/usr/bin/env python3
"""V1915 bounded stock-kernel/source xref for service-notifier instance74."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from a90_kernel_tools import markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


CYCLE = "V1915"
DEFAULT_OUT_DIR = Path("tmp/wifi/v1915-stock-kernel-service74-static-xref")
DEFAULT_REPORT = Path("docs/reports/NATIVE_INIT_V1915_STOCK_KERNEL_SERVICE74_STATIC_XREF_2026-06-03.md")
DEFAULT_STOCK_BOOT = Path("backups/baseline_a_20260423_030309/boot.img")
DEFAULT_NATIVE_BOOT = Path("stage3/boot_linux_v724.img")
UNPACK_BOOTIMG = Path("mkbootimg/unpack_bootimg.py")
KERNEL_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel')
SOURCE_ROOTS = [
    KERNEL_ROOT / "drivers/soc/qcom",
    KERNEL_ROOT / "include/soc/qcom",
    KERNEL_ROOT / "drivers/net/wireless/cnss2",
]

FOCUSED_TERMS = [
    "service_notif_register_notifier",
    "service_notifier_new_server",
    "qmi_add_lookup",
    "SERVREG_NOTIF_SERVICE_ID",
    "servreg_notif",
    "wlan/fw",
    "wlan_pd",
    "msm/modem/wlan_pd",
    "wlfw",
    "icnss_get_service_location",
    "service_locator",
    "restart_pd",
    "74 service",
    "service 74",
    "instance 74",
]


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    return resolved.read_text(encoding="utf-8", errors="replace") if resolved.exists() else ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_capture(cmd: list[str], cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    return {
        "cmd": " ".join(cmd),
        "rc": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def unpack_boot(boot_img: Path, out_dir: Path) -> dict[str, Any]:
    unpacker = repo_path(UNPACK_BOOTIMG)
    boot = repo_path(boot_img)
    target = repo_path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    result = run_capture(
        [sys.executable, str(unpacker), "--boot_img", str(boot), "--out", str(target), "--format=mkbootimg"],
        repo_path("."),
    )
    kernel = target / "kernel"
    result.update({
        "boot_img": rel(boot),
        "out_dir": rel(target),
        "kernel": rel(kernel),
        "kernel_exists": kernel.exists(),
        "kernel_size": kernel.stat().st_size if kernel.exists() else 0,
        "kernel_sha256": sha256(kernel) if kernel.exists() else "",
    })
    return result


def ascii_strings(data: bytes, min_len: int = 4) -> list[tuple[int, str]]:
    strings: list[tuple[int, str]] = []
    start: int | None = None
    buf = bytearray()
    for offset, value in enumerate(data):
        if 32 <= value < 127:
            if start is None:
                start = offset
            buf.append(value)
            continue
        if start is not None and len(buf) >= min_len:
            strings.append((start, buf.decode("ascii", errors="replace")))
        start = None
        buf.clear()
    if start is not None and len(buf) >= min_len:
        strings.append((start, buf.decode("ascii", errors="replace")))
    return strings


def kernel_string_summary(kernel: Path) -> dict[str, Any]:
    resolved = repo_path(kernel)
    data = resolved.read_bytes() if resolved.exists() else b""
    strings = ascii_strings(data)
    focused: dict[str, dict[str, Any]] = {}
    for term in FOCUSED_TERMS:
        hits = [{"offset": offset, "text": text} for offset, text in strings if term.lower() in text.lower()]
        focused[term] = {
            "count": len(hits),
            "first_hits": hits[:8],
        }
    lines = [
        f"{term}: count={value['count']} first={json.dumps(value['first_hits'][:3], ensure_ascii=False)}"
        for term, value in focused.items()
    ]
    return {
        "kernel": rel(resolved),
        "string_count": len(strings),
        "focused": focused,
        "focused_lines": lines,
        "required_symbols_present": all(focused[term]["count"] > 0 for term in [
            "service_notif_register_notifier",
            "service_notifier_new_server",
            "qmi_add_lookup",
            "wlan/fw",
            "wlan_pd",
        ]),
        "literal_service74_absent": all(focused[term]["count"] == 0 for term in ["74 service", "service 74", "instance 74"]),
    }


def source_files() -> list[Path]:
    files: list[Path] = []
    for root in SOURCE_ROOTS:
        resolved = repo_path(root)
        if not resolved.exists():
            continue
        files.extend(path for path in resolved.rglob("*") if path.suffix in {".c", ".h"})
    return sorted(files)


def line_hits(files: list[Path], pattern: str) -> list[str]:
    regex = re.compile(pattern)
    hits: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for index, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                hits.append(f"{rel(path)}:{index}: {line.strip()}")
    return hits


def non_definition_register_callers(files: list[Path]) -> list[str]:
    callers: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for index, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if "service_notif_register_notifier(" not in stripped:
                continue
            if stripped.startswith(("/*", "*")):
                continue
            if re.search(r"^(?:extern\s+)?(?:static\s+inline\s+)?void \*service_notif_register_notifier\s*\(", stripped):
                continue
            if path.name == "service-notifier.h":
                continue
            callers.append(f"{rel(path)}:{index}: {stripped}")
    return callers


def source_summary() -> dict[str, Any]:
    files = source_files()
    register_callers = non_definition_register_callers(files)
    servreg_service_id = line_hits(files, r"SERVREG_NOTIF_SERVICE_ID(?:_V01)?")
    qmi_lookup_lines = line_hits(files, r"qmi_add_lookup\(")
    instance_id_lines = line_hits(files, r"\binstance_id\b")
    service74_literal_lines = [
        line for line in line_hits(files, r"\b74\b")
        if re.search(r"instance_id|service_notif|service-notifier|wlan_pd|wlan/fw", line, re.IGNORECASE)
        and not re.search(r"MAX_MSG_LEN|MSG_ID|MSG_V01|ARRAY_SIZE", line)
    ]
    new_server_print_lines = line_hits(files, r"Connection established between QMI handle and %d service")
    return {
        "file_count": len(files),
        "register_callers": register_callers,
        "register_caller_count": len(register_callers),
        "servreg_service_id_lines": servreg_service_id[:16],
        "qmi_lookup_lines": qmi_lookup_lines[:32],
        "instance_id_lines_count": len(instance_id_lines),
        "instance_id_lines_excerpt": instance_id_lines[:24],
        "service74_literal_lines": service74_literal_lines[:24],
        "service74_literal_line_count": len(service74_literal_lines),
        "new_server_print_lines": new_server_print_lines,
    }


def local_symbol_artifact_summary() -> dict[str, Any]:
    root = workspace_private_input_path("kernel_source", "SM-A908N_KOR_12_Opensource")
    artifacts = []
    if root.exists():
        for pattern in ("vmlinux", "System.map*", "*.o", "*.ko", "Module.symvers"):
            artifacts.extend(root.rglob(pattern))
    return {
        "search_root": rel(root),
        "symbol_artifact_count": len(artifacts),
        "artifact_excerpt": [rel(path) for path in sorted(artifacts)[:24]],
        "has_vmlinux_or_system_map": any(path.name == "vmlinux" or path.name.startswith("System.map") for path in artifacts),
    }


def classify(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    stock = manifest["stock_boot"]
    native = manifest["native_boot"]
    strings = manifest["kernel_strings"]
    source = manifest["source"]
    artifacts = manifest["local_symbol_artifacts"]
    kernel_same = (
        stock["rc"] == 0
        and native["rc"] == 0
        and stock["kernel_exists"]
        and native["kernel_exists"]
        and stock["kernel_sha256"] == native["kernel_sha256"]
    )
    source_boundary = (
        source["register_caller_count"] == 1
        and len(source["new_server_print_lines"]) == 1
        and source["service74_literal_line_count"] == 0
    )
    static_limited = (
        strings["required_symbols_present"]
        and strings["literal_service74_absent"]
        and not artifacts["has_vmlinux_or_system_map"]
    )
    manifest["gates"] = {
        "stock_and_v724_kernel_identical": kernel_same,
        "stock_strings_have_relevant_symbols": strings["required_symbols_present"],
        "stock_strings_have_no_literal_service74": strings["literal_service74_absent"],
        "osrc_register_caller_boundary": source_boundary,
        "no_local_vmlinux_or_system_map": not artifacts["has_vmlinux_or_system_map"],
    }
    if kernel_same and source_boundary and static_limited:
        return (
            "v1915-stock-kernel-static-xref-no-service74-caller-host-pass",
            True,
            "stock and v724 kernels are identical and expose service-notifier strings, but bounded strings/source xref has no literal instance74 caller beyond the ICNSS domain-list path; static host evidence cannot identify the runtime service74 publisher",
            "stock-kernel-static-xref-no-service74-caller",
        )
    return (
        "v1915-stock-kernel-static-xref-incomplete",
        False,
        "bounded kernel/source xref gates are incomplete",
        "stock-kernel-static-xref-incomplete",
    )


def render_report(manifest: dict[str, Any]) -> str:
    stock = manifest["stock_boot"]
    native = manifest["native_boot"]
    strings = manifest["kernel_strings"]
    source = manifest["source"]
    artifacts = manifest["local_symbol_artifacts"]
    gates = manifest["gates"]
    focused = strings["focused"]
    return "\n".join([
        "# Native Init V1915 Stock Kernel Service74 Static Xref",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only bounded stock-kernel/source xref preflight for service-notifier instance74",
        f"- Decision: `{manifest['decision']}`",
        f"- Label: `{manifest['label']}`",
        f"- Result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Gate Results",
        "",
        markdown_table(
            ["gate", "pass"],
            [[name, value] for name, value in gates.items()],
        ),
        "",
        "## Boot Kernel",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["stock boot/kernel/sha", f"{stock['boot_img']} / {stock['kernel']} / {stock['kernel_sha256']}"],
                ["v724 boot/kernel/sha", f"{native['boot_img']} / {native['kernel']} / {native['kernel_sha256']}"],
                ["kernel sizes", f"{stock['kernel_size']} / {native['kernel_size']}"],
                ["unpack rc", f"{stock['rc']} / {native['rc']}"],
            ],
        ),
        "",
        "## Focused Strings",
        "",
        markdown_table(
            ["term", "count", "first offsets"],
            [
                [term, focused[term]["count"], ", ".join(str(item["offset"]) for item in focused[term]["first_hits"][:4])]
                for term in FOCUSED_TERMS
            ],
        ),
        "",
        "## Source Xref",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["source files scanned", source["file_count"]],
                ["register callers", json.dumps(source["register_callers"])],
                ["new-server print", json.dumps(source["new_server_print_lines"])],
                ["service74 literal line count", source["service74_literal_line_count"]],
                ["SERVREG service-id lines", json.dumps(source["servreg_service_id_lines"][:6])],
                ["qmi_add_lookup lines", json.dumps(source["qmi_lookup_lines"][:12])],
            ],
        ),
        "",
        "## Symbol Artifact Limit",
        "",
        markdown_table(
            ["field", "value"],
            [
                ["search root", artifacts["search_root"]],
                ["symbol artifact count", artifacts["symbol_artifact_count"]],
                ["has vmlinux/System.map", artifacts["has_vmlinux_or_system_map"]],
                ["artifact excerpt", json.dumps(artifacts["artifact_excerpt"])],
            ],
        ),
        "",
        "## Selected Diff",
        "",
        "- Label: `stock-kernel-static-xref-no-service74-caller`.",
        "- Source confirms the dmesg text `74 service` is `data->instance_id`, not the fixed SERVREG notifier service id.",
        "- Source also confirms the QMI lookup is `SERVREG_NOTIF_SERVICE_ID` with runtime `instance_id`; the visible OSRC caller passes ICNSS service-locator domain-list values.",
        "- Stock kernel strings retain relevant symbol names but no literal service74/instance74 caller clue, and no local `vmlinux`/`System.map` is available for bounded callgraph xref.",
        "- Do not repeat broad kallsyms/disasm brute force; the next useful step is a read-only live observer around service74 lookup/publication or a fuller Android kallsyms-symbol capture.",
        "",
        "## Safety Scope",
        "",
        "V1915 is host-only. It unpacks local boot images into ignored tmp evidence and scans local kernel/source text. It executes no live device command, reboot, flash, tracefs write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, partition write, or restart-PD request.",
        "",
        "## Next",
        "",
        "- Next live gate: Android-good handoff that captures broader read-only `/proc/kallsyms` names and tracefs availability around service-notifier/qmi/service-locator before service74, then rollback to v724.",
        "- Native connect/ping remains gated until native proves WLFW service69 and `wlan0`.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--stock-boot", type=Path, default=DEFAULT_STOCK_BOOT)
    parser.add_argument("--native-boot", type=Path, default=DEFAULT_NATIVE_BOOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = repo_path(args.out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    store = EvidenceStore(out_dir)
    stock = unpack_boot(args.stock_boot, args.out_dir / "stock")
    native = unpack_boot(args.native_boot, args.out_dir / "native")
    kernel_path = Path(stock["kernel"])
    kernel_strings = kernel_string_summary(kernel_path)
    manifest: dict[str, Any] = {
        "cycle": CYCLE,
        "out_dir": rel(out_dir),
        "stock_boot": stock,
        "native_boot": native,
        "kernel_strings": kernel_strings,
        "source": source_summary(),
        "local_symbol_artifacts": local_symbol_artifact_summary(),
        "safety": {
            "device_commands_executed": False,
            "tracefs_write_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "restart_pd_request_executed": False,
            "subsys_esoc0_open_executed": False,
            "pmic_gpio_gdsc_regulator_write_executed": False,
            "pcie_rescan_executed": False,
            "platform_bind_unbind_executed": False,
        },
    }
    decision, passed, reason, label = classify(manifest)
    manifest.update({"decision": decision, "pass": passed, "reason": reason, "label": label, "report": rel(repo_path(args.report))})
    store.write_json("manifest.json", manifest)
    store.write_text("focused-strings.txt", "\n".join(kernel_strings["focused_lines"]) + "\n")
    report = render_report(manifest)
    store.write_text("summary.md", report)
    write_private_text(repo_path(args.report), report)
    print(json.dumps({"decision": decision, "pass": passed, "label": label, "out_dir": manifest["out_dir"], "report": manifest["report"]}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
