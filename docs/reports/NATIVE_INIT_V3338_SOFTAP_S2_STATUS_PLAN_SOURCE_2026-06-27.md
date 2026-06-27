# Native Init V3338 SoftAP S2 Status/Plan Source

## Summary

- Cycle: `V3338`
- Decision: `v3338-softap-s2-status-plan-source-pass`
- Scope: source/docs/test only.
- Device action: none.
- Flash action: none.
- Wi-Fi mutation: none.
- Server exposure: none.
- Secrets/network identifiers: none used; no SSID, PSK, MAC/BSSID, client identifier, concrete network
  address, storage UUID, or raw log is recorded.

V3338 adds the first native-init `wifi softap` command surface, but deliberately keeps it below AP
bring-up. It reports the S1 no-go blocker through machine-readable fields and does not start AP mode,
hostapd, DHCP-server mode, or a transfer listener.

## Change

- Added `A90_WIFI_SOFTAP_VERSION` and `A90_WIFI_SOFTAP_ROOT`.
- Added `wifi softap` dispatch under the existing `wifi` command.
- Added:
  - `wifi softap`
  - `wifi softap status`
  - `wifi softap plan`
  - `wifi softap prepare [profile]`
  - `wifi softap cleanup`
- The surface calls `a90_wififeas_evaluate()` and prints:
  - feasibility decision/reason/next
  - WLAN/rfkill/module/candidate gates
  - inventory counters
  - S0-S4 plan state for `plan` and `prepare`
  - explicit non-mutation fields
- Updated `docs/operations/NATIVE_INIT_WIFI_LIFECYCLE_COMMANDS.md`.
- Added `tests/test_native_softap_s2_source_v3338.py`.

## Non-Mutation Contract

The S2 source surface hard-reports:

```text
config_write_attempted=0
hostapd_start_attempted=0
dhcp_server_start_attempted=0
listener_start_attempted=0
interface_mode_change_attempted=0
address_assign_attempted=0
server_exposure_attempted=0
start_supported=0
start_allowed=0
ssid_psk_logged=0
```

`prepare` is dry-run/no-op while the S1 lower gate remains blocked. The expected decision on the
current resident is `softap-prepare-blocked-wlan-gate`.

## Validation

```text
PYTHONPYCACHEPREFIX=workspace/private/tmp/pycache python3 -m py_compile tests/test_native_softap_s2_source_v3338.py
PYTHONPYCACHEPREFIX=workspace/private/tmp/pycache python3 tests/test_native_softap_s2_source_v3338.py
aarch64-linux-gnu-gcc -std=gnu11 -Wall -Wextra -Werror -Os -Iworkspace/public/src/native-init -c workspace/public/src/native-init/a90_wifi.c -o workspace/private/builds/native-init/v3338-softap-s2-compile/a90_wifi.o
file workspace/private/builds/native-init/v3338-softap-s2-compile/a90_wifi.o
git diff --check
```

Results:

- V3338 source test: `5` tests passed.
- AArch64 object compile: PASS.
- Object file type: `ELF 64-bit LSB relocatable, ARM aarch64`.
- `git diff --check`: PASS.

## Safety

- No boot image was built.
- No flash was run.
- No live device command was run for this source unit.
- No credentials were read.
- No config file was generated.
- No AP daemon, DHCP-server daemon, or listener was started.
- No interface mode, address, route, rfkill, firmware, module, PMIC, regulator, GDSC, GPIO, backlight,
  panel, forbidden partition, or raw block path was touched.

## Next Unit

V3339 should either:

- build/flash a bounded candidate and live-check `wifi softap status|plan|prepare` outputs only, with
  `start_allowed=0` and follow-up `selftest fail=0`; or
- remain host-only and add a read-only hostapd/vendor asset classifier if the current resident's missing
  AP stack needs to be explained before flashing the status/plan surface.
