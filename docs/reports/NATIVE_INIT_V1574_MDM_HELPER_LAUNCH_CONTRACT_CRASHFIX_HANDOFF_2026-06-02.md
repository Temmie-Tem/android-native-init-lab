# Native Init V1574 Wi-Fi Test Boot Handoff

## Summary

- Cycle: `V1574`
- Type: bounded live test-boot handoff with rollback
- Decision: `v1574-test-boot-no-downstream-wifi-progress-blocked`
- Result: BLOCKED
- Reason: test boot ran and rollback verified, but strict Wi-Fi progress markers were absent
- Evidence: `tmp/wifi/v1574-mdm-helper-launch-contract-crashfix-handoff`
- Handoff/rollback pass: `True`
- Rollback attempt: `from-native`
- Strict Wi-Fi progress mode: `True`
- Wi-Fi progress pass: `False`
- Progress decision: `no-provider-no-downstream`

## Progress Classification

- `provider_trigger`: `False`
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
- `helper_timed_out`: `0`
- `helper_result_file_seen`: `True`
- `helper_result_contract_seen`: `True`
- `helper_result_size`: `581319`
- `helper_result_subsys_open_attempted`: `0`
- `helper_result_subsys_trigger_started`: `0`
- `helper_result_subsys_trigger_gate_open`: `0`
- `helper_result_mdm_helper_esoc0_fd_count`: `0`
- `helper_result_final_result`: `subsys-trigger-not-attempted-no-mdm-helper-esoc-fd`
- `helper_result_final_reason`: `service-window-gate-did-not-see-dev-esoc-0`
- `pid1_rc1_watcher_requested`: `0`
- `pid1_rc1_watcher_result_summary`: `None`
- `pid1_rc1_watcher_result_file`: ``
- `pid1_rc1_window_sampler_requested`: `0`
- `pid1_rc1_window_result_summary`: `None`
- `pid1_rc1_window_result_file`: ``
- `pid1_rc1_window_sample_count`: `0`
- `pid1_rc1_window_has_post_500ms`: `False`

## Launch-contract Result

- `result_file_version`: `a90_android_execns_probe v290`
- helper process: `helper_status_raw=0`, `helper_exited=1`,
  `helper_exit_code=0`, `helper_signaled=0`
- `planned.compare.pm_proxy_absent_delta`: `1`
- `after_mdm_helper_spawn.compare.pm_proxy_absent_delta`: `1`
- `after_mdm_helper_spawn.fd.esoc0`: `0`
- `after_mdm_helper_spawn.fd.subsys_esoc0`: `0`
- `after_mdm_helper_spawn.fd.subsys_modem`: `0`
- `mdm_helper_esoc0_fd_count`: `0`
- `subsys_trigger_gate_open`: `0`
- `subsys_trigger.started`: `0`
- final helper result: `subsys-trigger-not-attempted-no-mdm-helper-esoc-fd`
- final helper reason: `service-window-gate-did-not-see-dev-esoc-0`

This confirms the crash/stale-result defect from V1572 is fixed.  The active
service-window path is blocked before RC1/MHI/WLFW because `mdm_helper` is
started without the Android-good `pm_proxy`/`pm_proxy_helper` launch contract
and never holds `/dev/esoc-0`.

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

- Test image: `tmp/wifi/v1573-mdm-helper-launch-contract-crashfix-test-boot/boot_linux_v1393_wifi_test.img`
- Rollback image: `stage3/boot_linux_v724.img`

## Next

Do not proceed to RC1 retry, firmware/MHI deep dive, Wi-Fi scan/connect,
credentials, DHCP/routes, or external ping.  The next gate is either a
source/build-only service-window route that restores the missing
`pm_proxy`/`pm_proxy_helper` launch contract, or a host-only contract diff that
identifies the exact `pm-service` Binder request needed before `mdm_helper`
can acquire `/dev/esoc-0`.
