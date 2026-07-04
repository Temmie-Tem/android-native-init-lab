# Server Distro Wi-Fi STA Upstream WSTA33 Cache ENOSPC Fallback V3390 Live

- Date: `2026-07-04`
- Decision: `wsta25-blocked-helper-confirmed-autoconnect`
- Candidate: `A90 Linux init 0.11.146 (v3390-wifi-cache-enospc-fallback)`
- Boot image:
  `workspace/private/inputs/boot_images/boot_linux_v3390_wifi_cache_enospc_fallback.img`
- Boot SHA256: `6c9101fa1e5c835e9d3ec0f828bf924089589fc7d56eff9398257f4f29ee2dbf`
- Source-build report:
  `docs/reports/NATIVE_INIT_V3390_WIFI_CACHE_ENOSPC_FALLBACK_SOURCE_BUILD_2026-07-04.md`
- Live evidence:
  `workspace/private/runs/server-distro/wsta25-confirmed-autoconnect-live-20260704T035853Z/wsta25_result.json`

## Scope

WSTA33 removes the WSTA32 `/cache` ENOSPC blocker without broad cache deletion.  V3390 keeps the
V3389 redacted connect diagnostics and adds a bounded fallback in the supplicant config writer:
when the atomic temp-file rewrite fails with storage pressure, native init rewrites only the
existing generated supplicant config in place through `O_NOFOLLOW`.

The unit intentionally does not delete `/cache` boot images, runtime logs, credential sources, or
unrelated cache directories.  It also keeps confirmed-autoconnect explicit-gated, public tunnel
disabled, external ping disabled, and secret-value logging disabled.

## Build And Flash

V3390 source build passed AArch64 helper/native-init compilation, required-string audit with the
new `wifi-config-enospc-inplace-fallback` marker, preserved ramdisk overlay, boot-image packing, and
SHA256 capture.

Rollback image checks passed before flash: v2321 and v2237 matched their expected hashes, and v48
was present.  `native_init_flash.py --from-native` flashed only boot with the V3390 SHA pinned,
verified remote SHA, verified boot-prefix readback SHA, rebooted system, and verified native V3390
over cmdv1.  Total helper time was `61.807s`.  Post-flash native health reported V3390 and
`selftest fail=0`.

## Live Result

WSTA25 confirmed live was rerun against V3390 with the explicit live gate and credentialed-Wi-Fi
ack.  The pre-confirm scan guard was skipped so the request would enter native autoconnect and
exercise the native fallback and downstream diagnostics.  Public tunnel and external ping stayed
disabled.

Confirmed helper result:

- `helper_confirmed_attempted=true`
- `helper_confirmed_pass=false`
- `decision=wifi-uplink-service-autoconnect-failed`
- `autoconnect_decision=wifi-autoconnect-connect-failed`
- `connect_rc=-107`
- `dhcp_rc=0`
- `final_rc=-107`
- `carrier_up=0`
- `external_ping_execution=0`
- `public_tunnel=0`
- `secret_values_logged=0`

New WSTA33 result: the `/cache` storage-pressure blocker is gone.  Native reached and controlled
`wpa_supplicant`:

- `connect_diag_attempted=1`
- `connect_diag_decision=wifi-connect-status-not-completed`
- `connect_wlan0_wait_rc=0`
- `connect_link_up_rc=1`
- `connect_prepare_rc=0`
- `connect_runtime_prepare_rc=0`
- `connect_supplicant_root_exec_rc=0`
- `connect_supplicant_process_count_before=0`
- `connect_supplicant_start_rc=0`
- `connect_ctrl_wait_rc=0`
- `connect_ctrl_wait_category=pong`
- `connect_ctrl_scan_rc=0`
- `connect_ctrl_enable_network_rc=0`
- `connect_ctrl_select_network_rc=0`
- `connect_ctrl_reassociate_rc=0`
- `connect_carrier_wait_rc=0`
- `connect_carrier_up_at_wait=1`
- `connect_ctrl_status_wpa_state=4WAY_HANDSHAKE`
- `connect_ctrl_status_completed=0`
- `connect_supplicant_spawned=1`
- `connect_supplicant_left_running=0`
- `connect_cleanup_status=0`

Interpretation: WSTA33 fixed the earlier config-prepare `-ENOSPC` failure and moved the active
frontier downstream.  Association/control reached the WPA handshake, but it did not complete within
the bounded native wait, so the confirmed autoconnect still fails with `-107`.

## Cleanup

The runner stopped the native uplink service and cleaned the temporary Debian helper surface.  The
postcheck reported no remaining chroot mount, no loop node, and no dropbear process.  Codex then
restored `wifi autoconnect disable`, ran `wifi cleanup`, verified no IPv4/default route and no
supplicant process, and rechecked final `selftest fail=0`.

## Safety

No forbidden partition was touched.  The only flash was the checked-helper boot-image flash.  No
public tunnel, external ping, raw credential logging, SSID, PSK, BSSID, raw MAC, gateway, DNS
server, public URL, or confirm-token value is recorded in public artifacts.  No successful DHCP
lease, default route, or public exposure occurred.  Raw transcripts remain under `workspace/private/`.

## Validation

- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile ...`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_build_native_init_boot_v3390_wifi_cache_enospc_fallback tests.test_native_wifi_cache_enospc_fallback_source tests.test_native_wifi_uplink_service_source tests.test_server_distro_wsta24_native_wifi_uplink_client tests.test_server_distro_wsta25_confirmed_autoconnect_live tests.test_server_distro_wsta26_scan_failure_diagnostic`
- `aarch64-linux-gnu-gcc -fsyntax-only -Wall -Wextra -Werror ... workspace/public/src/native-init/a90_wificfg.c`
- `aarch64-linux-gnu-gcc -fsyntax-only -Wall -Wextra -Werror ... workspace/public/src/native-init/a90_wifi.c`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v3390_wifi_cache_enospc_fallback.py`
- `python3 workspace/public/src/scripts/revalidation/native_init_flash.py ... --expect-sha256 6c9101fa1e5c835e9d3ec0f828bf924089589fc7d56eff9398257f4f29ee2dbf --expect-version 0.11.146 --verify-protocol cmdv1 --from-native`
- `python3 workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py --allow-confirmed-live --ack-credentialed-wifi --confirm-token <redacted> --skip-pre-confirm-scan-gate --service-lifetime-ms 360000 --confirmed-timeout-sec 300`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi autoconnect disable`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi cleanup`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi status`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest`

## Next

WSTA34 should diagnose why the native-owned confirmed STA path stalls in `4WAY_HANDSHAKE` even
though control commands and carrier wait now pass.  The next bounded unit should add redacted
wpa-control event/status capture around scan/auth/assoc/handshake and compare it against the earlier
known-good Debian WSTA7 association flow, without logging credentials or enabling public exposure.
