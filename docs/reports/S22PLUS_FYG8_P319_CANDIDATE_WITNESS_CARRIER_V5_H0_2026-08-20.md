# S22+ FYG8 P3.19 Candidate Witness Carrier / Envelope-v5 H0

Status: **SCOPED_PASS_GO_H0_CAPABILITY**

Target: **Samsung Galaxy S22+ FYG8 only** (`SM-S906N` / `g0q` /
`S906NKSS7FYG8`)

Tier: **H0 host-only**. No device, ADB, USB, Odin, transfer, recovery,
rollback, replay, or live action occurred. This unit creates no D0, D1, F1,
recovery, or live authority.

## Outcome

The reviewed P3.19 parser predecessor now has a canonical retained encoding.
The generated 73-row runtime copies its structured state immediately before
terminal publication and encodes it as a distinct 128-byte Envelope-v5 split
across the existing Carrier positions 105 and 106, 64 bytes each.

This is not an extension bit inside Envelope-v4. The V4 CRC and encoder bodies
remain byte-identical, its `TIME_MASK=0xff` remains fully allocated, and its
domain remains `S22PLUS-FYG8-MAX77705-DIAG-V4\0`. V5 has magic `MXD5`, version
5, encoding id 3, witness flag bit 5, and CRC domain
`S22PLUS-FYG8-MAX77705-DIAG-V5\0`.

Two exact driver-source deltas supply the previously missing producers:

- `max77705_muic_detect_dev` prints all five bytes already returned by the
  existing five-byte bulk read. This adds zero I2C transactions.
- `max77705_usbc_umask_irq` checks the existing register-`0x23` write, performs
  one new readback, and emits `P319_INTSRC_MASK:0x%02x`. The value, rather than
  absence of an error line, proves whether bit 3 is clear.

Only source and deterministic patches are materialized. No new
`pdic_max77705.ko`, boot image, AP archive, manifest, or candidate build exists.
The currently bound row-72 module remains the reviewed predecessor byte; a
future candidate build must compile and bind the materialized driver source
before any qualification can claim that the new emitters execute.

## Exact predecessor

The implementation bound-executes and reopens:

- parser predecessor source: 101,509 bytes, SHA-256
  `7078ef471ffb5a1291d40274201b1f71db93f0465348bb9f1135215d65e659e5`;
- predecessor receipt: 15,478 bytes, SHA-256
  `14ca869c411a5940ecffbc24cd2231bc1d10e0bc410ad379d6914809b0debaf0`,
  regular mode `0400`, link count one;
- all twelve exact generated predecessor sources; and
- the exact stock `max77705-muic.c` and `max77705_usbc.c` snapshots already
  bound by that predecessor.

The new generated-source set changes only
`s22plus_fyg8_p290_e3_runtime.inc.c`. The wrapper and the other eleven
generated sources remain byte-identical. The final runtime include is 431,581
bytes, SHA-256
`99d6cdc92f699c8644d8dd1dd9ec95f73de8454ee23cc7dec9279f720573a2a4`.

## Canonical Envelope-v5 geometry

The 48-byte inherited header remains in place. V5 clears the V4 poll-overflow
and poll-lossless flags, sets the V5 witness flag, sets encoding id 3, and uses
all 76 payload bytes. The existing compact binding, execution witness,
semantic code, observer tag, fixed diagnostic fields, poll counts, and raw
count remain in the header and are strictly checked by the V5 host decoder.

V5 calls the exact V4 encoder as its semantic/header validator. V4 may replace
the caller semantic with `result_payload_unrepresentable` when its own 47-byte
poll capacity overflows. Because V5 deliberately does not retain that poll
payload, V5 restores the already-validated caller semantic before calculating
its own terminal detail and CRC. A native fixture forces the V4 overflow code
and proves that the V5 result restores the caller code.

The 76-byte payload is:

| offset | bytes | canonical value |
|---:|---:|---|
| 0 | 1 | payload ABI 2 |
| 1 | 1 | exact witness-presence mask; bit 7 reserved |
| 2 | 1 | sequence, readback, module, status, and classification validity |
| 3 | 1 | chain stage 0–5, complete bit, ambiguous bit; high bits reserved |
| 4 | 6 | signed little-endian results for fixed rows 69, 71, and 72 |
| 10 | 5 | uint8 counts: probe, IRQ, five-byte status, form-1 class, readback |
| 15 | 5 | `USBC1`, `USBC2`, `BC`, `CC0`, `CC1` |
| 20 | 1 | register `0x23` readback |
| 21 | 10 | five little-endian uint16 nested IRQ values |
| 31 | 8 | form-1 classification index |
| 39 | 16 | first 128 bits of SHA-256 over the exact classification name |
| 55 | 2 | bounded record count, maximum 4,096 |
| 57 | 3 | bounded record bytes, maximum 1,048,576 |
| 60 | 8 | first `/dev/kmsg` sequence |
| 68 | 8 | last `/dev/kmsg` sequence |

The target-module identities are schema-fixed as row 69
`i2c-msm-geni.ko`, row 71 `mfd_max77705.ko`, and row 72
`pdic_max77705.ko`. V5 publication requires all 73 loads and all 73 per-module
drains to have completed, and all three retained target results to be exact
zero successes. A module-load failure still terminates through the inherited
checkpoint failure path before V5; V5 does not relabel that failure as a
successful module witness.

## Ordered witness context

The V2 state order is now:

`IRQ five-tuple -> five-byte initial status -> form-1 classification -> 0x23 readback -> probe complete`.

Only the immediate successful row-72 drain can advance that chain. The native
generated-C parser reaches stage 5, complete 1, ambiguous 0 for the exact five
messages. Wrong order remains incomplete and ambiguous.

The primary values are frozen once the chain completes. A later reset or
RAM-test path may emit another status or mask line after the active row-72
context has ended; that later line is fully grammar-checked, sets ambiguity,
and cannot overwrite the retained row-72 values. The native fixture proves a
later `0x0f` mask leaves the retained `0x07` and its original count unchanged
while changing ambiguity from zero to one.

The delayed seven-register work-item form and the second classification form
remain auxiliary presence bits. They do not advance or replace the initial
chain.

## Producer boundary

The exact materialized driver-source identities are:

- `max77705-muic.c`: 76,187 bytes, SHA-256
  `1a25794b6b7e54f8dd00f1d972223a389e37526a37d2045ec117cb50fe5e73dc`;
- `max77705_usbc.c`: 124,849 bytes, SHA-256
  `1b8bebe9f5bff892a6d9fcb9a5ef5fae783898a6e8cee03297df47ea75a92b43`.

The first delta changes only the log arguments after the already successful
five-byte bulk read. The second delta fixes one source order:

`read 0x23 -> clear bit 3 -> checked write 0x23 -> new read 0x23 -> exact log`.

A failed write or failed new readback returns from the existing `static void`
helper. The outer probe may still print complete. Therefore a missing readback
is retained as incomplete/ambiguous witness evidence, never inferred as a
successful unmask. A present value with bit 3 set is also retained rather than
reclassified as absence.

## Decoder authority boundary

The host decoder rejects invalid magic, version, CRC, V5 flags, encoding,
semantic pair, observer tag, compact-binding reserved values, execution-state
reserved values, fixed-result state, payload validity, module tuple, counter
range, sequence coherence, mask/count relationship, chain stage, and reserved
bits. Header mutations are tested after recomputing a valid CRC, so the CRC is
not the only gate.

The decoder also mirrors the bound V3/V4 producer's source-reachable semantic
domain. Every MUX row requires a diagnostic result, exact causal compact
binding, and an exact causal execution witness. A result-bearing row must
classify to its exact terminal or MUX code, while execution-only terminal
codes 10 through 15 require their corresponding policy/provider/link witness
and cannot carry a result or observer tag. Valid-CRC mutations cover absent
MUX results, noncausal binding or execution, result/semantic disagreement,
and inconsistent execution-only terminals. The Python payload encoder also
matches the native parser's classification-name grammar: 1--64 printable
ASCII bytes with neither leading nor trailing space.

V5 intentionally omits the V4 timing witness, banner outcome, and raw or
summary poll payload. It retains and validates the fixed diagnostic header but
always emits:

`causal_result_allowed = false`

with denial reason `v5_omits_v4_poll_timing_and_banner_payload`. No V4 timing,
host-silent, MUX-causal, banner, or poll claim may be inherited from this V5
payload. This is the cost of dedicating the fixed 76-byte payload to the
P3.19 candidate witness and is explicit rather than silently dropping old
authority.

## Native and deterministic validation

The exact generated runtime compiles under the repository AArch64
freestanding syntax command. Two native host fixtures execute source extracted
from that generated runtime:

- the parser qualifies the five-byte status, parent-mask readback, complete
  row-72 chain, wrong order, post-complete freeze, and four malformed forms;
- the encoder produces bytes identical to the Python codec and rejects ten
  module, sequence, absent-value, chain, range, mask, byte-accounting, and
  context mutations.

The focused suite contains 35 tests covering deterministic regeneration,
no-clobber, hostile source/receipt identities, V4 byte preservation, exact
64+64 Carrier reassembly, full-header valid-CRC mutations, payload ranges,
producer order, native/Python parity, source-reachable semantic classes,
classification-name parity, and authority boundaries.

## Receipt and attempts

Current private authority:

- path:
  `workspace/private/outputs/s22plus_fyg8_p319/successor-witness-carrier-v5-20260820-13/result.json`;
- 11,647 bytes;
- SHA-256
  `05ee3385c8c8001039a329316c65f9bee9d5d3181e8673f7ddf9dea420532917`;
- regular mode `0400`, link count one.

The bound auditor is 87,577 bytes, SHA-256
`a6c0c410f5c5157da4e9b2044dfc9eb710c7f39460f44e41a4deb9034c3bdcc8`.
The focused test is 24,785 bytes, SHA-256
`1d76ce701a99d9b34dba86753caec475885878542bdc08518e248a13a96dbb4d`
at the implementation freeze.

Attempts `-01`, `-03`, `-04`, `-08`, and `-09` stopped before a result
receipt. Receipts `-02`, `-05`, `-06`, `-07`, and `-10` remain private and
superseded respectively by the V4-overflow semantic restoration, native
negative gates, complete V5 header decoder, row-72 value freeze, and strict
fixed-result validation. No path was reused or overwritten.

The first complete implementation receipt `-11` remains preserved at 11,647
bytes, SHA-256
`3cfa39591486e3540325d005511a985e4c5284d3a809f3c7f62006c31ec9398a`,
regular mode `0400`, link count one. Independent review found that its decoder
accepted a CRC-valid MUX row without a result and that its Python
classification-name grammar was broader than the native parser. The `-12`
successor closes those findings and the related causal-execution and
execution-only-terminal state space; it is preserved at 11,647 bytes,
SHA-256
`c3b25c4f1eb193f6078eaef1ee92850e3920f41f2ee9a1c96c491cacd24d1975`,
regular mode `0400`, link count one. Re-review then found its source default
`OUTPUT_ROOT` still named `-11`: explicit `--output-root ...-12 --audit-only`
passed, but the ordinary CLI did not select current authority. The `-13`
successor changes that default and makes the MUX negative fixtures use a sole
MUX semantic so they reach the intended result/binding/execution gates. The
append-only rows citing `-11` and `-12` remain accurate historical records;
only the later successor row and eventual independent review may name `-13`
as current authority.

## Authority and next step

Independent Luna MAX review reproduced the default `-13` receipt and fresh
materialization, attacked the exact generated parser, encoder, driver-source
deltas, source-reachable semantic domain, decoder denial boundary, and
predecessor/V4 preservation, and issued scoped H0 PASS_GO. The append-only
`h0-candidate-witness-transport-review-7` row resolves exactly the existing
`candidate-witness-transport` topic and opens no second obligation.

Only a subsequent host-only candidate-build unit may compile the new PDIC source,
replace and bind row-72 module bytes, freeze the full 73-row byte manifest,
derive a new intent, and run build qualification. This report is not that unit
and authorizes no device action.
