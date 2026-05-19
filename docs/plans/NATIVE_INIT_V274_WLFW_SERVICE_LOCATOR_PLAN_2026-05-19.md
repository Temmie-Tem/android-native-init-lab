# Native Init v274 WLFW Service Locator Plan

## Summary

- target: v274 WLFW service id locator
- boot image change: none
- device command: none
- packet transmission: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_wlfw_service_locator.py`

v273 showed that WDS and DMS nameservice lookup did not produce QRTR service
notifications. v274 stays host-only and resolves the Wi-Fi-specific WLFW
service id by correlating public Qualcomm kernel headers with local
`cnss-daemon` strings.

## References

- `WLFW_SERVICE_ID_V01 0x45` and `WLFW_SERVICE_VERS_V01 0x01` appear in the
  Android kernel CNSS2 WLAN firmware service header:
  `https://android.googlesource.com/kernel/msm/+/c2aee3401467314b48882a22d71906f380a5c17a/drivers/net/wireless/cnss2/wlan_firmware_service_v01.h`
- The same service id/version appear in the older Qualcomm SoC WLAN firmware
  service header:
  `https://android.googlesource.com/kernel/msm.git/+/7601617b4549fa3c1a237fb11cac04c54b182466/drivers/soc/qcom/wlan_firmware_service_v01.h`
- CNSS2 QMI code includes `wlan_firmware_service_v01.h`, which is the kernel
  side of the WLFW service contract:
  `https://android.googlesource.com/kernel/msm.git/+/a9259a89dc7ee9f37d4dd1aaa1670b53f29ef015/drivers/net/wireless/cnss2/qmi.h`

## Scope

- Read local vendor evidence:
  - `tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon`
  - `tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libqmiservices.so`
- Confirm local WLFW flow strings:
  - `wlfw_service_request`
  - `wlfw_send_cap_req`
  - `wlfw_send_bdf_download_req`
  - `wlfw_send_ind_register_req`
  - `WLFW service connected`
- Confirm the exported WLFW service object remains absent from
  `libqmiservices.so`.
- Emit next candidate matrix string: `wlfw:69:0,1`.

## Guardrails

v274 must not:

- execute Android code
- execute device commands
- open QRTR sockets
- send QRTR nameservice packets
- send QMI payloads
- start `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, DHCP,
  or routing commands
- scan/connect/link-up Wi-Fi

## Validation

```bash
python3 scripts/revalidation/wifi_wlfw_service_locator.py \
  --out-dir tmp/wifi/v274-wlfw-service-locator \
  analyze

python3 -m py_compile \
  scripts/revalidation/wifi_wlfw_service_locator.py \
  scripts/revalidation/wifi_qrtr_readback_matrix.py \
  scripts/revalidation/wifi_qmi_service_object_extractor.py \
  scripts/revalidation/a90ctl.py

git diff --check
```

## Acceptance

- manifest decision is `wlfw-service-id-source-backed`
- WLFW service id is `69` / `0x45`
- WLFW service version is `1`
- local `cnss-daemon` WLFW strings match the source-backed service family
- no packet or device command is executed
- next step is an explicit-approval QRTR nameservice readback for WLFW `0x45`,
  still with no QMI payload
