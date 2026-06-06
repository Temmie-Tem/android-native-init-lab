#!/usr/bin/env python3
"""V1009 host-only comparator for V911 and V1008 mdm_helper contracts."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1009-v911-v1008-contract-comparator")
LATEST_POINTER = Path("tmp/wifi/latest-v1009-v911-v1008-contract-comparator.txt")

DEFAULT_V911_MANIFEST = Path("tmp/wifi/v911-mdm-helper-esoc-fd-stall-live/manifest.json")
DEFAULT_V911_TRANSCRIPT = Path(
    "tmp/wifi/v911-mdm-helper-esoc-fd-stall-live/native/mdm-helper-runtime-contract.txt"
)
DEFAULT_V1008_MANIFEST = Path("tmp/wifi/v1008-android-service-window-fd-poll-live/manifest.json")
DEFAULT_V1008_TRANSCRIPT = Path(
    "tmp/wifi/v1008-android-service-window-fd-poll-live/native/mdm-helper-cnss-before-esoc.txt"
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v911-manifest", type=Path, default=DEFAULT_V911_MANIFEST)
    parser.add_argument("--v911-transcript", type=Path, default=DEFAULT_V911_TRANSCRIPT)
    parser.add_argument("--v1008-manifest", type=Path, default=DEFAULT_V1008_MANIFEST)
    parser.add_argument("--v1008-transcript", type=Path, default=DEFAULT_V1008_TRANSCRIPT)
    return parser.parse_args()


def read_text(path: Path, limit: int = 8_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def sha256(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    digest = hashlib.sha256()
    with resolved.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_contract(manifest: dict[str, Any]) -> dict[str, str]:
    helper = ((manifest.get("analysis") or {}).get("helper") or {})
    contract = helper.get("contract") or {}
    return {str(key): str(value) for key, value in contract.items()}


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line or line.startswith("$ "):
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or any(char.isspace() for char in key):
            continue
        values[key] = value.strip()
    return values


def first_present(text: str, patterns: list[str]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(0).strip()
    return ""


def value(values: dict[str, str], key: str, default: str = "") -> str:
    return values.get(key, default)


def bool_str(value_: str) -> bool:
    return value_ in ("1", "true", "True", "yes")


def child_summary(contract: dict[str, str], name: str) -> dict[str, str]:
    prefix = f"child.{name}."
    return {
        "observable": contract.get(f"{prefix}observable", ""),
        "exited": contract.get(f"{prefix}exited", ""),
        "exit_code": contract.get(f"{prefix}exit_code", ""),
        "signal": contract.get(f"{prefix}signal", ""),
        "start_order": contract.get(f"{prefix}start_order", ""),
        "postflight_safe": contract.get(f"{prefix}postflight_safe", ""),
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v911_manifest = load_json(args.v911_manifest)
    v1008_manifest = load_json(args.v1008_manifest)
    v911_text = read_text(args.v911_transcript)
    v1008_text = read_text(args.v1008_transcript)
    v911_keys = parse_key_values(v911_text)
    v1008_keys = parse_key_values(v1008_text)
    v911_contract = manifest_contract(v911_manifest)
    v1008_contract = manifest_contract(v1008_manifest)

    v911_mdm_helper = {
        "expected_uid": value(v911_keys, "wifi_hal_composite_child.mdm_helper.expected.uid"),
        "expected_gid": value(v911_keys, "wifi_hal_composite_child.mdm_helper.expected.gid"),
        "expected_groups": value(v911_keys, "wifi_hal_composite_child.mdm_helper.expected.groups"),
        "preexec_status": value(v911_keys, "wifi_hal_composite_child.mdm_helper.preexec_status"),
        "target_context": value(v911_keys, "wifi_hal_composite_child.mdm_helper.selinux_exec.target_context"),
        "actual_current": value(v911_keys, "wifi_hal_composite_child.mdm_helper.selinux.current"),
        "actual_exec": value(v911_keys, "wifi_hal_composite_child.mdm_helper.selinux.exec"),
        "exec_target": value(v911_keys, "wifi_hal_composite_child.mdm_helper.exec_target"),
    }
    v1008_mdm_helper = {
        "expected_uid": value(v1008_keys, "wifi_hal_composite_child.mdm_helper.expected.uid"),
        "expected_gid": value(v1008_keys, "wifi_hal_composite_child.mdm_helper.expected.gid"),
        "expected_groups": value(v1008_keys, "wifi_hal_composite_child.mdm_helper.expected.groups"),
        "preexec_status": value(v1008_keys, "wifi_hal_composite_child.mdm_helper.preexec_status"),
        "target_context": value(v1008_keys, "wifi_hal_composite_child.mdm_helper.selinux_exec.target_context"),
        "actual_current": value(v1008_keys, "wifi_hal_composite_child.mdm_helper.selinux.current"),
        "actual_exec": value(v1008_keys, "wifi_hal_composite_child.mdm_helper.selinux.exec"),
        "exec_target": value(v1008_keys, "wifi_hal_composite_child.mdm_helper.exec_target"),
    }

    v911_per_mgr = {
        "label": "per_mgr_light",
        "observable": v911_contract.get("per_mgr_light.observable", ""),
        "exited": v911_contract.get("per_mgr_light.exited", ""),
        "exit_code": v911_contract.get("per_mgr_light.exit_code", ""),
        "signal": v911_contract.get("per_mgr_light.signal", ""),
        "actual_current": value(v911_keys, "wifi_hal_composite_child.per_mgr_light.selinux.current"),
        "actual_exec": value(v911_keys, "wifi_hal_composite_child.per_mgr_light.selinux.exec"),
        "target_context": value(v911_keys, "wifi_hal_composite_child.per_mgr_light.selinux_exec.target_context"),
        "fd_count": value(v911_keys, "capture.wifi_hal_composite_per_mgr_light.fd_links.count"),
    }
    v1008_per_mgr = {
        "label": "per_mgr",
        **child_summary(v1008_contract, "per_mgr"),
        "actual_current": value(v1008_keys, "wifi_hal_composite_child.per_mgr.selinux.current"),
        "actual_exec": value(v1008_keys, "wifi_hal_composite_child.per_mgr.selinux.exec"),
        "target_context": value(v1008_keys, "wifi_hal_composite_child.per_mgr.selinux_exec.target_context"),
        "fd_count": value(v1008_keys, "capture.wifi_hal_composite_per_mgr.fd_links.count"),
    }

    v911_fd_positive = (
        v911_manifest.get("decision") == "v908-mdm-helper-esoc-fd-observed"
        and v911_contract.get("fd_esoc0_count.window") == "1"
        and v911_contract.get("fd_esoc0_count.final") == "1"
        and v911_contract.get("result") == "mdm-helper-esoc-fd-observed"
    )
    v1008_fd_negative = (
        v1008_manifest.get("decision") == "v1008-mdm-helper-esoc-fd-missing-no-trigger"
        and v1008_contract.get("mdm_helper_esoc0_fd_poll_seen") == "0"
        and v1008_contract.get("mdm_helper_esoc0_fd_poll_max_count") == "0"
        and v1008_contract.get("mdm_helper_esoc0_fd_count") == "0"
        and v1008_contract.get("subsys_trigger_start_attempted") == "0"
    )
    v1008_poll_window_valid = (
        v1008_contract.get("fd_poll.after_mdm_helper_spawn.polls") == "2"
        and v1008_contract.get("fd_poll.after_cnss_daemon_spawn.polls") == "14"
        and v1008_contract.get("fd_poll.after_cnss_daemon_spawn.first_seen_elapsed_ms") == "-1"
    )
    same_property_root = v911_manifest.get("property_root") == v1008_manifest.get("property_root")
    same_mdm_helper_identity = all(
        v911_mdm_helper[key] == v1008_mdm_helper[key]
        for key in ("expected_uid", "expected_gid", "expected_groups", "preexec_status", "target_context", "exec_target")
    )
    selinux_actual_diff = v911_mdm_helper["actual_exec"] != v1008_mdm_helper["actual_exec"]
    per_mgr_liveness_diff = v911_per_mgr["exited"] == "0" and v1008_per_mgr["exited"] == "1"
    v1008_full_actor_set = all(
        bool_str(v1008_contract.get(key, "0"))
        for key in (
            "service_manager_start_executed",
            "wifi_hal_start_executed",
            "wificond_start_executed",
            "mdm_helper_start_executed",
            "cnss_daemon_start_executed",
            "all_observable_at_timeout",
            "all_postflight_safe",
        )
    )
    surface_shared = all(
        value(v911_keys, key) == "1" and value(v1008_keys, key) == "1"
        for key in (
            "context.sys_bus_esoc_device_esoc0.exists",
            "context.sys_bus_msm_subsys_device_subsys9.exists",
            "context.selinux_status.exists",
        )
    )
    no_forbidden = all(
        v1008_manifest.get(key) is False
        for key in (
            "qcwlanstate_write_executed",
            "iwifi_start_executed",
            "live_esoc_ioctl_executed",
            "scan_connect_executed",
            "credential_use_executed",
            "dhcp_route_executed",
            "external_ping_executed",
            "subsys_esoc0_open_attempted",
        )
    ) and all(
        v911_manifest.get(key) is False
        for key in (
            "scan_connect_executed",
            "credential_use_executed",
            "dhcp_route_executed",
            "external_ping_executed",
            "subsys_esoc0_controller_open_attempted",
        )
    )

    checks = {
        "v911_input_present": bool(v911_manifest and v911_text),
        "v1008_input_present": bool(v1008_manifest and v1008_text),
        "v911_mdm_helper_fd_positive": v911_fd_positive,
        "v1008_service_window_fd_negative": v1008_fd_negative,
        "v1008_fd_poll_window_valid": v1008_poll_window_valid,
        "same_property_root": same_property_root,
        "same_mdm_helper_identity_contract": same_mdm_helper_identity,
        "shared_esoc_subsys_selinux_surfaces": surface_shared,
        "selinux_actual_domain_differs": selinux_actual_diff,
        "per_mgr_liveness_differs": per_mgr_liveness_diff,
        "v1008_full_actor_set_observed": v1008_full_actor_set,
        "no_forbidden_actions": no_forbidden,
    }

    if all(checks.values()):
        decision = "v1009-select-reduced-service-defaults-mdm-helper-isolation"
        passed = True
        route = "v1010-reduced-mdm-helper-runtime-contract-with-service-defaults"
        reason = (
            "V911 proves the reduced runtime-contract can make mdm_helper hold /dev/esoc-0, "
            "but that positive path ran with a different actual SELinux domain and a persistent per_mgr_light; "
            "V1008 proves the full service-window with service-defaults never opens that fd"
        )
        next_step = (
            "Run a reduced V911-style mdm_helper runtime-contract gate using helper v171 and "
            "--android-selinux-context-mode service-defaults before adding CNSS/HAL actors"
        )
    elif v911_fd_positive and v1008_fd_negative:
        decision = "v1009-contract-delta-present-but-incomplete"
        passed = True
        route = "repair-comparator-inputs-before-live"
        reason = "The positive/negative fd split is proven, but one or more environment deltas were not captured strongly enough"
        next_step = "Refresh transcripts with uid/gid/SELinux/per_mgr snapshots before another live trigger"
    else:
        missing = ", ".join(name for name, ok in checks.items() if not ok)
        decision = "v1009-comparison-evidence-incomplete"
        passed = False
        route = "refresh-v911-v1008-evidence"
        reason = f"required comparison evidence missing or contradictory: {missing}"
        next_step = "Recreate the missing V911 or V1008 evidence before selecting a new live gate"

    return {
        "decision": decision,
        "pass": passed,
        "route": route,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "v911": {
            "decision": v911_manifest.get("decision"),
            "mode": v911_manifest.get("mode"),
            "helper_marker": v911_manifest.get("helper_marker"),
            "property_root": v911_manifest.get("property_root"),
            "order": v911_contract.get("order"),
            "result": v911_contract.get("result"),
            "reason": v911_contract.get("reason"),
            "fd_esoc0_count_window": v911_contract.get("fd_esoc0_count.window"),
            "fd_esoc0_count_final": v911_contract.get("fd_esoc0_count.final"),
            "mdm_helper": v911_mdm_helper,
            "per_mgr": v911_per_mgr,
            "subsys_esoc0_controller_open_attempted": v911_contract.get("subsys_esoc0_controller_open_attempted"),
            "wait_for_req_marker": first_present(v911_text, [r"ESOC_WAIT_FOR_REQ", r"esoc_dev_ioctl"]),
        },
        "v1008": {
            "decision": v1008_manifest.get("decision"),
            "mode": v1008_manifest.get("mode"),
            "helper_marker": v1008_manifest.get("helper_marker"),
            "property_root": v1008_manifest.get("property_root"),
            "order": v1008_contract.get("order"),
            "result": v1008_contract.get("result"),
            "reason": v1008_contract.get("reason"),
            "child_started": v1008_contract.get("child_started"),
            "fd_poll_after_mdm_polls": v1008_contract.get("fd_poll.after_mdm_helper_spawn.polls"),
            "fd_poll_after_cnss_polls": v1008_contract.get("fd_poll.after_cnss_daemon_spawn.polls"),
            "mdm_helper_esoc0_fd_poll_seen": v1008_contract.get("mdm_helper_esoc0_fd_poll_seen"),
            "mdm_helper_esoc0_fd_poll_max_count": v1008_contract.get("mdm_helper_esoc0_fd_poll_max_count"),
            "subsys_trigger_start_attempted": v1008_contract.get("subsys_trigger_start_attempted"),
            "mdm_helper": v1008_mdm_helper,
            "per_mgr": v1008_per_mgr,
            "cnss_daemon": child_summary(v1008_contract, "cnss_daemon"),
        },
    }


def dict_rows(prefix: str, payload: dict[str, str]) -> list[tuple[str, str, str]]:
    return [(prefix, key, value) for key, value in payload.items()]


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    checks = classification["checks"]
    v911 = classification["v911"]
    v1008 = classification["v1008"]
    identity_rows: list[tuple[str, str, str]] = []
    identity_rows.extend(dict_rows("V911 mdm_helper", v911["mdm_helper"]))
    identity_rows.extend(dict_rows("V1008 mdm_helper", v1008["mdm_helper"]))
    per_mgr_rows: list[tuple[str, str, str]] = []
    per_mgr_rows.extend(dict_rows("V911 per_mgr_light", v911["per_mgr"]))
    per_mgr_rows.extend(dict_rows("V1008 per_mgr", v1008["per_mgr"]))
    return "\n".join(
        [
            "# V1009 V911/V1008 Contract Comparator",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{classification['decision']}`",
            f"- pass: `{classification['pass']}`",
            f"- route: `{classification['route']}`",
            f"- reason: {classification['reason']}",
            f"- next: {classification['next_step']}",
            "",
            "## Inputs",
            "",
            markdown_table(
                ["input", "path", "exists", "sha256"],
                [
                    (name, payload["path"], str(payload["exists"]), payload["sha256"])
                    for name, payload in manifest["inputs"].items()
                ],
            ),
            "",
            "## Checks",
            "",
            markdown_table(["check", "pass"], [(name, str(value)) for name, value in checks.items()]),
            "",
            "## FD Split",
            "",
            markdown_table(
                ["unit", "decision", "result", "fd signal", "trigger"],
                [
                    (
                        "V911",
                        str(v911["decision"]),
                        str(v911["result"]),
                        f"window={v911['fd_esoc0_count_window']} final={v911['fd_esoc0_count_final']}",
                        f"subsys_controller={v911['subsys_esoc0_controller_open_attempted']}",
                    ),
                    (
                        "V1008",
                        str(v1008["decision"]),
                        str(v1008["result"]),
                        f"seen={v1008['mdm_helper_esoc0_fd_poll_seen']} max={v1008['mdm_helper_esoc0_fd_poll_max_count']}",
                        f"subsys_trigger={v1008['subsys_trigger_start_attempted']}",
                    ),
                ],
            ),
            "",
            "## mdm_helper Identity",
            "",
            markdown_table(["unit", "field", "value"], identity_rows),
            "",
            "## per_mgr Delta",
            "",
            markdown_table(["unit", "field", "value"], per_mgr_rows),
            "",
            "## Selected V1008 Actors",
            "",
            "```json",
            json.dumps(
                {
                    "child_started": v1008["child_started"],
                    "cnss_daemon": v1008["cnss_daemon"],
                    "fd_poll_after_mdm_polls": v1008["fd_poll_after_mdm_polls"],
                    "fd_poll_after_cnss_polls": v1008["fd_poll_after_cnss_polls"],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            "```",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    inputs = {
        "v911_manifest": args.v911_manifest,
        "v911_transcript": args.v911_transcript,
        "v1008_manifest": args.v1008_manifest,
        "v1008_transcript": args.v1008_transcript,
    }
    classification = classify(args)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "host_only": True,
        "device_commands_executed": False,
        "device_mutations": False,
        "native_live_executed": False,
        "android_live_executed": False,
        "classification": classification,
        "inputs": {
            name: {
                "path": str(repo_path(path)),
                "exists": repo_path(path).exists(),
                "sha256": sha256(path),
                "bytes": repo_path(path).stat().st_size if repo_path(path).exists() else 0,
            }
            for name, path in inputs.items()
        },
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {classification['decision']}")
    print(f"pass: {classification['pass']}")
    print(f"route: {classification['route']}")
    print(f"reason: {classification['reason']}")
    print(f"next: {classification['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if classification["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
