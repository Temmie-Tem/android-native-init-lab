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

Before another F1, add durable markers immediately before and after the sync
boundary, avoid an unbounded global-sync dependency in the recovery timer, and
record reboot and sysrq fallback results. Keep recovery independent of SSH.

## Disposition

- Debian sysvinit PID1 in V3404: technically proven.
- Firstboot execution: proven.
- Dropbear start: proven.
- Live SSH contract: failed because the host candidate NCM profile was absent.
- Timer arm and 120-second wake: proven.
- Automatic reboot syscall: unproved.
- Original F1 journal/result: unchanged and still formally closed no-proof.
- Candidate/rollback transfers: still exactly `1/1`; no replay.
- Final device health: exact V2321, healthy.
- Device work image and host mode-`0600` preservation image: retained.
- New live authority: none.

Raw identities, host logs, the extracted filesystem, and structured D0
analysis remain under `workspace/private/` and are not committed.
