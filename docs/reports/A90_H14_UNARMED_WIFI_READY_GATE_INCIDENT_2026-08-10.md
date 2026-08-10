# A90 H14 unarmed Wi-Fi readiness-gate incident

Date: 2026-08-10
Target: Samsung Galaxy A90 5G only
Classification: F1 candidate boot incident before UFS handoff

## Incident

The attended H14 F1 transaction transferred and wrote the exact boot-only
candidate once. Boot readback matched candidate SHA256
`4245ec2b56c314727138d84ad47de85a74f769277b5e3003057213b85c478312`,
but the candidate never reached its expected resident verifier. The durable
transaction parked recovery instead of replaying the candidate.

The exact V2321 rollback was then written once through the reviewed native
recovery continuation. Readback and final health proved V2321 `0.9.285`, build
`v2321-usb-clean-identity-rodata`, self-test `11/1/0`, released guard, and
`BASELINE_HEALTHY`. The transaction closed
`FAILED_CANDIDATE_RECOVERY_ROLLBACK_COMPLETE`. Candidate replay, rootfs
payload, SD staging, and userdata writes were all zero. S22+ received no
command.

## Cause

The candidate log proved that the persistent Wi-Fi helper was spawned during
the unarmed first boot. Native PID 1 then waited synchronously for at most 20
seconds for the helper's final readiness file. The helper had started its 13
required children and opened the service gate, but had not yet published the
final ready record when the fixed deadline expired. Native PID 1 returned
`-ETIMEDOUT`, terminated the helper, and entered native fallback.

This gate ran before the durable automatic-handoff state was consulted. An
unarmed resident-install boot therefore paid an unnecessary Wi-Fi readiness
gate and could fail even though it was required to stay native. No UFS mount or
UFS handoff was attempted; UFS speed and capacity were not causal.

## Containment and correction

- H14 is consumed and never eligible for candidate replay.
- H15 uses a fresh version/build, Wi-Fi label, and enable/latch namespace.
- Direct boot inspects the exact durable handoff state before Wi-Fi or NCM
  preparation. Unarmed and latched boots stay native without starting either.
- An armed boot starts the reviewed private-mount/shared-network Wi-Fi helper,
  requires its process to be alive, and continues to the UFS handoff without a
  fixed pre-switch-root readiness delay.
- The helper may publish its redacted status, resolver, and companion health
  asynchronously through the existing read-only Debian bind.
- Final D1 PASS still requires same-intent helper readiness and health. Missing,
  late, or negative proof remains no-proof or refuted and permits no arm,
  reboot, or handoff replay.
- The H15 F1/D1 runners retain one boot-only candidate attempt, exact V2321
  rollback, exact A90 binding, fresh attended approvals, and zero userdata
  writes, rootfs payloads, and SD staging.

## Safety judgment

Exact V2321 health and the physical Download/TWRP recovery path are restored.
The incident was a candidate boot regression, not a storage failure, and the
durable journal proves that the uncertain candidate was not replayed. H15
changes automatic-dispatch timing and therefore requires a fresh independent
capability review over its complete execution-critical and native closures
before any live candidate use. Readiness, a deterministic build, or this
report grants no F1 authority.
