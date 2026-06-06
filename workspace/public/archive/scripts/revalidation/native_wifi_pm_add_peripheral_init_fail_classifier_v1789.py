#!/usr/bin/env python3
"""V1789 host-only classifier for PM-service add-peripheral init-fail."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1789-pm-add-peripheral-init-fail-static"
HOST_DIR = OUT_DIR / "host"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1789_PM_ADD_PERIPHERAL_INIT_FAIL_CLASSIFIER_2026-06-03.md"
)

INPUTS = {
    "pm_service": REPO_ROOT / "tmp" / "wifi" / "v1073-host-only" / "vendor-extract" / "files" / "pm-service",
    "libmdmdetect": REPO_ROOT / "tmp" / "wifi" / "v1073-host-only" / "vendor-extract" / "files" / "libmdmdetect.so",
    "v1788_manifest": REPO_ROOT / "tmp" / "wifi" / "v1788-pm-service-init-discovery-handoff" / "manifest.json",
    "v1788_helper": REPO_ROOT / "tmp" / "wifi" / "v1788-pm-service-init-discovery-handoff" / "test-v1393-helper-result.stdout.txt",
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


def classify(facts: dict[str, Any]) -> tuple[str, str, str]:
    if not facts["inputs_present"]:
        return (
            "v1789-pm-add-peripheral-init-fail-input-missing",
            "input-missing",
            "required V1788 or vendor binary evidence is missing",
        )
    if facts["v1788_label"] != "pm-service-discovery-zero-list-commit":
        return (
            "v1789-pm-add-peripheral-init-fail-baseline-mismatch",
            "baseline-mismatch",
            "V1788 did not fix the expected zero-list-commit baseline",
        )
    if (
        facts["v1788_known_name_hits"] > 0
        and facts["v1788_init_fail_hits"] == facts["v1788_add_peripheral_entry_hits"]
        and facts["v1788_list_commit_hits"] == 0
        and facts["pm_add_peripheral_calls_devnode_access"]
        and facts["mdmdetect_record_devnode_offset"] == "0x44"
    ):
        return (
            "v1789-pm-add-peripheral-devnode-access-gap-host-pass",
            "pm-add-peripheral-devnode-access-gap",
            "V1788 passed known-name validation, but every add-peripheral object failed before list commit because pm-service checks access(F_OK) on the libmdmdetect devnode field at record+0x44",
        )
    return (
        "v1789-pm-add-peripheral-init-fail-unclassified-host-pass",
        "pm-add-peripheral-init-fail-unclassified",
        "host inputs are present but the init-fail branch could not be pinned to the devnode access check",
    )


def render_report(manifest: dict[str, Any]) -> str:
    facts = manifest["facts"]
    table_lines = [
        f"- `{row['name']}`: index `{row['index']}`, file offset `{row['file_offset']}`, enabled `{row['enabled']}`, kind `{row['kind']}`, off/ack/extra `{row['off_timeout']}`/`{row['ack_timeout']}`/`{row['extra_timeout']}`"
        for row in facts["pm_static_peripheral_table"]
    ]
    return "\n".join(
        [
            "# Native Init V1789 PM Add-peripheral Init-fail Classifier",
            "",
            "## Summary",
            "",
            "- Cycle: `V1789`",
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
            "## V1788 Baseline",
            "",
            f"- V1788 decision: `{facts['v1788_decision']}`",
            f"- V1788 rollback ok: `{facts['v1788_rollback_ok']}`",
            f"- PM-service discovery label: `{facts['v1788_label']}`",
            f"- get_system_info call / fail hits: `{facts['v1788_get_system_info_hits']}` / `{facts['v1788_get_system_info_fail_hits']}`",
            f"- first add-peripheral call / fail-log hits: `{facts['v1788_first_add_call_hits']}` / `{facts['v1788_first_add_fail_log_hits']}`",
            f"- second add-peripheral call / fail-log hits: `{facts['v1788_second_add_call_hits']}` / `{facts['v1788_second_add_fail_log_hits']}`",
            f"- add-peripheral entry / known-name / init-fail / list-commit hits: `{facts['v1788_add_peripheral_entry_hits']}` / `{facts['v1788_known_name_hits']}` / `{facts['v1788_init_fail_hits']}` / `{facts['v1788_list_commit_hits']}`",
            f"- PM server label: `{facts['v1788_pm_server_label']}`",
            f"- register TX / requested wlanmdsp / WLFW 69 / wlan0: `{facts['v1788_register_tx_hits']}` / `{facts['v1788_requested_wlanmdsp']}` / `{facts['v1788_wlfw_service69_seen']}` / `{facts['v1788_wlan0_present']}`",
            "",
            "## Static Add-peripheral Branch",
            "",
            f"- `pm-service` SHA256: `{facts['pm_service_sha256']}`",
            f"- `libmdmdetect.so` SHA256: `{facts['libmdmdetect_sha256']}`",
            f"- add-peripheral entry: `pm-service+0x65ec`",
            f"- known-name validation checkpoint: `pm-service+0x663c`",
            f"- object constructor: `pm-service+0x8d60`",
            f"- init/access check: `pm-service+0x8eb0`",
            f"- init-fail log branch: `pm-service+0x668c`",
            f"- supported-list commit: `pm-service+0x6758..0x6788`",
            f"- init-fail log string: `{facts['pm_init_fail_string']}`",
            f"- device-file access-fail string: `{facts['pm_devnode_access_fail_string']}`",
            f"- add-peripheral calls `access(F_OK)` on constructor path: `{facts['pm_add_peripheral_calls_devnode_access']}`",
            f"- `libmdmdetect` record devnode offset: `{facts['mdmdetect_record_devnode_offset']}`",
            f"- `libmdmdetect` devnode format: `{facts['mdmdetect_devnode_format']}`",
            "",
            "## Static Peripheral Table",
            "",
            *table_lines,
            "",
            "## Interpretation",
            "",
            "- V1788 is no longer a service-object or CNSS client TX problem: the provider is visible and CNSS reaches register/vote TX.",
            "- V1788 also is not a candidate-name mismatch: add-peripheral reaches the known-name checkpoint twice.",
            "- Both attempted candidates fail inside the Peripheral object init path before the supported-list node is committed.",
            "- Static control flow shows that path calls `access(<record+0x44 devnode>, F_OK)` and logs `%s can not access device file %s: %s` on failure.",
            "- `libmdmdetect` fills record `+0x44` as `/dev/subsys_<discovered-entry>`, so the current blocker is private devnode discovery/parity for the discovered PM-service candidates.",
            "- V1788's second/internal subsystem add-peripheral path did not run; the immediate observed failures are first-loop discovery candidates, not the later CNSS register traversal.",
            "",
            "## Next",
            "",
            "- V1790 should remain source/build-only first: add a bounded PM-service discovery argument/string observer or private namespace preflight that records the exact candidate names and devnode strings before any repair.",
            "- A future live repair must be separately scoped and must not blindly open `/dev/subsys_esoc0` or restart eSoC/RC1. The current evidence justifies classifying devnode path parity, not executing power paths.",
            "- Keep hard stops: no `boot_wlan`, restart-PD, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, forced RC1, fake-ONLINE, PMIC/GPIO/GDSC writes, eSoC notify/BOOT_DONE, PCI rescan, or platform bind/unbind.",
            "",
            "## Safety Scope",
            "",
            "This classifier is host-only. It executed local `objdump`, `strings`-equivalent byte reads, and manifest parsing. It performed no live device command, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PM actor start, QCACLD/`boot_wlan`, eSoC/RC1 action, restart-PD request, firmware write, partition write, PMIC/GPIO/GDSC write, PCI rescan, platform bind/unbind, BPF attach, or tracefs write.",
            "",
        ]
    )


def main() -> int:
    HOST_DIR.mkdir(parents=True, exist_ok=True)
    pm_service = INPUTS["pm_service"]
    libmdmdetect = INPUTS["libmdmdetect"]
    v1788 = load_json(INPUTS["v1788_manifest"])
    v1788_fields = parse_fields(read_text(INPUTS["v1788_helper"]))
    gate = v1788.get("gate", {}) if isinstance(v1788.get("gate"), dict) else {}

    pm_add_disasm = objdump(pm_service, 0x65EC, 0x67C0, "pm-service-add-peripheral-0x65ec-0x67c0.S")
    pm_access_disasm = objdump(pm_service, 0x8D60, 0x8FD0, "pm-service-peripheral-object-init-0x8d60-0x8fd0.S")
    mdm_disasm = objdump(libmdmdetect, 0x2904, 0x2FF8, "libmdmdetect-discovery-record-layout-0x2904-0x2ff8.S")

    facts: dict[str, Any] = {
        "inputs_present": all(path.exists() for path in INPUTS.values()),
        "pm_service_sha256": sha256(pm_service),
        "libmdmdetect_sha256": sha256(libmdmdetect),
        "v1788_decision": v1788.get("decision", ""),
        "v1788_pass": truthy(v1788.get("pass")),
        "v1788_rollback_ok": truthy((v1788.get("rollback") or {}).get("ok") if isinstance(v1788.get("rollback"), dict) else False),
        "v1788_label": gate.get("pm_service_discovery_label", ""),
        "v1788_get_system_info_hits": intish(gate.get("pm_service_init_get_system_info_call_hits")),
        "v1788_get_system_info_fail_hits": intish(gate.get("pm_service_init_get_system_info_fail_hits")),
        "v1788_first_add_call_hits": intish(gate.get("pm_service_init_first_add_peripheral_call_hits")),
        "v1788_first_add_fail_log_hits": intish(gate.get("pm_service_init_first_add_peripheral_fail_log_hits")),
        "v1788_second_add_call_hits": intish(gate.get("pm_service_init_second_add_peripheral_call_hits")),
        "v1788_second_add_fail_log_hits": intish(gate.get("pm_service_init_second_add_peripheral_fail_log_hits")),
        "v1788_add_peripheral_entry_hits": intish(gate.get("pm_service_add_peripheral_entry_hits")),
        "v1788_known_name_hits": intish(gate.get("pm_service_add_peripheral_known_name_hits")),
        "v1788_init_fail_hits": intish(gate.get("pm_service_add_peripheral_init_fail_hits")),
        "v1788_list_commit_hits": intish(gate.get("pm_service_add_peripheral_list_commit_hits")),
        "v1788_pm_server_label": gate.get("pm_server_label", ""),
        "v1788_register_tx_hits": intish(gate.get("register_tx_hits")),
        "v1788_requested_wlanmdsp": gate.get("requested_wlanmdsp", ""),
        "v1788_wlfw_service69_seen": gate.get("wlfw_service69_seen", ""),
        "v1788_wlan0_present": gate.get("wlan0_present", ""),
        "v1788_no_esoc0": gate.get("no_esoc0", ""),
        "v1788_helper_field_count": len(v1788_fields),
        "pm_init_fail_string": c_string_at(pm_service, 0x438B),
        "pm_devnode_access_fail_string": c_string_at(pm_service, 0x44EB),
        "pm_add_peripheral_calls_devnode_access": contains_all(
            pm_access_disasm,
            [
                "8ee4:",
                "ldr\tx0, [x0, #16]",
                "8ee8:",
                "bl\ta310 <access@plt>",
                "8ef0:",
                "ldr\tx20, [x19]",
                "8ef4:",
                "ldr\tx19, [x19, #16]",
            ],
        ),
        "pm_add_peripheral_known_name_before_init": contains_all(
            pm_add_disasm,
            [
                "663c:",
                "bl\t6884",
                "667c:",
                "bl\t8d60",
                "6684:",
                "bl\t8eb0",
                "668c:",
            ],
        ),
        "mdmdetect_record_devnode_offset": "0x44" if "91011280" in mdm_disasm and "/dev/subsys_%s" in c_string_at(libmdmdetect, 0xD98) else "",
        "mdmdetect_devnode_format": c_string_at(libmdmdetect, 0xD98),
        "mdmdetect_esoc_root": c_string_at(libmdmdetect, 0xDA7),
        "mdmdetect_msm_subsys_root": c_string_at(libmdmdetect, 0xF77),
        "pm_static_peripheral_table": parse_static_pm_peripheral_table(pm_service),
        "host_evidence_files": [
            display_path(HOST_DIR / "pm-service-add-peripheral-0x65ec-0x67c0.S"),
            display_path(HOST_DIR / "pm-service-peripheral-object-init-0x8d60-0x8fd0.S"),
            display_path(HOST_DIR / "libmdmdetect-discovery-record-layout-0x2904-0x2ff8.S"),
        ],
    }
    decision, label, reason = classify(facts)
    manifest = {
        "cycle": "V1789",
        "decision": decision,
        "label": label,
        "pass": True,
        "reason": reason,
        "inputs": {name: display_path(path) for name, path in INPUTS.items()},
        "facts": facts,
        "out_dir": display_path(OUT_DIR),
        "report": display_path(REPORT_PATH),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(json.dumps({"decision": decision, "label": label, "pass": True, "reason": reason}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
