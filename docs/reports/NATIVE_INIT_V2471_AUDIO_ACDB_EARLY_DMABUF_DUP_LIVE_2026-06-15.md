# NATIVE_INIT_V2471_AUDIO_ACDB_EARLY_DMABUF_DUP_LIVE_2026-06-15

## Scope

Fresh bounded Android-good live rerun using the V2470 early dmabuf fd
duplication helper.

The run stayed inside the GOAL.md recoverable envelope:

- checked Android boot handoff only;
- temporary Magisk measurement capsule staged and cleaned up;
- Android framework `AudioTrack` speaker playback used as known-good stimulus;
- no native `/dev/msm_audio_cal` calibration ioctl;
- no native speaker write;
- checked rollback to V2321.

Private raw artifacts remain under:

`workspace/private/runs/audio/v2471-acdb-early-dmabuf-dup-live-20260615-210638/`

## Decision

`v2471-early-dmabuf-dup-attempted-but-proc-fd-open-enxio-rollback-pass`

V2471 disproves the simple early-dup hypothesis:

- the helper reached the same Android-good ACDB custom-topology edge;
- it observed the target 4916-byte dmabuf `mmap2()` records;
- at `mmap_entry` time, `readlink(/proc/<tgid>/fd/<fd>)` already reports
  `/dmabuf:dmabuf*`;
- but `open(/proc/<tgid>/fd/<fd>, O_RDONLY|O_CLOEXEC)` still fails with errno
  `6` (`ENXIO`) for the target 4916-byte dmabuf records;
- therefore no retained duplicate fd exists at SET_CAL time, the old
  owner-VA fallback runs, and that still fails with errno `5` (`EIO`).

No dmabuf payload bytes or hashes were captured.

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
  "ioctl_entries": 116,
  "ioctl_fd_match_count": 116,
  "dmabuf_payload_count": 0,
  "mmap_entry_count": 3606,
  "mmap_success_count": 3593,
  "mmap_error_count": 13,
  "mmap_record_count": 3393
}
```

Custom-topology SET_CAL attempts:

| Process JSONL | seq | cal_type | cal_size | mem_handle | status | open_errno | read/write errno |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| `p4328` | 28 | 39 | 4916 | 37 | `open-proc-fd-failed-remote-mmap-read-failed` | 6 | 5 |
| `p7282` | 28 | 39 | 4916 | 36 | `open-proc-fd-failed-remote-mmap-read-failed` | 6 | 5 |
| `p794` | 28 | 39 | 4916 | 37 | `open-proc-fd-failed-remote-mmap-read-failed` | 6 | 5 |
| `p8738` | 28 | 39 | 4916 | 37 | `open-proc-fd-failed-remote-mmap-read-failed` | 6 | 5 |

Matching target mmap records:

| Process JSONL | mmap seq | fd | len | mmap status | mmap ret | fd target | dup_fd | dup_errno |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: | ---: |
| `p4328` | 84 | 37 | 4916 | `ok` | `0xea021000` | `/dmabuf:dmabuf165` | -1 | 6 |
| `p7282` | 151 | 36 | 4916 | `ok` | `0xed7a8000` | `/dmabuf:dmabuf201` | -1 | 6 |
| `p794` | 84 | 37 | 4916 | `ok` | `0xecf94000` | `/dmabuf:dmabuf139` | -1 | 6 |
| `p8738` | 151 | 37 | 4916 | `ok` | `0xf64ac000` | `/dmabuf:dmabuf227` | -1 | 6 |

For each process, the immediately preceding failed mmap attempt still shows the
same `fd`/`len` but `readlink-error:No such file or directory` and mmap return
`0xfffffff7` (`-9` / `EBADF`), matching V2468's two-attempt pattern.

## Additional implementation finding

V2471 also exposed a second mmap fd-noise class:

- V2469 fixed AArch32 `mmap2(fd=-1)` decoding.
- The late 64-bit observer still records AArch64 anonymous mmap entries with
  fd `4294967295`.
- In this run there were `1105` AArch64 `mmap_entry` records and `1105`
  matching `mmap_exit` records for that fd value.

This does not affect the target 32-bit audio HAL custom-topology records, but it
should be fixed host-only before another live rerun so summaries stay clean.

## Interpretation

The target dmabuf fd is visible by name at `mmap_entry`, but procfs fd reopen is
not a usable duplication primitive for this object. The failure happens before
the later SET_CAL edge, not only after the stock process closes the fd.

The remaining payload-capture problem is now owner-context capture:

- cross-process owner-VA reads fail with `EIO`;
- procfs fd reopen fails with `ENXIO` even while readlink sees `/dmabuf:*`;
- the payload likely must be captured either before it enters the dmabuf or by
  code running inside the stock Android audio process context.

## Rollback / health

Rollback sequence:

- cleanup removed the temporary APK, module files, and run directory;
- Android `adb reboot recovery` returned `rc=0`;
- checked V2321 flash through `native_init_flash.py` returned `rc=0`.

Independent post-run native health check passed:

```text
A90 Linux init 0.9.285 (v2321-usb-clean-identity-rodata)
selftest: pass=11 warn=1 fail=0
```

## Next safe unit

Do not rerun the V2470 live path unchanged.

Next meaningful unit is host-only V2472:

1. extend mmap fd decoding/filtering so AArch64 fd value `0xffffffff` is also
   treated as anonymous `fd=-1` and not recorded;
2. preserve the V2471 early-dup finding as a negative discriminator;
3. design the next owner-context capture method, most likely by measuring the
   source buffer before dmabuf handoff or by a separately reviewed Android-side
   in-process instrumentation capsule.

Native `/dev/msm_audio_cal` calibration ioctls remain blocked.

