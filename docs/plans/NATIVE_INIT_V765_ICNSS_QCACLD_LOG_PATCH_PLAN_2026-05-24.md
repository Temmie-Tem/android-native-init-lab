# Native Init V765 ICNSS/QCACLD Log Patch Plan

- date: `2026-05-24 KST`
- scope: host-only source patch generation
- runner: `scripts/revalidation/native_wifi_icnss_qcacld_log_patch_v765.py`

## Goal

After V764 proved service180-gated `mdm_helper` is startable but insufficient,
return to the V757/V758/V763 source-backed instrumentation route. V765 should
generate a reviewable minimal `A90V765` log patch from staged Samsung OSRC
source without applying it, building a kernel, writing a boot image, or touching
the device.

## Inputs

- V760: staged source target verification passed.
- V763: SM-A908N live path is ICNSS/QCACLD SNOC, not CNSS2/MHI.
- V764: service180-gated `mdm_helper` started safely but did not advance
  mdm3/WLAN-PD/MHI/QCA6390/WLFW/BDF/`wlan0`.

## Target Patch Points

The patch must use a unique `A90V765` marker and cover:

- `drivers/soc/qcom/icnss_qmi.c`
  - `icnss_register_fw_service()`
  - `wlfw_new_server()`
- `drivers/soc/qcom/icnss.c`
  - `icnss_driver_event_server_arrive()`
  - `icnss_driver_event_fw_ready_ind()`
  - `icnss_driver_event_register_driver()`
  - `icnss_call_driver_probe()`
  - `__icnss_register_driver()`
- `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/src/pld_snoc.c`
  - `pld_snoc_probe()`
  - `pld_snoc_register_driver()`
- `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/`
  - `wlan_boot_cb()`
  - `hdd_driver_load()` stages
  - `wlan_hdd_register_driver()`
  - `hdd_wlan_startup()`

## Forbidden

- no source tree mutation in `kernel_build`
- no kernel build
- no boot image or partition write
- no device command
- no service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or
  external ping

## Success Criteria

- Generate a unified diff under private `tmp/wifi` evidence.
- Confirm all patch anchors apply.
- Confirm V760/V763/V764 prerequisites are present.
- Preserve the next build/apply/flash as separate gates.
