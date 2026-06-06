#!/usr/bin/env python3
"""V1144 host-only classifier for the post-PM eSoC wait ioctl contract.

This script consumes V1143 lower-trace evidence and Samsung eSoC source/header
artifacts only. It does not contact the device, open eSoC/subsys nodes, start
Wi-Fi HAL, scan/connect, use credentials, run DHCP/routes, external ping, or
write boot/partitions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text, workspace_private_input_path


DEFAULT_OUT_DIR = Path("tmp/wifi/v1144-esoc-wait-ioctl-contract")
LATEST_POINTER = Path("tmp/wifi/latest-v1144-esoc-wait-ioctl-contract.txt")
DEFAULT_V1143 = Path("tmp/wifi/v1143-post-pm-lower-trace-live/manifest.json")

UAPI_ESOC_CTRL = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'include', 'uapi', 'linux', 'esoc_ctrl.h')
ESOC_CLIENT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel', 'include', 'linux', 'esoc_client.h')
ESOC_SOURCE_ROOT = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source/drivers/esoc")
ESOC_DEV = ESOC_SOURCE_ROOT / "esoc_dev.c"
ESOC_MDM_PON = ESOC_SOURCE_ROOT / "esoc-mdm-pon.c"
ESOC_MDM_4X = ESOC_SOURCE_ROOT / "esoc-mdm-4x.c"
ESOC_MDM_DRV = ESOC_SOURCE_ROOT / "esoc-mdm-drv.c"
ESOC_BUS = ESOC_SOURCE_ROOT / "esoc_bus.c"

HISTORICAL_REPORTS = {
    "v884": Path("docs/reports/NATIVE_INIT_V884_REQ_REGISTERED_SUBSYS_HOLD_OBSERVER_2026-05-26.md"),
    "v885": Path("docs/reports/NATIVE_INIT_V885_ESOC_REQ_IMG_RESPONSE_CLASSIFIER_2026-05-26.md"),
    "v891": Path("docs/reports/NATIVE_INIT_V891_ESOC_CONDITIONAL_RESPONSE_PROOF_2026-05-26.md"),
    "v893": Path("docs/reports/NATIVE_INIT_V893_ESOC_POST_IMG_XFER_CLASSIFIER_2026-05-26.md"),
    "v896": Path("docs/reports/NATIVE_INIT_V896_ANDROID_MDM_HELPER_IMAGE_CONTRACT_2026-05-26.md"),
    "v911": Path("docs/reports/NATIVE_INIT_V911_MDM_HELPER_ESOC_FD_STALL_CLASSIFIER_2026-05-26.md"),
    "v1020": Path("docs/reports/NATIVE_INIT_V1020_AFTER_FD_SUBSYS_WINDOW_LIVE_2026-05-26.md"),
}

IOCTL_REQUEST_RE = re.compile(r"\b0x[0-9a-fA-F]+\b")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1143", type=Path, default=DEFAULT_V1143)
    return parser.parse_args()


def read_text(path: Path, limit: int = 4_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def intish(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return 0
    try:
        return int(text, 0)
    except ValueError:
        return 0


def nested_get(data: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    current: Any = data
    for item in path:
        if not isinstance(current, dict):
            return default
        current = current.get(item)
    return default if current is None else current


def decode_ioctl(value: int) -> dict[str, Any]:
    nr = value & 0xFF
    ioctl_type = (value >> 8) & 0xFF
    size = (value >> 16) & 0x3FFF
    direction = (value >> 30) & 0x3
    direction_name = {
        0: "_IOC_NONE",
        1: "_IOC_WRITE",
        2: "_IOC_READ",
        3: "_IOC_READ|_IOC_WRITE",
    }.get(direction, "unknown")
    symbolic = ""
    if ioctl_type == 0xCC and nr == 2 and size == 4 and direction == 2:
        symbolic = "ESOC_WAIT_FOR_REQ"
    return {
        "value_hex": f"0x{value:08x}",
        "nr": nr,
        "type_hex": f"0x{ioctl_type:02x}",
        "type_ascii": chr(ioctl_type) if 32 <= ioctl_type <= 126 else "",
        "size": size,
        "direction": direction,
        "direction_name": direction_name,
        "symbolic": symbolic,
        "uapi_expr": "_IOR(ESOC_CODE, 2, unsigned int)" if symbolic else "",
    }


def lower_trace(manifest: dict[str, Any]) -> dict[str, str]:
    value = nested_get(manifest, ("analysis", "tracefs_uprobe", "post_pm_mdm_helper_lower_trace"), {})
    return {str(key): str(item) for key, item in value.items()} if isinstance(value, dict) else {}


def sample_ids(lower: dict[str, str]) -> list[str]:
    ids = set()
    for key in lower:
        match = re.match(r"sample_(\d+)\.", key)
        if match:
            ids.add(match.group(1))
    return sorted(ids)


def extract_thread_entries(lower: dict[str, str], sample_id: str) -> list[dict[str, Any]]:
    count = intish(lower.get(f"thread_probe.sample_{sample_id}.count"))
    entries: list[dict[str, Any]] = []
    for index in range(count):
        prefix = f"thread_probe.sample_{sample_id}.entry_{index:02d}."
        raw = lower.get(prefix + "syscall.raw", "")
        request_hex = ""
        decoded: dict[str, Any] = {}
        if lower.get(prefix + "name") == "ioctl":
            parts = raw.split()
            if len(parts) >= 3:
                match = IOCTL_REQUEST_RE.search(parts[2])
                if match:
                    request_hex = match.group(0).lower()
                    decoded = decode_ioctl(int(request_hex, 16))
        entries.append(
            {
                "index": index,
                "comm": lower.get(prefix + "comm", ""),
                "tid": lower.get(prefix + "tid", ""),
                "nr": lower.get(prefix + "nr", ""),
                "name": lower.get(prefix + "name", ""),
                "wchan": lower.get(prefix + "wchan", ""),
                "syscall_raw": raw,
                "request_hex": request_hex,
                "decoded_ioctl": decoded,
            }
        )
    return entries


def summarize_v1143(manifest: dict[str, Any]) -> dict[str, Any]:
    lower = lower_trace(manifest)
    samples: list[dict[str, Any]] = []
    for sample_id in sample_ids(lower):
        samples.append(
            {
                "sample": f"sample_{sample_id}",
                "alive": intish(lower.get(f"sample_{sample_id}.alive")),
                "fd_esoc0_count": intish(lower.get(f"sample_{sample_id}.fd_esoc0_count")),
                "fd_subsys_esoc0_count": intish(lower.get(f"sample_{sample_id}.fd_subsys_esoc0_count")),
                "fd_mhi_pipe_count": intish(lower.get(f"sample_{sample_id}.fd_mhi_pipe_count")),
                "ks_count": intish(lower.get(f"sample_{sample_id}.ks_count")),
                "fd3_target": lower.get(f"fd_match.sample_{sample_id}_mdm_helper_esoc0.entry_00.target", ""),
                "thread_entries": extract_thread_entries(lower, sample_id),
            }
        )
    global_fw = nested_get(manifest, ("analysis", "global_firmware"), {})
    qrtr_services = global_fw.get("qrtr_services_after_observer", {}) if isinstance(global_fw, dict) else {}
    markers = nested_get(global_fw, ("markers", "counts"), {}) if isinstance(global_fw, dict) else {}
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "post_pm_mdm_helper_lower_trace_emitted": bool(manifest.get("post_pm_mdm_helper_lower_trace_emitted")),
        "guardrails": {
            "wifi_hal_start_executed": bool(manifest.get("wifi_hal_start_executed")),
            "scan_connect_executed": bool(manifest.get("scan_connect_executed")),
            "credential_use_executed": bool(manifest.get("credential_use_executed")),
            "dhcp_route_executed": bool(manifest.get("dhcp_route_executed")),
            "external_ping_executed": bool(manifest.get("external_ping_executed")),
            "partition_write_executed": bool(manifest.get("partition_write_executed")),
            "flash_executed": bool(manifest.get("flash_executed")),
        },
        "mss_after_observer": global_fw.get("mss_after_observer", "") if isinstance(global_fw, dict) else "",
        "mdm3_after_observer": global_fw.get("mdm3_after_observer", "") if isinstance(global_fw, dict) else "",
        "qrtr_service69": intish(qrtr_services.get("69") if isinstance(qrtr_services, dict) else 0),
        "qrtr_service74": intish(qrtr_services.get("74") if isinstance(qrtr_services, dict) else 0),
        "qrtr_service180": intish(qrtr_services.get("180") if isinstance(qrtr_services, dict) else 0),
        "wlfw_count": intish(markers.get("wlfw") if isinstance(markers, dict) else 0),
        "bdf_count": intish(markers.get("bdf") if isinstance(markers, dict) else 0),
        "wlan0_count": intish(markers.get("wlan0") if isinstance(markers, dict) else 0),
        "samples": samples,
    }


def line_hits(path: Path, patterns: list[str]) -> list[dict[str, Any]]:
    text = read_text(path)
    hits: list[dict[str, Any]] = []
    if not text:
        return hits
    lines = text.splitlines()
    for index, line in enumerate(lines, start=1):
        for pattern in patterns:
            if pattern in line:
                hits.append(
                    {
                        "path": str(path),
                        "line": index,
                        "pattern": pattern,
                        "text": line.strip()[:220],
                    }
                )
    return hits


def source_contract() -> dict[str, Any]:
    return {
        "uapi": line_hits(
            UAPI_ESOC_CTRL,
            [
                "ESOC_WAIT_FOR_REQ",
                "ESOC_REG_REQ_ENG",
                "ESOC_NOTIFY",
                "ESOC_IMG_XFER_DONE",
                "ESOC_REQ_IMG",
            ],
        ),
        "esoc_dev": line_hits(
            ESOC_DEV,
            [
                "esoc_udev_handle_clink_req",
                "ESOC_REG_REQ_ENG",
                "ESOC_WAIT_FOR_REQ",
                "copy_to_user",
                "ESOC_NOTIFY",
            ],
        ),
        "esoc_bus": line_hits(ESOC_BUS, ["esoc_clink_queue_request", "handle_clink_req"]),
        "mdm_power": line_hits(ESOC_MDM_DRV, ["req_eng_wait", "wait_for_completion", "ESOC_PWR_ON", "power_on"]),
        "mdm_pon": line_hits(ESOC_MDM_PON, ["ESOC_REQ_IMG", "esoc_clink_queue_request"]),
        "mdm_notify": line_hits(ESOC_MDM_4X, ["ESOC_IMG_XFER_DONE", "mdm2ap_status_check_work", "ESOC_BOOT_DONE"]),
        "client_hooks": line_hits(ESOC_CLIENT, ["ESOC_MHI_HOOK", "struct esoc_client_hook", "register_esoc_client_notifier"]),
    }


def historical_references() -> dict[str, Any]:
    refs: dict[str, Any] = {}
    checks = {
        "v884": ["ESOC_WAIT_FOR_REQ", "rc=4", "value=1", "ESOC_REQ_IMG"],
        "v885": ["rc=4", "byte count", "ESOC_REQ_IMG"],
        "v891": ["ESOC_IMG_XFER_DONE", "ESOC_GET_STATUS", "stayed"],
        "v893": ["IMG_XFER_DONE", "not readiness"],
        "v896": ["/dev/mhi_0305_01.01.00_pipe_10", "`ks`", "/dev/subsys_esoc0"],
        "v911": ["0x8004cc02", "ESOC_WAIT_FOR_REQ", "esoc_dev_ioctl"],
        "v1020": ["sdx50m_toggle_soft_reset", "/dev/subsys_esoc0", "uninterruptible sleep"],
    }
    for name, path in HISTORICAL_REPORTS.items():
        text = read_text(path)
        refs[name] = {
            "path": str(path),
            "present": bool(text),
            "checks": {needle: (needle in text) for needle in checks.get(name, [])},
        }
    return refs


def classify(analysis: dict[str, Any]) -> dict[str, Any]:
    v1143 = analysis["v1143"]
    sources = analysis["sources"]
    history = analysis["historical"]
    guardrails_clean = not any(v1143["guardrails"].values())
    ioctl_decodes = []
    all_samples_stable = bool(v1143["samples"])
    for sample in v1143["samples"]:
        ioctl_entries = [
            entry for entry in sample["thread_entries"]
            if entry.get("name") == "ioctl" and entry.get("wchan") == "esoc_dev_ioctl"
        ]
        decoded_ok = any(
            (entry.get("decoded_ioctl") or {}).get("symbolic") == "ESOC_WAIT_FOR_REQ"
            for entry in ioctl_entries
        )
        ioctl_decodes.extend(entry.get("decoded_ioctl") or {} for entry in ioctl_entries)
        all_samples_stable = all_samples_stable and decoded_ok
        all_samples_stable = all_samples_stable and sample["alive"] == 1
        all_samples_stable = all_samples_stable and sample["fd_esoc0_count"] > 0
        all_samples_stable = all_samples_stable and sample["fd_subsys_esoc0_count"] == 0
        all_samples_stable = all_samples_stable and sample["fd_mhi_pipe_count"] == 0
        all_samples_stable = all_samples_stable and sample["ks_count"] == 0

    source_flags = {
        "uapi_wait_declared": any(hit["pattern"] == "ESOC_WAIT_FOR_REQ" for hit in sources["uapi"]),
        "uapi_req_img_declared": any(hit["pattern"] == "ESOC_REQ_IMG" for hit in sources["uapi"]),
        "esoc_dev_wait_implemented": any(hit["pattern"] == "ESOC_WAIT_FOR_REQ" for hit in sources["esoc_dev"]),
        "esoc_dev_copy_to_user": any(hit["pattern"] == "copy_to_user" for hit in sources["esoc_dev"]),
        "request_queue_path_present": bool(sources["esoc_bus"]) and bool(sources["mdm_pon"]),
        "img_xfer_notify_path_present": bool(sources["mdm_notify"]),
        "mhi_hook_contract_present": bool(sources["client_hooks"]),
    }
    history_flags = {
        key: value["present"] and all(value["checks"].values())
        for key, value in history.items()
    }
    flags = {
        "v1143_lower_trace_passed": (
            v1143["pass"]
            and v1143["decision"] == "v1143-post-pm-lower-trace-no-advance"
            and v1143["post_pm_mdm_helper_lower_trace_emitted"]
        ),
        "all_samples_stable_esoc_wait": all_samples_stable,
        "ioctl_decoded_as_esoc_wait_for_req": any(item.get("symbolic") == "ESOC_WAIT_FOR_REQ" for item in ioctl_decodes),
        "lower_artifacts_absent": (
            v1143["mdm3_after_observer"] == "OFFLINING"
            and v1143["qrtr_service69"] == 0
            and v1143["wlfw_count"] == 0
            and v1143["bdf_count"] == 0
            and v1143["wlan0_count"] == 0
        ),
        "guardrails_clean": guardrails_clean,
        **{f"source_{key}": value for key, value in source_flags.items()},
        **{f"history_{key}": value for key, value in history_flags.items()},
    }
    required = [
        "v1143_lower_trace_passed",
        "all_samples_stable_esoc_wait",
        "ioctl_decoded_as_esoc_wait_for_req",
        "lower_artifacts_absent",
        "guardrails_clean",
        "source_uapi_wait_declared",
        "source_uapi_req_img_declared",
        "source_esoc_dev_wait_implemented",
        "source_esoc_dev_copy_to_user",
        "source_request_queue_path_present",
        "source_img_xfer_notify_path_present",
        "history_v884",
        "history_v891",
        "history_v896",
        "history_v911",
        "history_v1020",
    ]
    missing = [name for name in required if not flags.get(name)]
    if not missing:
        return {
            "decision": "v1144-post-pm-esoc-wait-ioctl-contract-classified",
            "pass": True,
            "reason": (
                "V1143 mdm_helper worker is stably blocked in ESOC_WAIT_FOR_REQ on /dev/esoc-0; "
                "this is a request-engine wait path, not a direct mdm3 power-on or MHI/ks progression"
            ),
            "next_step": (
                "V1145 should be host-only first: compare Android mdm_helper/ks/MHI image-link contract "
                "against native, then design a fail-closed contract verifier before any new live eSoC retry"
            ),
            "flags": flags,
            "missing": [],
        }
    return {
        "decision": "v1144-esoc-wait-ioctl-contract-input-incomplete",
        "pass": False,
        "reason": "missing=" + ",".join(missing),
        "next_step": "refresh V1143 lower-trace/source/history evidence before selecting a new live gate",
        "flags": flags,
        "missing": missing,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    v1143 = manifest["analysis"]["v1143"]
    classification = manifest["analysis"]["classification"]
    sample_rows = []
    for sample in v1143["samples"]:
        ioctl = ""
        wchan = ""
        for entry in sample["thread_entries"]:
            if entry.get("name") == "ioctl":
                ioctl = (entry.get("decoded_ioctl") or {}).get("symbolic", "") or entry.get("request_hex", "")
                wchan = entry.get("wchan", "")
        sample_rows.append(
            [
                sample["sample"],
                str(sample["fd_esoc0_count"]),
                str(sample["fd_subsys_esoc0_count"]),
                str(sample["fd_mhi_pipe_count"]),
                str(sample["ks_count"]),
                wchan,
                ioctl,
            ]
        )
    source_rows = []
    for name, hits in manifest["analysis"]["sources"].items():
        first = hits[0] if hits else {}
        detail = f"{first.get('path', '')}:{first.get('line', '')}" if first else "missing"
        source_rows.append([name, str(len(hits)), detail])
    flag_rows = [[name, str(value)] for name, value in classification["flags"].items()]
    return "\n".join(
        [
            "# V1144 eSoC Wait Ioctl Contract Classifier",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next_step: {manifest['next_step']}",
            "",
            "## V1143 Samples",
            "",
            markdown_table(["sample", "esoc0 fd", "subsys fd", "mhi fd", "ks", "wchan", "ioctl"], sample_rows),
            "",
            "## Source Contract",
            "",
            markdown_table(["source", "hits", "first hit"], source_rows),
            "",
            "## Classification Flags",
            "",
            markdown_table(["flag", "value"], flag_rows),
            "",
            "## Safety",
            "",
            "- device commands executed: `false`",
            "- live eSoC/subsys/ioctl retry: `false`",
            "- Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping: `false`",
            "- boot image/partition writes/flash: `false`",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    analysis = {
        "v1143": summarize_v1143(load_json(args.v1143)),
        "sources": source_contract(),
        "historical": historical_references(),
    }
    classification = classify(analysis)
    analysis["classification"] = classification
    manifest = {
        "cycle": "v1144",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v1143": str(repo_path(args.v1143)),
            "sources": {
                "uapi_esoc_ctrl": str(repo_path(UAPI_ESOC_CTRL)),
                "esoc_client": str(repo_path(ESOC_CLIENT)),
                "esoc_source_root": str(repo_path(ESOC_SOURCE_ROOT)),
            },
            "historical_reports": {key: str(repo_path(path)) for key, path in HISTORICAL_REPORTS.items()},
        },
        "analysis": analysis,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "device_commands_executed": False,
        "device_mutations": False,
        "live_esoc_ioctl_executed": False,
        "tracefs_write_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
