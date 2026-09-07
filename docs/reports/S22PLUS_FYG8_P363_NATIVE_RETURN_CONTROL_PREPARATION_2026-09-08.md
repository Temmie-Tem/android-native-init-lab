# P363 native return control preparation and result

Status: consumed and CLOSED/19 after one candidate and one exact Magisk
rollback. `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`, `NO_PROOF_OBSERVER`,
recovery_required=false. Final rooted FYG8, original boot/supporting hashes,
Android health and absent Download passed. No native return or visible display
proof was obtained; there is no active lease or successor F1 authority.

The operator reported no pattern, only a black screen or logo. The observer
retained a 365-byte raw stream and classified `authenticated-session-error`
after 60.028114 seconds. No session completed, no durable CONTROL intent or ACK
was retained, and the fixed return-window record says `not-requested`.
The generic qualification conservatively retains control occurrence UNKNOWN;
that is not evidence of a command acceptance or successful native Download.
The supplemental stock witness also supplied no accepted candidate record.
Module preparation and the precise exchange failure cause remain unproved.
Post-run replay subsequently verified authentication and the complete host
display-frame write; the enclosing error label does not mean authentication
failed. See [preparation-path analysis](S22PLUS_FYG8_P363_POSTRUN_PREPARATION_PATH_ANALYSIS_2026-09-08.md)
for the confirmed silent-error path and its remaining causal limits.

After observation closed, original execute stopped on measured USB endpoint
evidence: attempted snapshot23, `usbfs-endpoint-departed`,
`enumeration-evidence-before-snapshot`, snapshot_persisted=false. Its immutable
diagnostic and bounded observer bytes remain private. The physical cause is
unproved; missing endpoint evidence is not continuity proof. Durable state was
OBSERVED with candidate completion and no rollback intent. The operator then
confirmed physical Download entry. One ordinary same-journal rollback-only
recovery completed exact rollback and final health without candidate, display
or CONTROL replay. No execution-critical source was changed during recovery.

The canonical UTC timeline is retained in the live result:

| Event | 2026-09-07 UTC |
| --- | --- |
| live_session_start | 16:30:50.595394 |
| candidate_flash_start | 16:31:08.523893 |
| candidate_flash_done | 16:31:10.167299 |
| candidate_boot_ready | 16:32:12.013475 |
| rollback_flash_start | 16:34:25.088610 |
| rollback_flash_done | 16:34:26.611141 |
| rollback_boot_ready | 16:35:04.217299 |
| live_session_end | 16:35:04.237433 |

`candidate_boot_ready` is the journal's observation-close event; it does not
turn the failed exchange into successful display or native control. Final
live-result is 20,832 bytes, SHA256
`b1d4dbe1dde8be813b6affd5ffa3b7b4c981fb4116d98f15c04650e841d42ac3`.
The retained preparation, execution closure and final journal/result passed
reopening with the actual consumers before reporting close. A90/S20+ received
no command from this task.

The following preparation history preserves what was qualified before the
consumed run. It grants no replay or fresh device authority.

P361 proved operator-observed repeated display and ended CLOSED/19 after exact
Magisk rollback. P362 found the missing stock reboot-reason/provider closure.
P363 retains the P361 renderer and adds a supervisor-owned authenticated fixed
Download request. Ordinary same-PID1 reboot is intentional, but only its H0 code
path is included in this first Download-only qualification.

The native parent loads five exact stock modules from the same hash-checked
ramdisk FDs. It resolves both NVMEM providers by exact DT node, waits at most
five seconds for the asynchronous command table, and checks the final writer's
synchronous binding. Pointer-bearing debugfs text remains local and is reduced
to a readiness predicate. The renderer retains its existing privilege drop.

READY reports ten submitted swaps while running, or the observed count and an
early child exit. It does not report visible pixels. Fixed CONTROL is accepted
only in the authenticated session and immutable Download mode; consumption
precedes ACK and syscall. ACK write failure prevents the syscall. A returned
syscall and any uncertain host write are never retried. The original absolute
60-second child/control deadline does not bound blocking kernel operations.

BOOT-v2 uses SHA256 of exactly 36 lowercase kernel UUID ASCII bytes. Host receipt
fields hash those 32 wire bytes again. RNG nonce remains session-specific;
historical random wire boot tokens retain their historical meaning.

The host seals intent before any CONTROL byte and joins raw replay to the exact
run, nonce, boot digest, endpoint and pre-control lane. A 30-second software
observation window precedes the physical Download prompt. Only an actual
observer timeout selects fallback; USB enumeration and identity failures retain
the existing stop. Actual Download, ACK, exact rollback and final health remain
separate. Physical intervention is unobserved by the machine, so software causal
attribution stays UNPROVED until separately supported by operator observation.

The five-module stock path includes known limitations: qcom-dload-mode initially
requests NODUMP/disable_sdi, but Samsung writer probe then requests FULLDUMP.
A clean reboot notifier clears it. Firmware persistence semantics of disable_sdi
remain unproved. The stock writer contains kfree(ERR_PTR) after a failing NVMEM
read and does not propagate every reason write/readback failure. This trial is
attended with physical Download and exact Magisk rollback; no dump collection,
panic/watchdog/EDL trigger or automatic recovery is enabled.

The final 24 C/Python and host tests passed: normal/split requests, wrong
HMAC/run/nonce/mode/sequence, oversized/partial input, early renderer exit with
multi-read backlog, malformed kernel UUID, intent failure, ACK failure/partial
ACK, ordinary restart mapping in an H0-only build, and the absolute child timeout.
Host tests covered raw intent joins, no-clobber/fsync-failure behavior, actual
bounded timeout versus fatal USB error, orphan-window reopening, timestamp/
attribution rejection, and malformed/invalid-UTF8 local-record recovery.
The unchanged P361 C/dispatch paths also passed 15 regression tests.
Independent module review passed 20 actual-C cases with ASan/UBSan, using the
five real stock byte streams and repository SHA256 implementation.

Final A/B Image, init, renderer, boot and AP are equal. AP is 31,006,761 bytes,
SHA256 `216611fec417eff40ddf9c56f1626876371debd1066db070e4dc8bcba223b608`.
Image is `d575108eec0dfcffec077817d696bd4a18853c2f26f0cb111c902f118ece5dc5`;
renderer bytes are unchanged from P361. Both static qualification and the actual
published ready-manifest verifier passed. Touched Python compiled, native C
cross-compiled to a static AArch64 init, and the repository boundary check passed.
The final input check reverified 119 source identities and six artifacts.

H0 corrections preserved earlier build/evidence directories. A registry timing
race was repaired with a fixed readiness wait; signed READY count is frozen
across buffered child output. Local-record errors foreclose return proof while
preserving physical rollback. Later comment/audit wording and the builder's
captured default-output path were corrected in a fresh A/B build; final AP bytes
match the earlier pair, with no byte-affecting candidate change. Final source
closure pins the corrected host verifiers and policy, not historical receipts.
These are H0 qualifications, not native Download or automatic recovery proof.

Connected preparation first stopped at the retained baseline decoder, before
any F1 effect. The existing reviewed D1 primitive then sent one authorized
ordinary Android reboot. Its 240-second healthy-return bound expired with ADB
offline, so that D1 is STOPPED and consumed with bounded return NO_PROOF.
Its start record, 125 raw command captures and exception remain intact; no
primitive result was fabricated and no reboot, reconnect or USB reset was retried.

The operator subsequently reported the Android lock/home screen. Host kernel
records show a later USB disconnect/re-enumeration; its physical cause remains
UNPROVED. A separate read-only D0 invocation then passed, and the actual bundle/
D0 validators reopened its raw evidence successfully. Boot identity changed,
while rooted FYG8, original boot/supporting hashes, Android health and absent
Download were verified. This establishes current health, not bounded D1 return
or automatic recovery. The separate private incident observation-close record
preserves that distinction and the executed source identities. Only fresh
H0/D0 preparation through code issuance resumed at that point; F1 execution
still required separately returned attended approval and physical recovery.
At that preparation stage no P363 candidate or native control had executed.
A90/S20+ received no command.

Fresh preparation `p363-ready1-prepared-20260908-2` passed exact connected D0
on the same healthy boot as the independent late observation. The first failed
preparation remains intact and is not reused. The approval token is retained
privately and issued to the operator; no transfer or live journal existed at
that stage. The operator subsequently returned it for the consumed run above.
The actual `load_prepared` consumer successfully reopened the prepared record,
including its execution closure, raw D0 evidence and approval binding. All 119
qualified source identities, six artifacts and two review receipts still match.

Private artifacts and raw evidence are under
`workspace/private/outputs/s22plus_fyg8_p363/`. No private identifier, firmware
payload, pointer-bearing text or raw device log belongs in this report.
