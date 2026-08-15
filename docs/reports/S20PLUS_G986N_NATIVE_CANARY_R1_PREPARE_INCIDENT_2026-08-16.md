# S20+ G986N Native-Canary R1 Prepare Incident

Date: 2026-08-16

Target: operator-owned `SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2` only

Status: **PASS_GO - QUOTED ROOT PREFLIGHT ACTIVE - NO CURRENT RUN OR APPROVAL**

## Outcome

Two separately requested connected R1 preparations selected the exact target,
completed the bounded Android-health check, and verified working Magisk root.
Both stopped at the fixed Magisk install-closure read before creating a
prepared binding or shared action guard.

The failed preparation created no approval, staged file, root-data/module
write, install intent, reboot intent, Download transition, Odin intent, or
partition transfer. Pre-guard private run directories are preserved as private
host evidence and grant no continuation authority. The shared S20+ guard is
absent.

An earlier invocation failed even earlier because the sandbox could not create
the local ADB daemon listener. A bounded redacted host diagnostic established
that condition without exposing the serial; both later preparations reached
the target and root checks, so USB detection and ADB authorization were not
the material blocker.

## Stop decision

The first active runner reported only `N1 Magisk install closure read failed`.
Its reviewed finite classifier made the next separately authorized preparation
report `magisk=absent,busybox=absent,util_functions=absent`. No guard or effect
followed either result.

That second output did **not** prove the files were absent. AOSP ADB constructs
the remote shell command by joining every argument after `shell` with spaces
and deliberately does not escape them. The runner passed its multiline script
as an unquoted final argument, so `su -c` was not guaranteed to receive the
complete script as one command. Remaining lines could execute in the ordinary
shell context, where inaccessible root paths also appeared absent. No Magisk
reinstall or root-data change was performed from that invalid inference.

## H0 corrections

The first correction kept the same three constant paths and the same single fixed
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
shell fixture.

The second correction changes only the common fixed `root_argv` framing. It
shell-quotes the complete script before ADB joins the remote arguments, so the
remote shell removes that quoting and passes exactly one script argument to
`su -c`. The Magisk closure additionally runs absolute-path `toybox id -u`
inside the same command and stops with fixed rc `97` unless it is UID 0. A
tracked fake-ADB-join/fake-`su` shell fixture covers newlines, quotes, and
variable expansion; all root-script consumers use this one wrapper.

The ADB source authority is the immutable AOSP
[`client/commandline.cpp`](https://android.googlesource.com/platform/packages/modules/adb/+/7c2fd99d6ec7e0d2d977ba03cecc82375af1baad/client/commandline.cpp),
whose `adb shell` path joins command arguments without escaping. Independent
review returned `PASS_GO` for the self-blocked quoting candidate at SHA-256
`66fcf659b2025a477bc19336c746bb745774258f8395b860038b0f906b37d274`,
normalized
`5e29e8659fb493f0b1885cdc8954e11ec8be6fb60e6953e80923da4ed225300c`.
Exact identity activation set the root-data runner to 213,525 bytes, SHA-256
`71cb0617d6989ad1bbfce98779796e7cf923c65fb497b67cd4ea93fe9f4253b1`,
with the same normalized hash. Focused hostile tests pass 115/115 and the exact
eight-module S20+ aggregate passes 277/277.
A later live preparation still needs a fresh direct operator request and is not
authorized by this report.
