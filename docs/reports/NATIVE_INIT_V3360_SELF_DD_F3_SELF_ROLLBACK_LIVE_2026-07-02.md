# Native Init V3360 Self-dd F3 Self Rollback Live

- Cycle: `V3360`
- Decision: `v3360-self-dd-f3-self-rollback-live-pass`
- Parent writer: V3359 `A90 Linux init 0.11.122 (v3359-self-dd-f2-boot-candidate)`
- Self-written candidate: V3360 `A90 Linux init 0.11.123 (v3360-self-dd-f3-self-rollback)`
- V3360 boot SHA256: `2989c292d1a7ae7cd5f9eb78906b2451d717e4221b9c9b76114ddc9054b52a29`
- Rollback target: v2321 `A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)`
- Rollback target SHA256: `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- Policy gate: `AGENTS.md` + design §12.1 amended in commit `c4280620` for V3360 F3 only.
- Private run log: `workspace/private/runs/self-dd-v3360-f3-live-20260702T112752Z/`
- Final state: self-rolled back to `v2321-usb-clean-identity-rodata`, final `selftest fail=0`.

## Gate

- Rollback images were present and SHA-confirmed before the parent flash: v2321, v2237, and v48.
- Pre-flash resident was v2321 with `selftest fail=0` and pstore entries `0`.
- V3360 and v2321 were staged in the approved SD root:
  `/mnt/sdext/a90/flash-staging/`.
- Device-side staged SHA checks matched:
  - V3360:
    `2989c292d1a7ae7cd5f9eb78906b2451d717e4221b9c9b76114ddc9054b52a29`
  - v2321:
    `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`
- V3359 parent was flashed only through `native_init_flash.py`; pushed-image and boot readback SHA
  matched `4f51a7a325c014b80571fd1f8982f0510c48ea8b7c666721d4667a54626fd8c9`.
- V3359 boot verification used raw version fallback after the helper missed a cmdv1 END marker, then
  the bridge was restarted and normal cmdv1 health passed:
  `0.11.122 build=v3359-self-dd-f2-boot-candidate`, `selftest fail=0`, pstore entries `0`.

## Parent F2 To V3360

V3359 first ran F0 against the staged V3360 image and returned:

```text
A90BWF0 before_full_sha=60544a9ceadf1457535ffa5d51c7510a8fba8eab695433c1dfce55aad96917b3
A90BWF0 candidate_sha=2989c292d1a7ae7cd5f9eb78906b2451d717e4221b9c9b76114ddc9054b52a29 expected_sha_match=1
A90BWF0 expected_version=0.11.123 version_marker_found=1
A90BWF0 target_full_sha=3c2718d819880bd3a554e28632f4ffa54b6829dc412d9bb4b1684170efb6b617
A90BWF0 changed_chunks=5 changed_bytes=920604
A90BWF0 result=ok source-plan-only
```

Then V3359 ran:

```text
boot-flash-f2 BOOT-FLASH-F2-BOOT-CANDIDATE /mnt/sdext/a90/flash-staging/boot_linux_v3360_self_dd_f3_self_rollback.img 2989c292d1a7ae7cd5f9eb78906b2451d717e4221b9c9b76114ddc9054b52a29 0.11.123
```

Observed key output:

```text
A90BWF2 before_full_sha=60544a9ceadf1457535ffa5d51c7510a8fba8eab695433c1dfce55aad96917b3
A90BWF2 target_full_sha=3c2718d819880bd3a554e28632f4ffa54b6829dc412d9bb4b1684170efb6b617
A90BWF2 snapshot_sha=60544a9ceadf1457535ffa5d51c7510a8fba8eab695433c1dfce55aad96917b3 snapshot_match_before=1
A90BWF2 target_pwrite_count=64 target_fsync=ok
A90BWF2 target_full_sha_after=3c2718d819880bd3a554e28632f4ffa54b6829dc412d9bb4b1684170efb6b617 target_full_match=1
A90BWF2 restore_skipped=target-verified-host-reboot-required
A90BWF2 result=ok target-written-ready-to-reboot
A90P1 END seq=8 cmd=boot-flash-f2 rc=0 errno=0 duration_ms=6791 flags=0x4 status=ok
```

The host immediately sent `reboot`. That command synced and restarted before returning an END marker,
which is expected for the reboot command itself.

## Self-Written V3360 Boot

- The device booted the self-written V3360 candidate:
  `0.11.123 build=v3360-self-dd-f3-self-rollback`.
- Candidate status passed with `selftest fail=0`.
- Independent candidate selftest passed: `pass=12 warn=1 fail=0`.
- Candidate pstore summary reported `entries=0`.
- The parent F2 `before.full` snapshot was retained on SD at size `67108864` until final v2321
  rollback health passed.

## F0 Rollback Preflight

Command:

```text
boot-flash-plan /mnt/sdext/a90/flash-staging/boot_linux_v2321_usb_clean_identity_rodata.img ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb 0.9.285
```

Observed key output:

```text
A90BWF0 before_full_sha=3c2718d819880bd3a554e28632f4ffa54b6829dc412d9bb4b1684170efb6b617
A90BWF0 candidate_sha=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb expected_sha_match=1
A90BWF0 expected_version=0.9.285 version_marker_found=1
A90BWF0 target_full_sha=b4abab92a80674dbcccc410f089da77b303200c42c2c3f6a9e56a585348cc456
A90BWF0 changed_chunks=13 changed_bytes=10077930 chunk_len=1048576
A90BWF0 result=ok source-plan-only
A90P1 END seq=8 cmd=boot-flash-plan rc=0 errno=0 duration_ms=3592 flags=0x0 status=ok
```

## F3 Self Rollback Result

Command:

```text
boot-flash-f3 BOOT-FLASH-F3-SELF-ROLLBACK /mnt/sdext/a90/flash-staging/boot_linux_v2321_usb_clean_identity_rodata.img ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb 0.9.285
```

Observed key output:

```text
A90BWF3 token=accepted mode=self-rollback-write reboot_candidate=host-controlled
A90BWF3 before_full_sha=3c2718d819880bd3a554e28632f4ffa54b6829dc412d9bb4b1684170efb6b617
A90BWF3 candidate_sha=ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb expected_sha_match=1
A90BWF3 expected_version=0.9.285 version_marker_found=1
A90BWF3 target_full_sha=b4abab92a80674dbcccc410f089da77b303200c42c2c3f6a9e56a585348cc456
A90BWF3 snapshot_sha=3c2718d819880bd3a554e28632f4ffa54b6829dc412d9bb4b1684170efb6b617 snapshot_match_before=1
A90BWF3 snapshot_reopen_sha=3c2718d819880bd3a554e28632f4ffa54b6829dc412d9bb4b1684170efb6b617 snapshot_reopen_match_before=1
A90BWF3 target_pwrite_count=64 target_fsync=ok
A90BWF3 target_full_sha_after=b4abab92a80674dbcccc410f089da77b303200c42c2c3f6a9e56a585348cc456 target_full_match=1
A90BWF3 restore_skipped=rollback-verified-host-reboot-required
A90BWF3 target_written=1 restore_attempted=0
A90BWF3 snapshot_retained=/mnt/sdext/a90/flash-staging/boot-flash-f3-before.full
A90BWF3 reboot_required=1 host_must_reboot_now=1
A90BWF3 result=ok rollback-written-ready-to-reboot
A90P1 END seq=9 cmd=boot-flash-f3 rc=0 errno=0 duration_ms=6538 flags=0x4 status=ok
```

The host immediately sent `reboot`. That command synced and restarted before returning an END marker,
which is expected for the reboot command itself.

## Self-Rolled V2321 Boot And Cleanup

- The device booted v2321:
  `0.9.285 build=v2321-usb-clean-identity-rodata`.
- Final v2321 status passed with `selftest fail=0`, pstore entries `0`.
- Final independent v2321 selftest passed: `pass=11 warn=1 fail=0`.
- Final pstore summary reported `entries=0`.
- The retained F2 and F3 snapshots were deleted only after final v2321 health passed.
- Final staging contents retained only the staged boot images:
  - `boot_linux_v2321_usb_clean_identity_rodata.img`
  - `boot_linux_v3355_boot_write_e5_full.img`
  - `boot_linux_v3360_self_dd_f3_self_rollback.img`

## Timeline

Private `timeline.json` uses the canonical single top-level `events` schema and contains the required
phase events:

```text
candidate_flash_start
candidate_flash_done
candidate_boot_ready
live_session_start
live_session_end
rollback_flash_start
rollback_flash_done
rollback_boot_ready
```

For this F3 self-rollback run, `rollback_flash_start` / `rollback_flash_done` refer to the F3
self-write command that wrote the staged v2321 image from the self-written V3360 boot. The timing
aggregator accepted the timeline set with `invalid_timelines=[]`.

## Conclusion

V3360 F3 passed live. The device booted a candidate that had itself been written by the F2 self-write
path, then that self-written candidate wrote the verified v2321 rollback image, verified the full
boot-partition target SHA, rebooted, and returned to the clean v2321 baseline. This closes F3 only.
F4 and production self-write integration remain blocked until a future explicit policy amendment.
