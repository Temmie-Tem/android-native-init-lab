# S22+ FYG8 P3.19 raw-first observer boundary

Date: 2026-08-17 KST
Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q`) only
Tier: H0 host-only
Status: **PASS_GO_P319_RAW_FIRST_CROSS_TARGET_MEMBERSHIP_H0_CAPABILITY_V1; H0 ONLY; NO D0/D1/F1/LIVE AUTHORITY**

## Result

The P3.19 Stage A device action was correctly bounded, returned `rc=0` with
empty stderr, and requested no attribute body, I2C transaction, debugfs read,
sysfs write, reboot, or module action. The host then parsed before publishing
raw stdout and discarded already-received evidence. This is the same
`WRITE_AFTER_PARSE_DEVICE_EVIDENCE_LOSS` class recorded by P3.03
`stock-log-d0-1`; P3.03's next D0 proved that write-before-parse preserves the
raw bytes even when the parser still rejects them.

The repair is therefore a permanent observer boundary, not another local
Stage A shape-parser exception. It introduces one common acquisition module
whose completed output is exposed only as an immutable `RawCaptureHandle`.
The handle reopens a no-clobber regular stdout/stderr pair and canonical
receipt, all mode `0400`, link count one, file-fsynced and directory-fsynced
before any active result parser or classifier runs. Timeout, output-limit,
nonzero-return, launch-error, and interruption paths retain bounded partial
bytes before reporting failure. Old result-schema spellings cannot omit the
new raw receipt and pass current validation.

## Active S22+ coverage

The reviewed-current source set covers these connected paths:

- reusable Process-v2 D0 ADB inventory, identity, health, and baseline EOF;
- P2.57 stock-pivot, P3.03 stock-log, Max77705 sysfs, and P3.19 Stage A D0;
- Android Download request and Odin endpoint enumeration;
- USBFS birth-time identity, Odin candidate/rollback stdout and stderr;
- CDC-ACM udev properties and candidate TTY bytes; and
- the USB trace sidecar's snapshots and streaming source logs.

Active parser entry points receive a `RawCaptureHandle` and may then delegate
to a pure byte decoder. The ModemManager arm acquisition reads only the fixed
protocol-frame byte count without inspecting its values, writes each chunk,
finalizes and fsyncs the raw handle, and only then reopens that handle to check
the exact marker line. It is not a candidate-result classifier. The final
Android observer uses a fresh phase-specific ADB client and validates both
reads only from their handles. P3.00 source logs and start/end snapshots now
carry nested raw receipts which its live downstream verifier reopens exactly.

The full top-level `revalidation/` inventory was scanned. Thirty-one older
S22+ observer sources remain inactive historical programs rather than current
authority; their exact file identities are frozen under aggregate SHA-256
`850e87ac23c849faafdf2847ab6b5ba47892e8cc37578846d7c0f34ee0c53798`.
The broader closed inventory freezes `(name,size,sha256)` for 121
observer-like sources at digest
`e0fde5ae9afb7b39579ed41ad09e70d9f4ef82c9e316a9eb5c3ff68bba8456af`;
any new or changed source requires review regardless of import spelling.
Adding or changing one of those bypasses fails the audit, as does adding a new
D0/F1 observer, changing an active source, removing a handle seam, restoring
direct subprocess parsing, or changing the permanent boundary implementation.
This does not retroactively qualify any retired live gate.

## Machine evidence

Private receipt:

`workspace/private/outputs/s22plus_fyg8_p319/raw-first-observer-audit-20260817-01.json`

- 10,040 bytes;
- SHA-256 `7f9e6f6c2048b55748532177e1af978b43a23828197f754d587a12eb73351011`;
- mode `0400`, link count one; and
- byte-identical to independent stdout regeneration.

The receipt records 1,716 top-level Python files scanned, 411 modules with an
actual `subprocess` import, 31 exact inactive legacy observer sources, 40
active function seams, and 15 source identities (14 execution sources plus
the auditor). Critical execution files are individually byte-frozen inside
the auditor. A minimal bootstrap reads stable auditor bytes and compile-executes
that exact payload; the bound audit reopens the same bytes before and after its
work. Changing either requires a fresh receipt and independent review. The
earlier 8,729-byte `61617e20` receipt lacked self-binding. The later 8,828-byte
`89f93fad` receipt had normalized source binding but preceded the finalized
guard, P3.00 consumer, and final-observer closures. The first two remain private,
mode-0400/nlink-1 superseded evidence. A third 9,779-byte `0c8f8d3b` receipt
closed those consumers but still used an unbounded sidecar `readline()`; it is
also preserved and superseded. A fourth 9,779-byte `54303f11` receipt bounded
that stream but preceded the initial AST subprocess-import checks. It too is
preserved and superseded. A fifth 9,779-byte `60009597` receipt added those checks but
preceded the closed 121-name observer inventory; it is likewise preserved and
superseded. A sixth 9,982-byte `d42eecc0` receipt closed names but not the
bytes of existing non-acquisition observer-like sources; the full byte freeze
supersedes it. None of these receipts is current authority.

Primary implementation identities are:

- common capture: 25,006 bytes, SHA-256 `410e260129c0c50dca29b008dc7cf1051ee007816ab18bea76aeae62505ca0e4`;
- Stage A successor: 19,894 bytes, SHA-256 `c28097ef576f971ff427c97bdf62d839047c1c4ec1a861c8bf39592dc352fc38`;
- CDC observer: 58,773 bytes, SHA-256 `a1fa4dc117fcd9b1f755f50a7d105a86f7b8ddf43ef30a48d34c0b1f0dcf0da1`;
- F1 live adapter v2-6: 158,382 bytes, SHA-256 `1acb93802479ed6061cb7dd0f97859b7dfbc232cc25f28c210d6a0482d6823f1`;
- USB trace sidecar: 18,137 bytes, SHA-256 `f4a87987c0feddf00e89235070ccfaebf6f29353d06f3aa0c887dc3da6dc12ab`;
- P3.00 binding consumer: 27,069 bytes, SHA-256 `d987d6732132eea3adddf27ed42336486d914706b6555ba279cd98c4987e613f`;
- source auditor: 32,585 bytes, SHA-256 `7a94c6537d1f851aff3ec4adfaf0f42d430e4fb1fee488940d465b3509ecf2b7`.

Focused active D0/F1, raw-helper, Stage A, selector-control, Odin, CDC-ACM,
and sidecar tests pass 294/294. The common Process-v2 set passes 122/122
(`22 + 28 + 47 + 25`). Python compilation and scoped whitespace checks pass.

The exact old P3.18 qualification is intentionally not refreshed. Its
source-pinned historical suite passes 188 of 209 tests and rejects 21 at the
old D0/observer/QEMU/finalizer identities. Those rejections prove that V3 and
its ready/live bindings cannot be silently reused after this execution-closure
change. The closed P3.18 evidence remains historical; a future P3.19 F1 needs
fresh qualification, binding, and approval.

The ledger contains eight typed `HOST_OBSERVER_FAILURE` action rows: D0 3,
D1 1, and F1 4. A raw string count is ten because the header prose and format
grammar each contain the token once; they are not two additional actions.

Independent read-only review regenerated the current receipt byte-identically,
reproduced the 294/294, 122/122, 69/69, and 188/209 boundaries, and rejected
new-name plus existing-source direct, alias-import, and dynamic-import bypasses.
Its scoped `PASS_GO` applies only to this exact H0 permanent boundary closure.

## Authority and next step

This H0 unit contacted no device, ADB server, USB endpoint, Odin session, or
other target. It did not retry P3.19 Stage A and did not infer the discarded
attribute list. `regmap` presence and the Stage B target remain unproved.

## Current cross-target membership successor

The earlier `PASS_GO` above is historical evidence for the prior raw-first
boundary. Its historical status was
`PASS_GO_P319_RAW_FIRST_OBSERVER_BOUNDARY_H0_CAPABILITY_V1; H0 ONLY`; the
current default no-clobber receipt is
`workspace/private/outputs/s22plus_fyg8_p319/raw-first-observer-audit-20260821-04-cross-target-membership-default.json`:
11,012 bytes, SHA-256
`d3e5013134c74837b2c36a14f5dfd8ac2ab874707dd5f30a5090002bc2a380da`, mode
`0400`, link count one. It regenerates byte-identically from the bound auditor
whose source is 57,919 bytes, SHA-256
`6d218854492b5ac1191fac171efb12324acf743020406daba2ab75e2edbc7183`, with
normalized self-binding `89ecc662487c94e2211dfb413a9ec74d870e60e695bbe51aa4f85d38a349b7ca`.

The false positive was a scope mistake, not an acquisition path: the committed
S22+ P3.19 candidate qualifier is a host-only H0 builder/auditor. Its exact
46,610-byte identity is `e74c299a1446cc379bd2bb065309ce2dc7b4f1cb189a03fb58877c6805fdfca9`,
and the typed registry records owner `s22plus-fyg8-p319`, classification
`host-only-non-acquiring`, profile `H0-candidate-qualification`, two allowed
`compile(..., "exec")` sites only in bound `_load_stock`/`_load_adapter`, and
the sole `getattr(os, "O_DIRECTORY", 0)` site. Forbidden subprocess/pty/asyncio/
multiprocessing/ctypes imports, system/popen/fork/execv/posix_spawn/
bounded-command calls, unapproved `exec`/`getattr`, and non-H0/no-live process
fields fail closed; exact source identity and invariant sites are required.

The receipt now records one host-only non-acquiring source with canonical
inventory SHA-256
`a85944d3066909bbb54fd5e00fdf265900708f0ca9a4af2245e46fff25de9933`, while
the S22 pre-boundary device inventory remains exactly 127 at
`c7029746710d2f83d710a3abbecbba5a6bbc3367c7a5f20a559b63a92f1677db`. The
pre-boundary S22+ inventory is still 127. The set has 51 target-external membership entries, including the S20+
autonomous coordinator; that membership is not an active S22 source and its
ordinary edit remains isolated. Copied or renamed bytes, comments, byte edits,
device-scope changes, and altered allowed execution sites are rejected. The
previous current `-03` receipt
`workspace/private/outputs/s22plus_fyg8_p319/raw-first-observer-audit-20260821-03-cross-target-membership.json`
is preserved unchanged at 11,012 bytes,
SHA-256 `2016f6cb812daa3ee633c65677b7418d80624cd0dd20a6635f9d8c57b2e0108d`;
the earlier current 10,296-byte receipt `e5689fee2322b22cba04c5ecfc21d00e59de0fe44e1f0834389ee783eee53f7f`
is also preserved unchanged as superseded evidence.

This successor is now **PASS_GO_P319_RAW_FIRST_CROSS_TARGET_MEMBERSHIP_H0_CAPABILITY_V1**.
No D0/D1/F1/LIVE authority exists. It is H0-only and creates no
D0, D1, F1, device, ADB, USB, Odin, recovery, replay, or live authority. The
Stage A/Stage B historical boundaries above remain unchanged; no device action
was retried.

The required independent changed-closure review is complete; full-tail taxonomy is 45 total / 31 resolved / 14 unresolved, with only the -27 topic resolved by this review. Only a fresh direct operator request may authorize any future directory-only Stage A D0, and this
receipt grants no such authority.
