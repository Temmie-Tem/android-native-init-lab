# WSTA217 Operator Status Default-Drop Hardening Policy

Date: 2026-07-05

## Verdict

PASS.  WSTA217 folds the WSTA216 legacy-iptables loopback/default-drop
hardening policy into the WSTA108 operator server status bundle.  The operator
surface now shows that the default-drop policy is defined, explicit-gated,
default-off, control-plane-preserving, and not executed by this status unit.

Private evidence:

```text
workspace/private/runs/server-distro/wsta217-operator-status-default-drop-hardening-policy-20260705T2054KST/wsta108_operator_server_status.json
workspace/private/runs/server-distro/wsta217-operator-status-default-drop-hardening-policy-20260705T2054KST/wsta108_operator_server_status.md
```

Decision:

```text
wsta108-operator-server-status-source-pass
```

## Status State

The accepted status records:

```text
default_drop_hardening_policy_defined=true
state=LEGACY_IPTABLES_DEFAULT_DROP_HARDENING_POLICY_DEFINED
hardening_lever=legacy-iptables-loopback-default-drop
activation=explicit-operator-gated
default_public_off=true
live_execution_requested=false
packet_filter_mutation_by_wsta216=false
control_plane_preserved=true
```

Operator next-actions now end with:

```text
use-legacy-iptables-default-drop-only-through-attended-dpublic-live-gate
move-to-attended-default-drop-live-use-or-next-hardening-layer
```

The previous policy-definition next action is retired from the current operator
status once WSTA216 is supplied:

```text
move-to-legacy-iptables-default-drop-hardening
```

## Safety

This was host-only status aggregation.  No device action, boot flash, native
reboot, Wi-Fi connect/association, DHCP, ping, public tunnel, public smoke,
packet-filter mutation, rootfs mutation, userdata write, LSM profile load, or
switch-root occurred.

Safety fields remained:

```text
device_action=false
boot_flash=false
native_reboot=false
wifi_connect=false
dhcp=false
public_tunnel=false
public_smoke=false
packet_filter_mutation=false
userdata_touch=false
switch_root=false
public_url_value_logged=false
secret_values_logged=0
```

## Validation

```text
python3 -m py_compile workspace/public/src/scripts/server-distro/run_wsta108_operator_server_status.py tests/test_server_distro_wsta108_operator_server_status.py
PYTHONPATH=tests python3 -m unittest tests/test_server_distro_wsta108_operator_server_status.py
PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_server_distro*.py'
```

Results:

```text
WSTA108 unit tests: 57 tests OK
server-distro regression: 803 tests OK
host-only WSTA217 run: PASS
```

## Code Changes

- Added `--wsta216-default-drop-hardening-policy-json` to WSTA108.
- Added WSTA216 compaction into `hardening.default_drop_hardening_policy`.
- Added status checks for policy definition, explicit gate, default-off, no live
  execution, no packet-filter mutation in WSTA108, and control-plane
  preservation.
- Updated operator next-actions after the policy is folded into status.
- Added focused WSTA108 tests for WSTA217 and WSTA216 fail-closed paths.

## Next

Continue from the now-visible hardening state: either use the existing attended
D-public live gate with the default-drop policy precondition, or proceed to the
next hardening layer without weakening the default-off gate.
