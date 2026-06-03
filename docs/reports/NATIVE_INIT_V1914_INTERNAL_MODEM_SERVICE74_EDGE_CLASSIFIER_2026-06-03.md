# Native Init V1914 Internal Modem Service74 Edge Classifier

## Summary

- Cycle: `V1914`
- Type: host-only retained-evidence classifier for the internal-modem guest-PD-load trigger boundary
- Decision: `v1914-internal-service74-built-in-publication-edge-host-pass`
- Label: `internal-modem-service74-built-in-publication-edge`
- Result: `PASS`
- Reason: normal Android reaches internal-modem service74/wlan_pd/wlanmdsp/wlan0 without PCIe/MHI, while native post-/dev/subsys_modem open remains service74 absent; the wlan/fw locator is 180-only and pm-service msg20/21/22 dispatch is not the observed trigger
- Evidence: `tmp/wifi/v1914-internal-modem-service74-edge-classifier`

## Gate Results

| gate | pass | meaning |
| --- | --- | --- |
| native servloc 180-only gap | True | native sees `msm/modem/wlan_pd` instance 180 but no service74/wlan_pd/WLFW69/wlan0 |
| native post-open gap | True | `/dev/subsys_modem` open and PM-client success do not start wlan_pd |
| Android normal state-up | True | normal Android reaches service74, wlan_pd, wlanmdsp, and wlan0 with no PCIe/MHI contamination |
| locator excludes service74 | True | early Android `wlan/fw` service-locator response is instance 180 only after service74 and before wlan_pd |
| pm-service excluded | True | pm-service msg20/21/22 and pending-client/msg22 observability are zero through normal state-up |
| built-in edge | True | `service_notif_register_notifier` is built into the kernel with ICNSS/service_locator/wlan present |

## Native Evidence

| field | value |
| --- | --- |
| V1908 manifest | tmp/wifi/v1908-servloc-domain-list-live-handoff/manifest.json |
| decision/pass/label | v1908-servloc-domain-list-180-only-service74-missing-rollback-pass/True/servloc-domain-list-180-only-service74-missing |
| servloc result/name/instance | domain-list-response-success/msm/modem/wlan_pd/180 |
| service180/service74/wlan_pd counts | 1,1,1/0,0,0/0,0,0 |
| servnotif states | uninit->uninit |
| WLFW69/wlanmdsp/wlan0 | 0/0/0 |
| V1888 native open path/fd | /dev/subsys_modem/0x7 |
| PM register/connect/open hits/msg22 hits | 0/0/1/0 |

## Android Evidence

| field | value |
| --- | --- |
| V1910 locator decision | v1910-android-early-servloc-180-only-after-service74-before-wlanpd-pass/True/android-early-servloc-180-only-after-service74-before-wlanpd |
| V1910 query instances/domain74/domain180 | [180]/False/True |
| V1910 time service74/query/wlan_pd/wlan0 | 7.211039/7.213/9.567936/15.02341 |
| V1912 owner decision | v1912-android-service-notifier-register-builtin-normal-stateup-pass/True/android-service-notifier-register-builtin-normal-stateup |
| V1912 owners/modules | ["builtin"]/["icnss", "qmi_rmnet", "service_locator", "subsystem_restart", "vservices", "vservices_serial", "wlan"] |
| V1912 service74/wlan_pd/wlanmdsp/wlan0 | 1/2/10/15.379517 |
| V1913 service74/wlan_pd/wlanmdsp/wlan0 | 1/2/10/15.010257 |
| V1913 contamination pcie-mhi/esoc/degraded257 | 0/0/False |

## pm-service Exclusion

| field | value |
| --- | --- |
| trace armed/service74/wlan_pd | 5.83/7.343928/9.727775 |
| register-ok/enable-ok | 8/8 |
| dispatch/msg20/msg21/msg22 | 0/0/0/0 |
| dispatch msgid 0x20/0x21/0x22 | 0/0/0 |
| V1888 Android msg20/msg21/msg22 | 0/0/0 |
| V1894 qmi-client/msg22/restart-ind | 0/0/0 |

## Source Boundary

| field | value |
| --- | --- |
| V1911 decision | v1911-service74-pre-wlanpd-caller-boundary-host-pass/True/service74-pre-wlanpd-caller-boundary |
| source non-header callers | ["kernel_build/SM-A908N_KOR_12_Opensource/Kernel/drivers/soc/qcom/icnss.c:2006"] |
| exported symbol | True |
| trace capability kprobe/function | False/False |

## Selected Diff

- Label: `internal-modem-service74-built-in-publication-edge`.
- `/dev/subsys_modem` is confirmed as a PM-client/subsys-get step on an already-online modem; it does not cause wlan_pd state-up by itself.
- The normal Android guest-PD-load trigger is now bounded before `wlan_pd` and outside pm-service msg20/21/22 dispatch observability.
- The remaining useful target is the built-in internal-modem service-notifier/service-locator path that creates the instance74 lookup/publication before WLFW service69 appears.
- Do not use the degraded 257s PCIe/MHI boot, SDX50M, eSoC, pcie1, or GDSC evidence for this path.

## Safety Scope

V1914 is host-only. It reads retained manifests and evidence text only. It executes no live device command, reboot, flash, tracefs write, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, partition write, or restart-PD request.

## Next

- Next live gate: read-only/bounded internal-modem kernel/servreg observer for the service74 lookup/publication edge, armed before ~7s and stopped before Wi-Fi HAL/scan/connect.
- If only static work is allowed, use a bounded stock-kernel image/kallsyms string/xref pass focused on `service_notif_register_notifier`, `SERVREG_NOTIF_SERVICE_ID`, instance `74`, ICNSS, and service-locator built-in code.
- Do not attempt Wi-Fi credentials/connect/ping until native proves WLFW service69 and `wlan0`.
