# Native Init V2236 Strict Wi-Fi Connect Live Validation

Date: `2026-06-12`

## Summary

V2236 is promoted as the current native-init baseline.

V2235 first validated that the V2232 service-object FWClass bridge baseline can
produce a functional native `wlan0` when exercised before the QCACLD/PSOC idle
window: passive scan passed, 5 GHz connect/DHCP/ping passed, and isolated
2.4 GHz connect/DHCP/ping passed. V2235 also exposed a validation bug: after a
hold/data-path failure, `wifi connect` could report `wifi-connect-carrier-up`
while supplicant status was still `DISCONNECTED`.

V2236 keeps the V2232 WLAN bring-up route and fixes that validation gap:

- stale `wpa_supplicant` is not reused across `wifi connect` profile changes;
- an existing supplicant is terminated before starting the requested profile;
- connect success now requires both carrier and
  `ctrl.status_confirm.field.wpa_state=COMPLETED`;
- direct 5 GHz to 2.4 GHz switching is live-validated without accepting stale
  carrier from the previous profile.

## Baseline Identity

| Field | Value |
| --- | --- |
| Build tag | `v2236-strict-wifi-connect` |
| Device-visible version | `A90 Linux init 0.9.267 (v2236-strict-wifi-connect)` |
| Boot image | `workspace/private/inputs/boot_images/boot_linux_v2236_strict_wifi_connect.img` |
| Boot SHA256 | `47dea2d602e25b60d7e6cd20619076446de0066fff0ed8b5ac80286f279ccd5b` |
| Builder | `workspace/public/src/scripts/revalidation/build_native_init_boot_v2236_strict_wifi_connect.py` |
| Source/build report | `docs/reports/NATIVE_INIT_V2236_STRICT_WIFI_CONNECT_SOURCE_BUILD_2026-06-12.md` |
| Primary live run | `workspace/private/runs/wifi/v2236-strict-connect-fresh-20260612-094037` |
| V2235 discovery run | `workspace/private/runs/wifi/v2235-baseline-connect-20260612-091225` |

## V2235 Discovery

V2235 on V2232 proved the baseline was functionally usable if commands ran soon
after `wlan0` appeared:

| Gate | Result |
| --- | --- |
| Immediate scan | `decision=wifi-scan-pass`, `scan_result_count=10` |
| 5 GHz connect | `decision=wifi-connect-carrier-up`, `wpa_state=COMPLETED`, `freq=5745` |
| 5 GHz DHCP | `decision=wifi-dhcp-pass`, masked IPv4 assigned, default route present |
| 5 GHz ping | gateway `0%` loss, internet `0%` loss |
| isolated 2.4 GHz connect | `decision=wifi-connect-carrier-up`, `wpa_state=COMPLETED`, `freq=2412` |

V2235 also exposed two follow-up facts:

- a 120 second 2.4 GHz hold kept carrier/status superficially up but ping failed
  with `100%` packet loss and DHCP refresh later failed;
- a subsequent 5 GHz reconnect could still return `wifi-connect-carrier-up`
  while `ctrl.status.field.wpa_state=DISCONNECTED`.

The second item is the V2236 fixed bug. The first item remains a separate
long-idle/hold data-path stability issue, not a blocker for bounded scan/connect
baseline promotion.

## V2236 Live Validation

Fresh V2236 boot was flashed from native through recovery and verified through
`cmdv1`:

- version: `A90 Linux init 0.9.267 (v2236-strict-wifi-connect)`;
- boot readback SHA matched
  `47dea2d602e25b60d7e6cd20619076446de0066fff0ed8b5ac80286f279ccd5b`;
- post-flash status reported `selftest: pass=11 warn=1 fail=0`;
- fresh validation reboot reached `wlan0_present=1` at poll `75`.

Functional results from the fresh validation run:

| Gate | Result |
| --- | --- |
| Passive scan | `decision=wifi-scan-pass`, `scan_result_count=9` |
| 5 GHz connect | `decision=wifi-connect-carrier-up`, `wpa_state=COMPLETED`, confirm `completed=1`, `freq=5745` |
| 5 GHz DHCP | `decision=wifi-dhcp-pass`, masked IPv4 assigned, default route present |
| 5 GHz ping | gateway `0%` loss, internet `0%` loss |
| direct 5 GHz to 2.4 GHz switch | existing supplicant terminated, process count after terminate `0` |
| 2.4 GHz connect | `decision=wifi-connect-carrier-up`, `wpa_state=COMPLETED`, confirm `completed=1`, `freq=2412` |
| 2.4 GHz DHCP | `decision=wifi-dhcp-pass`, masked IPv4 assigned, default route present |
| 2.4 GHz ping | gateway `0%` loss, internet `0%` loss |
| final cleanup | `decision=wifi-cleanup-done` |
| final selftest | `selftest: pass=11 warn=1 fail=0` |

Credential hygiene stayed intact: Wi-Fi commands reported
`secret_values_logged=0` and masked private IPv4 values.

## Code Change

`wifi connect` now rejects stale carrier by requiring a live supplicant status
confirmation:

- emits `ctrl.status_confirm.field.wpa_state` and
  `ctrl.status_confirm.completed`;
- returns success only when `carrier_up=1` and `wpa_state=COMPLETED`;
- returns `wifi-connect-status-not-completed` and terminates the spawned
  supplicant when carrier is up but supplicant is not associated;
- terminates an existing supplicant before starting a new profile, preventing
  profile-switch tests from reusing the previous in-memory network.

The public command contract is updated in
`docs/operations/NATIVE_INIT_WIFI_LIFECYCLE_COMMANDS.md`.

## Promotion Decision

Decision: `v2236-strict-wifi-connect-baseline-pass`.

V2236 becomes the current rollback/test baseline because it combines:

- the V2232 native `wlan0` producer path;
- strict connect success semantics;
- bounded 5 GHz and 2.4 GHz connect/DHCP/ping proof;
- cleanup and `selftest fail=0` after validation.

## Remaining Risk

Long idle/hold data-path stability is not closed by this promotion. V2235 showed
that a 120 second 2.4 GHz hold can lose packet forwarding while carrier remains
misleadingly up. That should be handled as a separate power-save/keepalive or
reconnect policy task, using `wpa_state`, DHCP route state, and ping as the gate;
carrier alone must not be used as a success criterion.
