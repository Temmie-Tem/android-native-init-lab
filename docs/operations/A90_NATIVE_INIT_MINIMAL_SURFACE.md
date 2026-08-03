# A90 native-init minimal surface

Status: `H0_DEPENDENCY_MAP_V1`

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

1. Freeze and print/hash the current flat-builder source keys; do not edit the
   accepted resident or rollback artifacts.
2. Add a no-authority successor profile that first removes the separate Doom
   engine and obsolete ramdisk engines while preserving bootstrap, USB,
   storage, release, handoff, return, and health behavior.
3. Build the successor twice from the same pinned inputs and require identical
   init, ramdisk, and boot hashes.
4. Produce a symbol/reachability diff for the 60 native translation units and
   classify every remaining function against this map.
5. Stop at H0. A changed boot candidate requires refreshed qualification,
   independent review of its changed closure, and attended boot-only F1.
