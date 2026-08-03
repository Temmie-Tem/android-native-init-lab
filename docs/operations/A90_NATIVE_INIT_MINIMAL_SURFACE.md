# A90 native-init minimal surface

Status: `H0_PHASE3_MINIMAL_A_CAPABILITY_PASS_GO`

Date: 2026-08-03

## Purpose

This is the live dependency map for reducing A90 native-init after the
qualified `switch_root` proof. It grants no D0, D1, or F1 authority and does
not select a boot candidate. Source removal remains H0 until a new boot image
is built; any later boot transfer is attended F1.

The current `phase2-display-v1` flat profile is inherited rather than minimal.
Its resolved manifest contains 60 native-init C translation units, 84 init
flags, one Wi-Fi/firmware helper with 29 flags, and an 80-source Doom engine.
Those counts describe the resident artifact; they are not claims that every
item belongs in the product surface.

`workspace/public/src/scripts/revalidation/a90_native_minimal_surface_v1.py`
now revalidates the manifest lineage, public source keys, private input pins,
exact counts, and `candidate_authority=false`. Its first slice changes no
native-init source, helper, accepted artifact, or device state. The successor
profile removes 47 Doom-only init flags while retaining all 60 native-init
translation units for the first reachability slice.

## Phase3 minimal-A H0 build result

The no-authority `phase3-minimal-a-no-doom-engine` successor now builds the
init and helper but skips the separate 80-source Doom engine product. It also
requires the packed ramdisk to contain exactly the selected engine set: the
active engine only for an enabled profile, or no private Doom engine for a
disabled profile.

Host-only findings were fixed before accepting the deterministic output:

- Removing `a90_doomgeneric_bridge.c` caused an init link failure because
  `init_v724.c` still directly references bridge entry points. The source stays
  in this slice; the incomplete output was not reused.
- A successful intermediate ramdisk still contained three older engine
  variants inherited from the base boot. Those variants were added to the
  obsolete set, and an exact engine-family listing check now rejects any stale
  variant. That intermediate output was also not reused.
- The first independent capability review refused `PASS_GO` because the
  engine-family check inspected the staging directory after packing rather
  than reopening the emitted CPIO. The builder now parses the emitted `newc`
  bytes independently of the external cpio tool, rejects malformed archives,
  and validates required entries and the exact engine set from those bytes.
- The next review refused `PASS_GO` because noncanonical path aliases and
  Python's permissive hexadecimal parser could bypass the initial parser.
  Archive names must now equal their canonical POSIX representation, all 13
  numeric fields must be exactly eight ASCII hexadecimal digits, and member
  alignment padding must be zero. Focused tests cover each reported alias and
  malformed numeric form.

The fresh final private A/B build is byte-identical, keeps the accepted input
boot unchanged, binds both builder source files by path, size, and SHA256, and
has `candidate_authority=false`. Independent parsing found 33 archive members,
including the init, helper, and audio manifest, with no
`bin/a90_doomgeneric_private_engine_*` member.

| Artifact | v3404 reference bytes | minimal-A bytes | Difference |
|---|---:|---:|---:|
| boot | 66,379,776 | 61,505,536 | -4,874,240 |
| ramdisk | 16,545,280 | 11,673,088 | -4,872,192 |
| init | 1,855,248 | 1,789,712 | -65,536 |
| helper | 1,649,904 | 1,649,904 | 0 |
| separate Doom engine | 1,201,512 | absent | -1,201,512 |

This result is H0 evidence only. It is not an F1 candidate, qualification, or
device authority. Independent review of the exact builder and manifest closure
returned reusable `PASS_GO` with no unresolved finding. The capability receipt
remains reusable across manifests, qualifications, ordinals, and campaigns only
until a bound execution-critical closure changes or a new hazard or incident
occurs. Any later F1 still requires fresh qualification and attended authority.

## Object-symbol reachability inventory

A read-only comparison of the deterministic phase2 and minimal-A unstripped
init objects found the same link-level graph in both profiles:

| Measure | phase2 | minimal-A |
|---|---:|---:|
| init translation units | 60 | 60 |
| defined global symbols | 439 | 439 |
| internal object dependency edges | 267 | 267 |
| objects referenced directly by `init_v724.o` | 52 | 52 |
| objects reachable from `init_v724.o` | 60 | 60 |
| non-root objects with zero incoming references | 0 | 0 |

Only four object sizes changed after removing the 47 Doom-only flags:
`init_v724.o` decreased by 29,680 bytes, `a90_doomgeneric_bridge.o` by 440
bytes, and `a90_longsoak.o` and `a90_wififeas.o` by 8 bytes each. The bridge
still satisfies nine direct undefined references from `init_v724.o`:
status, probe, WAD verification, play, frame rendering and reading, input file
and socket writes, and frame-loop helper launch.

This is link-symbol reachability, not runtime necessity proof. It shows why
deleting a translation unit from the manifest alone fails, but it does not
justify retaining all 60 units. The next slice must first isolate or remove the
monolithic menu/HUD/command callsites (or provide an explicitly inert boundary)
and then repeat the link graph before dropping the bridge implementation.

## Debian ownership already proved

The attended ordinal and two qualified unattended ordinals independently
prove the following after `switch_root`:

| Function | Debian proof | Native steady-state disposition |
|---|---|---|
| PID 1 and service supervision | `/usr/sbin/init` is PID 1 | move to Debian |
| USB-local IP and SSH | inherited `ncm0` is configured and Dropbear answers | move policy and service to Debian |
| DRM/KMS display | Debian obtains DRM master, creates a framebuffer, and completes `SETCRTC` | remove native presenter ownership before handoff |
| bounded return initiation | Debian starts the bounded automatic return path | keep only native recovery landing and health |

Physical visibility is proved by the attended ordinal only. The unattended
ordinals prove the same mechanical DRM path without asserting a human-visible
observation.

## Native functions retained now

| Native function | Why it remains | Named unproved Debian dependency |
|---|---|---|
| early USB ACM/NCM control | exact-target D0, handoff control, and post-return recovery must exist before Debian SSH | Debian cold-start gadget creation and recovery control without a native channel |
| SD identity and immutable root selection | the future root must be selected and hash-checked before Debian becomes PID 1 | Debian cannot validate its own not-yet-mounted root before `switch_root` without a smaller initramfs owner |
| work-copy, loop, mount, and mount-move setup | the immutable source stays untouched and the writable root must be ready before exec | equivalent Debian/initramfs bootstrap with the same source/work separation and cleanup proof |
| native DRM/service release | every predecessor DRM owner must be gone before Debian can become master | Debian acquisition in the presence of an unreleased native owner is not proved |
| the one-shot `switch_root` primitive | it is the ownership-transfer boundary itself | no replacement is needed unless the bootstrap owner changes |
| resident return health and diagnostics | failed Debian startup must land in an exact observable recovery environment | Debian cannot report health after it has exited or before its SSH/display observers start |
| Wi-Fi vendor bring-up, if retained | the current D1 proof uses USB-local NCM, not Debian Wi-Fi | Debian firmware, regulatory, association, and recovery ownership on this kernel |

## Remove or prove before retaining

The inherited Doom engine, game adapter, demo HUD, audio demo, stress, input
demo, boot-write experiments, historical UI applications, and their feature
flags are not dependencies of the proved Debian PID1/SSH/display path. They are
removal candidates for the minimal product profile. They must not be justified
merely because they are present in the resident rollback baseline.

Native audio, touch/input, sensors, Wi-Fi uplink, application supervision, and
general logging may remain only when the product objective requires them and a
specific Debian replacement is still unproved. Otherwise they leave the
minimal profile rather than becoming permanent bridge duties.

## Next bounded H0 build unit

1. The read-only inventory has frozen and printed/hashed the current
   flat-builder source keys without editing accepted resident or rollback
   artifacts.
2. The no-authority successor profile and deterministic A/B build are complete.
3. Independent review of the changed flat-builder capability closure is
   complete with reusable `PASS_GO`.
4. The object-symbol reachability diff is complete: all 60 units remain in one
   root-connected graph, so file-only removal is not a valid next step.
5. Stop at H0. A changed boot candidate requires refreshed qualification,
   independent review of its changed closure, and attended boot-only F1.

Focused inventory regression passes `3/3`; flat-builder and Phase 1A regression
passes `26/26`. `py_compile`, private pin validation, A/B byte comparison,
archive inspection, and `git diff --check` pass. No device was contacted.
