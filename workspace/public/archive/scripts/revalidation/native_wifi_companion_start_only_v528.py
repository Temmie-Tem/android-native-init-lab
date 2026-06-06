#!/usr/bin/env python3
"""V528 bounded native Wi-Fi companion start-only proof.

This is the v62-helper variant of V527. It keeps the same bounded safety
contract: companion services only, no service-manager, no Wi-Fi HAL, no scan,
no connect/link-up, no DHCP, and no external ping. v62 specifically replays
`rmt_storage` and `tftp_server` as Android init root services based on vendor
init rc evidence.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_companion_start_only_v527 as v527


v527.__doc__ = __doc__
v527.DEFAULT_OUT_DIR = Path("tmp/wifi/v528-companion-start-only")
v527.DEFAULT_HELPER_SHA256 = "65d9ae002ff3f1e3eef1cc9526139dec6bec57e1b989b2090c46056bd2169ed3"
v527.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v62"
v527.PROOF_VERSION = "V528"
v527.PROOF_SLUG = "v528-companion-start-only"
v527.LIVE_HELPER_STEP_NAME = "v528-helper-run"
v527.APPROVAL_PHRASE = (
    "approve v528 companion start-only proof only; "
    "no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)


if __name__ == "__main__":
    raise SystemExit(v527.main())
