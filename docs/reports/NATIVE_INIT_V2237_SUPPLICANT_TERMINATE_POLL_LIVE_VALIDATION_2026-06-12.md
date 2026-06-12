# Native Init V2237 Supplicant Terminate Poll Live Validation

Date: `2026-06-12`

## Identity

| Field | Value |
| --- | --- |
| Run ID | `V2237` |
| Native init | `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)` |
| Build tag | `v2237-supplicant-terminate-poll` |
| Helper | `a90_android_execns_probe helper-v427`, SHA256 `062c7a491bee66bcb7112850f4581e53e58d923719d85dbbe651d9df285ee910` |
| Boot image | `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img` |
| Boot SHA256 | `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f` |
| Builder | `workspace/public/src/scripts/revalidation/build_native_init_boot_v2237_supplicant_terminate_poll.py` |
| Source/build report | `docs/reports/NATIVE_INIT_V2237_SUPPLICANT_TERMINATE_POLL_SOURCE_BUILD_2026-06-12.md` |
| Private live evidence | `workspace/private/runs/wifi/v2237-supplicant-terminate-poll-20260612-102531/` |
| Host commit before run | `8481bf6e` |
| Device flash | yes, boot partition only |

## Reason

V2236 fixed stale-carrier success by requiring `wpa_state=COMPLETED`, but it
still used a blind 500 ms delay after `TERMINATE` when replacing an existing
`wpa_supplicant` instance. V2237 replaces that delay with a bounded process-exit
poll and SIGKILL escalation.

The specific implementation goal was:

- keep V2236 strict connect semantics;
- send `TERMINATE` to an existing supplicant;
- wait up to 3000 ms for `wpa_supplicant` to disappear;
- if it does not exit, send `SIGKILL` to matching `wpa_supplicant` processes;
- wait up to 1500 ms after SIGKILL;
- fail with `wifi-connect-supplicant-terminate-timeout` instead of starting a
  new profile on top of an uncollected stale process.

## Implementation Summary

Changed file:

- `workspace/public/src/native-init/a90_wifi.c`

New connect telemetry:

- `supplicant.existing_terminate_attempted`
- `supplicant.existing_terminate_wait_timeout_ms`
- `supplicant.existing_terminate_wait_rc`
- `supplicant.existing_terminate_wait_elapsed_ms`
- `supplicant.process_count_after_terminate`
- `supplicant.existing_kill_attempted`
- `supplicant.existing_kill_rc`
- `supplicant.existing_kill_wait_timeout_ms`
- `supplicant.existing_kill_wait_rc`
- `supplicant.existing_kill_wait_elapsed_ms`
- `supplicant.process_count_after_kill`

Documentation change:

- `docs/operations/NATIVE_INIT_WIFI_LIFECYCLE_COMMANDS.md` documents
  `wifi-connect-supplicant-terminate-timeout`.

## Static And Build Validation

Host validation:

```text
python3 -m py_compile workspace/public/src/scripts/revalidation/build_native_init_boot_v2237_supplicant_terminate_poll.py
git diff --check
```

Both passed before flashing.

Source build result:

```text
decision=v2237-supplicant-terminate-poll-source-build-pass
cycle=V2237
init_version=0.9.268
init_build=v2237-supplicant-terminate-poll
init_sha256=7e30cf72c7ad2db941589daf769f255a0abe529daf295593af0078006a2a4315
ramdisk_sha256=2e627089278574d2bc358dd055f7a78007c7a5c333bb9f8551842fbe51fa7235
boot_sha256=b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f
```

## Flash Safety Gates

Before flash:

```text
current device=A90 Linux init 0.9.267 (v2236-strict-wifi-connect)
current selftest=pass=11 warn=1 fail=0
rollback image=workspace/private/inputs/boot_images/boot_linux_v2236_strict_wifi_connect.img
rollback SHA256=47dea2d602e25b60d7e6cd20619076446de0066fff0ed8b5ac80286f279ccd5b
known-good fallback=workspace/private/inputs/boot_images/boot_linux_v48.img
known-good fallback SHA256=1c87fa59712395027c5c2e489b15c4f6ddefabc3c50f78d3c235c4508a63e042
```

Flash command class:

```text
python3 workspace/public/src/scripts/revalidation/native_init_flash.py --from-native ...
```

Flash result:

```text
local image sha256=b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f
remote image sha256=b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f
boot block prefix sha256=b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f
post-flash version=A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)
post-flash selftest=pass=11 warn=1 fail=0
```

## Live Wi-Fi Validation

Bounded same-boot validation:

1. wait for `wlan0_present=1`;
2. run bounded scan;
3. connect 5 GHz profile;
4. run DHCP and bounded gateway/internet ping;
5. connect directly to 2.4 GHz profile without manual cleanup;
6. run DHCP and bounded gateway/internet ping;
7. cleanup;
8. verify `selftest fail=0`.

Result summary:

| Step | Evidence |
| --- | --- |
| `wlan0` wait | `wlan0_present=1` after poll 63 |
| Scan | `scan_result_count=11`, `decision=wifi-scan-pass` |
| 5 GHz connect | `ctrl.status_confirm.completed=1`, `freq=5745`, `decision=wifi-connect-carrier-up` |
| 5 GHz DHCP | `dhcp_duration_ms=501`, `decision=wifi-dhcp-pass` |
| 5 GHz ping | gateway `0%` loss, internet `0%` loss, `decision=wifi-ping-pass` |
| Direct 2.4 GHz switch | stale supplicant detected, terminate poll succeeded in `104 ms`, `freq=2412`, `decision=wifi-connect-carrier-up` |
| 2.4 GHz DHCP | `dhcp_duration_ms=100`, `decision=wifi-dhcp-pass` |
| 2.4 GHz ping | gateway `0%` loss, internet `0%` loss, `decision=wifi-ping-pass` |
| Cleanup | `decision=wifi-cleanup-done` |
| Final selftest | `selftest: pass=11 warn=1 fail=0` |

Direct-switch terminate-poll proof:

```text
supplicant.process_count_before=1
supplicant.existing_terminate_attempted=1
ctrl.terminate_existing.rc=0
supplicant.existing_terminate_wait_timeout_ms=3000
supplicant.existing_terminate_wait_rc=0
supplicant.existing_terminate_wait_elapsed_ms=104
supplicant.process_count_after_terminate=0
supplicant.existing_kill_attempted=0
ctrl.status_confirm.field.wpa_state=COMPLETED
ctrl.status_confirm.field.freq=2412
ctrl.status_confirm.completed=1
```

## Decision

`V2237` passes as the current native-init Wi-Fi baseline candidate.

Promote:

- `A90 Linux init 0.9.268 (v2237-supplicant-terminate-poll)`
- `workspace/private/inputs/boot_images/boot_linux_v2237_supplicant_terminate_poll.img`
- SHA256 `b2ea2d26d160b7702ce7d4438b84367788eea26c6a5bbe4ed93f3d270292ac7f`

The V2236 stale-carrier fix remains intact, and V2237 removes the remaining
blind post-`TERMINATE` sleep from direct profile switching.

## Remaining Risk

Long idle/hold data-path stability is still separate from this focused
terminate-poll validation. V2237 does not claim a new multi-minute or multi-hour
Wi-Fi soak result.
