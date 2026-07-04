# Server Distro Wi-Fi STA Upstream WSTA37 WPA Failure Detail V3394 Live

- Date: `2026-07-04`
- Decision: `wsta25-blocked-wpa-wrong-key-classified`
- Candidate: `A90 Linux init 0.11.150 (v3394-wifi-wpa-failure-detail)`
- Boot image:
  `workspace/private/inputs/boot_images/boot_linux_v3394_wifi_wpa_failure_detail.img`
- Boot SHA256: `471ac301103e27e02bfac7faae3fee850e759218a05ffede1b596c10e5a240a7`
- Source-build report:
  `docs/reports/NATIVE_INIT_V3394_WIFI_WPA_FAILURE_DETAIL_SOURCE_BUILD_2026-07-04.md`
- Live evidence:
  `workspace/private/runs/server-distro/wsta37-wpa-failure-detail-v3394-20260704T051251Z/wsta25_result.json`

## Scope

WSTA37 keeps the V3393 native WPA control-socket uniqueness fix and adds redacted
failure-detail classification around the true WPA 4-way-handshake stall.  The added
fields classify monitor disconnect/temp-disabled/assoc-reject reasons and expose safe
`STATUS` fields such as selected network id, key management, ciphers, station mode,
frequency, and completion state.  SSID, PSK, BSSID, raw MAC, raw IP, gateway, DNS,
confirm token, public URL, and public tunnel data remain out of public artifacts.

## Build And Flash

V3394 source build passed AArch64 helper/native-init compilation, required-string
audit, preserved-ramdisk overlay, boot-image packing, and SHA256 capture.

Rollback image checks passed before flash: v2321 and v2237 matched their expected
hashes, v48 was present, and TWRP recovery artifacts were present.
`native_init_flash.py --from-native` flashed only boot with the V3394 SHA pinned,
verified remote SHA, verified boot-prefix readback SHA, rebooted system, and verified
native V3394 over cmdv1.  Total helper time was `62.763s`.  Post-flash native health
reported V3394 and `selftest fail=0`.

## Live Result

WSTA25 confirmed live was rerun against V3394 with the explicit live gate and
credentialed-Wi-Fi ack.  The pre-confirm scan guard was skipped to exercise native
autoconnect directly.  Public tunnel and external ping stayed disabled.

The native control plane remains fixed from WSTA36:

- `connect_ctrl_driver_country_rc=0`
- `connect_ctrl_scan_rc=0`
- `connect_ctrl_enable_network_rc=0`
- `connect_ctrl_select_network_rc=0`
- `connect_ctrl_reassociate_rc=0`

The confirmed helper still blocks before a completed WPA state:

- `helper_confirmed_attempted=true`
- `helper_confirmed_pass=false`
- `decision=wifi-uplink-service-autoconnect-failed`
- `autoconnect_decision=wifi-autoconnect-connect-failed`
- `connect_diag_decision=wifi-connect-status-not-completed`
- `connect_rc=-107`
- `final_rc=-107`
- `connect_carrier_wait_rc=0`
- `connect_carrier_up_at_wait=1`
- `connect_wpa_monitor_attach_rc=0`
- `connect_wpa_monitor_event_count=53`
- `connect_wpa_monitor_scan_results_seen=1`
- `connect_wpa_monitor_disconnected_seen=1`
- `connect_wpa_monitor_temp_disabled_seen=1`
- `connect_wpa_monitor_connected_seen=0`
- `connect_wpa_monitor_assoc_reject_seen=0`
- `connect_wpa_monitor_auth_reject_seen=0`
- `connect_wpa_monitor_eap_failure_seen=0`
- `connect_wpa_complete_wait_rc=-110`
- `connect_wpa_complete_wait_elapsed_ms=25000`
- `connect_wpa_complete_samples=96`
- `connect_wpa_complete_retry_count=4`
- `connect_wpa_complete_first_state=4WAY_HANDSHAKE`
- `connect_wpa_complete_last_state=4WAY_HANDSHAKE`
- `connect_wpa_complete_completed=0`
- `connect_ctrl_status_rc=0`
- `connect_ctrl_status_wpa_state=4WAY_HANDSHAKE`
- `connect_ctrl_status_completed=0`
- `external_ping_execution=0`
- `public_tunnel=0`
- `secret_values_logged=0`

The new V3394 redacted failure-detail fields classify the blocker:

- `connect_wpa_monitor_disconnect_reason_class=15`
- `connect_wpa_monitor_temp_disabled_reason_class=WRONG_KEY`
- `connect_wpa_monitor_assoc_reject_status_class=-`
- `connect_ctrl_status_network_id=0`
- `connect_ctrl_status_network_selected=1`
- `connect_ctrl_status_key_mgmt=WPA2-PSK`
- `connect_ctrl_status_pairwise_cipher=CCMP`
- `connect_ctrl_status_group_cipher=CCMP`
- `connect_ctrl_status_mode=station`
- `connect_ctrl_status_freq_mhz=5745`

Interpretation: the prior blind spots are closed.  Native init now reaches carrier-up,
keeps WPA control commands working after monitor attach, selects the configured
network, and waits in `4WAY_HANDSHAKE`.  The WPA monitor then reports temp-disabled
with the safe reason class `WRONG_KEY` and disconnect reason class `15`.  The next
frontier is no longer native control plumbing; it is credential/AP authentication
material or AP-side compatibility for the configured WPA2-PSK profile.

## Cleanup

The runner stopped the native uplink service and cleaned the temporary Debian helper
surface.  The postcheck reported no remaining chroot mount, no loop node, and no
dropbear process.  Codex then restored `wifi autoconnect disable`, ran `wifi cleanup`,
verified no IPv4/default route and no supplicant process, and rechecked final
`selftest fail=0`.

## Safety

No forbidden partition was touched.  The only flash was the checked-helper boot-image
flash.  No public tunnel, external ping, raw credential logging, SSID, PSK, BSSID, raw
MAC, gateway, DNS server, public URL, or confirm-token value is recorded in public
artifacts.  Raw transcripts remain under `workspace/private/`.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile ...`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_native_wifi_uplink_service_source tests.test_server_distro_wsta24_native_wifi_uplink_client tests.test_server_distro_wsta26_scan_failure_diagnostic tests.test_build_native_init_boot_v3394_wifi_wpa_failure_detail`
- `aarch64-linux-gnu-gcc -fsyntax-only -Wall -Wextra -Werror ... workspace/public/src/native-init/a90_wifi.c`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v3394_wifi_wpa_failure_detail.py`
- `python3 workspace/public/src/scripts/revalidation/native_init_flash.py ... --expect-sha256 471ac301103e27e02bfac7faae3fee850e759218a05ffede1b596c10e5a240a7 --expect-version 0.11.150 --verify-protocol cmdv1 --from-native`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi autoconnect enable`
- `python3 workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py --allow-confirmed-live --ack-credentialed-wifi --confirm-token <redacted> --skip-pre-confirm-scan-gate --service-lifetime-ms 360000 --confirmed-timeout-sec 300`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi autoconnect disable`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi cleanup`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi status`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest`

## Next

WSTA38 should stop treating this as a native-init transport/control bug.  Run a
credential/AP-side reconciliation unit: compare the private credential material and AP
security mode against the earlier known-good Debian WSTA7 association path without
logging secrets, then either refresh the native profile material or prove an AP
compatibility delta.  Only after `WRONG_KEY` is cleared should DHCP/default-route and
uplink exposure be retried.
