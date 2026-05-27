# Native Init V1144 eSoC Wait Ioctl Contract Report

Date: `2026-05-27`

## Result

- Decision: `v1144-post-pm-esoc-wait-ioctl-contract-classified`
- Pass: `true`
- Runner: `scripts/revalidation/native_wifi_esoc_wait_ioctl_contract_v1144.py`
- Manifest: `tmp/wifi/v1144-esoc-wait-ioctl-contract/manifest.json`
- Summary: `tmp/wifi/v1144-esoc-wait-ioctl-contract/summary.md`

## Summary

V1144 is host-only. It consumes V1143 lower-trace evidence and Samsung eSoC
headers/source references. It performs no live ioctl, no eSoC/subsys node open,
and no Wi-Fi action.

The V1143 worker syscall:

```text
ioctl fd=3 request=0x8004cc02
```

decodes to:

```text
_IOR(0xcc, 2, unsigned int) = ESOC_WAIT_FOR_REQ
```

So the current post-PM `mdm_helper` state is not a direct MDM3 power-on or
MHI/`ks` progression. It is waiting on the eSoC request-engine FIFO behind
`/dev/esoc-0`.

## Evidence

| evidence | result |
| --- | --- |
| V1143 decision | `v1143-post-pm-lower-trace-no-advance` |
| lower-trace samples | `3` |
| `mdm_helper` fd `/dev/esoc-0` | `1` in every sample |
| `mdm_helper` fd `/dev/subsys_esoc0` | `0` in every sample |
| MHI pipe fd | `0` in every sample |
| `/vendor/bin/ks` | `0` in every sample |
| worker `wchan` | `esoc_dev_ioctl` |
| ioctl request | `0x8004cc02` |
| decoded symbol | `ESOC_WAIT_FOR_REQ` |
| `mdm3` | still `OFFLINING` |
| WLFW/service69/BDF/wlan0 | not observed |

## Contract

Samsung eSoC source/header mapping:

| path | meaning |
| --- | --- |
| `include/uapi/linux/esoc_ctrl.h` | `ESOC_WAIT_FOR_REQ` is `_IOR(ESOC_CODE, 2, unsigned int)`; `ESOC_REQ_IMG = 1` |
| `drivers/esoc/esoc_dev.c` | `ESOC_WAIT_FOR_REQ` waits for a request event and copies an unsigned int to userspace |
| `drivers/esoc/esoc_bus.c` | lower driver paths queue eSoC requests into the request engine |
| `drivers/esoc/esoc-mdm-pon.c` | PON paths can queue `ESOC_REQ_IMG` |
| `drivers/esoc/esoc-mdm-4x.c` | `ESOC_IMG_XFER_DONE` starts post-image status waiting; it is not itself MDM2AP readiness |
| `include/linux/esoc_client.h` | MHI/CNSS client hooks exist after eSoC power-on progression |

Historical evidence is consistent:

- V884/V885: after request-engine registration, `/dev/subsys_esoc0` caused
  `ESOC_WAIT_FOR_REQ` to return `rc=4`, `value=1`, i.e. `ESOC_REQ_IMG`.
- V891/V893: sending `ESOC_IMG_XFER_DONE` alone did not make status ready.
- V896: Android has an additional `mdm_helper`/`ks`/MHI image-link contract.
- V1020: blind `/dev/subsys_esoc0` open can block in `sdx50m_toggle_soft_reset`
  and require cleanup reboot.

## Interpretation

The obsolete branch remains closed:

```text
V1071 pm-service exit255 / BPF-uProbe path
```

The active branch is now:

```text
post-policy PM/CNSS register/connect OK
  -> mdm_helper opens /dev/esoc-0
  -> worker waits in ESOC_WAIT_FOR_REQ
  -> no /dev/subsys_esoc0, MHI pipe, ks, mdm3 ONLINE, WLFW, or wlan0
```

This means another live retry should not blindly open `/dev/subsys_esoc0` or
blindly notify `ESOC_IMG_XFER_DONE`. The next unit should reconstruct the
Android `mdm_helper`/`ks`/MHI image-link contract first, then design a
fail-closed verifier for native.

## Safety

- Device commands executed: `false`
- Live eSoC/subsys/ioctl retry: `false`
- Wi-Fi HAL start: `false`
- Scan/connect/link-up: `false`
- Credential use: `false`
- DHCP/route: `false`
- External ping: `false`
- Boot image/partition write/flash: `false`

## Validation

Executed:

```bash
python3 -m py_compile scripts/revalidation/native_wifi_esoc_wait_ioctl_contract_v1144.py
python3 scripts/revalidation/native_wifi_esoc_wait_ioctl_contract_v1144.py
```

## Next

V1145 should be host-only first: compare Android `mdm_helper`/`ks`/MHI
image-link behavior against native, identify the exact image source and eSoC
notification sequence, and only then plan a bounded live gate.
