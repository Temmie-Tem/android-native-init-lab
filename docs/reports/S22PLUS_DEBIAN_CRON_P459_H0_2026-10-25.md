# P459 packaged cron workload and exact reboot retention

Status: **PASS_H0_PRODUCTION_CRON / independent PASS_GO**. The bounded unit is
one actual packaged-cron job followed by exact data retention across the
existing two-boot Debian sequence. This report records capability qualification
and subsequent physical preparation; it does not establish physical execution
or an attended grant. A90, S20+ and server work remain untouched.

The subsequently approved [physical run](S22PLUS_DEBIAN_CRON_P459_RUN_2026-10-25.md)
completed the workload and exact reboot retention, then closed healthy in
Android. Its task and grant are consumed; the preparation facts below retain
their original H0 meaning.

## Resulting behavior

The [cron specialization](../operations/S22PLUS_DEBIAN_CRON_V1.md) selects
`p459` / `v0.20.0-rc.0`. After packaged rc2, boot 1 stops, starts and restarts
the installed cron service once each. Exit zero is insufficient: the old
daemon must disappear and each new daemon must pass executable, root, FD and
PID/start-time checks. Bounded readiness reads share the original service
dispatch deadline; hard identity mismatches stop immediately. The original
120-second stable-service observation starts only after the final restart.

One fixed RAM crontab invokes the actual packaged cron/PAM/shell path. The
worker authenticates its ancestry, consumes an exclusive RAM intent, retires
the schedule, hashes the installed cron and sshd programs and exclusively
creates one 512-byte root-owned report on native_data. File/parent sync and
close must succeed before the RAM completion receipt. The sequential observer
waits for the winning job and its intermediate processes to disappear; the
asynchronous job never appends the existing sequential runtime chain.

Both boot-2 protected admissions authenticate the report against the exact
first-boot early record, run, key, source, root device and sealed count. The
host also compares its bytes with the acknowledged first-boot snapshot. Boot 2
creates no new cron report. The original one-N/two-boot/four-writable-lifetime/
one-A owner, deadlines and physical recovery remain. The crontab is a RAM
overlay; persistent configuration and package installation are not proved.

Original PAM behavior is retained. Its temporary output is confined to an
8 MiB/512-inode RAM `/tmp`. A separately owned failure revocation clears READY
and the same schedule inode, sets the schedule mtime to zero and records the
outcome in RAM. This fixed cleanup may finish after expiry but cannot retry a
disk write, remove a partial report, renew a deadline or prove quiescence.
An already accepted worker can still be in flight; uncertainty retains the
original physical A return.

The four final P458 files are exact expectations derived from the original
authenticated reboot/shutdown captures and healthy closure. Their source
provenance is preserved. They are not post-Android retrieval evidence; the
first successful current complete admission must establish later retention.

## Validation

The final frozen ARM64 build is A/B identical. All **45 production cases pass**:
the retained 25-case two-boot/root corpus, eight cron-report admission failures
and twelve cron-runtime failures. The strict production validators rederive
the complete raw corpus. Independent rederivation also passes with writes,
process launches and network access prohibited.

The normal run executes the real cron workload and two kernel boots. Its pinned
SSH responses span 141440 and 120710 ms; the boundary fixture advances installed
boot count from 99998 to 99999 and 100000. The report is identical in both boot
snapshots and final extracted disk bytes. Four admitted RW setups advance M=22
to clean M+4=26, with bytes outside native_data unchanged. These are VM results
with declared platform/watchdog/USB substitutions, not physical-device proof.

Failures cover absent, changed, linked, symlinked, oversized, wrong-mode,
wrong-boot and already-present reports; missing work; partial output without
replay; failed lifecycle/revocation; deadline expiry; a no-op service command;
manual invocation; cached-schedule revocation; transient readiness; readiness
timeout; and hard program identity mismatch. Runtime failures are stopped by
the H0 driver only after their failure evidence and never claim normal cleanup.

**48 focused tests pass**, including both real phase constructors, P459 owner
selection, finite windows, uncertain controls and lost-result reconstruction.
Touched Python compiles. The actual production terminal payload saves and
reopens at 41767 bytes for success and 17001 bytes for a late second-boot failure;
the fixture ownership is explicit. The latter does not claim retained cron data.

The actual **38,041,641-byte boot-only AP** passes archive/payload qualification.
Its output remains `h0-synthetic-package.json`, without a physical `image.json`.
The actual physical image consumer rejects the synthetic baseline. The separate
preparation below supplies fixed D0 and its qualified physical artifact;
current target/health/recovery checks and a returned finite attended grant
remain necessary for physical use.

## Findings repaired before physical preparation

Independent review found that truncation within cron's cached whole second
could leave a periodic entry cached. Revocation now sets mtime to zero. The
actual cached-cron regression observes one invocation and no second entry for
92052 ms, with the same daemon, an empty zero-mtime schedule and no disk report.

A loaded VM exposed the gap between service-start completion and daemon
readiness. Only narrowly classified startup absence and disappearing proc/FD
objects may be reobserved; content/hash/root/forbidden-FD mismatches remain hard
failures. The revised normal run actually observed a transient proc absence
after restart and accepted its second complete sample without another command.

The first hardlink fixture changed link count without creating an alias, so
the read-only filesystem checker rejected inconsistency before the intended
root-consumer test. A valid hardlink pair now exercises the intended rejection.
An initial host decoder also expected a scalar device number instead of the
actual major/minor projection; the real producer/consumer join and regression
test cover the corrected conversion. Original failed builds and VM evidence
remain private and unchanged.

## Existing past-failure checklist

| ID | Evidence and limit |
| --- | --- |
| ABI | ARM64 producers exercise proc identity, exclusive writes, synchronization, tmpfs and inode timestamp changes; no new raw block writer. |
| IO | The 512-byte report, partial-write/no-repeat case and original bounded SSH collector retain producer status and exact bytes. |
| SEMANTIC | Actual scheduled ancestry, readiness, lifecycle, sync receipt, process settlement and later retention are separate predicates. |
| WIRE | Real C report/HMAC bytes pass both protected consumers and the host decoder; nonce/boot/source and noncanonical records reject. |
| PERSIST | Actual report snapshots, final VM bytes and success/late-failure terminal JSON save/reopen; control-publication loss never retransmits. |
| ROUTE | Actual P458/P459 phase constructors and P459 eight-step owner tests pass; physical admission rejects synthetic data. |
| ARTIFACT | Identical A/B binaries, source closure, exact template substitutions and actual boot-only AP are qualified. |
| AUDIT | Faults operate only on labelled regular VM fixtures; P458 producer expectations are not relabelled as retrieval. |
| HOST | Backend review must match current sources; unchanged stable worker machinery retains its privilege and exact-approval checks. Live worker and host readiness remain preparation/run checks. |
| DISPLAY | Not applicable: no display change or proof. |
| RETURN | Existing one-shot N/reboot/shutdown/A and health-only recovery tests pass; actual physical return and Android health remain unproved by H0. |

Private evidence is under
`workspace/private/outputs/s22plus-debian-cron-p459-h0-20261025-1/`:
`build-6`, `vm-4/result.json`, `package-h0-1`, `physical-admission-guard.json`,
`focused-tests-review3.json`, `terminal-persist-result.json` and `review/`.
The review binds 152 reachable host/policy sources and 172 runtime sources.
The published [P459 capability](../../workspace/public/src/device-action/bindings/s22plus_debian_autoboot_p459_review.json)
passes its original current-source consumer.
Its separate dispatch review covers the five changed members of the existing
20-source backend closure; the stable worker and policy are unchanged.
The immutable [backend v4 review](../../workspace/public/src/device-action/bindings/s22plus_approved_terminal_persistent_v4_review.json)
was selected for this qualification, preserving v3. Actual connector status confirms the connected
uid/euid-1000 worker with NoNewPrivs=0 and a fresh backend per request; no restart
or privilege change was needed. Worker readiness supplies no device authority.
Historical reviews, consumed records and pre-existing unrelated changes remain
preserved. No new grant, transfer or device effect belongs to this H0 unit.

## Physical candidate and ordinary-entry correction

The separate fixed Android D0 reads the existing native_data superblock and
confirms clean M=22, unchanged Android32 geometry and same-boot original-A
health. It performs no mount, write, control or transfer. This is superblock
evidence only; both full protected admissions remain execution requirements.
The physical A/B build is identical and its new run/key pass all 45 ARM64 cases,
production raw rederivation and independent rederivation. The actual physical
38,041,641-byte boot-only AP passes original archive/image qualification.
The normal VM retains the exact 512-byte cron report across both boots and in
the final disk, with clean M=26 and unchanged bytes outside native_data.

The first ordinary preparation exposed a missing host module search path:
the build driver could import the frozen cron-failure decoder, while the normal
V3 entry could not. It stopped before creating a task directory or any device
effect. The original failure is retained. The seven-line host-only correction
in `s22plus_native_task_v3.py` appends the exact repository module directory
once, preserving normal import precedence. No producer, validator or artifact
input changes; all 172 original runtime source identities remain unchanged.

Seven focused tests pass, including an isolated Python process from an unrelated
directory and the actual decoder/reload path. A separate cold original
`image_valid(..., artifact_bytes=True)` invocation passes with every file write,
process launch, network action and raw acquisition denied. It confirms the
decoder's exact repository location and revalidates the complete retained
physical image. Independent **PASS_GO** covers the one changed host source and
the corresponding dispatch binding. The original review and backend v4 remain
preserved; immutable backend v5 is selected and the existing connected worker
reports its exact identity without a restart.

The concrete task selects one attended 3600-second operation: one N transfer,
two Debian boots, four admitted native_data RW lifetimes, one ordinary reboot,
one final shutdown and one physical Download/original-A return. The original
offline preparation and both real phase constructors pass. The exact eight-step
sequence is retained, and constructor fixture data is rejected as a grant.
Independent **PASS_READY_H0_AND_UNEXECUTED_ENTRY** has no findings. The actual
current `Controller.bundle` and its persisted receipt pass; seven negative
cases reject missing or mismatched approval/binding data. At that preparation
boundary no operator approval, grant or dispatch was present. The later
physical run supplied its exact returned approval and current attendance;
neither this readiness nor the consumed grant authorizes a successor.

Private evidence adds `baseline-d0-2/result.json`, `physical-build-1`,
`vm-physical-1/result.json`, `package-physical-1/image.json`,
`offline-prepare-failure-1.json`, `review-4/closure.json`,
`host-import-cold-result.json`, `review/independent-host-import-review.json`,
`review/independent-host-import-bridge-review.json`,
`host-import-capability-activation.json`, `live-bridge-status-v5.json`,
`prepared-validation.json`, `unexecuted-validation.json` and
`review/prepared-entry-review.json`.
