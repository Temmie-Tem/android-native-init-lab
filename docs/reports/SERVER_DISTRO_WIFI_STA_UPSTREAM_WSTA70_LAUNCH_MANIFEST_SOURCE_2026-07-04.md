# WSTA70 Persistent Session Launch Manifest Source

- Date: 2026-07-04
- Scope: host-only launch manifest for one selected READY persistent session
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta70-persistent-session-launch-manifest-pass`

## Summary

WSTA70 adds the default-off selection step after WSTA67 inventory and WSTA69
snapshot reporting.  It consumes a private WSTA67 inventory, selects one READY
candidate, revalidates that candidate through WSTA65 at the current time, and
writes:

```text
wsta70_launch_manifest.json
wsta70_launch_manifest.md
```

The manifest contains the WSTA63/WSTA64-validated WSTA58 live command template
with token placeholders.  It does not replace tokens, start a tunnel, touch the
device, connect Wi-Fi, or run public smoke.

## Source Change

Added:

- `workspace/public/src/scripts/server-distro/run_wsta70_persistent_session_launch_manifest.py`
- `tests/test_server_distro_wsta70_persistent_session_launch_manifest.py`

The runner is fail-closed until a private WSTA67 inventory is supplied:

```text
python3 workspace/public/src/scripts/server-distro/run_wsta70_persistent_session_launch_manifest.py \
  --wsta67-inventory-json workspace/private/runs/server-distro/<wsta67-run>/wsta67_inventory.json \
  --ready-index 0
```

WSTA70 intentionally treats an inventory READY row as staleable evidence.  Before
emitting a launch manifest it reruns WSTA65 over the selected WSTA64 result and
requires:

```text
wsta65_decision=wsta65-persistent-session-status-pass
session_state=READY
ready_for_live=true
live_template_placeholders_only=true
```

If the selected session has aged into STALE/EXPIRED/NOT_READY, WSTA70 blocks and
writes the WSTA65 revalidation path for inspection.

## Private Smoke

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta70-launch-manifest-smoke-20260704T103358Z
```

Observed flow:

```text
READY session: WSTA63 -> WSTA64
WSTA67 inventory over the smoke root
WSTA70 selection and WSTA65 revalidation
```

WSTA70 result:

```text
decision=wsta70-persistent-session-launch-manifest-pass
ready_candidate_count=1
selected_ready_index=0
wsta65_session_state=READY
ready_for_live=true
initial_seconds_remaining=297
live_command_template contains <native-confirm-token>
live_execution_requested=false
```

Generated manifest:

```text
workspace/private/runs/server-distro/wsta70-launch-manifest-smoke-20260704T103358Z/launch/wsta70_launch_manifest.json
workspace/private/runs/server-distro/wsta70-launch-manifest-smoke-20260704T103358Z/launch/wsta70_launch_manifest.md
```

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- No device command, native reboot, Wi-Fi association, DHCP, public tunnel,
  public smoke, userdata action, switch-root, or external service action ran.
- The runner has no `native_init_flash.py` or `a90ctl.py` call path.
- The WSTA58 command remains a placeholder template; raw confirm-token values
  are not embedded.
- READY sessions remain default-off.  WSTA70 only creates a private launch
  manifest for an operator-selected, explicit WSTA58 live gate.
- Redaction checks are applied to the public summary and generated Markdown
  before Markdown is written.
- The committed report/source/test changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw private lease artifacts, inventories, status results, and launch manifests
  remain under `workspace/private/`.

## Validation

Compile check:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta70_persistent_session_launch_manifest.py
```

Result: pass

WSTA70 focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta70_persistent_session_launch_manifest
```

Result: `Ran 8 tests ... OK`

Focused WSTA52-WSTA70 regression:

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
  tests.test_server_distro_wsta70_persistent_session_launch_manifest
```

Result: `Ran 99 tests ... OK`

Fresh WSTA63 + WSTA64 + WSTA67 + WSTA70 private smoke: pass.

## Next

The default-off persistent exposure workflow now has prepare, readiness, status,
retire, inventory, bulk-retire cleanup, operator snapshot, and selected launch
manifest layers.  Continue only with explicit operator-selected WSTA58 live
proof, or further default-off operator UX/reporting that does not start public
exposure.
