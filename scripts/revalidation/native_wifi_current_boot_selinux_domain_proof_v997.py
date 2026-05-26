#!/usr/bin/env python3
"""V997 current-boot SELinux domain proof wrapper for helper v169."""

from __future__ import annotations

from pathlib import Path

import native_selinux_post_load_domain_proof_v491 as base


base.DEFAULT_OUT_DIR = Path("tmp/wifi/v997-current-boot-selinux-domain-proof")
base.DEFAULT_HELPER_SHA256 = "c47f0659178186d45cf5199fdad4d198f0c69b6998f2127ff420f9e0f0204a74"
base.APPROVAL_PHRASE = (
    "approve v997 current-boot SELinux domain proof only; "
    "no policy load, no daemon start and no Wi-Fi bring-up"
)
base.CONTEXTS = (
    "u:r:servicemanager:s0",
    "u:r:hwservicemanager:s0",
    "u:r:vndservicemanager:s0",
    "u:r:wificond:s0",
    "u:r:hal_wifi_default:s0",
)
base.ATTR_MODES = ("exec",)


if __name__ == "__main__":
    raise SystemExit(base.main())
