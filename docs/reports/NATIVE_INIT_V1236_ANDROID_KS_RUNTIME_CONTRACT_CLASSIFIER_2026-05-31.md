# V1236 Android ks/MHI Runtime Contract Classifier

- report: `docs/reports/NATIVE_INIT_V1236_ANDROID_KS_RUNTIME_CONTRACT_CLASSIFIER_2026-05-31.md`
- classifier: `scripts/revalidation/native_wifi_android_ks_runtime_contract_classifier_v1236.py`
- evidence: `tmp/wifi/v1236-android-ks-runtime-contract-classifier/manifest.json`

- generated: `2026-05-31T01:31:56.265364+00:00`
- decision: `v1236-ks-contract-is-pm-proxy-pm-service-trigger-not-mdm-helper-exec`
- pass: `True`
- reason: Android ks/MHI path correlates with per_proxy -> pm-service Binder -> subsys_esoc0/mdm_subsys_powerup, while native V1235 proves mdm_helper WAIT_FOR_REQ return does not exec ks or create MHI by itself
- next_step: V1237 should run a bounded live gate that keeps V1235 branch snapshot but enables late per_proxy only after mdm_helper holds /dev/esoc-0; capture pm-service Binder wchan/fds plus ks/MHI/GPIO142, still no Wi-Fi HAL or connect

## Checks

| check | status | detail |
| --- | --- | --- |
| android-positive-lower-chain | pass | Android has mdm3 ONLINE, WLFW/BDF/wlan0, and GPIO142 IRQ |
| android-actor-contract | pass | Android actor handoff includes mdm_helper, ks, MHI, and per_mgr subsystem fds |
| android-pm-proxy-precedes-esoc0 | pass | per_proxy=8.824458 esoc0=9.491382 |
| native-mdm-helper-wait-returned | pass | transition_sample=4 |
| native-no-mdm-helper-exec | pass | execve_count=0 |
| native-no-ks-mhi-wlfw | pass | latest native window has no ks/MHI/GPIO142 progress |
| native-direct-subsys-blocks | pass | direct subsystem trigger child is in mdm_subsys_powerup |
| guardrails-clean | pass | no Wi-Fi HAL/scan/credential/DHCP/ping guardrail violation in V1235 parser |

## Android Contract Evidence

| field | value |
| --- | --- |
| mdm3_online | True |
| wlan0_present | True |
| bdf_present | True |
| wlfw_present | True |
| gpio142_irq_count | 1 |
| mdm_helper_esoc_fd | True |
| ks_esoc_fd | True |
| ks_mhi_pipe | True |
| per_mgr_subsys_esoc0_fd | True |
| per_proxy_start_time | 8.824458 |
| pm_service_esoc0_time | 9.491382 |
| pm_service_binder_mdm_subsys_powerup | True |
| fw_ready_time | 15.344607 |
| wlan0_time | 15.784281 |

## Native Negative Evidence

| field | value |
| --- | --- |
| v1228_wait_for_req_seen | True |
| v1235_wait_returned | True |
| v1235_transition_sample | 4 |
| v1235_execve_count | 0 |
| v1235_ioctl_count | 4 |
| v1235_nanosleep_count | 68 |
| v1235_ks_count | 0 |
| v1235_mhi_pipe_exists | 0 |
| v1235_mhi_pipe_fd_count | 0 |
| observer_child_mdm_subsys_powerup | True |
| observer_mdm_helper_holds_esoc0 | True |
| observer_max_gpio142_count | 0 |
| observer_max_mhi_dev_count | 0 |
| observer_max_ks_count | 0 |
| observer_mdm3_states | OFFLINING |
| observer_pcie_states | absent |

## Safety

| field | value |
| --- | --- |
| device_commands_executed | False |
| device_mutations | False |
| pm_actor_executed | False |
| mdm_helper_executed | False |
| tracefs_write_executed | False |
| wifi_hal_start_executed | False |
| scan_connect_executed | False |
| credential_use_executed | False |
| dhcp_route_executed | False |
| external_ping_executed | False |
| wifi_bringup_executed | False |
| flash_executed | False |
| partition_write_executed | False |

## Interpretation

V1236 closes the direct `mdm_helper` post-return exec branch as the primary missing link. Android reaches `ks`/MHI only in the path where `vendor.per_proxy` starts before the `pm-service` Binder thread enters `__subsystem_get(esoc0)` / `mdm_subsys_powerup`. Native V1235 proves that `mdm_helper` holding `/dev/esoc-0` and returning from `ESOC_WAIT_FOR_REQ` is not enough: it goes back to sleep, does not exec `ks`, and no MHI or GPIO142 progress appears.

The next live gate should therefore add exactly the missing late `per_proxy` trigger after `mdm_helper` holds `/dev/esoc-0`, while preserving all lower safety gates.
