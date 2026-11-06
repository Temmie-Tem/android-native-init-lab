# S22+ ML030 mainline UFS link V1

Status: **REVIEW_GATED_CAPABILITY**

On 2026-11-06 the operator adopted the exact
[ML030 scope proposal](../plans/S22PLUS_ML030_LINK_ONLY_SCOPE_2026-11-05.md),
SHA-256 `614afaf025a6c7f7f322f2d10a1e19d1d7e5db5dc4fa5e6ba4029cf2620ce4e8`.
The complete positive delegation is incorporated into common boundary 3 in
[the contract details](DEVICE_ACTION_CONTRACT_DETAILS.md#permanent-device-safety-boundaries).
This policy and the [S22+ target](targets/S22PLUS_FYG8_TARGET_CONTRACT.md#ml030-mainline-ufs-link-v1)
specialize that single experiment on SM-S906N / g0q / S906NKSS7FYG8.

## Exact bounded unit

The unit uses one new boot-only N from healthy original-A Android. Its
qualified four-package Debian SysVinit RAM root runs one direct witness
child. The child loads the fixed g0q module once, after the authenticated
same-boot five-minute witness and the separate permit. The shared RPMh
transport, interconnect observation, clocks, regulators, reset pulse, PHY
initialization and six local UniPro commands must match the common scope.
At most one newly issued DME_LINK_STARTUP may follow. The terminal hardware
claim requires its fresh completion, result zero and device-present
transition. The accepted finite task has one operation in 1800 seconds,
with physical attendance and usable Download recovery throughout.

The reviewed H0 candidate is pinned below. Its full provenance, package,
loader, VM evidence and kernel/module closure remain required. A changed
artifact requires fresh qualification and applicable independent review.
The scope admits only one ML030 candidate. A consumed or uncertain dispatch
ends that candidate's authority. A successor requires its own scope.

| Artifact | SHA-256 |
| --- | --- |
| Mainline Image | `19fc260fc880731167d3612804e34a0ea64c48efb1a46bdf7aee803d35a2bc3c` |
| Fixed g0q module | `7859073e9abfef8cb93202683046bec2878b3210c4703fc36eb6a1474a6615f8` |
| Physical RAM archive | `3c829b6137b10745ad1b0a3d16c227d498f96dbf0ca4c1495058033244a04631` |
| uniLoader | `6be55da7a4d53f18ad6c9129f66bcf24843117662a16b54dcfc03f5ae0b979ed` |
| Single-member boot-only AP | `44ea04f4f7a9aaa09e3ad4e86e5162c08eb6aaba6d4bf5b94632feb95d9d7aba` |

The selected archive has schema
`s22plus-mainline-debian-ufs-link-ram-v1`. The current RAM variants and their
120-second control windows remain separately governed by
[mainline RAM V1](S22PLUS_MAINLINE_RAM_V1.md). A live implementation must
explicitly select and validate the ML030 schema, artifact closure and this
policy before it can reach any effect. The existing RAM validator rejects
this archive. A successful H0 build or this policy's adoption supplies no
live owner, transfer intent or returned grant.

## Observation, dispatch and return

The first authenticated response must arrive within 120 seconds of the
original N launch. The host seals complete bounded raw bytes before
interpreting them. On the same socket it waits at least 300 seconds after
sealing that response before generating and sending the new challenge.
The guest checks at least 300 seconds of additional uptime, the same
boot, kernel, DT, PID 1 and observer, and zero block devices.
The original launch plus 540 seconds and the finite grant bound every late
host request. Guest observation, module dispatch and EOF/restart remain
within its absolute 540-second boot-time ceiling. The module has its own
15-second absolute deadline for new submissions and command issue.

The source-bound owner must durably consume the one permit before sending
it. The intent binds the operation, candidate, both witnesses and nonces,
boot, endpoint, original deadlines, target and grant. The witness verifies
the fixed module file on the descriptor passed to finit_module. The module
retains the request/completion records and reached hardware state until the attended
return. Ambiguous posted writes retain their slot. A complete authenticated
result preserves the syscall errno and the bounded status prefix even when
the status read fails.

Normal return requires a successfully verified link result, complete power
command settlement and released USB reference. The one late Download
control is authenticated on the original socket and binds the SHA-256 of
that entire signed result. The owner must durably record its exact control
before sending it and check the current original grant at dispatch.
The guest uses the fixed reboot-mode binding and exactly one
`restart2("download")` after the authenticated command and the required EOF.
The final clock check remains immediately before the syscall.

The fixed SDAM reboot reason, existing SCM NODUMP shutdown and ordinary
cold-default PSCI reset retain the exact qualified effects described in the
[normal Download policy](S22PLUS_MAINLINE_RAM_V1.md#optional-normal-download-from-packaged-debian-ram).
The host must observe the exact Download ticket before original A. The
normal arrival window is at most 600 seconds from its durable Download
intent, further limited by the original grant. All ordinary and recovery
paths share the same one-shot N and A transfer history.

An incomplete or uncertain witness, permit, module result or return does
not permit a reconnect, repeated control or repeated transfer. The original
owner follows its durable journal and attended physical Download/original-A
recovery where available. Fresh final-health observation may follow a
failed read under the existing reviewed health-only continuation. It cannot
repeat a completed A transfer. Closure requires exact original-A rooted
Android health and settlement of the task-owned network profile.

## Implementation and activation

The explicit `ufs_link` image branch in
`s22plus_mainline_profile_v1.py` selects
`s22plus_mainline_ufs_image_v1.py`. Its fixed artifact admission binds
the qualified candidate above. The existing `mainline-download` Session
action calls `s22plus_mainline_ufs_access_v1.py` for that branch. It records
one Session effect-intent for the bounded compound operation before GO.
The conditional Download records its separate no-clobber return intent
and unique `ml030-return-intent` journal stage under that original intent.
The current Session check and original deadline remain required immediately
before each send. A second same-step Session intent remains forbidden.
The source-bound capability review is
`workspace/public/src/device-action/bindings/s22plus_mainline_ufs_link_v1_review.json`.
It must be PASS_GO over the current reachable source closure before use.

The execution implementation must reuse the existing Process-v2 target,
transport, lease, consumed-candidate and original-A recovery boundaries.
Qualification must exercise the real selected producer, consumer and
failure paths, including partial results and a final result followed by a
failed normal return. Link completion, Download arrival, A transfer and
final health must remain independently reportable facts.

One independent review must cover the actual reachable owner and recovery
closure together with the common and target adoption. It may reuse the
retained H0 guest/transport review while its named hashes are unchanged.
Only that reviewed implementation with fresh target/host/rollback checks,
exact artifact qualification, a returned one-operation approval and current
attendance may execute. Existing and consumed approvals, source bindings
and journals retain their identities.

The current adopted scope permits no media-backed filesystem activity,
SCSI or media command, fDeviceInit, LU discovery, partition access, ICE/key
operation, general shell, persistent installation or unattended execution.
The generic UFS host/PHY/ICE drivers and their SCSI discovery path stay
disabled for the UFS device. The kernel's common SCSI library may remain
compiled into the retained baseline. The exact late module is the sole
new UFS path and registers no SCSI host or logical unit.

The five-minute witness, finite windows and slot-retention conditions apply
to this one candidate. They prevent premature dispatch, late submissions
and replay after uncertain completion. Their scope ends with this candidate's
closure or consumption. A changed hazard, recovery path or successor scope
requires review under the common rules.
