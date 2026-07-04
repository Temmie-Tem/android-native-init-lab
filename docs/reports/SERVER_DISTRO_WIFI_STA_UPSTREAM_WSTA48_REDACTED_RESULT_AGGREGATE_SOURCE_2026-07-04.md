# WSTA48 Redacted Result Aggregate Source

- Date: 2026-07-04
- Scope: host-only operator result aggregation
- Device action: none
- Flash: none
- Public exposure: none
- Decision: `wsta48-redacted-result-aggregate-source-pass`

## Summary

WSTA48 adds a concrete operator surface for the WSTA45/WSTA43/WSTA42 publish path:

- `workspace/public/src/scripts/server-distro/run_wsta48_redacted_result_aggregate.py`

The helper reads explicit WSTA result JSON files or directories supplied with `--input`,
recursively discovers `wsta*_result.json`, and emits a redacted aggregate summary.  It
reuses the existing WSTA45/WSTA43 public-summary allowlists and the WSTA43 WSTA42
summarizer.  Unknown WSTA result files are reduced to a narrow decision/check/safety
allowlist.

The output records:

- generated time;
- input/result counts;
- pass/fail decision counts;
- per-result kind, path, decision, start/end timestamps, and elapsed seconds;
- redacted public summaries only;
- a final redaction guard status.

## Redaction Guard

The helper fail-closes if the aggregate payload contains known confirm-token values,
public URL/domain material, public URL scratch paths, or obvious Wi-Fi credential
assignment strings.  The operator-facing guard metadata records labels/counts only, not
the raw blocked patterns.

## Safety

- No device command ran.
- No boot image was built or flashed.
- No native reboot, Wi-Fi association, DHCP, public tunnel, public smoke request, or
  external service action ran in this unit.
- The live WSTA46 aggregate validation read existing private artifacts only and wrote its
  output under `workspace/private/runs/`, which is not committed.
- No raw public URL, confirm token, SSID, PSK, BSSID, IP, gateway, or DNS value is
  committed.

## Validation

Focused tests:

```text
PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest \
  tests.test_server_distro_wsta48_redacted_result_aggregate \
  tests.test_server_distro_wsta42_native_uplink_dpublic_tunnel \
  tests.test_server_distro_wsta45_appliance_operator
```

Result: `Ran 22 tests ... OK`

Syntax:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile \
  workspace/public/src/scripts/server-distro/run_wsta48_redacted_result_aggregate.py
```

Result: pass

Actual WSTA46 aggregate smoke:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 \
  workspace/public/src/scripts/server-distro/run_wsta48_redacted_result_aggregate.py \
  --input workspace/private/runs/server-distro/wsta46-wsta45-publish-live \
  --output workspace/private/runs/server-distro/wsta48-wsta46-aggregate/wsta48_result.json
```

Result: `result_count=5`, `all_pass=True`; decisions counted:
`wsta27-materialization-scan-gate-pass`, `wsta28-reboot-materialization-scan-gate-pass`,
`wsta42-native-uplink-dpublic-tunnel-pass`, `wsta43-orchestrated-native-uplink-dpublic-pass`,
and `wsta45-appliance-operator-wsta43-profile-pass`.  The redaction guard passed.

```text
git diff --check
```

Result: pass

## Next

The source/productization track now has the core operator surfaces for this path:
profile wrapper, redacted publish template, consistent run end timestamps, and redacted
result aggregation.  The next meaningful WSTA step should move toward an appliance-level
operator runbook/HUD/menu integration or a deliberately gated persistent exposure design,
not another metadata-only cleanup.
