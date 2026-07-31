# A90 V3405 F1 Retained-pmsg and NCM Rebind H0 Closure

- Date: `2026-07-31`
- Scope: H0 F1 observer/recovery support implementation and independent review
- Decision: `A90_V3405_F1_OBSERVER_SUPPORT_H0_PASS`
- Live authority: none
- Device contact, staging, reboot, handoff, or flash in this unit: none

## Selected gap

The V3405 return supervisor and exact private rootfs already existed, but they
were not live-adoptable for two reasons:

1. no observer recovered the current run's retained
   `A90D3RET_V3405 phase=armed` positive control; and
2. the host NetworkManager profile remained bound to a transient NCM interface
   name after the A90 USB composite device re-enumerated.

This unit closes those host/orchestrator gaps. It does not prepare or authorize
a live F1 transaction.

## Stable NCM rebind

After the exact candidate native-init health check and before rootfs handoff,
the orchestrator:

1. reopens the manifest-bound exact ACM bridge identity;
2. selects exactly one `cdc_ncm` interface beneath that current ACM device's
   USB parent;
3. rejects zero-after-deadline or multiple matches;
4. requires the manifest-bound NetworkManager profile to exist as an Ethernet
   profile;
5. keeps an already-correct, reachable binding unchanged; otherwise
6. modifies that profile to the newly selected interface with the exact
   USB-local manual address, no gateway, no DNS, no default route, disabled
   IPv6, and no autoconnect; and
7. activates it once and re-runs the existing direct-route, source-address,
   same-parent, and device-ping gates.

The path does not select by MAC address, USB serial, or a global first-NCM
heuristic. It does not delete or recreate a NetworkManager profile. A failed
post-modification validation stops before handoff and cannot authorize a
candidate retry; the host profile change may remain for inspection.

## Current-run pstore proof

Before handoff, native-init mounts pstore read-only, requires zero entries, and
unmounts it. A pre-existing record is contamination: it is not deleted, and
the handoff stops.

After the bounded return to the exact candidate native-init, the orchestrator:

1. mounts pstore;
2. requires exactly one regular pmsg entry with the reviewed ramoops name;
3. reads its SHA256 and content;
4. requires exactly one `A90D3RET_V3405 phase=armed` token;
5. classifies later evidence as sync-timeout, sync-return/reboot-enter,
   sync-enter without a terminal marker, or armed-before-sync;
6. publishes and fsyncs a private capture containing the manifest, rootfs,
   entry, hash, and raw framed read;
7. publishes and fsyncs a cleanup-intent receipt;
8. re-reads the entry SHA256 inside the one cleanup command and unlinks only
   that exact path if the hash is unchanged;
9. requires pstore to be empty and unmounts it; and
10. publishes a private cleanup closure.

The unlink command uses the non-retrying command path. If its response is lost,
the durable capture and cleanup intent remain, proof fails, the candidate is
not replayed, and only the already-authorized rollback path remains. An
unexpected entry set or missing positive control is preserved rather than
cleaned.

## F1 ordering and approval binding

The source contract fixes this order:

`candidate health -> same-parent NCM rebind -> read-only empty-pstore gate ->`
`source recheck -> handoff -> Debian SSH PID1 proof -> candidate return ->`
`retained pmsg capture/cleanup -> rollback -> final health`

Both unattended and attended paths use the same pmsg return proof. The
attended `900/3/1` window, durable one-handoff intent, one candidate attempt,
no replay, mandatory rollback, and rollback-only recovery rules remain.

The new observer fields are inside the immutable manifest and therefore its
approval hash. They bind the NetworkManager profile name, same-current-ACM
USB-parent selector, retained marker and phase, cleanup-after-private-fsync
rule, and exact observer contract. The staging adapter now derives a distinct
V3405 absent-only final path and rejects unsupported cycle names.

## Validation and independent review

The reviewed source identities are:

```text
orchestrator        7397284176dbf612528dd2ce92f61a5a142506a6c0ca896effda3fb07502bd9c
staging adapter     782f581e2022041945f81ddd9d3e5cc5511c6cb7a2f6e340c97480350fb956eb
orchestrator tests  2276264975cdb6b754928a85db6da7e789260fc66f239050d2810d429f6aa9ec
staging tests       f3ee028b223cb99ebd001143282679710265757457f34b0720c0f97d934a594d
```

Validation passed:

- focused changed-machinery suite: `120/120`;
- related F1, V3405 supervisor, switch-root, sysvinit-rootfs, and
  post-rollback closure suites: `166/166`;
- Python `py_compile` for all four changed Python files; and
- `git diff --check`.

The independent safety review returned `GO` for this H0 closure and future
fresh-manifest adoption. It found no live authority in this change and
performed no device action or file edit.

## Remaining live gates

Before any new A90 F1:

1. create and read back the dedicated NetworkManager profile, prove it is
   unique, and bind its name in host preparation;
2. run fresh connected D0 and path preflight against the current tty realpath;
3. bind the exact candidate boot, V2321 rollback, V3405 rootfs, staging
   adapter, orchestrator, observer key, and recovery evidence in a new
   immutable manifest;
4. prepare the exact approval token from that final closure; and
5. obtain one fresh F1 approval.

All prior approvals and run IDs remain consumed. This report is not approval
and does not permit staging, handoff, reboot, or flash.
