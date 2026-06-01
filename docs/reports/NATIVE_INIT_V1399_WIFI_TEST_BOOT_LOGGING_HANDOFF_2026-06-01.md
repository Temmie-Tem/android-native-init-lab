# Native Init V1399 Wi-Fi Test Boot Logging Handoff

## Summary

- Cycle: `V1399`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1399-test-boot-provider-trigger-no-downstream-rollback-pass`
- Result: PASS
- Reason: test boot reached the esoc0 provider trigger and rollback verified, but no RC1/MHI/WLFW/wlan0 progress marker appeared
- Evidence: `tmp/wifi/v1399-wifi-test-boot-logging-handoff`

V1399 is the first live handoff of the V1397 logging test boot. It proves the
new fresh-log and summary-watcher path works during a real flash/boot/rollback
cycle, but it also shows the PID1-launched helper has already become a zombie by
the `35s` summary sample while no downstream Wi-Fi/PCIe marker appears.

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner. Device mutation was limited to flashing the V1397
test boot image and rolling back to `stage3/boot_linux_v724.img`.

## Images

- Test image: `tmp/wifi/v1397-wifi-test-boot/boot_linux_v1397_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Observations

- Test boot reached `A90 Linux init 0.9.70 (v1397-wifitest)`.
- The V1397 log was fresh for this boot: it begins with `log_reset` and only one
  `armed`/`spawned` sequence.
- PID1 spawned `a90_android_execns_probe` as helper pid `545` and watcher pid
  `546`.
- The watcher summary sampled after `35001ms`; helper pid `545` was still
  present but in `State: Z (zombie)`.
- Dmesg showed `subsys_modem` at about `3.249s` and `__subsystem_get: esoc0` at
  about `9.093s`.
- No `PCIe RC1`, `LTSSM`, MHI, WLFW/BDF, or `wlan0` marker appeared.
- `/sys/class/net/wlan0` remained absent.
- Rollback verified return to `A90 Linux init 0.9.68 (v724)`.

## Interpretation

The V1397 logging change worked: old append pollution is gone, and the summary
watcher captured a new, useful state. The key new fact is that the helper exits
before the `35s` watcher sample, but PID1 does not collect the helper exit code
or final result because it launches the helper directly and does not wait for it.

This makes another identical handoff low-value. The next source/build cycle
should turn the test boot into a non-blocking supervised run: fork a small
supervisor child, let that child spawn and wait for the helper with a bounded
timeout, and write helper exit status plus any final stdout/stderr/log summary.
That keeps PID1 non-blocking while making the helper result observable.

## Next

V1400 should be source/build-only: replace the direct PID1 helper spawn with a
non-blocking supervisor child that waits for the helper, records exit status,
duration, timeout state, log size, `wlan0` presence, and relevant helper summary
keys. Do not proceed to Wi-Fi scan/connect, credentials, DHCP/routes, or external
ping until WLFW/`wlan0` progress is proven.
