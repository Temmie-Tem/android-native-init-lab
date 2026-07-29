# S22+ FYG8 P2.86 Full-LTO private-path reproducibility failure H0

Date: 2026-07-30 KST
Tier: H0, host-only build attribution
Candidate run ID: `c6cde593033d6f1be93f82c8ff5a81e8`
Source contract: `s22plus-fyg8-p286-parent-tail-bounded-restart-v1`

## Verdict

```text
FAIL_CLOSED_P286_FULL_LTO_AB_RANDOM_PRIVATE_PATH_LEAK_HOST_ONLY
```

The first P2.86 Full-LTO A/B pair is invalid and cannot be promoted. Its only
linked-byte difference is an unmapped random private build-root token embedded
in DWARF line data, plus the GNU build ID derived from that content.

This is not Full-LTO code-generation or BTF nondeterminism. No source receipt
changed, no candidate was packaged or promoted, and no device action occurred.

## Exact byte attribution

The two `vmlinux` files have equal size. `cmp -l` reports exactly 1,124
different bytes:

```text
138 path-token occurrences * 8 changed bytes = 1,104 bytes
GNU build-id descriptor                         =    20 bytes
                                                   -----------
                                                     1,124 bytes
```

The source and destination token each occur exactly 138 times. Every occurrence
belongs to a full clang-resource path string, their absolute offsets match
between A and B, and there are no unrelated token occurrences.

All 138 path tokens are in `.debug_line`. Removing their expected difference
set leaves one contiguous 20-byte residual. That residual is wholly inside the
GNU build-id descriptor in the allocatable ELF `.notes` section and equals the
build ID printed by `readelf -n` for each file.

The raw arm64 `Image` differs by exactly 20 bytes. Its difference interval is
the same GNU build-id descriptor mapped through the loadable `PT_NOTE`; it is
the `vmlinux` residual shifted by the exact Image load offset. No other Image
byte differs.

The following retained linked artifacts are byte-identical:

- `.config`;
- `System.map`;
- `vmlinux.symvers`; and
- `abi.xml`.

The evidence therefore proves that the random path and its derived build ID
exhaust the A/B mismatch.

## Cause

`s22plus_fyg8_p286_build.py` appends:

```make
KBUILD_AFLAGS += -fdebug-prefix-map=$(realpath $(abs_srctree)/../../..)=/private-repo
KBUILD_CFLAGS += -fdebug-prefix-map=$(realpath $(abs_srctree)/../../..)=/private-repo
```

This expression maps the parent of the selected kernel work tree. Its coverage
depends on directory layout.

P2.84 used a repository-root work tree and a sibling clang repository. The
expression therefore covered both, and both lanes retained only stable
`/private-repo/...` paths even though their private namespace tokens differed.

P2.86 used:

```text
work tree  -> workspace/private/work/<tree>
clang repo -> workspace/private/inputs/toolchains/<repo>
```

The expression covered `workspace/private/work` only. The clang repository was
outside that prefix, so the private namespace root survived in clang resource
include paths.

Both runs used eight jobs. The timestamp, build user, build host, build version,
patched Makefile bytes, linked layout, and non-path linked outputs were fixed.
Those variables are not needed to explain the observed difference.

## Selected bounded correction

P2.86 keeps all 70 selected source bytes and its existing intent. The pinned
clang repository is copied as a real directory below the mapped work-tree
parent, and only the private `--clang-repo` invocation path changes.

A symlink is not sufficient because the build resolver canonicalizes it back
to the original path.

The build accepts the relocation using content identity:

- expected and actual Git commit;
- clean Git work tree;
- required clang version markers; and
- effective-tool size and SHA256.

The configured path is recorded as provenance but is not the toolchain
acceptance identity. The P2.86 build-result verifier does not require the old
toolchain path.

Before Full-LTO, an actual relocated copy passed:

- the pinned commit and clean-work-tree checks;
- exact clang executable byte identity;
- all 17 effective-tool `(size, SHA256)` comparisons; and
- a debug-prefix microcompile that removed both old and new unmapped resource
  paths and retained only `/private-repo/toolchains/...`.

## A-before-B stop gate

After the corrected A build, and before starting B, scan A `vmlinux` for:

1. the random private namespace prefix; and
2. an absolute host/tmp clang resource include path.

Both counts must be zero. The stable `/private-repo/toolchains/...` path must
be present. Any nonzero leak count stops the pair; B must not start.

Only a passing A leak scan permits one clean B build and the ordinary
byte-identity verifier.

## Deferred identity debt

The incident proves a structural gap:

```text
build layout can affect candidate bytes
while build layout is outside SOURCE_KEYS
```

All 70 source receipts can match while directory placement breaks
reproducibility. The selected relocation closes P2.86 without changing source
identity, but it intentionally leaves the fixed-relative-depth assumption in
place.

The durable alternatives are:

- make the build mapping independent of work-tree depth; or
- bind the accepted build layout in the candidate/build manifest.

Either is a later design and identity change. It is deferred until after
P2.86, alongside the P2.64 identity-split debt. This report grants no F1
authority.
