# Native Init V1464 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1464`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1464-test-boot-provider-trigger-no-downstream-rollback-pass`
- Result: PASS
- Reason: test boot reached the esoc0 provider trigger and rollback verified, but no RC1/MHI/WLFW/wlan0 progress marker appeared
- Evidence: `tmp/wifi/v1464-wifi-test-boot-exact-provider-tracepoint-handoff`
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
- `pid1_rc1_watcher_result_file`: `state=triggered source=/proc/kmsg write_rc=0 errno=0 detect_elapsed_ms=7425 write_elapsed_ms=8579 delay_ms=0 retry_count=0 retry_delay_ms=0 line=<3>[    9.178983]  [1:   Binder:593_3:  614] subsys-restart: __subsystem_get(): __subsystem_get: esoc0 count:0`
- `pid1_rc1_window_sampler_requested`: `None`
- `pid1_rc1_window_result_summary`: `None`
- `pid1_rc1_window_result_file`: `state=armed sampler=read-only-v1462-exact-provider-tracepoint detect_elapsed_ms=7425 delay_ms=0 exact_provider_line=1 long_provider_window=1 tracepoint_sampler=1 line=<3>[ 9.178983] [1: Binder:593_3: 614] subsys-restart: __subsystem_get(): __subsystem_get: esoc0 count:0`
- `pid1_rc1_window_sample_count`: `1`
- `pid1_rc1_window_has_post_500ms`: `False`

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
Device mutation was limited to flashing the test boot image and
rolling back to `stage3/boot_linux_v724.img`.

## Images

- Test image: `tmp/wifi/v1462-wifi-test-boot-exact-provider-tracepoint-sampler/boot_linux_v1462_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

Treat `provider-trigger-no-downstream` as diagnostic evidence, not Wi-Fi
bring-up progress. Do not proceed to scan/connect, credentials, DHCP/routes,
or external ping until at least RC1/MHI/WLFW/`wlan0` progress is proven.
