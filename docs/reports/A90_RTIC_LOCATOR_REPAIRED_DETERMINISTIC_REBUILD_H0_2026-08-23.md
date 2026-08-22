# A90 RTIC locator-repaired deterministic rebuild — H0

Date: 2026-08-23
Target: Samsung Galaxy A90 5G only
Tier: H0 private-host deterministic rebuild and artifact analysis
Device contact: none
Authority: none — no candidate identity, boot image, manifest, D0, D1, F1,
approval, journal, transfer, reboot, rollback, replay, or live authority exists

## Verdict

The two known static defects in the stock-shaped public-MPGen rebuild are
closed. The unmodified historical MPGen now locates the three exact kernel
objects and emits task offsets `88/1704/1728/2144` in every MPGen pass. Two
fresh, initially empty output trees produce byte-identical `vmlinux`, raw
`Image`, MP C/XML/DTS/DTB, `System.map`, and initramfs bytes.

Both independently assembled H0 comparison wrappers pass
`a90_rtic_mp_consistency.py`: one `rtic_mp`, one RTIC DTB, one `MP_DATA`, MP
VA `0xffffff8009f00000`, raw-Image offset `0x01e80000`, size 1,624, interface
`30.3`, marker present, in-range bytes, and exact expected/actual MP SHA-256.

This is not a boot result. The non-stock public MPGen content version,
candidate-derived measured extent, public catalog/tool provenance, proprietary
RTIC/QHEE acceptance, and any proprietary whole-Image enforcement remain
unproved. Those residual facts form one previously reviewed canary hazard
bundle; they are not erased by structural consistency or deterministic bytes.

## Exact retained inputs

The final pair reused the previously bound input closure without source or
configuration edits:

| Input | Exact identity |
|---|---|
| A908N OSRC `Kernel.tar.gz` | `403fdc49f086d238c01a796c390083c3c47c1754c218e228f29b55cc7c35d554` |
| selected `.config` | 188,380 / `e4b7fa2f4fd6055eecfc7fd7b7546ab3e77ffdaf8ee77da27c9f341646f77f8b` |
| Snapdragon LLVM 10.0.7 `clang` | 96,189,952 / `453971166fa1b628df189e602f355cb2c58c12cd289515400ee6260c9a83459d` |
| GNU 4.9/gold repository | `606f80986096476912e04e5c2913685a8f2c3b65` |
| historical public MPGen commit/tree | `381c7b77b9e47d4cf81d9a9ac2b9e7597ec9b3e5` / `1b75830441422a5bd2380b1b5871d6768f43ef20` |
| historical `mpgen.py` / catalog | `7c21589480f95e5901d4cbcdc4d9c5a8d819cb9857014a3e27cd952a8082af88` / `decf021c9f7cb518bf2b9ba24b10548df49e766492ec133df7b2977484a599c4` |
| retained X.509 | 1,324 / `c773e5d46d151f8e10e966c1fbeba21dd49213dc80d057ecc9a7e200a8bc26db` |
| fixed-clock wrapper / launcher | `b086170d3c9be044d5cae405547e7e22cd51cf29316f60aa5f2b569e019596c9` / `f2609961db419722f85bde1b36d38df217e206473f73a9200a565cb1e6a392b0` |
| locator-repair build wrapper | `6eaddbf3ffdbd222b4f4c90e9cab909e8510710d403ca05641fbe27ca84c466c` |

The MPGen Git subtree was clean before and after the final builds. The
stock-fixed MP clock remained `2023-01-12T09:54:31Z`; the kernel build inputs
retained `SOURCE_DATE_EPOCH=1673517220`,
`TIMESTAMP=2023-01-12T09:49:35Z`, and
`KBUILD_BUILD_TIMESTAMP='Thu Jan 12 18:53:40 KST 2023'`.

## Locator and path repair

The public locator takes the basename of `DW_AT_comp_dir`, searches for that
component in `DW_AT_name`, and derives the corresponding object path beneath
the compilation directory. An out-of-tree directory such as
`out-stock-shape-fixed-d` does not occur in the source pathname, so the old
run found no object even though all necessary DWARF data existed.

The repair is entirely outside MPGen and precedes linking:

1. one fixed logical object-map path ending in `source` points to the current
   fresh output tree for the duration of that sequential build;
2. `-fdebug-compilation-dir=<fixed-object-map>/source` makes every C
   compilation unit name that same logical directory;
3. `-Wa,--debug-prefix-map,<real-output>=<fixed-object-map>/source` makes the
   external GNU assembler normalize vDSO DWARF to the same directory; and
4. the two output trees are built sequentially, never concurrently, so the
   one logical mapping cannot cross-bind objects.

No MPGen, catalog, kernel source, generated MP, `vmlinux`, build ID, or Image
byte was hard-coded or patched after linking.

The first diagnostic build proved the C-side locator repair and emitted all
four offsets, but showed that the external assembler still retained its real
vDSO output path. It was rejected before a comparison partner was built. The
GNU assembler's supported `--debug-prefix-map` was then added and two new
empty output trees were built from the beginning. Their C and vDSO
`DW_AT_comp_dir` values both name the one fixed logical path.

## Object and producer evidence

The mapped objects are identical across final A and B:

| Object | Size | SHA-256 |
|---|---:|---|
| `init/main.o` | 361,904 | `69cc2ab41e6f91ca10c0cf7fc090914b62fd5b652d3a235a5d3fa2b5dfa12aad` |
| `init/version.o` | 39,344 | `9484a1133fc8048a588940096e31e9201dee7164671790715dfc447f840a1a80` |
| `init/init_task.o` | 198,848 | `8a14c7826f0e8f94c836e5d6ec999505612163db6711718670c82edc15b77757` |

The unchanged direct-object decoder returns
`state=88, pid=1704, parent=1728, comm=2144`. The automatic locator feeds the
same objects to all three MPGen invocations, and `.tmp_rtic_mp1.c`,
`.tmp_rtic_mp2.c`, and final `rtic_mp.c` each contain exactly
`{88, 1704, 1728, 2144}`. No `0xffffffff` sentinel remains.

Each final log contains three `COMPLETE: GREAT SUCCESSS` MPGen terminals,
then RKP/CFP instrumentation and a completed FIPS HMAC update. There is no
MPGen traceback, catalog failure, locator failure, or fatal build terminal.
The long-standing host/Kconfig warnings and absent generic DTS-directory probe
remain nonfatal and are not relabeled as clean output.

## Pairwise deterministic outputs

Every selected final artifact is byte-identical across A and B:

| Artifact | Size | SHA-256 |
|---|---:|---|
| raw `Image` | 48,830,480 | `1ddae56f8df97030794a590192e4a4162876736029b1a54fd26173c9287002b7` |
| `vmlinux` | 475,447,112 | `46d92aca9526ff7851d4fc6f4a3a962e36aac4672196e271869d8d68c6581135` |
| `System.map` | 6,363,557 | `01df7d8ad1915ef64a48916dd3fee19aadf57005777fb73ad6ebad8e15ff31db` |
| final `rtic_mp.c` | 20,190 | `40ce65d99bc380a5ea607cff064813c6211474e4ae7077bf06cff70e448b7ad2` |
| `rtic_mp.xml` | 2,282 | `6d050ebdcec3e6f92665c58d6828aac381e2bb94a6c097152baa439fee1e1289` |
| `rtic_mp.dts` | 234 | `fc760b76a13e7580219c67a690b9b8eb7515834dd382d7cab4fa6f09722a9b29` |
| `rtic_mp.dtb` | 173 | `68e6ab5bb2ccdde5e3d87086110257176c0fe55726d1d4f5db6eba3a4b6aca04` |
| initramfs cpio | 512 | `1a920d47b51f4a323bc1033b6aa630db5917421971dcaabf08b36e629afc23c7` |

The private comparison evidence has schema
`a90-rtic-locator-repaired-deterministic-rebuild-h0-v1`, SHA-256
`155e9e1432772502a181f822f01a75318ea81628fb5ba4cb9ef3cc5f4b5f6ef5`,
and `all_selected_outputs_byte_identical=true`. The A and B build-log digests
are respectively
`b738ac8e1c50e119f2be431c4b67f7d067fbc665b21d5954d76bfc733a11d42b`
and
`6f3014a7a8692b4cd3af13b8e369bd054e6b93916cb76c6946f6fd58d73751dd`.
Raw logs and build products remain private and untracked.

## RTIC binding

Both validators independently produce the same evidence:

| Field | Result |
|---|---|
| decision | `PASS` |
| RTIC DTB cardinality / `MP_DATA` cardinality | 1 / 1 |
| MP VA / raw offset / size | `0xffffff8009f00000` / `0x01e80000` / 1,624 |
| interface | `30.3` |
| expected == actual MP SHA-256 | `d95fd9710dd019c5f2e0a273669bcb9b96f81dfdf994afd940b9abb4ff04ec69` |
| RTIC DTB SHA-256 | `68e6ab5bb2ccdde5e3d87086110257176c0fe55726d1d4f5db6eba3a4b6aca04` |
| task offsets decoded from final Image | `88/1704/1728/2144` |

The complete comparison wrapper made from the exact Image, the same first two
stock hardware DTBs, and the generated RTIC DTB is 49,827,613 bytes with
SHA-256
`15b49a71aeb2342a5b5a7e24de27f78a4124bf877f6d8d8f28aaab928fa6bd71`
for both builds. The two private validator JSON files are themselves
byte-identical, SHA-256
`d4c9095c1141066a8533ad9dd14285f3e858a331b0f08f3cbe8c74fc082b953b`.

## Exact delta from the preceding stock-shaped build

The preceding D Image and the repaired final Image have equal length and
differ in exactly 56 bytes across only three ranges:

| Raw-Image range | Bytes | Meaning |
|---|---:|---|
| `0x019862c8..0x019862db` | 20 | vDSO GNU build ID after pre-link path normalization |
| `0x01e80648..0x01e80657` | 16 | four task offsets: all-ones sentinels replaced by little-endian `88/1704/1728/2144` |
| `0x0256a5a8..0x0256a5bb` | 20 | enclosing kernel GNU build ID reflecting the two legitimate pre-link changes |

There is no other Image delta. In particular, the path repair did not alter
CFP code or configuration. The old D Image was
`f17c74663b6e394529f892e6bc3e1f221a56d860c62aefe6ff6fa93f9e8797d7`;
the repaired A/B Image is
`1ddae56f8df97030794a590192e4a4162876736029b1a54fd26173c9287002b7`.

## Remaining hazard and exact next sequence

The repaired MP still honestly contains public content version
`2.7.e26468.30`, not stock `2.7.ef86a6.30`. It still measures the
candidate-derived extent `0x039d3000`, not stock `0x03973000`. Available
source cannot prove how the A90 proprietary RTIC/QHEE consumer treats those
values or whether another proprietary stage measures the whole Image.

Therefore the next unit is one independent H0 review of the already named
complete canary hazard bundle against these exact final bytes. If and only if
that review accepts one narrow canary, later work may allocate a fresh
candidate identity and create a candidate-specific boot package,
qualification, manifest, current D0, attendance, and exact F1 approval. Those
are separate later units; this report creates none of them.

The current tracked resident-health state after H34 remains unproved and must
be freshly established before any future F1. H34 and every earlier consumed
candidate remain non-replayable.

## Independent public H0 review

An independent public-scope review returned `PASS_H0_BUILD_GATE` with no high,
medium, or low finding. It ran 33 focused public RTIC documentation tests and
did not open private build inputs or evidence. The review accepted sequential
fresh output trees sharing the fixed source/toolchain closure as the bounded
determinism test, accepted both path controls as pre-link normalization rather
than output patching, and accepted the 56-byte delta only for the narrow claim
that no other Image or embedded-config byte changed.

The review also confirmed the evidence split: `a90_rtic_mp_consistency.py`
proves wrapper/FDT/`MP_DATA` binding, range, marker, hash, and interface; it
does not decode task offsets or prove the symbol. The separate unchanged
direct-object decoder and all three generated MP C files carry the offset
claim. `PASS_H0_BUILD_GATE` qualifies only this host build gate and grants no
candidate or live authority.

## Boundary

This unit read existing private host build inputs and wrote only private host
build products/evidence plus this tracked report and its tests. It did not
enumerate `/dev`, contact USB, invoke ADB, use a target network, open recovery
or Download mode, build a boot image, or touch A90, S22+, or S20+.
