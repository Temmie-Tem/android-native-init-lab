#!/usr/bin/env python3
"""V657 helper-v106 exact V653-mode service-74 replay.

This gate reuses the V653 service-74 gated service-manager proof, but pins the
already deployed helper v106 and a V657-specific V490 manifest. It is intended
to distinguish a helper-version/mode regression from the broader lower
service-notifier nondeterminism before retrying the V655 CNSS retry tail.

It does not write DSP boot nodes, open esoc0, write qcwlanstate, start Wi-Fi
HAL, scan/connect, use credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

from typing import Any

import native_wifi_service74_gated_service_manager_v653 as v653


base = v653.base

base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v657-service74-v106-replay")
base.DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
base.DEFAULT_HELPER_SHA256 = "5492f3cc32087e4f589b816c8b0757edb5caa2e9b87f8c0fa7f4486f05fb63cb"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v106"
base.DEFAULT_V490_MANIFEST = base.Path("tmp/wifi/v657-v490-current-run/manifest.json")
base.APPROVAL_PHRASE = (
    "approve v657 helper v106 exact V653-mode service74 replay only; "
    "no CNSS retry, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

_v653_build_checks = v653.build_checks
_v653_decide = v653.decide
_v653_render_summary = v653.render_summary
_v653_build_manifest = v653.build_manifest


def _rewrite_text(text: str) -> str:
    return (
        text.replace("V653", "V657")
        .replace("v653", "v657")
        .replace("helper v105", "helper v106")
        .replace("helper-v105", "helper-v106")
        .replace("a90_android_execns_probe v105", "a90_android_execns_probe v106")
        .replace("deploy helper v105", "deploy helper v106")
    )


def _rename_check(check: base.Check) -> base.Check:
    return base.Check(
        _rewrite_text(check.name),
        check.status,
        check.severity,
        _rewrite_text(check.detail),
        [_rewrite_text(item) for item in check.evidence],
        _rewrite_text(check.next_step),
    )


def build_checks(args: base.argparse.Namespace,
                 steps: list[dict[str, Any]],
                 mount_preflight: dict[str, Any],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[base.Check]:
    checks = [_rename_check(check) for check in _v653_build_checks(args, steps, mount_preflight, v490, v525)]
    if args.command != "plan":
        base.add_check(
            checks,
            "v657-exact-v653-mode-with-helper-v106",
            "pass",
            "info",
            (
                "V657 intentionally keeps the V653 service74-gated mode and "
                "changes only helper version/prerequisite evidence labels"
            ),
            [v653.SERVICE74_GATED_MODE],
            "if service74 returns, retry V655 CNSS retry mode from the same prerequisite shape",
        )
    return checks


def decide(args: base.argparse.Namespace,
           checks: list[base.Check],
           live: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, live_executed = _v653_decide(args, checks, live)
    return _rewrite_text(decision), pass_ok, _rewrite_text(reason), _rewrite_text(next_step), live_executed


def render_summary(manifest: dict[str, Any]) -> str:
    text = _v653_render_summary(manifest)
    text = _rewrite_text(text)
    text = text.replace(
        "# V657 Service-74 Gated Service-Manager Proof",
        "# V657 Helper-v106 Exact V653-Mode Service-74 Replay",
        1,
    )
    return "\n".join([
        text,
        "",
        "## V657 Replay Contract",
        "",
        "- target: exact V653-compatible service74-gated service-manager mode",
        "- helper: `a90_android_execns_probe v106`",
        "- allowed live tail: service-manager trio only after fresh service `74` gate opens",
        "- blocked tail: V655 CNSS retry, Wi-Fi HAL, scan/connect, credentials, DHCP, routes, external ping",
        "",
    ])


def build_manifest(args: base.argparse.Namespace, store: base.EvidenceStore) -> dict[str, Any]:
    manifest = _v653_build_manifest(args, store)
    manifest["cycle"] = "v657"
    manifest["replay_target_cycle"] = "v653"
    manifest["helper_version"] = "v106"
    manifest["exact_replay_mode"] = v653.SERVICE74_GATED_MODE
    manifest["v655_retry_tail_executed"] = False
    manifest["explicitly_not_approved"] = [
        _rewrite_text(item) for item in manifest.get("explicitly_not_approved", [])
    ] + [
        "V655 vndservicemanager readiness and cnss-daemon retry tail",
    ]
    return manifest


base.build_checks = build_checks
base.decide = decide
base.render_summary = render_summary
base.build_manifest = build_manifest


if __name__ == "__main__":
    raise SystemExit(base.main())
