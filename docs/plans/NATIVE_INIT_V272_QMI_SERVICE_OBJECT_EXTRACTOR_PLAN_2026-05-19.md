# Native Init v272 QMI Service Object Extractor Plan

## Summary

- target: v272 QMI service object ID extractor
- boot image change: none
- device command: none
- QRTR/QMI packet transmission: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_qmi_service_object_extractor.py`

v271 showed that the arbitrary QRTR lookup for service `1`, instance `1` is
negative evidence and that DMS/WLFW/WLAN need service-object-based selection.
v272 therefore stays host-only and parses exported QMI IDL service object data
from vendor ELF files to derive numeric service ids without executing Android
code or sending packets.

## Reference Model

- Qualcomm generated QMI service objects are ordinary ELF data objects exposed
  by service libraries; generated accessor functions return pointers to those
  objects.
- Open-source Android QMI examples show generated `*_get_service_object_internal`
  accessors returning `qmi_idl_service_object_type`.
- QMI clients commonly call `qmi_client_get_service_list()` with a service
  object before initializing a client, but v272 does not call that function
  because it can perform live service discovery.

Reference sources:

- Android generated QMI service object example: `https://android.googlesource.com/device/google/marlin/+/android-7.1.0_r2/location/loc_api/loc_api_v02/location_service_v02.c`
- Android QMI client service-list example: `https://android.googlesource.com/device/google/marlin/+/nougat-dr1-release/location/loc_api/ds_api/ds_client.c`
- Qualcomm WLAN DMS QMI client example: `https://android.googlesource.com/platform/hardware/qcom/wlan/+/16d38e6/qcwcn/wcnss-service/wcnss_qmi_client.c`

## Scope

- Parse local vendor evidence:
  - `tmp/wifi/v226-vendor-root-live-export/vendor-source/lib64/libqmiservices.so`
  - `tmp/wifi/v226-vendor-root-live-export/vendor-source/bin/cnss-daemon`
- Parse ELF64 little-endian sections, program headers, and dynamic symbols
  without requiring `pyelftools`.
- Extract exported symbols matching `*_qmi_idl_service_object_vXX`.
- For each service object, read:
  - service id
  - IDL library/major version
  - max message length
  - command/response/indication table counts
  - max message id
- Resolve v271 candidates:
  - service `1`, instance `1`
  - DMS
  - WLFW
  - WLAN

## Guardrails

v272 must not:

- execute Android code
- execute device commands
- open QRTR sockets
- send QRTR nameservice packets
- send QMI payloads
- call `qmi_client_get_service_list()` or `qmi_client_init*()`
- start `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, hostapd, DHCP,
  or routing commands
- scan/connect/link-up Wi-Fi

## Validation

```bash
python3 scripts/revalidation/wifi_qmi_service_object_extractor.py \
  --out-dir tmp/wifi/v272-qmi-service-object-extractor \
  analyze

python3 -m py_compile \
  scripts/revalidation/wifi_qmi_service_object_extractor.py \
  scripts/revalidation/wifi_qrtr_service_selector.py \
  scripts/revalidation/wifi_qrtr_nameservice_runner.py \
  scripts/revalidation/a90ctl.py

git diff --check

rg -n "v272|qmi-service-object-ids-extracted|service id 1|DMS|WLFW" \
  docs/plans docs/reports scripts/revalidation/wifi_qmi_service_object_extractor.py
```

## Acceptance

- manifest decision is `qmi-service-object-ids-extracted`
- at least one QMI service object is extracted
- DMS resolves to service id `2`
- service id `1` maps to WDS and is therefore deprioritized as the Wi-Fi
  firmware-control candidate
- WLFW remains unresolved unless an exported service object is found
- next step remains no-QMI-payload: an explicit-approval QRTR nameservice
  readback matrix or a WLFW service-object locator
