# S22+ P389 temperatures and admitted-native roundtrip preparation

Status: **H0 qualification complete; independent PASS_GO with no findings.**

The operator requested CPU/battery temperature support and a fresh
`native -> development -> native` test. P389 / `v0.2.0-rc.7` adds the
[thermal profile](../operations/S22PLUS_NATIVE_THERMAL_V1.md) as a distinct E
under the existing [native baseline V2](../operations/S22PLUS_NATIVE_BASELINE_V2.md)
owner. P387 remains the exact admitted N. This work has made no device contact,
opened no grant and created no new native admission. Physical attendance and a
separately returned exact finite approval remain prerequisites to the live test.

## Diagnosis and implementation

The retained P387/P388 observations had fresh system/gauge data but no valid
CPU or battery temperature. The native collector's CPU coverage was zero. The
existing gauge provider supplies SOC, voltage and current; it does not supply
battery temperature. Temperature modules exist in the sealed vendor ramdisk,
but the current native module plan does not load them. Absence from that plan
must not be reported as absence of the files from the inherited vendor image.

P389 preserves the resident control framing, lifetime, IPC, fixed command set
and native/Android return machinery. Its fixed loader adds the inherited
`qcom-vadc-common.ko`, `qcom-spmi-adc5.ko` and new temperature provider, in that
order. The new renderer accepts only fresh acquisitions from this provider and
records the displayed battery value in a separate thermal HUD dialect.

The CPU provider validates both TSENS banks and the unchanged 13 named CPU
sensor mappings. It reads enable/version/readiness and valid temperature
registers without modifying TSENS control or thresholds. CPU maximum and
available-sensor coverage remain separate. The battery source is the board's
named ADC channel `0x14b`, shared with WPC temperature. Its scale-function-5
output is microvolts despite `IIO_TEMP` metadata; the exact board table converts
that to signed tenths Celsius. The current stock IIO callback's success return
is `IIO_VAL_INT` (1), not zero.

Battery sampling performs the stock ADC7 configuration and conversion writes
and uses its EOC IRQ. It borrows the existing battery device/IIO references
without binding a battery driver, avoiding that node's charger/WPC/OVP pinctrl
selection. Failed conversions, unexpected formats and out-of-table values stop
further ADC conversions for that boot. No earlier temperature is relabelled
fresh. CPU observation, battery availability and command health are independent.

The actual fast C/PTY fixture initially exported only the first `WAITING` frame
before the asynchronous collectors had produced a rendered sample. P389 now
settles for three seconds immediately before the existing fixed HUD export,
inside the original 60-second observer deadline. Other profiles retain zero
settling. A grant expiring during that interval stops further native roles and
permits only the prebound exact Android recovery.

## Artifact and source bindings

| Role | AP bytes | SHA-256 |
| --- | ---: | --- |
| Preserved admitted P387 N | 31,150,121 | `98bc0e8f2f902a5e587afd9fe2a0f3ed61efed65a21efe0e9acf03b8414e9565` |
| Fresh P389 E | 31,293,481 | `4fe89df2617927e058578e66e6728ec43b2bb8649a0291a87e186d5e7c4c3873` |
| Existing exact Android A | 23,367,721 | `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56` |

P389's Image is an identity-only transform of the frozen platform:
`fe8dfd63799efba54387e9071a5394a80e6758293c673d59f5f1c7bc55370f05`.
The module/renderer/init and actual boot-only AP A/B pairs match. All 7,222
Image export/CRC entries remain equal to the provider qualification Image, and
the three added modules resolve against that Image and their preceding provider.
Independent binary inspection also confirmed the stock ADC7 configuration,
conversion, IIO return and voltage-scaling paths. This is not a claim of complete
binary/source equivalence or a live sensor observation.

All **121 P387 native source inputs** remain unchanged. Its original admission
and latest `NATIVE_CLOSED` terminal rederive under the new host reader and equal
the refreshed N request identity. The terminal remains a past snapshot. The
previous P387/P388 approvals, installation claims and journals are unchanged;
P388 remains permanently consumed.

The final reachable host closure contains **195 sources**. Sorted compact JSON
with one trailing newline has these SHA-256 identities:

- Current working tree: `f0398218c47021381a2703a3671db5c080a7cbcd4d8b4aada6a1767e4861ffea`.
- Selected publication: `774282196eb07234efa1df18e4f58fe4e88320a0a876d4dbfa6614143e96aa7d`.

Their sole difference is the pre-existing uncommitted S20+ closed-history text
in `AGENTS.md`; the common details digest and S22+ rules are identical. The
consumed local review receipt is preserved privately before its replacement by
a new source-qualified capability review. Unrelated S20+ edits are excluded from
this unit's publication.

Independent reviewer `p386_terminal_review` returned **PASS_GO**, no findings,
for both exact variants after rederiving the final artifacts, admission and
combined request. The new capability receipt qualifies these sources only;
it creates no grant and provides no live temperature proof.

## Validation and limits

Twenty-one regression tests pass, including the actual kernel-wrapper/collector/
HUD path, new C/PTY/IPC N/P389/N operation, missing temperatures, expiry during
settling, retained baseline-owner cases and interruption/no-replay corpus.
Three additional real-artifact tests reject 25 mutated package, runtime and
provider metadata publications. Python compilation, ARM64 ELF checks, selected
links, repository boundary checks and `git diff --check` pass.

Independent review found that the first thermal audit did not regenerate all
published metadata even though it checked actual AP contents. The repaired
reader reconstructs the complete provider/runtime/package projections, joins
standalone LZ4 bytes to the actual AP frame and rederives archive structure.
The final mutation corpus exercises that actual reader with unchanged real
artifact parsers; original H0 records are preserved.

Fresh P387 and P389 static bundles pass. The complete **368,785-byte** combined
N/E request reopens through the actual publisher/reader with exact native-role
validation. That probe uses `H0_UNBOUND`, resides outside the grant namespace,
and grants no authority. Its SHA-256 is
`df6ed65ea115be4c66cc2d5bf3a9e303f55a250956a5b0a24b7730b3d39c78eb`.

Private evidence is under
`workspace/private/outputs/s22plus-temperature-native-h0-20260913-1/`; the final
P389 package is under `workspace/private/outputs/s22plus-native-thermal-v1/p389/build-2/`.
Actual CPU/battery values, physical pixels and this new E's live N/E/N roundtrip
remain unproved. TSENS hardware conversion age is unknown; the battery result
is a single board-ADC conversion, not stock's five-read filter. Normal healthy N
restoration and failure-only exact Android A recovery remain distinct.
