# Proposed S22+ ML030 mainline UFS link scope

**Draft for operator adoption.** The current common contract delegates UFS
initialization to the eight stock drivers on the exact FYG8 vendor V3 profile.
The existing mainline RAM target keeps its UFS host and PHY disabled. The
proposed change is a separate positive delegation for one mainline experiment
on SM-S906N / g0q / S906NKSS7FYG8.
[Common UFS clause](../operations/DEVICE_ACTION_CONTRACT_DETAILS.md#permanent-device-safety-boundaries)
and [current mainline runtime](../operations/S22PLUS_MAINLINE_RAM_V1.md#runtime-and-observation).

## Proposed text for incorporation in common boundary 3

The S22+ target may adopt one distinct attended F1 mainline link experiment.
One boot-only N may boot the qualified four-package Debian RAM root and its
fixed witness. The host must first authenticate its original response within
120 seconds of N launch. On the same connection it may issue one fresh
challenge at least 300 seconds after sealing that response. The second
authenticated witness must report the same boot, kernel, DT, PID 1, observer
and zero block devices with at least 300 seconds of additional guest uptime.
Only a separately authenticated one-shot permit after verification of that
witness may dispatch the fixed module. The late host window is bounded by
540 seconds from the original launch and by the existing finite grant. The
guest enforces its own absolute boot-time ceiling of 540 seconds.

The module may use the held active g0q USB path solely to confirm existing
SH1/CN0 fabric votes. It may acquire the fixed UFS GDSC, clocks, host reset,
shared L5 reference and separate PM8350 L6, L7, L9 and S12 votes. It may
pulse only the already-output UFS device reset on GPIO 210, program the
qualified v4 Waipio PHY and symbol clocks, enable HCE and issue the six
fixed local UniPro commands and at most one DME_LINK_STARTUP. The 15-second
absolute kernel budget covers new resource submission and command issue.
A late completion can settle a previously triggered request. An uncertain
slot retains its request storage and cannot be replayed or reused. The
generic UFS, PHY, ICE and SCSI drivers stay disabled. Media commands,
fDeviceInit, LU discovery, partition access, media-backed filesystem activity and key
operations are excluded. No use of another target or another UFS profile
is delegated.

Activation requires a reviewed target adoption, the exact qualified image,
a source-bound owner with durable pre-dispatch intentions, a fresh finite
single-operation approval, attendance, available Download recovery and an
exact original-A rollback. Evidence distinguishes a verified five-minute
witness, one issued link command, and a fresh successful completion with the
device-present transition. A received request or an absent USB endpoint
cannot establish a physical link. Loss of the observer, ambiguous slot or
transfer, or an unresolved module outcome stops new commands. The original
owner may recover using physical Download and original A at most once in
its existing recovery state. On a fully verified normal path ML030 may use
one separately adopted late Download transaction on the original connection.
It binds the authenticated final link result, settled power commands, released
USB reference, candidate and boot before its single fixed restart2("download").
Host control and guest EOF/restart must fit both original 540-second ceilings
and the unextended grant. The same fixed reboot-mode binding, Download ticket
and arrival window then admit original A. Normal and physical paths share
one original-A consumption history. Closure requires
final rooted Android health and settlement of the task-owned network profile.

## Adoption and retirement

The proposal requires a separate review of the common text, the root digest,
the target routing and the actual runner. It does not amend those files or
authorize a connected read or transfer. Its only proposed scope is ML030's
new, exact, single-operation candidate. A consumed or uncertain dispatch
is terminal for that candidate. A successor requires its own scope. Future
media access or lasting installation would require separate policy and review.
[Current H0 findings](../reports/S22PLUS_MAINLINE_ML030_DWELL_LINK_H0_2026-11-05.md).
