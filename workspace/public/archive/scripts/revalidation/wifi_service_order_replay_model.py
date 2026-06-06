#!/usr/bin/env python3
"""Build a no-execution Wi-Fi service-order replay model.

v287 consumes prior Android/native evidence and produces a deterministic replay
stage model.  It does not talk to the device, start daemons, send QRTR/QMI
traffic, modify rfkill/sysfs, or bring up any network interface.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_V216 = Path("tmp/wifi/v216-service-replay-model/manifest.json")
DEFAULT_V228 = Path("tmp/wifi/v228-controlled-cnss-start-plan/manifest.json")
DEFAULT_V286 = Path("tmp/wifi/v286-icnss-boot-timing-native-20260519-133421/manifest.json")
DEFAULT_OUT_DIR = Path("tmp/wifi/v287-wifi-service-order-replay-model")

SERVICE_EVENT_MAP = {
    "android_wifi_action": "vendor.wifi_hal_ext",
    "wifi_hal_start": "vendor.wifi_hal_ext",
    "cnss_diag_start": "cnss_diag",
    "wificond_start": "wificond",
    "cnss_daemon_start": "cnss-daemon",
}

CHECKPOINT_EVENTS = {
    "wlfw_start": "wlfw-start-observed",
    "qmi_server_connected": "qmi-server-connected-observed",
    "bdf_download": "bdf-download-observed",
    "wlan_fw_ready": "wlan-fw-ready-observed",
    "firmware_load": "firmware-load-observed",
    "wlan_driver_log": "wlan-driver-log-observed",
    "fw_ready_event": "fw-ready-event-observed",
    "wlan_netdev": "wlan-netdev-observed",
    "wiphy_rfkill": "wiphy-rfkill-observed",
}

SIBLING_CANDIDATES = {
    "vendor.wifi_hal_ext": ["vendor.wifi_hal_legacy"],
}

REQUIRED_DECISIONS = {
    "v216": "replay-model-ready",
    "v228": "cnss-start-plan-ready",
    "v286": "icnss-boot-timing-gap-mapped",
}

FORBIDDEN_ALLOWED_SERVICES = {
    "vendor.wifi_hal_legacy",
    "vendor.wifi_hal_ext",
    "wificond",
    "wpa_supplicant",
    "hostapd",
    "cnss_diag",
}


@dataclass
class ServiceRef:
    name: str
    executable: str = ""
    args: list[str] = field(default_factory=list)
    source: str = ""
    user: str = ""
    groups: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    android_state: str = ""
    android_pid: str = ""
    android_boottime: str = ""
    native_availability: str = ""
    risk: str = ""
    blockers: list[str] = field(default_factory=list)


@dataclass
class ReplayStage:
    index: int
    event: str
    android_time_sec: float | None
    service: str
    stage_type: str
    policy: str
    allowed_now: bool
    required_gate: str
    notes: list[str] = field(default_factory=list)
    service_ref: ServiceRef | None = None
    sibling_candidates: list[ServiceRef] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v216-manifest", type=Path, default=DEFAULT_V216)
    parser.add_argument("--v228-manifest", type=Path, default=DEFAULT_V228)
    parser.add_argument("--v286-manifest", type=Path, default=DEFAULT_V286)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def normalize_service(raw: dict[str, Any]) -> ServiceRef:
    executable = str(raw.get("executable") or raw.get("binary") or "")
    return ServiceRef(
        name=str(raw.get("name") or ""),
        executable=executable,
        args=as_list(raw.get("args")),
        source=str(raw.get("source") or ""),
        user=str(raw.get("user") or ""),
        groups=as_list(raw.get("groups")),
        capabilities=as_list(raw.get("capabilities")),
        interfaces=as_list(raw.get("interfaces")),
        flags=as_list(raw.get("flags")),
        android_state=str(raw.get("android_state") or ""),
        android_pid=str(raw.get("android_pid") or ""),
        android_boottime=str(raw.get("android_boottime") or ""),
        native_availability=str(raw.get("native_availability") or ""),
        risk=str(raw.get("risk") or ""),
        blockers=as_list(raw.get("blockers")),
    )


def merge_service(primary: ServiceRef, overlay: ServiceRef) -> ServiceRef:
    def pick(left: str, right: str) -> str:
        return right or left

    def merge_list(left: list[str], right: list[str]) -> list[str]:
        values = list(left)
        seen = set(values)
        for item in right:
            if item and item not in seen:
                values.append(item)
                seen.add(item)
        return values

    return ServiceRef(
        name=primary.name,
        executable=pick(primary.executable, overlay.executable),
        args=overlay.args or primary.args,
        source=pick(primary.source, overlay.source),
        user=pick(primary.user, overlay.user),
        groups=merge_list(primary.groups, overlay.groups),
        capabilities=merge_list(primary.capabilities, overlay.capabilities),
        interfaces=merge_list(primary.interfaces, overlay.interfaces),
        flags=merge_list(primary.flags, overlay.flags),
        android_state=pick(primary.android_state, overlay.android_state),
        android_pid=pick(primary.android_pid, overlay.android_pid),
        android_boottime=pick(primary.android_boottime, overlay.android_boottime),
        native_availability=pick(primary.native_availability, overlay.native_availability),
        risk=pick(primary.risk, overlay.risk),
        blockers=merge_list(primary.blockers, overlay.blockers),
    )


def build_service_index(v216: dict[str, Any], v228: dict[str, Any]) -> dict[str, ServiceRef]:
    services: dict[str, ServiceRef] = {}
    for raw in v216.get("graph", {}).get("services", []):
        if isinstance(raw, dict):
            service = normalize_service(raw)
            if service.name:
                services[service.name] = service
    for raw in v228.get("services", []):
        if isinstance(raw, dict):
            service = normalize_service(raw)
            if not service.name:
                continue
            if service.name in services:
                services[service.name] = merge_service(services[service.name], service)
            else:
                services[service.name] = service
    return services


def android_rows(v286: dict[str, Any]) -> list[dict[str, Any]]:
    rows = v286.get("comparison", {}).get("rows", [])
    if not isinstance(rows, list):
        return []
    return [
        row
        for row in rows
        if isinstance(row, dict) and (row.get("android") is not None or row.get("android_line"))
    ]


def service_policy(service_name: str) -> tuple[str, bool, str, list[str]]:
    if service_name == "cnss-daemon":
        return (
            "bounded-start-only-candidate",
            False,
            "explicit live approval plus v283-v285 runner guardrails",
            ["only already-proven start-only candidate", "v287 records model only"],
        )
    if service_name == "cnss_diag":
        return (
            "diagnostic-daemon-blocked",
            False,
            "primary cnss-daemon readiness signal or diagnostic-specific plan",
            ["diagnostic side channel; do not start before primary path is understood"],
        )
    if service_name.startswith("vendor.wifi_hal"):
        return (
            "hal-service-blocked",
            False,
            "binder/hwbinder/hwservicemanager/VINTF/property namespace inventory",
            ["HAL has Android IPC and capability context not replicated by native init"],
        )
    if service_name == "wificond":
        return (
            "framework-service-blocked",
            False,
            "framework socket/binder/property dependency inventory",
            ["wificond is model-only before Android framework boundary is understood"],
        )
    if service_name in {"wpa_supplicant", "hostapd"}:
        return (
            "active-network-blocked",
            False,
            "separate scan/connect/link-up/credential gate",
            ["supplicant/hostapd can alter network state and remain blocked"],
        )
    return ("unknown-service-blocked", False, "manual review", [])


def checkpoint_policy(event: str) -> tuple[str, bool, str, list[str]]:
    return (
        "observe-only-checkpoint",
        False,
        "preceding service stage must be safely reproducible first",
        [CHECKPOINT_EVENTS[event], "no QMI payload, rfkill write, link-up, or scan/connect"],
    )


def build_replay_stages(v286: dict[str, Any], services: dict[str, ServiceRef]) -> list[ReplayStage]:
    stages: list[ReplayStage] = []
    for row in android_rows(v286):
        event = str(row.get("kind") or "")
        android_time = row.get("android")
        android_time_sec = float(android_time) if isinstance(android_time, (int, float)) else None
        if event in SERVICE_EVENT_MAP:
            service_name = SERVICE_EVENT_MAP[event]
            policy, allowed_now, gate, notes = service_policy(service_name)
            service = services.get(service_name, ServiceRef(name=service_name))
            sibling_refs = [
                services.get(name, ServiceRef(name=name))
                for name in SIBLING_CANDIDATES.get(service_name, [])
            ]
            if event == "android_wifi_action":
                notes = notes + ["first missing native boot-window boundary from v286"]
            stages.append(
                ReplayStage(
                    index=len(stages) + 1,
                    event=event,
                    android_time_sec=android_time_sec,
                    service=service_name,
                    stage_type="service",
                    policy=policy,
                    allowed_now=allowed_now,
                    required_gate=gate,
                    notes=notes,
                    service_ref=service,
                    sibling_candidates=sibling_refs,
                )
            )
            continue
        if event in CHECKPOINT_EVENTS:
            policy, allowed_now, gate, notes = checkpoint_policy(event)
            stages.append(
                ReplayStage(
                    index=len(stages) + 1,
                    event=event,
                    android_time_sec=android_time_sec,
                    service="",
                    stage_type="checkpoint",
                    policy=policy,
                    allowed_now=allowed_now,
                    required_gate=gate,
                    notes=notes,
                )
            )
    return stages


def validate_inputs(v216: dict[str, Any], v228: dict[str, Any], v286: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for name, manifest in (("v216", v216), ("v228", v228), ("v286", v286)):
        if not manifest.get("present"):
            errors.append(f"{name} manifest missing: {manifest.get('path')}")
            continue
        expected = REQUIRED_DECISIONS[name]
        if manifest.get("decision") != expected:
            errors.append(f"{name} decision expected {expected}, got {manifest.get('decision')}")
        if manifest.get("pass") is not True:
            errors.append(f"{name} pass expected true")
    return errors


def classify(input_errors: list[str], stages: list[ReplayStage]) -> tuple[bool, str, str]:
    if input_errors:
        missing = [item for item in input_errors if "missing" in item]
        decision = "wifi-service-order-input-missing" if missing else "wifi-service-order-input-incomplete"
        return False, decision, "; ".join(input_errors)
    if not stages:
        return False, "wifi-service-order-input-incomplete", "no Android timing rows mapped to replay stages"
    unsafe = [
        stage.service
        for stage in stages
        if stage.allowed_now and stage.service in FORBIDDEN_ALLOWED_SERVICES
    ]
    if unsafe:
        return False, "wifi-service-order-unsafe-policy", "unsafe service marked allowed: " + ", ".join(sorted(set(unsafe)))
    return True, "wifi-service-order-replay-model-ready", "Android service-order gap is mapped without live execution"


def stage_payload(stage: ReplayStage) -> dict[str, Any]:
    payload = asdict(stage)
    if stage.service_ref is None:
        payload["service_ref"] = None
    return payload


def render_summary(manifest: dict[str, Any]) -> str:
    stage_rows = []
    for stage in manifest["replay_stages"]:
        ref = stage.get("service_ref") or {}
        stage_rows.append([
            str(stage["index"]),
            stage["event"],
            "" if stage["android_time_sec"] is None else f"{stage['android_time_sec']:.3f}",
            stage["service"] or stage["stage_type"],
            stage["policy"],
            "yes" if stage["allowed_now"] else "no",
            stage["required_gate"],
            ref.get("executable", ""),
        ])
    service_rows = []
    for service in manifest["service_order"]:
        service_rows.append([
            service["name"],
            service.get("executable", ""),
            ", ".join(service.get("capabilities", [])),
            service.get("risk", ""),
            service.get("native_availability", ""),
            ", ".join(service.get("blockers", [])[:3]) or "none",
        ])
    lines = [
        "# v287 Wi-Fi Service-Order Replay Model\n\n",
        f"- generated: `{manifest['created']}`\n",
        f"- pass: `{manifest['pass']}`\n",
        f"- decision: `{manifest['decision']}`\n",
        f"- reason: {manifest['reason']}\n",
        f"- first missing native event: `{manifest['v286_first_missing_native']}`\n\n",
        "## Replay Stages\n\n",
        markdown_table(
            ["#", "event", "android_s", "boundary", "policy", "allowed_now", "required gate", "executable"],
            stage_rows,
        ),
        "\n\n## Service Metadata\n\n",
        markdown_table(["service", "executable", "capabilities", "risk", "native availability", "blockers"], service_rows),
        "\n\n## Guardrails\n\n",
    ]
    lines.extend(f"- {item}\n" for item in manifest["guardrails"])
    lines.extend([
        "\n## Recommendation\n\n",
        "- Do not repeat blind `cnss-daemon -n -l` start-only runs.\n",
        "- Next step should inventory HAL/framework boundaries before Wi-Fi HAL or `wificond` execution.\n",
        "- `wpa_supplicant` and `hostapd` remain blocked until scan/connect/link-up policy exists.\n",
    ])
    return "".join(lines)


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v216 = load_manifest(args.v216_manifest)
    v228 = load_manifest(args.v228_manifest)
    v286 = load_manifest(args.v286_manifest)
    input_errors = validate_inputs(v216, v228, v286)
    services = build_service_index(v216, v228)
    stages = build_replay_stages(v286, services) if not input_errors else []
    pass_ok, decision, reason = classify(input_errors, stages)
    ordered_services = [
        asdict(services[name])
        for name in (
            "vendor.wifi_hal_ext",
            "vendor.wifi_hal_legacy",
            "cnss_diag",
            "wificond",
            "cnss-daemon",
            "wpa_supplicant",
            "hostapd",
        )
        if name in services
    ]
    manifest: dict[str, Any] = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "inputs": {
            "v216_manifest": str(repo_path(args.v216_manifest)),
            "v228_manifest": str(repo_path(args.v228_manifest)),
            "v286_manifest": str(repo_path(args.v286_manifest)),
        },
        "source_decisions": {
            "v216": v216.get("decision"),
            "v228": v228.get("decision"),
            "v286": v286.get("decision"),
        },
        "input_errors": input_errors,
        "v286_first_missing_native": v286.get("comparison", {}).get("first_missing_native"),
        "replay_stages": [stage_payload(stage) for stage in stages],
        "service_order": ordered_services,
        "blocked_services": [
            "vendor.wifi_hal_ext",
            "vendor.wifi_hal_legacy",
            "cnss_diag",
            "wificond",
            "wpa_supplicant",
            "hostapd",
        ],
        "start_only_candidate": "cnss-daemon",
        "next_recommendation": "v288 HAL/framework boundary inventory before any HAL or wificond execution",
        "guardrails": [
            "no device command execution",
            "no service start",
            "no cnss-daemon/cnss_diag/Wi-Fi HAL/wificond/supplicant/hostapd execution",
            "no QMI payload",
            "no QRTR nameservice packet",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill write",
            "no ICNSS bind/unbind or driver_override",
            "no firmware path mutation",
            "no reboot/recovery/poweroff",
            "no Android partition write",
        ],
        "host_metadata": collect_host_metadata(),
    }
    return manifest


def main() -> int:
    args = parse_args()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_json("service-order.json", {"services": manifest["service_order"]})
    store.write_json("replay-stages.json", {"stages": manifest["replay_stages"]})
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"out_dir: {out_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
