# Native Init V1469 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1469`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1469-test-boot-provider-trigger-no-downstream-rollback-pass`
- Result: PASS
- Reason: test boot reached the esoc0 provider trigger and rollback verified, but no RC1/MHI/WLFW/wlan0 progress marker appeared
- Evidence: `tmp/wifi/v1469-wifi-test-boot-exact-provider-pil-gpio-tracepoint-handoff`
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
- `debugfs_pci_msm_case_present`: `1`
- `helper_timed_out`: `1`
- `pid1_rc1_watcher_requested`: `1`
- `pid1_rc1_watcher_result_summary`: `state=triggered source=/proc/kmsg write_rc=0 errno=0 detect_elapsed_ms=7364 write_elapsed_ms=8523 delay_ms=0 retry_count=0 retry_delay_ms=0 line=<3>[ 9.113701] [1: Binder:588_3: 609] subsys-restart: __subsystem_get(): __subsystem_get: esoc0 count:0`
- `pid1_rc1_watcher_result_file`: `state=triggered source=/proc/kmsg write_rc=0 errno=0 detect_elapsed_ms=7364 write_elapsed_ms=8523 delay_ms=0 retry_count=0 retry_delay_ms=0 line=<3>[    9.113701]  [1:   Binder:588_3:  609] subsys-restart: __subsystem_get(): __subsystem_get: esoc0 count:0`
- `pid1_rc1_window_sampler_requested`: `1`
- `pid1_rc1_window_result_summary`: `state=armed sampler=read-only-v1467-exact-provider-pil-gpio-tracepoint detect_elapsed_ms=7364 delay_ms=0 exact_provider_line=1 long_provider_window=1 tracepoint_sampler=1 pil_tracepoint_sampler=1 line=<3>[ 9.113701] [1: Binder:588_3: 609] subsys-restart: __subsystem_get(): __subsystem_get: esoc0 count:0 rc1_micro_sample label=provider_micro_after_trigger_0ms elapsed_ms=7365 detec`
- `pid1_rc1_window_result_file`: `state=armed sampler=read-only-v1467-exact-provider-pil-gpio-tracepoint detect_elapsed_ms=7364 delay_ms=0 exact_provider_line=1 long_provider_window=1 tracepoint_sampler=1 pil_tracepoint_sampler=1 line=<3>[ 9.113701] [1: Binder:588_3: 609] subsys-restart: __subsystem_get(): __subsystem_get: esoc0 count:0`
- `pid1_rc1_window_sample_count`: `1`
- `pid1_rc1_window_has_post_500ms`: `False`

## Safety Scope

No Wi-Fi scan/connect, credential handling, DHCP/routes, external ping,
PMIC/GPIO/GDSC direct write, or blind eSoC notify/`BOOT_DONE` spoof was
performed by this runner.
Device mutation was limited to flashing the test boot image and
rolling back to `stage3/boot_linux_v724.img`.

## Images

- Test image: `tmp/wifi/v1467-wifi-test-boot-exact-provider-pil-gpio-tracepoint-sampler/boot_linux_v1467_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

Treat `provider-trigger-no-downstream` as diagnostic evidence, not Wi-Fi
bring-up progress. Do not proceed to scan/connect, credentials, DHCP/routes,
or external ping until at least RC1/MHI/WLFW/`wlan0` progress is proven.
