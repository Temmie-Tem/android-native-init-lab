#!/usr/bin/env python3
"""V764 service180-gated mdm_helper live retry.

V764 deliberately replaces the kernel-source instrumentation plan with a
bounded live retry of the service-notifier 180 gated `mdm_helper` path. It first
classifies V745-V749 evidence, then checks current `mdm_helper` and esoc0
surfaces with read-only stat/list/cat probes. It does not open esoc0 char
devices, write subsystem state, start service-manager/HAL, scan/connect, use
credentials, run DHCP/routes, or external ping.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import native_wifi_mdm_helper_gated_live_v741 as v741
from a90_kernel_tools import capture_to_manifest, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v764-mdm-helper-service180-retry")
DEFAULT_HELPER_SHA256 = "d44cbb538db11a280aa789ccafb008476ac541ec08bb96f549670ae28db7cec6"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v124"
MODE = "wifi-companion-service180-gated-mdm-helper-start-only"
EXPECTED_ORDER = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service180_gate,mdm_helper"
PROOF_PREFIX = "/tmp/a90-v764-"
LATEST_POINTER = Path("tmp/wifi/latest-v764-mdm-helper-service180-retry.txt")

PRIOR_MANIFESTS = {
    "v745": Path("tmp/wifi/v745-mdm-helper-service180-live-current/manifest.json"),
    "v746": Path("tmp/wifi/v746-mdm-helper-sysmon-live-current/manifest.json"),
    "v747": Path("tmp/wifi/v747-qca6390-driver-binding-delta/manifest.json"),
    "v748": Path("tmp/wifi/v748-nonbind-powerup-trigger/manifest.json"),
    "v749": Path("tmp/wifi/v749-nonbind-trigger-selector/manifest.json"),
}

_ORIG_CAPTURE_PREFLIGHT = v741.observer.capture_preflight


def repo_path(path: Path) -> Path:
    return v741.observer.base.repo_path(path)


def load_json_if_exists(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "error": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "error": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def check_detail(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    for check in manifest.get("checks", []):
        if check.get("name") == name and isinstance(check.get("detail"), dict):
            return check["detail"]
    return {}


def prior_summary() -> dict[str, Any]:
    loaded = {name: load_json_if_exists(path) for name, path in PRIOR_MANIFESTS.items()}
    v745_gate = check_detail(loaded["v745"], "service180-gate")
    v746_gate = check_detail(loaded["v746"], "sysmon-gate")
    v746_lower = check_detail(loaded["v746"], "mdm3-wlanpd-mhi-progression")
    return {
        "manifests": {
            name: {
                "path": manifest.get("path"),
                "exists": manifest.get("exists", False),
                "decision": manifest.get("decision", ""),
                "pass": bool(manifest.get("pass")),
                "reason": manifest.get("reason", ""),
                "next_step": manifest.get("next_step", ""),
            }
            for name, manifest in loaded.items()
        },
        "classification": {
            "v745_service180_gate_open": int(v745_gate.get("gate_open") or 0),
            "v745_mdm_helper_started": int(v745_gate.get("mdm_helper_child_started") or 0),
            "v746_sysmon_gate_open": int(v746_gate.get("gate_open") or 0),
            "v746_mdm_helper_started": int(v746_gate.get("mdm_helper_child_started") or 0),
            "v746_lower_markers": v746_lower.get("markers") or {},
            "v747_bind_unbind_rejected": loaded["v747"].get("decision") == "v747-qca-driver-link-gap-not-bind-target",
            "v748_mdm_retry_eliminated": loaded["v748"].get("decision") == "v748-icnss-qmi-wlfw-nonbind-trigger-selected",
            "v749_lower_window_boot_wlan_selected": loaded["v749"].get("decision") == "v749-lower-window-boot-wlan-trigger-selected",
        },
        "interpretation": (
            "V745 did not start mdm_helper because service180 gate stayed closed; "
            "V746 proved mdm_helper can start under sysmon but did not advance lower markers. "
            "V764 therefore retries service180 only after current access surfaces are captured, "
            "and treats repeated no-progress as evidence against mdm_helper as the lower trigger."
        ),
    }


def safe_capture(args: Any,
                 store: EvidenceStore,
                 steps: list[dict[str, Any]],
                 name: str,
                 command: list[str],
                 timeout: float) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = str(store.write_text(f"native/{name}.txt", text))
    item["payload"] = text
    steps.append(item)
    return item


def capture_preflight(args: Any, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    preflight = _ORIG_CAPTURE_PREFLIGHT(args, store, steps)
    safe_capture(args, store, steps, "v764-mdm-helper-global-ls", ["run", args.toybox, "ls", "-lZ", "/vendor/bin/mdm_helper"], 10.0)
    safe_capture(args, store, steps, "v764-mdm-helper-system-ls", ["run", args.toybox, "ls", "-lZ", "/mnt/system/system/vendor/bin/mdm_helper"], 10.0)
    safe_capture(args, store, steps, "v764-esoc-bus-ls", ["run", args.toybox, "ls", "-lZ", "/sys/bus/esoc/devices/esoc0"], 10.0)
    safe_capture(args, store, steps, "v764-esoc-subsys-ls", ["run", args.toybox, "ls", "-lZ", "/sys/class/subsys/subsys_esoc0"], 10.0)
    safe_capture(args, store, steps, "v764-esoc-devnode-ls", ["run", args.toybox, "ls", "-lZ", "/dev/subsys_esoc0"], 10.0)
    safe_capture(
        args,
        store,
        steps,
        "v764-esoc-safe-attrs",
        [
            "run",
            args.busybox,
            "sh",
            "-c",
            f"for f in /sys/bus/esoc/devices/esoc0/esoc_name "
            "/sys/bus/esoc/devices/esoc0/esoc_link "
            "/sys/bus/esoc/devices/esoc0/esoc_link_info "
            "/sys/class/subsys/subsys_esoc0/name "
            "/sys/class/subsys/subsys_esoc0/state; do "
            f"[ -e \"$f\" ] && echo \"--- $f\" && {args.toybox} cat \"$f\" 2>&1; done",
        ],
        10.0,
    )
    return preflight


def payload(base_manifest: dict[str, Any], name: str) -> str:
    for step in base_manifest.get("base_manifest", {}).get("steps", []):
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def access_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    def visible(text: str) -> bool:
        return bool(text.strip()) and "No such file" not in text and "not found" not in text and "[err]" not in text

    global_mdm = payload(manifest, "v764-mdm-helper-global-ls")
    system_mdm = payload(manifest, "v764-mdm-helper-system-ls")
    esoc_bus = payload(manifest, "v764-esoc-bus-ls")
    esoc_subsys = payload(manifest, "v764-esoc-subsys-ls")
    esoc_devnode = payload(manifest, "v764-esoc-devnode-ls")
    esoc_attrs = payload(manifest, "v764-esoc-safe-attrs")
    return {
        "mdm_helper_global_visible": visible(global_mdm),
        "mdm_helper_system_visible": visible(system_mdm),
        "esoc_bus_visible": visible(esoc_bus),
        "esoc_subsys_visible": visible(esoc_subsys),
        "esoc_devnode_visible": visible(esoc_devnode),
        "esoc_safe_attrs_visible": bool(esoc_attrs.strip()),
        "esoc_devnode_open_executed": False,
        "esoc_hold_executed": False,
        "subsystem_write_executed": False,
    }


def configure_v741_adapter() -> None:
    v741.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    v741.DEFAULT_HELPER_SHA256 = DEFAULT_HELPER_SHA256
    v741.DEFAULT_HELPER_MARKER = DEFAULT_HELPER_MARKER
    v741.MODE = MODE
    v741.EXPECTED_ORDER = EXPECTED_ORDER
    v741.PROOF_PREFIX = PROOF_PREFIX
    v741.LATEST_POINTER = LATEST_POINTER
    v741.configure_observer()
    v741.observer.capture_preflight = capture_preflight


def retag_manifest(manifest: dict[str, Any]) -> None:
    manifest["cycle"] = "v764"
    manifest["adapter"] = "native_wifi_mdm_helper_service180_retry_v764.py"
    manifest["mode"] = MODE
    manifest["expected_order"] = EXPECTED_ORDER
    for key in ("decision", "reason", "next_step"):
        value = str(manifest.get(key, ""))
        manifest[key] = (
            value.replace("v741", "v764")
            .replace("V741", "V764")
            .replace("service74", "service180")
            .replace("v122", "v124")
            .replace("helper v122", "helper v124")
        )
    if manifest["decision"] == "v764-mdm-helper-started-no-lower-progress":
        manifest["next_step"] = "treat mdm_helper retry as insufficient unless service180/esoc access evidence changes the lower-trigger model"
    for check in manifest.get("checks", []):
        if not isinstance(check, dict):
            continue
        if check.get("name") == "service74-gate":
            check["name"] = "service180-gate"
        if isinstance(check.get("next_step"), str):
            check["next_step"] = check["next_step"].replace("service74", "service180")


def render_summary(manifest: dict[str, Any]) -> str:
    text = v741.render_summary(manifest)
    prior = manifest.get("v764_prior_evidence") or {}
    access = manifest.get("v764_access") or {}
    extra = "\n".join([
        "",
        "## V764 Prior Evidence Classification",
        "",
        v741.observer.base.markdown_table(["item", "value"], [
            [key, value] for key, value in (prior.get("classification") or {}).items()
        ]),
        "",
        "## V764 Access Surface",
        "",
        v741.observer.base.markdown_table(["item", "value"], [[key, value] for key, value in access.items()]),
    ])
    return (
        text.replace("# V741 Gated MDM Helper Live Proof", "# V764 Service180-gated MDM Helper Retry")
        .replace("service74_gate_open", "service180_gate_open")
        .replace("V741", "V764")
        .replace("service74", "service180")
        + extra
    )


def main() -> int:
    configure_v741_adapter()
    args = v741.parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    prior = prior_summary()
    manifest = v741.build_manifest(args, store)
    retag_manifest(manifest)
    manifest["v764_prior_evidence"] = prior
    manifest["v764_access"] = access_summary(manifest) if args.command == "run" else {
        "not_executed": "plan-only",
        "esoc_devnode_open_executed": False,
        "esoc_hold_executed": False,
        "subsystem_write_executed": False,
    }
    manifest["esoc0_open_executed"] = False
    manifest["esoc0_hold_executed"] = False
    manifest["subsystem_writes_executed"] = False
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path(Path(".")))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"mdm_helper_start_executed: {manifest['mdm_helper_start_executed']}")
    print(f"esoc0_open_executed: {manifest['esoc0_open_executed']}")
    print(f"service_manager_start_executed: {manifest['service_manager_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
