# S22+ native storage census H0

The operator selected a **64 GiB native-only partition**, retained Android as
a comparison environment, and explicitly allowed clearing the current Android
apps, settings and user data. This removes data-preserving shrink from the
required scope. It does not establish a safe GPT modification or restoration.

The smallest missing evidence is the actual UFS LU0 geometry and original GPT.
The new V3 `storage-census` operation implements that fixed D0 read on admitted
P393, without a new native image, normal CONTROL or image transfer. The census
implementation and its narrow common/target read exception received independent
`PASS_GO` for both current and publication source closures. No new grant,
device command, GPT write or formatting has occurred.

## Why the firmware table is insufficient

The retained FYG8 CSC contains `G0Q_USA_SINGLEW.pit`, 15,324 bytes, SHA-256
`e9b6e141bdd046d76db1c2d8cf547cd79fa239776734ea6a9e0efa10e385bd9d`.
The 112 records include GPT/PIT/PAD entries and repeated bootloader labels;
they are not 112 usable filesystems. The 4096-byte PIT unit agrees with four
actual stock image lengths and the retained super metadata.

The USERDATA record has start block 3,726,848 and count zero. Its template
secondary-GPT address is not a current 256 GB LU0-capacity measurement. Neither
the actual userdata end nor a valid 64 GiB split address follows from these
values. CACHE is 800 MiB, correcting the earlier unquantified description as
small; that separate option does not satisfy the selected 64 GiB goal.

Current Odin evidence proves original boot-image recovery through an intact
layout. It does **not** prove restoration of changed LU0 GPT, or continued
Download availability after a GPT interruption. Generic GPT backup rules and
published MediaTek/LK Odin research are not exact Qualcomm FYG8 recovery proof.
The independent preliminary review therefore permits no partition-write plan.

## Fixed read and separate results

The existing V3 owner claims the unique prior native tail and consumes one
operation immediately before its native attempt. Host preflight failure stays
unconsumed. One authenticated session performs existing fixed health checks,
one fixed census EXEC and DETACH/actual close. Its immutable source-bound task
uses V3's finite returned-grant mechanism and selected recovery mode.

The census identifies one userdata node under the FYG8 UFS controller's LU0,
checks logical block size and capacity, and retains matching before/after
userdata/parent geometry. Its reads cover only six initial and five final
4096-byte metadata blocks. The parser requires complete primary/backup GPT
headers and arrays inside those captures, valid CRCs, equal tables,
nonoverlapping partition extents, and agreement with the sysfs userdata extent.
All GPT names, unique identifiers and raw bytes stay private.

Source inspection found that native `/dev` is tmpfs, without udev/devtmpfs;
assuming an existing `/dev/sda` would have been a foreseeable failed trial.
The fixed script therefore creates one mode-0400 block alias
`/dev/.s22-gpt-$$` in the existing `/dev` tmpfs from the verified LU0 device
number. It refuses an existing path and arms cleanup only after creation. A successful final
marker follows removal. Failed cleanup remains unproved and is not retried.
The mode bits do not contain privileged root; the reviewed input-only command
is the access boundary. No storage byte is written by creating this RAM alias.

The readable script has a byte-checked literal gzip/base64 representation to
fit the existing 767-byte command limit. It is a fixed transport encoding,
not a caller-supplied script or a native protocol expansion. The native C,
authentication key, P393 AP and reviewed native source closure remain unchanged.
The final command is 759 bytes; the readable script is 883 bytes. The frozen
third review input's `command_bytes: 767` denotes the limit, not the final
length; the separate review close records this correction without rewriting it.

`PASS_METADATA_ONLY` is separate from native health. A complete negative
command or invalid metadata returns `NO_PROOF` and may still end with proved
health/DETACH. Uncertain protocol delivery retains the existing original-A
recovery path, with actual attendance for recovery. No result grants GPT-write
or format authority; those scopes still require their own exact restoration
evidence and common-boundary review.

## Validation and evidence

The **56 focused tests pass**, with all **14 changed-path tests** repeated
successfully for the final command. The raw test producers returned zero
without timeout, overflow or producer error. An initial test expected the
wrong exception class for another operation's recovery owner; that expectation
was corrected without changing the owner rejection. The outer H0 capture check
initially rejected unittest's normal stderr report; reopening the same complete
raw receipt establishes the successful result without rerunning a device action.

Independent review found that an oversized decimal device number could raise
a plain conversion exception after successful DETACH. The corrected parser
bounds decimal and hexadecimal spellings to the target kernel's 12-bit major
and 20-bit minor domains before conversion. Pure and actual C/PTY regressions
now retain proved health and return metadata `NO_PROOF` for that dataset.

Review also caught the initial alias location on `/s22-root-work`, whose
unchanged native mount has `MS_NODEV`. The final alias uses `/dev` instead;
the existing cwd and runtime mount restrictions remain unchanged. FIFO and
regular-file fixtures do not prove access through a `nodev` mount.
The qualified P393 generated platform source mounts `/dev` with `MS_NOSUID`
alone and requires successful `/dev/null` creation/open/read/write. Its source
receipt and built-init identity join the retained qualification; this evidence
uses the actual generated image input rather than an unbound legacy source.

Focused tests cover synthetic GPT CRC disagreement, overlapping extents,
unsupported metadata sizes, wrong LU/sector size, geometry changes and short
captures. Actual resident C over a PTY carries the binary census into the new
parser and completes DETACH. A complete negative dataset retains health; a
publication interruption rederives the same raw result without another read.
Owner tests cover read-operation capacity, no normal transfers, unique recovery
ownership and original-A recovery after uncertain protocol.

The actual ARM64 BusyBox decodes the fixed transport bytes, parses the shell,
and reads the exact primary/backup byte counts from ordinary host fixture files
through QEMU. Its mode option, existing-path refusal and removal are tested with
an unprivileged FIFO fixture. Those fixtures do not claim live block access or
GPT recovery. The prior real P393 bootstrap/P394 N/E/N raw sequences, original
P393 admission and final native tail still rederive unchanged.

Private inputs and verification are under
`workspace/private/outputs/s22plus-native-storage-census-h0-20260915-1/`.
The firmware map is under
`workspace/private/outputs/s22plus-fyg8-partition-survey-20260915-1/`.
The next device step is the prepared V3 census request: 600 seconds, one
storage-census operation, admitted P393 and deferred physical recovery.
The old task is closed; this new task needs its actual returned finite grant.
Host-only preparation reverified the five installed PC files, noninteractive
readiness and the expected USB endpoint with no tty holder. No native command
was sent. The request selects no E, normal Android exit, HUD or USB reconnect.
No A90 or S20+ command is part of this work.
