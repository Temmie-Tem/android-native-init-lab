# Native Init V1422 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1422`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1422-test-boot-downstream-progress-rollback-pass`
- Result: PASS
- Reason: test boot produced downstream Wi-Fi/PCIe evidence and rollback verified
- Evidence: `tmp/wifi/v1422-wifi-test-boot-rc1-window-sampler-handoff`
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
- `pid1_rc1_watcher_result_file`: `state=triggered source=/proc/kmsg write_rc=0 errno=0 detect_elapsed_ms=7425 write_elapsed_ms=7799 delay_ms=250 line=<3>[    9.128636]  [3:    cnss-daemon:  601] __netlink_sendskb(1245) skb:0000000087039599 queued sk: 000000009ac43631`
- `pid1_rc1_window_sampler_requested`: `None`
- `pid1_rc1_window_result_summary`: `None`
- `pid1_rc1_window_result_file`: `state=armed sampler=read-only-v1420 detect_elapsed_ms=7425 delay_ms=250 line=<3>[ 9.128636] [3: cnss-daemon: 601] __netlink_sendskb(1245) skb:0000000087039599 queued sk: 000000009ac43631 <3>[ 9.128660] [3: cnss-daemon: 60`
- `pid1_rc1_window_sample_count`: `5`
- `pid1_rc1_window_has_post_500ms`: `True`

## RC1 Window Findings

The V1420 sampler collected all five intended snapshots:

- `pre_delay`
- `pre_rc1`
- `post_rc1_50ms`
- `post_rc1_150ms`
- `post_rc1_500ms`

Across all five snapshots:

- GPIO135/AP2MDM stayed `out 0 16mA no pull`.
- GPIO142/MDM2AP stayed `in 0 8mA no pull`.
- `mdm status` IRQ stayed at count `0`.
- RC1 reached PHY ready and LTSSM polling, then failed before L0.
- MHI, WLFW, BDF, FW-ready, and `wlan0` stayed absent.

This narrows the current blocker below scan/connect and below Wi-Fi HAL:
corrected RC1 timing and reset/release execution are present, but the endpoint
does not assert the MDM2AP ready/status path and never reaches PCIe L0.

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
Device mutation was limited to flashing the test boot image and
rolling back to `stage3/boot_linux_v724.img`.

## Images

- Test image: `tmp/wifi/v1420-wifi-test-boot-rc1-window-sampler/boot_linux_v1420_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

V1423 should be host-only/read-only classification over V1422 plus Android
positive evidence: determine whether Android ever shows GPIO135/AP2MDM high in
a comparable window, or whether GPIO135 is active-low/pulsed too briefly for the
current sampler. Do not proceed to scan/connect, credentials, DHCP/routes, or
external ping until at least L0/MHI/WLFW/`wlan0` progress is proven.
