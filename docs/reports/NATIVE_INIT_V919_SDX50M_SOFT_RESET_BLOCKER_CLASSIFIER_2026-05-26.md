# V919 SDX50M Soft-Reset Blocker Classifier

- generated: `2026-05-25T21:03:36.535421+00:00`
- decision: `v919-sdx50m-soft-reset-blocker-classified`
- pass: `True`
- reason: existing Android dmesg/IRQ/GPIO evidence is sufficient; V918 blocks in SDX50M soft-reset after mdm_helper fd gating, while Android orders vendor.mdm_helper and cnss-daemon wlfw_start before esoc0 subsystem_get and then reaches WLAN-PD/BDF/wlan0
- next_step: plan V920 as host-only design for a bounded cnss-daemon/WLFW-request-before-esoc0 trigger gate; do not repeat /dev/subsys_esoc0 open or boot Android solely for Magisk-style evidence

## Classification

| field | value |
| --- | --- |
| android_upper_positive | True |
| native_soft_reset_block | True |
| android_precondition_gap | True |
| research_support | True |

## Android Positive Ordering

| marker | present | time | line |
| --- | --- | --- | --- |
| mdm3_config | True | 0.822552 | [    0.822552] ext-mdm soc:qcom,mdm3: Cannot config MDM_PMIC_PWR_STATUS gpio |
| vendor_mdm_helper_start | True | 8.14817 | [    8.148170] init: starting service 'vendor.mdm_helper'... |
| cnss_wlfw_start | True | 8.349631 | [    8.349631] cnss-daemon wlfw_start: Starting |
| esoc0_subsystem_get | True | 8.402277 | [    8.402277] subsys-restart: __subsystem_get(): __subsystem_get: esoc0 count:0 |
| wlan_pd | True | 9.414862 | [    9.414862] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1 |
| bdf_regdb | True | 9.476146 | [    9.476146] cnss-daemon wlfw_send_bdf_download_req: BDF file : regdb.bin |
| bdf_bdwlan | True | 9.487515 | [    9.487515] cnss-daemon wlfw_send_bdf_download_req: BDF file : bdwlan.bin |
| wlan0 | True | 14.950217 | [   14.950217] dev : wlan0 : event : 16 |

## Android Lower Snapshots

| field | value |
| --- | --- |
| gpio_debug_readable | True |
| gpio135_snapshot | gpio135 : out 0 16mA no pull |
| gpio142_snapshot | gpio142 : in  0 8mA no pull |
| pmic_gpio9_snapshot | gpio9 : out  normal  vin-1 pull-down 10uA              push-pull  high low     atest-1 dtest-0 |
| mdm_status_irq | 290:          0          0          0          0          0          0          0          0  msmgpio-dc 142 Edge      mdm status |
| vendor_mdm_helper_running | True |

## V918 Native Negative Control

| field | value |
| --- | --- |
| decision | v918-reboot-required-cleaned |
| cleanup_reboot_executed | True |
| post_cleanup_healthy | True |
| mdm_helper_observable | 1 |
| fd_esoc0_gate | 1 |
| subsys_open_attempted | 1 |
| subsys_trigger_started | 1 |
| subsys_trigger_exited | 0 |
| timed_out | 1 |
| result | reboot-required |
| wchan | sdx50m_toggle_soft_reset |
| state | D (disk sleep) |
| mdm3_state_before | OFFLINING |
| mdm3_state_after |  |
| ks_final | 0 |
| mhi_final | 0 |
| wlan0_after | 0 |

## V918 Guardrails

| forbidden path | executed |
| --- | --- |
| service_manager | False |
| cnss | False |
| wifi_hal | False |
| scan_connect | False |
| credentials | False |
| dhcp_route | False |
| external_ping | False |
| notify | False |
| boot_done | False |

## Research Anchors

- `sdx50m_toggle_soft_reset()` de-asserts PMIC GPIO9 and does not wait for GPIO142 inside the function.
- `wait_for_err_ready()` is not the observed wait location; V918 captured the block inside the proprietary SDX50M power-up path.
- Android positive control already has enough after-the-fact dmesg/GPIO/IRQ evidence for this gate; a Magisk module is not required before the next host-only design step.

### Selected Android Lines

- [    0.822552] ext-mdm soc:qcom,mdm3: Cannot config MDM_PMIC_PWR_STATUS gpio
- [    0.822604] ext-mdm soc:qcom,mdm3: mdm_configure_ipc set AP2MDM_ERRFATAL2 as a AP2MDM_ERRFATAL
- [    8.148170] init: starting service 'vendor.mdm_helper'...
- [    8.171920] init: Control message: Processed ctl.start for 'vendor.mdm_helper' from pid: 1110 (start vendor.mdm_helper)
- [    8.349631] cnss-daemon wlfw_start: Starting
- [    8.402277] subsys-restart: __subsystem_get(): __subsystem_get: esoc0 count:0
- [    8.402289] subsys-restart: __subsystem_get(): Changing subsys fw_name to esoc0
- [    9.414862] service-notifier: root_service_service_ind_cb: Indication received from msm/modem/wlan_pd, state: 0x1fffffff, trans-id: 1
- [    9.415084] service-notifier: send_ind_ack: Indication ACKed for transid 1, service msm/modem/wlan_pd, instance 180!
- [    9.476146] cnss-daemon wlfw_send_bdf_download_req: BDF file : regdb.bin
- [    9.487515] cnss-daemon wlfw_send_bdf_download_req: BDF file : bdwlan.bin
- [   14.950217] dev : wlan0 : event : 16

### Selected V918 Stack Lines

- sdx50m_toggle_soft_reset
- [<0000000000000000>] sdx50m_toggle_soft_reset+0x114/0x128
- [<0000000000000000>] mdm4x_do_first_power_on+0x5c/0x128
- [<0000000000000000>] mdm_cmd_exe+0x430/0x590
- [<0000000000000000>] mdm_subsys_powerup+0x174/0x5d8
- [<0000000000000000>] __subsystem_get+0x150/0x320
- [<0000000000000000>] subsys_device_open+0x78/0xb0
- sdx50m_toggle_soft_reset

## Guardrails

- Host-only classifier: no device contact, no ADB command, no Android boot, and no Magisk module.
- No actor start, eSoC ioctl, `/dev/subsys_esoc0` open, CNSS daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, GPIO/sysfs/debugfs write, boot image write, partition write, or firmware mutation.
