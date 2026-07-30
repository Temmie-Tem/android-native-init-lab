# A90 V3404 D3 Switchroot No-Proof F1 Closed

- Date: `2026-07-31`
- Run: `a90-v3404-debian-f1-20260731-01`
- Manifest SHA256:
  `9efd0a72a9927c6281647bdda457195e2f3bc0ba0826049fa01d9e016f9b4777`
- Decision: `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`
- Final device state: exact V2321, `selftest fail=0`, pstore entries zero

## Live result

The attended run staged one exact 2 GiB keyed rootfs, completed one checked
V3404 boot transfer, and observed exact candidate version, build, and health.
The single handoff passed strict display cleanup, copied the immutable source
to the absent-only work image, verified source and copy hashes, attached the
loop device, mounted the rootfs, moved proc/sys, prepared dev nodes, and
reached:

```text
A90D3B exec_switch_root_now ... init=/sbin/init console=reuse-stdio
SELinux: Could not open policy file ...
```

This is strong evidence that BusyBox reached the Debian `/sbin/init` exec
boundary. It is not the run's acceptance proof: no Debian marker or
`/proc/1/exe=/usr/sbin/init` observation was received over the bounded SSH
observer. The device also did not return automatically within the bounded
candidate-return observation. The operator-observed HUD stop and screen-off
are consistent with the successful display-owner cleanup.

The operator then manually rebooted to the exact V3404 native-init candidate.
The checked recovery path performed one exact V2321 boot write and readback.
The original orchestrator stopped after that proven transition because USB
re-enumeration preserved the exact A90 by-id identity but changed the transient
`ttyACM` realpath. The rollback was never repeated.

## Post-rollback closure

A dedicated no-transfer closure helper was added for this one narrow state:

`workspace/public/src/scripts/server-distro/a90_f1_postrollback_realpath_closure.py`

It has no transfer, flash, reboot, recovery, or partition primitive. It binds:

- the original immutable manifest, consumed approval, journal, observation,
  exact rollback raw log, and one-transfer history;
- the same USB serial digest and exact by-id device despite transient realpath
  drift;
- one localhost listener inode and PID to the managed serial bridge metadata,
  process argv, exact device, and current realpath;
- private mode-`0600` metadata, capture, and stderr files;
- an externally supplied independently reviewed helper SHA before D0 and
  before every local publication; and
- every existing timeline event to its source journal timestamp.

Three independent review rounds returned `NO_GO` while those bindings were
incomplete. Final independent review returned `GO` for helper SHA256
`a7ebd40503517b465f870a472d83886a1f1f1edee4d481ba8d460d1e24ceaeda`.
The focused suite passed `14/14`.

The reviewed helper then performed only exact framed `version`, `status`, and
`selftest` reads. It appended `rollback-boot-ready`, `health-verified`, and
`closed`, without invoking rollback. The final journal has contiguous
sequences `0..17`; candidate, handoff, and rollback starts each occur once.
The structured result records candidate/rollback counts `1/1`, no candidate
replay, no rollback reinvocation, restored V2321 health, and the canonical
eight-event timeline.

## Rootfs lineage check

The private 2026-07-03 successful keyed image is no longer retained, so a
direct old-image/new-image byte comparison is unavailable. The retained
public and private evidence nevertheless rejects the missing-firstboot
hypothesis:

- current source and keyed images contain byte-identical `/etc/inittab`,
  `/etc/a90-d3-firstboot`, and `/usr/sbin/init`;
- inittab contains the exact
  `si::sysinit:/etc/a90-d3-firstboot` hook, and firstboot is mode `0755`;
- firstboot still arms the 120-second reboot before networking and contains
  the marker and Dropbear paths;
- the current init binary SHA256 is
  `402c5e6daeae7f19f01040ba17657f43c14ef6570316ec34a06c6bb87ab923f2`;
- it comes from the exact `sysvinit-core 3.06-4` archive SHA256
  `59bedbd7fd5d6e918bb485f10571fe4bd48468f13dc6c629ab4e6d8d4ebe87dd`
  recorded by the 2026-07-03 successful lineage; and
- an isolated host PID-namespace execution of the current rootfs created the
  D3 marker, recorded `autoreboot_sec=120`, armed the reboot child, and ran the
  Dropbear setup path.

The clean current rootfs does contain regular `/dev/*` placeholders whereas
the original D3A report recorded a character `/dev/null`. This run's native
handoff replaced console, tty, ptmx, null, zero, random, and urandom and
reported `dev_nodes=prepared` before exec, so that metadata difference is not
yet a demonstrated cause.

The 2026-07-03 live pass remains the decisive proof that A90 can complete the
same switch-root mechanism and make sysvinit PID1. The current failure is
therefore an A90 live-runtime regression or unobserved firstboot failure, not
evidence that the mechanism or firstboot payload is absent. Before another F1,
use H0 and, if needed, bounded D0 postmortem work to distinguish the new
absent-only work copy and display-cleanup state and to add a durable pre-init
watchdog/trace boundary.

## Safety disposition

- Candidate transfer count: `1`
- Rollback transfer count: `1`
- Candidate replay: `false`
- Rollback reinvoked during closure: `false`
- Debian PID1 proven in this run: `false`
- Final health restored: `true`
- Internal userdata: untouched
- Run and approvals: consumed and non-reusable
- Current live authority: none

Raw logs, serial identity, health response hashes, journals, and structured
results remain under `workspace/private/` and are not committed.
