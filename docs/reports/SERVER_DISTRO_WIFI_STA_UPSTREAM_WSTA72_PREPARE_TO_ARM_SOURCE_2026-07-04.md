# WSTA72 Persistent Prepare-To-Arm Source

- Date: 2026-07-04
- Scope: host-only orchestrator for the default-off persistent exposure ladder
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta72-persistent-prepare-to-arm-pass`

## Summary

WSTA72 composes the default-off persistent exposure preparation ladder into one
operator command.  It runs:

```text
WSTA63 prepare session
WSTA64 readiness audit
WSTA67 inventory
WSTA69 operator snapshot
WSTA70 launch manifest selection
WSTA71 launch-readiness audit
```

The output is a private prepare-to-arm JSON plus Markdown summary:

```text
wsta72_prepare_to_arm.json
wsta72_prepare_to_arm.md
```

This is still not live execution.  WSTA72 does not replace token placeholders,
start a tunnel, touch the device, connect Wi-Fi, or run public smoke.  The pass
state means the private run tree has reached `READY_TO_ARM_DEFAULT_OFF` and an
operator may separately choose the explicit WSTA58 live gate.

## Source Change

Added:

- `workspace/public/src/scripts/server-distro/run_wsta72_persistent_prepare_to_arm.py`
- `tests/test_server_distro_wsta72_persistent_prepare_to_arm.py`

The runner is fail-closed until the operator supplies the host-only preparation
gate:

```text
python3 workspace/public/src/scripts/server-distro/run_wsta72_persistent_prepare_to_arm.py \
  --prepare-to-arm \
  --ttl-sec 300 \
  --ack-credentialed-wifi \
  --ack-public-exposure \
  --native-confirm-token-source private \
  --public-confirm-token-source private
```

WSTA72 returns pass only if every composed stage passes:

```text
wsta63-persistent-session-preflight-pass
wsta64-persistent-session-readiness-pass
wsta67-persistent-session-inventory-pass
wsta69-persistent-session-snapshot-pass
wsta70-persistent-session-launch-manifest-pass
wsta71-persistent-launch-readiness-audit-pass
```

## Private Smoke

Private smoke directory:

```text
workspace/private/runs/server-distro/wsta72-prepare-to-arm-smoke-20260704T104514Z
```

Observed WSTA72 result:

```text
decision=wsta72-persistent-prepare-to-arm-pass
state=READY_TO_ARM_DEFAULT_OFF
wsta63_decision=wsta63-persistent-session-preflight-pass
wsta64_decision=wsta64-persistent-session-readiness-pass
wsta67_decision=wsta67-persistent-session-inventory-pass
wsta69_decision=wsta69-persistent-session-snapshot-pass
wsta70_decision=wsta70-persistent-session-launch-manifest-pass
wsta71_decision=wsta71-persistent-launch-readiness-audit-pass
initial_seconds_remaining=299
live_command_template contains <native-confirm-token>
live_execution_requested=false
```

Key final artifact:

```text
workspace/private/runs/server-distro/wsta72-prepare-to-arm-smoke-20260704T104514Z/wsta71-readiness/wsta71_launch_readiness.json
```

## Safety

- No boot image was built or flashed.
- No forbidden partition was touched.
- No device command, native reboot, Wi-Fi association, DHCP, public tunnel,
  public smoke, userdata action, switch-root, or external service action ran.
- The runner has no `native_init_flash.py` or `a90ctl.py` call path.
- The WSTA58 command remains a placeholder template; raw confirm-token values
  are not embedded.
- READY sessions remain default-off.  WSTA72 only prepares private artifacts for
  a later explicit operator-selected WSTA58 live gate.
- Redaction checks are applied to the public summary and generated Markdown.
- The committed report/source/test changes contain no raw public URL, public
  tunnel domain, confirm-token value, Wi-Fi credential, SSID, BSSID, MAC, IP,
  gateway, DNS, lease id value, or device serial.
- Raw private lease artifacts, inventories, status results, launch manifests,
  readiness audits, and prepare-to-arm outputs remain under `workspace/private/`.

## Validation

Compile check:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta72_persistent_prepare_to_arm.py
```

Result: pass

WSTA72 focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta72_persistent_prepare_to_arm
```

Result: `Ran 7 tests ... OK`

Focused WSTA52-WSTA72 regression:

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
  tests.test_server_distro_wsta72_persistent_prepare_to_arm
```

Result: `Ran 114 tests ... OK`

Fresh WSTA72 private smoke: pass.

## Next

The default-off persistent exposure workflow now has a one-command host-only
prepare-to-arm path that produces all artifacts through WSTA71.  Continue only
with explicit operator-selected WSTA58 live proof, or further default-off
operator UX/reporting that does not start public exposure.
