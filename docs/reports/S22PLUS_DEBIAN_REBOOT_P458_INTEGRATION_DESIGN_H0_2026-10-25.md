# P458: physical-runtime reboot integration design

## Bounded task and completion criterion

The operator selected integration of the remaining root checks, second-boot
owner and log rotation rules, including the past-failure checklist and an
independent review. This design precedes implementation. Complete the actual
production paths, strict consumers, representative ARM64 positive/failure
evidence, artifact qualification and source-bound independent review. No device
effect, new live grant or server action is part of this H0 integration task.
A90, S20+ and the 46 pre-existing changed files remain outside scope.

Retain the [P456 minimal architecture](S22PLUS_DEBIAN_MINIMAL_P456_RUN_2026-10-24.md)
and the [P458 feasibility evidence](S22PLUS_DEBIAN_REBOOT_P458_H0_2026-10-24.md).
The separate prototype is not the production runtime or its root validator.
Use the actual automatic package, root comparison/checker, supervised early
writer, PID1 transition, SysV hooks, SSH collector and V3 owner.

## First-phase baseline and policy scope

The prototype learned its initial mount count when both first-phase files were
absent. That does not bound an earlier clean error-unmount before file creation.
For production, seal the initial ext4 mount count M into the candidate and
require M<=65531. Never replace it using a later clean view or record absence.

P457 retained state/RECOVER/orphan, not M. Existing Android preparation does
not authorize this native_data superblock read, and its image-first API would
create a dependency cycle if used to construct the image's baseline. Add one
named, reviewed pre-build D0 metadata entry using retained exact target/GPT/
filesystem/closed-return binding, the existing target lease, no active F1 owner,
shell-v2 and original-A health brackets. It reads one fixed 4096-byte block
from the existing native_data entry-41 node after matching controller/LU0,
partition identity/start/size and major/minor. Retain raw bytes separately from
the existing bounded GPT stream. Check identity/features/checksum/clean state
and unchanged returned Android boot. No mount, RO ioctl, node creation, staged
helper, repair, write or control action belongs to this reader.

Its immutable result is candidate data. A later exact runtime comparison must
still pass; the read is not full-root admission or authority. A missing or stale
baseline blocks production qualification. H0 fixtures may supply explicitly
labelled synthetic baselines but cannot become physical readiness records.

The common-incorporated automatic policy and target currently admit one boot's
two writable lifetimes. Define a separately selected reboot specialization:
one fresh N, at most two admitted Debian boots, four named writable lifetimes,
one ordinary reboot request, one final shutdown, and one attended original-A
return. The original one-operation/3600-second grant remains finite. Existing
selections, consumed grants, journals and artifact pins keep their meaning.

## Runtime and root admission

Use a single reviewed runtime with two explicit phases and four exact paths:
early and runtime files for boot one and boot two. Generate all names/rules from
one declaration. Keep the current boot/run/source authentication and same-boot
early-file/RAM-copy comparison. Extend the existing early and durable wire
formats only for the selected reboot variant, binding phase and sealed count;
legacy formats retain their current interpretation.

| Boundary | Required count and state |
| --- | --- |
| First boot before early RW | Clean, M, all four current files absent |
| First early RW setup / second admission | M+1; complete clean checker/root admission again before installed RW |
| First installed RW setup | M+2 |
| Second boot before early RW | Clean, M+2; authenticated first pair ending in completion and reboot intent; second pair absent |
| Second early RW setup / second admission | M+3; exact current early receipt plus unchanged first pair |
| Second installed RW setup | M+4 |
| Any further startup or inconsistent count | Reject before a new RW lifetime |

Check at the actual clear/mount boundaries and after completed RW setup, with
explicit `barrier=1`. Do not use a raw superblock writer or reset the counter.
Dirty filesystems, partial/wrong records, extra files, metadata/hash mismatch,
overflow or unexpected remount increments stop the selected path. The bound
concerns admitted writable work, not the number of physical kernel starts or
proof that a stalled kernel is quiescent.

Retain both full protected admissions per boot: exact UFS/LU0/GPT, partition RO,
clean ext4, fixed protected checker, markers/witness, immutable archive table
and full-tree accounting. Add P456's two exact files from closed P457 as immutable
history. Validate the first current pair dynamically before boot two; do not
admit it as arbitrary mutable history. Reuse the actual authenticated chain
validator for service completion and the single reboot tail.

The retained `bootlogs` producer uses `savelog -c 5`. Declare only dmesg.0 and
dmesg.1.gz through dmesg.4.gz with bounded exact metadata/size rules. The two
names observed in the prototype are insufficient to infer the physical initial
rotation depth. Account for two boot-count increments without raising the
existing 100000 ceiling. Other immutable files and existing mutable limits stay
unchanged. No package, cron or installed-script mutation is selected.

## Actual host owner and control

Keep one owner through first health, reboot, second health, shutdown and Android
return. First observation is still bounded from N completion. Second observation
has its own fixed 360-second deadline starting at the durable reboot intent,
clipped to the original grant; neither a response nor USB arrival renews it.
Each actual kernel boot has its own absolute 300000 ms BOOTTIME deadline.

Give the two health/evidence results distinct fixed folders and expected phase/
boot identities. Current hardcoded first-health consumers must be parameterized
or explicitly specialized, not reused unchanged for a new step name. Require
different authenticated boots, the same pinned SSH key, exact final first-boot
file equality and the normal 120-second service/SSH proof in each boot.

The first fixed reboot command appends its authenticated terminal intent once,
publishes the final snapshot and invokes packaged SysV shutdown/reboot. The host
retains its intent before transmission. An uncertain control is never resent;
preserve raw evidence and use the existing preauthorized original-A recovery.
The final shutdown has a separate one-shot intent. A reboot message or masked
`umountroot` status is not clean-filesystem proof; the next protected admission
supplies that fact. Final shutdown and Android health retain separate claims.

NCM is attempted once in each boot. The second endpoint may have a different
host interface. Reuse/rebind only the exactly owned NetworkManager connection
with fresh endpoint checks; do not create a duplicate UUID or infer interface
identity from gadget descriptors. Retain original-A recovery even if host
network cleanup or reporting fails. The approved connector must route the
selected owner and its existing recovery continuations correctly.

## Validation and independent review

Reuse unchanged P458 component evidence as background only. Exercise the actual
generated package and full-root consumer with two real boots, all count/file
boundaries, dirty/clean error-unmount, record corruption, log metadata/size and
boot-count limits, baseline mismatch, uncertain command and second-window
failure. Verify actual producer-to-collector-to-saved-result paths and recovery
from durable journals without another effect. Cross-compile touched C and
inspect it; compile touched Python and run focused behavioral tests.

Review all eleven [past-failure checklist IDs](../operations/S22PLUS_FYG8_PAST_FAILURE_CHECKLIST.md),
marking DISPLAY inapplicable unless scope changes. Independent review covers
the changed reachable runtime/owner, baseline reader, wire contracts, higher-
precedence specialization, artifacts and failure consumers. Review qualifies
the capability only; physical use still requires a current baseline, exact
artifact/target/health/recovery binding and its own attended finite grant.
