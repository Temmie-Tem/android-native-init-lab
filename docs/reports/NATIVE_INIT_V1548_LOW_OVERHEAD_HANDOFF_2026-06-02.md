# Native Init V1548 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1548`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1548-test-boot-downstream-progress-rollback-pass`
- Result: PASS
- Reason: test boot produced downstream Wi-Fi/PCIe evidence and rollback verified
- Evidence: `tmp/wifi/v1548-low-overhead-handoff`
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
- `pid1_rc1_watcher_result_file`: `state=triggered source=/proc/kmsg trigger_mode=sysfs_client_enumerate write_rc=0 errno=0 detect_elapsed_ms=7385 write_elapsed_ms=7813 delay_ms=0 retry_count=0 retry_delay_ms=0 line=<3>[    9.060457]  [0:    cnss-daemon:  599] netlink_recvmsg(1926) skb: 0000000021b57722 copy dgram pid:599 comm:cnss-da`
- `pid1_rc1_window_sampler_requested`: `None`
- `pid1_rc1_window_result_summary`: `None`
- `pid1_rc1_window_result_file`: `state=armed sampler=auto-v1485-wifi-readiness-test detect_elapsed_ms=7385 delay_ms=0 exact_provider_line=0 long_provider_window=0 tracepoint_sampler=0 pil_tracepoint_sampler=0 sysfs_client_enumerate=1 trigger_mode=sysfs_client_enumerate line=<3>[ 9.060457] [0: cnss-daemon: 599] netlink_recvmsg(1926) skb: 0000000021b57722 copy dgram pid:599 comm:cnss-daemon sk: 0000000045adc8e6 <3>[ 9.0604`
- `pid1_rc1_window_sample_count`: `1`
- `pid1_rc1_window_has_post_500ms`: `False`

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
Device mutation included flashing the test boot image, any bounded
in-boot actions declared by that test image's artifact contract, and
rolling back to `stage3/boot_linux_v724.img`. If enabled, native direct
rollback may restore the boot partition from a pre-staged `/cache`
rollback image when recovery ADB is unavailable.

## Images

- Test image: `tmp/wifi/v1546-low-overhead-endpoint-observer-test-boot/boot_linux_v1546_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

Treat `rc1-ltssm-link-failed-no-l0` as the fixed diagnostic outcome for this
handoff. The low-overhead critical sampler removed `micro_focused_clk` from the
critical loop and captured pre-fail GPIO, interrupt, regulator, pinmux, and
link-state evidence, but RC1 still failed before L0 and no MHI/WLFW/BDF/
FW-ready/`wlan0` marker appeared. Next work should classify the V1548 pre-fail
evidence and focus on pcie1 power-domain/debugfs semantics before any new live
mutation or connect-side work.
