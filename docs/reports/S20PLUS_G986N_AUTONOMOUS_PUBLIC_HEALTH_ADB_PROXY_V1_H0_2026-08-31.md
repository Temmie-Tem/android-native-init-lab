# S20+ G986N autonomous public-health restricted ADB proxy v1 H0

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **H0 POST-RUN AUDIT MODEL PASS_GO - NOT ACTIVE**

## Purpose

Model the narrow protocol firewall needed to preserve the frozen ADB argv and
output parsers without allowing the exact ADB client to send `host:kill` to the
real server or to start a replacement server. This unit follows the separate
host-kill review. It is a pure post-run trace validator and static render plan,
not a socket parser, proxy, seccomp filter, child launcher, executor, campaign
opening, or connected capability.

The implementation is
`workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_adb_proxy_v1_h0.py`.
Its final 46,477-byte source is SHA-256
`18993008de3c236211c11de2756dc9b05424d9704cfdcb9c02f3cf70e9e29d92`,
with activation-normalized SHA-256
`8878c5e39f2d34ea90707bf81697aed119db1fdf3141807b56c81480fbe1c8c9`.
The final 30,975-byte test is SHA-256
`058977bc8cb16cdf28af3ae2a4828e0eab035caa5d2a6177e788df8efd7f568e`.

## Exact protocol model

The modeled future ADB child receives a runner-owned private AF_UNIX proxy
socket under a held mode-`0700` session directory. Its path is never a caller
input. Each accepted downstream connection must bind exact `SO_PEERCRED`
PID/UID/GID to the direct child, the child's process start time, and a held
direct-child pidfd. The server UID must equal the child UID, while server and
child PIDs must differ. A separate runtime effective-UID receipt is not
integrated and remains an explicit unresolved gate.

The proxy handles the client's `host:version` request locally with exactly:

```text
OKAY00040029
```

No version byte is forwarded upstream. The `0029` basis is the exact held ADB
file plus the server's same device/inode/size/hash, pidfd/start/listener, and
accepted-peer composition. A version connection may never own an upstream
proof or send an upstream byte.

For each non-local command, the model allows one new upstream connection and
no reconnect. Before the first upstream wire event it requires a reciprocal
loopback TCP tuple, held proxy-side FD/inode, distinct server listener and
accepted-peer FD/inodes, the exact listener/accepted-peer entries in the bound
server's FD inventory, and the same pinned ADB executable device/inode/size/
hash as the held child executable.

The six command ordinals have this closed shape:

1. exact `adb version`: local-only and zero proxy connections;
2. local version, then exactly `host:devices-l`;
3. local version, then exactly `host-serial:<bound-serial>:get-devpath`;
4. local version, then `host:tport:serial:<bound-serial>`, exact `OKAY`, one
   nonzero eight-byte little-endian transport ID, then the fixed `exec:`
   request on that same connection;
5. the byte-identical ordinal-4 shape; and
6. the byte-identical ordinal-2 shape.

The fixed `exec-out` service follows ADB 34.0.5 construction: argv element 1
`sh` is copied raw, and `-c` plus the frozen Phase-A snapshot are independently
escaped with ADB's single-quote algorithm. The snapshot is 1,472 bytes at
SHA-256 `a571dc5009eb57952a6230e3ecca8ad342627eb1bf9df38060886ee6382cd17a`.
The complete service is 1,523 bytes at SHA-256
`c3db3a45d41b3684316c2344c8dad45b23f61b40f03e3d43f6e00d565b9f781e`.

## Relay audit boundary

The trace uses typed ordered logical wire events. It requires exact equality
for downstream request and upstream-forward bytes; upstream and downstream
`OKAY`; the eight-byte transport ID; query protocol strings; exec output; and
upstream/downstream EOF order. Exec output is bounded to 64 KiB. A partial,
oversized, reordered, duplicated, cross-ordinal, unknown, caller-selected,
reconnected, or trailing event is rejected.

`host:kill`, `host:start-server`, reconnect, tracking, and every service not in
the exact ordinal allowlist are rejected before an accepted forward event.
This proves only that one caller-constructed normalized post-run trace matches
the modeled firewall. It does not implement the incremental, fragmentation-
safe socket parser and event emitter that must enforce this ordering before
bytes are forwarded.

The Phase-A, runtime, and exact ADB identities in this source are declarative
pins. Tests independently compare the live host files with those pins, but all
three exact-bound gates remain false. The model is not a trusted live-file
binding or a producer receipt.

## Seccomp model boundary

A private AF_UNIX proxy is classified as local by ADB. If it is absent before
the first version connection, the child can attempt to launch a server. The
future child must therefore install a reviewed filter before its first
held-file `execveat` transition. The structural model denies process clone,
fork/vfork/clone3, path `execve`, bind, and listen.

No filter byte, architecture/ABI closure, installation routine, or failure
path exists here. Classic seccomp is stateless. Although the held ADB FD is
required to close across the first exec, a later FD-number reuse bypass and
the inability of any follow-up `execveat` to succeed are both unproved. The
model explicitly keeps filter implementation/installation, filter-byte pin,
and one-shot closure false.

## Validation and review

The focused suite passes 40/40. The canonical thirteen-suite autonomous
aggregate, including this model, passes 486/486. `py_compile`, render-only
execution, and `git diff --check` pass.

The hostile corpus covers exact identities; self/status/gate normalization;
all-false gates and the unconditional all-true unimplemented stub; exact
ordinal connection counts; local-only version; forbidden service rejection;
partial/oversized/extra frames; exact `tport`/transport-ID/exec order; exact
request, status, protocol-string, output, and EOF relay; owner proof before
the first upstream event; child/server UID and PID composition; reciprocal TCP
tuples and FD/inode roles; held ADB equality; no reconnect/retry; snapshot and
escape identities; and every disclosed seccomp/proxy limitation.

Independent review first rejected a legacy `host:transport` service, missing
transport-ID relay, an inaccurate stateful-filter claim, incomplete response
relay, and incomplete owner composition. After correction and final claim
narrowing, two independent exact-byte reviews returned `PASS_GO` with
HIGH/MEDIUM/LOW `0/0/0`.

## Non-authority result

The final status is
`H0_AUTONOMOUS_PUBLIC_HEALTH_ADB_PROXY_V1_MODEL_PASS_GO_NOT_ACTIVE`.
All 17 gates remain false. The CLI exposes only `--render-plan`; even forcing
all gates true reaches an unconditional unimplemented stub. No socket,
subprocess, ADB, USB, device, root, Odin, write, or partition operation was
performed by this unit.

Concrete proxy ownership/lifecycle, incremental parsing before forward,
response streaming, exact seccomp BPF/install/failure behavior, ADB child
compatibility against an isolated fake server, executable journal/evidence,
same-process campaign/runtime handoff, production cross-code interlock,
recovery integration, combined independent review, contract/mechanical
activation, and a fresh attended opening remain future work. This PASS_GO
qualifies only the exact inactive H0 audit-model bytes.
