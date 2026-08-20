# S22+ FYG8 P3.19 stock Image provenance repair H0

Status: **PASS_GO; H0 ONLY; NO LIVE AUTHORITY**
Verdict: **PASS_GO_P319_STOCK_IMAGE_PROVENANCE_REPAIR_H0_CAPABILITY_V1**

This is a new host-only repair under
`h0-stock-image-provenance-repair-22`. It does not alter the earlier
stock-witness-runtime PASS_GO, its receipts, or any prior append-only row.
There was no device, ADB, USB, Odin, transfer, recovery, replay, or live
authority action.

## Finding and boundary

The e721bf2a24 review found that the previous auditor pinned Image
`71f573eb...` while treating a different-run P310 `vmlinux`, `vmlinux.symvers`,
and `.config` as its build provenance. That same_magic/provenance claim is
withdrawn. The repair removes those files from the authority and input bundle;
they cannot bless or alter the result. No rebuilt PDIC module or candidate
byte was produced or changed.

The fixed Image is now the sole ABI authority. The auditor strictly decodes
exactly one bounded gzip `IKCFG_ST`/`IKCFG_ED` payload, requiring ASCII config
schema, `CONFIG_MODVERSIONS=y`, unset module signature/force-load/relative-CRC
lanes, profile 3, run ID
`b9cc424d0d184f5accbce94a844e817d`, and UNSAT tag
`ecbfff41d2c5ed22383db45dedfb622d`. It derives the unique kernel vermagic and
compares only the suffix required by `same_magic`. It decodes PREL32 names and
parallel CRC tables directly from the Image: 7,222 providers close 3,566
imports as 3,238 Image providers plus 328 earlier modules, with zero missing,
ambiguous, or duplicate providers. Address-sensitive vmlinux value-field
counts are no longer claimed.

Duplicate, corrupt, truncated, trailing-marker, Image section/layout/name/CRC,
vermagic, wrong-run substitution, and module snapshot mutations fail closed.
The reviewed 73-row plan and exact mode `0400`/nlink-1 module snapshot remain
bound; directories are mode `0700` with exact child sets. The P318 packager is
lineage-only and is not executed.

## Current no-clobber outputs

The current auditor source is `113532` bytes, SHA-256
`574132854258ac2affd038bc98f9629663c9f1c6aa95cfc8585101c1abe0d29e`.

| output | result size | SHA-256 | mode/nlink | phase |
|---|---:|---|---|---|
| `stock-witness-runtime-v1-20260821-32/result.json` | 382059 | `a6e1734bdd527eb598446269e860a171fb4ad3785c792db0837f4850b8dbd177` | 0400/1 | source + ABI inputs |
| `stock-witness-runtime-v1-20260821-33/result.json` | 392896 | `e491c79722c3ae080770026eb3e2e6bcd4c8bc5c34d4b29e18ae24765e2c6173` | 0400/1 | A/B userspace + boot/AP |

Both outputs regenerate byte-identically with `--audit-only`. Phase 2 is
host-only and starts from the exact P311 clean base; it replaces init/child and
adds only the four delta members (latch, `spu_verify`, `mfd_max77705`, and
`pdic_max77705`). The prior `-24/-25` closure and intermediate
`-26/-27`/`-28/-29`/`-30/-31` outputs remain preserved as superseded historical
evidence. Current reviewed authority for this repair is exclusively `-32/-33`
and the current auditor tuple above.

The append-only bookkeeping follow-up
`h0-stock-image-provenance-repair-followup-23` corrects the original pending
row's mixed current tuple without editing that historical row or its literal
`\\n` ending. The `113553`-byte `f811e202...` auditor identity was a pre-final
intermediate; current-only authority is the `113532`-byte `574132854258...`
auditor paired with the two receipts above. This follow-up creates no new
obligation and is not itself a `PASS_GO` row; the appended
`h0-stock-image-provenance-repair-review-22` is the scoped resolution.

## Validation and authority

Focused stock-runtime tests are 24/24, the relevant predecessor closure is
94/94, taxonomy is 39/39 with full-tail obligations 42 total / 28 resolved /
14 unresolved, and relevant docs are 149/149. The exact resolution is
`h0-stock-image-provenance-repair-review-22`; it changes no candidate or device
authority. `py_compile` and `git diff --check` pass. This H0 PASS_GO grants no
D0, D1, F1, recovery, replay, or live authority; fresh candidate intent and
attended approval remain separate requirements.
