# S20+ G986N TWRP T1 live result

Date: 2026-08-31
Target: `SM-G986N/y2q/y2qksx/G986NKSS8IYC2`
Status: **NO_PROOF - EXACT STOCK RECOVERY RESTORED AND HEALTHY**

## Result

The attended T1 run consumed exactly one candidate recovery-only transfer and
one exact-stock recovery-only rollback transfer. Both transfers are proved.
The terminal is 2,144 bytes at SHA-256
`9475e2cd6f283c7390b0d4b86b5e5208f0e943b2b452439febbe1dc3ca82cd7f`
and reports `NO_PROOF_T1_RETURNED_STOCK_RECOVERY_HEALTHY`. Candidate and
rollback replay are both false. All other partition transfers, S22+ commands,
A90 commands, and other-target commands are zero.

Final health proves a fresh healthy rooted IYC2 Android boot and the exact
82,694,144-byte stock recovery at SHA-256
`dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e`.

## Discriminating observation

The attended key choreography reached the transferred recovery and its ADB
endpoint. The fixed observer returned root UID, TWRP
`3.7.1_12-AstroForge_v2`, donor incremental, `ro.secure=0`,
`ro.debuggable=1`, running adbd, and the exact T1 marker SHA-256. The sole
fixed-field difference was `sys.usb.config=mtp,adb`; T1 had predeclared only
`adb` as acceptable.

The 271-byte raw observer stdout is retained privately at SHA-256
`c2c8b4e7393153ff40e1ca3487b76d8c345e1c2816636a6f30913e9d27baf0cc`.
Its 546-byte raw-capture receipt is SHA-256
`bbd780281ffccf7991ad4a5b10c4ba063be9bc690422699b75a9b033159d024b`.
The resulting 336-byte immutable observation is SHA-256
`c2c1d123d1f26a2416252fc5da8c576efbb0bf2bd9527c2b2fcebd3529204e74`.
These retained bytes support a corrected future observer but do not relabel
T1: its journal correctly remains `NO_PROOF` and its candidate is permanently
consumed.

## Recovery note and next boundary

The first post-rollback finalizer read reached ADB before Android published the
complete healthy public tuple and stopped before any durable final-health,
recovery-read, or terminal effect. The reviewed terminal-only resume path then
performed fresh bounded health reads, proved stock recovery, and closed the
run without replaying either transfer.

A future T2 must use a byte-distinct candidate and marker, require this complete
T1 terminal and private raw observation as predecessor evidence, accept only
the observed `mtp,adb` property alongside the same exact root/version/marker
closure, and receive independent dormant and activation review. This report
grants no T2 device command or standing approval.
