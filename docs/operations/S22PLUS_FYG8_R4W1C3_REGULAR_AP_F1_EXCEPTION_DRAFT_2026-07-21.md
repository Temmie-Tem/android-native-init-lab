# S22+ FYG8 R4W1-C3 Regular-Path F1 Exception Draft

State: `DRAFT_INACTIVE`

This document defines a possible successor to the consumed R4W1-C2 run. It is
not installed in `AGENTS.md`, grants no device authority, and cannot activate
itself. A separate source review, exact binding clause, commit, and fresh
operator acknowledgement are required before any connected or live action.

Policy marker: `S22+ FYG8 R4W1-C3 regular-path direct-PID1 boot-only F1 gate`

Prospective clause markers:
`BEGIN_S22PLUS_FYG8_R4W1C3_REGULAR_AP_F1_POLICY_V1` and
`END_S22PLUS_FYG8_R4W1C3_REGULAR_AP_F1_POLICY_V1`.

Prospective active sentinel:
`S22PLUS_FYG8_R4W1C3_REGULAR_AP_F1_POLICY_STATE=ACTIVE`

## Purpose

The qualified R4W1-C candidate remains byte-identical. R4W1-C2 failed before
Odin setup because Odin4 was given `/proc/self/fd/N` as its AP name and rejected
that name before transfer. C3 changes only the host transport: a checked direct
regular file remains open while Odin receives its real absolute `.tar.md5`
pathname. The candidate kernel, ramdisk, marker, rollback APs, and boot-only
scope do not change.

## Exact Sources

- live helper:
  `workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c3_regular_ap_live_gate.py`
  SHA256 `a936c2d2a1a563bbfa696ce203b03d5dfb9cd4c0077013f4c56959bc15ec1f60`
- live helper tests:
  `tests/test_s22plus_fyg8_r4w1c3_regular_ap_live_gate.py`
  SHA256 `aff9e7895a4ed0fcaa8edd86c88ddf831906720e96275466b59ea349536d318b`
- regular-path F1 transport:
  `workspace/public/src/scripts/revalidation/s22plus_boot_only_f1_transport.py`
  SHA256 `f6b38e8438af2b4a42c13b6414503addbe1f69128ed9219e4815d99acf79fba5`
- F1 transport tests:
  `tests/test_s22plus_boot_only_f1_transport.py`
  SHA256 `1fbc274895e449299960d76dabc4785cc18c395d7182a0e945e1970e2aee69d5`
- connected artifact/baseline gate:
  `workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c_connected_gate.py`
  SHA256 `fa4e9b0a77032fbb8b17affb2ae985b80c990b6e4b07c0ee095328cfd80516b9`
- retained USB/observer helper source:
  `workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1c_live_gate.py`
  SHA256 `ce39196e58c6e7be83e8e8bcf7b56cb46e0e4ef22c05c1251f58b3310aae57ff`

## Exact Artifacts

- candidate raw boot: size `100663296`, SHA256
  `1d394028714c48cfc0fd220acade9ead9a49ea21a81c59b2b87f88e61de704b0`
- candidate AP: size `27064361`, SHA256
  `85514e79e3400de30b7146606a9e86c3655fc7a8766daba5f054ae1bd54fd42f`
- Magisk rollback AP: size `23367721`, SHA256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
- cleanup-only stock AP: size `100669481`, SHA256
  `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`
- full FYG8 firmware evidence: size `9680091538`, SHA256
  `f831e5fb8abe1c7a9d8c38fe9c033a3fce7e77651776383641c385c2bb85a2c8`
- Odin4: size `3746744`, SHA256
  `6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b`

Every AP must contain exactly one regular `boot.img.lz4` member. No anonymous
`/proc/self/fd` path is allowed as the Odin executable or AP argument.

## Proposed F1 Sequence

1. Re-run the full R4W1-C host artifact checker and regular-path transport gate.
2. Require one exact normal FYG8 Android target, Magisk root, known boot,
   vendor_boot, DTBO, and recovery hashes, orange state, stopped boot animation,
   and no Odin endpoint.
3. Bind the Android USB serial hash and physical USB topology.
4. Request Download mode and require one stable exact Samsung `04e8:685d`
   endpoint on the same topology.
5. Durably and exclusively consume the one-shot exception before candidate
   transfer.
6. Transfer the exact candidate AP once using its real `.tar.md5` pathname.
7. Observe passively for at most 120 seconds. Candidate ADB is not required and
   passive time is not proof.
8. The attending operator physically enters Download mode for mandatory
   rollback. Require the same exact topology and one stable endpoint.
9. Transfer the exact Magisk AP. Only a definite Magisk transfer failure while
   the same endpoint remains may use the exact stock cleanup AP.
10. Require exact final Android/Magisk health and no Odin endpoint. Read
    `/proc/last_kmsg` twice to EOF and require byte identity and one accepted
    R4W1-B marker family record for PASS.

The canonical timeline is exactly `events:[{name,timestamp_utc}]` with, in
order, `live_session_start`, `candidate_flash_start`, `candidate_flash_done`,
`candidate_boot_ready`, `rollback_flash_start`, `rollback_flash_done`,
`rollback_boot_ready`, and `live_session_end`.

## Prospective Acknowledgements

- connected D0:
  `S22PLUS-FYG8-R4W1C3-CONNECTED-READ-ONLY-DRY-RUN`
- candidate F1:
  `S22PLUS-FYG8-R4W1C3-REGULAR-AP-DIRECT-PID1-LIVE`
- interrupted rollback:
  `S22PLUS-FYG8-R4W1C3-MAGISK-ROLLBACK-FROM-DOWNLOAD`

## Safety Boundary

The candidate and both rollback paths are boot-only. This draft authorizes no
device contact or transfer. A future installed exception may authorize only the
exact candidate once and the mandatory rollback chain. It must not authorize a
second candidate run, raw host `dd`, fastboot, recovery/vendor_boot/DTBO/vbmeta,
BL, CP, CSC, super, userdata, persist, EFS, sec_efs, RPMB, keymaster, modem,
bootloader, partition-table, qdl/Sahara/Firehose, RAM dump, EUD/UART write,
format, panic, SysRq, RDX command, fuse, or security-state action.

PASS can only be
`PASS_R4W1C3_DIRECT_PID1_EXEC_ACCEPTED_AND_ROLLED_BACK`. Candidate transfer
without exact marker proof is no-proof. Stock cleanup is non-PASS. Any missing
final Magisk health is non-PASS and leaves only the separately acknowledged
rollback-from-download path available.
