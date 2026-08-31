# S20+ G986N ADB autostart and host-kill H0 review

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **H0 DESIGN REVIEW; NO SAFE TRANSPORT ACTIVE**

## Purpose

Resolve the remaining autonomous public-health blocker around implicit ADB
server lifecycle changes. The reviewed opening must use only a pre-existing,
exactly bound host server. A client-side connection failure, version mismatch,
or endpoint replacement must never start, replace, re-exec, or kill a server.

This review used host package metadata, exact-file hashing, bounded ELF/string
inspection, Ubuntu source-package patches, and the corresponding AOSP 34.0.5
sources. It did not invoke `adb`, open an ADB/device socket, contact USB, issue
a device command, or use `su`, Odin, a mode transition, or a partition payload.

## Exact host input

The currently pinned client is
`/usr/lib/android-sdk/platform-tools/adb`, 716,968 bytes at SHA-256
`05a1a4435e436230931acd8737fd68f31542d652731d3ca8c464cab7a42be226`.
It is Ubuntu package `adb` / source `android-platform-tools`
`34.0.5-12build1`, x86-64 PIE, with GNU build ID
`5c2ce2f2194f8dbeb4756fba1b891676eef048ec`.

The matching Ubuntu source inputs were downloaded into an ephemeral host
working directory for this review and were not retained as repository
artifacts. Their observed identities were:

- `android-platform-tools_34.0.5.orig.tar.xz`, SHA-256
  `4893f6a85b205f1df2c35cde5d6ca3bedd5e9f19afdb3b5ac781e647aa2243f4`;
- `android-platform-tools_34.0.5-12build1.debian.tar.xz`, SHA-256
  `b6e320190108117bb801432fd001f5a306b0cbbfe21259e6cf58e6353eee782f`.

The observed Debian/Ubuntu patch series contains no patch to `client/adb_client.cpp`,
`socket_spec.cpp`, or this server-lifecycle decision path. The matching AOSP
tag is [platform-tools-34.0.5](https://android.googlesource.com/platform/packages/modules/adb/+/refs/tags/platform-tools-34.0.5),
whose server protocol version is `41` (`0x29`) in
[adb.h](https://android.googlesource.com/platform/packages/modules/adb/+/refs/tags/platform-tools-34.0.5/adb.h).

## Finding 1: numeric loopback is only a partial guard

The current candidate sets `ADB_SERVER_SOCKET=tcp:127.0.0.1:5037`. In the
matching [socket classifier](https://android.googlesource.com/platform/packages/modules/adb/+/refs/tags/platform-tools-34.0.5/socket_spec.cpp),
only an empty host or the literal `localhost` is classified as local;
`127.0.0.1` is therefore classified as remote. If the first server connection
fails, the [client path](https://android.googlesource.com/platform/packages/modules/adb/+/refs/tags/platform-tools-34.0.5/client/adb_client.cpp)
reports that it cannot start a server on a remote host and returns without
launching one.

That behavior does not cover version mismatch. After parsing `host:version`,
the exact client compares the response with `0x29`. On mismatch it may first
attempt a newer-server re-exec, then calls `adb_kill_server()`, sends the
literal `host:kill` request to the selected server socket, and only afterward
jumps to `launch_server()`. The documented meaning of `host:kill` is a request
for immediate server termination in [ADB services](https://android.googlesource.com/platform/packages/modules/adb/+/refs/tags/platform-tools-34.0.5/SERVICES.TXT).
The exact binary also contains a server-side reject setting, but its effective
state is not proven here; a mismatch must therefore be treated as capable of
terminating the current server.

Therefore:

- numeric loopback alone is `NO_GO`; and
- a child seccomp filter that blocks only fork/exec/bind/listen is also
  `NO_GO`: it does not cover every mismatch branch, and the older-server path
  reaches `host:kill` before a denied syscall. A newer-server path may instead
  be stopped by its earlier re-exec attempt, which does not repair the older
  path.

The independently reproduced exact-binary landmarks were classifier
`0x3d710`, remote reject `0x5169e`, launch call `0x517de`, optional re-exec
`0x51927`, mismatch log/kill/jump `0x51988`/`0x5199c`/`0x519a1`,
`host:kill` write `0x4f524`–`0x4f530`, and fork/execv
`0x2dc35`/`0x2e1df`.

The current pidfd/listener/executable owner does prove the observed server at
its verification points. It does not atomically bind the later ADB client's
new TCP peer. A listener replacement between verification and connection can
still expose the mismatch path. Detecting that replacement afterward cannot
undo a transmitted kill request.

## Candidate decision

Two designs remain supported as H0 candidates, not qualified capabilities:

1. A direct, closed smart-socket client removes every server launch, re-exec,
   and kill implementation from the consumer. A dedicated peer-bound version
   connection must require `host:version == 0029`; because that host query
   closes after its protocol string, every later service connection must
   independently bind its TCP tuple/socket inode to the same held exact server
   PID and reverify pidfd/start/executable/listener continuity before its first
   frame. Every fault closes without reconnect. This has the smallest security
   surface but requires a new transport and Phase-A identity rotation.
2. A restricted proxy preserves the current ADB argv/output/parser closure.
   It may answer downstream `host:version` locally only after binding the exact
   server executable/protocol identity; it never forwards that query. Every
   actual-service upstream FD must independently bind its established peer to
   the same held PID/start/executable/listener before its first forwarded byte.
   It forwards only ordinal-specific fixed frames, returns only exact version
   `0029`, and never forwards `host:kill`,
   `host:start-server`, or an unknown frame. A child seccomp layer must
   additionally prevent a downstream client
   from creating a replacement server if the private proxy disappears or
   rejects it. This is the minimum-integration candidate.

Neither design is implemented here. The restricted-proxy model, concrete
proxy, child filter, peer binding, closed executor, evidence owner, production
interlock, recovery integration, contract gate, mechanical activation, and
live authority all remain false.

## Required hostile evidence

Before qualification, the selected implementation must prove at least:

- exact source/binary/build identity and complete transitive execution path;
- no upstream byte for `host:kill`, `host:start-server`, or any unlisted frame;
- old, new, malformed, partial, oversized, timed-out, or missing version
  responses leave the real server unchanged;
- proxy/server absence, replacement, and mid-frame death create no descendant
  or listener, cause no retry, and send zero bytes toward the real server or
  device after an unbound downstream endpoint is observed;
- the dedicated version connection returns exactly `0029`, and every later
  established service socket belongs to the same bound PID before its first
  service frame;
- duplicate, reordered, cross-ordinal, caller-supplied, and reconnect attempts
  fail closed;
- every seccomp installation failure stops before ADB execution, and every
  filter trip is terminal non-success; and
- the normal six-command public-health transcript remains byte- and
  accounting-exact in an isolated fake-server corpus before any connected use.

Until that evidence and an independent integrated review exist,
`autostart_prevention_implemented=false` remains the correct status and no
autonomous connected command is authorized.
