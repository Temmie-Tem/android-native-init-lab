# V3414 S22+ O3 Minimal-ACM Live Result

## Verdict

`O3 FAIL; ROLLBACK PASS; PHASE UNVERIFIABLE`. The exact candidate AP flashed
boot-only and left Odin, but the required O3 ACM control endpoint did not
appear within 120 seconds. No roundtrip or `O3 STATUS` response occurred, so
O3 is not promoted. The one-shot exception is consumed.

## Run

```text
workspace/private/runs/s22plus_o3_minimal_acm_live_gate_20260709T203740Z
```

```text
candidate_ap_sha256=41b7e32424a809cec6ac7bded281b9ac355a9f3d2d0a3727f8b02de6d1e757f7
candidate_boot_sha256=4f4a073f79b47c0a6a3924fabf09b2389c62bb731ed3355ebb83e48c53868609
result=candidate-proof-failed
rc=9
error=O3 ACM tty with exact serial did not appear
roundtrip=null
status=null
```

The operator observed that the device did not enter a bootloop. That is useful
survival evidence, but it is not USB control proof and does not identify the
runtime phase.

## Host Observation

The original candidate Odin endpoint disconnected at `20:38:04Z`. From then
until manual Download appeared at `20:41:21Z`, the continuous udev and kernel
journal observers recorded no new candidate USB device, CDC ACM interface, or
tty. This excludes a helper-side serial filter mismatch as the explanation for
the miss: the device did not enumerate under another visible candidate USB
identity during that window.

`candidate_boot_ready` was deliberately not recorded. The canonical timeline
contains the seven events that actually occurred:

```text
live_session_start
candidate_flash_start
candidate_flash_done
rollback_flash_start
rollback_flash_done
rollback_boot_ready
live_session_end
```

It is marked incomplete rather than fabricating the missing boot-ready phase.

## Rollback

After the helper requested attended recovery, the operator entered Download
mode. The helper restored the pinned Magisk boot-only AP successfully and
proved:

```text
rollback_target=magisk
rollback_rc=0
android_restored=true
boot_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
root=uid=0 context=u:r:magisk:s0
boot_completed=1
stability_samples=4/4 pass
```

The device ended on the known rooted Android baseline.

## Retained Evidence

The helper collected an empty pstore set and 2,097,136 bytes from
`/proc/last_kmsg`. Neither contained `S22_NATIVE_INIT_O3_MINIMAL_ACM` or the O3
control marker. The retained file contains prior Android shutdown and Samsung
bootloader material, but no reliable candidate phase marker. Therefore it
cannot distinguish these possibilities:

- the replacement `/init` did not reach `main`;
- minimum filesystem setup failed before a usable kmsg/pmsg path;
- the init reached a later module/gate failure but its userspace marker was not
  retained by this reset path.

The result is `UNVERIFIABLE`, not an inferred module or bind-gate failure.

## Next Unit

Do not repeat this AP or widen its module list. O3 introduced one large runtime
delta relative to the previously survival-proven direct-PID1 line: both O3
binaries use static glibc startup, while M31B/M34 used freestanding raw-syscall
entry. The next unit is host-only:

1. Diff the O3 earliest startup/filesystem path against the proven M31B/M34
   freestanding entry.
2. Move O3 PID1 back to a no-libc raw-syscall runtime while retaining the same
   59-module plan, eight gates, generic ACM behavior, and fail-closed status
   contract.
3. Add an earliest possible observation boundary before module loading and
   separately prove the generated ramdisk entry/ELF execution contract.
4. Build and review a new artifact. Any new live run requires a new exact
   one-shot exception.
