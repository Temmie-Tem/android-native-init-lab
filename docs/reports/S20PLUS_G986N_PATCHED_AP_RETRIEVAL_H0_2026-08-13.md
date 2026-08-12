# S20+ G986N patched AP retrieval H0

Date: 2026-08-13

Status: **PASS_GO - ROUTINE D0 RETRIEVAL ACTIVATED**

## Purpose

The operator asked to retrieve the AP archive produced interactively by the
official Magisk v30.7 app after the previously reviewed APK installation and
stock-AP staging actions completed. Existing authority did not permit general
Download enumeration or an arbitrary device-to-host pull, so this unit defines
one closed D0 retrieval without expanding root, flash, or partition authority.

## Proposed closure

- exact target remains `SM-G986N` / `y2q` / `y2qksx` /
  `G986NKSS8IYC2` with the existing pinned ADB tool and normal-health checks;
- discovery is one fixed `find` expression limited to direct regular files in
  `/sdcard/Download` matching
  `magisk_patched-30700_[A-Za-z0-9_-]{1,64}.tar`, followed on-device by the
  exact `LC_ALL=C` extended-regex filter so invalid glob matches never reach
  host output;
- zero, multiple, malformed, traversal-shaped, symlink, or out-of-range
  candidates fail before pull;
- the accepted file must be between 1 GiB and 12 GiB and gets a device-side
  SHA-256 before one `adb pull -a`;
- the host destination is fixed below
  `workspace/private/inputs/s20plus_g986n/G986NKSS8IYC2_KTC/patched/`;
- host free space must exceed the file size by at least 1 GiB;
- a unique partial is size/hash checked and published with atomic no-clobber
  `link`, then made read-only; and
- there is no device write, deletion, root, package-data read, partition/block
  access, reboot, mode transition, Odin command, or F1 action.

The existing fixed active guard excludes concurrent retrieval/setup/control.
Because retrieval has no device effect, a handled failure may close the guard;
the unique partial must first be absent or removed as an exact regular
non-symlink file, and an unexpected node or cleanup failure retains the guard.
An existing final artifact is never replaced.
Raw serial/topology/boot ID and the retrieved payload remain private.

## Host validation required

Focused tests must cover exact success, zero/multiple/malformed discovery,
wrong size, device/host hash mismatch, existing destination no-clobber, wrong
target before pull, private-only publication, no device effect, and absence of
S22+/A90/other-target commands. The full S20+ suite, `py_compile`, source
exclusion checks, device-hidden dry run, and `git diff --check` must pass.

## Review and activation

Independent review of the common D0 wording, S20+ target contract, runner,
tests, report, goal, and registry interaction returned `PASS_GO` with no
unresolved finding. The review reproduced and closed two findings before pass:
unexpected partial-node cleanup now retains the guard, and device-side exact
ASCII filtering prevents invalid glob matches from reaching host output.

The reviewed pre-activation runner SHA-256 was
`5361f986811f9283b340c7ee37f2ff6945f3081979d395409201e9b823f51bad`.
The permitted mechanical activation changed only the activation constant and
named status/hash assertions. The active runner SHA-256 is
`7b1d8989db5ffbf012cbf356e4e1411d5e487e965361b4ea61307a508b17bc72`.
Activation did not contact a device and grants only the exact current-request
D0 retrieval described above.

## Live result

The exact current operator request consumed one retrieval invocation and
returned `PASS_S20PLUS_G986N_PATCHED_AP_RETRIEVED_VERIFIED`. The one accepted
artifact was `magisk_patched-30700_kFiLC.tar`, `7,362,972,672` bytes, SHA-256
`a025e13cf5665701df2229e07ecdab404a906d816aa7dd93aa3393bf8797b5f6`.
Device and host SHA-256 values matched. The final file is a read-only regular
file in the fixed private firmware destination, no partial remains, and the
active guard was released after the durable result.

The run used two global inventories and six exact-target commands. Device
effect count, S22+, A90, other-target, root, reboot, mode, partition, flash, and
F1 counts were all zero/false. The private result SHA-256 is
`c6183f5679510d713d2cefc7c58f7fbeebb811fbeb86e503f6567ca8f4b3e292`.
