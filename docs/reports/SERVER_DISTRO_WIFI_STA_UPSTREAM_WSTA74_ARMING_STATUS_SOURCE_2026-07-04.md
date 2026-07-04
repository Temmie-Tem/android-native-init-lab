# WSTA74 Persistent Arming Status Source

- Date: 2026-07-04
- Scope: host-only status check for WSTA73 arming packets
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta74-persistent-arming-status-pass`

## Summary

WSTA74 consumes a private WSTA73 arming packet and reports whether it is still
usable for an explicit WSTA58 live gate.  It reruns WSTA73 against the packet's
original WSTA72 prepare-to-arm path, then classifies the packet as:

```text
READY_TO_EXECUTE_DEFAULT_OFF
STALE_OR_NOT_READY
DRIFT_RECHECK_REQUIRED
```

This is a status layer, not a launch.  WSTA74 does not replace token
placeholders, start a tunnel, touch the device, connect Wi-Fi, or run public
smoke.

## Source Change

Added:

- `workspace/public/src/scripts/server-distro/run_wsta74_persistent_arming_status.py`
- `tests/test_server_distro_wsta74_persistent_arming_status.py`

The runner is fail-closed until a private WSTA73 arming packet is supplied:

```text
python3 workspace/public/src/scripts/server-distro/run_wsta74_persistent_arming_status.py \
  --wsta73-arming-packet-json workspace/private/runs/server-distro/<wsta73-run>/wsta73_arming_packet.json
```

WSTA74 returns a pass decision when it can evaluate a valid WSTA73 packet.  The
packet's current readiness is carried in `arming_status.state` and
`arming_status.ready_for_live`.

## Private Smoke

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta74-arming-status-smoke-20260704T105643Z
```

Observed flow:

```text
WSTA72 prepare-to-arm
WSTA73 arming packet
WSTA74 status over the WSTA73 packet
```

Observed WSTA74 result:

```text
decision=wsta74-persistent-arming-status-pass
state=READY_TO_EXECUTE_DEFAULT_OFF
ready_for_live=true
wsta73_recheck_decision=wsta73-persistent-arming-packet-pass
template_match=true
initial_seconds_remaining=298
recommended_next_action=operator-may-run-explicit-wsta58-live-gate
live_execution_requested=false
```

Generated status:

```text
workspace/private/runs/server-distro/wsta74-arming-status-smoke-20260704T105643Z/status/wsta74_arming_status.json
workspace/private/runs/server-distro/wsta74-arming-status-smoke-20260704T105643Z/status/wsta74_arming_status.md
```

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- No device command, native reboot, Wi-Fi association, DHCP, public tunnel,
  public smoke, userdata action, switch-root, or external service action ran.
- The runner has no `native_init_flash.py` or `a90ctl.py` call path.
- The WSTA58 command remains a placeholder template; raw confirm-token values
  are not embedded.
- READY status remains default-off.  WSTA74 only reports whether an operator may
  separately select the explicit WSTA58 live gate.
- Redaction checks are applied to the public summary and generated Markdown.
- The committed report/source/test changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw private prepare-to-arm outputs, WSTA73 packets, WSTA73 rechecks, and WSTA74
  status artifacts remain under `workspace/private/`.

## Validation

Compile check:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta74_persistent_arming_status.py
```

Result: pass

WSTA74 focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta74_persistent_arming_status
```

Result: `Ran 7 tests ... OK`

Focused WSTA52-WSTA74 regression:

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
  tests.test_server_distro_wsta74_persistent_arming_status
```

Result: `Ran 128 tests ... OK`

Fresh WSTA72 + WSTA73 + WSTA74 private smoke: pass.

## Next

The default-off persistent exposure workflow now has prepare-to-arm, arming
packet, and packet status surfaces.  Continue only with explicit
operator-selected WSTA58 live proof, or further default-off operator UX/reporting
that does not start public exposure.
