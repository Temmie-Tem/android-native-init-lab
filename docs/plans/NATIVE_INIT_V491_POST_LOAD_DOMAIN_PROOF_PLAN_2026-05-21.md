# Native Init V491 Post-Load Domain Proof Plan

- Date: 2026-05-21 KST
- Scope: post-V490 SELinux domain-transition proof before any daemon or Wi-Fi HAL start
- Status: implementation-ready; live V491 requires a successful V490 policy-load manifest
- Final Wi-Fi objective status: not achieved yet

## Background

V487 proved that before Android policy load, requested Android contexts such as `u:r:init:s0` and `u:r:hal_wifi_default:s0` still resolved back to `kernel` after static helper re-exec. V489 proved that native init can compile the Android split policy. V490 is prepared to load that compiled policy into `/sys/fs/selinux/load`.

V491 is the next safe step after V490. It does not load policy itself. It only checks whether V490 changed the kernel SELinux state enough for a native-init child to enter useful Android domains.

## Preconditions

V491 requires a V490 manifest with:

```text
decision=v490-selinux-policy-load-proof-pass
pass=true
policy_load_executed=true
init_reexec_executed=false
daemon_start_executed=false
wifi_hal_start_executed=false
wifi_bringup_executed=false
```

The runner enforces this through:

```text
--v490-manifest path/to/V490/manifest.json
```

Without that manifest, V491 must remain blocked.

## Test Matrix

The runner uses the already deployed `a90_android_execns_probe v48` mode:

```text
--mode selinux-domain-proof
```

Contexts:

| context | reason |
|---|---|
| `u:r:init:s0` | proves native child can enter Android init domain |
| `u:r:hal_wifi_default:s0` | direct Wi-Fi HAL target candidate |
| `u:r:servicemanager:s0` | service-manager start candidate |
| `u:r:hwservicemanager:s0` | HAL binder registration candidate |

Attribute modes:

| attr mode | reason |
|---|---|
| `current` | tests direct `/proc/self/attr/current` write |
| `exec` | tests exec transition via `/proc/self/attr/exec` |
| `both` | tests current+exec combined behavior |

## Safety Boundary

V491 is allowed to:

- write child-local SELinux proc attrs inside the helper child
- run the static post-exec current-context probe
- capture process and netdev postflight state

V491 is not allowed to:

- write `/sys/fs/selinux/load`
- reexec PID1
- start service-manager or hwservicemanager
- start CNSS or Wi-Fi HAL
- start supplicant or wificond
- scan, connect, DHCP, route, or ping externally

## Approval

Required phrase:

```text
approve v491 post-load SELinux domain proof only; no policy load, no daemon start and no Wi-Fi bring-up
```

## Decision Rules

| decision | meaning |
|---|---|
| `v491-post-load-domain-handoff-present` | at least one requested domain survived static re-exec; move to service-manager/HAL registration planning |
| `v491-post-load-domain-kernel-stuck` | policy load alone did not solve domain handoff; inspect SELinux transition rules or alternate Android init handoff |
| `v491-post-load-domain-proof-blocked` | V490 evidence, helper, runtime, process, or Wi-Fi-clean precondition is missing |

## Next Work

1. Run V490 policy-load proof under its explicit approval.
2. Pass the V490 manifest to V491 preflight.
3. If V491 proves a useful domain, plan service-manager/HAL registration retry.
4. If registration works, continue to Wi-Fi readiness, scan/connect/link-up, DHCP/routing, and external ping.
