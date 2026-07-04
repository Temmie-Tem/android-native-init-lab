# WSTA47 Operator Productization Source

- Date: 2026-07-04
- Scope: host-only productization polish for the proven WSTA45 profile publish path
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta47-operator-productization-source-pass`

## Summary

WSTA47 productizes the WSTA46-proven WSTA45 publish path without running another live
public gate.

The update has two parts:

- WSTA42 now stamps `ended_utc` through a shared `finish_result()` helper on terminal
  gate failures, helper/image failures, final classification, and the top-level runner
  error path.  This makes persisted result metadata easier to aggregate across runs.
- WSTA45 now exposes a redacted `operator_publish_template` and a
  `--print-publish-template` CLI.  The template includes the full profile-enabled
  publish command shape but uses `<native-confirm-token>` and `<public-confirm-token>`
  placeholders instead of secret values.

## Safety

- No boot image was built or flashed.
- No native reboot, Wi-Fi association, DHCP, public tunnel, public smoke request, or
  device command ran in this unit.
- The template output records placeholder tokens only.
- No public URL value, raw SSID, PSK, BSSID, IP, gateway, DNS value, or confirm-token
  value is committed.

## Validation

Focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta42_native_uplink_dpublic_tunnel \
  tests.test_server_distro_wsta45_appliance_operator
```

Result: `Ran 17 tests ... OK`

Syntax:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta42_native_uplink_dpublic_tunnel.py \
  workspace/public/src/scripts/server-distro/run_wsta45_appliance_operator.py
```

Result: pass

Template CLI:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta45_appliance_operator.py \
  --print-publish-template
```

Result: printed the publish command with `<native-confirm-token>` and
`<public-confirm-token>` placeholders, `secret_values_logged=0`, and
`public_url_value_logged=false`.

```text
git diff --check
```

Result: pass

## Next

WSTA48 should avoid more metadata churn unless it adds a concrete operator surface.  Good
next candidates are a short committed operator runbook for the WSTA45 publish template or
a source-only aggregation helper that consumes WSTA42/WSTA43/WSTA45 result JSON and
summarizes pass/fail timing without exposing private values.  Persistent always-on public
exposure remains a separate explicit gate.
