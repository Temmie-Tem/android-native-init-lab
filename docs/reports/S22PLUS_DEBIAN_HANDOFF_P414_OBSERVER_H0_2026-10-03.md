# S22+ P414 startup-boundary observer H0

Scope: host-only successor preparation for `SM-S906N/g0q/S906NKSS7FYG8`.
No connected observation, device command, grant, boot-image transfer or root
repair is part of this unit. P414 names this H0 work; it is not an activated
physical candidate. The [V2 capability](../operations/S22PLUS_DEBIAN_HANDOFF_V2.md)
retains its one-operation, original-deadline and attended-recovery boundaries.

## Problem and resulting behavior

[P413 causal research](S22PLUS_P413_CAUSAL_RESEARCH_H0_2026-10-03.md) established
USB departure in the EOF episode, but not its trigger. The last authenticated
rcS-entry record preceded close, fork and startup, leaving those operations
indistinguishable in the retained prefix. A closed parent descriptor also
prevented reporting an ordinary child failure through that channel.

Fresh helpers now declare observer revision 3. The rcS hook emits a
before-close boundary, closes ACM, saves its return time, reopens and verifies
the endpoint and actual installed init, then emits a reopen boundary before
forking the original rcS. The parent keeps ACM during its bounded wait. The
child closes all descriptors from 3 upward and checks fd 3 is absent before
executing the unchanged startup script. The rc2 hook similarly owns ACM while
its ordinary child runs. PID1 and the executed services inherit neither ACM
nor the state descriptor.

Authenticated records distinguish child creation, ten-second waiting
heartbeats and the exact reaped child's raw wait status. Child creation does
not prove exec. Completion requires zero exit; existing thirteen same-boot
init/cron/sshd samples over at least 120 seconds remain necessary before
release. Both startup phases share the original 300-second deadline and a
forty-boundary consumer limit. Failure parks without a new continuation,
reconnection or replay. Killing the direct child at timeout does not establish
that all descendants stopped.

The host preserves raw capture before bounded frame receipt files. Their
CLOCK_BOOTTIME values are host receive upper bounds, not target execution
timestamps. Frame hashes and captured-prefix lengths join them to raw bytes;
buffering can give several frames the same prefix length. No sub-millisecond
comparison with host kernel printk timestamps is asserted.

Revision selection is explicit in fresh helper and image metadata and must
agree with the pinned helper result. Missing revision selects only the
historical revision-2 parser. Retained P411/P413 binaries, sources, grants,
journals and proof projections are not repinned or relabelled.

## Post-loss boot identity

The existing native D0 reader cannot be used after this failure: it needs a
completed admitted baseline, no unresolved F1 owner and the same boot with
increasing ordinals. Native AUTH currently emits identity and immediately
enters return preparation; closing the host then is not a read-only exchange.
This unit therefore adds no post-loss connection.

A future preparation-free identity receiver would need review for both native
and Debian endpoint lifetimes, preserving the original failure/recovery owner
and budgets. It could distinguish changed authenticated boot, same
authenticated boot and no authenticated identity. A timeout or re-enumeration
alone cannot establish reboot or gadget reset. That larger protocol change is
not necessary to qualify this startup observer and is not implemented here.

## Qualification

Evidence is private under
`workspace/private/outputs/s22plus-debian-handoff-p414-h0-20261003-1/`.
Synthetic run/key inputs are H0 fixtures, not physical execution bindings.

- Static ARM64 hook, witness and preparation helpers build identically in A/B
  pairs for virtual and physical bindings; the physical helper audit passes.
- All 27 focused host tests pass. These include legacy replay, ordered
  revision-3 boundaries, boot/child/status/deadline rejection, helper/image
  revision mismatch, receipt-write failure and partial-prefix preservation.
- A real C producer over PTY reaches the reopen boundary, then actual peer
  termination causes EOF and cleanup `EIO`. The owner closes its descriptor,
  retains the prefix and transmits no release or reconnect. This is a host
  hangup test, not an emulation of Samsung electrical USB behavior.
- The real ARM64 system VM boots the installed SysVinit and original rcS/rc2,
  produces all seven startup boundaries, observes init/cron/sshd for 120136 ms,
  proves pinned SSH on the same kernel boot and performs fixed shutdown.
  Post-shutdown ext4 is clean and complete `e2fsck -fn` succeeds; bytes outside
  the regular-file native_data fixture are unchanged.

The six negative ARM64 VM runs also pass:

| Injected fault | Retained evidence | Outcome |
| --- | --- | --- |
| Injected failure after close, before reopen | Only before-close boundary | No child creation or completion |
| rcS exit 23 | Raw wait status 5888 | Authenticated STOP, no completion |
| Exec failure, exit 126 | Raw wait status 32256 | Authenticated STOP, no completion |
| SIGTERM | Raw wait status 15 | Authenticated STOP, no completion |
| Child skips fd closure | Guard exits 125, raw status 32000 | No script exec; authenticated STOP |
| Child never exits | 31 boundaries, including 28 waiting heartbeats | Original 300-second timeout and parked parent |

All negatives preserve bytes outside native_data, have no runtime proof or
release, and leave SSH unavailable. The timeout uses the real original budget,
not an accelerated clock. Missing STOP after the injected post-close failure or expired deadline
is not converted into success; raw boundary prefixes remain diagnostic only.
All eight helper builds (physical plus seven virtual variants) are A/B identical.
Python compilation, local links, diff checks and repository boundary checks
pass. Nine retained P413 evidence pins remain unchanged.

Independent execution review is **PASS_GO** for this H0 capability change. It
binds the changed execution and authority interactions and independently replays
all seven authenticated RX/TX streams and every complete-frame prefix. Exact
source, artifact and review pins are retained with private qualification and
completion records. This does not activate a physical candidate.

## Claim limits and next unit

This changes the close interval and descriptor lifetime. VM success qualifies
the prospective observer arrangement; it does not establish P413's cause or
Samsung USB stability. Close-return evidence is transmitted only after reopen;
absence of that record cannot identify which step failed. The new boundary
also cannot exclude an unobserved transient USB cycle.

There is no fresh full boot image, physical activation or new device grant in
this result. A later physical candidate requires a freshly qualified complete artifact,
exact original-A health and applicable finite authority; current native_data
admission must pass at the protected boundary before any writable handoff. P413's later filesystem
cleanliness remains unknown; no repair or replay is inferred from H0 success.
