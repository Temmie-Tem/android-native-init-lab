# A90 F1 failure analysis, pre-write reconciliation, and failed-boot evidence — H0

Date: 2026-08-21
Target: operator-owned Samsung Galaxy A90 5G only
Authority: none

This is host-only design and repair work. It creates no D0, D1, F1,
manifest, approval, token, device command, recovery command, or replay
authority. The current checkout remains on codex/p319-process-v2-integration
and all changes remain uncommitted.

## 1. Native pre-effect inventory boundary

H30 stopped before candidate or rollback transfer because the continuation
backend invoked adb devices -l while Native was visible over ACM. If the host
ADB server was absent, that read started the daemon and its normal startup
banner appeared on stderr. The strict producer wrapper classified the banner
as a failure even though no device operation had begun.

The repair separates the two endpoint roles:

- Native is identified by one Samsung USB endpoint with product 04e8:6861,
  the fixed managed ACM bridge preflight, and the existing ACM observation
  protocol. The Native role check does not invoke ADB and does not use an
  empty ADB inventory as a receipt.
- Recovery is identified by one Samsung USB endpoint with product 04e8:6860
  and one bound recovery ADB row. ADB is opened only in that recovery-scoped
  phase, after a Native recovery transition, or for an already-present
  Recovery endpoint.
- The first recovery-scoped ADB inventory may suppress only the exact
  daemon-start banner. The exact header, row grammar, endpoint count, bound
  serial hash, return code, quiescence, and all unexpected stderr remain
  strict. This is a producer-specific exception, not a general relaxation.
- The owner repeats the USB boundary immediately before the Native recovery
  frame and checks the Recovery USB/ADB role before push or boot write.
  Native and Recovery raw inventories are different epochs; the changed
  post-transition bytes are not compared with the Native bytes.

This repair preserves no-replay semantics. It only removes an unnecessary
Native-side host-daemon dependency and narrows the allowed producer
exception.

## 2. H30 pre-write reconciliation

The fixed H30 journal is the exact run recorded by
docs/reports/A90_H30_NATIVE_ADB_INVENTORY_PREWRITE_FAILURE_2026-08-21.md.
The candidate and rollback result receipts are both PRE_WRITE_FAILURE,
quiescent, and writeStarted=false. The reconciliation must bind, without
reinterpreting prose:

1. the exact run ID, manifest digest, candidate and V2321 rollback artifact
   identities;
2. the immutable prepared, approved, candidate-intent, candidate-launch,
   rollback-intent, rollback-launch, result, and terminal record bytes;
3. each result receipt to its complete private stdout/stderr log set and
   exact helper argv/duration envelope;
4. absence of every sealed-copy, adb-push, remote-hash, boot-dd-write,
   boot-readback, and TWRP System-return stage in both helper logs; and
5. candidateReplay=false, zero candidate/rollback writes, and no effect
   replay in the reconciliation result.

The host-only validator is
workspace/public/src/scripts/server-distro/a90_h30_prewrite_reconcile_v1.py.
The reconciliation is terminal-only and cannot select a new artifact, send
ADB, start TWRP, request recovery, write a guard, or retry either helper.
The consumed candidate and rollback protections remain in force. A missing,
changed, extra, malformed, or unbound record/log, or any evidence of a
transfer stage is a permanent stop. The host-only implementation is
review-gated; this turn does not execute it or remove the live active guard.
Its current host receipt is PREWRITE_ABORTED_NO_BOOT_WRITE with
candidateWriteCount=0, rollbackWriteCount=0, candidateReplay=false,
rollbackReplay=false, deviceContact=false, and guards=retained. Therefore H30
remains unclosed at the durable-guard level until an
independent review binds the repaired reconciliation and its exact H30
receipt. That is intentional under the user-requested no-authority boundary.

Guard closure does not require another H30-specific owner. The existing
candidate-neutral `A90_F1_POSTROLLBACK_RECOVERY_V1` already accepts the exact
consumed rollback prefix, performs one fresh bounded Native/ACM V2321 health
observation, publishes canonical `41-recovery-closed.json`, removes only the
active guard, and retains the candidate guard. Its execution closure changed
with the owner repair, so its prior review is stale and it must receive a fresh
independent review at the replaceable `A90_F1_POSTROLLBACK_RECOVERY_CURRENT_REVIEW.json`
lease before use. The dated H29 review stays immutable. H30 candidate reuse
remains forbidden.

## 3. Failed-boot evidence path on TWRP

The native-init pstore reader is not a failed-boot reader. It only counts
entries under /sys/fs/pstore, and native init does not run during a boot loop.
The first-opportunity reader belongs on the TWRP side, inside the recovery
session that the existing F1 owner already opens for fixed sha256sum and dd.

The primary source contract is:

| field | fixed value |
| --- | --- |
| source | /proc/last_kmsg |
| source mode | 0444, read-only |
| mount requirement | none |
| decoder | a90-proc-last-kmsg-raw-v1 |
| policy_id | A90_TWRP_FAILED_BOOT_LAST_KMSG_READONLY_V1 |
| source_contract_id | A90_PROC_LAST_KMSG_0444_NO_MOUNT_V1 |

The reader runs immediately after a failed-boot determination and before any rollback write.
It performs exactly two fixed open reads in the already bound
TWRP session:

1. cat /proc/cmdline, bounded as one ASCII command-line receipt; and
2. cat /proc/last_kmsg, bounded as a raw byte receipt with byte length and
   SHA-256.

The host stores only the reviewed canonical receipt and private raw evidence.
The decoder is byte-preserving at capture time; interpretation of kernel
messages is a separate H0 parser and cannot alter the captured source bytes.
An empty last_kmsg is an explicit result, not proof of a clean boot. A read
failure, truncated output, changed source identity, or publication failure
consumes the observation opportunity and records no-proof before the
prebound rollback path; it never retries a boot or rollback effect.

The cmdline receipt is retained to settle whether sec_log= is actually
present. The Native status summary sec_debug_or_sec_log is an OR and cannot
prove sec_log specifically. /proc/reset_reason, /proc/reset_klog, and
/proc/reset_summary are richer sources, but the installed TWRP kernel does
not set CONFIG_SEC_USER_RESET_DEBUG, so they are not available in the
boot-loop recovery state. They may be considered only if a candidate boots
far enough for Native init, and they do not replace the TWRP first-opportunity
receipt.

The sibling S22+ source pattern is the model: source, decoder, policy_id,
and source_contract_id are explicit manifest fields. A90 should use the same
shape in a future reviewed device-action declaration; this H0 document does
not create that declaration.

The sequence is therefore:

    failed boot determined
      -> durable evidence intent
      -> TWRP /proc/cmdline read
      -> TWRP /proc/last_kmsg read
      -> durable evidence receipt
      -> rollback intent
      -> exact bound V2321 rollback, if required

## 4. H30 reuse decision

H30 wrote nothing, so reuse remains plausible. It is not decided by the
host-side kernel comparisons alone, and it is not decided by pstore entries=0.
The next reviewed receipt must first bind the repaired Native/Recovery
boundary and the TWRP evidence path above. Only then may a separate H0
decision classify H30 reuse. No H30 reuse, candidate replay, approval,
manifest, token, or F1 action is created here.

## Withdrawn health element

The A90 status line reports mounted=no and dir=yes for pstore in the existing
captures. An unmounted pstore directory has zero entries by construction.
The adapter and menu-hide observer now retain status output as diagnostic
evidence but no longer make entries=0 a health predicate. GOAL_A90.md uses
the same wording: pstore entry count is diagnostic only.

## Implementation follow-up

`docs/reports/A90_TWRP_FAILED_BOOT_EVIDENCE_WIRING_H0_2026-08-22.md` records
the host-only owner, adapter, journal, raw-evidence, crash-cut, and
postrollback-consumer implementation. It remains review-lease inactive and
grants no device or replay authority.

## Validation boundary

Focused tests cover: no ADB call in the Native backend role check; Native
USB-only owner binding; recovery-only ADB binding; exact startup-banner
scoping; Native pre-frame absence of ADB; pstore non-authority; and the
ordering/source-contract requirements in this document. Static validation is
host-only. No device endpoint, ADB server, bridge, TWRP session, or private
run guard is contacted or changed by this work.
