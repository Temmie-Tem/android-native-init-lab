# S22+ FYG8 P3.19 candidate witness parser predecessor H0

Status: **INDEPENDENTLY REVIEWED SCOPED PASS; H0 ONLY; TRANSPORT OBLIGATION UNRESOLVED; NO CARRIER, BUILD, OR LIVE AUTHORITY**

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

This host-only unit implements the source-derived `/dev/kmsg` parser and the
per-successful-module drain predecessor requested by the unresolved
`candidate-witness-transport` review obligation. It changes no existing
candidate, boot image, package, Process-v2 binding, or device state. It ran no
ADB, USB, Odin, D0, D1, or F1 action.

The result is intentionally narrower than the pending obligation. It defines
and qualifies an internal structured summary **state**, but no canonical
Carrier byte encoding. Envelope-v4 is unchanged and cannot carry the new state
without redesign. The obligation therefore remains unresolved; a later
reviewed Envelope-v5 or other explicit Carrier encoding is still required.

## Frozen predecessor and source inputs

The exact predecessor is the reviewed 73-row materialization receipt:

- 10,658 bytes;
- SHA-256
  `8b8c1f5afd8c02693901d3552c221bcc73bafa2543c77dfff4954bdba188f6b5`;
- exact `mfd_max77705.ko` and `pdic_max77705.ko` at rows 71 and 72;
- exact `i2c-msm-geni.ko` at row 69;
- tuple-derived EUD row 38.

The parser derivation reopens exact FYG8 inputs before interpreting a format:

| input | bytes | SHA-256 |
|---|---:|---|
| `max77705_usbc.c` | 124,569 | `4dabc4b25e99e26c662748934a6a98775073683832f08652e15762f4689a3e3d` |
| `max77705-muic.c` | 76,141 | `bfdb034d7571ca233202221cdc8cdfe68bab3e837afea9c4b5a37378ed7acbab` |
| Maxim Makefile | 450 | `8055a9480971e835edccb441ce0554940a1d211be5bc1d1702ebc4587580c91d` |
| `max77705_usbc.h` | 10,072 | `1cc7e211c50685c3eed3d1b4582869d0a65a559a2114c0087fac2646f4fc883e` |
| `max77705.h` | 13,686 | `ff2498061ddb20c1891cb9fe6611edde655c3e1cda8fa4446d0c876a476ff1c7` |
| `kernel/printk/printk.c` | 91,182 | `eabf2acf23694f94b973981d684037556f62cbc74583907f087019d35d0acd3a` |
| `pdic_max77705.ko` | 423,456 | `27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db` |

`msg_maxim` supplies `max77705: <function>:`, while the MUIC source supplies
`pr_fmt(fmt) KBUILD_MODNAME ": " fmt`. The Makefile binds
`max77705-muic.o` into `pdic_max77705.o`, and the exact module carries the sole
`name=pdic_max77705` metadata. The prefixes are therefore not inferred from a
corpus example.

The exact `printk.c` function `info_print_ext_header` binds the record header
as unsigned facility/level, sequence and timestamp, followed by `c` or `-`, an
optional `caller=[CT]<decimal>`, and the semicolon. This predecessor accepts
one terminal newline and fails closed on dictionary lines rather than silently
interpreting a larger `/dev/kmsg` record class.

## Four source-derived witness grammars

The generated C parser recognizes these source sites as distinct grammars:

1. `max77705_usbc_probe`: `probing Complete..` through `msg_maxim`;
2. `max77705_muic_irq_init`: the five signed decimal fields `uiadc`,
   `chgtyp`, `dcdtmo`, `vbadc`, and final `vbusdet`;
3. `max77705_muic_detect_dev`: exactly the synchronous three bytes `USBC1`,
   `USBC2`, and `BC`, each emitted by `%02x`;
4. both non-interchangeable classification sites:
   `max77705_muic_check_new_dev` with `%lu`, and
   `muic_lookup_vps_table (<attached>)` with `%d`.

Printable internal spaces in a VPS name are retained, including the real
`DCD Timeout` control. Canonical `%d`, `%lu`, `%x`, and `%02x` spelling and
ranges are shared by the C implementation and Python test model. `+1`, `-0`,
out-of-range form-2 indices, uppercase `0X`, and noncanonical leading zeroes
reject.

The seven-register `max77705_muic_print_reg_log` form remains a separate
auxiliary grammar. It never sets the synchronous initial-status witness or
advances the initial chain.

## Runtime delta and bounded transport

Ten of twelve predecessor sources remain byte-identical. Only the wrapper and
runtime include change. Both direct and folded module loops call one shared
helper only after a zero module-load result. The helper records exact target
rows 69, 71, and 72 from the bound plan, performs the bounded drain, clears the
active module context, and only then executes the row-38 EUD cache read. An
EUD-cache failure can no longer occur before the successful module's log drain.

The fixed transport limits are implementation resource bounds, not the
withdrawn stock `sec_log_buf` FIFO budget:

| boundary | exact limit |
|---|---:|
| one `/dev/kmsg` record | 4,096 bytes |
| records per drain | 256 |
| bytes per drain | 262,144 |
| cumulative records | 4,096 |
| cumulative bytes | 1,048,576 |
| successful module drains | 73 |

Positive read amounts are charged before header or message parsing. The first
and last sequence are retained; wrap, gap, `EPIPE`, malformed framing, record,
byte, and counter overflow stop the predecessor.

The generated C transport was executed, not represented only by a Python
mirror. Its independent negative boundary results are:

| boundary | records | bytes | drains | result detail |
|---|---:|---:|---:|---:|
| per-drain bytes | 64 | 261,760 | 1 | 24,610 |
| per-drain records | 256 | 2,982 | 1 | 24,610 |
| cumulative bytes | 256 | 1,047,206 | 5 | 24,610 |
| cumulative records | 4,096 | 52,168 | 33 | 24,610 |
| drain counter overflow | — | — | 4,294,967,295 | 24,609 |

`EPIPE`, a sequence gap, leading-zero sequence, empty flag, invalid caller,
missing newline, and trailing bytes all reject in the same generated C path.

## Context and semantic boundary

Only the immediate drain for successful row 72 may build the candidate's
initial chain. Its required order is:

`IRQ five-tuple -> synchronous three-byte status -> form-1 classification -> probe-complete`.

The generated C fixture proves that exact order produces stage 4,
`complete=1`, and `ambiguous=0` for row 72. Wrong row, missing or reordered
events produce no complete chain and set ambiguity. Form-2 classification and
the delayed seven-register line remain auxiliary even inside a synthetic row-72
context.

This is still not a live result. `probing Complete..` follows an outer probe
that can discard the MUIC-probe failure, and a completed host fixture does not
prove a candidate will emit the chain. The state explicitly remains no-proof
until a future runtime captures it and a reviewed retained encoding preserves
it.

## External corpus qualification

The positive corpus does not define the grammar. It only tests the grammar
derived above. The exact 121-row manifest
`s22plus-fyg8-p319-abl-capture-manifest-v3` contains exactly one row binding the
selected 2,097,136-byte capture, SHA-256
`1ad451372ad5bf72fab681656249f07b4451df3255bd3a642759c4cbf5297df1`,
to its exact private relative path.

That capture supplies thirteen accepted messages: one probe, one IRQ tuple,
one synchronous status, one form-1 classification, seven form-2
classifications, and two delayed register lines. Both classification forms and
the auxiliary/synchronous split are therefore positive-controlled without
using corpus strings to invent the parser.

## Envelope-v4 remains unchanged

The transform mechanically compares base and generated function bytes for:

- `s22plus_max77705_p318_envelope_crc32` — 393 bytes,
  SHA-256 `10ad362b...`;
- `s22plus_max77705_p318_encode_envelope` — 5,049 bytes,
  SHA-256 `5fbefefd...`;
- `p317_publish` — 1,888 bytes, SHA-256 `26b59bef...`.

It also fixes envelope size 128, CRC offset 124, version 4, timing size 26,
lossless capacity 47, `TIME_MASK=0xff`, and the V4 CRC domain. Mutating any of
those checked values fails closed.

This matters because lossless Envelope-v4 already consumes its complete
76-byte payload as a 29-byte prefix plus as many as 47 poll bytes. Earlier
progress is overwritten by the final two-slot pair. The new summary state is
therefore neither Carrier-retained nor a spare-field extension. A separately
reviewed canonical encoding remains mandatory.

## Receipt, tests, and failed attempts

The current private receipt is:

- `workspace/private/outputs/s22plus_fyg8_p319/successor-witness-parser-v2-20260820-14/result.json`;
- 15,478 bytes;
- SHA-256
  `14ca869c411a5940ecffbc24cd2231bc1d10e0bc410ad379d6914809b0debaf0`;
- regular mode `0400`, link count one.

The bound implementation is 101,509 bytes, SHA-256
`7078ef471ffb5a1291d40274201b1f71db93f0465348bb9f1135215d65e659e5`.
The focused test is 20,042 bytes, SHA-256
`86a77c451ad31fca4997b6f0fef03066b8d8d36b7311811e96a095de4c1804c2`.
Twenty-five implementation,
generated-C, mutation, receipt, and regeneration tests pass. Audit-only and an
independent temporary materialization reproduce the receipt byte-for-byte.

Runs `-01` through `-13` remain private and are not current authority. The
first five stopped before a receipt; the later receipts predate one or more of
the final source binding, exact framing, row-72 context, independent limits,
manifest binding, or numeric-parity repairs. No directory was reused or
overwritten.

## Authority and next step

This implementation sits under the existing unresolved
`candidate-witness-transport` obligation and opens no second obligation.
An independent Luna MAX review regenerated the 15,478-byte receipt exactly and
reproduced the focused and related closure tests. It found no blocking fail-open
in the source-derived grammar, generated-C transport, module context, or
authority boundary. Its scoped PASS qualifies only this H0 parser and
bounded-transport predecessor. The appended bookkeeping action deliberately
does not use the taxonomy's `PASS_GO_` resolution form.
It does not resolve `candidate-witness-transport`; canonical Carrier bytes remain absent. It does
not build or package a candidate, grant D0/D1/F1 or recovery authority,
authorize replay, or permit a device action.

One nonblocking source hygiene note remains: the generated record path assigns
the first sequence idempotently twice. Both assignments write the same value,
so this changes neither the retained state nor the fail-closed sequence checks.

The next technical boundary is an explicit canonical Envelope-v5/Carrier
encoding for this state together with the still-missing producers for status
bytes 3/4 and register `0x23` bit-3 readback. Only after that boundary and its
independent review should a fresh candidate intent/build closure be considered.
