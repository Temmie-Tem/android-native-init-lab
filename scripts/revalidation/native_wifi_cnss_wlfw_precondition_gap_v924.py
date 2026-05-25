#!/usr/bin/env python3
"""V924 host-only CNSS/WLFW precondition gap classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v924-cnss-wlfw-precondition-gap")
LATEST_POINTER = Path("tmp/wifi/latest-v924-cnss-wlfw-precondition-gap.txt")
DEFAULT_V923_MANIFEST = Path("tmp/wifi/v923-mdm-helper-cnss-before-esoc-capture-live/manifest.json")
DEFAULT_V923_HELPER = Path("tmp/wifi/v923-mdm-helper-cnss-before-esoc-capture-live/native/mdm-helper-cnss-before-esoc.txt")
DEFAULT_V923_DMESG = Path("tmp/wifi/v923-mdm-helper-cnss-before-esoc-capture-live/native/post-dmesg-wifi-esoc-tail.txt")
DEFAULT_V914_MANIFEST = Path("tmp/wifi/v914-v913-android-timeline-reclassifier/manifest.json")
DEFAULT_V919_MANIFEST = Path("tmp/wifi/v919-sdx50m-soft-reset-blocker-classifier/manifest.json")

PROPERTY_CONTEXT_RE = re.compile(r'Could not find context for property "([^"]+)"')
PROPERTY_DENIAL_RE = re.compile(r'Access denied finding property "([^"]+)"')


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v923-manifest", type=Path, default=DEFAULT_V923_MANIFEST)
    parser.add_argument("--v923-helper", type=Path, default=DEFAULT_V923_HELPER)
    parser.add_argument("--v923-dmesg", type=Path, default=DEFAULT_V923_DMESG)
    parser.add_argument("--v914-manifest", type=Path, default=DEFAULT_V914_MANIFEST)
    parser.add_argument("--v919-manifest", type=Path, default=DEFAULT_V919_MANIFEST)
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
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


def count_pattern(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.IGNORECASE))


def selected_lines(text: str, pattern: str, limit: int = 30) -> list[str]:
    regex = re.compile(pattern, re.IGNORECASE)
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line in seen:
            continue
        if regex.search(line):
            seen.add(line)
            lines.append(line)
            if len(lines) >= limit:
                break
    return lines


def extract_properties(text: str) -> dict[str, Any]:
    missing_context = sorted(set(PROPERTY_CONTEXT_RE.findall(text)))
    access_denied = sorted(set(PROPERTY_DENIAL_RE.findall(text)))
    return {
        "missing_context": missing_context,
        "access_denied": access_denied,
        "missing_context_count": len(missing_context),
        "access_denied_count": len(access_denied),
        "mdm_helper_property_gap": any("mdm_helper" in item for item in missing_context + access_denied),
        "vndk_property_gap": "ro.vndk.lite" in missing_context or "ro.vndk.lite" in access_denied,
    }


def extract_v923(manifest: dict[str, Any], helper_text: str, dmesg_text: str) -> dict[str, Any]:
    contract = (((manifest.get("analysis") or {}).get("helper") or {}).get("contract") or {})
    return {
        "decision": manifest.get("decision", ""),
        "pass": bool(manifest.get("pass")),
        "cnss_diag_start_executed": bool(manifest.get("cnss_diag_start_executed")),
        "cnss_daemon_start_executed": bool(manifest.get("cnss_daemon_start_executed")),
        "wlfw_precondition_observed": bool(manifest.get("wlfw_precondition_observed")),
        "subsys_esoc0_open_attempted": bool(manifest.get("subsys_esoc0_open_attempted")),
        "wifi_bringup_executed": bool(manifest.get("wifi_bringup_executed")),
        "contract_result": contract.get("result", ""),
        "contract_reason": contract.get("reason", ""),
        "wlfw_poll_count": contract.get("wlfw_precondition_poll", ""),
        "stdout_truncated": bool((((manifest.get("analysis") or {}).get("helper") or {}).get("execns") or {}).get("stdout_truncated")),
        "netlink_cld80211_count": count_pattern(dmesg_text, r"cld80211"),
        "native_wlfw_start_count": count_pattern(helper_text + "\n" + dmesg_text, r"cnss-daemon wlfw_start"),
        "native_bdf_count": count_pattern(helper_text + "\n" + dmesg_text, r"BDF file|regdb\.bin|bdwlan\.bin"),
        "native_wlan0_exists_count": count_pattern(helper_text + "\n" + dmesg_text, r"wlan0_netdev\.exists=1|\bwlan0\b.*event"),
        "linkerconfig_missing_count": count_pattern(helper_text, r"failed to find generated linker configuration"),
        "kmsg_denied_count": count_pattern(helper_text, r"can't create /dev/kmsg"),
        "shell_quote_error_count": count_pattern(helper_text, r"no closing quote"),
        "properties": extract_properties(helper_text),
        "selected_native_lines": selected_lines(
            helper_text + "\n" + dmesg_text,
            r"cld80211|wlfw_start|BDF file|wlan0_netdev|failed to find generated linker configuration|Could not find context|Access denied finding property|can't create /dev/kmsg|no closing quote",
            limit=50,
        ),
    }


def extract_android(v914: dict[str, Any], v919: dict[str, Any]) -> dict[str, Any]:
    timeline = ((v914.get("classification") or {}).get("timeline") or {})
    return {
        "v914_decision": v914.get("decision", ""),
        "v914_pass": bool(v914.get("pass")),
        "v919_decision": v919.get("decision", ""),
        "v919_pass": bool(v919.get("pass")),
        "wlfw_start": timeline.get("wlfw_start") or {},
        "wlan_pd_indication": timeline.get("wlan_pd_indication") or {},
        "bdf_regdb": timeline.get("bdf_regdb") or {},
        "bdf_bdwlan": timeline.get("bdf_bdwlan") or {},
        "wlan0": timeline.get("wlan0") or {},
        "android_precondition_gap": bool((v919.get("classification") or {}).get("android_precondition_gap")),
    }


def decide(v923: dict[str, Any], android: dict[str, Any]) -> tuple[str, bool, str, str, dict[str, Any]]:
    native_cnss_reaches_netlink = (
        v923["pass"]
        and v923["cnss_diag_start_executed"]
        and v923["cnss_daemon_start_executed"]
        and int(v923["netlink_cld80211_count"]) > 0
    )
    native_upper_absent = (
        not v923["wlfw_precondition_observed"]
        and int(v923["native_wlfw_start_count"]) == 0
        and int(v923["native_bdf_count"]) == 0
        and int(v923["native_wlan0_exists_count"]) == 0
        and not v923["subsys_esoc0_open_attempted"]
    )
    android_upper_positive = all(
        bool((android.get(key) or {}).get("present"))
        for key in ("wlfw_start", "wlan_pd_indication", "bdf_regdb", "bdf_bdwlan", "wlan0")
    )
    namespace_gap = (
        int(v923["linkerconfig_missing_count"]) > 0
        or bool((v923["properties"] or {}).get("vndk_property_gap"))
        or bool((v923["properties"] or {}).get("mdm_helper_property_gap"))
    )
    derived = {
        "native_cnss_reaches_netlink": native_cnss_reaches_netlink,
        "native_upper_absent": native_upper_absent,
        "android_upper_positive": android_upper_positive,
        "namespace_gap": namespace_gap,
        "service_manager_or_hal_not_next": True,
        "subsys_open_not_next": native_upper_absent,
    }
    if native_cnss_reaches_netlink and native_upper_absent and android_upper_positive and namespace_gap:
        return (
            "v924-cnss-wlfw-runtime-namespace-gap",
            True,
            "native CNSS reaches cld80211 netlink but never reaches WLFW/BDF/wlan0, while Android does; native stderr still shows linkerconfig/property-context namespace gaps",
            "plan V925 as source/build-only CNSS runtime namespace/output-throttle repair before another live gate",
            derived,
        )
    if native_cnss_reaches_netlink and native_upper_absent and android_upper_positive:
        return (
            "v924-cnss-wlfw-precondition-gap-unranked",
            True,
            "native CNSS reaches cld80211 netlink but misses WLFW/BDF/wlan0; no strong namespace signature was found",
            "inspect CNSS daemon stderr and Android init/runtime inputs before another live gate",
            derived,
        )
    return (
        "v924-cnss-wlfw-gap-input-incomplete",
        False,
        f"derived={derived}",
        "repair V923/V914/V919 inputs before selecting another live gate",
        derived,
    )


def render_summary(manifest: dict[str, Any]) -> str:
    v923_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in manifest["v923"].items() if key != "selected_native_lines"]
    android_rows = [[key, json.dumps(value, ensure_ascii=False, sort_keys=True)] for key, value in manifest["android"].items()]
    derived_rows = [[key, value] for key, value in manifest["derived"].items()]
    selected_rows = [[line] for line in manifest["v923"].get("selected_native_lines", [])]
    return "\n".join([
        "# V924 CNSS/WLFW Precondition Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_contact: `{manifest['device_contact']}`",
        f"- live_action_executed: `{manifest['live_action_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Derived",
        "",
        markdown_table(["field", "value"], derived_rows),
        "",
        "## V923 Native Evidence",
        "",
        markdown_table(["field", "value"], v923_rows),
        "",
        "## Android Positive Control",
        "",
        markdown_table(["field", "value"], android_rows),
        "",
        "## Selected Native Lines",
        "",
        markdown_table(["line"], selected_rows),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v923_manifest = read_json(args.v923_manifest)
    v923_helper = read_text(args.v923_helper)
    v923_dmesg = read_text(args.v923_dmesg)
    v914_manifest = read_json(args.v914_manifest)
    v919_manifest = read_json(args.v919_manifest)
    v923 = extract_v923(v923_manifest, v923_helper, v923_dmesg)
    android = extract_android(v914_manifest, v919_manifest)
    decision, pass_ok, reason, next_step, derived = decide(v923, android)
    manifest = {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v923_manifest": str(args.v923_manifest),
            "v923_helper": str(args.v923_helper),
            "v923_dmesg": str(args.v923_dmesg),
            "v914_manifest": str(args.v914_manifest),
            "v919_manifest": str(args.v919_manifest),
        },
        "v923": v923,
        "android": android,
        "derived": derived,
        "device_contact": False,
        "live_action_executed": False,
        "subsys_esoc0_open_attempted": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {decision}")
    print(f"pass: {pass_ok}")
    print(f"reason: {reason}")
    print(f"next: {next_step}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
