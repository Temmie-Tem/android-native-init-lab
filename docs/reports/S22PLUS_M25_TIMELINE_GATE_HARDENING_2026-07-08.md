# S22+ M25 Timeline-Gate Hardening (2026-07-08)

## Scope

Host-side/live-gate hardening only. No live flash, reboot, rollback, partition
write, or sysfs write was performed.

## Change

`s22plus_m25_hs_only_usb2_acm_live_gate.py` now validates `timeline.json`
before appending a new event:

- top-level JSON object must contain only `events`;
- `events` must be a list;
- every event must contain only `name` and `timestamp_utc`;
- `name` must be a non-empty string;
- `timestamp_utc` must be a parseable UTC timestamp ending in `Z`.

The auxiliary `--restore-dtbo-from-android` path can perform a stock-DTBO write
after rebooting to Download mode, so it now records:

```text
live_session_start
live_session_end
```

This aligns that mode with the live, rollback-from-download, and
restore-dtbo-from-download paths.

## Validation

Commands run:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_s22plus_m25_hs_only_usb2_acm_live_gate
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py --offline-check
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py
git diff --check
```

Results:

```text
unit tests: Ran 13 tests ... OK
offline-check: ok
dry-run: ok
dry-run log: workspace/private/runs/s22plus_m25_hs_only_usb2_acm_live_gate_20260708T122023Z/s22plus_m25_hs_only_usb2_acm_live_gate.txt
```

Dry-run baseline evidence:

```text
agents_exception_missing=[]
android_stability_result=ok samples=4
current_boot_hash_rc=0
current_vendor_boot_hash_rc=0
current_dtbo_hash_rc=0
host_snapshot label=dryrun_current
```

## Status

M25 remains live-ready but was not executed in this unit. Live still requires the
operator-attended command with exact ack:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/s22plus_m25_hs_only_usb2_acm_live_gate.py --live --ack S22PLUS-M25-HS-ONLY-USB2-ACM-LIVE-GATE
```
