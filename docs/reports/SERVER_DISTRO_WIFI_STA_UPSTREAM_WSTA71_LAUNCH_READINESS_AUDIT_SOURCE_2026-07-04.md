# WSTA71 Persistent Launch Readiness Audit Source

- Date: 2026-07-04
- Scope: host-only freshness audit for a selected WSTA70 launch manifest
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta71-persistent-launch-readiness-audit-pass`

## Summary

WSTA71 adds the last default-off freshness check before an operator explicitly
chooses the WSTA58 live gate.  It consumes a private WSTA70 launch manifest,
reruns WSTA65 for the selected WSTA64 session, validates that the manifest still
matches the original WSTA63 session command template, and writes:

```text
wsta71_launch_readiness.json
wsta71_launch_readiness.md
```

This is an audit, not a launch.  It does not replace token placeholders, start a
tunnel, touch the device, connect Wi-Fi, or run public smoke.

## Source Change

Added:

- `workspace/public/src/scripts/server-distro/run_wsta71_persistent_launch_readiness_audit.py`
- `tests/test_server_distro_wsta71_persistent_launch_readiness_audit.py`

The runner is fail-closed until a private WSTA70 launch manifest is supplied:

```text
python3 workspace/public/src/scripts/server-distro/run_wsta71_persistent_launch_readiness_audit.py \
  --wsta70-launch-manifest-json workspace/private/runs/server-distro/<wsta70-run>/wsta70_launch_manifest.json
```

Before returning pass, WSTA71 requires:

```text
wsta70_decision=wsta70-persistent-session-launch-manifest-pass
wsta65_decision=wsta65-persistent-session-status-pass
session_state=READY
ready_for_live=true
manifest_consistency_ok=true
live_template_placeholders_only=true
```

If the selected session has aged into STALE/EXPIRED/NOT_READY, WSTA71 blocks and
writes the WSTA65 revalidation path for inspection.  If the WSTA63 command
template changed after WSTA70 emitted the launch manifest, WSTA71 blocks on
manifest drift.

## Private Smoke

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta71-launch-readiness-smoke-20260704T103945Z
```

Observed flow:

```text
READY session: WSTA63 -> WSTA64
WSTA67 inventory over the smoke root
WSTA70 launch manifest
WSTA71 readiness audit over the WSTA70 manifest
```

WSTA71 result:

```text
decision=wsta71-persistent-launch-readiness-audit-pass
state=READY_TO_ARM_DEFAULT_OFF
wsta65_session_state=READY
ready_for_live=true
initial_seconds_remaining=296
live_command_template contains <native-confirm-token>
live_execution_requested=false
```

Generated audit:

```text
workspace/private/runs/server-distro/wsta71-launch-readiness-smoke-20260704T103945Z/readiness/wsta71_launch_readiness.json
workspace/private/runs/server-distro/wsta71-launch-readiness-smoke-20260704T103945Z/readiness/wsta71_launch_readiness.md
```

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- No device command, native reboot, Wi-Fi association, DHCP, public tunnel,
  public smoke, userdata action, switch-root, or external service action ran.
- The runner has no `native_init_flash.py` or `a90ctl.py` call path.
- The WSTA58 command remains a placeholder template; raw confirm-token values
  are not embedded.
- READY sessions remain default-off.  WSTA71 only confirms that a WSTA70 launch
  manifest is still fresh enough for an explicit operator-selected WSTA58 live
  gate.
- Redaction checks are applied to the public summary and generated Markdown
  before Markdown is written.
- The committed report/source/test changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw private lease artifacts, inventories, status results, launch manifests,
  and readiness audits remain under `workspace/private/`.

## Validation

Compile check:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta71_persistent_launch_readiness_audit.py
```

Result: pass

WSTA71 focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta71_persistent_launch_readiness_audit
```

Result: `Ran 8 tests ... OK`

Focused WSTA52-WSTA71 regression:

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
  tests.test_server_distro_wsta71_persistent_launch_readiness_audit
```

Result: `Ran 107 tests ... OK`

Fresh WSTA63 + WSTA64 + WSTA67 + WSTA70 + WSTA71 private smoke: pass.

## Next

The default-off persistent exposure workflow now has prepare, readiness, status,
retire, inventory, bulk-retire cleanup, operator snapshot, selected launch
manifest, and last-moment launch-readiness audit layers.  Continue only with
explicit operator-selected WSTA58 live proof, or further default-off operator
UX/reporting that does not start public exposure.
