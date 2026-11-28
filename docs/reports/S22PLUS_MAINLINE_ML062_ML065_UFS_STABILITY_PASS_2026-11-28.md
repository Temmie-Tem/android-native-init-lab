# ML062–ML065: UFS stability series, four of four healthy (roadmap step 3)

One returned series approval covered four attended V17 runs, each on its own
freshly qualified candidate under capability-10 (`b607313b…`, reused per the
capability rule). Each run is a separate cold boot.

```
APPROVE S22PLUS MAINLINE SERIES V1 1efd8f770c6ab9e0aca9f567e56b85c7196a0a1a84e43d0c37d820c943a5ce2e 4steps 1800s attended
```

**All four closed `PASS_MAINLINE_UFS_LINK` / `ANDROID_CLOSED_HEALTHY`.** None
needed a physical action, a replug or recovery. In every run the storage stage
completed (rc 0, step `DONE`) and found the ML060 pattern still on LBA
62,305,152 (`ALREADY_PRESENT`), so nothing was written.

| Run | Candidate | Module permit | Download return | Final health | Closure |
| --- | --- | ---: | ---: | ---: | --- |
| ML062 | v17-7 | 106.3 s | 112.9 s | 195.6 s | `1bad36fc…` |
| ML063 | v17-8 | 105.9 s | 112.6 s | 195.1 s | `51fb6174…` |
| ML064 | v17-9 | 93.1 s | 99.8 s | 181.9 s | `3309c3e4…` |
| ML065 | v17-10 | 106.1 s | 112.7 s | 195.1 s | `b7fbdb61…` |

Times are seconds from preflight. Each run had 1 N, 1 original A and 3
controls.

## Per-run results: identical

- **Link:** `UFS_LINK_COMPLETED`, operation errno 0, one USB attempt, normal and recovery return proved, all 2047 stage-2 records observed.
- **Storage:**
  - TUR #1 returned CHECK CONDITION with Target Failure and UNIT ATTENTION (key 6, ASC 0x29), then one repeat passed.
  - fDeviceInit cleared on the first poll.
  - Capacity last LBA 62,305,279; the pinned GPT matched and the range check passed.
  - Block SHA-256 is the pattern (`1155097a…`). Flags include `PATTERN_PRESENT`; write status 0.

## What this establishes

Counting ML056–ML065, ten consecutive mainline runs completed the UFS link.
ML059–ML065 are seven consecutive completed storage stages. The test block
held the written pattern across seven reboots after the write:
- six mainline boots and one stock-Android read;
- four Android returns in this series alone.

No run in the series varied in its link or storage fields. ML064's permit
came about 13 s earlier than the others; that cause was not examined.

## Evidence

- Series: `workspace/private/outputs/s22plus-ufs-stability-series-h0-20261128-1/` (series, approval, claims step-0..3)
- Runs: `workspace/private/outputs/s22plus-ml06{2,3,4,5}-ufs-stability-h0-20261128-1/task-1/closed.json`
- Candidates and qualifications: `.../s22plus-ufs-route-h0-20261127-1/candidate-storage-v17-{7..10}`, `prepare-stability.py` (log)

## Next

Roadmap step 4 is the handover to the upstream UFS driver.
