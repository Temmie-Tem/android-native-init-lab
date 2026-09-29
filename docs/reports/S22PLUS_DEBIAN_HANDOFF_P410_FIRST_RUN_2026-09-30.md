# S22+ P410: installed PID1 reached, basic access failed

Date: 2026-09-30 KST. Target: `SM-S906N/g0q/S906NKSS7FYG8` only.

## Result

P410 `v0.4.0-rc.10` reached the installed Debian init as actual host PID 1.
The authenticated physical transcript rederives to
**`PASS_INSTALLED_DEBIAN_PID1`**. This proves the reached init boundary, not a
working Debian service boot. No Debian NCM endpoint appeared in the fixed
180-second access window; no SSH command or fixed shutdown was sent.

About 51 seconds into that window, the same P410 candidate's **native ACM
descriptor identity returned** and remained visible. The operator also
reported continued native time/screen updates. The retained records support
a later native startup or boot, rather than successful Debian ownership.
There is no later authenticated boot ID or retained reset-cause record, so an
actual reboot and its cause remain inferences, not proved classifications.

Research stopped. Attended physical Download and one original-A transfer
restored Android. Final raw health proves rooted original Android, exact
boot/supporting partition hashes, unchanged GPT and Android32 capacity.
Terminal: **`ANDROID_CLOSED_HEALTHY`, `recovered=true`**.

The candidate and its one-operation/3600-second grant are consumed and
explicitly closed. The F1 owner is absent. There was one N transfer and one A
transfer, with no repeated handoff or SSH control. A90 and S20+ were untouched.
Native_data had a writable lifetime; healthy Android does not establish clean
ext4 or preservation of all Debian writes.

## What the physical proof establishes

Fresh rooted original-A health preceded the only Android Download intent and
fresh P410 N transfer. Native first-boot authentication and fixed health then
preceded the compound handoff intent. The protected root admission, native
worker retirement, fresh RW mount and separate post-switch RAM witness all
passed their authenticated boundaries.

The installed init's first synchronous sysinit hook produced a distinct
authenticated record. It checks the actual `/proc/1/exe` against the pinned
installed init, the root device and current kernel boot, its own hook identity
and absence of inherited native ACM/state descriptors in PID 1. The host
retained this proof before sending the unique ACM release. Its ACK and measured
ACM departure are separately retained. The complete native transcript and
effect/continuation joins were revalidated after Android recovery.

This proof precedes the hook's final UDC unbind/readback and later rcS/service
execution. Release acceptance does not itself prove every later hook step,
successful rcS, Debian USB configuration, SSH or continued init liveness.
`debian_boot_proved=true` in the retained terminal denotes the installed-init
boundary in this profile; it must not be presented as a successful complete
Debian boot. `ssh_access_proved` and `clean_shutdown_proved` are both false.

## Native screen and USB reappearance

The access observer's first 49 snapshots show the bound endpoint absent.
Snapshot 50, at +50.915 seconds relative to the access window, shows Samsung
`04e8:6861`, product `S22+ E3 ACM`, with the exact native serial derivation for
the frozen P410 candidate. That native identity persists through snapshot 174.
It is a new USB generation, first observed 51.009 seconds after the prior ACM
departure. No observed endpoint has the retained Debian NCM identity. All 174
access-window USB captures were independently revalidated.

An independent review checked the actual display producer as well as the raw
PID1 proof. The native renderer paints uptime from fresh snapshots supplied
by native PID 1 and commits the frames; it has a five-second parent-staleness
limit. The handoff stops those PID1 updates, kills/reaps all three workers and
proves no other userspace before the root transition. Retained framebuffer
contents can remain visible, but do not explain indefinitely advancing native
time digits after that retirement.

The operator's screen observation is consistent with the recorded later
native endpoint. Its exact observation interval was not machine timestamped.
The supported conclusion is: installed init was reached, basic access failed,
and native startup subsequently appears to have resumed. Neither a successful
Debian boot nor a specific watchdog, panic, init failure or reset cause is
proved. The returned native endpoint was not reopened or authenticated.

## Recovery and canonical timeline

Seconds below are measured from the original grant opening.

| Seconds | Durable event |
| ---: | --- |
| 7.862 | Fresh exact rooted Android preflight complete |
| 8.028 | One Android-to-Download intent |
| 11.842 | Android departure complete |
| 20.740 | One P410 N transfer intent |
| 22.245 | N transfer complete |
| 47.326 | Authenticated compound handoff intent |
| 50.652 | Installed PID1 proof, release ACK and ACM departure complete |
| 50.704 | Bounded NCM/SSH observation step starts |
| 231.463 | Access window ended without NCM; research stopped |
| 263.352 | Original-A recovery starts waiting for physical Download |
| 364.266 | Fresh recovery observation after a pre-transfer USB read failure |
| 365.711 | Sole original-A transfer intent |
| 367.116 | Original-A transfer complete |
| 367.129 | Initial final-health observation starts |
| 472.716 | Health-only continuation after an ADB read failure |
| 476.497 | Rooted Android/GPT/Android32 final health complete |
| 675.144 | H0 reconstruction and explicit grant closure complete |

The first recovery invocation observed a USB endpoint disappearing during
its snapshot. Its failure was preserved before any A transfer intent. Fresh
observation in the same recovery owner then bound the exact Download endpoint
and performed the single original-A transfer. No transfer was repeated.

The first final-health `03-health` read returned exit 1 with target-not-found
stderr, without timeout, overflow or producer fault. The durable transfer was
rederived before continuing only final health. The completed bracket proved
a different Android boot from preflight, exact original partitions, full GPT
and 34,357,624,832 bytes of Android32 filesystem capacity. This recovery used
physical intervention; automatic recovery was not qualified.

## Evidence and next bounded work

Private evidence base:
`workspace/private/outputs/s22plus-debian-handoff-h0-20260930-1/`.
Operation: `prepared-2/task/operation-0001/`. Execution source commit:
`ea760859a5dafaf500d0e281090f4c7a7c362dad`.

| Record | SHA-256 |
| --- | --- |
| Approved task | `cd4731b594bdffddd8581d43ae1cfe35f5f2665ec8c7e307137fc82fa30aebe4` |
| Grant | `b85fab2d823c9ba3d6d6de9d2016bed96a462803309c8e10f00fad780ff44b06` |
| Actual P410 AP | `e408becedd9e913ac6a478c0f212f8437dbcbded59e10226ec0c67ae9e3e4aeb` |
| Terminal | `26471a65ad733c3d409505372d405c2f1023240f8dffae63f80215edae223f82` |
| Closure audit | `fb102f3b2a118b34df5d8bff0b8108c14b374ed0e938bcd27586ca77998cc444` |
| Closed grant | `848e6425eaceffda91ebfa8498f9b6a7bc99c2680317a33b52c94c655bbf7410` |

H0 reconstruction verified 1,779 raw capture receipts and both streams, all
257 saved source files, the authenticated native proof, both transfers and
initial/final Android health. All 19 journal records and the terminal stayed
unchanged. The global candidate claim remains consumed. No host network
connection was created, and no new device command was used by the H0 audit.
Raw identities, USB captures, source snapshots and operator observations stay
private.

Next work is H0 analysis of the interval after init proof and before native
USB reappearance, using the retained startup, hook, kernel and transport
evidence. The reset mechanism and continued userspace ownership are unresolved.
A future device unit needs its own reviewed scope and current root admission;
the writable P410 lifetime cannot be relabelled as the prior pristine root.
No repair, reinstall or repeated P410 effect follows from this closed grant.

See the [H0 preparation](S22PLUS_DEBIAN_HANDOFF_P410_H0_2026-09-30.md) and
[binding handoff scope](../operations/S22PLUS_DEBIAN_HANDOFF_V1.md).
