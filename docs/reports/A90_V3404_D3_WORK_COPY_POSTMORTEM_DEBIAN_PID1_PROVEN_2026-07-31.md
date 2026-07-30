# A90 V3404 D3 Work-Copy Postmortem: Debian PID1 Proven

- Date: `2026-07-31`
- Run: `a90-v3404-debian-f1-20260731-01`
- Device action: bounded D0 read-only preservation and offline inspection
- Technical verdict: `PASS_TECHNICAL_D3_SWITCH_ROOT_DEBIAN_PID1_POSTMORTEM`
- Formal F1 verdict remains:
  `NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK`

## Preservation

The exact A90 returned healthy on V2321 with `selftest fail=0` and zero pstore
entries. The retained D3 work image existed as one regular 2 GiB file and was
not mounted through a loop device or at the old distro-root path. Its
device-side SHA256 was:

```text
ef45a234db2b3a28ecd8bfddef5932ba87298a266247f304f288712aa6e36d02
```

One initial sender invocation failed before opening the image because it named
a nonexistent helper path. It produced no listener and no partial host file;
that exact command was not repeated. A corrected invocation used the
read-only selected helper and one USB-local NCM connection. The host received
exactly `2147483648` bytes, reproduced the device SHA256, and published the
private preservation image with mode `0600`.

The extraction did not mount, write, rename, or delete any device file. The
device-side work image remains present, so absent-only handoff still refuses
another run rather than destroying this evidence. The existing host NCM
profile was rebound only to the exact interface under the same USB parent;
the device's NCM configuration and USB composition were unchanged. One
attended UI-only `hide` was used after the automatic menu rejected the first
D0 command as busy.

## Offline proof

The immutable keyed source SHA256 was `6dbc2e7d...`; the preserved work image
SHA256 is `ef45a234...`. The source has mount count `0` and journal sequence
`1`. The work image records mount count `1`, last-mounted path `/`, and journal
sequence `2`.

The work image contains new runtime state that was absent from the keyed
source:

```text
/run/a90-d3-autoreboot.pid
/run/a90-d3-marker
/run/a90-d3-dropbearkey.log
/run/a90-d3-dropbear.log
/run/a90-d3-dropbear.pid
```

The marker records:

```text
pid1_comm=init
proc1_exe=/usr/sbin/init
autoreboot_sec=120
dropbear_started=1
```

`/etc/inittab` still contains
`si::sysinit:/etc/a90-d3-firstboot`; firstboot is executable mode `0755`.
The generated Dropbear host key exists, the Dropbear PID file exists, and its
log records a successful background start.

This state cannot be inherited from the clean source: the live pre-handoff
gate proved the work path absent, V3404 copied and hash-verified the clean
source into that path, and only then mounted the work copy read-write. Combined
with the retained live `exec_switch_root_now ... init=/sbin/init` boundary,
`proc1_exe=/usr/sbin/init` proves that this V3404 handoff did complete
`switch_root`, made Debian sysvinit PID1, and ran firstboot.

The sysvinit SELinux missing-policy line is therefore a warning on this path,
not the stopping boundary.

## SSH observer failure

The live observer made nine SSH attempts and received connection timeouts.
The work image now proves that Dropbear started, so the timeout did not mean
that Debian PID1 or firstboot was absent.

Private host logs provide the matching host-side cause. Candidate boot
re-enumerated USB NCM under a new transient interface identity. NetworkManager
attached a default DHCP profile, repeatedly failed address configuration, and
never installed the required static USB-local host address during the
observation window. The versioned static profile remained bound to the prior
pre-flash interface. This fully explains the SSH timeouts without a Debian or
Dropbear failure.

A successor must reselect the NCM interface under the manifest-bound A90 USB
parent and activate the fixed host profile after candidate re-enumeration,
before handoff. Because this changes F1 observer machinery, it requires the
normal focused independent review.

## Automatic-return boundary

The automatic-return child was armed. Runtime access times on the work image
show:

```text
/bin/sleep  10:49:51
/bin/sync   10:51:51
```

The exact 120-second delta proves that the timer child woke and entered the
global `sync`. The `/sbin/reboot` target executable retains its source access
time, and utmp/wtmp contain boot and runlevel entries but no shutdown record.
Thus reboot execution is not proven.

The narrowest supported boundary is:

```text
sleep 120 -> entered global sync -> [unresolved] -> reboot exec not observed
```

The leading hypothesis is that global `sync` did not return on the
loop-backed ext4 image stored on the outer SD ext4 filesystem. That hypothesis
is not yet proven; a signal or another failure immediately after `sync`
remains possible. A read-only `e2fsck -fn` skipped journal recovery and found
free-block and free-inode counters behind its full scan, so the original
preservation image must not be repaired in place.

An ordinary userspace timeout around `sync` would not close this hazard. A
task blocked in uninterruptible I/O sleep cannot be recovered by a signal or
`SIGKILL`; the recovery edge must be owned by another execution context that
does not enter the same writeback path.

## Reboot executable closure

Offline inspection of the preserved work image excludes a missing or
filesystem-level broken reboot executable:

- `/sbin/reboot` is the expected relative link to `halt`;
- `/sbin/halt` is executable mode `0755` and is an AArch64 PIE executable;
- its ELF interpreter and required `libc.so.6` are present in the image; and
- the link targets and loader dependencies all resolve within the Debian root.

This does not prove that the reboot program or reboot syscall ran. It removes
the proposed `127`/missing-command branch and leaves the bracket at either an
unreturned `sync` or a later reboot/fallback failure. The unchanged halt
access time remains supporting evidence for the former, not standalone proof.

## Recovery-backstop inventory

One bounded connected D0 read-only inventory was run against the exact healthy
V2321 target. It made no device write, created no node, opened no watchdog, and
ended with `version`, `status`, and `selftest fail=0`.

The current kernel reports:

```text
CONFIG_WATCHDOG=y
CONFIG_WATCHDOG_CORE=y
# CONFIG_WATCHDOG_NOWAYOUT is not set
# CONFIG_WATCHDOG_SYSFS is not set
CONFIG_SOFT_WATCHDOG=y
CONFIG_QCOM_WATCHDOG_V2=y
kernel.sysrq=1
```

The Qualcomm hardware watchdog is present and enabled. The
`qcom,msm-watchdog` platform device is bound to `msm_watchdog`, its disable
state is `0`, and the `msm_watchdog` kernel thread exists. Device-tree values
select a 9.36-second pet interval and an 11-second bark interval. The node has
no `qcom,userspace-watchdog` property and exposes only the one-way `disable`
attribute, not the userspace-pet attributes.

This distinction is load-bearing: the existing hardware watchdog is
kernel-owned and continuously pet by its kernel thread. It detects a wider
kernel/CPU liveness failure, but it is not a userspace lease that expires when
the Debian timer child blocks in `sync`. It therefore cannot be treated as the
automatic-return backstop without a separate kernel/device-tree design.

The one standard watchdog-class entry is virtual, has no native-init-created
`/dev/watchdog` or `/dev/watchdog0`, and has no optional watchdog sysfs
attributes because `CONFIG_WATCHDOG_SYSFS` is disabled. Together with the
built-in softdog symbols and the fact that the Qualcomm driver owns its
separate platform surface, this strongly attributes the standard entry to
softdog. Opening it could arm a reset, so identity/close/timeout semantics must
be closed host-side before any versioned helper creates or opens its device
node. This D0 deliberately did neither.

RTC0 is the bound `qcom,qpnp-rtc`, is marked wakeup-enabled, and has a readable
`/proc/driver/rtc`, but no `wakealarm` attribute and no `/dev/rtc*` node is
present in native-init. No alarm is armed. RTC wake is therefore not a
currently exposed automatic-return surface, and in any case is not by itself
an awake-system reset mechanism.

The sysrq fallback is enabled on the current kernel and
`/proc/sysrq-trigger` exists. It is useful only if a separate process reaches
it: the current script places `sync` before both `reboot -f` and the sysrq
write, so an unreturned sync makes both unreachable.

The public Android msm 4.14 `watchdog_v2.c` reference matches the observed
driver, thread, device-tree properties, sysfs surface, and pet/bark model. It
is supporting source evidence, not a claim that the public commit is
byte-identical to this Samsung kernel.

Before another F1:

1. remove global `sync` from the recovery-critical sequence;
2. use a rootfs-local durability operation with explicit before/after markers,
   while treating it as potentially blocking rather than killable;
3. arm a later, independent no-sync sysrq supervisor before that operation;
4. close softdog semantics and fault-test its helper host-side before deciding
   whether it should replace or supplement the supervisor; and
5. keep recovery independent of SSH and repair the host NCM profile after
   candidate re-enumeration.

This is a new recovery-hazard design. Any execution-critical implementation
and live use require the normal focused independent review and fresh
manifest/approval; this inventory grants no authority.

## Disposition

- Debian sysvinit PID1 in V3404: technically proven.
- Firstboot execution: proven.
- Dropbear start: proven.
- Live SSH contract: failed because the host candidate NCM profile was absent.
- Timer arm and 120-second wake: proven.
- Reboot executable and loader presence: proven.
- Automatic reboot syscall: unproved.
- Existing Qualcomm hardware watchdog: active but kernel-petted, not a
  userspace automatic-return lease.
- Sysrq fallback availability on V2321: present and enabled, but unreachable
  behind the current global sync if that call does not return.
- Watchdog/RTC write or open: none.
- Original F1 journal/result: unchanged and still formally closed no-proof.
- Candidate/rollback transfers: still exactly `1/1`; no replay.
- Final device health: exact V2321, healthy.
- Device work image and host mode-`0600` preservation image: retained.
- New live authority: none.

Raw identities, host logs, the extracted filesystem, and structured D0
analysis remain under `workspace/private/` and are not committed.
