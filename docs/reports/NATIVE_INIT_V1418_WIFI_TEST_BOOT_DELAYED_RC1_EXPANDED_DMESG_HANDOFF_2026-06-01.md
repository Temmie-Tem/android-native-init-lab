# Native Init V1418 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1418`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1418-test-boot-downstream-progress-rollback-pass`
- Result: PASS
- Reason: test boot produced downstream Wi-Fi/PCIe evidence and rollback verified
- Evidence: `tmp/wifi/v1418-wifi-test-boot-delayed-rc1-expanded-dmesg-handoff`
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
- `pid1_rc1_watcher_result_summary`: `state=triggered source=/proc/kmsg write_rc=0 errno=0 detect_elapsed_ms=7425 write_elapsed_ms=7791 delay_ms=250 line=<3>[ 9.146396] [3: cnss-daemon: 601] __netlink_sendskb(1245) skb:00000000705a2e23 queued sk: 00000000074c2c36 <3`
- `pid1_rc1_watcher_result_file`: `state=triggered source=/proc/kmsg write_rc=0 errno=0 detect_elapsed_ms=7425 write_elapsed_ms=7791 delay_ms=250 line=<3>[    9.146396]  [3:    cnss-daemon:  601] __netlink_sendskb(1245) skb:00000000705a2e23 queued sk: 00000000074c2c36`

## Timing and RC1 Markers

- `esoc0`: `9.199070s`
- `TEST: 11`: `9.475987s`
- `Assert endpoint reset`: `9.476043s`
- `PCIE20_PARF_INT_ALL_MASK`: `9.479581s`, value `0x7f80c202`
- `PHY ready`: `9.481797s`
- `Release endpoint reset`: `9.481812s`
- First `LTSSM_POLL_ACTIVE`: `9.498258s`
- First `LTSSM_POLL_COMPLIANCE`: `9.523996s`
- Link failure: `9.590797s`, `LTSSM_STATE:0x3`
- `esoc0_to_assert`: about `0.277s`
- Android reference `esoc0_to_assert`: about `0.255s`
- `assert_to_release`: about `0.0058s`, matching the source/Android shape
- `release_to_link_failed`: about `0.109s`

V1418 proves the V1414 test boot does execute the normal corrected RC1
enumerate sequence: assert PERST, program interrupt mask, reach PHY ready,
release PERST, and enter LTSSM. It still never reaches L0/GEN2 and produces no
MHI/WLFW/BDF/FW-ready/`wlan0`. The remaining blocker is therefore endpoint
readiness/response after PERST release, not missing reset/release execution.

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

V1419 should be host/source-only: design the next below-connect probe around
endpoint readiness after PERST release. Useful candidates are a test-boot
read-only GPIO142/interrupt sampler around the RC1 window, a tighter comparison
with Android V852 GPIO142/PCIe/MHI timing, or a bounded delay sweep only if the
design can prove why endpoint readiness would depend on a narrower delay. Do
not proceed to scan/connect, credentials, DHCP/routes, or external ping until
at least MHI/WLFW/`wlan0` progress is proven.
