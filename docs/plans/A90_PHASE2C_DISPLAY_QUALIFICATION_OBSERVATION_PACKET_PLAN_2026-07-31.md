# A90 Phase 2C Display Qualification and Observation Packet

- Date: 2026-07-31 KST
- Tier: H0
- Host schema: `a90-phase2c-display-qualification-v1`
- Candidate identity: none
- Device authority: none

## Question

Can the exact Phase 2B native boot and clean Debian display rootfs be bound
into a fail-closed host qualification packet, and what remains before they can
become one A90 display-acquisition F1 experiment?

## Selected scope

This unit:

1. reopens and hashes both sides of the Phase 2B native and Debian A/B builds;
2. binds all five native artifact identities and the clean 2 GiB ext4 identity;
3. re-audits the coupled A90 checked boot-only flash command;
4. re-audits absent-only rootfs publication and fixed work-image refusal;
5. defines exact native release, Debian DRM acquisition, physical visibility,
   bounded display failure, no-sync return, rollback, and final-health
   evidence; and
6. emits one private H0 packet that states every remaining live blocker.

It does not assign V3406, create a run ID, materialize a per-run key, contact a
device, stage a rootfs, prepare an approval, flash, reboot, or create live
authority.

## Identity roles

The Phase 2B native boot is a byte-qualified host artifact. It is not yet a
candidate because no target-bound final manifest or fresh F1 approval exists.

The Phase 2B ext4 image is a clean deterministic base, not a final keyed
rootfs. Read-only ext4 inspection must prove the absence of:

- `/root/.ssh/authorized_keys`;
- a generated Dropbear host key;
- the native release runtime marker;
- the Debian display-ready marker; and
- the Debian display-failure marker.

A later run must copy this base to a new inode, insert exactly one fresh
run-bound observer public key, revalidate the display overlay and filesystem,
and bind the resulting new size and SHA256. The clean-base hash must never be
substituted for that final keyed-image hash.

## Coupled flash and staging audit

The accepted A90 route remains the manifest-bound coupling of:

- `a90_v3403_f1_orchestrator.py`;
- `native_init_flash.py`; and
- `a90_v3403_absent_only_staging.py`.

The qualification packet must prove that the orchestrator supplies the exact
candidate or rollback path, SHA256, version, recovery target, and
`--from-native`, while supplying none of the flash runner's broad standalone
overrides. The runner must retain sealed-copy validation, remote image hash,
the default boot block, and boot-prefix readback. This coupled invocation is
the proof; the runner's general CLI by itself is not.

The staging audit must retain:

- one run-derived final path;
- the fixed `d3-handoff-work.img` path;
- all final, work, and staging paths absent before reservation;
- hard-link no-clobber publication;
- exact inode, size, and SHA verification; and
- no deletion or replacement of a preexisting final or work image.

An old retained work image is a stop. It is never automatically deleted to
unblock a candidate. Any later cleanup remains a separately classified,
explicit action after evidence preservation.

## One-run observation contract

### Native release

The handoff transcript and work-root marker must jointly prove:

- every KMS cleanup return is zero;
- DRM master was dropped and the native descriptor closed;
- native PID 1 and every other process have zero DRM descriptors;
- native KMS state is uninitialized;
- native display services cannot restart in the synchronous corridor; and
- the exact `a90-native-display-release-v1` marker exists before mount
  movement.

### Debian acquisition

The exact `a90-debian-display-v1` marker must prove:

- `/usr/sbin/init` is PID 1;
- the presenter is UID/GID 3904;
- effective capabilities are zero and `no_new_privs=1`;
- no controlling VT exists;
- `/dev/dri/card0` matches the recorded nonzero DRM major and minor;
- DRM master and `SETCRTC` succeeded;
- connector, CRTC, and nonzero mode are recorded;
- the presenter owns exactly one DRM descriptor;
- every other process owns zero DRM descriptors; and
- no native-init process remains.

### Visible acquisition

The operator must see all four fixed strings:

```text
A90 DEBIAN
DIRECT DRM SESSION
PID 1: SYSVINIT / VT: NONE
DISPLAY OWNER: DEBIAN
```

Free-form acknowledgement is not proof. A later attended receipt must bind the
final manifest, candidate boot, final keyed rootfs, exact ready-marker hash,
and observation deadline. Designing and implementing that receipt changes the
execution-critical observation schema and therefore requires independent
safety review before live use.

### Bounded failure

Terminal display failure is exact attempt 3 with nonzero return code and no
ready marker. It does not authorize a retry or candidate replay. The no-sync
return and mandatory rollback still proceed. With final health restored, the
formal outcome remains `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`.

### Return and close

The same run must observe the healthy candidate identity after the no-sync
return, capture one retained `A90D3RET_V3405 phase=armed` pmsg record before
cleanup, perform one exact rollback, and restore exact baseline health. A
display marker without return and rollback is not an F1 pass.

## Expected H0 decision

Successful host validation closes:

`A90_PHASE2C_HOST_PROFILES_BOUND_NOT_LIVE_READY`

The expected blockers are:

1. final per-run keyed rootfs not materialized;
2. Phase 2 live staging/run identity deliberately not defined;
3. display and visible-acquisition observation absent from the execution
   runner; and
4. fresh D0, final manifest, exact rollback binding, and F1 approval absent.

The next implementation unit is reviewed per-run keying plus Phase 2 display
observation integration. It remains H0 until the execution-critical closure,
focused fault tests, and independent review all pass.
