# P413 first run: installed PID1 and rcS entry before observer EOF

Date: 2026-10-03 KST. Target: only `SM-S906N/g0q/S906NKSS7FYG8`.
Candidate: P413 `v0.4.0-rc.13`, archive-free [handoff V2](../operations/S22PLUS_DEBIAN_HANDOFF_V2.md).

## Result

P413 proved installed Debian init as actual host PID1 in the original kernel
boot, accepted the fixed service-start continuation and emitted authenticated
rcS entry. The host observation then ended with `EOFError`. It obtained no
rcS completion, runlevel completion or 120-second service-runtime proof.

Scientific result: **PASS_INSTALLED_DEBIAN_PID1; service runtime, NCM and SSH
NO_PROOF**. No USB release or SSH/shutdown request was sent. The installed-init
proof survives this later observation failure; it is not a usable Debian
service-boot result.

Original Android was restored and fully checked. Terminal:
**ANDROID_CLOSED_HEALTHY**, `recovered=true`. Exactly one N and one A were
transferred. The one-operation/3600-second grant and candidate are consumed
and closed; the F1 owner is absent. A90 and S20+ received no command or transfer.

## Authenticated native and Debian evidence

Fresh admission observed `clean=1 state=1 recover=0 orphan=0`, a successful
protected checker, all installation markers and all **8,969 expected entries**
with zero missing/content/metadata findings. This independently re-established
the condition repaired by P412; its prior proof was not substituted for the
current check.

The native workers settled, the protected root was ordinarily unmounted and
native_data activated RW. The RAM witness proved PID1 on writable ext4,
partition RO cleared, seven mounts, zero other userspace and only descriptors
0–3. The host then retained the installed-init proof: PID1, same kernel boot,
exact init/hook identities, and zero inherited ACM or state descriptors.
The fixed START request was sent once and acknowledged.

Exactly one Debian progress record followed: stage 1, sample 0, elapsed 0 ms,
services 0. The strict protocol defines this as **rcS entry**, not successful
rcS completion or service liveness. No later progress or authenticated STOP
record exists. There was no release intent, release ACK or release-departure
proof, and the NCM/SSH/shutdown phases were not reached by the host.

The raw native capture retains `producer_error_type=EOFError`, without timeout
or output overflow. Its valid authenticated prefix and fixed transmitted
continuations rederive. The 2,254-byte authenticated preparation log is retained
privately with its digest. No new command was sent to obtain that log.

EOF identifies where the host lost observation. It does not establish whether
rcS failed, continued without observation, the USB endpoint reset, or the device
rebooted. No subsequent authenticated native boot identity or reset-cause
evidence was acquired. No causal claim is made from screen appearance or
USB enumeration alone.

## Recovery

The runner stopped research and retained the original A recovery owner.
The operator was asked to use the existing physical Download procedure; the
host sent no new native Download or handoff command after the uncertain session.

The first recovery preparation failed when a USB node disappeared during
measured endpoint enumeration. This occurred before any A launch receipt,
transfer capture or effect intent. Its failure was preserved and the same
authorized recovery resumed through a fresh bounded endpoint observation.
The exact Download endpoint was subsequently verified and A transferred once.
The records establish Download arrival, not the mechanism that caused it.

The first Android health acquisition then failed with ADB `device not found`
after A was already proved complete. Only remaining health reads continued;
there was no second transfer. Final root, original boot/supporting partition
hashes, a distinct Android boot, full matching Android32 GPT, native_data
presence and **34,357,624,832-byte** reported capacity passed.

No Debian shutdown was requested. Native_data cleanliness and durability after
the writable lifetime and forced return remain **unproved**. Healthy Android
does not prove clean ext4 or preserve the pre-RW clean-state result. The consumed
grant permits no further filesystem recovery, replay or installation.

## Canonical timeline

Elapsed seconds are from the original grant. Its deadline and operation budget
were not renewed.

| Seconds | Durable event |
| ---: | --- |
| 6.694 | Fresh rooted original-A preflight completed |
| 6.904 / 10.542 | Android Download intent / completion |
| 20.247 / 21.801 | Sole N transfer intent / completion |
| 35.092 | Compound handoff intent after authenticated native health |
| 60.588 | Observation stopped with EOF after installed PID1, START and rcS entry |
| 137.890 | Original-A recovery preparation started; endpoint read failed before dispatch |
| 282.024 | Bounded original-A recovery continuation started |
| 283.727 / 285.136 | Sole A transfer intent / completion |
| 285.151 | First final-health acquisition started; a later ADB read failed |
| 359.804 / 363.698 | Health-only continuation / full Android health completion |
| 530.935 | H0 evidence audit and finite-grant closure |

## Retained evidence and validation

Private run root:
`workspace/private/outputs/s22plus-debian-handoff-p413-live-20261003-1/`.
The operation is under `connected-preparation-1/task/operation-0001/`.
Execution source commit: `6ac642a5191af95b32e386540a8698d4fddf8dad`.

The H0 closure audit verified both streams of **1,759 operation captures**,
all **264 frozen source files**, original and final Android health, exact N/A
transfers, permanent consumed claim and the authenticated partial result.
With command acquisition blocked, `Session.repair_close` reproduced the
terminal while all **17 journal rows** and terminal bytes stayed unchanged.
The separate 19-capture connected preparation and both recovery failure logs
remain private. No execution code, approval or historical review was changed
during the run or its closure.

| Record | SHA-256 |
| --- | --- |
| Task | `cb86591156b7004700cafb49748cf77e10f1f743ddb3dc97f147dce0fb5d725a` |
| Frozen source closure | `014b17f1fe96a622e6811fdafd1fa28934f315115d7c71e5c3d3e25cf4f8ab34` |
| Authenticated partial result | `f7af7008c443c848b998bde11253ea7b4701c2a647b6d8ffdc21347e83626c79` |
| Authenticated preparation log | `e2cdc500a6c99860186a54a2fc467f0c11da0c5164b92f90ab8b5c5c82e6cd92` |
| Terminal | `4fe9c4303c7526d40416512df4644f35a5297699920d1e1cb14092d2ab091b9a` |
| Closure audit | `7fda7a486ee30d5416bf0fdf830f24739ba634eb225061f17fd6fcf9ebe73959` |
| Closed grant/task | `96cb8c96f820d5a8672d523cfaa566884e5405f8b98c4f037c37446dae4cee14` |

## Next bounded work

Use H0 inspection of the retained stream, host tty/EOF semantics and actual
installed rcS ordering to narrow the missing observation. Preserve this
consumed prefix and distinguish an observation defect from unproved device
failure. Any fresh candidate retains current clean-root admission, reviewed
changes where needed, its own finite scope and original-A recovery. P413's
failure is not permission to reconnect, release USB, retry the handoff or
repair native_data.
