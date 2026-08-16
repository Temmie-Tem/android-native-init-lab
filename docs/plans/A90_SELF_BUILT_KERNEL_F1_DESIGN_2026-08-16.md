# A90 self-built kernel F1 design (draft for independent review)

Date: 2026-08-16
Target: operator-owned Samsung Galaxy A90 5G only
Tier of this document: H0 design draft
Device or live effect of this document: none
Status: **DRAFT — grants no authority, creates no candidate, and is not an
approval request until it has passed independent review**

This design proposes one attended F1 that answers a single question. It does
not authorize that F1, does not qualify a candidate, and does not create an
identity, ordinal, or approval. `GOAL_A90.md` currently states that "No
successor candidate, approval, transfer, reboot, or D1 effect is authorized by
this goal", and nothing here changes that.

## The single question

**Does the A90 boot a kernel this project compiled?**

That is the whole scope. The A90 has flashed many custom boot images and every
one of them reused the stock kernel blob; only ramdisks changed. No self-built
`Image` has ever been resident on this target. Until that is answered, every
downstream kernel-side option — including the private `binderfs` instance the
isolated-Debian design needs — rests on an untested assumption.

## What this F1 does not do

- It does not enable `CONFIG_ANDROID_BINDERFS`. That symbol stays off. Testing
  the build path and testing the feature in one flash would confuse two
  results.
- It does not change userspace. The candidate carries the resident's own
  ramdisk, byte for byte.
- It does not change the device tree. The candidate reuses the resident's own
  appended DTB region.
- It does not attempt `switch_root`, Debian PID 1, WLAN handoff, or any H24 D1
  effect. Those are separate, already-bounded work.
- It does not retire any WLAN gate. `H0D01` through `H0D10` are untouched.

## What is being accepted, stated before the identities

The candidate kernel has `CONFIG_RKP_CFP`, `CONFIG_RKP_CFP_JOPP`, and
`CONFIG_RKP_CFP_ROPP` disabled. Samsung's JOPP/ROPP control-flow protection
cannot be reproduced because it requires a patched LLVM that the OSRC package
does not ship and AOSP clang does not implement. The operator authorized the
removal on 2026-08-16.

`docs/reports/A90_SELF_BUILT_KERNEL_H0_2026-08-16.md` records the mechanism and
the bounded scope: the RKP hypervisor layer, `CONFIG_UH_RKP`, `CONFIG_RKP_KDP`,
`CONFIG_RKP_NS_PROT`, and `CONFIG_RKP_DMAP_PROT` are untouched, and `System.map`
shows zero `rkp_cfp`, `jopp_springboard`, and `ropp_` symbols against retained
`rkp_init` and `uh_call`.

**Approving this F1 accepts a reduced kernel exploit-mitigation posture on this
unit for as long as the candidate is resident.** A reviewer who is not willing
to accept that should reject this design rather than the artifact.

## Exact identities

All paths are private and none is committed.

| role | artifact | size | sha256 |
|---|---|---|---|
| resident | `workspace/private/outputs/a90-h24-minimal-debian-dev-ab-20260812-01/A/boot.img` | 58,372,096 | `d8c280e4acee5d17d13270fdf25535b4ce05304e786bc22efa84ab16f6b82782` |
| candidate | `workspace/private/inputs/boot_images/boot_a90_h24_selfbuilt_nocfp_20260816.img` | 58,368,000 | `7c293af9c0fd6bfea5247cd5c3415956c452c67a79e8269c967860d2a2c0cead` |
| rollback | `workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img` | 60,882,944 | `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb` |

The resident is H24 `0.11.192`, build
`phase3-minimal-h24-ufs-auth-native-hud-private-card-root-minimal-debian-dev`,
named by `GOAL_A90.md` as the exact installed resident. Its A/B build output is
reproducible: `A/boot.img` and `B/boot.img` are byte-identical.

The rollback is V2321, which `GOAL_A90.md` names as "the exact bound rollback
for a future, freshly qualified successor". Its digest matches the
`rollback-boot-v2321.img` consumed by prior A90 F1 runs.

Candidate against resident, the only differing boot header field is
`kernel_size` (49,827,613 → 49,823,517). Ramdisk bytes are identical. Load
addresses, tags offset, page size, header version, OS version, patch level,
product name, and the full command line are identical.

Proposed transport is the unchanged runner
`workspace/public/src/scripts/revalidation/native_init_flash.py`, size 43,118,
sha256 `366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53` —
byte-identical to the runner used by the prior A90 F1 run, invoked
`--from-native --image <path> --expect-sha256 <digest>` with `boot` as the only
partition payload.

## The discriminator problem

**A version check cannot tell the candidate from the rollback here.**

Every prior A90 F1 distinguished states by userspace version, because each
candidate shipped a new native-init build. This candidate deliberately ships
the resident's ramdisk, so it reports the same `0.11.192` and the same build
string whether the self-built kernel booted or not. An acceptance predicate
written the usual way would pass on a silent fallback.

The kernel banner is the discriminator and it is unambiguous:

```
resident   Linux version 4.14.190-25818860-abA908NKSU5EWA3 (dpi@SWDK6110)
           (clang version 10.0.7 for Android NDK, GNU ld (binutils-2.27-bd24d23f) ...)
           #2 SMP PREEMPT Thu Jan 12 18:53:40 KST 2023

candidate  Linux version 4.14.190 (temmie@debian)
           (Android (7284624, based on r416183b) clang version 12.0.5 ...,
           GNU ld (binutils-2.27-bd24d23f) 2.27.0.20170315)
           #5 SMP PREEMPT Sun Aug 16 20:25:50 KST 2026
```

Both strings are extractable host-side from the respective `Image` before any
device contact, and the exact expected candidate banner must be pinned in the
manifest before approval.

Note the release suffix: stock is `4.14.190-25818860-abA908NKSU5EWA3` and ours
is a bare `4.14.190`. `CONFIG_LOCALVERSION=""` in **both** configurations, so
the suffix comes from Samsung's build environment rather than a configuration
difference we could restore. See the open risks.

## Acceptance predicate

`PASS` requires **all** of the following, in one attended window:

1. the candidate transfer completes and the read-back digest equals
   `7c293af9c0fd6bfea5247cd5c3415956c452c67a79e8269c967860d2a2c0cead`;
2. the device reaches the resident's exact native health predicate, unchanged
   from the H24 close — the same `binding=1 enable=1 latch=1` shape and the
   same userspace version `0.11.192`;
3. `/proc/version` matches the pinned candidate banner **exactly**;
4. one distinct returned USB epoch reproduces 2 and 3;
5. zero rollback transfers occur before the terminal.

Condition 3 is what makes this experiment mean anything. Conditions 2 and 4
are the existing resident-health and return semantics and are not relaxed.

`REFUTED` is a legitimate terminal. If the device does not boot the candidate,
that is a real answer to the single question and the rollback restores service.

## Stop conditions

New device effects freeze immediately, and the terminal is a health
classification rather than a retry, on any of:

- candidate transfer read-back digest mismatch;
- boot timeout at the candidate boot timeout;
- health predicate reached but `/proc/version` **not** matching the pinned
  banner — this is the dangerous case, because it means something booted and it
  is not what we flashed;
- any missing, late, timed-out, or malformed observation;
- any observed write outside `boot`.

No uncertain action is ever replayed. A transfer whose completion is uncertain
consumes its ordinal.

## Recovery

Rollback is the exact V2321 transfer, authorized only after candidate transfer
start, with the same runner and `--expect-sha256 ca978551...`. It is a
predeclared recovery, not a retry of the candidate.

Physical recovery follows the existing A90 target profile and is unchanged by
this design. Download-mode entry and Odin transport semantics are not modified
here; if any change to them turns out to be required, this design must return
for review rather than proceed.

## Preconditions that must hold before approval

Each is independent and none is satisfied by this document:

1. independent review of this design;
2. `GOAL_A90.md` updated to authorize exactly one successor candidate, since
   it currently authorizes none;
3. a fresh connected D0 qualification;
4. a prepared manifest pinning the identities above **and** the exact expected
   candidate `/proc/version` banner;
5. exact attended F1 approval referencing that final manifest;
6. the operator physically present — the A90 v1 runner is attended-only and
   `--operator-attended` must never be asserted in the operator's absence.

## Open risks

- **`uname -r` changes** from `4.14.190-25818860-abA908NKSU5EWA3` to
  `4.14.190`. No A90 native-init path loads kernel modules — every
  `/lib/modules` and `.ko` reference in the tree belongs to S22+ sources — so
  the expected impact is low. It is not zero: any future component that
  resolves a module or firmware path by release string would break, and Debian
  userspace under a later `switch_root` is exactly such a component. This
  should be checked before Option C work depends on the self-built kernel.
- **Functional equivalence is unproved.** A different compiler and linker
  produce a different kernel even where configuration matches. Booting proves
  booting; it does not prove the WLAN, display, GPU, audio, or USB paths behave
  as before. A separate observation set would be needed for that, and this F1
  does not attempt it.
- **The one-page size delta is not evidence of equivalence** and must not be
  cited as reassurance.
- **CFP removal is not reversible by rebuilding.** Restoring it requires
  Samsung's compiler, which is unavailable. If the reduced posture proves
  unacceptable later, the remedy is returning to the stock kernel blob, not
  rebuilding with CFP.

## Why this ordering

The disciplined sequence is: prove the build path boots with the resident's own
userspace and device tree, and only then change a kernel feature. If
`binderfs` were enabled in the same flash and the device failed to boot, the
failure would have two explanations and the attended ordinal would buy one
ambiguous bit. Keeping the change to one variable is the entire reason the
candidate was repacked against the resident.

## Sources

- `GOAL_A90.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`
- `docs/reports/A90_SELF_BUILT_KERNEL_H0_2026-08-16.md`
- `docs/plans/A90_HEADLESS_NATIVE_WIFI_ISOLATED_DEBIAN_DESIGN_2026-08-14.md`
- private: the three artifacts tabulated above
- private: `workspace/private/runs/server-distro/a90-v3406-debian-display-f1-20260801-01/prepared-manifest.json`
  (prior-run transport and observation shape)

## Boundary

Produced host-only from staged artifacts and repository documents. Device,
`/dev`, USB, S22+, and S20+ contacts are zero. No ordinal, identity, candidate,
qualification, approval, manifest, or command is created. No D0, D1, or F1
authority is granted or implied, and this draft is not itself an approval
request.
