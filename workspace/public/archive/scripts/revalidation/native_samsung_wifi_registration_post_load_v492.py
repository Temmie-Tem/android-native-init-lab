#!/usr/bin/env python3
"""V492 post-load Samsung ISehWifi/default registration proof.

This runner reuses the V483 bounded Samsung registration path, but requires a
V491 manifest proving that `u:r:hal_wifi_default:s0` survives the static
post-exec domain proof after V490 policy load.

It starts only the private service-manager/hwservicemanager/Samsung Wi-Fi
HAL/CNSS surface and runs `lshal wait` for Samsung ISehWifi/default targets.
It does not call Wi-Fi HAL methods, scan/connect/link-up, read credentials,
run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import native_samsung_wifi_registration_v483 as v483


base = v483.base
_BASE_PARSE_ARGS = base.parse_args
_BASE_BUILD_PLAN = base.build_plan
_BASE_BUILD_CHECKS = base.build_checks
_BASE_DECIDE = base.decide
_BASE_REFUSAL_MANIFEST = base.refusal_manifest
_BASE_RENDER_SUMMARY = base.render_summary

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v492-samsung-registration-post-load")
base.DEFAULT_HELPER_SHA256 = "5bc491c7ed0c4da498c6ee16568004dd886df577edd5f8cbebd50fb0740db10c"
base.HELPER_LABEL = "v48"
base.APPROVAL_PHRASE = (
    "approve v492 post-load Samsung ISehWifi/default registration only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)


def _extract_v491_manifest_arg() -> Path | None:
    value: str | None = None
    stripped = [sys.argv[0]]
    index = 1
    while index < len(sys.argv):
        item = sys.argv[index]
        if item == "--v491-manifest":
            if index + 1 >= len(sys.argv):
                raise SystemExit("--v491-manifest requires a path")
            value = sys.argv[index + 1]
            index += 2
            continue
        if item.startswith("--v491-manifest="):
            value = item.split("=", 1)[1]
            index += 1
            continue
        stripped.append(item)
        index += 1
    sys.argv[:] = stripped
    return Path(value) if value else None


def parse_args() -> base.argparse.Namespace:
    v491_manifest = _extract_v491_manifest_arg()
    args = _BASE_PARSE_ARGS()
    args.v491_manifest = v491_manifest
    return args


def _load_v491_manifest(args: base.argparse.Namespace) -> dict[str, Any]:
    path = getattr(args, "v491_manifest", None)
    result: dict[str, Any] = {
        "path": str(path) if path else "",
        "present": False,
        "valid": False,
        "decision": "",
        "hal_wifi_domain_match": False,
        "matched_cases": [],
        "reason": "missing-v491-manifest",
    }
    if path is None:
        return result
    if not path.exists():
        result["reason"] = "v491-manifest-not-found"
        return result
    result["present"] = True
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - preserve parse issue
        result["reason"] = f"v491-manifest-read-failed-{exc}"
        return result
    result["decision"] = str(manifest.get("decision", ""))
    cases = manifest.get("cases") or []
    matched = [
        {
            "context": case.get("context", ""),
            "attr_mode": case.get("attr_mode", ""),
            "postexec_current": case.get("postexec_current", ""),
        }
        for case in cases
        if case.get("postexec_match") is True
    ]
    result["matched_cases"] = matched
    result["hal_wifi_domain_match"] = any(
        case.get("context") == "u:r:hal_wifi_default:s0"
        for case in cases
        if case.get("postexec_match") is True
    )
    result["valid"] = (
        manifest.get("decision") == "v491-post-load-domain-handoff-present"
        and manifest.get("pass") is True
        and manifest.get("policy_load_executed") is False
        and manifest.get("init_reexec_executed") is False
        and manifest.get("daemon_start_executed") is False
        and manifest.get("wifi_hal_start_executed") is False
        and manifest.get("wifi_bringup_executed") is False
        and result["hal_wifi_domain_match"]
    )
    result["reason"] = "v491-hal-wifi-domain-ready" if result["valid"] else "v491-hal-wifi-domain-required"
    return result


def build_plan(args: base.argparse.Namespace) -> dict[str, Any]:
    plan = _BASE_BUILD_PLAN(args)
    plan["helper_version"] = base.HELPER_LABEL
    plan["v491_post_load_domain_manifest"] = str(getattr(args, "v491_manifest", "") or "")
    plan["precondition"] = {
        "decision": "v491-post-load-domain-handoff-present",
        "required_context": "u:r:hal_wifi_default:s0",
        "required_postexec_match": True,
    }
    plan["scope"] = {
        "starts": ["private servicemanager", "private hwservicemanager", "Samsung Wi-Fi HAL", "CNSS"],
        "queries": ["lshal wait vendor.samsung.hardware.wifi@2.x::ISehWifi/default"],
        "blocks": ["Wi-Fi HAL methods", "scan/connect/link-up", "credentials", "DHCP", "routes", "external ping"],
    }
    return plan


def build_checks(args: base.argparse.Namespace,
                 store: base.EvidenceStore,
                 steps: list[base.Step],
                 android_manifest: dict[str, Any]) -> list[base.Check]:
    checks = _BASE_BUILD_CHECKS(args, store, steps, android_manifest)
    if args.command == "plan":
        return checks
    v491 = _load_v491_manifest(args)
    base.add_check(
        checks,
        "v491-hal-wifi-domain-ready",
        "pass" if v491["valid"] else "blocked",
        "blocker",
        f"path={v491['path']} present={v491['present']} decision={v491['decision']} hal_match={v491['hal_wifi_domain_match']} reason={v491['reason']}",
        [str(v491["matched_cases"])[:512]],
        "run V490 and V491 first; pass the V491 handoff-present manifest to --v491-manifest",
    )
    return checks


def _v492_label(decision: str) -> str:
    return (
        decision
        .replace("v483-samsung-registration-property-shim", "v492-samsung-registration-post-load")
        .replace("v479-samsung-wifi-registration-selinux-context", "v492-samsung-registration-post-load")
        .replace("v473-samsung-wifi-registration-v471-property", "v492-samsung-registration-post-load")
        .replace("v469-samsung-wifi-registration", "v492-samsung-registration-post-load")
    )


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, daemon_started = _BASE_DECIDE(args, checks, live_result, post)
    return (
        _v492_label(decision),
        pass_ok,
        reason.replace("V483", "V492").replace("v42", "v48"),
        next_step.replace("V483", "V492").replace("v42", "v48"),
        daemon_started,
    )


def refusal_manifest(args: base.argparse.Namespace, android_manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = _BASE_REFUSAL_MANIFEST(args, android_manifest)
    manifest["decision"] = _v492_label(str(manifest["decision"]))
    manifest["next_step"] = "rerun with exact V492 approval after V491 HAL-domain proof"
    manifest["required_approval_phrase"] = base.APPROVAL_PHRASE
    manifest["v491_post_load_domain"] = _load_v491_manifest(args)
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    summary = _BASE_RENDER_SUMMARY(manifest).replace(
        "# V483 Samsung ISehWifi/default Registration With Private Property-Service Shim",
        "# V492 Post-Load Samsung ISehWifi/default Registration",
        1,
    )
    v491 = manifest.get("v491_post_load_domain")
    if v491:
        summary += "\n\n## V491 Precondition\n\n"
        summary += base.markdown_table(["item", "value"], [
            ["manifest", v491.get("path", "")],
            ["valid", str(v491.get("valid", ""))],
            ["decision", v491.get("decision", "")],
            ["hal_wifi_domain_match", str(v491.get("hal_wifi_domain_match", ""))],
        ])
        summary += "\n"
    return summary


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = v483.v479.v473.v469.build_manifest(args, store)
    manifest["decision"] = _v492_label(str(manifest["decision"]))
    manifest["required_approval_phrase"] = base.APPROVAL_PHRASE
    manifest["v491_post_load_domain"] = _load_v491_manifest(args)
    manifest["plan"] = build_plan(args)
    return manifest


base.parse_args = parse_args
base.build_plan = build_plan
base.build_checks = build_checks
base.decide = decide
base.refusal_manifest = refusal_manifest
base.render_summary = render_summary
base.build_manifest = build_manifest
v483.v479.v473.v469.parse_args = parse_args
v483.v479.v473.v469.build_plan = build_plan
v483.v479.v473.v469.build_checks = build_checks
v483.v479.v473.v469.decide = decide
v483.v479.v473.v469.refusal_manifest = refusal_manifest
v483.v479.v473.v469.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
