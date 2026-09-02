# S22+ FYG8 P3.27 framed exec H0

Date: 2026-09-02 KST

Target: `SM-S906N / g0q / S906NKSS7FYG8`

Tier: H0 only

Device contact: none

Independent review: `PASS_GO_P327_FRAMED_EXEC_H0`

## Outcome

P3.27 now has an independently reviewed host-only prototype for a framed fixed-command
session over the ACM path proved by P3.26. It does not yet have an AP builder,
Process-v2 registration, target-contract activation, ready declaration,
approval, or live authority.

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
- P3.27 transformed runtime: 468,067 bytes,
  SHA-256 `19a930c3d4d818e3a3e9909eba0bfd61fd8035c250e297f53639fbf1fefa64ef`.
- Runtime transformer source: 21,286 bytes,
  SHA-256 `d1ce20d3eaa1833ff721f8c6468b63aab40f4ac8bf4b9cf214e782375d170b8a`.
- Host codec/observer source: 13,461 bytes,
  SHA-256 `d07d406be9972a5826e0d73f108f71176e2dca6c4ea08d3c079320c40fc43d2d`.
- Focused tests: 12,531 bytes,
  SHA-256 `22492c3073b6424352a2b2600352063a302b6d96436bda450edd40e33c513235`.

## Validation

- Focused P3.27 tests: 9/9 pass.
- O0 plus P3.26 regression tests: 22/22 pass.
- Python byte compilation: pass.
- Full P3.26 source closure transformed and cross-linked with the repository
  AArch64 freestanding flags: pass.
- Resulting temporary `/init`: static AArch64 ELF, no undefined symbols,
  81,424 bytes, SHA-256
  `56de8daa756b5a661e8f5e03ee6ed453968aa849f978d0a305eaa1dd7380df5d`.
- `git diff --check`: pass.

The tests cover fragmented reads/writes, CRC corruption, sequence mismatch,
multi-frame output, explicit timeout/truncation, exec failure accounting,
exact-command rejection including BusyBox `setsid`, finite host deadlines,
fresh run binding, and the exact two-anchor runtime transform.

## Next bounded unit

Add only the fresh P3.27 artifact identity, candidate builder, and thin
Process-v2 adapter needed to produce and reopen one boot-only A/B AP. Common
live registration, target-contract activation and a ready declaration remain
a later combined review unit. No device work occurs in either host-only unit.
