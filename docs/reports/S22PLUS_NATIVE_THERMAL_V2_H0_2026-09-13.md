# S22+ P390 CPU/GPU/DDR thermal V2 H0 qualification

Target: **SM-S906N / g0q / S906NKSS7FYG8**, G0Q board revision 12.
Scope: implement the thermal successor and prepare one exact finite F1 request.
Device contact, grants and candidate transfers during this H0 unit: **0**.

## Result and evidence limits

P390 / `v0.2.0-rc.8` fixes the CPU provider's DT parent and adds two GPU
locations plus one **SoC DDR-region** location. It retains per-sensor values,
coverage and bank diagnostics through the provider, collector, actual PID1,
renderer and bounded authenticated HUD export. Missing data remains unavailable;
valid zero and negative temperatures are retained. This is H0 qualification.
Actual CPU/GPU/DDR values, physical display pixels and P390 live N/E/N remain
unproved until an independently authorized device run.

The [thermal V2 profile](../operations/S22PLUS_NATIVE_THERMAL_V2.md) defines
the exact surface. The [prior census](S22PLUS_THERMAL_SENSOR_CENSUS_H0_2026-09-13.md)
supplies the retained stock DT evidence and separates DDR-region TSENS from
RAM-die temperature. UFS, additional board ADC channels and PMIC sensors remain
outside P390. The existing single battery ADC conversion, pacing and fault
latch remain explicit effects. TSENS reads do not enable or configure hardware.

The existing [native baseline V2 policy](../operations/S22PLUS_NATIVE_BASELINE_V2.md)
owns admitted P387 N, one distinct P390 E, normal restoration of exact N after
fixed E health and timely Download, and failure-only exact Android A recovery.
This work does not alter that policy, permanent boundaries, control protocol,
command list, child limits, capture bounds or attendance requirements.

## Implementation and qualification

The production provider now looks under `/soc/thermal-zones`. Positive fixtures
are generated from each of the four hash-bound stock base-plus-r12-overlay DTBs,
including exact resources, provider phandles, sensor IDs and the battery table.
The original incorrect root is a negative fixture. CPU mapping remains a
per-bank prerequisite; missing optional GPU/DDR mappings withhold only those
optional readings.

Per-bank diagnostics distinguish an unseen bank, a retained probe snapshot and
registers read during the current acquisition. Presence bits separate unread
placeholders from observed zero values. Every retained sample carries all 16
temperatures, validity/mapping masks, acquisition sequence and times, bank
diagnostics and battery conversion provenance. Software acquisition freshness
does not prove TSENS hardware conversion age.

E's actual PID1 and renderer compile the same generated extended IPC header:
304-byte metrics and 656-byte views, with new magic values. The unchanged N
keeps its original wire sizes. PID1 retains sequence/time high-water marks over
unavailable gaps. The host joins each frame with its sample companion; the same
acquisition must preserve its full sample and hardware sequence, while a new
acquisition must advance both sequences without overlapping acquisition time.
Missing evicted companions withhold temperature proof; duplicate, late or
conflicting companions fail validation.

Validation completed for this unit:

- **35 passing regression tests, no skips**, covering V1/V2 thermal units,
  actual generated C/PTY N/E/N execution, unavailable temperatures, battery
  failure with working TSENS, grant expiry during settling, legacy IPC rejection,
  owner recovery/no-replay and backend close/reopen behavior. The owner corpus
  includes the existing 21 publication cuts.
- **5 passing actual-artifact tests, no skips**, with 34 metadata mutations and
  four byte mutations against the actual helper, preserved child source and
  each init side. The real AP/runtime/provider readers reject disagreement;
  immutable boot parsing results are reused without replacing the parser.
- Real AArch64 builds and QEMU execution of the generated collector, acquisition
  IPC and old/new socket directions agree with host results. Matched formats
  accept; each crossed old/new direction rejects. Maximum-width sample companion
  is **525/768 bytes**; the fixed ring and decoder limits remain unchanged.
- The actual `paint()` path produced a 1080x2340 synthetic HUD. Visual inspection
  found separate readable CPU coverage, GPU, DDR region and battery rows.
  Its fixture temperatures are not device observations.
- Actual A/B native init, renderer, provider module and boot-only AP outputs
  are identical. The readers regenerate source/header identities, native helper
  composition, preserved child source, metadata, archive inventory and standalone
  LZ4/AP correspondence. Exact FYG8 Image import CRC checks pass.

Independent review found and closed two related host join defects: a reused
acquisition could change its retained sample, and an advancing acquisition could
reuse its hardware sequence. Both now have rejection regressions. A first H0
package attempt stopped before init compilation because the new builder omitted
the existing child-source input; the successor supplies and audits that exact
preserved source. Earlier H0 failure records remain private and unchanged. Final staged diff
validation found one extra newline at the end of the new probe fragment. Its
removal changes only one blank line in the generated provider C; the new
provider/package were rebuilt in fresh directories, nine V2 tests and the five
actual-artifact tests were rerun, and source/request bindings were regenerated.
Unchanged IPC, renderer, owner and backend checks were reused.

## Exact artifacts and retained N

| Role/artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| P387 N AP | 31,150,121 | `98bc0e8f2f902a5e587afd9fe2a0f3ed61efed65a21efe0e9acf03b8414e9565` |
| P390 E AP | 31,303,721 | `5f42d3e6b2d163c2c88de78cd057962be012e915f833898e40564c136726a349` |
| Exact Android A AP | 23,367,721 | `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` |
| P390 Image | 41,490,944 | `2d359b523cfe05c996c3ed2d0b1768484d4df8fef6afb9883e1be2b3b072650c` |
| P390 native init | 150,224 | `0c24a99943972816594c1d1a05279439d8693f5ec3ae49ea9f43545bfddf6082` |
| P390 renderer | 778,688 | `2c91a70b9b19407ac8a726940da56f9ea3209b2e39f686d0279e2d53b579e275` |
| P390 thermal provider | 332,920 | `95517b3f6c79c365c900ea40b6144e4cb87d9a72b1deb0c18734d7849385a837` |

The actual identity transform/inverse preserves Image bytes outside its two
declared identity spans. P387's **121 native inputs**, native build selection,
terminal and admission rederive unchanged. The latest retained terminal is the
closed P389 operation's restored P387 N, SHA-256
`5de43667d48baa8f33fe56c54c04250f8d49cdd00d41a1278502bb50ae3592ca`.
This is a past healthy snapshot, not a new device observation. P388/P389 remain
permanently consumed and their grants closed.

P389's consumed native sources, artifacts, profile and run records are preserved.
Its historical build metadata is not repinned to generalized host builders.
The new P390 package is separately qualified from current source.

## Review and request preparation

The frozen capability contains **207 reachable execution inputs**. Sorted compact
JSON with one trailing newline has these SHA-256 identities:

- Current working tree: `762b574096817bf5cd88d5abf5529baa8cfe0279d3fbf6e7ca3384fe519bb32a`.
- Selected publication: `1ae27503b63b6a43cb826864d5c27bba812a77db21f2c118ae1f386d4f090d0c`.

Only `AGENTS.md` differs between these variants: unrelated S20+ work remains
outside the selected publication. Both exact variants require independent review;
no source normalization or reader bypass authorizes a mismatched variant.

Fresh exact P387 and P390 static bundles pass. The complete **378,963-byte** N/E
request probe reopens through the actual publisher/reader and native-role
validation, with N equal to the retained terminal. Its SHA-256 is
`cec0faddb182ed7eef1ebcb3f00f0f37540f26c1507a518ed68a1ccd3d287c13`.
This probe is explicitly `H0_UNBOUND` with no authority receipt, outside the
grant namespace. Python compilation of 14 touched files, 48 local document
links, repository-boundary and diff checks also pass.

Independent review returns **PASS_GO with no outstanding findings** for both
exact final closures, build-3 AP and the combined request above. The selected
publication receipt is committed; the separately reviewed working-instance
receipt binds the actual local AGENTS bytes for subsequent H0 request preparation.
The exact finite request is issued only after that current reader passes.

Private evidence is under
`workspace/private/outputs/s22plus-native-thermal-v2-h0-20260913-1/`.
The actual P390 package is under
`workspace/private/outputs/s22plus-native-thermal-v2/p390/build-3/`.
No A90 or S20+ commands were issued, and no push occurred.
