#!/usr/bin/env python3
"""V1011 host-only actor-delta classifier for V1008 and V1010."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1011-v1008-v1010-actor-delta")
LATEST_POINTER = Path("tmp/wifi/latest-v1011-v1008-v1010-actor-delta.txt")
DEFAULT_V1008_MANIFEST = Path("tmp/wifi/v1008-android-service-window-fd-poll-live/manifest.json")
DEFAULT_V1010_MANIFEST = Path("tmp/wifi/v1010-mdm-helper-runtime-contract-service-defaults-live/manifest.json")
DEFAULT_V1010_TRANSCRIPT = Path(
    "tmp/wifi/v1010-mdm-helper-runtime-contract-service-defaults-live/native/mdm-helper-runtime-contract.txt"
)
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1008-manifest", type=Path, default=DEFAULT_V1008_MANIFEST)
    parser.add_argument("--v1010-manifest", type=Path, default=DEFAULT_V1010_MANIFEST)
    parser.add_argument("--v1010-transcript", type=Path, default=DEFAULT_V1010_TRANSCRIPT)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
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


def child(contract: dict[str, str], name: str, field: str) -> str:
    return contract.get(f"child.{name}.{field}", "")


def bool_contract(contract: dict[str, str], key: str) -> bool:
    return contract.get(key) == "1"


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1008_manifest = load_json(args.v1008_manifest)
    v1010_manifest = load_json(args.v1010_manifest)
    v1010_text = read_text(args.v1010_transcript)
    source = read_text(args.helper_source)
    v1008 = manifest_contract(v1008_manifest)
    v1010 = manifest_contract(v1010_manifest)
    v1010_keys = parse_key_values(v1010_text)

    v1008_fd_negative = (
        v1008_manifest.get("decision") == "v1008-mdm-helper-esoc-fd-missing-no-trigger"
        and v1008.get("mdm_helper_esoc0_fd_poll_seen") == "0"
        and v1008.get("subsys_trigger_start_attempted") == "0"
    )
    v1010_fd_positive = (
        v1010_manifest.get("decision") == "v1010-mdm-helper-esoc-fd-observed"
        and v1010.get("fd_esoc0_count.window") == "1"
        and v1010.get("fd_esoc0_count.final") == "1"
    )
    v1010_service_defaults = (
        v1010_keys.get("android_selinux_context_mode") == "service-defaults"
        and v1010_keys.get("wifi_hal_composite_child.mdm_helper.selinux.exec") == "u:r:vendor_mdm_helper:s0"
        and v1010_keys.get("wifi_hal_composite_child.per_mgr_light.selinux.exec") == "u:r:vendor_per_mgr:s0"
    )
    v1010_per_mgr_alive = (
        v1010.get("per_mgr_light.observable") == "1"
        and v1010.get("per_mgr_light.exited") == "0"
    )
    v1008_per_mgr_exited = (
        child(v1008, "per_mgr", "observable") == "1"
        and child(v1008, "per_mgr", "exited") == "1"
        and child(v1008, "per_mgr", "exit_code") == "0"
    )
    v1008_full_actor_set = all(
        bool_contract(v1008, key)
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
    v1010_reduced_actor_set = (
        v1010.get("per_mgr_start_attempted") == "1"
        and v1010.get("mdm_helper_start_attempted") == "1"
        and v1010.get("service_manager_start_executed") == "0"
        and v1010.get("cnss_start_executed") == "0"
        and v1010.get("wifi_hal_start_executed") == "0"
        and v1010.get("subsys_esoc0_controller_open_attempted") == "0"
        and v1010.get("all_postflight_safe") == "1"
    )
    matrix_mode_available = all(
        token in source
        for token in (
            "wifi-companion-mdm-helper-cnss-service-manager-matrix",
            "--allow-mdm-helper-cnss-service-manager-matrix",
            "after-mdm-helper-esoc-fd",
        )
    )
    service_window_too_broad_next = v1008_full_actor_set and v1008_fd_negative and v1010_fd_positive
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
        v1010_manifest.get(key) is False
        for key in (
            "wifi_hal_start_executed",
            "scan_connect_executed",
            "credential_use_executed",
            "dhcp_route_executed",
            "external_ping_executed",
            "subsys_esoc0_open_attempted",
        )
    )

    checks = {
        "v1008_input_present": bool(v1008_manifest),
        "v1010_input_present": bool(v1010_manifest and v1010_text),
        "v1008_fd_negative": v1008_fd_negative,
        "v1010_fd_positive": v1010_fd_positive,
        "v1010_service_defaults_confirmed": v1010_service_defaults,
        "v1010_per_mgr_light_alive": v1010_per_mgr_alive,
        "v1008_per_mgr_exited_cleanly": v1008_per_mgr_exited,
        "v1008_full_actor_set_observed": v1008_full_actor_set,
        "v1010_reduced_actor_set_observed": v1010_reduced_actor_set,
        "matrix_mode_available": matrix_mode_available,
        "service_window_too_broad_for_next_retry": service_window_too_broad_next,
        "no_forbidden_actions": no_forbidden,
    }

    if all(checks.values()):
        decision = "v1011-select-after-fd-cnss-service-manager-matrix"
        passed = True
        route = "v1012-helper-v171-after-mdm-helper-esoc-fd-matrix-live"
        reason = (
            "V1010 proves service-defaults mdm_helper can hold /dev/esoc-0 in the reduced path; "
            "V1008 proves the full service-window is too broad and loses that fd predicate"
        )
        next_step = (
            "Run helper v171 in the existing matrix mode with service_manager_order=after-mdm-helper-esoc-fd, "
            "so mdm_helper fd is proven before service-manager/CNSS actors are added"
        )
    elif v1008_fd_negative and v1010_fd_positive:
        decision = "v1011-actor-delta-present-inputs-incomplete"
        passed = True
        route = "refresh-actor-delta-before-live"
        reason = "The fd split is proven, but one or more actor/context inputs are missing"
        next_step = "Refresh V1008/V1010 transcripts or helper source scan before selecting an incremental live gate"
    else:
        missing = ", ".join(name for name, ok in checks.items() if not ok)
        decision = "v1011-actor-delta-evidence-incomplete"
        passed = False
        route = "repair-evidence-before-live"
        reason = f"required actor-delta evidence missing or contradictory: {missing}"
        next_step = "Recreate the missing V1008 or V1010 evidence before another live gate"

    return {
        "decision": decision,
        "pass": passed,
        "route": route,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "v1008": {
            "decision": v1008_manifest.get("decision"),
            "mode": v1008_manifest.get("mode"),
            "order": v1008.get("order"),
            "result": v1008.get("result"),
            "mdm_helper_fd_seen": v1008.get("mdm_helper_esoc0_fd_poll_seen"),
            "mdm_helper_fd_max": v1008.get("mdm_helper_esoc0_fd_poll_max_count"),
            "subsys_trigger_start_attempted": v1008.get("subsys_trigger_start_attempted"),
            "per_mgr": {
                "observable": child(v1008, "per_mgr", "observable"),
                "exited": child(v1008, "per_mgr", "exited"),
                "exit_code": child(v1008, "per_mgr", "exit_code"),
                "start_order": child(v1008, "per_mgr", "start_order"),
            },
            "cnss_daemon": {
                "observable": child(v1008, "cnss_daemon", "observable"),
                "start_order": child(v1008, "cnss_daemon", "start_order"),
            },
        },
        "v1010": {
            "decision": v1010_manifest.get("decision"),
            "mode": v1010_manifest.get("mode"),
            "order": v1010.get("order"),
            "result": v1010.get("result"),
            "fd_esoc0_count_window": v1010.get("fd_esoc0_count.window"),
            "fd_esoc0_count_final": v1010.get("fd_esoc0_count.final"),
            "subsys_esoc0_controller_open_attempted": v1010.get("subsys_esoc0_controller_open_attempted"),
            "per_mgr_light": {
                "observable": v1010.get("per_mgr_light.observable"),
                "exited": v1010.get("per_mgr_light.exited"),
                "exit_code": v1010.get("per_mgr_light.exit_code"),
                "exec_context": v1010_keys.get("wifi_hal_composite_child.per_mgr_light.selinux.exec"),
            },
            "mdm_helper": {
                "exec_context": v1010_keys.get("wifi_hal_composite_child.mdm_helper.selinux.exec"),
                "android_selinux_context_mode": v1010_keys.get("android_selinux_context_mode"),
            },
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    checks = classification["checks"]
    v1008 = classification["v1008"]
    v1010 = classification["v1010"]
    return "\n".join(
        [
            "# V1011 V1008/V1010 Actor Delta",
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
            "## Route Split",
            "",
            markdown_table(
                ["unit", "result", "fd", "per_mgr", "next implication"],
                [
                    (
                        "V1008",
                        str(v1008["result"]),
                        f"seen={v1008['mdm_helper_fd_seen']} max={v1008['mdm_helper_fd_max']}",
                        json.dumps(v1008["per_mgr"], sort_keys=True),
                        "full service-window is too broad for the next retry",
                    ),
                    (
                        "V1010",
                        str(v1010["result"]),
                        f"window={v1010['fd_esoc0_count_window']} final={v1010['fd_esoc0_count_final']}",
                        json.dumps(v1010["per_mgr_light"], sort_keys=True),
                        "preserve reduced fd-positive route, then add actors after fd",
                    ),
                ],
            ),
            "",
            "## Selected Gate",
            "",
            "- Use the existing matrix mode.",
            "- Order: `after-mdm-helper-esoc-fd`.",
            "- Add service-manager/CNSS only after the `mdm_helper` `/dev/esoc-0` predicate is true.",
            "- Keep Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping forbidden.",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    inputs = {
        "v1008_manifest": args.v1008_manifest,
        "v1010_manifest": args.v1010_manifest,
        "v1010_transcript": args.v1010_transcript,
        "helper_source": args.helper_source,
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
