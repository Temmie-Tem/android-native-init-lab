# Native Init V1496 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1496`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1496-test-boot-downstream-progress-rollback-pass`
- Result: PASS
- Reason: test boot produced downstream Wi-Fi/PCIe evidence and rollback verified
- Evidence: `tmp/wifi/v1496-wifi-rc1-window-short-hold-handoff`
- Handoff/rollback pass: `True`
- Rollback attempt: `from-native`
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
- `pid1_rc1_watcher_result_file`: `state=triggered source=/proc/kmsg write_rc=0 errno=0 detect_elapsed_ms=7385 write_elapsed_ms=7509 delay_ms=0 retry_count=0 retry_delay_ms=0 line=<3>[    9.080191]  [2:    cnss-daemon:  599] __netlink_sendskb(1245) skb:00000000463f74aa queued sk: 00000000b93e51ed`
- `pid1_rc1_window_sampler_requested`: `None`
- `pid1_rc1_window_result_summary`: `None`
- `pid1_rc1_window_result_file`: `state=armed sampler=auto-v1485-wifi-readiness-test detect_elapsed_ms=7385 delay_ms=0 exact_provider_line=0 long_provider_window=0 tracepoint_sampler=0 pil_tracepoint_sampler=0 line=<3>[ 9.080191] [2: cnss-daemon: 599] __netlink_sendskb(1245) skb:00000000463f74aa queued sk: 00000000b93e51ed <3>[ 9.080215] [2: cnss-daemon: 59`
- `pid1_rc1_window_sample_count`: `5`
- `pid1_rc1_window_has_post_500ms`: `True`

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
Device mutation was limited to flashing the test boot image and
rolling back to `stage3/boot_linux_v724.img`. If enabled, native
direct rollback may restore the boot partition from a pre-staged
`/cache` rollback image when recovery ADB is unavailable.

## Images

- Test image: `tmp/wifi/v1493-wifi-auto-readiness-rc1-window-test-boot/boot_linux_v1493_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

Treat this as real lower-stack progress but not Wi-Fi readiness. Native now
reaches PCIe RC1 PHY readiness and LTSSM polling, but it fails at
`LTSSM_POLL_COMPLIANCE` and never reaches L0, MHI, WLFW, BDF, FW-ready, or
`wlan0`. Do not proceed to scan/connect, credentials, DHCP/routes, or external
ping. Next classify the RC1 link failure against the Android-good RC1 sequence:
PERST/refclk/reset GPIO state, MDM2AP/GPIO142, and whether the endpoint is
electrically responding before LTSSM compliance stalls.
