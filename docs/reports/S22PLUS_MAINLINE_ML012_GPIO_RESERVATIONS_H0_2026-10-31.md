# S22+ ML012: retain the FYG8 board's GPIO reservations

Status: **READY_H0_AND_CURRENT_D0_NO_EXPERIMENT**.

ML011 remains consumed and closed healthy. This preparation has no grant or
experimental device effect. A90 and S20+ are untouched.

## Selected correction

Two-round Claude Opus 5.5 / Gemini 4 Argon High discussion selected a board-data
correction after inspection of the exact retained FYG8 live FDT. Its TLMM node
reserves GPIOs **36–39, 50 and 93**. ML011 inherited only **36–39** from the
minimal r0q base. ML012 adds the two omitted indices through the standard
`gpio-reserved-ranges = <36 4>, <50 1>, <93 1>` property in `g0q.dtsi`.

The retained live FDT SHA-256 is
`75593f93beef0fe659d595bc1eb23e515bcea8023b38256e808e5528bf891560`.
Its non-VM `qcom,waipio-pinctrl` binding consumes the vendor's explicit index
list before GPIO direction enumeration. Mainline consumes start/count pairs
before its corresponding enumeration. Both drivers have 211 GPIOs and map a
given index to the same physical control register despite different resource
bases. The corrected set therefore excludes the same six indices from this
registration-time read loop.

This is a supported port correction, not a diagnosis of ML011's reset. The
reservation does not establish why a pin was reserved, whether a read would
fault, or whether ML011 reached that loop. Its missing callback return cannot
rule out an ordinary return whose record was not retained.

## Scope and source checks

The compiled DTB comparison finds exactly one changed semantic property:
TLMM `gpio-reserved-ranges`. Kernel configuration, memory reservations, USB
supplies and node identities are unchanged. The new DTB SHA-256 is
`ecd378bd32dff7a70d7d26ec53aa55c9eea8b0d6cccbdeb8a6bf5bba69440e59`.

The independent compiled-DT scan covers GPIO tuples, direct/extended/inherited
interrupts, interrupt maps, hogs and pinctrl consumers. GPIO50's only named
pinstate consumer and its parent are disabled; no GPIO93 consumer was found.
There is no TLMM self pinctrl state or GPIO hog. General GPIO validity and
IRQ validity use separate bitmaps. Direct pinmux and hierarchical IRQ paths
are not universally blocked by the GPIO mask; this change is not advertised
as a blanket MMIO exclusion.

The V9 writer, callbacks, node catalog and all 3,914 events are retained. A
fresh candidate/key changes the bound frame bytes and therefore the Image;
it does not introduce new observation sites. Full kernel-source comparison
finds only the generated frame header changed, matching its existing producer.
The complete Image differs only in that frame table and its derived 20-byte
GNU build ID. Both executable sections and the complete symbol layout match
ML011 byte-for-byte. The initial frame-only comparison correctly rejected the
build-ID difference; both ELF note descriptors identify its exact scope.
Watchdog behavior, storage exclusions and original-A recovery are unchanged.

No execution-critical owner or decoder source changes. The existing V9
capability and terminal backend review remain current. Fresh artifact tests
and the consumer's exact entry/package review are still required.

## Parallel external-watchdog investigation

The requested independent H0 investigation rejoined the actual ML011
Image/ELF and embedded configuration to the retained FYG8 firmware path.
Both relevant Linux watchdog drivers are disabled, but that does not prove
firmware timers are disabled. The existing Gunyah service-UID mismatch remains;
enabling only the driver would not resolve the analyzed discovery path.

Two bounded actual-instruction fixtures distinguish a disabled generic
watchdog-object constructor from a separately enabled hypervisor-owned
watchdog initialization path. Neither establishes the guest/HLOS handoff
state, a candidate watchdog expiry, or a reset period. Retained watchdog text
belongs to other Android/XBL contexts, while NoC reason-string freshness
remains unproved. A GPIO-related stall followed by an external watchdog reset
is possible; neither component is diagnosed by ML011's missing return frame.

The requested hardware/firmware follow-up also identifies concrete threshold
and pet stores for one hypervisor-managed physical watchdog bank and separate
pet, threshold and enable/control stores for a TrustZone-managed bank. A
further TZ timeout configuration distinguishes initial and HLOS-accept stages,
without a complete active-object/reset-callback chain. Both firmware images
rehash to their original FYG8 extraction receipt; selected instruction spans
and stored configuration defaults were rechecked. No MMIO was executed.
These paths establish capability below Linux, not current arming or expiry.
Default constants are not measured reset periods. PMIC/PON, undervoltage,
thermal and PS_HOLD events remain distinct unproved categories.

This investigation supplies no new blocker to the GPIO correction and changes
no watchdog behavior. Its private reports and source/fixture receipts are under
`workspace/private/outputs/s22plus-mainline-ml012-watchdog-h0-20261031-1/`, with
the hardware follow-up in `hardware-firmware-followup/REPORT.md`.

## Qualification and admission

The new Image SHA-256 is
`6a7df4019545ba18038944a1126dc5bf9484a70c07c911309bf1e4cacb170e3c`.
The complete build has no compiler warning, error or section mismatch. Fresh
qualification passes 361 actual ARM64 writer cases, 16 independent actual-hook
cases and 11 real-MMU/EL fixtures, including PID1/worker contexts, no-map alias
exclusion, mapping cleanup and failed/interrupted recording. The hook fixture
retains mocked CPU/OF/mapping API limits; the separate real-MMU suite supplies
its stated translation and scheduler-context evidence.

The RAM-userspace-PID1 VM passes in 4.208 seconds, with complete raw evidence
and a successful offline recheck. Loader checks pass 20 linked cases and
1,051 copy cases, actual EL1/EL2 entry and EL3 refusal. Two boot-v4 images and
boot-only AP archives are byte-identical. These are H0 results, not physical
TLMM, USB or watchdog-margin evidence.

The 101 focused host tests, 13 admission negatives and maximum-size retained
result fixture are reused with their complete raw receipts and unchanged
source inputs. The synthetic maximum fixture has the identical event catalog,
dimensions, owner and key; the new candidate's actual production binding is
checked separately. The source packet uses repository-relative paths and does
not include `g0q.dtsi`; the reuse checker was corrected to consume that actual
schema. The changed compiled DT has its own fresh comparison and independent
consumer scan. No old evidence or approval was rewritten.

Final independent exact-artifact review is **PASS_GO with no findings**. It
verified 87 sources and 372 artifact/raw pins, independently redecoded all
3,914 frames and all 11 complete MMU buffers, checked the actual production
marker/entry consumers and package/ELF/key/CPIO joins, and verified unchanged
review/test reuse. The existing 39-source capability, 44-source backend and
two resident-worker inputs remain unchanged; no new activation was published.

Production image and task preparation from closed ML011 passed. One fixed
preapproval D0 invocation then produced seven successful, empty-stderr Android
health captures; the actual health projection agrees. No approval, grant,
experimental operation or unresolved F1 owner exists. Readiness is a snapshot:
if older than 300 seconds when an approval arrives, the same fixed read is
refreshed before opening the grant. The current foreground task already
permits that read. The existing mainline policy still requires its generated
exact one-operation approval, actual attendance and usable Download recovery.

| Receipt | SHA-256 |
| --- | --- |
| Exact marker qualification | `6dbc472b789f54659487c254d8874d31bb9b58213e03a892ac92f8e550acd528` |
| Independent artifact review | `0a3eef8c237c0f0b169e420fe876ae775a246416c5541e88f70c9b8492c6ece2` |
| Prepared task | `474f8b36b3ee7e9fd1c7d91ac5316e1cbc1ee5d238ea53eb34f0866a14fa1a98` |
| First fixed readiness | `5e2219abb3846d1f2e812728a441a742660e97de3e868df767610f6222405a97` |
| Preparation checkpoint | `b4ca5c1f24d77609fd6a08fb933d2b60cb383db0c4919bc789a816c7e3a19934` |

Private preparation: `workspace/private/outputs/s22plus-mainline-ml012-h0-20261031-1/`.
Discussion and source comparison:
`workspace/private/outputs/s22plus-mainline-ml011-next-discussion-20261031-1/`.

All four external calls completed without failure, refusal, fallback or tool
use. Claude reported four uncached input, 39,745 cache-creation input and
27,456 output tokens, including 20,989 thinking tokens. Its CLI list-price
equivalent was USD 0.867096, not subscription billing. Argon reported 57,544
input and 28,571 output tokens, including 20,369 thinking tokens, for 86,115
total; cost was unavailable. Account snapshots moved from 0% to 5% Claude
five-hour used and 63.36% to 60.69% Argon weekly remaining. These account-wide
changes are not exact per-call quota attribution; before/after records are
retained in the private usage ledger.
