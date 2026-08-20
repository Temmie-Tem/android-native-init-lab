# A90 H28 slow-input health reconciliation design — 2026-08-21

## Disposition

H0 design only. No current D0, D1, F1, reboot, recovery, physical-action,
partition, observer, or guard-removal authority is granted.

The H28 physical return reached exact V2321 Native, but its sole finalizer
observation stopped when normal serial input truncated `cmdv1 selftest` to
`cmdv1 selft`. The fixed physical action and its first observation are
consumed. Candidate and rollback replay remain forbidden. The active and H28
candidate guards remain exact and `41-recovery-closed.json` is absent.

## Objective

One fixed terminal-only capability may perform one fresh read-only V2321
health session using the already reviewed slow serial framing that addresses
this exact observer failure. It:

- binds the exact H28 manifest, original nine-record incident, both guards,
  physical-return intent, consumed first-observation intent, failed observer
  evidence, current independent review, and execution closure;
- sends no ADB, TWRP, reboot, flash, candidate, rollback, partition, physical,
  service-control, or arbitrary command;
- permits only exact read-only `version`, `selftest`, `status`, and boot-ID
  requests through `a90ctl --input-mode slow`;
- uses only the existing managed A90 Native ACM bridge and exact target/foreign
  endpoint inventory checks;
- publishes recovery closure only after exact V2321 `fail=0` health; and
- removes only the active guard after durable recovery-record readback. The
  H28 candidate guard remains consumed.

## Fixed interface and launch

The program accepts no caller path, run, device, serial, command, image,
outcome, timeout, input mode, or guard. Its sole process launch is fixed to
`/usr/bin/python3.14 -B -s -E`, repository-root cwd, and its absolute direct
non-symlink source path. A stdlib-only pre-import guard verifies interpreter,
flags, cwd, argv0, `sys.path`, and exact source/owner/adapter path identities
before importing local code. The same trusted-operator/system-Python boundary
and same-UID-host-compromise stop rule as the H28 physical-return capability
apply.

It exposes only:

### `prepare`

Host-only and write-free. It verifies every fixed input, exact absence of the
slow-observer sidecar and recovery record, active and candidate guards, current
review, and closure. It emits one approval token binding the capability, H28
run/manifest/terminal, both prior intent digests, current review, and closure.

### `execute --approval TOKEN`

After exact approval, it repeats all fixed checks under the current review
lease and durably publishes one no-replace
`10-slow-health-observation-intent.json`. That record consumes the sole slow
health session on success, timeout, command error, wrong health, or host loss.
A present slow intent without recovery closure always parks and never creates
another observer.

Only after durable intent readback may it create one fixed observer. The
observer performs:

1. exact complete USB inventory;
2. exact managed A90 bridge preflight;
3. `a90ctl --input-mode slow -- version`;
4. `a90ctl --input-mode slow -- selftest`;
5. `a90ctl --input-mode slow -- status`; and
6. `a90ctl --input-mode slow -- cat /proc/sys/kernel/random/boot_id`.

Each request is fixed, read-only, and may use only `a90ctl`'s bounded safe
retry inside the single overall health session. No caller can enable
`--retry-unsafe`, select another input mode, add a command, or start a second
session.

## Success and crash rules

Success requires exact V2321 version/build, structural command receipts,
selftest `fail=0`, status `pstore entries=0`, valid fresh boot ID, recovery
availability, exact A90 endpoint, and unchanged other-target disposition.
It publishes `41-recovery-closed.json` binding both prior intent digests, the
slow intent, failed normal-input observation as `NO_PROOF_TRANSPORT_TRUNCATION`,
current review/closure, canonical V2321 snapshot, both replay flags false, and
all device-effect/write/reboot counts zero.

- Before slow intent: no D0 session is authorized.
- After slow intent without recovery closure: park permanently; no new
  observer or slow intent.
- Observation failure or wrong health: keep both guards and publish no 41.
- Publication or readback failure: keep both guards.
- Exact 41 plus active guard present: park; never resume cleanup from a mutable
  snapshot.
- Exact 41 plus active absent and candidate present: report-only completion,
  with zero observation calls.
- Active removal occurs only after exact 41 readback, under the same review
  lease, and never removes the candidate guard.

## Review and activation

The complete execution closure and hostile corpus require one independent full
H0 review. A PASS qualifies capability bytes only. A fresh exact approval is
still required before its sole read-only session. Until both exist, do not send
another Native command and do not alter either guard.
