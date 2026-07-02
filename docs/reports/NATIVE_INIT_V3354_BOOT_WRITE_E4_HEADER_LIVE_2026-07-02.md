# Native Init V3354 §0.2 Write-Probe E4 Header Live

- Cycle: `V3354`
- Decision: `v3354-boot-write-e4-header-live-pass`
- Candidate: `A90 Linux init 0.11.118 (v3354-boot-write-e4-header)`
- Candidate boot SHA256: `627b0192d53d9744805c21f151159c177a17827fdd78883a2990faedaa034a43`
- Private run log: `workspace/private/runs/self-dd-v3354-e4-live-20260702T005055Z/`
- Final state: rolled back to `v2321-usb-clean-identity-rodata`, final `selftest fail=0`.

## Gate

- Rollback images were present and SHA-confirmed before flash: v2321, v2237, and v48.
- Pre-flash resident was v2321 with `selftest fail=0`.
- Candidate flash used the checked helper `native_init_flash.py` with expected SHA and version guard.
- Candidate helper readback matched the V3354 boot SHA, then native boot verified `version/status`.
- Candidate selftest passed: `selftest: pass=12 warn=1 fail=0`.

## E4 Probe Result

Command:

```text
boot-write-e4 BOOT-WRITE-PROBE-E4-HEADER-SECTOR
```

Observed E4 output:

```text
A90BWE4 boot_header=ok version=1 page_size=4096 used_len=62644224
A90BWE4 target_off=0 len=4096 header_magic=ANDROID source_sha=3d331efd81b3b9ece40cf6243326cbc68f36e040979d72efdc2dd8acf4975864
A90BWE4 full_sha_before=ce20f41c4b5969f2f42f9dc4d5ef2f15826a18669407a201162dd703fda22d29
A90BWE4 pwrite_rc=4096
A90BWE4 pwrite_count=1 pwrite=ok fsync=ok
A90BWE4 readback_rc=4096 region_match=1 readback_sha=3d331efd81b3b9ece40cf6243326cbc68f36e040979d72efdc2dd8acf4975864
A90BWE4 sector_sha_match=1
A90BWE4 region_match_all=1
A90BWE4 full_sha_after=ce20f41c4b5969f2f42f9dc4d5ef2f15826a18669407a201162dd703fda22d29
A90BWE4 full_match=1
A90BWE4 result=ok pwrite-permitted-identity-verified
A90BWE4 end rc=0
```

This proves normal-boot PID1 can perform one 4096-byte identity `pwrite` to boot partition offset 0,
the Android boot-header sector. The sector readback matched, the sector SHA matched, and the full
64MiB boot-partition SHA stayed unchanged.

## Health And Rollback

- Post-probe status: `selftest fail=0`, pstore entries `0`.
- Post-probe selftest: `pass=12 warn=1 fail=0`.
- Rollback flash used v2321 SHA
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`; readback SHA matched.
- Final v2321 version: `0.9.285 build=v2321-usb-clean-identity-rodata`.
- Final v2321 selftest: `pass=11 warn=1 fail=0`.
- Final pstore summary after `hide`: `entries=0`.

The first final selftest host attempt after rollback produced no command output and was terminated
host-side. A fresh `version` and `selftest` immediately passed; no device-side command failure was
observed. The first final pstore query was blocked by the auto-menu, then passed after `hide`.

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

## Conclusion

V3354 E4 passed. The self-dd ladder now proves normal-boot PID1 can complete identity writes to tail
slack, a contiguous 1MiB non-zero tail-slack block, and the boot-header sector at offset 0, all with
readback/full-SHA preservation and clean v2321 rollback.
