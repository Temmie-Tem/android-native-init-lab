# Native Init V1443 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1443`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1443-test-boot-downstream-progress-rollback-pass`
- Result: PASS
- Reason: test boot produced downstream Wi-Fi/PCIe evidence and rollback verified
- Evidence: `tmp/wifi/v1443-wifi-test-boot-micro-endpoint-handoff`
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
- `pid1_rc1_watcher_result_file`: `state=triggered source=/proc/kmsg write_rc=0 errno=0 detect_elapsed_ms=7424 write_elapsed_ms=7978 delay_ms=250 retry_count=0 retry_delay_ms=0 line=<3>[    9.108742]  [0:    cnss-daemon:  601] __netlink_sendskb(1245) skb:00000000abcfecee queued sk: 000000001d6b5500`
- `pid1_rc1_window_sampler_requested`: `None`
- `pid1_rc1_window_result_summary`: `None`
- `pid1_rc1_window_result_file`: `state=armed sampler=read-only-v1441-micro-endpoint detect_elapsed_ms=7424 delay_ms=250 line=<3>[ 9.108742] [0: cnss-daemon: 601] __netlink_sendskb(1245) skb:00000000abcfecee queued sk: 000000001d6b5500 <3>[ 9.108767] [0: cnss-daemon: 60`
- `pid1_rc1_window_sample_count`: `1`
- `pid1_rc1_window_has_post_500ms`: `False`

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
Device mutation was limited to flashing the test boot image and
rolling back to `stage3/boot_linux_v724.img`.

## Images

- Test image: `tmp/wifi/v1441-wifi-test-boot-micro-endpoint-sampler/boot_linux_v1441_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Micro Endpoint Evidence Notes

- The V1441 image still reached corrected RC1/LTSSM and failed before
  `LTSSM L0`.
- No MHI, WLFW, BDF, FW-ready, or `wlan0` evidence appeared.
- The micro endpoint sampler emitted nine `rc1_micro_sample` entries plus a
  bounded writer summary.
- The writer completed `rc_sel=2` and `case=11` successfully with
  `writer_wait_rc=0`, `status=0x0`, and `micro_writer rc=0`.
- The micro reader started before the case write completed: writer case elapsed
  was `7790ms`, micro start elapsed was `7675ms`, so only
  `micro_after_case_150ms` landed after the actual case write.
- GPIO135 stayed `out 0` and GPIO142 stayed `in 0` across the micro samples.

## Next

Run a host-only classifier over the V1443 micro endpoint evidence before
another live mutation. Do not proceed to scan/connect, credentials,
DHCP/routes, or external ping until at least L0/MHI/WLFW/`wlan0` progress is
proven.
