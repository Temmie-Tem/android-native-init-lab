#!/usr/bin/env python3
"""V1029 host-only classifier for PM actor runtime input/domain deltas."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1029-pm-runtime-input-delta")
LATEST_POINTER = Path("tmp/wifi/latest-v1029-pm-runtime-input-delta.txt")
DEFAULT_V1028_MANIFEST = Path("tmp/wifi/v1028-pm-proxy-helper-modem-get-classifier/manifest.json")
DEFAULT_ANDROID_SAMPLE = Path(
    "tmp/wifi/v1024-fast-fd-android-timing-handoff-live-20260526-181232/"
    "v1022-early-android-pm-esoc-timing/android/commands/sample-loop.txt"
)
DEFAULT_ANDROID_PROPS = Path(
    "tmp/wifi/v1024-fast-fd-android-timing-handoff-live-20260526-181232/"
    "v1022-early-android-pm-esoc-timing/android/commands/props-before.txt"
)
DEFAULT_NATIVE_TRANSCRIPT = Path("tmp/wifi/v1027-pm-full-contract-live/native/mdm-helper-cnss-before-esoc.txt")
DEFAULT_NATIVE_DMESG = Path("tmp/wifi/v1027-pm-full-contract-live/native/post-dmesg-wifi-esoc-tail.txt")
DEFAULT_V863_MANIFEST = Path("tmp/wifi/v863-pm-proxy-helper-rc-live/manifest.json")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")


ANDROID_EXPECTED_DOMAINS = {
    "pm_proxy_helper": "u:r:per_proxy_helper:s0",
    "pm-service": "u:r:vendor_per_mgr:s0",
    "pm-proxy": "u:r:vendor_per_proxy:s0",
    "mdm_helper": "u:r:vendor_mdm_helper:s0",
}
NATIVE_CHILD_MAP = {
    "pm_proxy_helper": "pm_proxy_helper",
    "pm-service": "per_mgr_light",
    "pm-proxy": "pm_proxy",
    "mdm_helper": "mdm_helper",
}
NATIVE_EXPECTED_TARGETS = {
    "pm_proxy_helper": "u:r:per_proxy_helper:s0",
    "per_mgr_light": "u:r:vendor_per_mgr:s0",
    "pm_proxy": "u:r:vendor_per_mgr:s0",
    "mdm_helper": "u:r:vendor_mdm_helper:s0",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1028-manifest", type=Path, default=DEFAULT_V1028_MANIFEST)
    parser.add_argument("--android-sample", type=Path, default=DEFAULT_ANDROID_SAMPLE)
    parser.add_argument("--android-props", type=Path, default=DEFAULT_ANDROID_PROPS)
    parser.add_argument("--native-transcript", type=Path, default=DEFAULT_NATIVE_TRANSCRIPT)
    parser.add_argument("--native-dmesg", type=Path, default=DEFAULT_NATIVE_DMESG)
    parser.add_argument("--v863-manifest", type=Path, default=DEFAULT_V863_MANIFEST)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path, limit: int = 8_000_000) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes()[:limit].replace(b"\0", b"\\0").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {"_missing": True, "_path": str(path)}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"_invalid": True, "_path": str(path)}
    if not isinstance(payload, dict):
        return {"_invalid": True, "_path": str(path)}
    payload["_path"] = str(path)
    return payload


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "pass"}
    return False


def parse_key_values(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line or line.startswith("$ "):
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def selected_lines(text: str, pattern: str, limit: int = 12) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line and regex.search(line):
            lines.append(line)
            if len(lines) >= limit:
                break
    return lines


def android_surface(sample_text: str, props_text: str) -> dict[str, Any]:
    actors: dict[str, dict[str, Any]] = {}
    for actor, expected_domain in ANDROID_EXPECTED_DOMAINS.items():
        actor_pattern = re.escape(actor)
        target_line = next(
            (
                line.strip()
                for line in sample_text.splitlines()
                if line.startswith("TARGET_PROC")
                and re.search(rf"(tag|comm)={actor_pattern}\b", line)
            ),
            "",
        )
        domain_present = f"attr={expected_domain}" in target_line
        if actor == "pm_proxy_helper":
            fd_present = "/dev/subsys_modem" in sample_text and "u:r:per_proxy_helper:s0" in sample_text
        elif actor == "pm-service":
            fd_present = "/dev/subsys_modem" in sample_text and "u:r:vendor_per_mgr:s0" in sample_text
        elif actor == "mdm_helper":
            fd_present = "/dev/esoc-0" in sample_text and "u:r:vendor_mdm_helper:s0" in sample_text
        else:
            fd_present = True
        actors[actor] = {
            "expected_domain": expected_domain,
            "target_line": target_line,
            "domain_present": domain_present,
            "fd_present": fd_present,
        }
    props = parse_key_values(props_text)
    return {
        "sample_present": bool(sample_text),
        "props_present": bool(props_text),
        "actors": actors,
        "props": {
            "init.svc.vendor.per_proxy_helper": props.get("init.svc.vendor.per_proxy_helper", ""),
            "init.svc.vendor.per_mgr": props.get("init.svc.vendor.per_mgr", ""),
            "init.svc.vendor.per_proxy": props.get("init.svc.vendor.per_proxy", ""),
            "init.svc.vendor.mdm_helper": props.get("init.svc.vendor.mdm_helper", ""),
        },
        "evidence_lines": selected_lines(
            sample_text,
            r"TARGET_PROC tag=(pm_proxy_helper|pm-service|pm-proxy|mdm_helper)|/dev/(subsys_modem|esoc-0)",
            limit=16,
        ),
    }


def native_surface(transcript: str, dmesg: str) -> dict[str, Any]:
    kv = parse_key_values(transcript)
    actors: dict[str, dict[str, Any]] = {}
    for android_actor, child in NATIVE_CHILD_MAP.items():
        target_context = kv.get(f"wifi_hal_composite_child.{child}.selinux_exec.target_context", "")
        setexec_ok = boolish(kv.get(f"wifi_hal_composite_child.{child}.selinux_exec.ok"))
        attr_kernel_lines = selected_lines(
            transcript,
            rf"A90_EXECNS_CNSS_PROC_attr_current_BEGIN path=/proc/\d+/attr/current.*|kernel\\0|wifi_hal_composite_child\.{re.escape(child)}\.selinux\.(current|exec)=kernel",
            limit=20,
        )
        actors[android_actor] = {
            "child": child,
            "expected_target": NATIVE_EXPECTED_TARGETS[child],
            "target_context": target_context,
            "setexec_ok": setexec_ok,
            "runtime_kernel_observed": "kernel\\0" in "\n".join(attr_kernel_lines)
            or kv.get(f"wifi_hal_composite_child.{child}.selinux.current") == "kernel",
            "context_lines": selected_lines(
                transcript,
                rf"wifi_hal_composite_child\.{re.escape(child)}\.selinux|A90_EXECNS_CNSS_PROC_attr_current_BEGIN path=/proc/\d+/attr/current|kernel\\0",
                limit=10,
            ),
        }
    return {
        "transcript_present": bool(transcript),
        "actors": actors,
        "pm_proxy_helper_fd_count": kv.get("cnss_before_esoc.pm_proxy_helper_subsys_modem_fd_count", ""),
        "per_mgr_fd_count": kv.get("cnss_before_esoc.per_mgr_subsys_modem_fd_count", ""),
        "mdm_helper_fd_count": kv.get("cnss_before_esoc.mdm_helper_esoc0_fd_count", ""),
        "per_mgr_ioprio_ok": boolish(kv.get("wifi_hal_composite_child.per_mgr_light.ioprio.ok")),
        "private_subsys_modem_visible": kv.get("wifi_companion_start.private_node.subsys_modem.exists") == "1",
        "private_esoc_0_visible": "wifi_companion_start.private_node.esoc_0.path=" in transcript,
        "modem_get_lines": selected_lines(
            dmesg or transcript,
            r"__subsystem_get:\s+modem|Changing subsys fw_name to modem|modem: loading",
            limit=8,
        ),
    }


def init_contract(v863: dict[str, Any], helper_source: str) -> dict[str, Any]:
    service_contract = v863.get("service_contract") or {}
    return {
        "v863_decision": v863.get("decision"),
        "v863_pass": boolish(v863.get("pass")),
        "service": service_contract.get("service", "") or service_contract.get("name", ""),
        "path": service_contract.get("path", ""),
        "class": service_contract.get("class", ""),
        "user": service_contract.get("user", ""),
        "group": service_contract.get("group", ""),
        "disabled": service_contract.get("disabled", ""),
        "oneshot": service_contract.get("oneshot", ""),
        "source_has_pm_proxy_helper_child": "/vendor/bin/pm_proxy_helper" in helper_source and "per_proxy_helper" in helper_source,
        "source_has_ioprio_rt4": "IOPRIO_CLASS_RT" in helper_source and "ioprio.priority=4" in helper_source,
        "source_has_lifecycle_marker": "init.svc.vendor.per_mgr=running" in helper_source,
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1028 = load_json(args.v1028_manifest)
    android = android_surface(read_text(args.android_sample), read_text(args.android_props))
    native = native_surface(read_text(args.native_transcript), read_text(args.native_dmesg))
    contract = init_contract(load_json(args.v863_manifest), read_text(args.helper_source))

    android_domain_fd_positive = all(
        actor["domain_present"] and actor["fd_present"]
        for actor in android["actors"].values()
    )
    android_services_running = all(value == "running" for value in android["props"].values())
    native_requested_domains = all(
        actor["target_context"] == actor["expected_target"] and actor["setexec_ok"]
        for actor in native["actors"].values()
    )
    native_runtime_kernel_gap = all(
        actor["runtime_kernel_observed"] for actor in native["actors"].values()
    )
    native_fd_gap_reproduced = (
        native["pm_proxy_helper_fd_count"] == "0"
        and native["per_mgr_fd_count"] == "0"
        and native["mdm_helper_fd_count"] == "1"
        and native["private_subsys_modem_visible"]
        and native["private_esoc_0_visible"]
    )
    init_contract_model_present = (
        contract["v863_pass"]
        and contract["service"] == "vendor.per_proxy_helper"
        and contract["path"] == "/vendor/bin/pm_proxy_helper"
        and contract["source_has_pm_proxy_helper_child"]
        and contract["source_has_ioprio_rt4"]
        and contract["source_has_lifecycle_marker"]
    )
    v1028_ready = (
        v1028.get("decision") == "v1028-pm-proxy-helper-modem-get-blocker-classified"
        and boolish(v1028.get("pass"))
    )

    checks = {
        "v1028_ready": v1028_ready,
        "android_domain_fd_positive": android_domain_fd_positive,
        "android_services_running": android_services_running,
        "native_requested_domains": native_requested_domains,
        "native_runtime_kernel_gap": native_runtime_kernel_gap,
        "native_fd_gap_reproduced": native_fd_gap_reproduced,
        "native_modem_get_lines_present": bool(native["modem_get_lines"]),
        "init_contract_model_present": init_contract_model_present,
    }

    if all(checks.values()):
        decision = "v1029-pm-actor-selinux-runtime-domain-gap-classified"
        passed = True
        route = "v1030-pm-actor-runtime-domain-proof-support"
        reason = (
            "Android PM actors run in vendor domains while holding the required fds; native V1027 requests "
            "matching target contexts but captured attr/current remains kernel before the PM fd predicate appears"
        )
        next_step = (
            "Add source/build support for a fail-closed PM actor runtime-domain proof before another PM full-contract live retry"
        )
    elif v1028_ready and native_runtime_kernel_gap:
        decision = "v1029-native-domain-gap-present-inputs-incomplete"
        passed = True
        route = "refresh-android-pm-domain-evidence"
        reason = "native PM actors remain kernel, but Android fd/domain or init-contract evidence is incomplete"
        next_step = "Refresh Android PM actor domain evidence or repair classifier inputs before helper changes"
    else:
        missing = ", ".join(name for name, ok in checks.items() if not ok)
        decision = "v1029-pm-runtime-input-delta-incomplete"
        passed = False
        route = "repair-v1028-or-runtime-input-evidence"
        reason = f"required evidence missing or contradictory: {missing}"
        next_step = "Repair input evidence before changing PM runtime behavior"

    return {
        "decision": decision,
        "pass": passed,
        "route": route,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "android": android,
        "native": native,
        "init_contract": contract,
        "guardrails": {
            "device_contact_executed": False,
            "device_mutations": False,
            "actor_start_executed": False,
            "daemon_start_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "boot_image_write_executed": False,
        },
    }


def render_summary(manifest: dict[str, Any]) -> str:
    c = manifest["classification"]
    android_rows = []
    for actor, data in c["android"]["actors"].items():
        android_rows.append([actor, data["expected_domain"], data["domain_present"], data["fd_present"]])
    native_rows = []
    for actor, data in c["native"]["actors"].items():
        native_rows.append([actor, data["child"], data["target_context"], data["setexec_ok"], data["runtime_kernel_observed"]])
    return "\n".join(
        [
            "# V1029 PM Runtime Input Delta",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- route: `{c['route']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            "## Checks",
            "",
            markdown_table(["check", "value"], [[key, value] for key, value in c["checks"].items()]),
            "",
            "## Android PM Actors",
            "",
            markdown_table(["actor", "domain", "domain_present", "fd_present"], android_rows),
            "",
            "## Native PM Actors",
            "",
            markdown_table(["actor", "child", "target_context", "setexec_ok", "runtime_kernel"], native_rows),
            "",
            "## Android Evidence Lines",
            "",
            "\n".join(f"- `{line}`" for line in c["android"]["evidence_lines"]) or "- none",
            "",
            "## Native Modem-Get Lines",
            "",
            "\n".join(f"- `{line}`" for line in c["native"]["modem_get_lines"]) or "- none",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        classification = {
            "decision": "v1029-pm-runtime-input-delta-plan-ready",
            "pass": True,
            "route": "host-only-runtime-input-comparison",
            "reason": "plan-only; no live device contact required",
            "next_step": "run V1029 against Android V1024 and native V1027 evidence",
            "checks": {},
            "android": {"actors": {}, "evidence_lines": []},
            "native": {"actors": {}, "modem_get_lines": []},
            "init_contract": {},
            "guardrails": {"device_contact_executed": False, "device_mutations": False},
        }
    else:
        classification = classify(args)
    manifest = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "host": collect_host_metadata(),
        "classification": classification,
        "device_commands_executed": False,
        "device_mutations": False,
        "actor_start_executed": False,
        "daemon_start_executed": False,
        "wifi_command_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
