# S22+ FYG8 P3.19 successor module materialization H0

Status: **IMPLEMENTED_REVIEW_PENDING; H0 ONLY; NO LIVE AUTHORITY**

Target: `SM-S906N` / `g0q` / `S906NKSS7FYG8`

This host-only unit consumes the reviewed V2 derivation and materializes the
first exact successor source bundle. It does not build userspace, a boot image,
an Odin package, or a parser binding. It ran no device, ADB, USB, or Odin
command and grants no D0, D1, F1, recovery, replay, or live authority.

## Input boundary

The derivation input is the preserved 14,833-byte V2 receipt, SHA-256
`d8c12396e241e387fe342803eca4537b6728dcda7fb901aa8dc7e591d4745cb2`.
Independent review commit `f88b1cbdbf` confirmed the exact intersection:
fourteen PDIC-closure members, eleven already present, and only three missing.
It also withdrew the false DWC3-replacement framing: the custom latch at row 0
and stock `dwc3-msm.ko` at row 59 coexist.

The materializer reopens all twelve P3.18 materialized sources, including the
5,142-byte plan `682f18fb...`, 30,664-byte wrapper `8c0bf6a4...`, and
397,669-byte runtime include `050a8eb0...`. Nine are copied byte-for-byte. Only
the plan, wrapper, and runtime include change.

Four exact FYG8 modules are read from both candidate-accessible vendor_boot
ramdisk `lib/modules` and stock `vendor_dlkm/lib/modules`. Each pair must be
byte-identical before publication, and both copies are preserved independently
as mode-`0400`, link-count-one files:

| plan role | bytes | SHA-256 | successor index |
|---|---:|---|---:|
| `spu_verify.ko` | 18,608 | `d670a944288dffcc5fbf67a76550dc8a746665113f6ee4354521e482489f4b84` | 70 |
| `mfd_max77705.ko` | 125,840 | `26f238730604789293db237b2bcdc4d44c5f63c263e4298f6e8e28b85d0f6f94` | 71 |
| `pdic_max77705.ko` | 423,456 | `27e988788242888dc0c3acaf835a66585c024b034b07741e619b674ee77db3db` | 72 |
| existing `dwc3-msm.ko` provider | 308,624 | `8913b050419e88699033e957d927beef86742ed035f531dc5c4729f50cea60f1` | 59 |

The `mfd` and `pdic` bytes also match the prior immutable IRQ/DT
disassembly inputs. The DWC3 bytes match the exact P3.18 69-stock-module
closure row, where it was stock index 58 and became effective plan index 59
after the latch prefix. A name in a plan is therefore no longer being used as
a proxy for provider identity.

## Materialized plan and EUD consumer

The exact additions are appended in dependency-safe order:

1. `spu_verify.ko` / `spu_verify` / empty params;
2. `mfd_max77705.ko` / `mfd_max77705` / empty params;
3. `pdic_max77705.ko` / `pdic_max77705` / empty params.

The resulting header is 5,316 bytes, SHA-256 `57d74678...`, and contains 73
unique rows. Its same materialization pass searches for the sole full tuple
`("eud.ko", "eud", "")` and renders
`S22PLUS_O2_EUD_MODULE_INDEX 38U` into that header. The inherited independent
runtime literal `P307_EUD_MODULE_INDEX 37U` is removed.

The 30,895-byte wrapper, SHA-256 `c6ea8dbb...`, defines one helper:

```c
static long p319_after_module_load(size_t index) {
    return index == S22PLUS_O2_EUD_MODULE_INDEX
        ? p307_read_eud_cache()
        : 0;
}
```

Both module loops call that same helper only after their load has succeeded.
The direct loop calls it after `E1_REQUIRE(...p241_load_and_verify_module...)`;
the folded loop calls it after the nonzero load branch has terminated through
`fail_at`. The 397,635-byte runtime include, SHA-256 `3699cfb9...`, retains the
one EUD cache reader but no longer owns an index. The source-bound AArch64 GCC
15 syntax pass succeeds with profile 3 and the frozen P3.18 run ID.

## Exact provider edge

The materializer does not rely only on the earlier prose symbol analysis. Its
minimal ELF64 reader rechecks the bound bytes:

- exact `dwc3-msm.ko` defines and exports
  `dwc3_restart_usb_host_mode` through `__ksymtab`;
- exact `pdic_max77705.ko` has one undefined import and one
  `R_AARCH64_CALL26` relocation at `.text+0x12318`;
- that relocation lies inside `max77705_vdm_dp_select_pin`.

This closes the provider-byte caveat of the V2 unit. It does not authorize a
stub, and it does not yet prove that a future packaged boot contains or loads
these bytes; that proof belongs to the successor intent/build/packaging
closure.

## Fail-closed construction history

Three pre-receipt host-only stops are preserved under distinct private names.
None is current authority:

- `-01-failed-repeated-modinfo` rejected legal repeated `.modinfo parmtype`
  keys; the repair keeps arbitrary repeated metadata but requires exactly one
  `name`, `vermagic`, and `depends` value;
- `-02-failed-dependency-name-normalization` compared file-style hyphens with
  runtime underscores; the repair normalizes only dependency names and keeps
  their original strings in the receipt;
- `-03-failed-relocation-section` assumed generic `.rela.text`; the repair
  binds the exact LTO section `.rela.text.max77705_ccic_event_work`.

The complete `-03` bundle was then used read-only to exercise the corrected
result builder before the sole current `-04` publication. No output directory
was reused or overwritten.

## Receipt and validation

The current private receipt is:

- path:
  `workspace/private/outputs/s22plus_fyg8_p319/successor-module-materialization-v1-20260820-04/result.json`;
- 10,658 bytes;
- SHA-256
  `8b8c1f5afd8c02693901d3552c221bcc73bafa2543c77dfff4954bdba188f6b5`;
- regular mode `0400`, link count one.

The bound implementation is 41,356 bytes, SHA-256 `a693c3be...`; the focused
test source is 13,486 bytes, SHA-256 `13feed07...`. Sixteen implementation and
mutation tests cover exact regeneration, the 73-row delta, unchanged-source
identity, same-plan EUD derivation, both post-load call sites, strict JSON,
module-copy equality, module metadata/order, DWC3 export and PDIC relocation,
source/receipt binding, hostile umask, no-clobber, mode/link count, and
no-authority claims. Three report/ledger/goal checks make the focused module
19/19. Independent `/tmp` regeneration is byte-identical to the current
receipt.

The bounded closure bundle passes 186/186 (materialization, V2, predecessor
closure, P3.19 report, and ledger taxonomy), and common Process-v2 passes
122/122. Full P3.19 discovery passes 351/352; its sole failure is the already
known raw-first source-population receipt mismatch, preserved 1,726 versus
current 1,724, caused by unrelated concurrent dirty S20+ files. This unit
neither edits nor stages those files. Python compilation and scoped whitespace
checks pass.

## Boundary and next step

This is an implementation under the existing unresolved
`module-closure-plan` review obligation; it creates no second pending topic.
Independent review must cover the exact changed closure before a matching
append-only review row may resolve that obligation.

Even after review this unit would qualify only the host materialization
capability. A separate successor intent must bind these exact sources and
module bytes, then build and statically qualify userspace/boot/package bytes.
The bounded live-`/dev/kmsg` parser and structured Carrier summary remain a
later H0 qualification. No candidate or device action may be inferred from
this receipt.
