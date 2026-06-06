#!/usr/bin/env python3
"""v232 host wrapper for private linkerconfig materialization probes."""

from __future__ import annotations

from pathlib import Path

import wifi_android_exec_namespace_probe as probe


probe.SCRIPT_LABEL = "v232"
probe.DEFAULT_OUT_DIR = Path("tmp/wifi/v232-linkerconfig-materialization-probe")
probe.DEFAULT_V229_OUT_DIR = Path("tmp/wifi/v229-controlled-cnss-start-experiment-preflight-before-v232")


if __name__ == "__main__":
    raise SystemExit(probe.run_mode(probe.parse_args()))
