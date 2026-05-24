# Native Init V766 ICNSS/QCACLD Patch Apply Build-readiness Report

- date: `2026-05-25 KST`
- status: `pass`
- decision: `v766-patch-applied-defconfig-pass-toolchain-incomplete`
- runner: `scripts/revalidation/native_wifi_icnss_qcacld_patch_apply_build_v766.py`
- evidence: `tmp/wifi/v766-icnss-qcacld-patch-apply-build/`

## Summary

V766 found and fixed the first real V765 patch quality issue: the generated
diff format had to be patch-applicable, not just reviewable. After the V765
generator fix and patch regeneration, V766 safely extracted the Samsung OSRC
source to private evidence, applied the patch cleanly, verified all 19
`A90V765` markers, and ran `r3q_kor_single_defconfig` successfully.

No `kernel_build` mutation, full kernel build, boot image write, partition
write, device command, Wi-Fi HAL, scan/connect, credential use, DHCP/routes, or
external ping was executed.

## Results

| check | result |
| --- | --- |
| V765 input | pass; `v765-icnss-qcacld-log-patch-ready` |
| source archive | pass; `Kernel.tar.gz` present |
| safe extract | pass; required targets present |
| patch dry-run | pass |
| patch apply | pass |
| marker count | pass; `19` total |
| defconfig | pass; `r3q_kor_single_defconfig` rc `0` |
| Samsung toolchain path | warn; bundled GCC/clang paths absent |

Marker distribution:

| file | markers |
| --- | ---: |
| `drivers/soc/qcom/icnss_qmi.c` | 2 |
| `drivers/soc/qcom/icnss.c` | 5 |
| `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/src/pld_snoc.c` | 2 |
| `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_main.c` | 9 |
| `drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c` | 1 |

## Validation

Commands:

```text
python3 -m py_compile scripts/revalidation/native_wifi_icnss_qcacld_log_patch_v765.py scripts/revalidation/native_wifi_icnss_qcacld_patch_apply_build_v766.py
python3 scripts/revalidation/native_wifi_icnss_qcacld_log_patch_v765.py run
python3 scripts/revalidation/native_wifi_icnss_qcacld_patch_apply_build_v766.py run
```

Evidence logs:

- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/logs/patch-dry-run.txt`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/logs/patch-apply.txt`
- `tmp/wifi/v766-icnss-qcacld-patch-apply-build/logs/defconfig.txt`

## Interpretation

The instrumentation patch is now source-apply-ready and defconfig-ready. The
remaining host blocker before a full kernel build is toolchain selection:
Samsung's `build_kernel.sh` expects bundled Android GCC/clang paths that are not
present in the staged source tree. V767 should select or stage a compatible
toolchain and run a bounded full kernel build/package check. Boot image writing
and live flashing remain separate gates.
