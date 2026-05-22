# Native Init V609 Post-Sysmon Observer Plan

- date: `2026-05-23 KST`
- status: `planned`
- target: isolate the unstable `service-notifier` `180` publication before
  CNSS userspace can add noise

## Context

V608 replayed the V598 no-service-manager path with helper v100 and still did
not reproduce `service-notifier` `180`. This means helper version is not a
sufficient root-cause explanation. The next useful proof must observe the
post-sysmon window without starting CNSS.

## Scope

V609 may add a new helper mode and host runner for a bounded observer window.
It may mount the same firmware surfaces and hold only `subsys_modem`.

It must not start `cnss_diag`, `cnss-daemon`, service-manager, Wi-Fi HAL,
`wificond`, supplicant, or hostapd during the primary observer window. It must
not send QMI payloads, write `qcwlanstate`, scan/connect/link-up, use
credentials, run DHCP, change routes, ping externally, flash boot images, or
write persistent partitions.

## Proposed Helper Mode

Add a helper mode equivalent to:

```text
wifi-companion-post-sysmon-observer-start-only
```

Allowed child order:

```text
qrtr_ns,rmt_storage,tftp_server,pd_mapper
```

Blocked child order:

```text
cnss_diag,cnss_daemon,servicemanager,hwservicemanager,vndservicemanager,Wi-Fi HAL,wificond,supplicant,hostapd
```

## Observation Contract

1. Host runner refreshes V401/V490 after the current boot.
2. Host runner holds `subsys_modem` only; `esoc0` remains unopened.
3. Runner waits for QRTR RX, QRTR TX, and modem `sysmon-qmi`.
4. Helper holds the lower companion window for a bounded duration.
5. Runner captures dmesg, `/proc/net/qrtr` if available, qipcrtr socket counts,
   rpmsg surface, subsystem states, and cleanup evidence.
6. Runner reboot-cleans and verifies native status.

## Decision Labels

- `v609-service-notifier-pre-cnss-visible`
- `v609-service-notifier-pre-cnss-missing`
- `v609-qrtr-sysmon-not-reached`
- `v609-preflight-blocked`
- `v609-cleanup-review`

## Next Decision

- If `service-notifier` `180` appears pre-CNSS, the next gate should start CNSS
  only after that marker.
- If it remains absent, the next gate should compare Android/native lower modem
  publication preconditions around QRTR/sysmon/service-notifier, not Wi-Fi HAL
  or scan/connect.
