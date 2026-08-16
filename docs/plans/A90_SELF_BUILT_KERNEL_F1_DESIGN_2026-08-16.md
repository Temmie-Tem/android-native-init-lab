# A90 self-built kernel F1 design (draft 2, for independent review)

Date: 2026-08-16
Target: operator-owned Samsung Galaxy A90 5G only
Tier of this document: H0 design draft
Device or live effect of this document: none
Status: **DRAFT — grants no authority, creates no candidate, and is not an
approval request**

Supersedes draft 1 of the same date, which was reviewed and returned **no-go**.
Draft 1 was written without reading `docs/operations/targets/A90_TARGET_CONTRACT.md`,
the binding target contract, and it contradicted that contract on the point its
central design choice rested on. The corrections are recorded in
"What draft 1 got wrong" below rather than silently absorbed.

`GOAL_A90.md` states: "No successor candidate, approval, transfer, reboot, or
D1 effect is authorized by this goal." This draft does not authorize that F1
and nothing here changes that.

## The single question

**Does the A90 boot a kernel this project compiled?**

Every prior A90 custom boot image reused the stock kernel blob and changed only
the ramdisk. No self-built `Image` has ever been resident on this target, so
every kernel-side option downstream — including the private `binderfs` instance
the isolated-Debian design needs — rests on an untested assumption.

## What draft 1 got wrong

Recording these plainly is cheaper than rediscovering them.

1. **The candidate identity was contract-violating.** Draft 1 reused the
   resident's ramdisk byte for byte so that the kernel would be the only
   variable. `A90_TARGET_CONTRACT.md:320-324` forbids exactly that: "Every
   replacement candidate uses a new build identity, absent rootfs destination,
   and absent versioned state paths; a prior enable/latch pair is never reused,
   cleared, or reinterpreted to authorize the replacement." `:394-396` adds
   that F1 success requires "its fresh versioned enable/latch paths absent".
   The staged image reuses H24's `/cache/a90-auto-handoff-phase3-minimal-h24.
   enable` and `.done` paths and is therefore **not usable as a candidate**.
2. **The runner invocation did not exist.** Draft 1 specified
   `--from-native --image <path>`. `native_init_flash.py` takes the boot image
   as a positional argument and has no `--image` option.
3. **The transaction owner was wrong.** Draft 1 named `native_init_flash.py` as
   the transport. That helper writes and verifies; it does not own the durable
   journal, approval consumption, rollback state, or terminal result. The
   reviewed owner is `a90_v3403_f1_orchestrator.py`, which invokes the helper.
4. **Paths were relative** where the process requires stable absolute names.
5. **The health predicate was incomplete** against `A90_TARGET_CONTRACT.md:1272-1279`.
6. **Recovery was ambiguous** exactly where the contract is not: "Once candidate
   execution begins, rollback never waits" (`:1268`).
7. **First-use execution qualification was missing** from the preconditions
   (`:1284-1289`).

The review also corrected a framing error: the design's own claim that it kept
"one variable" was the thing that broke the contract. One variable is a good
instinct and it is not a licence to reuse an identity.

## What this F1 does not do

- It does not enable `CONFIG_ANDROID_BINDERFS`. That symbol stays off.
- It does not change the device tree; the candidate reuses the resident's own
  appended DTB region.
- It does not attempt `switch_root`, Debian PID 1, WLAN handoff, or any D1
  effect.
- It does not retire any WLAN gate. `H0D01` through `H0D10` are untouched.
- It does not treat boot success as functional equivalence. Booting proves
  booting, not that WLAN, display, GPU, audio, or USB behave as before.

## What is being accepted, stated before the identities

The candidate kernel has `CONFIG_RKP_CFP`, `CONFIG_RKP_CFP_JOPP`, and
`CONFIG_RKP_CFP_ROPP` disabled. Samsung's JOPP/ROPP control-flow protection
requires a patched LLVM that the OSRC package does not ship and AOSP clang does
not implement. The operator authorized the removal on 2026-08-16.

`docs/reports/A90_SELF_BUILT_KERNEL_H0_2026-08-16.md` records the bounded scope:
the RKP hypervisor layer, `CONFIG_UH_RKP`, `CONFIG_RKP_KDP`, `CONFIG_RKP_NS_PROT`,
and `CONFIG_RKP_DMAP_PROT` are untouched, and `System.map` shows zero `rkp_cfp`,
`jopp_springboard`, and `ropp_` symbols against retained `rkp_init` and
`uh_call`.

**Approving this F1 accepts a reduced kernel exploit-mitigation posture on this
unit for as long as the candidate is resident.** A reviewer unwilling to accept
that should reject this design rather than the artifact. The terminal report
must repeat the same statement and must not let boot success stand in for it.

## Required candidate construction

A self-built boot image is **not itself a candidate**. An intermediate image
pairing the self-built kernel with the resident's ramdisk was produced first and
then deleted: it reused the H24 identity and latch paths, so the contract
forbids it as a candidate, and it also cannot serve as `base_boot` because its
ramdisk is already built. Only the base image below survives.

The candidate must be produced by the reviewed flat builder as a new version
carrying the full `phase3-minimal-h24` definition. It extends
`phase3-minimal-h16` rather than `phase3-minimal-h24` because the builder caps
`extends` depth at 2; the h24 body is therefore copied, not inherited. It sets:

- `[inputs] base_boot` and `base_boot_sha256` pointing at a **base** image that
  pairs the self-built kernel with the v3403 base ramdisk. The builder unpacks
  `base_boot` for the kernel and header arguments and then overlays its own
  init/helper/engine onto that ramdisk, so an already-built image is rejected
  with `base ramdisk already contains the H17 observer key path`;
- a new `profile`, `cycle`, `decision`, and `random_seed`;
- a new `INIT_VERSION` and `INIT_BUILD`;
- **fresh `A90_AUTO_HANDOFF_ENABLE_PATH` and `A90_AUTO_HANDOFF_LATCH_PATH`**
  that have never been used, satisfying `A90_TARGET_CONTRACT.md:320-324,394-396`;
- `validation.init_strings` updated to the new version banner;
- deterministic A/B output, byte-identical across the two builds, as the H24
  lineage already demonstrates.

That build is a separate H0 unit with its own capability and execution
qualification, matching the `capability-qualification.json` and
`execution-qualification.json` that accompany every existing version.

**Built on 2026-08-16** as `phase3-minimal-h24k`, version `0.11.193`, build
`phase3-minimal-h24k-selfbuilt-kernel-nocfp`. A/B output is byte-identical, the
candidate's embedded `Image` hashes to the self-built kernel, only `kernel_size`
differs from the resident header, and the ramdisk carries the fresh
`/cache/a90-auto-handoff-phase3-minimal-h24k.{enable,done}` paths with zero
occurrences of the H24 pair. The version's capability and execution
qualification records are **still absent** and remain a precondition.

## Identities

Absolute paths, as the process requires. All are private and none is committed.

| role | absolute path | size | sha256 |
|---|---|---|---|
| resident | `/home/temmie/dev/android-native-init-lab/workspace/private/outputs/a90-h24-minimal-debian-dev-ab-20260812-01/A/boot.img` | 58,372,096 | `d8c280e4acee5d17d13270fdf25535b4ce05304e786bc22efa84ab16f6b82782` |
| rollback | `/home/temmie/dev/android-native-init-lab/workspace/private/inputs/boot_images/boot_linux_v2321_usb_clean_identity_rodata.img` | 60,882,944 | `ca978551aabe4b39563abaf529ccf2522054952d8b2ad852e632d26da88168cb` |
| builder `base_boot` | `/home/temmie/dev/android-native-init-lab/workspace/private/inputs/boot_images/boot_a90_base_selfbuilt_kernel_20260816.img` | 66,375,680 | `2d0be40158d56b6b053bc1aff6c6e149beb904da43a303b812e8ca6c4d583a9e` |
| self-built `Image` (inside both) | — | 48,826,384 | `6cab67938d2d235ad5ad965abaefe7e3ebda6d13b57251705c91f5f333ab1b6d` |
| **candidate** | `/home/temmie/dev/android-native-init-lab/workspace/private/outputs/a90-h24k-selfbuilt-kernel-ab-20260816-01/A/boot.img` | 58,368,000 | `2c4ca81152987dc484d5b147f7a09a77f16f8fad0b7236cf3c67f4a562c6ceba` |

The resident is H24 `0.11.192`, build
`phase3-minimal-h24-ufs-auth-native-hud-private-card-root-minimal-debian-dev`,
named by `GOAL_A90.md` as the exact installed resident; its A/B build output is
reproducible. The rollback is V2321, which `GOAL_A90.md` names as "the exact
bound rollback for a future, freshly qualified successor", and its digest
matches the `rollback-boot-v2321.img` consumed by prior A90 F1 runs.

## Transport

Owner: `a90_v3403_f1_orchestrator.py`, which owns the durable append-only
journal, approval consumption, rollback state, and terminal result. The
orchestrator invokes the flash helper; the helper is not the transaction.

Helper: `workspace/public/src/scripts/revalidation/native_init_flash.py`, size
43,118, sha256
`366dd38304625d37607916e92ea98a95271bbc4d9dfdc7eea106a5437b6dfe53`,
byte-identical to the helper used by the prior A90 F1 run.

The invocation is the orchestrator's checked form, with the boot image
**positional**:

```
<python> <helper> <boot image path>
  --bridge-host <host> --bridge-port <port> --bridge-timeout <sec>
  --reboot-timeout <sec>
  --expect-sha256 <digest> --expect-version <version>
  --verify-protocol selftest
  --serial <recovery serial, private>
  [--from-native]
```

`--verify-protocol selftest` is pinned rather than left at the helper's `auto`
default. `--boot-block` and `--remote-image` stay at their defaults so a
caller-supplied path cannot widen the payload surface. `boot` is the only
partition written.

## Acceptance predicate

Because the candidate carries a **new** build identity, `--expect-version`
discriminates candidate from rollback on its own, and the candidate image
contains only the self-built kernel — so reaching candidate health *is* proof
that the self-built kernel booted. Draft 1 needed `/proc/version` because it
had reused the resident's identity; that requirement disappears with the
correct construction.

`/proc/version` is retained as a **supplementary** positive record, not as the
load-bearing discriminator, and is not a blocking prerequisite:

```
resident kernel   4.14.190-25818860-abA908NKSU5EWA3 (dpi@SWDK6110), clang 10.0.7, #2 SMP
candidate kernel  4.14.190 (built by this project), clang 12.0.5, #5 SMP
```

Both banners are extractable host-side before any device contact.

Install `PASS_A90_RESIDENT_INSTALLED` requires all of:

1. candidate transfer completes and read-back digest equals the pinned value;
2. exact candidate version/build reported — the new identity, not `0.11.192`;
3. the bound native self-test and health predicates pass;
4. a working bounded control response;
5. physical recovery preserved;
6. the candidate's fresh versioned enable/latch paths **absent**
   (`A90_TARGET_CONTRACT.md:394-396`);
7. zero rollback transfers before the terminal.

## Terminals

Device safety and experiment proof are separate axes
(`A90_TARGET_CONTRACT.md:62-71`):

| axis | value | meaning here |
|---|---|---|
| device safety | `RESIDENT_HEALTHY` | candidate installed and the unit is controlled and recoverable |
| device safety | `RECOVERY_REQUIRED` | rollback itself failed |
| experiment proof | `PROVED` | the A90 booted a kernel this project compiled |
| experiment proof | `REFUTED` | it did not, and the device reported state contradicting health |
| experiment proof | `NO_PROOF_OBSERVER` | the host could not reach, parse, or decide |

`REFUTED` is a legitimate answer to the single question. Per `:102-121`, only
device-attributable evidence may burn an ordinal; a missing, late, or malformed
observation is `NO_PROOF_OBSERVER`, which freezes new non-recovery device
effects without closing the campaign and never permits candidate replay.

Observation is not attribution (`:123-128`). A responding endpoint proves only
that the observation occurred; the returned USB epoch must be bound by
same-intent evidence — endpoint identity, boot generation, stale-node
rejection, and same-target attribution — not by a port answering.

## State machine and recovery

Before candidate execution begins, a stop is a stop: new device effects freeze
and the run closes without a transfer.

**Once candidate execution begins, rollback never waits** (`:1268`). There is no
second acknowledgement and no candidate retry. Exact rollback is required on:

- candidate transfer ambiguity;
- wrong identity;
- explicit initial-health failure;
- inability to establish initial control;
- lost recovery.

Rollback is the one bound V2321 transfer through the same helper with
`--expect-sha256 ca978551...`. The run closes only after V2321 health is
verified. A rollback failure is `RECOVERY_REQUIRED`. An uncertain released
rollback is never replayed or closed from running baseline health; it remains
explicitly recovery-pending.

If native control is unavailable, recovery proceeds through the existing
physical Download/recovery path in the target contract, which this design does
not modify. Any required change to Download-mode entry or Odin transport
returns this design for review rather than proceeding.

Once `RESIDENT_HEALTHY` is durably recorded, a later refutation or
observer-only no-proof does not retroactively fail installation and does not
require rollback (`:1276-1279`).

## Target isolation

Resolve exactly one A90 target and its private profile before every action.
Inventory all attached devices first, select the A90 explicitly, and report
that S22+ and S20+ were untouched with zero commands. Serials and topology
identifiers stay private. Any target ambiguity, unexpected identity change, or
lost physical recovery path ends the session (`A90_TARGET_CONTRACT.md:40-49`).

## Preconditions

Each is independent; none is satisfied by this document.

1. independent review of this draft;
2. the new flat-builder candidate version built, A/B reproducible, and
   qualified — see "Required candidate construction";
3. `GOAL_A90.md` updated to authorize exactly one successor candidate, since it
   authorizes none today;
4. one fresh `A90_F1_RESIDENT_INSTALL_V1` binding for that candidate plus its
   exact rollback (`A90_TARGET_CONTRACT.md:1268-1270`);
5. first-use execution qualification: runner schema update, focused tests,
   execution review, connected preflight, and compatibility binding
   (`:1284-1289`);
6. a fresh connected D0;
7. an empty durable journal, checked flash and bridge closures, and proven
   physical recovery availability (`:1262-1265`);
8. exact attended F1 approval referencing the final manifest;
9. the operator physically present — the A90 v1 runner is attended-only and
   `--operator-attended` must never be asserted in the operator's absence.

## Open risks

- **`uname -r` changes** from `4.14.190-25818860-abA908NKSU5EWA3` to
  `4.14.190`. No A90 native-init path loads kernel modules — every
  `/lib/modules` and `.ko` reference in the tree belongs to S22+ sources — so
  expected impact is low but not zero. Debian userspace under a later
  `switch_root` resolves module paths by release string and is exactly the
  component that would break. Check before Option C depends on this kernel.
- **Functional equivalence is unproved.** A different compiler and linker
  produce a different kernel even where configuration matches. A separate
  observation set would be needed, and this F1 does not attempt it.
- **The one-page `Image` size delta is not evidence of equivalence** and must
  not be cited as reassurance.
- **CFP removal is not reversible by rebuilding.** Restoring it requires
  Samsung's compiler. The remedy, if the posture proves unacceptable, is
  returning to the stock kernel blob.
- **Two things change at once, unavoidably.** The candidate necessarily carries
  a new userspace build identity alongside the new kernel. The userspace delta
  is confined to version/build strings and fresh enable/latch paths, is
  deterministic, and is A/B verifiable — but it is not zero, and a boot failure
  must be attributed rather than assumed kernel-side.

## Why this ordering

Prove the build path boots before changing a kernel feature. If `binderfs` were
enabled in the same flash and the device failed to boot, the failure would have
two explanations and the attended ordinal would buy one ambiguous bit.

## Sources

- `AGENTS.md`
- `docs/operations/targets/A90_TARGET_CONTRACT.md`
- `docs/operations/DEVICE_ACTION_PROCESS_V2.md`
- `docs/operations/DEVICE_ACTION_RISK_TIERS.md`
- `GOAL_A90.md`
- `docs/reports/A90_SELF_BUILT_KERNEL_H0_2026-08-16.md`
- `workspace/public/src/scripts/server-distro/a90_v3403_f1_orchestrator.py`
- `workspace/public/src/scripts/revalidation/native_init_flash.py`
- `workspace/public/src/scripts/revalidation/a90_flat_builder/versions/phase3-minimal-h24/manifest.toml`
- private: the artifacts tabulated above

## Boundary

Produced host-only from staged artifacts and repository documents. Device,
`/dev`, USB, S22+, and S20+ contacts are zero. No ordinal, identity, candidate,
qualification, approval, manifest, or command is created. No D0, D1, or F1
authority is granted or implied, and this draft is not itself an approval
request.
