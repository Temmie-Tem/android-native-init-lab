# WSTA216 Default-Drop Hardening Policy

Date: 2026-07-05

## Verdict

PASS.  WSTA216 turns the already proven legacy-iptables loopback/default-drop
path into the next explicit/default-off D-public hardening policy step.  This is
a source/policy unit only: it does not apply packet-filter rules or start public
exposure.

Private evidence:

```text
workspace/private/runs/server-distro/wsta216-default-drop-hardening-policy-20260705T2043KST/wsta216_result.json
workspace/private/runs/server-distro/wsta216-default-drop-hardening-policy-20260705T2043KST/wsta216_default_drop_hardening_policy.json
workspace/private/runs/server-distro/wsta216-default-drop-hardening-policy-20260705T2043KST/wsta216_default_drop_hardening_policy.md
```

Decision:

```text
wsta216-default-drop-hardening-policy-source-pass
```

## Policy State

The emitted policy records:

```text
schema=a90-wsta216-legacy-iptables-default-drop-hardening-policy-v1
state=LEGACY_IPTABLES_DEFAULT_DROP_HARDENING_POLICY_DEFINED
hardening_lever=legacy-iptables-loopback-default-drop
backend=legacy-iptables
policy=loopback-default-drop
activation=explicit-operator-gated
default_public_off=true
live_execution_requested=false
packet_filter_mutation_by_wsta216=false
```

The required live sequence remains bounded and default-off:

```text
preflight-helper
save-existing-rules-before-mutation
local-loopback-smoke-before-apply
apply-loopback-default-drop-before-public-exposure
verify-usb-control-plane-preserved
restore-exact-rules-before-public-off-success
cleanup-runtime-services
```

## Evidence Folded

WSTA216 accepts the policy only when all of these existing artifacts agree:

```text
WSTA215 operator status: packet-filter loopback and control-plane proof live, AppArmor parked
WSTA94 live proof: preflight/apply/default-drop/loopback/restore/health all proven
packet-filter control summary: preflight/apply/restore pass and USB control session survives apply
source wiring: WSTA42 applies before public start and restores in finally; WSTA76/79/80 keep default-off gates
```

## Safety

This was host-only policy generation.  No device action, boot flash, native
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
python3 -m py_compile workspace/public/src/scripts/server-distro/run_wsta216_default_drop_hardening_policy.py tests/test_server_distro_wsta216_default_drop_hardening_policy.py
PYTHONPATH=tests python3 -m unittest tests/test_server_distro_wsta216_default_drop_hardening_policy.py
PYTHONPATH=tests python3 -m unittest discover -s tests -p 'test_server_distro*.py'
```

Results:

```text
WSTA216 unit tests: 4 tests OK
server-distro regression: 800 tests OK
host-only WSTA216 run: PASS
```

## Code Changes

- Added `run_wsta216_default_drop_hardening_policy.py`.
- Added focused WSTA216 tests for the valid policy, explicit gate, private input
  gate, control-plane survival evidence, and live-execution regression.

## Next

Fold WSTA216 into the WSTA108 operator status bundle so the operator surface
shows `LEGACY_IPTABLES_DEFAULT_DROP_HARDENING_POLICY_DEFINED` and the next
D-hardening action can move from policy definition to an explicit attended live
use of the existing D-public gate.
