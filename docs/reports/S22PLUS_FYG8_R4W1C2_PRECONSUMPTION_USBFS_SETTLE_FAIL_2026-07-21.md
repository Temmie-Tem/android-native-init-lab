# S22+ FYG8 R4W1-C2 Pre-Consumption USBFS Settle Failure

Date: 2026-07-21 KST

## Verdict

`FAIL_R4W1C2_PRECONSUMPTION_NO_CANDIDATE_FLASH`

The first R4W1-C2 live entry failed closed after exact Android preflight and
normal Download entry but before candidate consumption or transfer. This is a
live-gate implementation failure, not a candidate boot or flash failure.

## Exact Evidence

- Run:
  `workspace/private/runs/s22plus-r4w1c2-measured-live-20260720T162342Z`.
- Result SHA256:
  `32c88db20413246a034913f87366a8554bb8242891c74b2608f839d39abfafc3`.
- Timeline SHA256:
  `54a534c600427a0aaff742b191ebe2d2ac8397271aad6cedebadc643acc4d52f`.
- Connected preflight SHA256:
  `95e0bac1e71d7e8232954564674b892f347af5c2ad8c5d00f2f25e82571647a5`.
- Error: `bound Download measured identity is unavailable`.
- `candidate_transfer_attempted=false` and `candidate_transfer_ok=false`.
- The timeline contains only `live_session_start` and `live_session_end`.
- The unique R4W1-C2 consumed-state path remains absent.

The connected preflight proved exact `SM-S906N` / `g0q` /
`S906NKSS7FYG8`, completed boot, stopped boot animation, orange state, Magisk
root, known Magisk boot, stock vendor_boot/DTBO/recovery, live retained-log
binding, clean duplicate observers, absent pstore consoles, and no Odin
endpoint. The Android USB binding was exact serial `DEVICE-S22P-01`, topology
`2-1.3`, and required absent Download serial state.

## Failure Mechanism

Normal Download appeared at the bound topology as Samsung `04e8:685d`, exact
product `SAMSUNG USB`, manufacturer `Samsung`, and no serial. The direct node
was `/dev/bus/usb/002/024`.

The first `snapshot_node()` ran while udev was still applying initial usbfs node
metadata. Its before/after identity comparison therefore raised
`usbfs endpoint changed during snapshot`. `bound_download_node_sample()`
collapsed that specific settle race into the generic fatal measured-identity
error, and `wait_for_stable_download_node()` had no transient-initial-sample
path.

After settlement, the same exact node produced a valid snapshot and immutable
identity `usbfs-immutable-v1:77cd1330...bb9b8b1`. Static inspection then found a
second latent contract defect: `bound_download_node_sample()` returns this
`immutable_identity`, but the stabilization loop required a node dictionary
containing only `st_dev`, `st_ino`, `st_rdev`, and `st_ctime_ns`. A retry with
the old bytes would therefore fail even after the first race disappeared.

## Recovery

No AP image argument or partition payload was supplied. The exact current
Download endpoint was returned to normal mode with:

`/usr/bin/odin4 --reboot -d /dev/bus/usb/002/024`

Post-return read-only checks proved exact FYG8 model/device/bootloader/build,
`sys.boot_completed=1`, `init.svc.bootanim=stopped`, orange verified boot, and
Magisk `uid=0(root)`. No candidate transfer or rollback image was needed.

## Repair

The corrected helper:

- classifies only the exact initial snapshot-change condition as transient;
- retries it only before the first complete sample;
- treats the same condition after stabilization begins as fatal;
- requires `immutable_identity` in every complete sample;
- validates its exact prefix and digest shape; and
- includes it in replacement detection alongside device, inode, and rdev.

Focused tests cover the observed initial race, late-race rejection, missing
digest rejection, inode replacement, and digest-only replacement. The focused
suite passes `60/60`; the related live, binding, transition, USBFS, and connected
suite passes `162/162`.

New source identities before rebinding:

- helper: size `111396`, SHA256
  `22cba55a924e9c56e5d245114357921ebefc73460a673e40e22c7ecf2e145172`;
- focused test: size `92470`, SHA256
  `9ba6da5d1e72e030e3648297491dc8c745b33607b0ea08a37478eb2787c9cbdb`.

The prior active clause no longer matches the changed source and therefore
cannot authorize a retry. A new exact binding, independent review, policy
reactivation, post-activation offline check, and fresh acknowledgement are
required.
