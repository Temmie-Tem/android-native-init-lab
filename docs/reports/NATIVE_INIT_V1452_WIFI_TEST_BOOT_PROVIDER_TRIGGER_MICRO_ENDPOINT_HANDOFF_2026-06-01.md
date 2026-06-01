# Native Init V1452 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1452`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1452-test-boot-provider-trigger-no-downstream-rollback-pass`
- Result: PASS
- Reason: test boot reached the esoc0 provider trigger and rollback verified, but no RC1/MHI/WLFW/wlan0 progress marker appeared
- Evidence: `tmp/wifi/v1452-wifi-test-boot-provider-trigger-micro-endpoint-handoff`
- Handoff/rollback pass: `True`
- Strict Wi-Fi progress mode: `False`
- Wi-Fi progress pass: `False`
- Progress decision: `provider-trigger-no-downstream`

## Progress Classification

- `provider_trigger`: `True`
- `rc1_progress`: `False`
- `rc1_l0`: `False`
- `rc1_link_failed`: `False`
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
- `pid1_rc1_watcher_result_file`: `state=triggered source=/proc/kmsg write_rc=0 errno=0 detect_elapsed_ms=7386 write_elapsed_ms=7687 delay_ms=0 retry_count=0 retry_delay_ms=0 line=<3>[    9.050498]  [1:    cnss-daemon:  599] __netlink_sendskb(1245) skb:00000000388bb57c queued sk: 000000009f58a7fc`
- `pid1_rc1_window_sampler_requested`: `None`
- `pid1_rc1_window_result_summary`: `None`
- `pid1_rc1_window_result_file`: `state=armed sampler=read-only-v1450-provider-trigger-micro-endpoint detect_elapsed_ms=7386 delay_ms=0 line=<3>[ 9.050498] [1: cnss-daemon: 599] __netlink_sendskb(1245) skb:00000000388bb57c queued sk: 000000009f58a7fc <3>[ 9.050522] [1: cnss-daemon: 59`
- `pid1_rc1_window_sample_count`: `1`
- `pid1_rc1_window_has_post_500ms`: `False`

## Key Evidence

- Test boot version: `A90 Linux init 0.9.83 (v1450-wifitest)`.
- Rollback version after handoff: `A90 Linux init 0.9.68 (v724)`.
- Provider window was reached and sampled, but `wlan0=absent`.
- GPIO135 stayed `out 0` and GPIO142 stayed `in 0` in the provider-trigger
  micro samples from `0ms` through `150ms`.
- Interrupt counts for `msmgpio-dc 104` and `msmgpio-dc 142` stayed at `0` in
  the same micro window.
- pcie1 `current_link_state` and `link_state` sysfs reads were unreadable in
  the micro window.
- No RC1/MHI/WLFW/BDF/FW-ready downstream progress marker was observed.

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
Device mutation was limited to flashing the test boot image and
rolling back to `stage3/boot_linux_v724.img`.

## Images

- Test image: `tmp/wifi/v1450-wifi-test-boot-provider-trigger-micro-endpoint-sampler/boot_linux_v1450_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

Treat `provider-trigger-no-downstream` as diagnostic evidence, not Wi-Fi
bring-up progress. Do not proceed to scan/connect, credentials, DHCP/routes,
or external ping until at least RC1/MHI/WLFW/`wlan0` progress is proven.
