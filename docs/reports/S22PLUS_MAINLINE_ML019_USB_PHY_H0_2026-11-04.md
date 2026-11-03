# ML019: resume full RAM boot with corrected USB2 PHY setup

Status: **H0 qualified, independently reviewed and fixed preapproval D0
healthy; exact attended approval pending; no ML019 grant or device control**.

After the completed [ML018 entry-park experiment](S22PLUS_MAINLINE_ML018_RUN_2026-11-04.md),
two rounds with Claude Opus 5.5 and Gemini 4 Argon High selected one functional
successor. ML019 resumes the ordinary kernel/RAM PID1 path and corrects the
USB2 PHY reference-clock mask/value order plus nine supported device-tree
tuning fields. The bounded objective is authenticated RAM PID1/USB access
followed by healthy original-A return. Installed Debian remains a later step.

The operator's direction is reflected in this choice: prioritize a usable
mainline boot, reuse unchanged validation, and keep detailed historical fault
attribution optional. ML018's one-park unit is complete. There is no new
instrumentation ladder, watchdog experiment or observability prerequisite.
Exact target/artifact identity, finite authority, recovery and no-replay
boundaries remain unchanged.

## Concrete source change

The exact Linux 7.2.11 SNPS FEMTO driver calls a helper declared as
`write_mask(base, offset, mask, value)` with the reference-clock mask and value
reversed. For this field the old call leaves bit 0 unchanged, while the
corrected call sets bits 1:0 to binary `10`. Only the reachable initialization
call changes; host-only AUTO_RESUME and all other driver operations remain
unchanged. The corresponding [Qualcomm patch submission](https://lkml.iu.edu/2610.0/09839.html)
corroborates the correction; its publication does not establish merge status
or device behavior. The retained Samsung source's normal initialization uses
the corrected mask/value order after PHY reset.

The retained FYG8 device-mode DT has four tuning writes. The selected upstream
driver supports nine properties covering their defined fields:

| Property suffix after `qcom,` | DT value |
| --- | ---: |
| hs-disconnect-bp | 2156 |
| squelch-detector-bp | -2090 |
| hs-amplitude-bp | 2670 |
| pre-emphasis-duration-bp | 20000 |
| pre-emphasis-amplitude-bp | 40000 |
| hs-rise-fall-time-bp | -4100 |
| hs-crossover-voltage-microvolt | 0 |
| hs-output-impedance-micro-ohms | 0 |
| ls-fs-output-impedance-bp | 0 |

These map to `e7`, `0f`, `2f`, `03` in the supported fields at offsets
`6c`, `70`, `74`, `78`, with masks `e7`, `ef`, `3f`, `0f`. All three
zero-valued DT properties are explicit updates, not omitted defaults. The exact
C table entries are checked, including valid final entries. Unsupported
values that could fall through to a table endpoint are rejected by qualification.

The Samsung consumer writes full 32-bit registers; the mainline consumer
preserves bits outside its supported masks. This is mapped-field parity,
not full-register parity or a measurement of live vendor values. Vendor
EUD early return and runtime debugfs/sysfs overrides are not ported or measured.
Physical post-reset values and whether this path is reached remain unknown;
the reference-clock fix can be a no-op if bit 0 is already zero. Neither change
is claimed to explain an earlier failure.

The patch is applied with zero fuzz only to a fresh private kernel source
copy. Shared base sources and consumed artifacts are preserved. GPIO 36–39,
50 and 93 reservations, disabled TLMM, kernel configuration, clocks, supplies,
reset order, USB role and storage exclusion remain as in ML017. Ordinary V1
loader/entry writers are retained; the entry park is absent.

## Validation and review

The focused fixture compiles verbatim actual driver tables, property lookup,
mask/write helper and complete initialization function for host and ARM64.
It reads the real baseline/candidate DTBs through retained libfdt. Supply,
clock, reset and MMIO services are mocks, so this proves code behavior under
those inputs rather than physical PHY behavior.

All 32 baseline/candidate host/ARM64 cases pass across four register seeds and
four resource-failure paths. The intended field changes preserve outside bits;
all other writes and power/clock/reset event sequences agree. The nine tuning
writes occur inside the override/POR window. Failed resource operations produce
no MMIO writes. Four negative inputs reject missing/extra properties,
out-of-range values and an in-range value absent from the exact driver table.

The first fixture link attempted an unavailable bundled-libfdt symbol and was
repaired before any PASS; its failed output remains private. The negative
test runner's exception type was corrected without changing the checker.
Touched Python compiles; the fixture, kernel PHY object and RAM init are ARM64
and inspected with `file`. Complete kernel production passed without compiler
warnings, errors or section mismatches. The full source-tree comparison finds
only the fresh V1 frame and single PHY call change, plus the patch utility's
preserved `.orig` file, verified byte-identical to the baseline. The compiled
DT differs in exactly nine properties; the kernel configuration is identical.

- 342 actual V1 writer cases and six real-EL marker cases pass.
- 20 linked-loader cases, 1,051 aligned-copy cases and three real-EL loader
  entry cases pass.
- The new kernel/RAM PID1 VM passes in 4.901 seconds and its complete raw
  evidence rechecks.
- Two boot images and boot-only AP packages are byte-identical.

These qualify the new artifacts in H0. Physical RAM PID1/USB and automatic
recovery remain unproved. Final independent artifact review returned
`PASS_GO` with no findings, binding 100 sources and 313 artifact/raw pins.
It independently reproduced all 32 PHY cases and both init ELFs, verified the
compiled PHY initialization in the object, vmlinux and shipped Image, checked
the unparked entry path, revalidated authenticated VM raw evidence, and joined
the embedded payloads and both AP round trips. The current normal V1 admission
was exercised without stubs. The review receipt is retained privately.

The existing mainline capability and backend V27 source closures pass their
actual production checks unchanged. Independent review confirms that these
candidate-only edits do not require a capability rollover. The existing
capability and backend V27 receipts are reused; no source selector, policy or
old receipt is repinned. H0 results create no device authority.

The unmocked production image/task consumers and connector binding pass.
The new task inherits only the exact original-A recovery evidence from closed
ML018. The connected worker reports the same V27 backend and unchanged stable
worker sources. One fixed preapproval D0 completed; all seven complete,
successful raw captures rederive exact current original-A health. No F1 owner,
operator approval record, grant or candidate dispatch exists. Fresh effect-time
checks and the exact finite attended approval remain required before transfer.

Applicable past-failure rows are ARTIFACT, SEMANTIC, WIRE, ROUTE, PERSIST and
RETURN: exact producer/package joins, limited interpretation of static markers,
actual raw consumers, selected current capability, durable evidence and original
recovery ownership. No new control, reset or storage effect is introduced.

Private preparation is under
`workspace/private/outputs/s22plus-mainline-ml019-h0-20261104-1/` and discussion
under `workspace/private/outputs/s22plus-ml018-next-discussion-20261104-1/`.
A90, S20+ and initial unrelated changes remain untouched.

## External discussion accounting

All four calls completed without retries or fallback. Claude reported four
uncached input, 31,427 cache-creation input and 13,939 output tokens, including
7,773 thinking tokens. Its five-hour account meter moved from 7% to 10% used.
Argon reported 46,755 input and 20,971 output tokens, including 14,498 thinking
tokens, for 67,726 total. Weekly remaining moved from 95.81% to 93.56%; the
unchanged display after the first call did not imply zero use. Account-wide
percentage changes are separate from per-call tokens. Before/after records
are private; Claude's USD 0.530212 price equivalent is not a subscription
charge, and Argon cost is unavailable.
