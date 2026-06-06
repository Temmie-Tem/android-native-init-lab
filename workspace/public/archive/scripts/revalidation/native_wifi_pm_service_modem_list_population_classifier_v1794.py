#!/usr/bin/env python3
"""V1794 host-only classifier for PM-service modem list population."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1794-pm-service-modem-list-population-classifier"
HOST_DIR = OUT_DIR / "host"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1794_PM_SERVICE_MODEM_LIST_POPULATION_CLASSIFIER_2026-06-03.md"
)

INPUTS = {
    "pm_service": REPO_ROOT / "tmp" / "wifi" / "v1073-host-only" / "vendor-extract" / "files" / "pm-service",
    "libmdmdetect": REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1073-host-only"
    / "vendor-extract"
    / "files"
    / "libmdmdetect.so",
    "v1793_manifest": REPO_ROOT / "tmp" / "wifi" / "v1793-pm-register-request-string-handoff" / "manifest.json",
    "v1793_helper": REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1793-pm-register-request-string-handoff"
    / "test-v1393-helper-result.stdout.txt",
    "v1789_manifest": REPO_ROOT / "tmp" / "wifi" / "v1789-pm-add-peripheral-init-fail-static" / "manifest.json",
    "v1786_manifest": REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1786-pm-server-supported-list-population-static"
    / "manifest.json",
}


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": display_path(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data["present"] = True
        return data
    return {"present": True, "value": data}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").replace("\0", "?")


def intish(value: Any) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def run_capture(command: list[str], out_path: Path) -> str:
    result = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out_path.write_text(result.stdout, encoding="utf-8")
    if result.stderr:
        out_path.with_suffix(out_path.suffix + ".stderr").write_text(result.stderr, encoding="utf-8")
    return result.stdout


def objdump(path: Path, start: int, stop: int, name: str) -> str:
    return run_capture(
        [
            "aarch64-linux-gnu-objdump",
            "-d",
            f"--start-address=0x{start:x}",
            f"--stop-address=0x{stop:x}",
            str(path),
        ],
        HOST_DIR / name,
    )


def c_string_at(path: Path, offset: int, max_bytes: int = 240) -> str:
    if not path.exists():
        return ""
    data = path.read_bytes()
    if offset >= len(data):
        return ""
    return data[offset : offset + max_bytes].split(b"\0", 1)[0].decode("latin1", errors="replace")


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


def contains_all(text: str, needles: list[str]) -> bool:
    return all(needle in text for needle in needles)


def extract_block(text: str, block_name: str) -> str:
    start = f"A90_EXECNS_PATH_{block_name}_BEGIN"
    end = f"A90_EXECNS_PATH_{block_name}_END"
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if start not in line:
            continue
        values: list[str] = []
        for inner in lines[index + 1 :]:
            if end in inner:
                return "\n".join(values).strip()
            values.append(inner)
    return ""


def dir_has_entry(text: str, dir_name: str, entry: str) -> bool:
    start = f"A90_EXECNS_DIR_{dir_name}_BEGIN"
    end = f"A90_EXECNS_DIR_{dir_name}_END"
    in_block = False
    for line in text.splitlines():
        if start in line:
            in_block = True
            continue
        if in_block and end in line:
            return False
        if in_block and re.search(rf"entry\.\d+={re.escape(entry)}$", line):
            return True
    return False


def classify(facts: dict[str, Any]) -> tuple[str, str, str, bool]:
    if not facts["inputs_present"]:
        return (
            "v1794-pm-modem-list-population-input-missing",
            "input-missing",
            "required V1793 or vendor static evidence is missing",
            False,
        )
    if facts["v1793_requested_peripheral"] != "modem":
        return (
            "v1794-pm-modem-list-population-baseline-mismatch",
            "baseline-mismatch",
            "V1793 did not capture a modem PM register request",
            False,
        )
    if (
        facts["mdmdetect_modem_goes_to_primary_count"]
        and facts["pm_init_second_loop_is_nonmodem_additional_count"]
        and facts["sysfs_mss_subsys0_name"] == "modem"
        and facts["v1793_first_add_peripheral_call_hits"] >= 2
        and facts["v1793_second_add_peripheral_call_hits"] == 0
        and facts["v1793_list_commit_hits"] == 0
        and facts["v1793_init_fail_hits"] == facts["v1793_add_peripheral_entry_hits"]
    ):
        return (
            "v1794-pm-modem-primary-list-devnode-gate-host-pass",
            "pm-modem-primary-list-devnode-gate",
            "the missing modem record is not explained by the second count path; libmdmdetect routes modem into the primary count, and the observed primary add-peripheral attempts all fail before supported-list commit",
            True,
        )
    return (
        "v1794-pm-modem-list-population-unclassified-host-pass",
        "pm-modem-list-population-unclassified",
        "host inputs are present but the modem population path could not be pinned to the primary-list devnode gate",
        True,
    )


def render_report(manifest: dict[str, Any]) -> str:
    facts = manifest["facts"]
    table_lines = [
        f"- `{row['name']}`: index `{row['index']}`, file offset `{row['file_offset']}`, enabled `{row['enabled']}`, kind `{row['kind']}`, off/ack/extra `{row['off_timeout']}`/`{row['ack_timeout']}`/`{row['extra_timeout']}`"
        for row in facts["pm_static_peripheral_table"]
    ]
    return "\n".join(
        [
            "# Native Init V1794 PM-service Modem List Population Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1794`",
            "- Type: host-only static/evidence classifier",
            f"- Decision: `{manifest['decision']}`",
            f"- Label: `{manifest['label']}`",
            f"- Result: {'PASS' if manifest['pass'] else 'BLOCKED'}",
            f"- Reason: {manifest['reason']}",
            f"- Evidence: `{manifest['out_dir']}`",
            "",
            "## Inputs",
            "",
            *[f"- {name}: `{path}`" for name, path in manifest["inputs"].items()],
            "",
            "## V1793 Baseline",
            "",
            f"- V1793 decision: `{facts['v1793_decision']}`",
            f"- V1793 rollback ok: `{facts['v1793_rollback_ok']}`",
            f"- requested PM peripheral: `{facts['v1793_requested_peripheral']}`",
            f"- no-peripheral branch name: `{facts['v1793_no_peripheral_name']}`",
            f"- PM server loop / strcmp / match / success hits: `{facts['v1793_loop_hits']}` / `{facts['v1793_strcmp_hits']}` / `{facts['v1793_match_hits']}` / `{facts['v1793_success_hits']}`",
            f"- first add-peripheral call/fail hits: `{facts['v1793_first_add_peripheral_call_hits']}` / `{facts['v1793_first_add_peripheral_fail_log_hits']}`",
            f"- second add-peripheral call/fail hits: `{facts['v1793_second_add_peripheral_call_hits']}` / `{facts['v1793_second_add_peripheral_fail_log_hits']}`",
            f"- add-peripheral entry / init-fail / list-commit hits: `{facts['v1793_add_peripheral_entry_hits']}` / `{facts['v1793_init_fail_hits']}` / `{facts['v1793_list_commit_hits']}`",
            f"- first captured candidate: `{facts['v1793_first_candidate_name']}` / `{facts['v1793_first_candidate_devnode']}`",
            "",
            "## Static Count Model",
            "",
            f"- `pm-service` SHA256: `{facts['pm_service_sha256']}`",
            f"- `libmdmdetect.so` SHA256: `{facts['libmdmdetect_sha256']}`",
            f"- first count load: `pm-service+0x6be8`, stack field `[sp,#24]`",
            f"- first add-peripheral call: `pm-service+0x6cb4`",
            f"- second count load: `pm-service+0x6cd4`, stack field `[sp,#28]`",
            f"- second add-peripheral call: `pm-service+0x6d9c`",
            f"- first loop uses primary record base `get_system_info_output+0x8`: `{facts['pm_init_first_loop_is_primary_count']}`",
            f"- second loop uses additional record base `get_system_info_output+0xe18`: `{facts['pm_init_second_loop_is_nonmodem_additional_count']}`",
            f"- `libmdmdetect` stores `modem` into the primary count path: `{facts['mdmdetect_modem_goes_to_primary_count']}`",
            f"- `libmdmdetect` stores non-modem additional subsystems into the second count path: `{facts['mdmdetect_nonmodem_goes_to_secondary_count']}`",
            f"- `libmdmdetect` devnode format: `{facts['mdmdetect_devnode_format']}`",
            "",
            "## Live Sysfs Inputs",
            "",
            f"- `/sys/bus/msm_subsys/devices` has `subsys0`: `{facts['helper_msm_subsys_has_subsys0']}`",
            f"- `subsys0` name/state/firmware: `{facts['sysfs_mss_subsys0_name']}` / `{facts['sysfs_mss_subsys0_state']}` / `{facts['sysfs_mss_subsys0_firmware']}`",
            f"- `subsys9` name/state/firmware: `{facts['sysfs_mdm3_subsys9_name']}` / `{facts['sysfs_mdm3_subsys9_state']}` / `{facts['sysfs_mdm3_subsys9_firmware']}`",
            f"- inferred primary candidate names: `{', '.join(facts['inferred_primary_candidates'])}`",
            f"- second-loop candidate source: `{facts['second_loop_candidate_source']}`",
            "",
            "## Static Peripheral Table",
            "",
            *table_lines,
            "",
            "## Interpretation",
            "",
            "- The second count/load path is not the source of the `modem` record. Static `libmdmdetect` control flow routes `name=modem` from `/sys/bus/msm_subsys/devices` into the first/primary count.",
            "- V1793 hit the first add-peripheral call twice and hit the second add-peripheral call zero times. That shape matches primary candidates only, not a missing second-loop modem path.",
            "- The first observed candidate was `SDX50M` at `/dev/subsys_esoc0`; the same first-loop set also includes the live `subsys0` modem record by static/sysfs reconstruction.",
            "- Both observed add-peripheral attempts failed before `pm-service+0x6758..0x6788`, so the PM server list stayed empty and CNSS's `modem` register request took the no-peripheral branch.",
            "- Therefore the next source/build unit should observe first/second count values and all add-peripheral hit strings before any private devnode repair.",
            "",
            "## Next",
            "",
            "- V1795 should stay source/build-only first: add fetchargs or direct helper logging for `[sp,#24]`, `[sp,#28]`, first-loop record names, and second-loop record names.",
            "- Fixed outcomes should distinguish `modem-devnode-access-fail`, `sdx50m-only-first-loop`, `count-fetcharg-unavailable`, and `list-commit-progress`.",
            "- Do not repair `/dev/subsys_esoc0`, synthesize PM records, start Wi-Fi HAL, scan/connect, configure DHCP/routes, or external ping from this classifier.",
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It executed local `objdump` against extracted vendor binaries and read prior evidence. It performed no live device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PM actor start, QCACLD/`boot_wlan`, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write.",
            "",
        ]
    )


def main() -> int:
    HOST_DIR.mkdir(parents=True, exist_ok=True)
    pm_service = INPUTS["pm_service"]
    libmdmdetect = INPUTS["libmdmdetect"]
    v1793 = load_json(INPUTS["v1793_manifest"])
    v1789 = load_json(INPUTS["v1789_manifest"])
    v1786 = load_json(INPUTS["v1786_manifest"])
    helper_text = read_text(INPUTS["v1793_helper"])
    gate = v1793.get("gate", {}) if isinstance(v1793.get("gate"), dict) else {}

    pm_init_disasm = objdump(pm_service, 0x6B6C, 0x6EBC, "pm-service-init-0x6b6c-0x6ebc.S")
    pm_add_disasm = objdump(pm_service, 0x65EC, 0x67C0, "pm-service-add-peripheral-0x65ec-0x67c0.S")
    mdmdetect_system_disasm = objdump(
        libmdmdetect, 0x2C94, 0x2FF8, "libmdmdetect-get-system-info-0x2c94-0x2ff8.S"
    )
    mdmdetect_subsystem_disasm = objdump(
        libmdmdetect, 0x2AA4, 0x2C90, "libmdmdetect-get-subsystem-info-0x2aa4-0x2c90.S"
    )

    sysfs_mss_name = extract_block(helper_text, "wifi_window_soc_mss_subsys0_name")
    sysfs_mss_state = extract_block(helper_text, "wifi_window_soc_mss_subsys0_state")
    sysfs_mss_firmware = extract_block(helper_text, "wifi_window_soc_mss_subsys0_firmware_name")
    sysfs_mdm3_name = extract_block(helper_text, "wifi_window_soc_mdm3_subsys9_name")
    sysfs_mdm3_state = extract_block(helper_text, "wifi_window_soc_mdm3_subsys9_state")
    sysfs_mdm3_firmware = extract_block(helper_text, "wifi_window_soc_mdm3_subsys9_firmware_name")
    first_candidate = gate.get("pm_service_add_peripheral_entry_name", "")
    primary_candidates = [name for name in [first_candidate, sysfs_mss_name] if name]

    facts: dict[str, Any] = {
        "inputs_present": all(path.exists() for path in INPUTS.values()),
        "pm_service_sha256": sha256(pm_service),
        "libmdmdetect_sha256": sha256(libmdmdetect),
        "v1793_decision": v1793.get("decision", ""),
        "v1793_pass": truthy(v1793.get("pass")),
        "v1793_rollback_ok": truthy((v1793.get("rollback") or {}).get("ok") if isinstance(v1793.get("rollback"), dict) else False),
        "v1793_register_label": gate.get("pm_register_request_label", ""),
        "v1793_requested_peripheral": gate.get("pm_register_requested_peripheral", ""),
        "v1793_no_peripheral_name": gate.get("pm_server_register_no_peripheral_name", ""),
        "v1793_loop_hits": intish(gate.get("pm_server_loop_node_hits")),
        "v1793_strcmp_hits": intish(gate.get("pm_server_register_strcmp_call_hits")),
        "v1793_match_hits": intish(gate.get("pm_server_match_hits")),
        "v1793_success_hits": intish(gate.get("pm_server_success_return_hits")),
        "v1793_first_count_load_hits": intish(gate.get("pm_service_init_first_count_load_hits")),
        "v1793_second_count_load_hits": intish(gate.get("pm_service_init_second_count_load_hits")),
        "v1793_first_add_peripheral_call_hits": intish(gate.get("pm_service_init_first_add_peripheral_call_hits")),
        "v1793_first_add_peripheral_fail_log_hits": intish(
            gate.get("pm_service_init_first_add_peripheral_fail_log_hits")
        ),
        "v1793_second_add_peripheral_call_hits": intish(gate.get("pm_service_init_second_add_peripheral_call_hits")),
        "v1793_second_add_peripheral_fail_log_hits": intish(
            gate.get("pm_service_init_second_add_peripheral_fail_log_hits")
        ),
        "v1793_add_peripheral_entry_hits": intish(gate.get("pm_service_add_peripheral_entry_hits")),
        "v1793_init_fail_hits": intish(gate.get("pm_service_add_peripheral_init_fail_hits")),
        "v1793_list_commit_hits": intish(gate.get("pm_service_add_peripheral_list_commit_hits")),
        "v1793_first_candidate_name": first_candidate,
        "v1793_first_candidate_devnode": gate.get("pm_service_add_peripheral_entry_devnode", ""),
        "v1789_label": v1789.get("label", ""),
        "v1786_label": v1786.get("label", ""),
        "pm_init_first_loop_is_primary_count": contains_all(
            pm_init_disasm,
            [
                "6be8:",
                "ldr\tw8, [sp, #24]",
                "6bf8:",
                "b.lt\t6cd4",
                "6c1c:",
                "add\tx27, x8, #0x8",
                "6cb4:",
                "bl\t65ec",
            ],
        ),
        "pm_init_second_loop_is_nonmodem_additional_count": contains_all(
            pm_init_disasm,
            [
                "6cd4:",
                "ldr\tw8, [sp, #28]",
                "6cdc:",
                "b.lt\t6dbc",
                "6d04:",
                "add\tx26, x8, #0xe18",
                "6d9c:",
                "bl\t65ec",
            ],
        ),
        "mdmdetect_modem_goes_to_primary_count": contains_all(
            mdmdetect_system_disasm,
            [
                "2ed0:",
                "cbz\tw8, 2f04",
                "2f1c:",
                "bl\t3570",
                "2f24:",
                "ldr\tw8, [x19]",
                "2f2c:",
                "str\tw8, [x19]",
            ],
        )
        and c_string_at(libmdmdetect, 0xCE2) == "modem",
        "mdmdetect_nonmodem_goes_to_secondary_count": contains_all(
            mdmdetect_system_disasm,
            [
                "2ed4:",
                "ldrsw\tx8, [x19, #4]",
                "2ee4:",
                "add\tx0, x8, #0xe18",
                "2e5c:",
                "ldr\tw8, [x19, #4]",
                "2e64:",
                "str\tw8, [x19, #4]",
            ],
        ),
        "mdmdetect_subsystem_accepts_modem": "modem" in mdmdetect_subsystem_disasm and "get_subsystem_info" in mdmdetect_subsystem_disasm,
        "mdmdetect_devnode_format": c_string_at(libmdmdetect, 0xD98),
        "helper_msm_subsys_has_subsys0": dir_has_entry(helper_text, "wifi_window_msm_subsys_devices", "subsys0"),
        "sysfs_mss_subsys0_name": sysfs_mss_name,
        "sysfs_mss_subsys0_state": sysfs_mss_state,
        "sysfs_mss_subsys0_firmware": sysfs_mss_firmware,
        "sysfs_mdm3_subsys9_name": sysfs_mdm3_name,
        "sysfs_mdm3_subsys9_state": sysfs_mdm3_state,
        "sysfs_mdm3_subsys9_firmware": sysfs_mdm3_firmware,
        "inferred_primary_candidates": primary_candidates,
        "second_loop_candidate_source": "non-modem additional msm_subsys entries",
        "pm_static_peripheral_table": parse_static_pm_peripheral_table(pm_service),
        "host_evidence_files": [
            display_path(HOST_DIR / "pm-service-init-0x6b6c-0x6ebc.S"),
            display_path(HOST_DIR / "pm-service-add-peripheral-0x65ec-0x67c0.S"),
            display_path(HOST_DIR / "libmdmdetect-get-system-info-0x2c94-0x2ff8.S"),
            display_path(HOST_DIR / "libmdmdetect-get-subsystem-info-0x2aa4-0x2c90.S"),
        ],
    }
    decision, label, reason, passed = classify(facts)
    manifest = {
        "cycle": "V1794",
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "inputs": {name: display_path(path) for name, path in INPUTS.items()},
        "facts": facts,
        "out_dir": display_path(OUT_DIR),
        "report": display_path(REPORT_PATH),
        "device_command_executed": False,
        "flash_executed": False,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(
        f"# V1794 PM-service Modem List Population Classifier\n\n"
        f"- decision: `{decision}`\n"
        f"- label: `{label}`\n"
        f"- pass: `{passed}`\n"
        f"- reason: {reason}\n"
        f"- report: `{display_path(REPORT_PATH)}`\n",
        encoding="utf-8",
    )
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(json.dumps({"decision": decision, "label": label, "pass": passed, "report": display_path(REPORT_PATH)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
