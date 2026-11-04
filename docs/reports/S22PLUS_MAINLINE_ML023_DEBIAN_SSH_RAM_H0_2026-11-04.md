# S22+ ML023: packaged OpenSSH on Debian RAM PID1

Status: **H0 QUALIFIED / INDEPENDENT PASS_GO; PHYSICAL RUN CONSUMED /
SSH NO_PROOF / ANDROID_CLOSED_HEALTHY**. No successor grant is armed.
The [physical run report](S22PLUS_MAINLINE_ML023_RUN_2026-11-04.md) records
positive base Debian evidence, a host pre-spawn SSH failure and completed
original-A recovery. The preparation evidence below retains its original scope.

## Selected unit

ML022 demonstrated packaged Debian SysVinit as initial RAM PID1 and its direct
runlevel-2 observer child. ML023 adds the next useful server capability: an
ordinary packaged OpenSSH daemon and one authenticated, noninteractive session
running a fixed unprivileged command. The final product remains persistent
Debian with ordinary services and headless access. This unit does not claim
persistence or a general shell.

Two critique/challenge rounds with Claude Opus 5.5 High and Gemini 4 Argon High
selected this unit ahead of mainline UFS bring-up or a new Type-C attach path.
It advances standard access using the already working kernel/USB condition;
UFS would require a new driver/storage scope, while the no-replug mechanism
remains unresolved. Suggestions were checked against actual package source,
binaries and VM behavior rather than adopted as authority.

The physical scope retains one attended operation, one N transfer, the same
original observation window, separate physical Download and one original-A
return with full final Android health. The old ML022 candidate and grant remain
consumed. The daemon and kernel are not claimed to stop at the observation
deadline, and no automatic recovery is qualified.

## Implementation and actual package behavior

The signed closure contains 22 Debian packages and 27 ELF members: SysVinit,
OpenSSH's listener/session/auth executables, dash and their recursive dynamic
libraries. The fixed CPIO, accounts, keys, configuration and command are
reconstructed canonically. SysVinit directly starts the existing observer and
foreground sshd as parallel `once` children, with no restart loop. Static
null/zero/urandom nodes and `/run/sshd` are available before concurrent startup.

Only the fixed UID/GID 1000 account and its candidate-specific Ed25519 key are
accepted. Root/password/PAM/GSSAPI authentication, PTY, forwarding/tunnels,
user RC/environment and configured subsystems are disabled. System sshrc and
the standalone SFTP helper are absent. Internal-SFTP bytes remain part of the
packaged program but cannot be selected by this configuration. The fixed dash
command uses builtins to return this boot's ID and its own UID/GID, groups and
effective capabilities; requested command text is not interpreted.

The existing authenticated observer gains a distinct SSH wire domain and a
bounded positive startup indication. It checks a complete post-listen pidfile
and the live sshd executable path after authenticating its original request.
The existing listener is available while this check waits. Actual SSH output,
not the pidfile, proves the session and joins the base proof by boot ID.

The host uses one config-free, agent-free, host-key-pinned SSH invocation.
Inspection of the actual installed client showed that `-b` takes precedence
over `-B`; both implement address binding, not `SO_BINDTODEVICE`. The final
command therefore uses only the exact source address. A fresh unconstrained
route lookup must select the bound NCM interface directly, and complete USB
endpoint censuses bracket SSH. Its intent, bounded stdout/stderr and process
status are durable before interpretation; neither a failed call nor an
uncertain result can create a second client invocation.

## H0 corrections and proof limits

- The first real VM connected to sshd but authentication failed because the
  minimum CPIO omitted an explicit root-directory entry. OpenSSH `StrictModes`
  rejected `/`. Adding root-owned `.` with mode 0755 fixed the actual session;
  authentication limits were not weakened. The earlier failed raw is retained.
- A preliminary SFTP expectation incorrectly assumed all subsystem requests
  reach `ForceCommand`. Exact source and raw output show that an undefined
  subsystem is rejected before command execution. The checker and scope now
  describe that rejection; no subsystem was enabled.
- Forwarding was rejected, but ERROR-level client logging hid the specific
  reason required by the H0 checker. Only that negative VM case uses VERBOSE
  logging, preserving the explicit administrative-prohibition evidence.
- The shared raw producer's ordinary timeout uses a monotonic clock. SSH now
  additionally selects its original absolute `CLOCK_BOOTTIME` deadline, which
  includes host suspend, with the existing four-second termination settlement
  reserved. Tests include expiry before spawn, a clock jump during acquisition,
  and a jump immediately after a child exits with code zero. Late zero-exit
  output remains timed out and cannot become success. Other callers retain
  their existing default behavior. This does not assert atomic cancellation
  of a remote child on suspend.
- VM aggregation now preserves the settled process and raw capture even when
  a later interpretation fails. Earlier incomplete aggregate provenance is
  not promoted to final qualification. Functional success, raw completeness
  and checker success remain separate.

The private preliminary VM proved actual packaged authentication and fixed
command execution with all UID/GID fields 1000, supplementary group 1000 and
zero effective capabilities. Wrong-key, root, PTY, forwarding and undefined
SFTP requests were rejected, and an arbitrary command request produced only
the fixed result. Final qualification has repeated these cases with the fresh candidate's exact
kernel and complete raw captures; the preliminary results do not substitute
for that qualification.

Standard OpenSSH entropy/crypto, privilege separation, chroot/seccomp,
process/signal handling, RAM accounting attempts and process-local OOM proc
adjustments remain in scope. The selected kernel still has BLOCK, DEVMEM and
KEXEC settings; RAM use is not a claim of zero hardware hazard. The fixed
nonroot command and exact closure bound this experiment. Linux UFS remains
compiled out; no installed-root or native_data operation is added.

## Validation and pre-execution preparation

The unchanged functional kernel/config/DT/PHY baseline is checked against
ML022. Fresh candidate identity and retained-marker literals require a fresh
Image and loader despite that functional equality. The first H0 preparation
predated the final SSH address-binding correction and is retained as a draft;
the final candidate is prepared in a fresh second directory with current input
pins. No device effect or grant was created by either preparation.

The focused base/SSH wire, one-shot owner, approved terminal and raw producer
suite passed 64 tests. Three later cases cover ready-false without an attempt,
actual producer-to-offline-consumer proof with endpoint-intent tampering, and
original-A recovery despite an unavailable SSH validation dependency. The final
SSH suite passes all 14 cases; unchanged tests retain their previous results.

Both final observer binaries reproduce exactly. The new Image, enlarged
loader placement and actual linked routines pass 20 loader cases, three actual
exception-level loader boots, 342 marker cases and six actual exception-level
marker runs. Two independently packaged APs are identical. The fresh kernel
boots the exact VM-marked packaged closure for a positive base/SSH exchange,
a wrong-HMAC rejection and all six additional SSH cases. Complete raw recheck
and the combined physical/VM qualification pass. Five modified real CPIOs,
with honestly updated outer archive hashes, reject writable root, setuid dash,
changed authorized key, disabled StrictModes and missing split executable.
Independent final review is `PASS_GO` with no findings. It rederived the
signed package/CPIO closure, all complete final VM evidence, actual embedded
Image/DTB/initramfs, enlarged loader layout and both boot-only AP envelopes.
An isolated use of the actual image/task/terminal preparation consumers passed,
while missing human approval was rejected. The public capability receipt and
backend V29 are adopted; the two stable worker inputs are unchanged. This
qualifies the capability and candidate, not a physical run.

The actual production image admission also rejects eight honestly rebound
cross-mode, identity, qualification, parent-proof, missing-SSH-case and wrong
host-client variants. The exact task and connector preparation are published
against ML022's closed healthy predecessor. The existing stable terminal
worker reports backend V29 and remains unchanged.

One authorized fixed preapproval D0 completed and its full seven raw health
captures rederive successfully, with successful producer status and empty
stderr throughout. The current Android target/health and original-A identity
passed at preparation. That D0 created no candidate control, partition transfer,
operation grant or attendance claim. Execution subsequently used a refreshed
health check, the actual returned one-operation, 1800-second approval and the
operator's explicit attendance/usable Download confirmation. Those effects
and closure belong to the linked run report; physical SSH remains unproved.

Past-failure checklist application:

- **ABI / SEMANTIC / ROUTE:** actual signed split executables, root-directory
  mode, account/privilege behavior, standard client binding and real package
  execution are checked; startup readiness is not session/lifetime proof.
- **WIRE / IO / PERSIST:** separate authenticated format, same-boot join,
  complete raw before parsing, finite clock domain, failed/partial captures
  and one-call no-replay are exercised through the actual producer/consumer.
- **ARTIFACT / AUDIT:** fixed member/type/mode/key closure and fresh candidate
  provenance are separate from retained preliminary evidence and current
  checker provenance. Exact final Image/loader/AP checks pass.
- **HOST / RETURN:** current executable and route semantics are bound;
  candidate-only SSH files are not original-A recovery prerequisites. No
  uncertainty creates another transfer or client invocation.
- **DISPLAY:** no display path changed or claimed.

Private discussion/source evidence is under
`workspace/private/outputs/s22plus-ml022-next-discussion-20261104-1/`.
Candidate, tests and independent review are under
`workspace/private/outputs/s22plus-mainline-ml023-debian-ssh-h0-20261104-1/`.
A90 and S20+ were not accessed; unrelated existing work is preserved.

## External-model accounting

All four advisory calls have private before/after usage and token records.
Claude reported 4 uncached input tokens, 8,986 cache-creation input tokens and
25,875 output tokens, including 15,104 thinking tokens. Its reported list-price
equivalent totals USD 0.589404, not a subscription charge. Account five-hour
usage snapshots moved from 5% to 8%; these rounded account-wide readings are
not exact attribution to these calls.

Argon reported 31,547 input and 20,259 output tokens, including 12,750 thinking
tokens, totaling 51,806. Fresh-process weekly remaining readings were 87.76%,
86.77% and 85.76%. An earlier same-process quota display was stale and is
retained with that label. The first Argon response completed successfully but
its CLI did not exit; the bounded wrapper stopped its own process after the
post-result grace period. The second call exited normally. There was no
inference replay or fallback. Provider quota, tokens, list-price equivalents
and unavailable actual billing remain separate.
