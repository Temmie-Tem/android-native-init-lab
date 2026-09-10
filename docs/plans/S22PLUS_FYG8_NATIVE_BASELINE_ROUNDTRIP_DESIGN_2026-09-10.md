# S22+ native baseline Download roundtrip

Status: **P383 first-qualification owner implemented and independently reviewed;
no device grant or standing native baseline.**

Target: SM-S906N / g0q / S906NKSS7FYG8. This is the next proposed functional
unit after successful v0.1.2/P382 journal close. The new P383 candidate uses
functional label v0.2.0-rc.1 and its own freshly qualified artifacts. P381 remains consumed
NO_PROOF. The retained functional version is v0.1.2, mapped to consumed successful
P382 artifacts; neither historic candidate may be reused as a new N installation.

Implementation review found a higher-precedence omission: common F1 and the
permanent content-keyed consumed registry prohibit the repeated N transfer.
The [separate common exception](../operations/S22PLUS_NATIVE_ROUNDTRIP_FIRST_QUALIFICATION_V1.md)
is independently reviewed and incorporated as a dormant capability definition.
The prior design-only review does not cover this exception or activate the graph.

## Purpose and current gap

Demonstrate native PID1 -> exact Download -> the same qualified native boot
artifact -> newly authenticated native health. Future ordinary experiment
rollback could then target that exact native baseline rather than restoring
Android after every experiment. Android remains an independently bound emergency
fallback. Neither role is currently activated.

The ordinary path in the [target contract](../operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md)
requires one candidate, one exact Magisk rollback and final rooted FYG8 Android
health. Replacing only rollback_ap would violate its terminal assumptions and
the live runner's validators. Existing source-bound reviews and consumed run
records cannot be used as approval for the proposed transition graph.

The earlier root-console evidence establishes useful qualification checks.
It does not qualify an artifact as a native rollback destination, establish
cross-boot console freshness, or demonstrate kernel/PID1 stall recovery.

## Smallest bounded qualification transaction

Use an attended, finite qualification transaction with these predeclared roles:

| Role | Identity and purpose |
| --- | --- |
| Native artifact N | One newly qualified boot-only AP, exact archive/member digests and source closure; identical bytes on both native arrivals |
| Android artifact A | Present, readable, hash-verified exact current Magisk rollback; independently verified physical Download recovery route |
| First native boot | One N installation; establish fresh native identity, console health and ability to request Download |
| Native restoration | One separately declared N restoration attempt from exact Download; establish a different boot/session identity and the same artifact identity |
| Qualification cleanup | After collecting the native roundtrip result, one exact A restoration and current rooted FYG8/original partition health |

The successful initial qualification therefore needs three declared boot-only
transfers: N installation, N restoration, A cleanup. These are distinct roles
with separate one-shot intents under that common exception, never
retries of a consumed historic candidate.
The common exception and new lane must expressly permit and represent repeated N bytes across those roles;
the current one-candidate/one-rollback runner must continue rejecting that use.
P383 N is now A/B and statically qualified. Its exact identity and H0 results are
recorded in the [implementation report](../reports/S22PLUS_FYG8_NATIVE_BASELINE_ROUNDTRIP_H0_2026-09-10.md).

This first transaction ends in Android so it does not silently establish a
standing native session. Keeping native as the terminal baseline for later
experiments is a subsequent explicit adoption of the qualified native-health
profile, exact N and reviewed transition graph.

## Native health and evidence

Before each native arrival is called healthy, require:

- Exact target/transport and verified N transfer identity, joined to the
  native observer through the run binding. A self-reported image hash alone
  is insufficient to prove which image booted.
- Authenticated boot identity bound to native PID1 startup (for example, the
  per-boot kernel boot_id), different across the two arrivals, plus expected
  root-console protocol/version. A new challenge and a durable host arrival
  ordinal prevent stale-frame/session reuse; they alone do not prove a new boot.
- Numeric root, required proc/sys/dev mounts, a bounded command with complete
  stdout/stderr and terminal status, and a fresh STATUS after that command.
- The existing bounded CONTROL handling and an exact observed Download return
  where the transaction requires departure. ACK remains acceptance only.

No long soak, display/gauge requirement, memory cleanup or arbitrary repetition
is needed for this roundtrip criterion. Command budgets and the native deadline
are fixed before effects. A fresh boot has no inherited same-boot RAM-state
claim; the health probe must tolerate the intended loss of tmpfs content.

Raw authenticated traffic, transfer receipts and health observations are
published privately before interpretation. Journal transitions contain bounded
state and receipt hashes, using the repaired compact OBSERVED pattern. Track
first native health, Download arrival, N restoration, second native health,
and Android cleanup independently; a later cleanup does not prove a failed
native restoration. Host timestamps of recovered record publication are not
retrospective boot or timely-return observations.

## Failure and recovery

Each transfer or CONTROL intent is consumed before first delivery. Recovery
reopens durable intents, results and raw receipts; it cannot retransmit a
possibly delivered command or an already attempted N restoration. The design
must distinguish pre-effect refusal, completed effect, and uncertain effect.

On failed native health or unexplained native/session failure, stop research.
Only the new lane's explicitly preauthorized A fallback may continue, with
current exact Download/artifact/target binding and physical attendance. Failure
to observe software Download does not authorize another CONTROL. Use the
already demonstrated physical recovery path; park if it becomes unavailable
or target/effect identity is uncertain. A failed or uncertain A attempt also
parks without replay. A successful A return is recovery evidence only.

No unattended recovery, reconnect within one native session, automatic reboot
loop, native-to-native failure recovery or storage persistence is claimed.
Fresh authentication after a new boot is a separate declared arrival, not
reopening the closed console from the previous boot.

## Implementation and acceptance work

Before device use, implement the small role-aware transition extension and
native terminal-health profile in the existing F1 machinery. Reuse archive,
exact target, raw evidence, no-replay and transfer validation. Review the
changed common/target/process/schema/runner closure together, including the
explicit same-N specialization; do not relax permanent boot-only or
evidence boundaries. Preserve old run/schema recovery behavior.

Host tests must exercise the real journal and result writer through all three
transfer roles, native health success/failure, cuts around intent/result/health
publication, stale boot authentication, wrong N/A identity, missing fallback,
and failed/uncertain transfer without replay. Native code changes additionally
need strict A/B ARM64 builds and representative real ARM64 producer/consumer
checks for changed ABI or runtime behavior. Mocks are not target ABI proof.

Then a fresh candidate qualification, source-bound independent PASS review,
exact live preparation and finite attended grant are required. A completed
roundtrip with second native health plus successful Android cleanup qualifies
the bounded capability; it does not activate a standing native baseline.
If native restoration fails, retain NO_PROOF and report fallback/final health
separately. Any prospective baseline adoption must use exact successful N bytes
and the reviewed native-health profile, not a newly rebuilt image.

## Persistence is a separate later unit

No userdata repartitioning, new partition, filesystem formatting or persistent
write is needed for this boot roundtrip. Current RAM files disappear at reboot;
stream required evidence to the host before Download. Persistent native storage
would need its own concrete design and applicable authorization under the
existing partition/persistent-mutation boundaries. Do not couple that work or
the approximately 56 MiB RAM-file cleanup question to this qualification.
