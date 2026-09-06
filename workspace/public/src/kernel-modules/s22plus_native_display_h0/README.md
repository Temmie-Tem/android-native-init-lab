# S22+ native display reduction — H0 only

This is a source patch for the retained SM-S906N / g0q / S906NKSS7FYG8
vendor display tree. It is not a flash artifact, module-load recipe, capability
activation or replacement for the current P349 candidate.

- `display-reduction.patch`: eleven changed/added source files; DP/HDCP/VM
  configuration reduction, paired diagnostic guard, unsupported POC/SPI
  implementations, explicit header dependencies and deterministic build timestamp.
- `module-config.fragment`: four disabled options for the isolated **vendor
  module** configuration. It must not replace the fixed Image configuration.
- `source-identities.json`: before/after identities for exact patch application.

The original POC/SPI implementations remain in the source tree but are not built.
Unsupported functions return errors or do not dispatch; POC diagnostic output
must not be interpreted as successful device reads. Other display functions,
including ordinary panel command handling and sysfs interfaces, remain.

The paired build guard addresses the observed diagnostic-triggered persistent
partition/parameter write hazard and applies only to this reduction variant.
Its review trigger is any change to the guarded options, forced headers or
reachable diagnostic code. It can be retired when an independent source/binary
review establishes that enabling those options cannot restore the identified
write paths; it is not a new permanent repository boundary.

## Reproduction prerequisites

Use a private writable copy of the retained `display-drivers` tree. Check each
before hash, apply the patch with `patch --batch --fuzz=0 -p1`, and check each
after hash. The checked roundtrip reproduced all eleven files.

Prepare a separate vendor kernel output with the retained `msm-kernel` source,
`vendor/waipio-gki_defconfig`, and Android clang r416183b. Disable the four
fragment options with `scripts/config`; run `olddefconfig` and `modules_prepare`
and check their effective values. Preserve Full-LTO, CFI and MODVERSIONS.
Do not use the fixed GKI config as the vendor module config: it lacks required
Qualcomm declarations and enables incorrect fallback paths for this purpose.

The successful external build used `M=<private display copy>`,
`DISPLAY_ROOT=<same copy>`, `CONFIG_DRM_MSM=m`, `MODNAME=msm_drm`, the vendor
source as KERNEL_SRC/KERNEL_ROOT, and its include/include-uapi search paths.
`SOURCE_DATE_EPOCH=1754027756` fixes the display build timestamp.
The full compiler environment and argv are retained in the private
`workspace/private/outputs/s22-display-build-h0/build-command.json`.

Supply the exact Image-matched kernel symbol table and verified supporting
module exports to modpost. Do not fabricate missing exports, suppress errors or
use an arbitrary symbol table. This build extracted CRC, export type and
namespace for 26 needed symbols from verified stock ELF files. The kernel's
7,222 entries were compared with the exact Image export tables.
Provider-supplied version agreement does not independently validate C structure
layout or runtime ABI.

Private build11 completed with no compiler/modpost error. Its debug-stripped
AArch64 module is 10,534,768 bytes, SHA-256
`f4e5e9f5cf737f6e128e3bd904f3cadcb961552aa8a2ade86d2b94e01b2239e4`.
Binaries and raw logs remain private. No reproducible A/B claim is made.

See the [consolidated findings](../../../../../docs/reports/S22PLUS_FYG8_NATIVE_DISPLAY_CONSOLIDATED_H0_2026-09-06.md)
for verification scope, failed approaches and remaining runtime limits.
