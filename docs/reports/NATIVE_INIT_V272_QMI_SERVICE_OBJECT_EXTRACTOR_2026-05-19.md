# Native Init v272 QMI Service Object Extractor Report

## Summary

- status: PASS
- boot image change: none
- device command: none
- QRTR/QMI packet transmission: none
- baseline device build: `A90 Linux init 0.9.60 (v261)`
- tool: `scripts/revalidation/wifi_qmi_service_object_extractor.py`
- evidence: `tmp/wifi/v272-qmi-service-object-extractor/`
- decision: `qmi-service-object-ids-extracted`

v272 parses local vendor ELF evidence and extracts QMI service ids from exported
`*_qmi_idl_service_object_vXX` data objects. It does not execute Android code,
open QRTR sockets, send QRTR nameservice packets, or send QMI payloads.

## Inputs

- v271 manifest: `tmp/wifi/v271-qrtr-service-selector/manifest.json`
- vendor export:
  `tmp/wifi/v226-vendor-root-live-export/vendor-source/`
- parsed ELF files:
  - `lib64/libqmiservices.so`
  - `bin/cnss-daemon`

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
```

Result:

```text
decision: qmi-service-object-ids-extracted
pass: True
reason: DMS service id extracted as 2 and service id 1 mapped to WDS; WLFW remains unresolved
```

## Key Checks

- `v271-ready`: PASS
- `libqmiservices-exists`: PASS
- `cnss-daemon-exists`: PASS
- `service-objects-extracted`: PASS, count `37`
- `dms-service-id-extracted`: PASS, DMS service id `2`
- `service-id-1-maps-to-wds`: PASS
- `wlfw-service-object-absent`: PASS as warning/unresolved classifier

## Candidate Resolution

| candidate | status | service id | interpretation |
| --- | --- | --- | --- |
| service `1`, instance `1` | deprioritized | `1` | maps to WDS in `libqmiservices.so`; v270 readback returned zero events |
| DMS | resolved | `2` | exported `dms_qmi_idl_service_object_v01` parsed successfully |
| WLFW | unresolved | none | `cnss-daemon` strings indicate WLFW, but no exported WLFW service object was found |
| WLAN | unresolved | none | WLAN strings exist, but no exported object was proven |

## Extracted Highlights

- WDS: service id `1`
- DMS: service id `2`
- NAS: service id `3`
- WDA: service id `26`
- LOWI: service id `56`
- total extracted service objects: `37`

The important correction is that v269/v270 service `1` was not a neutral or
Wi-Fi-specific selector; in current vendor evidence it corresponds to WDS. That
explains why service `1`, instance `1` is weak evidence for CNSS/WLFW bring-up.

## Guardrails Preserved

- host-only ELF parsing
- no Android code execution
- no device command executed
- no QRTR socket opened
- no QRTR nameservice packet sent
- no QMI payload sent
- no Wi-Fi scan/connect/link-up
- no credentials, DHCP, routing, or Internet-facing exposure
- no `cnss-daemon`, `cnss_diag`, HAL, supplicant, wificond, or hostapd start

## Next Step

v273 should either:

1. run an explicit-approval QRTR nameservice readback matrix for evidence-based
   known service ids such as DMS `2`, still with no QMI payloads, or
2. locate the WLFW service object from Android source or additional vendor
   blobs before any packet-based lookup.
