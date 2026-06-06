#!/usr/bin/env python3
"""V547 bounded companion replay with cleanup signal classification."""

from __future__ import annotations

import native_wifi_companion_binder_replay_v545 as v545


base = v545.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v547-companion-cleanup-classified")
base.DEFAULT_HELPER_SHA256 = "e46b87897551ea4a4cee1991758e58c90e7d668e8b98057c41ddec3a99a9d424"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v74"
base.PROOF_VERSION = "V547"
base.PROOF_SLUG = "v547-companion-cleanup-classified"
base.LIVE_HELPER_STEP_NAME = "v547-helper-run"
base.APPROVAL_PHRASE = (
    "approve v547 companion cleanup-classified replay only; "
    "no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)


if __name__ == "__main__":
    raise SystemExit(base.main())
