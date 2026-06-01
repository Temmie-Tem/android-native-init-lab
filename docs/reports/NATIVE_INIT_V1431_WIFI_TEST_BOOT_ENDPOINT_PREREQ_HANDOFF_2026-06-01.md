# Native Init V1431 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1431`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1431-test-boot-downstream-progress-rollback-pass`
- Result: PASS
- Reason: test boot produced downstream Wi-Fi/PCIe evidence and rollback verified
- Evidence: `tmp/wifi/v1431-wifi-test-boot-endpoint-prereq-handoff`
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
- `pid1_rc1_watcher_result_file`: `state=triggered source=/proc/kmsg write_rc=0 errno=0 detect_elapsed_ms=7384 write_elapsed_ms=7921 delay_ms=250 retry_count=0 retry_delay_ms=0 line=<3>[    9.059879]  [1:    cnss-daemon:  598] __netlink_sendskb(1245) skb:00000000a275c72e queued sk: 00000000392a81f0`
- `pid1_rc1_window_sampler_requested`: `None`
- `pid1_rc1_window_result_summary`: `None`
- `pid1_rc1_window_result_file`: `state=armed sampler=read-only-v1429-endpoint-prereq detect_elapsed_ms=7384 delay_ms=250 line=<3>[ 9.059879] [1: cnss-daemon: 598] __netlink_sendskb(1245) skb:00000000a275c72e queued sk: 00000000392a81f0 <3>[ 9.059906] [1: cnss-daemon: 59`
- `pid1_rc1_window_sample_count`: `5`
- `pid1_rc1_window_has_post_500ms`: `True`

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
Device mutation was limited to flashing the test boot image and
rolling back to `stage3/boot_linux_v724.img`.

## Images

- Test image: `tmp/wifi/v1429-wifi-test-boot-endpoint-prereq-sampler/boot_linux_v1429_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

Treat `provider-trigger-no-downstream` as diagnostic evidence, not Wi-Fi
bring-up progress. Do not proceed to scan/connect, credentials, DHCP/routes,
or external ping until at least RC1/MHI/WLFW/`wlan0` progress is proven.
