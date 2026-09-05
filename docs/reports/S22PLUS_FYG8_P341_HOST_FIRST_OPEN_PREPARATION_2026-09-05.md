# P341 host-first OPEN preparation

Target: `SM-S906N / g0q / S906NKSS7FYG8`. H0/D0 preparation is not F1 authority.

## Change and evidence

P340 closed with exact candidate/rollback 1/1 and healthy rooted return. Its
193-byte capture retained the rejected 16-byte header `S22PLUS-FYG8-E3:`.
Local PTY tests reproduced kernel echo returning this banner prefix before raw
setup. The P340 incident itself did not retain pre-raw termios or a complete
USB OUT trace, so echo remains a strongly supported mechanism, not definitive
attribution of every historical failure.

P341 reuses one existing run-bound OPEN as the host's first transmission after
raw setup. The device validates it before banner, stage 0 and OPEN_PARSED.
All three session entries share that order. No-input idle is silent; partial
OPEN consumption survives timeout/error and cannot restart a frame. HMAC,
three fixed commands, three sessions, one planned reopen, deadlines and exact
rollback remain. This does not activate a resident action lease.

H0 tests cover real PTY initial/authenticated/reopen sessions and bad HMAC;
raw failure publication and common receipt reopening without an invented
banner; actual C reader silence, partial consumption and valid preamble order;
and AArch64 compilation. The first package build found an obsolete unused
banner predicate under production `-Werror`. Only that dead predicate was
removed; the C test now uses production `-Os -Wall -Wextra -Werror`. Failed
output `stock-candidate-build-v1-20260905-01` is preserved and never reused.

## Qualified build

Output: `workspace/private/outputs/s22plus_fyg8_p341/stock-candidate-build-v1-20260905-02`.
Fresh run: `c341f1e0a90b5e6d7c8a9b0c1d2e3f9b`.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| result.json | 79393 | 5733271ebbe1c88db405921275152e5696ca4e38226894d08c6eb434021b2e47 |
| A/B AP | 28631081 | 714c6c254d0685f67dfbdee3e8035d69ca7b6ee8230a24bcd2d81e770a68bca6 |
| Image | 41490944 | 7ede2bc496fdffcf98140106caa2c42ee957536b04b45b1778071128bc95144a |
| init | 82552 | 9af94fa4698d8a33ae3caf863bc7f6e2c44580f51f49e9cdbf5d162ae3d2d873 |
| Magisk rollback AP | 23367721 | d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56 |

The Image identity-only transform preserves size/layout; the runtime is not an
identity-only change. Actual A/B packaging and current-helper/copied-input
audits pass. The builder reuses exact P340 packaging source through a small
namespace/semantic wrapper. Artifact unit commit: `3d9fbf3f07`.

## D1 interruption and independent D0 health

The preapproved one-reboot primitive ran once in
`workspace/private/runs/device-action-d1-p341-baseline/p341-normal-reboot-20260905-1`.
Its start digest is `0d0cf1db56f11878bda606edccdaf05edf2e47776f96eb8ac72682719b2d252d`.
Raw `0005-adb-normal-reboot.capture.json` proves returncode 0 without timeout.
The final property capture `0025` returned code 0 with empty stdout/stderr,
raising incomplete-properties before the primitive result was published.
This is an interrupted D1, not a successful primitive receipt. The cause of
the empty capture is not established; early-boot timing is not claimed as fact.
No second reboot or fabricated D1 result was used.

A new read-only invocation at
`workspace/private/runs/device-action-d0-p341-health/health-after-d1-20260905-1`
verified the same selection, changed boot, rooted FYG8 and expected partition
digests through the unchanged raw transport and health validator. Its result
is `1516B/e5e0eb81d88501b145e4cf03aaddcc356c4efc7d0d03ffaa182afb0d4e340998`,
`PASS_D0_EXACT_RETURN_HEALTH`, with zero reboots/Odin/device writes and no
other-target commands. Fresh ordinary preparation must independently verify
the current baseline; the interrupted primitive is never replayable.

## Approval boundary

Independent `PASS_GO_P341_H0` covers current artifact/runtime, common
evidence/core/live, target clause, static and prepare paths. Independent P341
tests 15/15 and common evidence 29/29 passed; canonical host-only rehearsal
passed. After publication, the root initial/closure suite passed 5/5,
including actual PTY proof validation, no-banner raw publication/reopening,
and success/NO_PROOF final routing. No extra review gate was introduced.

Canonical ready is
`workspace/public/src/device-action/manifests/s22plus_fyg8_p341_process_v2_ready_1.json`,
`12341B/bc498d9bd3865818e2e2f7d407d4e9fb37670c23ede1afa727515c0f9e2a3b9e`.
Its public mode is 0644 (publication's umask-filtered 0640 was corrected
without changing bytes). Private promotion is
`workspace/private/outputs/s22plus_fyg8_p341/process-v2-promotion-20260905-01`:
static `50350B/f2489d67`, run manifest `1351B/2d226718`, static check
`1930B/b6b1ac99`. Bundle digest:
`35d5f88daaad0eb521795afac185b20e0df55f112f35a4d8dfd7895ea793b924`.

Fresh ordinary connected D0 passed in
`workspace/private/runs/device-action-f1-live-v2/p341-ready1-prepared-20260905-1`.
Preflight is `3261B/ba258295d83f158db2d6e52e39f03f6e0ee6a7d048dff9124da90e49a5cd2c2c`;
clean baseline is `2097136B/2fce77d1cbd7adbccbc36104394054947d8553d11d3103dd66e1f5cd108f8065`;
prepared is `28109B/ac1f7ab59369490461ef4eb53c1fa27e5a9ae541967c39e10d8cdddd237e0b7b`.
The fresh approval digest starts `381707d5`. It is issued for the operator
to return, not consumed by the agent. No P341 candidate/rollback transfer,
Download request or F1 transaction occurred. No later resident action lease
is activated. P340 approvals and consumed artifacts grant no authority.

The prepared record reopens against the unchanged current execution closure.
Its D0 boot matches the independent post-reboot D0 health receipt, and its raw
baseline has zero exact markers and zero marker-family occurrences. The
canonical ledger records the interrupted D1, separate healthy D0, H0 readiness
and this preparation; P320–P322 historical disposition remains unchanged.

## Attended F1 observation accepted; rollback pending

The operator returned the exact `381707d5` approval and the ordinary runner
executed the prepared P341 once. Candidate transfer completed; candidate and
rollback completed counts are currently 1/0. The journal has 10 records through
OBSERVED/candidate_boot_ready. During physical Download waiting, execution
stopped with `measured USB endpoint evidence failed`. Rollback has no attempt
yet; the same journal's preapproved exact Magisk recovery remains required.
No candidate or fixed command may be replayed.

The actual candidate receipt was published and accepted:

- Receipt: `28495B/01c6663e2d7bd79b6c568b3364332d77a7c18ff85d69bbea5e34f2459ab95931`.
- RX: `1983B/da3438a40e886db7d9b87d7f9d6a2abcbf2cd6b49cef8b445b18fe4bc5ae270f`.
- TX: `1107B/aa322f6a69945f8e94c1207349b2267cca6b757f501c6fb0a84482d4a0591707`.
- Three successful authenticated sessions; nine fixed commands, every exit 0.
- Two same-FD sessions and one planned host close/reopen; same authenticated
  per-boot identity, diagnostic order and retained-listener proof all true.
- All three session audit stages are complete without partial exceptions.

This proves the intended bounded candidate exchange worked in this run.
It does not establish indefinite residency, later-action authority, arbitrary
shell commands, autonomous reboot/Download or historical echo causality.
The earlier zero-transfer preparation paragraphs are historical stages. Formal
F1 PASS, final healthy return and the matching F1 closure ledger row remain
pending rollback and durable close; the candidate/approval are consumed.
