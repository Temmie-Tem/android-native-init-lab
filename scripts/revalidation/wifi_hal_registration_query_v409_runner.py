#!/usr/bin/env python3
"""Superseded V409 bounded Wi-Fi HAL registration query gate.

V409 was superseded by V410 before live query because the V409 approved command
could fit the native argument budget only by dropping explicit private
`/data/vendor/wifi` handling.  V410 moves that default into helper v26.  This
wrapper is intentionally fail-closed and never starts service-manager,
hwservicemanager, a Wi-Fi HAL, lshal, or Wi-Fi bring-up.
"""

from __future__ import annotations

from wifi_superseded_gate import run_superseded_gate


if __name__ == "__main__":
    raise SystemExit(run_superseded_gate(
        gate="V409 Wi-Fi HAL registration query",
        default_slug="v409-registration-query-superseded",
        replacement_script="scripts/revalidation/wifi_hal_registration_query_v410_runner.py",
        next_phrase=(
            "approve v410 bounded lshal registration query only; "
            "no scan/connect/link-up and no Wi-Fi bring-up"
        ),
        reason=(
            "V409 registration query is superseded by V410; "
            "no device command, daemon start, HAL start, lshal query, or Wi-Fi bring-up was executed"
        ),
    ))
