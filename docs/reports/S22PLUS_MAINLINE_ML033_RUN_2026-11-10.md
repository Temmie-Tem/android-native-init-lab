# ML033: authenticated USB and five-minute survival, early UFS refusal

ML033 closed **`NO_PROOF / ANDROID_CLOSED_HEALTHY`**. The authenticated first
response arrived within 120 seconds, and the second witness proved the same
boot after more than five minutes. The permitted module then reported
`EBUSY(16)` at stage 0, before any local UniPro or link command. Physical
Download, one original-A transfer and a complete fresh Android health bracket
closed the run. N and A each transferred once; no F1 owner remains.

The execution source was commit `1ca9243d83`. The operator returned the exact
one-operation 1800-second approval with current attendance and usable Download
recovery. One foreground preapproval D0 invocation passed. The exact candidate,
scope and source-bound reviews are retained in the
[H0 comparison and preparation](S22PLUS_MAINLINE_ML033_USB_COMPARISON_H0_2026-11-10.md)
and [ML033 policy](../operations/S22PLUS_MAINLINE_UFS_LINK_TIMED_ATTACH_V1.md).

## First USB and same-boot witness

The existing caller issued one cue at N+37.182 seconds with 82.818 seconds
remaining. Its original guards passed, and the instruction was displayed
immediately. This was later than the approximate +25-second planning aim;
no admission condition or deadline changed. The operator reported one completed
reconnect, recorded at +83.291 seconds. That record is not a measured physical
contact time and was later than the approximate +55-second diagnostic aim.

After 51 absent censuses, the next sealed census selected the exact candidate
at +72.568 seconds. The base frame was sealed at +74.463 seconds and rederived
from raw bytes: packaged SysVinit as PID 1, its direct observer, exact kernel/DT,
one CPU, zero block devices and the required timer/namespace fields. The
reported guest uptime was 49.059 seconds. Base proof preceded the operator's
completion-record publication. The resolved cue was closed before later control.

The second witness was sealed at +374.963 seconds. The host interval from
base sealing to the fresh challenge was 300.422 seconds; guest uptime advanced
300.564 seconds to 349.623 seconds. The same socket, boot, kernel, DT, PID1 and
observer, and zero block devices, passed the actual witness validator. This
establishes the bounded five-minute result on hardware, not indefinite endurance.

## UFS stage and source-localized refusal

One separately authenticated permit was sent at +377.360 seconds. The complete
authenticated result followed at +377.391 seconds:

| Field | Result |
| --- | --- |
| Module report | operation errno 16 (`EBUSY`), stage 0 |
| Fixed RPMh records, claims, triggers, acknowledgments and reclaims | All 0 |
| USB coverage / release flags | Both false |
| Local UniPro commands | 0 |
| DME_LINK_STARTUP issued | false |
| Normal-return eligibility | false |

This is an operation report from the loaded module, not a module-load errno.
The retained module source and exact transport input/output hashes were checked
before locating the refusal. In that source, successful `g0q_rpmh_begin()` is
followed by `g0q_usb_cover()` before overlay application or the UFS `run()`
function. Stage 0, operation errno 16 and a false USB-coverage flag locate this
result at that initial coverage admission. The existing report cannot distinguish
device-lock availability, driver/private-data identity, runtime-PM active-reference
availability, or ICC/BCM USB-vote coverage. None is claimed as the specific cause.
No link attempt, UFS media access or SCSI result was established.

The host stopped new normal control at +378.760 seconds. No native Download
control packet or intent was created. The empty ACK capture retained a
`SessionError` and `timed_out=true`: the capture finalizer still compared with
the original 120-second first-phase deadline because the late callback raised
before returning its replacement deadline. This flag is not evidence that a
sent Download command timed out. The connection record independently confirms
that no such control was sent and that the socket was closed.

## Recovery and final health

The already-completed cable cue was resolved before the separate physical
Download request. The operator reported physical Download completion. The
original stopped owner reidentified the Download target and transferred only
its original A, once. During the first return-health bracket, the root/digest
read returned code 1 with empty stdout and an ADB target-not-found diagnostic.
That failed raw capture and prefix remain preserved.

Raw transfer evidence proved A complete. The existing health-only continuation
then completed all seven fresh health reads without another transfer or control.
Final rooted original-A health and `ANDROID_CLOSED_HEALTHY` were rederived.
The task-owned network profile was deleted and its absence checked; the later
cleanup observed it already absent. No unresolved F1 owner remains.

| Event | Seconds from the host N-launch anchor |
| --- | ---: |
| N transfer complete | 2.266 |
| One replug cue | 37.182 |
| First present candidate census | 72.568 |
| Authenticated base sealed | 74.463 |
| Operator completion resolved | 83.291 |
| Second witness sealed | 374.963 |
| One module permit sent | 377.360 |
| Authenticated stage-0 refusal | 377.391 |
| Normal path stopped | 378.760 |
| Physical Download confirmation recorded | 466.755 |
| Original-A transfer intent | 470.658 |
| Original-A transfer complete | 472.048 |
| Final health and durable close | 551.604 |

The canonical timeline uses the grant origin and is retained privately. Its
combined `candidate_boot_ready` step remains `NOT_PROVED` because the full
late operation did not finish normally. That does not erase the independently
authenticated base and same-boot witness facts.

## Raw audit and interpretation

Private run evidence is under
`workspace/private/outputs/s22plus-ml033-policy-adoption-h0-20261110-1/`.
`run-audit-2.json` reopens all 544 indexed raw captures plus the two separately
sealed cue captures. Acquisition, process creation and sockets were blocked.
It rederives transfers, base, witness, module report, absence/presence censuses,
cue timing, final health, profile removal and owner closure. The initial H0
audit expected the base exception name `ValueError`; the actual producer uses
its `SessionError` subclass. The failed checker and log were retained, and the
corrected checker joins the exact subtype to the original stopped journal.
No production assertion or device action was changed or repeated.

The five diagnostic/non-success captures are accounted for: one empty ACK
finalizer after the hardware stop, three expected owned-profile absence
results, and the single failed first return-health read. Old consumed records
and unrelated work remain byte-identical.

Compared with ML028 and ML030–ML032, ML033 demonstrates that the retained
ML030-family functional stack can deliver its authenticated first response and
survive the required interval on this device. Combined with ML032's retained
out-of-window enumeration, this removes the basis for treating all earlier
absent windows as deterministic pre-USB boot failure. It does not measure the
earlier cable actions, prove replug necessity or identify the Type-C mechanism.
The newly reached frontier is the initial USB-coverage admission for UFS.
ML033 is consumed and cannot replay; a future experiment needs its own scope.
A90, S20+ and unrelated boot-journal work were untouched.
