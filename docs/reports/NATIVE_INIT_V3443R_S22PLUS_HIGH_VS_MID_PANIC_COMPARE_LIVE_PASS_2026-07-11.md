# Native-init V3443R S22+ HIGH versus MID Panic Comparison Live Pass

Date: 2026-07-11 KST

## Verdict

`PASS_HIGH_RDX_NEGATIVE_ACK_CORE_EQUIVALENT_AND_MID_RESTORED_WITH_HOST_CONTINUATION`

HIGH does not unlock this retail S22+ RDX path and did not increase the core
Samsung sec_debug panic record in this controlled comparison. HIGH does enable
some additional Android debug producers, which is a separate, narrower effect.

## Live Sequence

1. Exact MID `18765` / `0x494d` Android/Magisk baseline and all partition hashes
   passed.
2. Quoted `id; id` control returned two root lines and no shell UID.
3. Exact HIGH returned as `18760` / `0x4948` with unchanged boot, DTBO, and
   recovery hashes.
4. One run-bound marker and one SysRq panic executed. ADB disappeared and exact
   Samsung RDX `04e8:685d` enumerated.
5. The helper sent only `PrEaMbLe\0`. It received exact 15-byte
   `NeGaTiVeAcKmNt\0`, SHA256
   `3a4a3980e7835ebb77c927b99863e01847086171bdb81773e81e06f2192ab60c`.
   Probe and data transfer remained false.
6. After physical RDX EXIT, HIGH Android returned and `/proc/last_kmsg` was
   captured before MID restoration.
7. The exact setter dispatched MID once. A host parser observed a transient
   empty partition-hash output during partial boot and raised `IndexError`.
   Read-only continuation then proved final MID and all exact identities.

No candidate or rollback flash occurred.

## Retained Evidence

Private run:
`workspace/private/runs/s22plus_v3443r_high_panic_20260711T015902Z/`

```text
HIGH last_kmsg bytes    2097136
HIGH last_kmsg lines    19679
HIGH last_kmsg SHA256   7791a811db90cf4fa145fa44756d941d3e6efd6ead6229a8ce7ed1433aff0574
marker uptime           26.084243 s
marker                  1
SysRq panic             1
RDX is locked           1
upload cause            1
```

The MID control used the same fixed 2 MiB ring but panicked at uptime
`1683.710701s`. Whole-ring counts are therefore not directly comparable: HIGH
still retained early boot and module-loader messages that MID had overwritten.
That explains the misleading whole-ring deltas `ramdump +39`, `rst_exinfo +8`,
and `sec_debug +1`.

## Marker-forward Comparison

Restricting each log to its current-run marker and everything after it removes
the boot-age bias:

| Metric | MID | HIGH | Delta |
|---|---:|---:|---:|
| Segment bytes | 171750 | 176286 | +4536 |
| Segment lines | 3177 | 3246 | +69 |
| `ramdump` | 15 | 15 | 0 |
| `minidump` | 3 | 3 | 0 |
| `sec_debug` | 1 | 1 | 0 |
| `rst_exinfo` | 0 | 0 | 0 |
| `RDX is locked` | 1 | 1 | 0 |
| kernel-panic upload cause | 1 | 1 | 0 |
| SysRq panic | 1 | 1 | 0 |

The remaining byte/line difference comes from runtime-dependent task, CPU,
stack, fuel-gauge, and bootloader diagnostics. It is not an additional HIGH
debug channel. Every selected capability signature is equal.

## RDX Security Result

MID and HIGH returned the same response bytes and response hash. HIGH therefore
does not override the LCS PROD S-Boot token/lock gate on this device. No
`PrObE`, `DaTaXfEr`, range, qdl, Sahara, Firehose, or RAM transfer occurred.

## What HIGH Actually Adds

Read-only inspection of the live FYG8 init rules shows a smaller Android-side
difference:

- MID sets `persist.nfc.debug_enabled=true`; HIGH additionally sets
  `persist.nfc.vendor_debug_enabled=true`.
- MID and HIGH both set `debug.enable=true`,
  `libc.debug.pthread.lock_owner=1`, and create `/data/log/core` mode 0777.
- HIGH additionally sets `persist.systemserver.sa_bindertracker=true`; MID and
  LOW explicitly clear that property.
- Modem SSR restart policy contains equivalent MID and HIGH branches for the
  same CP debug level.

Thus HIGH can produce additional NFC vendor and system_server Binder diagnostic
logs during extended Android operation. It did not expand the panic/RDX capture
surface measured here.

## Final State

```text
debug_level          18765
ro.boot.debug_level  0x494d
Android/root         PASS
boot SHA256          2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
DTBO SHA256          97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c
recovery SHA256      93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4
```

The timeline contains exactly the eight standard events. V3443R is consumed and
retired. The post-live helper fix converts transient empty partition SHA output
into a caught `GateError`, allowing `wait_android_mid()` to continue polling;
the maintained shared V3442 helper SHA256 is
`9af60450ea255b963a4bab1b70e2ff5638c0a229245b08c994becc5df76f3e66`.
It does not authorize another run.
