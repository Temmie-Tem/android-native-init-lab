# A90 stock-shaped MPGen catalog and deterministic rebuild — H0

Date: 2026-08-22
Target: Samsung Galaxy A90 5G only
Tier: H0 host-only public-source acquisition, build, and artifact analysis
Device contact: none
Authority: no candidate, D0, D1, F1, rollback, reboot, or live authority
Disposition: the stock 3/1/2/0 catalog shape and stock MP creation time are
reproduced deterministically; exact stock MPGen and stock MP equivalence remain
unproved

## Result

The bounded question from the preceding public-MPGen control is answered in
two parts:

1. **The stock feature catalog is present in public history.** The historical
   Qualcomm dump at
   [`381c7b77b9e4`](https://github.com/tadiphone-caf/vendor_qcom_proprietary/commit/381c7b77b9e47d4cf81d9a9ac2b9e7597ec9b3e5)
   contains exactly the stock A90 feature names, order, and cardinality: RO 3,
   WK 1, WU 2, AW 0. It predates the public addition of `selinux_state`.
2. **MP creation time is deterministic without changing MPGen source bytes.**
   A private host launcher fixes MPGen's Python clock to the stock MP epoch,
   while a build-only host `date` adapter preserves Samsung's exact UTS string
   and supplies the corresponding initramfs epoch. Two independent output
   trees produce byte-identical MP source, XML, DTS, DTB, `System.map`, and
   initramfs bytes.

This does **not** reproduce the exact stock MP. The public content version is
`2.7.e26468.30`, not stock `2.7.ef86a6.30`; the rebuilt kernel-size field is
different; and the unmodified public DWARF locator leaves four task offsets at
`-1`. Those differences are kept visible. No value was injected into the MP.

## Frozen public source

| Surface | Exact identity |
|---|---|
| public repository commit | `381c7b77b9e47d4cf81d9a9ac2b9e7597ec9b3e5` |
| `qrsp/mpgen` Git tree | `1b75830441422a5bd2380b1b5871d6768f43ef20` |
| historical `mpgen_catalog.py` SHA-256 | `decf021c9f7cb518bf2b9ba24b10548df49e766492ec133df7b2977484a599c4` |
| historical `const.py` SHA-256 | `35ca852f5f115123c7d589d1ad969cd04a5a0bf675c269d114f31330e4c954f0` |
| computed public content version | `2.7.e26468.30` |
| stock content version | `2.7.ef86a6.30` |

The exact stock content version was not found in the public sources searched
for this unit. That is a bounded search result, not proof that no copy exists.
The historical catalog itself is directly inspectable in the
[`381c7b77` tree](https://github.com/tadiphone-caf/vendor_qcom_proprietary/blob/381c7b77b9e47d4cf81d9a9ac2b9e7597ec9b3e5/qrsp/mpgen/mpgen_catalog.py).

The guarded local checkout remained at the exact commit and tree above. The
clock launcher is outside that checkout, and the wrapper rejects tracked,
staged, or untracked changes under `qrsp/mpgen` before every invocation.

## Exact catalog comparison

The historical public catalog and stock MP both contain:

| Type | Ordered assets |
|---|---|
| RO | `linux_banner`, `linux_proc_banner`, `selinux_hooks` |
| WK | `ss_initialized` |
| WU | `.head.text`, `selinux_enforcing` |
| AW | none |

For all six assets, generated and stock records agree on name, virtual
address, length, attributes, digest where applicable, and writer address and
length where applicable. The generated MP is 1,624 bytes, has interface
`30.3`, resides at VA `0xffffff8009f00000` / raw-Image offset `0x01e80000`,
and has no `selinux_state` record.

The fixed creation time is stock-exact:

| Field | Stock | Rebuild C | Rebuild D |
|---|---|---|---|
| MP generated text | `2023-01-12 09:54:31` | same | same |
| MP epoch | `1673517271` | same | same |
| WLAN build tag | `2023-01-12T09:49:35Z` | same | same |
| UTS string | `Thu Jan 12 18:53:40 KST 2023` | same | same |
| initramfs mtime | `1673517220` | same | same |

## Independent rebuild comparison

The two final output trees used the same exact A90 OSRC reconstruction,
`.config`, Snapdragon LLVM 10.0.7 / GNU 4.9 toolchain closure, retained H34
module-signing key, historical MPGen tree, and fixed clocks. C required one
link-stage resume after a local inspection accidentally created five
untracked Python bytecode files and the source-cleanliness guard rejected
MPGen. The files were removed, the same `vmlinux.o` was relinked without source
edits or changed build inputs, and MPGen completed. D completed in one clean
run.

| Artifact | Bytes | C SHA-256 | D SHA-256 | Result |
|---|---:|---|---|---|
| raw `Image` | 48,830,480 | `da50dd6139503d6203239bf23cff0668d0e8f34a4c6c9fecd0b495f314289da5` | `f17c74663b6e394529f892e6bc3e1f221a56d860c62aefe6ff6fa93f9e8797d7` | 40 build-ID bytes differ |
| `System.map` | 6,363,557 | `01df7d8ad1915ef64a48916dd3fee19aadf57005777fb73ad6ebad8e15ff31db` | same | byte-identical |
| `rtic_mp.c` | 20,184 | `66fc4f4db84abeeb0003caa6aa54ea60eadc6a0af09110b7f0130ae87a03c888` | same | byte-identical |
| `rtic_mp.xml` | 2,282 | `6d050ebdcec3e6f92665c58d6828aac381e2bb94a6c097152baa439fee1e1289` | same | byte-identical |
| `rtic_mp.dts` | 234 | `1a5e28c3cd22e9831d263c214293f05ca7c5a6ca6cb173ef154b6680866c587d` | same | byte-identical |
| `rtic_mp.dtb` | 173 | `1976d1b08244b857b62d4f7104201129344c53827a0637b7a964bda674cd98d1` | same | byte-identical |
| initramfs cpio | 512 | `1a920d47b51f4a323bc1033b6aa630db5917421971dcaabf08b36e629afc23c7` | same | byte-identical |

The two Images differ at exactly two 20-byte ranges:
`0x019862c8..0x019862db` and `0x0256a5a8..0x0256a5bb`. The first is the
embedded vDSO GNU build ID; the second is the final kernel GNU build ID. The
vDSO debug metadata records the output-tree-specific `DW_AT_comp_dir`, ending
in `out-stock-shape-fixed-c` or `out-stock-shape-fixed-d`, so its build ID and
then the enclosing kernel build ID change. Zeroing only those two ranges makes
the Images byte-identical with normalized SHA-256
`0f03a462f96b08b48c62e51a909fa748cffe0b925cb8f928f012865d865e4248`.

Therefore clock determinism is closed, while full path-independent Image
reproducibility is not claimed. No further rebuild was spent merely to
normalize debug compilation paths.

In-memory comparison wrappers were assembled from each Image, the unchanged
first two stock hardware DTBs, and the corresponding generated RTIC DTB. Both
pass the existing host-only `a90_rtic_mp_consistency.py` parser. In both cases:

- expected and actual MP SHA-256 are
  `2bcf7869f375a8f39178afa85c097f83c2e895b85bafc2adc64f0b21b48f95a7`;
- MP size is 1,624 at `0x01e80000` / `0xffffff8009f00000`; and
- interface is `30.3`.

The wrappers existed only in memory and were not boot images or candidate
artifacts.

## Exact remaining stock-MP delta

Stock and rebuilt MP are both 1,624 bytes. Exactly 22 bytes differ in three
ranges:

| Range | Bytes | Stock | Rebuild | Meaning |
|---|---:|---|---|---|
| `33..37` | 5 | content-version suffix `f86a6` | `26468` | exact production MPGen source remains unproved |
| `618` | 1 | kernel size `0x03973000` | `0x039d3000` | reconstructed kernel layout/content gap remains unproved |
| `1608..1623` | 16 | `(88, 1704, 1728, 2144)` | four `0xffffffff` values | public DWARF object locator failed |

The task-offset failure is localized. The public locator sees 3,943
compilation units but maps none of the `init/main.c`, `init/version.c`, or
`init/init_task.c` units back to their out-of-tree object paths. Calling the
same unmodified parser on those three exact object files returns
`state=88`, `pid=1704`, `parent=1728`, and `comm=2144`, exactly matching stock.
Thus the data is present and the parser logic can decode it; only automatic
`O=` path location failed. This unit does not silently inject those values.

The kernel-size difference is not explained away. It may be security-relevant
because it is inside the measured policy, and it remains an explicit blocker
to an exact-stock-MP claim.

## Consequence and next sequence

This unit closes the requested H0 work item: stock catalog 3/1/2/0 recreation
and deterministic stock-time generation. It also weakens two earlier
uncertainties: the stock catalog is not missing from all public history, and
the stock task offsets are recoverable from the current DWARF bytes.

It does not qualify a kernel, manifest, D0, or F1. Before any rebuilt-kernel
candidate can claim stock RTIC equivalence, one of these must happen:

1. acquire and bind exact `2.7.ef86a6.30` production MPGen; or
2. separately design and review a minimal compatibility path that fixes the
   out-of-tree locator and explains the kernel-size field without hiding an
   unresolved stock delta.

The previously planned repository unit remains the uncertain-return failed-boot
evidence extension. That is a separate continuation-closure change and does
not gain live authority from this report.

## Boundary

This unit used public web/source hosts and existing private host build inputs.
It did not enumerate or contact `/dev`, USB, ADB, recovery, serial, Download
mode, an A90 endpoint, S22+, or S20+. It did not create a boot image,
candidate, approval, manifest, journal, transfer, reboot, rollback, or device
claim. Consumed experiments remain non-replayable.
