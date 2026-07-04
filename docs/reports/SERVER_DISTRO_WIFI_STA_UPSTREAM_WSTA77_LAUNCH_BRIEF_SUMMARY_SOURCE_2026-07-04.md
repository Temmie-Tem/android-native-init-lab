# WSTA77 Persistent Launch Brief Summary Source

- Date: 2026-07-04
- Scope: host-only summary of WSTA76 launch briefs
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta77-persistent-launch-brief-summary-pass`

## Summary

WSTA77 scans a private WSTA run tree for WSTA76 launch briefs, reruns WSTA76
for each brief's source WSTA75 inventory, and emits a redacted operator summary
of which briefs are still ready, stale, drifted, or blocked.

This is the "one screen before live" view.  It answers:

```text
Which launch brief, if any, is still fresh enough to use for an explicit WSTA58 live gate?
```

WSTA77 does not replace token placeholders, start a tunnel, touch the device,
connect Wi-Fi, or run public smoke.

## Source Change

Added:

- `workspace/public/src/scripts/server-distro/run_wsta77_persistent_launch_brief_summary.py`
- `tests/test_server_distro_wsta77_persistent_launch_brief_summary.py`

The runner scans only private paths:

```text
python3 workspace/public/src/scripts/server-distro/run_wsta77_persistent_launch_brief_summary.py \
  --scan-root workspace/private/runs/server-distro \
  --max-briefs 50
```

WSTA77 ignores WSTA77-generated nested `wsta76-recheck` artifacts so repeated
summary runs do not count their own recheck briefs as independent operator
briefs.

## States

```text
READY_TO_EXECUTE_DEFAULT_OFF
STALE_OR_NOT_READY
DRIFT_RECHECK_REQUIRED
INVALID_OR_BLOCKED
```

`DRIFT_RECHECK_REQUIRED` means the original brief is no longer the fresh
selected packet for its source inventory.  The operator should use the newly
generated WSTA76 recheck brief or rerun WSTA76 directly.

## Private Smoke

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta77-launch-brief-summary-smoke-20260704T111625Z
```

Observed flow:

```text
WSTA72 prepare-to-arm
WSTA73 arming packet
WSTA75 arming inventory
WSTA76 launch brief
WSTA77 launch brief summary
```

Observed WSTA77 result:

```text
decision=wsta77-persistent-launch-brief-summary-pass
overall_state=READY_BRIEF_PRESENT_DEFAULT_OFF
brief_count=1
ready_count=1
selected_ready_brief=workspace/private/runs/server-distro/wsta77-launch-brief-summary-smoke-20260704T111625Z/brief/wsta76_launch_brief.json
selected_state=READY_TO_EXECUTE_DEFAULT_OFF
initial_seconds_remaining=299
recommended_next_action=operator-may-run-explicit-wsta58-live-gate-from-selected-brief
live_execution_requested=false
public_url_value_logged=false
secret_values_logged=0
```

Generated summary:

```text
workspace/private/runs/server-distro/wsta77-launch-brief-summary-smoke-20260704T111625Z/summary/wsta77_launch_brief_summary.json
workspace/private/runs/server-distro/wsta77-launch-brief-summary-smoke-20260704T111625Z/summary/wsta77_launch_brief_summary.md
```

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- No device command, native reboot, Wi-Fi association, DHCP, public tunnel,
  public smoke, userdata action, switch-root, or external service action ran.
- The runner has no `native_init_flash.py` or `a90ctl.py` call path.
- WSTA77 invokes WSTA76/WSTA75/WSTA74/WSTA73 status, inventory, and brief
  surfaces only; WSTA58 live execution remains a separate explicit
  operator-selected gate.
- Redaction checks are applied to the public summary and generated Markdown.
- The committed report/source/test changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw private prepare-to-arm outputs, WSTA73 packets, WSTA75 inventories,
  WSTA76 briefs, and WSTA77 summary artifacts remain under `workspace/private/`.

## Validation

Compile check:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta77_persistent_launch_brief_summary.py
```

Result: pass

WSTA77 focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta77_persistent_launch_brief_summary
```

Result: `Ran 9 tests ... OK`

Focused WSTA52-WSTA77 regression:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta52_persistent_exposure_design \
  tests.test_server_distro_wsta53_persistent_exposure_plan \
  tests.test_server_distro_wsta54_private_lease_artifact \
  tests.test_server_distro_wsta55_short_lived_public_proof \
  tests.test_server_distro_wsta58_renewal_manual_stop_proof \
  tests.test_server_distro_wsta63_persistent_session_controller \
  tests.test_server_distro_wsta64_persistent_session_readiness_audit \
  tests.test_server_distro_wsta65_persistent_session_status \
  tests.test_server_distro_wsta66_persistent_session_retire \
  tests.test_server_distro_wsta67_persistent_session_inventory \
  tests.test_server_distro_wsta68_persistent_session_bulk_retire \
  tests.test_server_distro_wsta69_persistent_session_snapshot \
  tests.test_server_distro_wsta70_persistent_session_launch_manifest \
  tests.test_server_distro_wsta71_persistent_launch_readiness_audit \
  tests.test_server_distro_wsta72_persistent_prepare_to_arm \
  tests.test_server_distro_wsta73_persistent_arming_packet \
  tests.test_server_distro_wsta74_persistent_arming_status \
  tests.test_server_distro_wsta75_persistent_arming_inventory \
  tests.test_server_distro_wsta76_persistent_launch_brief \
  tests.test_server_distro_wsta77_persistent_launch_brief_summary
```

Result: `Ran 152 tests ... OK`

Fresh WSTA72 + WSTA73 + WSTA75 + WSTA76 + WSTA77 private smoke: pass.

## Next

The default-off persistent exposure workflow now has prepare-to-arm, arming
packet, per-packet status, multi-packet inventory, launch brief, and a
multi-brief operator summary.  Continue only with explicit operator-selected
WSTA58 live proof, or further default-off operator UX/reporting that does not
start public exposure.
