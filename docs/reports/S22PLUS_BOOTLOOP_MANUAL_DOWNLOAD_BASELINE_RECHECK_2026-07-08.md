# S22+ Bootloop Manual Download Baseline Recheck (2026-07-08)

## Verdict

RECOVERED / BASELINE VERIFIED.

The operator reported another bootloop observation followed by manual download
mode entry. Host follow-up found the device already back in normal Android over
ADB. No Odin transfer, flash, rollback flash, reboot command, or partition write
was performed in this recheck.

## Current Device State

Captured at approximately `2026-07-08 03:13 KST`.

Read-only host observations:

```text
model=SM-S906N
device=g0q
build=AP3A.240905.015.A2.S906NKSS7FYG8
sys.boot_completed=1
ro.boot.verifiedbootstate=orange
ro.boot.boot_recovery=0
ro.boot.bootreason=reboot,download
Magisk root: uid=0(root) context=u:r:magisk:s0
```

Current partition hashes:

```text
boot        2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
vendor_boot 096e433e049fb088cd956e083d5a1039b33cdf0ca907e713bba7feaaf1b080b7
recovery    153373cd6c1efda2a9b57f91fac761ff92d515ae604cd3d22f97877759e51f18
```

Interpretation:

- `boot` matches the pinned Magisk boot baseline.
- `vendor_boot` matches stock FYG8 vendor_boot.
- `recovery` was not changed or relied on in this recheck.

The earlier empty block-device SHA attempt was a bad host command shape: the
actual direct device-side `sha256sum /dev/block/by-name/...` reads succeeded.

## Log Surface

```text
/sys/fs/pstore file count: 0
/proc/last_kmsg: missing in the current Android boot
```

So this recheck confirms recovery state, not root cause. There is still no
kernel-console evidence explaining the native-init bootloop/reset path.

## Operational Decision

Treat the operator bootloop/manual-download report as a no-proof failure shape.
Do not run additional blind native-init boot candidates from this state.

The active forward path remains the observability steer: get reliable kernel
console capture first, starting with the already built but not live-authorized
ramoops `vendor_boot` host candidate. That candidate still requires a separate
SHA-pinned live exception and a decision on the `magiskboot repack -n` drift
before any vendor_boot flash.
