# S22+ FYG8 P3.26 bidirectional ACM and BusyBox-console H0

Date: 2026-09-02

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

Status: `P326_BIDIRECTIONAL_ACM_BUSYBOX_CONSOLE_IMPLEMENTED_REVIEW_PENDING`

## Result

P3.26 is a fresh host-only successor to the consumed P3.25 candidate. It keeps
the exact P3.24 Type-C lane, P3.25 tty-class ModemManager guard, single endpoint
selector, passive trace, mandatory rollback, and final-health choreography.
It does not replay or modify P3.25.

The candidate-side PID 1 retains the proved 49-byte banner, then accepts only
one exact run-bound `PING` line and returns one exact `PONG ... pid=1` line. It
starts one static `/bin/busybox ash` child, which accepts only one exact
run-bound `SHELL` line, returns one exact `SHELL-OK ... busybox=1` line, and
then becomes an ephemeral interactive `ash`. The current Process-v2 observer
closes after that fixed proof, so this unit proves the byte path but does not
yet expose a general host command interface.

The host transmits exactly 77 fixed bytes in two writes. The device transcript
is exactly 145 bytes. Received chunks are written to the inherited durable raw
writer before any equality or success classification. Wrong banner, missing
reply, wrong endpoint identity, guard loss, and predecessor identities remain
non-accepting.

## Exact host artifacts

- Fresh run ID: `c326f1e0a90b5e6d7c8a9b0c1d2e3f4b`.
- Builder result `stock-candidate-build-v1-20260902-05/result.json`:
  42,176 bytes, SHA-256
  `acbba4fd75a207e31aa4e857b8871f63bd8660ba9ad826ba6d082a14d146763e`.
- Candidate A/B AP: 28,631,081 bytes, SHA-256
  `df0eea9f06866d1a3943280f13a03a34d3afc230e167350b8a0ca0f1148e11d8`.
- Boot image: 100,663,296 bytes, SHA-256
  `7d8f3ac400a9506eb0051adf23800e3c926156bf1e8d5fdbfae0db28b4b79507`.
- Image: 41,490,944 bytes, SHA-256
  `062f1366794d31b2f674ef5dd2cb61ab572b79ea2115b745805468272c8d69b0`.
- `/init`: 80,808 bytes, SHA-256
  `0452d2545a9512500f132c6d5342767d55409bdb526386a178fead1740cdabed`.
- Candidate-static `process-v2-candidate-static-20260902-03.json`:
  23,667 bytes, SHA-256
  `5bebc42b150ef10e85f4560b9333293da4c9eeb74b9d857dbefb1cc786c0a64c`.
- Exact Magisk rollback remains 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

The A/B AP files are byte-identical and contain only `boot.img.lz4`. The
ramdisk adds only `bin` and `bin/busybox` to the inherited exact rootfs. The
static AArch64 BusyBox 1.36.1 binary is 2,237,056 bytes with SHA-256
`d4e1ca8235fd5c47a7dfca5c9c60ad2243f5d17d3c43d58a7c42355f10fa2cba`;
its fixed config enables static linkage and `ash` while omitting `su`,
`sulogin`, and `getty`.

## Validation

The P3.26 focused suites pass 12/12. Shared evidence, Process-v2 core, and live
runner suites pass 131/131. Python compilation and diff checks pass. Builder
audit, candidate-static audit, and a noncreating Process-v2 rehearsal all pass;
the rehearsal reports `verification=true`, `created=false`,
`run_directory_created=false`, `device_contact=false`, `odin_invoked=false`,
and `live_authorized=false`.

The repository-wide raw-first census is already stale on separately owned S20+
and earlier P3.23-P3.25 source registrations. Its first current-tree stop is an
unchanged tracked S20+ source, before reaching P3.26. This unrelated maintenance
debt is not relabeled as a P3.26 pass and was not widened into this unit. The
P3.26 raw-before-classification behavior is covered directly by its exchange
test and by exact execution-closure binding.

No public ready manifest or private promotion was published. No D0, D1, F1,
ADB, USB, `pkexec`, Odin, transfer, flash, or device contact occurred.

## Claim boundary and next step

This unit is `PROVED` only as a deterministic H0 implementation and artifact
closure. It does not prove on-device bidirectional traffic, a usable general
shell, persistent recovery, Max77705 causality, or candidate success. The
execution-critical common runner, observer, schema, and target-contract change
require one independent review. After a clean review, publish the already
rehearsed promotion and ready declaration, then perform one fresh connected
prepare and request one exact attended F1 approval.
