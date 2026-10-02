# S22+ fixed native_data journal recovery V1

Status: **REVIEW_GATED_CAPABILITY**. H0 preparation opens no device grant.
Only `SM-S906N/g0q/S906NKSS7FYG8`, its unchanged Android32 GPT and native_data
entry 41 are selected. Profile:
`thermal-v3-reconnect-ufs-drain-journal-recovery-v1`.

This is a separate, narrow filesystem-write exception to common boundaries
2 and 3. It does not activate or repeat P410/P411, the installer, ordinary
fsck repair, formatting or another Debian boot. Its implementation and
higher-precedence incorporation require independent source-bound review.

## One attended operation

Use V3 `journal-recovery`, a fresh archive-free boot-only N, one returned
finite attended grant, one operation and at most 1800 original BOOTTIME
seconds. Exact rooted original-A health, Android32/GPT geometry, the readable
hash-verified original A and demonstrated attended Download recovery precede
the sole N transfer. H0/offline preparation does not prove current health.

```text
original-A health -> Download -> one N -> authenticated native health
  -> original pre-EXEC effect intent -> protected native_data binding
  -> eligible dirty root: one partition RO clear and one strict writer
  -> conclusive child/descriptor settlement -> partition RO restoration
  -> fixed e2fsck -fn -> noload/RO/noexec inspection and full root comparison
  -> authenticated DETACH/close -> fresh same-boot health -> Download
  -> one original A -> full original partition/GPT/Android32 health
```

The existing authenticated console and PID1 retain ownership. There is no
worker retirement, switch_root, installed executable, service, NCM/SSH,
ordinary Debian reboot or shutdown command. The complete helper command is
bounded by 240 seconds and the original observation by 300 seconds. Each
child has a 150-second wall limit; the writer CPU limit is 120 seconds and
the checker CPU limit is 25 seconds. Outer command timeout/cancellation
owns the original process group and never creates a second writer.

The single pre-EXEC intent consumes the complete operation, including a
possible partial write, rejected result or lost response. Never repeat EXEC,
the writer, N or an uncertain control/transfer. The normal and recovery paths
share a one-A maximum. Proved A with incomplete health permits only the
existing health continuation.

## Exact write surface

The parent reuses exact UFS/LU0 ancestry, complete sealed GPT, capacity,
4096-byte geometry, native_data identity, no-holder/no-mount checks and the
partition-only RO ioctl/sysfs readback. The whole LU and userdata are never
made writable by a control operation. Its private tmpfs native_data alias is
the only write operand; the LU alias remains read-only.

Before a writer, require the original primary-superblock checksum, exact
sealed UUID, geometry/features/internal journal inode 8, state 1, RECOVER=1,
zero orphan head and no filesystem error count. An already clean filesystem
skips the writer and proceeds to protected admission. Other initially
ineligible state stops without data writes.

The pinned static ARM64 strict replayer accepts no options or caller path.
Its entry bypasses ordinary e2fsck options/configuration, restart, repair,
superblock checks that clean orphans, and passes 1–5. The upstream `-E
journal_only` option is not used: it can repair journal metadata, reach
orphan cleanup and report exit zero after a replay error.

Only the existing internal V2 journal, exact UUID and journal inode size,
supported checksum V2/V3, supported revoke/64-bit features, valid ring bounds
and zero journal error are admitted. External journals, backup-inode repair,
fast commit, discard, alternate superblocks, undo files and ambient
configuration are excluded. All journal mappings and every read/write are
bounded within the exact partition. Replayed home blocks cannot overwrite
the journal's own mapped blocks.

Allowed data writes are JBD2 replay of committed, non-revoked blocks, followed
only on success by the journal head/sequence/checksum finalization and the
primary superblock's RECOVER/checksum update. Preserve other bytes and verify
the final complete 4096-byte blocks. No `s_wtime`, group descriptor, orphan,
inode repair or backup-superblock update is added by finalization. Replay may
itself reproduce committed filesystem/data changes. A logical payload error
can coexist with partially replayed other blocks; this is a consumed negative
result, never an unchanged-disk claim.

The dedicated I/O manager has no write cache, implicit close flush or retry.
Short I/O and failed flush/readback/close are errors; a sticky I/O failure
blocks later writes and finalization. Success requires replay and data flush,
fresh superblock admission including zero orphan head, checked journal-header
write/flush/readback, then checked primary write/flush/readback and close.
Exit zero alone is insufficient: validate the strict result and write-count
accounting. A completed writer has both finalization writes.

The writer/checker close borrowed descriptors, retain the inherited command
group, drop all capabilities and supplementary groups, set no_new_privs and
run only their pinned image-owned executable. UID/GID 0 retains access to the
owned block alias; it does not retain capabilities. No filesystem is mounted
writable or used to load code or configuration.

## Post-replay proof and return

Only after conclusive child and descriptor settlement may the parent restore
partition RO and verify it. Then run the separate pinned `e2fsck -fn` and
protected `ro,noload,nodev,noexec,nosuid` mount. Require original installation
markers/witness, all P401 archive paths and immutable bytes, empty lost+found
and precisely the [P410 mutable-data bounds](S22PLUS_DEBIAN_HANDOFF_V2.md#current-root-admission-after-p410).
No additional mutable path or byte exception is introduced.

The post-replay protected segment must preserve its new superblock baseline
and the original GPT through unmount/cleanup. This new baseline does not
overwrite the recorded pre-replay digest or imply that replay made no change.
Writer completion, checker completion, exact root admission and Android
closure are separate claims.

A completely observed rejection may use the fixed normal authenticated
return only with all children reaped, no inherited writer descriptor,
confirmed partition RO, completed helper cleanup and no unresolved I/O.
Malformed/incomplete output, timeout, unsettled child or I/O uncertainty stops
for the original attended physical Download/original-A recovery. A later
read never retroactively proves or repeats the failed writer.

Original A restores boot and Android health; it does not undo native_data
writes or prove that filesystem clean. There is no transactional filesystem
rollback or guaranteed recovery of Debian data, and a failed replay may leave
a partial native_data state. Further repair or a new Debian handoff requires
its own selected scope after this operation closes healthy.

## Evidence and capability lifetime

Retain one task/grant, append-only intent/result journal, bounded private raw
console bytes and terminal, plus the target timeline and incident/capability
report. A parser/report failure permits rederivation only. Preserve consumed
source snapshots and pins; never repin P410/P411 to the new implementation.

Qualification covers real ARM64 committed/revoked/uncommitted journal data,
pre-write rejection, replay-revealed orphan state, partial writes and failed
flush/readback/close, kernel partition RO and protected root comparison,
timeout/child settlement, original-A/no-replay owner behavior and actual A/B
payloads. VM evidence does not establish Samsung I/O or USB behavior.
This permanent narrow exception is reviewed when its write, privilege,
target, proof, health or recovery semantics change; routine fresh candidate
data does not expand it or reopen a consumed grant.
