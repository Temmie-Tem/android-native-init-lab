#!/usr/bin/env python3
"""V832 host-only route classifier after V831 service-notifier result.

V829 already proved the service-locator `wlan/fw` domain list is populated and
V830/V831 already proved the service-notifier listener can be registered for
`msm/modem/wlan_pd`, but native still reports the domain state as `uninit`.
This classifier reconciles those results with earlier rejected trigger paths so
the next gate does not repeat old experiments.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v832-post-v831-route-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v832-post-v831-route-classifier.txt")

INPUTS = {
    "v750": Path("tmp/wifi/v750-lower-window-boot-wlan/manifest.json"),
    "v752": Path("tmp/wifi/v752-cnss-then-boot-wlan/manifest.json"),
    "v764": Path("tmp/wifi/v764-mdm-helper-service180-retry/manifest.json"),
    "v775": Path("tmp/wifi/v775-boot-incompat-postmortem/manifest.json"),
    "v817": Path("tmp/wifi/v817-in-window-sysmon-sampler/manifest.json"),
    "v818": Path("tmp/wifi/v818-mdm3-esoc-registration-classifier/manifest.json"),
    "v819": Path("tmp/wifi/v819-mdm3-esoc-registration-catalogue/manifest.json"),
    "v826": Path("tmp/wifi/v826-qrtr-event-detail-classifier/manifest.json"),
    "v829": Path("tmp/wifi/v829-servloc-domain-list-probe-retry-20260525-113735/manifest.json"),
    "v830": Path("tmp/wifi/v830-service-notifier-listener-run-20260525-115840/manifest.json"),
    "v831": Path("tmp/wifi/v831-service-notifier-early-listener-run-20260525-121658/manifest.json"),
}

REPORTS = {
    "v750": Path("docs/reports/NATIVE_INIT_V750_LOWER_WINDOW_BOOT_WLAN_2026-05-24.md"),
    "v752": Path("docs/reports/NATIVE_INIT_V752_CNSS_THEN_BOOT_WLAN_2026-05-24.md"),
    "v764": Path("docs/reports/NATIVE_INIT_V764_SERVICE180_MDM_HELPER_RETRY_2026-05-24.md"),
    "v775": Path("docs/reports/NATIVE_INIT_V775_BOOT_INCOMPAT_POSTMORTEM_2026-05-25.md"),
    "v817": Path("docs/reports/NATIVE_INIT_V817_IN_WINDOW_SYSMON_SAMPLER_2026-05-25.md"),
    "v818": Path("docs/reports/NATIVE_INIT_V818_MDM3_ESOC_REGISTRATION_CLASSIFIER_2026-05-25.md"),
    "v819": Path("docs/reports/NATIVE_INIT_V819_MDM3_ESOC_REGISTRATION_CATALOGUE_2026-05-25.md"),
    "v826": Path("docs/reports/NATIVE_INIT_V826_QRTR_EVENT_DETAIL_CLASSIFIER_2026-05-25.md"),
    "v829": Path("docs/reports/NATIVE_INIT_V829_SERVLOC_DOMAIN_LIST_PROBE_2026-05-25.md"),
    "v830": Path("docs/reports/NATIVE_INIT_V830_SERVICE_NOTIFIER_LISTENER_PROBE_2026-05-25.md"),
    "v831": Path("docs/reports/NATIVE_INIT_V831_EARLY_SERVICE_NOTIFIER_LISTENER_2026-05-25.md"),
}

EXPECTED_DECISIONS = {
    "v750": "v750-lower-window-boot-wlan-control-surface-only",
    "v752": "v752-cnss-then-boot-wlan-hdd-init-still-stalls",
    "v764": "v764-mdm-helper-started-no-lower-progress",
    "v775": "v775-non-dtb-custom-kernel-incompat-classified",
    "v817": "v817-in-window-mdm3-service-gap-confirmed",
    "v818": "v818-mdm3-esoc-registration-gap-classified",
    "v819": "v819-mdm3-esoc-registration-catalogue-captured",
    "v826": "v826-qrtr-event-details-classified",
    "v829": "v829-servloc-domain-list-response-success",
    "v830": "v830-service-notifier-listener-state-not-up",
    "v831": "v831-service-notifier-early-listener-state-not-up",
}


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


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
    data["exists"] = True
    data["path"] = str(resolved)
    return data


def int_value(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(str(value), 0)
    except ValueError:
        return default


def input_summary(inputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        name: {
            "path": item.get("path"),
            "exists": item.get("exists", False),
            "decision": item.get("decision", ""),
            "pass": bool(item.get("pass")),
            "reason": item.get("reason", ""),
            "next_step": item.get("next_step", ""),
        }
        for name, item in inputs.items()
    }


def report_summary() -> dict[str, dict[str, Any]]:
    return {
        name: {
            "path": str(repo_path(path)),
            "exists": repo_path(path).exists(),
        }
        for name, path in REPORTS.items()
    }


def nested(manifest: dict[str, Any], *keys: str) -> Any:
    value: Any = manifest
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def get_v829_domain(v829: dict[str, Any]) -> dict[str, Any]:
    servloc = nested(v829, "live", "servloc")
    if not isinstance(servloc, dict):
        servloc = {}
    domains = servloc.get("domains") if isinstance(servloc.get("domains"), list) else []
    first_domain = domains[0] if domains and isinstance(domains[0], dict) else {}
    return {
        "domain_count": int_value(servloc.get("domain_count")),
        "total_domains": int_value(servloc.get("total_domains")),
        "wlan_like_domains": int_value(servloc.get("wlan_like_domains")),
        "name": first_domain.get("name", ""),
        "instance_id": int_value(first_domain.get("instance_id")),
        "qmi_result": int_value(servloc.get("qmi_result"), -1),
        "qmi_error": int_value(servloc.get("qmi_error"), -1),
    }


def get_listener(manifest: dict[str, Any]) -> dict[str, Any]:
    listener = nested(manifest, "live", "service_notifier")
    if not isinstance(listener, dict):
        listener = {}
    return {
        "endpoint_found": int_value(listener.get("endpoint_found")),
        "endpoint_node": int_value(listener.get("endpoint_node"), -1),
        "endpoint_port": int_value(listener.get("endpoint_port"), -1),
        "service": int_value(listener.get("service")),
        "instance": int_value(listener.get("instance")),
        "service_name": listener.get("service_name", ""),
        "register_send_rc": int_value(listener.get("register_send_rc"), -1),
        "response_success": int_value(listener.get("response_success")),
        "register_response_qmi_result": int_value(listener.get("register_response_qmi_result"), -1),
        "register_response_qmi_error": int_value(listener.get("register_response_qmi_error"), -1),
        "response_curr_state": listener.get("response_curr_state", ""),
        "response_curr_state_name": listener.get("response_curr_state_name", ""),
        "indication_seen": int_value(listener.get("indication_seen")),
        "indication_curr_state_name": listener.get("indication_curr_state_name", ""),
    }


def matrix_row(label: str, classification: str, reason: str, next_step: str) -> dict[str, str]:
    return {
        "candidate": label,
        "classification": classification,
        "reason": reason,
        "next_step": next_step,
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    inputs = {name: load_json(path) for name, path in INPUTS.items()}
    v829_domain = get_v829_domain(inputs["v829"])
    v830_listener = get_listener(inputs["v830"])
    v831_listener = get_listener(inputs["v831"])

    v829_domain_ready = (
        v829_domain["qmi_result"] == 0
        and v829_domain["qmi_error"] == 0
        and v829_domain["name"] == "msm/modem/wlan_pd"
        and v829_domain["instance_id"] == 180
    )
    v830_registered_uninit = (
        v830_listener["endpoint_found"] == 1
        and (
            v830_listener["response_success"] == 1
            or (
                v830_listener["register_response_qmi_result"] == 0
                and v830_listener["register_response_qmi_error"] == 0
            )
        )
        and v830_listener["response_curr_state_name"] == "uninit"
    )
    v831_registered_uninit = (
        v831_listener["endpoint_found"] == 1
        and (
            v831_listener["response_success"] == 1
            or (
                v831_listener["register_response_qmi_result"] == 0
                and v831_listener["register_response_qmi_error"] == 0
            )
        )
        and v831_listener["response_curr_state_name"] == "uninit"
        and v831_listener["indication_seen"] == 0
    )

    candidate_matrix = [
        matrix_row(
            "repeat V829 service-locator domain-list",
            "reject",
            "V829 already returned msm/modem/wlan_pd instance 180; pd-mapper DB is not empty",
            "do not resend GET_DOMAIN_LIST unless service-locator evidence changes",
        ),
        matrix_row(
            "repeat V830/V831 listener timing",
            "reject",
            "late and early listener windows both register successfully but return current state uninit",
            "classify why Android reaches state-up before another identical native listener probe",
        ),
        matrix_row(
            "repeat boot_wlan or qcwlanstate",
            "reject",
            "V750/V752 already reach only the HDD/qcwlanstate control surface without WLFW/BDF/wlan0",
            "keep boot_wlan gated until a lower state-up signal appears",
        ),
        matrix_row(
            "repeat mdm_helper",
            "reject",
            "V764 started mdm_helper below service180 and still left mdm3/WLAN-PD/WLFW unchanged",
            "do not retry mdm_helper unless esoc or service180 contract evidence changes",
        ),
        matrix_row(
            "raw esoc0 open, subsystem write, bind/unbind, module load",
            "forbidden",
            "existing safety policy and V764/V818 keep this class outside the current safe gate",
            "require a separate safety proof before considering any of these actions",
        ),
        matrix_row(
            "custom OSRC diagnostic kernel flash",
            "paused",
            "V775 classified stock-vs-OSRC boot incompatibility after V771/V774 failures",
            "resume only after a host-only compatibility contract exists",
        ),
        matrix_row(
            "service-manager, Wi-Fi HAL, scan/connect, DHCP, external ping",
            "blocked",
            "WLAN-PD state-up, WLFW service69, BDF, wiphy, and wlan0 are still absent",
            "keep final Wi-Fi bring-up above the current blocker",
        ),
        matrix_row(
            "Android service-notifier positive control",
            "select-next",
            "native can register the listener but sees uninit; the missing comparison is the same bounded query on the Android-success reference",
            "V833 should prove expected current_state/indication for msm/modem/wlan_pd on Android or explain a payload/model mismatch",
        ),
    ]

    return {
        "inputs": input_summary(inputs),
        "reports": report_summary(),
        "signals": {
            "v829_domain": v829_domain,
            "v830_listener": v830_listener,
            "v831_listener": v831_listener,
            "v817_lower_window": {
                "decision": inputs["v817"].get("decision", ""),
                "reason": inputs["v817"].get("reason", ""),
            },
        },
        "derived": {
            "v829_domain_ready": v829_domain_ready,
            "v830_registered_uninit": v830_registered_uninit,
            "v831_registered_uninit": v831_registered_uninit,
            "listener_timing_repetition_closed": v830_registered_uninit and v831_registered_uninit,
            "pd_mapper_db_empty_hypothesis_closed": v829_domain_ready,
            "next_gate": "v833-android-service-notifier-positive-control",
        },
        "candidate_matrix": candidate_matrix,
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(analysis: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    inputs = analysis["inputs"]
    for name, expected in EXPECTED_DECISIONS.items():
        item = inputs[name]
        add_check(
            checks,
            f"{name}-input",
            "pass" if item.get("exists") and item.get("pass") and item.get("decision") == expected else "blocked",
            "blocker",
            f"decision={item.get('decision')} pass={item.get('pass')} expected={expected}",
            f"refresh {name} evidence before using V832 route selection",
        )

    derived = analysis["derived"]
    add_check(
        checks,
        "v829-domain-ready",
        "pass" if derived["v829_domain_ready"] else "blocked",
        "blocker",
        f"domain={analysis['signals']['v829_domain']}",
        "complete service-locator domain proof before continuing",
    )
    add_check(
        checks,
        "v830-listener-uninit",
        "pass" if derived["v830_registered_uninit"] else "blocked",
        "blocker",
        f"listener={analysis['signals']['v830_listener']}",
        "complete late-window listener proof before comparing timing",
    )
    add_check(
        checks,
        "v831-early-listener-uninit",
        "pass" if derived["v831_registered_uninit"] else "blocked",
        "blocker",
        f"listener={analysis['signals']['v831_listener']}",
        "complete early-window listener proof before closing timing hypothesis",
    )
    add_check(
        checks,
        "host-only-boundary",
        "pass",
        "blocker",
        "V832 reads only local manifests/reports and writes private evidence",
        "keep V832 host-only",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v832-post-v831-route-classifier-plan-ready",
            True,
            "plan-only; no device command, QMI payload, daemon, Wi-Fi action, or flash executed",
            "run V832 host-only classifier",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v832-post-v831-route-classifier-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "refresh missing prerequisite evidence before selecting the next Wi-Fi gate",
        )
    return (
        "v832-android-service-notifier-positive-control-selected",
        True,
        "V829 is complete and V830/V831 close native listener timing; the next missing proof is the Android-success state for the same service-notifier request",
        "V833 should perform or plan an Android reference positive-control for msm/modem/wlan_pd listener state before more native retries",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    return "\n".join([
        "# V832 Post-V831 Route Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- qmi_payload_executed: `{manifest['qmi_payload_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Derived Signals",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in analysis["derived"].items()]),
        "",
        "## Candidate Matrix",
        "",
        markdown_table(["candidate", "classification", "reason", "next"], [
            [row["candidate"], row["classification"], row["reason"], row["next_step"]]
            for row in analysis["candidate_matrix"]
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = classify(args)
    checks = build_checks(analysis)
    decision, ok, reason, next_step = decide(args.command, checks)
    manifest: dict[str, Any] = {
        "cycle": "v832",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "qmi_payload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "esoc0_open_executed": False,
        "subsystem_write_executed": False,
        "module_load_unload_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path(Path(".")))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"qmi_payload_executed: {manifest['qmi_payload_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
