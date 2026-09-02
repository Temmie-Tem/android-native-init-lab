# S22+ FYG8 P3.27 framed exec H0

Date: 2026-09-02 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: H0 only

Device contact: none

Independent review: `PASS_GO_P327_PROCESS_V2_H0`

## Outcome

P3.27 now has a host-only framed fixed-command runtime and a deterministic
boot-only A/B AP builder over the ACM path proved by P3.26. The initial
protocol unit received `PASS_GO_P327_FRAMED_EXEC_H0`; the fresh Image/run-ID,
adapter and candidate-build extension received
`PASS_GO_P327_FRAMED_EXEC_CANDIDATE_H0`. The minimal Process-v2 registration,
target-contract clause, and ready declaration subsequently received
`PASS_GO_P327_PROCESS_V2_H0`. No connected preparation, approval, device
contact, or live authority exists yet.

The design deliberately keeps the next step smaller than ADB, FunctionFS,
NCM/TCP, or an interactive PTY. It reuses the earlier S22+ O0 16-byte framed
wire shape and the P3.26 PID1/BusyBox path.

## Wire contract

- Fresh magic/version: `S327 / 1`.
- Header: magic, version, type, little-endian payload length, sequence, CRC32.
- Session: `OPEN -> READY -> (EXEC -> DATA* -> EXIT){3} -> CLOSE -> DONE`.
- `OPEN` and `READY` carry the exact 16-byte P3.27 run ID.
- Maximum frame payload: 1,024 bytes.
- Maximum wire command field: 1,023 bytes, with only the three exact commands
  accepted.
- Commands: exactly three fixed proof commands; caller-selected commands are
  rejected.
- Per-command timeout: ten seconds.
- Forwarded output bound: 128 KiB per command.
- `EXIT` retains flags, exit code, terminating signal, forwarded byte count,
  and duration.

The future proof session uses only BusyBox `id`, BusyBox `uname -a`, and one
run-bound BusyBox `echo`. P3.27 does not accept arbitrary live commands.

## PID1 child handling

PID1 starts `/bin/busybox ash -c` with stdin bound to `/dev/null` and merged
stdout/stderr on one nonblocking pipe. The child enters a new session. PID1
streams output frames, checks the deadline even during continuous output,
kills and reaps a timed-out child, then kills and boundedly reaps remaining
children in that process group before publishing `EXIT`.

This is a noninteractive command channel. It does not prove PTY job control,
terminal resize, signals from a client, stdin streaming, file transfer, ADB,
NCM, or a persistent resident supervisor.

## Exact H0 identities

- P3.26 transformed-runtime preimage: 457,784 bytes,
  SHA-256 `20dd261f0acd065c711a327bbbe3f7c03452db3979e12b443f36d4b02ab0a93a`.
- P3.27 transformed runtime: 467,943 bytes,
  SHA-256 `623d19160d4a9815b013cb27c42cc0a44755b1913ce341a61d0aae85472c8073`.
- Runtime transformer source: 21,194 bytes,
  SHA-256 `1e78259b7306aec772c0b5abff8d6253cc361442b1a10ea31d3bca417bc45575`.
- Host codec/observer source: 13,461 bytes,
  SHA-256 `d07d406be9972a5826e0d73f108f71176e2dca6c4ea08d3c079320c40fc43d2d`.
- Focused tests: 12,531 bytes,
  SHA-256 `22492c3073b6424352a2b2600352063a302b6d96436bda450edd40e33c513235`.

## Candidate build

The same-length Image run identity is
`c327f1e0a90b5e6d7c8a9b0c1d2e3f3b`. It changes only the declared IKCONFIG
line/gzip span and one raw Image slot. The final host output is
`stock-candidate-build-v1-20260902-04`:

- result: 42,906 bytes, SHA-256
  `b6ea8cc54addc7b1e5500c68004db928cc7aef704f09157b6d895f3d0318f431`;
- Image: 41,490,944 bytes, SHA-256
  `4f778fb87a2cdc01c70aadc10d67576e1a1a438575a2863883d2289193275818`;
- `/init`: 81,384 bytes, SHA-256
  `b21e94b37a2e58fc1cf08bccbfd3d43156ba01bf580579ed0616f3cb7ea637b0`;
- candidate A/B AP: 28,631,081 bytes, SHA-256
  `024322fd25bf1782c80e2878547c2bb6a9fd314ff21f14c8b37b3805373d3ed0`;
- boot image: 100,663,296 bytes, SHA-256
  `5014c0ed095dc7667d2450a9c0ae8772664c4e3d9c5b2c1c6fd1d55c5b780533`;
- exact rollback remains 23,367,721 bytes, SHA-256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`.

The AP has exactly one `boot.img.lz4` member. A and B are byte-identical and
the AP differs from consumed P3.26. The packaged BusyBox bytes are unchanged.
Image IKCONFIG/raw rodata and `/init` join to the one fresh P3.27 ID.

The first output `-01` stopped host-only because a second raw run-ID array made
the compiled `/init` contain the ID twice. P3.27 now references the inherited
`k_run_id`, restoring the exact one-occurrence invariant. `-02` and `-03` are
preserved metadata predecessors; `-04` is the current idempotently auditable
output. None contacted a device or invoked Odin.

## Validation

- Focused protocol tests: 9/9 pass.
- Focused artifact/adapter/builder tests: 7/7 pass.
- O0 plus P3.26 regression tests: 22/22 pass.
- Python byte compilation: pass.
- Full P3.26 source closure transformed and cross-linked with the repository
  AArch64 freestanding flags: pass.
- Resulting temporary `/init`: static AArch64 ELF, no undefined symbols,
  and exact one fresh run-ID occurrence. The final candidate build reproduces
  that 81,384-byte `/init` in A and B.
- Candidate builder `--audit-only`: pass with exact result re-emission.
- `git diff --check`: pass.

The tests cover fragmented reads/writes, CRC corruption, sequence mismatch,
multi-frame output, explicit timeout/truncation, exec failure accounting,
exact-command rejection including BusyBox `setsid`, finite host deadlines,
fresh run binding, and the exact two-anchor runtime transform.

## Process-v2 registration

P327 has a distinct common evidence/core/live dispatch; it does not alias the
P326 transcript role or parser. It reuses only the unchanged P324 Type-C lane,
P325 tty-class guard, rollback, and final-health choreography. Its live receipt
requires all three framed commands, clean `DONE`, raw-first capture, and
immediate trailing-byte retention/rejection.

Independent review first blocked a real defect: session creation hashed the
seven-field inherited CDC projection while receipt reopen hashed the larger
P327 manifest object. Both paths now use one shared projection. A real socket
exchange through raw capture, durable receipt publication, and reopen passes;
the P327 live tests pass 5/5 and ready tests pass 5/5.

Published H0 identities:

- candidate-static: 24,347 bytes, SHA-256
  `e4ba955e06d61475fc6bdc2949fe9b8e8585232fe06945702c30bba63b96bbdd`;
- run manifest: 1,021 bytes, SHA-256
  `6966232397876bc338b5fbb7f73ac13260366397ab9a36d0f8db4a08dce9feeb`;
- static result: 1,938 bytes, SHA-256
  `493c6d9a9ecfda8faa2f9ce3ab00dda476d64e74b6d91f021e40f87781084210`;
- ready manifest: 4,105 bytes, SHA-256
  `c5a4a4abcc4ae00951d895c1ae899a66acdbda1fdea2467b7fdf87fe340b9d2c`.

The ready manifest is H0 qualification only. It creates no F1 approval and no
permission to transfer either AP.

## Ledger continuity

The current machine-readable ledger independently reproduces 25 candidate and
25 rollback transfers. It omits the retained P320, P321, and P322 consumed F1
runs; audit commit `bd86d11337` records that divergence without choosing a
retrospective disposition. This unit does not backfill them.

P327 currently has no F1 row because it has no device run. If its candidate is
transferred, the same post-terminal reporting unit that proves
`CAMPAIGN_CLOSED` will append exactly one P327 F1 closure row from the retained
journal/result. The connected preparation will use a campaign-visible direct
child name such as `p327-ready1-prepared-20260902-1`, avoiding the P322
locatability problem without changing the common allocator or adding a gate.

## Next bounded unit

Run one fresh connected D0 preparation into the campaign-visible P327
directory, then obtain one exact attended F1 approval. No new protocol feature,
general shell, PTY, resident service, or extra qualification gate belongs
between ready and that preparation.
