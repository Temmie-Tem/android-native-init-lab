#!/usr/bin/env python3
"""V1218: rerun bounded PM/CNSS observer after V1217 readback proof."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from a90harness.evidence import write_private_json

import native_wifi_pm_esoc_sdxprairie_name_v1216 as base


HELPER_SHA256_V252 = "4511f11399d4f86f5265d79eb57b2db04ae5ad869ab543565f2c657b97af8587"
HELPER_MARKER_V252 = "a90_android_execns_probe v252"

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1218-pm-cnss-sdxprairie-observer")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1218-pm-cnss-sdxprairie-observer.txt")
base.DEFAULT_EXECNS_HELPER_SHA256 = HELPER_SHA256_V252
base.DEFAULT_EXECNS_HELPER_MARKER = HELPER_MARKER_V252

ORIGINAL_DECIDE = base.decide_v1216


def _map_v1218(text: str) -> str:
    return (
        text.replace("v1216", "v1218")
        .replace("V1216", "V1218")
        .replace("helper v250", "helper v252")
    )


def decide_v1218(args: Any, manifest: dict) -> tuple[str, bool, str, str]:
    decision, passed, reason, next_step = ORIGINAL_DECIDE(args, manifest)
    decision = _map_v1218(decision)
    reason = _map_v1218(reason)
    next_step = _map_v1218(next_step)

    if decision == "v1218-peripheral-modem-unexpected":
        next_step = (
            "V1219: positive readback but cnss-daemon still selects modem; "
            "trace libmdmdetect/cnss-daemon selection after get_system_info"
        )
    elif decision == "v1218-peripheral-sdxprairie-no-esoc0":
        next_step = (
            "V1219: SDXPRAIRIE registration confirmed; extend/trace per_mgr "
            "subsys_esoc0 open path"
        )
    elif decision == "v1218-peripheral-sdxprairie-per-mgr-esoc0":
        next_step = (
            "V1219: MDM power-on completion / WLFW service 69 / BDF / wlan0 "
            "observer, still no scan/connect"
        )
    elif decision == "v1218-wlan0-up":
        next_step = "V1219: bounded link/DHCP gate; no credential persistence"
    return decision, passed, reason, next_step


def _patch_manifest() -> None:
    try:
        run_dir = Path(base.LATEST_POINTER.read_text(encoding="utf-8").strip())
        manifest_path = run_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    manifest["cycle"] = "v1218"
    manifest["helper_version"] = HELPER_MARKER_V252
    manifest["helper_sha256"] = HELPER_SHA256_V252
    if isinstance(manifest.get("decision"), str):
        manifest["decision"] = _map_v1218(manifest["decision"])
    if isinstance(manifest.get("next_step"), str):
        manifest["next_step"] = _map_v1218(manifest["next_step"])
    write_private_json(manifest_path, manifest)


def main() -> int:
    base.decide_v1216 = decide_v1218
    rc = base.main()
    _patch_manifest()
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
