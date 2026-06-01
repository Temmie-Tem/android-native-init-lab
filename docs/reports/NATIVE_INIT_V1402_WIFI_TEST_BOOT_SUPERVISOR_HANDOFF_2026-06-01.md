# Native Init V1402 Wi-Fi Test Boot Supervisor Handoff

## Summary

- Cycle: `V1402`
- Type: bounded live supervised test-boot handoff with rollback
- Decision: `v1402-test-boot-provider-trigger-no-downstream-rollback-pass`
- Result: PASS
- Reason: test boot reached the esoc0 provider trigger and rollback verified, but no RC1/MHI/WLFW/wlan0 progress marker appeared
- Evidence: `tmp/wifi/v1402-wifi-test-boot-supervisor-handoff`

V1402 is the first live handoff of the V1400 supervised test boot. It proves the
supervisor path works: the supervisor waited for the helper and recorded a clean
exit status. It also proves the helper exits successfully before any downstream
Wi-Fi/PCIe marker appears.

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner. Device mutation was limited to flashing the V1400
test boot image and rolling back to `stage3/boot_linux_v724.img`.

## Images

- Test image: `tmp/wifi/v1400-wifi-test-boot/boot_linux_v1400_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Observations

- Test boot reached `A90 Linux init 0.9.71 (v1400-wifitest)`.
- The V1400 log was fresh for this boot and starts with `log_reset`.
- PID1 spawned supervisor pid `545`; the supervisor spawned helper pid `546`.
- Supervisor recorded `helper_wait_rc=0`, `helper_timed_out=0`, `helper_status_raw=0`, and `helper_exit_code=0`.
- Summary sampled after `23322ms` since helper spawn and showed `wlan0_present=0`.
- Dmesg showed `subsys_modem` at about `3.269s` and `__subsystem_get: esoc0` at about `9.112s`.
- No `PCIe RC1`, `LTSSM`, MHI, WLFW/BDF, or `wlan0` marker appeared.
- `/sys/class/net/wlan0` remained absent.
- Rollback verified return to `A90 Linux init 0.9.68 (v724)`.

## Interpretation

The supervised path closes the V1399 zombie/unknown-exit gap. The helper is not
hanging and not timing out; it exits `0` while the kernel still has no RC1, MHI,
WLFW, BDF, or `wlan0` progress. That means the current helper mode's success
criteria are too weak for the Wi-Fi objective: it treats provider-trigger
observation as a successful diagnostic run even though the desired downstream
state is absent.

The next source/build cycle should make the test-boot helper contract stricter
for this path. It should either classify `provider-trigger-no-downstream` as a
non-success result in the helper's emitted summary, or add explicit output keys
for `provider_trigger`, `rc1_progress`, `wlfw_progress`, `wlan0_present`, and
`final_decision` so PID1 summary can distinguish diagnostic pass from Wi-Fi
progress.

## Next

V1403 should be source/build-only: add a strict downstream-progress decision to
the helper/test-boot summary path. Do not proceed to Wi-Fi scan/connect,
credentials, DHCP/routes, or external ping until WLFW/`wlan0` progress is proven.
