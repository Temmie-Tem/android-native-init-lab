# P459 packaged cron workload and exact reboot retention

Status: **PASS_H0_PRODUCTION_CRON / independent PASS_GO**. The bounded unit is
one actual packaged-cron job followed by exact data retention across the
existing two-boot Debian sequence. This report records capability qualification;
it does not establish physical execution, a current physical baseline or an
attended grant. A90, S20+ and server work remain untouched.

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
The actual physical image consumer rejects the synthetic baseline. Fresh fixed
D0, an artifact qualified against it, current target/health/recovery checks and
a returned finite attended grant remain necessary for physical use.

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
is selected, preserving v3. Actual connector status confirms the connected
uid/euid-1000 worker with NoNewPrivs=0 and a fresh backend per request; no restart
or privilege change was needed. Worker readiness supplies no device authority.
Historical reviews, consumed records and pre-existing unrelated changes remain
preserved. No new grant, transfer or device effect belongs to this H0 unit.
