# WSTA68 Persistent Session Bulk Retire Source

- Date: 2026-07-04
- Scope: host-only bulk retire for non-liveable persistent sessions
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta68-persistent-session-bulk-retire-pass`

## Summary

WSTA68 adds a host-only cleanup layer on top of the WSTA67 inventory.  It consumes
a private WSTA67 inventory result and creates WSTA66-compatible retire markers
only for selected non-liveable states:

```text
STALE
EXPIRED
NOT_READY
```

READY sessions are skipped by default, and already RETIRED sessions are skipped.
This lets the operator clear stale prepared sessions from the live-ready surface
without starting public exposure or deleting private artifacts.

## Source Change

Added:

- `workspace/public/src/scripts/server-distro/run_wsta68_persistent_session_bulk_retire.py`
- `tests/test_server_distro_wsta68_persistent_session_bulk_retire.py`

Default execution is fail-closed until the operator supplies:

```text
--bulk-retire
--ack-bulk-retire
--wsta67-inventory-json workspace/private/runs/server-distro/<wsta67-run>/wsta67_inventory.json
```

Generated retire markers are named `wsta66_retire_marker.json`, so WSTA67 and
WSTA65 consume them through the same retire-marker path as WSTA66.

## Private Smoke

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta68-bulk-retire-smoke-20260704T1032Z
```

Observed flow:

```text
READY session: WSTA63 -> WSTA64
STALE session: WSTA63 -> WSTA64 -> WSTA67 inventory at near-expiry
WSTA68 bulk retire over the WSTA67 inventory
WSTA67 inventory again over the same smoke root
```

Inventory before WSTA68:

```text
session_count=2
ready_count=1
stale_count=1
state_counts.READY=1
state_counts.STALE=1
```

WSTA68 result:

```text
decision=wsta68-persistent-session-bulk-retire-pass
target_states=[EXPIRED, NOT_READY, STALE]
retired_count=1
skipped_count=1
retired[0].previous_session_state=STALE
retired[0].reason=session-stale
skipped[0].session_state=READY
ready_sessions_retired=false
live_execution_requested=false
public_url_value_logged=false
secret_values_logged=0
```

Inventory after WSTA68:

```text
session_count=2
ready_count=1
retired_count=1
state_counts.READY=1
state_counts.RETIRED=1
```

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- No device command, native reboot, Wi-Fi association, DHCP, public tunnel,
  public smoke, userdata action, switch-root, or external service action ran.
- The runner has no `native_init_flash.py` or `a90ctl.py` call path.
- READY sessions are not retired by default.
- The committed report/source/test changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw private lease artifacts, inventories, and retire markers remain under
  `workspace/private/`.

## Validation

Focused tests:

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
  tests.test_server_distro_wsta68_persistent_session_bulk_retire
```

Result: `Ran 84 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta68_persistent_session_bulk_retire.py
```

Result: pass

Fresh WSTA63 + WSTA64 + WSTA67 + WSTA68 + WSTA67 private smoke: pass.

## Next

The default-off persistent exposure workflow now has prepare, readiness, status,
retire, inventory, and bulk-retire cleanup layers.  Continue only with explicit
operator-selected WSTA58 live proof, or further default-off operator UX/reporting
that does not start public exposure.
