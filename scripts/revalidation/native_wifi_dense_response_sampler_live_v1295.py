#!/usr/bin/env python3
"""V1295 bounded dense no-write late per_proxy response sampler.

This wraps the V1242 response sampler with helper v271 and injects the dense
response sampler flag. It still does not start Wi-Fi HAL, scan/connect, use
credentials, run DHCP/routes, ping externally, write PMIC/GPIO/eSoC state, or
flash/partition-write.
"""

from __future__ import annotations

from pathlib import Path

import native_wifi_late_per_proxy_response_sampler_live_v1242 as base


DENSE_RESPONSE_SAMPLER_FLAG = "--pm-observer-late-per-proxy-dense-response-sampler"

base.DEFAULT_OUT_DIR = Path("tmp/wifi/v1295-dense-response-sampler-live")
base.LATEST_POINTER = Path("tmp/wifi/latest-v1295-dense-response-sampler-live.txt")
base.HELPER_MARKER = "a90_android_execns_probe v271"
base.HELPER_SHA256 = "335b875516e76419933f2e0ab6e21cd7ee4d1d217b32f378f1925adc30010a24"
base.CYCLE_LABEL = "v1295"
base.CYCLE_NAME = "V1295"
base.SUMMARY_HEADING = "V1295 Dense Response Sampler"
base.EVIDENCE_FILE_PREFIX = "v1295"


def _force_dense_response_sampler_child_command(original):
    def command(args):
        result = original(args)
        for flag in (base.RESPONSE_SAMPLER_FLAG, DENSE_RESPONSE_SAMPLER_FLAG):
            if flag not in result:
                result.append(flag)
        return result

    return command


base._force_response_sampler_child_command = _force_dense_response_sampler_child_command


if __name__ == "__main__":
    raise SystemExit(base.main())
