# Server Distro Wi-Fi STA Upstream WSTA36 Ctrl Socket Unique V3393 Live

- Date: `2026-07-04`
- Decision: `wsta25-blocked-helper-confirmed-autoconnect`
- Candidate: `A90 Linux init 0.11.149 (v3393-wifi-ctrl-socket-unique)`
- Boot image:
  `workspace/private/inputs/boot_images/boot_linux_v3393_wifi_ctrl_socket_unique.img`
- Boot SHA256: `ee9d185e831265c47b11939a929ce361d70efc770e746f65d7b2c65884162f79`
- Source-build report:
  `docs/reports/NATIVE_INIT_V3393_WIFI_CTRL_SOCKET_UNIQUE_SOURCE_BUILD_2026-07-04.md`
- Live evidence:
  `workspace/private/runs/server-distro/wsta36-ctrl-socket-unique-v3393-20260704T045702Z/wsta25_result.json`

## Scope

WSTA36 fixes the V3392 diagnostic artifact where ordinary WPA control commands immediately after
monitor attach returned `-98`.  Source inspection showed the likely cause: native control client
sockets used a local abstract name derived only from `pid + monotonic_millis`, so a persistent
monitor socket and a one-shot command socket could bind the same name in the same millisecond.

V3393 keeps V3392's tmp-backed control socket directory and V3391's redacted WPA monitor/status
diagnostics, then adds a process-local monotonic sequence to the local abstract socket name.

## Build And Flash

V3393 source build passed AArch64 helper/native-init compilation, required-string audit,
preserved-ramdisk overlay, boot-image packing, and SHA256 capture.

Rollback image checks passed before flash: v2321 and v2237 matched their expected hashes, v48 was
present, and TWRP recovery artifacts were present.  `native_init_flash.py --from-native` flashed
only boot with the V3393 SHA pinned, verified remote SHA, verified boot-prefix readback SHA,
rebooted system, and verified native V3393 over cmdv1.  Total helper time was `63.135s`.
Post-flash native health reported V3393 and `selftest fail=0`.

## Live Result

WSTA25 confirmed live was rerun against V3393 with the explicit live gate and credentialed-Wi-Fi
ack.  The pre-confirm scan guard was skipped to exercise native autoconnect directly.  Public
tunnel and external ping stayed disabled.

The V3392 `-98` artifact is fixed:

- `connect_ctrl_wait_rc=0`
- `connect_ctrl_wait_category=pong`
- `connect_ctrl_driver_country_rc=0`
- `connect_ctrl_scan_rc=0`
- `connect_ctrl_enable_network_rc=0`
- `connect_ctrl_select_network_rc=0`
- `connect_ctrl_reassociate_rc=0`

The confirmed helper still blocks at WPA completion:

- `helper_confirmed_attempted=true`
- `helper_confirmed_pass=false`
- `decision=wifi-uplink-service-autoconnect-failed`
- `autoconnect_decision=wifi-autoconnect-connect-failed`
- `connect_diag_decision=wifi-connect-status-not-completed`
- `connect_rc=-107`
- `final_rc=-107`
- `connect_wlan0_wait_rc=0`
- `connect_link_up_rc=1`
- `connect_prepare_rc=0`
- `connect_runtime_prepare_rc=0`
- `connect_supplicant_start_rc=0`
- `connect_carrier_wait_rc=0`
- `connect_carrier_up_at_wait=1`
- `connect_wpa_monitor_attach_rc=0`
- `connect_wpa_monitor_event_count=55`
- `connect_wpa_monitor_scan_results_seen=1`
- `connect_wpa_monitor_disconnected_seen=1`
- `connect_wpa_monitor_temp_disabled_seen=1`
- `connect_wpa_monitor_connected_seen=0`
- `connect_wpa_monitor_assoc_reject_seen=0`
- `connect_wpa_monitor_auth_reject_seen=0`
- `connect_wpa_monitor_eap_failure_seen=0`
- `connect_wpa_complete_wait_rc=-110`
- `connect_wpa_complete_wait_elapsed_ms=25000`
- `connect_wpa_complete_samples=97`
- `connect_wpa_complete_retry_count=4`
- `connect_wpa_complete_first_state=4WAY_HANDSHAKE`
- `connect_wpa_complete_last_state=4WAY_HANDSHAKE`
- `connect_wpa_complete_completed=0`
- `connect_ctrl_status_rc=0`
- `connect_ctrl_status_wpa_state=4WAY_HANDSHAKE`
- `connect_ctrl_status_completed=0`
- `connect_ctrl_signal_rc=0`
- `connect_supplicant_spawned=1`
- `connect_supplicant_left_running=0`
- `connect_cleanup_status=0`
- `external_ping_execution=0`
- `public_tunnel=0`
- `secret_values_logged=0`

Interpretation: V3393 removes the diagnostic blind spot.  The remaining blocker is now a real
WPA completion failure after successful supplicant control, scan, network enable/select,
reassociate, carrier-up, and monitor attach.  The native path stays in `4WAY_HANDSHAKE` for the
bounded 25s window and sees temp-disabled/disconnect categories without connected, assoc-reject,
auth-reject, or EAP-failure categories.

## Cleanup

The runner stopped the native uplink service and cleaned the temporary Debian helper surface.  The
postcheck reported no remaining chroot mount, no loop node, and no dropbear process.  Codex then
restored `wifi autoconnect disable`, ran `wifi cleanup`, verified no IPv4/default route and no
supplicant process, and rechecked final `selftest fail=0`.

## Safety

No forbidden partition was touched.  The only flash was the checked-helper boot-image flash.  No
public tunnel, external ping, raw credential logging, SSID, PSK, BSSID, raw MAC, gateway, DNS
server, public URL, or confirm-token value is recorded in public artifacts.  Raw transcripts remain
under `workspace/private/`.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile ...`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_native_wifi_uplink_service_source tests.test_server_distro_wsta24_native_wifi_uplink_client tests.test_server_distro_wsta26_scan_failure_diagnostic tests.test_build_native_init_boot_v3393_wifi_ctrl_socket_unique`
- `aarch64-linux-gnu-gcc -fsyntax-only -Wall -Wextra -Werror ... workspace/public/src/native-init/a90_wifi.c`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v3393_wifi_ctrl_socket_unique.py`
- `python3 workspace/public/src/scripts/revalidation/native_init_flash.py ... --expect-sha256 ee9d185e831265c47b11939a929ce361d70efc770e746f65d7b2c65884162f79 --expect-version 0.11.149 --verify-protocol cmdv1 --from-native`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi autoconnect enable`
- `python3 workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py --allow-confirmed-live --ack-credentialed-wifi --confirm-token <redacted> --skip-pre-confirm-scan-gate --service-lifetime-ms 360000 --confirmed-timeout-sec 300`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi autoconnect disable`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi cleanup`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi status`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest`

## Next

WSTA37 should keep the V3393 socket fix and add redacted WPA failure-detail classification for
the true 4-way-handshake stall: temp-disabled reason class, disconnect reason class, selected
network state, key-management/pairwise/group/country summary without SSID/PSK/BSSID, and a
same-run comparison against the known-good Debian WSTA7 association shape where possible.
