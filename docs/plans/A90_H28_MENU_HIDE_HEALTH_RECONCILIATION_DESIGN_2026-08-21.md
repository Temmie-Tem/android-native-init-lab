# A90 H28 menu-hide health reconciliation design — 2026-08-21

## Disposition

H0 design and implementation only. This document grants no D0, D1, F1,
reboot, image, partition, physical-action, or live authority.

The prior `A90_H28_SLOW_HEALTH_RECONCILIATION_V1` session is consumed. It
proved exact V2321 `version`, `selftest fail=0`, and `status pstore entries=0`,
but its final boot-ID request returned `EBUSY` because the native automatic
menu was still active. The prior intent, both guards, and the original H28
recovery-required journal remain retained. This is a new capability and a new
sidecar namespace; the consumed session and its log directory are never
reused.

## Objective

Provide one narrowly bounded terminal-only observer that repairs the observed
menu-state precondition without replaying any earlier effect. The capability
is `A90_H28_MENU_HIDE_HEALTH_RECONCILIATION_V1` and its only modes are:

- `prepare`: host-only, write-free derivation of one review/closure-bound token;
- `execute --approval TOKEN`: one fresh attended read-only Native session.

The fixed H28 run, manifest, terminal, physical-return intent, first Native
observation intent, consumed slow-health intent, and all twelve prior
slow-health receipt bytes are bound by digest. The prior receipt set is
declared in the source from the public incident facts; execution may verify
those private bytes, but preparation and review do not open them.

## Effect and observation ordering

`execute` first repeats all public/private closure checks and then publishes
one `O_EXCL` intent in the new sidecar. Only after the intent is fsynced and
read back may it contact the device path. The observer then performs exactly:

1. complete USB inventory, binding one A90 Native `04e8:6861` and the foreign
   Samsung disposition;
2. managed bridge preflight for the fixed A90 by-id ACM path;
3. one unframed bridge line `hide\n`, with one captured receipt and no retry;
   the receipt must explicitly contain `hide requested` (a prompt or `[done]`
   marker alone is not success);
4. the fixed existing 3.0-second asynchronous-menu settle from
   `native_init_flash.py`, with no device command before the full settle;
5. slow-input `cat /proc/sys/kernel/random/boot_id` (first command);
6. slow-input `version`;
7. slow-input `selftest`; and
8. slow-input `status`;
9. a final fixed slow-input `cat /proc/sys/kernel/random/boot_id`, captured as
   `boot-id-final`, followed by a second host USB inventory to prove that the
   A90 and foreign endpoint set did not drift.

The five Native reads use only the fixed `a90ctl --input-mode slow` safe
read-only path. No caller can choose a command, path, input mode, endpoint,
timeout, or retry policy. The raw `hide` line is not sent through the framed
command protocol and is never retried, including after a partial response. A
settle interruption or sleep failure consumes the intent and parks without a
boot-ID request. Success derives `sameBoot` from equality of the initial and
final boot-ID receipts; a changed, missing, invalid, or failed final read
parks with no recovery record.

## Terminal conditions

Success requires the exact V2321 version/build, a valid initial boot ID,
selftest `fail=0`, exactly one `pstore=` status line with `entries=0`, a
successful hide receipt, an exact matching final boot ID, unchanged USB
inventory, and a structurally valid Native receipt set. The result derives
`sameBoot: true` from that equality and binds the final boot-ID receipt, hide
receipt, and new intent.

The successful result is published as the original run's
`41-recovery-closed.json`, then read back byte-for-byte under the current
review lease. Only after that readback is the active-run guard removed. The
consumed H28 candidate guard remains present. The result records zero image,
reboot, physical, and recovery-effect counts and keeps both replay flags
false.

Any malformed input, menu-busy receipt, command error, timeout, wrong
resident, pstore entry, boot/USB drift, host loss, publication uncertainty,
or review/closure drift consumes the new intent and parks permanently. No
second hide, observer, token, or sidecar is permitted. A later invocation may
only report an already published result after the active guard is absent.

## Review boundary

The execution closure includes the new source, this design, its review
handoff, the exact `prior.EXECUTION_SOURCE_RELS` closure of the physical
return reconciler, both prior incident reports, the binding A90 contract,
`GOAL_A90.md`, `AGENTS.md`, and the fixed owner/adapter source closure. A
fresh independent
`PASS_GO` is required before preparation. A PASS qualifies only this
capability; it grants no live session. A fresh exact token is still required,
and the operator must attend the single read-only session.

The implementation is intentionally not a general menu controller: it has no
start/stop service, shell, ADB, recovery, reboot, transfer, image, partition,
candidate, rollback, or arbitrary-command path.
