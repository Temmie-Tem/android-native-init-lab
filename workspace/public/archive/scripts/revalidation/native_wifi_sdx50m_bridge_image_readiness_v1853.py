#!/usr/bin/env python3
"""V1853 host-only readiness classifier for the SDX50M bridge test image."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1853"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1853-sdx50m-bridge-image-readiness"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1853_SDX50M_BRIDGE_IMAGE_READINESS_2026-06-03.md"
)
V1846_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1846-pm-service-open-context-test-boot"
    / "manifest.json"
)
V1847_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1847-pm-service-open-context-handoff"
    / "manifest.json"
)
V1852_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1852-sdx50m-bridge-gate-scaffold"
    / "manifest.json"
)


REQUIRED_SELECTION_LABELS = {
    "pm_init_pm_client_register_call",
    "pm_init_pm_client_register_retcheck",
    "pm_init_pm_client_connect_call",
    "pm_init_pm_client_connect_retcheck",
    "pm_init_return_path",
    "pm_server_register_entry",
    "pm_server_register_strcmp_call",
}

REQUIRED_OPEN_CONTEXT_LABELS = {
    "pm_service_post_ack_power_state_loaded",
    "pm_service_post_ack_open_context",
    "pm_service_post_ack_open_path_loaded",
    "pm_service_post_ack_open_fd_store",
    "pm_service_post_ack_open_fd_compare",
    "pm_service_post_ack_open_success_counter",
}

REQUIRED_LOWER_FIELDS = {
    "lower_mdm3_states",
    "lower_mhi_present",
    "lower_service69_progress",
    "lower_wlan0_present",
    "pm_focus_mhi_wlan0_progress",
    "pm_focus_change_fields",
    "pm_focus_mdm_status_delta",
}


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def intish(value: object) -> int:
    try:
        return int(str(value or "0"), 0)
    except ValueError:
        return 0


def collect_image(manifest: dict[str, Any]) -> dict[str, Any]:
    boot_image = REPO_ROOT / str(manifest.get("boot_image", ""))
    image_exists = boot_image.exists()
    actual_sha = sha256_file(boot_image) if image_exists else ""
    safety = manifest.get("safety") or {}
    return {
        "path": rel(V1846_MANIFEST),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "source_build_only": bool(manifest.get("source_build_only")),
        "boot_image": str(manifest.get("boot_image", "")),
        "boot_image_exists": image_exists,
        "boot_sha256": manifest.get("boot_sha256", ""),
        "boot_sha256_actual": actual_sha,
        "boot_sha256_ok": image_exists and actual_sha == manifest.get("boot_sha256", ""),
        "helper_marker": manifest.get("helper_marker", ""),
        "helper_sha256": manifest.get("helper_sha256", ""),
        "safety": safety,
        "safety_clean": (
            not bool(safety.get("credentials"))
            and not bool(safety.get("device_command"))
            and not bool(safety.get("dhcp_routes_external_ping"))
            and not bool(safety.get("flash"))
            and not bool(safety.get("partition_write"))
            and not bool(safety.get("wifi_scan_connect"))
        ),
        "wifi_test_label": (manifest.get("wifi_test") or {}).get("label", ""),
        "wifi_test_scan_connect_credentials": bool((manifest.get("wifi_test") or {}).get("scan_connect_credentials")),
    }


def collect_handoff(manifest: dict[str, Any]) -> dict[str, Any]:
    gate = manifest.get("gate") or {}
    return {
        "path": rel(V1847_MANIFEST),
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "safety_ok": bool(gate.get("safety_ok")),
        "open_context_registered_ok": bool(gate.get("open_context_registered_ok")),
        "open_context_enabled_ok": bool(gate.get("open_context_enabled_ok")),
        "open_context_hit_keys": gate.get("open_context_hit_keys") or [],
        "open_context_path": gate.get("open_context_path", ""),
        "open_context_fd": gate.get("open_context_fd", ""),
        "post_ack_registered_ok": bool(gate.get("post_ack_registered_ok")),
        "post_ack_enabled_ok": bool(gate.get("post_ack_enabled_ok")),
        "pm_client_register_rc": intish(gate.get("pm_client_register_rc")),
        "pm_client_connect_rc": intish(gate.get("pm_client_connect_rc")),
        "pm_init_return_path_rc": intish(gate.get("pm_init_return_path_rc")),
        "lower_mdm3_states": gate.get("lower_mdm3_states", ""),
        "lower_service69_progress": bool(gate.get("lower_service69_progress")),
        "lower_wlan0_present": bool(gate.get("lower_wlan0_present")),
    }


def collect_scaffold(manifest: dict[str, Any]) -> dict[str, Any]:
    inputs = ((manifest.get("details") or {}).get("inputs") or {})
    return {
        "path": rel(V1852_MANIFEST),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label", ""),
        "pass": bool(manifest.get("pass")),
        "selection_labels": sorted(set(inputs.get("available_selection_labels") or [])),
        "open_context_labels": sorted(set(inputs.get("available_open_context_labels") or [])),
        "lower_fields": sorted(set(inputs.get("available_lower_fields") or [])),
        "spec": ((manifest.get("details") or {}).get("scaffold_spec") or {}),
    }


def classify(details: dict[str, Any]) -> tuple[str, str, str, bool]:
    image = details["v1846_image"]
    handoff = details["v1847_handoff"]
    scaffold = details["v1852_scaffold"]
    image_ready = (
        image["pass"]
        and image["decision"] == "v1846-pm-service-open-context-source-build-pass"
        and image["source_build_only"]
        and image["boot_image_exists"]
        and image["boot_sha256_ok"]
        and image["helper_marker"] == "a90_android_execns_probe v356"
        and image["safety_clean"]
        and not image["wifi_test_scan_connect_credentials"]
    )
    labels_ready = (
        scaffold["pass"]
        and scaffold["label"] == "sdx50m-bridge-gate-scaffold-dry-run-ready"
        and REQUIRED_SELECTION_LABELS.issubset(set(scaffold["selection_labels"]))
        and REQUIRED_OPEN_CONTEXT_LABELS.issubset(set(scaffold["open_context_labels"]))
        and REQUIRED_LOWER_FIELDS.issubset(set(scaffold["lower_fields"]))
    )
    handoff_proves_labels = (
        handoff["pass"]
        and handoff["safety_ok"]
        and handoff["open_context_registered_ok"]
        and handoff["open_context_enabled_ok"]
        and handoff["post_ack_registered_ok"]
        and handoff["post_ack_enabled_ok"]
        and set(handoff["open_context_hit_keys"]) == REQUIRED_OPEN_CONTEXT_LABELS
        and handoff["pm_client_register_rc"] == 0
        and handoff["pm_client_connect_rc"] == 0
        and handoff["pm_init_return_path_rc"] == 0
        and handoff["open_context_path"] == "/dev/subsys_modem"
        and handoff["lower_mdm3_states"] == "OFFLINING"
        and not handoff["lower_service69_progress"]
        and not handoff["lower_wlan0_present"]
    )
    spec_no_live = (
        scaffold["spec"].get("mode") == "dry-run-only"
        and not bool(scaffold["spec"].get("live_execution_implemented"))
        and not bool(scaffold["spec"].get("wifi_hal_start_executed"))
        and not bool(scaffold["spec"].get("scan_connect_executed"))
        and not bool(scaffold["spec"].get("credential_use_executed"))
        and not bool(scaffold["spec"].get("external_ping_executed"))
        and not bool(scaffold["spec"].get("direct_subsys_esoc0_open_executed"))
    )
    if not image_ready:
        return "image-review", "v1853-image-review", "V1846 bridge-capable test image is missing, changed, or safety-unclean", False
    if not labels_ready:
        return "label-review", "v1853-label-review", "V1852 scaffold labels are incomplete", False
    if not handoff_proves_labels:
        return "handoff-label-review", "v1853-handoff-label-review", "V1847 handoff does not prove labels register/enable and produce baseline values", False
    if not spec_no_live:
        return "dry-run-review", "v1853-dry-run-review", "V1852 scaffold is not dry-run-only", False
    return (
        "bridge-test-image-ready-no-rebuild",
        "v1853-bridge-test-image-ready-no-rebuild-host-pass",
        "The V1846 rollbackable test image already carries the PM register, selection-compare, open-context, and lower-response surfaces needed by the V1852 dry-run scaffold; no helper rebuild is required before a future gated run",
        True,
    )


def render_report(result: dict[str, Any]) -> str:
    image = result["details"]["v1846_image"]
    handoff = result["details"]["v1847_handoff"]
    scaffold = result["details"]["v1852_scaffold"]
    return "\n".join([
        "# Native Init V1853 SDX50M Bridge Image Readiness",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only image readiness classifier for the dry-run SDX50M bridge scaffold",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Image",
        "",
        f"- V1846 decision: `{image['decision']}` / pass `{image['pass']}`",
        f"- boot image: `{image['boot_image']}` exists `{image['boot_image_exists']}`",
        f"- boot SHA: `{image['boot_sha256']}` actual `{image['boot_sha256_actual']}` ok `{image['boot_sha256_ok']}`",
        f"- helper: `{image['helper_marker']}` sha `{image['helper_sha256']}`",
        f"- source-build/safety: `{image['source_build_only']}` / `{image['safety_clean']}`",
        "",
        "## Label Surface",
        "",
        f"- V1852 decision: `{scaffold['decision']}` / `{scaffold['label']}`",
        f"- selection labels: `{scaffold['selection_labels']}`",
        f"- open-context labels: `{scaffold['open_context_labels']}`",
        f"- lower fields: `{scaffold['lower_fields']}`",
        f"- V1847 open-context registered/enabled: `{handoff['open_context_registered_ok']}` / `{handoff['open_context_enabled_ok']}`",
        f"- V1847 open-context hits: `{handoff['open_context_hit_keys']}`",
        f"- V1847 baseline path/lower: `{handoff['open_context_path']}` / `{handoff['lower_mdm3_states']}` / service69 `{handoff['lower_service69_progress']}` / wlan0 `{handoff['lower_wlan0_present']}`",
        "",
        "## Interpretation",
        "",
        "- No helper rebuild is required for the next dry-run bridge step: the existing V1846 image already produced the required V1847 field surface.",
        "- This readiness result does not authorize Wi-Fi connect. It only avoids unnecessary source churn before a future bounded gate.",
        "- Wi-Fi connect and ping remain blocked until WLFW service 69 and `wlan0` are observed first.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- Next candidate is a no-live wrapper around the future SDX50M bridge run contract that can fail closed unless explicitly switched out of dry-run in a later, separately reviewed unit.",
        "",
    ])


def main() -> int:
    details = {
        "v1846_image": collect_image(load_json(V1846_MANIFEST)),
        "v1847_handoff": collect_handoff(load_json(V1847_MANIFEST)),
        "v1852_scaffold": collect_scaffold(load_json(V1852_MANIFEST)),
    }
    label, decision, reason, passed = classify(details)
    result = {
        "cycle": CYCLE,
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "report": rel(REPORT_PATH),
        "details": details,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("decision", "label", "pass", "reason", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
