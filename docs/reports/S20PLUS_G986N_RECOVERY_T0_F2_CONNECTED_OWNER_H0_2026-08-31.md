# S20+ G986N recovery T0 F2 connected-owner H0 record

Date: 2026-08-31
Target: `SM-G986N` / `y2q` / `y2qksx` / `G986NKSS8IYC2`
Result: **ACTIVATED_AFTER_INDEPENDENT_PASS_GO_COMMIT**

## Outcome

The boot-carrier B0 surrogate is no longer the selected next experiment. This
unit implements a separate concrete owner for the actual recovery-partition T0
canary and the matching common F2 and target-specific exception. Dormant review
returned `PASS_GO` with HIGH/MEDIUM/LOW `0/0/0`; the activation becomes binding
only when its separately reviewed complete diff is committed. Qualification
sent no ADB, `su`, USB, reboot, Odin, or device command and performed no
partition read, write, transfer, or format.
S22+, A90, and every other target received zero commands.

The existing T0 ramdisk already uses a fixed attended root-adbd configuration:
two exact `ro.adb.secure=1 -> 0` substitutions, `ro.secure=0`,
`ro.debuggable=1`, an exact boot trigger for ADB, and a read-only marker. A
host ADB public key was therefore not added. Baking a key would introduce a new
private-input binding and a separate unproved recovery-adbd lookup path without
improving the first attended acceptance test.

## Exact artifacts

The previously built candidate and rollback revalidated without drift:

| Item | Size | SHA-256 |
|---|---:|---|
| candidate recovery-only AP | 36,556,841 | `30227458889f1fa99eca192c9b7f8747f168d9e33cc1f407b52ae2b4d298559a` |
| candidate `recovery.img.lz4` | 36,547,618 | `7f0e6b53a1036904fd02c5e8c2c014d3112ffb58fc33f9aa9a26c0962af45928` |
| candidate decoded recovery | 82,694,144 | `e1297613df576d25cc9391df97dac7cf316fee545f56111e6bc5340cb8ce659b` |
| exact-stock rollback AP | 36,608,041 | `ac9745b642c7fbd950d988671f707e47d58f8e2092464b27a37bede2267d7157` |
| rollback `recovery.img.lz4` | 36,600,544 | `6b962af2fc4fcc424d16ecdcee1793bdd6d4c8dba2e80d35cb21961fcb865923` |
| exact-stock decoded recovery | 82,694,144 | `dd797bc0a462d2486ff71c020e89d1137df46299374e48855012e36e86f97e0e` |

Each AP has a valid appended MD5 and exactly one deterministic regular member
named `recovery.img.lz4`. Neither contains boot, VBMeta, DTBO, BL, CP, CSC,
super, userdata, persist, EFS, misc, or another member.

## Concrete owner

The activated owner is
`workspace/public/src/scripts/revalidation/s20plus_g986n_recovery_canary_t0_f2.py`:

- size: 153,798 bytes;
- SHA-256:
  `a91d45e14f4cb82f10a83a8c2bdc38126deb20b9b841918888ec45842ad51e75`;
- activation-normalized SHA-256:
  `82a357b96f5b7cc03868d5c174d70f5b3d66a4aa2525482e14bd862e40d5425b`;
- `T0_F2_ACTIVE=true`.

Its closed CLI has host-only render/validation and the active named operations
`prepare`, `execute`, `observe-recovery`, `abort-pre-candidate`,
`arm-physical-rollback`, `confirm-physical-rollback`, `resume`, and `finalize`. It accepts
no caller artifact, path, partition, serial, endpoint, shell fragment, command,
property, executable, or output destination.

The direct-Recovery instruction is fixed rather than improvised at runtime:
keep USB connected; hold Side/Power plus Volume Down until the screen is fully
black; keep Side/Power held while immediately switching to Volume Up; continue
until Recovery appears, without allowing Android to boot. This sequence is
consistent with the Galaxy S20/Note20 installation instructions in
[`ExtremeROM`'s source guide](https://github.com/ExtremeXT/ExtremeROM/wiki/Installation-Guide)
and the same afaneh92 Snapdragon recovery lineage's
[`t2q` guide](https://github.com/afaneh92/android_device_samsung_t2q).

Preparation is read-only: exact rooted Android health surrounds the fixed
stock-recovery SHA-256 profile, then an empty Download baseline is recorded and
one short-lived exact approval is emitted. Only approval consumption can record
the initial Download intent. A missing Download arrival creates no candidate
claim or candidate intent and may close only after attended payload-free/manual
return plus exact Android and stock-recovery health.

Each possible recovery-block read has its own no-replay intent: preparation,
execution pre-transfer, and either final health or pre-candidate abort. The
owner validates a closed regular-file namespace and exact predecessor graph;
root, recovery, reboot, observer, and Odin claims are rederived from their raw
capture receipts. `--resume` first quiesces every intent-bound Odin cgroup. A
missing transfer result becomes raw-derived or conservative unknown and is
never resent; an observation-intent cut becomes `NO_PROOF`; a consumed
physical confirmation allows at most one deadline-bounded resume observation.
Expiry, absence, ambiguity, or a listing/identity mismatch publishes a durable
miss, so a later endpoint cannot be rebound and no second physical action is
inferred.
The final-health wait retries only genuine target absence; ambiguity, malformed
inventory, wrong state, or prepared-serial/metadata mismatch stops on its first
observation.

The candidate SHA-256 has a permanent global no-replace claim. Candidate and
rollback intent each precede a single caged Odin process and permanently remove
replay. The candidate command omits auto-reboot and the rollback command uses
only the exact-stock recovery AP with auto-reboot. Open Odin/AP/shell
identities are checked across dispatch; bounded raw streams and process-cage
quiescence precede later action. The recovery observer binds the original
serial/topology, a fresh boot, exact IYC2 identity, root-adbd properties, and
the canary marker. Terminal closure requires later rooted Android health and a
fresh read proving exact stock recovery bytes.

## Validation

The focused owner suite passes 44/44. Together with the prior H0 T0 journal/AP
validator and fixed recovery-digest profile, 79/79 tests pass. `py_compile`,
host validation, and `git diff --check` pass. The revision-5 consumed-state
assertion rotation makes the focused test 54,712 bytes at SHA-256
`685437ceff6879f01e10eeedc4c13da5f78dcd6232ac3fc08b2351b1de11efe6`;
the reviewed T0 execution model and owner identity remain unchanged.

## First live-run incident and repair

The candidate recovery transfer completed once. Before the first recovery ADB
inventory, `--observe-recovery` rejected `candidate-download-arrival.json`.
The reused `b0.wait_download()` producer records `b0.digest(baseline)`, whose
canonical durable JSON includes a trailing newline; `_validate_arrival()` had
incorrectly compared the distinct T0 no-newline binding digest. The durable
arrival is internally consistent with its producer and was not rewritten.

The repair changes only that validator edge to `b0.digest(baseline)` and adds a
hostile regression proving that the producer digest is accepted and the T0
binding digest is rejected. It performs no device action, does not widen an
artifact, target, partition, endpoint, command, or replay rule, and preserves
the consumed candidate plus exact-stock rollback. Continuation remains the
same run journal after independent incident-diff review and commit.

## Activation and remaining live gate

The activation transition changes only the reviewed boolean/status-derived
plan, exact identities and tests, F2 status text, the single S20+ registry row,
and goal/report wording. It requires independent activation-diff `PASS_GO` and
the complete commit; a partial or uncommitted working tree grants no device
authority.

Four existing document-assertion tests rotate only to the one active registry
row and F1/F2 target header:

| Test | Size | SHA-256 |
|---|---:|---|
| onboarding D0 | 13,402 | `7bcd65e8030156f1aa026f248775afb962163df3f5b41b0c2ce5eba90e91bfab` |
| routine D0 | 12,430 | `fdbc8ffc19a520b5d4a12cf0cbd26ff1ab033832ed3d12d3f9fca210c37a1712` |
| routine actions | 37,302 | `1a258784ffdf2fb1596a494f174c506fe4cad54bf6b04be22832eba206694a8f` |
| bootstrap F1 | 96,507 | `650734d33662bd1d0cedeb671e592028f8699e085a65dd5fa56b87a8fb5aec63` |

After that commit, activation created no run or standing approval. The first
live step was a fresh attended prepare, followed by the exact returned approval
and the now-consumed single candidate transfer. A fresh prepare or candidate
replay is no longer available. The current next step is recovery observation,
exact-stock rollback, and final health from the same durable journal.

T1 remains ineligible. A later T0 `PROVED` result is evidence for a separate T1
review and never authorizes the TWRP image by itself.
