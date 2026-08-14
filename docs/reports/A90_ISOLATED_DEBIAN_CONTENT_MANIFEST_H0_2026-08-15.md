# A90 isolated-Debian minimal UFS content manifest (H0)

Date: 2026-08-15
Target: Samsung Galaxy A90 5G only
Tier: H0 host-only content/build work
Authority: none; no device, USB, device-network, installation, or UFS write

This report covers the separately versioned manifest
`isolated-debian-minimal-content-v2/userdata-content-manifest.json` and its
host-side builder. It follows the h14 JSON shape but uses
`a90-isolated-debian-ufs-content-manifest-v2`; the h14 manifest remains
unchanged and its historical consumers remain bound to h14.

The selected PID 1 is a new purpose-built static-PIE binary at
`/usr/local/libexec/a90-pid1`. It owns one exact workload child, has no
sysvinit/inittab/getty surface, and is entered only after the trusted
bootstrap supplies the fixed nonzero service identity. The historical
root-owned `/usr/sbin/init` is therefore replaced rather than assumed
compatible. The same tracked-source build produces the immutable forced probe
dispatcher and the selected bounded readiness workload.

## h14 19-file delta

| h14 path | disposition | v2 path | reason |
|---|---|---|---|
| `/usr/sbin/init` | replaced | `/usr/local/libexec/a90-pid1` | Historical sysvinit and root identity are not assumed compatible; the selected PID 1 is purpose-built, nonprivileged, consoleless, and owns only the selected workload child. |
| `/etc/inittab` | removed | — | No SysV init or init-script dispatch is in the content closure. |
| `/etc/a90-d3-firstboot` | removed | — | The immutable firstboot overlay is the rejected h14 mismatch and is not part of this rootfs. |
| `/etc/a90-appliance-stage` | replaced | `/etc/a90-appliance-stage` | Retains only a static public provenance marker for the read-only UFS appliance; it contains no firstboot, service, key, or network action. |
| `/etc/a90-server-distro-stage` | replaced | `/etc/a90-server-distro-stage` | Replaced the legacy D3/sysvinit/NCM instructions with a static H0 content marker naming native-bootstrap veth ownership and absent HUD/smoke paths. |
| `/etc/debian_version` | removed | — | Suite identification is build provenance, not a runtime dependency of the selected static content; removing it avoids retaining an unneeded base-rootfs file. |
| `/usr/bin/ip` | removed | — | The trusted native bootstrap owns veth and network setup; general `ip` is forbidden in Debian. |
| `/usr/bin/dropbearkey` | removed | — | Host-key generation is a trusted bootstrap operation; the rootfs cannot create, rotate, or read the per-boot server key. |
| `/usr/sbin/dropbear` | replaced | `/usr/sbin/dropbear` | Same service path, but only the separately built feature-removed Dropbear selected from the private pinned source is present. Its exact binary/source hashes are host-bound and remain H0 evidence only. |
| `/usr/local/bin/a90-dpublic-wifi-sta` | removed | — | Wi-Fi remains native-owned; Debian consumes only the already-configured veth peer. |
| `/usr/local/bin/a90-dpublic-smoke-httpd` | removed | — | Smoke HTTP is outside the selected server workload and is forbidden. |
| `/usr/local/bin/a90-dpublic-hud-intent` | removed | — | HUD intent is outside the headless content closure. |
| `/usr/local/bin/a90-dpublic-hud-presenter` | removed | — | Display/HUD presentation is outside this headless content unit. |
| `/usr/local/bin/a90-service-launch` | removed | — | The historical launcher could start the retired service set; the new PID 1 and workload have fixed argv and no general launcher. |
| `/usr/sbin/iw` | removed | — | Debian has no Wi-Fi administration path. |
| `/lib/aarch64-linux-gnu/libselinux.so.1` | removed | — | The selected static-PIE components and deferred static Dropbear build do not carry a SELinux runtime dependency. |
| `/lib/aarch64-linux-gnu/libc.so.6` | removed | — | The tracked PID 1, dispatcher, and workload are static PIEs; no shared libc closure is retained. |
| `/lib/ld-linux-aarch64.so.1` | removed | — | No dynamic ELF interpreter is needed by the selected static-PIE component closure. |
| `/lib/aarch64-linux-gnu/libpcre2-8.so.0` | removed | — | No retained binary in the v2 closure uses the historical PCRE2 symlink. |

No h14 file is silently retained. The v2 additions are the exact account
database (`passwd`, `group`, locked `shadow`, files-only `nsswitch.conf`, and
one forced shell), the three tracked static-PIE components, and the public
static provenance markers. The one-line service authorization is structural
`redacted-unbound`: its algorithm, exact restrictive options, path, owner,
mode, and grammar are tracked, but the boot-private key bytes are not.

## Bound content properties

The v2 manifest binds the following content-only facts:

- exactly one login-eligible nonzero service identity `a90svc` (`3301:3301`)
  and one distinct locked non-login key-daemon identity `a90key`
  (`3302:3302`); root is locked/non-login, IDs and names are unique, groups
  are empty, account lookup is files-only, and PAM/network lookup is false;
- the service home is `/srv/a90-service`, its only shell is the immutable
  probe dispatcher, and its read-only authorization tree is not `/root/.ssh`;
- the probe accepts only the direct `--request=readiness` form or the exact
  Dropbear shell `-c` form, reads only the fixed readiness record, emits at
  most 256 bytes, and performs no write, shell parsing, arbitrary command, or
  subsystem action;
- Dropbear is bound to port `2222` with exact foreground/stderr/key-only,
  root-disabled, no-forwarding launch arguments and the canonical forced-key
  options. The feature matrix disables password, empty-password, `none`,
  keyboard-interactive/PAM, root/alternate accounts and key sources, general
  shell, arbitrary command/subsystem, PTY, local/remote forwarding, agent,
  X11, and host-key generation;
- the only workload-writable path is the native-created `/run/a90` tmpfs
  subtree, with one bounded readiness file; no rootfs file creates that mount;
- the explicit absent list rejects the h14 firstboot, smoke, HUD, Debian
  Wi-Fi, `iw`, general `ip`, display/getty/console, root authorization,
  Dropbear key-generator, PTY/devpts, and setuid/file-capability surfaces;
- the filesystem tuple and usrmerge links retain the h14 appliance identity
  while the content schema and semantic contract are new.

## Dropbear source materialization

The pinned source was supplied after the specification was first written, so
the manifest has moved from `h0-specification-deferred` to
`h0-materialized-private`. It remains `candidate_eligible=false` and
`device_install_authorized=false`.

- upstream Dropbear `2026.94`, tarball SHA-256
  `e098034a843699200c8c977a991fff73159735bf795d5f72ef672c41a6b1ae81`,
  retrieved from the `dropbear.nl` release mirror because the canonical
  `matt.ucc.asn.au` host returned HTTP 525 at fetch time;
- the detached signature verifies as a good signature from
  `Dropbear SSH Release Signing <matt@ucc.asn.au>`, key
  `F7347EF2EE2E07A267628CA944931494F29C6773`. Upstream `release.sh` at the
  `DROPBEAR_2026.94` tag on `raw.githubusercontent.com` names key id
  `F29C6773` as the signing key, so tarball host and key-id publisher are
  independent. That cross-check binds only the low 32 bits of the
  fingerprint; a full-fingerprint publication by upstream was not located;
- the archive carries no symlink, hardlink, or special member, satisfying the
  builder's rejection rules;
- the built server is 1,550,912 bytes, static-PIE aarch64.

Compile-time feature removal was verified against the built binary rather than
assumed from the macro list. `svr_auth_password`, `svr_auth_pam`, `x11req`,
`agentreq`, `recv_msg_channel_open_tcp`, `setup_listener_tcp`,
`send_msg_channel_open_x11`, `svr_chansession_checksignal`, `newptycmd`, and
`sessionpty` are all absent from its symbol table, while `svr_auth_pubkey` is
present. Dropbear's Makefile compiles those translation units unconditionally,
so their absence from the link result is the fact that supports the manifest's
`compile-time-feature-removal-required` enforcement claim.

Static glibc emits link-time warnings that `getpwnam`, `getpwuid`, `getgrnam`,
`getgrouplist`, `initgroups`, `getspnam`, and `getaddrinfo` need the shared
libraries from the linking glibc. Because the appliance retains no shared
library at all, that warning was treated as a possible blocker and tested: a
static-PIE probe built with the same flags resolves the service account from a
files-only `/etc/passwd`, `/etc/group`, and `nsswitch.conf` under
`qemu-aarch64`. The instrument was validated first — the same probe returns
NULL when run without the emulated root prefix, so it is reading the supplied
database and not the host's.

Two builder defects surfaced only once the source existed, because the
previous validation could reach neither path:

- `materialize_tree()` re-checked the absence of the output root that
  `build()` had already created and populated, so a complete build could never
  finish. It now checks the `rootfs` subdirectory it owns; the root's absence
  is still enforced once, in `build()`.
- `configuration_semantics_sha256` was computed over the build dictionary that
  already contained that same field, so each build hashed the previous build's
  result. The manifest never reached a fixed point and every rebuild produced
  a spurious diff while the built artifact was byte-identical. The digest now
  excludes itself, and a regression test recomputes it.

With both repaired, three consecutive builds produce an identical manifest and
an identical `content.tar`.

## Launch argv: a bound flag that would have stopped the server

With the source present, each flag was derived from `src/svr-runopts.c` and the
result retired the argv-semantics deferral. It also found a blocking defect.

The parser's default branch prints `Invalid option -%c`, prints usage, and
calls `exit(EXIT_FAILURE)`. Feature removal deletes case labels, and only some
of them leave an ignore-the-flag `#else`:

- `-j` sits in `#if DROPBEAR_SVR_LOCALANYFWD` with an `#else` that accepts and
  ignores it, and `-k` likewise in `#if DROPBEAR_SVR_REMOTEANYFWD`. With those
  features removed the flags are harmless no-ops.
- `-s` sits in `#if DROPBEAR_SVR_PASSWORD_AUTH || DROPBEAR_SVR_PAM_AUTH`, also
  with an ignoring `#else`.
- `-a` sits in `#if DROPBEAR_SVR_REMOTETCPFWD` **with no `#else`**. This build
  removes that feature, so `case 'a'` does not exist and the flag reaches the
  default branch.

The previously bound argv therefore could not start the server. Running the
built binary confirms it: with `-a` it prints `Invalid option -a` and exits 1;
without `-a` the same sequence parses and proceeds to host-key loading. On
device this would have presented as a healthy handoff with no SSH, and it
would have consumed an ordinal to learn.

`-a` is removed from the bound argv and recorded under
`dropbear.argv_semantics.rejected` with its effect, guard, consequence, and the
verification. The retained flags carry their derived effect, guard, and whether
they are required. Four of them — `-s`, `-w`, `-j`, `-k` — are marked
`redundant_with_compile_time_removal`: the features they disable are already
gone from the binary. They are kept as defence in depth, but redundancy with a
compile-time removal is exactly the condition that produced this defect, so the
table records it explicitly. `-E` is flagged separately: its case label is
guarded by `#ifndef DISABLE_SYSLOG`, which this build does not define, so a
future build that does would make `-E` fatal in the same way.

Tests now assert that every bound flag has derived semantics, that every
rejected flag is absent from the argv, that reintroducing `-a` fails
validation, and — when a private build is present — that the bound argv is
accepted by the actual binary under `qemu-aarch64`.

## Security derivation status

The seccomp positive syscall/argument allowlist, capability minimum set, and
`/proc` scalar allowlist were re-derived after all four private AArch64
binaries were materialized. The exact method, raw sets, unresolved `svc`
sites, exercised and unexercised scenarios, and successor conditions are in
`docs/reports/A90_ISOLATED_DEBIAN_SECURITY_DERIVATION_H0_2026-08-15.md`.

The trace interpretation is now explicit and two-sided: QEMU output covers
only exercised paths and may be a strict subset of the real syscall set, so a
missing syscall can kill the service, while every observed syscall must be in
the candidate allowlist. QEMU is an emulator and not the A90 vendor kernel;
on-device negative testing remains required. The current host trace reached
Dropbear startup and component identity gates, but host socket creation and
the exact service/root isolation needed for the full scenarios were
unavailable, so the three manifest items remain narrowed deferred evidence.

The native-bootstrap key-daemon/generator clean-exec and observer proofs are
not rootfs content and are not implemented by this static-content unit; the
manifest records only their rootfs-facing ownership and absence boundary.

Building the private content tarball, when the missing source is supplied, is
still only host-side preparation. It grants no UFS installation authority;
the current common contract activates no direct UFS filesystem-content
mutation. A future installation process, higher-precedence boundary change,
exact target/recovery closure, and attended authority remain separate work.

No ordinal, version identity, build string, enable/latch path, artifact
qualification, approval, command, device contact, USB contact, or device
network contact was created by this unit. S20+ and S22+ files and lanes were
not touched.
