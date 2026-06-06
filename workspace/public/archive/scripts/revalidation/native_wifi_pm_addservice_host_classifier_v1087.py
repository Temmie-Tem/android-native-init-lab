#!/usr/bin/env python3
"""V1087 host-only PM-service addService blocker classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1087-pm-addservice-host-classifier")
DEFAULT_V1086_MANIFEST = Path("tmp/wifi/v1086-pm-service-success-path-trace-live/manifest.json")
DEFAULT_V1086_TRANSCRIPT = Path(
    "tmp/wifi/v1086-pm-service-success-path-trace-live/host/pm-service-tracefs-uprobe-observer.txt"
)
DEFAULT_V694_MANIFEST = Path("tmp/wifi/v694-peripheral-vndservice-query-orchestrated-live-rerun/manifest.json")
DEFAULT_V1072_TRANSCRIPT = Path(
    "tmp/wifi/v1072-pm-observer-pm-actor-exit-fd-trace-v192-live/host/pm-service-trigger-observer.txt"
)
LATEST_POINTER = Path("tmp/wifi/latest-v1087-pm-addservice-host-classifier.txt")

KEY_VALUE_RE = re.compile(r"^([A-Za-z0-9_.-]+)=(.*)$")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def repo_path(path: Path | str) -> Path:
    path = Path(path)
    return path if path.is_absolute() else Path.cwd() / path


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = KEY_VALUE_RE.match(line.strip())
        if match:
            values[match.group(1)] = match.group(2)
    return values


def nested_get(payload: dict[str, Any], keys: tuple[str, ...], default: Any = "") -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def extract_v1086(v1086: dict[str, Any], transcript_values: dict[str, str]) -> dict[str, Any]:
    tracefs = nested_get(v1086, ("analysis", "tracefs_uprobe"), {})
    counts = tracefs.get("counts") if isinstance(tracefs, dict) else {}
    counts = counts if isinstance(counts, dict) else {}
    pm_contract = tracefs.get("pm_contract") if isinstance(tracefs, dict) else {}
    pm_contract = pm_contract if isinstance(pm_contract, dict) else {}
    return {
        "decision": v1086.get("decision", ""),
        "pass": bool(v1086.get("pass")),
        "reason": v1086.get("reason", ""),
        "order": pm_contract.get("order") or transcript_values.get("pm_service_trigger_observer.order", ""),
        "per_mgr_exit_code": pm_contract.get("child.per_mgr.exit_code")
        or transcript_values.get("pm_service_trigger_observer.child.per_mgr.exit_code", ""),
        "per_mgr_signal": pm_contract.get("child.per_mgr.signal")
        or transcript_values.get("pm_service_trigger_observer.child.per_mgr.signal", ""),
        "per_mgr_observable": pm_contract.get("child.per_mgr.observable")
        or transcript_values.get("pm_service_trigger_observer.child.per_mgr.observable", ""),
        "vndservicemanager_signal": pm_contract.get("child.vndservicemanager.signal")
        or transcript_values.get("pm_service_trigger_observer.child.vndservicemanager.signal", ""),
        "observer_result": pm_contract.get("result") or transcript_values.get("pm_service_trigger_observer.result", ""),
        "observer_reason": pm_contract.get("reason") or transcript_values.get("pm_service_trigger_observer.reason", ""),
        "add_service_call": int(counts.get("pm_add_service_call", 0)),
        "add_service_fail_log": int(counts.get("pm_add_service_fail_log", 0)),
        "qmi_thread_create_call": int(counts.get("pm_pthread_create_call", 0)),
        "qmi_service_start_log": int(counts.get("pm_qmi_service_start_log", 0)),
        "clean_return_zero": int(counts.get("pm_clean_return_zero", 0)),
        "trace_counts": counts,
        "vndservice_ready_gate": "vndservicemanager_ready" in str(pm_contract.get("order", ""))
        or "vndservicemanager_ready" in transcript_values.get("pm_service_trigger_observer.order", ""),
        "policy_load_proof": "v490" in json.dumps(v1086, sort_keys=True).lower(),
    }


def extract_v694(v694: dict[str, Any]) -> dict[str, Any]:
    arm = v694.get("arm_v694") if isinstance(v694.get("arm_v694"), dict) else {}
    peripheral = arm.get("peripheral") if isinstance(arm.get("peripheral"), dict) else {}
    children = peripheral.get("children") if isinstance(peripheral.get("children"), dict) else {}
    per_mgr = children.get("per_mgr") if isinstance(children.get("per_mgr"), dict) else {}
    query = arm.get("vndservice_query") if isinstance(arm.get("vndservice_query"), dict) else {}
    phases = query.get("phases") if isinstance(query.get("phases"), dict) else {}
    after_per_mgr = phases.get("after_per_mgr_probe") if isinstance(phases.get("after_per_mgr_probe"), dict) else {}
    prep = v694.get("prep_v694") if isinstance(v694.get("prep_v694"), dict) else {}
    v490 = prep.get("v490") if isinstance(prep.get("v490"), dict) else {}
    return {
        "decision": v694.get("decision", ""),
        "pass": bool(v694.get("pass")),
        "reason": v694.get("reason", ""),
        "order": peripheral.get("order", ""),
        "provider_exact_match": truthy(after_per_mgr.get("vendor_qcom_peripheral_manager_seen")),
        "vndservice_query_result": after_per_mgr.get("result", ""),
        "vndservice_query_reason": after_per_mgr.get("reason", ""),
        "vndservicemanager_ready": truthy(nested_get(peripheral, ("vndservicemanager_readiness", "ready"))),
        "vndservicemanager_observable": truthy(nested_get(peripheral, ("vndservicemanager_readiness", "observable"))),
        "per_mgr_observable": truthy(nested_get(peripheral, ("per_mgr", "observable"))),
        "per_mgr_ready": truthy(nested_get(peripheral, ("per_mgr", "ready"))),
        "per_mgr_exit_code": per_mgr.get("exit_code", ""),
        "per_mgr_signal": per_mgr.get("signal", ""),
        "per_mgr_selinux_exec_skipped": per_mgr.get("selinux_exec_skipped", ""),
        "per_mgr_selinux_exec_reason": per_mgr.get("selinux_exec_reason", ""),
        "policy_load_pass": v490.get("decision") == "v490-selinux-policy-load-proof-pass" and bool(v490.get("pass")),
    }


def extract_runtime_context(transcript: str) -> dict[str, Any]:
    values = parse_key_values(transcript)
    return {
        "context_files_visible": all(
            values.get(f"context.{label}.exists") == "1"
            for label in (
                "plat_service_contexts",
                "system_ext_service_contexts",
                "vendor_service_contexts",
            )
        ),
        "vendor_service_contexts_hash": values.get("context.vendor_service_contexts.hash", ""),
        "service_manager_current": values.get("service_manager.identity.after.selinux.current", ""),
        "vndservicemanager_selinux_exec_target": values.get(
            "wifi_hal_composite_child.vndservicemanager.selinux_exec.target_context", ""
        ),
        "vndservicemanager_selinux_current": values.get("wifi_hal_composite_child.vndservicemanager.selinux.current", ""),
        "vndservicemanager_selinux_exec": values.get("wifi_hal_composite_child.vndservicemanager.selinux.exec", ""),
        "per_mgr_selinux_exec_target": values.get("wifi_hal_composite_child.per_mgr.selinux_exec.target_context", ""),
        "per_mgr_selinux_current": values.get("wifi_hal_composite_child.per_mgr.selinux.current", ""),
        "per_mgr_selinux_exec": values.get("wifi_hal_composite_child.per_mgr.selinux.exec", ""),
        "setexec_accepted_but_current_kernel": (
            values.get("wifi_hal_composite_child.per_mgr.selinux_exec.ok") == "1"
            and values.get("wifi_hal_composite_child.per_mgr.selinux.current") == "kernel"
        ),
    }


def classify(v1086_summary: dict[str, Any], v694_summary: dict[str, Any], runtime_context: dict[str, Any]) -> dict[str, Any]:
    v1086_addservice_failure = (
        v1086_summary["decision"] == "v1086-binder-add-service-failure"
        and v1086_summary["add_service_fail_log"] > 0
        and v1086_summary["per_mgr_exit_code"] == "0"
    )
    v694_provider_positive = (
        v694_summary["decision"] == "v694-peripheral-vndservice-registration-confirmed"
        and v694_summary["provider_exact_match"]
    )
    readiness_delta = v694_summary["vndservicemanager_ready"] and not v1086_summary["vndservice_ready_gate"]
    policy_delta = v694_summary["policy_load_pass"] and not v1086_summary["policy_load_proof"]
    if not v1086_addservice_failure:
        decision = "v1087-v1086-addservice-input-missing"
        passed = False
        reason = "V1086 addService failure evidence is missing or no longer matches"
        next_step = "rerun or inspect V1086 before changing PM observer behavior"
    elif not v694_provider_positive:
        decision = "v1087-provider-positive-control-missing"
        passed = False
        reason = "V694 no longer proves vendor.qcom.PeripheralManager registration"
        next_step = "rebuild a provider-positive control before repairing V1086"
    elif readiness_delta and policy_delta:
        decision = "v1087-addservice-readiness-policy-delta-classified"
        passed = True
        reason = (
            "V1086 fails addService after mdmdetect success, while V694 proves provider registration only after "
            "SELinux policy-load proof and an explicit vndservicemanager readiness gate"
        )
        next_step = (
            "V1088 should add a PM-observer vndservicemanager readiness/query gate and require or refresh the V490 "
            "policy-load precondition before another PM-service addService retry"
        )
    elif readiness_delta:
        decision = "v1087-addservice-vndservicemanager-readiness-delta-classified"
        passed = True
        reason = "V1086 lacks the vndservicemanager readiness gate used by the V694 provider-positive path"
        next_step = "V1088 should add a PM-observer vndservicemanager readiness/query gate before per_mgr"
    elif policy_delta:
        decision = "v1087-addservice-policy-load-delta-classified"
        passed = True
        reason = "V694 provider-positive path had V490 policy load, but V1086 evidence does not"
        next_step = "V1088 should require or refresh V490 policy-load proof before PM-service addService retry"
    elif runtime_context.get("setexec_accepted_but_current_kernel"):
        decision = "v1087-addservice-runtime-domain-gap-classified"
        passed = True
        reason = "setexec is accepted but runtime context remains kernel; addService may still be rejected by policy"
        next_step = "V1088 should capture vndservicemanager denial/logs and post-exec attr/current immediately"
    else:
        decision = "v1087-addservice-delta-manual-review"
        passed = True
        reason = "V1086 addService failure and V694 provider-positive control are both present, but no single host-only delta dominates"
        next_step = "V1088 should capture vndservicemanager readiness, exact vndservice query, and addService stderr in one bounded live run"
    return {
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "v1086_addservice_failure": v1086_addservice_failure,
        "v694_provider_positive": v694_provider_positive,
        "readiness_delta": readiness_delta,
        "policy_delta": policy_delta,
        "exit255_direction_obsolete": v1086_summary["per_mgr_exit_code"] == "0",
        "bpf_uprobe_route_already_used": v1086_summary["add_service_call"] > 0,
    }


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v1086 = load_json(args.v1086_manifest)
    v694 = load_json(args.v694_manifest)
    v1086_transcript = read_text(args.v1086_transcript)
    v1072_transcript = read_text(args.v1072_transcript)
    v1086_values = parse_key_values(v1086_transcript)
    v1086_summary = extract_v1086(v1086, v1086_values)
    v694_summary = extract_v694(v694)
    runtime_context = extract_runtime_context(v1072_transcript)
    classification = classify(v1086_summary, v694_summary, runtime_context)
    return {
        "cycle": "v1087",
        "generated_at": now_iso(),
        "command": "host-classify",
        "inputs": {
            "v1086_manifest": str(repo_path(args.v1086_manifest)),
            "v1086_transcript": str(repo_path(args.v1086_transcript)),
            "v694_manifest": str(repo_path(args.v694_manifest)),
            "v1072_transcript": str(repo_path(args.v1072_transcript)),
        },
        "v1086": v1086_summary,
        "v694_positive_control": v694_summary,
        "runtime_context_reference": runtime_context,
        "classification": classification,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "device_commands_executed": False,
        "device_mutations": False,
        "tracefs_write_executed": False,
        "bpf_attach_executed": False,
        "pm_actor_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
        "reboot_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    v1086 = manifest["v1086"]
    v694 = manifest["v694_positive_control"]
    runtime_context = manifest["runtime_context_reference"]
    return "\n".join(
        [
            "# V1087 PM addService Host Classifier",
            "",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            "## Key Findings",
            "",
            f"- V1086 PM-service exit code: `{v1086['per_mgr_exit_code']}`.",
            f"- V1086 addService failure log count: `{v1086['add_service_fail_log']}`.",
            f"- V1086 QMI thread start count: `{v1086['qmi_thread_create_call']}`.",
            f"- V694 provider exact match: `{v694['provider_exact_match']}`.",
            f"- V694 vndservicemanager readiness: `{v694['vndservicemanager_ready']}`.",
            f"- V694 policy-load precondition: `{v694['policy_load_pass']}`.",
            f"- Runtime context files visible: `{runtime_context['context_files_visible']}`.",
            f"- PM setexec accepted but current stayed kernel: `{runtime_context['setexec_accepted_but_current_kernel']}`.",
            "",
            "## Direction Update",
            "",
            "- The V1071 exit-255/BPF-syscall direction is obsolete for the current branch.",
            "- V1075-V1086 already used the uprobe route and narrowed the branch to `addService` failure.",
            "- The next live gate should reproduce the V694 provider-positive preconditions inside the PM observer:",
            "  explicit `vndservicemanager` readiness/query gate plus V490 policy-load precondition.",
            "",
            "## Classification Flags",
            "",
            "```json",
            json.dumps(classification, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1086-manifest", type=Path, default=DEFAULT_V1086_MANIFEST)
    parser.add_argument("--v1086-transcript", type=Path, default=DEFAULT_V1086_TRANSCRIPT)
    parser.add_argument("--v694-manifest", type=Path, default=DEFAULT_V694_MANIFEST)
    parser.add_argument("--v1072-transcript", type=Path, default=DEFAULT_V1072_TRANSCRIPT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(repo_path(args.out_dir)) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {repo_path(args.out_dir)}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
