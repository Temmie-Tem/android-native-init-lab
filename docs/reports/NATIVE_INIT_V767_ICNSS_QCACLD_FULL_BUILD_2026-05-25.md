# Native Init V767 ICNSS/QCACLD Full Build Gate Report

- date: `2026-05-25 KST`
- status: `pass-classified`
- decision: `v767-instrumented-objects-built-rkp-cfp-python2-blocked`
- runner: `scripts/revalidation/native_wifi_icnss_qcacld_full_build_v767.py`
- evidence: `tmp/wifi/v767-icnss-qcacld-full-build/`

## Summary

V767 advanced V766 from patch-apply/defconfig readiness to a real bounded
kernel build in the disposable OSRC source tree. The build compiled the
instrumented ICNSS/QCACLD target objects and preserved all 19 `A90V765` markers.

No `Image` was produced because the post-link `RKP_CFP` instrumentation step
invokes a Python2-only script, which fails under the current host Python path
with `SyntaxError: Missing parentheses in call to 'print'`.

No boot image write, partition write, flash, reboot, device command, Wi-Fi HAL,
scan/connect, credential use, DHCP/routes, or external ping was executed.

## Results

| check | result |
| --- | --- |
| V766 input | pass; `v766-patch-applied-defconfig-pass-toolchain-incomplete` |
| patch markers in source | pass; `19` |
| clang/libtinfo compatibility | pass |
| GCC wrapper/Python compatibility | pass |
| disposable ION UAPI header exposure | pass |
| disposable `techpack/audio` host-build path/header repair | pass |
| ICNSS/QCACLD instrumented object compile | pass |
| final kernel image | blocked by `scripts/rkp_cfp/instrument.py` Python2 syntax |

Instrumented object evidence:

| object | markers |
| --- | ---: |
| `out/drivers/soc/qcom/icnss_qmi.o` | 2 |
| `out/drivers/soc/qcom/icnss.o` | 5 |
| `out/drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/src/pld_snoc.o` | 2 |
| `out/drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.o` | 9 |
| `out/drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.o` | 1 |

## Validation

Commands:

```text
python3 -m py_compile scripts/revalidation/native_wifi_icnss_qcacld_full_build_v767.py
python3 scripts/revalidation/native_wifi_icnss_qcacld_full_build_v767.py run
```

Key evidence:

- `tmp/wifi/v767-icnss-qcacld-full-build/manifest.json`
- `tmp/wifi/v767-icnss-qcacld-full-build/summary.md`
- `tmp/wifi/v767-icnss-qcacld-full-build/logs/kernel-build.txt`

## Interpretation

The V765 patch has now passed source apply, defconfig, and target-object compile
coverage. The remaining blocker is not the ICNSS/QCACLD log patch; it is the
Samsung post-link `RKP_CFP` Python2 host compatibility step before final `Image`
packaging.

This does not solve the missing WLFW service `69` root cause. The next work
should stay split into two gates:

1. **Runtime root-cause branch**: classify why `mdm_helper`/esoc/mdm3 still does
   not advance WLAN-PD/WLFW despite service180/sysmon evidence.
2. **Instrumentation packaging branch**: decide whether to make `RKP_CFP`
   Python2-compatible, disable that post-link step for a diagnostic image, or
   provide a real Python2 runtime before any boot-image handoff.
