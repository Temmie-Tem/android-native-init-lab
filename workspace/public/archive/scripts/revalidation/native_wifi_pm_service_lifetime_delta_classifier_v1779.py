#!/usr/bin/env python3
"""V1779 host-only classifier for V1778 pm-service lifetime delta."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
V1778_DIR = REPO_ROOT / "tmp" / "wifi" / "v1778-service-object-policy-load-handoff"
V1092_DIR = REPO_ROOT / "tmp" / "wifi" / "v1092-pm-observer-provider-ready-live"
SOURCE_PATH = REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_android_execns_probe.c"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1779-pm-service-lifetime-delta-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1779_PM_SERVICE_LIFETIME_DELTA_CLASSIFIER_2026-06-03.md"
)


@dataclass(frozen=True)
class RunText:
    manifest: dict[str, Any]
    text: str
    fields: dict[str, str]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def text_from_binary_safe(path: Path) -> str:
    data = path.read_bytes()
    return data.replace(b"\0", b"\n").decode("utf-8", errors="replace")


def parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or " " in key or key.startswith("A90_"):
            continue
        fields[key] = value.strip()
    return fields


def load_v1778() -> RunText:
    manifest = load_json(V1778_DIR / "manifest.json")
    text = text_from_binary_safe(V1778_DIR / "test-v1393-helper-result.stdout.txt")
    return RunText(manifest=manifest, text=text, fields=parse_fields(text))


def load_v1092() -> RunText:
    manifest = load_json(V1092_DIR / "manifest.json")
    text = text_from_binary_safe(V1092_DIR / "host" / "pm-service-trigger-observer.txt")
    return RunText(manifest=manifest, text=text, fields=parse_fields(text))


def contains(text: str, needle: str) -> bool:
    return needle in text


def regex_present(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.MULTILINE | re.DOTALL) is not None


def property_values(fields: dict[str, str], prop: str) -> list[str]:
    values: list[str] = []
    prefix = "wifi_hal_composite_start.property_service_shim.request."
    for key, value in fields.items():
        if not key.startswith(prefix) or not key.endswith(".name"):
            continue
        if value != prop:
            continue
        values.append(fields.get(key[: -len(".name")] + ".value", ""))
    return values


def classify(v1778: RunText, v1092: RunText, source: str) -> tuple[str, bool, str, dict[str, Any]]:
    v1778_gate = v1778.manifest.get("gate", {})
    facts: dict[str, Any] = {
        "v1778_decision": v1778.manifest.get("decision"),
        "v1778_pass": bool(v1778.manifest.get("pass")),
        "v1778_policy_load_result": v1778_gate.get("policy_load_result"),
        "v1778_policy_load_pass": v1778_gate.get("policy_load_pass"),
        "v1778_per_mgr_state": v1778_gate.get("per_mgr_state"),
        "v1778_per_mgr_zombie": v1778_gate.get("per_mgr_zombie"),
        "v1778_provider_seen": v1778_gate.get("provider_seen"),
        "v1778_as_interface_hits": v1778_gate.get("as_interface_hits"),
        "v1778_register_tx_hits": v1778_gate.get("register_tx_hits"),
        "v1778_vndservicemanager_exec_target": v1778.fields.get(
            "wifi_hal_composite_child.vndservicemanager.exec_target"
        ),
        "v1778_vndservicemanager_argv": v1778.fields.get("wifi_companion_start.vndservicemanager_argv"),
        "v1778_property_request_count": v1778.fields.get(
            "wifi_hal_composite_start.property_service_shim.request_count"
        ),
        "v1778_shutdown_critical_values": property_values(
            v1778.fields, "vendor.peripheral.shutdown_critical_list"
        ),
        "v1092_decision": v1092.manifest.get("decision"),
        "v1092_pass": bool(v1092.manifest.get("pass")),
        "v1092_provider_seen_manifest": bool(v1092.manifest.get("vndservice_provider_seen")),
        "v1092_provider_seen_text": contains(v1092.text, "vendor.qcom.PeripheralManager"),
        "v1092_per_mgr_sleeping": regex_present(
            v1092.text, r"Name:\s*pm-service.*?State:\s*S \(sleeping\)"
        ),
        "v1092_vndservicemanager_exec_target": v1092.fields.get(
            "wifi_hal_composite_child.vndservicemanager.exec_target"
        ),
        "v1092_vndservice_ready": v1092.fields.get(
            "pm_service_trigger_observer.vndservicemanager_readiness.ready"
        ),
        "v1092_per_mgr_ready": v1092.fields.get(
            "pm_service_trigger_observer.child.per_mgr.post_start_ready"
        ),
        "v1092_shutdown_critical_values": property_values(
            v1092.fields, "vendor.peripheral.shutdown_critical_list"
        ),
        "source_forces_vndservice_system_fallback": contains(
            source,
            'identity == COMPOSITE_ID_VND_SERVICE_MANAGER &&\n'
            '                     streq(target, "/vendor/bin/vndservicemanager"))\n'
            '                        ? "/system/bin/servicemanager"'
        ),
    }

    target_gap = (
        facts["v1778_vndservicemanager_exec_target"] == "/system/bin/servicemanager /dev/vndbinder"
        and facts["v1092_vndservicemanager_exec_target"] == "/vendor/bin/vndservicemanager /dev/vndbinder"
    )
    v1778_lifetime_failed = (
        facts["v1778_policy_load_result"] == "policy-load-pass"
        and facts["v1778_per_mgr_state"] == "Z"
        and facts["v1778_per_mgr_zombie"] == "1"
        and facts["v1778_provider_seen"] == "0"
    )
    v1092_lifetime_ok = (
        facts["v1092_provider_seen_manifest"]
        and facts["v1092_provider_seen_text"]
        and facts["v1092_per_mgr_sleeping"]
        and facts["v1092_per_mgr_ready"] == "1"
    )

    facts["target_gap"] = target_gap
    facts["v1778_lifetime_failed_after_policy"] = v1778_lifetime_failed
    facts["v1092_lifetime_provider_positive"] = v1092_lifetime_ok

    if target_gap and v1778_lifetime_failed and v1092_lifetime_ok:
        return (
            "v1779-vndservicemanager-spawn-parity-gap-host-pass",
            True,
            "V1778 fails after policy-load because pm-service exits zombie; V1092 keeps pm-service alive and publishes the provider with vendor vndservicemanager, while V1778 uses the system servicemanager fallback",
            facts,
        )
    if v1778_lifetime_failed and v1092_lifetime_ok:
        return (
            "v1779-pm-service-lifetime-gap-host-pass",
            True,
            "V1778 fails after policy-load while V1092 is provider-positive, but the exact spawn-target delta is incomplete",
            facts,
        )
    return (
        "v1779-pm-service-lifetime-delta-incomplete-host-blocked",
        False,
        "required V1778/V1092 evidence is incomplete or inconsistent",
        facts,
    )


def render_report(manifest: dict[str, Any]) -> str:
    facts = manifest["facts"]
    shutdown_1778 = ", ".join(facts["v1778_shutdown_critical_values"])
    shutdown_1092 = ", ".join(facts["v1092_shutdown_critical_values"])
    return "\n".join([
        "# Native Init V1779 PM-service Lifetime Delta Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1779`",
        "- Type: host-only classifier",
        f"- Decision: `{manifest['decision']}`",
        f"- Result: `{'PASS' if manifest['pass'] else 'BLOCKED'}`",
        f"- Reason: {manifest['reason']}",
        f"- Evidence: `{manifest['out_dir']}`",
        "",
        "## Delta",
        "",
        f"- V1778 policy-load result: `{facts['v1778_policy_load_result']}`",
        f"- V1778 `pm-service` state: `{facts['v1778_per_mgr_state']}`",
        f"- V1778 provider seen: `{facts['v1778_provider_seen']}`",
        f"- V1778 VND service-manager target: `{facts['v1778_vndservicemanager_exec_target']}`",
        f"- V1778 shutdown-list values: `{shutdown_1778}`",
        f"- V1092 provider-positive: `{facts['v1092_lifetime_provider_positive']}`",
        f"- V1092 `pm-service` sleeping: `{facts['v1092_per_mgr_sleeping']}`",
        f"- V1092 VND service-manager target: `{facts['v1092_vndservicemanager_exec_target']}`",
        f"- V1092 shutdown-list values: `{shutdown_1092}`",
        f"- Source currently forces VND service-manager fallback: `{facts['source_forces_vndservice_system_fallback']}`",
        "",
        "## Interpretation",
        "",
        "- The V1778 result is not a modem/WLAN-PD response result: it fails before `vendor.qcom.PeripheralManager` is visible.",
        "- Policy-load and SELinux domain transition are no longer the missing precondition.",
        "- The strongest host-side delta is VND service-manager parity: V1092 uses `/vendor/bin/vndservicemanager /dev/vndbinder`, while V1778 uses `/system/bin/servicemanager /dev/vndbinder` through the helper fallback.",
        "- The next source/build gate should restore vendor `vndservicemanager` spawning for the narrow service-object route, then rerun the same four-label discriminator.",
        "",
        "## Safety",
        "",
        "- Host-only analysis. No live device command, flash, reboot, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping was performed.",
        "",
    ])


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    v1778 = load_v1778()
    v1092 = load_v1092()
    source = SOURCE_PATH.read_text(encoding="utf-8")
    decision, pass_ok, reason, facts = classify(v1778, v1092, source)
    manifest = {
        "cycle": "V1779",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "out_dir": str(OUT_DIR.relative_to(REPO_ROOT)),
        "inputs": {
            "v1778_manifest": str((V1778_DIR / "manifest.json").relative_to(REPO_ROOT)),
            "v1092_manifest": str((V1092_DIR / "manifest.json").relative_to(REPO_ROOT)),
            "helper_source": str(SOURCE_PATH.relative_to(REPO_ROOT)),
        },
        "facts": facts,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (OUT_DIR / "summary.md").write_text(render_report(manifest), encoding="utf-8")
    REPORT_PATH.write_text(render_report(manifest), encoding="utf-8")
    print(json.dumps({"decision": decision, "pass": pass_ok, "reason": reason}, indent=2))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
