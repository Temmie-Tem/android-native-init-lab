# S22+ FYG8 R3C0 Live Result

Date: 2026-07-12 KST

Target: `SM-S906N/g0q/S906NKSS7FYG8`

Verdict: `PASS_R3C0_NORMALIZED_STOCK_CARRIER_AND_ROLLED_BACK`

The one-shot attended R3C0 control completed. The synthetic minimal
signer-normalized carrier booted normal FYG8 Android with the exact stock kernel
and ramdisk, and the device returned to the exact known Magisk baseline. This
proves acceptance of the exact R3C0 carrier shape only. It does not prove the
rebuilt R2 kernel, native PID1, Debian, root on the candidate, or any R3C1
behavior.

## Authorized Inputs

- executed live helper SHA256:
  `921800725fa73b7d37fd8d3c46369d0015ab4a8e366111e079b5f7ce674246e3`
- candidate raw boot SHA256:
  `384efeb0f81534cbfaf3643f42e34fb6e01fe6f0b6bf80139a047a1f9a71f29f`
- candidate boot-only AP SHA256:
  `8f2b16d3ee8932ff927e06fee8956f975ec3f9e5cc0ef16337e00ad5108d3c00`
- Magisk rollback AP SHA256:
  `d2373bf88dda342709440dc3db468f11d80a4593856768a4d8ae402bef215a56`
- static checker SHA256:
  `917b12f82dc5525b84cf2627379a80e49d921b6c33ca79fe3fc5c6a9ece6a514`
- static verdict: `PASS_R3C0_STATIC_CONTRACT`

Only boot was transferred. No stock cleanup AP was needed. No other partition,
raw host `dd`, fastboot, panic, RDX command, RAM dump, or A90 action occurred.

## Candidate Result

The candidate AP transferred with Odin rc=0 and the original Odin endpoint
disconnected. Android returned and three bounded samples all proved:

- model/device/bootloader/incremental exact;
- `sys.boot_completed=1`;
- `init.svc.bootanim=stopped`;
- verified-boot state `orange`;
- `uname -r` exactly
  `5.10.226-android12-9-30958166-abS906NKSS7FYG8`;
- `/proc/version` exactly matched the FYG8 `build-user@build-host`, Clang
  `12.0.5`, and build timestamp identity.

The operator independently observed Android on the panel. Candidate root was
not required and was not used as a PASS condition.

## Rollback Result

The helper requested Download mode after candidate observation. The exact
Magisk boot-only AP transferred with Odin rc=0. Final read-only validation
proved:

- normal Android and stopped boot animation;
- Magisk `uid=0(root)`;
- boot SHA256
  `2e541703951dc725bad35850faf7028c2d910dd5f21166449b63f1248c29967e`;
- DTBO SHA256
  `97a4864fee4e61892d733962d1ec76f8d14b52bc19e6f47440bc27d9dfc4bd0c`;
- recovery SHA256
  `93fac06ca79bf4b365b25a8d49902bc41aba112ea253c30880c90e314d7895d4`;
- no Odin endpoint.

## Host Continuation

After rollback Android first appeared, one root `sha256sum` transiently
returned an empty output. The helper indexed the empty split result and raised
`IndexError` before writing `rollback_boot_ready` and `live_session_end`.
This was a final-observation race, not a rollback failure: Odin had already
reported rc=0 and Android/Magisk subsequently passed every exact final gate.

A host read-only continuation immediately reran the exact final validation,
required no Odin endpoint, appended the two remaining standard timeline events,
and recorded completion mode
`HOST_READ_ONLY_CONTINUATION_AFTER_HELPER_EARLY_ADB_INDEXERROR`. No device write
or additional flash occurred in the continuation. The helper was then changed
to treat empty/malformed SHA output as `GateError`, allowing the bounded Android
wait to retry instead of indexing an empty list. Post-fix helper SHA256 is
`f10a30735882bbd59453471fe901b1cef11fdf42bcf3560a8ae61b4af361c4f4`;
it was not the executed artifact and is not authorized for another live run.

## Timeline

The final timeline contains exactly the required eight events in order. Key
elapsed intervals derived from UTC timestamps:

- candidate transfer: about `1.49 s`;
- candidate flash done to candidate milestone: about `49.58 s`;
- rollback transfer: about `1.55 s`;
- full attended session through host continuation: about `189.65 s`.

Private evidence pins:

| Evidence | SHA256 |
| --- | --- |
| `result.json` | `01bc411700541fefe4339e081cedf3831c8a08373b64065c95444c3646581a83` |
| `timeline.json` | `364c292695f9e78c3cd6702ee79ad738e50109e1475b0a5cafa4840a5485e6b5` |
| `live.log` | `64acc82c60c511e18b949b4cb86401b5f5f8407b6512bf9e8383b4f253f30e73` |
| consumed state | `c510f0a80cbd446a2eb2ea74c39b928283b01fffaca70ff72ce806ae9a1dec97` |

## Policy State

`S22PLUS_FYG8_R3C0_POLICY_STATE=RETIRED`. The durable consumed-state file exists
and the R3C0 helper refuses another candidate run. This exception cannot be
reused. R3C1 is now eligible for host-only construction, independent static
review, and a new SHA-pinned policy design; it is not yet authorized for live
use.

Post-run validation: `py_compile` PASS, `36/36` focused and related tests PASS,
retired offline gate PASS, retired connected read-only dry-run PASS with exact
Magisk baseline, policy inactive, one-shot consumed, and device writes false;
`git diff --check` PASS.
