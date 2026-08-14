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
| `/usr/sbin/dropbear` | replaced | `/usr/sbin/dropbear` | Same service path, but only a separately built feature-removed Dropbear can be selected. Its exact binary/source hashes remain deferred until the private pinned source input exists. |
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

## Deferred requirements

The exact Dropbear binary hash and source/configuration semantics are deferred:
the required private pinned Dropbear source input is not present in this host
workspace, so the manifest deliberately says
`h0-specification-deferred`, leaves that hash null, and cannot be candidate
eligible. The builder fails closed rather than using the historical Dropbear
binary as a substitute.

The Dropbear launch argv is bound as an exact token sequence, but each flag's
meaning is not yet bound against the selected version. The design accepts a
runtime option only after its exact selected-version source, help, and parser
semantics are independently bound. The bound sequence includes `-a` alongside
the `-j` and `-k` forwarding denials, and that combination is not justified
from source here. The per-flag semantics table is deferred to the same unit
that supplies the pinned source; any flag whose effect is not required by the
session contract is then rejected or replaced.

The seccomp positive syscall/argument allowlist, capability minimum set, and
`/proc` scalar allowlist are also deferred. The intended successor method is
qemu-aarch64 user-mode tracing after all binaries are built; its output must be
treated as a candidate superset and then subjected to later on-device negative
testing. The trace was not attempted here. The current host has the
`qemu-aarch64` executable and cross-compiler, but the fresh
`/proc/sys/fs/binfmt_misc/qemu-aarch64` entry is unavailable, so no trace claim
is inferred.

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
