# Server Distro Wi-Fi STA Upstream WSTA34 WPA Handshake Diagnostics V3391 Live

- Date: `2026-07-04`
- Decision: `wsta25-blocked-helper-confirmed-autoconnect`
- Candidate: `A90 Linux init 0.11.147 (v3391-wifi-wpa-handshake-diagnostics)`
- Boot image:
  `workspace/private/inputs/boot_images/boot_linux_v3391_wifi_wpa_handshake_diagnostics.img`
- Boot SHA256: `11a2685964a93271bac9d2ef34348f2a74a2aa079a3ca46941b731d5f4ed76b3`
- Source-build report:
  `docs/reports/NATIVE_INIT_V3391_WIFI_WPA_HANDSHAKE_DIAGNOSTICS_SOURCE_BUILD_2026-07-04.md`
- Live evidence:
  `workspace/private/runs/server-distro/wsta34-wpa-handshake-diagnostics-v3391-20260704T042353Z/wsta25_result.json`

## Scope

WSTA34 adds redacted WPA completion diagnostics to the native-owned confirmed STA path.  V3391
keeps the V3390 cache ENOSPC config fallback, then adds a bounded WPA completion wait after
carrier-up plus a WPA control monitor that records only categories and counters.  The unit keeps
confirmed-autoconnect explicit-gated, public tunnel disabled, external ping disabled, and
secret-value logging disabled.

## Build And Flash

V3391 source build passed AArch64 helper/native-init compilation, required-string audit,
preserved-ramdisk overlay, boot-image packing, and SHA256 capture.

Rollback image checks passed before flash: v2321 and v2237 matched their expected hashes, and v48
was present.  `native_init_flash.py --from-native` flashed only boot with the V3391 SHA pinned,
verified remote SHA, verified boot-prefix readback SHA, rebooted system, and verified native V3391
over cmdv1.  Total helper time was `61.686s`.  Post-flash native health reported V3391 and
`selftest fail=0`.

## Live Result

WSTA25 confirmed live was rerun against V3391 with the explicit live gate and credentialed-Wi-Fi
ack.  The request reached the native uplink-service confirmed autoconnect path, but it did not
reach the new WPA diagnostics because the control socket directory was still under the full
`/cache` filesystem.

Confirmed helper result:

- `helper_confirmed_attempted=true`
- `helper_confirmed_pass=false`
- `decision=wifi-uplink-service-autoconnect-failed`
- `autoconnect_decision=wifi-autoconnect-connect-failed`
- `connect_diag_attempted=1`
- `connect_diag_decision=wifi-connect-config-prepare-failed`
- `connect_wlan0_wait_rc=0`
- `connect_link_up_rc=1`
- `connect_prepare_rc=-28`
- `connect_rc=-28`
- `final_rc=-28`
- `connect_supplicant_spawned=0`
- `connect_wpa_monitor_attach_rc=-2`
- `connect_wpa_complete_wait_rc=0`
- `external_ping_execution=0`
- `public_tunnel=0`
- `secret_values_logged=0`

Interpretation: V3391's diagnostic surface is source-valid, but the live unit was blocked before
supplicant startup by `/cache` storage pressure.  Direct native `wifi config prepare` then confirmed
the issue: the generated supplicant config existed, while the `/cache` control socket directory
could not be created.  That made the next bounded rung a runtime placement fix, not a WPA
handshake interpretation.

## Cleanup

Codex restored `wifi autoconnect disable`, ran `wifi cleanup`, verified no IPv4/default route and no
supplicant process, and rechecked final `selftest fail=0`.

## Safety

No forbidden partition was touched.  The only flash was the checked-helper boot-image flash.  No
public tunnel, external ping, raw credential logging, SSID, PSK, BSSID, raw MAC, gateway, DNS
server, public URL, or confirm-token value is recorded in public artifacts.  Raw transcripts remain
under `workspace/private/`.

## Validation

- `sh -n workspace/public/src/scripts/server-distro/a90_native_wifi_uplink_client.sh`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m py_compile ...`
- `PYTHONPATH=tests PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 -m unittest tests.test_native_wifi_uplink_service_source tests.test_server_distro_wsta24_native_wifi_uplink_client tests.test_server_distro_wsta26_scan_failure_diagnostic tests.test_build_native_init_boot_v3391_wifi_wpa_handshake_diagnostics`
- `aarch64-linux-gnu-gcc -fsyntax-only -Wall -Wextra -Werror ... workspace/public/src/native-init/a90_wifi.c`
- `PYTHONPYCACHEPREFIX=/tmp/a90_pycache python3 workspace/public/src/scripts/revalidation/build_native_init_boot_v3391_wifi_wpa_handshake_diagnostics.py`
- `python3 workspace/public/src/scripts/revalidation/native_init_flash.py ... --expect-sha256 11a2685964a93271bac9d2ef34348f2a74a2aa079a3ca46941b731d5f4ed76b3 --expect-version 0.11.147 --verify-protocol cmdv1 --from-native`
- `python3 workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py --allow-confirmed-live --ack-credentialed-wifi --confirm-token <redacted> --skip-pre-confirm-scan-gate --service-lifetime-ms 360000 --confirmed-timeout-sec 300`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi autoconnect disable`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi cleanup`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py wifi status`
- `python3 workspace/public/src/scripts/revalidation/a90ctl.py selftest`

## Next

WSTA35 should move the supplicant control socket directory off full `/cache` while keeping the
generated credential config under `/cache/a90-wifi/wpa_supplicant.conf`.  Then rerun the same
confirmed-autoconnect gate to reach the WPA diagnostics added by V3391.
