#!/usr/bin/env python3
"""V844 host-only mdm3/ext-sdx50m boot-interface classifier.

V843 confirmed the current native `cnss-daemon` retry is alive before WLFW.
This classifier folds in the Samsung DTS and ICNSS source evidence that mdm3 is
an external SDX50M/eSoC path and that WLFW publication is driven by QRTR service
69 arrival, not by service-notifier UP callbacks.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v844-mdm3-ext-sdx50m-boot-interface-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v844-mdm3-ext-sdx50m-boot-interface-classifier.txt")
DEFAULT_V843_MANIFEST = Path("tmp/wifi/v843-current-window-cnss-stall-classifier/manifest.json")
DEFAULT_V819_MANIFEST = Path("tmp/wifi/v819-mdm3-esoc-registration-catalogue/manifest.json")
DEFAULT_V823_MANIFEST = Path("tmp/wifi/v823-ssctl-nameservice-matrix/manifest.json")
DEFAULT_V840_MANIFEST = Path("tmp/wifi/v840-provider-first-prearmed-listener-live/manifest.json")
DEFAULT_SOURCE_ROOT = Path("kernel_build/SM-A908N_KOR_12_Opensource/Kernel")

DTS_PATH = Path("arch/arm64/boot/dts/samsung/renovation/sm8150-sec-r3q-kor-overlay-r02.dts")
ICNSS_PATH = Path("drivers/soc/qcom/icnss.c")
ICNSS_QMI_PATH = Path("drivers/soc/qcom/icnss_qmi.c")

EXPECTED_V843 = "v843-cnss-retry-poll-futex-prewlfw-event-gap"
EXPECTED_V819 = "v819-mdm3-esoc-registration-catalogue-captured"
EXPECTED_V823 = "v823-ssctl-nameservice-clean-empty-below-hal"
EXPECTED_V840 = "v840-provider-first-prearmed-no-indication"


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: Any
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v843-manifest", type=Path, default=DEFAULT_V843_MANIFEST)
    parser.add_argument("--v819-manifest", type=Path, default=DEFAULT_V819_MANIFEST)
    parser.add_argument("--v823-manifest", type=Path, default=DEFAULT_V823_MANIFEST)
    parser.add_argument("--v840-manifest", type=Path, default=DEFAULT_V840_MANIFEST)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "error": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "error": "not-json-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def nested(data: Any, *keys: Any) -> Any:
    current: Any = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            return None
    return current


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass"}


def line_of(text: str, pattern: str, flags: int = 0) -> int | None:
    regex = re.compile(pattern, flags)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return None


def source_info(root: Path, relative: Path) -> dict[str, Any]:
    resolved = repo_path(root / relative)
    return {
        "path": str(resolved),
        "exists": resolved.exists(),
        "size": resolved.stat().st_size if resolved.exists() else None,
    }


def extract_mdm3_block(dts: str) -> str:
    start = dts.find("qcom,mdm3 {")
    if start < 0:
        return ""
    brace = 0
    end = start
    entered = False
    for index in range(start, len(dts)):
        char = dts[index]
        if char == "{":
            brace += 1
            entered = True
        elif char == "}":
            brace -= 1
            if entered and brace == 0:
                end = index + 1
                break
    return dts[start:end]


def extract_property(block: str, name: str) -> str:
    match = re.search(rf"{re.escape(name)}\s*=\s*([^;]+);", block)
    return match.group(1).strip().strip('"') if match else ""


def analyze_dts(source_root: Path) -> dict[str, Any]:
    dts_path = source_root / DTS_PATH
    dts = read_text(dts_path)
    block = extract_mdm3_block(dts)
    properties = {
        "compatible": extract_property(block, "compatible"),
        "mdm_link_info": extract_property(block, "qcom,mdm-link-info"),
        "sysmon_id": extract_property(block, "qcom,sysmon-id"),
        "ssctl_instance_id": extract_property(block, "qcom,ssctl-instance-id"),
        "mdm2ap_status_gpio": extract_property(block, "qcom,mdm2ap-status-gpio"),
        "ap2mdm_status_gpio": extract_property(block, "qcom,ap2mdm-status-gpio"),
        "ap2mdm_soft_reset_gpio": extract_property(block, "qcom,ap2mdm-soft-reset-gpio"),
        "interrupt_names": extract_property(block, "interrupt-names"),
        "status": extract_property(block, "status"),
    }
    return {
        "source": source_info(source_root, DTS_PATH),
        "block_found": bool(block),
        "block_line": line_of(dts, r"qcom,mdm3\s*\{"),
        "properties": properties,
        "anchors": {
            "compatible_ext_sdx50m": properties["compatible"] == "qcom,ext-sdx50m",
            "mdm_link_0305": properties["mdm_link_info"] == "0305_01.01.00",
            "sysmon_id_20": properties["sysmon_id"] == "<0x14>",
            "ssctl_instance_16": properties["ssctl_instance_id"] == "<0x10>",
            "mdm2ap_status_gpio_142": "0x8e" in properties["mdm2ap_status_gpio"].lower(),
            "ap2mdm_status_gpio_135": "0x87" in properties["ap2mdm_status_gpio"].lower(),
            "ap2mdm_soft_reset_gpio_present": bool(properties["ap2mdm_soft_reset_gpio"]),
            "status_ok": properties["status"] == "ok",
        },
    }


def analyze_icnss_source(source_root: Path) -> dict[str, Any]:
    icnss = read_text(source_root / ICNSS_PATH)
    qmi = read_text(source_root / ICNSS_QMI_PATH)
    anchors = {
        "service_notifier_callback": line_of(icnss, r"static int icnss_service_notifier_notify"),
        "service_notifier_ignores_non_down": line_of(icnss, r"notification != SERVREG_NOTIF_SERVICE_STATE_DOWN_V01"),
        "service_notifier_up_only_clears_fw_down": line_of(icnss, r"notification == SERVREG_NOTIF_SERVICE_STATE_UP_V01"),
        "service_notifier_registered_from_domain_list": line_of(icnss, r"service_notif_register_notifier\(pd->domain_list\[i\]\.name"),
        "wlfw_new_server": line_of(qmi, r"static int wlfw_new_server"),
        "wlfw_server_arrive_event": line_of(qmi, r"ICNSS_DRIVER_EVENT_SERVER_ARRIVE"),
        "wlfw_lookup_registration": line_of(qmi, r"qmi_add_lookup\(&priv->qmi,\s*WLFW_SERVICE_ID_V01"),
    }
    return {
        "sources": {
            str(ICNSS_PATH): source_info(source_root, ICNSS_PATH),
            str(ICNSS_QMI_PATH): source_info(source_root, ICNSS_QMI_PATH),
        },
        "anchors": anchors,
        "all_required_present": all(value is not None for value in anchors.values()),
    }


def marker_counts(v840: dict[str, Any], v843: dict[str, Any]) -> dict[str, int]:
    counts = nested(v843, "analysis", "surface", "counts")
    if not isinstance(counts, dict):
        counts = nested(v840, "provider_first_prearmed", "provider_manifest", "live", "v655_counts")
    if not isinstance(counts, dict):
        counts = {}
    keys = (
        "service_notifier_180",
        "service_notifier_74",
        "cnss_daemon_netlink",
        "cnss_daemon_cld80211",
        "wlfw_start",
        "wlfw_service_request",
        "wlan_pd",
        "qmi_server_connected",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    )
    return {key: int_value(counts.get(key)) for key in keys}


def analyze_existing_evidence(v843: dict[str, Any], v819: dict[str, Any], v823: dict[str, Any], v840: dict[str, Any]) -> dict[str, Any]:
    counts = marker_counts(v840, v843)
    mdm3_states = nested(v819, "checks", 1, "detail", "mdm3")
    if not isinstance(mdm3_states, list):
        mdm3_states = []
    v817 = v819.get("wrapped_v817") if isinstance(v819.get("wrapped_v817"), dict) else {}
    before = nested(v817, "checks", 6, "detail", "before_holder") or {}
    after = nested(v817, "checks", 6, "detail", "after_companion") or {}
    v823_reason = str(v823.get("reason", ""))
    return {
        "v843": {
            "decision": v843.get("decision"),
            "pass": bool_value(v843.get("pass")),
            "main_wchan": nested(v843, "analysis", "surface", "main_wchan"),
            "cnss_user_socket": nested(v843, "analysis", "surface", "cnss_user_socket"),
            "netlink_has_retry_pid": nested(v843, "analysis", "surface", "netlink_has_retry_pid"),
        },
        "v819": {
            "decision": v819.get("decision"),
            "pass": bool_value(v819.get("pass")),
            "mdm3_states": mdm3_states,
            "esoc0_open_executed": bool_value(v819.get("esoc0_open_executed")),
            "esoc_surface_present": bool_value(after.get("esoc_surface_present")),
            "before_mss": before.get("mss_or_modem_state"),
            "after_mss": after.get("mss_or_modem_state"),
            "after_mdm3": after.get("mdm3_state"),
        },
        "v823": {
            "decision": v823.get("decision"),
            "pass": bool_value(v823.get("pass")),
            "ssctl_clean_empty": "clean-empty" in str(v823.get("decision", "")) or "end-of-list" in v823_reason,
            "reason": v823.get("reason", ""),
        },
        "v840": {
            "decision": v840.get("decision"),
            "pass": bool_value(v840.get("pass")),
            "listener_open_at_service74": nested(v840, "provider_first_prearmed", "timing", "listener_open_at_service74"),
            "held_5s_after_service74": nested(v840, "provider_first_prearmed", "timing", "held_5s_after_service74"),
        },
        "counts": counts,
        "missing_wlfw_chain": not any(
            int_value(counts.get(key))
            for key in ("wlfw_start", "wlan_pd", "qmi_server_connected", "bdf_regdb", "bdf_bdwlan", "wlan_fw_ready", "wlan0")
        ),
    }


def check(name: str, status: bool, detail: Any, next_step: str, severity: str = "blocker") -> Check:
    return Check(name, "pass" if status else "blocked", severity, detail, next_step)


def candidate(name: str, classification: str, reason: str, next_step: str) -> dict[str, str]:
    return {
        "candidate": name,
        "classification": classification,
        "reason": reason,
        "next_step": next_step,
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    source_root = repo_path(args.source_root)
    v843 = load_json(args.v843_manifest)
    v819 = load_json(args.v819_manifest)
    v823 = load_json(args.v823_manifest)
    v840 = load_json(args.v840_manifest)
    dts = analyze_dts(source_root)
    icnss = analyze_icnss_source(source_root)
    evidence = analyze_existing_evidence(v843, v819, v823, v840)
    checks = [
        check(
            "v843-input",
            v843.get("decision") == EXPECTED_V843 and bool_value(v843.get("pass")),
            {"decision": v843.get("decision"), "pass": v843.get("pass")},
            "refresh V843 current-window stall classifier",
        ),
        check(
            "v819-input",
            v819.get("decision") == EXPECTED_V819 and bool_value(v819.get("pass")),
            evidence["v819"],
            "refresh V819 read-only mdm3/eSoC catalogue",
        ),
        check(
            "v823-input",
            v823.get("decision") == EXPECTED_V823 and bool_value(v823.get("pass")),
            evidence["v823"],
            "refresh V823 SSCTL 43/16 nameservice matrix",
        ),
        check(
            "v840-input",
            v840.get("decision") == EXPECTED_V840 and bool_value(v840.get("pass")),
            evidence["v840"],
            "refresh V840 provider-first prearmed listener evidence",
        ),
        check(
            "dts-mdm3-ext-sdx50m",
            bool(dts["block_found"]) and all(dts["anchors"].values()),
            dts,
            "verify Samsung r3q overlay DTS before selecting mdm3/eSoC path",
        ),
        check(
            "icnss-wlfw-source-path",
            bool(icnss["all_required_present"]),
            icnss["anchors"],
            "verify ICNSS service-notifier and WLFW server-arrival source anchors",
        ),
        check(
            "native-mdm3-offline-wlfw-absent",
            evidence["v819"]["after_mss"] == "ONLINE"
            and evidence["v819"]["after_mdm3"] == "OFFLINING"
            and evidence["v819"]["esoc_surface_present"]
            and evidence["v823"]["ssctl_clean_empty"]
            and evidence["missing_wlfw_chain"],
            {
                "mss_after": evidence["v819"]["after_mss"],
                "mdm3_after": evidence["v819"]["after_mdm3"],
                "esoc_surface_present": evidence["v819"]["esoc_surface_present"],
                "ssctl_clean_empty": evidence["v823"]["ssctl_clean_empty"],
                "counts": evidence["counts"],
            },
            "if mdm3 or WLFW already advanced, route to WLFW/BDF continuation instead",
        ),
        check(
            "host-only-boundary",
            True,
            "V844 reads existing evidence and local OSRC source only",
            "keep V844 non-mutating",
        ),
    ]
    blocked = [item.name for item in checks if item.status != "pass" and item.severity == "blocker"]
    derived = {
        "mdm3_is_ext_sdx50m": bool(dts["anchors"].get("compatible_ext_sdx50m")),
        "mdm3_uses_ap2mdm_gpio": bool(dts["anchors"].get("ap2mdm_status_gpio_135")),
        "mdm3_uses_mdm2ap_gpio": bool(dts["anchors"].get("mdm2ap_status_gpio_142")),
        "mdm3_ssctl_instance": dts["properties"].get("ssctl_instance_id"),
        "mdm3_sysmon_id": dts["properties"].get("sysmon_id"),
        "service_notifier_up_not_initial_boot_trigger": icnss["anchors"].get("service_notifier_ignores_non_down") is not None,
        "wlfw_depends_on_qrtr_service69_arrival": icnss["anchors"].get("wlfw_new_server") is not None
        and icnss["anchors"].get("wlfw_lookup_registration") is not None,
        "native_mss_online_mdm3_offlining": evidence["v819"]["after_mss"] == "ONLINE"
        and evidence["v819"]["after_mdm3"] == "OFFLINING",
        "selected_next_gate": "v845-read-only-mdm3-ext-sdx50m-esoc-gpio-surface",
    }
    result = {
        "cycle": "v844",
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "v843": {"path": str(repo_path(args.v843_manifest)), "decision": v843.get("decision"), "pass": bool_value(v843.get("pass"))},
            "v819": {"path": str(repo_path(args.v819_manifest)), "decision": v819.get("decision"), "pass": bool_value(v819.get("pass"))},
            "v823": {"path": str(repo_path(args.v823_manifest)), "decision": v823.get("decision"), "pass": bool_value(v823.get("pass"))},
            "v840": {"path": str(repo_path(args.v840_manifest)), "decision": v840.get("decision"), "pass": bool_value(v840.get("pass"))},
        },
        "dts": dts,
        "icnss_source": icnss,
        "evidence": evidence,
        "derived": derived,
        "checks": [asdict(item) for item in checks],
        "candidate_matrix": [
            candidate(
                "repeat service-notifier listener",
                "reject",
                "DTS/source show service-notifier UP is not the initial WLFW boot trigger; V838/V840 already held a listener through service74",
                "do not repeat V830-V840 listener gates unchanged",
            ),
            candidate(
                "repeat CNSS launcher repair",
                "reject",
                "V842/V843 close broad launcher identity/fd/liveness enough for the current blocker",
                "do not redesign launcher before mdm3/eSoC boot surface is classified",
            ),
            candidate(
                "Wi-Fi HAL / scan / connect / DHCP / external ping",
                "blocked",
                "WLFW service69, FW_READY, BDF, wiphy, and wlan0 are still absent",
                "keep final bring-up blocked until mdm3/WLFW progresses",
            ),
            candidate(
                "raw esoc0 open or GPIO write",
                "blocked",
                "raw esoc0 open previously blocks and DTS GPIO manipulation changes external modem state",
                "only read-only esoc/GPIO/sysfs surface may run next",
            ),
            candidate(
                "mdm3/ext-sdx50m eSoC boot interface",
                "select-next",
                "DTS identifies mdm3 as qcom,ext-sdx50m with AP/MDM GPIO handshake and SSCTL instance 16; native evidence has mss ONLINE but mdm3 OFFLINING and no WLFW",
                "V845 should capture read-only mdm3/eSoC GPIO and sysfs control-surface state before any write",
            ),
        ],
        "device_commands_executed": False,
        "device_mutations": False,
        "qmi_payload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "esoc0_open_executed": False,
        "gpio_write_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
    }
    if args.command == "plan":
        result.update(
            {
                "decision": "v844-mdm3-ext-sdx50m-boot-interface-plan-ready",
                "pass": True,
                "reason": "plan-only; no device command, QRTR/QMI payload, esoc open, GPIO write, daemon start, Wi-Fi action, credential, route, ping, or flash executed",
                "next_step": "run V844 host-only classifier against DTS, ICNSS source, and existing mdm3/WLFW evidence",
            }
        )
    elif blocked:
        result.update(
            {
                "decision": "v844-mdm3-ext-sdx50m-boot-interface-blocked",
                "pass": False,
                "reason": "blocked by " + ", ".join(blocked),
                "next_step": "refresh blocked input evidence before selecting a live mdm3/eSoC gate",
            }
        )
    else:
        result.update(
            {
                "decision": "v844-mdm3-ext-sdx50m-boot-interface-selected",
                "pass": True,
                "reason": "DTS identifies mdm3 as qcom,ext-sdx50m with AP/MDM GPIO handshake; ICNSS source shows service-notifier UP is not the initial WLFW trigger and WLFW depends on service69 arrival; native has mss ONLINE but mdm3 OFFLINING and no WLFW",
                "next_step": "V845 should perform a read-only live mdm3/ext-sdx50m eSoC GPIO/sysfs surface snapshot; no raw esoc0 open, GPIO write, HAL, scan/connect, DHCP, external ping, or boot image work",
            }
        )
    return result


def summary_text(result: dict[str, Any]) -> str:
    dts = result.get("dts", {})
    props = dts.get("properties", {})
    derived = result.get("derived", {})
    evidence = result.get("evidence", {})
    counts = evidence.get("counts", {})
    lines = [
        "# V844 mdm3/ext-sdx50m Boot Interface Classifier",
        "",
        f"- generated: `{result['generated_at']}`",
        f"- command: `{result['command']}`",
        f"- decision: `{result['decision']}`",
        f"- pass: `{result['pass']}`",
        f"- reason: {result['reason']}",
        f"- next_step: {result['next_step']}",
        f"- device_commands_executed: `{result['device_commands_executed']}`",
        f"- esoc0_open_executed: `{result['esoc0_open_executed']}`",
        f"- gpio_write_executed: `{result['gpio_write_executed']}`",
        f"- wifi_hal_start_executed: `{result['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{result['scan_connect_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(
            ["name", "status", "severity", "detail", "next"],
            [[item["name"], item["status"], item["severity"], json.dumps(item["detail"], ensure_ascii=False, sort_keys=True), item["next_step"]] for item in result["checks"]],
        ),
        "",
        "## DTS mdm3 Properties",
        "",
        markdown_table(
            ["property", "value"],
            [[key, value] for key, value in props.items()],
        ),
        "",
        "## Derived",
        "",
        markdown_table(
            ["signal", "value"],
            [[key, value] for key, value in derived.items()],
        ),
        "",
        "## Existing Evidence",
        "",
        markdown_table(
            ["signal", "value"],
            [
                ["mss after lower window", evidence.get("v819", {}).get("after_mss")],
                ["mdm3 after lower window", evidence.get("v819", {}).get("after_mdm3")],
                ["esoc surface present", evidence.get("v819", {}).get("esoc_surface_present")],
                ["SSCTL 43/16 clean-empty", evidence.get("v823", {}).get("ssctl_clean_empty")],
                ["wlfw_start", counts.get("wlfw_start")],
                ["wlan_pd", counts.get("wlan_pd")],
                ["qmi_server_connected", counts.get("qmi_server_connected")],
                ["wlan0", counts.get("wlan0")],
            ],
        ),
        "",
        "## Candidate Matrix",
        "",
        markdown_table(
            ["candidate", "classification", "reason", "next"],
            [[item["candidate"], item["classification"], item["reason"], item["next_step"]] for item in result["candidate_matrix"]],
        ),
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    result = classify(args)
    store.write_json("manifest.json", result)
    store.write_text("summary.md", summary_text(result))
    write_private_text(repo_path(LATEST_POINTER), str(repo_path(args.out_dir)) + "\n")
    print(f"decision: {result['decision']}")
    print(f"pass: {result['pass']}")
    print(f"reason: {result['reason']}")
    print(f"next: {result['next_step']}")
    print(f"device_commands_executed: {result['device_commands_executed']}")
    print(f"esoc0_open_executed: {result['esoc0_open_executed']}")
    print(f"gpio_write_executed: {result['gpio_write_executed']}")
    print(f"wifi_hal_start_executed: {result['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {result['scan_connect_executed']}")
    print(f"external_ping_executed: {result['external_ping_executed']}")
    print(f"evidence: {repo_path(args.out_dir)}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
