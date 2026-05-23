# Native Init V661 Binder Registration Context Classifier Plan

- date: `2026-05-23 KST`
- cycle: `v661`
- scope: host-only classifier
- target: classify the post-V660 blocker after proven service `74`,
  service-manager trio startup, `vndservicemanager` readiness, and fresh
  `cnss-daemon` retry still stop at a native-only vendor binder transaction
  failure before WLFW

## Background

V660 closed the earlier readiness/order uncertainty. The fresh retry sequence
ran only after:

```text
service 74
  -> servicemanager/hwservicemanager/vndservicemanager
  -> vndservicemanager_ready
  -> cnss_daemon_initial_cleanup
  -> cnss_daemon_retry
```

The retry was observable and cleanup-safe, but `cnss-daemon` still hit a
vendor-binder transaction failure and native did not reach WLFW, WLAN-PD, QMI
server connected, BDF, firmware-ready, or `wlan0`.

## Guardrails

V661 must not:

- contact the device;
- write sysfs, `boot_wlan`, `qcwlanstate`, DSP boot nodes, partitions, or boot
  images;
- start companion daemons, service-manager, CNSS, Wi-Fi HAL, `wificond`,
  supplicant, or hostapd;
- scan/connect/link-up, use credentials, run DHCP, change routes, or ping
  externally.

## Inputs

- V660 live evidence:
  `tmp/wifi/v660-ready-cnss-retry-live/manifest.json`
- V660 helper transcript:
  `tmp/wifi/v660-ready-cnss-retry-live/native/companion-start-only-with-holder.txt`
- V660 dmesg delta:
  `tmp/wifi/v660-ready-cnss-retry-live/native/dmesg-delta.txt`
- V659 readiness-only evidence
- V654 binder runtime classifier evidence
- Android V649 reference dmesg used by V654/V651

## Checks

1. Confirm V660 reached fresh service `74` and preserved it through the
   service-manager trio.
2. Confirm `vndservicemanager_readiness.ready=1` before `cnss_daemon_retry`.
3. Confirm `cnss_daemon_retry` was observable, cleanup-safe, and opened
   `/dev/vndbinder`.
4. Confirm binder devnodes, SELinux service context files, and service-manager
   children were present/readable/observable.
5. Confirm the blocker persisted as a native `cnss-daemon` binder transaction
   failure before WLFW.
6. Compare against Android reference where generic binder ioctl `-22` is
   non-fatal and WLFW/WLAN-PD/QMI/BDF/`wlan0` continue.
7. Identify whether the remaining missing evidence is dynamic service
   registration/listing, property namespace, or binder context-manager state,
   rather than another readiness-order retry.

## Success Criteria

V661 passes if it can classify the next blocker without live mutation:

- `v661-binder-registration-context-gap-classified`
- `v661-android-reference-gap-needs-recapture`
- `v661-v660-evidence-incomplete`

Passing V661 does not authorize Wi-Fi HAL, scan/connect, credentials, DHCP,
routes, or external ping. If V661 selects a next live gate, it must be bounded
to readout/observation of service registration and runtime context before any
Wi-Fi bring-up attempt.
