# S22+ bounded automatic Debian reboot V1

Status: **REVIEW_GATED_CAPABILITY**. H0 integration and synthetic baseline
qualification grant no device authority. This separately selected specialization
of [automatic boot V1](S22PLUS_DEBIAN_AUTOBOOT_V1.md) applies only to
`post-autoboot-p457-reboot-v1`, namespace `p458`, `debian-autoboot-v1` and V3
operation `debian-autoboot` on `SM-S906N/g0q/S906NKSS7FYG8`.

## Selected finite effect and original recovery

One fresh N, one exact original A, one attended one-operation/3600-second grant,
one ordinary Debian reboot request and one final shutdown are selected. N owns
at most two admitted Debian boots, each with the same two sequential protected
admissions and bounded writable lifetimes: early file, then installed root.
There are four writable lifetimes total, two first-gadget NCM attempts total,
and no second N transfer. All other automatic-boot restrictions remain.

The same owner and global consumption continue through first health, one
journaled reboot, second health, one journaled shutdown, physical Download,
one original-A transfer and full Android32 health. Each control appends one
authenticated terminal intent to that boot's completed runtime chain, emits
the final snapshot and invokes packaged SysV `shutdown -r now` or `-h now`.
It creates no standalone persistent shutdown marker. Uncertain transfer or
control never replays; preserve raw evidence and retain original attended A
recovery. A completed effect may be reconstructed from its original raw capture
and journal without retransmission. A transfer proved complete followed by a
health failure admits only the existing health/closure continuation.

Each actual kernel boot has an absolute 300000 ms BOOTTIME deadline covering
all its preparation, admissions and service work. The first host window is
360 seconds from successful N completion. The second is 360 seconds from the
original durable host reboot intent, clipped to the original grant. Arrival,
response and result reconstruction renew neither window. Before N, more than
240+720+600 seconds must remain for transfer, two observations and physical
return. This launch check never blocks preauthorized original-A recovery.
The predecessor's sample limits apply independently inside each fixed window.

Both boots require authenticated local 120-second service proof and two
pinned SSH health responses spanning at least 120000 ms in that same boot.
The second must have a different kernel boot identity, the same pinned SSH
key, the exact final first-boot files and installed boot count increased by one.
The existing temporary host NetworkManager UUID is inspected and rebound with
`--temporary` to the freshly verified second interface. No duplicate UUID or
persistent host connection is created. Cleanup failure does not block A.

## Sealed count and complete root admission

Seal pre-build ext4 mount count M, with 0<=M<=65531, into the candidate. No
runtime code learns or replaces M from missing files or a later clean view.
Explicit `barrier=1` and exact counts at actual RW setup boundaries are required.

| Admission or setup | Required count |
| --- | --- |
| First boot, before early RW | M |
| First early RW / second protected admission | M+1 |
| First installed RW / second boot first protected admission | M+2 |
| Second early RW / second protected admission | M+3 |
| Second installed RW | M+4 |

All four complete protected admissions retain exact UFS/LU0/GPT and partition
RO checks, clean ext4 with no RECOVER/orphan state, the fixed unprivileged
checker, installation markers/witness, the immutable archive table and full-tree
accounting. The second admission in each boot authenticates its current early
file against the same-boot RAM receipt. The first boot requires all four current
paths absent. Before any second-boot write, the first pair must authenticate
under this candidate's source/run/key/M, end in completed services plus exactly
one reboot intent, and bind a different boot. Second-boot files must be absent.
A further startup at M+4, dirty state, unexpected count, partial chain, changed
file or failed admission rejects before a new writable lifetime. The count
bounds admitted RW setups and does not prove how many physical kernel starts
or pre-commit mount attempts occurred, or that a stalled kernel is quiescent.
No raw superblock writer, counter reset, repair or replay is permitted.

Paths are exactly `var/lib/lab/s22-early-<run>-b1`,
`var/lib/lab/s22-evidence-<run>-b1`, and the corresponding `-b2` pair. All four
are root:root 0600, single-link, same-filesystem, exclusively created and bounded
by the existing early/runtime limits. Early version 4 and durable revision 7
use separate reboot HMAC domains and authenticate phase and count. The same
chain validator is used by the protected root consumer and runtime hook.
Legacy formats, consumed artifacts and their source pins keep their meaning.

Only P456's exact early/runtime pair authenticated by closed clean P457 is
added to immutable history, for fourteen rows. The old P456 shutdown producer
and its authenticated raw SSH boot imply one possible 37-byte `shutdown-start`
file. This is an optional producer-derived expectation, not P457 retrieval
proof: if present it must be a same-filesystem regular root:root 0644 single-link
file with the exact independently reviewed SHA-256. Absence is allowed; changed
content or metadata stops admission. Previously present metadata, persistence
and clean shutdown are not inferred from the producer.

The packaged `bootlogs` producer's `savelog -c 5` rotation admits only
`var/log/dmesg.0` and `var/log/dmesg.1.gz` through `var/log/dmesg.4.gz`, as optional
regular root:adm 0640 single-link same-filesystem files. The first is at most
1048576 bytes; compressed files at most 1064960 bytes including gzip overhead.
No wildcard or arbitrary history is admitted. Initial boot count is at most
99998; the second boot admits at most 99999, preserving the 100000 ceiling.
Other mutable rules and immutable archive members remain unchanged.

## Fixed pre-build baseline D0

Named profile `debian-reboot-baseline-d0-v1` may be used within the current
foreground S22+ research task after independent current capability review and
common/target adoption, with no per-read human request or physical attendance.
This read neither opens an F1 grant nor establishes recovery or full-root health.
It requires an exact closed original-A return rederived from raw evidence,
the existing S22+ target lease and no active F1 owner. Capture current exact
original-A health before and after; require the same Android boot/properties.

Use pinned ADB, shell-v2 without a fallback, the existing fixed tail-nine GPT
and Android32 statfs reads, and one additional fixed native_data read. Resolve
the existing userdata entry-40 and native_data entry-41 nodes under the exact
FYG8 controller/LU0, verify partition name/index, start, size, block size and
major/minor before and after, and join them to the same exact GPT parent.
Read only the first 4096 bytes of existing native_data with bounded separate
raw stdout/stderr capture. Check superblock UUID, geometry, exact features,
CRC32C, clean state and M; retain the immutable receipt and source snapshot.
There is no mount, node creation, RO ioctl, staged helper, write or control.
A failed read permits its fixed post-read health bracket but no automatic
baseline retry. Its new invocation must separately satisfy this profile.

The baseline is immutable candidate data, not an execution identity or full
root admission. Runtime count/state and complete root checks remain mandatory.
A missing or mismatched baseline blocks production artifact qualification.
Explicit `H0_SYNTHETIC` fixtures are permitted for host qualification, must be
labelled in all build/package records and cannot pass physical image admission.

## Qualification and proof boundaries

Independent review covers this common/target specialization, fixed baseline
reader, actual full-root C consumer, early/runtime grammar, two-boot owner,
connector continuation, network ownership and exact artifact construction.
A new device run still needs its own attended finite grant, a physical D0
baseline, current exact target/health/artifact/recovery binding and unconsumed N.

Qualification exercises real ARM64 production producers and root consumers,
two boot lifetimes, raw SSH collectors, exact saved-result rederivation,
dirty/clean error-unmount, count/file/rotation limits, uncertain controls and
second-window failure. Every declared test substitution remains explicit.
All eleven past-failure checklist IDs must be assessed; DISPLAY is inapplicable
unless display work is added. Acknowledged reboot is not clean shutdown proof;
next-boot clean protected admission establishes the clean post-reboot view.
Final filesystem persistence and final Android health remain separate facts.
No device step, recovery guarantee, new approval or activation follows from H0
success, reviewer PASS_GO or the existence of this policy.
