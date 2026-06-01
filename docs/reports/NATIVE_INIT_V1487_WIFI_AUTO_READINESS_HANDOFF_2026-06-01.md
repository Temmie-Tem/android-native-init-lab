# Native Init V1487 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1487`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1487-test-boot-provider-trigger-no-downstream-wifi-progress-blocked`
- Result: BLOCKED
- Reason: test boot reached the esoc0 provider trigger and rollback verified, but strict Wi-Fi progress markers were absent
- Evidence: `tmp/wifi/v1487-wifi-auto-readiness-test-boot-handoff`
- Handoff/rollback pass: `True`
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

## Evidence Notes

- Test boot verified `A90 Linux init 0.9.90 (v1485-wifitest)` and rollback
  verified `A90 Linux init 0.9.68 (v724)`.
- PID1 summary shows `auto_readiness_supervisor_requested=1` and marker
  `auto-v1485-wifi-readiness-test`.
- The helper reached the same provider path as prior live tests:
  `__subsystem_get: modem` at about 3.27s and `__subsystem_get: esoc0` at
  about 9.13s.
- The helper timed out (`helper_wait_rc=-110`, `helper_timed_out=1`,
  `helper_status_raw=15`) before producing the buffered `auto_readiness.*`
  summary lines.
- Focused dmesg still has no PCIe RC1/LTSSM, MHI, WLFW, BDF, FW-ready, or
  `wlan0` marker.
- `wlan0=absent`.

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
Device mutation was limited to flashing the test boot image and
rolling back to `stage3/boot_linux_v724.img`.

## Images

- Test image: `tmp/wifi/v1485-wifi-auto-readiness-test-boot/boot_linux_v1485_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

Treat `provider-trigger-no-downstream` as diagnostic evidence, not Wi-Fi
bring-up progress. V1488 should make the auto-readiness summary timeout-safe
instead of relying on the long-running helper's buffered stdout: persist a
sidecar result or let PID1 synthesize readiness from focused dmesg/`wlan0`
after the bounded helper timeout. Do not proceed to scan/connect, credentials,
DHCP/routes, or external ping until at least RC1/MHI/WLFW/`wlan0` progress is
proven.
