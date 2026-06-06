#!/usr/bin/env python3
"""V818 host-only mdm3/esoc0 registration gap classifier.

V817 proved that the bounded lower window advances mss/QRTR/sysmon but leaves
mdm3 and WLAN service publication absent.  This classifier reconciles that
result with prior PIL/source evidence and selects the next safe live gate
without contacting the device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v818-mdm3-esoc-registration-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v818-mdm3-esoc-registration-classifier.txt")
DEFAULT_V817_MANIFEST = Path("tmp/wifi/v817-in-window-sysmon-sampler/manifest.json")
DEFAULT_V798_MANIFEST = Path("tmp/wifi/v798-pil-code-gap-classifier/manifest.json")
DEFAULT_V795_MANIFEST = Path("tmp/wifi/v795-lower-window-mdm3-esoc-observer/manifest.json")
DEFAULT_V817_ESOC = Path("tmp/wifi/v817-in-window-sysmon-sampler/native/after-companion-esoc.txt")
DEFAULT_V817_SUBSYS = Path("tmp/wifi/v817-in-window-sysmon-sampler/native/after-companion-subsys.txt")
DEFAULT_V817_QRTR = Path("tmp/wifi/v817-in-window-sysmon-sampler/native/proc-net-qrtr-after-companion.txt")
DEFAULT_SOURCE_SNIPPETS = {
    "sysmon_qmi_notif_map": Path("tmp/wifi/v798-pil-code-gap-classifier/source/sysmon_qmi_notif_map.txt"),
    "service_notifier_new_server": Path("tmp/wifi/v798-pil-code-gap-classifier/source/service_notifier_new_server.txt"),
    "icnss_service_notifier_registration": Path("tmp/wifi/v798-pil-code-gap-classifier/source/icnss_service_notifier_registration.txt"),
    "subsystem_restart_start_order": Path("tmp/wifi/v798-pil-code-gap-classifier/source/subsystem_restart_start_order.txt"),
}

FORBIDDEN_ACTIONS = (
    "device command",
    "custom kernel flash, boot image write, or partition write",
    "reboot or bootloader handoff",
    "service-manager, Wi-Fi HAL, wificond, supplicant, scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "qcwlanstate on/off, esoc0 open, bind/unbind, driver override, or module load/unload",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v817-manifest", type=Path, default=DEFAULT_V817_MANIFEST)
    parser.add_argument("--v798-manifest", type=Path, default=DEFAULT_V798_MANIFEST)
    parser.add_argument("--v795-manifest", type=Path, default=DEFAULT_V795_MANIFEST)
    parser.add_argument("--v817-esoc", type=Path, default=DEFAULT_V817_ESOC)
    parser.add_argument("--v817-subsys", type=Path, default=DEFAULT_V817_SUBSYS)
    parser.add_argument("--v817-qrtr", type=Path, default=DEFAULT_V817_QRTR)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def safe_read(path: Path, limit: int = 1024 * 1024) -> tuple[str, dict[str, Any]]:
    resolved = resolve(path)
    info: dict[str, Any] = {"path": str(resolved), "exists": resolved.exists()}
    if not resolved.exists() or not resolved.is_file():
        return "", info
    data = resolved.read_bytes()[:limit]
    size = resolved.stat().st_size
    info.update({"is_file": True, "size": size, "bytes_read": len(data), "truncated": size > len(data)})
    return data.decode("utf-8", errors="replace"), info


def load_json(path: Path) -> dict[str, Any]:
    text, info = safe_read(path, limit=16 * 1024 * 1024)
    if not text:
        return {"file": info, "data": {}}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"file": info, "data": {}, "error": str(exc)}
    return {"file": info, "data": payload if isinstance(payload, dict) else {}}


def nested(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def manifest_summary(label: str, path: Path) -> dict[str, Any]:
    loaded = load_json(path)
    data = loaded["data"]
    return {
        "label": label,
        "file": loaded["file"],
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
        "next_step": data.get("next_step", ""),
        "data": data,
    }


def contains(text: str, *needles: str) -> bool:
    return all(needle in text for needle in needles)


def source_snippet_summary(store: EvidenceStore) -> dict[str, dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    for name, source in DEFAULT_SOURCE_SNIPPETS.items():
        text, info = safe_read(source)
        rel = f"source/{name}.txt"
        if text:
            store.write_text(rel, text)
        summaries[name] = {
            "file": info,
            "copied_to": rel if text else "",
            "has_sysmon": "sysmon" in text.lower(),
            "has_service_notifier": "service_notifier" in text or "service-notifier" in text,
            "has_icnss": "icnss" in text.lower(),
            "has_subsys_notif": "subsys" in text.lower() or "SUBSYS" in text,
        }
    return summaries


def evidence_texts(args: argparse.Namespace, store: EvidenceStore) -> dict[str, dict[str, Any]]:
    files = {
        "v817_esoc_after_companion": args.v817_esoc,
        "v817_subsys_after_companion": args.v817_subsys,
        "v817_qrtr_after_companion": args.v817_qrtr,
    }
    out: dict[str, dict[str, Any]] = {}
    for name, path in files.items():
        text, info = safe_read(path, limit=2 * 1024 * 1024)
        rel = f"evidence/{name}.txt"
        if text:
            store.write_text(rel, text)
        out[name] = {
            "file": info,
            "copied_to": rel if text else "",
            "text": text,
        }
    return out


def build_analysis(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    inputs = {
        "v817": manifest_summary("v817", args.v817_manifest),
        "v798": manifest_summary("v798", args.v798_manifest),
        "v795": manifest_summary("v795", args.v795_manifest),
    }
    texts = evidence_texts(args, store)
    snippets = source_snippet_summary(store)

    v817 = inputs["v817"]["data"]
    v817_live = as_dict(v817.get("live"))
    snapshots = as_dict(v817_live.get("snapshots"))
    after_holder = as_dict(snapshots.get("after-holder"))
    after_companion = as_dict(snapshots.get("after-companion"))
    after_companion_runtime = as_dict(after_companion.get("runtime_counts"))
    after_holder_runtime = as_dict(after_holder.get("runtime_counts"))
    helper = as_dict(v817_live.get("helper_result"))
    qrtr_readback = as_dict(v817_live.get("qrtr_readback"))
    v795_live = as_dict(inputs["v795"]["data"].get("live"))
    v798_analysis = as_dict(inputs["v798"]["data"].get("analysis"))
    v798_derived = as_dict(v798_analysis.get("derived"))
    v798_gap = as_dict(v798_analysis.get("gap"))

    esoc_text = texts["v817_esoc_after_companion"]["text"]
    subsys_text = texts["v817_subsys_after_companion"]["text"]
    qrtr_text = texts["v817_qrtr_after_companion"]["text"]

    esoc_surface = {
        "bus_esoc0_visible": contains(esoc_text, "/sys/bus/esoc/devices/esoc0", "qcom,mdm3"),
        "class_subsys_esoc0_visible": "subsys_esoc0" in esoc_text,
        "subsys_esoc0_devname": "DEVNAME=subsys_esoc0" in esoc_text,
        "dev_subsys_absent": "/dev/subsys*" in esoc_text and "No such file or directory" in esoc_text,
        "dev_esoc_absent": "/dev/esoc*" in esoc_text and "No such file or directory" in esoc_text,
    }

    subsys_surface = {
        "subsys_count_marker": "subsys9" in subsys_text and "subsys0" in subsys_text,
        "mss_online": contains(subsys_text, "name=modem", "state=ONLINE"),
        "mdm3_esoc0_offlining": contains(subsys_text, "name=esoc0", "state=OFFLINING"),
        "mdm3_firmware_name": "firmware_name=esoc0" in subsys_text,
    }

    qrtr_surface = {
        "global_proc_net_qrtr_missing": "cat: /proc/net/qrtr: No such file or directory" in qrtr_text,
        "helper_qipcrtr_window": int_value(helper.get("qipcrtr_window")),
        "helper_service_events": int_value(helper.get("service_events")),
        "readback_service69_events": int_value(qrtr_readback.get("service_events")),
        "readback_timeouts": int_value(qrtr_readback.get("timeouts")),
    }

    lower_progression = {
        "v795": {
            "decision": inputs["v795"]["decision"],
            "mss": [v795_live.get("mss_before"), v795_live.get("mss_after_holder")],
            "mdm3": [v795_live.get("mdm3_before"), v795_live.get("mdm3_after_holder")],
            "qrtr_services": v795_live.get("qrtr_services_after_holder"),
        },
        "v817": {
            "decision": inputs["v817"]["decision"],
            "mss": [v817_live.get("mss_before"), v817_live.get("mss_after_holder"), v817_live.get("mss_after_companion")],
            "mdm3": [v817_live.get("mdm3_before"), v817_live.get("mdm3_after_holder"), v817_live.get("mdm3_after_companion")],
            "after_holder_runtime": after_holder_runtime,
            "after_companion_runtime": after_companion_runtime,
            "qrtr_services_after_companion": v817_live.get("qrtr_services_after_companion"),
        },
        "v798": {
            "decision": inputs["v798"]["decision"],
            "derived": v798_derived,
            "gap": {
                "native_mss": v798_gap.get("native_v797_mss"),
                "native_mdm3": v798_gap.get("native_v797_mdm3"),
                "native_service_notifier": v798_gap.get("native_v797_service_notifier"),
                "native_service69": v798_gap.get("native_v797_service69"),
                "android_mdm3_state": v798_gap.get("android_mdm3_state"),
                "android_service_notifier_180": v798_gap.get("android_service_notifier_180"),
                "android_service_notifier_74": v798_gap.get("android_service_notifier_74"),
                "android_wlan_pd": v798_gap.get("android_wlan_pd"),
                "android_wlan0": v798_gap.get("android_wlan0"),
            },
        },
    }

    return {
        "inputs": inputs,
        "texts": {key: {k: v for k, v in value.items() if k != "text"} for key, value in texts.items()},
        "source_snippets": snippets,
        "esoc_surface": esoc_surface,
        "subsys_surface": subsys_surface,
        "qrtr_surface": qrtr_surface,
        "lower_progression": lower_progression,
    }


def build_checks(command: str, analysis: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only classifier plan; no device command executed",
            "next_step": "run V818 host-only classifier",
        }]

    inputs = analysis["inputs"]
    v817 = analysis["lower_progression"]["v817"]
    v798 = analysis["lower_progression"]["v798"]
    v795 = analysis["lower_progression"]["v795"]
    after_companion_runtime = v817["after_companion_runtime"]
    after_holder_runtime = v817["after_holder_runtime"]
    source_snippets = analysis["source_snippets"]
    source_ready = all(item["file"]["exists"] for item in source_snippets.values())

    all_inputs_ready = all(inputs[name]["pass"] for name in ("v817", "v798", "v795"))
    v817_gap_confirmed = (
        inputs["v817"]["decision"] == "v817-in-window-mdm3-service-gap-confirmed"
        and v817["mss"] == ["OFFLINING", "ONLINE", "ONLINE"]
        and v817["mdm3"] == ["OFFLINING", "OFFLINING", "OFFLINING"]
        and int_value(after_companion_runtime.get("sysmon_qmi")) > 0
        and int_value(after_companion_runtime.get("service_notifier_74")) == 0
        and int_value(after_companion_runtime.get("wlfw")) == 0
        and int_value(after_companion_runtime.get("wlan0")) == 0
    )
    companion_delta_bounded = (
        int_value(after_holder_runtime.get("sysmon_qmi")) == 0
        and int_value(after_companion_runtime.get("sysmon_qmi")) > 0
        and int_value(after_companion_runtime.get("service_notifier")) == 0
        and int_value(after_companion_runtime.get("service_notifier_74")) == 0
    )
    pil_not_blocker = (
        inputs["v798"]["decision"] == "v798-modem-pil-complete-service-notifier-mdm3-gap-classified"
        and bool(v798["derived"].get("modem_pil_sequence_complete"))
        and bool(v798["derived"].get("service_notifier_gap_after_modem_powerup"))
    )
    holder_not_enough = (
        inputs["v795"]["decision"] == "v795-holder-modem-online-mdm3-offlining-classified"
        and v795["mss"] == ["OFFLINING", "ONLINE"]
        and v795["mdm3"] == ["OFFLINING", "OFFLINING"]
    )
    esoc_surface_ready = (
        analysis["esoc_surface"]["bus_esoc0_visible"]
        and analysis["esoc_surface"]["class_subsys_esoc0_visible"]
        and analysis["esoc_surface"]["dev_subsys_absent"]
        and analysis["esoc_surface"]["dev_esoc_absent"]
    )
    subsys_surface_consistent = (
        analysis["subsys_surface"]["mss_online"]
        and analysis["subsys_surface"]["mdm3_esoc0_offlining"]
        and analysis["subsys_surface"]["mdm3_firmware_name"]
    )
    qrtr_surface_consistent = (
        analysis["qrtr_surface"]["helper_qipcrtr_window"] == 1
        and analysis["qrtr_surface"]["helper_service_events"] == 0
        and analysis["qrtr_surface"]["readback_service69_events"] == 0
        and analysis["qrtr_surface"]["readback_timeouts"] == 0
    )

    return [
        {
            "name": "required-inputs",
            "status": "pass" if all_inputs_ready else "blocked",
            "detail": {name: {"decision": inputs[name]["decision"], "pass": inputs[name]["pass"]} for name in inputs},
            "next_step": "restore missing prior evidence before selecting V819",
        },
        {
            "name": "host-only-boundary",
            "status": "pass",
            "detail": "no device command, reboot, flash, service-manager/HAL, scan/connect, credential use, route, or ping",
            "next_step": "preserve V818 as a classifier only",
        },
        {
            "name": "source-anchor-present",
            "status": "pass" if source_ready else "blocked",
            "detail": source_snippets,
            "next_step": "refresh V798 source snippets if service-locator/sysmon anchors are missing",
        },
        {
            "name": "v817-in-window-gap",
            "status": "pass" if v817_gap_confirmed else "blocked",
            "detail": v817,
            "next_step": "rerun V817 only if mss/sysmon/mdm3/service markers changed",
        },
        {
            "name": "companion-delta-bounded",
            "status": "pass" if companion_delta_bounded else "blocked",
            "detail": {
                "after_holder_runtime": after_holder_runtime,
                "after_companion_runtime": after_companion_runtime,
            },
            "next_step": "do not widen to HAL/connect; isolate what companion still fails to publish",
        },
        {
            "name": "pil-not-current-blocker",
            "status": "pass" if pil_not_blocker else "blocked",
            "detail": v798,
            "next_step": "do not retry custom-kernel instrumentation or blind PIL trigger",
        },
        {
            "name": "holder-alone-not-enough",
            "status": "pass" if holder_not_enough else "blocked",
            "detail": v795,
            "next_step": "do not rerun holder-only as the next gate",
        },
        {
            "name": "esoc-sysfs-no-devnode-gap",
            "status": "pass" if esoc_surface_ready and subsys_surface_consistent else "blocked",
            "detail": {
                "esoc_surface": analysis["esoc_surface"],
                "subsys_surface": analysis["subsys_surface"],
            },
            "next_step": "V819 should read registration surfaces only; do not open esoc0",
        },
        {
            "name": "qrtr-service-publication-empty",
            "status": "pass" if qrtr_surface_consistent else "blocked",
            "detail": analysis["qrtr_surface"],
            "next_step": "V819 should catalogue per-process QRTR/service-locator state before any active query",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v818-mdm3-esoc-registration-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v818-mdm3-esoc-registration-classifier-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "restore or refresh required evidence before selecting a live gate",
        )
    return (
        "v818-mdm3-esoc-registration-gap-classified",
        True,
        "V817 confirms mss/sysmon advance without mdm3/service publication; V798 removes modem PIL absence; V795 removes holder-only retry; esoc sysfs exists but device nodes are absent",
        "V819 should run a bounded read-only mdm3/esoc0 service-locator/sysmon registration catalogue below service-manager/HAL/connect",
    )


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = build_analysis(args, store)
    checks = build_checks(args.command, analysis)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v818",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "analysis": {
            "esoc_surface": analysis["esoc_surface"],
            "subsys_surface": analysis["subsys_surface"],
            "qrtr_surface": analysis["qrtr_surface"],
            "lower_progression": analysis["lower_progression"],
            "texts": analysis["texts"],
            "source_snippets": analysis["source_snippets"],
        },
        "inputs": {
            name: {
                "path": value["file"]["path"],
                "exists": value["file"]["exists"],
                "decision": value["decision"],
                "pass": value["pass"],
            }
            for name, value in analysis["inputs"].items()
        },
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "reboot_executed": False,
        "esoc0_open_executed": False,
        "module_load_unload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    input_rows = [
        [name, str(item["exists"]), str(item["pass"]), item["decision"], item["path"]]
        for name, item in manifest["inputs"].items()
    ]
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    signal_rows = [
        ["esoc_surface", json.dumps(manifest["analysis"]["esoc_surface"], ensure_ascii=False, sort_keys=True)],
        ["subsys_surface", json.dumps(manifest["analysis"]["subsys_surface"], ensure_ascii=False, sort_keys=True)],
        ["qrtr_surface", json.dumps(manifest["analysis"]["qrtr_surface"], ensure_ascii=False, sort_keys=True)],
        ["v817", json.dumps(manifest["analysis"]["lower_progression"]["v817"], ensure_ascii=False, sort_keys=True)],
        ["v798", json.dumps(manifest["analysis"]["lower_progression"]["v798"], ensure_ascii=False, sort_keys=True)],
        ["v795", json.dumps(manifest["analysis"]["lower_progression"]["v795"], ensure_ascii=False, sort_keys=True)],
    ]
    return "\n".join([
        "# V818 mdm3/esoc0 Registration Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "exists", "pass", "decision", "path"], input_rows),
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Signals",
        "",
        markdown_table(["signal", "value"], signal_rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"esoc0_open_executed: {manifest['esoc0_open_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
