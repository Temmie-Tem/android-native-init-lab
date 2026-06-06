#!/usr/bin/env python3
"""V1133 host-only classifier for the lower modem holder route after V1132."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1133-lower-holder-route-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1133-lower-holder-route-classifier.txt")
DEFAULT_V731 = Path("tmp/wifi/v731-firmware-mounted-modem-holder/manifest.json")
DEFAULT_V1113 = Path("tmp/wifi/v1113-global-firmware-pm-connect-live/manifest.json")
DEFAULT_V1128 = Path("tmp/wifi/v1128-post-policy-private-firmware-cnss-pm-classifier/manifest.json")
DEFAULT_V1131 = Path("tmp/wifi/v1131-post-policy-global-firmware-modem-holder-classifier/manifest.json")
DEFAULT_V1131_LIVE = Path("tmp/wifi/v1131-post-policy-global-firmware-modem-holder-cnss-pm-live/manifest.json")
DEFAULT_V1132 = Path("tmp/wifi/v1132-subsys-nonblock-semantics-classifier/manifest.json")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path, limit: int = 16_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def nested_get(data: dict[str, Any], path: tuple[str, ...], default: Any = None) -> Any:
    cur: Any = data
    for item in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(item)
    return default if cur is None else cur


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "ok", "pass", "online"}


def listify(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def count_dmesg_failure_lines(data: dict[str, Any]) -> dict[str, Any]:
    lines: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str):
            if "modem.mdt" in value or "Failed to locate modem" in value or "_request_firmware_load" in value:
                for line in value.splitlines():
                    if (
                        "modem.mdt" in line
                        or "Failed to locate modem" in line
                        or "_request_firmware_load" in line
                    ):
                        clean = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line).strip()
                        if clean:
                            lines.append(clean)

    walk(data)
    return {
        "count": len(lines),
        "sample": lines[:8],
        "failed_locate_modem_mdt": any("Failed to locate modem.mdt" in line for line in lines),
        "firmware_wait_timeout": any("_request_firmware_load" in line for line in lines),
    }


def summarize_v731(data: dict[str, Any]) -> dict[str, Any]:
    fw = nested_get(data, ("analysis", "global_firmware"), {})
    if not fw:
        fw = data.get("live") if isinstance(data.get("live"), dict) else {}
    marker_counts = nested_get(data, ("analysis", "markers", "counts"), {})
    if not marker_counts:
        marker_counts = nested_get(data, ("analysis", "global_firmware", "markers", "counts"), {})
    text = json.dumps(data)
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "holder_opened": "holder_opened=true" in text or boolish(nested_get(data, ("analysis", "holder_opened"), False)),
        "mss_online": "mss:  OFFLINING -> ONLINE" in text
        or "mss_after_holder\": \"ONLINE" in text
        or "mss_after_observer\": \"ONLINE" in text,
        "mdm3_after": nested_get(data, ("analysis", "global_firmware", "mdm3_after_observer"), ""),
        "qrtr_rx_seen": "Modem QMI Readiness RX" in text
        or int(marker_counts.get("qrtr_rx", 0) or 0) > 0,
        "wlan0_seen": "wlan0" in text and "wlan0_absent" not in text,
    }


def summarize_v1113(data: dict[str, Any]) -> dict[str, Any]:
    fw = nested_get(data, ("analysis", "global_firmware"), {})
    markers = fw.get("markers") if isinstance(fw, dict) else {}
    counts = markers.get("counts") if isinstance(markers, dict) else {}
    tracefs = nested_get(data, ("analysis", "tracefs_uprobe"), {})
    by_comm = tracefs.get("return_values_by_comm") if isinstance(tracefs, dict) else {}
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "holder_opened": boolish(fw.get("holder_opened")) if isinstance(fw, dict) else False,
        "mss_after_holder": fw.get("mss_after_holder", "") if isinstance(fw, dict) else "",
        "mss_after_observer": fw.get("mss_after_observer", "") if isinstance(fw, dict) else "",
        "mdm3_after_observer": fw.get("mdm3_after_observer", "") if isinstance(fw, dict) else "",
        "qrtr_rx": int(counts.get("qrtr_rx", 0) or 0) if isinstance(counts, dict) else 0,
        "qrtr_tx": int(counts.get("qrtr_tx", 0) or 0) if isinstance(counts, dict) else 0,
        "sysmon_qmi": int(counts.get("sysmon_qmi", 0) or 0) if isinstance(counts, dict) else 0,
        "cnss_register_ret": listify(nested_get(by_comm, ("cnss-daemon", "pm_client_register_ret"), [])),
        "cnss_connect_ret": listify(nested_get(by_comm, ("cnss-daemon", "pm_client_connect_ret"), [])),
    }


def summarize_v1128(data: dict[str, Any]) -> dict[str, Any]:
    flags = nested_get(data, ("analysis", "flags"), {})
    live = nested_get(data, ("analysis", "comparison", "live"), {})
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "policy_load_ready": boolish(flags.get("policy_load_ready")),
        "provider_seen": boolish(flags.get("provider_seen")),
        "cnss_pm_register_ok": boolish(flags.get("cnss_pm_register_ok")),
        "cnss_pm_connect_ok": boolish(flags.get("cnss_pm_connect_ok")),
        "pm_server_register_ok": boolish(flags.get("pm_server_register_ok")),
        "pm_server_connect_ok": boolish(flags.get("pm_server_connect_ok")),
        "subsys_modem_pending": boolish(live.get("subsys_modem_pending")),
        "mdm3_state": live.get("mdm3_state", ""),
        "wlan0_exists": live.get("wlan0_exists", ""),
    }


def summarize_v1131(classifier: dict[str, Any], live: dict[str, Any]) -> dict[str, Any]:
    summary = nested_get(classifier, ("analysis", "summary"), {})
    flags = nested_get(classifier, ("analysis", "flags"), {})
    fw = nested_get(live, ("analysis", "firmware_mount_only"), {})
    blobs = fw.get("modem_blob_visible") if isinstance(fw, dict) else {}
    return {
        "decision": classifier.get("decision", ""),
        "pass": bool(classifier.get("pass")),
        "policy_load_ready": boolish(flags.get("policy_load_ready")),
        "provider_cnss_pm_ok": boolish(flags.get("provider_and_cnss_pm_ok")),
        "holder_attempted_but_open_pending": boolish(flags.get("holder_attempted_but_open_pending")),
        "subsys_modem_blocker_reproduced": boolish(flags.get("subsys_modem_blocker_reproduced")),
        "holder_confirmed": boolish(summary.get("holder_confirmed")),
        "mss_after": summary.get("mss_after", ""),
        "mdm3_after": summary.get("mdm3_after", ""),
        "firmware_class_path": fw.get("firmware_class_path", "") if isinstance(fw, dict) else "",
        "mounted_hits": fw.get("mounted_hits", {}) if isinstance(fw, dict) else {},
        "modem_blob_visible": blobs if isinstance(blobs, dict) else {},
        "dmesg_modem_firmware_failures": count_dmesg_failure_lines(live),
    }


def summarize_v1132(data: dict[str, Any]) -> dict[str, Any]:
    classification = nested_get(data, ("analysis", "classification"), {})
    return {
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "open_no_nonblock_branch": boolish(nested_get(classification, ("source_flags", "open_no_nonblock_branch"), False)),
        "start_sync_powerup": boolish(nested_get(classification, ("source_flags", "start_sync_powerup"), False)),
        "holder_attempted_no_result": boolish(nested_get(classification, ("evidence_flags", "holder_attempted_no_result"), False)),
        "provider_cnss_ok": boolish(nested_get(classification, ("evidence_flags", "provider_cnss_ok"), False)),
    }


def helper_source_summary(text: str) -> dict[str, Any]:
    return {
        "source_present": bool(text),
        "helper_marker_v213": "a90_android_execns_probe v213" in text,
        "has_private_firmware_flag": "pm_observer_private_firmware_mounts" in text,
        "has_modem_pre_holder_flag": "pm_observer_modem_pre_holder" in text,
        "mounts_apnhlos_to_firmware_mnt": 'mount_one_wifi_firmware_partition("apnhlos"' in text
        and "paths->vendor_firmware_mnt" in text,
        "mounts_modem_to_firmware_modem": 'mount_one_wifi_firmware_partition("modem"' in text
        and "paths->vendor_firmware_modem" in text,
        "has_outer_global_holder_model": "global_firmware" in text and "qrtr_rx_wait" in text,
    }


def classify(v731: dict[str, Any],
             v1113: dict[str, Any],
             v1128: dict[str, Any],
             v1131: dict[str, Any],
             v1132: dict[str, Any],
             helper: dict[str, Any]) -> dict[str, Any]:
    flags = {
        "old_outer_holder_positive": v731["pass"] and v731["mss_online"] and v731["qrtr_rx_seen"],
        "recent_outer_holder_positive": v1113["pass"]
        and v1113["holder_opened"]
        and v1113["mss_after_holder"] == "ONLINE"
        and v1113["qrtr_rx"] > 0,
        "post_policy_cnss_pm_positive": v1128["pass"]
        and v1128["policy_load_ready"]
        and v1128["provider_seen"]
        and v1128["cnss_pm_register_ok"]
        and v1128["cnss_pm_connect_ok"]
        and v1128["pm_server_register_ok"]
        and v1128["pm_server_connect_ok"],
        "private_preholder_closed": v1131["pass"]
        and v1131["provider_cnss_pm_ok"]
        and v1131["holder_attempted_but_open_pending"]
        and v1131["subsys_modem_blocker_reproduced"]
        and not v1131["holder_confirmed"],
        "nonblock_route_closed": v1132["pass"]
        and v1132["open_no_nonblock_branch"]
        and v1132["start_sync_powerup"]
        and v1132["holder_attempted_no_result"],
        "current_helper_has_pm_observer_surface": helper["source_present"]
        and helper["helper_marker_v213"]
        and helper["has_private_firmware_flag"]
        and helper["has_modem_pre_holder_flag"],
    }
    missing = [name for name, ok in flags.items() if not ok]
    if not missing:
        return {
            "decision": "v1133-outer-global-holder-post-policy-cnss-composite-selected",
            "pass": True,
            "reason": (
                "V731/V1113 prove the outer global firmware+subsys_modem holder advances mss/QRTR; "
                "V1128 proves current post-policy CNSS PM register/connect; "
                "V1131/V1132 close helper-private/nonblocking pre-holder retries"
            ),
            "next_step": (
                "V1134 should combine the outer global holder window with the V1128/V1131 post-policy "
                "provider-positive CNSS PM observer, using helper v213 and no helper-private modem pre-holder"
            ),
            "flags": flags,
            "missing": [],
        }
    return {
        "decision": "v1133-lower-holder-route-incomplete",
        "pass": False,
        "reason": "missing=" + ",".join(missing),
        "next_step": "inspect the missing evidence before creating another live runner",
        "flags": flags,
        "missing": missing,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    route = analysis["classification"]
    rows = [
        ["V731 outer holder", str(route["flags"]["old_outer_holder_positive"]), analysis["v731"]["decision"]],
        ["V1113 outer holder", str(route["flags"]["recent_outer_holder_positive"]), analysis["v1113"]["decision"]],
        ["V1128 CNSS PM", str(route["flags"]["post_policy_cnss_pm_positive"]), analysis["v1128"]["decision"]],
        ["V1131 private pre-holder", str(route["flags"]["private_preholder_closed"]), analysis["v1131"]["decision"]],
        ["V1132 nonblock route", str(route["flags"]["nonblock_route_closed"]), analysis["v1132"]["decision"]],
        ["helper v213 surface", str(route["flags"]["current_helper_has_pm_observer_surface"]), "source"],
    ]
    state_rows = [
        ["V1113 mss_after_holder", analysis["v1113"]["mss_after_holder"]],
        ["V1113 qrtr_rx", str(analysis["v1113"]["qrtr_rx"])],
        ["V1128 mdm3_state", analysis["v1128"]["mdm3_state"]],
        ["V1131 mss_after", analysis["v1131"]["mss_after"]],
        ["V1131 mdm3_after", analysis["v1131"]["mdm3_after"]],
        ["V1131 firmware_failures", str(analysis["v1131"]["dmesg_modem_firmware_failures"]["count"])],
    ]
    return "\n".join([
        "# V1133 Lower Holder Route Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Route Evidence",
        "",
        markdown_table(["evidence", "ok", "decision"], rows),
        "",
        "## State Evidence",
        "",
        markdown_table(["key", "value"], state_rows),
        "",
        "## Missing",
        "",
        json.dumps(route["missing"], indent=2, sort_keys=True),
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v731", type=Path, default=DEFAULT_V731)
    parser.add_argument("--v1113", type=Path, default=DEFAULT_V1113)
    parser.add_argument("--v1128", type=Path, default=DEFAULT_V1128)
    parser.add_argument("--v1131", type=Path, default=DEFAULT_V1131)
    parser.add_argument("--v1131-live", type=Path, default=DEFAULT_V1131_LIVE)
    parser.add_argument("--v1132", type=Path, default=DEFAULT_V1132)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v731 = summarize_v731(load_json(args.v731))
    v1113 = summarize_v1113(load_json(args.v1113))
    v1128 = summarize_v1128(load_json(args.v1128))
    v1131 = summarize_v1131(load_json(args.v1131), load_json(args.v1131_live))
    v1132 = summarize_v1132(load_json(args.v1132))
    helper = helper_source_summary(read_text(args.helper_source))
    classification = classify(v731, v1113, v1128, v1131, v1132, helper)
    manifest = {
        "cycle": "v1133",
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "inputs": {
            "v731": str(repo_path(args.v731)),
            "v1113": str(repo_path(args.v1113)),
            "v1128": str(repo_path(args.v1128)),
            "v1131": str(repo_path(args.v1131)),
            "v1131_live": str(repo_path(args.v1131_live)),
            "v1132": str(repo_path(args.v1132)),
            "helper_source": str(repo_path(args.helper_source)),
        },
        "analysis": {
            "v731": v731,
            "v1113": v1113,
            "v1128": v1128,
            "v1131": v1131,
            "v1132": v1132,
            "helper": helper,
            "classification": classification,
        },
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "device_commands_executed": False,
        "device_mutations": False,
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
