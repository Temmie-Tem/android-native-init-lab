#!/usr/bin/env python3
"""V1855 host-only classifier for the next SDX50M bridge live-design delta."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1855"
OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1855-sdx50m-bridge-live-delta-classifier"
REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1855_SDX50M_BRIDGE_LIVE_DELTA_CLASSIFIER_2026-06-03.md"
)
V1853_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1853-sdx50m-bridge-image-readiness"
    / "manifest.json"
)
V1854_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1854-sdx50m-bridge-fail-closed-wrapper"
    / "manifest.json"
)
V1221_SCRIPT = REPO_ROOT / "scripts" / "revalidation" / "native_wifi_private_cnss_daemon_sdx50m_live_v1221.py"


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    if not path.exists():
        raise SystemExit(f"missing input script: {path}")
    return path.read_text(encoding="utf-8")


def extract_constant(text: str, name: str) -> str:
    match = re.search(rf'^{re.escape(name)}\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return match.group(1) if match else ""


def collect_legacy_script(text: str) -> dict[str, Any]:
    return {
        "path": rel(V1221_SCRIPT),
        "exists": V1221_SCRIPT.exists(),
        "helper_marker": extract_constant(text, "HELPER_MARKER_V253"),
        "helper_sha256": extract_constant(text, "HELPER_SHA256_V253"),
        "private_cnss_flag": extract_constant(text, "PRIVATE_CNSS_FLAG"),
        "private_cnss_path": extract_constant(text, "PRIVATE_CNSS_PATH"),
        "patched_cnss_sha256": extract_constant(text, "PATCHED_CNSS_SHA256"),
        "uses_esoc_dev_node_flag": "ESOC_DEV_NODE_FLAG" in text,
        "removes_subsys_esoc0_flag": "SUBSYS_ESOC0_FLAG" in text and "continue" in text,
        "mentions_wifi_guardrail": "No Wi-Fi HAL" in text and "external ping" in text,
        "has_plan_mode": "command\") == \"plan\"" in text,
        "has_live_child_command": "pm_cnss_child_command" in text and "write_child_script" in text,
    }


def collect_v1853(manifest: dict[str, Any]) -> dict[str, Any]:
    image = ((manifest.get("details") or {}).get("v1846_image") or {})
    handoff = ((manifest.get("details") or {}).get("v1847_handoff") or {})
    return {
        "path": rel(V1853_MANIFEST),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label", ""),
        "pass": bool(manifest.get("pass")),
        "helper_marker": image.get("helper_marker", ""),
        "boot_image": image.get("boot_image", ""),
        "boot_sha256_ok": bool(image.get("boot_sha256_ok")),
        "baseline_open_path": handoff.get("open_context_path", ""),
        "baseline_service69": bool(handoff.get("lower_service69_progress")),
        "baseline_wlan0": bool(handoff.get("lower_wlan0_present")),
    }


def collect_v1854(manifest: dict[str, Any]) -> dict[str, Any]:
    contract = ((manifest.get("details") or {}).get("contract") or {})
    return {
        "path": rel(V1854_MANIFEST),
        "decision": manifest.get("decision", ""),
        "label": manifest.get("label", ""),
        "pass": bool(manifest.get("pass")),
        "supported_modes": contract.get("supported_modes") or [],
        "live_mode_supported": bool(contract.get("live_mode_supported")),
        "implemented_live_runner": bool(contract.get("implemented_live_runner")),
        "requires_new_cycle_for_live": bool(contract.get("requires_new_cycle_for_live")),
        "forbidden_actions": contract.get("forbidden_actions") or [],
    }


def delta_requirements() -> dict[str, Any]:
    return {
        "must_be_new_cycle": True,
        "must_not_modify_v1854_to_enable_live": True,
        "must_not_reuse_legacy_v1221_verbatim": True,
        "required_helper_surface": "a90_android_execns_probe v356 or later with V1847 open-context labels",
        "required_artifacts": [
            "V1220 private SDX50M cnss-daemon artifact",
            "V1846/V1853 bridge-ready test image",
            "V1852 dry-run field scaffold",
            "V1854 fail-closed wrapper negative test",
        ],
        "required_live_guards": [
            "one-run bounded timeout",
            "rollback to v724 with filtered version check and selftest fail=0",
            "PM register/connect rc=0 before interpreting lower state",
            "PM-service path must select /dev/subsys_esoc0; no direct host open",
            "stop on no GPIO142/PCIe/MHI/WLFW/wlan0 response",
            "stop on modem crash/down marker increase",
            "Wi-Fi HAL/scan/connect still forbidden until WLFW service 69 and wlan0",
        ],
        "blocked_legacy_traits": [
            "helper v253 surface",
            "legacy child-command patch chain",
            "implicit live path inside historical V1221 script",
        ],
    }


def classify(details: dict[str, Any]) -> tuple[str, str, str, bool]:
    legacy = details["legacy_v1221"]
    image = details["v1853"]
    wrapper = details["v1854"]
    requirements = details["delta_requirements"]
    wrapper_closed = (
        wrapper["pass"]
        and wrapper["label"] == "sdx50m-bridge-wrapper-fail-closed-ready"
        and wrapper["supported_modes"] == ["dry-run"]
        and not wrapper["live_mode_supported"]
        and not wrapper["implemented_live_runner"]
        and wrapper["requires_new_cycle_for_live"]
    )
    image_current = (
        image["pass"]
        and image["label"] == "bridge-test-image-ready-no-rebuild"
        and image["helper_marker"] == "a90_android_execns_probe v356"
        and image["boot_sha256_ok"]
        and image["baseline_open_path"] == "/dev/subsys_modem"
        and not image["baseline_service69"]
        and not image["baseline_wlan0"]
    )
    legacy_is_old_live_path = (
        legacy["exists"]
        and legacy["helper_marker"] == "a90_android_execns_probe v253"
        and legacy["private_cnss_flag"] == "--pm-observer-private-cnss-daemon-sdx50m"
        and legacy["private_cnss_path"] == "/cache/bin/cnss-daemon.sdx50m"
        and legacy["has_live_child_command"]
        and legacy["mentions_wifi_guardrail"]
    )
    requirements_safe = (
        requirements["must_be_new_cycle"]
        and requirements["must_not_modify_v1854_to_enable_live"]
        and requirements["must_not_reuse_legacy_v1221_verbatim"]
        and "Wi-Fi HAL/scan/connect still forbidden until WLFW service 69 and wlan0" in requirements["required_live_guards"]
    )
    if not wrapper_closed:
        return "wrapper-review", "v1855-wrapper-review", "V1854 fail-closed wrapper is missing or no longer closed", False
    if not image_current:
        return "image-review", "v1855-image-review", "V1853 image readiness is missing or stale", False
    if not legacy_is_old_live_path:
        return "legacy-review", "v1855-legacy-review", "Legacy V1221 private route script was not recognized as the old live path", False
    if not requirements_safe:
        return "requirements-review", "v1855-requirements-review", "Live delta requirements are incomplete or unsafe", False
    return (
        "live-delta-must-be-new-v356-bridge-not-v1221-reuse",
        "v1855-live-delta-must-be-new-v356-bridge-not-v1221-reuse-host-pass",
        "The next live-capable unit must be a new reviewed V1846/v356 bridge delta; V1854 stays fail-closed and the legacy V1221 v253 live path must not be reused verbatim",
        True,
    )


def render_report(result: dict[str, Any]) -> str:
    legacy = result["details"]["legacy_v1221"]
    image = result["details"]["v1853"]
    wrapper = result["details"]["v1854"]
    requirements = result["details"]["delta_requirements"]
    return "\n".join([
        "# Native Init V1855 SDX50M Bridge Live Delta Classifier",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only design-delta classifier for any future live-capable SDX50M bridge unit",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Current Guard",
        "",
        f"- V1854: `{wrapper['decision']}` / `{wrapper['label']}` modes `{wrapper['supported_modes']}` live_supported `{wrapper['live_mode_supported']}`",
        f"- V1853: `{image['decision']}` / helper `{image['helper_marker']}` boot_sha_ok `{image['boot_sha256_ok']}` baseline `{image['baseline_open_path']}`",
        "",
        "## Legacy Route",
        "",
        f"- script: `{legacy['path']}` exists `{legacy['exists']}`",
        f"- helper/private flag/path: `{legacy['helper_marker']}` / `{legacy['private_cnss_flag']}` / `{legacy['private_cnss_path']}`",
        f"- legacy traits: esoc_dev_node_flag `{legacy['uses_esoc_dev_node_flag']}`, removes_subsys_esoc0_flag `{legacy['removes_subsys_esoc0_flag']}`, live_child_command `{legacy['has_live_child_command']}`",
        "",
        "## Delta Requirements",
        "",
        f"- must be new cycle: `{requirements['must_be_new_cycle']}`",
        f"- must not modify V1854 to enable live: `{requirements['must_not_modify_v1854_to_enable_live']}`",
        f"- must not reuse V1221 verbatim: `{requirements['must_not_reuse_legacy_v1221_verbatim']}`",
        f"- required helper surface: `{requirements['required_helper_surface']}`",
        f"- required artifacts: `{requirements['required_artifacts']}`",
        f"- required live guards: `{requirements['required_live_guards']}`",
        f"- blocked legacy traits: `{requirements['blocked_legacy_traits']}`",
        "",
        "## Interpretation",
        "",
        "- V1221 remains useful as historical proof that SDX50M selection can reach PM-service eSoC powerup, not as the current live runner.",
        "- The current candidate must be based on the V1846/v356 open-context image and V1852 field scaffold so PM selection and lower response are distinguishable.",
        "- V1854 must remain fail-closed; live support needs a separate reviewed source/build unit and cannot be hidden behind a mode switch.",
        "- Wi-Fi connect and ping remain blocked until WLFW service 69 and `wlan0` are observed first.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This classifier did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- Next source/build candidate: V1856 new v356 bridge delta skeleton that imports the fail-closed contract and has no live default.",
        "",
    ])


def main() -> int:
    details = {
        "legacy_v1221": collect_legacy_script(read_text(V1221_SCRIPT)),
        "v1853": collect_v1853(load_json(V1853_MANIFEST)),
        "v1854": collect_v1854(load_json(V1854_MANIFEST)),
        "delta_requirements": delta_requirements(),
    }
    label, decision, reason, passed = classify(details)
    result = {
        "cycle": CYCLE,
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(OUT_DIR),
        "report": rel(REPORT_PATH),
        "details": details,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(render_report(result), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("decision", "label", "pass", "reason", "out_dir", "report")}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
