#!/usr/bin/env python3
"""V1856 dry-run skeleton for a future v356 SDX50M bridge delta."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
CYCLE = "V1856"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1856-sdx50m-bridge-v356-delta-skeleton"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1856_SDX50M_BRIDGE_V356_DELTA_SKELETON_2026-06-03.md"
)
V1855_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1855-sdx50m-bridge-live-delta-classifier"
    / "manifest.json"
)


LIVE_IMPLEMENTED = False
LEGACY_V1221_REUSE_ALLOWED = False
HELPER_SURFACE = "a90_android_execns_probe v356"
SUPPORTED_MODES = ("dry-run",)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("dry-run", "live"), default="dry-run")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def collect_inputs(v1855: dict[str, Any]) -> dict[str, Any]:
    details = v1855.get("details") or {}
    requirements = details.get("delta_requirements") or {}
    image = details.get("v1853") or {}
    wrapper = details.get("v1854") or {}
    return {
        "v1855": {
            "path": rel(V1855_MANIFEST),
            "decision": v1855.get("decision", ""),
            "label": v1855.get("label", ""),
            "pass": bool(v1855.get("pass")),
        },
        "requirements": requirements,
        "image": image,
        "wrapper": wrapper,
    }


def skeleton_spec(requested_mode: str) -> dict[str, Any]:
    return {
        "cycle": CYCLE,
        "requested_mode": requested_mode,
        "supported_modes": list(SUPPORTED_MODES),
        "live_implemented": LIVE_IMPLEMENTED,
        "legacy_v1221_reuse_allowed": LEGACY_V1221_REUSE_ALLOWED,
        "helper_surface": HELPER_SURFACE,
        "default_mode": "dry-run",
        "live_denial_reason": "V1856 is only a skeleton; live support requires a later reviewed implementation unit",
        "planned_integration_points": [
            "V1220 private SDX50M cnss-daemon artifact",
            "V1846 bridge-ready v356 test image",
            "V1852 field scaffold",
            "V1854 fail-closed contract",
            "V1855 no-legacy-reuse design delta",
        ],
        "planned_classification_labels": [
            "bridge-v356-dry-run-ready",
            "bridge-v356-live-denied",
            "bridge-v356-input-review",
        ],
        "blocked_actions": [
            "Wi-Fi HAL",
            "scan/connect",
            "credential use",
            "DHCP/routes",
            "external ping",
            "direct /dev/subsys_esoc0 open",
            "PMIC/GPIO/GDSC writes",
            "eSoC ioctl/notify",
            "forced RC1 or PCI rescan",
        ],
    }


def classify(inputs: dict[str, Any], spec: dict[str, Any]) -> tuple[str, str, str, bool, int]:
    if spec["requested_mode"] != "dry-run":
        return (
            "bridge-v356-live-denied",
            "v1856-bridge-v356-live-denied",
            spec["live_denial_reason"],
            False,
            2,
        )
    v1855_ok = (
        inputs["v1855"]["pass"]
        and inputs["v1855"]["label"] == "live-delta-must-be-new-v356-bridge-not-v1221-reuse"
    )
    requirements_ok = (
        inputs["requirements"].get("must_be_new_cycle") is True
        and inputs["requirements"].get("must_not_reuse_legacy_v1221_verbatim") is True
        and inputs["requirements"].get("required_helper_surface") == "a90_android_execns_probe v356 or later with V1847 open-context labels"
    )
    image_ok = (
        inputs["image"].get("helper_marker") == HELPER_SURFACE
        and bool(inputs["image"].get("boot_sha256_ok"))
    )
    wrapper_ok = (
        inputs["wrapper"].get("supported_modes") == ["dry-run"]
        and not bool(inputs["wrapper"].get("live_mode_supported"))
        and not bool(inputs["wrapper"].get("implemented_live_runner"))
    )
    skeleton_closed = (
        spec["supported_modes"] == ["dry-run"]
        and not spec["live_implemented"]
        and not spec["legacy_v1221_reuse_allowed"]
        and spec["helper_surface"] == HELPER_SURFACE
    )
    if not v1855_ok:
        return "bridge-v356-input-review", "v1856-bridge-v356-input-review", "V1855 design delta input is missing or not passing", False, 1
    if not requirements_ok:
        return "bridge-v356-requirements-review", "v1856-bridge-v356-requirements-review", "V1855 requirements are incomplete for the v356 skeleton", False, 1
    if not image_ok:
        return "bridge-v356-image-review", "v1856-bridge-v356-image-review", "V1853 image readiness is missing or not v356", False, 1
    if not wrapper_ok:
        return "bridge-v356-wrapper-review", "v1856-bridge-v356-wrapper-review", "V1854 wrapper is not fail-closed", False, 1
    if not skeleton_closed:
        return "bridge-v356-skeleton-review", "v1856-bridge-v356-skeleton-review", "V1856 skeleton is not closed by default", False, 1
    return (
        "bridge-v356-dry-run-ready",
        "v1856-bridge-v356-dry-run-ready-host-pass",
        "V356 bridge delta skeleton is ready in dry-run mode, with live support absent and legacy V1221 reuse blocked",
        True,
        0,
    )


def render_report(result: dict[str, Any]) -> str:
    inputs = result["details"]["inputs"]
    spec = result["details"]["skeleton_spec"]
    return "\n".join([
        "# Native Init V1856 SDX50M Bridge V356 Delta Skeleton",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only dry-run skeleton for a future v356 SDX50M bridge delta",
        f"- Requested mode: `{spec['requested_mode']}`",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Inputs",
        "",
        f"- V1855: `{inputs['v1855']['decision']}` / `{inputs['v1855']['label']}`",
        f"- helper/image: `{inputs['image'].get('helper_marker')}` / boot_sha_ok `{inputs['image'].get('boot_sha256_ok')}`",
        f"- wrapper modes/live: `{inputs['wrapper'].get('supported_modes')}` / `{inputs['wrapper'].get('live_mode_supported')}`",
        "",
        "## Skeleton Contract",
        "",
        f"- supported modes: `{spec['supported_modes']}`",
        f"- live implemented: `{spec['live_implemented']}`",
        f"- legacy V1221 reuse allowed: `{spec['legacy_v1221_reuse_allowed']}`",
        f"- helper surface: `{spec['helper_surface']}`",
        f"- integration points: `{spec['planned_integration_points']}`",
        f"- planned labels: `{spec['planned_classification_labels']}`",
        f"- blocked actions: `{spec['blocked_actions']}`",
        "",
        "## Interpretation",
        "",
        "- V1856 creates the new v356 bridge delta skeleton named by V1855 but keeps it dry-run-only.",
        "- `--mode live` is a negative path and returns a failure code; no live runner exists in this unit.",
        "- Wi-Fi connect and ping remain blocked until WLFW service 69 and `wlan0` are observed first.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This skeleton did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- Next candidate is a source patch that adds non-executing argument plumbing for the private SDX50M artifact into this v356 skeleton, with dry-run still default.",
        "",
    ])


def write_outputs(out_dir: Path, report_path: Path, result: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    result["out_dir"] = rel(out_dir)
    result["report"] = rel(report_path)
    (out_dir / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(render_report(result), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir if args.out_dir.is_absolute() else REPO_ROOT / args.out_dir
    report_path = args.report if args.report.is_absolute() else REPO_ROOT / args.report
    inputs = collect_inputs(load_json(V1855_MANIFEST))
    spec = skeleton_spec(args.mode)
    label, decision, reason, passed, rc = classify(inputs, spec)
    result = {
        "cycle": CYCLE,
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(out_dir),
        "report": rel(report_path),
        "details": {
            "inputs": inputs,
            "skeleton_spec": spec,
        },
    }
    write_outputs(out_dir, report_path, result)
    print(json.dumps({key: result[key] for key in ("decision", "label", "pass", "reason", "out_dir", "report")}, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
