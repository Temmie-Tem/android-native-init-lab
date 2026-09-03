# S22+ FYG8 P3.34 first-console-return Process-v2 H0 readiness

Date: 2026-09-04 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: H0, host only

Status: `PASS_GO_P334_PROCESS_V2_H0`

## Outcome

P3.34 retains P3.33's two authenticated logical sessions on one tty file
descriptor, fixed commands, timeouts, framing and no-retry behavior. It changes
only the first outer console call: the existing post-call checkpoint reports
`0xB000 | errno` or the bounded `0xBFFF` sentinel before any later stage. This
answers whether the call returns before `OPEN_PARSED`; it adds no USB response,
reopen, reconnect, protocol retry, command, interactive PTY or persistent
state.

The linked console body is semantically unchanged. Growth in the outer
`p318_run` moves its rodata by 44 bytes, so nine address-forming ADD immediates
change by exactly `0x2c`; the remaining 525 of 534 instructions are identical.
The symbol address (`0x408250`), symbol size (`0x858`), control flow, protocol
and source body remain unchanged.

## Exact host closure

- run identity: `c334f1e0a90b5e6d7c8a9b0c1d2e3f6b`;
- builder result: 50,133 bytes, SHA-256
  `765b70a794503e9819940926af3e975334368f551c5c766f5fd754fa8ea2868a`;
- candidate A/B AP: byte-identical and boot-only, 28,631,081 bytes,
  SHA-256 `d79ecf0721604dc30b32777e6a8bfdda54609198b09e3cf081d62446fcbaf7dc`;
- Image: 41,490,944 bytes, SHA-256
  `7f1ecf568b474575d5258c91beeb9d721a3fee6ba527b3c88083ebf16af70cc2`;
- `/init`: 82,264 bytes, SHA-256
  `f4218f326d63b13f8ae6cea3034b3570476f6dd58ac31f525ecdf651ff9abdc9`;
- `boot.img.lz4`: 28,622,828 bytes, SHA-256
  `4988f20b2be2ee16ab0463dcf0315d8b2cdf06a8f2432f53a71f9ed497e97b51`;
- exact Magisk rollback AP: 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

Only the P3.34 runtime member differs from the retained P3.33 closure. P3.33
and all older run identities and candidate APs remain rejected predecessors.

## Process-v2 readiness

- candidate-static: 32,039 bytes, SHA-256
  `e77e4b9c862a4667ceece4f3c15f2f030400e5d24aabe61b569392cba4ae87f4`;
- run manifest: 1,023 bytes, SHA-256
  `92620d9349ea8ab4141f8a324a3b6aa62aea612a6a80e5bc7c7beada23c0e2ba`;
- static check: 1,940 bytes, SHA-256
  `4428c9b9068988922e8e0555e9d19ceb7ebdce20422463d8394d268afa84d1f5`;
- tracked ready manifest: 7,580 bytes, SHA-256
  `a662083e264c1784cf8782153eb918816207e4ad42135bfe9cf57480c93225c5`;
- raw-first audit: SHA-256
  `a755afe3e6e321556b555975471461a49e7077d285ef1e7b3167c8548adc1609`.

The private promotion records are mode `0400`; the public ready manifest is
mode `0644`. Non-creating rehearsal returned `verification=true`,
`created=false`, `run_directory_created=false`, `device_contact=false`,
`odin_invoked=false` and `live_authorized=false`.

P3.34 D0 recognizes only the retained P3.33 rollback baseline at
`2,097,136` bytes and SHA-256
`ce236dfaddd23c9edd5165cee871d576cb8bb106ad4dbbf508c2861162ae617d`.
The fixed decoder requires exactly one clean, foreign-free P3.33
`NO_PROOF_OBSERVER` record at offset `1,652,363` and zero P3.34 records. This
does not reuse P3.33 candidate evidence.

## Validation

Package tests pass 20/20. P3.34 common, static and prepare tests pass 11/11;
the P3.32/P3.33 common regressions pass 9/9. Current-tree and P3.34 mutation
raw-first tests pass 2/2, the raw-first CLI audit passes, and Python compilation
and diff checks pass. Independent review of the final common/ready closure
returned `PASS_GO_P334_PROCESS_V2_H0`: it confirmed the exact P3.33 baseline,
P3.34 observer selection, two sessions on one tty descriptor, zero physical
reopen/reconnect, raw-before-parse ordering, source mutation rejection, and
unchanged D0/F1 authority boundaries.

## Next boundary

This H0 work creates no prepared run, approval, F1 action, device contact,
Odin transfer, recovery, replay, resident install, standing shell or causal
USB claim. The next step is one fresh exact-target D0 preparation. F1 still
requires the newly emitted attended approval and the exact rollback.
