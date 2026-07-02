# Native Init V3357 Self-dd F0 Source-Plan Live

- Cycle: `V3357`
- Decision: `v3357-self-dd-f0-plan-live-pass`
- Candidate: `A90 Linux init 0.11.120 (v3357-self-dd-f0-plan)`
- Candidate boot SHA256: `fd379bfde2b4566e926cfec16339a6e43e1d992012401551384fa5e1584ef63e`
- Planned source candidate: V3355 `A90 Linux init 0.11.119 (v3355-boot-write-e5-full)`
- Planned source candidate SHA256: `ed7aa46f9abc3d1a34c1d0eede247e58219b77375028b2f8bacd070454b1362c`
- Private run log: `workspace/private/runs/self-dd-v3357-f0-live-20260702T093551Z/`
- Final state: rolled back to `v2321-usb-clean-identity-rodata`, final `selftest fail=0`.

## Gate

- Rollback images were present and SHA-confirmed before flash: v2321, v2237, and v48.
- Pre-flash resident was v2321 with `selftest fail=0`.
- Candidate flash used the checked helper `native_init_flash.py` with expected SHA and version guard.
- Candidate helper readback matched the V3357 boot SHA, then native boot verified `version/status`.
- Candidate selftest passed: `selftest: pass=12 warn=1 fail=0`.

## Staging

The first upload attempts exposed two host/device staging facts:

- V3357 has `/bin/toybox`; the host helper default `/cache/bin/toybox` path was absent.
- `/cache` was full, so `/cache/a90-runtime/flash-staging/` was not usable for a 60 MiB candidate.

The candidate was then staged through the approved SD root:
`/mnt/sdext/a90/flash-staging/boot_linux_v3355_boot_write_e5_full.img`.

Observed staged file evidence:

```text
sent_bytes=62644224
sent_sha256=ed7aa46f9abc3d1a34c1d0eede247e58219b77375028b2f8bacd070454b1362c
staged_size=62644224 path=/mnt/sdext/a90/flash-staging/boot_linux_v3355_boot_write_e5_full.img
ed7aa46f9abc3d1a34c1d0eede247e58219b77375028b2f8bacd070454b1362c  /mnt/sdext/a90/flash-staging/boot_linux_v3355_boot_write_e5_full.img
```

## F0 Probe Result

Command:

```text
boot-flash-plan /mnt/sdext/a90/flash-staging/boot_linux_v3355_boot_write_e5_full.img ed7aa46f9abc3d1a34c1d0eede247e58219b77375028b2f8bacd070454b1362c 0.11.119
```

Observed F0 output:

```text
A90BWF0 mode=read-only-source-plan would_write=0
A90BWF0 current_boot_header=ok version=1 page_size=4096 used_len=62644224
A90BWF0 before_full_sha=513bc751f442896f0a6571e90e95b71d29e60da36a8364d244ed1e113d4882b1
A90BWF0 candidate_size=62644224
A90BWF0 candidate_header=ok version=1 page_size=4096 used_len=62644224
A90BWF0 candidate_sha=ed7aa46f9abc3d1a34c1d0eede247e58219b77375028b2f8bacd070454b1362c expected_sha_match=1
A90BWF0 expected_version=0.11.119 version_marker_found=1
A90BWF0 current_stream_sha=513bc751f442896f0a6571e90e95b71d29e60da36a8364d244ed1e113d4882b1 current_match_before=1
A90BWF0 target_full_sha=fa1deeae1ff724c44d6102c5685764e01863ec5a163ca97b4aba6e397f4d4eea
A90BWF0 changed_chunks=5 changed_bytes=1416607 chunk_len=1048576
A90BWF0 would_write=0
A90BWF0 result=ok source-plan-only
A90BWF0 end rc=0
A90P1 END seq=19 cmd=boot-flash-plan rc=0 errno=0 duration_ms=2903 flags=0x0 status=ok
```

This proves the read-only source-plan rung can open an approved staged candidate, verify its SHA and
version marker, parse the Android boot header, stream-check the current boot snapshot, and compute
the exact target full-partition SHA without writing to boot.

## Health And Rollback

- Post-probe status: `selftest fail=0`, pstore entries `0`.
- Post-probe selftest: `pass=12 warn=1 fail=0`.
- Rollback flash used v2321 SHA
  `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb`; readback SHA matched.
- Final v2321 version: `0.9.285 build=v2321-usb-clean-identity-rodata`.
- Final v2321 selftest: `pass=11 warn=1 fail=0`.
- Final pstore summary after prompt recovery: `entries=0`.

One staging receiver stayed open after the host send because `busybox nc` did not exit on EOF without
an explicit timeout. It was cancelled with native shell `q`; the temp file size and SHA matched the
expected candidate before the file was renamed into the approved SD staging path. A final pstore retry
also initially hit the auto-menu busy path, then passed after prompt recovery.

## Timing

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

Elapsed time from the canonical events:

```text
candidate_flash_sec=79.000
live_session_sec=17.000
rollback_flash_sec=73.000
total_sec=633.000
```

The total includes manual staging recovery and prompt cleanup. The actual F0 command completed in
`2903ms`; the checked helper reported V3357 flash total `63.814s` and rollback total `64.443s`.
`analyze_repl_run_timing.py --runs-dir workspace/private/runs --json` accepted the canonical
timeline set with `timelines_found=6`, `runs_used=6`, and `invalid_timelines=[]`.

## Conclusion

V3357 F0 passed live. The source-plan stage is deterministic and read-only, and the device ended in
clean v2321 state. The next self-dd rung is F1: paired content-change roundtrip with immediate
restore before any reboot into the changed image. F1 should use the SD staging root by default unless
cache free-space is explicitly repaired first.
