#!/usr/bin/env python3
"""V468 extended IWifi/default registration-latency proof.

This reuses the V467 private service-manager/HAL/CNSS registration proof, but
expects helper v34 where the IWifi `lshal wait` window follows
`--timeout-sec`. It still does not call IWifi.start(), read credentials, scan,
connect, request DHCP, change routes, or send packets.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import native_iwifi_registration_v467 as v467


base = v467.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = Path("tmp/wifi/v468-iwifi-registration-longwait")
base.DEFAULT_HELPER_SHA256 = "f43308d768d5921a645d3de7e31562609a772f5c800cbd619170c592d18dba66"
base.DEFAULT_V404 = Path("tmp/wifi/v467-iwifi-registration-live-20260521-010150/manifest.json")
base.HELPER_LABEL = "v34"
base.APPROVAL_PHRASE = (
    "approve v468 extended lshal wait IWifi/default registration proof only; "
    "no scan/connect/link-up and no Wi-Fi bring-up"
)

_BASE_PARSE_ARGS = v467.parse_args
_BASE_BUILD_PLAN = v467.build_plan
_BASE_DECIDE = v467.decide
_BASE_REFUSAL_MANIFEST = v467.refusal_manifest
_BASE_RENDER_SUMMARY = v467.render_summary


def parse_args() -> base.argparse.Namespace:
    args = _BASE_PARSE_ARGS()
    if "--max-runtime-sec" not in sys.argv:
        args.max_runtime_sec = 12
    return args


def build_plan(args: base.argparse.Namespace) -> dict[str, Any]:
    plan = _BASE_BUILD_PLAN(args)
    plan["helper_version"] = base.HELPER_LABEL
    plan["extended_wait"] = {
        "lshal_wait_timeout_ms": args.max_runtime_sec * 1000,
        "reason": "V467 timed out at the fixed 2000ms IWifi/default wait window",
    }
    return plan


def _v468_label(decision: str) -> str:
    return decision.replace("v467-iwifi-registration", "v468-iwifi-registration-longwait")


def decide(args: base.argparse.Namespace, checks: list[base.Check], live_result: dict[str, Any] | None,
           post: dict[str, Any] | None) -> tuple[str, bool, str, str, bool]:
    decision, pass_ok, reason, next_step, daemon_started = _BASE_DECIDE(args, checks, live_result, post)
    return _v468_label(decision), pass_ok, reason, next_step.replace("V467", "V468").replace("v33", "v34"), daemon_started


def refusal_manifest(args: base.argparse.Namespace, v466_manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = _BASE_REFUSAL_MANIFEST(args, v466_manifest)
    manifest["decision"] = _v468_label(str(manifest["decision"]))
    manifest["next_step"] = str(manifest["next_step"]).replace("v33", "v34").replace("V467", "V468")
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    return _BASE_RENDER_SUMMARY(manifest).replace(
        "# V467 IWifi/default Registration Proof",
        "# V468 Extended IWifi/default Registration-Latency Proof",
        1,
    )


v467.parse_args = parse_args
v467.build_plan = build_plan
v467.decide = decide
v467.refusal_manifest = refusal_manifest
v467.render_summary = render_summary

base.parse_args = parse_args
base.build_plan = build_plan
base.decide = decide
base.refusal_manifest = refusal_manifest
base.render_summary = render_summary


if __name__ == "__main__":
    raise SystemExit(base.main())
