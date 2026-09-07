# S22+ P364 historical failure applicability audit

Scope: H0 review of prior S22+ incidents against the current P364 successor
path, including its inherited native supervisor, unchanged P361 renderer,
observer and generic host persistence. No device contact, consumed-run reopen,
production-code change, new candidate, preparation or F1 authority occurred.
This is an applicability audit of the selected lineage, not a whole-repository
absence-of-bugs claim. P364 remains consumed, CLOSED/19, NO_PROOF and healthy.

## Findings that apply now

### 1. Success evidence can exceed the current state writer's bound

The earlier P325 result-size incident and P342 state-size correction are directly
relevant. The terminal-result writer permits 64 KiB, but `_save_state` selects
that larger bound only for P342 and named/retained exploration owners. P364 is
neither, so its live-state writer still permits only 32,768 bytes.

A private H0 probe ran the actual generated preparation/console C with the
existing syscall fixtures, obtained a valid successful P364 qualification with
46 signed progress frames, and reopened its raw progress through the real
observer. It replaced only the qualification and native-progress projections
in a copy of the existing P364 closed-state evidence. All writes were to private
scratch storage. This is a representative size probe, not a complete semantically
consistent successful terminal fixture or a new successful device result.

| Quantity | Bytes |
| --- | ---: |
| Retained P364 failed live state | 28,978 |
| Representative state with real success projections, actual writer encoding | 37,750 |
| Selected live-state writer limit | 32,768 |
| Excess | 4,982 |

The actual `_save_state` rejected the representative state with
`durable record exceeds its bound`. Compact canonical JSON is 24,152 bytes,
but the durable writer uses indented JSON; measuring the compact form would
miss this failure. A larger result limit does not fix an earlier state write.
The successful projection is validated, but the complete future terminal size
and exact first failing live phase are not proved by this hybrid fixture.

Before a successor is qualified, exercise the real success and late-failure
producer/state/result serialization and reopening together. Then use the
smallest reviewed correction: remove redundant projection data or select an
appropriate existing bound for this exact state path, with matching read limits.
Do not widen journal limits or every JSON writer. The retained prepared record
is also 32,273 bytes, leaving 495 bytes under its 32-KiB writer; this is a capacity
consideration for added closure entries, not proof that a future prepare fails.

Current consumer: `_save_state` and `_write_prepared_record` in
[the live runner](../../workspace/public/src/scripts/revalidation/device_action_f1_live_v2.py),
plus `_write_exclusive_bounded` in
[the core writer](../../workspace/public/src/scripts/revalidation/device_action_f1_v2.py).
Historical examples: [P325 finalizer](S22PLUS_FYG8_P325_CLOSED_RESULT_FINALIZER_INDEPENDENT_REVIEW_2026-09-02.md),
[P347 sizing qualification](S22PLUS_FYG8_P347_OUTPUT_TIMING_PREPARED_2026-09-06.md),
and [P342 retained-state preparation](S22PLUS_FYG8_P342_IDLE_REUSE_PREPARATION_2026-09-05.md).

### 2. Journal reopen is a repairing operation, not a pure read

The P325 finalizer review already recorded the same issue in P324:
`Journal.reopen` calls `_write_head` even when the existing head bytes are correct.
The current core still does this. A scratch-only journal reproduction confirmed
identical head SHA-256 but changed inode, mtime and ctime. The direct constructor
and read validation can be used without that repairing reopen when a pure audit
is intended; ordinary recovery's repairing semantics must not be removed blindly.

P364's terminal-repair helper used this same `Journal.reopen` path. Its comparison
of all 7,119 prior file contents remains valid, and no device operation, live-state
write, append-only journal-record edit or candidate/rollback replay occurred.
However, it did not preserve or test all filesystem metadata: the same-byte
journal-head index was replaced. Descriptions of that operation must say
content-preserving host finalization, not strictly read-only or metadata-preserving.
No old journal was reopened during this applicability audit.

A future audit/finalization helper should distinguish read validation from index
repair explicitly and verify metadata when claiming no filesystem mutation.
This affects evidence bookkeeping; it does not invalidate P364's authenticated
progress, closed record chain, rollback or final-health facts.

### 3. The confirmed ARM64 flag defects remain unfixed in candidate sources

The directory O_DIRECT/O_DIRECTORY mismatch and missing module O_NOFOLLOW
protection remain the immediate native-source repairs. The display loader already
uses target header names for these operations; its implementation illustrates why
numeric literals in the freestanding return helper needed a target-specific check.
The frozen C, transferred ELF, Samsung kernel source and real ARM64 syscall
comparison are documented in the [P364 diagnosis](S22PLUS_FYG8_P364_PREPARATION_DIAGNOSTICS_2026-09-08.md).
Do not remove provider verification to avoid its error, or patch consumed inputs.

## Prior mechanisms checked against the current path

| Historical problem | Current applicability and evidence | Action |
| --- | --- | --- |
| P310 nested bytes and P345 JSON representation drift blocked final reporting | Current P364 failure/result persisted after the separately fixed namespace rejection; its real successful qualification serializes. Size remains the newly reproduced issue. | Test producer-to-persisted-record roundtrips, including success and late failure. |
| P339/P345 legacy projection dispatch and P364 shared-name rejection | The common runner now registers shell variants and admits only three exact shared return-state names for return owners. Four focused namespace tests and P363 regressions passed in the prior correction. | Retain exact namespace rejection and exercise complete terminal routing when adding a successor. Do not add wildcard exemptions. |
| P345 parent identity expected presentation names | Current return observer calls the numeric `parent_identity_valid` predicate. P364 retained valid parent identity. | Keep numeric witnesses; no new identity repair indicated. |
| P346 nonblocking stdout lost data with exit zero | Frozen P364 child setup retains P347's F_SETFL=0 on the pipe write end before dup/exec; parent reads stay nonblocking. | Preserve blocking child output and failure handling. The old defect was not found reintroduced. |
| P346 denied clock_nanosleep made sleep/usleep return zero early | The corrected relative realtime clock_nanosleep rule is present in the inherited child fragment. The fixed display child takes its separate executable path; arbitrary unsupported applets are not exposed by this return workload. | Preserve the existing scoped rule. Do not broaden sysinfo/prlimit64 or arbitrary shell capability for this candidate. |
| P339 collector rejected evidence before a later parser could capture it | P364 intercepts fixed signed progress in the actual protocol reader, forwards raw bytes and replays partial failures. The live run retained all 28 frames including terminal errno. | Preserve raw-first collection and the fixed grammar; parser-only tests are insufficient. |
| P340 early terminal echo corrupted OPEN | P341's host-first OPEN ordering is inherited. P364 authenticated and reached stage 30; the H0 success probe also completed that path. | Retain ordering and exact raw transport setup. No echo repair is indicated by current evidence. |
| P320 mixed kernel/userspace identity | Current artifact qualification binds raw Image and embedded configuration identity, packaged init and AP; the P364 ABI review joined init/AP to the actual transfer receipt. | Recheck actual packaged successor identity, not namespace labels alone. |
| P351 DRM-name/readiness and P352 inherited-plane assumptions | The current renderer is the byte-identical P361 renderer, with the source-bound DRM-name and inherited-plane corrections. P361 has separate observed clean repeated display evidence. | Reuse unchanged renderer qualification; new return preparation still needs its own evidence. |
| P353–P357 corrupt output despite accepted display requests | P358's CACHED route and subsequent pattern/transition checks remain in the P361 renderer. Pixel rendering, ioctl acceptance and visibility remain different facts. | Keep the working buffer route and separate visible-output evidence; do not infer scanout from host byte tests. |
| USB endpoint departure while waiting for physical recovery in several prior runs | This remains a bounded transport/recovery limitation. Current source keeps exact endpoint checks; P364's physical return completed without that incident. | Preserve failure-specific stop and same-journal recovery. Do not turn an unexplained departure into automatic-reboot proof. |
| P341/P346/P363 baseline D1 stops or late return | Healthy Android return outside a bound does not qualify that D1 or prove recovery from a stuck native runtime. | Reuse current health only within its proper scope; no automatic recovery or replay inference. |

Historical detail for the checked mechanisms is retained in
[P310 serialization](S22PLUS_FYG8_P310_CARRIER_V2_JSON_SERIALIZATION_INCIDENT_2026-08-09.md),
[P339 collector/finalizer](S22PLUS_FYG8_P339_INITIAL_CAPTURE_INCIDENT_2026-09-05.md),
[P341 host-first OPEN](S22PLUS_FYG8_P341_HOST_FIRST_OPEN_PREPARATION_2026-09-05.md),
[P345 identity/projection](S22PLUS_FYG8_P345_SHELL_QUALIFICATION_NO_PROOF_2026-09-06.md),
[P346 adjacent audit](S22PLUS_FYG8_P346_ADJACENT_FAILURE_AUDIT_2026-09-06.md),
[P347 repair](S22PLUS_FYG8_P347_OUTPUT_TIMING_PREPARED_2026-09-06.md),
[P352 source-bound display](S22PLUS_FYG8_P352_SOURCE_BOUND_DISPLAY_H0_2026-09-07.md),
[P358 cached framebuffer](S22PLUS_FYG8_P358_CACHED_FRAMEBUFFER_PREPARATION_2026-09-07.md),
and [P362 native return analysis](S22PLUS_FYG8_P362_REBOOT_DOWNLOAD_PATH_ANALYSIS_2026-09-07.md).
These historical artifacts are evidence, not transferable device authority.

## Existing limitations that must remain explicit

The stock reason-writer NVMEM failure hazard and its initialization FULLDUMP
window remain relevant when the fifth module becomes reachable. This reinforces
the provider/registration checks; it does not justify removing them to get past
stage 30. The cached display driver's internal DMA-map retry behavior identified
in P358 also remains unchanged. Neither hazard was newly observed in P364.

The fixed diagnostic deadline starts before preparation; the child deadline
starts later. Therefore a late child failure may have no terminal diagnostic
after the earlier deadline expires. The existing test and target contract state
this limitation. Missing RETURN means return unobserved, and ACK means control
acceptance rather than verified Download arrival. No new timeout mechanism,
background session or mandatory long experiment was added by this audit.

## Evidence and validation

Private evidence root:
`workspace/private/outputs/s22plus_fyg8_p364/history-applicability-audit/`.

- `probe.py`, `success-proof.json`, `state-budget-probe-serialized.json`: generated
  C success, raw replay, exact indented writer sizing and actual writer rejection.
- `scratch-journal-metadata-evidence.json`: scratch-only index rewrite evidence,
  SHA-256 `f42a176f6f4fe0652964411446c4721a2b8963b637ab8c9ea3ec0b10535ed217`.
- `independent-applicability-review.json`: independent confirmation of both
  findings and the hybrid-fixture limit, SHA-256
  `c0d694b94758df75ac70d933ebda880cc2ecd782bc79f75fb223f3f7814ca93e`.

The audit changes documentation only. It does not apply native flags or writer
repairs. The next useful unit is a scoped successor repair with target-ABI tests
and complete persistence-path fixtures, followed by the existing independent
changed-closure review and qualification. No old candidate or approval is reusable.

Document links, diff whitespace and repository boundary checks passed.
