# S22+ one USB HTTPS APT transaction V1

Status: **REVIEW_GATED_CAPABILITY**. This specialization selects only
`post-autoboot-p462-apt-v1`, namespace `p463`, `debian-autoboot-v1` and the
existing V3 owner on `SM-S906N/g0q/S906NKSS7FYG8`. H0 implementation and review
do not open a grant or renew P462's consumed operation or attendance.

## Owner and clock

Inherit the [Download return](S22PLUS_DEBIAN_DOWNLOAD_RETURN_V1.md) two-boot,
four-lifetime owner, fixed cron lifecycle, one ordinary reboot, checked final
SysV Download/original-A return, physical fallback and exact target isolation.
Use one fresh N and one original A, 300000 ms absolute device deadline per
boot, two 360-second host windows and one finite attended operation within
3600 seconds. Fresh physical baseline M must be 38. Qualified source-bound
artifacts, independent review, current health and demonstrated usable physical
Download recovery remain required. No extra boot, unattended execution or
failure-recovery claim is added.

Before cron is armed in each boot, the same pinned SSH connection may publish
one fixed numeric UTC request bound to the current run, phase and kernel boot.
An exclusive RAM intent precedes publication. The sequential observer alone
claims the request and sets CLOCK_REALTIME once, then records readback and an
authenticated runtime event. The original BOOTTIME deadlines never change.
No RTC, hwclock, persistent clock configuration or time service is permitted.
Host readiness, dispatch and readback remain within the original observation
window and a 30-second freshness bound; the device consumes the request within
20 seconds and checks readback within one second of the requested time.
An uncertain reply permits only the fixed status read, never another request.

## USB sharing and acquisition

The host may create one NetworkManager `save no` Ethernet profile with the
derived task UUID, exact candidate name, USB interface and MAC, fixed private
address, `ipv4.method=shared`, `never-default=yes`, IPv6 disabled and
autoconnect disabled. This explicitly includes NetworkManager-managed
temporary DNS/DHCP, NAT and host IPv4 forwarding needed for that share.
Reject another active owner, a matching foreign Ethernet profile or an
overlapping active route/interface/profile subnet before activation. The host
default routes and resolver must remain unchanged. The second boot may only
rebind and activate this same checked UUID. No bridge, new proxy, global
firewall flush or stale global forwarding restoration is authorized.

The guest adds its fixed USB default route once in phase 1 and binds a
read-only RAM resolver file over the initially empty `/etc/resolv.conf`.
Successful acquisition/install removes that overlay; failure retains it only
for the existing boot. It changes no persistent network file. All APT lists,
cache, extended state, configuration, logs and temporary files are in a
separate RAM directory. The private owner/HMAC directory remains private.
APT_CONFIG is applied before config parts/main, preventing installed hooks
from being inherited. Force IPv4, zero acquisition retries, peer/hostname
verification, signature verification, Check-Date and Check-Valid-Until remain
enabled. There is no unauthenticated, trust, date or TLS bypass.

One unprivileged `_apt` update verifies the retained Debian keyring and exact
signed trixie metadata. One unprivileged download selects only Debian arm64
`tree=2.2.1-1`, 57900 bytes, SHA-256
`5cbe57d830e015571ee86d8b64177978371fca0c5c4ce555ba40c129ee9b87a0`.
The exact acquired metadata and archive hashes are sealed in
`s22plus_debian_apt_files_v1.json`. Every acquisition process runs with the
retained `_apt` UID/GID and no-new-privileges; no root fallback is permitted.
After children settle, root seals readable metadata/archive files and their
ancestors. A fixed simulation must show exactly one new tree package and no
upgrade, removal or additional dependency. Repository drift stops before the
installation intent. The existing libc satisfies tree's only dependency.
The inspected archive has no maintainer scripts, conffiles, links or triggers,
and its payload activates no installed file trigger.

## One transaction and exact state

After the first 120-second service window, and after acquisition and exact
plan validation, one authenticated intent permits only the pinned apt-get
`--no-download --no-remove --no-install-recommends install tree=2.2.1-1`.
This is one APT transaction, including its ordinary dpkg unpack/configure
children, rather than a promise of one dpkg invocation. Use-Pty is false;
the fixed process group, output bounds and child settlement remain required.
The entire acquisition/package workload has at most 90000 ms inside the
original boot deadline. A userspace deadline does not stop an unresponsive
kernel or establish failure recovery.

The sealed prestate includes all P462 hello files and its exact two database
files. The successful state retains 52 hello entries, adds seven tree payload
files, one documentation directory and two dpkg info files, and replaces only
status/status-old: 64 declared rows total. Status contains tree installed;
status-old contains the measured tree-unpacked state. Every other package
paragraph and immutable root row remains exact. Ordinary parent metadata and
the package manager's fixed transaction staging, locks, numbered updates,
temporary control/status/info files, `.dpkg-new`/`.dpkg-tmp`, reassemble check
and in-transaction error unwind are included. They are not additional parent
repair, cleanup or replay authority. No other-partition write is added.

Success requires empty-output audit/verify, the exact full state, no updates
or transaction remnants, the pinned tree command's exact output on a fixed
RAM directory, checked synchronization and an authenticated completion record.
Both second-boot protected admissions require that record and the ordinary
reboot intent, clean ext4, sealed mount progression and exact retained state.
The second boot only audits, verifies and runs tree; it never acquires or
installs again. No failed or live partial state is learned as an expectation.

## Return, failure and qualification

Original A does not undo package changes. An uncertain transaction stops the
experiment, may leave partial native_data state and permits only the existing
attended original-A recovery and health procedure. It never permits package
retry, removal, configure-all, repair, reinstall or filesystem repair. Later
health or a clean superblock does not grant replay or accept partial state.

Host sharing cleanup must not precede or consume the automatic Download/A
window. After A completion, or after normal progress has stopped, best-effort
cleanup checks the full owned tuple, deactivates that UUID if active, deletes
it and verifies profile/activation absence. Recovery remains independent of
this host cleanup. Its receipt proves only those NetworkManager observations;
it does not independently prove every managed firewall/sysctl/DNS resource
was retired. A cleanup failure is reported without changing another profile.

Only P463 final/recovery Android health may replace one failed health bracket
after the exact same-target root-read disappearance witnessed in P462. The
original raw attempt is retained; seven entirely fresh captures must satisfy
the same inventory/topology/property/root/archive checks within the original
260-second bracket budget, clipped by the owner. Complete prior boot identity
must agree. Partial property output alone is not a retry trigger. Wrong target,
ambiguous inventory, timeout, capture corruption and arbitrary diagnostics
remain strict failures. GPT/statfs and device controls are never repeated by
this reobservation; initial and after-storage health remain strict.

Qualification covers real ARM64 HTTPS/signature acquisition and APT effects,
the full two-boot producer/consumer path, clock binding and one-shot behavior,
metadata/archive/plan rejection, installer/child settlement failure, exact
pre/poststate rejection, host share ownership/cleanup and P462 health failure
bytes. H0 network/hardware substitutions do not prove physical USB internet,
package persistence, final Android health or universal recovery. Review binds
the final execution closure; historical artifacts and grants keep their pins.
