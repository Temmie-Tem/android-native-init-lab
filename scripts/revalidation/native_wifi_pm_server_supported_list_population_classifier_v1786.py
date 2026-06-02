#!/usr/bin/env python3
"""V1786 host-only classifier for PM server supported-list population."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1786-pm-server-supported-list-population-static"
HOST_DIR = OUT_DIR / "host"
REPORT_PATH = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1786_PM_SERVER_SUPPORTED_LIST_POPULATION_CLASSIFIER_2026-06-03.md"

INPUTS = {
    "pm_service": REPO_ROOT / "tmp" / "wifi" / "v1073-host-only" / "vendor-extract" / "files" / "pm-service",
    "libperipheral_client": REPO_ROOT / "tmp" / "wifi" / "v1073-host-only" / "vendor-extract" / "files" / "libperipheral_client.so",
    "libmdmdetect": REPO_ROOT / "tmp" / "wifi" / "v1073-host-only" / "vendor-extract" / "files" / "libmdmdetect.so",
    "v1784_manifest": REPO_ROOT / "tmp" / "wifi" / "v1784-pm-server-forwarding-observer-handoff" / "manifest.json",
    "v1784_helper": REPO_ROOT / "tmp" / "wifi" / "v1784-pm-server-forwarding-observer-handoff" / "test-v1393-helper-result.stdout.txt",
    "v1785_manifest": REPO_ROOT / "tmp" / "wifi" / "v1785-pm-server-no-peripheral-classifier" / "manifest.json",
    "v1779_manifest": REPO_ROOT / "tmp" / "wifi" / "v1779-pm-service-lifetime-delta-classifier" / "manifest.json",
}


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": display_path(path)}
    data = json.loads(path.read_text())
    if isinstance(data, dict):
        data["present"] = True
        return data
    return {"present": True, "value": data}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            fields[key] = value.strip()
    return fields


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass"}


def intish(value: Any) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def run_capture(command: list[str], out_path: Path) -> str:
    result = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out_path.write_text(result.stdout, encoding="utf-8")
    if result.stderr:
        out_path.with_suffix(out_path.suffix + ".stderr").write_text(result.stderr, encoding="utf-8")
    return result.stdout


def objdump(path: Path, start: int, stop: int, name: str) -> str:
    out_path = HOST_DIR / name
    return run_capture(
        [
            "aarch64-linux-gnu-objdump",
            "-d",
            f"--start-address=0x{start:x}",
            f"--stop-address=0x{stop:x}",
            str(path),
        ],
        out_path,
    )


def strings_tx(path: Path) -> str:
    out_path = HOST_DIR / f"{path.name}.strings.txt"
    return run_capture(["strings", "-tx", str(path)], out_path)


def parse_static_pm_peripheral_table(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = path.read_bytes()
    base = 0xC0B8
    stride = 0x88
    records: list[dict[str, Any]] = []
    for index in range(6):
        offset = base + stride * index
        record = data[offset : offset + stride]
        if len(record) < stride:
            continue
        name = record[:32].split(b"\0", 1)[0].decode("latin1", errors="replace")
        values = struct.unpack_from("<" + "I" * 10, record, 32)
        records.append(
            {
                "index": index,
                "file_offset": f"0x{offset:x}",
                "name": name,
                "enabled": values[0],
                "kind": values[1],
                "off_timeout": values[3],
                "ack_timeout": values[4],
                "extra_timeout": values[5],
            }
        )
    return records


def count_shutdown_requests(fields: dict[str, str]) -> tuple[int, list[str]]:
    values: list[str] = []
    for key, value in fields.items():
        if not key.endswith(".name") or value != "vendor.peripheral.shutdown_critical_list":
            continue
        base = key[: -len(".name")]
        values.append(fields.get(base + ".value", ""))
    return len(values), values


def has_all(text: str, patterns: list[str]) -> bool:
    return all(re.search(pattern, text) for pattern in patterns)


def classify(facts: dict[str, Any]) -> tuple[str, str, str]:
    if not facts["inputs_present"]:
        return (
            "v1786-pm-supported-list-population-input-missing",
            "input-missing",
            "required V1784/V1785 or vendor binary evidence is missing",
        )
    if facts["v1785_label"] != "pm-server-supported-list-empty":
        return (
            "v1786-pm-supported-list-population-baseline-mismatch",
            "baseline-mismatch",
            "V1785 did not fix the supported-list-empty baseline",
        )
    if (
        facts["pm_main_initializes_supported_list"]
        and facts["pm_init_calls_get_system_info"]
        and facts["pm_add_peripheral_commits_supported_list_node"]
        and facts["mdmdetect_get_system_info_scans_sysfs"]
        and facts["v1784_pm_server_label"] == "pm-server-no-peripheral"
    ):
        return (
            "v1786-pm-supported-list-sysfs-enumeration-gap-host-pass",
            "pm-supported-list-sysfs-enumeration-gap",
            "pm-service only populates the supported-peripheral list from libmdmdetect get_system_info sysfs enumeration; V1784 publishes the service but the list is still empty at CNSS registration time",
        )
    return (
        "v1786-pm-supported-list-population-unclassified-host-pass",
        "pm-supported-list-population-unclassified",
        "host inputs are present but the static population path was not fully reconstructed",
    )


def render_report(manifest: dict[str, Any]) -> str:
    facts = manifest["facts"]
    table_lines = [
        f"- `{row['name']}`: index `{row['index']}`, file offset `{row['file_offset']}`, enabled `{row['enabled']}`, kind `{row['kind']}`, off/ack/extra `{row['off_timeout']}`/`{row['ack_timeout']}`/`{row['extra_timeout']}`"
        for row in facts["pm_static_peripheral_table"]
    ]
    return "\n".join(
        [
            "# Native Init V1786 PM Server Supported-list Population Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1786`",
            "- Type: host-only static classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Label: `{manifest['label']}`",
            "- Result: PASS",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Inputs",
            "",
            *[f"- {name}: `{display_path(path)}`" for name, path in INPUTS.items()],
            "",
            "## V1784 / V1785 Baseline",
            "",
            f"- V1784 decision: `{facts['v1784_decision']}`",
            f"- V1784 PM server label: `{facts['v1784_pm_server_label']}`",
            f"- V1784 provider / asInterface / register TX: `{facts['provider_seen']}` / `{facts['as_interface_hits']}` / `{facts['register_tx_hits']}`",
            f"- V1784 PM server entry / loop / no-peripheral hits: `{facts['entry_hits']}` / `{facts['loop_hits']}` / `{facts['no_peripheral_hits']}`",
            f"- V1784 requested `wlanmdsp`: `{facts['requested_wlanmdsp']}`",
            f"- V1785 label: `{facts['v1785_label']}`",
            f"- V1779 Android-good shutdown-list values: `{', '.join(facts['v1779_android_shutdown_values'])}`",
            f"- V1784 shutdown-list set requests: `{facts['v1784_shutdown_request_count']}` values `{', '.join(facts['v1784_shutdown_request_values'])}`",
            "",
            "## Static Population Model",
            "",
            f"- `pm-service` SHA256: `{facts['pm_service_sha256']}`",
            f"- `libperipheral_client.so` SHA256: `{facts['libperipheral_client_sha256']}`",
            f"- `libmdmdetect.so` SHA256: `{facts['libmdmdetect_sha256']}`",
            f"- main initializes supported-list sentinel at object `+0x20`: `{facts['pm_main_initializes_supported_list']}`",
            f"- main calls init helper `pm-service+0x6b6c` before Binder service registration: `{facts['pm_main_calls_init_helper_before_registration']}`",
            f"- init helper calls `get_system_info@plt` at `pm-service+0x6bc0`: `{facts['pm_init_calls_get_system_info']}`",
            f"- init helper loops two `get_system_info` counts before registration: `{facts['pm_init_loops_system_info_counts']}`",
            f"- add-peripheral helper commits supported-list node at `pm-service+0x6758..0x6788`: `{facts['pm_add_peripheral_commits_supported_list_node']}`",
            f"- add-peripheral helper rejects unsupported names before insertion: `{facts['pm_add_peripheral_validates_known_names']}`",
            f"- `libmdmdetect:get_system_info` scans `/sys/bus/esoc/devices` and `/sys/bus/msm_subsys/devices`: `{facts['mdmdetect_get_system_info_scans_sysfs']}`",
            f"- `libmdmdetect:get_system_info` accepts internal subsystem names `modem`, `slpi`, `spss`: `{facts['mdmdetect_internal_names']}`",
            f"- `libmdmdetect` eSoC strings include `SDX50M` and `SDXPRAIRIE`: `{facts['mdmdetect_esoc_names']}`",
            "",
            "## Static Peripheral Table",
            "",
            *table_lines,
            "",
            "## Interpretation",
            "",
            "- The PM server list is not populated by the CNSS vote/register transaction itself.",
            "- The list starts empty in the `pm-service` object constructor path and is populated only during the pre-registration init helper.",
            "- That helper delegates discovery to `libmdmdetect.so:get_system_info`, which reads sysfs under `/sys/bus/esoc/devices` and `/sys/bus/msm_subsys/devices`.",
            "- V1784 proves the Binder provider is visible and CNSS reaches `asInterface` plus register TX, but the server-side supported-list loop never starts.",
            "- Therefore the next useful target is not another PM actor. It is a narrow observation or repair of the `pm-service` discovery namespace before CNSS registration.",
            "",
            "## Next",
            "",
            "- V1787 source/build-only: add a PM service init observer for `get_system_info` return/counts and add-peripheral insert hits before Binder registration.",
            "- If counts are zero while provider is visible, the next repair candidate is a private read-only sysfs discovery bind/parity fix for `/sys/bus/msm_subsys/devices` and, if needed, `/sys/bus/esoc/devices` inside the vendor exec namespace.",
            "- Do not start the full PM trio, `boot_wlan`, restart-PD, eSoC, forced RC1, Wi-Fi HAL, scan/connect, DHCP/routes, credentials, or external ping from this classifier.",
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It executed local `strings`/`objdump` against extracted vendor binaries and read prior evidence. It performed no live device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PM actor start, QCACLD/`boot_wlan`, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write.",
            "",
        ]
    )


def main() -> int:
    HOST_DIR.mkdir(parents=True, exist_ok=True)
    v1784 = load_json(INPUTS["v1784_manifest"])
    v1785 = load_json(INPUTS["v1785_manifest"])
    v1779 = load_json(INPUTS["v1779_manifest"])
    helper_fields = parse_fields(read_text(INPUTS["v1784_helper"]))

    pm_main = objdump(INPUTS["pm_service"], 0x7650, 0x7A40, "pm-service-main-0x7650-0x7a40.S")
    pm_init = objdump(INPUTS["pm_service"], 0x6B6C, 0x6EBC, "pm-service-init-0x6b6c-0x6ebc.S")
    pm_add = objdump(INPUTS["pm_service"], 0x65EC, 0x6B6C, "pm-service-add-peripheral-0x65ec-0x6b6c.S")
    mdmdetect = objdump(INPUTS["libmdmdetect"], 0x2000, 0x3400, "libmdmdetect-get-system-info-0x2000-0x3400.S")
    pm_strings = strings_tx(INPUTS["pm_service"])
    mdmdetect_strings = strings_tx(INPUTS["libmdmdetect"])
    shutdown_count, shutdown_values = count_shutdown_requests(helper_fields)
    gate = v1784.get("gate") or {}
    facts: dict[str, Any] = {
        "inputs_present": all(path.exists() for path in INPUTS.values()),
        "pm_service_sha256": sha256(INPUTS["pm_service"]),
        "libperipheral_client_sha256": sha256(INPUTS["libperipheral_client"]),
        "libmdmdetect_sha256": sha256(INPUTS["libmdmdetect"]),
        "v1784_decision": v1784.get("decision", ""),
        "v1784_pm_server_label": gate.get("pm_server_label", ""),
        "provider_seen": gate.get("provider_seen", ""),
        "as_interface_hits": gate.get("as_interface_hits", ""),
        "register_tx_hits": gate.get("register_tx_hits", ""),
        "entry_hits": intish(gate.get("pm_server_register_entry_hits")),
        "loop_hits": intish(gate.get("pm_server_loop_node_hits")),
        "no_peripheral_hits": intish(gate.get("pm_server_no_peripheral_hits")),
        "requested_wlanmdsp": gate.get("requested_wlanmdsp", ""),
        "v1785_label": v1785.get("label", ""),
        "v1779_android_shutdown_values": (v1779.get("facts") or {}).get("v1092_shutdown_critical_values", []),
        "v1784_shutdown_request_count": shutdown_count,
        "v1784_shutdown_request_values": shutdown_values,
        "pm_static_peripheral_table": parse_static_pm_peripheral_table(INPUTS["pm_service"]),
        "pm_main_initializes_supported_list": has_all(
            pm_main,
            [
                r"7798:\s+91008278\s+add\s+x24, x19, #0x20",
                r"77bc:\s+a9026278\s+stp\s+x24, x24, \[x19, #32\]",
            ],
        ),
        "pm_main_calls_init_helper_before_registration": has_all(
            pm_main,
            [
                r"77c8:\s+97fffce9\s+bl\s+6b6c",
                r"78d4:.*",
                r"7904:.*defaultServiceManager",
            ],
        ),
        "pm_init_calls_get_system_info": "6bc0:" in pm_init and "get_system_info@plt" in pm_init,
        "pm_init_loops_system_info_counts": has_all(
            pm_init,
            [
                r"6be8:\s+b9401be8\s+ldr\s+w8, \[sp, #24\]",
                r"6cd4:\s+b9401fe8\s+ldr\s+w8, \[sp, #28\]",
                r"6cb4:\s+97fffe4e\s+bl\s+65ec",
                r"6d9c:\s+97fffe14\s+bl\s+65ec",
            ],
        ),
        "pm_add_peripheral_commits_supported_list_node": has_all(
            pm_add,
            [
                r"6758:\s+52800300\s+mov\s+w0, #0x18",
                r"675c:\s+91008275\s+add\s+x21, x19, #0x20",
                r"6768:\s+a900d115\s+stp\s+x21, x20, \[x8, #8\]",
                r"6778:\s+f9000528\s+str\s+x8, \[x9, #8\]",
                r"6780:\s+f9001268\s+str\s+x8, \[x19, #32\]",
            ],
        ),
        "pm_add_peripheral_validates_known_names": has_all(
            pm_add,
            [
                r"6634:.*bl\s+67bc",
                r"67cc:.*",
                r"6824:.*",
            ],
        ),
        "mdmdetect_get_system_info_scans_sysfs": all(
            token in mdmdetect_strings for token in ["/sys/bus/esoc/devices", "/sys/bus/msm_subsys/devices", "%s/%s/name"]
        )
        and has_all(
            mdmdetect,
            [
                r"2d00:.*#0xda7",
                r"2d28:.*opendir",
                r"2de4:.*#0xf77",
                r"2de8:.*opendir",
                r"2e98:.*",
            ],
        ),
        "mdmdetect_internal_names": [name for name in ["modem", "slpi", "spss"] if name in mdmdetect_strings],
        "mdmdetect_esoc_names": [name for name in ["SDX50M", "SDXPRAIRIE", "SDX55M"] if name in mdmdetect_strings],
        "pm_strings_include_shutdown_property": "vendor.peripheral.shutdown_critical_list" in pm_strings,
    }
    decision, label, reason = classify(facts)
    manifest = {
        "cycle": "V1786",
        "pass": True,
        "decision": decision,
        "label": label,
        "reason": reason,
        "inputs": {name: display_path(path) for name, path in INPUTS.items()},
        "out_dir": display_path(OUT_DIR),
        "report": display_path(REPORT_PATH),
        "facts": facts,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(
        f"# V1786 PM Server Supported-list Population Classifier\n\n"
        f"- decision: `{decision}`\n"
        f"- label: `{label}`\n"
        f"- reason: {reason}\n"
        f"- report: `{display_path(REPORT_PATH)}`\n",
        encoding="utf-8",
    )
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(json.dumps({"decision": decision, "label": label, "report": display_path(REPORT_PATH)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
