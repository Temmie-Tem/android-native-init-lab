# S20+ G986N recovery-only T0 process, proposed v1

Status: **CONCRETE OWNER IMPLEMENTED; REVIEW PENDING; NOT ACTIVE**
Date: 2026-08-31
Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`
Experiment: exact-stock-derived recovery ADB canary T0 only

## Non-authority statement

This document is a review input. It is not a binding target contract, is not a
live process, and grants no device authority.

The repository-wide contract still permits ordinary partition payloads only to
`boot`. Revision 3 now delegates one F2 T0 exception, but its S20+ target
section and connected owner are not active. Every other `recovery` payload
remains forbidden, and the active root-health D0 lane still excludes privileged
partition access. Consequently:

- the proposed fixed stock-recovery digest is not presently an allowed live
  read;
- neither the candidate nor rollback AP may presently be transferred;
- the user direction to continue does not mechanically activate this design;
- ordinary D0, D1, R1, or F1 labels must not be used to disguise this gap;
- `T0` identifies the single experiment and `F2` its inactive dedicated tier;
  neither grants authority before mechanical activation.

Activation requires an independently reviewed common-boundary amendment,
matching risk-tier and S20+ target-contract clauses, independent review of the
new connected owner, exact activation identities, and a fresh attended
binding. The earlier H0 runner named below still contains no device backend.
The separate concrete owner is
`workspace/public/src/scripts/revalidation/s20plus_g986n_recovery_canary_t0_f2.py`;
its activation constant is false and changing that Boolean without the complete
reviewed contract/status transition grants nothing.

## Objective

Prove or refute the smallest unresolved runtime claim before trying TWRP:

> Can the exact unlocked `G986NKSS8IYC2` device accept and start a recovery
> image that retains the exact stock kernel, DTB, recovery DTBO, boot header,
> and partition size, but changes only the bounded recovery ADB canary
> ramdisk?

T0 does not test TWRP, `/data` decryption, touch, display, MTP, fastbootd,
formatting, backup, restore, or native Debian. A T0 PASS is only a prerequisite
for a separately reviewed T1 run.

## Frozen host closure

| Item | Size | SHA-256 |
|---|---:|---|
| Odin4 `/usr/bin/odin4` | 3,746,744 | `6754aa54f2abe6e99ece32414cd34c8b23b28dbddde537a33203036813637c3b` |
| candidate recovery-only `AP.tar.md5` | 36,556,841 | `30227458889f1fa99eca192c9b7f8747f168d9e33cc1f407b52ae2b4d298559a` |
| candidate `recovery.img.lz4` member | 36,547,618 | `7f0e6b53a1036904fd02c5e8c2c014d3112ffb58fc33f9aa9a26c0962af45928` |
| candidate decoded recovery | 82,694,144 | `e1297613df576d25cc9391df97dac7cf316fee545f56111e6bc5340cb8ce659b` |
| exact-stock rollback `AP.tar.md5` | 36,608,041 | `ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157` |
| rollback `recovery.img.lz4` member | 36,600,544 | `6b962af2fc4fcc424d16ecdcee1793bdd6d4c8dba2e80d35cb21961fcb865923` |
| exact-stock decoded recovery | 82,694,144 | `dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e` |
| T0 build manifest | 5,459 | `7c693b4e2e13efa912b5de00a95bbd41bb1651913427461e756225243381e1e3` |
| T0 host builder | 25,007 | `811b2f80db822689d716c0de400cea22440af3069d7ea20945ddf0b36908c118` |
| stock-recovery digest H0 profile | 9,509 | `9377e58d3717e0fa96826210815b09df20bf2ba62a70c85c896f5a6fdf68fded` |

Each AP must be a direct, single-link, non-group/world-writable regular file.
It must have exactly one regular tar member named `recovery.img.lz4`, mode
`0644`, uid/gid zero, mtime zero, and the exact member receipt above. The
appended Odin MD5 and the tar MD5 must agree. Any additional member, including
VBMeta, stops before device contact.

## Proposed effect ceiling

The complete T0 campaign may contain at most:

1. at most three one-shot fixed privileged recovery-block reads: preparation,
   execution pre-transfer, and final health (or pre-candidate abort instead of
   final health); each read has its own durable intent and may not replay;
2. one candidate transfer to `recovery`;
3. one attended physical direct-recovery boot after a completed candidate
   transfer classification;
4. one transition to Download for stock rollback;
5. one exact-stock rollback transfer to `recovery`;
6. bounded read-only recovery and final Android observations.

No other partition transfer is allowed. In particular, T0 grants no `boot`,
`vendor_boot`, DTBO, VBMeta, BL, CP, CSC, super, userdata, persist, EFS,
`sec_efs`, RPMB, keymaster, modem, `misc`, or partition-table action. It grants
no raw host `dd`, format, mount, remount, deletion, property mutation, service
mutation, package action, Magisk mutation, or generic caller-supplied `su`.

## Entry conditions

All conditions are conjunctive and fresh for one run:

1. The device is operator-owned and physically attended.
2. A fresh global ADB inventory contains exactly one healthy exact S20+ match;
   all other target rows receive zero commands.
3. Model, device, product, incremental, serial hash, USB topology hash, current
   boot ID hash, unlocked/orange state, SELinux, boot completion, PID 1, and
   exact Magisk version match the reviewed binding.
4. The separately reviewed fixed read reports recovery size `82,694,144` and
   SHA-256
   `dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e`.
   `/dev/block/by-name/recovery` must resolve exactly to `/dev/block/sda24`.
   That expected node is derived host-side from the exact 12,156-byte
   `Y2Q_USA_SINGLE.pit` SHA-256
   `06f87a8aba5ac95c4784f034816d2744c246af6067452b0a3acd2b63c5763b99`:
   entry 23 is `RECOVERY`, identifier 24, with 20,189 4-KiB blocks. The node
   mapping remains live-unconfirmed and therefore fails closed if it differs.
5. Candidate, rollback, Odin, builder, digest profile, connected owner, parser,
   journal schema, and tests match the independently reviewed hashes.
6. Physical Download entry and return remain demonstrated independently of the
   recovery partition. This is the recovery path if the candidate cannot boot.
7. The owner fixes the S20-series post-transfer choreography: keep USB
   connected, hold Side/Power plus Volume Down until fully black, keep
   Side/Power held while immediately switching from Volume Down to Volume Up,
   and hold Side/Power plus Volume Up until Recovery; Android must not boot.
8. The initial Download listing is empty. After the attended transition, one
   exact `04e8:685d` / `SM8250` endpoint arrives on an allowed topology and is
   bound by path hash plus device/inode/type identity.
9. A new durable run directory and exclusive guard exist with no candidate or
   rollback intent from another run.
10. One fresh approval binds the exact current boot, endpoint, all closure
    hashes, both transfers, physical handoffs, observations, recovery, and
    expiry.

Any drift or ambiguity stops before candidate intent.

## Concrete state and journal

Every final journal node is canonical JSON, file-fsynced, atomically published
no-replace, and followed by a directory fsync. A later node cannot exist without
its predecessor. `recovery-boot-intent.json` is optional: it exists only on the
completed-candidate branch.

| Phase | Durable node | Permitted next action |
|---|---|---|
| host preparation | `prepared.json` | obtain one exact attended approval |
| approval | `approval.json` | record intent to enter candidate Download |
| candidate Download handoff | `candidate-download-intent.json` | one attended transition, then bind one arrival |
| candidate endpoint bound | `candidate-download-arrival.json` | publish candidate transfer intent |
| candidate attempt consumed | `candidate-intent.json` | invoke the exact candidate command once |
| candidate classified | `candidate-result.json` | completed branch may arm recovery boot; all other branches skip it |
| direct-recovery action armed | `recovery-boot-intent.json` | perform the attended physical chord once |
| canary observation closed | `candidate-observation.json` | enter or confirm Download for stock rollback |
| rollback Download armed | `rollback-download-intent.json` | one transition or attended physical handoff, then bind one arrival |
| rollback endpoint bound | `rollback-download-arrival.json` | publish rollback transfer intent |
| rollback attempt consumed | `rollback-intent.json` | invoke the exact rollback command once |
| rollback classified | `rollback-result.json` | observe only; never replay rollback |
| final state observed | `final-health.json` | publish terminal only if every terminal condition passes |
| campaign closed | `terminal.json` | no more device action |

If execution stops after an intent but before its result, a later invocation may
publish an `unknown`/`uncertain` result from the durable intent and read-only
state. It must not invoke that effect again.

The concrete `--resume` path validates the whole closed namespace and graph,
quiesces each intent-bound Odin cgroup before device observation, and derives a
missing transfer result from a complete raw receipt or publishes conservative
unknown. An observation-intent cut closes as `NO_PROOF`. A consumed physical
confirmation permits only its deadline-bounded initial observation and at most
one separately intended resume observation after an owner cut. Expiry, absence,
ambiguity, or listing/identity mismatch publishes a durable miss; later
endpoints cannot be rebound, and the arm or physical action cannot repeat.
Each recovery-block digest read is likewise preceded by a phase-fixed
one-shot intent and may reuse only its complete existing raw receipt.

## Exact transfer shapes

The candidate command shape is:

```text
/usr/bin/odin4 -a <EXACT_CANDIDATE_AP> -d <BOUND_USBFS_ENDPOINT>
```

It deliberately omits `--reboot`. After a completed Odin classification the
device remains at the attended handoff, and the operator performs one direct-
recovery key action already covered by `recovery-boot-intent.json`. This avoids
an intervening Android boot before the canary observation.

The rollback command shape is:

```text
/usr/bin/odin4 --reboot -a <EXACT_ROLLBACK_AP> -d <BOUND_USBFS_ENDPOINT>
```

The endpoint is not accepted from a CLI. It comes only from the current bound
Download arrival. The artifact and partition are not caller-selectable. The
connected owner must pin open Odin and the AP, revalidate both and the endpoint
immediately before dispatch, retain bounded raw stdout/stderr, and revalidate
the pinned files after return.

## Candidate classification and observation

Only `odin_transfer_completed` may proceed to the direct-recovery action. A
timeout, output overflow, endpoint identity change beyond an explicitly
reviewed re-enumeration case, missing completion grammar, nonzero return, or
host exception is `uncertain-consumed`:

- candidate replay is permanently false;
- the candidate recovery is not booted;
- `candidate-observation.json` records `NO_PROOF` without claiming rejection;
- recovery proceeds only toward exact-stock rollback.

On the completed branch, the physical recovery action occurs once. A future
connected observer may run only the frozen, no-input recovery script from
`s20plus_g986n_recovery_canary_t0_runner_h0.py`. It verifies:

- exact target model/device/product/incremental properties;
- a newly bound recovery boot ID;
- `service.adb.root=1`, `sys.usb.config=adb`, and `init.svc.adbd=running`;
- direct regular marker
  `/init.s20plus_g986n_recovery_adb_canary` with SHA-256
  `5aafd7ca6918bf82aef0b7de62346d8de1b17bb0c9ececafa15978cfae2c87b0`.

Arrival without the exact marker, observer timeout, an Android boot, Download
state, a foreign ADB row, or ambiguous USB state is `NO_PROOF`, not `REFUTED`.
It never permits candidate replay. The process immediately continues to stock
rollback.

## Mandatory stock rollback

Stock rollback is mandatory even after a successful canary observation. From a
healthy canary recovery, a future reviewed owner may use one fixed
`adb reboot download` only after `rollback-download-intent.json`. If recovery
ADB is absent or candidate transfer was uncertain, the owner uses the separately
bound attended physical Download handoff. It never sends a command to a foreign
ADB endpoint.

Once `rollback-intent.json` exists, rollback replay is permanently false. A
missing result, timeout, transport exception, or ambiguous Odin transcript is
`RECOVERY_PENDING`; it does not authorize another write. Read-only observation
may determine whether Android boots and whether the recovery block matches a
known digest, but a further repair attempt requires a new incident-specific
review and authority.

## Terminal outcomes

`PROVED` requires all of the following:

1. candidate Odin transfer classified completed;
2. one new recovery boot arrived;
3. the exact marker and recovery properties passed;
4. exact-stock rollback transfer classified completed;
5. exact healthy rooted Android returned on a later boot;
6. the fixed recovery digest read again reports size `82,694,144` and exact
   stock SHA-256;
7. no foreign target command, forbidden payload, replay, or unexplained device
   effect occurred.

`NO_PROOF` means the canary claim was not established but stock rollback and
final health passed. `RECOVERY_PENDING` means rollback or final health is not
proved. `REFUTED` is reserved for discriminating evidence that the exact
candidate was accepted for transfer but deterministically rejected before its
recovery init/marker could run; a mere timeout or wrong boot target is not
enough.

T1 is never authorized by this process. A T0 `PROVED` result only supplies one
review input for a separate T1 binding.

## Activation checklist

Before any live use, an independent reviewer must verify and a later commit
must mechanically activate all of these together:

- common `AGENTS.md` recovery-only T0 exception with unchanged permanent bans;
- a risk-tier definition that cannot leak into ordinary F1 or another target;
- an exact S20+ target-contract section and expiry/retirement condition;
- fixed stock-recovery digest read owner and its private evidence schema;
- connected T0 owner, Download/ADB selectors, durable journal, guard, raw
  evidence bounds, transfer classification, recovery branches, and finalizer;
- exact source and artifact hashes, hostile tests, and independent `PASS_GO`;
- a fresh attended prepared binding and approval after activation.

The dormant connected owner is 153,449 bytes at SHA-256
`c89ef6658e85c60c0d933acd4eb0d2acef6c86da58c032eb03d617c10018d9c4`,
normalized SHA-256
`33f5e9ae3b98327a78dec6168a458ef263816f3707d8edefcf9b5d2a7aee0c5e`.
Its 53,775-byte test at SHA-256
`6028cfc471a860e145df20e32b7c7d8425dd66c2c129ccff441c9ae985f931f6`
passes 43/43; the combined T0 owner/model/digest suite passes 78/78. The exact
instruction above is emitted only after candidate completion and before the
already-intended attended physical action.

Until then, the only permitted commands are the H0 render and host-validation
modes. `--connected` must return the dormant verdict without reading artifacts,
enumerating USB, invoking ADB, invoking `su`, or invoking Odin.
