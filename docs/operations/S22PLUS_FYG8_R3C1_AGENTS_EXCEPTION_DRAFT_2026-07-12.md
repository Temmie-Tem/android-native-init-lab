# S22+ FYG8 R3C1 AGENTS Exception Draft

State: `RETIRED_AFTER_PASS`

This is the historical pre-live policy source. The exact approved helper ran
once, R3C1 passed with verified Magisk rollback, and the binding exception is
retired. This document authorizes no further device write.

## Proposed Narrow Exception

After independent review, the consumed exception authorized one bounded
attended `S22+ FYG8 R3C1 unpatched rebuilt-kernel boot-only live gate` on
Samsung S22+ `SM-S906N` / `g0q` / `S906NKSS7FYG8`, using only helper
`workspace/public/src/scripts/revalidation/s22plus_fyg8_r3c1_live_gate.py`
SHA256
`2e6bf83733685288d0289d175c9639858ae0d3c5f2fe06f83737bceb186a6eb1`.
The consumed active clause used the exact whole-line ACTIVE state. Live
acknowledgement was `S22PLUS-FYG8-R3C1-UNPATCHED-KERNEL-LIVE`; interrupted
rollback from an already-started run would use
`S22PLUS-FYG8-R3C1-MAGISK-ROLLBACK-FROM-DOWNLOAD`.

Before any candidate transfer, the helper must verify:

- static checker SHA256
  `917b12f82dc5525b84cf2627379a80e49d921b6c33ca79fe3fc5c6a9ece6a514`
  with verdict `PASS_R3C1_STATIC_CONTRACT`;
- builder SHA256
  `11f6e270ba5c63b498b2072573bb8a870f6dd031b5fb407268b6d39c55577596`;
- candidate raw boot SHA256
  `e1f0be9933e9c76d881a2cc39c0431bf54930ee0f216f55de4d7a166a60d120c`,
  size `100663296`;
- candidate boot-only AP SHA256
  `023d7780e11363bd152900e28279233a0fd66ce8dd8902417d23eb781f613fb4`,
  containing exactly `boot.img.lz4`;
- candidate manifest SHA256
  `2596b5f1c6a8fa88d8ee75224c8a039764c67453875789744a7087db2fb97bb0`;
- Magisk rollback AP SHA256
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`;
- cleanup-only stock boot AP SHA256
  `2f6a8ac093587a0f03c423d8e21f65c6fe3a8d2ce9915297170cdaa2cac37c94`;
- Odin SHA256
  `6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b`,
  size `3746744`.

The checker must rehash full FYG8 firmware evidence, exact R3C0 and R2 inputs,
intentional stale AVB, the kernel-only delta, and both rollback chains. Live
preflight must prove one exact normal Android target, completed boot and stopped
boot animation, orange verified-boot state, Magisk root, known Magisk boot,
stock DTBO/recovery hashes, no Odin endpoint, and an unconsumed R3C1 one-shot
state.

The future helper may request Download mode and transfer the exact candidate AP
once to boot only. Candidate flash start consumes the exception. Candidate PASS
requires one ADB target, exact FYG8 identity/incremental, completed boot, stopped
boot animation, exact FYG8 kernel release and `/proc/version`, orange verified-
boot state, and three stable samples. Root is not a candidate requirement.

Mandatory rollback uses the exact Magisk AP. The operator physically enters
Download if candidate Android has no ADB. Only a failed Magisk transfer with one
remaining unambiguous Odin endpoint permits the exact stock boot cleanup AP.
Final PASS requires normal Android, Magisk root, exact Magisk boot, stock DTBO
and recovery, and no Odin endpoint.

The helper must reject an existing
`workspace/private/state/s22plus_fyg8_r3c1_live_exception_consumed.json` and
durably create it at `candidate_flash_start`. Emergency rollback remains
available after consumption. Timeline is only `events:[{name,timestamp_utc}]`
with the standard eight phases exactly once and in order.

This consumed exception authorizes no second
candidate run, R3C0 reuse, R3B, native PID1, Debian, raw `dd`, fastboot, module,
panic, RDX, dump, EUD/UART, format, partition-table action, non-boot partition
write, or A90 action. Activation requires completed offline/connected gates,
independent review, an exact helper SHA re-pin after every fix, and a new fresh
attended approval supplied after those gates. Binding state is now
`S22PLUS_FYG8_R3C1_POLICY_STATE=RETIRED` and must not be restored. See
`docs/reports/S22PLUS_FYG8_R3C1_LIVE_RESULT_2026-07-12.md`.
