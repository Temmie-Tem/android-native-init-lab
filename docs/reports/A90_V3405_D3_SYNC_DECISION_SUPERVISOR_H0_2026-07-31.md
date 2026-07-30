# A90 V3405 D3 Sync-Decision Supervisor H0 Closure

- Date: `2026-07-31`
- Scope: H0 implementation, static/fault validation, independent safety review,
  private artifact build, and bounded D0 read-only inventory/health
- Decision: `A90_D3_V3405_RETURN_DIAGNOSTIC_HOST_PASS`
- Live adoption: blocked
- Device write, reboot, handoff, or flash in this unit: none

## Selected question

V3404 proved that `switch_root` made Debian sysvinit PID1 and ran firstboot.
Its 120-second return child entered `/bin/sync`, while execution of
`/sbin/reboot` was not observed. This supports, but does not prove, a global
sync stall on the loop-ext4-over-SD-ext4 stack.

V3405 turns the next run into a decision experiment:

- execute the one global `sync()` only in a diagnostic child;
- bound that child from a separate resident supervisor;
- after timeout, sample the sync child's `/proc/<pid>/stat` and
  `/proc/<pid>/wchan`;
- write the sample to pmsg without making it a recovery prerequisite; and
- make the final recovery edge a pre-opened sysrq `b` write with no preceding
  sync, exec, file open, proc read, or marker write.

It intentionally does not replace the experiment with `syncfs()`. A
rootfs-local flush still traverses the same loop and SD writeback path and can
stall.

## A90 D0 inventory

The exact healthy A90 V2321 target reported:

```text
kernel.sysrq=1
/proc/sysrq-trigger=present
/proc/devices: pmsg major=251
ramoops platform driver/device=bound
pmsg_size=262144
pstore filesystem=supported, not mounted
/dev/pmsg0=absent
/dev/kmsg=absent
```

The absent pmsg node and present registered major are separate facts. The
supervisor may create only `/dev/pmsg0` after it has already pre-opened sysrq;
it verifies that an existing node is the exact character major/minor or fails.
The arm parent retains its own pre-opened sysrq FD until the supervisor has
opened pmsg and successfully written the `phase=armed` positive control.

This proves write-side prerequisites, not reboot retention. A later live
observer must recover the current run's retained `phase=armed` marker before
any missing later marker is interpreted.

The final read-only health check returned exact
`v2321-usb-clean-identity-rodata`, `BOOT OK`, and `selftest fail=0`.

## Supervisor contract

The versioned static AArch64 helper is:

`workspace/public/src/scripts/server-distro/a90_d3_return_supervisor_v3405.c`

Its production sequence is:

1. The short arm process opens sysrq and locks its resident memory.
2. It forks the supervisor and waits on one absolute five-second ready
   deadline. EINTR does not renew the deadline.
3. The supervisor pre-opens sysrq, creates/validates and opens pmsg, optionally
   opens kmsg, locks memory, and writes `phase=armed`.
4. Only after the positive-control write succeeds does the arm process print
   the supervisor PID and allow firstboot to continue.
5. At 120 seconds the supervisor forks the only child containing `sync()`.
6. The supervisor waits on one absolute 20-second deadline.
7. On timeout it forks an evidence child. That child alone opens and reads
   procfs and attempts the nonblocking pmsg marker. The parent waits at most
   one second.
8. The parent then writes exactly `b\n` to its pre-opened sysrq FD. Its final
   path performs no marker write or filesystem access.
9. If sync returns, a separate reboot child invokes the reboot syscall. The
   supervisor waits at most five seconds; every syscall return, child failure,
   or timeout falls back to the same pre-opened `b` write.

No path emits sysrq `s`. There is no `syncfs`, `fsync`, late exec, shell, or
external reboot binary in the helper.

The firstboot contract arms the helper before `mkdir`, NCM configuration,
rootfs marker writes, key generation, or Dropbear. Canonical IPv4, peer,
port, timing, run ID, private output path, and debugfs source/target grammar
are fail-closed.

## Base-image and ownership correction

The first builder draft copied the old extracted rootfs directory into
`mke2fs -d`. That was rejected before artifact build: the directory was
created in an earlier fakeroot session and now appears as host UID/GID
`1000:1000`, while the authenticated clean ext4 contains the required Debian
inode ownership such as root UID/GID for init, inittab, and `/root`.

The accepted builder instead binds:

- the exact absolute, non-symlink clean ext4 path;
- exact size `2147483648`;
- base image SHA256
  `16c504a8b1860fcc56272140b48d27a015bab1748b6c6be10fdb958bcdd7d749`;
- the exact accepted summary SHA256;
- critical path type, mode, UID, and GID; and
- absence of runtime state, host keys, authorized keys, and Wi-Fi credential
  files.

It clones that exact image before mutation and overlays only:

```text
/usr/local/sbin/a90-d3-return-supervisor-v3405
/etc/a90-d3-firstboot
/etc/a90-server-distro-stage
```

Each target is read back through debugfs and must match source bytes, SHA256,
size, regular-file mode, UID 0, and GID 0. The builder then verifies label
`A90D3V3405`, `e2fsck -fn=0`, unchanged critical base ownership, and unchanged
base-image SHA. A failure leaves only an absent-only private partial run and
never publishes a PASS summary.

## Validation and independent review

The final execution-critical source identities are:

```text
supervisor C  dc4fae13984d458f512d9b5f88239c7e9b68cfcff29ec64d8857474a1a49e8bb
builder       fec5e2582eae5942b209c7517ebe952127e83257fe2e98e34690dc4154880d31
tests         295c3dbec8295f3ef8fd98310a0b631af44ead3be78b49a2d6171d4d93ef924b
```

Validation passed:

- focused supervisor/builder suite: `17/17`;
- related D3/rootfs suites: `8/8`;
- Python `py_compile`;
- AArch64 static compile with `-Wall -Wextra -Werror -fanalyzer`;
- static ELF file inspection with no dynamic section; and
- small-ext4 mutation testing, including the mode-field fault that would have
  produced an illegal FIFO.

The initial independent review correctly returned NO-GO for direct reboot in
the supervisor, synchronous proc/pmsg work before sysrq, unvalidated shell
inputs, weak base binding, resettable ready timeouts, and comment-foolable
source checks. All were corrected.

The final independent review returned:

`GO — H0 artifact-build closure only`

One first build attempt, run ID ending `01`, failed before image clone because
the empty overlay lacked its `/etc` parent. It produced no image and no PASS
summary. The private mode-0700 partial run is retained and will not be reused.
The minimal parent-directory fix and an actually empty-overlay regression
test passed a separate independent delta review.

## Private artifact

Fresh run `a90-v3405-d3-return-diagnostic-20260731-02` passed the host builder.
The private artifact is:

```text
size=2147483648
mode=0600
label=A90D3V3405
sha256=96cb77e7be9adae5a5964b8a5a3e849dd949216eb902286dbdaf253159965b86
filesystem_state=clean
e2fsck_read_only_rc=0
```

The embedded static supervisor is mode `0755`, UID/GID `0:0`, and SHA256
`d52f09dc0ed1622550d9bc1ea0b486d4e7ec874b99f9ea7cccae3d3822f2fb4c`.
The firstboot and stage file hashes also match the private PASS summary.

No artifact was staged to the device.

## Remaining live gates

This closure is not an F1 manifest and grants no live authority.

Before another A90 F1:

1. implement a retained-pstore observer that requires the current run's exact
   `phase=armed` positive control before interpreting later phases;
2. reselect the candidate NCM netdev under the manifest-bound A90 USB parent
   after re-enumeration and bind/activate the host profile by stable
   attributes rather than a prior transient interface name;
3. bind the exact V3405 image and exact V2321 rollback into a new immutable
   manifest and unchanged Process v2 machinery;
4. independently review any changed observer/recovery machinery; and
5. run fresh preflight and obtain a fresh exact approval.

V3402/V3404 approvals and all prior run IDs remain consumed and non-reusable.
