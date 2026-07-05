# WSTA219 Attended Default-Drop Live

Date: 2026-07-05
Scope: attended D-public/default-drop live validation plus source fixes

## Result

PASS.  The explicit WSTA88 live workflow completed with the legacy-iptables
loopback/default-drop packet filter applied before public exposure and restored
after cleanup.

Live result:

`workspace/private/runs/server-distro/wsta219-explicit-default-drop-live-fixed-20260705T213431KST/wsta88_operator_workflow.json`

Decision:

`wsta88-persistent-operator-workflow-live-pass`

Final native health stayed clean on resident v3402:

- `status`: `selftest pass=12 warn=1 fail=0`, exposure guard OK, NCM/tcpctl ready.
- `selftest`: `pass=12 warn=1 fail=0`.

No boot flash, forbidden partition write, userdata write, LSM profile load, or
switch-root occurred.  The live action performed bounded runtime Wi-Fi,
D-public tunnel/smoke, Debian rootfs mount, and packet-filter mutation behind
the explicit operator gate.

## Live Blockers Fixed

The first WSTA219 live attempt exposed two source drifts:

- WSTA28/WSTA24 post-reboot health rejected resident v3402 because the supported
  native build list stopped at v3397.  The post-reboot `version/status/selftest`
  commands were healthy; only the supported-build classifier was stale.
- WSTA88/WSTA80 defaulted to the original D1 Debian image even though the live
  path now requires the WSTA98 packet-filter-ready rootfs.  That produced
  `wsta42-blocked-packet-filter-preflight` with missing
  `/usr/sbin/iptables-legacy*` tools.

## Implementation

- Extended the WSTA24 supported native lineage through v3402:
  v3398, v3399, v3400, v3401, and v3402.
- Added tests proving v3402 is accepted by WSTA24/WSTA26 scan diagnostics.
- Promoted the WSTA98 packet-filter-ready image as the default D-public live
  image for WSTA42 and the wrapper chain WSTA43/WSTA55/WSTA58/WSTA80/WSTA88:
  SHA256 `2dae0d4dcfde1854f0d91b0fe94948720b175638261d156572e82ca7d18e928b`.
- Preserved explicit `--local-image`, `--local-image-sha256`,
  `--remote-image`, and `--remote-clean-image` overrides.

## Live Evidence

Initial and renewal WSTA55 both passed:

- `wsta55-short-lived-public-proof-live-pass`
- TTL expiry proof reported `PUBLIC_OFF`.
- WSTA48 redaction guard passed.
- Manual stop cleanup reported `PUBLIC_OFF`.

Both nested WSTA42 runs passed:

- `wsta42-native-uplink-dpublic-tunnel-pass`
- packet-filter preflight: `packet-filter-preflight-pass`
- packet-filter apply: `packet-filter-loopback-default-drop-applied`
- packet-filter restore: `packet-filter-restored`
- public smoke: HTTP 200 with marker/service/public-exposure markers OK
- final nested selftest: fail zero

WSTA58 and WSTA80 accepted the full live chain:

- `wsta58-renewal-manual-stop-live-pass`
- `wsta80-persistent-operator-execute-gate-live-pass`

The public URL, Wi-Fi credentials, tunnel credentials, network identifiers, and raw
secrets were not committed.

## Validation

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile <touched WSTA scripts and tests>
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest tests/test_server_distro_wsta24_native_wifi_uplink_client.py tests/test_server_distro_wsta26_scan_failure_diagnostic.py tests/test_server_distro_wsta28_reboot_materialization_gate.py tests/test_server_distro_wsta42_native_uplink_dpublic_tunnel.py tests/test_server_distro_wsta43_orchestrated_native_uplink_dpublic.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest tests/test_server_distro_wsta42_native_uplink_dpublic_tunnel.py tests/test_server_distro_wsta43_orchestrated_native_uplink_dpublic.py tests/test_server_distro_wsta55_short_lived_public_proof.py tests/test_server_distro_wsta58_renewal_manual_stop_proof.py tests/test_server_distro_wsta80_persistent_operator_execute_gate.py tests/test_server_distro_wsta88_persistent_operator_workflow.py
PYTHONPYCACHEPREFIX=/tmp/a90_pycache PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_server_distro*.py'
```

Results:

- Focused WSTA24/WSTA26/WSTA28/WSTA42/WSTA43 validation: `41 tests OK`.
- Focused WSTA42/WSTA43/WSTA55/WSTA58/WSTA80/WSTA88 regression:
  `68 tests OK`.
- Full server-distro regression: `806 tests OK`.
- Final device health: `selftest pass=12 warn=1 fail=0`.

## Next

WSTA219 closes the attended default-drop live use path.  Continue with the next
D-hardening layer or fold this WSTA219 live proof into the operator status bundle
so the default-drop live posture is visible without re-running public exposure.
