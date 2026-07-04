# WSTA67 Persistent Session Inventory Source

- Date: 2026-07-04
- Scope: host-only persistent session inventory
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta67-persistent-session-inventory-pass`

## Summary

WSTA67 adds a redacted inventory layer for persistent exposure sessions.  WSTA63
through WSTA66 operate on individual session artifacts; WSTA67 scans a private
run tree for WSTA64 readiness results and WSTA66 retire markers, then
recalculates each session's current lifecycle state through the WSTA65 logic.

The inventory reports:

```text
READY
STALE
EXPIRED
NOT_READY
RETIRED
```

Retire markers take precedence.  Otherwise, WSTA67 re-reads the initial private
lease at inventory time, so old readiness results cannot stay green after they
age out.

## Source Change

Added:

- `workspace/public/src/scripts/server-distro/run_wsta67_persistent_session_inventory.py`
- `tests/test_server_distro_wsta67_persistent_session_inventory.py`

Default execution scans the private server-distro run root:

```text
--scan-root workspace/private/runs/server-distro
--max-sessions 50
```

Both `--scan-root` and `--run-dir` must be under `workspace/private/`.  Public
output contains only redacted paths, lifecycle states, counts, booleans, and
freshness seconds.

## Private Smoke

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta67-inventory-smoke-20260704T1024Z
```

Observed flow:

```text
READY session:   WSTA63 -> WSTA64 -> WSTA65
RETIRED session: WSTA63 -> WSTA64 -> WSTA65 -> WSTA66
WSTA67 inventory scan over the smoke root
```

Observed public summary:

```text
decision=wsta67-persistent-session-inventory-pass
session_count=2
ready_count=1
retired_count=1
stale_count=0
expired_count=0
not_ready_count=0
invalid_session_count=0
state_counts.READY=1
state_counts.RETIRED=1
live_execution_requested=false
public_url_value_logged=false
secret_values_logged=0
```

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- No device command, native reboot, Wi-Fi association, DHCP, public tunnel,
  public smoke, userdata action, switch-root, or external service action ran.
- The runner has no `native_init_flash.py` or `a90ctl.py` call path.
- The committed report/source/test changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw private lease artifacts, readiness results, status results, and retire
  markers remain under `workspace/private/`.

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
  tests.test_server_distro_wsta67_persistent_session_inventory
```

Result: `Ran 77 tests ... OK`

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta67_persistent_session_inventory.py
```

Result: pass

Fresh WSTA63 + WSTA64 + WSTA65 + WSTA66 + WSTA67 private smoke: pass.

## Next

The default-off persistent exposure workflow now has per-session prepare,
readiness, status, retire, and inventory layers.  Continue only with explicit
operator-selected WSTA58 live proof, or further default-off operator UX/reporting
that does not start public exposure.
