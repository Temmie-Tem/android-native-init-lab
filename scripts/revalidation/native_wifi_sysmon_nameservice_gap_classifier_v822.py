#!/usr/bin/env python3
"""V822 host-only sysmon-vs-nameservice gap classifier.

V821 proved that AF_QIPCRTR lookup/delete works for the service-locator,
service-notifier, and WLFW candidate matrix, but all cases returned only
end-of-list.  This classifier compares that evidence with Samsung OSRC source
constants and the board DTS SSCTL instance to decide the next safe matrix
without touching the device.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v822-sysmon-nameservice-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v822-sysmon-nameservice-gap-classifier.txt")
DEFAULT_V821_MANIFEST = Path("tmp/wifi/v821-qrtr-nameservice-matrix/manifest.json")
OSRC_ROOT = workspace_private_input_path("kernel_source", 'SM-A908N_KOR_12_Opensource', 'Kernel')
DEFAULT_SOURCE_PATHS = {
    "service_locator_private": OSRC_ROOT / "drivers/soc/qcom/service-locator-private.h",
    "service_locator": OSRC_ROOT / "drivers/soc/qcom/service-locator.c",
    "service_notifier_private": OSRC_ROOT / "drivers/soc/qcom/service-notifier-private.h",
    "service_notifier": OSRC_ROOT / "drivers/soc/qcom/service-notifier.c",
    "sysmon_qmi": OSRC_ROOT / "drivers/soc/qcom/sysmon-qmi.c",
    "wlfw": OSRC_ROOT / "drivers/soc/qcom/wlan_firmware_service_v01.h",
    "icnss_qmi": OSRC_ROOT / "drivers/soc/qcom/icnss_qmi.c",
    "r3q_overlay": OSRC_ROOT / "arch/arm64/boot/dts/samsung/renovation/sm8150-sec-r3q-kor-overlay-r02.dts",
}

FORBIDDEN_ACTIONS = (
    "host-only; no bridge command",
    "no device command, reboot, bootloader handoff, boot image write, or partition write",
    "no custom kernel flash",
    "no QRTR socket open or QRTR/QMI packet transmission",
    "no service-manager, Wi-Fi HAL, scan/connect, credential use, DHCP, route, or external ping",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v821-manifest", type=Path, default=DEFAULT_V821_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = path if path.is_absolute() else repo_path(path)
    if not resolved.exists():
        return {"file": {"path": str(resolved), "exists": False}, "data": {}}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"file": {"path": str(resolved), "exists": True}, "data": {}, "error": str(exc)}
    return {
        "file": {"path": str(resolved), "exists": True, "size": resolved.stat().st_size},
        "data": data if isinstance(data, dict) else {},
    }


def read_source(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"path": str(resolved), "exists": False, "text": ""}
    return {
        "path": str(resolved),
        "exists": True,
        "size": resolved.stat().st_size,
        "text": resolved.read_text(encoding="utf-8", errors="replace"),
    }


def parse_int_literal(value: str) -> int | None:
    try:
        return int(value, 0)
    except ValueError:
        return None


def extract_define(text: str, name: str) -> int | None:
    pattern = re.compile(rf"^\s*#define\s+{re.escape(name)}\s+([xXa-fA-F0-9]+)", re.MULTILINE)
    match = pattern.search(text)
    return parse_int_literal(match.group(1)) if match else None


def extract_service_locator_instance(text: str) -> int | None:
    match = re.search(r"#define\s+SERVREG_LOC_SERVICE_INSTANCE_ID\s+([xXa-fA-F0-9]+)", text)
    return parse_int_literal(match.group(1)) if match else None


def extract_ssctl_instances(text: str) -> list[int]:
    values: list[int] = []
    for match in re.finditer(r"qcom,ssctl-instance-id\s*=\s*<\s*([xXa-fA-F0-9]+)\s*>", text):
        value = parse_int_literal(match.group(1))
        if value is not None and value not in values:
            values.append(value)
    return values


def matrix_rows(v821: dict[str, Any]) -> list[dict[str, Any]]:
    matrix = (((v821.get("live") or {}).get("matrix") or {}))
    rows = matrix.get("rows", [])
    return rows if isinstance(rows, list) else []


def matrix_has(rows: list[dict[str, Any]], service: int | None, instance: int | None) -> bool:
    if service is None or instance is None:
        return False
    return any(row.get("service") == service and row.get("instance") == instance for row in rows)


def matrix_result(rows: list[dict[str, Any]], service: int | None, instance: int | None) -> dict[str, Any]:
    for row in rows:
        if row.get("service") == service and row.get("instance") == instance:
            return row
    return {}


def v821_runtime_counts(v821: dict[str, Any]) -> dict[str, Any]:
    snapshots = ((((v821.get("live") or {}).get("live") or {}).get("snapshots") or {}))
    if not isinstance(snapshots, dict):
        return {}
    out: dict[str, Any] = {}
    for phase in ("before-holder", "after-holder", "after-companion"):
        snap = snapshots.get(phase) or {}
        out[phase] = {
            "mss_or_modem_state": snap.get("mss_or_modem_state"),
            "mdm3_state": snap.get("mdm3_state"),
            "runtime_counts": snap.get("runtime_counts", {}),
        }
    return out


def source_model() -> dict[str, Any]:
    sources = {name: read_source(path) for name, path in DEFAULT_SOURCE_PATHS.items()}
    servloc_text = sources["service_locator_private"]["text"]
    servloc_impl = sources["service_locator"]["text"]
    servnotif_text = sources["service_notifier_private"]["text"]
    sysmon_text = sources["sysmon_qmi"]["text"]
    wlfw_text = sources["wlfw"]["text"]
    overlay_text = sources["r3q_overlay"]["text"]
    return {
        "sources": {
            name: {key: value for key, value in source.items() if key != "text"}
            for name, source in sources.items()
        },
        "services": {
            "service-locator": {
                "service": extract_define(servloc_text, "SERVREG_LOC_SERVICE_ID_V01"),
                "version": extract_define(servloc_text, "SERVREG_LOC_SERVICE_VERS_V01"),
                "instance": extract_service_locator_instance(servloc_impl),
                "lookup_source": "service-locator.c:qmi_add_lookup",
            },
            "service-notifier": {
                "service": extract_define(servnotif_text, "SERVREG_NOTIF_SERVICE_ID_V01"),
                "version": extract_define(servnotif_text, "SERVREG_NOTIF_SERVICE_VERS_V01"),
                "instances": [74, 180],
                "lookup_source": "service-notifier.c:qmi_add_lookup(instance_id)",
            },
            "sysmon-ssctl": {
                "service": extract_define(sysmon_text, "SSCTL_SERVICE_ID"),
                "version": extract_define(sysmon_text, "SSCTL_VER_2"),
                "instances": extract_ssctl_instances(overlay_text),
                "lookup_source": "sysmon-qmi.c:qmi_add_lookup(desc->ssctl_instance_id)",
            },
            "wlfw": {
                "service": extract_define(wlfw_text, "WLFW_SERVICE_ID_V01"),
                "version": extract_define(wlfw_text, "WLFW_SERVICE_VERS_V01"),
                "instances": [0],
                "lookup_source": "icnss_qmi.c:qmi_add_lookup(..., instance 0)",
            },
        },
    }


def build_matrix_coverage(v821: dict[str, Any], model: dict[str, Any]) -> list[dict[str, Any]]:
    rows = matrix_rows(v821)
    services = model["services"]
    coverage: list[dict[str, Any]] = []
    for name in ("service-locator",):
        service = services[name]["service"]
        instance = services[name]["instance"]
        coverage.append({
            "name": name,
            "service": service,
            "instance": instance,
            "included": matrix_has(rows, service, instance),
            "row": matrix_result(rows, service, instance),
        })
    for name in ("service-notifier", "sysmon-ssctl", "wlfw"):
        service = services[name]["service"]
        for instance in services[name]["instances"]:
            coverage.append({
                "name": name,
                "service": service,
                "instance": instance,
                "included": matrix_has(rows, service, instance),
                "row": matrix_result(rows, service, instance),
            })
    return coverage


def build_checks(args: argparse.Namespace,
                 loaded: dict[str, Any],
                 model: dict[str, Any],
                 coverage: list[dict[str, Any]]) -> list[dict[str, Any]]:
    v821 = loaded["data"]
    sources_ok = all(source.get("exists") for source in model["sources"].values())
    service_constants_ok = all(
        service.get("service") is not None and service.get("version") is not None
        for service in model["services"].values()
    )
    matrix = ((v821.get("live") or {}).get("matrix") or {})
    ssctl_entries = [item for item in coverage if item["name"] == "sysmon-ssctl"]
    ssctl_missing = bool(ssctl_entries) and all(not item["included"] for item in ssctl_entries)
    included_clean = [
        item for item in coverage
        if item["included"] and int(item.get("row", {}).get("service_events") or 0) == 0
    ]
    return [
        {
            "name": "host-only-boundary",
            "status": "pass",
            "detail": "no bridge/device command; source and evidence only",
            "next_step": "keep V822 host-only",
        },
        {
            "name": "v821-matrix-ready",
            "status": "pass" if loaded["file"].get("exists") and v821.get("pass") and v821.get("decision") == "v821-qrtr-nameservice-matrix-empty-below-hal" else "blocked",
            "detail": {"file": loaded["file"], "decision": v821.get("decision"), "pass": v821.get("pass")},
            "next_step": "complete V821 before V822",
        },
        {
            "name": "source-constants-ready",
            "status": "pass" if sources_ok and service_constants_ok else "blocked",
            "detail": {"sources_ok": sources_ok, "service_constants_ok": service_constants_ok, "services": model["services"]},
            "next_step": "restore staged OSRC source before classification",
        },
        {
            "name": "v821-transport-clean-empty",
            "status": "pass" if matrix.get("socket_ok") and matrix.get("lookup_ok") and matrix.get("total_service_events") == 0 and matrix.get("total_timeouts") == 0 else "blocked",
            "detail": matrix,
            "next_step": "fix V821 transport/readback before interpreting source model",
        },
        {
            "name": "sysmon-ssctl-not-in-v821-matrix",
            "status": "finding" if ssctl_missing else "blocked",
            "detail": ssctl_entries,
            "next_step": "add SSCTL service 43 board instance to the next no-QMI nameservice matrix",
        },
        {
            "name": "included-candidates-clean-empty",
            "status": "finding" if included_clean else "blocked",
            "detail": included_clean,
            "next_step": "do not retry the same service-locator/service-notifier/WLFW matrix unchanged",
        },
    ]


def decide(checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    if blockers:
        return (
            "v822-sysmon-nameservice-gap-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "resolve host-only evidence/source blockers before selecting next live gate",
        )
    return (
        "v822-sysmon-ssctl-matrix-gap-classified",
        True,
        "V821 did not include the sysmon SSCTL service 0x2b/instance 0x10 path that source and board DTS identify for sysmon-qmi",
        "V823 should extend helper v125 matrix to include ssctl:43:16 before any QMI payload, HAL, scan/connect, credential, DHCP, route, external ping, or custom-kernel flash",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    loaded = load_json(args.v821_manifest)
    model = source_model()
    v821 = loaded["data"]
    coverage = build_matrix_coverage(v821, model)
    checks = build_checks(args, loaded, model, coverage)
    decision, pass_ok, reason, next_step = decide(checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v822",
        "decision": decision if args.command == "run" else "v822-sysmon-nameservice-gap-plan-ready",
        "pass": pass_ok,
        "reason": reason if args.command == "run" else "plan-only; host-only classifier defined",
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v821": {
            "file": loaded["file"],
            "decision": v821.get("decision"),
            "pass": v821.get("pass"),
            "matrix": ((v821.get("live") or {}).get("matrix") or {}),
            "runtime_counts": v821_runtime_counts(v821),
        },
        "source_model": model,
        "coverage": coverage,
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "qmi_payload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    coverage_rows = [
        [
            item["name"],
            str(item["service"]),
            str(item["instance"]),
            str(item["included"]),
            str((item.get("row") or {}).get("service_events", "")),
            str((item.get("row") or {}).get("end_of_list", "")),
        ]
        for item in manifest["coverage"]
    ]
    services = manifest["source_model"]["services"]
    service_rows = [
        [name, str(data.get("service")), str(data.get("version")), json.dumps(data.get("instances", data.get("instance")), sort_keys=True), data.get("lookup_source", "")]
        for name, data in services.items()
    ]
    return "\n".join([
        "# V822 Sysmon Nameservice Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Source Services",
        "",
        markdown_table(["name", "service", "version", "instances", "source"], service_rows),
        "",
        "## Matrix Coverage",
        "",
        markdown_table(["name", "service", "instance", "included", "service_events", "eol"], coverage_rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"qmi_payload_executed: {manifest['qmi_payload_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
