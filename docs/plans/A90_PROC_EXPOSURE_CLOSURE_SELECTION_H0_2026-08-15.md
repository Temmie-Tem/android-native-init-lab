# A90 `/proc` exposure closure selection (H0)

Date: 2026-08-15
Target: operator-owned Samsung Galaxy A90 5G only
Tier: H0 static design selection
Authority: none; no device, USB, network, or private-evidence contact

This document selects a closure for
`docs/reports/A90_NATIVE_WIFI_SIDECAR_PROC_ROOT_EXPOSURE_HOST_INCIDENT_2026-08-13.md`.
It bounds the proof conditions for the selected closure. It does not redesign
the isolated-Debian architecture and does not claim that any condition is
implemented or proved.

## Closure comparison and selection

| Closure | Required proof | Fit with the current A90 goal |
|---|---|---|
| `DEBIAN_OWNS_WIFI_ZERO_NATIVE_SIDECARS` | Stop and reap every native Wi-Fi/Android companion before handoff; have Debian bring up and retain final Wi-Fi from boot-private non-SD input; and prove in the same run that no foreign root, FD, or mount-namespace capability is exposed. | Not selected. It changes the current native Wi-Fi ownership boundary and first requires a new Debian Wi-Fi ownership proof. |
| `NESTED_PID_NAMESPACE_ISOLATION` | Keep native Wi-Fi and its native sidecars under the native supervisor; run Debian as PID 1 in a fresh nested PID namespace with a matching private procfs; and prove the native processes are absent and unnameable from Debian, with the separate veth boundary and exact cleanup. | Selected. It preserves the current goal's native Wi-Fi owner while closing the shared-PID/shared-proc exposure. |

The explicit selection is `NESTED_PID_NAMESPACE_ISOLATION`. The selected
closure is the nested PID/proc closure plus a separate Debian network namespace
and a parent-owned veth boundary. The first closure is not a fallback or a
future implicit requirement; it remains a different, unselected closure.

## Minimum Debian PID/proc invariants

- The native supervisor remains outside the child PID namespace. The child is
  created in a fresh PID namespace and a separate mount namespace; Debian's
  eventual init must be PID 1 in that child namespace.
- A procfs instance is mounted after the child PID namespace exists and is
  bound to that namespace's PID view. It must have a distinct superblock and
  mount identity from native procfs. Moving or binding the native procfs,
  `chroot`, path-name hiding, or `hidepid` without a fresh PID namespace is not
  the closure.
- The child procfs uses the fixed bounded read-only shape
  `nosuid,nodev,noexec,hidepid=2`. Writable and sensitive global views are
  masked, only a finite reviewed scalar allowlist remains, and the procfs and
  masks are remounted read-only before Debian release.
- The child receives no native PID, proc, pidfd, nsfs, root, or native-device
  descriptor. Native PID 1 stays in its own namespace and remains the only
  native recovery supervisor. Any missing namespace, shared procfs, writable
  proc view, or unbounded global view is `NO_GO`.

## Conditions for non-nameable native `/proc` paths

The claim is stronger than “permission denied.” For every native PID in the
parent-side bound process set, the following conditions must hold in one
same-run proof:

1. The child PID namespace and the child procfs identity are recorded. Child
   procfs enumeration contains only the child namespace's visible PID set;
   no native PID is mapped into it.
2. A known native PID supplied to the Debian-side read-only observer produces
   `ENOENT` for `/proc/<native-pid>` itself. Therefore
   `/proc/<native-pid>/{root,fd,ns}` is not nameable from Debian, rather than
   merely unreadable. The same negative check covers every native PID, not
   only the Wi-Fi helper.
3. The child FD and mount evidence proves that no host-proc bind, native proc
   FD, pidfd, nsfs FD, or old-root handle is available to Debian. A successful
   lookup, a visible native PID directory, or an inherited handle is a
   `NO_GO`.
4. The negative result is repeated after the child reaches its intended
   post-exec observation point and while the persistent service is live. It is
   not inferred from a pre-exec marker, a port response, `hidepid`, or a host
   parser result.

The existing `switch_root_exec` marker is written before `execve()` is called;
it is not exec-success evidence. It cannot by itself prove Debian userspace,
Debian PID 1, or Dropbear. H16 did not prove Debian PID 1 or Dropbear, and
this document also does not claim that H16 failed to reach userspace; both
outcomes remain unproved.

## Native Wi-Fi survival and the Debian veth boundary

Native PID 1 keeps ownership of `wlan0` and the native Wi-Fi service. The
selected closure does not stop or reap native Wi-Fi sidecars merely to make
the proc exposure disappear. Debian instead receives one separate network
namespace and one bound veth peer; it does not receive `wlan0`, the native
network namespace, native Wi-Fi/control sockets, or native network-admin
capability.

The native end remains under a closed default-drop forwarding/NAT policy. The
Debian path is bounded to the reviewed veth/IP boundary and its one-shot
ingress gate; native forwarding preconditions are read-only and existing
native Wi-Fi configuration is unchanged. A same-run proof must show native
Wi-Fi remains available while Debian cannot bypass the veth boundary or reach
native listeners. Final Wi-Fi and persistent Debian service health are not
claimed by this H0 document.

## Failure ordering

On every selected isolated-Debian failure branch, the order is immutable:

`block ingress -> record cause -> reap -> cleanup`

First block new veth traffic and SSH accepts/sessions. Then durably record the
original stage, return code/errno, cleanup intent, and exact bound identities.
Only after that record is durable may the supervisor terminate and reap the
exact child-namespace members. Cleanup then removes only the bound veth,
rules, cgroup, mount, and related state and proves their absence. The original
cause and cleanup result are separate records; cleanup never overwrites or
reclassifies the cause. Missing identity or cleanup proof parks recovery and
never replays handoff or candidate activity.

## Implementability, negative corpus, and observer contract

Before any successor identity, an independent H0 review must prove that the
host toolchain and supported kernel can implement the fresh PID/mount/proc
boundary, veth/netfilter limits, read-only proc masks, pivot/cleanup, ownership-
aware reap, crash-prefix journal, and no-replay continuation. Unsupported
namespace or proc behavior, an unbounded resource path, or cleanup ambiguity
is `NO_GO`; no live qualification follows from a host dry run.

The negative corpus must reject at least:

- shared PID namespace, shared/native procfs, private-mount-only isolation,
  `chroot`, `hidepid`-only isolation, or path-name checks used as substitutes;
- any native PID directory or successful `/proc/<native-pid>/{root,fd,ns}`
  lookup from Debian, including a result that is only hidden by a permissive
  parser;
- inherited native proc/pidfd/nsfs/root descriptors, native `wlan0` or
  control sockets, a shared network namespace, or traffic outside the veth
  default-drop boundary;
- cleanup that records the cause after reap, removes state before ingress is
  blocked, loses the original cause, or retransmits an uncertain effect; and
- treating `switch_root_exec`, EOF, a responding port, H16 evidence, or a
  parser PASS as proof of Debian PID 1, Dropbear, or exec success.

Each assertion needs a passing fixture and a failing fixture for the stated
reason. The future observer contract is a same-run, target-bound,
authenticated, non-PTY read-only probe. It must bind the child PID/proc
evidence to the native supervisor's same-run facts and must not infer a
process, root, namespace, Wi-Fi, or health claim from an unbound marker.
Observer reachability, framing, parsing, or attribution failure is
`NO_PROOF_OBSERVER` and freezes new non-recovery device effects; a
device-attributable contradiction is `REFUTED` and cannot be downgraded to an
observer failure. `unproved` remains unproved.

## Allocation state

- Candidate identity: **unallocated**.
- D0: **unallocated**; no connected read or USB action is authorized.
- F1: **unallocated**.
- D1: **unallocated**.
- No ordinal, version, build string, manifest, enable/latch path, artifact,
  qualification, approval, or command is allocated by this selection.

The selection is H0 documentation only. It grants no candidate, D0, D1, F1,
flash, handoff, reboot, or recovery authority.
