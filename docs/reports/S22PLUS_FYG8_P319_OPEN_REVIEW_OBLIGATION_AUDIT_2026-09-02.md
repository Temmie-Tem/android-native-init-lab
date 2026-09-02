# P3.19 open review obligations — host-only audit

Date: 2026-09-02
Target: Samsung Galaxy S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`
Tier: H0 process audit
Device contact: none — zero ADB, USB, Odin, reboot, transfer, rollback or replay
Authority: none. This audit discharges no review obligation, qualifies no
capability, and does not retire, weaken, or supersede any finding from any
prior independent review. Only a same-topic independent `PASS_GO` resolves an
obligation; nothing here is one.

## Why this audit exists

`s22plus-fyg8-p319` was closed at `2026-08-30T08:34:52Z` with seventeen review
obligations still open. The campaign that owned them is closed and the loop has
moved to P327, so no current unit is positioned to discharge them.

## Measured state

Computed by `audit_review_obligations` in
`workspace/public/src/scripts/revalidation/s22plus_fyg8_campaign_ledger_taxonomy.py`
over all 455 rows of `docs/operations/CAMPAIGN_LEDGER_S22PLUS.md`:

| | |
|---|---|
| total obligations | 78 |
| resolved | 60 |
| unresolved | 18 |
| unresolved belonging to P3.19 | 17 |
| unresolved belonging elsewhere | 1 (`closed-result-publisher`, opened 2026-09-01) |

The seventeen, in the order they opened:

| opened | topic | pending ordinal |
|---|---|---|
| 08-17 | `raw-first-observer` | `h0-raw-first-observer-2` |
| 08-17 | `acm-control-requalification` | `h0-acm-control-requalification-1` |
| 08-17 | `guard-fixture-invalidation` | `h0-guard-fixture-invalidation-1` |
| 08-18 | `stage-b-rederivation` | `h0-stage-b-rederivation-1` |
| 08-18 | `boundary-failclosed` | `h0-boundary-failclosed-1` |
| 08-18 | `stage-b-reg-runner` | `h0-stage-b-reg-runner-1` |
| 08-18 | `log-harvest-runner` | `h0-log-harvest-runner-1` |
| 08-18 | `auditor-stale-bytecode` | `h0-auditor-stale-bytecode-1` |
| 08-18 | `usblog-parse` | `h0-usblog-parse-1` |
| 08-18 | `last-kmsg-retention` | `h0-last-kmsg-retention-1` |
| 08-18 | `mux-module-chain` | `h0-mux-module-chain-1` |
| 08-19 | `stock-choreography` | `h0-stock-choreography-1` |
| 08-19 | `usb-role-state-runner` | `h0-usb-role-state-runner-1` |
| 08-19 | `evidence-crosscheck` | `h0-evidence-crosscheck-1` |
| 08-23 | `fyd9-fyg8-usb-delta` | `h0-fyd9-fyg8-usb-delta-33` |
| 08-23 | `usb-recovery-control-correction` | `h0-usb-recovery-control-correction-35` |
| 08-23 | `stock-recovery-control-result` | `h0-stock-recovery-control-result-36` |

## Finding 1 — this is a steady state, not a lapse of attention

P3.19 issued 55 `PASS_GO` rows. The campaign reviewed heavily; it did not skip
review as a practice.

Replaying the ledger row by row, the unresolved count over the 96 rows after
`2026-08-23T16:11:47Z` — the moment the last of the seventeen opened — ranges
from 17 to 20 and ends at 18. The floor is exactly these seventeen. Every
excursion above 17 is a new obligation opened and then resolved.

By the loop's own accounting, carried in the row text, the tail moved from
`54 total / 36 resolved / 18 unresolved` on 08-23 to `75 / 57 / 18` at the end:
twenty-one obligations opened and twenty-one resolved, none of them these.

The backlog was never invisible. Most rows in this range state the number in
prose — "changing full-tail review-obligation accounting from 53 total / 36
resolved / 17 unresolved to 54/36/18". The count was computed, written down,
and carried forward unchanged for fifteen days.

The loop's self-reported total and resolved counts (`75 / 57`) differ from the
taxonomy's (`78 / 60`) by three, which is the legacy-mapping population. The
unresolved figure, 18, agrees. This audit does not resolve which denominator is
canonical; it notes only that the disagreement does not touch the debt.

## Finding 2 — two of the seventeen are runners that were pointed at the device

| pending row | opened | collected | elapsed |
|---|---|---|---|
| `h0-stage-b-reg-runner-1` | 08-18T19:42:00Z | `stage-b-reg-1` D0 | 113 s |
| `h0-usb-role-state-runner-1` | 08-19T02:13:12Z | `usb-role-state-1` D0 | 7 m 20 s |

Both collections were `HEALTHY`, `0/0` transfers, and read-only. Both were made
under explicit operator approval, and `stage-b-reg-1` additionally under the
`--accept-vdm-int-clear` acknowledgement its own runner requires. **The device
gate was satisfied.** Nothing here says an unreviewed script was fired at the
device unsupervised.

What lapsed is a different gate. `AGENTS.md:280` requires one independent
review when a boundary or a hazard changes, and `h0-stage-b-reg-runner-1`
declares its own hazard in its own row: reading `/sys/class/mxim/debug0/reg`
consumes a latched `REG_VDM_INT`, so a path the campaign had called a read is a
state change. The collection row records that the cost was zero on that run
because `VDM_INT` read back `0x00`, and correctly declines to treat that as a
reason to drop the gate. The hazard is real, declared, and still unreviewed
fifteen days later.

The two gates are independent by design, and the audit's point is only that
passing the device gate did not, and does not, advance the review gate.

## Finding 3 — two more are formally open but factually examined

`h0-raw-first-cross-target-membership-review-27` (08-21T15:40:00Z) and
`h0-raw-first-population-diagnostic-review-28` (08-21T16:30:00Z) are
independent `PASS_GO` rows that pin the raw-first auditor's post-08-18 bytes by
exact digest and report its suites passing 18/18 and 20/20.

Both scope themselves explicitly and narrowly — "resolves only
`h0-raw-first-cross-target-membership-27`" and "resolves only the
population-diagnostic classification closure, not an enforcement upgrade". An
independent reviewer therefore held the changed auditor in hand, twice, and
declined to extend qualification to the 08-18 acquisition-rule change.

That declination is correct under `AGENTS.md:283` — a `PASS_GO` qualifies a
named capability, not whatever else happens to be in the file. But the
consequence is that `raw-first-observer` and `boundary-failclosed` are open in a
weaker sense than the rest. The right disposition is a scope extension or an
explicit statement of coverage, not a review from scratch.

## Disposition

Four classes, ordered by what a defect would cost.

**A. Enforcement machinery, genuinely unexamined — highest.**
`auditor-stale-bytecode`, `guard-fixture-invalidation`, `evidence-crosscheck`.

These decide what the repository's own audits accept. `auditor-stale-bytecode`
closes a hole where the auditor could report one set of constants while
auditing under another; a defect in that fix silently un-binds every receipt
later units cite. `guard-fixture-invalidation` records that the observer
migration regressed a campaign the ledger still carries as `PROVED` and
`HEALTHY`, and deliberately left two guard fixtures unrepaired. Both rows state
in their own text that they carry a review obligation because they change a
boundary. `evidence-crosscheck` is the machinery that recomputes rather than
pins — the guard against a green test on a wrong number, a failure that had
already occurred once in this campaign.

**B. Device runners — review before any reuse.**
`stage-b-reg-runner`, `usb-role-state-runner`, `log-harvest-runner`,
`acm-control-requalification`.

Finding 2 covers the first two. `log-harvest-runner` carries a refusal contract
against `dmesg` ring-clearing forms and has not been collected. The fourth is
not a runner but the standing record that the migrated common CDC-ACM observer
**has no passing positive control** — the unit repaired two plumbing failures
and deliberately stopped at the semantic one rather than hand-fit the fixture
to green. That state has not changed since.

**C. Formally open, factually examined — cheapest to close correctly.**
`raw-first-observer`, `boundary-failclosed`. See Finding 3.

**D. Analysis and claims, no machinery.**
`mux-module-chain`, `stage-b-rederivation`, `last-kmsg-retention`,
`usblog-parse`, `stock-choreography`, `fyd9-fyg8-usb-delta`,
`usb-recovery-control-correction`, `stock-recovery-control-result`.

One of these is load-bearing rather than archival. `mux-module-chain` is the
row that produced the campaign's current live hypothesis — that a native-init
candidate never runs `modprobe`, so `pdic_max77705.ko` never loads, so
`com_to_usb_ap` never runs and the D+/D− pair is never routed. The ledger
references `pdic_max77705` thirty-one times and `GOAL.md:130` builds on its
dependency closure. It also holds an F1 approval recorded unconsumed and
deliberately retargeted, and it corrects a reading published earlier in the
same report. The current frontier rests on an unreviewed row.

The rest are analyses whose conclusions have already been absorbed downstream:
three of them exist specifically to retract or correct an earlier claim
(`stage-b-rederivation` a false sysfs claim, `last-kmsg-retention` two July
conclusions including a false-positive panic detection, `stock-choreography` a
stale unavailability claim). Retractions that were never independently reviewed
are a milder risk than unreviewed machinery, but they are also the cheapest
class to close, because the work is reading rather than re-deriving.

## Recommended order

1. `auditor-stale-bytecode`, `guard-fixture-invalidation`, `evidence-crosscheck`
2. `stage-b-reg-runner`, then the other three in class B
3. `mux-module-chain`
4. `raw-first-observer` and `boundary-failclosed` as a scope extension
5. the remaining seven in class D, together, as a single reading pass

Alternatively, if the operator judges that some of these no longer warrant the
cost, the contract-clean way to clear them is an explicit recorded retirement
with a stated reason per topic — not silence. Seventeen obligations sitting at
a constant floor for fifteen days is the outcome that neither reviewing nor
retiring produces.

## What this audit does not claim

- It does not assert that any of the seventeen units is defective. None was
  re-derived, re-executed, or read for correctness here.
- It does not assert that any device action was unauthorized. Both D0
  collections in Finding 2 record explicit operator approval.
- It does not assert that the raw-first auditor is unsound. Finding 3 records
  the opposite: it was independently examined twice, under a narrow scope.
- It does not distinguish, for class D, which conclusions later work has already
  re-derived independently. That would require reading the successor units.

## Limitations

The obligation set is derived entirely from the ledger's own topic keying.
A unit whose follow-up work landed under a different topic string appears open
here even if the substance was covered; Finding 3 is the one case where that
was checked and found to be partially true. Four topics were spot-checked
against later rows for supersession; the other thirteen were not.

## Method

Host-only. The ledger was parsed with the repository's own taxonomy auditor
rather than by hand. Counts, the 96-row replay, the two collection intervals,
and the two 08-21 scope statements were each read from the ledger rows named
above. No file outside `docs/` was modified and no test was changed except the
taxonomy row-count anchor this row's own append requires.
