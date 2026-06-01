# Native Init V1427 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1427`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1427-test-boot-downstream-progress-rollback-pass`
- Result: PASS
- Reason: test boot produced downstream Wi-Fi/PCIe evidence and rollback verified
- Evidence: `tmp/wifi/v1427-wifi-test-boot-rc1-retry-handoff`
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
- `pid1_rc1_watcher_result_file`: `state=triggered source=/proc/kmsg write_rc=0 errno=0 detect_elapsed_ms=7367 write_elapsed_ms=7740 delay_ms=250 retry_count=2 retry_delay_ms=500 retry1_rc=0 retry1_errno=0 retry1_elapsed_ms=8355 retry2_rc=0 retry2_errno=0 retry2_elapsed_ms=8970 line=<3>[    9.061460]  [2:    cnss-daemon:  599] __netlink_sendskb(1245) skb:000000000d4163e9 queued sk: 00000000ed240626`
- `pid1_rc1_window_sampler_requested`: `None`
- `pid1_rc1_window_result_summary`: `None`
- `pid1_rc1_window_result_file`: `state=armed sampler=read-only-v1420 detect_elapsed_ms=7367 delay_ms=250 line=<3>[ 9.061460] [2: cnss-daemon: 599] __netlink_sendskb(1245) skb:000000000d4163e9 queued sk: 00000000ed240626 <3>[ 9.061485] [2: cnss-daemon: 59`
- `pid1_rc1_window_sample_count`: `5`
- `pid1_rc1_window_has_post_500ms`: `True`

## RC1 Retry Findings

V1425 executed the intended bounded retry policy:

- initial corrected RC1 write: `retry_count=2`, `retry_delay_ms=500`
- retry 1: `retry1_rc=0`, elapsed `8355ms`
- retry 2: `retry2_rc=0`, elapsed `8970ms`

Expanded dmesg shows:

- `TEST: 11` count: `3`
- RC1 link initialization failure count: `3`
- L0 count: `0`
- MHI/WLFW/BDF/FW-ready/`wlan0`: absent

Each attempt reaches the same RC1 reset/release/LTSSM path and fails at
`LTSSM_STATE:0x3` before L0. This rules out "single early corrected-RC1 attempt"
as the primary blocker. The endpoint still does not respond even after two
post-failure retries spaced by `500ms`.

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
Device mutation was limited to flashing the test boot image and
rolling back to `stage3/boot_linux_v724.img`.

## Images

- Test image: `tmp/wifi/v1425-wifi-test-boot-rc1-retry/boot_linux_v1425_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

V1428 should stop widening corrected-RC1 retry count and return to the lower
endpoint prerequisite model: compare/prepare only read-only evidence for RC1
power/refclk/PERST/PMIC state, or design a narrowly justified pre-RC1 prerequisite
test. Do not proceed to scan/connect, credentials, DHCP/routes, or external ping
until at least L0/MHI/WLFW/`wlan0` progress is proven.
