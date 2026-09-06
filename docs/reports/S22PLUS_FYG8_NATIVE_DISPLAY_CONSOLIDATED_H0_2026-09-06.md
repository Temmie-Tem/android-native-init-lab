# S22+ FYG8 native display — consolidated H0 conclusion

Date: 2026-09-06. Exact target: SM-S906N / g0q / S906NKSS7FYG8.
Status: **REDUCED_MODULE_BUILT_AND_SYMBOL_GRAPH_CHECKED_H0**.
Native screen output, runtime ABI, safe probe and recovery remain **UNPROVED**.

## Final conclusion

The retained source can produce an AArch64 vendor display module with the
identified display diagnostic partition/parameter paths and POC/DDI-SPI transfer
implementations excluded. This has advanced from a source proposal to an actual
Full-LTO/CFI module build and a checked combined USB/display symbol graph.
It does not establish that the panel will initialize, that all transitive paths
are persistence-free, or that a display stall is recoverable.

The bounded H0 implementation and consolidation are complete. No device command,
module load, flash, runtime renderer or new F1 candidate was used. P349 inputs,
Image and its paused state were preserved; A90 and S20+ received no command.

## Evidence across the investigations

| Question | Current evidence | Limit |
| --- | --- | --- |
| Display interface | Exact Image has DRM/KMS; framebuffer/fbdev/VT support is absent. Vendor msm_drm is needed beyond the existing USB plan. | A DRM node or active display is not yet observed in native runtime. |
| Panel selection | Retained boot evidence selects S6E3FAC_AMB655AY01; corresponding DT declares 1080x2340 modes. | Retained evidence is not a fresh panel/mode binding. |
| Stock module linkage | Extracted stock graph: 50 modules, 2,965 imports resolved against exact Image/providers. | Stock display/debug paths include persistent writes; do not load the stock graph as a shortcut. |
| CPU buffer route | Vendor GEM supports a WC allocation/mapping route. | Coherency, pitch, formats and flip completion are not runtime-qualified. |
| Reduced module | Actual Full-LTO/CFI build succeeds; known display persistence imports and original POC/SPI objects are excluded. | Functional omissions and vendor module ABI require qualification. |
| Combined graph | 82 modules, 4,391 versioned imports, zero missing/ambiguous/CRC-mismatched providers; dependency graph is acyclic. | This is symbol resolution, not structure-layout, order, probe or recovery proof. |
| Visible PID1 indication | Run identifier plus changing counter correlated with authenticated same-boot PID1 evidence remains the intended criterion. | No renderer was implemented or run in this unit. |

The source records are the [initial investigation](S22PLUS_FYG8_NATIVE_DISPLAY_RESEARCH_H0_2026-09-06.md),
[binary/panel/cache follow-up](S22PLUS_FYG8_NATIVE_DISPLAY_FOLLOWUP_H0_2026-09-06.md),
and [minimal-build investigation](S22PLUS_FYG8_NATIVE_DISPLAY_MINIMAL_BUILD_RESEARCH_H0_2026-09-06.md).
Their historic evidence and limits remain unchanged. This report supersedes only
their statements that a reduced module build had not yet been attempted.

## Actual implementation

[Source patch and recipe](../../workspace/public/src/kernel-modules/s22plus_native_display_h0/README.md)
contain eleven changed/added files and before/after hashes.

- Paired make/header changes exclude DP, HDCP and SDE VM. The separate
  SECDP_SWITCH define also had to be removed: its EDID function otherwise accessed
  a member omitted by the SECDP gate.
- The isolated vendor module config disables SEC_DEBUG, SEC_PARAM,
  HDCP_QSEECOM and SEC_DISPLAYPORT. A forced-header guard rejects either enabled
  diagnostic option, including module forms. The running Image configuration is
  not changed, and shared stock debug modules are not relabeled disabled.
- Kbuild selects explicit unsupported POC/SPI implementations. POC init clears
  support and controller callback; SPI init clears support without registration.
  No POC dispatch, SPI table parsing, SPI speed change or SPI transfer occurs in
  these replacements. The otherwise retained SPI wrapper also returns unsupported.
- Original POC/SPI sources remain unbuilt. NULL SPI-command getters are checked
  by the inspected callers. Some POC callers ignore error returns and could
  display empty/stale diagnostic values; those values are not successful reads.
- Explicit existing header includes resolve build dependencies. An unused KGSL
  include was removed; its only callers were already inside `#if 0`.
  The display timestamp now uses SOURCE_DATE_EPOCH instead of wall-clock time.

This is a reduced functional scope, not a proof of the smallest possible module.
Other panel, sysfs and diagnostic code remains. Ordinary DSI command handling was
not replaced with a new raw framebuffer or physical-memory path.

## Build evidence and corrected assumptions

Private evidence root: `workspace/private/outputs/s22-display-build-h0/`.

The initial direct-GKI attempt was unsuitable: the fixed GKI config has QCOM_SCM
disabled and lacks required vendor declarations. Header inclusion alone would
leave incorrect fallback behavior. That approach was abandoned with its logs
preserved. It was not made to pass by ignoring implicit declarations or replacing
secure calls with invented success values.

The successful path uses the retained supplier `msm-kernel` source and
`vendor/waipio-gki_defconfig` in a separate output directory. Four options are
then disabled and resolved by olddefconfig. Full-LTO, CFI and MODVERSIONS remain
enabled. This module configuration differs from the fixed Image configuration;
that is explicitly not an independent runtime ABI proof.

All 7,222 retained kernel symbol entries matched the exact Image export tables.
Twenty-six external symbols were supplied using CRC, export type and namespace
extracted from verified supporting ELF modules. The generated module metadata
supplies `__this_module`; it was not invented as an external provider.

Build10 compiled/linked the reduced module; build11 incorporated the final SPI
wrapper exclusion and completed successfully. The fixed timestamp allowed reuse
of unchanged compiled objects. Build11 selected 118 objects. No full kernel
image build, signature bypass, forced module load or modpost-warning bypass was
performed. Debug stripping preserves imports, dependencies and vermagic; a full
A/B reproducibility claim is not made.

Final private module: `msm_drm.h0.ko`, **10,534,768 bytes**, SHA-256
`f4e5e9f5cf737f6e128e3bd904f3cadcb961552aa8a2ade86d2b94e01b2239e4`.
Its 641 versioned imports resolve in the final graph. The source/config/command
identities are retained in `final-inputs.json`; intermediate logs describe failed
approaches and are not terminal PASS evidence.

## Verification performed

- Actual compiler preprocessing: intended baseline passes; SEC_DEBUG=y,
  SEC_DEBUG=m, SEC_PARAM=y and SEC_PARAM=m injections each fail at the named
  guard. The baseline has neither those flags nor DP/HDCP/VM/SECDP defines.
- Final binary has no identified partition read/write, sec parameter write or
  SPI transfer/registration imports. Original POC/SPI, DP and HDCP objects are
  absent from the actual object list. Disassembly of unsupported SPI sync returns
  `-EOPNOTSUPP`; other replacement disassemblies are retained.
- Combined graph includes the existing 73-module USB plan plus nine modules.
  Its 82 identities were checked, including the exact existing event-latch module.
  The rebuilt display closure has 25 modules. Kernel/provider resolution covers
  4,391 imports with no ambiguity, missing entry or CRC mismatch.
- The nine additions are msm_drm, msm_dma_iommu_mapping, dev_ril_bridge, lcd,
  llcc-qcom, msm-mmrm, panel_event_notifier, sec_input_notifier and
  sec_panel_notifier. Shared sec_debug remains; sec_qc_dbg_part and sec_param
  are absent from this display graph. This is not a claim that every dependency
  has no persistent effect.
- Fresh patch application with zero fuzz reproduced all eleven after hashes;
  original before hashes remained unchanged. Private Python helpers passed
  py_compile. Documentation links, diff and repository boundary checks apply.

The definitive graph receipt is `union-audit-final.json`; `binary-checks.json`
and `patch-roundtrip.json` retain the preprocessing/build and patch checks.
Provider CRCs are inputs to modpost: their subsequent agreement confirms correct
symbol binding and integration, not an independent C-layout compatibility test.

## Independent review and remaining work

Independent review found no concrete H0 blocker in the inspected POC/SPI
replacements. SPI getter callers check NULL, while ignored POC errors remain a
functional evidence limitation. A bounded scan of the eight added supporting
providers found no direct partition/file-write primitive; hardware register
writes and notifier dispatch remain. This is not a persistence-free transitive
execution proof. No live-safety PASS or activation was granted.

Before a future display experiment, the remaining work is runtime-interface and
initialization qualification, a minimal renderer with explicit buffer ownership
and completion evidence, and a separately reviewed attended candidate/recovery
path. TEST_ONLY is not visible output, nonblocking return is not completion, and
a helper process cannot guarantee recovery from a kernel display stall. A static
photo or changing text alone does not prove PID1 identity.

The public references remain useful at their proper scope:
[Linux 5.10 KMS](https://docs.kernel.org/5.10/gpu/drm-kms.html),
[DRM userspace API](https://www.kernel.org/doc/html/latest/gpu/drm-uapi.html),
[AOSP modetest](https://android.googlesource.com/platform/external/libdrm/+/refs/heads/main/tests/modetest/modetest.c),
and [related SM8450 vendor source](https://github.com/samsung-sm8450-kernel/vendor_qcom_opensource).
They support interface/design research; none substitutes for exact FYG8 runtime
or recovery evidence.
