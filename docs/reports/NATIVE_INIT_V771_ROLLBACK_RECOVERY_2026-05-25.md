# Native Init V771 Rollback Recovery Report

## Result

- decision: `v771-rollback-v724-recovered`
- pass: `true`
- evidence: `tmp/wifi/v771-rollback-v724-20260525-014803/`
- rollback image: `stage3/boot_linux_v724.img`

## What Ran

```bash
python3 scripts/revalidation/native_init_flash.py \
  stage3/boot_linux_v724.img \
  --expect-version 'A90 Linux init 0.9.68 (v724)' \
  --verify-protocol auto
```

## Evidence Summary

| Signal | Value |
| --- | --- |
| rollback image sha256 | `4ca72f17aec64153d49def4ad42a49714d27bd833623aa9423220ce2181fc682` |
| adb recovery reached | yes, `RFCM90CFWXA recovery` |
| adb push to TWRP | pass |
| remote image sha256 | matched local |
| boot partition prefix sha256 | matched local |
| native verify | `version/status rc=0 status=ok` |
| bootstatus | `BOOT OK shell 4.1s` |
| selftest | `pass=11 warn=1 fail=0` |
| runtime storage | SD backend mounted read-write |
| USB state after recovery | Samsung Android `04e8:6861` |

## Interpretation

The V771 boot failure was recovered by flashing the known-good v724 native-init
boot image from TWRP. Native init is healthy again, with bridge command framing,
bootstatus, selftest, and status all passing.

The V770 diagnostic image remains unsafe to retry as-is. Any further custom
kernel flash must first explain why the OSRC-built instrumented kernel entered
Download mode after a successful boot partition write.

## Safety State

- rollback completed: yes
- native health: pass
- Wi-Fi scan/connect: not executed
- credential use: not executed
- DHCP/routes/external ping: not executed

## Next

V772 should be host-only. Compare the stock/v724 kernel payload and the V769
OSRC-built `Image-dtb` before any more live flashing. The next live gate should
only be considered after a classifier explains the boot incompatibility or
selects a safer non-kernel instrumentation path.
