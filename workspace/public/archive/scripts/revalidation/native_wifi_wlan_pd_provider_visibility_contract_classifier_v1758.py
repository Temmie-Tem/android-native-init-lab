#!/usr/bin/env python3
"""V1758 host-only provider visibility contract classifier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_V1757 = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1757-wlan-pd-peripheral-interface-branch-classifier"
    / "manifest.json"
)
DEFAULT_V1092 = REPO_ROOT / "tmp" / "wifi" / "v1092-pm-observer-provider-ready-live" / "manifest.json"
DEFAULT_V1087 = REPO_ROOT / "tmp" / "wifi" / "v1087-pm-addservice-host-classifier" / "manifest.json"
DEFAULT_V1101 = (
    REPO_ROOT / "tmp" / "wifi" / "v1101-pm-server-register-path-tracefs-live" / "manifest.json"
)
DEFAULT_V1736 = (
    REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"
)
DEFAULT_V1686 = REPO_ROOT / "tmp" / "wifi" / "v1686-wlan-pd-pm-trio-handoff" / "manifest.json"
DEFAULT_V1736_HELPER = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1736-wlan-pd-timestamped-observer-handoff"
    / "test-v1393-helper-result.stdout.txt"
)
DEFAULT_V1686_HELPER = (
    REPO_ROOT / "tmp" / "wifi" / "v1686-wlan-pd-pm-trio-handoff" / "test-v1393-helper-result.stdout.txt"
)
DEFAULT_PM_SERVICE = REPO_ROOT / "tmp" / "wifi" / "v1073-host-only" / "vendor-extract" / "files" / "pm-service"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1758-wlan-pd-provider-visibility-contract-classifier"
DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1758_WLAN_PD_PROVIDER_VISIBILITY_CONTRACT_CLASSIFIER_2026-06-03.md"
)


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path, limit: int = 8_000_000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip()
    return values


def nested(data: dict[str, Any], path: str, default: Any = None) -> Any:
    value: Any = data
    parts = path.split(".")
    for index, part in enumerate(parts):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, dict):
            remainder = ".".join(parts[index:])
            return value.get(remainder, default)
        else:
            return default
    return value


def str_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def str_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value or str(default)), 0)
    except ValueError:
        return default


def collect_pm_service_surface(path: Path) -> dict[str, Any]:
    data = path.read_bytes() if path.exists() else b""
    text = data.decode("latin-1", errors="ignore")
    literals = {
        "vendor_qcom_peripheral_manager": "vendor.qcom.PeripheralManager" in text,
        "dev_vndbinder": "/dev/vndbinder" in text,
        "libbinder": "libbinder.so" in text,
        "libperipheral_client": "libperipheral_client.so" in text,
        "qmi_service_start": "QMI service start" in text,
        "vendor_peripheral_prefix": "vendor.peripheral." in text,
    }
    return {
        "path": display_path(path),
        "exists": path.exists(),
        "size": path.stat().st_size if path.exists() else 0,
        "literals": literals,
    }


def collect_v1736(manifest: dict[str, Any], helper_path: Path) -> dict[str, Any]:
    keys = parse_key_values(read_text(helper_path))
    gate = manifest.get("gate") or {}
    return {
        "manifest_decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "helper": display_path(helper_path),
        "order": keys.get("wifi_companion_start.order", ""),
        "with_service_manager": keys.get("wifi_companion_start.with_service_manager", ""),
        "with_vnd_service_manager": keys.get("wifi_companion_start.with_vnd_service_manager", ""),
        "vndservicemanager_argv": keys.get("wifi_companion_start.vndservicemanager_argv", ""),
        "vndservicemanager_readiness_enabled": keys.get("wifi_companion_start.vndservicemanager_readiness.enabled", ""),
        "peripheral_manager_enabled": keys.get("wifi_companion_start.peripheral_manager.enabled", ""),
        "vndservice_query_enabled": keys.get("wifi_companion_start.vndservice_query.enabled", ""),
        "wlfw_start_seen": gate.get("wlfw_start_seen"),
        "wlfw_service_request_hit_count": gate.get("wlfw_service_request_hit_count"),
        "requested_wlanmdsp": gate.get("requested_wlanmdsp"),
        "service_window_label": gate.get("service_window_label"),
    }


def collect_v1686(manifest: dict[str, Any], helper_path: Path) -> dict[str, Any]:
    keys = parse_key_values(read_text(helper_path))
    gate = manifest.get("gate") or {}
    return {
        "manifest_decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "helper": display_path(helper_path),
        "order": keys.get("wifi_companion_start.order", ""),
        "vndservicemanager_readiness_enabled": keys.get("wifi_companion_start.vndservicemanager_readiness.enabled", ""),
        "vndservice_query_enabled": keys.get("wifi_companion_start.vndservice_query.enabled", ""),
        "per_mgr_running": gate.get("per_mgr_running"),
        "per_proxy_running": gate.get("per_proxy_running"),
        "wlfw_service_request_seen": gate.get("wlfw_service_request_seen"),
        "requested_wlanmdsp": gate.get("requested_wlanmdsp"),
        "label": keys.get("wlan_pd_pm_service_window_trigger.label", ""),
    }


def collect_v1092(manifest: dict[str, Any]) -> dict[str, Any]:
    contract = nested(manifest, "analysis.helper.contract", {})
    return {
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "provider_seen": str_bool(nested(manifest, "analysis.helper.vndservice_provider_seen")),
        "vndservicemanager_ready": str_bool(contract.get("vndservicemanager_readiness.ready")),
        "vndservicemanager_ready_enabled": str_bool(contract.get("vndservicemanager_readiness.enabled")),
        "policy_load_required": str_bool(contract.get("policy_load_precondition.required")),
        "order": contract.get("order", ""),
        "vndservice_query_enabled": str_bool(contract.get("vndservice_query.enabled")),
        "pm_service_start_executed": bool(manifest.get("pm_service_start_executed")),
        "scan_connect_executed": bool(manifest.get("scan_connect_executed")),
        "external_ping_executed": bool(manifest.get("external_ping_executed")),
    }


def collect_v1087(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "policy_delta": bool(nested(manifest, "classification.policy_delta")),
        "readiness_delta": bool(nested(manifest, "classification.readiness_delta")),
        "v1086_add_service_call": str_int(nested(manifest, "v1086.add_service_call")),
        "v1086_add_service_fail_log": str_int(nested(manifest, "v1086.add_service_fail_log")),
        "v694_provider_exact_match": bool(nested(manifest, "v694_positive_control.provider_exact_match")),
        "v694_vndservicemanager_ready": bool(nested(manifest, "v694_positive_control.vndservicemanager_ready")),
        "v694_policy_load_pass": bool(nested(manifest, "v694_positive_control.policy_load_pass")),
    }


def collect_v1101(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "provider_seen": str_bool(nested(manifest, "analysis.tracefs_uprobe.pm_contract.vndservice_provider_seen")),
        "vndservicemanager_ready": str_bool(
            nested(manifest, "analysis.tracefs_uprobe.pm_contract.vndservicemanager_readiness.ready")
        ),
        "cnss_client_register_entry": str_int(
            nested(manifest, "analysis.tracefs_uprobe.by_label_comm.pm_client_register_entry.cnss-daemon")
        ),
        "cnss_server_register_entry": str_int(
            nested(manifest, "analysis.tracefs_uprobe.pm_server_hits_by_comm.Binder:2193_3.pm_server_register_entry")
        ),
        "pm_server_register_success_return": str_int(
            nested(manifest, "analysis.tracefs_uprobe.counts.pm_server_register_success_return")
        ),
        "pm_client_connect_ret": str_int(nested(manifest, "analysis.tracefs_uprobe.counts.pm_client_connect_ret")),
    }


def classify(collected: dict[str, Any]) -> tuple[str, bool, str, str]:
    v1757 = collected["v1757"]
    v1092 = collected["v1092"]
    v1087 = collected["v1087"]
    v1101 = collected["v1101"]
    v1736 = collected["v1736"]
    v1686 = collected["v1686"]
    pm_service = collected["pm_service"]

    v1757_null_service = v1757.get("label") == "peripheral-manager-service-object-null" and bool(v1757.get("pass"))
    v1092_provider_positive = (
        v1092["provider_seen"]
        and v1092["vndservicemanager_ready"]
        and v1092["policy_load_required"]
        and v1092["vndservice_query_enabled"]
    )
    v1087_preconditions_known = (
        v1087["policy_delta"]
        and v1087["readiness_delta"]
        and v1087["v1086_add_service_fail_log"] > 0
        and v1087["v694_provider_exact_match"]
        and v1087["v694_vndservicemanager_ready"]
        and v1087["v694_policy_load_pass"]
    )
    v1101_provider_and_cnss_register_meet = (
        v1101["provider_seen"]
        and v1101["vndservicemanager_ready"]
        and v1101["cnss_client_register_entry"] > 0
        and v1101["cnss_server_register_entry"] > 0
    )
    v1736_wlfw_without_provider = (
        str_bool(v1736["pass"])
        and str_int(v1736["wlfw_service_request_hit_count"]) > 0
        and str_int(v1736["requested_wlanmdsp"]) == 0
        and str_int(v1736["peripheral_manager_enabled"]) == 0
        and str_int(v1736["vndservice_query_enabled"]) == 0
        and str_int(v1736["vndservicemanager_readiness_enabled"]) == 0
    )
    v1686_actor_march_not_enough = (
        str_bool(v1686["pass"])
        and str_int(v1686["per_mgr_running"]) > 0
        and str_int(v1686["per_proxy_running"]) > 0
        and str_int(v1686["wlfw_service_request_seen"]) == 0
        and str_int(v1686["requested_wlanmdsp"]) == 0
        and str_int(v1686["vndservice_query_enabled"]) == 0
    )
    pm_service_contract_present = all(pm_service["literals"].values())

    if (
        v1757_null_service
        and v1092_provider_positive
        and v1087_preconditions_known
        and v1101_provider_and_cnss_register_meet
        and v1736_wlfw_without_provider
        and v1686_actor_march_not_enough
        and pm_service_contract_present
    ):
        return (
            "v1758-provider-positive-contract-not-composed-with-wlfw-route-host-pass",
            True,
            "V1757 proves V1736 sees a null PeripheralManager service object; V1092/V1087 prove the provider requires policy-load plus explicit vndservicemanager readiness/query; V1101 proves provider-positive PM register can reach pm-service; V1736 reaches WLFW without that provider-positive contract, while V1686's broad actor march regresses WLFW",
            "compose-provider-positive-vndservice-gate-before-cnss-pm-register",
        )

    return (
        "v1758-provider-visibility-contract-incomplete",
        False,
        "Existing PM provider and WLFW-route evidence did not match the supported composition-gap classification",
        "incomplete",
    )


def render_report(result: dict[str, Any]) -> str:
    c = result["collected"]
    return "\n".join([
        "# Native Init V1758 WLAN-PD Provider Visibility Contract Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1758`",
        "- Type: host-only provider visibility contract classifier",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Inputs",
        "",
        "| Input | Decision / State | Key Facts |",
        "| --- | --- | --- |",
        f"| V1757 | `{c['v1757'].get('decision')}` | label `{c['v1757'].get('label')}`: V1736 `getService(\"vendor.qcom.PeripheralManager\")` returns null |",
        f"| V1092 | `{c['v1092']['decision']}` | provider_seen=`{c['v1092']['provider_seen']}`, vndservicemanager_ready=`{c['v1092']['vndservicemanager_ready']}`, query=`{c['v1092']['vndservice_query_enabled']}` |",
        f"| V1087 | `{c['v1087']['decision']}` | addService failure without readiness/policy, provider-positive with V490 + readiness |",
        f"| V1101 | `{c['v1101']['decision']}` | provider_seen=`{c['v1101']['provider_seen']}`, CNSS client/server register entries `{c['v1101']['cnss_client_register_entry']}`/`{c['v1101']['cnss_server_register_entry']}` |",
        f"| V1736 | `{c['v1736']['manifest_decision']}` | WLFW request hits `{c['v1736']['wlfw_service_request_hit_count']}`, provider enabled/query/readiness `{c['v1736']['peripheral_manager_enabled']}`/`{c['v1736']['vndservice_query_enabled']}`/`{c['v1736']['vndservicemanager_readiness_enabled']}` |",
        f"| V1686 | `{c['v1686']['manifest_decision']}` | PM actors running `{c['v1686']['per_mgr_running']}`/`{c['v1686']['per_proxy_running']}`, WLFW request `{c['v1686']['wlfw_service_request_seen']}`, query `{c['v1686']['vndservice_query_enabled']}` |",
        "",
        "## pm-service Static Surface",
        "",
        f"- Path: `{c['pm_service']['path']}`",
        f"- Exists/size: `{c['pm_service']['exists']}` / `{c['pm_service']['size']}`",
        "",
        "| Literal / Dependency | Present |",
        "| --- | ---: |",
        *[
            f"| `{name}` | `{present}` |"
            for name, present in c["pm_service"]["literals"].items()
        ],
        "",
        "## Interpretation",
        "",
        "- The missing object in V1757 is not an unknown `libperipheral_client.so` branch anymore. It is a missing visible provider object.",
        "- V1092 proves `pm-service` can register `vendor.qcom.PeripheralManager` when V490 policy-load and explicit `vndservicemanager_ready`/`vndservice list` gating are present.",
        "- V1087 explains why earlier attempts failed: `addService` was sensitive to the policy/readiness preconditions.",
        "- V1101 proves a provider-positive namespace can carry CNSS PM register traffic into `pm-service`.",
        "- V1736 is the route that reaches `wlfw_start`/`wlfw_service_request`, but it explicitly has `peripheral_manager.enabled=0`, `vndservice_query.enabled=0`, and `vndservicemanager_readiness.enabled=0`.",
        "- V1686 proves that simply adding PM actors is not enough; that broad actor march regresses the WLFW worker and still does not request `wlanmdsp.mbn`.",
        "",
        "## Next Candidate",
        "",
        "- V1759 should be source/build-only first: compose the V1092 provider-positive contract into the V1736 internal-modem/WLFW route.",
        "- Minimum intended order: service managers -> explicit `vndservicemanager_ready` -> `pm_proxy_helper`/`per_mgr` -> `vndservice list` provider proof -> internal modem firmware/tftp/CNSS route -> CNSS PM register/WLFW observer.",
        "- Success criterion for the next live gate is not actor presence. It must observe non-null PeripheralManager lookup or PM register/transaction progress, then measure whether `wlanmdsp.mbn` is requested.",
        "- Keep blocked: broad PM actor march, eSoC/RC1, `/dev/subsys_esoc0`, `boot_wlan`, restart-PD, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping until `wlanmdsp.mbn` request or WLFW service 69 appears.",
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It reads retained manifests, retained helper transcripts, and a staged `pm-service` binary. It performs no device contact, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware/partition write, or new actor start.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1757-manifest", type=Path, default=DEFAULT_V1757)
    parser.add_argument("--v1092-manifest", type=Path, default=DEFAULT_V1092)
    parser.add_argument("--v1087-manifest", type=Path, default=DEFAULT_V1087)
    parser.add_argument("--v1101-manifest", type=Path, default=DEFAULT_V1101)
    parser.add_argument("--v1736-manifest", type=Path, default=DEFAULT_V1736)
    parser.add_argument("--v1686-manifest", type=Path, default=DEFAULT_V1686)
    parser.add_argument("--v1736-helper", type=Path, default=DEFAULT_V1736_HELPER)
    parser.add_argument("--v1686-helper", type=Path, default=DEFAULT_V1686_HELPER)
    parser.add_argument("--pm-service", type=Path, default=DEFAULT_PM_SERVICE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    v1757 = load_json(args.v1757_manifest)
    collected = {
        "v1757": {
            "manifest": display_path(args.v1757_manifest),
            "decision": v1757.get("decision"),
            "label": v1757.get("label"),
            "pass": bool(v1757.get("pass")),
        },
        "v1092": collect_v1092(load_json(args.v1092_manifest)),
        "v1087": collect_v1087(load_json(args.v1087_manifest)),
        "v1101": collect_v1101(load_json(args.v1101_manifest)),
        "v1736": collect_v1736(load_json(args.v1736_manifest), args.v1736_helper),
        "v1686": collect_v1686(load_json(args.v1686_manifest), args.v1686_helper),
        "pm_service": collect_pm_service_surface(args.pm_service),
    }
    decision, pass_ok, reason, label = classify(collected)
    result = {
        "cycle": "V1758",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "label": label,
        "collected": collected,
        "out_dir": display_path(args.out_dir),
        "report_path": display_path(args.report_path),
        "safety": {
            "host_only": True,
            "device_contact": False,
            "flash": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credentials": False,
            "dhcp_routes": False,
            "external_ping": False,
        },
    }
    store.write_json("manifest.json", result)
    report = render_report(result)
    write_private_text(store.path("summary.md"), report)
    write_private_text(args.report_path, report)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
