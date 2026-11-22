# S22+ mainline UFS V13: next attended run preparation (H0)

Date: 2026-11-22. Host-only preparation. This document grants no device
authority and approves no candidate. It records what the next V13 attempt can
reuse, what blocks it, and the attended run card that keeps the cue
resolution off the assistant's turn. ML051 and ML052 were each lost on cue
timing ([ML051](S22PLUS_MAINLINE_ML051_V13_RUN_2026-11-19.md),
[ML052](S22PLUS_MAINLINE_ML052_V13_RUN_2026-11-19.md)).

## What can be reused

**ML053 candidate** (`workspace/private/outputs/s22plus-ml053-v13-reuse-h0-20261119-1/`,
name `ml053-v13-key-only`):
- It is a key-only V13 candidate on capability `3532b540…`, with candidate
  ID `6871a9f6…`.
- It was built and pre-approval audited on 2026-11-19 (`PASS_FRESH_V13_PREAPPROVAL`).
- It was never granted or transferred, and its ID is absent from the
  consumed-candidate registry. The artifact itself can therefore still be
  used.
- The SCM adoption (`f95650a5b4`) kept the V13 capability's fixed fields and
  retained evidence.

**Not reusable: the ML053 task** (`task.json` `9d9fb256…`). It pins 86 sources,
and 6 of them have changed since 2026-11-19, mostly through the SCM merge and
adoption:
- `docs/operations/targets/S22PLUS_FYG8_TARGET_CONTRACT.md`
- `workspace/public/src/mainline/s22plus_canary_h0/package_loader.py`
- `workspace/public/src/scripts/revalidation/s22plus_mainline_{access,profile,session,task}_v1.py`

Its pre-approval health captures are also three days old. A new task,
proposal, pre-approval audit and D0 are needed. They should be made after the
blocker below, which changes the same files again.

## Blockers before the run

1. **Shared cue fixes (Codex).** Agenda item 3 in
   [the ordinary-route cue agenda](../plans/S22PLUS_MAINLINE_ORDINARY_CUE_AGENDA_2026-11-22.md),
   accepted in `a8517e4ff0`, applies to the UFS cue route as well. Codex
   scheduled the fixes on `codex/s22-mainline-ordinary-cue-h0` "before the
   next related cue run":
   - reconcile an unresolved cue before attended recovery;
   - let H0 close repair use the normal `android-final` health;
   - put census and endpoint selection under the same lock as cue issuance.
2. **Review refresh.** The same branch updates the active reviews and gateway
   pins. The approved-terminal backend reviews v53 and v54 pin the changed
   session files.
3. **Operator decision on the click: accepted (2026-11-22).** The operator
   accepted that clicking **다시 꽂았음** or **취소** in the cue dialog is their
   actual cue resolution. The helper records it through the reviewed `resolve`
   CLI, and the statement names the button and the time. The prepared typed
   command (`! …resolve…`) remains the fallback if the dialog cannot be shown.
   Codex's review (`97d9ba794e`) put the helper's adoption on hold for four
   reasons, which were fixed in `efb2950fc5`. A separate Codex review of that
   fix returned `HELPER_HOLD` with five further findings, all fixed
   afterwards (see the agenda log). The helper needs a re-review. Until then,
   the direct cue and explicit `resolve` path is used.
4. **Fresh task.** That means a new task, D0, pre-approval audit and the exact
   approval line.

## Attended run card

| When | Who | Action |
|---|---|---|
| Before the approval line | operator or assistant (background) | Start `python3 workspace/public/src/scripts/host_tools/s22plus_mainline_cue_dialog_v1.py --operation <task>/operation-0001 --captures <prep>/cue-dialog --cable <c-to-a or c-to-c>`. It waits up to 600 s for the journal's `step-start mainline-evidence`. |
| Approval and dispatch | operator, then assistant | The assistant dispatches and **ends its turn immediately**. No polling call stays open. |
| W (window opens) | helper | Starts the Stage 0 host port watch on `3-1.3` and `2-1.3` (`<prep>/cue-dialog/host-port-watch/`). |
| W+22 s (on the sealed BOOTTIME window) | helper | Calls the reviewed `issue`. The dialog is shown only when the call exits 0 and its stdout result is `CUE_RECORDED_DISPLAY_NOW`, and only when its cue receipt is this operation's `mainline-attach-cue.json` bound to this window. A refusal is retried only while no cue exists and more than 60 s remain. |
| On the dialog | operator | The dialog shows the reviewed instruction verbatim. Unplug the phone end **once** for about 3 s and reconnect with the same cable, port and orientation. Press no phone buttons and do not repeat. Then click **다시 꽂았음**, or **취소** if the replug will not happen. **닫기**, Esc or closing the window record nothing; the dialog reappears with a warning not to replug again. Before each display the helper checks that the step is current and that no resolution, closure or recovery fence exists. |
| Click | helper | Rechecks the same conditions, then calls the reviewed `resolve completed` or `resolve cancelled`. The statement names the button and the time the helper observed it (wall time and W+ on the sealed window). Success requires exit 0 and the receipt of `mainline-attach-resolution.json`. Zenity runs without `ZENITY_*` exit-code overrides. |
| deadline − 8 s | helper | The dialog closes if nothing was clicked, and a button observed after this point is discarded. Nothing is resolved, and the owner's interlock handles the attempt as before. |
| After the base response | owner | `close_issuance` needs the resolution before W+120 s. In ML052 the replug at about W+27 s gave the base response at W+75.7 s, so a prompt click leaves about 40 s of margin. |

The helper only calls `s22plus_mainline_attach_cue_v1.py issue|resolve` with
`--capture-directory`. It never writes operation records, never touches
USB/ADB and opens no grant. Its exit codes:
- 0: resolved;
- 2: cue not possible, or the cue stopped being open (step ended, fenced, resolved elsewhere);
- 3: no window, or a window of another operation or host boot;
- 4: dialog timeout;
- 5: resolve failed.

[Helper tests](../../tests/test_s22plus_mainline_cue_dialog.py) cover the
button mapping, timeout, refusals, retry naming, the no-window case and
calls to the reviewed tool only.

## Order of work

1. Codex lands and adopts `codex/s22-mainline-ordinary-cue-h0`.
2. Review the cue dialog helper (the operator accepted the click on 2026-11-22).
3. Create the new task for the ML053 candidate, or a fresh key-only build,
   then pre-approval audit and D0.
4. Hold the attended run with the card above.
