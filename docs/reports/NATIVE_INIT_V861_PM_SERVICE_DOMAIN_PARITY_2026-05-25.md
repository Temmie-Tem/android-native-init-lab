# Native Init V861 pm-service Domain Parity Report

## Result

V861 passed as a bounded diagnostic/proof cycle.

| Unit | Evidence | Decision |
|---|---|---|
| helper v133 build | `tmp/wifi/v861-execns-helper-v133-build/a90_android_execns_probe` | static aarch64, sha256 `ff7039d41f7d4b0c17c480297a58b33cac49aeceaba33a865a347d300fc2fb15` |
| plan | `tmp/wifi/v861-pm-service-domain-parity-plan-r2/manifest.json` | `v861-pm-service-domain-parity-plan-ready` |
| live | `tmp/wifi/v861-pm-service-domain-parity-live-r2/manifest.json` | `v861-exec-target-accepted-current-kernel-no-subsys-hold` |

## Helper Change

Helper v133 adds Android default SELinux exec-context mappings:

| Target | Context |
|---|---|
| `/vendor/bin/pm-service` | `u:r:vendor_per_mgr:s0` |
| `/vendor/bin/pm-proxy` | `u:r:vendor_per_mgr:s0` |

## Live Replay

The bounded replay deployed helper v133, reused the V860 private property root,
materialized and cleaned up Android-equivalent eSoC/subsys nodes, and ran only
the `pm-service`/`pm-proxy` start-only path.

| Observation | Value |
|---|---|
| property denial total | `0` |
| `pm-service` exec target accepted | `true` |
| `pm-proxy` exec target accepted | `true` |
| `pm-service` runtime `attr/current` | `kernel` |
| `pm-proxy` runtime `attr/current` | `kernel` |
| `pm-service` exit code | `0` |
| `pm-proxy` exit code | `1` |
| `pm-service` fd count | `0` |
| `pm-proxy` fd count | `5` |
| `pm-service` holds `/dev/subsys_esoc0` | `false` |
| `pm-service` holds `/dev/subsys_modem` | `false` |
| `mdm_helper` / `ks` start executed | `false` |
| Wi-Fi HAL / bring-up executed | `false` |
| external ping executed | `false` |

## Device Health

Post-run selftest passed:

```text
selftest: pass=11 warn=1 fail=0 duration=40ms entries=12
```

## Interpretation

The V861 change closes the helper-side missing target-context mapping, but it
does not reproduce Android process-domain state or subsystem fd ownership. The
helper can request `u:r:vendor_per_mgr:s0`, yet the observed runtime
`attr/current` remains `kernel` and `pm-service` still exits with code `0`
before holding any fds.

The active blocker is therefore not the specific missing helper mapping alone.
The next useful boundary is the native init/service launch context around
PeripheralManager: init service metadata, ctl/start property semantics,
provider registration, and whether Android keeps `vendor.per_mgr` alive through
init rather than by direct exec.

## Next Gate

V862 should be a host/live classifier for the Android `vendor.per_mgr` service
contract:

1. Compare Android init service fields for `vendor.per_mgr`,
   `vendor.per_proxy`, and `vendor.per_proxy_helper`.
2. Classify whether native direct exec misses init-managed service state,
   class/group/supplementary groups, disabled/oneshot/restart policy, or
   property-triggered lifecycle.
3. If safe, replay only an init-service-equivalent start wrapper below
   `mdm_helper`, Wi-Fi HAL, scan/connect, DHCP/routes, and external ping.
