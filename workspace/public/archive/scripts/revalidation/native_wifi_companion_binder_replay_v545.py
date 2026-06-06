#!/usr/bin/env python3
"""V545 bounded companion replay after private binder surface.

This reuses the V543 cnss-daemon ptrace capture contract with helper v73. It
exists to verify whether adding private `/dev/binder`, `/dev/hwbinder`, and
`/dev/vndbinder` moves `cnss-daemon` past the previous binder-open abort. It
does not start service-manager, Wi-Fi HAL, scan/connect/link-up, DHCP, routing,
or external ping.
"""

from __future__ import annotations

import native_wifi_companion_ptrace_capture_v543 as v543


base = v543.base
base.__doc__ = __doc__
base.DEFAULT_OUT_DIR = base.Path("tmp/wifi/v545-companion-binder-replay")
base.DEFAULT_HELPER_SHA256 = "a6fd0ec516d3c828c47c6359dc7d8afeabedd59c0509b7eaa75e7a9177c8e9b1"
base.DEFAULT_HELPER_MARKER = "a90_android_execns_probe v73"
base.PROOF_VERSION = "V545"
base.PROOF_SLUG = "v545-companion-binder-replay"
base.LIVE_HELPER_STEP_NAME = "v545-helper-run"
base.APPROVAL_PHRASE = (
    "approve v545 companion binder replay only; "
    "no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)


if __name__ == "__main__":
    raise SystemExit(base.main())
