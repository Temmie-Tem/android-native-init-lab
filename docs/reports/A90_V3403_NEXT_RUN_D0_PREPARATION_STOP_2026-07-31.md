# A90 V3403 Next-Run D0 Preparation Stop

Date: 2026-07-31 KST

Status: `STOP_UNAPPROVED_D1_HIDE_RETURN_HEALTH_PASS`

## Scope

This report records the stopped attempt to prepare fresh connected D0 evidence
for a later A90 V3403 run. No new F1 run, manifest, approval receipt, staging
transaction, candidate transfer, or rollback transaction was created.

## Confirmed D0 state

Host USB inspection selected exactly one A90 native-init product separately
from the connected S22+ Android ACM endpoint. The selected A90 bridge matched
the prior target digest, its exact device, and its expected realpath.

Bounded read-only commands then confirmed:

- exact V2321 version and build;
- framed version, status, and selftest success;
- selftest failure count zero;
- pstore entry count zero; and
- mounted writable SD-backed native-init storage.

The host A90 NCM profile had retained the correct address but was bound to an
obsolete interface name after USB re-enumeration. Its interface binding was
updated to the only NCM interface under the same A90 USB parent. Direct route,
host CIDR, and device ping then passed. This was a host-only network repair.

## Incident

The first SD path query over the serial command channel was rejected by the
automatic-menu busy gate before its read-only body ran. The fallback plan was
to retrieve the existing tcpctl token read-only and use USB-local NCM without
menu control.

The shell command group did not enable fail-fast handling. The token request
returned busy, but subsequent checks did not stop the shell. An empty token was
therefore passed to `tcpctl_host.py`, whose default missing-token path requests
menu hide before retry. One `hide` command ran without a fresh D1 approval.

After authentication, the tcpctl shell payload had an unterminated quoted
string and exited before executing its body. It produced no SD path evidence
and performed no device file operation.

This was a process violation even though `hide` is transient and no payload or
partition operation was involved. The selected D0 unit stopped immediately
after return-health checks.

## Return health and safety

Post-incident read-only checks proved exact V2321 and selftest failure count
zero. There was:

- no flash or partition payload;
- no reboot or boot-mode request;
- no rootfs staging or SD file write;
- no userdata access;
- no candidate or rollback attempt; and
- no live authority created.

Private structured evidence is under
`workspace/private/runs/server-distro/a90-v3403-d0-prep-stop-20260731-01/`.
Raw bridge traffic remains private.

## Disposition

The SD source, fixed work path, new source path, and run-owned temporary path
remain unproved for this preparation attempt. No final connected D0 result may
be inferred.

Resume requires explicit operator direction after this report. The successor
must avoid all serial menu-control fallbacks: load the already private
current-boot token without a device command, use direct authenticated tcpctl
requests with simple absolute argv, enforce fail-fast host orchestration, and
stop before any D1 or F1 boundary.
