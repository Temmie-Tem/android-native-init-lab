# A90 H14 immutable firstboot / isolated-Debian mismatch

Date: 2026-08-14
Target: Samsung Galaxy A90 5G only
Tier: H0 public-source audit
Live authority: none

## Question

Can the exact immutable H14/H24 UFS content be reused unchanged for the first
native-Wi-Fi / isolated-Debian proof, without a firstboot overlay or an
inherited post-exec evidence descriptor?

## Exact public identity

`phase3-minimal-h14/userdata-content-manifest.json` and the compiled H24 content
table bind `/etc/a90-d3-firstboot` as mode `0755`, size 12,092, SHA-256
`fd8625402c76b2ee0cc4a2aff07eed3b182c6dd12eba1a022a445ea428c8c84a`.
The exact bytes remain reproducible from Git commit
`a4925b80eadf781cf524c7eaf6741bb940ce78d4` at
`workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh`; the Git
blob is `4cb89506a9e61d2e2fa3b052df83ebd8da259167`.

The H14 content manifest also binds the 123-byte inittab, and retained public
lineage evidence records its sysinit hook as
`si::sysinit:/etc/a90-d3-firstboot`.

## Findings

The exact firstboot can start Dropbear when the boot-private
`/root/.ssh/authorized_keys` exists, but it is not the selected minimal
isolated-Debian service contract:

- it brings up `ncm0`, installs its legacy fixed address/prefix, and replaces
  the default route rather than consuming an exact newly bound isolated-veth
  contract;
- it binds Dropbear specifically to that legacy NCM address and fixed port;
- the exact H14 content manifest contains an executable smoke HTTP server, so
  firstboot starts that legacy service;
- the same manifest contains the HUD-intent producer and service launcher, so
  firstboot executes the retired HUD-intent path even though the presenter is
  left to native init;
- the manifest requires nonempty Debian Wi-Fi enable and immediate-snapshot
  markers, so firstboot invokes the Debian Wi-Fi helper even though the selected
  architecture keeps Wi-Fi exclusively native;
- it writes `/etc/hosts` and `/etc/resolv.conf` despite the selected read-only
  root/writable-set contract; failures are ignored under `set +e`;
- it has no writer for a new fixed-descriptor post-exec health/log protocol.
- it does not bind the Dropbear build/config/argv and account database to
  public-key-only client authentication, one login-eligible nonzero account,
  one accepted key, one forced probe, and zero alternate authentication or
  session features. Possessing one `authorized_keys` file is not proof that
  password, empty-password, interactive, root/alternate-account, shell,
  subsystem, PTY, forwarding, agent, and X11 paths are disabled.

These are not evidence that the historical appliance is corrupt. They show
that it is a visual/server demonstration rootfs with a different network and
service contract.

## Decision

The unchanged H14/H24 UFS content is rejected for the first isolated-Debian
candidate. Before any successor identity is allocated, create and independently
review a separately versioned minimal UFS content manifest that:

- contains one independently reviewed nonprivileged consoleless PID 1, the
  selected non-PTY Dropbear/authentication path on a non-privileged port, and
  only the chosen server workload; it does not assume the historical sysvinit
  binary or root identity is compatible, and the chosen PID 1 must pass the
  exact manifest-fixed UID/device/default-deny-filter and normalized scheduler
  trace;
- assumes the trusted native bootstrap has already configured the exact veth
  peer and does not configure or own `wlan0`;
- starts no HUD, smoke HTTP, tunnel, Debian Wi-Fi helper, or display service;
- requires the trusted bootstrap's already-present per-boot Ed25519 Dropbear
  server key, whose mode-0700/mode-0400 tree is owned only by a distinct locked
  non-login SSH-key-daemon UID/GID and remounted read-only before release; the
  service UID/PID 1/workload never creates, replaces, rotates, traverses,
  reads, or inherits it;
- uses only the declared writable tmpfs set;
- installs the boot-private client public key only in the manifest-fixed
  nonzero service UID's read-only home authorization tree, not `/root/.ssh`;
- binds the exact Dropbear binary hash, source/configuration feature matrix,
  argv, account database, service home, forced read-only probe, and canonical
  one-line `authorized_keys` grammar; exactly one fixed nonzero service account
  and one run-bound key are accepted, while password/empty-password/`none`/
  keyboard-interactive/PAM, root/alternate accounts or key sources, general
  shell, arbitrary command/subsystem, PTY, local/remote forwarding, agent, and
  X11 paths are disabled and negatively tested;
- requires trusted bootstrap alone to launch the filtered non-dumpable key
  daemon through one manifest-bound static clean exec before key load/listener
  bind; exact `maps`/`map_files`/FD proof must contain no inherited native
  mapping before those operations. The daemon reports exact
  `KEY_DAEMON_CLEAN_READY` then `KEY_DAEMON_LISTEN_READY` and EOF only through
  its transient internal status pipe; clean bootstrap is the sole
  native-receipt writer and forwards only the validated canonical summary. Its exact
  authenticated child transition uses an explicit zero-`capset` and ambient
  clear after the nonzero-to-nonzero UID/GID change, rereads exact saved IDs
  and empty capability sets, zeroes child-side key copies, then execs the forced dispatcher with no
  key/config/listener FD; service-side proc/ptrace/process-vm/pidfd-getfd access
  to daemon memory/FDs is denied and negatively tested;
- binds the sole manifest-pinned transient generator as a pre-`ROOT_PREPARED`
  clean-exec non-dumpable `RLIMIT_CORE=0` exception with exact argv/stdio/FD/output,
  exact internal `GENERATOR_CLEAN_READY` then public-only
  `GENERATOR_PUBLIC_COMPLETE` receipt, terminal EOF, exit/reap, and zero
  core/log/temp/private-output residue; generator and daemon helper forks close
  both native-facing bootstrap-pipe ends before clean exec and never write or
  carry them across it, their internal channels never
  overlap, and wrong writer/extra FD/frame/EOF/residue fails closed;
  after its proven reap, private bytes may exist only in the mode-0400 file or
  filtered key-daemon signing memory;
- PID 1, the forced dispatcher, and workload inherit no private key buffer or
  private control, health, or log descriptor;
- is observed after exec by native parent facts plus an attended authenticated
  host SSH probe bound to the same boot/run nonce, after the host has retrieved
  the target-bound public key/fingerprint receipt and enforced strict host-key
  checking without TOFU and after the native journal proves durable
  `INGRESS_OPEN_INTENT`, one atomic dormant-gate activation, and exact
  `INGRESS_OPEN` return/readback with no replay; the host receipt additionally binds the negotiated
  public-key client method, accepted client-key fingerprint, exact account,
  forced-probe result, and absence of every alternate SSH feature.

Building that content host-side does not authorize installing it. The current
common contract activates no direct UFS filesystem-content mutation. Any
future installation needs a separately reviewed higher-precedence boundary
change, its exact target-contract process, an exact rollback/recovery model,
and explicit attended authority. It may not use a raw partition image or
reinterpret this H0 report as D1/F1 permission.

## Boundary

No device, `/dev`, USB, network, private evidence, S22+, or S20+ path was
contacted. No H26 identity, artifact, approval, candidate transfer, rootfs
write, reboot, or handoff is created here.
