# Server Distro Wi-Fi STA Upstream WSTA35 Tmp Ctrl Dir V3392 Live

- Date: `2026-07-04`
- Decision: `wsta25-blocked-helper-confirmed-autoconnect`
- Candidate: `A90 Linux init 0.11.148 (v3392-wifi-tmp-ctrl-dir)`
- Boot image:
  `workspace/private/inputs/boot_images/boot_linux_v3392_wifi_tmp_ctrl_dir.img`
- Boot SHA256: `da2f39b60300497d8957abff77a97764864fd8a6d3de3018bb8e837837c9861c`
- Source-build report:
  `docs/reports/NATIVE_INIT_V3392_WIFI_TMP_CTRL_DIR_SOURCE_BUILD_2026-07-04.md`
- Live evidence:
  `workspace/private/runs/server-distro/wsta35-tmp-ctrl-dir-v3392-20260704T043745Z/wsta25_result.json`

## Scope

WSTA35 removes the WSTA34 control-socket ENOSPC blocker by moving the supplicant control directory
from `/cache/a90-wifi/sockets` to volatile `/tmp/a90-wifi/sockets`.  The generated supplicant config
stays under `/cache/a90-wifi/wpa_supplicant.conf`, and all V3391 redacted WPA diagnostics remain
enabled.

## Build And Flash

V3392 source build passed AArch64 helper/native-init compilation, required-string audit, preserved
ramdisk overlay, boot-image packing, and SHA256 capture.  Required strings confirmed the new
`/tmp/a90-wifi/sockets` path plus V3391 WPA diagnostic fields.

Rollback image checks passed before flash: v2321 and v2237 matched their expected hashes, and v48
was present.  `native_init_flash.py --from-native` flashed only boot with the V3392 SHA pinned,
verified remote SHA, verified boot-prefix readback SHA, rebooted system, and verified native V3392
over cmdv1.  Total helper time was `61.517s`.  Post-flash native health reported V3392 and
`selftest fail=0`.

After boot, direct `wifi config prepare` succeeded with `prepare_rc=0` and
`ctrl_interface.dir=/tmp/a90-wifi/sockets`, confirming that the `/cache` ENOSPC control-directory
blocker was removed.

## Live Result

WSTA25 confirmed live was rerun against V3392 with the explicit live gate and credentialed-Wi-Fi
ack.  The native path reached supplicant startup, control PING, carrier, WPA monitor attach, and the
bounded WPA completion wait.

Confirmed helper result:

- `helper_confirmed_attempted=true`
- `helper_confirmed_pass=false`
- `decision=wifi-uplink-service-autoconnect-failed`
- `autoconnect_decision=wifi-autoconnect-connect-failed`
- `connect_diag_attempted=1`
- `connect_diag_decision=wifi-connect-status-not-completed`
- `connect_wlan0_wait_rc=0`
- `connect_link_up_rc=1`
- `connect_prepare_rc=0`
- `connect_runtime_prepare_rc=0`
- `connect_supplicant_process_count_before=0`
- `connect_supplicant_start_rc=0`
- `connect_ctrl_wait_rc=0`
- `connect_ctrl_wait_category=pong`
- `connect_ctrl_driver_country_rc=-98`
- `connect_ctrl_scan_rc=-98`
- `connect_ctrl_enable_network_rc=-98`
- `connect_ctrl_select_network_rc=-98`
- `connect_ctrl_reassociate_rc=-98`
- `connect_carrier_wait_rc=0`
- `connect_carrier_up_at_wait=1`
- `connect_wpa_monitor_attach_rc=0`
- `connect_wpa_monitor_event_count=56`
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
- `connect_rc=-107`
- `final_rc=-107`
- `external_ping_execution=0`
- `public_tunnel=0`
- `secret_values_logged=0`

Interpretation: V3392 proves the `/tmp` control-dir fix and reaches the intended WPA diagnostic
frontier.  The new evidence shows a bounded 25s WPA completion timeout in `4WAY_HANDSHAKE`, with
monitor categories showing scan-results, disconnect, and temp-disabled events but no connected,
association-reject, authentication-reject, or EAP-failure category.

There is also a native diagnostic artifact to fix before treating those command results as final:
the ordinary ctrl commands immediately after monitor attach all returned `-98`.  Source inspection
shows a likely root cause: local abstract ctrl socket names use only `pid + monotonic_millis`, so
the persistent monitor socket can collide with request sockets created in the same millisecond and
produce `EADDRINUSE(-98)`.  Later status requests succeeded, so WSTA36 should make ctrl local
socket names monotonic-unique and rerun this same gate.

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

- `sh -n workspace/public/src/scripts/server-distro/a90_native_wifi_uplink_client.sh`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile ...`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_native_wifi_cache_enospc_fallback_source tests.test_native_wifi_uplink_service_source tests.test_server_distro_wsta24_native_wifi_uplink_client tests.test_server_distro_wsta26_scan_failure_diagnostic tests.test_build_native_init_boot_v3391_wifi_wpa_handshake_diagnostics tests.test_build_native_init_boot_v3392_wifi_tmp_ctrl_dir`
- `aarch64-linux-gnu-gcc -fsyntax-only -Wall -Wextra -Werror ... workspace/public/src/native-init/a90_wifi.c`
- `aarch64-linux-gnu-gcc -fsyntax-only -Wall -Wextra -Werror ... workspace/public/src/native-init/a90_wificfg.c`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v3392_wifi_tmp_ctrl_dir.py`
- `python3 workspace/public/src/scripts/revalidation/native_init_flash.py ... --expect-sha256 da2f39b60300497d8957abff77a97764864fd8a6d3de3018bb8e837837c9861c --expect-version 0.11.148 --verify-protocol cmdv1 --from-native`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi config prepare`
- `python3 workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py --allow-confirmed-live --ack-credentialed-wifi --confirm-token <redacted> --skip-pre-confirm-scan-gate --service-lifetime-ms 360000 --confirmed-timeout-sec 300`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi autoconnect disable`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi cleanup`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi status`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest`

## Next

WSTA36 should fix native WPA ctrl local abstract socket uniqueness so monitor and one-shot request
sockets cannot collide.  Then rerun the same confirmed-autoconnect gate and compare whether
`ctrl.driver_country`, `ctrl.scan`, `ENABLE_NETWORK`, `SELECT_NETWORK`, and `REASSOCIATE` return
cleanly before interpreting the remaining 4-way-handshake stall.
