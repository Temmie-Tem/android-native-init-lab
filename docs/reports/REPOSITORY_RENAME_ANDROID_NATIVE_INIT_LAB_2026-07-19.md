# Repository Rename: Android Native Init Lab

Date: 2026-07-19 KST

## Decision

The repository identity is `android-native-init-lab` and its display title is
`Android Native Init Lab`.

The previous name, `A90_5G_rooting`, described the project's original single-
device rooting/recovery phase. It no longer represented the active tree, which
contains established Galaxy A90 5G native-init work and an active Galaxy S22+
vendor-kernel/PID1 frontier.

The new name follows the shared method rather than a device or vendor:

- Android vendor boot chain and kernel as the substrate;
- a custom native `/init` as PID 1;
- a minimal native userspace and target-specific observation/recovery paths;
- multiple owned research devices with evidence and authorization kept separate.

The `-lab` suffix distinguishes this research workspace from Android's own
first-stage init implementation and avoids claiming a completed Linux
distribution port or production framework.

## Recovery Baseline

The renamed checkout was restored from the complete recovered Git bundle before
any identity edit. The verified baseline is:

- commit: `3d52bd4c7fbdb319918eec4f19a81c3bd0a6333c`
- root tree: `a628eba3c1f9c81ded950c5ac4cb909b647b0142`
- recovered branch: `recovery/original-3d52bd4c-20260715`
- integrity check: `git fsck --full --no-dangling` passed with no output

The damaged `A90_5G_rooting` working directory was not merged into this
checkout. The recovered bundle remains configured as the read-only provenance
remote named `recovery-bundle`.

## Scope

This rename changes current project-level identity only:

- root README title, scope, targets, and current frontier;
- `GOAL.md` headline and multi-target iteration contract;
- documentation index title and entry guidance.

Historical reports, historical local paths, target-specific `a90_*` and
`s22plus_*` identifiers, artifact names, protocol markers, and pinned hashes are
not renamed. Their existing names are part of the evidence and implementation
contracts.

No build, image generation, device connection, reboot, transfer, flash, or live
authorization occurred in this unit. Renaming the hosted GitHub repository and
updating the final `origin` URL are separate administrative actions.
