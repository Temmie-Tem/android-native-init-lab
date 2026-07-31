# A90 Phase 2C Display Qualification and Observation Packet

- Date: 2026-07-31 KST
- Tier: H0
- Decision: `A90_PHASE2C_HOST_PROFILES_BOUND_NOT_LIVE_READY`
- Candidate identity: none
- Device action: none
- Live authority: none

## Result

The exact Phase 2B native and Debian host profiles are now bound by one
fail-closed H0 qualification packet. The packet reopens both A/B sides of all
five native artifacts, both clean ext4 images, and both static Debian
presenters. It also audits the coupled A90 checked boot-only flash route and
the absent-only rootfs publication lifecycle.

The profiles are not live-candidate ready. This is an intentional and useful
result: the remaining gaps are now explicit machine-readable blockers rather
than assumptions hidden in the old V3403-V3405 execution path.

## Bound host identities

Native Phase 2B:

```text
boot     3d3e66535654a62f83c5772caba27624acc160911307190de458154acaefdabb
ramdisk  7a34eec3bfd66abfca5d6d4043d514d87eb4eb3c458d281562025045ea45be66
init     67db45ee45144c1cd7bfde9cfd2ac6401292bad57fcf36f6c8543e31b59b83bd
helper   fa395d3ecb6944a57487f3966948a634596157e4de3fdc39575a2fc502d1ceef
engine   5b262978867bf98239e5d7e1b112f29b0217b59f057fc48c5b6e91d90eb5eaad
```

Every A and B file was reopened, size-checked, and hash-checked. The boot image
also retained Android boot magic. The historical accepted V3404 boot remained
unchanged, and the Phase 2 profile still grants no candidate authority.

Debian Phase 2B:

```text
ext4       cf2cf17d5c706123f85b21d4f2479fc348329cdc09e48fe6406874328e3977c8
presenter  8c41524749c6a59a8896e02d96a613efdffafcd01d165872f2317b22606a805b
```

Both ext4 sides are exact 2 GiB images with label `PHASE2DISPLAYV1`, and both
presenter files match. Read-only ext4 inspection proved that the clean image
contains none of:

- `/root/.ssh/authorized_keys`;
- `/etc/dropbear/dropbear_ed25519_host_key`;
- `/run/a90-native-display-release`;
- `/run/a90-display/ready`; or
- `/run/a90-display/failure`.

This proves the Phase 2B ext4 role is a clean deterministic base. It is not a
final single-run keyed rootfs. A future run must create a new inode, insert one
fresh observer public key, and bind the resulting new hash. Reusing the clean
base hash as the final staged identity is forbidden.

## Coupled A90 route audit

The existing A90 path remains valid only as the exact coupling of the
orchestrator, `native_init_flash.py`, and absent-only staging adapter.

The audit proved that the orchestrator supplies:

- one exact candidate or rollback path;
- its exact SHA256 and version;
- the exact recovery target; and
- `--from-native`.

It supplies none of the flash runner's broad standalone overrides. The runner
retains a sealed local copy, remote upload hash check, default boot block, and
post-write boot-prefix readback. Therefore the coupled route is the checked
boot-only path; the general runner CLI alone is not treated as proof.

The staging audit proved:

- fixed work path `/mnt/sdext/a90/runtime/d3-handoff-work.img`;
- final, work, and stage absence before publication;
- hard-link no-clobber publication;
- exact inode, size, and SHA checks; and
- no automatic removal of a preexisting final or work image.

The current adapter accepts only V3403, V3404, and V3405 run identities. It
correctly rejects the Phase 2 host profile because Phase 2C creates no new
candidate cycle.

## Observation contract

The new validator and fault tests define the later one-run evidence:

1. exact candidate health before handoff;
2. fresh final keyed rootfs and absent fixed work image;
3. zero-return native KMS teardown plus the exact native release marker;
4. Debian sysvinit PID 1 plus the exact sole-master display marker;
5. operator observation of all four fixed Phase 2 display strings through a
   manifest-, artifact-, marker-, and deadline-bound attended receipt;
6. terminal attempt-3 display failure classification with no candidate replay;
7. healthy no-sync candidate return and retained
   `A90D3RET_V3405 phase=armed` pmsg capture;
8. one exact rollback; and
9. final exact baseline health.

Free-form visual acknowledgement is not proof. A terminal display failure with
healthy return and rollback remains
`NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`.

## Machine-readable blockers

The final packet records exactly:

```text
FINAL_KEYED_ROOTFS_NOT_MATERIALIZED
PHASE2_LIVE_STAGING_IDENTITY_NOT_DEFINED
DISPLAY_OBSERVATION_NOT_IN_EXECUTION_RUNNER
FRESH_D0_MANIFEST_APPROVAL_ABSENT
```

The current orchestrator still proves Debian PID 1, Dropbear, retained pmsg,
return, and rollback. It does not yet read the native release marker, Debian
display ready/failure markers, or a bound physical visibility receipt.

## Validation

The new focused suite passed `6/6`, including:

- exact host-only runtime surface;
- full Phase 2B A/B reopen and hash validation;
- partial native cleanup rejection;
- non-sole or privileged DRM owner rejection;
- terminal bounded-failure enforcement; and
- exclusive private packet output.

The existing Phase 2 display suite passed `9/9`. The existing absent-only
staging plus A90 F1 orchestrator suites passed `120/120`. Touched Python passed
`py_compile`, and no device command was available in the new tool; its only
subprocess is read-only `debugfs`.

Final tracked identities:

```text
packet generator  79b28deca91c5ba98e9fa7a5f869178da6354c7d1ccd6fda1956b9eb2da79d43
contract          b4f7fa99728e0d1de57cb1e6521df14493d838fa34207bc52d2c914710de5b21
focused test      6e39d6e498e0b15a2abc157e01efa0f2112528be1f0be12d4d551b4d3e43b2e9
```

The final private packet is:

```text
workspace/private/outputs/a90-phase2c-display-packet-04/packet.json
sha256=42eef2f97cb37d4620fdcc6e9773bc39e7e79ae105f50c4760bc3764f16ec937
```

An earlier private packet file was successfully written before its CLI
relative-path rendering failed. It was not overwritten or reused. The output
path was then made absolute before publication, an exclusive-output fault
test was retained, and the final packet was created in a new directory.
There was no device transition to repeat.

## Review boundary and next unit

This unit did not change the F1 runner, manifest schema, flash wrapper, staging
adapter, recovery logic, permanent boundary, or hazard class. It added a
host-only analyzer and therefore did not require an execution-critical
independent safety review.

The next unit will change the execution-critical closure: implement per-run
key materialization from the clean Phase 2 base and integrate exact display
plus visible-acquisition observation into the manifest/orchestrator path.
That work requires focused fault tests and independent safety review before
any live use. It remains H0 and assigns no candidate identity until the new
closure passes.

Neither the A90 nor the separately connected S22+ was contacted or changed.
