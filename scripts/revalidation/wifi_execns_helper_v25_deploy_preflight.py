#!/usr/bin/env python3
"""Superseded V409 execns helper v25 deploy gate.

V409 helper v25 was superseded by V410 before live deployment because its
approved query plan could only fit the native argument budget by omitting the
private `/data/vendor/wifi` handling from the helper argv.  This wrapper is
therefore intentionally fail-closed and never deploys `/cache/bin` content.
"""

from __future__ import annotations

from wifi_superseded_gate import run_superseded_gate


if __name__ == "__main__":
    raise SystemExit(run_superseded_gate(
        gate="V409 execns helper v25 deploy",
        default_slug="v409-helper-v25-deploy-superseded",
        replacement_script="scripts/revalidation/wifi_execns_helper_v26_deploy_preflight.py",
        next_phrase=(
            "approve v410 bounded lshal registration query only; "
            "no scan/connect/link-up and no Wi-Fi bring-up"
        ),
        reason=(
            "V409 helper v25 deploy is superseded by V410; "
            "no device command or /cache/bin mutation was executed"
        ),
    ))
