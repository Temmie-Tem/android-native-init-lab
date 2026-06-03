#!/usr/bin/env python3
"""V1946 host-only classifier for libsec-ril as the PM-voter caller."""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


CYCLE = "V1946"
OUT_DIR = repo_path("tmp/wifi/v1946-libsec-ril-pm-voter-classifier")
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1946_LIBSEC_RIL_PM_VOTER_CLASSIFIER_2026-06-04.md")
ANDROID_LOGCAT = repo_path(
    "tmp/wifi/v1934-android-libqmi-service69-positive-control-live-20260603-170139/"
    "android-postfs-evidence/a90-v1934-libqmi69/logcat-filtered.txt"
)
V1945_MANIFEST = repo_path("tmp/wifi/v1945-ril-impl-export/manifest.json")
V1945_VENDOR_SOURCE = repo_path("tmp/wifi/v1945-ril-impl-export/vendor-source")
LIBSEC_RIL = V1945_VENDOR_SOURCE / "lib64/libsec-ril.so"
BUILD_PROP = V1945_VENDOR_SOURCE / "build.prop"
RILCHIP_RC = V1945_VENDOR_SOURCE / "etc/init/init.vendor.rilchip.rc"
PM_CLIENT_SYMBOLS = {
    "pm_client_register",
    "pm_client_connect",
    "pm_client_event_acknowledge",
    "pm_client_disconnect",
    "pm_client_unregister",
}
MODEM_BOOT_SYMBOL_RE = re.compile(
    r"(ModemBoot.*PeripheralManager|ModemBoot.*BootupModemUsingPM|ModemBoot.*CheckAndRegisterWithPM|DoModemBoot)",
    re.IGNORECASE,
)
FORBIDDEN_DOWNSTREAM_RE = re.compile(r"(wlan_pd|wlanmdsp|wlfw)", re.IGNORECASE)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(repo_path(".")))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "path": rel(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": rel(path), "invalid": str(exc)}
    return data if isinstance(data, dict) else {"exists": True, "path": rel(path), "invalid": "not-object"}


def run_command(command: list[str], timeout: int = 25) -> tuple[str, str]:
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


def readelf_symbols(path: Path) -> tuple[str, dict[str, Any]]:
    status, output = run_command(["readelf", "-Ws", str(path)])
    if status != "ok":
        return status, {"pm_client": [], "modem_boot": []}
    pm_client: list[str] = []
    modem_boot: list[str] = []
    for line in output.splitlines():
        if any(symbol in line for symbol in PM_CLIENT_SYMBOLS):
            pm_client.append(line.strip()[:240])
        if MODEM_BOOT_SYMBOL_RE.search(line):
            modem_boot.append(line.strip()[:240])
    return status, {"pm_client": pm_client, "modem_boot": modem_boot}


def strings_summary(path: Path) -> tuple[str, dict[str, Any]]:
    status, output = run_command(["strings", "-a", str(path)])
    if status != "ok":
        return status, {"samples": [], "forbidden_downstream": []}
    sample_re = re.compile(r"(PeripheralManager|pm_client|libperipheral_client|PeripheralInfo|BootupModemUsingPM|CheckAndRegisterWithPM|RIL_Init)", re.IGNORECASE)
    samples: list[str] = []
    forbidden: list[str] = []
    for line in output.splitlines():
        if sample_re.search(line) and len(samples) < 30:
            samples.append(line[:240])
        if FORBIDDEN_DOWNSTREAM_RE.search(line) and len(forbidden) < 20:
            forbidden.append(line[:240])
    return status, {"samples": samples, "forbidden_downstream": forbidden}


def android_qcril_summary() -> dict[str, Any]:
    lines = read_text(ANDROID_LOGCAT).splitlines()
    qcril_lines = [
        {"line": index, "text": line}
        for index, line in enumerate(lines, start=1)
        if "PerMgrSrv" in line and "QCRIL" in line
    ]
    wlanmdsp_line = next((index for index, line in enumerate(lines, start=1) if "wlanmdsp.mbn" in line), None)
    qcril_vote_line = next((row["line"] for row in qcril_lines if "voting for modem" in row["text"]), None)
    qcril_sdx_line = next((row["line"] for row in qcril_lines if "voting for SDX50M" in row["text"]), None)
    return {
        "path": rel(ANDROID_LOGCAT),
        "exists": ANDROID_LOGCAT.exists(),
        "qcril_lines": qcril_lines,
        "wlanmdsp_line": wlanmdsp_line,
        "qcril_vote_line": qcril_vote_line,
        "qcril_sdx_line": qcril_sdx_line,
        "qcril_vote_before_wlanmdsp": isinstance(qcril_vote_line, int) and isinstance(wlanmdsp_line, int) and qcril_vote_line < wlanmdsp_line,
        "qcril_sdx_coupled": isinstance(qcril_sdx_line, int),
    }


def summarize_source() -> dict[str, Any]:
    manifest = load_json(V1945_MANIFEST)
    needed_status, needed = readelf_needed(LIBSEC_RIL)
    symbol_status, symbols = readelf_symbols(LIBSEC_RIL)
    strings_status, strings = strings_summary(LIBSEC_RIL)
    build_prop = read_text(BUILD_PROP)
    rilchip = read_text(RILCHIP_RC)
    return {
        "manifest": rel(V1945_MANIFEST),
        "vendor_source": rel(V1945_VENDOR_SOURCE),
        "libsec_ril": rel(LIBSEC_RIL),
        "libsec_ril_exists": LIBSEC_RIL.exists(),
        "v1945_pass": bool(manifest.get("pass")),
        "v1945_label": manifest.get("label", ""),
        "needed_status": needed_status,
        "needed": needed,
        "symbol_status": symbol_status,
        "pm_client_symbols": symbols["pm_client"],
        "modem_boot_symbols": symbols["modem_boot"],
        "strings_status": strings_status,
        "strings_samples": strings["samples"],
        "forbidden_downstream_strings": strings["forbidden_downstream"],
        "build_prop_libpath": "vendor.sec.rild.libpath=/vendor/lib64/libsec-ril.so" in build_prop,
        "ril_daemon_uses_rild": "service ril-daemon /vendor/bin/hw/rild" in rilchip,
    }


def classify(android: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    pm_client_complete = all(
        any(symbol in line for line in source["pm_client_symbols"])
        for symbol in ("pm_client_register", "pm_client_connect", "pm_client_event_acknowledge")
    )
    libperipheral_needed = "libperipheral_client.so" in source["needed"]
    modem_boot_pm_present = any("PeripheralManagerVote" in line for line in source["modem_boot_symbols"]) and any(
        "PeripheralManagerInit" in line for line in source["modem_boot_symbols"]
    )
    no_explicit_wlan_trigger = not source["forbidden_downstream_strings"]
    android_edge_matches = android["qcril_vote_before_wlanmdsp"] and android["qcril_sdx_coupled"]

    if (
        source["v1945_pass"]
        and source["libsec_ril_exists"]
        and source["build_prop_libpath"]
        and source["ril_daemon_uses_rild"]
        and libperipheral_needed
        and pm_client_complete
        and modem_boot_pm_present
        and android_edge_matches
    ):
        label = "libsec-ril-peripheral-manager-voter-caller-identified"
        reason = (
            "build.prop points rild to lib64/libsec-ril.so; libsec-ril needs libperipheral_client.so, imports "
            "pm_client_register/connect/event_acknowledge, and defines ModemBoot PeripheralManagerInit/Vote; "
            "this matches Android's PerMgrSrv QCRIL modem vote before wlanmdsp while remaining SDX50M-coupled source evidence"
        )
        passed = True
    elif source["libsec_ril_exists"] and libperipheral_needed:
        label = "libsec-ril-pm-voter-review"
        reason = "libsec-ril is present and links libperipheral_client, but caller or Android edge evidence is incomplete"
        passed = False
    else:
        label = "libsec-ril-pm-voter-incomplete"
        reason = "required V1945/libsec-ril source evidence is missing"
        passed = False

    return {
        "label": label,
        "decision": f"v1946-{label}-host-{'pass' if passed else 'review'}",
        "pass": passed,
        "reason": reason,
        "libperipheral_needed": libperipheral_needed,
        "pm_client_complete": pm_client_complete,
        "modem_boot_pm_present": modem_boot_pm_present,
        "no_explicit_wlan_trigger": no_explicit_wlan_trigger,
        "android_edge_matches": android_edge_matches,
    }


def render_report(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    source = manifest["source"]
    android = manifest["android"]
    needed_rows = [[library] for library in source["needed"] if library in {"libperipheral_client.so", "libqmi_cci.so", "libqmiservices.so", "libmdmdetect.so", "libril_sem.so"}]
    symbol_rows = [[line] for line in (source["pm_client_symbols"][:8] + source["modem_boot_symbols"][:10])]
    string_rows = [[line] for line in source["strings_samples"][:16]]
    android_rows = [[row["line"], row["text"]] for row in android["qcril_lines"]]
    return "\n".join(
        [
            "# Native Init V1946 libsec-ril PM Voter Classifier",
            "",
            "## Summary",
            "",
            f"- Cycle: `{manifest['cycle']}`",
            "- Type: host-only ELF/string/logcat classifier over V1945 libsec-ril export",
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
                    ["build.prop libpath", source["build_prop_libpath"], "vendor.sec.rild.libpath=/vendor/lib64/libsec-ril.so"],
                    ["ril-daemon uses rild", source["ril_daemon_uses_rild"], "init.vendor.rilchip.rc service ril-daemon"],
                    ["libperipheral needed", classification["libperipheral_needed"], "libsec-ril NEEDED libperipheral_client.so"],
                    ["pm_client imports", classification["pm_client_complete"], "register/connect/event_acknowledge"],
                    ["ModemBoot PM symbols", classification["modem_boot_pm_present"], "PeripheralManagerInit/Vote"],
                    ["Android edge matches", classification["android_edge_matches"], "PerMgrSrv QCRIL vote before wlanmdsp plus SDX50M vote"],
                    ["No explicit WLAN strings", classification["no_explicit_wlan_trigger"], "no wlan_pd/wlanmdsp/wlfw strings in libsec-ril"],
                ],
            ),
            "",
            "## Key Needed Libraries",
            "",
            markdown_table(["library"], needed_rows or [["none"]]),
            "",
            "## PM Voter Symbols",
            "",
            markdown_table(["symbol"], symbol_rows or [["none"]]),
            "",
            "## String Samples",
            "",
            markdown_table(["string"], string_rows or [["none"]]),
            "",
            "## Android QCRIL Edge",
            "",
            markdown_table(["line", "text"], android_rows or [["none", ""]]),
            "",
            "## Interpretation",
            "",
            "- This identifies the source owner for the Android `PerMgrSrv: QCRIL voting for modem` edge as the dynamically loaded Samsung RIL implementation, not a missing QTI `qcrild` binary.",
            "- It remains read-only source evidence and is still SDX50M-coupled: the same Android window logs `QCRIL voting for SDX50M`.",
            "- Next host-only step: disassemble `ModemBoot::PeripheralManagerInit/Vote/BootupModemUsingPM` to recover peripheral IDs/client names and decide whether a bounded internal-modem-only native shim is possible without starting radio/QCRIL/eSoC/PCIe.",
            "",
            "## Inputs",
            "",
            f"- Android logcat: `{android['path']}`",
            f"- V1945 manifest: `{source['manifest']}`",
            f"- V1945 vendor source: `{source['vendor_source']}`",
            f"- libsec-ril: `{source['libsec_ril']}`",
            "",
            "## Safety Scope",
            "",
            "Host-only parser over already exported files. No live device command, flash, reboot, rild/radio/QCRIL start, firmware/partition write, remount-write, `/dev/subsys_esoc0`, eSoC/PCIe/GDSC/PMIC/GPIO/regulator action, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, or restart-PD request was used.",
            "",
        ]
    )


def main() -> int:
    store = EvidenceStore(OUT_DIR)
    android = android_qcril_summary()
    source = summarize_source()
    classification = classify(android, source)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(OUT_DIR),
        "android": android,
        "source": source,
        "classification": classification,
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(f"{'PASS' if classification['pass'] else 'FAIL'} out_dir={OUT_DIR} decision={classification['decision']} reason={classification['reason']}")
    return 0 if classification["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
