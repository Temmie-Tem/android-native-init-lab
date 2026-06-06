#!/usr/bin/env python3
"""V1033 current-boot PM SELinux domain proof wrapper.

Runs the V491 post-load static exec-domain proof over the PM domains that V1032
blocked before actor exec. This proof starts no PM actors and performs no Wi-Fi
bring-up; it only writes child-local SELinux procattrs and re-execs the static
helper probe after a valid V490 current-boot policy-load proof.
"""

from __future__ import annotations

from pathlib import Path

import native_selinux_post_load_domain_proof_v491 as base


ORIGINAL_DECIDE = base.decide
ORIGINAL_RENDER_SUMMARY = base.render_summary
ORIGINAL_BUILD_MANIFEST = base.build_manifest

HELPER_SHA256_V175 = "9036bb15ced9fb1098c4375c15c2c729502c841574ae14798fb331fc29c89e42"

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1033-pm-selinux-domain-proof")
base.DEFAULT_HELPER_SHA256 = HELPER_SHA256_V175
base.APPROVAL_PHRASE = (
    "approve v1033 PM SELinux domain proof only; "
    "no daemon start and no Wi-Fi bring-up"
)
base.CONTEXTS = (
    "u:r:per_proxy_helper:s0",
    "u:r:vendor_per_mgr:s0",
    "u:r:vendor_per_proxy:s0",
    "u:r:vendor_mdm_helper:s0",
    "u:r:vendor_wcnss_service:s0",
)
base.ATTR_MODES = ("exec",)

PM_REQUIRED_CONTEXTS = (
    "u:r:per_proxy_helper:s0",
    "u:r:vendor_per_mgr:s0",
    "u:r:vendor_per_proxy:s0",
    "u:r:vendor_mdm_helper:s0",
)


def _map_decision(decision: str) -> str:
    mapping = {
        "v491-post-load-domain-proof-plan-ready": "v1033-pm-selinux-domain-proof-plan-ready",
        "v491-post-load-domain-proof-blocked": "v1033-pm-selinux-domain-proof-blocked",
        "v491-post-load-domain-proof-preflight-ready": "v1033-pm-selinux-domain-proof-preflight-ready",
        "v491-post-load-domain-proof-approval-required": "v1033-pm-selinux-domain-proof-approval-required",
        "v491-post-load-domain-handoff-present": "v1033-pm-selinux-domain-handoff-present",
        "v491-post-load-domain-kernel-stuck": "v1033-pm-selinux-domain-kernel-stuck",
    }
    return mapping.get(decision, decision.replace("v491", "v1033"))


def decide(args, checks, cases):
    decision, pass_ok, reason, next_step = ORIGINAL_DECIDE(args, checks, cases)
    if cases:
        matched = {case["context"]: bool(case["postexec_match"]) for case in cases}
        case_by_context = {case["context"]: case for case in cases}
        pm_match_count = sum(1 for context in PM_REQUIRED_CONTEXTS if matched.get(context))
        all_pm_match = pm_match_count == len(PM_REQUIRED_CONTEXTS)
        pm_allowlist_blocked = [
            context
            for context in PM_REQUIRED_CONTEXTS
            if (case_by_context.get(context) or {}).get("step", {}).get("rc") == 2
            and not (case_by_context.get(context) or {}).get("result")
        ]
        any_non_pm_match = any(
            ok for context, ok in matched.items() if context not in PM_REQUIRED_CONTEXTS
        )
        if all_pm_match:
            return (
                "v1033-pm-selinux-domain-handoff-present",
                True,
                "all required PM domains survived static re-exec after policy load",
                "rerun V1032 PM runtime-domain guard after current-boot policy load; do not start Wi-Fi HAL or scan/connect yet",
            )
        if len(pm_allowlist_blocked) == len(PM_REQUIRED_CONTEXTS):
            return (
                "v1033-pm-selinux-domain-proof-helper-allowlist-blocked",
                True,
                "helper selinux-domain-proof allowlist rejected all required PM contexts before policy transition testing",
                "add PM contexts to the helper selinux-domain-proof allowlist, rebuild/deploy, then rerun PM domain proof",
            )
        if any_non_pm_match:
            return (
                "v1033-pm-selinux-domain-kernel-stuck-non-pm-only",
                True,
                f"only non-PM domains matched; PM matches {pm_match_count}/{len(PM_REQUIRED_CONTEXTS)}",
                "classify PM domain transition rules or target executable labels before another PM actor retry",
            )
        return (
            "v1033-pm-selinux-domain-kernel-stuck",
            True,
            f"PM matches {pm_match_count}/{len(PM_REQUIRED_CONTEXTS)} after policy load",
            "repair PM domain handoff before another PM actor live retry",
        )
    if decision == "v491-post-load-domain-handoff-present":
        next_step = (
            "rerun V1032 PM runtime-domain guard after current-boot policy load; "
            "do not start Wi-Fi HAL or scan/connect yet"
        )
    elif decision == "v491-post-load-domain-kernel-stuck":
        next_step = "repair PM domain handoff before another PM actor live retry"
    elif decision == "v491-post-load-domain-proof-plan-ready":
        next_step = "run V401/V490 current-boot policy load first, then V1033 PM domain proof"
    return _map_decision(decision), pass_ok, reason.replace("V491", "V1033"), next_step


def render_summary(manifest):
    return (
        ORIGINAL_RENDER_SUMMARY(manifest)
        .replace("# V491 Post-Load SELinux Domain Proof", "# V1033 PM SELinux Domain Proof")
        .replace("V491", "V1033")
        .replace("helper v48", "helper v175")
        .replace("No policy load is performed by V1033.", "No policy load is performed by V1033; it requires a separate V490 pass manifest.")
    )


def build_manifest(args, store):
    manifest = ORIGINAL_BUILD_MANIFEST(args, store)
    manifest["decision"] = _map_decision(str(manifest.get("decision", "")))
    manifest["plan"]["helper_version"] = "a90_android_execns_probe v175"
    manifest["plan"]["pm_contexts"] = list(base.CONTEXTS)
    manifest["plan"]["required_pm_contexts"] = list(PM_REQUIRED_CONTEXTS)
    manifest["pm_domain_proof"] = True
    manifest["pm_required_contexts"] = list(PM_REQUIRED_CONTEXTS)
    manifest["pm_required_matches"] = [
        case
        for case in manifest.get("cases", [])
        if case.get("context") in PM_REQUIRED_CONTEXTS and case.get("postexec_match")
    ]
    manifest["pm_allowlist_blocked_contexts"] = [
        case.get("context")
        for case in manifest.get("cases", [])
        if case.get("context") in PM_REQUIRED_CONTEXTS
        and (case.get("step") or {}).get("rc") == 2
        and not case.get("result")
    ]
    manifest["pm_required_match_count"] = len(manifest["pm_required_matches"])
    manifest["pm_required_all_match"] = manifest["pm_required_match_count"] == len(PM_REQUIRED_CONTEXTS)
    manifest["pm_allowlist_blocked_all"] = len(manifest["pm_allowlist_blocked_contexts"]) == len(PM_REQUIRED_CONTEXTS)
    manifest["actor_start_executed"] = False
    manifest["scan_connect_executed"] = False
    manifest["credential_use_executed"] = False
    manifest["dhcp_route_executed"] = False
    manifest["next_step"] = str(manifest.get("next_step", "")).replace("V491", "V1033")
    return manifest


base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
