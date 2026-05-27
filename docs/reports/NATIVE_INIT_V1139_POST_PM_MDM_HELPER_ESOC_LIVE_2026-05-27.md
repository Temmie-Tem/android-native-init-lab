# Native Init V1139 Post-PM mdm_helper eSoC Live Report

Date: `2026-05-27`

## Result

- Decision: `v1139-post-pm-mdm-helper-lower-artifact-observed`
- Pass: `true`
- Runner: `scripts/revalidation/native_wifi_post_pm_mdm_helper_esoc_live_v1139.py`
- Manifest: `tmp/wifi/v1139-post-pm-mdm-helper-esoc-live-r2/manifest.json`
- Summary: `tmp/wifi/v1139-post-pm-mdm-helper-esoc-live-r2/summary.md`
- Raw pre-classifier-fix manifest: `tmp/wifi/v1139-post-pm-mdm-helper-esoc-live-r2/manifest.pre-classifier-fix.json`

## Summary

V1139 combined the previously proven V1134 upper path with helper `v214`'s new
post-PM `mdm_helper`/eSoC observer mode:

```text
global firmware mounts + outer /dev/subsys_modem holder
  -> V490 Android SELinux policy load
  -> service-manager trio + PM service/provider path
  -> cnss-daemon PM register/connect
  -> mdm_helper after cnss-daemon
  -> post-PM eSoC/MHI/WLFW lower-surface snapshot
```

The bounded live run observed the first lower artifact after the successful
PM/CNSS path: `mdm_helper` was alive in the post-PM window and held
`/dev/esoc-0` through the private namespace path.

## Evidence

| item | value |
| --- | --- |
| helper | `a90_android_execns_probe v214` |
| helper mode | `wifi-companion-post-pm-mdm-helper-esoc-observer` |
| helper SHA256 | `4dd6dea42fddfc1b70732e5695323421a0abf505530ab2d437c6e5418a75638f` |
| V401 evidence | `tmp/wifi/v1139-r2-v401-selinuxfs-mount` |
| V490 evidence | `tmp/wifi/v1139-r2b-v490-policy-load-run` |
| V1139 evidence | `tmp/wifi/v1139-post-pm-mdm-helper-esoc-live-r2` |

## Observed State

| key | value |
| --- | --- |
| `mss` | `OFFLINING -> ONLINE -> ONLINE` |
| `mdm3` | `OFFLINING -> OFFLINING -> OFFLINING` |
| QRTR services `69/74/180` | all `0` after observer |
| `pm_client_register_ret` | `0x0` |
| `pm_client_connect_ret` | `0x0` |
| `post_pm_mdm_helper_esoc_observer.result` | `lower-artifact-observed` |
| `post_pm_mdm_helper_esoc_observer.mdm_helper_observable` | `1` |
| `post_pm_mdm_helper_esoc_observer.fd_esoc0_count.window` | `1` |
| `post_pm_mdm_helper_esoc_observer.fd_subsys_esoc0_count.window` | `0` |
| `post_pm_mdm_helper_esoc_observer.fd_mhi_pipe_count.window` | `0` |
| `post_pm_mdm_helper_esoc_observer.ks_count.window` | `0` |
| `post_pm_mdm_helper_esoc_observer.lower_artifact_observed` | `1` |

## Interpretation

This is a forward step from V1134/V1135. The upper PM/CNSS path is still clean,
and `mdm_helper` now reaches `/dev/esoc-0` when started after `cnss-daemon`.
The remaining gap is lower than the previous PM provider/CNSS layer:

```text
PM/CNSS register+connect OK
  -> mdm_helper /dev/esoc-0 fd OK
  -> mdm3 still OFFLINING
  -> no MHI pipe, ks, WLFW service 69, BDF, or wlan0 yet
```

The next cycle should classify why this `/dev/esoc-0` hold does not progress to
`/dev/subsys_esoc0`, MHI pipe, `ks`, or WLFW publication.

## Safety

- Wi-Fi HAL start: `false`
- Scan/connect/link-up: `false`
- Credential use: `false`
- DHCP/route: `false`
- External ping: `false`
- Boot image/partition write/flash: not executed
- Cleanup reboot completed; post-reboot version/selftest were healthy.

## Notes

The first V1139 run failed before actor execution because the inherited V1095
command carried `--allow-qrtr-ns-readback`, which helper `v214` correctly rejects
for the new post-PM mode. The runner now removes that inherited flag.

The r2 live run originally produced a false negative because the command-output
budget preserved the post-PM tail markers but not the initial
`begin/allowed/start_after_cnss` markers. The raw evidence already contained
`exec_attempted=1`, `end=1`, and `result=lower-artifact-observed`; the runner's
classifier now accepts that tail-complete shape and keeps the original manifest
as `manifest.pre-classifier-fix.json`.
