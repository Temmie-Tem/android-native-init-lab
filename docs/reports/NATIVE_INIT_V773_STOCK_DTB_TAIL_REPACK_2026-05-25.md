# Native Init V773 Stock DTB Tail Repack Report

## Result

- decision: `v773-stock-dtb-tail-diagnostic-boot-staged`
- pass: `true`
- runner: `scripts/revalidation/native_wifi_dtb_tail_repack_v773.py`
- evidence: `tmp/wifi/v773-stock-dtb-tail-repack/`
- staged boot image: `tmp/wifi/v773-stock-dtb-tail-repack/boot_linux_v773_icnss_diag_stockdtb.img`

## What Ran

```bash
python3 -m py_compile scripts/revalidation/native_wifi_dtb_tail_repack_v773.py
python3 scripts/revalidation/native_wifi_dtb_tail_repack_v773.py plan
python3 scripts/revalidation/native_wifi_dtb_tail_repack_v773.py run
```

## Evidence Summary

| Signal | Value |
| --- | --- |
| stock DTB tail size | `997113` bytes |
| combined kernel size | `49827629` bytes |
| combined FDT count | `3` |
| combined FDT offsets | `48830516`, `49327847`, `49827456` |
| combined `A90V765` markers | `19` |
| staged boot size | `53972992` bytes |
| staged boot sha256 | `0fcde6e76fd0de3d2b974aad20dcbbba714e5a81b9fccf5ea2b6a67bdc06f400` |
| staged boot mode | `0600` |
| native-init marker count | `1` |
| staged boot `A90V765` markers | `19` |
| unpacked kernel hash matches combined | `true` |

## Interpretation

V773 fixes the structural issue found by V772 at the artifact level: the local
diagnostic boot image now contains the instrumented kernel plus the stock v724
appended DTB tail. This does not prove live boot yet, but it removes the missing
DTB-tail cause that made V770 unsafe to retry.

## Safety

- device command: not executed
- partition write/flash/reboot: not executed
- Wi-Fi HAL/scan/connect/credential use: not executed
- DHCP/routes/external ping: not executed

## Next

Before any live flash, review V773 evidence and keep rollback target
`stage3/boot_linux_v724.img` ready. If a live V774 handoff is attempted, it
should flash only the V773 artifact, verify boot immediately, capture
`A90V765` dmesg around `boot_wlan`, and roll back on any boot-health failure.
