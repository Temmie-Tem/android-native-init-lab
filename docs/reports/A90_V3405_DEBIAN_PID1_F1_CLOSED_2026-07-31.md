# A90 V3405 Live Debian PID1 Evidence and F1 Closure

Date: 2026-07-31

Status: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

## Scope

Run `a90-v3405-debian-f1-20260731-01` consumed one exact F1 approval and one
exact operator-attended continuation. It authorized one V3404 boot candidate,
one V3405 Debian handoff, and the mandatory exact V2321 rollback on the
manifest-bound A90 only.

No command was sent to the separately connected S22+. No non-boot partition,
internal userdata, or additional partition authority was used.

## Immutable inputs

The final manifest SHA256 is:

```text
9db8e9870cbce47d98ac2efbdf363eb42efc1db48874bca58231b632506eff97
```

Host inspection reported zero contract issues. The fresh private transaction
and staging directories were absent before execution. The 2 GiB keyed rootfs
staged once through the topology-bound NCM path, was rehashed on the device,
and was published through the reviewed no-clobber contract.

## Candidate and handoff

The runner durably recorded candidate intent before invoking the checked
boot-only path. The candidate transferred once, returned its exact version and
build, and passed selftest with `fail=0`.

The attended pre-handoff gates then proved:

- exact candidate health;
- the manifest-bound A90 bridge and NCM topology;
- empty pre-handoff pstore;
- the immutable staged source at its exact size and SHA256; and
- one remaining handoff attempt.

The single handoff proved all four source identities:

```text
source_sha phase=initial expected_sha_match=1
source_sha phase=post-display-cleanup expected_sha_match=1
source_sha phase=work-copy expected_sha_match=1
source_sha phase=post-copy-source expected_sha_match=1
```

It also returned the exact `exec_switch_root_now` boundary. No handoff retry
or candidate replay occurred.

## Live Debian PID1 evidence

USB-local SSH succeeded on its second bounded attempt. Its private evidence
proves:

```text
A90D3_MARKER
pid1_comm=init
proc1_exe=<distro init executable>
dropbear_started=1
```

This is direct live evidence that `switch_root` replaced PID1 with the Debian
init. It is not a chroot inference.

The V3405 no-sync supervisor also returned to the exact healthy native
candidate before the from-native rollback gate passed. This bypasses the
V3404 global-`sync` return failure. The first candidate-return channel check,
however, failed on a missing `A90P1 END` frame after exact bridge selection.
Because the observer performs retained-pmsg collection only after that check,
no retained-pmsg record was collected.

The structured observation therefore correctly remained atomic
`observation-no-proof`: its live handoff and SSH subproofs are affirmative,
but its candidate-return and retained-pmsg closure was incomplete. The
structured result does not promote those subproofs to F1 PASS.

## Rollback and recovery

Rollback authority was already active when candidate intent began. After the
observation stopped, the runner reopened the consumed approval and selected
the exact A90 native bridge. The exact healthy candidate gate passed, then
V2321 transferred once.

The first post-rollback health read met serial-menu interleaving: the framed
`hide` input was corrupted before command parsing. Durable state already
proved `rollback-flashed`, so health-only recovery did not reinvoke rollback.
It then proved:

```text
exact V2321 version and build
selftest fail=0
pstore entries=0
```

The canonical transaction counts are:

```text
candidate_transfer_count=1
candidate_replay=false
rollback_transfer_count=1
final_health_restored=true
```

The canonical eight-event timeline is complete.

## Evidence identities

Private structured evidence remains mode `0600`:

```text
result.json       12d53024326e03d261e340073a59c4aa8adcd5be0bdfc9f1dcca8725c7ac9426
observation.json  91730c7d08740f15cdb4dd8d4e070d1b43ce11888d7bfe51f8f642c402c93bba
timeline.json     8efa6ae3e87a885c05ea75641e255947bb5459076690b1b6055c1f0483791325
```

The journal contains exactly one candidate start/completion, one handoff
intent, one observation-no-proof record, one rollback start/completion, one
health verification, and one close.

## Disposition

The mechanism-level result is stronger than V3404: live Debian PID1, Dropbear,
and automatic healthy native return are now directly evidenced. The formal F1
verdict remains no-proof because the retained-pmsg observer closure was not
completed.

The next work is H0 analysis of return-channel framing and retained-pmsg
collection ordering. This run, its F1 approval, and its attended continuation
are closed and non-reusable. No A90 live authority remains.
