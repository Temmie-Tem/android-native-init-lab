# S20+ G986N Native-Canary R1 Prepare Incident

Date: 2026-08-16

Target: operator-owned `SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2` only

Status: **PASS_GO - FINITE PREFLIGHT CLASSIFIER ACTIVE - NO CURRENT RUN OR APPROVAL**

## Outcome

One fresh connected R1 preparation selected the exact target, completed the
bounded Android-health check, and verified working Magisk root. It then stopped
at the fixed Magisk install-closure read before creating a prepared binding or
shared action guard.

The failed preparation created no approval, staged file, root-data/module
write, install intent, reboot intent, Download transition, Odin intent, or
partition transfer. Pre-guard private run directories are preserved as private
host evidence and grant no continuation authority. The shared S20+ guard is
absent.

An earlier invocation failed even earlier because the sandbox could not create
the local ADB daemon listener. A bounded redacted host diagnostic established
that condition without exposing the serial; the later preparation reached the
target and root checks, so USB detection and ADB authorization were not the
material blocker.

## Stop decision

The active runner reported only `N1 Magisk install closure read failed`. That
message did not identify whether the fixed Magisk binary, BusyBox, or
`util_functions.sh` was absent, indirect, non-regular, unreadable, or had
unsafe metadata. No additional device command or preparation retry followed
the material preflight failure.

## H0 remediation candidate

The correction keeps the same three constant paths and the same single fixed
root-read boundary. Its shell probe always emits exactly three ordered records
and maps expected incompatibilities to a finite vocabulary:

- `symlink`, `absent`, or `not-regular`;
- one of the exact mode, uid, gid, link-count, size, or SHA-256 read failures;
  or
- host-side `unsafe-metadata` after strict receipt parsing.

Known per-file read failures suppress raw stderr. The host parser requires the
exact label order, cardinality, token vocabulary, ASCII framing, and existing
safe receipt grammar. A classified failure stops before Magisk version,
inventory, staging, or any persistent effect. No CLI argument, path, shell
fragment, module ID, or generic root command is added.

Independent review returned `PASS_GO` for the finite classifier and hostile
shell fixture. Exact identity activation set the root-data runner to 212,818
bytes, SHA-256
`536cb88c67ddd378c511b3e6c659433009b68a5f2d9b767f7e41afdcf6a567a3`,
normalized
`83ea1116e17ba1551633d9e4b73008f512b83764957f6bcc9bfd84f79e2479aa`.
Focused hostile tests pass 114/114 and the exact eight-module S20+ aggregate
passes 276/276.
A later live preparation still needs a fresh direct operator request and is not
authorized by this report.
