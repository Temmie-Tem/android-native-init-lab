#!/usr/bin/env python3
"""V939 host-only classifier for V938 mdm_helper lower-contract evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v939-v938-lower-contract-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v939-v938-lower-contract-classifier.txt")
DEFAULT_V938_MANIFEST = Path("tmp/wifi/v938-mdm-helper-lower-contract-capture-live/manifest.json")
DEFAULT_V914_MANIFEST = Path("tmp/wifi/v914-v913-android-timeline-reclassifier/manifest.json")

PROPERTY_KEYS = [
    "arm64.memtag.process.mdm_helper",
    "persist.vendor.mdm_helper.fail_action",
    "persist.vendor.mdm_helper.timeout",
    "persist.log.tag.mdm_helper",
    "log.tag.mdm_helper",
]

PHASES = [
    "runtime_contract_before",
    "runtime_contract_window",
    "runtime_contract_final",
    "runtime_contract_after",
]

SOURCES = ["plat", "system_ext", "vendor"]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v938-manifest", type=Path, default=DEFAULT_V938_MANIFEST)
    parser.add_argument("--v914-manifest", type=Path, default=DEFAULT_V914_MANIFEST)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8"))


def helper(manifest: dict[str, Any]) -> dict[str, Any]:
    return ((manifest.get("analysis") or {}).get("helper") or {})


def contract(manifest: dict[str, Any]) -> dict[str, Any]:
    return helper(manifest).get("contract") or {}


def lower_contract(manifest: dict[str, Any]) -> dict[str, str]:
    return helper(manifest).get("lower_contract") or {}


def as_int(value: Any) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def exact_key_totals(lower: dict[str, str]) -> dict[str, int]:
    totals = {key: 0 for key in PROPERTY_KEYS}
    for phase in PHASES:
        for source in SOURCES:
            for key in PROPERTY_KEYS:
                suffix = {
                    "arm64.memtag.process.mdm_helper": "memtag_mdm_helper",
                    "persist.vendor.mdm_helper.fail_action": "persist_fail_action",
                    "persist.vendor.mdm_helper.timeout": "persist_timeout",
                    "persist.log.tag.mdm_helper": "persist_log_tag_mdm_helper",
                    "log.tag.mdm_helper": "log_tag_mdm_helper",
                }[key]
                name = f"mdm_helper_lower_contract.property_context.{phase}.{source}.exact.{suffix}"
                totals[key] += as_int(lower.get(name))
    return totals


def prefix_totals(lower: dict[str, str]) -> dict[str, int]:
    totals = {"log.tag": 0, "persist.log.tag": 0}
    for phase in PHASES:
        for source in SOURCES:
            totals["log.tag"] += as_int(
                lower.get(f"mdm_helper_lower_contract.property_context.{phase}.{source}.prefix.log_tag")
            )
            totals["persist.log.tag"] += as_int(
                lower.get(f"mdm_helper_lower_contract.property_context.{phase}.{source}.prefix.persist_log_tag")
            )
    return totals


def runtime_surface(lower: dict[str, str]) -> dict[str, Any]:
    return {
        "private_property_root_present": lower.get(
            "mdm_helper_lower_contract.runtime_contract_final.property_root_present"
        )
        == "1",
        "dev_properties_present": lower.get(
            "mdm_helper_lower_contract.path.runtime_contract_final.dev_properties.exists"
        )
        == "1",
        "property_service_socket_present": lower.get(
            "mdm_helper_lower_contract.path.runtime_contract_final.property_service_socket.exists"
        )
        == "1",
        "private_esoc0_char": (
            lower.get("mdm_helper_lower_contract.path.runtime_contract_final.private_esoc0.exists") == "1"
            and lower.get("mdm_helper_lower_contract.path.runtime_contract_final.private_esoc0.is_chr") == "1"
        ),
        "private_esoc0_mode": lower.get(
            "mdm_helper_lower_contract.path.runtime_contract_final.private_esoc0.mode"
        ),
        "sys_bus_esoc_visible": lower.get(
            "mdm_helper_lower_contract.path.runtime_contract_final.sys_bus_esoc.exists"
        )
        == "1",
        "sys_bus_msm_subsys_visible": lower.get(
            "mdm_helper_lower_contract.path.runtime_contract_final.sys_bus_msm_subsys.exists"
        )
        == "1",
    }


def post_surface(manifest: dict[str, Any]) -> dict[str, Any]:
    return (manifest.get("analysis") or {}).get("post_surface") or {}


def classify(v938: dict[str, Any], v914: dict[str, Any]) -> dict[str, Any]:
    c = contract(v938)
    lower = lower_contract(v938)
    exact = exact_key_totals(lower)
    prefixes = prefix_totals(lower)
    surface = runtime_surface(lower)
    post = post_surface(v938)
    android = v914.get("classification") or {}
    android_process = android.get("process") or {}

    mdm_helper_reached_esoc = c.get("fd_esoc0_count.final") == "1"
    no_ks_or_mhi = c.get("ks_count.final") == "0" and c.get("fd_mhi_pipe_count.final") == "0"
    exact_all_zero = all(value == 0 for value in exact.values())
    generic_prefix_present = prefixes["log.tag"] > 0 or prefixes["persist.log.tag"] > 0
    runtime_ready = all(
        surface[name]
        for name in [
            "private_property_root_present",
            "dev_properties_present",
            "property_service_socket_present",
            "private_esoc0_char",
            "sys_bus_esoc_visible",
            "sys_bus_msm_subsys_visible",
        ]
    )
    android_upper_positive = bool(android.get("pass")) and bool(android.get("boot_complete"))
    android_same_lower_shape = (
        bool(android_process.get("mdm_helper_esoc0"))
        and not bool(android_process.get("current_ks"))
        and not bool(android_process.get("mhi_pipe"))
    )
    queue_lines = [
        line
        for line in post.get("wlfw_or_wlan_dmesg_hits", [])
        if "unable to queue event for SDX50M" in line
    ]

    if (
        bool(v938.get("pass"))
        and mdm_helper_reached_esoc
        and no_ks_or_mhi
        and runtime_ready
        and exact_all_zero
        and generic_prefix_present
        and android_upper_positive
        and android_same_lower_shape
    ):
        decision = "v939-exact-property-context-gap-not-sufficient"
        pass_ok = True
        reason = (
            "V938 has repaired runtime property/eSoC surfaces and reaches /dev/esoc-0; "
            "exact mdm_helper property-context entries are absent, but Android positive evidence "
            "uses the same lower post-boot shape, so the exact-key gap is not sufficient as the next blocker"
        )
        next_step = (
            "use Android read-only recapture only to refresh early timing if needed; otherwise classify "
            "mdm_helper/peripheral SDX50M queue inputs before any /dev/subsys_esoc0 or Wi-Fi HAL retry"
        )
    elif bool(v938.get("pass")) and exact_all_zero:
        decision = "v939-property-context-gap-still-review"
        pass_ok = True
        reason = "V938 captured exact property-context absence, but not enough correlated evidence to close it as non-root"
        next_step = "compare Android property/runtime evidence before materializing property-context overrides"
    else:
        decision = "v939-v938-evidence-incomplete"
        pass_ok = False
        reason = "V938 evidence does not contain the expected lower-contract surface"
        next_step = "repair or rerun V938 before selecting another live gate"

    return {
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "v938": {
            "decision": v938.get("decision"),
            "pass": v938.get("pass"),
            "reason": v938.get("reason"),
        },
        "runtime_surface": surface,
        "actor_surface": {
            "mdm_helper_reached_esoc": mdm_helper_reached_esoc,
            "no_ks_or_mhi": no_ks_or_mhi,
            "fd_esoc0_count_final": c.get("fd_esoc0_count.final"),
            "fd_mhi_pipe_count_final": c.get("fd_mhi_pipe_count.final"),
            "ks_count_final": c.get("ks_count.final"),
            "queue_failure_lines": queue_lines,
            "queue_failure_count": len(queue_lines),
        },
        "property_context": {
            "exact_totals": exact,
            "exact_all_zero": exact_all_zero,
            "prefix_totals": prefixes,
            "generic_prefix_present": generic_prefix_present,
        },
        "android_reference": {
            "decision": v914.get("decision"),
            "pass": v914.get("pass"),
            "boot_complete": android.get("boot_complete"),
            "upper_positive": android_upper_positive,
            "same_lower_postboot_shape": android_same_lower_shape,
            "process": android_process,
            "irq": android.get("irq"),
            "subsys_state_values": android.get("subsys_state_values"),
        },
        "guardrails": {
            "host_only": True,
            "device_commands_executed": False,
            "device_mutations": False,
            "daemon_start_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credentials_used": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "boot_image_write": False,
            "partition_write": False,
        },
    }


def summary(manifest: dict[str, Any]) -> str:
    classification = manifest["classification"]
    prop = classification["property_context"]
    actor = classification["actor_surface"]
    runtime = classification["runtime_surface"]
    android = classification["android_reference"]
    exact_rows = [[key, str(value)] for key, value in prop["exact_totals"].items()]
    runtime_rows = [[key, str(value)] for key, value in runtime.items()]
    actor_rows = [
        ["mdm_helper_reached_esoc", str(actor["mdm_helper_reached_esoc"])],
        ["no_ks_or_mhi", str(actor["no_ks_or_mhi"])],
        ["queue_failure_count", str(actor["queue_failure_count"])],
        ["android_upper_positive", str(android["upper_positive"])],
        ["android_same_lower_postboot_shape", str(android["same_lower_postboot_shape"])],
    ]
    return "\n".join(
        [
            "# V939 V938 Lower-Contract Classifier Summary",
            "",
            f"decision: {classification['decision']}",
            f"pass: {classification['pass']}",
            f"reason: {classification['reason']}",
            f"next: {classification['next_step']}",
            "",
            "## Actor Surface",
            "",
            markdown_table(["marker", "value"], actor_rows),
            "",
            "## Runtime Surface",
            "",
            markdown_table(["marker", "value"], runtime_rows),
            "",
            "## Exact Property-Context Totals",
            "",
            markdown_table(["property", "hits"], exact_rows),
            "",
            "## Prefix Totals",
            "",
            "```json",
            json.dumps(prop["prefix_totals"], indent=2, sort_keys=True),
            "```",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v938 = load_json(args.v938_manifest)
    v914 = load_json(args.v914_manifest)
    classification = classify(v938, v914)
    manifest = {
        "schema": "v939-v938-lower-contract-classifier",
        "created_at": now_iso(),
        "inputs": {
            "v938_manifest": str(args.v938_manifest),
            "v914_manifest": str(args.v914_manifest),
        },
        "host": collect_host_metadata(),
        "decision": classification["decision"],
        "pass": classification["pass"],
        "reason": classification["reason"],
        "next_step": classification["next_step"],
        "classification": classification,
        "guardrails": classification["guardrails"],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
