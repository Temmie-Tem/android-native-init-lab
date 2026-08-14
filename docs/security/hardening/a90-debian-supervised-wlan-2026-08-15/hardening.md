# Security Hardening Review: A90 Debian-Supervised WLAN Control Plane

## Evidence Basis

This H0 review asks whether we can replace the selected dual-supervisor steady
state with Debian PID 1 as the sole administrative owner. The source collection
is bound by SHA256
`f2f26a6afd630cba1d23e3d44fb426b90f487d243bb816ed65ae446263c4d1c8`
across 28 public artifacts at revision
`dc65c5797d820f20afcbbb13fe9f30d3c8d6c82b`.

The record is stronger than either simple conclusion. WSTA18 proves that
letting Android/vendor userspace disappear while Debian merely inherits
`wlan0` does not work. WSTA19 and the later native-uplink lineage prove that a
surviving vendor backend works. They do not prove that native PID 1 is the only
possible supervisor. Current H24 source also shows that the accumulated,
not-live-qualified backend is a multi-service compatibility environment, not a
single daemon.

No private run artifact was read and no result was reproduced. See
[`context.md`](context.md) for the exact inventory and observed/inferred split.

## Constraints

- A90 only; H24 remains installed and its D1 remains consumed and unreplayable.
- H0 only. This review creates no identity, artifact, qualification, D0, D1,
  F1, candidate, handoff, reboot, flash, or device authority.
- Boot-only payload, read-only UFS, exact rollback/recovery, durable no-replay,
  SD-free evidence, and cross-target isolation remain non-negotiable.
- A rootfs/key/config change alone is insufficient; a live vendor WLAN backend
  must be preserved or relaunched.
- Latency, memory, power, wakeup, and recovery deltas are unmeasured.

## Opportunity Portfolio

| Opportunity | Evidence | Options | Recommendation | Proposal |
| --- | --- | --- | --- | --- |
| Make WLAN control-plane supervision single-owner without losing WCNSS/WMI | WSTA14/18 failure, WSTA19/40/42/43 success, H24 service-tree source, `/proc` incident | Reduced native baseline; clean prelaunch and adoption; clean Debian relaunch | Keep the reduced native baseline for any near-term candidate; run the clean-relaunch option as a separate H0 feasibility program and promote it only if its minimum service closure is smaller and independently containable | [Detailed proposal](proposals/debian-supervised-wlan.md) |

## Recommendation Summary

I do not recommend rewriting the current selected contract around Debian
ownership yet. We know that the current native-owned path can keep the radio
alive, and we do not yet know whether the service-object-visible H24 set can be
reduced or cold-restarted after Debian becomes PID 1.

I do recommend treating clean Debian supervision as the next architectural
research question. It best matches the single-responsibility goal: Debian PID 1
would own lifecycle, network policy, evidence, and application service, while a
restricted vendor capsule acts as a hardware backend. That is materially
different from giving an SSH-visible Debian root the Android control plane. The
remote workload must remain a separate non-root sandbox.

If static closure and ablation show that the capsule needs the whole Android
Binder/property/peripheral-manager environment, the current native supervisor
is the more honest and smaller boundary. If a finite clean-exec subset can
recreate WCNSS/WMI and then allow Debian to own station/IP policy, the clean
relaunch design becomes preferable and can supersede the current architecture
through a separately reviewed contract change.

## Next Decisions

1. Decide whether “single owner” means one steady-state PID 1 and policy owner,
   while accepting a multi-process vendor backend. A literal single-process TCB
   is not supported by the hardware record.
2. Authorize only an H0 dependency/ablation unit for the vendor backend. Do not
   allocate a candidate identity.
3. Freeze benchmark budgets before any future device proof: WLAN readiness,
   authenticated SSH readiness, steady RSS/PSS, wakeups, recovery latency, and
   veth/direct data-plane cost.
4. Revisit the target contract only after the clean-relaunch gate produces a
   complete dependency manifest, security envelope, and independent review.
