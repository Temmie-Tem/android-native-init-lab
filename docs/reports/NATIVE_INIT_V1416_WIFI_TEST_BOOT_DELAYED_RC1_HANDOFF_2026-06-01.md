# Native Init V1416 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1416`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1416-test-boot-downstream-progress-rollback-pass`
- Result: PASS
- Reason: test boot produced downstream Wi-Fi/PCIe evidence and rollback verified
- Evidence: `tmp/wifi/v1416-wifi-test-boot-delayed-rc1-handoff`
- Handoff/rollback pass: `True`
- Strict Wi-Fi progress mode: `True`
- Wi-Fi progress pass: `True`
- Progress decision: `rc1-ltssm-link-failed-no-l0`

## Progress Classification

- `provider_trigger`: `True`
- `rc1_progress`: `True`
- `rc1_l0`: `False`
- `rc1_link_failed`: `True`
- `mhi_progress`: `False`
- `wlfw_progress`: `False`
- `bdf_progress`: `False`
- `fw_ready_progress`: `False`
- `wlan0_present`: `False`
- `connect_ready`: `False`
- `debugfs_pci_msm_case_present`: `1`
- `helper_timed_out`: `1`
- `pid1_rc1_watcher_requested`: `1`
- `pid1_rc1_watcher_result_summary`: `state=triggered source=/proc/kmsg write_rc=0 errno=0 detect_elapsed_ms=7367 write_elapsed_ms=7732 delay_ms=250 line=<3>[ 9.098002] [0: cnss-daemon: 598] __netlink_sendskb(1245) skb:00000000b568874e queued sk: 0000000089f1eafb <3`
- `pid1_rc1_watcher_result_file`: `state=triggered source=/proc/kmsg write_rc=0 errno=0 detect_elapsed_ms=7367 write_elapsed_ms=7732 delay_ms=250 line=<3>[    9.098002]  [0:    cnss-daemon:  598] __netlink_sendskb(1245) skb:00000000b568874e queued sk: 0000000089f1eafb`

## Timing Notes

- `esoc0`: `9.151711s`
- `TEST: 11`: `9.426832s`
- `esoc0_to_test11`: about `0.275s`
- V1413 `esoc0_to_test11`: about `0.032s`
- Android reference `esoc0_to_assert`: about `0.255s`
- Interpretation: the V1414 `250ms` watcher delay moved the corrected RC1
  trigger into the Android-derived timing window, but RC1 still failed in
  `LTSSM_POLL_COMPLIANCE` before L0. That makes "too early trigger" unlikely
  to be the sole remaining blocker. The next classifier should compare the
  exact RC1 trigger semantics against Android, especially reset/PERST/refclk
  markers that may not be reproduced by the debugfs `TEST: 11` path.

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
Device mutation was limited to flashing the test boot image and
rolling back to `stage3/boot_linux_v724.img`.

Rollback health was verified after the run: current device reports
`A90 Linux init 0.9.68 (v724)` and selftest `fail=0`.

## Images

- Test image: `tmp/wifi/v1414-wifi-test-boot-delayed-rc1/boot_linux_v1414_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

V1417 should be host-only: compare V1416, V1413, and Android RC1 traces to
classify whether the remaining gap is delay tuning, debugfs `TEST: 11` trigger
semantics, or endpoint reset/refclk/PERST readiness. Do not proceed to
scan/connect, credentials, DHCP/routes, or external ping until at least
MHI/WLFW/`wlan0` progress is proven.
