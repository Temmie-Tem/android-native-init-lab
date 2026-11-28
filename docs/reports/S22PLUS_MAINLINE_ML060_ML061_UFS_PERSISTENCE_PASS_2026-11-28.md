# ML060–ML061: first mainline UFS write, persistent across reboot (phase 2b/2c complete)

One returned series approval (v75 `0fae3fa3af`, capability-10 `b607313b…`)
covered three attended steps. All three closed healthy. No step needed a
physical action, a replug or recovery.

```
APPROVE S22PLUS MAINLINE SERIES V1 06e66cdb75e391bdf340f8678ee0456f4c74d12c62c430bdbaeaac1ec5153e30 3steps 1800s attended
```

| Step | Run | What happened | Closure |
| --- | --- | --- | --- |
| 0 | ML060 (candidate a, report V17) | LBA 62,305,152 read as zeros; **one WRITE(10) FUA of the fixed pattern, GOOD; readback matched byte for byte** (`WRITTEN`) | `PASS_MAINLINE_UFS_LINK` / `ANDROID_CLOSED_HEALTHY`, 209 s |
| 1 | Phase 2c Android read | Stock Android, after the full return reboot, read that block by root: SHA-256 `1155097a…` = **`PATTERN`** | `ANDROID_CLOSED_HEALTHY`, same boot as ML060's final health, 0 device writes |
| 2 | ML061 (candidate b, distinct AP) | Fresh mainline boot read the block: pattern already present, **no write** (`ALREADY_PRESENT`) | `PASS_MAINLINE_UFS_LINK` / `ANDROID_CLOSED_HEALTHY`, 197 s |

**This is the first direct mainline write to the phone's UFS media.** It
persists across two reboots, and a different kernel and driver (stock
Android) read it back. Roadmap step 2 (UFS read/write plus persistence
across reboot) is done.

## The block

LU0 LBA 62,305,152 lies in LU0's unallocated tail, past every GPT entry and
inside the last usable LBA. ML059 verified that against the live table.
The pattern is 256 records of `S22UFS2B`, the LBA and the record index, each
a little-endian 32-bit value (SHA-256
`1155097a861b1bdf671fc262e660197e2974599d89831fd1d32b20304e820d18`). The
pattern stays on the block; nothing restores it.

## ML060 storage result (report V17)

rc 0, step `DONE`, the same read-only stage as ML059:
- TUR #1 returned CHECK CONDITION with Target Failure and UNIT ATTENTION (key 6, ASC 0x29); the one repeat passed.
- READ CAPACITY gave last LBA 62,305,279.
- The GPT matched `a0de4421…` and the range check passed.
- The block read was zeros (`ad7facb2…`).

The write stage then ran. The write's status was GOOD (`0x21000000`). The
readback word is `0x1155097a`, the first word of the pattern digest. Flags
include `WRITTEN` and `READBACK_MATCH`; uncertain is false.

## ML061 storage result

rc 0, step `DONE`. The block digest is the pattern digest. Flags include
`PATTERN_PRESENT` and do not include `BLOCK_ZERO`. No write was sent:
write status 0, readback word 0.

## Timelines (seconds from preflight)

| Event | ML060 | ML061 |
| --- | ---: | ---: |
| N step start (`mainline-evidence`) | 19.5 | 19.5 |
| module permit (effect intent) | 106.7 | 106.5 |
| Download return intent | 114.0 | 113.2 |
| final rooted Android health complete | 208.9 | 196.6 |

Each run: 1 N, 1 original A and 3 controls, no recovery. The Android read
ran 128 s after ML060's closure. Its before-health boot ID matched
ML060's final health, and its two rooted health brackets agreed.

## Series mechanics

- Each step was claimed before its grant opened (`step-0.json` to `step-2.json`).
- ML061's binding checked every earlier step: ML060 closed by its own grant, operation, terminal and final health, outcome `WRITTEN`; the Android read's `terminal.json` named the series and step 1, outcome `PATTERN`.
- Fresh readiness ran before each mainline dispatch.

## Evidence

- `workspace/private/outputs/s22plus-ufs-persistence-series-h0-20261128-1/` (series, approval, claims, `block-1/`)
- `workspace/private/outputs/s22plus-ml060-ufs-write-h0-20261128-1/task-1/closed.json` (`54d0f8af…`)
- `workspace/private/outputs/s22plus-ml061-ufs-write-h0-20261128-1/task-1/closed.json` (`abde1b80…`)
- Capability-10 and its owner review rounds: `workspace/private/outputs/s22plus-ufs-route-h0-20261127-1/capability-10/`, `workspace/private/analysis/s22plus-cue-adoption-reviews-20261122/ufs-storage-v17-owner-r{1,2,3}.*`

## Next

Roadmap step 3: stability, meaning repeated runs that are healthy across
boots. Then step 4: handing over to the upstream UFS driver.
