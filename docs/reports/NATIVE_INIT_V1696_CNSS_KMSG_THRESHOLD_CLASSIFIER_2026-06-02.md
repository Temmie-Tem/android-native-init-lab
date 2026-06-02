# Native Init V1696 CNSS kmsg Threshold Classifier

## Summary

- Cycle: `V1696`
- Type: host-only stock `cnss-daemon` kmsg/logging threshold classifier
- Decision: `v1696-cnss-kmsg-threshold-gap-classified`
- Result: `PASS`
- Reason: wlfw_start logs at severity 2, but V1695 used kmsg_logging=1; therefore V1695 could not expose wlfw_start through /dev/kmsg
- Evidence: `tmp/wifi/v1696-cnss-kmsg-threshold-classifier`
- Binary: `tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon`
- Binary SHA256: `bced9853a77cfb02252571196584efa535be14f8f3fd9ce32712ddee224ba4bc`

## V1695 Basis

- decision/pass: `v1695-cnss-output-still-invisible-rollback-pass` / `True`
- output label: `cnss-output-still-invisible`
- property lookup all_match: `1`
- `kmsg_logging` / `debug_level`: `1` / `4`
- `wlfw_start_seen`: `0`
- first failure slug: `none`
- cnss-daemon running: `1`
- syslog available/filtered: `1` / `0`
- non-log label / kmsg fd count: `cnss-uprobe-unavailable-fallback-needed` / `0`

## Static Logging Model

- logging helper: `cnss-daemon+0xa21c`
- debug threshold: message emitted only when debug_level >= message_severity
- kmsg threshold: system('echo ... > /dev/kmsg') only when kmsg_logging >= message_severity
- Android log path: __android_log_print still runs when debug_level threshold passes
- `wlfw_start` entry/log call: `cnss-daemon+0xec00` / `cnss-daemon+0xec24`
- `wlfw_start` severity: `2`
- `wlfw_start` kmsg-visible under V1695 thresholds: `False`
- pre-`wlfw_start` failure severity: `1`
- pre-`wlfw_start` failures kmsg-visible under V1695 thresholds: `True`

## Interpretation

- V1695 `cnss-output-still-invisible` does not prove that stock `cnss-daemon` skipped `wlfw_start`.
- `wlfw_start: Starting` is a severity-2 log, while V1695 used `persist.vendor.cnss-daemon.kmsg_logging=1`; the `/dev/kmsg` `system('echo ...')` path is therefore statically gated off for that entry log.
- The eight pre-`wlfw_start` failure logs are severity 1, so V1695 thresholds were sufficient for those specific failure strings. Their absence remains useful evidence that no named pre-wlfw init failure was observed.
- `/dev/kmsg` fd count `0` is not decisive because the kmsg path is a transient `system('echo ... > /dev/kmsg')` path, not a persistent daemon fd.

## Next Gate

- Cycle: `V1697`
- Action: source/build-only private property runtime with persist.vendor.cnss-daemon.kmsg_logging >= 2, preferably 4
- Then: one rollbackable V1698 output-visibility live handoff on the same internal-modem route
- Keep forbidden: `PM/service-window actors`, `boot_wlan`, `/dev/subsys_esoc0`, `forced RC1`, `fake-ONLINE`, `Wi-Fi HAL`, `scan/connect`, `credentials`, `DHCP/routes`, `external ping`
