#!/usr/bin/env python3
"""V1944 host-only classifier for the rild dynamic RIL implementation gap."""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1944"
OUT_DIR = repo_path("tmp/wifi/v1944-rild-loader-gap-classifier")
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1944_RILD_LOADER_GAP_CLASSIFIER_2026-06-04.md")
V1942_MANIFEST = repo_path("tmp/wifi/v1942-qcril-radio-vendor-artifact-export/manifest.json")
V1942_VENDOR_SOURCE = repo_path("tmp/wifi/v1942-qcril-radio-vendor-artifact-export/vendor-source")
V1943_REPORT = repo_path("docs/reports/NATIVE_INIT_V1943_QCRIL_OWNER_CLASSIFIER_2026-06-04.md")
RILD_PATH = "bin/hw/rild"
LIKELY_RIL_IMPL_NAMES = (
    "libsec-ril.so",
    "libsec-ril-dsds.so",
    "libsecril-client.so",
    "libreference-ril.so",
    "libril-qc-qmi-1.so",
    "libqcrilNr.so",
)
LOADER_KEYWORDS = (
    "vendor.sec.rild.libpath",
    "vendor.rild.libpath",
    "rilLibPath",
    "libsec",
    "RIL_Init",
    "RIL_SAP_Init",
    "dlopen",
)
PM_CLIENT_RE = re.compile(r"(pm_client_|IPeripheralManager|PeripheralManagerClient|libperipheral_client)", re.IGNORECASE)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": rel(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": rel(path), "invalid": str(exc)}
    return data if isinstance(data, dict) else {"exists": True, "path": rel(path), "invalid": "not-object"}


def run_command(command: list[str], timeout: int = 20) -> tuple[str, str]:
    try:
        result = subprocess.run(
            command,
            cwd=repo_path("."),
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
    except FileNotFoundError:
        return f"{command[0]}-unavailable", ""
    except subprocess.TimeoutExpired:
        return f"{command[0]}-timeout", ""
    if result.returncode != 0:
        return f"{command[0]}-rc-{result.returncode}", result.stdout
    return "ok", result.stdout


def readelf_needed(path: Path) -> tuple[str, list[str]]:
    status, output = run_command(["readelf", "-W", "-d", str(path)])
    if status != "ok":
        return status, []
    needed = sorted(set(re.findall(r"Shared library:\s*\[([^\]]+)\]", output)))
    return status, needed


def readelf_pm_symbols(path: Path) -> tuple[str, list[str]]:
    status, output = run_command(["readelf", "-Ws", str(path)])
    if status != "ok":
        return status, []
    symbols: list[str] = []
    for line in output.splitlines():
        if PM_CLIENT_RE.search(line):
            symbols.append(line.strip()[:240])
            if len(symbols) >= 24:
                break
    return status, symbols


def strings_loader_hits(path: Path) -> tuple[str, list[str]]:
    status, output = run_command(["strings", "-a", str(path)])
    if status != "ok":
        return status, []
    hits: list[str] = []
    for line in output.splitlines():
        if any(keyword.lower() in line.lower() for keyword in LOADER_KEYWORDS + LIKELY_RIL_IMPL_NAMES):
            hits.append(line[:240])
            if len(hits) >= 40:
                break
    return status, hits


def summarize_artifacts() -> dict[str, Any]:
    manifest = load_json(V1942_MANIFEST)
    pulled_files = manifest.get("pulled_files") if isinstance(manifest.get("pulled_files"), list) else []
    pulled_paths = [str(item.get("relative_path", "")) for item in pulled_files if isinstance(item, dict)]
    pulled_set = set(pulled_paths)
    summaries: dict[str, dict[str, Any]] = {}
    for relative_path in pulled_paths:
        full_path = V1942_VENDOR_SOURCE / relative_path
        if not full_path.exists():
            continue
        needed_status, needed = readelf_needed(full_path)
        symbol_status, pm_symbols = readelf_pm_symbols(full_path)
        loader_status, loader_hits = strings_loader_hits(full_path)
        summaries[relative_path] = {
            "needed_status": needed_status,
            "needed": needed,
            "symbol_status": symbol_status,
            "pm_symbols": pm_symbols,
            "loader_status": loader_status,
            "loader_hits": loader_hits,
        }

    rild_summary = summaries.get(RILD_PATH, {})
    pm_symbol_paths = sorted(path for path, summary in summaries.items() if summary.get("pm_symbols"))
    direct_pm_client_users = sorted(
        path
        for path, summary in summaries.items()
        if "libperipheral_client.so" in summary.get("needed", []) and path != "bin/pm-service"
    )
    missing_likely_impls = sorted(name for name in LIKELY_RIL_IMPL_NAMES if not any(path.endswith("/" + name) or path == name for path in pulled_set))
    return {
        "manifest": rel(V1942_MANIFEST),
        "vendor_source": rel(V1942_VENDOR_SOURCE),
        "v1942_pass": bool(manifest.get("pass")),
        "pulled_paths": pulled_paths,
        "summaries": summaries,
        "rild_present": RILD_PATH in pulled_set,
        "rild_needed": rild_summary.get("needed", []),
        "rild_loader_hits": rild_summary.get("loader_hits", []),
        "rild_has_dlopen_hint": any("dlopen" in hit for hit in rild_summary.get("loader_hits", [])),
        "rild_has_libsec_hint": any("libsec" in hit.lower() for hit in rild_summary.get("loader_hits", [])),
        "rild_has_property_hint": any("vendor.sec.rild.libpath" in hit or "vendor.rild.libpath" in hit for hit in rild_summary.get("loader_hits", [])),
        "pm_symbol_paths": pm_symbol_paths,
        "direct_pm_client_users": direct_pm_client_users,
        "missing_likely_impls": missing_likely_impls,
    }


def classify(artifacts: dict[str, Any]) -> dict[str, Any]:
    pm_symbols_only_in_pm_layer = set(artifacts["pm_symbol_paths"]).issubset(
        {"bin/pm-service", "lib/libperipheral_client.so", "lib64/libperipheral_client.so"}
    )
    rild_loader_gap = (
        artifacts["v1942_pass"]
        and artifacts["rild_present"]
        and artifacts["rild_has_dlopen_hint"]
        and artifacts["rild_has_libsec_hint"]
        and artifacts["rild_has_property_hint"]
        and "libsec-ril.so" in artifacts["missing_likely_impls"]
    )
    no_exported_radio_pm_client_user = not artifacts["direct_pm_client_users"] and pm_symbols_only_in_pm_layer

    if rild_loader_gap and no_exported_radio_pm_client_user:
        label = "rild-dlopen-ril-impl-missing-from-v1942-source"
        reason = (
            "exported rild has dlopen/vendor.sec.rild.libpath/libsec/RIL_Init hints, but the likely RIL implementation "
            "library is not in the V1942 export; exported Samsung radio HAL artifacts do not directly reference "
            "libperipheral_client, so the PM-voter caller is likely in the dynamically loaded RIL implementation"
        )
        passed = True
    elif artifacts["rild_present"]:
        label = "rild-loader-gap-review"
        reason = "rild is present, but dynamic implementation or pm-client caller evidence is incomplete"
        passed = False
    else:
        label = "rild-loader-gap-incomplete"
        reason = "V1942 export lacks rild, so loader classification cannot run"
        passed = False

    return {
        "label": label,
        "decision": f"v1944-{label}-host-{'pass' if passed else 'review'}",
        "pass": passed,
        "reason": reason,
        "rild_loader_gap": rild_loader_gap,
        "no_exported_radio_pm_client_user": no_exported_radio_pm_client_user,
        "pm_symbols_only_in_pm_layer": pm_symbols_only_in_pm_layer,
    }


def render_report(manifest: dict[str, Any]) -> str:
    artifacts = manifest["artifacts"]
    classification = manifest["classification"]
    needed_rows = []
    for path in (RILD_PATH, "bin/pm-service", "lib64/libperipheral_client.so"):
        summary = artifacts["summaries"].get(path, {})
        needed_rows.append([path, summary.get("needed_status", ""), ", ".join(summary.get("needed", []))])
    pm_rows = []
    for path in artifacts["pm_symbol_paths"]:
        summary = artifacts["summaries"].get(path, {})
        pm_rows.append([path, summary.get("symbol_status", ""), " | ".join(summary.get("pm_symbols", [])[:4])])
    loader_rows = [[hit] for hit in artifacts["rild_loader_hits"]]
    lines = [
        "# Native Init V1944 RILD Loader Gap Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{manifest['cycle']}`",
        "- Type: host-only ELF/strings classifier over V1942 vendor-source",
        f"- Decision: `{classification['decision']}`",
        f"- Label: `{classification['label']}`",
        f"- Pass: `{classification['pass']}`",
        f"- Reason: {classification['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Matrix",
        "",
        markdown_table(
            ["area", "value", "detail"],
            [
                ["rild present", artifacts["rild_present"], RILD_PATH],
                ["rild loader gap", classification["rild_loader_gap"], "dlopen + vendor.sec.rild.libpath + libsec + missing libsec-ril.so"],
                ["no exported radio PM client user", classification["no_exported_radio_pm_client_user"], "pm_client symbols only in pm-service/libperipheral_client"],
                ["rild needed", ", ".join(artifacts["rild_needed"]), "readelf -d"],
                ["missing likely impls", ", ".join(artifacts["missing_likely_impls"]), "not copied by V1942 target set"],
            ],
        ),
        "",
        "## RILD Loader Hints",
        "",
        markdown_table(["string"], loader_rows or [["none"]]),
        "",
        "## Needed Libraries",
        "",
        markdown_table(["path", "readelf", "needed"], needed_rows),
        "",
        "## PM Client Symbol Owners",
        "",
        markdown_table(["path", "readelf", "sample"], pm_rows or [["none", "", ""]]),
        "",
        "## Interpretation",
        "",
        "- V1943 narrowed `QCRIL` to a `PerMgrSrv` client-name vote, not a standalone QTI qcrild artifact.",
        "- V1944 narrows the missing source object further: current exported rild/radio HAL files do not contain the PM-client caller; `rild` expects a dynamically loaded RIL implementation via `vendor.sec.rild.libpath`/`libsec`.",
        "- Next bounded read-only step: export the actual RIL implementation path (`libsec-ril.so` family and related init/property evidence) from `sda29`, then repeat the PM-client symbol/string/callgraph scan. Do not execute rild/radio/QCRIL.",
        "",
        "## Inputs",
        "",
        f"- V1942 manifest: `{artifacts['manifest']}`",
        f"- V1942 vendor source: `{artifacts['vendor_source']}`",
        f"- V1943 report: `{rel(V1943_REPORT)}`",
        "",
        "## Safety Scope",
        "",
        "Host-only parser over already exported files. No live device command, flash, reboot, rild/radio/QCRIL start, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or restart-PD request was used.",
        "",
    ]
    return "\n".join(str(line) for line in lines)


def main() -> int:
    store = EvidenceStore(OUT_DIR)
    artifacts = summarize_artifacts()
    classification = classify(artifacts)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(OUT_DIR),
        "artifacts": artifacts,
        "classification": classification,
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(f"{'PASS' if classification['pass'] else 'FAIL'} out_dir={OUT_DIR} decision={classification['decision']} reason={classification['reason']}")
    return 0 if classification["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
