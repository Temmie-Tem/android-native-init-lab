# NATIVE_INIT V3407 — S22+ O1.1 seclabel host build

Date: 2026-07-10 04:17 KST / 2026-07-09 19:17 UTC

## Verdict

HOST BUILD PASS. O1.1 changes the O1 rc behavior by exactly one service option:

```rc
seclabel u:r:magisk:s0
```

No device action or flash occurred. O1.1 is not live-authorized by this result.

## Why This Is The Narrow Fix

V3406 retained `/proc/last_kmsg` proved that Magisk injected the O1 rc and
Android init ran its `sys.usb.configured=configured` action. Init rejected the
service before exec because the rootfs-overlay script had
`u:object_r:system_file:s0` and no transition from `u:r:init:s0`.

AOSP init's service contract states that `seclabel` selects the process context
before exec and is intended for rootfs services. Magisk v30.7's own generated
init actions execute its binary in `u:r:magisk:s0`. O1.1 therefore selects the
already-present Magisk domain without adding or changing a policy file.

References:

- [AOSP Android 15 init `seclabel`](https://android.googlesource.com/platform/system/core/+/refs/heads/android15-qpr2-s9-release/init/README.md)
- [Magisk root directory overlay guide](https://topjohnwu.github.io/Magisk/guides.html)
- Magisk v30.7 tag `e8a58776`, `native/src/init/rootdir.rs`

## Exact Delta

The O1.1 builder compares the rc bodies after comments and trailing blank-line
normalization. It requires:

```text
base=workspace/public/src/android/s22plus_o1_control.rc
candidate=workspace/public/src/android/s22plus_o11_control.rc
added_service_option=seclabel u:r:magisk:s0
other_behavioral_delta=false
seclabel_count=1
```

The property trigger, service name/path, class, uid/groups, disabled/oneshot
options, wrapper, daemon, and every runtime parameter are unchanged.

## Preservation Gates

```text
known-good base boot
  2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e
kernel before=after
  bceca73edbfca3499148e16741c939779157925949ef6bc8a8e31d6b68fc2cff
Magisk /init before=after
  383670a7ba3a6a4b79e5f3467e1da4b66a5df66a9b356ab9f70916854dd6b468
O1 service unchanged
  3e5c000308acaa52495c1b235b9f3e777123e3ddeb1e51f01b7461a38593be93
O0 daemon unchanged
  a82cd32f83afc20d40fc74a9402896ae07378811f259913ed6df7cbc540f858c
```

The no-change MagiskBoot repack remains byte-identical to the known-good base.
Ramdisk listing comparison still shows exactly three additions and no removal
or replacement. The only changed added-file content is the rc above.

Safety manifest remains:

```text
boot_only=true
live_flash_authorized=false
stock_first_stage_preserved=true
stock_magisk_init_preserved=true
kernel_preserved=true
service_seclabel=u:r:magisk:s0
selinux_policy_file_change=false
active_gadget_change=false
configfs_write=false
sysfs_write=false
module_insertions=false
persistent_partition_mount=false
reboot_request=false
```

## Artifacts

```text
output=workspace/private/outputs/s22plus_native_init/o11_magisk_overlay_v0_1
rc_sha256=36363a0c6aedbd901310ac5de7bcdd9b85c2a2f985f92a0d78d86daefef8503b
boot.img_sha256=1e59b172edda0d2c717a93021c9084af1393c0c4db7d28eeb10e06c0b1787b0d
boot.img.lz4_sha256=afef7ff56c7efd54cbb094b1a36bc8068cb3c780ccc8e2667baee9493c6ca6e6
AP.tar_sha256=a139942a34fed32f4017a3c875f71f4df5a9ea70a3ffa2925cfcdb0207132706
AP.tar.md5_sha256=c43eeb83cedb2db3e0758de71050ef2960765740face7378fcc285a5b8188730
tar_members=[boot.img.lz4]
```

Odin invalid-device parsing accepted the AP and failed only on the deliberately
nonexistent USB endpoint.

## Validation

```text
python py_compile: PASS
git diff --check: PASS
combined O0/O1/O1.1 tests: Ran 28, OK
exact one-line rc behavior comparator: PASS
full O1 inherited build/preservation gates: PASS
O1.1 manifest validation: PASS
boot-only Odin tar membership: PASS
```

Tracked files:

- `workspace/public/src/android/s22plus_o11_control.rc`
- `workspace/public/src/scripts/revalidation/build_s22plus_o11_magisk_overlay.py`
- `tests/test_build_s22plus_o11_magisk_overlay.py`

## Next

Prepare an O1.1-specific default-dry-run live helper. Besides pinning the new
artifact, it should retain the O1 protocol and postflight gates, retry
`adb reboot download` only after a bounded transport reconnect check, and
collect `/proc/last_kmsg` automatically after rollback. Only after helper tests,
connected dry-run, a fresh SHA-pinned one-shot exception, and new operator
approval may O1.1 be flashed.
