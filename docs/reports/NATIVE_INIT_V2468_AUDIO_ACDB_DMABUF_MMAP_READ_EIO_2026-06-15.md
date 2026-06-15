# NATIVE_INIT_V2468_AUDIO_ACDB_DMABUF_MMAP_READ_EIO_2026-06-15

## Scope

Fresh bounded Android-good dmabuf live rerun using the V2467 mmap-lifecycle
fallback helper.

The run stayed inside the GOAL.md recoverable envelope:

- checked Android boot handoff only;
- temporary Magisk measurement capsule state staged and cleaned up;
- Android framework `AudioTrack` speaker playback used as the known-good
  stimulus;
- no native `/dev/msm_audio_cal` calibration ioctl;
- no native speaker write;
- checked rollback to V2321.

Private raw artifacts remain under:

`workspace/private/runs/audio/v2468-acdb-dmabuf-mmap-live-20260615-203737/`

## Decision

`v2468-dmabuf-mmap-record-found-remote-read-eio-rollback-pass`

V2468 closed one more discriminator:

- V2466 had only shown that proc-fd duplication fails.
- V2468 proves the Android audio process does successfully `mmap2()` the
  target custom-topology dmabuf fd with the declared payload length.
- The helper found matching fd `37` mappings for the SET_CAL `mem_handle=37`.
- Reading those mapped bytes from the traced process still failed with errno
  `5` (`EIO`), so no payload bytes or SHA-256 were captured.

## Live evidence

Top-level result:

```json
{
  "decision": "v2451-acdb-m1-hybrid-late-observer-payload-captured-before-rollback-rollback-pass",
  "ok": true,
  "rolled_back": true
}
```

Payload summary:

```json
{
  "classification": "msm-audio-cal-payload-captured",
  "ioctl_entries": 90,
  "ioctl_fd_match_count": 90,
  "dmabuf_payload_count": 0,
  "mmap_entry_count": 5412,
  "mmap_success_count": 5391,
  "mmap_error_count": 21,
  "mmap_record_count": 5271
}
```

Three custom-topology SET_CAL attempts were captured:

| Source process | seq | cal_type | cal_size | mem_handle | status | open_errno | read/write errno |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| p4319 | 28 | 39 | 4916 | 37 | `open-proc-fd-failed-remote-mmap-read-failed` | 6 | 5 |
| p7261 | 28 | 39 | 4916 | 37 | `open-proc-fd-failed-remote-mmap-read-failed` | 6 | 5 |
| p8738 | 28 | 39 | 4916 | 37 | `open-proc-fd-failed-remote-mmap-read-failed` | 6 | 5 |

For each of those processes, the helper observed the same pattern immediately
before SET_CAL:

1. one failed `mmap2(fd=37, len=4916, prot=0x3, flags=0x1)` returning
   `0xfffffff7` (`-9` / `EBADF`) while the fd path was transiently missing;
2. one successful `mmap2(fd=37, len=4916, prot=0x3, flags=0x1)` whose fd target
   was `/dmabuf:dmabuf*`;
3. the SET_CAL header with `mem_handle=37`;
4. proc-fd open failed with errno `6`;
5. fallback read from the recorded mapped address failed with errno `5`.

Representative successful mapping records:

| Process | mmap seq | fd | len | prot | flags | return VA | fd target |
| --- | ---: | ---: | ---: | --- | --- | --- | --- |
| p4319 | 281 | 37 | 4916 | `0x3` | `0x1` | `0xecb6b000` | `/dmabuf:dmabuf165` |
| p7261 | 362 | 37 | 4916 | `0x3` | `0x1` | `0xf68c0000` | `/dmabuf:dmabuf201` |
| p8738 | 286 | 37 | 4916 | `0x3` | `0x1` | `0xef281000` | `/dmabuf:dmabuf227` |

No private `dmabuf-*.bin` payload file was produced.

## Important implementation finding

V2468 also exposed a helper-noise bug:

- AArch32 `mmap2` fd argument `-1` was displayed as unsigned
  `4294967295`.
- This polluted the mmap summary with anonymous mappings and inflated
  `mmap_record_count`.

That noise is not the payload blocker. The real payload path still had clean
fd `37` records with `len=4916`, `PROT_READ|PROT_WRITE`, and `MAP_SHARED`.
However, the next host-only fix should cast the AArch32 fd argument as signed
and avoid recording `fd < 0` mappings.

## Interpretation

V2468 narrows the wall:

- `mem_handle=37` really is a userspace fd at mmap time.
- The payload-sized dmabuf is mapped in the stock Android audio process.
- The mapping is not readable through the helper's current
  `process_vm_readv()` / `PTRACE_PEEKDATA` fallback at SET_CAL time.

This is consistent with a dmabuf mapping type that is valid for the owning
process and the kernel/DSP path but not readable through cross-process memory
inspection. It is not a negative result for native replay and not evidence that
the payload bytes do not exist.

## Rollback / health

Rollback sequence:

- Android ADB was available before rollback.
- `adb reboot recovery` returned `rc=0`.
- Checked V2321 flash through `native_init_flash.py` returned `rc=0`.

Independent post-run native health check required `--input-mode slow` once after
an initial serial framing desync, then passed:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
selftest: pass=11 warn=1 fail=0
```

## Next safe unit

Do not rerun the unchanged V2467 live path. It already proved the mapping exists
and that cross-process read returns `EIO`.

Next meaningful unit is host-only V2469:

1. fix the AArch32 signed-fd mmap noise (`fd=-1` must not be recorded);
2. preserve the fd37 mapping evidence cleanly in summaries;
3. design the next capture method for a dmabuf mapping that is visible to the
   owner but not readable through `process_vm_readv()` / `PTRACE_PEEKDATA`.

Native `/dev/msm_audio_cal` calibration ioctls remain blocked.
