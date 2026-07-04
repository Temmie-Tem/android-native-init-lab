# Server Distro Wi-Fi STA Upstream WSTA32 Connect Carrier Diagnostics V3389 Live

- Date: `2026-07-04`
- Decision: `wsta25-blocked-helper-confirmed-autoconnect`
- Candidate: `A90 Linux init 0.11.145 (v3389-wifi-connect-carrier-diagnostics)`
- Boot image:
  `workspace/private/inputs/boot_images/boot_linux_v3389_wifi_connect_carrier_diagnostics.img`
- Boot SHA256: `e9eca0744848f51a44690768c4c6335e2867d718acb2cd1afc010c4cb1dc5b4c`
- Source-build report:
  `docs/reports/NATIVE_INIT_V3389_WIFI_CONNECT_CARRIER_DIAGNOSTICS_SOURCE_BUILD_2026-07-04.md`
- Live evidence:
  `workspace/private/runs/server-distro/wsta25-confirmed-autoconnect-live-20260704T033938Z/wsta25_result.json`

## Scope

WSTA32 exposed redacted native connect/carrier diagnostics through the existing autoconnect result
and uplink-service response.  The goal was to explain the WSTA31 `connect_rc=-107` blocker without
relying on raw console transcripts or leaking credentials.

V3389 records bounded, redacted fields for wlan0 readiness, link-up, supplicant config preparation,
supplicant start/control readiness, selected control commands, carrier wait, final WPA state, and
supplicant cleanup.  The Debian uplink helper allowlist now passes those fields through to the WSTA25
live runner JSON.

## Build And Flash

V3389 build validation completed:

- AArch64 helper/native-init compile;
- required-string audit for the new `connect_*` fields;
- preserved ramdisk overlay;
- boot image pack;
- SHA256 capture.

Rollback image checks passed before flash: v2321 and v2237 matched their expected hashes, and v48 was
present.  `native_init_flash.py --from-native` flashed only boot with the V3389 SHA pinned, verified
remote SHA, verified boot-prefix readback SHA, rebooted system, and verified native V3389 over cmdv1.
Total helper time was `61.766s`.  Post-flash native health reported V3389 and `selftest fail=0`.

## Live Result

WSTA25 confirmed live was rerun against V3389 with the explicit live gate and credentialed-Wi-Fi ack.
The pre-confirm scan guard was skipped so the request would enter native autoconnect and exercise the
new diagnostics.  Public tunnel and external ping stayed disabled.

Confirmed helper result:

- `helper_confirmed_attempted=true`
- `helper_confirmed_pass=false`
- `decision=wifi-uplink-service-autoconnect-failed`
- `autoconnect_decision=wifi-autoconnect-connect-failed`
- `connect_rc=-28`
- `dhcp_rc=0`
- `final_rc=-28`
- `carrier_up=0`
- `external_ping_execution=0`
- `public_tunnel=0`
- `secret_values_logged=0`

New connect diagnostics:

- `connect_diag_attempted=1`
- `connect_diag_decision=wifi-connect-config-prepare-failed`
- `connect_wlan0_wait_rc=0`
- `connect_link_up_rc=1`
- `connect_prepare_rc=-28`
- `connect_runtime_prepare_rc=0`
- `connect_supplicant_root_exec_rc=0`
- `connect_supplicant_process_count_before=-1`
- `connect_supplicant_start_rc=0`
- `connect_ctrl_wait_category=not-run`
- `connect_ctrl_scan_rc=0`
- `connect_ctrl_reassociate_rc=0`
- `connect_carrier_wait_rc=0`
- `connect_ctrl_status_wpa_state=-`
- `connect_ctrl_status_completed=0`
- `connect_supplicant_spawned=0`
- `connect_supplicant_left_running=0`

Interpretation: WSTA32 proved the new diagnostic path end-to-end, and it changed the active blocker.
The run did not reach association/carrier.  Native connect failed earlier while preparing the
wpa_supplicant config with `-ENOSPC`.

A metadata-only check after the run confirmed `/cache` was full (`Use%=100%`) while the existing
supplicant config file was present.  That explains `connect_prepare_rc=-28` and makes `/cache`
runtime pressure the next frontier.

## Cleanup

Post-run cleanup disabled autoconnect, ran native Wi-Fi cleanup, verified no IPv4/default route and
no supplicant process, and final `selftest fail=0`.

## Safety

No forbidden partition was touched.  The only flash was the checked-helper boot-image flash.  No
public tunnel, external ping, raw credential logging, SSID, PSK, BSSID, MAC, gateway, DNS server,
public URL, or confirm-token value is recorded in public artifacts.  No successful association, DHCP
lease, default route, or public exposure occurred.  Raw transcripts remain under `workspace/private/`.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile ...`
- `sh -n workspace/public/src/scripts/server-distro/a90_native_wifi_uplink_client.sh`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_build_native_init_boot_v3389_wifi_connect_carrier_diagnostics tests.test_native_wifi_uplink_service_source tests.test_server_distro_wsta24_native_wifi_uplink_client tests.test_server_distro_wsta25_confirmed_autoconnect_live tests.test_server_distro_wsta26_scan_failure_diagnostic`
- `aarch64-linux-gnu-gcc -fsyntax-only -Wall -Wextra -Werror ... workspace/public/src/native-init/a90_wifi.c`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v3389_wifi_connect_carrier_diagnostics.py`
- `python3 workspace/public/src/scripts/revalidation/native_init_flash.py ... --expect-sha256 e9eca0744848f51a44690768c4c6335e2867d718acb2cd1afc010c4cb1dc5b4c --expect-version 0.11.145 --verify-protocol cmdv1 --from-native`
- `python3 workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py --allow-confirmed-live --ack-credentialed-wifi --confirm-token <redacted> --skip-pre-confirm-scan-gate --service-lifetime-ms 360000 --confirmed-timeout-sec 300`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi autoconnect disable`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi cleanup`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi status`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest`

## Next

WSTA33 should fix the `/cache` ENOSPC blocker before retrying carrier diagnostics.  Preferred
direction: move bulky/native Wi-Fi runtime artifacts to SD-backed runtime storage or add a bounded
native Wi-Fi runtime cleanup that never removes credential/config sources and reports only redacted
metadata.
