# NATIVE_INIT V3404 — S22+ O1 Magisk overlay host build

Date: 2026-07-10 03:47 KST / 2026-07-09 18:47 UTC

## Verdict

HOST BUILD PASS. O1 now has a reproducible boot-only artifact that preserves the
known-good FYG8 Magisk kernel and `/init` while adding exactly three Magisk
`overlay.d` entries. No device action, reboot, or flash occurred in V3404.

This result prepares, but does not authorize, an O1 live run. A new SHA-pinned
`AGENTS.md` boot-only exception and checked live helper are still required.

## Discriminator

O1 asks one question: can the already-proven O0 framed tty protocol start during
normal Android early boot while stock first-stage module loading and the stock
USB gadget remain responsible for hardware bring-up?

The candidate therefore does not test native DWC3/configfs/module bring-up. It
removes those variables from the experiment.

## Construction

Base image:

```text
path=workspace/private/outputs/s22plus_magisk_root_boot_only/boot.img
sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
size=100663296
```

Pinned `magiskboot`:

```text
sha256=a18ecbd7981179494b7d281453d6c4e25b5c719e7d2ef7f6eba3c6be3043c58e
```

The builder first performs a no-change unpack/repack probe. Its output SHA is
identical to the base boot SHA. It then adds only:

```text
overlay.d/s22plus_o1_control.rc                    0644
overlay.d/sbin/s22plus_o1_service.sh              0750
overlay.d/sbin/s22plus_o1_tty_echo                0750
```

Parsed ramdisk listing comparison proves `added` equals those three paths,
`removed=[]`, and all three modes match. The builder extracts every added entry
and verifies its SHA against the source artifact. It also extracts `/init`
before and after the patch and again from the final repacked boot.

Preservation evidence:

```text
nochange_repack_sha256=2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel_before=kernel_after=bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
init_before=init_after=383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468
ramdisk_test_before_rc=1
ramdisk_test_after_rc=1
```

## Runtime Contract

The overlay rc waits for `sys.usb.configured=configured` and starts one disabled,
oneshot wrapper service. The rc itself does not stop `DR-daemon`; failed wrapper
execution therefore leaves stock tty ownership unchanged.

The wrapper:

1. requires the daemon executable and `/dev/ttyGS0`;
2. requires `DR-daemon` running and `ddexe` owning ttyGS0;
3. creates a `/dev` one-shot marker only after those prerequisites pass;
4. stops `DR-daemon` and requires stopped/no `ddexe` owner;
5. runs the O0 daemon for at most 128 requests with a 180-second idle timeout;
6. restores and revalidates `DR-daemon` on normal completion and signal exit.

It records `phase=started|handoff|daemon-running` and final line-oriented
`result=pass|fail|aborted`, `daemon_rc=...`, and `restore_rc=...` fields only in
`/dev/.s22plus_o1_status`. This volatile evidence is available to the postflight
ADB check without mounting or writing persistent storage.

The service script contains no configfs/sysfs write, module insertion, reboot,
block write, or persistent partition mount.

## Artifacts

```text
boot.img
  sha256=df7a166752f78aa07bea10aef53de1ba2737abf43bb041fe01738cce36113070
  size=100663296
boot.img.lz4
  sha256=26af084cca0cf23525e8786a50a49b270d60ae7b2fa7f4ed8d652bc9e102bb21
AP.tar
  sha256=457f14165087786926dda0aa64d354419e56fee3f6a9b547db9687eaf08c5a7b
AP.tar.md5
  sha256=388d35c12e9f5024f053837444da46254db6a6177c046400549148e24eaeec29
  members=[boot.img.lz4]
O0 daemon
  sha256=a82cd32f83afc20d40fc74a9402896ae07378811f259913ed6df7cbc540f858c
```

Private output root:

```text
workspace/private/outputs/s22plus_native_init/o1_magisk_overlay_v0_1
```

Odin invalid-device parsing reached the AP file check and failed only on the
deliberately nonexistent `/dev/bus/usb/999/999` endpoint.

## Validation

```text
python py_compile: PASS
bash -n service script: PASS
git diff --check: PASS
O0+O1 unit tests: Ran 18, OK
AArch64 static daemon build: PASS
no-change MagiskBoot repack: byte-identical PASS
ramdisk exact listing delta: PASS
kernel and /init preservation: PASS
boot-only Odin tar membership: PASS
```

Tracked implementation:

- `workspace/public/src/android/s22plus_o1_control.rc`
- `workspace/public/src/android/s22plus_o1_service.sh`
- `workspace/public/src/scripts/revalidation/build_s22plus_o1_magisk_overlay.py`
- `tests/test_build_s22plus_o1_magisk_overlay.py`

## Next

Create a fresh narrow O1 boot-only live exception pinned to the artifact hashes
above. The live helper must preflight the known Android/Magisk baseline and both
rollback APs, observe candidate disconnect/re-enumeration continuously, run the
O0 framed protocol during the bounded service window, prove `DR-daemon`
restoration, then return to the pinned Magisk boot baseline. Failure must stop at
the recovery boundary rather than widening into USB/module experiments.
