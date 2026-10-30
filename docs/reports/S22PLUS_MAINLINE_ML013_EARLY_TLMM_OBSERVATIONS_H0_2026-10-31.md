# S22+ ML013: earlier retained evidence and bounded TLMM observations

Status: **READY_H0_AND_CURRENT_D0_NO_EXPERIMENT**.
No ML013 grant or experimental device action has occurred. ML012 remains
consumed and closed healthy. A90 and S20+ are untouched.

## Selected bounded change

Two-round Claude Opus 5.5 / Gemini 4 Argon High discussion selected one C
writer with a shared header/window latch. The candidate keeps ML012's
source-supported GPIO reservations, RAM PID1, USB2 observer and storage
exclusions. It adds no watchdog intervention or alternate recovery mechanism.

V10 adds three fixed points: immediately after early ioremap initialization
and before FDT setup, after `setup_arch` returns, and at entry to
`kernel_init_freeable`. The existing twenty fixed points, sparse regular
initcall selection and full node-association catalog remain. Lower event IDs
now occupy the newest end of the effective contiguous window. Short history
still admits the available priority slots. This improves their placement
under a forward-overwrite model; physical retention improvement is unproved.

The earliest valid header observation latches the window before checking that
event's own slot eligibility. An early latch requires header stability over
a longer interval. Observed drift disables later recording permanently, so
an early positive without later records cannot locate a failure. The format
does not combine an assembly writer, a second latch or another RAM region.

The exact TLMM association gains seventeen structural/return-class points in
three groups sampled at invocation entry: prepared before deferred arming,
deferred phase 1, and deferred phase 2. Only the first invocation admitted to
each group receives a local token, including when recording fails. Nested or
later invocations receive none. Steps retain the original group and task
owner across phase changes; a final return class closes the active token.

The original probe body and its early returns are preserved inside a wrapper.
It calls the body once and returns its unchanged value, recording only zero,
`-EPROBE_DEFER`, or another return class. Tokens pass into its sole GPIO helper.
No per-GPIO, lock-held or IRQ-handler observation is added. Independent removal
of only observer calls and token plumbing reconstructs the complete original
pinctrl source byte-for-byte. Linked inspection confirms the wrapper ABI and
original return preservation. Compiler-inlined GPIO paths may contain several
copies of one source return point; the per-event once bound still applies.

The declaration generates **3,968 frames**: 23 fixed, 51 TLMM, 84 sparse
initcall and 3,810 generic node events. Their 507,904-byte payload and maximum
539,648 byte stores remain within the existing ceilings. Generated C constants
and frames share the same event declaration. V9 sources and frame identities
remain available for their historical artifacts.

## Evidence limits and previous capture

Every record proves occurrence at least once in this candidate's attempts.
Static records do not establish shared boots, paired invocations, retry counts
or a last attempt. A TLMM return class does not prove a successful overall
boot or that the GPIO correction caused progress. Missing records identify
neither a failure location nor overwrite, short initial history or non-entry.

An offline content census of the complete ML011 and ML012 captures found
Android service-start text in ML012 that was absent in ML011. The exported
payload omits the writer's header, and text families cannot establish which
boot supplied those bytes. This does not prove an extra Android boot, a
retention failure or the cause of ML012's zero markers. The earlier failed
health prefix still has no boot ID. Recovery and complete final health remain
independent from this unresolved diagnostic.

## Qualification

The Image SHA-256 is
`38e9f617c89710901f53f8323590af82d8744a5a51661dd77f42c767ed2aea33`.
The configuration and corrected DTB match ML012. The ARM64 build has no
compiler warning, error or section mismatch.

- 361 actual ARM64 writer cases pass, including short history, invalid state,
  failed mappings, interrupted commits, seen-event consumption and sticky drift.
- Independent actual-instruction tests pass all 30 hook/lifetime/token cases.
  CPU state, OF APIs and mapping APIs are explicitly mocked there; the driver
  body is mocked only for the outer-wrapper return ABI tests. Independent
  complete-source conservation and linked disassembly cover that separate body.
- Fourteen real-MMU EL1/EL2 cases pass. They cover bootstrap, PID1 and worker
  contexts, early/late mapping, lower/upper translation-root geometry and
  alias exclusion, full pre-free traversal, cleanup, early/later drift and
  failed mappings. The whole early mark restores preemption count 1 after
  its writer observes count 2; later task/worker writes observe count 1.
- All 2,605,041 distinct short-history/modulo address states satisfy the fixed
  window, available-prefix and disjoint-slot bounds. Actual instructions
  separately exercise the maximum unsigned index and boundary cases.
- The production proof consumer accepts the complete artifact join and rejects
  ten altered proofs, including missing bootstrap return/translation geometry,
  false catalog claims, missing TLMM coverage and a hidden wrapper mock.
- The maximum synthetic capture contains 32,768 records spanning all 3,968
  events and serializes to 1,360,372 bytes, below the existing 2-MiB limit.
- 106 focused mainline tests and 78 approved-terminal tests pass.

The RAM PID1 VM passed with a complete offline evidence recheck. Loader checks
pass 20 actual cases and 1,051 copy cases, with actual EL1/EL2 entry and EL3
refusal. Two boot-v4 images and boot-only AP archives are byte-identical.
The AP SHA-256 is
`ec6dbd4947c9cce022e9a1662b4262f4e4c57a23ae61202df480ebdc6b0e8555`.
Counter-free VM timings between preparation and the final pre-free boundary
were 1.609 seconds at EL1 and 1.558 seconds at EL2. They are host/VM costs,
not physical timing, retention or watchdog-margin evidence.

Two H0 checker corrections preserve the candidate bytes. GCC moved the new
entry argument into the function prologue; the placement checker now executes
that exact prefix to verify the argument instead of assuming a `MOV` directly
before the call. One failure-injection VM reported a duplicate counter stop at
writer entry while adding a recheck breakpoint. Its log did not distinguish
actual re-entry from a repeated unadvanced debugger stop. A diagnostic replay
passed, and the adopted harness now single-steps the real first instruction,
requires PC advancement, then reenables the unchanged once-per-event counter.
No guest PC/register value is injected. All fourteen cases pass under that
harness. The initial failure remains preserved without a claimed cause.

## Admission state

Final independent review is **PASS_GO with no findings**. It binds 92 sources,
410 artifact/raw receipts, the 40-source capability, 44-source backend and two
unchanged resident-worker inputs. All fourteen complete MMU buffers were
independently rederived, along with the producer, consumer and package joins.
The exact review SHA-256 is
`f9a94d6022a2fca53841a04d40ce1fd5152af66718d24ee079efc3d16a4613df`.

The V10 capability and V21 terminal backend were published under that review.
The connected worker confirms the new backend and unchanged resident inputs;
it was not restarted. Independent publication checks confirm the exact new
receipt/selector/task joins and unchanged historical V9/V20 receipts.
Production image/task preparation from closed ML012 passed. One fixed
preapproval D0 obtained seven successful, empty-stderr health captures, and
the production health projection rederived them. No approval, grant,
experimental operation or unresolved F1 owner exists. Readiness is a snapshot;
the same authorized fixed read is refreshed if older than 300 seconds when
the approval arrives. No readiness, review or VM result grants device authority.
The existing mainline lane requires the generated exact one-operation,
1,800-second approval, actual attendance and usable physical Download recovery.
Original-A transfer and fixed health do not depend on retained-log publication.

| Receipt | SHA-256 |
| --- | --- |
| Exact marker qualification | `f5fbdb0a12a81e76b1fe1e74d6ee53ea4d62e745e964e8ebe104c76e4dae63a4` |
| Published V10 capability | `f3cb9cd250032c6c5c0232a7ee594098c677c293c7663059fcbc9a7ef37e0f8e` |
| Published V21 backend | `92a8416c41e2d32c2918ebda6f95431537af2c716aadce6c67c3e65eedff5823` |
| Publication instantiation review | `db98cd478012d13543ab3145c24ce8ef057db59f552e6a56d9dd6f90307f49e2` |
| Prepared task | `e4918ecf4d9368c4fd7fe73553febf24ca78226538d3d45cb49a527dfb723173` |
| First fixed readiness | `74546ccb1df265b6edaeb71f5783f6d100f3c4865df2b19c5e2db4be4c4f8b9b` |

Private preparation and raw qualification are under
`workspace/private/outputs/s22plus-mainline-ml013-h0-20261031-1/`.
The advisory discussion and content census are under
`workspace/private/outputs/s22plus-mainline-ml012-next-discussion-20261031-1/`.
All four external calls completed without failure, fallback or tool use;
before/after quota and token accounting are retained separately in the private
usage ledger. Account-wide quota changes and CLI list-price equivalents are
not attributed as subscription charges.
