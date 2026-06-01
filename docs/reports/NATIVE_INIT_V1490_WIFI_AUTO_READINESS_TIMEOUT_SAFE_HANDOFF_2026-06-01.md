# Native Init V1490 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1490`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1490-timeout-safe-provider-trigger-no-downstream-manual-rollback-pass`
- Result: BLOCKED
- Reason: timeout-safe readiness summary worked and v724 was restored manually, but Wi-Fi downstream markers are still absent
- Evidence: `tmp/wifi/v1490-wifi-auto-readiness-timeout-safe-handoff`
- Handoff/rollback pass: `False` from the generic runner; final manual rollback verification: `True`
- Strict Wi-Fi progress mode: `True`
- Wi-Fi progress pass: `False`
- Progress decision: `provider-trigger-no-downstream`

## Progress Classification

- `provider_trigger`: `True`
- `modem_trigger`: `True`
- `rc1_progress`: `False`
- `rc1_l0`: `False`
- `rc1_link_failed`: `False`
- `mhi_progress`: `False`
- `wlfw_progress`: `False`
- `bdf_progress`: `False`
- `fw_ready_progress`: `False`
- `wlan0_present`: `False`
- `connect_ready`: `False`
- `debugfs_pci_msm_case_present`: `1`
- `helper_timed_out`: `1`
- `pid1_rc1_watcher_requested`: `0`
- `pid1_rc1_watcher_result_summary`: `None`
- `pid1_rc1_watcher_result_file`: ``
- `pid1_rc1_window_sampler_requested`: `0`
- `pid1_rc1_window_result_summary`: `None`
- `pid1_rc1_window_result_file`: ``
- `pid1_rc1_window_sample_count`: `0`
- `pid1_rc1_window_has_post_500ms`: `False`

## Timeout-safe Readiness

- `auto_readiness_pid1.begin`: `1`
- `auto_readiness_pid1.syslog_ok`: `1`
- `auto_readiness_pid1.modem_trigger_seen`: `1`
- `auto_readiness_pid1.provider_trigger_seen`: `1`
- `auto_readiness_pid1.pcie_rc1_seen`: `0`
- `auto_readiness_pid1.mhi_seen`: `0`
- `auto_readiness_pid1.wlfw_seen`: `0`
- `auto_readiness_pid1.icnss_qmi_seen`: `0`
- `auto_readiness_pid1.bdf_seen`: `0`
- `auto_readiness_pid1.fw_ready_seen`: `0`
- `auto_readiness_pid1.wlan0_seen`: `0`
- `auto_readiness_pid1.primary_checkpoint`: `provider-trigger`
- `helper_wait_rc`: `-110`
- `helper_timed_out`: `1`

## Rollback Correction

The generic TWRP rollback path failed because recovery ADB never appeared after
the native `recovery` command. The device remained on the V1488 test boot, so a
manual rollback was performed from native init:

- NCM was brought up temporarily and host `192.168.7.1/24` was assigned.
- `stage3/boot_linux_v724.img` was downloaded to `/cache/boot_linux_v724.img`.
- Downloaded image sha256 matched
  `ae01fa106391756dae12fc9a6c9f57d4111b2180c82cdcfe3691ee31f7542adc`.
- `boot` was identified as `sda24` (`259:8`) from sysfs `PARTNAME=boot`.
- `/dev/block/sda24` was created and written from `/cache/boot_linux_v724.img`.
- Boot block prefix sha256 matched the v724 image sha256 above.
- Final status verified `A90 Linux init 0.9.68 (v724)`.
- Final selftest verified `fail=0`.
- Evidence files: `manual-rollback-notes.txt`, `manual-v724-status.stdout.txt`,
  and `manual-v724-selftest.stdout.txt`.

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
Device mutation included flashing the test boot image and restoring
`stage3/boot_linux_v724.img`. The final restoration used native direct boot
partition write after the generic TWRP rollback path failed.

## Images

- Test image: `tmp/wifi/v1488-wifi-auto-readiness-timeout-safe-test-boot/boot_linux_v1488_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

Treat `provider-trigger-no-downstream` as diagnostic evidence, not Wi-Fi
bring-up progress. Before another live handoff, update the runner rollback
strategy so native direct rollback from a pre-staged `/cache/boot_linux_v724.img`
is an explicit fallback when recovery ADB is unavailable. Do not proceed to
scan/connect, credentials, DHCP/routes, or external ping until at least
RC1/MHI/WLFW/`wlan0` progress is proven.
