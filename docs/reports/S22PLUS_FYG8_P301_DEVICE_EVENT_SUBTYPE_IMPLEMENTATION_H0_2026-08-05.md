# S22+ FYG8 P3.01 Device-Event Subtype Implementation

Date: 2026-08-05 KST
Target: Samsung Galaxy S22+ FYG8 (`SM-S906N` / `g0q` / `S906NKSS7FYG8`)
Tier: H0 only
Verdict: `PASS_P301_DEVICE_EVENT_SUBTYPE_IMPLEMENTATION_HOST_ONLY`

## Outcome

P3.01 is implemented as a userspace-only overlay on the exact qualified P3.00
kernel Image. It changes one generated payload artifact,
`p290_e3_runtime_include`, and leaves the candidate patch, checkpoint client,
15-probe descriptor, and Image byte-identical to P3.00. No kernel build,
Full-LTO build, device command, transfer, or F1 arm occurred.

The fixed Image is pinned at:

- size: `41490944`
- SHA-256: `01457240881b432f725b0f2d795813c38ef7cca4365633f9b0fc7c3a62744a3f`

## Corrected result contract

A remains the exact P3.00 branch/link detail at ordinal 105 with outcome
`PROGRESS`. The generated C contains compile-time assertions for ordinal 105
and 106, checks `g_checkpoint.generation == 105` before A, verifies generation
106 and nonterminal state after A, then verifies generation 107 and terminal
state after B. The generated host fixture executes the correct transition and
rejects starting generations 104 and 106 without issuing the A write.

For `DEVICE_OTHER_ONLY` with the inherited exact final state, B encodes the
six known DWC31-enabled other-event types, first event-info nibble, and count
bucket into all 4,032 details from `0x4001` through `0x4FC0`:

```text
detail = 0x4001 + (((mask - 1) * 16 + first_info) * 4 + count_bucket)
```

The mask bits are ordered `DISCONNECT`, `WAKEUP`, `SUSPEND`,
`ERRATIC_ERROR`, `CMD_CMPL`, and `OVERFLOW`. Count buckets are `1`, `2-3`,
`4-7`, and `8+`.

Undefined or disabled event types are not treated as impossible. The parser
sets `unknown_subtype_seen` for any other four-bit device-event type. Any run
containing such a type, including a known/unknown mixture, terminates with the
dedicated `0x4FC1 UNKNOWN_SUBTYPE_SEEN` detail. A zero known mask without that
flag terminates with named contradiction `0x6001`; the zero check executes
before the only `(mask - 1)` expression, so no underflow path exists.

All 132 valid final-state indices use `0x5001-0x5084` when the final tuple does
not permit the subtype implication. Named final-selection contradictions use
`0x6001-0x600F`. Wide details are B-side `FAILURE` values; the three excluded
band bases `0x4000`, `0x5000`, and `0x6000` are never emitted.

## Fixed-Image overlay identity

Nine byte-affecting P3.01 `SOURCE_KEYS` were printed and hashed before the
overlay intent was derived. All nine were present in the Git-derived S22+
change set. P3.01 decoder/model/closure/tests and the host USB sidecar were
classified outside payload identity. Concurrent A90 native-init changes were
excluded from the S22+ key set and were not read as authority, edited, staged,
or used.

The immutable overlay intent preserves the P3.00 run ID
`e324abaec60286102e4c9eb19fd80600` because the reused Image enforces it. It
binds the exact P3.00 parent contract, the fixed Image, the nine source
receipts, and every generated source receipt.

- semantic intent SHA-256: `017267cd9111e98093dc4575590e98661f5b48154c5744278287acd476264edc`
- intent file SHA-256: `6884d41d7634110c80f3bff903fd142945883e9ea2e7fc2d0246162393516ddd`
- post-intent changed `SOURCE_KEYS`: none

## Build and packaging

The P3.01 static AArch64 `/init` was linked twice byte-identically. A separate
candidate A and candidate B were then constructed from the same fixed Image;
their boot image, LZ4 frame, and Odin AP are pairwise byte-identical.

| Artifact | Size | SHA-256 |
|---|---:|---|
| P3.01 `/init` | `66384` | `7b71b9a06161562d2fc280b24747454ae885d10b0dbf5435d92339b317c2df3b` |
| `boot.img` | `100663296` | `11edee10861ed65f9812849b5c5c9f2aee358a6fa2c0dcacb0932bef104cc299` |
| `boot.img.lz4` | `27100482` | `5250bf799291686fea1fde94c91be505e74985e5b256cdc770ebf1faa7111653` |
| `AP.tar.md5` | `27105321` | `35a1621716702ef553c2db83b8fbb075543c37a4b56507b1fa0c4ef86668c41b` |

The AP contains exactly one member, `boot.img.lz4`; zero module binaries were
injected. The final unpack recovered the exact fixed Image and exact P3.01
userspace.

## Executed validation

- all 4,032 subtype values round-trip without collision;
- all 132 final-state drift values round-trip;
- generated C executes known types, undefined types 8 and 12, a known/unknown
  mixture, all four count buckets, the zero-mask guard, and ordinal failures;
- inherited P3.00 stream parser, IRQ/event classification, trace lifecycle,
  cleanup, and AArch64 integrated link remain passing;
- focused P3.01 telemetry tests: 7/7;
- focused P3.01 overlay/contract tests: 2/2;
- focused P3.00 plus shared sidecar regressions: 22/22;
- final combined P3.01/P3.00/sidecar regression: 31/31;
- candidate A/B boot/AP byte comparison: pass.

One combined high-load test invocation produced an isolated `UNKNOWN` in the
existing synthetic live-sidecar timing test. The exact affected test and its
P3.00/sidecar suite then passed independently, and the complete combined suite
passed 31/31 on the final rerun. It did not affect a device or artifact and is
not used as positive evidence.

## Sidecar correction

The future verifier now accepts either direct SIGTERM death (`-15`) or a clean
zero exit after a monitor handles the recorded SIGTERM request. It still
requires the source to have been alive at arm and immediately before stop,
with a stop timestamp, zero truncation, zero capture error, exact source/log
receipts, ownership, and the same bounded candidate window. Other return
codes, including `1` and `-9`, remain rejected. This fixes the exact P3.00 live
observation mismatch without reclassifying the historical host axis.

## Independent review

Focused independent review returned `PASS_GO` for the exact current P3.01
overlay, decoder/model, boot-only packaging, and sidecar-verifier change set.
The reviewer independently reproduced the final 31/31 regression, source-key
intent verification, fixed-Image equality, candidate A/B equality, one-member
AP structure, subtype range and ordinal invariants, and sidecar return-code
guards. The only finding was the report-only LZ4 size typo corrected above;
execution code and all nine `SOURCE_KEYS` remained unchanged.

This approval qualifies the unchanged capability, not a device run. A change
to its execution-critical bytes or hazard assumptions requires a fresh review.

## Remaining gate

The candidate artifacts are host-built but do not themselves grant F1.
Process-v2 static evidence, exact rollback binding, fresh connected baseline,
attended presence, and final health remain separate gates. No new Full-LTO A/B
is warranted because the kernel Image and probe machinery are unchanged.
