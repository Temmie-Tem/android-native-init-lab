# Native Init V1901 Service-notifier Publication Absent Classifier

## Summary

- Cycle: `V1901`
- Type: host-only classifier over retained Android-good/native service-notifier evidence
- Decision: `v1901-servnotif-publication-absent-not-socket-mechanics-host-pass`
- Label: `servnotif-publication-absent-not-socket-mechanics`
- Result: `PASS`
- Reason: service74/msm/modem/wlan_pd publication remains absent after native post-open; QRTR socket, listener, and WLFW69 readback mechanics are not the blocker
- Evidence: `tmp/wifi/v1901-servnotif-publication-absent-classifier`

## Gate Checks

| check | result |
| --- | --- |
| `android_normal_internal` | `True` |
| `native_publication_absent` | `True` |
| `qipcrtr_mechanics_ruled_out` | `True` |
| `wlfw_readback_empty` | `True` |
| `servloc_domain_absent` | `True` |
| `uninit_transition_consistent` | `True` |

## Android Normal Internal Path

- V1900 decision/label/pass: `v1900-cnss-worker-parity-servnotif-stateup-gap-host-pass` / `cnss-worker-parity-servnotif-stateup-gap` / `True`
- V1900 Android requested_wlanmdsp/wlan_pd/wlanmdsp/wlan0: `1` / `2` / `20` / `15.181203`
- V1900 Android pre-wlan0 pcie-mhi/degraded257: `0` / `False`
- V1898 ordered service180/service74/wlan_pd/wlanmdsp: `1` / `1` / `2` / `20`
- V1898 pm_msg22 hits: `0`

## Native Publication Gap

- V1900 native service180/service74/wlan_pd: `1,1,1` / `0,0,0` / `0,0,0`
- V1900 native servnotif/WLFW69/wlanmdsp/wlan0: `uninit` / `0` / `0` / `0`
- V1898 native service180/service74/wlan_pd: `1,1,1` / `0,0,0` / `0,0,0`
- V1898 native servnotif/WLFW69/wlanmdsp/wlan0: `uninit` / `0` / `0` / `0`

## Mechanics Ruled Out

- V1834 QIPCRTR bound/poll/recv/no-send: `True` / `True` / `False` / `1`
- V1834 service180/service74/wlan_pd/WLFW69: `1,1,1` / `0,0,0` / `0,0,0` / `0`
- V1803 WLFW request/ind-register/cap/WLFW69: `1` / `0` / `0` / `0`
- V1803 QRTR service69 readback events/end-of-list: `0,0` / `1,1`
- V1819 servloc/service180/service74/wlan_pd-domain: `servloc-init-visible-domain-absent` / `1,1,1` / `0,0,0` / `0,0,0`
- V1836 qipcrtr/qrtr-readback/servnotif: `qipcrtr-bound-recv-poll-timeout-passive` / `wlfw-readback-empty` / `uninit`

## Selected Boundary

- Keep the path anchored on the internal modem WLAN-PD state-up sequence.
- Do not chase pm-service msg22: Android-good state-up has zero msg22 hits in the normal path.
- Do not chase QRTR socket mechanics: passive local bind and recv-poll execute without any inbound WLAN-PD publication.
- The next useful native unit is read-only instrumentation of service-locator/service-notifier publication transitions that would create service74 and WLFW service69.

## Safety Scope

V1901 is host-only. It reads retained manifests and writes local classifier artifacts only. It performs no device command, flash, reboot, tracefs write, service start, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC/regulator write, forced RC1/case write, `/dev/subsys_esoc0` open, fake ONLINE state, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware write, boot write, or partition write.

## Next

- Build the next bounded native read-only capture around service-notifier/service-locator publication and WLFW service69 readback after `/dev/subsys_modem` open.
- Do not attempt Wi-Fi connect or ping until native init proves WLFW service 69 and `wlan0`.
