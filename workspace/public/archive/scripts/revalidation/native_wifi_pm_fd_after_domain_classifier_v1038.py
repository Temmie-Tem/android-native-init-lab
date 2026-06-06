#!/usr/bin/env python3
"""V1038 host-only classifier for PM fd gap after domain proof."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1038-pm-fd-after-domain-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v1038-pm-fd-after-domain-classifier.txt")
DEFAULT_V1024_MANIFEST = Path("tmp/wifi/v1024-fast-fd-contract-classifier/manifest.json")
DEFAULT_ANDROID_SAMPLE = Path(
    "tmp/wifi/v1024-fast-fd-android-timing-handoff-live-20260526-181232/"
    "v1022-early-android-pm-esoc-timing/android/commands/sample-loop.txt"
)
DEFAULT_V1028_MANIFEST = Path("tmp/wifi/v1028-pm-proxy-helper-modem-get-classifier/manifest.json")
DEFAULT_V1029_MANIFEST = Path("tmp/wifi/v1029-pm-runtime-input-delta/manifest.json")
DEFAULT_V1036_MANIFEST = Path("tmp/wifi/v1036-pm-selinux-domain-proof-v176/manifest.json")
DEFAULT_V1037_MANIFEST = Path("tmp/wifi/v1037-pm-runtime-domain-guard-live-v176/manifest.json")
DEFAULT_V1037_DMESG = Path("tmp/wifi/v1037-pm-runtime-domain-guard-live-v176/native/post-dmesg-wifi-esoc-tail.txt")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")

ANDROID_DOMAINS = {
    "pm_proxy_helper": "u:r:per_proxy_helper:s0",
    "pm-service": "u:r:vendor_per_mgr:s0",
    "pm-proxy": "u:r:vendor_per_proxy:s0",
    "mdm_helper": "u:r:vendor_mdm_helper:s0",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v1024-manifest", type=Path, default=DEFAULT_V1024_MANIFEST)
    parser.add_argument("--android-sample", type=Path, default=DEFAULT_ANDROID_SAMPLE)
    parser.add_argument("--v1028-manifest", type=Path, default=DEFAULT_V1028_MANIFEST)
    parser.add_argument("--v1029-manifest", type=Path, default=DEFAULT_V1029_MANIFEST)
    parser.add_argument("--v1036-manifest", type=Path, default=DEFAULT_V1036_MANIFEST)
    parser.add_argument("--v1037-manifest", type=Path, default=DEFAULT_V1037_MANIFEST)
    parser.add_argument("--v1037-dmesg", type=Path, default=DEFAULT_V1037_DMESG)
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


def strish(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


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


def android_surface(v1024: dict[str, Any], sample: str) -> dict[str, Any]:
    classification = v1024.get("classification") or {}
    early = classification.get("early") or {}
    late = classification.get("late") or {}
    fd = early.get("fd") or {}
    chain = late.get("chain") or {}
    actor_rows: dict[str, dict[str, Any]] = {}
    for actor, domain in ANDROID_DOMAINS.items():
        actor_rows[actor] = {
            "expected_domain": domain,
            "domain_present": domain in sample,
            "fd_present": (
                boolish(fd.get("pm_proxy_helper_subsys_modem_fd"))
                if actor == "pm_proxy_helper"
                else boolish(fd.get("pm_service_subsys_modem_fd"))
                if actor == "pm-service"
                else boolish(fd.get("mdm_helper_esoc0_fd"))
                if actor == "mdm_helper"
                else domain in sample
            ),
        }
    return {
        "decision": v1024.get("decision", ""),
        "pass": boolish(v1024.get("pass")),
        "actors": actor_rows,
        "wlfw_chain": boolish(chain.get("wlfw_chain")),
        "evidence_lines": selected_lines(
            sample,
            r"TARGET_PROC tag=(pm_proxy_helper|pm-service|pm-proxy|mdm_helper)|/dev/(subsys_modem|esoc-0)",
            limit=16,
        ),
    }


def v1036_surface(v1036: dict[str, Any]) -> dict[str, Any]:
    cases = v1036.get("cases") if isinstance(v1036.get("cases"), list) else []
    case_map: dict[str, dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict):
            continue
        context = strish(case.get("context"))
        case_map[context] = {
            "result": case.get("result", ""),
            "postexec_match": boolish(case.get("postexec_match")),
            "postexec_current": case.get("postexec_current", ""),
        }
    return {
        "decision": v1036.get("decision", ""),
        "pass": boolish(v1036.get("pass")),
        "pm_domain_proof": boolish(v1036.get("pm_domain_proof")),
        "pm_required_match_count": int(strish(v1036.get("pm_required_match_count") or 0)),
        "vendor_per_proxy_static_proof": boolish(case_map.get("u:r:vendor_per_proxy:s0", {}).get("postexec_match")),
        "case_map": case_map,
    }


def v1037_surface(v1037: dict[str, Any], dmesg: str) -> dict[str, Any]:
    helper = ((v1037.get("analysis") or {}).get("helper") or {})
    contract = helper.get("contract") or {}
    guard = v1037.get("runtime_domain_guard") or {}
    matched = guard.get("matched") if isinstance(guard.get("matched"), dict) else {}
    return {
        "decision": v1037.get("decision", ""),
        "pass": boolish(v1037.get("pass")),
        "guard_blocked": boolish(v1037.get("runtime_domain_guard_blocked")),
        "guard_matched_count": int(strish(v1037.get("runtime_domain_guard_matched_count") or 0)),
        "matched": matched,
        "pm_proxy_expected": ((matched.get("pm_proxy") or {}).get("attr_exec_expected", "")),
        "pm_proxy_observed": ((matched.get("pm_proxy") or {}).get("attr_exec_observed", "")),
        "pm_proxy_helper_fd_count": strish(contract.get("pm_proxy_helper_subsys_modem_fd_count")),
        "per_mgr_fd_count": strish(contract.get("per_mgr_subsys_modem_fd_count")),
        "mdm_helper_esoc0_fd_count": strish(contract.get("mdm_helper_esoc0_fd_count")),
        "pm_full_contract_seen": boolish(contract.get("pm_full_contract_seen")),
        "pm_full_contract_poll_count": int(strish(contract.get("pm_full_contract_poll_count") or 0)),
        "service_manager_started": boolish(contract.get("service_manager_started")),
        "cnss_daemon_started": boolish(contract.get("cnss_daemon_started")),
        "subsys_esoc0_open_attempted": boolish(contract.get("subsys_esoc0_open_attempted")),
        "wifi_hal_started": boolish(contract.get("wifi_hal_started")),
        "scan_connect_linkup": boolish(contract.get("scan_connect_linkup")),
        "credentials": boolish(contract.get("credentials")),
        "external_ping": boolish(contract.get("external_ping")),
        "result": contract.get("result", ""),
        "pm_proxy_helper_postflight_safe": boolish(contract.get("pm_proxy_helper.postflight_safe")),
        "cleanup_reboot_executed": boolish(v1037.get("cleanup_reboot_executed")),
        "modem_get_lines": selected_lines(
            dmesg,
            r"pm_proxy_helper.*(__subsystem_get:\s+modem|Changing subsys fw_name to modem|modem: loading)",
            limit=8,
        ),
    }


def helper_source_surface(source: str) -> dict[str, Any]:
    pm_service_and_proxy_share_mgr = bool(
        re.search(
            r'streq\(target,\s*"/vendor/bin/pm-service"\).*?'
            r'streq\(target,\s*"/vendor/bin/pm-proxy"\).*?'
            r'return\s+"u:r:vendor_per_mgr:s0"',
            source,
            re.DOTALL,
        )
    )
    pm_proxy_separate_domain = bool(
        re.search(
            r'streq\(target,\s*"/vendor/bin/pm-proxy"\).*?'
            r'return\s+"u:r:vendor_per_proxy:s0"',
            source,
            re.DOTALL,
        )
    )
    return {
        "pm_service_and_proxy_share_vendor_per_mgr": pm_service_and_proxy_share_mgr,
        "pm_proxy_separate_vendor_per_proxy": pm_proxy_separate_domain,
        "allowlist_has_vendor_per_proxy": '"u:r:vendor_per_proxy:s0"' in source,
        "helper_version_v176": 'EXECNS_VERSION = "a90_android_execns_probe v176"' in source
        or 'a90_android_execns_probe v176' in source,
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1024 = load_json(args.v1024_manifest)
    v1028 = load_json(args.v1028_manifest)
    v1029 = load_json(args.v1029_manifest)
    v1036 = load_json(args.v1036_manifest)
    v1037 = load_json(args.v1037_manifest)
    android = android_surface(v1024, read_text(args.android_sample))
    domain = v1036_surface(v1036)
    live = v1037_surface(v1037, read_text(args.v1037_dmesg))
    helper = helper_source_surface(read_text(args.helper_source))

    android_positive = (
        android["pass"]
        and android["decision"] == "v1024-android-pm-esoc-fd-contract-captured"
        and android["wlfw_chain"]
        and android["actors"]["pm_proxy_helper"]["fd_present"]
        and android["actors"]["pm-service"]["fd_present"]
        and android["actors"]["pm-proxy"]["domain_present"]
        and android["actors"]["mdm_helper"]["fd_present"]
    )
    previous_domain_gap_hypothesis = (
        v1028.get("decision") == "v1028-pm-proxy-helper-modem-get-blocker-classified"
        and v1029.get("decision") == "v1029-pm-actor-selinux-runtime-domain-gap-classified"
    )
    pm_domains_static_proven = (
        domain["pass"]
        and domain["pm_domain_proof"]
        and domain["pm_required_match_count"] >= 4
        and domain["vendor_per_proxy_static_proof"]
    )
    v1037_domain_gap_removed = (
        live["pass"]
        and not live["guard_blocked"]
        and live["guard_matched_count"] >= 4
    )
    v1037_fd_gap_reproduced = (
        live["pm_proxy_helper_fd_count"] == "0"
        and live["per_mgr_fd_count"] == "0"
        and live["mdm_helper_esoc0_fd_count"] == "1"
        and not live["pm_full_contract_seen"]
        and live["pm_full_contract_poll_count"] > 0
        and bool(live["modem_get_lines"])
    )
    lower_guardrails_clean = (
        not live["service_manager_started"]
        and not live["cnss_daemon_started"]
        and not live["subsys_esoc0_open_attempted"]
        and not live["wifi_hal_started"]
        and not live["scan_connect_linkup"]
        and not live["credentials"]
        and not live["external_ping"]
        and live["cleanup_reboot_executed"]
    )
    pm_proxy_context_mismatch = (
        android["actors"]["pm-proxy"]["expected_domain"] == "u:r:vendor_per_proxy:s0"
        and live["pm_proxy_expected"] == "u:r:vendor_per_mgr:s0"
        and live["pm_proxy_observed"] == "u:r:vendor_per_mgr:s0"
        and helper["pm_service_and_proxy_share_vendor_per_mgr"]
        and not helper["pm_proxy_separate_vendor_per_proxy"]
        and helper["allowlist_has_vendor_per_proxy"]
    )

    checks = {
        "v1024_android_positive_pm_fd_contract": android_positive,
        "v1028_v1029_previous_hypothesis_present": previous_domain_gap_hypothesis,
        "v1036_pm_domains_static_proven": pm_domains_static_proven,
        "v1037_runtime_domain_gap_removed": v1037_domain_gap_removed,
        "v1037_pm_fd_gap_reproduced": v1037_fd_gap_reproduced,
        "v1037_lower_guardrails_clean": lower_guardrails_clean,
        "pm_proxy_service_default_context_mismatch": pm_proxy_context_mismatch,
    }

    if all(checks.values()):
        decision = "v1038-pm-fd-gap-after-domain-proof-classified"
        passed = True
        route = "v1039-pm-proxy-context-parity-support"
        reason = (
            "V1037 removed the PM runtime-domain blocker, but the PM fd contract still fails; "
            "one concrete Android/native parity gap remains because pm-proxy still runs as vendor_per_mgr "
            "instead of Android's vendor_per_proxy"
        )
        next_step = (
            "V1039 should source/build helper v177 with pm-proxy mapped to u:r:vendor_per_proxy:s0 "
            "and add focused PM fd/wchan capture before another bounded live retry"
        )
    elif v1037_domain_gap_removed and v1037_fd_gap_reproduced:
        decision = "v1038-pm-fd-gap-after-domain-proof-review"
        passed = True
        route = "pm-fd-deep-capture-before-retry"
        reason = "PM fd gap remains after domain proof, but the pm-proxy context mismatch evidence is incomplete"
        next_step = "Add focused PM fd/wchan capture and recheck helper service-default mappings before live retry"
    else:
        missing = ", ".join(name for name, ok in checks.items() if not ok)
        decision = "v1038-inputs-incomplete"
        passed = False
        route = "repair-input-evidence"
        reason = f"required evidence missing or contradictory: {missing}"
        next_step = "Repair V1024/V1036/V1037 evidence before helper changes"

    return {
        "decision": decision,
        "pass": passed,
        "route": route,
        "reason": reason,
        "next_step": next_step,
        "checks": checks,
        "android": android,
        "domain": domain,
        "live": live,
        "helper": helper,
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
    android_rows = [
        [actor, data["expected_domain"], data["domain_present"], data["fd_present"]]
        for actor, data in c["android"]["actors"].items()
    ]
    live = c["live"]
    helper = c["helper"]
    return "\n".join(
        [
            "# V1038 PM fd Gap After Domain Proof",
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
            "## Android PM Contract",
            "",
            markdown_table(["actor", "Android domain", "domain present", "fd present"], android_rows),
            "",
            "## V1037 Native Live Delta",
            "",
            markdown_table(
                ["item", "value"],
                [
                    ["runtime guard blocked", live["guard_blocked"]],
                    ["runtime guard matched count", live["guard_matched_count"]],
                    ["pm-proxy expected context", live["pm_proxy_expected"]],
                    ["pm-proxy observed context", live["pm_proxy_observed"]],
                    ["pm_proxy_helper /dev/subsys_modem fd count", live["pm_proxy_helper_fd_count"]],
                    ["pm-service /dev/subsys_modem fd count", live["per_mgr_fd_count"]],
                    ["mdm_helper /dev/esoc-0 fd count", live["mdm_helper_esoc0_fd_count"]],
                    ["PM full contract seen", live["pm_full_contract_seen"]],
                    ["service-manager started", live["service_manager_started"]],
                    ["/dev/subsys_esoc0 open attempted", live["subsys_esoc0_open_attempted"]],
                    ["cleanup reboot", live["cleanup_reboot_executed"]],
                ],
            ),
            "",
            "## Helper Source Surface",
            "",
            markdown_table(["item", "value"], [[key, value] for key, value in helper.items()]),
            "",
            "## Android Evidence Lines",
            "",
            "\n".join(f"- `{line}`" for line in c["android"]["evidence_lines"]) or "- none",
            "",
            "## V1037 Modem-Get Lines",
            "",
            "\n".join(f"- `{line}`" for line in live["modem_get_lines"]) or "- none",
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "plan":
        classification = {
            "decision": "v1038-pm-fd-after-domain-classifier-plan-ready",
            "pass": True,
            "route": "host-only-v1024-v1036-v1037-comparison",
            "reason": "plan-only; no live device contact required",
            "next_step": "run V1038 against existing PM fd/domain evidence",
            "checks": {},
            "android": {"actors": {}, "evidence_lines": []},
            "domain": {},
            "live": {
                "guard_blocked": False,
                "guard_matched_count": 0,
                "pm_proxy_expected": "",
                "pm_proxy_observed": "",
                "pm_proxy_helper_fd_count": "",
                "per_mgr_fd_count": "",
                "mdm_helper_esoc0_fd_count": "",
                "pm_full_contract_seen": False,
                "service_manager_started": False,
                "subsys_esoc0_open_attempted": False,
                "cleanup_reboot_executed": False,
                "modem_get_lines": [],
            },
            "helper": {},
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
