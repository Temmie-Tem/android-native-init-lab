# S22+ FYG8 R3C1 Live Result

Date: 2026-07-12 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `PASS_R3C1_UNPATCHED_REBUILT_KERNEL_VIABLE_AND_ROLLED_BACK`

The one-shot attended R3C1 run completed without host continuation. The exact
unpatched R2 Full-LTO rebuilt kernel reached normal FYG8 Android in the
live-proven R3C0 carrier, and the exact Magisk boot rollback restored the full
baseline. This proves narrow stock-userspace viability for this exact rebuilt
kernel and carrier. It does not prove native PID1, Debian, candidate root,
hardware completeness, long-duration stability, or any later rung.

## Executed Pins

- live helper SHA256:
  `2e6bf83733685288d0289d175c9639858ae0d3c5f2fe06f83737bceb186a6eb1`
- candidate raw boot SHA256:
  `e1f0be9933e9c76d881a2cc39c0431bf54930ee0f216f55de4d7a166a60d120c`
- candidate boot-only AP SHA256:
  `023d7780e11363bd152900e28279233a0fd66ce8dd8902417d23eb781f613fb4`
- exact R2 Image SHA256:
  `9110a7722f28f075c5cb09789710341b44956147fa05867d05e5b3e7d024770d`
- Magisk rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
- static checker SHA256:
  `917b12f82dc5525b84cf2627379a80e49d921b6c33ca79fe3fc5c6a9ece6a514`
- static verdict: `PASS_R3C1_STATIC_CONTRACT`

Only boot was transferred. The stock cleanup AP was not needed. No other
partition, raw host `dd`, fastboot, module, panic, RDX command, dump, or A90
action occurred.

## Candidate Milestone

The candidate AP transferred with Odin rc=0 and the original endpoint
disconnected. Android returned and three bounded samples all proved:

- exact model/device/bootloader/incremental;
- `sys.boot_completed=1`;
- `init.svc.bootanim=stopped`;
- verified-boot state `orange`;
- `uname -r` exactly
  `5.10.226-android12-9-30958166-abS906NKSS7FYG8`;
- `/proc/version` exactly matched the FYG8 `build-user@build-host`, Clang
  `12.0.5`, and corrected stock timestamp identity.

The operator independently observed Android on the panel. Root was not used as
a candidate requirement.

## Mandatory Rollback

The helper requested Download mode after candidate observation. The exact
Magisk boot AP transferred with Odin rc=0. The helper itself then proved:

- normal Android and stopped boot animation;
- Magisk `uid=0(root)`;
- boot SHA256
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
- DTBO SHA256
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`;
- recovery SHA256
  `93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4`;
- no Odin endpoint.

A separate post-run read-only check reproduced the same exact final baseline.

## Timeline

All eight required events appear exactly once and in order. Approximate elapsed
times derived from UTC timestamps:

- candidate transfer: `1.50 s`;
- candidate flash done to candidate milestone: `35.60 s`;
- rollback transfer: `1.52 s`;
- rollback flash done to final Android: `35.06 s`;
- complete attended session: `94.69 s`.

Private evidence pins:

| Evidence | SHA256 |
| --- | --- |
| `result.json` | `f7a0efb5bc90ea1ec18e345b7daa9245027aaad2446e0f6061cd6f83f6dc312a` |
| `timeline.json` | `b792570a8baf2f2aeecef15fcc3241a0f3b83dddbcbda0d293d592b0b26d9066` |
| `live.log` | `6198458588cc946dedfd4e6eebf613f43697baeb666c50b21af47183154646f3` |
| consumed state | `f7b4921df7c9dc51bc1c50f83f4d059cd5a5c0d24f778bec93dc25723079e3e2` |

## Policy State

`S22PLUS_FYG8_R3C1_POLICY_STATE=RETIRED`. The durable one-shot consumed state
exists and the exception cannot be reused. Any next kernel or native-PID1 rung
requires a separately designed, reviewed, SHA-pinned policy and fresh approval.

Post-run maintenance source SHA256 is
`0a74a7a49ec5bae316f54e406914072da5564c0db7690b62ae4a53061af0f851`;
it only distinguishes the executed helper SHA from the current retired source
and accepts the historical RETIRED policy document. It has no live authority.
Post-run validation: `54/54` related tests PASS, retired offline gate PASS,
retired connected read-only dry-run PASS with exact Magisk baseline, policy
inactive, one-shot consumed, and device writes false; `git diff --check` PASS.
