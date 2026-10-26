# S22+ one offline Debian package V1

Status: **REVIEW_GATED_CAPABILITY**. This specialization selects only
`post-autoboot-p461-package-v1`, namespace `p462`, `debian-autoboot-v1` and
the existing V3 owner on `SM-S906N/g0q/S906NKSS7FYG8`. Definition, H0 tests and
review do not open a device grant. Prior P461 actions remain consumed.

## Fixed transaction and inherited owner

Retain the [Download return specialization](S22PLUS_DEBIAN_DOWNLOAD_RETURN_V1.md),
including two Debian boots, four admitted native_data writable lifetimes,
the exact cron configuration lifecycle, one ordinary reboot and the final
checked SysV Download/original-A return. Use one fresh N and one original A,
the original 300000 ms absolute deadline per boot, two fixed 360-second host
windows and one finite attended operation within 3600 seconds. Current physical
baseline M must be 34. Exact target/health, qualified artifacts, source-bound
independent review and demonstrated usable physical Download recovery remain
required. This scope adds no boot, transfer, unattended run or failure-recovery
claim. The inherited stock Download initialization hazards remain applicable.

After the first 120-second service window, install only the already embedded
`/usr/local/lib/lab-offline/hello.deb`: Debian `hello` version `2.10-5`, arm64,
52660 bytes, SHA-256
`7a917c7f44fbd3373dff0f35a0b6bdf8ef564ff90579d8b130ff52fbf33fce1f`.
The retained signed Debian metadata and immutable root supply these bytes.
There is no package download, apt operation, dependency installation, upgrade,
removal, reinstallation, arbitrary package or caller-provided command.
The retained libc satisfies this package's dependency. Its control archive
contains no maintainer scripts, conffiles or trigger declarations. No installed
file trigger matches its payload; no service, alternatives, kernel, initramfs,
firmware or persistent service-policy change is selected.

The one fixed command is the pinned installed dpkg with
`--log=/run/s22-debian/package-dpkg.log --install` and that one archive.
The pinned dpkg-deb/dpkg-split and ordinary package-manager child work are part of this
single invocation. Environment, path and umask are fixed. Before the intent,
require the exact original status files, absent new package paths, empty dpkg
updates, absent temporary control/status files and a successful **empty-output**
`dpkg --audit`. Exit zero alone does not establish an empty audit.
An authenticated sequential intent precedes the install; no resume path may
dispatch it again. The package workload has at most 30000 ms within the
original boot deadline. Command output is bounded and kept in private RAM.
Userspace timeouts do not interrupt an unresponsive kernel or prove quiescence.

## Filesystem effects

The source declaration `s22plus_debian_package_files_v1.json` seals the exact
successful state: 49 package regular files, one new documentation directory,
two dpkg info files and replacements of only `var/lib/dpkg/status` and
`var/lib/dpkg/status-old`. It pins file contents, mode, owner, size and single
links; the new directory has its exact mode/owner and two links. Existing
parent-directory metadata changes caused by adding entries are expected.
Every other immutable root row retains its original comparison. The final
status contains exactly the additional installed hello paragraph; every other
package paragraph is unchanged, and status-old equals the original status.

Those 54 final paths are not the entire transient write set. Within this one
pinned dpkg invocation, ordinary transaction writes include its bounded
`var/lib/dpkg/updates/tmp.i` and numbered status journals, temporary control
directory `var/lib/dpkg/tmp.ci`, status/info replacement staging, lock-file
locking, the fixed `reassemble.deb` check/unlink (this archive is not split),
and `.dpkg-new`/`.dpkg-tmp` staging for the exact payload paths.
The package manager's own rename/unlink/error-unwind operations within that
same invocation are included. No parent-initiated retry, cleanup, rollback,
`--configure -a`, repair, removal or subsequent package operation follows an
uncertain outcome. The successful final state must contain no leftover
transaction path or undeclared file. No write to another partition, raw block
writer, mount change, formatter or filesystem repair is added.

## Completion and ordinary reboot

Success requires the one installer and its child work to settle successfully,
empty-output audit and `dpkg --verify hello`, full exact post-state checks,
empty updates/absent transaction remnants before and after installation,
and execution of the pinned new
`/usr/bin/hello --greeting=S22_PACKAGE_FUNCTION` with exactly that line and
successful exit. Checked synchronization and re-verification precede the
authenticated package-complete record. Service COMPLETE and the ordinary
reboot require that record. The package remains installed after success.

Both second-boot protected admissions require the authenticated first runtime
chain through package completion and the ordinary-reboot intent. They accept
only the 52 exact new entries plus the two exact database replacements.
The first boot continues to require the original database and absent new
paths. Both retain clean ext4, sealed mount-count progression, complete root
inventory and rejection of every unknown/missing/changed/linked/partial row.
No post-install state is learned from a failed run or from the live device.

The second boot runs only the same fixed empty-output audit/verify and hello
function, rechecks the exact post-state and appends its own authenticated
verification intent/completion. It never installs again. Host evidence joins
the two source-bound runtime chains, distinct boot identities, protected
admissions and exact first-pair retention. Installation, function, persistence,
normal Download/A return and final Android health remain separate facts.

## Failure and qualification

Failure may leave partial package data, an intermediate dpkg database or
transaction files on native_data. Original-A restoration changes boot and
does not undo them. Failed/uncertain package work stops the experiment and
retains the original attended physical Download/A and health owner. No later
read, Android health or clean superblock permits replay, repairs or acceptance
of partial package state. Subsequent Debian admission requires a separately
reviewed prospective scope if the root no longer matches either sealed state.

Qualification covers actual ARM64 dpkg and hello, two production VM boots,
the real producer/consumer grammar, missing/changed/linked package and database
rows, unknown transaction remnants, installer failure/timeout, failed output,
failed sync and duplicate intent. The final physical-format artifact must
match the reviewed execution-critical source closure. H0 hardware substitutions
and successful-state measurements do not prove physical package retention or
universal failure recovery. No historical approval or binding is repinned.
