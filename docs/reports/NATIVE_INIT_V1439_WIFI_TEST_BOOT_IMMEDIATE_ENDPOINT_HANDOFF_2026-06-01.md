# Native Init V1439 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1439`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1439-test-boot-downstream-progress-rollback-pass`
- Result: PASS
- Reason: test boot produced downstream Wi-Fi/PCIe evidence and rollback verified
- Evidence: `tmp/wifi/v1439-wifi-test-boot-immediate-endpoint-handoff`
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
- `debugfs_pci_msm_case_present`: `None`
- `helper_timed_out`: `None`
- `pid1_rc1_watcher_requested`: `None`
- `pid1_rc1_watcher_result_summary`: `None`
- `pid1_rc1_watcher_result_file`: `state=triggered source=/proc/kmsg write_rc=0 errno=0 detect_elapsed_ms=7386 write_elapsed_ms=20804 delay_ms=250 retry_count=0 retry_delay_ms=0 line=<3>[    9.079951]  [3:    cnss-daemon:  600] __netlink_sendskb(1245) skb:00000000d129016a queued sk: 00000000b8f3e8da`
- `pid1_rc1_window_sampler_requested`: `None`
- `pid1_rc1_window_result_summary`: `None`
- `pid1_rc1_window_result_file`: `state=armed sampler=read-only-v1437-immediate-endpoint detect_elapsed_ms=7386 delay_ms=250 line=<3>[ 9.079951] [3: cnss-daemon: 600] __netlink_sendskb(1245) skb:00000000d129016a queued sk: 00000000b8f3e8da <3>[ 9.079977] [3: cnss-daemon: 60`
- `pid1_rc1_window_sample_count`: `5`
- `pid1_rc1_window_has_post_500ms`: `True`

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
Device mutation was limited to flashing the test boot image and
rolling back to `stage3/boot_linux_v724.img`.

## Images

- Test image: `tmp/wifi/v1437-wifi-test-boot-immediate-endpoint-sampler/boot_linux_v1437_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Immediate Endpoint Evidence Notes

- The V1437 image still reached corrected RC1/LTSSM and failed before `LTSSM L0`.
- No MHI, WLFW, BDF, FW-ready, or `wlan0` evidence appeared.
- Immediate endpoint labels were emitted, but the exact debugfs scans were slow:
  `after_case_1ms` was recorded at `2402ms` immediate elapsed and
  `after_case_20ms` at `8634ms`.
- All immediate pcie1 GDSC/clock reads were already off; GPIO103/CLKREQ stayed
  high and GPIO142/MDM2AP stayed low.

## Next

Run a host-only classifier over the V1439 immediate endpoint evidence before
another live mutation. Do not proceed to scan/connect, credentials,
DHCP/routes, or external ping until at least L0/MHI/WLFW/`wlan0` progress is
proven.
