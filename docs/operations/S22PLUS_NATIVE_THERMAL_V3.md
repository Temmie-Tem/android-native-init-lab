# S22+ per-sensor VALID thermal profile V3

Status: **H0 capability preparation; no live grant or temperature proof.**
Target: **SM-S906N / g0q / S906NKSS7FYG8**, G0Q board revision 12.
The first declaration is fresh P391 / `v0.2.0-rc.9` under the existing
[native baseline V2 owner](S22PLUS_NATIVE_BASELINE_V2.md): admitted P387 N,
one distinct E, normal exact N restoration after proved E health and timely
Download, and one exact Android A as failure-only fallback.

## Changed reading rule

P390 mapped all 16 selected sensors and bound both TSENS banks, but its added
TRDY-bit-0 precondition prevented every temperature read. The exact FYG8
`qcom,tsens-v2` dispatch selects `get_temp_tsens_valid`, which uses sensor VALID
without that precondition. See the [retained result and applicability audit](../reports/S22PLUS_NATIVE_THERMAL_V2_H0_2026-09-13.md).

V3 retains the V2 root, two resources, sensor mapping, version and enable checks.
TRDY is read once per eligible bank and retained with its presence flag, but its
value does not decide whether the selected status words may be read. Each mapped
sensor on an eligible bank receives exactly one status-word read per acquisition.
That one word supplies both VALID and the signed temperature. VALID clear or an
out-of-range value withholds that sensor; valid zero and negative values remain
measurements. No polling, delay, cached-temperature override or hardware
configuration is copied from the reference driver.

The 13 CPU locations, two GPU locations, one SoC DDR-region location, ranges,
coverage and maxima remain [V2's declarations](S22PLUS_NATIVE_THERMAL_V2.md).
DDR-region TSENS is not RAM-package or DRAM-die temperature. A bank error still
describes inability to perform its selected status reads; an eligible bank with
all VALID bits clear may have error 0 and no valid temperatures. Presence/mapping
masks distinguish that result from a bank whose status words were never read.

VERSION, ENABLE, TRDY and eligible selected status words remain the only TSENS
reads. There is no TSENS enable, calibration, reset, threshold or IRQ write,
additional ADC channel, GPIO/PMIC control, UFS query or GPU workload. The exact
battery ADC path, single conversion, one-second pacing, bounded EOC wait and
per-boot fault latch remain unchanged. Software acquisition freshness stays
bounded by the existing five seconds; hardware conversion age remains unproved.

## Composition and evidence

V3 composes the frozen V2 native templates and replaces only the eligibility
predicate and version identifiers. Both the actual PID1 and workers compile
the same validator, where valid temperatures no longer imply TRDY bit 0 set.
Metrics/views remain 304/656 bytes, but their magic values are V3-specific.
The text sample is `S22THERM3` and the frame is `RESIDENT_THERMAL3_FRAME`; V2 and
V3 cannot substitute for each other even though their private IPC sizes agree.
The external authenticated control wire and resident source profile do not change.

The shared host parser selects an immutable dialect from the registered observer
class. Default V2 retains its original TRDY predicate and labels; V3 retains the
actual TRDY value without using it as a temperature prerequisite. No shared
module-global switch or caller-supplied live dialect is introduced. The original
P390 native inputs, artifacts, profile, consumed claim and records remain
historical inputs, and its terminal must rederive with the V2 interpretation.

The existing sample/frame acquisition join, replay high-water marks, diagnostic
presence, 64-record ring, 768-byte row and 50,000-byte decoder limits remain.
Missing retained companions withhold temperature proof. Fixed health, session
and CONTROL deadlines, one-shot roles, original grant expiry and recovery are
owned by the unchanged baseline policy. Optional missing temperatures do not
replace health or authorize replay; unexpected session failure retains only A.

## Qualification boundary

H0 covers TRDY `1/0/8` crossed with VALID `1/0`, exact per-sensor read counts,
partial values, zero/negative/range limits, forbidden reads after failed mapping
or version/enable checks, stale/replayed samples and battery faults. It exercises
the actual producer, collector, PID1, frame reader and N/E/N owner, including
same-size V2/V3 sample and view magic rejection. Exact ARM64 A/B init, renderer,
module and boot-only AP contents and their complete metadata must rederive.

Current P387 admission/native identity and the retained P390 terminal must reopen
unchanged. The changed host/native closure requires independent review before a
fresh exact request is issued. H0 and code issuance create no grant. Actual
CPU/GPU/DDR/battery availability requires fresh accepted evidence from a future
separately approved attended run; this definition does not predict those values.
