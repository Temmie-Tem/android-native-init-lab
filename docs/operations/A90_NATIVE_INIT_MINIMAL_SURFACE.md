# A90 native-init minimal surface

Status: `H0_PHASE3_MINIMAL_C_CAPABILITY_PASS_GO`

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

## Phase3 minimal-B inert bridge API boundary

The next no-authority profile replaces `a90_doomgeneric_bridge.c` in the
selected init sources with `a90_doomgeneric_bridge_inert.c`. The inert module
keeps the nine existing bridge ABI entry points temporarily, supplies
non-null diagnostic strings, and returns `-ENOTSUP` for every operational
request. The module itself opens no file, starts no process, creates no socket,
and sends no input. This contains the bridge implementation without pretending
the inherited menu/HUD callsites are already removed.

Independent review found one essential scope limit: `video demo doom
loop-start` can fork before its child reaches the inert helper API, and the
parent can record an audio start. Therefore minimal-B qualifies only the exact
bridge API boundary; it does not claim that every inherited Doom command is
globally inert. The next slice must block or delete those entry points before
any caller-side effect.

The fresh private A/B build is byte-identical and retains all permanent input
pins. Independent `newc` parsing again found 33 members, the three required
entries, and zero Doom engine-family member. The full bridge object was 14,016
bytes and had file, helper, process, and socket dependencies; the inert object
is 3,472 bytes with zero undefined symbols. The stripped init remains
1,789,712 bytes because the boot layout is alignment-stable, but its SHA256
changed with the behavior boundary.

This is still H0 only: `candidate_authority=false`, no device was contacted,
and no payload, partition write, or flash occurred. The builder capability
closure is unchanged and retains its reusable `PASS_GO`. Independent review of
the exact nine-entry inert bridge API also returned scoped, capability-wide
`PASS_GO`; caller-side global inertness is explicitly outside that receipt. Any
later boot use remains attended F1 with a fresh exact qualification and binding.

## Phase3 minimal-C no-Doom command surface

The no-authority minimal-C profile now defines
`A90_MINIMAL_NO_DOOM_COMMAND_SURFACE=1`. Under that exact feature selection,
the Doom demo menu item and menu action are absent, the dedicated `doompad`,
`doominput`, and `doominputmux` shell commands are absent, and `video demo
doom` takes a dedicated pre-dispatch reject before generic busy handling,
command logging, display/HUD shutdown, or reaping. It returns `-ENOTSUP` with
an explicit removal marker without reaching inherited fork, audio, file-open,
file-cleanup, log, socket, bridge, DRM, or process effects. Writing the marker,
usage, and protocol/result framing to the already-bound console descriptor and
in-memory result bookkeeping are retained. Existing profiles keep the prior
behavior because the feature default is zero.

Both the operational and inert bridge sources leave the selected manifest.
The root object now has zero undefined bridge symbols and zero bridge call
relocations. The profile contains 59 translation units, 430 global symbols,
264 internal object edges, 51 objects referenced directly by the root, and all
59 selected objects remain reachable. The monolithic root object decreases
from 902,248 to 819,168 bytes; the stripped init decreases by 16 bytes because
the packed boot layout remains alignment-stable.

Fresh private A/B builds are byte-identical. Independent `newc` parsing found
33 members, all required entries, and no Doom engine-family member. The six
objects that own the proved switch_root, KMS/display, USB-local networking,
SSH service, resident return, and recovery paths are byte-identical to
minimal-B.

This capability is deliberately narrower than a claim that every historical
Doom trace has left native-init. The compiled init still contains Doom input
role labels, audio capability labels, monitor/HUD informational strings, and
a private runtime path prefix in an audio setcal allowlist. None is a removed
menu, shell, video-dispatch, metadata/help, or bridge entry point. They remain
named source-removal candidates for later H0 slices.

This result is H0 only: `candidate_authority=false`, no device was contacted,
and no payload, partition write, or flash occurred. The first independent
capability review correctly refused `PASS_GO` because generic `CMD_DISPLAY`
dispatch stopped the HUD before the handler-level reject. The repaired closure
moves the exact removed-Doom reject ahead of that generic effect path. Repeat
independent review returned capability-wide `PASS_GO` with no unresolved
finding. The capability closure also binds the unchanged shell,
protocol-framing, console, and existing-console-fd write implementations
because they define the only allowed console and in-memory effects. The receipt
remains reusable across manifests, qualifications, ordinals, and campaigns
until one of its 14 bound source keys or named semantics changes, or a new
hazard or incident occurs. The previously reviewed
flat-builder closure is unchanged and its
capability-wide `PASS_GO` remains reusable.

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
still satisfies nine direct undefined symbols from `init_v724.o`:
status, probe, WAD verification, play, frame rendering and reading, input file
and socket writes, and frame-loop helper launch.

In minimal-B those same nine incoming references terminate at the inert
boundary. That object has no outgoing undefined reference, so the operational
bridge's helper, file, process, and socket dependency edges are gone. The
remaining 15 call relocations are now the exact next deletion surface;
removing them will allow the inert object itself to leave the profile.

The repeated graph calculation keeps all 60 objects reachable but reduces
internal object edges from 267 to 265 by removing the bridge-to-helper and
bridge-to-run edges. The nine symbols correspond to 15 call relocations across
the Doom menu, doompad command, video status/demo, and visible-loop functions.

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

1. The no-authority minimal-C manifest and deterministic A/B build are
   complete; accepted resident and rollback artifacts remain unchanged.
2. Doom menu and dedicated shell entry points are absent, and `video demo
   doom` stops before caller-side effects. Neither bridge implementation is
   selected.
3. The reviewed flat-builder source/schema/semantics closure is unchanged, so
   its capability-wide `PASS_GO` remains reusable.
4. Independent review of the exact no-Doom command-surface capability returned
   reusable `PASS_GO` with no unresolved finding.
5. The next H0 slice is the 11-command `boot-write/flash` experiment surface
   and its two directly referenced objects (`a90_boot_write_e1.o` and
   `a90_boot_write_probe.o`, about 104 KiB combined). Remove that surface and
   repeat the graph while preserving the proved switch_root, display, SSH,
   return, and recovery objects.
6. Stop at H0. Any later boot candidate requires fresh qualification and
   attended boot-only F1.

Focused minimal-C flat-builder regression passes `26/26`. Cross-compilation,
private pin validation, A/B byte comparison, archive inspection, and artifact
identity checks pass. No device was contacted for minimal-C.
