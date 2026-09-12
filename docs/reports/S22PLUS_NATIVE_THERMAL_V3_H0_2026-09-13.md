# S22+ P391 VALID-based thermal V3 H0 qualification

Target: **SM-S906N / g0q / S906NKSS7FYG8**, G0Q board revision 12.
Scope: qualify the fresh thermal successor and issue one exact attended F1 code.
Device contact, grants, candidate transfers and native admission changes: **0**.
Independent review is **PASS_GO with no outstanding findings**. The exact F1
request is issued and revalidated; no grant has been created.

## Change and proof boundary

P391 / `v0.2.0-rc.9` removes P390's extra TRDY-bit-0 eligibility condition
from the producer, shared C validator and selected host observer. TRDY remains
an acquired diagnostic with its presence flag. Each mapped sensor on an
eligible bank receives one status-word read; that same word supplies VALID and
the signed temperature. VALID clear or a value outside -40..150 C withholds
the sensor. Zero and negative values remain measurements when valid.

The exact FYG8 `qcom,tsens-v2 -> data_tsens_v2 -> ops_generic_v2 ->
get_temp_tsens_valid` dispatch does not use TRDY as a precondition. The retained
[P390 result and source-getter counterexample](S22PLUS_NATIVE_THERMAL_V2_H0_2026-09-13.md#checklist-applicability-audit-2026-09-13)
establish why the extra condition was unjustified. That evidence does not
predict actual sensor VALID bits or temperatures after its removal.

The [V3 profile](../operations/S22PLUS_NATIVE_THERMAL_V3.md) retains V2's exact
root, resource, version, enable and sensor-map checks, 13 CPU locations, two GPU
locations, one SoC DDR-region location, ranges, coverage and battery ADC path.
There is no polling or TSENS configuration write. The existing single ADC
conversion, pacing, EOC bound and fault latch remain unchanged. Software sample
freshness does not establish TSENS hardware conversion age. DDR-region TSENS
does not establish RAM-package or DRAM-die temperature.

New native source composition leaves frozen V2 templates unchanged. The new
304-byte sample and 656-byte view use separate V3 magic values; their sizes
alone cannot distinguish V2 and V3. The text labels are `S22THERM3` and
`RESIDENT_THERMAL3_FRAME`. The shared host parser uses an immutable selected
dialect, with strict V2 as its default. No shared-global mode change occurs.
The external authenticated control wire, health workload, one-shot owner,
original deadlines and failure-only Android recovery remain unchanged.

## H0 validation

- **32 tests pass without skips**: V1/V2/V3 thermal units and actual generated
  PID1/collector/renderer C/PTY N/E/N tests. They cover unavailable temperatures,
  ADC failure with retained TSENS data, original grant expiry, healthy normal N
  return and prior-format packets rejected by the actual PID1. V3's prior-format
  negative uses an equal-size V2 sample, not only the shorter baseline packet.
- The actual provider crosses TRDY `1/0/8` with VALID `1/0`. Every eligible
  acquisition reads exactly 11 selected status words on bank 0 and five on
  bank 1, each at most once, plus one TRDY word per bank. Failed map/resource,
  version or enable preconditions gain no status reads. Partial coverage,
  valid zero, negative and out-of-range values, stale/replayed samples,
  diagnostic consistency and acquisition/frame joins are exercised.
- The exact target toolchain builds the actual provider harness, collector,
  sample validator and renderer view reader as static AArch64 ELF. Real QEMU
  AArch64 execution agrees with host output for all six cross conditions and
  collector normal/bounds/IPC/frame paths. Both directions of equal-size V2/V3
  sample and actual view rejection pass. These are modeled MMIO/IIO values;
  real ARM64 execution is not a live hardware observation.
- A crossed view reaches the actual renderer's `DISPLAY_FAIL` for
  `hud-snapshot-order` and parks for its external supervisor without accepting
  the packet. The first test incorrectly expected process exit and timed out;
  the corrected test verifies that bounded observation and terminates only
  its host fixture process. Production failure/recovery behavior is unchanged.
- Actual init, renderer, thermal module and boot-only AP A/B outputs are
  identical. Source/header and native-helper joins, preserved child source,
  module import CRCs, archive inventory and standalone LZ4/AP correspondence
  rederive through the existing readers. Maximum companion length is 525 bytes
  under the unchanged 768-byte row bound; ring and decoder limits are unchanged.
- **6 actual-artifact tests pass without skips**, including 36 metadata
  mutations and four byte mutations against the actual helper, preserved child
  source and each init side. V2 sample/view magic values in equal-size V3
  metadata fail the current reader. The actual AP/runtime/provider readers
  reject disagreement; immutable boot parser results are reused without
  replacing their parsing behavior.

The earlier owner/backend publication-cut
qualification remains applicable because those execution sources are unchanged;
the selected actual V3 roundtrip is also exercised above.

Both exact static bundles completed and preserved their PASS results before the
H0 wrapper tried to duplicate those two full results into one ordinary summary.
The 64 KiB record bound correctly rejected that oversized summary. This was a
wrapper error matching the existing PERSIST warning. The corrected close record
contains the two original result receipts; the actual writer/reader roundtrip
passes. The completed bundles, source pins and artifacts were reused unchanged.

## Exact artifacts and preserved evidence

| Role/artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| P387 N AP | 31,150,121 | `98bc0e8f2f902a5e587afd9fe2a0f3ed61efed65a21efe0e9acf03b8414e9565` |
| P391 E AP | 31,303,721 | `cfbd810dee86672744bbfcd88ec59231332f3470f4b32661a4b452597ce07690` |
| Exact Android A AP | 23,367,721 | `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` |
| P391 Image | 41,490,944 | `53346bf68bc13a2981d1b63cf449404970f79ab7af65f5dc25224da25eb8f399` |
| P391 native init | 150,224 | `411b12a6161e5839b1b4afd8be472050cb3efe0439f8b4c024011774ef410c51` |
| P391 renderer | 778,688 | `4bc4c7362ba824b4f44c8a1d6f2a4ef90ed49427d34bbfdebace79b114cf5617` |
| P391 thermal provider | 332,920 | `107e2fba3bb9eaf94b543f7718316899936dd58d5c8540ceaa144e611bf1b5b0` |

The real identity transform/inverse preserves Image bytes outside the two
declared identity spans. The current reader reopens P387 admission and the
closed P390 terminal, SHA-256
`ad377de602a54ff20444da663f641f6192cc93d08b677d5930481be4a3ceb41d`.
All 121 P387 native inputs and 138 P390 native inputs are unchanged. P390 retains
its strict V2 interpretation, consumed content claim, artifacts and run records.
No historical build metadata or result is repinned. Its native close is past
health evidence, not a new live observation or continuing authority.

## Review and request

The frozen capability contains **211 reachable execution inputs**. Sorted
compact JSON with one trailing newline has these SHA-256 identities:

- Current working tree: `f6bb3d2fb3d5e9649bc077d253d53e8b0c7cd44f0f946b87dc2c21c5ac7b6882`.
- Selected publication: `5a58ce4d1f2f08d338068bfd5eeedaf119ab60d60bf97a1aa689886937c2ae3a`.

Only `AGENTS.md` differs between these variants because unrelated S20+ work
remains outside this publication. Each exact variant must receive independent
review. No normalization or reader bypass makes a mismatched review current.
The new finite request binds admitted P387 N, fresh P391 E and one shared
exact Android A for one attended experiment within 600 seconds.

The complete **382,226-byte** combined N/E H0 request passes the actual request
constructor, publisher, reader and native-role validation. Its SHA-256 is
`cabf04f0f72f15c1c977c48df7b554da99101981546115ebb5ceb0fed1a1121f`.
Both native/source closures equal the already verified static bundles, and N
equals the retained P390 terminal. The probe uses `H0_UNBOUND` outside the grant
namespace and has no authority receipt. The bounded static-summary writer/reader
also passes with exact references to both preserved individual results.
Python compilation of 10 touched files, 51 local document links, repository
boundary checks and staged/unstaged diff checks pass.

Independent review returns **PASS_GO** for both exact 211-source variants,
the actual build-1 package and the complete request above, with no outstanding
findings. The selected publication receipt binds the published source variant;
the separately reviewed working receipt binds the actual local AGENTS bytes.
The latter must pass the current owner reader before exact request issuance.

## Issued request

Source publication is commit `91924d4a4d2047f3f8693867b848648b91440fc4`.
The separately reviewed working receipt passes `owner.reviewed`. The actual
`prepare_request` and `load_request(current=True)` complete successfully for:

- Run: `p391-valid-thermal-experiment-20260913-1` under the private native
  baseline V2 run root.
- Operation: one attended `P387 -> P391 -> P387` experiment; one reservation,
  600 seconds, one unchanged exact Android A as failure-only recovery.
- Request: **382,334 bytes**, SHA-256
  `156fc01de788ccdbf2a8a2fb02f6d9cf940a07c7782e3cedcc0e73ee4beb5cc7`.
- Approval: `S22PLUS_NATIVE_BASELINE_V1_APPROVE:` followed by that request digest;
  the existing owner retains this prefix for the V2 policy.

All **225 frozen input files** match after the actual current-reader reopen.
N and the exact private target equal the retained P390 terminal; the host epoch
matches and its successor link is unused. The global candidate preflight finds
P391 unused, no F1 owner is present, and the new run directory contains only
`request.json`. Private `request-issuance-close-result.json` records this H0 close.
No grant, reservation, content claim, native role or device contact was created.

The [finite attended operation policy](../operations/S22PLUS_NATIVE_BASELINE_V2.md#finite-attended-operations)
requires a separately returned exact approval, physical attendance and usable
physical Download recovery before effects, followed by the owner's fresh runtime
binding. Actual CPU/GPU/DDR/battery availability, physical display and the live
P391 roundtrip remain unproved by this H0 qualification.

Private evidence is under
`workspace/private/outputs/s22plus-native-thermal-v3-h0-20260913-1/`; the actual
package is under `workspace/private/outputs/s22plus-native-thermal-v3/p391/build-1/`.
This report includes no target serial, live raw capture or private key.

## Changed-path checklist

| ID | Status and evidence |
| --- | --- |
| ABI / SEMANTIC | Checked: exact FYG8 variant/getter trace, independent TRDY/VALID inputs, actual one-word read counts, range/freshness and ARM64 execution. Hardware conversion age and future values remain unproved. |
| WIRE / ROUTE | Checked: actual C provider through collector, PID1, renderer and host join; equal-size prior-version rejection; default V2 retention and consumed terminal reopen. |
| ARTIFACT / AUDIT | Checked: actual A/B outputs, source and module linkage, decoded AP; independent PASS_GO for both exact 211-source variants and the full request. |
| PERSIST | Checked: actual 382,226-byte N/E request writer/reader and native roles; retained terminal/admission reopen. The oversized H0 wrapper summary was corrected to original-result receipts and reopened without repeating bundle validation. |
| HOST / RETURN | Changed V3 path exercised through actual C/PTY owner. Control, grant, transfer and recovery sources are unchanged. Future physical return and device health require the separately approved run. |
| IO / DISPLAY | No new I/O bound or drawing behavior. Acquisition/replay and failure-park paths checked; prior synthetic HUD layout remains applicable. Future physical pixels are unproved. |
