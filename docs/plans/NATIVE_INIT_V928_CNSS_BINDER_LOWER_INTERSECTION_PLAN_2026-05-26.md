# Native Init V928 CNSS Binder / Lower Publication Intersection Plan

## Goal

Classify the post-V927 blocker without another live mutation. V927 proved that
helper `v153` compact output and runtime namespace repair are active, but
`cnss-daemon` still does not reach the WLFW precondition.

## Inputs

- V927 compact CNSS-before-eSoC live manifest and transcript.
- V924 CNSS/WLFW precondition gap classifier.
- V914 Android positive WLFW/BDF/`wlan0` timeline.
- V600 registry/CNSS matrix.
- V603 QRTR-first service-manager live proof.

## Questions

1. Did V927 remove the prior linkerconfig/output-truncation blocker?
2. Does V927 still show `cnss-daemon` binder failure before `wlfw_start`?
3. Did V603 prove service-manager can clear binder failures?
4. Did V603 also show lower service-notifier publication regression?
5. Is the next useful gate a same-window ordering intersection rather than a
   full-output retry, HAL start, or Wi-Fi scan/connect attempt?

## Guardrails

- Host-only.
- No device command.
- No daemon start.
- No service-manager start.
- No Wi-Fi HAL start.
- No scan/connect/link-up.
- No credential use.
- No DHCP, route change, or external ping.
- No eSoC ioctl, subsystem open, GPIO/sysfs/debugfs write, boot image write, or
  partition write.

## Success Criteria

- Produce a manifest that proves V927 runtime namespace repair is active.
- Count V927 CNSS binder failures, `cld80211` reachability, and missing
  `wlfw_start`/BDF/`wlan0`.
- Compare V603 service-manager binder-clean result and service-notifier
  regression.
- Route V929 to a source/build-only same-window ordering gate if both halves are
  true.

## Next

If V928 passes, V929 should design helper support for a delayed
service-manager/CNSS intersection gate: preserve lower publication first, start
the service-manager trio only at the right point, then start CNSS with compact
output. Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping
remain blocked until WLFW/BDF/`wlan0` progresses.
