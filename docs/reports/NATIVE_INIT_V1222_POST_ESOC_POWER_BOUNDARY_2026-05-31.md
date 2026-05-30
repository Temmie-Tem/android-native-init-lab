# V1222 Post-eSoC Power Boundary Live Gate

- date: 2026-05-31
- cycle: V1222
- objective: after V1221 proved `SDX50M` registration and `subsys_esoc0` entry, hold the observer window open and classify what happens between `subsys_esoc0` open and WLFW/BDF/`wlan0` readiness.
- safety scope: bounded PM/CNSS observer only; no Wi-Fi HAL, scan/connect/link-up, credentials, DHCP/routes, external ping, boot image write, or vendor partition write.

## Implementation

- runner: `scripts/revalidation/native_wifi_post_esoc_power_boundary_v1222.py`
- base path: V1221 private patched `cnss-daemon.sdx50m` path and helper v253
- post-hold: 45 one-second samples after helper completion, while the collector continues sampling `pm-service` threads
- added samples: `mdm3` state, `wlan0` existence, modem-down/crash dmesg counts, WLFW/BDF/`wlan0` dmesg counts, and eSoC-open dmesg counts

## Evidence

- live manifest: `tmp/wifi/v1222-post-esoc-power-boundary-live/manifest.json`
- observer: `tmp/wifi/v1222-post-esoc-power-boundary-live/host/pm-server-wchan-tracefs-observer.txt`
- child script: `tmp/wifi/v1222-post-esoc-power-boundary-live/host/pm-cnss-voter-child-script.txt`

## Result

- decision: `v1222-esoc-powerup-crash-before-wlfw`
- pass: `true`
- `subsys_esoc0` open: observed via syscall path `/dev/subsys_esoc0`
- `pm-service` wchan: `mdm_subsys_powerup` observed and remained late
- post-hold samples: `46`
- `mdm3` states: `['OFFLINING']`
- modem-down/crash marker count: max `4`
- WLFW/BDF/`wlan0` marker count: max `0`
- `wlan0`: not present

## Interpretation

V1222 confirms the V1221 path reaches the eSoC power-up boundary, but the SDX50M side fails before WLFW service 69, BDF transfer, FW-ready, or `wlan0`. The blocker is no longer CNSS peripheral selection or `pm-service` eSoC routing. The blocker is now below `subsys_esoc0` open: SDX50M power-up, MHI/firmware handoff, or lifetime/order around the Android-equivalent `mdm_helper`/`ks`/PM stack.

The post-hold data stayed in `OFFLINING`, while dmesg crash/down markers rose from `2` to `4`. This is stronger than a mere timeout: the eSoC path is being entered and then fails before WLFW publication.

## Safety Audit

- `cnss_daemon_start_executed=true` as intended for this gate.
- `wifi_hal_start_executed=false`.
- `scan_connect_executed=false`.
- `external_ping_executed=false`.
- `wifi_bringup_executed=false`.
- postflight native health: `selftest fail=0`.

## Next

V1223 should classify the crash source at the Android/native boundary after `subsys_esoc0` open. Focus on the difference between Android's successful path and native's failing path:

- Android: `pm-service` opens `subsys_esoc0`, `mdm_helper` owns `/dev/esoc-0`, `ks` reaches `/dev/mhi_0305_01.01.00_pipe_10`, then WLFW/BDF/`wlan0` appear.
- Native V1222: `pm-service` opens `subsys_esoc0`, but `mdm3` stays `OFFLINING`, modem-down/crash markers increase, and WLFW/BDF/`wlan0` never appear.

Do not move to Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping until the lower SDX50M/WLFW readiness gate is proven.
