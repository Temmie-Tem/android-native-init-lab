# Native Init v274 WLFW Service Locator Report

## Summary

- status: PASS
- boot image change: none
- device command: none
- packet transmission: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_wlfw_service_locator.py`
- evidence: `tmp/wifi/v274-wlfw-service-locator/`
- decision: `wlfw-service-id-source-backed`
- WLFW service id: `69` / `0x45`
- WLFW service version: `1`

v274 uses public kernel headers and local `cnss-daemon` string evidence to
locate the Wi-Fi-specific WLFW service id. It does not execute Android code,
send QRTR packets, or send QMI payloads.

## References

- Android kernel CNSS2 header:
  `https://android.googlesource.com/kernel/msm/+/c2aee3401467314b48882a22d71906f380a5c17a/drivers/net/wireless/cnss2/wlan_firmware_service_v01.h`
- Android kernel Qualcomm SoC header:
  `https://android.googlesource.com/kernel/msm.git/+/7601617b4549fa3c1a237fb11cac04c54b182466/drivers/soc/qcom/wlan_firmware_service_v01.h`
- Android kernel CNSS2 QMI include path:
  `https://android.googlesource.com/kernel/msm.git/+/a9259a89dc7ee9f37d4dd1aaa1670b53f29ef015/drivers/net/wireless/cnss2/qmi.h`

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

Result:

```text
decision: wlfw-service-id-source-backed
pass: True
reason: public kernel headers identify WLFW service id 0x45 and local cnss-daemon strings match WLFW flows
```

## Key Checks

- `v273-ready`: PASS
- `v272-ready`: PASS
- `cnss-daemon-exists`: PASS
- `source-wlfw-service-id-known`: PASS, id `0x45`, version `1`
- `local-wlfw-string-coverage`: PASS
- `local-wlan-string-coverage`: PASS as warning context
- `local-exported-wlfw-object-absent`: PASS as warning/unresolved classifier

## Local Evidence

The local `cnss-daemon` contains WLFW flow strings including:

- `Failed to start wlfw service`
- `WLFW service connected`
- `wlfw_service_request`
- `wlfw_send_cap_req`
- `wlfw_send_bdf_download_req`
- `wlfw_send_ind_register_req`
- `wlfw_handle_initiate_cal_download_ind`
- `wlfw_handle_initiate_cal_update_ind`

`libqmiservices.so` still does not export a `wlfw_qmi_idl_service_object`
symbol, so the id is source-backed rather than local-object-extracted.

## Interpretation

- WLFW is now a concrete service-id candidate: service `69` / `0x45`.
- This is more Wi-Fi-specific than WDS `1` or DMS `2`.
- The next safe live step is a bounded QRTR nameservice readback matrix for
  WLFW `0x45`, not a QMI request payload.

## Guardrails Preserved

- host-only evidence correlation
- no Android code execution
- no device command executed
- no QRTR socket opened
- no QRTR nameservice packet sent
- no QMI payload sent
- no Wi-Fi scan/connect/link-up
- no credentials, DHCP, routing, or Internet-facing exposure
- no `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, or hostapd start

## Next Step

v275 should run an explicit-approval QRTR nameservice readback matrix for WLFW
service `0x45`, instances `0` and `1`, still with no QMI payloads.
