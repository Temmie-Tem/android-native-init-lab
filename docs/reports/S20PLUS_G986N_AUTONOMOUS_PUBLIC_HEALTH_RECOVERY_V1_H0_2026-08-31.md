# S20+ autonomous public-health recovery-v1 store/scanner H0 qualification

Date: 2026-08-31

Target: Samsung Galaxy S20+ 5G (`SM-G986N` / `y2q` / `y2qksx` /
`G986NKSS8IYC2`)

Status: **H0_PUBLIC_HEALTH_RECOVERY_V1_STORE_SCANNER_PASS_GO_NOT_ACTIVE**

## Objective and qualified scope

Define the self-contained recovery source and fixed three-root storage model
that must exist before any device-capable autonomous public-health runner can
be reviewed. This unit may embed and equivalence-test retained-return parsers,
model a content-bound recovery manifest, scan exact fixture journals, and
host-test anonymous no-replace publication. It does not implement or authorize
zero-command finalization, terminal re-emission, an attended opening, an ADB
producer, a campaign, or any device command.

The qualified source and focused test are:

- `workspace/public/src/scripts/revalidation/s20plus_g986n_autonomous_public_health_recovery_v1.py`;
- `tests/test_s20plus_g986n_autonomous_public_health_recovery_v1.py`.

Exact reviewed identities after the narrow status rotation are:

- source: 133,053 bytes, SHA-256
  `6186221593b3778475bf3b1ac4bd28bfe013534793eca4ce5fbe0007be8eb0c3`,
  activation-normalized SHA-256
  `1b769167018a2a08e71e67adc00c20148eb4e0a11a6c428bf8fc82b517533b5d`;
- focused test: 76,583 bytes, SHA-256
  `620d807c8038c145e738d08f4d05ca10e8e8a65e8c7881ecfc1cef8d69a50978`.

Independent exact-byte review returned `PASS_GO` only for the named inactive
parser/manifest/store/scanner model. Focused tests passed 76/76 and all six
autonomous H0 suites passed 216/216; `py_compile`, render-plan, and scoped
`git diff --check` passed. No private recovery bundle has been installed.

## Permanent dormant boundary

The public source exposes only `--render-plan`. Its qualification, scanner,
writer, finalizer, re-emission, manifest, contract, and live-authority gates
begin false. `SELF_CONTAINED_FINALIZER_IMPLEMENTED` is also false. Direct
entrypoints reject before accessing private state, and an unbound future-runner
identity hard-stops installation or scanning even if booleans are changed.

The source imports no subprocess, socket, ADB, USB, or device backend. Its
device-command, device-effect, root, control, payload, partition, R1, and F1
surfaces are empty. It grants no recovery authority: its presence-only cut
classifier always leaves settlement unproved, and its finalizer/re-emission
functions have no implementation.

## Self-contained parser boundary

The recovery source embeds the exact target, schemas, fixed six-command
transcript, snapshot literal, parser grammar, counter equations, evidence
receipt ancestry, 19-file manifest rules, and parked-completion shape. It
records these qualified oracle identities without reopening them at runtime:

- base coordinator SHA-256
  `87ad2dcdcf28d33192ca85bca3f440c87fb7609272dadab297f5b3c6397866dd`;
- health model SHA-256
  `03abc4fe5cbe258c0f8eafce27f1230960dc448af616a8f8a14b0e1809baaa4b`;
- inventory SHA-256
  `3c89eaa348ec7a3a06a3ae2a0de227c781c97238b4e8f33e62b6e0bd370eec81`;
- evidence owner SHA-256
  `1f737347330b5a2ed1c85e51cca852309ba25e15e7a68d59f6bd6bb4961ba0c4`;
- read leaf SHA-256
  `e2952245bf4433044fae12ff8114ee9ff4239cbacd173a83cdc5a3dfcfa3d2c6`.

Tests may load those public oracles only to compare semantics. Production
recovery code must remain usable after all five public paths are hidden,
deleted, or rotated. Simply copying an oracle would not satisfy this property
because the oracle reopens current public paths.

## Exact parser and identity closure

The retained accounting opening must contain the exact frozen absolute source
receipts, not merely matching basenames. Guard, opening, session, accounting,
lease, and intent are revalidated as one chain. The intent is reconstructed as
the exact lease mirror, and chronology is strict:

```text
base opened_at <= accounting recorded_at <= lease issued_at <= intent mirrored_at
```

Typed validators reject nested boolean/integer substitution, floats, and a
coherently rehashed chain that rewinds any time or reservation. Result and
completion still require the exact raw evidence hashes and parked flags.

The recovery/runner identity DAG is non-circular. Normalization replaces the
single expected-recovery anchor, future-runner binding block, status, and
reviewed booleans exactly once. The source embeds and verifies normalized hash
`1b769167018a2a08e71e67adc00c20148eb4e0a11a6c428bf8fc82b517533b5d`.
An arbitrary core, zero anchor, or unbound runner cannot install or scan. A
future runner may bind its normalized identity without changing this recovery
normalized identity; the manifest still binds the final full core bytes.

The same module's globals, self-read `__file__`, and direct private pathname
execution are not independent provenance. The future runner and loader must
pin the reviewed recovery normalized identity and independently verify the
private manifest/core before compiling it.

## Fixed roots and lock

The modeled roots are exact absolute paths under `workspace/private/runs/`:

1. `s20plus-g986n-autonomous-research`;
2. `s20plus-g986n-autonomous-public-health-evidence`;
3. `s20plus-g986n-autonomous-public-health-read-leaf`.

No caller supplies a root, component, filename, campaign/session ID, or output
path. Managed roots and descendants require the current effective UID/GID and
mode `0700`; every path component is opened from `/` with directory FDs and
`O_NOFOLLOW`. Host ancestors above the managed roots are no-follow checked but
are not claimed to have mode `0700`. Same-UID hostile replacement remains
outside the lane and is not solved by permissions.

Before creating a lock or directory, the store validates the bound core and
preflights all three roots; any foreign root or namespace fails with no
mutation. Fixed roots and the recovery directory are reopened and compared
after modeled installation. Every accumulated directory FD is closed in
reverse on success and at each intermediate failure depth.

The fixed leaf `coordinator.lock` is a direct zero-byte regular file, mode
`0600`, link count one, and matching owner/group. First creation is exclusive,
file-fsynced, and leaf-directory-fsynced. A nonblocking exclusive `flock` is
held while the scanner/store owns the roots. This serializes cooperative code;
it is not authentication against an unreviewed same-UID writer.
If creation previously cut during fsync, the exact existing lock is file- and
directory-fsynced and identity-revalidated before retry proceeds.

## Recovery bundle and manifest DAG

The future leaf namespace begins with:

```text
coordinator.lock
recovery-v1/
  recovery-core.py
  manifest.json
```

`recovery-core.py` is at most 256 KiB; `manifest.json` is at most 32 KiB;
their aggregate is at most 288 KiB. Core publishes first and manifest last.
The manifest omits its own hash to avoid recursion and binds:

- exact core name, size, mode, and SHA-256;
- exact target, roots, schemas, transcript, property keys, and caps;
- all five oracle identities;
- a future integrated-runner normalized identity and binding JSON hash;
- zero-command-only entrypoint declarations; and
- no replay, refund, next action, or live authority.

The current future-runner binding is deliberately
`UNBOUND_PLACEHOLDER` with a zero hash and `binding_complete=false`. Therefore
the current source cannot materialize a production bundle. A later reviewed
runner rotation must replace and bind it before manifest qualification.

Directly executing the private pathname is not provenance. A future immutable
loader must open the core no-follow, validate manifest and core bytes, then
compile those already-verified bytes. That loader and source-retention policy
remain unimplemented.

## Anonymous no-replace store model

The host-tested publication primitive accepts only the two recovery-bundle
final names and their role caps. It uses:

1. a held parent directory FD;
2. `O_TMPFILE` with no named temporary fallback;
3. complete bounded writes and mode `0400`;
4. file `fsync`;
5. `linkat(AT_EMPTY_PATH)` no-replace;
6. parent-directory `fsync`;
7. reopened final inode/device/mode/owner/link/size comparison to the anonymous
   inode; and
8. exact reopened byte comparison.

An exact existing final is revalidated, directory-fsynced, reopened, and
consumed without replacement. A different existing final, symlink, hardlink,
special node, short write, unsupported `O_TMPFILE`, link failure, or fsync
uncertainty stops. There is no rename, unlink, rmdir, refund, or repair by
replacement.

All expected regular-file and lock opens add `O_NONBLOCK` before type checks,
so FIFO opens cannot block; an opened non-regular node is then rejected by
`fstat`. This does not claim every device driver's open behavior is bounded.
Directory enumeration is lazy and stops at the exact directory-specific
maximum plus one before sorting; the largest accepted set is the 19-file
evidence directory. Repeated malformed intermediate evidence paths must leave
the process FD count stable.

This primitive is not active. Host tests exercise it under isolated temporary
roots; no production private final is written by this unit.

## Storage closure

The future complete public-health-only campaign has closed categories:

- recovery bundle: 288 KiB, two files;
- attended-opening evidence: 544 KiB, 21 files;
- campaign binding: 16 KiB, one file;
- existing structural journal: 48 KiB, eight files;
- ordinal-1 evidence: 512 KiB reservation, 19 files;
- total: 1,441,792 bytes and 52 regular files including the zero-byte lock.

No metadata file is free. Adding a loader receipt, clock node, source receipt,
or terminal requires recapping and review. The current scanner grammar models
only the already-qualified base/evidence/read-leaf subset and recovery bundle;
it intentionally rejects future `opening-v1` and `campaign-binding` nodes until
the integrated runner rotates the exact grammar and caps.

## Scanner and cut classification

The inactive scanner holds the leaf lock and exact root FDs, enforces closed
namespaces, parses strict canonical duplicate-key/nonfinite-rejecting JSON,
validates direct regular file identities, and re-derives retained health,
result, and parked completion only when all required bytes exist. It never
consults a device or current public oracle source.

The pure presence classifier distinguishes:

- pre-opening complete/partial/no recovery bundle;
- opening without a lease;
- lease without mirror;
- incomplete retained returns (`uncertain-consumed`);
- all 18 pre-health files as an unproved derivation candidate;
- exact 19 files without result;
- result without completion; and
- completion requiring full revalidation before re-emission.

It never sets settlement or zero-command finalization authority true. An empty
read directory before the exact intent is outside the publication order and
must stop. Missing raw or receipt bytes remain parked and never permit command
replay or refund.

## Unimplemented recovery behavior

The embedded pure functions are preparation for a later finalizer, not a
finalizer. `finalize_zero_command()` and `reemit_terminal()` remain hard-gated
and unimplemented. A later unit must:

- verify a bound private manifest/core through the immutable loader;
- publish an exact missing mirror only from the retained lease;
- derive missing health/result only from all retained raw/receipt bytes;
- publish exactly one missing parked completion;
- re-emit an existing terminal only after full validation; and
- prove every write/fsync/link/reopen/reporting cut without any device access.

No source rotation, expiry, disconnect, or boot drift can grant a command. The
future finalizer must work through retained bytes only.

## Review and activation gates

1. Implement and independently review the missing immutable loader,
   zero-command finalizer, re-emission path, and every publication cut.
2. Implement the separately attended opening plus fixed six-command producer;
   bind the future runner and expand scanner grammar/accounting exactly.
3. Review the combined closure and only then rotate target-contract and live
   registry authority.
4. After activation, require one fresh exact-target/current-boot attended
   opening. Pre-activation requests remain non-bankable.

## Work performed

This unit adds the exact H0 recovery source, hostile tests, and this report. It
runs no ADB, USB, `su`, root, device network, reboot, Download, Odin, payload,
partition, R1, F1, campaign, private recovery installation, or live evidence
action. The only promotion is `PASS_GO_NOT_ACTIVE` for the named parser/
manifest/store/scanner model. Whole recovery-v1 qualification, recovery
authority, every operational gate, and activation remain false.
